#!/usr/bin/env python3
"""Run repeated cold and warm Perspective route-load profile bundles."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"


def utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data: Any) -> None:
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


def text_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        if math.isnan(parsed) or math.isinf(parsed):
            return None
        return parsed
    return None


def stats(values: Iterable[Optional[float]]) -> Dict[str, Any]:
    nums = [value for value in values if isinstance(value, (int, float))]
    if not nums:
        return {"count": 0}
    return {
        "count": len(nums),
        "min": min(nums),
        "median": median(nums),
        "max": max(nums),
    }


def fmt(value: Any) -> str:
    parsed = number(value)
    if parsed is None:
        return ""
    if abs(parsed) >= 1000:
        return f"{parsed:,.0f}"
    return f"{parsed:.3f}".rstrip("0").rstrip(".")


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_rmtree(path: Path, *allowed_roots: Path) -> None:
    target = path.resolve()
    roots = [root.resolve() for root in allowed_roots if root]
    if not roots or not any(is_relative_to(target, root) for root in roots):
        raise RuntimeError(f"Refusing recursive delete outside intended output roots: {target}")
    if target.exists():
        shutil.rmtree(target)


def redact_command(cmd: List[str]) -> List[str]:
    redacted = list(cmd)
    secret_next = {
        "--browser-url",
        "--endpoint",
        "--token",
        "--browser-ready-text",
        "--browser-node-modules",
        "--browser-user-data-dir",
    }
    for index, value in enumerate(redacted[:-1]):
        if value in secret_next:
            redacted[index + 1] = "<redacted>"
    return redacted


def run_command(cmd: List[str], log_dir: Path, label: str, timeout_sec: int) -> Dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {
        "label": label,
        "startedAt": utc_now(),
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


def add_profile_args(cmd: List[str], args: argparse.Namespace, run_id: str, run_dir: Path, phase: str, user_data_dir: Path) -> None:
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
            str(run_dir.resolve()),
            "--gateway-alias",
            args.gateway_alias,
            "--scenario",
            f"{phase} route load profile",
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
            "--browser-user-data-dir",
            str(user_data_dir.resolve()),
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
    if args.browser_node:
        cmd.extend(["--browser-node", args.browser_node])
    if args.browser_node_modules:
        cmd.extend(["--browser-node-modules", args.browser_node_modules])


def summarize_profile(run_dir: Path, command_result: Dict[str, Any], phase: str, index: int, counted: bool) -> Dict[str, Any]:
    manifest = read_json(run_dir / "manifest.json")
    browser = read_json(run_dir / "browser-summary.json")
    network = read_json(run_dir / "network-summary.json")
    logs = read_json(run_dir / "logs.json")
    console = read_json_value(run_dir / "browser-console.json")
    lcp = browser.get("largestContentfulPaint") if isinstance(browser.get("largestContentfulPaint"), dict) else {}
    heap = browser.get("heap") if isinstance(browser.get("heap"), dict) else {}
    return {
        "phase": phase,
        "index": index,
        "counted": counted,
        "runDir": str(run_dir),
        "commandOk": bool(command_result.get("ok")),
        "profileOk": bool(manifest.get("ok")),
        "browserReady": bool(browser.get("ready")),
        "persistentContext": bool(browser.get("persistentContext")),
        "primaryReadyElapsedWallMs": number(browser.get("primaryReadyElapsedWallMs")),
        "primaryReadyElapsedBrowserMs": number(browser.get("primaryReadyElapsedBrowserMs")),
        "largestContentfulPaintMs": number(lcp.get("startTime")),
        "longTaskTotalMs": number(browser.get("longTaskTotalMs")),
        "domNodeCount": number(browser.get("domNodeCount")),
        "browserHeapUsedBytes": number(heap.get("usedJSHeapSize")),
        "resourceTransferSize": number(browser.get("resourceTransferSize")),
        "networkRequestCount": number(network.get("requestCount")),
        "webSocketBytesReceived": number(network.get("webSocketBytesReceived")),
        "browserConsoleCount": len(console) if isinstance(console, list) else None,
        "focusedLogCount": logs.get("count") if isinstance(logs.get("count"), int) else None,
        "changedResourcesCount": len(manifest.get("changedResources", [])) if isinstance(manifest.get("changedResources"), list) else None,
        "missingEvidenceCount": len(manifest.get("missingEvidence", [])) if isinstance(manifest.get("missingEvidence"), list) else None,
        "commandResult": command_result,
    }


def aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counted = [row for row in rows if row.get("counted")]
    phases = sorted({str(row.get("phase")) for row in counted})
    metrics = (
        "primaryReadyElapsedWallMs",
        "primaryReadyElapsedBrowserMs",
        "largestContentfulPaintMs",
        "longTaskTotalMs",
        "domNodeCount",
        "browserHeapUsedBytes",
        "resourceTransferSize",
        "networkRequestCount",
        "webSocketBytesReceived",
    )
    by_phase: Dict[str, Any] = {}
    for phase in phases:
        phase_rows = [row for row in counted if row.get("phase") == phase]
        by_phase[phase] = {
            "count": len(phase_rows),
            "okCount": sum(1 for row in phase_rows if row.get("commandOk") and row.get("profileOk") and row.get("browserReady")),
            "metrics": {metric: stats(number(row.get(metric)) for row in phase_rows) for metric in metrics},
        }
    deltas: Dict[str, Any] = {}
    if "cold" in by_phase and "warm" in by_phase:
        for metric in metrics:
            cold_median = number(by_phase["cold"]["metrics"][metric].get("median"))
            warm_median = number(by_phase["warm"]["metrics"][metric].get("median"))
            deltas[metric] = None if cold_median is None or warm_median is None else warm_median - cold_median
    return {"byPhase": by_phase, "warmMinusColdMedianDeltas": deltas}


def write_report(out_dir: Path, manifest: Dict[str, Any], rows: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    lines = [
        "# Cold/Warm Perspective Route Load Profiles",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Route: `{manifest['route']}`",
        f"Cold repetitions: `{manifest['coldRepetitions']}`",
        f"Warm repetitions: `{manifest['warmRepetitions']}`",
        f"Warm prime OK: `{str(summary.get('warmPrimeOk', False)).lower()}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        "",
        "Cold observations use fresh Chromium profile directories. Warm observations use one shared Chromium profile directory after an uncounted priming load. Treat deltas as cache/profile-state evidence for this route and scenario, not as a universal browser-cache rule.",
        "",
        "## Counted Runs",
        "",
        "| Phase | # | OK | Ready wall ms | LCP ms | Long tasks ms | DOM | Heap bytes | Transfer bytes | Console | Logs |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        if not row.get("counted"):
            continue
        ok = bool(row.get("commandOk") and row.get("profileOk") and row.get("browserReady"))
        lines.append(
            "| {phase} | {index} | `{ok}` | {ready} | {lcp} | {long} | {dom} | {heap} | {transfer} | {console} | {logs} |".format(
                phase=row.get("phase"),
                index=row.get("index"),
                ok=str(ok).lower(),
                ready=fmt(row.get("primaryReadyElapsedWallMs")),
                lcp=fmt(row.get("largestContentfulPaintMs")),
                long=fmt(row.get("longTaskTotalMs")),
                dom=fmt(row.get("domNodeCount")),
                heap=fmt(row.get("browserHeapUsedBytes")),
                transfer=fmt(row.get("resourceTransferSize")),
                console=row.get("browserConsoleCount"),
                logs=row.get("focusedLogCount"),
            )
        )
    by_phase = summary.get("aggregates", {}).get("byPhase") or {}
    if by_phase:
        lines.extend(
            [
                "",
                "## Phase Aggregates",
                "",
                "| Phase | Count | OK | Ready median ms | LCP median ms | Long tasks median ms | DOM median | Heap median bytes | Transfer median bytes |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for phase in sorted(by_phase):
            phase_summary = by_phase.get(phase) or {}
            metrics = phase_summary.get("metrics") or {}
            lines.append(
                "| {phase} | {count} | {ok_count} | {ready} | {lcp} | {long} | {dom} | {heap} | {transfer} |".format(
                    phase=phase,
                    count=phase_summary.get("count", ""),
                    ok_count=phase_summary.get("okCount", ""),
                    ready=fmt((metrics.get("primaryReadyElapsedWallMs") or {}).get("median")),
                    lcp=fmt((metrics.get("largestContentfulPaintMs") or {}).get("median")),
                    long=fmt((metrics.get("longTaskTotalMs") or {}).get("median")),
                    dom=fmt((metrics.get("domNodeCount") or {}).get("median")),
                    heap=fmt((metrics.get("browserHeapUsedBytes") or {}).get("median")),
                    transfer=fmt((metrics.get("resourceTransferSize") or {}).get("median")),
                )
            )
    lines.extend(["", "## Warm Minus Cold Median Deltas", "", "| Metric | Delta |", "|---|---:|"])
    for metric, value in (summary.get("aggregates", {}).get("warmMinusColdMedianDeltas") or {}).items():
        lines.append(f"| `{metric}` | {fmt(value)} |")
    lines.extend(["", "## Notes", ""])
    for note in summary.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--route", required=True)
    parser.add_argument("--view", default="")
    parser.add_argument("--browser-url", required=True)
    parser.add_argument("--browser-url-alias", default="configured-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-ready-text", default="")
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-timeout-sec", type=float, default=45.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=3000)
    parser.add_argument("--browser-node", default="node")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--duration-sec", type=float, default=8.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--cold-repetitions", type=int, default=3)
    parser.add_argument("--warm-repetitions", type=int, default=3)
    parser.add_argument("--gateway-alias", default="configured-gateway")
    parser.add_argument("--command-timeout-sec", type=int, default=240)
    parser.add_argument("--pause-sec", type=float, default=0.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.cold_repetitions < 1:
        raise SystemExit("--cold-repetitions must be >= 1")
    if args.warm_repetitions < 1:
        raise SystemExit("--warm-repetitions must be >= 1")
    if args.duration_sec < 0:
        raise SystemExit("--duration-sec must be >= 0")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        safe_rmtree(out_dir, Path.cwd(), SKILL_DIR)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    driver_logs = out_dir / "driver-logs"
    profile_root = out_dir / "browser-profiles"
    manifest = {
        "ok": False,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "route": args.route,
        "project": args.project,
        "view": args.view,
        "gatewayAlias": args.gateway_alias,
        "browserUrlAlias": args.browser_url_alias,
        "coldRepetitions": args.cold_repetitions,
        "warmRepetitions": args.warm_repetitions,
        "durationSec": args.duration_sec,
        "intervalSec": args.interval_sec,
        "changedResources": [],
        "missingEvidence": [],
        "notes": [
            "Read-only cold/warm route-load profile run.",
            "Raw browser URLs, tokens, endpoints, node_modules paths, and Chromium profile paths are redacted from orchestrator command evidence.",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)

    for index in range(1, args.cold_repetitions + 1):
        run_dir = out_dir / f"cold-{index:02d}"
        user_data_dir = profile_root / f"cold-{index:02d}"
        cmd = [sys.executable, str(COLLECT_SCRIPT)]
        add_profile_args(cmd, args, f"{args.run_id}-cold-{index:02d}", run_dir, "cold", user_data_dir)
        result = run_command(cmd, driver_logs, f"cold-{index:02d}", args.command_timeout_sec)
        rows.append(summarize_profile(run_dir, result, "cold", index, True))
        if args.pause_sec > 0:
            import time

            time.sleep(args.pause_sec)

    warm_profile_dir = profile_root / "warm-shared"
    warm_prime_dir = out_dir / "warm-prime"
    prime_cmd = [sys.executable, str(COLLECT_SCRIPT)]
    add_profile_args(prime_cmd, args, f"{args.run_id}-warm-prime", warm_prime_dir, "warm-prime", warm_profile_dir)
    prime_result = run_command(prime_cmd, driver_logs, "warm-prime", args.command_timeout_sec)
    rows.append(summarize_profile(warm_prime_dir, prime_result, "warm-prime", 0, False))

    for index in range(1, args.warm_repetitions + 1):
        run_dir = out_dir / f"warm-{index:02d}"
        cmd = [sys.executable, str(COLLECT_SCRIPT)]
        add_profile_args(cmd, args, f"{args.run_id}-warm-{index:02d}", run_dir, "warm", warm_profile_dir)
        result = run_command(cmd, driver_logs, f"warm-{index:02d}", args.command_timeout_sec)
        rows.append(summarize_profile(run_dir, result, "warm", index, True))
        if args.pause_sec > 0:
            import time

            time.sleep(args.pause_sec)

    counted_rows = [row for row in rows if row.get("counted")]
    prime_rows = [row for row in rows if row.get("phase") == "warm-prime"]
    warm_prime_ok = bool(
        prime_rows
        and prime_rows[0].get("commandOk")
        and prime_rows[0].get("profileOk")
        and prime_rows[0].get("browserReady")
    )
    aggregates = aggregate(rows)
    ok = bool(counted_rows) and warm_prime_ok and all(row.get("commandOk") and row.get("profileOk") and row.get("browserReady") for row in counted_rows)
    notes = list(manifest["notes"])
    notes.append("Warm prime is saved but excluded from counted cold/warm aggregate statistics.")
    summary = {
        "ok": ok,
        "warmPrimeOk": warm_prime_ok,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "rows": rows,
        "aggregates": aggregates,
        "notes": notes,
    }
    manifest["ok"] = ok
    manifest["finishedAt"] = utc_now()
    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "summary.json", summary)
    write_report(out_dir, manifest, rows, summary)
    print(json.dumps({"ok": ok, "summaryPath": str(out_dir / "summary.json")}, indent=2, sort_keys=True))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
