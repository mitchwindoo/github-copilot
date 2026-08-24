#!/usr/bin/env python3
"""Verify V-07 no-secondary-regression safety coverage.

This offline checker validates that a remediation evidence summary includes
declared limits and passing evidence for CPU, heap, messages, errors, and
operator latency. It does not call a Gateway or mutate resources.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


CPU_KEYS = ("cpu", "processCpuLoad", "gatewayCpu", "gateway.processCpuLoad")
HEAP_KEYS = ("heap", "heapUsedBytes", "gatewayHeap", "gateway.heapUsedBytes", "nonHeapUsedBytes")
MESSAGE_KEYS = ("messages", "messageCount", "perspectiveMessages", "webSocketFrames", "webSocketFramesSent", "webSocketFramesReceived", "webSocketBytesSent", "webSocketBytesReceived")
ERROR_KEYS = ("errors", "browserConsole", "browserConsoleErrors", "focusedLogs", "logErrors")
OPERATOR_KEYS = ("operatorLatency", "operatorActionLatency", "clickLatency", "interactionLatency")
DUPLICATE_KEYS = ("duplicateMessages", "duplicateWrites", "duplicateProcessWrites", "duplicateBusinessMessages")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def finite_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    return None


def load_safety_coverage(path: Path) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    if path.is_dir():
        for name in ("summary.json", "safety-coverage.json", "v07-safety-report.json"):
            candidate = path / name
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no summary.json or safety coverage report: {path}"]
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001 - report exact parse problem
        return None, [f"failed to load {path}: {type(exc).__name__}: {exc}"]
    if not isinstance(data, dict):
        return None, ["safety coverage report must be a JSON object"]
    coverage = data.get("safetyCoverage", data)
    if not isinstance(coverage, dict):
        return None, ["safetyCoverage must be a JSON object"]
    return coverage, []


def first_dict(row: Dict[str, Any], keys: Sequence[str]) -> Tuple[str, Optional[Dict[str, Any]]]:
    for key in keys:
        value = row.get(key)
        if isinstance(value, dict):
            return key, value
    return "", None


def nested_dict(root: Dict[str, Any], group_keys: Sequence[str], metric_keys: Sequence[str]) -> Tuple[str, Optional[Dict[str, Any]]]:
    for group_key in group_keys:
        group = root.get(group_key)
        if isinstance(group, dict):
            key, row = first_dict(group, metric_keys)
            if row is not None:
                return f"{group_key}.{key}", row
    key, row = first_dict(root, metric_keys)
    return key, row


def metric_limit(row: Dict[str, Any], default_limit: float) -> float:
    for key in ("limitPct", "maxRegressionPct", "maxPctDelta", "thresholdPct"):
        value = finite_number(row.get(key))
        if value is not None:
            return value
    return default_limit


def pct_delta(row: Dict[str, Any]) -> Optional[float]:
    for key in ("medianPctDelta", "p95PctDelta", "pctDelta", "percentDelta", "deltaPct"):
        value = finite_number(row.get(key))
        if value is not None:
            return value
    return None


def count_value(row: Dict[str, Any]) -> Optional[float]:
    for key in ("count", "duplicateCount", "regressionCount", "targetTotal", "delta", "errorCount"):
        value = finite_number(row.get(key))
        if value is not None:
            return value
    return None


def check_lower_is_better_metric(
    errors: List[str],
    warnings: List[str],
    label: str,
    row: Optional[Dict[str, Any]],
    *,
    default_limit: float,
    require_pct: bool = True,
) -> None:
    if row is None:
        errors.append(f"missing {label} safety evidence")
        return
    if row.get("status") in ("missing", "not-covered", "uncovered"):
        errors.append(f"{label} is marked as not covered")
        return
    regression_count = finite_number(row.get("regressionCount"))
    if regression_count is not None and regression_count > 0:
        errors.append(f"{label} regressionCount is {regression_count}")
    delta = pct_delta(row)
    if delta is None:
        if require_pct:
            errors.append(f"{label} is missing percent-delta evidence")
        else:
            warnings.append(f"{label} has no percent-delta evidence")
        return
    limit = metric_limit(row, default_limit)
    if delta > limit:
        errors.append(f"{label} percent delta {delta} exceeds limit {limit}")


def check_count_not_increased(errors: List[str], label: str, row: Optional[Dict[str, Any]], *, limit: float = 0.0) -> None:
    if row is None:
        errors.append(f"missing {label} safety evidence")
        return
    regression_count = finite_number(row.get("regressionCount"))
    if regression_count is not None and regression_count > limit:
        errors.append(f"{label} regressionCount is {regression_count}")
    count = count_value(row)
    if count is not None and count > limit:
        errors.append(f"{label} count {count} exceeds limit {limit}")


def validate_coverage(coverage: Dict[str, Any], default_limit_pct: float = 10.0) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    covered = coverage.get("covered")
    root = covered if isinstance(covered, dict) else coverage

    if coverage.get("status") in ("partial", "missing", "not-covered", "uncovered"):
        errors.append(f"safetyCoverage.status is {coverage.get('status')}; expected complete/pass/no-regression")
    if coverage.get("status") == "regression-detected":
        errors.append("safetyCoverage.status reports regression-detected")
    top_regression_count = finite_number(coverage.get("regressionCount"))
    if top_regression_count is not None and top_regression_count > 0:
        errors.append(f"safetyCoverage.regressionCount is {top_regression_count}")

    cpu_label, cpu = nested_dict(root, ("gatewayMetrics", "gateway", "cpu"), CPU_KEYS)
    heap_label, heap = nested_dict(root, ("gatewayMetrics", "gateway", "heap"), HEAP_KEYS)
    msg_label, messages = nested_dict(root, ("messageMetrics", "messages", "sessionMetrics"), MESSAGE_KEYS)
    err_label, errors_row = nested_dict(root, ("errors", "browserErrors", "logErrors"), ERROR_KEYS)
    op_label, operator = nested_dict(root, ("operatorLatency", "operator", "interactions"), OPERATOR_KEYS)
    dup_label, duplicate = nested_dict(root, ("messageMetrics", "messages", "duplicateChecks"), DUPLICATE_KEYS)

    check_lower_is_better_metric(errors, warnings, cpu_label or "CPU", cpu, default_limit=default_limit_pct)
    check_lower_is_better_metric(errors, warnings, heap_label or "heap", heap, default_limit=default_limit_pct)
    check_lower_is_better_metric(errors, warnings, msg_label or "messages", messages, default_limit=default_limit_pct, require_pct=False)
    check_count_not_increased(errors, err_label or "errors", errors_row, limit=0.0)
    check_count_not_increased(errors, dup_label or "duplicate messages/writes", duplicate, limit=0.0)

    if operator is None:
        errors.append("missing operator latency safety evidence")
    else:
        observations = finite_number(operator.get("observations") or operator.get("count"))
        if observations is not None and observations < 1:
            errors.append("operator latency has zero observations")
        check_lower_is_better_metric(errors, warnings, op_label or "operator latency", operator, default_limit=default_limit_pct)

    if isinstance(coverage.get("uncovered"), list) and coverage.get("uncovered"):
        errors.append("safetyCoverage.uncovered is not empty")

    return {
        "ok": not errors,
        "checkedAt": utc_now(),
        "status": coverage.get("status"),
        "defaultLimitPct": default_limit_pct,
        "dimensions": {
            "cpu": bool(cpu),
            "heap": bool(heap),
            "messages": bool(messages),
            "errors": bool(errors_row),
            "duplicates": bool(duplicate),
            "operatorLatency": bool(operator),
        },
        "errors": errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify V-07 no-secondary-regression safety coverage.")
    parser.add_argument("report", help="summary.json, safety coverage JSON, or bundle directory.")
    parser.add_argument("--out-json", help="Optional path for full verification JSON.")
    parser.add_argument("--default-limit-pct", type=float, default=10.0, help="Default lower-is-better regression limit percent.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    coverage, load_errors = load_safety_coverage(Path(args.report))
    if load_errors:
        result = {"ok": False, "checkedAt": utc_now(), "errors": load_errors, "warnings": []}
    else:
        result = validate_coverage(coverage or {}, default_limit_pct=args.default_limit_pct)
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(json.dumps({"ok": result.get("ok"), "dimensions": result.get("dimensions", {}), "errors": result.get("errors", [])[:8]}, indent=2, sort_keys=True))
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
