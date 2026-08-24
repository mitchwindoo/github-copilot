#!/usr/bin/env python3
"""Verify tag-binding/provider claims before recommendation wording.

This checker is offline and read-only. It accepts a tag-binding summary JSON
file, or a directory containing summary.json, and validates that A-15 evidence
does not confuse Perspective UI binding mode with tag/provider latency.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


REQUIRED_VARIANTS = ("direct", "indirect", "reference")


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
        for candidate in (path / "summary.json", path / "tag-binding-claim-report.json", path / "report.json"):
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no structured tag-binding report: {path}"], path
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001 - evidence should include exact parse failure
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
        return value.strip().lower() in {"true", "yes", "observed", "proven", "passed", "causal", "target-specific"}
    return False


def variants_by_name(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    variants: Dict[str, Dict[str, Any]] = {}
    for item in as_list(report.get("variants")):
        if isinstance(item, dict):
            name = str(item.get("variant") or item.get("name") or "").strip().lower()
            if name:
                variants[name] = item
    return variants


def nested_bool(row: Dict[str, Any], *keys: str) -> bool:
    value: Any = row
    for key in keys:
        if not isinstance(value, dict):
            return False
        value = value.get(key)
    return value is True


def variant_gate_errors(name: str, row: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if row.get("ok") is not True:
        errors.append(f"{name}:ok")
    gates = row.get("gates") if isinstance(row.get("gates"), dict) else {}
    for key in ("tagFixture", "viewRead", "pageValidate", "updateProbe", "profile"):
        if gates.get(key) is not True:
            errors.append(f"{name}:gates.{key}")
    cleanup = row.get("cleanup") if isinstance(row.get("cleanup"), dict) else {}
    for key in ("rollbackOk", "cleanupRouteAbsent", "cleanupViewAbsent"):
        if cleanup.get(key) is not True:
            errors.append(f"{name}:cleanup.{key}")
    update_probe = row.get("updateProbe") if isinstance(row.get("updateProbe"), dict) else {}
    if update_probe.get("ok") is not True:
        errors.append(f"{name}:updateProbe.ok")
    if update_probe.get("tagReadOk") is not True:
        errors.append(f"{name}:updateProbe.tagReadOk")
    browser = update_probe.get("browserSummary") if isinstance(update_probe.get("browserSummary"), dict) else {}
    for key in ("ok", "initialTextMatched", "updatedTextMatched"):
        if browser.get(key) is not True:
            errors.append(f"{name}:browserSummary.{key}")
    if int(browser.get("consoleErrorCount") or 0) > 0:
        errors.append(f"{name}:browserSummary.consoleErrorCount")
    if int(browser.get("pageErrorCount") or 0) > 0:
        errors.append(f"{name}:browserSummary.pageErrorCount")
    profile = row.get("profileSummary") if isinstance(row.get("profileSummary"), dict) else {}
    if profile and profile.get("browserReadyCount") != profile.get("browserProbeCount"):
        errors.append(f"{name}:profileSummary.browserReadyCount")
    if profile and profile.get("browserReadyTextMatchedCount") != profile.get("browserProbeCount"):
        errors.append(f"{name}:profileSummary.browserReadyTextMatchedCount")
    return errors


def has_reference_boundary(report: Dict[str, Any]) -> bool:
    comparison = report.get("comparison") if isinstance(report.get("comparison"), dict) else {}
    if comparison.get("referenceTagMode") and comparison.get("directAsReferenceMode"):
        return True
    text = " ".join(str(item) for item in as_list(report.get("interpretation"))).lower()
    boundary_terms = (
        "separates ui binding shape",
        "provider path",
        "provider latency",
        "remote or reference-provider behavior still needs",
        "static binding mode alone",
    )
    return any(term in text for term in boundary_terms)


def provider_evidence(report: Dict[str, Any]) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    for key in ("targetProviderEvidence", "providerEvidence", "remoteProviderEvidence", "referenceProviderEvidence"):
        value = report.get(key)
        if isinstance(value, dict):
            candidates.append(value)
    for candidate in candidates:
        provider_types = " ".join(str(item).lower() for item in as_list(candidate.get("providerTypes") or candidate.get("providers")))
        has_remote_or_reference = bool(
            candidate.get("remoteProvider") is True
            or candidate.get("referenceProvider") is True
            or "remote" in provider_types
            or "reference" in provider_types
        )
        quality = truthy(candidate.get("qualityTimestampEvidence") or candidate.get("qualityAndTimestampEvidence"))
        update_latency = truthy(candidate.get("updateLatencyEvidence") or candidate.get("updateLatencyMeasured"))
        fetch_message = truthy(candidate.get("fetchMessageEvidence") or candidate.get("fetchesMessagesMeasured"))
        if candidate.get("ok") is True and has_remote_or_reference and quality and update_latency and fetch_message:
            return {
                "ok": True,
                "providerTypes": as_list(candidate.get("providerTypes") or candidate.get("providers")),
                "qualityTimestampEvidence": quality,
                "updateLatencyEvidence": update_latency,
                "fetchMessageEvidence": fetch_message,
            }
    return {
        "ok": False,
        "providerTypes": [],
        "qualityTimestampEvidence": False,
        "updateLatencyEvidence": False,
        "fetchMessageEvidence": False,
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


def explicit_provider_claims(report: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for key in ("claim", "claims", "recommendation", "recommendations", "decision", "conclusion"):
        texts.extend(claim_texts(report.get(key)))
    patterns = (
        r"\b(recommend|enable|switch|prefer|replace|use)\b.*\b(reference tag|reference provider|remote provider|provider latency)\b",
        r"\b(reference tag|reference provider|remote provider|provider latency)\b.*\b(faster|slower|bottleneck|cause|causal|proven|recommend)\b",
        r"\bprovider-latency-claim\b",
    )
    matches: List[str] = []
    for text in texts:
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in patterns):
            matches.append(text)
    return matches


def analyze_report(path: Path, report: Dict[str, Any]) -> Dict[str, Any]:
    variants = variants_by_name(report)
    missing_variants = [name for name in REQUIRED_VARIANTS if name not in variants]
    gate_errors: List[str] = []
    for name, row in variants.items():
        if name in REQUIRED_VARIANTS:
            gate_errors.extend(variant_gate_errors(name, row))
    comparison = report.get("comparison") if isinstance(report.get("comparison"), dict) else {}
    provider = provider_evidence(report)
    claims = explicit_provider_claims(report)
    return {
        "path": str(path),
        "runId": report.get("runId"),
        "ok": report.get("ok") is True,
        "requiredVariantsPresent": not missing_variants,
        "missingVariants": missing_variants,
        "variantGateErrors": gate_errors,
        "referenceBoundaryPresent": has_reference_boundary(report),
        "referenceTagMode": comparison.get("referenceTagMode"),
        "directAsReferenceMode": comparison.get("directAsReferenceMode"),
        "targetProviderEvidence": provider,
        "explicitProviderClaims": claims,
    }


def validate_reports(
    analyses: Sequence[Dict[str, Any]],
    load_errors: Sequence[str],
    *,
    allow_local_mechanics: bool,
    require_target_provider_evidence: bool,
) -> Dict[str, Any]:
    errors: List[str] = list(load_errors)
    warnings: List[str] = []
    if not analyses:
        errors.append("no reports were loaded")

    any_provider_evidence = any(item["targetProviderEvidence"]["ok"] for item in analyses)
    for analysis in analyses:
        label = analysis.get("runId") or analysis.get("path")
        if not analysis["ok"]:
            errors.append(f"{label}: report ok is not true")
        if not analysis["requiredVariantsPresent"]:
            errors.append(f"{label}: missing required variants: {', '.join(analysis['missingVariants'])}")
        if analysis["variantGateErrors"]:
            errors.append(f"{label}: variant gates failed: {', '.join(analysis['variantGateErrors'])}")
        if not analysis["referenceBoundaryPresent"]:
            errors.append(f"{label}: missing boundary that separates UI binding shape from tag/provider model")
        if analysis["explicitProviderClaims"] and not analysis["targetProviderEvidence"]["ok"]:
            errors.append(f"{label}: provider/reference recommendation claim lacks target-provider evidence")
        if require_target_provider_evidence and not analysis["targetProviderEvidence"]["ok"]:
            errors.append(f"{label}: target-provider evidence is required but missing")
        if not analysis["targetProviderEvidence"]["ok"] and allow_local_mechanics:
            warnings.append(f"{label}: accepted as local binding-shape mechanics only, not remote/reference-provider proof")

    aggregate = {
        "reportsChecked": len(analyses),
        "hasTargetProviderEvidence": any_provider_evidence,
        "allowLocalMechanics": allow_local_mechanics,
        "requireTargetProviderEvidence": require_target_provider_evidence,
        "providerClaimCount": sum(len(item["explicitProviderClaims"]) for item in analyses),
    }
    if not allow_local_mechanics and not require_target_provider_evidence and not any_provider_evidence:
        errors.append("no target-provider evidence was found; use --allow-local-mechanics only for local mechanics/rejection wording")
    return {
        "ok": not errors,
        "checkedAt": utc_now(),
        "errors": errors,
        "warnings": warnings,
        "aggregate": aggregate,
        "reports": list(analyses),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify A-15 tag binding/provider claim evidence.")
    parser.add_argument("reports", nargs="+", help="Structured report JSON files or directories containing summary.json.")
    parser.add_argument("--out-json", default="", help="Optional JSON output path.")
    parser.add_argument("--allow-local-mechanics", action="store_true", help="Allow local direct/indirect/reference mechanics when no provider recommendation is made.")
    parser.add_argument("--require-target-provider-evidence", action="store_true", help="Require remote/reference provider evidence with quality/timestamp, update-latency, and fetch/message proof.")
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
        allow_local_mechanics=args.allow_local_mechanics,
        require_target_provider_evidence=args.require_target_provider_evidence,
    )
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
