#!/usr/bin/env python3
"""Run repeated paired Perspective profile bundles.

This script orchestrates collect_profile.py and compare_profiles.py. It is
read-only and is intended for repeated control/target or before/after evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"


def utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(value: str) -> str:
    safe = []
    for ch in value.lower():
        if ch.isalnum():
            safe.append(ch)
        elif ch in ("-", "_"):
            safe.append(ch)
        else:
            safe.append("-")
    out = "".join(safe).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out or "run"


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def redact_command(cmd: List[str]) -> List[str]:
    redacted = list(cmd)
    for index, value in enumerate(redacted[:-1]):
        if value in ("--browser-url", "--endpoint", "--token"):
            redacted[index + 1] = "<redacted>"
    return redacted


def text_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_command(cmd: List[str], log_dir: Path, label: str, timeout_sec: int) -> Dict[str, Any]:
    started = utc_now()
    log_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {
        "label": label,
        "startedAt": started,
        "command": redact_command(cmd),
        "stdoutPath": str(log_dir / f"{label}.stdout.txt"),
        "stderrPath": str(log_dir / f"{label}.stderr.txt"),
    }
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_sec if timeout_sec > 0 else None,
        )
        (log_dir / f"{label}.stdout.txt").write_text(completed.stdout or "", encoding="utf-8", newline="\n")
        (log_dir / f"{label}.stderr.txt").write_text(completed.stderr or "", encoding="utf-8", newline="\n")
        result.update(
            {
                "ok": completed.returncode == 0,
                "returnCode": completed.returncode,
                "finishedAt": utc_now(),
                "timedOut": False,
            }
        )
    except subprocess.TimeoutExpired as exc:
        (log_dir / f"{label}.stdout.txt").write_text(text_output(exc.stdout), encoding="utf-8", newline="\n")
        (log_dir / f"{label}.stderr.txt").write_text(text_output(exc.stderr), encoding="utf-8", newline="\n")
        result.update({"ok": False, "returnCode": None, "finishedAt": utc_now(), "timedOut": True})
    return result


def add_profile_args(cmd: List[str], args: argparse.Namespace, route: str, out_dir: Path, run_id: str, scenario: str, browser_url: Optional[str], ready_text: Optional[str]) -> None:
    cmd.extend(
        [
            "--run-id",
            run_id,
            "--route",
            route,
            "--duration-sec",
            str(args.duration_sec),
            "--interval-sec",
            str(args.interval_sec),
            "--out-dir",
            str(out_dir),
            "--gateway-alias",
            args.gateway_alias,
            "--scenario",
            scenario,
        ]
    )
    if args.project:
        cmd.extend(["--project", args.project])
    if args.endpoint:
        cmd.extend(["--endpoint", args.endpoint])
    if args.token:
        cmd.extend(["--token", args.token])
    if browser_url:
        cmd.extend(
            [
                "--browser-url",
                browser_url,
                "--browser-url-alias",
                args.browser_url_alias,
                "--browser-ready-selector",
                args.browser_ready_selector,
                "--browser-timeout-sec",
                str(args.browser_timeout_sec),
                "--browser-wait-after-ready-ms",
                str(args.browser_wait_after_ready_ms),
                "--browser-viewport",
                args.browser_viewport,
            ]
        )
        if ready_text:
            cmd.extend(["--browser-ready-text", ready_text])
        if args.browser_node_modules:
            cmd.extend(["--browser-node-modules", args.browser_node_modules])


def delta_at(comparison: Dict[str, Any], section: str, metric: str) -> Optional[float]:
    bucket = comparison.get(section, {})
    if not isinstance(bucket, dict):
        return None
    item = bucket.get(metric, {})
    if not isinstance(item, dict):
        return None
    value = item.get("delta")
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def stats(values: Iterable[Optional[float]]) -> Dict[str, Any]:
    nums = [value for value in values if isinstance(value, (int, float))]
    if not nums:
        return {"count": 0}
    return {
        "count": len(nums),
        "median": median(nums),
        "min": min(nums),
        "max": max(nums),
        "targetAboveControlCount": sum(1 for value in nums if value > 0),
        "targetBelowControlCount": sum(1 for value in nums if value < 0),
        "equalCount": sum(1 for value in nums if value == 0),
    }


def aggregate(pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    comparisons = [read_json(Path(pair["comparisonDir"]) / "comparison.json") for pair in pairs if pair.get("comparisonOk")]
    metrics = {
        "static.componentCount": ("staticDeltas", "componentCount"),
        "static.bindingCount": ("staticDeltas", "bindingCount"),
        "static.viewJsonBytes": ("staticDeltas", "viewJsonBytes"),
        "browser.largestContentfulPaintMs": ("browserDeltas", "largestContentfulPaintMs"),
        "browser.longTaskTotalMs": ("browserDeltas", "longTaskTotalMs"),
        "browser.domNodeCount": ("browserDeltas", "domNodeCount"),
        "browser.resourceTransferSize": ("browserDeltas", "resourceTransferSize"),
        "gateway.processCpuLoadAvg": ("gatewayDeltas", "processCpuLoad"),
        "gateway.heapUsedBytesAvg": ("gatewayDeltas", "heapUsedBytes"),
        "session.browserSessionCountAvg": ("sessionDeltas", "browserSessionCount"),
        "session.browserActivePagesAvg": ("sessionDeltas", "browserActivePages"),
    }
    return {
        name: stats(delta_at(comparison, section, metric) for comparison in comparisons)
        for name, (section, metric) in metrics.items()
    }


def make_report(path: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    lines = [
        "# Repeated Perspective Profile Comparison",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Comparison kind: `{manifest['comparisonKind']}`",
        f"Pairs requested: `{manifest['pairsRequested']}`",
        f"Pairs completed: `{summary.get('pairsCompleted', 0)}`",
        f"Evidence grade: `{manifest.get('evidenceGrade', 'Observed')}`",
        "",
        "## Direct Observations",
        "",
        "- Each completed pair contains one control profile, one target profile, and one generated comparison.",
        "- Aggregates below are target-minus-control deltas from completed pairs.",
        "",
        "This report is repeated observational evidence. Treat it as causal only when the scenario is a controlled before/after remediation, functional equivalence and rollback/readback gates pass, and the declared comparison policy is met.",
        "",
        "## Median Target-Minus-Control Deltas",
        "",
        "| Metric | Count | Median delta | Min | Max | Target above | Target below |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for metric, item in summary.get("aggregates", {}).items():
        lines.append(
            "| {metric} | {count} | {median} | {min_value} | {max_value} | {above} | {below} |".format(
                metric=metric,
                count=item.get("count", 0),
                median=format_number(item.get("median")),
                min_value=format_number(item.get("min")),
                max_value=format_number(item.get("max")),
                above=item.get("targetAboveControlCount", 0),
                below=item.get("targetBelowControlCount", 0),
            )
        )
    lines.extend(["", "## Interpretation", ""])
    lines.append("Use these deltas to separate target-route cost from same-Gateway control-route noise. Interpret direction and magnitude with the paired scenario, browser cache state, and concurrent Gateway load.")
    lines.extend(["", "## Unproven Limits", ""])
    lines.append("- This wrapper does not prove a remediation or final diagnosis by itself.")
    lines.append("- Customer-specific conclusions require the same route, selector, data, sessions, and cadence on the target Gateway.")
    lines.extend(["", "## Notes", ""])
    for note in summary.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def format_number(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run repeated collect_profile.py control/target pairs.")
    parser.add_argument("--endpoint", help="Runner Web Dev endpoint. Env fallback matches collect_profile.py.")
    parser.add_argument("--token", help="Runner token. Env fallback matches collect_profile.py.")
    parser.add_argument("--project", help="Target project. Env fallback matches collect_profile.py.")
    parser.add_argument("--run-id", required=True, help="Stable repeated-run identifier.")
    parser.add_argument("--out-dir", required=True, help="Evidence output root.")
    parser.add_argument("--pairs", type=int, default=7, help="Number of control/target pairs. Default: 7.")
    parser.add_argument("--comparison-kind", default="control-target", choices=["control-target", "before-after"], help="Comparison semantics.")
    parser.add_argument("--control-route", required=True, help="Control/before route.")
    parser.add_argument("--target-route", required=True, help="Target/after route.")
    parser.add_argument("--control-browser-url", help="Control/before browser URL.")
    parser.add_argument("--target-browser-url", help="Target/after browser URL.")
    parser.add_argument("--control-ready-text", help="Control/before ready text.")
    parser.add_argument("--target-ready-text", help="Target/after ready text.")
    parser.add_argument("--browser-url-alias", default="configured-gateway", help="Non-secret browser URL alias.")
    parser.add_argument("--browser-ready-selector", default="body", help="Browser ready selector.")
    parser.add_argument("--browser-viewport", default="1366x768", help="Browser viewport, e.g. 1366x768.")
    parser.add_argument("--browser-timeout-sec", type=int, default=45, help="Browser timeout seconds.")
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=5000, help="Post-ready browser wait.")
    parser.add_argument("--browser-node-modules", help="Optional Playwright node_modules path.")
    parser.add_argument("--duration-sec", type=float, default=8.0, help="Gateway sample duration per profile.")
    parser.add_argument("--interval-sec", type=float, default=2.0, help="Gateway sample interval per profile.")
    parser.add_argument("--gateway-alias", default="configured-gateway", help="Non-secret Gateway alias.")
    parser.add_argument("--command-timeout-sec", type=int, default=180, help="Timeout for each child command.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue remaining pairs after a failed child run.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.pairs < 1:
        raise SystemExit("--pairs must be at least 1")
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    driver_log_dir = out_dir / "driver-logs"
    pairs: List[Dict[str, Any]] = []
    manifest = {
        "ok": True,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "comparisonKind": args.comparison_kind,
        "scenario": f"repeated {args.comparison_kind} profile comparison",
        "evidenceGrade": "Observed",
        "pairsRequested": args.pairs,
        "gatewayAlias": args.gateway_alias,
        "browserUrlAlias": args.browser_url_alias,
        "project": args.project,
        "controlRoute": args.control_route,
        "targetRoute": args.target_route,
        "durationSec": args.duration_sec,
        "intervalSec": args.interval_sec,
        "browserWaitAfterReadyMs": args.browser_wait_after_ready_ms,
        "changedResources": [],
        "missingEvidence": [],
        "files": ["manifest.json", "summary.json", "summary.md", "pair-*/", "driver-logs/"],
        "notes": [
            "Read-only repeated paired profile run.",
            "Raw browser URLs, tokens, and endpoints are not written by this orchestrator.",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)

    for pair_index in range(1, args.pairs + 1):
        pair_slug = f"pair-{pair_index:02d}"
        control_dir = out_dir / pair_slug / "control"
        target_dir = out_dir / pair_slug / "target"
        comparison_dir = out_dir / pair_slug / "comparison"
        control_run_id = f"{args.run_id}-{pair_slug}-control"
        target_run_id = f"{args.run_id}-{pair_slug}-target"

        control_cmd = [sys.executable, str(COLLECT_SCRIPT)]
        add_profile_args(
            control_cmd,
            args,
            args.control_route,
            control_dir,
            control_run_id,
            f"{args.comparison_kind} {pair_slug} control",
            args.control_browser_url,
            args.control_ready_text,
        )
        control_result = run_command(control_cmd, driver_log_dir, f"{pair_slug}-control", args.command_timeout_sec)
        if not control_result.get("ok") and not args.continue_on_error:
            pairs.append({"pair": pair_index, "controlDir": str(control_dir), "controlOk": False, "controlResult": control_result})
            manifest["ok"] = False
            break

        target_cmd = [sys.executable, str(COLLECT_SCRIPT)]
        add_profile_args(
            target_cmd,
            args,
            args.target_route,
            target_dir,
            target_run_id,
            f"{args.comparison_kind} {pair_slug} target",
            args.target_browser_url,
            args.target_ready_text,
        )
        target_result = run_command(target_cmd, driver_log_dir, f"{pair_slug}-target", args.command_timeout_sec)
        if not target_result.get("ok") and not args.continue_on_error:
            pairs.append(
                {
                    "pair": pair_index,
                    "controlDir": str(control_dir),
                    "targetDir": str(target_dir),
                    "controlOk": bool(control_result.get("ok")),
                    "targetOk": False,
                    "controlResult": control_result,
                    "targetResult": target_result,
                }
            )
            manifest["ok"] = False
            break

        compare_cmd = [
            sys.executable,
            str(COMPARE_SCRIPT),
            "--control-dir",
            str(control_dir),
            "--target-dir",
            str(target_dir),
            "--out-dir",
            str(comparison_dir),
            "--label",
            f"{args.run_id}-{pair_slug}",
        ]
        compare_result = run_command(compare_cmd, driver_log_dir, f"{pair_slug}-comparison", args.command_timeout_sec)
        pair_record = {
            "pair": pair_index,
            "controlDir": str(control_dir),
            "targetDir": str(target_dir),
            "comparisonDir": str(comparison_dir),
            "controlOk": bool(control_result.get("ok")),
            "targetOk": bool(target_result.get("ok")),
            "comparisonOk": bool(compare_result.get("ok")),
            "controlResult": control_result,
            "targetResult": target_result,
            "compareResult": compare_result,
        }
        pairs.append(pair_record)
        write_json(out_dir / "pairs-progress.json", {"pairs": pairs})
        if not compare_result.get("ok") and not args.continue_on_error:
            manifest["ok"] = False
            break

    completed = [pair for pair in pairs if pair.get("controlOk") and pair.get("targetOk") and pair.get("comparisonOk")]
    aggregates = aggregate(completed)
    notes = [
        "A repeated control-target run quantifies route differences; it does not prove a remediation.",
        "For before-after remediation, require functional equivalence, no safety regression, and rollback/readback evidence before a causal claim.",
    ]
    if args.pairs < 7:
        notes.append("Pair count is below the default seven-pair policy; classify results as exploratory.")
    summary = {
        "ok": bool(manifest.get("ok")) and len(completed) == args.pairs,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "pairsRequested": args.pairs,
        "pairsCompleted": len(completed),
        "pairs": pairs,
        "aggregates": aggregates,
        "notes": notes,
        "files": ["manifest.json", "summary.json", "summary.md", "pair-*/", "driver-logs/"],
    }
    manifest["ok"] = summary["ok"]
    manifest["pairsCompleted"] = len(completed)
    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "summary.json", summary)
    make_report(out_dir / "summary.md", manifest, summary)
    print(json.dumps({"ok": summary["ok"], "outDir": str(out_dir), "pairsCompleted": len(completed), "summary": str(out_dir / "summary.json")}, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
