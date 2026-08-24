#!/usr/bin/env python3
"""Verify repeated clean-baseline evidence before causal or release wording."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


STRONG_CLAIM_PATTERNS = (
    r"\bcausal\b",
    r"\bproven improvement\b",
    r"\bproved improvement\b",
    r"\brecommend(?:ed|ation)?\b",
    r"\brelease[- ]?ready\b",
    r"\baccepted for release\b",
    r"\bacceptance (?:passed|complete|accepted)\b",
)
EXPLICIT_STRONG_CLAIM_KEYS = ("causalClaim", "recommendationClaim", "releaseClaim", "readyForRelease", "claimReleaseReady")
BOUNDARY_PATTERNS = (
    r"\bpartial\b",
    r"\blocal\b.*\bnot\b.*\brelease\b",
    r"\bdo not claim\b",
    r"\bdo not recommend\b",
    r"\bnot causal\b",
    r"\bnot a recommendation\b",
    r"\brecommendation rejected\b",
    r"\brelease wording rejected\b",
    r"\brelease claim rejected\b",
    r"\bnot proof\b",
    r"\bsuggestive\b",
    r"\bhypothesis\b",
)
NEGATED_STRONG_PATTERNS = (
    r"\bnot\s+(?:a\s+)?causal\b",
    r"\bnot\s+causal\s+proof\b",
    r"\bnot\s+release[- ]?ready\b",
    r"\bno\s+release[- ]?ready\b",
    r"\bnot\s+accepted\s+for\s+release\b",
    r"\bdo\s+not\s+recommend\b",
    r"\bnot\s+a\s+recommendation\b",
    r"\brecommendation\s+rejected\b",
    r"\brelease\s+wording\s+rejected\b",
    r"\brelease\s+claim\s+rejected\b",
)


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
        for candidate in (
            path / "summary.json",
            path / "repetition-policy-report.json",
            path / "acceptance-case-report.json",
            path / "cache-share-report.json",
            path / "tag-binding-claim-report.json",
            path / "report.json",
        ):
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no structured repetition-policy report: {path}"], path
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001 - exact parse failure belongs in evidence
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
        return value.strip().lower() in {"true", "yes", "observed", "proven", "passed", "causal", "complete"}
    return False


def meaningful_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or (text.startswith("<") and text.endswith(">")):
        return ""
    return text


def first_number(*sources: Dict[str, Any], keys: Sequence[str]) -> Optional[float]:
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in keys:
            value = to_float(source.get(key))
            if value is not None:
                return value
    return None


def first_bool(*sources: Dict[str, Any], keys: Sequence[str]) -> bool:
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in keys:
            if key in source:
                return truthy(source.get(key))
    return False


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


def collect_text(report: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "claim",
        "claims",
        "recommendation",
        "recommendations",
        "decision",
        "conclusion",
        "status",
        "summary",
        "interpretation",
    ):
        parts.extend(claim_texts(report.get(key)))
    return " ".join(parts).lower()


def remove_negated_strong_claims(text: str) -> str:
    cleaned = text
    for pattern in NEGATED_STRONG_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    return cleaned


def has_strong_claim(report: Dict[str, Any]) -> bool:
    for key in EXPLICIT_STRONG_CLAIM_KEYS:
        if truthy(report.get(key)):
            return True
    text = remove_negated_strong_claims(collect_text(report))
    return any(re.search(pattern, text) for pattern in STRONG_CLAIM_PATTERNS)


def has_boundary(report: Dict[str, Any]) -> bool:
    text = collect_text(report)
    return any(re.search(pattern, text) for pattern in BOUNDARY_PATTERNS)


def pair_metrics_from_rows(report: Dict[str, Any]) -> Dict[str, Optional[float]]:
    rows = [row for row in as_list(report.get("pairedRuns") or report.get("pairs")) if isinstance(row, dict)]
    if not rows:
        return {"pairedRunCount": None, "improvedPairCount": None}
    count = len(rows)
    improved = 0
    for row in rows:
        if truthy(row.get("improved") or row.get("primaryImproved")):
            improved += 1
        else:
            improvement = to_float(row.get("improvementPercent"))
            if improvement is not None and improvement > 0:
                improved += 1
    return {"pairedRunCount": float(count), "improvedPairCount": float(improved)}


def repetition_policy(report: Dict[str, Any]) -> Dict[str, Any]:
    policy = report.get("repetitionPolicy") if isinstance(report.get("repetitionPolicy"), dict) else {}
    comparison = report.get("comparison") if isinstance(report.get("comparison"), dict) else {}
    acceptance = report.get("acceptanceEvidence") if isinstance(report.get("acceptanceEvidence"), dict) else {}
    row_metrics = pair_metrics_from_rows(report)
    paired_count = first_number(
        policy,
        comparison,
        acceptance,
        report,
        row_metrics,
        keys=("pairedRunCount", "pairCount", "countedPairs", "pairedRuns", "repetitionsPerVariant", "runCount"),
    )
    improved_count = first_number(
        policy,
        comparison,
        acceptance,
        report,
        row_metrics,
        keys=("improvedPairCount", "pairsImproved", "improvedPairs", "runsImproved", "primaryMetricImprovedPairs"),
    )
    median_improvement = first_number(
        policy,
        comparison,
        acceptance,
        report,
        keys=("medianImprovementPercent", "medianImprovementPct", "primaryMetricMedianImprovementPercent", "primaryMetricImprovementPercent"),
    )
    max_safety_regression = first_number(
        policy,
        comparison,
        acceptance,
        report,
        keys=("maxSafetyRegressionPercent", "safetyRegressionPercentMax", "secondaryMetricMaxRegressionPercent", "worstSafetyRegressionPercent"),
    )
    clean_baseline = first_bool(
        policy,
        comparison,
        acceptance,
        report,
        keys=("repeatedCleanBaseline", "cleanBaseline", "cleanBaselineOk", "cleanBaselinesOk", "identicalCleanBaselinePairs"),
    )
    identical_scenario = first_bool(
        policy,
        comparison,
        acceptance,
        report,
        keys=("identicalScenario", "scenarioMatched", "scenarioEquivalent", "sameScenario", "sameScenarioAndCadence"),
    )
    safety_metrics_ok = first_bool(
        policy,
        comparison,
        acceptance,
        report,
        keys=("safetyMetricsOk", "secondaryMetricsOk", "noSecondaryRegression"),
    )
    return {
        "pairedRunCount": paired_count,
        "improvedPairCount": improved_count,
        "medianImprovementPercent": median_improvement,
        "maxSafetyRegressionPercent": max_safety_regression,
        "repeatedCleanBaseline": clean_baseline,
        "identicalScenario": identical_scenario,
        "safetyMetricsOk": safety_metrics_ok,
    }


def analyze_report(
    path: Path,
    report: Dict[str, Any],
    *,
    min_pairs: int,
    min_improved_pairs: int,
    min_median_improvement_percent: float,
    max_safety_regression_percent: float,
) -> Dict[str, Any]:
    policy = repetition_policy(report)
    safety_regression = policy["maxSafetyRegressionPercent"]
    safety_ok = bool(
        policy["safetyMetricsOk"]
        or (safety_regression is not None and safety_regression <= max_safety_regression_percent)
    )
    checks = {
        "repeatedCleanBaseline": policy["repeatedCleanBaseline"] is True,
        "identicalScenario": policy["identicalScenario"] is True,
        "pairedRunCount": policy["pairedRunCount"] is not None and policy["pairedRunCount"] >= min_pairs,
        "improvedPairCount": policy["improvedPairCount"] is not None and policy["improvedPairCount"] >= min_improved_pairs,
        "medianImprovement": policy["medianImprovementPercent"] is not None and policy["medianImprovementPercent"] >= min_median_improvement_percent,
        "safetyRegression": safety_ok,
    }
    return {
        "path": str(path),
        "runId": report.get("runId"),
        "strongClaim": has_strong_claim(report),
        "boundaryPresent": has_boundary(report),
        "policy": policy,
        "checks": checks,
        "policyPass": all(checks.values()),
        "missing": [key for key, value in checks.items() if not value],
    }


def validate_reports(
    analyses: Sequence[Dict[str, Any]],
    load_errors: Sequence[str],
    *,
    require_policy: bool,
    allow_local_rejection: bool,
) -> Dict[str, Any]:
    errors: List[str] = list(load_errors)
    warnings: List[str] = []
    if not analyses:
        errors.append("no reports were loaded")
    for analysis in analyses:
        label = analysis.get("runId") or analysis.get("path")
        if analysis["strongClaim"] and not analysis["policyPass"]:
            errors.append(f"{label}: causal/recommendation/release claim lacks repeated clean-baseline policy evidence: {', '.join(analysis['missing'])}")
        if require_policy and not analysis["policyPass"]:
            errors.append(f"{label}: repetition policy required but missing or insufficient: {', '.join(analysis['missing'])}")
        if not analysis["strongClaim"] and not analysis["policyPass"]:
            if allow_local_rejection and analysis["boundaryPresent"]:
                warnings.append(f"{label}: accepted as bounded/local or suggestive evidence only; missing policy checks: {', '.join(analysis['missing'])}")
            elif not analysis["boundaryPresent"]:
                warnings.append(f"{label}: no strong claim and no explicit boundary; do not use for causal or release wording")
    return {
        "ok": not errors,
        "checkedAt": utc_now(),
        "reportsChecked": len(analyses),
        "strongClaims": sum(1 for item in analyses if item["strongClaim"]),
        "policyPassCount": sum(1 for item in analyses if item["policyPass"]),
        "errors": errors,
        "warnings": warnings,
        "analyses": list(analyses),
    }


def verify_paths(
    paths: Sequence[Path],
    *,
    min_pairs: int = 7,
    min_improved_pairs: int = 6,
    min_median_improvement_percent: float = 15.0,
    max_safety_regression_percent: float = 10.0,
    require_policy: bool = False,
    allow_local_rejection: bool = False,
) -> Dict[str, Any]:
    analyses: List[Dict[str, Any]] = []
    load_errors: List[str] = []
    for path in paths:
        report, errors, actual_path = load_report(path)
        load_errors.extend(errors)
        if report is None:
            continue
        analyses.append(
            analyze_report(
                actual_path,
                report,
                min_pairs=min_pairs,
                min_improved_pairs=min_improved_pairs,
                min_median_improvement_percent=min_median_improvement_percent,
                max_safety_regression_percent=max_safety_regression_percent,
            )
        )
    return validate_reports(analyses, load_errors, require_policy=require_policy, allow_local_rejection=allow_local_rejection)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Structured report JSON files or directories containing summary.json.")
    parser.add_argument("--out-json", default="")
    parser.add_argument("--min-pairs", type=int, default=7)
    parser.add_argument("--min-improved-pairs", type=int, default=6)
    parser.add_argument("--min-median-improvement-percent", type=float, default=15.0)
    parser.add_argument("--max-safety-regression-percent", type=float, default=10.0)
    parser.add_argument("--require-policy", action="store_true", help="Require repetition policy evidence even without strong causal/release wording.")
    parser.add_argument("--allow-local-rejection", action="store_true", help="Allow explicit bounded/local or suggestive evidence that rejects causal/release wording.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = verify_paths(
        [Path(path) for path in args.paths],
        min_pairs=args.min_pairs,
        min_improved_pairs=args.min_improved_pairs,
        min_median_improvement_percent=args.min_median_improvement_percent,
        max_safety_regression_percent=args.max_safety_regression_percent,
        require_policy=args.require_policy,
        allow_local_rejection=args.allow_local_rejection,
    )
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(json.dumps({"ok": result["ok"], "errors": result["errors"], "warnings": result["warnings"]}, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
