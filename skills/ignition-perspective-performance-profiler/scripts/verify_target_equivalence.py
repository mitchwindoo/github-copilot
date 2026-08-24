#!/usr/bin/env python3
"""Verify target-equivalence evidence before customer-specific wording."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


STRONG_TARGET_PATTERNS = (
    r"\brecommend(?:ed|ation)?\b",
    r"\brelease[- ]?ready\b",
    r"\baccepted for release\b",
    r"\bacceptance (?:passed|complete|accepted)\b",
    r"\bcausal\b",
    r"\bproven improvement\b",
    r"\bproved improvement\b",
    r"\bapply (?:this )?(?:fix|remediation|change)\b",
)
TARGET_CONTEXT_PATTERNS = (
    r"\bcustomer\b",
    r"\btarget\b",
    r"\bthis route\b",
    r"\bthis view\b",
    r"\bthis screen\b",
    r"\bthis gateway\b",
    r"\bthis project\b",
    r"\bproduction\b",
    r"\bstaging\b",
)
EXPLICIT_TARGET_CLAIM_KEYS = (
    "customerSpecificClaim",
    "customerRecommendationClaim",
    "targetRecommendationClaim",
    "customerAcceptanceClaim",
    "targetAcceptanceClaim",
    "releaseClaim",
    "readyForRelease",
    "claimReleaseReady",
)
BOUNDARY_PATTERNS = (
    r"\bpartial\b",
    r"\blocal\b",
    r"\bfixture\b",
    r"\bsuggestive\b",
    r"\bhypothesis\b",
    r"\bnot customer[- ]?equivalent\b",
    r"\btarget equivalence missing\b",
    r"\bdo not recommend\b",
    r"\bnot a recommendation\b",
    r"\brecommendation rejected\b",
    r"\brelease wording rejected\b",
    r"\brelease claim rejected\b",
    r"\bnot release[- ]?ready\b",
    r"\bnot causal\b",
)
NEGATED_STRONG_PATTERNS = (
    r"\bnot\s+(?:a\s+)?causal\b",
    r"\bnot\s+release[- ]?ready\b",
    r"\bdo\s+not\s+recommend\b",
    r"\bnot\s+a\s+recommendation\b",
    r"\brecommendation\s+rejected\b",
    r"\brelease\s+wording\s+rejected\b",
    r"\brelease\s+claim\s+rejected\b",
)


BASE_TEXT_FIELDS = (
    "targetProjectOrAlias",
    "targetRouteOrAlias",
    "primaryViewHashOrAlias",
)
BASE_BOOL_FIELDS = (
    "scenarioMatched",
    "readyMarkerMatched",
    "browserClassMatched",
    "cacheStateMatched",
    "sessionClassMatched",
    "dataShapeMatched",
)
SCOPE_TEXT_FIELDS = {
    "query": ("queryPathOrAlias",),
    "tag-history": ("tagProviderOrAlias", "historyProviderOrAlias"),
    "tag-binding": ("tagProviderOrAlias",),
    "acceptance": ("acceptanceCaseId",),
}
SCOPE_BOOL_FIELDS = {
    "query": ("parameterShapeMatched", "queryActivityMetricSensitive"),
    "tag-history": ("historyProbeOk", "tagQualityTimestampObserved", "historyQueryActivityMetricSensitive"),
    "tag-binding": ("qualityTimestampObserved", "updateLatencyObserved", "fetchOrMessageEvidenceObserved"),
    "queue-backlog": ("symptomWindowCaptured", "queueLengthMetricObserved", "riseRecoveryObserved", "delayCorrelated"),
    "acceptance": ("primaryMetricMatched", "safetyMetricsMatched"),
    "remediation": ("changedResourcesMatched", "rollbackPathMatched", "functionalEquivalenceMatched", "safetyMetricsMatched"),
}
SCOPE_ALIASES = {
    "a-01": "query",
    "cache-share": "query",
    "query-cache-share": "query",
    "query": "query",
    "named-query": "query",
    "a-02": "tag-history",
    "tag-history": "tag-history",
    "history": "tag-history",
    "historian": "tag-history",
    "a-15": "tag-binding",
    "tag-binding": "tag-binding",
    "provider": "tag-binding",
    "i-02": "queue-backlog",
    "queue": "queue-backlog",
    "queue-backlog": "queue-backlog",
    "backlog": "queue-backlog",
    "ac-01": "acceptance",
    "ac-02": "acceptance",
    "ac-03": "acceptance",
    "ac-05": "acceptance",
    "acceptance": "acceptance",
    "remediation": "remediation",
}


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
            path / "target-equivalence-report.json",
            path / "acceptance-case-report.json",
            path / "repetition-policy-report.json",
            path / "cache-share-report.json",
            path / "tag-binding-claim-report.json",
            path / "queue-backlog-claim-report.json",
            path / "report.json",
        ):
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no structured target-equivalence report: {path}"], path
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


def truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "observed", "proven", "passed", "matched", "complete"}
    return False


def meaningful_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or (text.startswith("<") and text.endswith(">")):
        return ""
    if text.lower() in {"unknown", "todo", "tbd", "none", "n/a", "na"}:
        return ""
    return text


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
        "acceptanceStatus",
    ):
        parts.extend(claim_texts(report.get(key)))
    return " ".join(parts).lower()


def remove_negated_strong_claims(text: str) -> str:
    cleaned = text
    for pattern in NEGATED_STRONG_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    return cleaned


def explicit_target_claim(report: Dict[str, Any]) -> bool:
    for key in EXPLICIT_TARGET_CLAIM_KEYS:
        if truthy(report.get(key)):
            return True
    claims = report.get("claims")
    for item in as_list(claims):
        if isinstance(item, dict) and truthy(item.get("customerSpecific") or item.get("targetSpecific")):
            return True
    return False


def has_target_claim(report: Dict[str, Any]) -> bool:
    if explicit_target_claim(report):
        return True
    text = remove_negated_strong_claims(collect_text(report))
    has_strong = any(re.search(pattern, text) for pattern in STRONG_TARGET_PATTERNS)
    has_target_context = any(re.search(pattern, text) for pattern in TARGET_CONTEXT_PATTERNS)
    return bool(has_strong and has_target_context)


def has_boundary(report: Dict[str, Any]) -> bool:
    text = collect_text(report)
    return any(re.search(pattern, text) for pattern in BOUNDARY_PATTERNS)


def target_equivalence_block(report: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("targetEquivalence", "customerEquivalence", "targetEquivalentEvidence", "targetEvidence"):
        value = report.get(key)
        if isinstance(value, dict):
            return value
    return {}


def normalize_scope(value: Any) -> str:
    text = str(value).strip().lower().replace("_", "-")
    return SCOPE_ALIASES.get(text, text)


def detect_scopes(report: Dict[str, Any], block: Dict[str, Any]) -> List[str]:
    raw_values: List[Any] = []
    for key in ("scope", "scopes", "evidenceKind", "evidenceKinds", "guideItem", "guideItems", "acceptanceCase", "acceptanceCases"):
        raw_values.extend(as_list(block.get(key)))
        raw_values.extend(as_list(report.get(key)))
    text = collect_text(report)
    for token, scope in SCOPE_ALIASES.items():
        if token in text:
            raw_values.append(scope)
    scopes: Set[str] = set()
    for value in raw_values:
        if isinstance(value, dict):
            value = value.get("id") or value.get("name") or value.get("scope")
        if value is None:
            continue
        scope = normalize_scope(value)
        if scope in {"query", "tag-history", "tag-binding", "queue-backlog", "acceptance", "remediation"}:
            scopes.add(scope)
    if "acceptance" in scopes and report.get("acceptanceCase") == "AC-05":
        scopes.add("remediation")
    if not scopes:
        scopes.add("generic")
    return sorted(scopes)


def field_value(block: Dict[str, Any], report: Dict[str, Any], key: str) -> Any:
    if key in block:
        return block.get(key)
    return report.get(key)


def text_field_ok(block: Dict[str, Any], report: Dict[str, Any], key: str) -> bool:
    return bool(meaningful_text(field_value(block, report, key)))


def bool_field_ok(block: Dict[str, Any], report: Dict[str, Any], key: str) -> bool:
    return truthy(field_value(block, report, key))


def scope_checks(report: Dict[str, Any], block: Dict[str, Any], scopes: Sequence[str]) -> Dict[str, bool]:
    checks: Dict[str, bool] = {}
    for key in BASE_TEXT_FIELDS:
        checks[key] = text_field_ok(block, report, key)
    for key in BASE_BOOL_FIELDS:
        checks[key] = bool_field_ok(block, report, key)
    for scope in scopes:
        for key in SCOPE_TEXT_FIELDS.get(scope, ()):
            checks[f"{scope}.{key}"] = text_field_ok(block, report, key)
        for key in SCOPE_BOOL_FIELDS.get(scope, ()):
            if scope == "tag-history" and key == "historyQueryActivityMetricSensitive":
                checks[f"{scope}.{key}"] = bool_field_ok(block, report, key) or bool_field_ok(block, report, "queryActivityMetricSensitive")
            else:
                checks[f"{scope}.{key}"] = bool_field_ok(block, report, key)
    return checks


def analyze_report(path: Path, report: Dict[str, Any]) -> Dict[str, Any]:
    block = target_equivalence_block(report)
    scopes = detect_scopes(report, block)
    checks = scope_checks(report, block, scopes)
    missing = [key for key, value in checks.items() if not value]
    return {
        "path": str(path),
        "runId": report.get("runId"),
        "scopes": scopes,
        "targetClaim": has_target_claim(report),
        "explicitTargetClaim": explicit_target_claim(report),
        "boundaryPresent": has_boundary(report),
        "targetEquivalencePresent": bool(block),
        "checks": checks,
        "targetEquivalencePass": not missing,
        "missing": missing,
    }


def validate_reports(
    analyses: Sequence[Dict[str, Any]],
    load_errors: Sequence[str],
    *,
    require_target_equivalence: bool,
    allow_local_rejection: bool,
) -> Dict[str, Any]:
    errors: List[str] = list(load_errors)
    warnings: List[str] = []
    if not analyses:
        errors.append("no reports were loaded")
    for analysis in analyses:
        label = analysis.get("runId") or analysis.get("path")
        if analysis["targetClaim"] and not analysis["targetEquivalencePass"]:
            errors.append(f"{label}: customer-specific recommendation/acceptance/release claim lacks target-equivalence evidence: {', '.join(analysis['missing'])}")
        if require_target_equivalence and not analysis["targetEquivalencePass"]:
            errors.append(f"{label}: target equivalence required but missing or incomplete: {', '.join(analysis['missing'])}")
        if not analysis["targetClaim"] and not analysis["targetEquivalencePass"]:
            if allow_local_rejection and analysis["boundaryPresent"]:
                warnings.append(f"{label}: accepted as local/partial or suggestive evidence only; missing target-equivalence checks: {', '.join(analysis['missing'])}")
            elif not analysis["boundaryPresent"]:
                warnings.append(f"{label}: no target-equivalence proof and no explicit boundary; do not use for customer-specific recommendation or acceptance wording")
    return {
        "ok": not errors,
        "checkedAt": utc_now(),
        "reportsChecked": len(analyses),
        "targetClaims": sum(1 for item in analyses if item["targetClaim"]),
        "targetEquivalencePassCount": sum(1 for item in analyses if item["targetEquivalencePass"]),
        "errors": errors,
        "warnings": warnings,
        "analyses": list(analyses),
    }


def verify_paths(
    paths: Sequence[Path],
    *,
    require_target_equivalence: bool = False,
    allow_local_rejection: bool = False,
) -> Dict[str, Any]:
    analyses: List[Dict[str, Any]] = []
    load_errors: List[str] = []
    for path in paths:
        report, errors, actual_path = load_report(path)
        load_errors.extend(errors)
        if report is None:
            continue
        analyses.append(analyze_report(actual_path, report))
    return validate_reports(
        analyses,
        load_errors,
        require_target_equivalence=require_target_equivalence,
        allow_local_rejection=allow_local_rejection,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Structured report JSON files or directories containing summary.json.")
    parser.add_argument("--out-json", default="")
    parser.add_argument("--require-target-equivalence", action="store_true", help="Require target-equivalence evidence even without explicit customer-specific wording.")
    parser.add_argument("--allow-local-rejection", action="store_true", help="Allow explicit bounded/local evidence that rejects customer-specific recommendation or release wording.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = verify_paths(
        [Path(path) for path in args.paths],
        require_target_equivalence=args.require_target_equivalence,
        allow_local_rejection=args.allow_local_rejection,
    )
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(json.dumps({"ok": result["ok"], "errors": result["errors"], "warnings": result["warnings"]}, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
