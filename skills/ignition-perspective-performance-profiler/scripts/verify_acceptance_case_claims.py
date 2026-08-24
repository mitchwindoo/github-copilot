#!/usr/bin/env python3
"""Verify acceptance-case evidence before release/acceptance wording.

This checker is offline and read-only. It validates structured acceptance-case
reports for the end-to-end skill acceptance criteria. It accepts complete
staging/customer-equivalent evidence, or explicitly partial local evidence when
the report rejects release wording. It rejects local fixture mechanics that are
promoted as release-ready acceptance proof.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


CASE_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "AC-01": {
        "title": "Gateway-heavy case",
        "evidence": (
            "staticEvidence",
            "runtimeEvidence",
            "synchronizedGatewayBrowser",
            "excessivePollingOrScriptWork",
            "gatewayRuntimeRise",
            "browserStable",
            "repeatedOrIncidentWindow",
        ),
        "grades": ("Correlated", "Causal"),
    },
    "AC-02": {
        "title": "Browser-heavy case",
        "evidence": (
            "staticEvidence",
            "runtimeEvidence",
            "synchronizedGatewayBrowser",
            "largeTableEmbeddedOrChartEvidence",
            "browserLongTaskDomHeapRise",
            "gatewayStable",
        ),
        "grades": ("Correlated", "Causal"),
    },
    "AC-03": {
        "title": "Session-scaling case",
        "evidence": (
            "sessionGroups1_5_10",
            "perSessionCostQuantified",
            "cacheShareProof",
            "metricSensitivity",
            "repeatedCleanBaseline",
            "synchronizedGatewayBrowser",
        ),
        "grades": ("Correlated", "Causal"),
    },
    "AC-05": {
        "title": "Remediation case",
        "evidence": (
            "guardedVariant",
            "identicalRerun",
            "causalPolicyEvaluated",
            "functionalEquivalence",
            "safetyCoveragePassed",
            "rollbackPassed",
        ),
        "grades": ("Causal", "Rejected"),
    },
}

BOUNDARY_KEYS = ("observed", "inferred", "causal", "unproven")
RELEASE_ENVIRONMENTS = {
    "staging",
    "customer-staging",
    "customer-approved-staging",
    "customer-equivalent-staging",
    "customer-like-staging",
}
LOCAL_ENVIRONMENTS = {"local", "local-fixture", "dev", "development", "mechanics", "fixture"}
ACCEPTED_STATUSES = {"accepted", "complete", "passed", "release-ready", "ready"}
PARTIAL_STATUSES = {"partial", "rejected", "not-ready", "local-only", "mechanics-only"}


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
            path / "acceptance-case-report.json",
            path / "acceptance-report.json",
            path / "summary.json",
            path / "report.json",
        ):
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no structured acceptance-case report: {path}"], path
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
        return value.strip().lower() in {"true", "yes", "observed", "proven", "passed", "complete", "causal"}
    return False


def clean_status(value: Any) -> str:
    return re.sub(r"\s+", "-", str(value or "").strip().lower())


def evidence_map(row: Dict[str, Any]) -> Dict[str, Any]:
    value = row.get("requiredEvidence")
    if isinstance(value, dict):
        return value
    value = row.get("evidence")
    return value if isinstance(value, dict) else {}


def boundary_map(row: Dict[str, Any]) -> Dict[str, Any]:
    value = row.get("boundaries")
    return value if isinstance(value, dict) else {}


def missing_evidence(row: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for key in ("missingEvidence", "remainingEvidence", "unprovenEvidence"):
        for item in as_list(row.get(key)):
            text = str(item or "").strip()
            if text:
                missing.append(text)
    return missing


def case_rows(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("acceptanceCases", "cases", "caseResults"):
        value = report.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def text_parts(value: Any) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        parts: List[str] = []
        for key in ("id", "caseId", "status", "title", "summary", "claim", "conclusion", "decision"):
            if value.get(key) is not None:
                parts.append(str(value.get(key)))
        return [" ".join(parts)] if parts else []
    texts: List[str] = []
    for item in as_list(value):
        texts.extend(text_parts(item))
    return texts


def explicit_acceptance_claims(report: Dict[str, Any], row: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for key in ("claim", "claims", "conclusion", "decision", "summary"):
        texts.extend(text_parts(row.get(key)))
        texts.extend(text_parts(report.get(key)))
    patterns = (
        r"\b(release[- ]?ready|acceptance passed|accepted for release|customer-ready)\b",
        r"\b(ac-0[1235]|acceptance)\b.*\b(passed|complete|release-ready|accepted)\b",
    )
    matches: List[str] = []
    for text in texts:
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in patterns):
            matches.append(text)
    return matches


def release_claim(report: Dict[str, Any], row: Dict[str, Any]) -> bool:
    status = clean_status(row.get("status"))
    if status in ACCEPTED_STATUSES:
        return True
    for key in ("releaseClaim", "acceptanceClaim", "readyForRelease", "claimReleaseReady"):
        if truthy(row.get(key)) or truthy(report.get(key)):
            return True
    return bool(explicit_acceptance_claims(report, row))


def local_mechanics(row: Dict[str, Any]) -> bool:
    env = clean_status(row.get("environment") or row.get("evidenceScope"))
    return env in LOCAL_ENVIRONMENTS or truthy(row.get("localMechanicsOnly"))


def boundaries_ok(row: Dict[str, Any]) -> bool:
    boundaries = boundary_map(row)
    return all(truthy(boundaries.get(key)) for key in BOUNDARY_KEYS)


def analyze_case(report: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    case_id = str(row.get("id") or row.get("caseId") or "").strip().upper()
    spec = CASE_REQUIREMENTS.get(case_id)
    status = clean_status(row.get("status"))
    env = clean_status(row.get("environment") or row.get("evidenceScope"))
    grade = str(row.get("evidenceGrade") or row.get("grade") or "").strip()
    evidence = evidence_map(row)
    missing_required = []
    if spec:
        missing_required = [key for key in spec["evidence"] if not truthy(evidence.get(key))]
    missing = missing_evidence(row)
    release = release_claim(report, row)
    partial_or_rejected = status in PARTIAL_STATUSES or local_mechanics(row) or bool(missing)
    accepted = bool(
        spec
        and release
        and env in RELEASE_ENVIRONMENTS
        and grade in spec["grades"]
        and boundaries_ok(row)
        and not missing_required
        and not missing
        and not local_mechanics(row)
    )
    local_rejection = bool(
        spec
        and not release
        and partial_or_rejected
        and boundaries_ok(row)
        and (missing or local_mechanics(row) or status in PARTIAL_STATUSES)
    )
    return {
        "id": case_id,
        "title": spec["title"] if spec else row.get("title"),
        "status": status,
        "environment": env,
        "evidenceGrade": grade,
        "releaseClaim": release,
        "localMechanicsOnly": local_mechanics(row),
        "boundariesOk": boundaries_ok(row),
        "missingRequiredEvidence": missing_required,
        "missingEvidence": missing,
        "acceptedAcceptanceCase": accepted,
        "rejectedLocalAcceptanceClaim": local_rejection,
        "explicitAcceptanceClaims": explicit_acceptance_claims(report, row),
    }


def validate_report(
    report: Dict[str, Any],
    load_errors: Sequence[str],
    *,
    allow_local_rejection: bool,
    require_cases: Sequence[str],
) -> Dict[str, Any]:
    errors: List[str] = list(load_errors)
    warnings: List[str] = []
    rows = case_rows(report)
    analyses = [analyze_case(report, row) for row in rows]
    if not analyses:
        errors.append("report has no acceptanceCases list")

    present = {item["id"] for item in analyses if item["id"]}
    for case_id in require_cases:
        if case_id not in present:
            errors.append(f"missing required acceptance case: {case_id}")

    for analysis in analyses:
        label = analysis["id"] or "<missing-case-id>"
        if label not in CASE_REQUIREMENTS:
            errors.append(f"{label}: unknown or unsupported acceptance case")
            continue
        if analysis["releaseClaim"]:
            if analysis["localMechanicsOnly"]:
                errors.append(f"{label}: local/dev fixture mechanics cannot be release-ready acceptance proof")
            if analysis["environment"] not in RELEASE_ENVIRONMENTS:
                errors.append(f"{label}: release claim requires staging/customer-equivalent environment")
            if not analysis["boundariesOk"]:
                errors.append(f"{label}: release claim is missing observed/inferred/causal/unproven report boundaries")
            if analysis["missingRequiredEvidence"]:
                errors.append(f"{label}: release claim is missing required evidence: {', '.join(analysis['missingRequiredEvidence'])}")
            if analysis["missingEvidence"]:
                errors.append(f"{label}: release claim has unresolved missing evidence: {', '.join(analysis['missingEvidence'])}")
            if not analysis["acceptedAcceptanceCase"]:
                errors.append(f"{label}: acceptance claim is not supported by complete case evidence")
        else:
            if not allow_local_rejection:
                errors.append(f"{label}: no release claim; use --allow-local-rejection for explicit partial/local evidence")
            elif not analysis["rejectedLocalAcceptanceClaim"]:
                errors.append(f"{label}: partial/local evidence needs boundaries and explicit remaining evidence")
            else:
                warnings.append(f"{label}: accepted as partial/local evidence only, not release-ready acceptance proof")

    any_accepted = any(item["acceptedAcceptanceCase"] for item in analyses)
    any_rejected = any(item["rejectedLocalAcceptanceClaim"] for item in analyses)
    if not any_accepted and not (allow_local_rejection and any_rejected):
        errors.append("no acceptance case is complete; partial/local evidence must explicitly reject release wording")

    aggregate = {
        "casesChecked": len(analyses),
        "acceptedAcceptanceCases": sorted(item["id"] for item in analyses if item["acceptedAcceptanceCase"]),
        "rejectedLocalAcceptanceCases": sorted(item["id"] for item in analyses if item["rejectedLocalAcceptanceClaim"]),
        "allowLocalRejection": allow_local_rejection,
    }
    return {
        "ok": not errors,
        "checkedAt": utc_now(),
        "errors": errors,
        "warnings": warnings,
        "aggregate": aggregate,
        "cases": analyses,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify acceptance-case evidence before release wording.")
    parser.add_argument("report", help="Structured acceptance report JSON or directory containing acceptance-case-report.json.")
    parser.add_argument("--out-json", default="", help="Optional JSON output path.")
    parser.add_argument("--allow-local-rejection", action="store_true", help="Allow explicit local/partial evidence that rejects release wording.")
    parser.add_argument(
        "--require-case",
        action="append",
        default=[],
        help="Require a case id such as AC-01. Can be repeated.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report, load_errors, loaded_path = load_report(Path(args.report))
    result = validate_report(
        report or {},
        load_errors,
        allow_local_rejection=args.allow_local_rejection,
        require_cases=[str(item).strip().upper() for item in args.require_case],
    )
    result["path"] = str(loaded_path)
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
