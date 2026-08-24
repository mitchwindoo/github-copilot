#!/usr/bin/env python3
"""Run repeated Perspective click/action latency profile bundles.

This script orchestrates collect_profile.py for R-04 style interaction
evidence. It is read-only by itself; any process writes must come from the
target screen and need separate scenario-specific duplicate-write checks.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"


def utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def read_json_value(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    return None


def percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100.0) * (len(ordered) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] + ((ordered[upper] - ordered[lower]) * weight)


def stats(values: Iterable[Optional[float]]) -> Dict[str, Any]:
    nums = [value for value in values if isinstance(value, (int, float))]
    if not nums:
        return {"count": 0}
    return {
        "count": len(nums),
        "min": min(nums),
        "median": median(nums),
        "p95": percentile(nums, 95),
        "max": max(nums),
    }


def text_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def redact_command(cmd: List[str]) -> List[str]:
    redacted = list(cmd)
    secret_next = {
        "--browser-url",
        "--endpoint",
        "--token",
        "--browser-click-text",
        "--browser-click-result-text",
    }
    for index, value in enumerate(redacted[:-1]):
        if value in secret_next:
            redacted[index + 1] = "<redacted>"
    return redacted


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


def add_common_args(cmd: List[str], args: argparse.Namespace, run_id: str, out_dir: Path) -> None:
    cmd.extend(
        [
            "--run-id",
            run_id,
            "--route",
            args.route,
            "--duration-sec",
            str(args.duration_sec),
            "--interval-sec",
            str(args.interval_sec),
            "--out-dir",
            str(out_dir),
            "--gateway-alias",
            args.gateway_alias,
            "--scenario",
            "repeated click/action latency profile",
            "--browser-url",
            args.browser_url,
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
            "--browser-click-selector",
            args.browser_click_selector,
            "--browser-click-label",
            args.browser_click_label,
            "--browser-click-after-ready-delay-ms",
            str(args.browser_click_after_ready_delay_ms),
            "--browser-click-timeout-sec",
            str(args.browser_click_timeout_sec),
        ]
    )
    if args.project:
        cmd.extend(["--project", args.project])
    if args.view:
        cmd.extend(["--view", args.view])
    if args.endpoint:
        cmd.extend(["--endpoint", args.endpoint])
    if args.token:
        cmd.extend(["--token", args.token])
    if args.browser_ready_text:
        cmd.extend(["--browser-ready-text", args.browser_ready_text])
    if args.browser_node_modules:
        cmd.extend(["--browser-node-modules", args.browser_node_modules])
    if args.browser_click_text:
        cmd.extend(["--browser-click-text", args.browser_click_text])
    if args.browser_click_result_selector:
        cmd.extend(["--browser-click-result-selector", args.browser_click_result_selector])
    if args.browser_click_result_text:
        cmd.extend(["--browser-click-result-text", args.browser_click_result_text])


def summarize_run(run_dir: Path, command_result: Dict[str, Any], index: int) -> Dict[str, Any]:
    manifest = read_json(run_dir / "manifest.json")
    browser = read_json(run_dir / "browser-summary.json")
    network = read_json(run_dir / "network-summary.json")
    console = read_json_value(run_dir / "browser-console.json")
    logs = read_json(run_dir / "logs.json")
    interaction = browser.get("interaction", {}) if isinstance(browser.get("interaction"), dict) else {}
    return {
        "index": index,
        "runDir": str(run_dir),
        "commandOk": bool(command_result.get("ok")),
        "profileOk": bool(manifest.get("ok")),
        "browserReady": bool(browser.get("ready")),
        "interactionConfigured": bool(interaction.get("configured")),
        "interactionOk": bool(interaction.get("ok")),
        "resultAlreadyMatchedBeforeClick": bool(interaction.get("resultAlreadyMatchedBeforeClick")),
        "clickElapsedMs": to_float(interaction.get("clickElapsedMs")),
        "resultElapsedMs": to_float(interaction.get("resultElapsedMs")),
        "interactionError": interaction.get("error"),
        "browserLongTaskTotalMs": to_float(browser.get("longTaskTotalMs")),
        "browserLargestContentfulPaintMs": to_float((browser.get("largestContentfulPaint") or {}).get("startTime") if isinstance(browser.get("largestContentfulPaint"), dict) else None),
        "networkRequestCount": to_float(network.get("requestCount")),
        "webSocketFramesSent": to_float(network.get("webSocketFramesSent")),
        "webSocketFramesReceived": to_float(network.get("webSocketFramesReceived")),
        "browserConsoleCount": len(console) if isinstance(console, list) else None,
        "focusedLogCount": logs.get("count") if isinstance(logs.get("count"), int) else None,
        "changedResourcesCount": len(manifest.get("changedResources", [])) if isinstance(manifest.get("changedResources"), list) else None,
        "missingEvidenceCount": len(manifest.get("missingEvidence", [])) if isinstance(manifest.get("missingEvidence"), list) else None,
        "commandResult": command_result,
    }


def make_report(path: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    result_stats = summary.get("resultElapsedMs", {})
    click_stats = summary.get("clickElapsedMs", {})
    lines = [
        "# Repeated Click/Action Latency Profile",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Repetitions requested: `{manifest['repetitionsRequested']}`",
        f"Repetitions completed: `{summary.get('repetitionsCompleted', 0)}`",
        f"Interaction label: `{manifest['interactionLabel']}`",
        "",
        f"Evidence grade: `{manifest.get('evidenceGrade', 'Observed')}`",
        "",
        "This is R-04 interaction evidence. It proves latency distribution only for the selected deterministic control and result marker. Process write/message duplication still needs a scenario-specific marker when the interaction writes to real process state.",
        "",
        "## Direct Observations",
        "",
        f"- Completed `{summary.get('repetitionsCompleted', 0)}` of `{manifest['repetitionsRequested']}` requested repetitions.",
        f"- Pre-matched result markers: `{summary.get('preMatchedCount', 0)}`.",
        f"- Runs with changed resources: `{summary.get('changedResourceRunCount', 0)}`.",
        f"- Runs with missing evidence: `{summary.get('missingEvidenceRunCount', 0)}`.",
        "",
        "## Interpretation",
        "",
        "- The selected marker produced a repeatable click-to-visible latency distribution for this route and browser setup.",
        "- Empty changed-resource counts indicate the profiler did not write Perspective resources during these read-only profiles.",
        "",
        "## Unproven Limits",
        "",
        "- This does not prove a customer operator workflow, duplicate process-write behavior, or a causal remediation effect.",
        "- Treat these timings as local fixture observations until repeated on the real control and result marker.",
        "",
        "## Latency Distribution",
        "",
        "| Metric | Count | Min | Median | P95 | Max |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Click dispatch ms | {click_stats.get('count', 0)} | {fmt(click_stats.get('min'))} | {fmt(click_stats.get('median'))} | {fmt(click_stats.get('p95'))} | {fmt(click_stats.get('max'))} |",
        f"| Click to result ms | {result_stats.get('count', 0)} | {fmt(result_stats.get('min'))} | {fmt(result_stats.get('median'))} | {fmt(result_stats.get('p95'))} | {fmt(result_stats.get('max'))} |",
        "",
        "## Runs",
        "",
        "| # | OK | Pre-matched | Click ms | Result ms | Console | Logs | Changed |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for run in summary.get("runs", []):
        lines.append(
            f"| {run.get('index')} | {yes(run.get('interactionOk'))} | {yes(run.get('resultAlreadyMatchedBeforeClick'))} | "
            f"{fmt(run.get('clickElapsedMs'))} | {fmt(run.get('resultElapsedMs'))} | "
            f"{run.get('browserConsoleCount')} | {run.get('focusedLogCount')} | {run.get('changedResourcesCount')} |"
        )
    lines.extend(["", "## Notes", ""])
    for note in summary.get("notes", []):
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def yes(value: Any) -> str:
    return "yes" if bool(value) else "no"


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        if abs(float(value)) >= 1000:
            return f"{float(value):,.0f}"
        return f"{float(value):.3f}".rstrip("0").rstrip(".")
    return str(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run repeated R-04 click/action latency profiles.")
    parser.add_argument("--endpoint", help="Runner Web Dev endpoint. Env fallback matches collect_profile.py.")
    parser.add_argument("--token", help="Runner token. Env fallback matches collect_profile.py.")
    parser.add_argument("--project", help="Target project. Env fallback matches collect_profile.py.")
    parser.add_argument("--route", required=True, help="Perspective route/page path.")
    parser.add_argument("--view", help="Perspective view path. Pass this when route resolution is ambiguous.")
    parser.add_argument("--run-id", required=True, help="Stable repeated-run identifier.")
    parser.add_argument("--out-dir", required=True, help="Evidence output root.")
    parser.add_argument("--repetitions", type=int, default=7, help="Number of repeated click profiles. Default: 7.")
    parser.add_argument("--duration-sec", type=float, default=8.0, help="Gateway sample duration per profile.")
    parser.add_argument("--interval-sec", type=float, default=2.0, help="Gateway sample interval per profile.")
    parser.add_argument("--gateway-alias", default="configured-gateway", help="Non-secret Gateway alias.")
    parser.add_argument("--browser-url", required=True, help="Perspective route URL to probe.")
    parser.add_argument("--browser-url-alias", default="configured-gateway", help="Non-secret browser URL alias.")
    parser.add_argument("--browser-ready-selector", default="body", help="Browser ready selector.")
    parser.add_argument("--browser-ready-text", help="Optional ready text.")
    parser.add_argument("--browser-viewport", default="1366x768", help="Browser viewport, e.g. 1366x768.")
    parser.add_argument("--browser-timeout-sec", type=int, default=45, help="Browser timeout seconds.")
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=3000, help="Post-ready browser wait.")
    parser.add_argument("--browser-node-modules", help="Optional Playwright node_modules path.")
    parser.add_argument("--browser-click-selector", required=True, help="Selector to click after route readiness.")
    parser.add_argument("--browser-click-text", help="Optional text filter for click target. Redacted in stored commands.")
    parser.add_argument("--browser-click-label", default="interaction", help="Non-secret interaction label.")
    parser.add_argument("--browser-click-after-ready-delay-ms", type=int, default=0, help="Delay after route readiness before click.")
    parser.add_argument("--browser-click-result-selector", help="Selector that must become visible after click.")
    parser.add_argument("--browser-click-result-text", help="Text that must appear after click. Redacted in stored commands.")
    parser.add_argument("--browser-click-timeout-sec", type=int, default=10, help="Click/result timeout seconds.")
    parser.add_argument("--command-timeout-sec", type=int, default=180, help="Timeout for each child profile.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue after a failed repetition.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")
    if not args.browser_click_result_selector and not args.browser_click_result_text:
        raise SystemExit("Provide --browser-click-result-selector or --browser-click-result-text")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    driver_log_dir = out_dir / "driver-logs"
    manifest = {
        "ok": True,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "scenario": "repeated click/action latency profile",
        "evidenceGrade": "Observed",
        "project": args.project,
        "route": args.route,
        "view": args.view,
        "gatewayAlias": args.gateway_alias,
        "browserUrlAlias": args.browser_url_alias,
        "interactionLabel": args.browser_click_label,
        "repetitionsRequested": args.repetitions,
        "durationSec": args.duration_sec,
        "intervalSec": args.interval_sec,
        "changedResources": [],
        "missingEvidence": [],
        "files": ["manifest.json", "summary.json", "summary.md", "repetition-*/", "driver-logs/"],
        "notes": [
            "Read-only repeated interaction profile run.",
            "Raw browser URLs, tokens, endpoints, click text, and result text are not written by this orchestrator.",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)

    runs: List[Dict[str, Any]] = []
    for index in range(1, args.repetitions + 1):
        run_dir = out_dir / f"repetition-{index:02d}"
        child_run_id = f"{args.run_id}-rep-{index:02d}"
        cmd = [sys.executable, str(COLLECT_SCRIPT)]
        add_common_args(cmd, args, child_run_id, run_dir)
        command_result = run_command(cmd, driver_log_dir, f"repetition-{index:02d}", args.command_timeout_sec)
        run_summary = summarize_run(run_dir, command_result, index)
        runs.append(run_summary)
        write_json(out_dir / "runs-progress.json", {"runs": runs})
        if not run_summary.get("interactionOk") and not args.continue_on_error:
            manifest["ok"] = False
            break

    completed = [run for run in runs if run.get("commandOk") and run.get("profileOk") and run.get("interactionOk")]
    pre_matched = [run for run in completed if run.get("resultAlreadyMatchedBeforeClick")]
    changed = [run for run in completed if (run.get("changedResourcesCount") or 0) > 0]
    missing = [run for run in completed if (run.get("missingEvidenceCount") or 0) > 0]
    notes = [
        "Use this distribution only for the selected click selector and result marker.",
        "If resultAlreadyMatchedBeforeClick is true, the interaction marker was ambiguous.",
        "No changed resources in profile manifests proves the profiler did not write project resources; process write/message duplication requires scenario-specific evidence.",
    ]
    if args.repetitions < 7:
        notes.append("Repetition count is below the default seven-run comparison policy; classify results as exploratory.")
    summary = {
        "ok": bool(manifest.get("ok")) and len(completed) == args.repetitions and not pre_matched and not changed and not missing,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "repetitionsRequested": args.repetitions,
        "repetitionsCompleted": len(completed),
        "runs": runs,
        "clickElapsedMs": stats(run.get("clickElapsedMs") for run in completed),
        "resultElapsedMs": stats(run.get("resultElapsedMs") for run in completed),
        "preMatchedCount": len(pre_matched),
        "changedResourceRunCount": len(changed),
        "missingEvidenceRunCount": len(missing),
        "notes": notes,
        "files": ["manifest.json", "summary.json", "summary.md", "repetition-*/", "driver-logs/"],
    }
    manifest["ok"] = summary["ok"]
    manifest["repetitionsCompleted"] = len(completed)
    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "summary.json", summary)
    make_report(out_dir / "summary.md", manifest, summary)
    print(json.dumps({"ok": summary["ok"], "outDir": str(out_dir), "repetitionsCompleted": len(completed), "summary": str(out_dir / "summary.json")}, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
