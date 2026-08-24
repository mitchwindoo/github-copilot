#!/usr/bin/env python3
"""Classify profiler evidence into cautious incident hypotheses.

This post-processor reads an existing live profile summary and labels the
strongest evidence families. It does not mutate a Gateway and it does not turn a
single fixture into a remediation rule.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


MB = 1024 * 1024


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_number(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return ""
    if abs(number) >= 10:
        return f"{number:.0f}"
    return f"{number:.3f}".rstrip("0").rstrip(".")


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n")


def nested(data: Dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def first_number(*values: Any) -> Optional[float]:
    for value in values:
        number = to_float(value)
        if number is not None:
            return number
    return None


def extract_variants(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    variants = summary.get("variants")
    if isinstance(variants, list) and variants:
        return [row for row in variants if isinstance(row, dict)]
    return [summary]


def variant_name(row: Dict[str, Any], index: int) -> str:
    for key in ("variant", "name", "route", "viewPath"):
        value = row.get(key)
        if value:
            return str(value)
    return f"variant-{index + 1}"


def metric_summary_value(row: Dict[str, Any], key: str) -> Optional[float]:
    value = nested(row, "metricSummary", key)
    if value is not None:
        return to_float(value)
    profile_key = {
        "primaryDatabaseQueryDuringDelta": "databaseQueryDeltaDuring",
        "primaryPerspectiveFetchDuringDelta": "fetchDeltaDuring",
        "primaryPerspectivePropertyChangesDuringDelta": "propertyChangeDeltaDuring",
    }.get(key)
    if profile_key:
        return to_float(nested(row, "profileSummary", profile_key))
    return None


def extract_metric_row(row: Dict[str, Any], index: int) -> Dict[str, Any]:
    browser = row.get("browser") if isinstance(row.get("browser"), dict) else {}
    network = row.get("network") if isinstance(row.get("network"), dict) else {}
    gateway = row.get("gateway") if isinstance(row.get("gateway"), dict) else {}
    static = row.get("static") if isinstance(row.get("static"), dict) else {}
    rollup = row.get("metricRollup") if isinstance(row.get("metricRollup"), dict) else {}
    profile = row.get("profileSummary") if isinstance(row.get("profileSummary"), dict) else {}

    return {
        "name": variant_name(row, index),
        "ok": row.get("ok"),
        "browserDomNodes": first_number(browser.get("domNodeCount"), profile.get("domNodeCountAvg")),
        "browserHeapBytes": first_number(browser.get("usedJSHeapBytes"), profile.get("browserHeapUsedBytesAvg")),
        "browserLongTaskTotalMs": first_number(browser.get("longTaskTotalMs"), profile.get("longTaskTotalMsAvg")),
        "browserElapsedMs": first_number(browser.get("elapsedBrowserMs"), profile.get("elapsedBrowserMsAvg")),
        "resourceTransferBytes": first_number(network.get("resourceTransferSize"), browser.get("resourceTransferSize")),
        "webSocketBytesReceived": first_number(network.get("webSocketBytesReceived"), profile.get("webSocketBytesReceivedAvg")),
        "webSocketBytesSent": first_number(network.get("webSocketBytesSent"), profile.get("webSocketBytesSentAvg")),
        "gatewayCpuMedian": first_number(gateway.get("processCpuLoadMedian"), profile.get("duringMinusPreProcessCpuLoadAvg")),
        "gatewayHeapMedianBytes": first_number(gateway.get("heapUsedBytesMedian"), profile.get("duringMinusPreHeapUsedBytesAvg")),
        "staticBindings": to_float(static.get("bindingCount")),
        "staticViewJsonBytes": to_float(static.get("viewJsonBytes")),
        "staticPayloadBytes": first_number(static.get("tableDataBytes"), static.get("parameterPayloadBytes"), static.get("chartPayloadBytes"), static.get("xyPayloadBytes")),
        "databaseQueryDelta": metric_summary_value(row, "primaryDatabaseQueryDuringDelta"),
        "perspectiveFetchDelta": metric_summary_value(row, "primaryPerspectiveFetchDuringDelta"),
        "perspectivePropertyChangeDelta": metric_summary_value(row, "primaryPerspectivePropertyChangesDuringDelta"),
        "propertyChangesDeltaMax": to_float(rollup.get("propertychangesDeltaMax")),
        "scriptsDeltaMax": to_float(rollup.get("scriptsDeltaMax")),
        "queueTasksRateMax": to_float(rollup.get("queuetasksRateMax")),
        "messagesSentDeltaMax": to_float(rollup.get("messagessentDeltaMax")),
    }


def numeric_values(rows: Sequence[Dict[str, Any]], key: str) -> List[float]:
    values: List[float] = []
    for row in rows:
        number = to_float(row.get(key))
        if number is not None:
            values.append(number)
    return values


def span(rows: Sequence[Dict[str, Any]], key: str) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str], Optional[str]]:
    values = [(to_float(row.get(key)), row.get("name")) for row in rows]
    pairs = [(value, str(name)) for value, name in values if value is not None]
    if not pairs:
        return None, None, None, None, None
    low_value, low_name = min(pairs, key=lambda item: item[0])
    high_value, high_name = max(pairs, key=lambda item: item[0])
    return low_value, high_value, high_value - low_value, low_name, high_name


def evidence_line(rows: Sequence[Dict[str, Any]], key: str, label: str, unit: str = "") -> Optional[str]:
    low, high, delta, low_name, high_name = span(rows, key)
    if low is None or high is None or delta is None:
        return None
    suffix = f" {unit}" if unit else ""
    return f"{label}: {format_number(low)}{suffix} on `{low_name}` to {format_number(high)}{suffix} on `{high_name}` (delta {format_number(delta)}{suffix})"


def add_classification(classifications: List[Dict[str, Any]], label: str, confidence: str, evidence: Iterable[Optional[str]], caveats: Iterable[str]) -> None:
    evidence_rows = [item for item in evidence if item]
    if not evidence_rows:
        return
    classifications.append(
        {
            "label": label,
            "confidence": confidence,
            "evidence": evidence_rows,
            "caveats": list(caveats),
        }
    )


def classify(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    classifications: List[Dict[str, Any]] = []

    dom_low, dom_high, dom_delta, _, _ = span(rows, "browserDomNodes")
    heap_low, heap_high, heap_delta, _, _ = span(rows, "browserHeapBytes")
    long_low, long_high, long_delta, _, _ = span(rows, "browserLongTaskTotalMs")
    transfer_low, transfer_high, transfer_delta, _, _ = span(rows, "resourceTransferBytes")
    ws_rx_low, ws_rx_high, ws_rx_delta, _, _ = span(rows, "webSocketBytesReceived")
    cpu_values = numeric_values(rows, "gatewayCpuMedian")
    gateway_cpu_max = max(cpu_values) if cpu_values else None
    static_binding_values = numeric_values(rows, "staticBindings")
    max_static_bindings = max(static_binding_values) if static_binding_values else None

    browser_signals = []
    if dom_delta is not None and dom_delta >= 500:
        browser_signals.append(evidence_line(rows, "browserDomNodes", "DOM nodes"))
    if heap_delta is not None and heap_delta >= 10 * MB:
        browser_signals.append(evidence_line(rows, "browserHeapBytes", "Browser heap bytes"))
    if long_delta is not None and long_delta >= 100:
        browser_signals.append(evidence_line(rows, "browserLongTaskTotalMs", "Long-task total", "ms"))
    if transfer_delta is not None and transfer_delta >= 200_000:
        browser_signals.append(evidence_line(rows, "resourceTransferBytes", "Resource transfer bytes"))

    if browser_signals:
        confidence = "medium"
        caveats = [
            "This is a browser/payload pressure hypothesis, not a root-cause proof by itself.",
            "Confirm with repeated identical scenarios and keep Gateway/session counters beside browser evidence.",
        ]
        if gateway_cpu_max is not None and gateway_cpu_max <= 0.05:
            caveats.append("Gateway CPU stayed low in the summarized rows, which supports separating browser work from Gateway CPU pressure.")
            confidence = "medium-high"
        if max_static_bindings == 0:
            caveats.append("The summarized rows report zero static bindings, which supports a static client-rendering or payload fixture interpretation.")
        add_classification(classifications, "browser-rendering-pressure", confidence, browser_signals, caveats)

    network_signals = []
    if transfer_delta is not None and transfer_delta >= 200_000:
        network_signals.append(evidence_line(rows, "resourceTransferBytes", "Resource transfer bytes"))
    if ws_rx_delta is not None and ws_rx_delta >= 200_000:
        network_signals.append(evidence_line(rows, "webSocketBytesReceived", "WebSocket received bytes"))
    if network_signals:
        add_classification(
            classifications,
            "network-or-payload-pressure",
            "medium",
            network_signals,
            [
                "Payload evidence can be caused by view JSON, component data, websocket state, or static resources; inspect the fixture/source before naming the payload source.",
            ],
        )

    queue_values = numeric_values(rows, "queueTasksRateMax")
    script_values = numeric_values(rows, "scriptsDeltaMax")
    property_values = numeric_values(rows, "propertyChangesDeltaMax")
    queue_max = max(queue_values) if queue_values else None
    script_max = max(script_values) if script_values else None
    property_max = max(property_values) if property_values else None
    queue_signals = []
    if queue_max is not None and queue_max >= 50:
        queue_signals.append(evidence_line(rows, "queueTasksRateMax", "Queue-task rate max"))
    if script_max is not None and script_max >= 1000:
        queue_signals.append(evidence_line(rows, "scriptsDeltaMax", "Script delta max"))
    if property_max is not None and property_max >= 1000:
        queue_signals.append(evidence_line(rows, "propertyChangesDeltaMax", "Property-change delta max"))
    if queue_signals:
        caveats = [
            "Treat this as script/property/queue pressure evidence; use a bounded thread dump only during an active freeze, backlog, or CPU spike.",
            "A bounded fixture can prove detection mechanics but not a customer loop until a customer or Designer-seeded event shape reproduces it.",
        ]
        if dom_delta is not None and dom_delta < 100:
            caveats.append("Browser DOM stayed nearly fixed across summarized rows, which helps separate queue/script pressure from visible component growth.")
        add_classification(classifications, "gateway-script-queue-pressure", "medium-high", queue_signals, caveats)

    db_values = numeric_values(rows, "databaseQueryDelta")
    db_max = max(db_values) if db_values else None
    db_low, db_high, db_delta, _, _ = span(rows, "databaseQueryDelta")
    if db_max is not None and (db_max >= 50 or (db_delta is not None and db_delta >= 20)):
        add_classification(
            classifications,
            "database-query-activity",
            "medium",
            [evidence_line(rows, "databaseQueryDelta", "Database query during delta")],
            [
                "This labels query activity, not database latency. Pair it with query timers, fetch duration, or a controlled delay fixture before saying data-source-only delay.",
                "Parameterized or distinct-path query shapes must be recorded separately from Cache & Share settings.",
            ],
        )

    if not classifications:
        add_classification(
            classifications,
            "inconclusive-or-baseline",
            "low",
            ["No configured classifier threshold was crossed in the summarized rows."],
            ["Review raw samples and target-specific context before ruling out an incident class."],
        )
    return classifications


def write_report(path: Path, result: Dict[str, Any]) -> None:
    lines = [
        "# Incident Evidence Classification",
        "",
        f"Source: `{result.get('sourceName')}`",
        f"Run ID: `{result.get('runId')}`",
        "",
        "## Classifications",
        "",
    ]
    for item in result.get("classifications", []):
        lines.append(f"- `{item.get('label')}` ({item.get('confidence')})")
        for evidence in item.get("evidence", []):
            lines.append(f"  - {evidence}")
        for caveat in item.get("caveats", []):
            lines.append(f"  - Caveat: {caveat}")
    lines.extend(["", "## Variant Metrics", ""])
    lines.append("| Variant | DOM | Heap MB | Long tasks ms | Transfer bytes | WS received | Gateway CPU | DB queries | Queue rate | Scripts | Property changes |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in result.get("rows", []):
        heap_mb = to_float(row.get("browserHeapBytes"))
        lines.append(
            "| {name} | {dom} | {heap} | {long_task} | {transfer} | {ws_rx} | {cpu} | {db} | {queue} | {scripts} | {props} |".format(
                name=row.get("name"),
                dom=format_number(row.get("browserDomNodes")),
                heap=format_number(None if heap_mb is None else heap_mb / MB),
                long_task=format_number(row.get("browserLongTaskTotalMs")),
                transfer=format_number(row.get("resourceTransferBytes")),
                ws_rx=format_number(row.get("webSocketBytesReceived")),
                cpu=format_number(row.get("gatewayCpuMedian")),
                db=format_number(row.get("databaseQueryDelta")),
                queue=format_number(row.get("queueTasksRateMax")),
                scripts=format_number(row.get("scriptsDeltaMax")),
                props=format_number(row.get("propertyChangesDeltaMax")),
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Classifications are hypotheses for triage, not remediation conclusions.",
            "- Missing metric families stay blank in the table and should be called out before narrowing an incident.",
            "- Use bounded thread dumps only during an active freeze, queue backlog, or CPU spike.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def classify_summary(summary_path: Path, out_dir: Path, label: str, expected: Sequence[str]) -> Dict[str, Any]:
    if summary_path.is_dir():
        summary_path = summary_path / "summary.json"
    summary = read_json(summary_path)
    rows = [extract_metric_row(row, index) for index, row in enumerate(extract_variants(summary))]
    classifications = classify(rows)
    labels = [str(item.get("label")) for item in classifications]
    missing_expected = [item for item in expected if item not in labels]
    result = {
        "ok": not missing_expected,
        "sourcePath": str(summary_path),
        "sourceName": label or summary_path.parent.name,
        "runId": summary.get("runId"),
        "runnerVersion": summary.get("runnerVersion"),
        "stackVersion": summary.get("stackVersion"),
        "variantCount": len(rows),
        "expectedLabels": list(expected),
        "missingExpectedLabels": missing_expected,
        "classifications": classifications,
        "rows": rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "classification-summary.json", result)
    write_report(out_dir / "classification-report.md", result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, help="Path to a summary.json file or a bundle directory containing summary.json.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--label", default="")
    parser.add_argument("--expect-label", action="append", default=[], help="Expected classifier label. Repeatable; missing expected labels make the command fail.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = classify_summary(Path(args.summary), Path(args.out_dir), args.label, args.expect_label)
    print(json.dumps({"ok": result["ok"], "labels": [item["label"] for item in result["classifications"]], "summary": str(Path(args.out_dir) / "classification-summary.json")}, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
