#!/usr/bin/env python3
"""Verify queue-backlog evidence before I-02 claim wording.

This checker is offline and read-only. It accepts one or more queue-backlog
summary JSON files, or directories that contain summary.json. It validates that
I-02 queue-backlog reports prove backlog with actual queue-length rise/recovery
and correlated delay, or explicitly label the evidence as a negative local
result. Queue-task, script, and property-change counters are supporting
activity signals only.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n")


def load_report(path: Path) -> Tuple[Optional[Dict[str, Any]], List[str], Path]:
    if path.is_dir():
        for candidate in (path / "summary.json", path / "queue-backlog-claim-report.json", path / "report.json"):
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no structured queue-backlog report: {path}"], path
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001 - exact parse/load failure belongs in evidence
        return None, [f"failed to load {path}: {type(exc).__name__}: {exc}"], path
    if not isinstance(data, dict):
        return None, [f"report must be a JSON object: {path}"], path
    return data, [], path


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "observed", "proven", "passed", "causal", "accepted"}
    return False


def queue_sample_value(sample: Dict[str, Any]) -> Optional[float]:
    for key in ("max", "value", "sum"):
        value = to_float(sample.get(key))
        if value is not None:
            return value
    return None


def queue_values(queue: Dict[str, Any]) -> List[float]:
    values: List[float] = []
    for sample in as_list(queue.get("samples")):
        if isinstance(sample, dict):
            value = queue_sample_value(sample)
            if value is not None:
                values.append(value)
    for token in as_list(queue.get("tokens")):
        if not isinstance(token, dict):
            continue
        for sample in as_list(token.get("samples")):
            if isinstance(sample, dict):
                value = queue_sample_value(sample)
                if value is not None:
                    values.append(value)
    return values


def queue_stats(queue: Dict[str, Any], *, min_queue_length: float) -> Dict[str, Any]:
    values = queue_values(queue)
    first = to_float(queue.get("first"))
    last = to_float(queue.get("last"))
    maximum = to_float(queue.get("max"))
    if values:
        if first is None:
            first = values[0]
        if last is None:
            last = values[-1]
        if maximum is None:
            maximum = max(values)
    sustained = to_float(queue.get("sustainedSamples"))
    if sustained is None and values:
        sustained = float(sum(1 for value in values if value >= min_queue_length))
    token_count = len([token for token in as_list(queue.get("tokens")) if isinstance(token, dict)])
    return {
        "hasMetric": bool(values or token_count or maximum is not None),
        "sampleCount": len(values),
        "tokenCount": token_count,
        "first": first,
        "last": last,
        "max": maximum,
        "sustainedSamples": int(sustained or 0),
    }


def variants_by_name(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    variants: Dict[str, Dict[str, Any]] = {}
    for item in as_list(report.get("variants")):
        if isinstance(item, dict):
            name = str(item.get("variant") or item.get("name") or "").strip()
            if name:
                variants[name] = item
    return variants


def select_baseline_target(report: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], str, str]:
    variants = variants_by_name(report)
    evaluation = report.get("i02Evaluation") if isinstance(report.get("i02Evaluation"), dict) else {}
    baseline_name = str(evaluation.get("baselineVariant") or "")
    target_name = str(evaluation.get("targetVariant") or "")
    baseline = variants.get(baseline_name) if baseline_name else None
    target = variants.get(target_name) if target_name else None
    rows = [row for row in as_list(report.get("variants")) if isinstance(row, dict)]
    if baseline is None and rows:
        baseline = rows[0]
        baseline_name = str(baseline.get("variant") or baseline.get("name") or "baseline")
    if target is None and rows:
        target = rows[-1]
        target_name = str(target.get("variant") or target.get("name") or "target")
    return baseline, target, baseline_name, target_name


def thresholds(report: Dict[str, Any], args: argparse.Namespace) -> Dict[str, float]:
    evaluation = report.get("i02Evaluation") if isinstance(report.get("i02Evaluation"), dict) else {}
    configured = evaluation.get("thresholds") if isinstance(evaluation.get("thresholds"), dict) else {}
    return {
        "minQueueLength": float(to_float(configured.get("minQueueLength")) or args.min_queue_length),
        "minSustainedQueueSamples": float(to_float(configured.get("minSustainedQueueSamples")) or args.min_sustained_queue_samples),
        "recoveredQueueLength": float(to_float(configured.get("recoveredQueueLength")) if to_float(configured.get("recoveredQueueLength")) is not None else args.recovered_queue_length),
        "minInteractionDelayDeltaMs": float(to_float(configured.get("minInteractionDelayDeltaMs")) or args.min_interaction_delay_delta_ms),
    }


def variant_failures(row: Dict[str, Any], name: str, *, require_cleanup: bool) -> List[str]:
    failures: List[str] = []
    if row.get("ok") is not True:
        failures.append(f"{name}:ok")
    gates = row.get("gates") if isinstance(row.get("gates"), dict) else {}
    for key in ("dryRun", "apply", "viewRead", "pageValidate", "profile"):
        if key in gates and gates.get(key) is not True:
            failures.append(f"{name}:gates.{key}")
    if row.get("error"):
        failures.append(f"{name}:error")
    if require_cleanup:
        cleanup = row.get("cleanup") if isinstance(row.get("cleanup"), dict) else {}
        cleanup_values = {
            "rollbackOk": cleanup.get("rollbackOk", row.get("rollbackOk")),
            "cleanupRouteAbsent": cleanup.get("cleanupRouteAbsent", row.get("cleanupRouteAbsent")),
            "cleanupViewsAbsent": cleanup.get("cleanupViewsAbsent", row.get("cleanupViewsAbsent", row.get("cleanupViewAbsent"))),
        }
        for key, value in cleanup_values.items():
            if value is not None and value is not True:
                failures.append(f"{name}:{key}")
    return failures


def all_variant_failures(report: Dict[str, Any], *, require_cleanup: bool) -> List[str]:
    failures: List[str] = []
    for index, row in enumerate(as_list(report.get("variants"))):
        if not isinstance(row, dict):
            continue
        name = str(row.get("variant") or row.get("name") or f"variant-{index + 1}")
        failures.extend(variant_failures(row, name, require_cleanup=require_cleanup))
    return failures


def rollup_activity(row: Dict[str, Any]) -> Dict[str, Any]:
    rollup = row.get("metricRollup") if isinstance(row.get("metricRollup"), dict) else {}
    keys = {
        "queueTasksDeltaMax": ("queuetasksDeltaMax", "queueTasksDeltaMax"),
        "scriptsDeltaMax": ("scriptsDeltaMax", "scriptDeltaMax"),
        "propertyChangesDeltaMax": ("propertychangesDeltaMax", "propertyChangesDeltaMax"),
        "messagesSentDeltaMax": ("messagessentDeltaMax", "messagesSentDeltaMax"),
    }
    result: Dict[str, Any] = {}
    for output_key, candidates in keys.items():
        value = None
        for key in candidates:
            value = to_float(rollup.get(key))
            if value is not None:
                break
        result[output_key] = value
    result["hasSupportingActivity"] = any((value or 0) > 0 for value in result.values() if isinstance(value, (int, float)))
    return result


def interaction_delta(report: Dict[str, Any], baseline: Optional[Dict[str, Any]], target: Optional[Dict[str, Any]]) -> Optional[float]:
    evaluation = report.get("i02Evaluation") if isinstance(report.get("i02Evaluation"), dict) else {}
    direct = to_float(evaluation.get("interactionDelayDeltaMs"))
    if direct is not None:
        return direct
    baseline_ms = to_float(evaluation.get("baselineInteractionMs"))
    target_ms = to_float(evaluation.get("targetInteractionMs"))
    if baseline_ms is None and baseline:
        browser = baseline.get("browserInteraction") if isinstance(baseline.get("browserInteraction"), dict) else {}
        baseline_ms = to_float(browser.get("resultElapsedMs"))
    if target_ms is None and target:
        browser = target.get("browserInteraction") if isinstance(target.get("browserInteraction"), dict) else {}
        target_ms = to_float(browser.get("resultElapsedMs"))
    if baseline_ms is None or target_ms is None:
        return None
    return target_ms - baseline_ms


def claim_texts(value: Any) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        parts: List[str] = []
        for key in ("id", "type", "claimType", "status", "title", "summary", "text", "recommendation", "decision"):
            if value.get(key) is not None:
                parts.append(str(value.get(key)))
        return [" ".join(parts)] if parts else []
    texts: List[str] = []
    for item in as_list(value):
        texts.extend(claim_texts(item))
    return texts


def explicit_backlog_claims(report: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for key in ("claim", "claims", "queueBacklogClaim", "recommendation", "recommendations", "decision", "conclusion"):
        texts.extend(claim_texts(report.get(key)))
    patterns = (
        r"\b(proven|causal|observed|recommend)\b.*\b(queue[- ]?backlog|backlog|queue[- ]?length)\b",
        r"\b(queue[- ]?backlog|backlog|queue[- ]?length)\b.*\b(proven|causal|observed|recommend)\b",
        r"\bi-02-queue-backlog\b",
    )
    matches: List[str] = []
    for text in texts:
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in patterns):
            matches.append(text)
    return matches


def explicit_rejections(report: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for key in ("claim", "claims", "interpretation", "decision", "conclusion"):
        texts.extend(claim_texts(report.get(key)))
    patterns = (
        r"\b(not|no|reject|rejected|negative|insufficient)\b.*\b(queue[- ]?backlog|backlog|i-02)\b",
        r"\bqueue[- ]?length\b.*\b(0|zero|flat|did not rise|stayed)\b",
        r"\bqueue[- ]?task\b.*\b(supporting|not.*proof|insufficient)\b",
    )
    matches: List[str] = []
    for text in texts:
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in patterns):
            matches.append(text)
    return matches


def analyze_report(path: Path, report: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    threshold = thresholds(report, args)
    baseline, target, baseline_name, target_name = select_baseline_target(report)
    baseline_queue = queue_stats(
        baseline.get("queueLength") if isinstance(baseline, dict) and isinstance(baseline.get("queueLength"), dict) else {},
        min_queue_length=threshold["minQueueLength"],
    )
    target_queue = queue_stats(
        target.get("queueLength") if isinstance(target, dict) and isinstance(target.get("queueLength"), dict) else {},
        min_queue_length=threshold["minQueueLength"],
    )
    target_activity = rollup_activity(target or {})
    delta_ms = interaction_delta(report, baseline, target)
    evaluation = report.get("i02Evaluation") if isinstance(report.get("i02Evaluation"), dict) else {}
    checks = evaluation.get("checks") if isinstance(evaluation.get("checks"), dict) else {}
    active_incident_window = truthy(report.get("activeIncidentWindow") or evaluation.get("activeIncidentWindow"))

    baseline_max = baseline_queue["max"] if baseline_queue["max"] is not None else 0.0
    target_max = target_queue["max"] if target_queue["max"] is not None else 0.0
    target_last = target_queue["last"]
    queue_rose = bool(target_queue["hasMetric"] and target_max >= threshold["minQueueLength"] and target_max > baseline_max)
    queue_sustained = bool(target_queue["sustainedSamples"] >= int(threshold["minSustainedQueueSamples"]))
    queue_recovered = bool(target_last is not None and target_last <= threshold["recoveredQueueLength"])
    delay_correlated = bool(
        checks.get("interactionDelayIncreased") is True
        or active_incident_window
        or (delta_ms is not None and delta_ms >= threshold["minInteractionDelayDeltaMs"])
    )
    positive_proof = bool(
        report.get("ok") is True
        and target_queue["hasMetric"]
        and target_queue["sampleCount"] >= 3
        and queue_rose
        and queue_sustained
        and queue_recovered
        and delay_correlated
    )
    flat_zero = bool(target_queue["hasMetric"] and (target_max or 0.0) <= 0.0)
    negative_rejection = bool(
        report.get("ok") is True
        and report.get("mechanicsOk", True) is not False
        and not positive_proof
        and target_queue["hasMetric"]
        and (
            report.get("negativeI02Accepted") is True
            or report.get("strictI02Ok") is False
            or evaluation.get("ok") is False
            or bool(explicit_rejections(report))
        )
    )
    strict_flag = report.get("strictI02Ok")
    if strict_flag is None:
        strict_flag = evaluation.get("ok")

    return {
        "path": str(path),
        "runId": report.get("runId"),
        "ok": report.get("ok") is True,
        "mechanicsOk": report.get("mechanicsOk"),
        "strictI02Ok": strict_flag,
        "negativeI02Accepted": report.get("negativeI02Accepted") is True,
        "baselineVariant": baseline_name,
        "targetVariant": target_name,
        "thresholds": threshold,
        "baselineQueue": baseline_queue,
        "targetQueue": target_queue,
        "interactionDelayDeltaMs": delta_ms,
        "activeIncidentWindow": active_incident_window,
        "supportingActivity": target_activity,
        "checks": {
            "queueLengthMetricPresent": target_queue["hasMetric"],
            "queueHasPreDuringPostSamples": target_queue["sampleCount"] >= 3,
            "queueExceededBaseline": target_max > baseline_max,
            "queueRose": queue_rose,
            "queueSustained": queue_sustained,
            "queueRecovered": queue_recovered,
            "interactionDelayCorrelated": delay_correlated,
            "flatZeroQueueLength": flat_zero,
        },
        "positiveQueueBacklogProof": positive_proof,
        "rejectedLocalQueueBacklog": negative_rejection,
        "explicitBacklogClaims": explicit_backlog_claims(report),
        "explicitRejections": explicit_rejections(report),
        "variantFailures": all_variant_failures(report, require_cleanup=not args.no_require_cleanup),
    }


def validate_reports(
    analyses: Sequence[Dict[str, Any]],
    load_errors: Sequence[str],
    *,
    allow_negative_i02: bool,
    require_cleanup: bool,
) -> Dict[str, Any]:
    errors: List[str] = list(load_errors)
    warnings: List[str] = []
    if not analyses:
        errors.append("no reports were loaded")

    any_positive = any(item["positiveQueueBacklogProof"] for item in analyses)
    any_rejected = any(item["rejectedLocalQueueBacklog"] for item in analyses)
    any_metric = any(item["checks"]["queueLengthMetricPresent"] for item in analyses)
    any_activity = any(item["supportingActivity"]["hasSupportingActivity"] for item in analyses)

    for analysis in analyses:
        label = analysis.get("runId") or analysis.get("path")
        checks = analysis["checks"]
        if not analysis["ok"]:
            errors.append(f"{label}: report ok is not true")
        if analysis["mechanicsOk"] is False:
            errors.append(f"{label}: mechanicsOk is false")
        if require_cleanup and analysis["variantFailures"]:
            errors.append(f"{label}: variant gates or cleanup failed: {', '.join(analysis['variantFailures'])}")
        if not checks["queueLengthMetricPresent"]:
            errors.append(f"{label}: missing queue-length metric evidence")
        if analysis["explicitBacklogClaims"] and not analysis["positiveQueueBacklogProof"]:
            errors.append(f"{label}: explicit queue-backlog/proof claim lacks sustained queue-length rise, recovery, and correlated delay")
        if analysis["positiveQueueBacklogProof"] and analysis["strictI02Ok"] is False:
            errors.append(f"{label}: strictI02Ok is false despite queue-backlog proof-shaped evidence")
        if not analysis["positiveQueueBacklogProof"]:
            missing = [key for key, value in checks.items() if key != "flatZeroQueueLength" and not value]
            missing_text = ", ".join(missing) if missing else "report status, mechanics, or cleanup gates"
            if allow_negative_i02 and analysis["rejectedLocalQueueBacklog"]:
                warnings.append(f"{label}: accepted as negative I-02 evidence; missing strict proof checks: {missing_text}")
            else:
                errors.append(f"{label}: no strict queue-backlog proof; missing checks: {missing_text}")
        if checks["flatZeroQueueLength"] and analysis["supportingActivity"]["hasSupportingActivity"] and analysis["positiveQueueBacklogProof"]:
            errors.append(f"{label}: flat queue-length cannot be positive queue-backlog proof")

    if not any_positive and not (allow_negative_i02 and any_rejected):
        errors.append("no report proves queue backlog; use --allow-negative-i02 only for explicitly rejected local evidence")

    aggregate = {
        "reportsChecked": len(analyses),
        "hasQueueLengthMetricEvidence": any_metric,
        "hasSupportingQueueTaskOrScriptActivity": any_activity,
        "positiveQueueBacklogProof": any_positive,
        "rejectedLocalQueueBacklog": any_rejected,
        "allowNegativeI02": allow_negative_i02,
    }
    return {
        "ok": not errors,
        "checkedAt": utc_now(),
        "errors": errors,
        "warnings": warnings,
        "aggregate": aggregate,
        "reports": list(analyses),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify queue-backlog evidence before I-02 wording.")
    parser.add_argument("reports", nargs="+", help="Structured report JSON files or directories containing summary.json.")
    parser.add_argument("--out-json", default="", help="Optional JSON output path for the validation result.")
    parser.add_argument("--allow-negative-i02", action="store_true", help="Allow explicit negative/rejection evidence when strict queue-backlog proof is absent.")
    parser.add_argument("--allow-rejected-local-claim", action="store_true", help="Alias for --allow-negative-i02.")
    parser.add_argument("--min-queue-length", type=float, default=1.0)
    parser.add_argument("--min-sustained-queue-samples", type=int, default=2)
    parser.add_argument("--recovered-queue-length", type=float, default=0.0)
    parser.add_argument("--min-interaction-delay-delta-ms", type=float, default=100.0)
    parser.add_argument("--no-require-cleanup", action="store_true", help="Do not fail on variant rollback/cleanup fields.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.min_queue_length <= 0:
        raise SystemExit("--min-queue-length must be > 0")
    if args.min_sustained_queue_samples < 1:
        raise SystemExit("--min-sustained-queue-samples must be >= 1")
    if args.min_interaction_delay_delta_ms < 0:
        raise SystemExit("--min-interaction-delay-delta-ms must be >= 0")

    analyses: List[Dict[str, Any]] = []
    load_errors: List[str] = []
    for raw_path in args.reports:
        report, errors, loaded_path = load_report(Path(raw_path))
        load_errors.extend(errors)
        if report is not None:
            analyses.append(analyze_report(loaded_path, report, args))

    result = validate_reports(
        analyses,
        load_errors,
        allow_negative_i02=bool(args.allow_negative_i02 or args.allow_rejected_local_claim),
        require_cleanup=not args.no_require_cleanup,
    )
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
