#!/usr/bin/env python3
"""Compare two Perspective performance profile evidence bundles.

The comparison is read-only. It summarizes target-minus-control deltas from
bundles produced by collect_profile.py. A single comparison is observational;
use repeated paired runs before making a causal claim.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def read_ndjson(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
        if math.isnan(parsed) or math.isinf(parsed):
            return None
        return parsed
    return None


def value_at(data: Dict[str, Any], path: Iterable[str]) -> Optional[float]:
    current: Any = data
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return to_float(current)


def summarize_values(values: Iterable[Any]) -> Dict[str, Any]:
    nums = [item for item in (to_float(value) for value in values) if item is not None]
    if not nums:
        return {"count": 0}
    return {
        "count": len(nums),
        "min": min(nums),
        "max": max(nums),
        "avg": mean(nums),
        "first": nums[0],
        "last": nums[-1],
        "delta": nums[-1] - nums[0],
    }


def delta(control: Optional[float], target: Optional[float]) -> Dict[str, Any]:
    if control is None or target is None:
        return {"control": control, "target": target, "delta": None, "pctDelta": None}
    pct = None if control == 0 else ((target - control) / abs(control)) * 100.0
    return {"control": control, "target": target, "delta": target - control, "pctDelta": pct}


def flatten_static_summary(static_profile: Dict[str, Any]) -> Dict[str, Any]:
    summary = static_profile.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def summarize_browser(browser: Dict[str, Any], network: Dict[str, Any]) -> Dict[str, Any]:
    navigation = browser.get("navigation", {}) if isinstance(browser.get("navigation"), dict) else {}
    heap = browser.get("heap", {}) if isinstance(browser.get("heap"), dict) else {}
    lcp = browser.get("largestContentfulPaint", {}) if isinstance(browser.get("largestContentfulPaint"), dict) else {}
    return {
        "ready": bool(browser.get("ready")),
        "elapsedBrowserMs": to_float(browser.get("elapsedBrowserMs")),
        "domContentLoadedMs": to_float(navigation.get("domContentLoadedEventEnd")),
        "loadEventEndMs": to_float(navigation.get("loadEventEnd")),
        "largestContentfulPaintMs": to_float(lcp.get("startTime")),
        "longTaskCount": to_float(browser.get("longTaskCount")),
        "longTaskTotalMs": to_float(browser.get("longTaskTotalMs")),
        "domNodeCount": to_float(browser.get("domNodeCount")),
        "usedJSHeapBytes": to_float(heap.get("usedJSHeapSize")),
        "resourceCount": to_float(browser.get("resourceCount")),
        "resourceTransferSize": to_float(browser.get("resourceTransferSize")),
        "networkRequestCount": to_float(network.get("requestCount")),
        "knownContentLengthBytes": to_float(network.get("knownContentLengthBytes")),
        "webSocketCount": to_float(network.get("webSocketCount")),
        "webSocketFramesSent": to_float(network.get("webSocketFramesSent")),
        "webSocketFramesReceived": to_float(network.get("webSocketFramesReceived")),
        "webSocketBytesSent": to_float(network.get("webSocketBytesSent")),
        "webSocketBytesReceived": to_float(network.get("webSocketBytesReceived")),
    }


def summarize_gateway(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    perf_rows = [
        item.get("gatewayPerformanceSnapshot", {})
        for item in rows
        if isinstance(item.get("gatewayPerformanceSnapshot"), dict)
    ]
    metric_rows = [
        item.get("metricsSnapshot", {})
        for item in rows
        if isinstance(item.get("metricsSnapshot"), dict)
    ]
    summary = {
        "sampleCount": len(rows),
        "processCpuLoad": summarize_values(value_at(row, ["cpu", "processCpuLoad"]) for row in perf_rows),
        "systemCpuLoad": summarize_values(value_at(row, ["cpu", "systemCpuLoad"]) for row in perf_rows),
        "heapUsedBytes": summarize_values(value_at(row, ["heap", "usedBytes"]) for row in perf_rows),
        "nonHeapUsedBytes": summarize_values(value_at(row, ["nonHeap", "usedBytes"]) for row in perf_rows),
        "threadTotal": summarize_values(value_at(row, ["threads", "total"]) for row in perf_rows),
        "threadRunning": summarize_values(value_at(row, ["threads", "running"]) for row in perf_rows),
        "threadWaiting": summarize_values(value_at(row, ["threads", "waiting"]) for row in perf_rows),
        "metricReturnedCount": summarize_values(row.get("returnedCount") for row in metric_rows),
        "metricErrorCount": 0,
        "globalMetrics": {},
    }
    metric_errors = 0
    global_metrics: Dict[str, Dict[str, List[Any]]] = {}
    for row in metric_rows:
        metrics = row.get("metrics", [])
        if not isinstance(metrics, list):
            continue
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            if not metric.get("ok", False):
                metric_errors += 1
            if metric.get("redacted"):
                continue
            name = str(metric.get("name", "") or metric.get("token", "") or "")
            if not name:
                continue
            bucket = global_metrics.setdefault(name, {"value": [], "count": [], "mean": [], "p95": []})
            for key in bucket:
                bucket[key].append(metric.get(key))
    summary["metricErrorCount"] = metric_errors
    summary["globalMetrics"] = {
        name: {key: summarize_values(values) for key, values in values_by_key.items()}
        for name, values_by_key in sorted(global_metrics.items())
    }
    return summary


def summarize_sessions(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    returned_counts: List[Any] = []
    browser_sessions: List[int] = []
    active_pages: List[int] = []
    recent_bytes: List[float] = []
    total_bytes: List[float] = []
    for row in rows:
        query = row.get("perspectiveSessionsQuery", {})
        if not isinstance(query, dict):
            continue
        returned_counts.append(query.get("returnedCount"))
        sessions = query.get("sessions", [])
        if not isinstance(sessions, list):
            continue
        browser_count = 0
        page_count = 0
        for session in sessions:
            if not isinstance(session, dict):
                continue
            if str(session.get("sessionScope", "")).lower() == "browser":
                browser_count += 1
                page_count += int(to_float(session.get("activePages")) or 0)
                recent = to_float(session.get("recentBytesSent"))
                total = to_float(session.get("totalBytesSent"))
                if recent is not None:
                    recent_bytes.append(recent)
                if total is not None:
                    total_bytes.append(total)
        browser_sessions.append(browser_count)
        active_pages.append(page_count)
    return {
        "sampleCount": len(rows),
        "returnedCount": summarize_values(returned_counts),
        "browserSessionCount": summarize_values(browser_sessions),
        "browserActivePages": summarize_values(active_pages),
        "browserRecentBytesSent": summarize_values(recent_bytes),
        "browserTotalBytesSent": summarize_values(total_bytes),
    }


def load_bundle(path: Path) -> Dict[str, Any]:
    return {
        "path": str(path),
        "manifest": read_json(path / "manifest.json"),
        "summary": read_json(path / "summary.json"),
        "static": read_json(path / "static-profile.json"),
        "browser": summarize_browser(read_json(path / "browser-summary.json"), read_json(path / "network-summary.json")),
        "gateway": summarize_gateway(read_ndjson(path / "gateway-samples.ndjson")),
        "sessions": summarize_sessions(read_ndjson(path / "perspective-session-samples.ndjson")),
        "logs": read_json(path / "logs.json"),
    }


def compare_dict(control: Dict[str, Any], target: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key in keys:
        out[key] = delta(to_float(control.get(key)), to_float(target.get(key)))
    return out


def avg_delta(control: Dict[str, Any], target: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key in keys:
        out[key] = delta(
            to_float((control.get(key, {}) if isinstance(control.get(key), dict) else {}).get("avg")),
            to_float((target.get(key, {}) if isinstance(target.get(key), dict) else {}).get("avg")),
        )
    return out


def compare_global_metrics(control: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
    control_metrics = control.get("globalMetrics", {}) if isinstance(control.get("globalMetrics"), dict) else {}
    target_metrics = target.get("globalMetrics", {}) if isinstance(target.get("globalMetrics"), dict) else {}
    names = sorted(set(control_metrics) | set(target_metrics))
    out: Dict[str, Any] = {}
    for name in names:
        control_item = control_metrics.get(name, {})
        target_item = target_metrics.get(name, {})
        if not isinstance(control_item, dict) or not isinstance(target_item, dict):
            continue
        out[name] = {
            "valueAvg": delta(
                to_float((control_item.get("value", {}) if isinstance(control_item.get("value"), dict) else {}).get("avg")),
                to_float((target_item.get("value", {}) if isinstance(target_item.get("value"), dict) else {}).get("avg")),
            ),
            "countDeltaOverWindow": delta(
                to_float((control_item.get("count", {}) if isinstance(control_item.get("count"), dict) else {}).get("delta")),
                to_float((target_item.get("count", {}) if isinstance(target_item.get("count"), dict) else {}).get("delta")),
            ),
            "meanAvg": delta(
                to_float((control_item.get("mean", {}) if isinstance(control_item.get("mean"), dict) else {}).get("avg")),
                to_float((target_item.get("mean", {}) if isinstance(target_item.get("mean"), dict) else {}).get("avg")),
            ),
            "p95Avg": delta(
                to_float((control_item.get("p95", {}) if isinstance(control_item.get("p95"), dict) else {}).get("avg")),
                to_float((target_item.get("p95", {}) if isinstance(target_item.get("p95"), dict) else {}).get("avg")),
            ),
        }
    return out


def make_interpretation(comparison: Dict[str, Any]) -> List[str]:
    notes = [
        "This is a target-minus-control observation, not a causal A/B result.",
        "Use repeated paired runs with identical browser/cache/session conditions before claiming improvement or regression.",
    ]
    browser = comparison.get("browserDeltas", {})
    gateway = comparison.get("gatewayDeltas", {})
    long_tasks = (browser.get("longTaskTotalMs", {}) if isinstance(browser.get("longTaskTotalMs"), dict) else {}).get("delta")
    dom_nodes = (browser.get("domNodeCount", {}) if isinstance(browser.get("domNodeCount"), dict) else {}).get("delta")
    cpu = (gateway.get("processCpuLoad", {}) if isinstance(gateway.get("processCpuLoad"), dict) else {}).get("delta")
    if to_float(long_tasks) and to_float(long_tasks) > 0:
        notes.append("Target browser long-task time is higher than control; inspect browser/component rendering before blaming Gateway work.")
    if to_float(dom_nodes) and to_float(dom_nodes) > 0:
        notes.append("Target DOM node count is higher than control; pair this with long tasks and component counts when classifying browser cost.")
    if to_float(cpu) and to_float(cpu) > 0:
        notes.append("Target average Gateway process CPU is higher than control during the sample window; correlate with binding/script/fetch counters.")
    return notes


def make_report(path: Path, comparison: Dict[str, Any]) -> None:
    control = comparison["control"]
    target = comparison["target"]
    lines = [
        "# Perspective Profile Comparison",
        "",
        f"Generated: `{comparison['createdAt']}`",
        f"Control: `{control.get('route', '')}` / `{control.get('view', '')}`",
        f"Target: `{target.get('route', '')}` / `{target.get('view', '')}`",
        "",
        "Evidence grade: `Observed`. This comparison is not causal without repeated paired runs.",
        "",
        "## Key Deltas",
        "",
        "| Metric | Control | Target | Delta |",
        "|---|---:|---:|---:|",
    ]
    interesting = {
        "componentCount": comparison["staticDeltas"].get("componentCount", {}),
        "bindingCount": comparison["staticDeltas"].get("bindingCount", {}),
        "viewJsonBytes": comparison["staticDeltas"].get("viewJsonBytes", {}),
        "LCP ms": comparison["browserDeltas"].get("largestContentfulPaintMs", {}),
        "longTaskTotalMs": comparison["browserDeltas"].get("longTaskTotalMs", {}),
        "DOM nodes": comparison["browserDeltas"].get("domNodeCount", {}),
        "resourceTransferSize": comparison["browserDeltas"].get("resourceTransferSize", {}),
        "Gateway CPU avg": comparison["gatewayDeltas"].get("processCpuLoad", {}),
        "heap used avg bytes": comparison["gatewayDeltas"].get("heapUsedBytes", {}),
        "browser sessions avg": comparison["sessionDeltas"].get("browserSessionCount", {}),
    }
    for name, item in interesting.items():
        lines.append(
            "| {name} | {control} | {target} | {delta_value} |".format(
                name=name,
                control=format_number(item.get("control")),
                target=format_number(item.get("target")),
                delta_value=format_number(item.get("delta")),
            )
        )
    lines.extend(["", "## Interpretation", ""])
    for note in comparison.get("interpretation", []):
        lines.append(f"- {note}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def format_number(value: Any) -> str:
    num = to_float(value)
    if num is None:
        return ""
    if abs(num) >= 1000:
        return f"{num:,.0f}"
    return f"{num:.3f}".rstrip("0").rstrip(".")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare two collect_profile.py evidence bundles.")
    parser.add_argument("--control-dir", required=True, help="Control evidence bundle directory.")
    parser.add_argument("--target-dir", required=True, help="Target evidence bundle directory.")
    parser.add_argument("--out-dir", help="Output directory. Defaults to the target bundle directory.")
    parser.add_argument("--label", default="control-versus-target", help="Comparison label.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    control_dir = Path(args.control_dir)
    target_dir = Path(args.target_dir)
    out_dir = Path(args.out_dir) if args.out_dir else target_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    control_bundle = load_bundle(control_dir)
    target_bundle = load_bundle(target_dir)
    control_manifest = control_bundle["manifest"]
    target_manifest = target_bundle["manifest"]
    static_keys = [
        "componentCount",
        "bindingCount",
        "maxComponentDepth",
        "eventBlockCount",
        "scriptCount",
        "scriptChars",
        "transformCount",
        "embeddedViewCount",
        "flexRepeaterCount",
        "tableLikeCount",
        "chartLikeCount",
        "viewJsonBytes",
    ]
    browser_keys = [
        "elapsedBrowserMs",
        "domContentLoadedMs",
        "loadEventEndMs",
        "largestContentfulPaintMs",
        "longTaskCount",
        "longTaskTotalMs",
        "domNodeCount",
        "usedJSHeapBytes",
        "resourceCount",
        "resourceTransferSize",
        "networkRequestCount",
        "knownContentLengthBytes",
        "webSocketCount",
        "webSocketFramesSent",
        "webSocketFramesReceived",
        "webSocketBytesSent",
        "webSocketBytesReceived",
    ]
    gateway_keys = [
        "processCpuLoad",
        "systemCpuLoad",
        "heapUsedBytes",
        "nonHeapUsedBytes",
        "threadTotal",
        "threadRunning",
        "threadWaiting",
        "metricReturnedCount",
    ]
    session_keys = [
        "returnedCount",
        "browserSessionCount",
        "browserActivePages",
        "browserRecentBytesSent",
        "browserTotalBytesSent",
    ]
    comparison: Dict[str, Any] = {
        "ok": True,
        "label": args.label,
        "createdAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidenceGrade": "Observed",
        "control": {
            "path": str(control_dir),
            "runId": control_manifest.get("runId"),
            "project": control_manifest.get("project"),
            "route": control_manifest.get("route"),
            "view": control_manifest.get("view"),
            "sampleCount": control_manifest.get("sampleCount"),
            "runnerVersion": control_manifest.get("runnerVersion"),
            "stackVersion": control_manifest.get("stackVersion"),
        },
        "target": {
            "path": str(target_dir),
            "runId": target_manifest.get("runId"),
            "project": target_manifest.get("project"),
            "route": target_manifest.get("route"),
            "view": target_manifest.get("view"),
            "sampleCount": target_manifest.get("sampleCount"),
            "runnerVersion": target_manifest.get("runnerVersion"),
            "stackVersion": target_manifest.get("stackVersion"),
        },
        "staticDeltas": compare_dict(flatten_static_summary(control_bundle["static"]), flatten_static_summary(target_bundle["static"]), static_keys),
        "browserDeltas": compare_dict(control_bundle["browser"], target_bundle["browser"], browser_keys),
        "gatewayDeltas": avg_delta(control_bundle["gateway"], target_bundle["gateway"], gateway_keys),
        "sessionDeltas": avg_delta(control_bundle["sessions"], target_bundle["sessions"], session_keys),
        "globalMetricDeltas": compare_global_metrics(control_bundle["gateway"], target_bundle["gateway"]),
        "notes": [
            "Target-minus-control comparison only. Do not treat as remediation proof.",
            "Missing values mean the underlying bundle did not contain that evidence.",
        ],
    }
    comparison["interpretation"] = make_interpretation(comparison)
    (out_dir / "comparison.json").write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    make_report(out_dir / "comparison.md", comparison)
    print(json.dumps({"ok": True, "comparison": str(out_dir / "comparison.json"), "report": str(out_dir / "comparison.md")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
