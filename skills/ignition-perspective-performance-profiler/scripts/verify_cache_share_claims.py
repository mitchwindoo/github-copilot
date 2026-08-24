#!/usr/bin/env python3
"""Verify Cache & Share evidence before allowing recommendation wording.

This checker is offline and read-only. It accepts one or more structured
summary JSON files, or directories that contain summary.json. It validates that
query/tag-history Cache & Share reports apply a meaningful threshold, that
off/on evidence is internally consistent, and that explicit recommendation or
consolidation claims are not stronger than the measured evidence.
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
        candidates = [
            path / "summary.json",
            path / "cache-share-report.json",
            path / "query-cache-share-report.json",
            path / "report.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no structured Cache & Share report: {path}"], path
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001 - exact parse error belongs in evidence
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
        return value.strip().lower() in {"true", "yes", "observed", "proven", "passed", "causal"}
    return False


def cleanup_failures(variant: Dict[str, Any]) -> List[str]:
    cleanup = variant.get("cleanup")
    if not isinstance(cleanup, dict):
        return []
    failures: List[str] = []
    for key, value in cleanup.items():
        if key == "rollbackOk" and value is not True:
            failures.append(key)
        if key.startswith("cleanup") and key.endswith("Absent") and value is not True:
            failures.append(key)
    return failures


def variant_cache_values(report: Dict[str, Any]) -> Tuple[bool, bool, bool, List[str]]:
    variants = [row for row in as_list(report.get("variants")) if isinstance(row, dict)]
    if not variants:
        return False, False, True, []
    has_off = any(row.get("cacheAndShare") is False for row in variants)
    has_on = any(row.get("cacheAndShare") is True for row in variants)
    failures: List[str] = []
    for row in variants:
        variant_name = str(row.get("variant") or row.get("name") or "<unnamed>")
        if row.get("ok") is not True:
            failures.append(f"{variant_name}:ok")
        for cleanup_key in cleanup_failures(row):
            failures.append(f"{variant_name}:{cleanup_key}")
    return has_off, has_on, not failures, failures


def pair_from_values(name: str, off: Any, on: Any, minimum: Any, observed: Any, metric: str = "") -> Dict[str, Any]:
    off_value = to_float(off)
    on_value = to_float(on)
    minimum_value = to_float(minimum)
    reduction = None if off_value is None or on_value is None else off_value - on_value
    consistent = True
    threshold_applied = off_value is not None and on_value is not None and minimum_value is not None
    observed_bool = truthy(observed)
    if threshold_applied:
        should_observe = bool(reduction is not None and reduction >= minimum_value)
        consistent = observed_bool == should_observe
    return {
        "name": name,
        "metric": metric,
        "off": off_value,
        "on": on_value,
        "minimumReduction": minimum_value,
        "reductionFromOff": reduction,
        "observed": observed_bool,
        "thresholdApplied": threshold_applied,
        "consistentWithThreshold": consistent,
    }


def extract_pairs(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    comparison = report.get("comparison") if isinstance(report.get("comparison"), dict) else {}
    pairs: List[Dict[str, Any]] = []
    if "cacheOffDatabaseQueryDuringDelta" in comparison or "cacheOnDatabaseQueryDuringDelta" in comparison:
        pairs.append(
            pair_from_values(
                "cache-off-vs-cache-on",
                comparison.get("cacheOffDatabaseQueryDuringDelta"),
                comparison.get("cacheOnDatabaseQueryDuringDelta"),
                comparison.get("minimumReductionForConsolidation"),
                comparison.get("observedConsolidationSignal"),
                str(comparison.get("primaryDatabaseMetricOff") or comparison.get("primaryDatabaseMetricOn") or ""),
            )
        )
    for prefix, label in (("sameParam", "same-parameter"), ("distinctParam", "distinct-parameter")):
        reduction = comparison.get(f"{prefix}CacheReduction")
        if isinstance(reduction, dict):
            pairs.append(
                pair_from_values(
                    label,
                    reduction.get("off"),
                    reduction.get("on"),
                    reduction.get("minimumReduction"),
                    reduction.get("observedReduction"),
                    str(comparison.get("primaryDatabaseMetric") or "databases.queries"),
                )
            )
    return pairs


def sensitivity_observed(report: Dict[str, Any]) -> bool:
    comparison = report.get("comparison") if isinstance(report.get("comparison"), dict) else {}
    if comparison.get("parameterShapeVisibleWithCacheOff") is True and comparison.get("parameterShapeVisibleWithCacheOn") is True:
        return True
    off_delta = to_float(comparison.get("distinctMinusSameCacheOffDatabaseQueryDuringDelta"))
    on_delta = to_float(comparison.get("distinctMinusSameCacheOnDatabaseQueryDuringDelta"))
    off_min = to_float(comparison.get("minimumDifferenceForParameterShapeOff"))
    on_min = to_float(comparison.get("minimumDifferenceForParameterShapeOn"))
    if off_delta is not None and on_delta is not None and off_min is not None and on_min is not None:
        return off_delta >= off_min and on_delta >= on_min
    for key in ("metricSensitiveToParameterShape", "metricSensitiveToDistinctPaths", "queryMetricSensitive"):
        if report.get(key) is True or comparison.get(key) is True:
            return True
    return False


def meaningful_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or (text.startswith("<") and text.endswith(">")):
        return ""
    return text


def tag_history_evidence(report: Dict[str, Any]) -> Dict[str, Any]:
    history_fixture = report.get("historyFixture") if isinstance(report.get("historyFixture"), dict) else {}
    gates = history_fixture.get("gates") if isinstance(history_fixture.get("gates"), dict) else {}
    last_probe = history_fixture.get("lastProbe") if isinstance(history_fixture.get("lastProbe"), dict) else {}
    comparison = report.get("comparison") if isinstance(report.get("comparison"), dict) else {}
    packages = [row for row in as_list(report.get("packages")) if isinstance(row, dict)]

    provider = meaningful_text(report.get("actualHistoryProviderEvidence")) or meaningful_text(report.get("historyProvider"))
    provider_evidence = bool(provider)
    history_probe_ok = (
        gates.get("historyProbe") is True
        and last_probe.get("ok") is True
        and last_probe.get("queryOk") is True
        and (last_probe.get("historyAvailable") is True or history_fixture.get("historyAvailable") is True)
    )
    tag_stats = [row for row in as_list(last_probe.get("tagStats")) if isinstance(row, dict)]
    has_sample_backed_stats = last_probe.get("historyAvailabilityMode") == "storedSamples" or any(
        "storedSampleCount" in row for row in tag_stats
    )
    if has_sample_backed_stats:
        tag_stats_ok = bool(tag_stats) and all(
            to_float(row.get("storedSampleCount")) is not None
            and float(row.get("storedSampleCount")) > 0
            for row in tag_stats
        )
    else:
        tag_stats_ok = bool(tag_stats) and all(
            row.get("hasData") is True
            and meaningful_text(row.get("firstTimestamp"))
            and meaningful_text(row.get("lastTimestamp"))
            and to_float(row.get("nonNullCount")) is not None
            and float(row.get("nonNullCount")) > 0
            for row in tag_stats
        )
    tag_reads = [row for row in as_list(history_fixture.get("tagReadSample")) if isinstance(row, dict)]
    tag_read_ok = bool(tag_reads) and all(
        meaningful_text(row.get("path"))
        and str(row.get("quality", "")).lower().startswith("good")
        and meaningful_text(row.get("timestamp"))
        for row in tag_reads
    )
    off_packages = [row for row in packages if row.get("cacheAndShare") is False]
    on_packages = [row for row in packages if row.get("cacheAndShare") is True]
    same_shape = False
    if off_packages and on_packages:
        off = off_packages[0]
        on = on_packages[0]
        same_shape = (
            as_list(off.get("tagPaths")) == as_list(on.get("tagPaths"))
            and off.get("historyAggregation") == on.get("historyAggregation")
            and off.get("historyRangeMinutes") == on.get("historyRangeMinutes")
            and off.get("historyReturnRows") == on.get("historyReturnRows")
            and off.get("pollingRateSec") == on.get("pollingRateSec")
            and off.get("bindingCount") == on.get("bindingCount")
        )
    off_delta = to_float(comparison.get("cacheOffDatabaseQueryDuringDelta"))
    on_delta = to_float(comparison.get("cacheOnDatabaseQueryDuringDelta"))
    metric_name = str(comparison.get("primaryDatabaseMetricOff") or comparison.get("primaryDatabaseMetricOn") or "")
    query_activity = off_delta is not None and on_delta is not None and bool(metric_name)

    checks = {
        "providerEvidence": provider_evidence,
        "historyProbeOk": history_probe_ok,
        "tagStatsOk": tag_stats_ok,
        "tagReadQualityTimestampOk": tag_read_ok,
        "sameHistoryShape": same_shape,
        "queryActivityEvidence": query_activity,
    }
    return {
        "ok": all(checks.values()),
        "provider": provider,
        "checks": checks,
        "missing": [key for key, value in checks.items() if not value],
    }


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


def explicit_consolidation_claims(report: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for key in (
        "claim",
        "claims",
        "cacheShareClaim",
        "cacheShareClaims",
        "recommendation",
        "recommendations",
        "decision",
        "conclusion",
    ):
        texts.extend(claim_texts(report.get(key)))
    claim_patterns = (
        r"\b(proven|causal|observed)\b.*\b(cache\s*&?\s*share|consolidation)\b",
        r"\b(cache\s*&?\s*share|consolidation)\b.*\b(proven|causal|observed)\b",
        r"\b(enable|turn on|recommend)\b.*\b(cache\s*&?\s*share)\b",
        r"\bcache-share-consolidation\b",
    )
    matches: List[str] = []
    for text in texts:
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in claim_patterns):
            matches.append(text)
    return matches


def analyze_report(path: Path, report: Dict[str, Any]) -> Dict[str, Any]:
    pairs = extract_pairs(report)
    variant_off, variant_on, variants_ok, variant_failures = variant_cache_values(report)
    comparison = report.get("comparison") if isinstance(report.get("comparison"), dict) else {}
    comparison_off_on = "cacheOffDatabaseQueryDuringDelta" in comparison and "cacheOnDatabaseQueryDuringDelta" in comparison
    has_cache_off_on = bool((variant_off and variant_on) or comparison_off_on or len(pairs) >= 2)
    threshold_pairs = [pair for pair in pairs if pair["thresholdApplied"]]
    observed_pairs = [pair for pair in pairs if pair["observed"]]
    rejected_pairs = [pair for pair in threshold_pairs if not pair["observed"] and pair["consistentWithThreshold"]]
    inconsistent_pairs = [pair for pair in pairs if not pair["consistentWithThreshold"]]
    claims = explicit_consolidation_claims(report)
    return {
        "path": str(path),
        "runId": report.get("runId"),
        "ok": report.get("ok") is True,
        "hasCacheOffOnEvidence": has_cache_off_on,
        "variantsOk": variants_ok,
        "variantFailures": variant_failures,
        "pairs": pairs,
        "thresholdPairCount": len(threshold_pairs),
        "observedConsolidation": bool(observed_pairs),
        "rejectedLocalConsolidation": bool(rejected_pairs) and not bool(observed_pairs),
        "inconsistentPairs": inconsistent_pairs,
        "sensitivityObserved": sensitivity_observed(report),
        "tagHistoryEvidence": tag_history_evidence(report),
        "explicitConsolidationClaims": claims,
    }


def validate_reports(
    analyses: Sequence[Dict[str, Any]],
    load_errors: Sequence[str],
    *,
    require_cache_off_on: bool,
    require_threshold: bool,
    require_cleanup: bool,
    require_sensitive_metric: bool,
    require_history_evidence: bool,
    allow_rejected_local_claim: bool,
) -> Dict[str, Any]:
    errors: List[str] = list(load_errors)
    warnings: List[str] = []
    if not analyses:
        errors.append("no reports were loaded")

    any_cache_off_on = any(item["hasCacheOffOnEvidence"] for item in analyses)
    any_threshold = any(item["thresholdPairCount"] > 0 for item in analyses)
    any_sensitivity = any(item["sensitivityObserved"] for item in analyses)
    any_history_evidence = any(item["tagHistoryEvidence"]["ok"] for item in analyses)
    any_observed = any(item["observedConsolidation"] for item in analyses)
    any_rejected = any(item["rejectedLocalConsolidation"] for item in analyses)

    if require_cache_off_on and not any_cache_off_on:
        errors.append("no report contains Cache & Share off/on evidence")
    if require_threshold and not any_threshold:
        errors.append("no report applies a meaningful Cache & Share reduction threshold")
    if require_sensitive_metric and not any_sensitivity:
        errors.append("no report proves the selected query metric is sensitive to the tested query shape")
    if require_history_evidence and not any_history_evidence:
        errors.append("no report proves tag-history provider, probe, tag quality/timestamps, same-shape variants, and query-activity evidence")

    for analysis in analyses:
        label = analysis.get("runId") or analysis.get("path")
        if not analysis["ok"]:
            errors.append(f"{label}: report ok is not true")
        if require_cache_off_on and not analysis["hasCacheOffOnEvidence"]:
            warnings.append(f"{label}: not a direct Cache & Share off/on report")
        if require_cleanup and not analysis["variantsOk"]:
            errors.append(f"{label}: variant gates or cleanup failed: {', '.join(analysis['variantFailures'])}")
        if require_history_evidence and not analysis["tagHistoryEvidence"]["ok"]:
            missing = ", ".join(analysis["tagHistoryEvidence"].get("missing", []))
            errors.append(f"{label}: tag-history evidence incomplete: {missing}")
        if analysis["inconsistentPairs"]:
            pair_names = ", ".join(pair["name"] for pair in analysis["inconsistentPairs"])
            errors.append(f"{label}: observed consolidation flags disagree with threshold math: {pair_names}")
        if analysis["explicitConsolidationClaims"] and not analysis["observedConsolidation"]:
            errors.append(f"{label}: explicit Cache & Share consolidation/recommendation claim lacks observed consolidation")
        if analysis["explicitConsolidationClaims"] and require_sensitive_metric and not any_sensitivity:
            errors.append(f"{label}: explicit Cache & Share claim lacks metric-sensitivity evidence")
        if analysis["explicitConsolidationClaims"] and require_history_evidence and not analysis["tagHistoryEvidence"]["ok"]:
            errors.append(f"{label}: explicit tag-history Cache & Share claim lacks complete tag-history evidence")

    if allow_rejected_local_claim:
        if not (any_observed or any_rejected):
            errors.append("reports neither prove consolidation nor explicitly reject the local consolidation claim by threshold")
    elif not any_observed:
        errors.append("no report proves Cache & Share consolidation; use --allow-rejected-local-claim for safe rejection evidence")

    aggregate = {
        "reportsChecked": len(analyses),
        "hasCacheOffOnEvidence": any_cache_off_on,
        "hasMeaningfulThreshold": any_threshold,
        "hasMetricSensitivityEvidence": any_sensitivity,
        "hasTagHistoryEvidence": any_history_evidence,
        "observedConsolidation": any_observed,
        "rejectedLocalConsolidation": any_rejected,
        "allowRejectedLocalClaim": allow_rejected_local_claim,
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
    parser = argparse.ArgumentParser(description="Verify Cache & Share claim evidence before recommendation wording.")
    parser.add_argument("reports", nargs="+", help="Structured report JSON files or directories containing summary.json.")
    parser.add_argument("--out-json", default="", help="Optional JSON output path for the validation result.")
    parser.add_argument("--require-sensitive-metric", action="store_true", help="Require query-shape sensitivity evidence before accepting the claim boundary.")
    parser.add_argument("--require-history-evidence", action="store_true", help="Require tag-history provider/probe/tag quality/query-activity evidence for A-02 claims.")
    parser.add_argument("--allow-rejected-local-claim", action="store_true", help="Allow threshold-backed local rejection evidence instead of requiring observed consolidation.")
    parser.add_argument("--no-require-cache-off-on", action="store_true", help="Do not require Cache & Share off/on evidence.")
    parser.add_argument("--no-require-threshold", action="store_true", help="Do not require a meaningful reduction threshold.")
    parser.add_argument("--no-require-cleanup", action="store_true", help="Do not require variant gate and cleanup success when variants are present.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    analyses: List[Dict[str, Any]] = []
    load_errors: List[str] = []
    for raw_path in args.reports:
        report, errors, loaded_path = load_report(Path(raw_path))
        load_errors.extend(errors)
        if report is not None:
            analyses.append(analyze_report(loaded_path, report))

    result = validate_reports(
        analyses,
        load_errors,
        require_cache_off_on=not args.no_require_cache_off_on,
        require_threshold=not args.no_require_threshold,
        require_cleanup=not args.no_require_cleanup,
        require_sensitive_metric=args.require_sensitive_metric,
        require_history_evidence=args.require_history_evidence,
        allow_rejected_local_claim=args.allow_rejected_local_claim,
    )
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
