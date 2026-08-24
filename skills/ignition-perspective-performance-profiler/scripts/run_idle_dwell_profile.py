#!/usr/bin/env python3
"""Run a read-only Perspective idle dwell/soak profile for R-07."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import collect_profile as cp


SCRIPT_DIR = Path(__file__).resolve().parent


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def read_ndjson(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                rows.append(data)
    return rows


def to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def number_at(row: Dict[str, Any], path: Tuple[str, ...]) -> Optional[float]:
    current: Any = row
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return to_float(current)


def linear_slope_per_minute(values: List[float], interval_sec: float) -> Optional[float]:
    if len(values) < 2:
        return None
    xs = [(index * interval_sec) / 60.0 for index in range(len(values))]
    mean_x = mean(xs)
    mean_y = mean(values)
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denom


def summarize_series(values: List[float], interval_sec: float) -> Dict[str, Any]:
    if not values:
        return {"sampleCount": 0}
    return {
        "sampleCount": len(values),
        "first": values[0],
        "last": values[-1],
        "min": min(values),
        "max": max(values),
        "delta": values[-1] - values[0],
        "slopePerMinute": linear_slope_per_minute(values, interval_sec),
    }


def gateway_trends(rows: List[Dict[str, Any]], interval_sec: float) -> Dict[str, Any]:
    fields = {
        "gatewayHeapUsedBytes": ("gatewayPerformanceSnapshot", "heap", "usedBytes"),
        "gatewayNonHeapUsedBytes": ("gatewayPerformanceSnapshot", "nonHeap", "usedBytes"),
        "gatewayProcessCpuLoad": ("gatewayPerformanceSnapshot", "cpu", "processCpuLoad"),
        "gatewayThreadTotal": ("gatewayPerformanceSnapshot", "threads", "total"),
        "gatewayThreadWaiting": ("gatewayPerformanceSnapshot", "threads", "waiting"),
        "gatewayThreadTimedWaiting": ("gatewayPerformanceSnapshot", "threads", "timedWaiting"),
    }
    trends: Dict[str, Any] = {}
    for name, path in fields.items():
        values = [value for value in (number_at(row, path) for row in rows) if value is not None]
        trends[name] = summarize_series(values, interval_sec)
    return trends


def metric_item_value(item: Dict[str, Any]) -> Optional[float]:
    if item.get("type") == "gauge":
        return to_float(item.get("value"))
    return to_float(item.get("count"))


def add_metric(accumulator: Dict[str, float], key: str, value: Optional[float], mode: str = "sum") -> None:
    if value is None:
        return
    if mode == "max":
        accumulator[key] = max(accumulator.get(key, value), value)
    else:
        accumulator[key] = accumulator.get(key, 0.0) + value


def metric_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    out: List[Dict[str, float]] = []
    exact_map = {
        "perspective.bindings": ("globalBindingsGauge", "sum"),
        "perspective.components": ("globalComponentsGauge", "sum"),
        "perspective.expressions": ("globalExpressionsCount", "sum"),
        "perspective.fetches": ("globalFetchesCount", "sum"),
        "perspective.pages": ("globalPagesGauge", "sum"),
        "perspective.property-changes": ("globalPropertyChangesCount", "sum"),
        "perspective.scripts": ("globalScriptsCount", "sum"),
        "perspective.sessions": ("globalSessionsGauge", "sum"),
        "perspective.views": ("globalViewsGauge", "sum"),
    }
    suffix_map = [
        (".queue-length", "sessionQueueLengthMax", "max"),
        (".queue-tasks", "sessionQueueTasksCount", "sum"),
        (".messages-sent", "sessionMessagesSentCount", "sum"),
        (".messages-received", "sessionMessagesReceivedCount", "sum"),
        (".property-changes", "sessionPropertyChangesCount", "sum"),
        (".scripts", "sessionScriptsCount", "sum"),
        (".fetches", "sessionFetchesCount", "sum"),
        (".expressions", "sessionExpressionsCount", "sum"),
    ]
    for row in rows:
        sample: Dict[str, float] = {}
        snapshot = row.get("metricsSnapshot", {})
        metrics = snapshot.get("metrics", []) if isinstance(snapshot, dict) else []
        for item in metrics if isinstance(metrics, list) else []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))
            value = metric_item_value(item)
            if name in exact_map:
                key, mode = exact_map[name]
                add_metric(sample, key, value, mode)
                continue
            for suffix, key, mode in suffix_map:
                if name.endswith(suffix):
                    add_metric(sample, key, value, mode)
                    break
        out.append(sample)
    return out


def metric_trends(rows: List[Dict[str, Any]], interval_sec: float) -> Dict[str, Any]:
    samples = metric_rows(rows)
    keys = sorted({key for sample in samples for key in sample})
    trends: Dict[str, Any] = {}
    for key in keys:
        values = [sample[key] for sample in samples if key in sample]
        trends[key] = summarize_series(values, interval_sec)
    return trends


def session_counts(row: Dict[str, Any]) -> Dict[str, float]:
    query = row.get("perspectiveSessionsQuery", {})
    result = {
        "sessionReturnedCount": 0.0,
        "browserSessionCount": 0.0,
        "browserPageCount": 0.0,
        "browserRecentBytesSent": 0.0,
        "browserTotalBytesSent": 0.0,
    }
    if not isinstance(query, dict):
        return result
    returned = to_float(query.get("returnedCount"))
    if returned is not None:
        result["sessionReturnedCount"] = returned
    sessions = query.get("sessions", [])
    for session in sessions if isinstance(sessions, list) else []:
        if not isinstance(session, dict):
            continue
        if str(session.get("sessionScope", "")).lower() != "browser":
            continue
        result["browserSessionCount"] += 1
        result["browserPageCount"] += to_float(session.get("activePages")) or 0.0
        result["browserRecentBytesSent"] += to_float(session.get("recentBytesSent")) or 0.0
        result["browserTotalBytesSent"] += to_float(session.get("totalBytesSent")) or 0.0
    return result


def session_trends(rows: List[Dict[str, Any]], interval_sec: float) -> Dict[str, Any]:
    samples = [session_counts(row) for row in rows]
    keys = sorted({key for sample in samples for key in sample})
    return {key: summarize_series([sample[key] for sample in samples], interval_sec) for key in keys}


def browser_timeline_trends(browser_summary: Dict[str, Any]) -> Dict[str, Any]:
    samples = browser_summary.get("timelineSamples", [])
    if not isinstance(samples, list) or not samples:
        return {
            "timelineSampleCount": 0,
            "timelineAvailable": False,
            "finalHeapUsedBytes": ((browser_summary.get("heap") or {}).get("usedJSHeapSize") if isinstance(browser_summary.get("heap"), dict) else None),
            "finalDomNodeCount": browser_summary.get("domNodeCount"),
            "finalLongTaskCount": browser_summary.get("longTaskCount"),
            "finalLongTaskTotalMs": browser_summary.get("longTaskTotalMs"),
        }
    first_time = to_float(samples[0].get("performanceNowMs")) or 0.0
    last_time = to_float(samples[-1].get("performanceNowMs")) or first_time
    interval_sec = max((last_time - first_time) / max(len(samples) - 1, 1) / 1000.0, 0.001)
    fields = {
        "browserHeapUsedBytes": ("heap", "usedJSHeapSize"),
        "browserDomNodeCount": ("domNodeCount",),
        "browserLongTaskTotalMs": ("longTaskTotalMs",),
        "browserResourceTransferBytes": ("resourceTransferSize",),
    }
    trends: Dict[str, Any] = {
        "timelineSampleCount": len(samples),
        "timelineAvailable": True,
    }
    for key, path in fields.items():
        values = [value for value in (number_at(sample, path) for sample in samples if isinstance(sample, dict)) if value is not None]
        trends[key] = summarize_series(values, interval_sec)
    return trends


def browser_url_from_endpoint(endpoint: str, project: str, route: str) -> str:
    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        return ""
    normalized_route = route if route.startswith("/") else f"/{route}"
    return f"{parsed.scheme}://{parsed.netloc}/data/perspective/client/{project}{normalized_route}"


def redact_command(command: List[str], secrets: Iterable[str]) -> List[str]:
    secret_set = {secret for secret in secrets if secret}
    return ["<redacted>" if item in secret_set else item for item in command]


def run_collect_profile(args: argparse.Namespace, endpoint: str, token: str, project: str, route: str, view: str, browser_url: str, out_dir: Path) -> Dict[str, Any]:
    profile_dir = out_dir / "profile"
    command = [
        sys.executable,
        str(SCRIPT_DIR / "collect_profile.py"),
        "--project",
        project,
        "--route",
        route,
        "--run-id",
        f"{args.run_id}-profile",
        "--out-dir",
        str(profile_dir),
        "--duration-sec",
        str(args.duration_sec),
        "--interval-sec",
        str(args.interval_sec),
        "--max-metrics",
        str(args.max_metrics),
        "--scenario",
        "R-07 idle dwell/soak profile",
        "--gateway-alias",
        args.gateway_alias,
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
        "--browser-timeline-sample-interval-ms",
        str(args.browser_timeline_sample_interval_ms),
        "--browser-node",
        args.browser_node,
    ]
    if view:
        command.extend(["--view", view])
    if args.browser_ready_text:
        command.extend(["--browser-ready-text", args.browser_ready_text])
    if args.browser_node_modules:
        command.extend(["--browser-node-modules", args.browser_node_modules])

    log_dir = out_dir / "command-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "collect-profile.stdout.txt"
    stderr_path = log_dir / "collect-profile.stderr.txt"
    env = os.environ.copy()
    env["IGNITION_LLM_RUNNER_ENDPOINT"] = endpoint
    env["IGNITION_LLM_RUNNER_TOKEN"] = token
    env["IGNITION_TARGET_PROJECT"] = project
    started_at = cp.utc_now()
    with stdout_path.open("w", encoding="utf-8", newline="\n") as stdout, stderr_path.open("w", encoding="utf-8", newline="\n") as stderr:
        proc = subprocess.run(command, cwd=str(SCRIPT_DIR.parent), env=env, stdout=stdout, stderr=stderr, timeout=args.command_timeout_sec)
    return {
        "ok": proc.returncode == 0,
        "exitCode": proc.returncode,
        "startedAt": started_at,
        "finishedAt": cp.utc_now(),
        "command": redact_command(command, [browser_url, args.browser_node_modules]),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
        "profileDir": str(profile_dir),
    }


def collect_flags(summary: Dict[str, Any], args: argparse.Namespace) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    gateway = summary.get("gatewayTrends", {})
    browser = summary.get("browserTimeline", {})
    metrics = summary.get("metricTrends", {})
    sessions = summary.get("sessionTrends", {})

    heap_slope = ((gateway.get("gatewayHeapUsedBytes") or {}).get("slopePerMinute"))
    if isinstance(heap_slope, (int, float)) and heap_slope > args.flag_heap_slope_bytes_per_min:
        flags.append({"name": "gatewayHeapPositiveSlope", "value": heap_slope, "threshold": args.flag_heap_slope_bytes_per_min})
    nonheap_slope = ((gateway.get("gatewayNonHeapUsedBytes") or {}).get("slopePerMinute"))
    if isinstance(nonheap_slope, (int, float)) and nonheap_slope > args.flag_nonheap_slope_bytes_per_min:
        flags.append({"name": "gatewayNonHeapPositiveSlope", "value": nonheap_slope, "threshold": args.flag_nonheap_slope_bytes_per_min})
    browser_heap_slope = ((browser.get("browserHeapUsedBytes") or {}).get("slopePerMinute"))
    if isinstance(browser_heap_slope, (int, float)) and browser_heap_slope > args.flag_browser_heap_slope_bytes_per_min:
        flags.append({"name": "browserHeapPositiveSlope", "value": browser_heap_slope, "threshold": args.flag_browser_heap_slope_bytes_per_min})
    active_pages_delta = ((sessions.get("browserPageCount") or {}).get("delta"))
    if isinstance(active_pages_delta, (int, float)) and active_pages_delta > 0:
        flags.append({"name": "browserPageCountIncreased", "value": active_pages_delta})
    for key in ["globalPropertyChangesCount", "globalScriptsCount", "globalFetchesCount", "sessionMessagesSentCount", "sessionMessagesReceivedCount"]:
        delta = ((metrics.get(key) or {}).get("delta"))
        if isinstance(delta, (int, float)) and delta > args.flag_idle_counter_delta:
            flags.append({"name": f"{key}MovedDuringIdle", "value": delta, "threshold": args.flag_idle_counter_delta})
    return flags


def write_report(path: Path, summary: Dict[str, Any]) -> None:
    flags = summary.get("flags", [])
    lines = [
        "# Idle Dwell / Soak R-07",
        "",
        f"Run ID: `{summary.get('runId')}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion', '<unknown>')}`",
        f"Stack: `{summary.get('stackVersion', '<unknown>')}`",
        f"Route: `{summary.get('route')}`",
        f"Duration seconds: `{summary.get('durationSec')}`",
        f"Interval seconds: `{summary.get('intervalSec')}`",
        f"Gateway samples: `{summary.get('gatewaySampleCount')}`",
        f"Session samples: `{summary.get('sessionSampleCount')}`",
        f"Browser timeline samples: `{(summary.get('browserTimeline') or {}).get('timelineSampleCount')}`",
        f"Browser timeline OK: `{str(summary.get('timelineOk', False)).lower()}`",
        "",
        "## Flags",
    ]
    if flags:
        for flag in flags:
            lines.append(f"- `{flag.get('name')}` value `{flag.get('value')}` threshold `{flag.get('threshold', '')}`")
    else:
        lines.append("- None crossed the configured mechanics thresholds.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is read-only idle dwell mechanics evidence. It does not prove or disprove a production leak by itself.",
            "- JVM heap movement is separated from Perspective session/page retention and browser heap movement.",
            "- Persistent positive slopes across repeated identical intervals are flags for follow-up, not standalone root-cause proof.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a read-only R-07 idle dwell/soak profile.")
    parser.add_argument("--endpoint")
    parser.add_argument("--token")
    parser.add_argument("--project")
    parser.add_argument("--route", required=True)
    parser.add_argument("--view", default="")
    parser.add_argument("--browser-url", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--duration-sec", type=float, default=900.0)
    parser.add_argument("--interval-sec", type=float, default=30.0)
    parser.add_argument("--max-metrics", type=int, default=40)
    parser.add_argument("--min-samples", type=int, default=5)
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-ready-text", default="")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=-1)
    parser.add_argument("--browser-timeline-sample-interval-ms", type=int, default=5000)
    parser.add_argument("--browser-node", default="node")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--gateway-alias", default="configured-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--command-timeout-sec", type=float, default=1200.0)
    parser.add_argument("--flag-heap-slope-bytes-per-min", type=float, default=25_000_000.0)
    parser.add_argument("--flag-nonheap-slope-bytes-per-min", type=float, default=2_000_000.0)
    parser.add_argument("--flag-browser-heap-slope-bytes-per-min", type=float, default=10_000_000.0)
    parser.add_argument("--flag-idle-counter-delta", type=float, default=0.0)
    args = parser.parse_args()

    if args.duration_sec < 0:
        raise SystemExit("--duration-sec must be >= 0")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.browser_wait_after_ready_ms < 0:
        args.browser_wait_after_ready_ms = int((args.duration_sec + args.interval_sec) * 1000)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    endpoint, token, project = cp.resolve_config(args)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", int(args.command_timeout_sec))
    health_record = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health = cp.response(health_record)

    route = args.route
    view = args.view
    if not view:
        routes_record = client.call(f"{args.run_id}-routesList", {"action": "routesList", "requestId": f"{args.run_id}-routesList", "project": project})
        routes = cp.response(routes_record).get("routes", [])
        if isinstance(routes, list):
            route, view = cp.choose_route(routes, route, view)
    browser_url = args.browser_url or browser_url_from_endpoint(endpoint, project, route)
    if not browser_url:
        raise SystemExit("Unable to derive browser URL; pass --browser-url.")

    collect_result = run_collect_profile(args, endpoint, token, project, route, view, browser_url, out_dir)
    profile_dir = Path(collect_result["profileDir"])
    profile_summary = read_json(profile_dir / "summary.json")
    profile_manifest = read_json(profile_dir / "manifest.json")
    gateway_rows = read_ndjson(profile_dir / "gateway-samples.ndjson")
    session_rows = read_ndjson(profile_dir / "perspective-session-samples.ndjson")
    browser_summary = read_json(profile_dir / "browser-summary.json")

    summary: Dict[str, Any] = {
        "ok": False,
        "runId": args.run_id,
        "createdAt": cp.utc_now(),
        "project": project,
        "route": route,
        "view": view,
        "durationSec": args.duration_sec,
        "intervalSec": args.interval_sec,
        "runnerVersion": health.get("runnerVersion") or profile_manifest.get("runnerVersion"),
        "stackVersion": health.get("stackVersion") or profile_manifest.get("stackVersion"),
        "healthOk": cp.ok(health_record),
        "collectProfile": collect_result,
        "profileSummary": profile_summary,
        "gatewaySampleCount": len(gateway_rows),
        "sessionSampleCount": len(session_rows),
        "browserOk": bool(browser_summary.get("ok")),
        "gatewayTrends": gateway_trends(gateway_rows, args.interval_sec),
        "metricTrends": metric_trends(gateway_rows, args.interval_sec),
        "sessionTrends": session_trends(session_rows, args.interval_sec),
        "browserTimeline": browser_timeline_trends(browser_summary),
        "missingEvidence": profile_manifest.get("missingEvidence", []),
        "changedResources": profile_manifest.get("changedResources", []),
        "notes": [
            "Read-only R-07 idle dwell/soak mechanics evidence.",
            "JVM heap slope, Perspective session/page retention, and browser heap timeline are reported separately.",
            "A rising JVM heap alone is not leak proof.",
        ],
    }
    summary["flags"] = collect_flags(summary, args)
    timeline_sample_count = (summary.get("browserTimeline") or {}).get("timelineSampleCount")
    timeline_ok = (
        args.browser_timeline_sample_interval_ms <= 0
        or (isinstance(timeline_sample_count, int) and timeline_sample_count >= 2)
    )
    summary["timelineOk"] = timeline_ok
    summary["ok"] = bool(
        summary["healthOk"]
        and collect_result.get("ok")
        and profile_summary.get("ok") is True
        and summary["browserOk"]
        and timeline_ok
        and len(gateway_rows) >= args.min_samples
        and len(session_rows) >= args.min_samples
    )
    cp.write_json(out_dir / "summary.json", summary)
    write_report(out_dir / "summary.md", summary)
    print(json.dumps({"ok": summary["ok"], "summaryPath": str(out_dir / "summary.json")}, indent=2))
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
