#!/usr/bin/env python3
"""Verify runner API change workflow evidence before profiler use."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


DOC_REQUIRED = (
    "RUNNER.md",
    "docs/CAPABILITIES.md",
    "docs/API_CHANGE_WORKFLOW.md",
    "evidence/EVIDENCE.md",
    "handoff/HANDOFF.md",
    "root-api-reference",
    "product-version-surface",
)
SHIPPED_BOOL_FIELDS = (
    "sourceUpdated",
    "versionBumped",
    "docsUpdated",
    "contractTestsPassed",
    "newActionTestsPassed",
    "regressionTestsPassed",
    "noWriteProofPassed",
    "failureEnvelopePassed",
    "selfUpdateDryRunPassed",
    "selfUpdateApplyPassed",
    "postUpdateHealthPassed",
    "liveRunnerVersionMatches",
    "evidenceIntegrityPassed",
)
VISIBLE_RUNNER_VERSION_FIELDS = (
    "visibleRunnerVersion",
    "visibleHeaderRunnerVersion",
    "webDevHeaderRunnerVersion",
    "editorHeaderRunnerVersion",
    "copiedHeaderRunnerVersion",
    "displayedRunnerVersion",
    "pastedRunnerVersion",
)
VISIBLE_VERSION_MISMATCH_FIELDS = (
    "liveHealthUsedAsVersionSource",
    "staleVisibleVersionLabeled",
    "visibleVersionMismatchExplained",
)
DESIGN_BOOL_FIELDS = (
    "designOnly",
    "notShipped",
    "notUsedAsEvidence",
    "readOnlyRationale",
    "boundedResponse",
    "securityRedactionPlan",
    "requiredContractsListed",
    "selfUpdatePlanListed",
    "docsPlanListed",
)
CLAIM_KEYS = (
    "profilerEvidenceDependsOnApi",
    "usesNewRunnerAction",
    "customerRecommendationClaim",
    "releaseClaim",
    "readyForRelease",
)
CLAIM_PATTERNS = (
    r"\buse(?:s|d)?\s+new\s+runner\s+api\b",
    r"\bdepends\s+on\s+(?:the\s+)?new\s+(?:runner\s+)?api\b",
    r"\brelease[- ]?ready\b",
    r"\brecommend(?:ed|ation)?\b.*\bnew\s+(?:runner\s+)?api\b",
)
BOUNDARY_PATTERNS = (
    r"\bdesign[- ]?only\b",
    r"\bproposal\b",
    r"\bnot shipped\b",
    r"\bnot used as evidence\b",
    r"\bdo not use\b.*\bevidence\b",
    r"\brequires self[- ]?update\b",
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
            path / "runner-api-workflow-report.json",
            path / "runner-api-change-report.json",
            path / "api-change-report.json",
            path / "summary.json",
            path / "report.json",
        ):
            if candidate.exists():
                path = candidate
                break
        else:
            return None, [f"directory has no structured runner API workflow report: {path}"], path
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
        return value.strip().lower() in {"true", "yes", "passed", "complete", "observed", "updated", "shipped"}
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


def evidence_present(value: Any) -> bool:
    return truthy(value) or bool(meaningful_text(value))


def to_version(value: Any) -> Tuple[int, ...]:
    text = meaningful_text(value)
    if not text:
        return ()
    numbers = re.findall(r"\d+", text)
    return tuple(int(item) for item in numbers)


def version_increased(before: Any, after: Any) -> bool:
    before_version = to_version(before)
    after_version = to_version(after)
    return bool(before_version and after_version and after_version > before_version)


def version_matches(value: Any, targets: Iterable[Any]) -> bool:
    text = meaningful_text(value)
    if not text:
        return False
    value_version = to_version(text)
    for target in targets:
        target_text = meaningful_text(target)
        if not target_text:
            continue
        if text == target_text:
            return True
        target_version = to_version(target_text)
        if value_version and target_version and value_version == target_version:
            return True
    return False


def claim_texts(value: Any) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        parts: List[str] = []
        for key in ("id", "type", "status", "title", "summary", "text", "recommendation", "decision"):
            if value.get(key) is not None:
                parts.append(str(value.get(key)))
        return [" ".join(parts)] if parts else []
    texts: List[str] = []
    for item in as_list(value):
        texts.extend(claim_texts(item))
    return texts


def collect_text(report: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("claim", "claims", "recommendation", "recommendations", "decision", "conclusion", "status", "summary", "interpretation"):
        parts.extend(claim_texts(report.get(key)))
    block = workflow_block(report)
    for key in ("claim", "summary", "decision", "status", "boundary"):
        parts.extend(claim_texts(block.get(key)))
    return " ".join(parts).lower()


def workflow_block(report: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("runnerApiWorkflow", "runnerApiChange", "apiChange", "runnerApiChangeWorkflow", "runnerApi"):
        value = report.get(key)
        if isinstance(value, dict):
            return value
    return {}


def has_claim(report: Dict[str, Any], block: Dict[str, Any]) -> bool:
    for key in CLAIM_KEYS:
        if truthy(report.get(key)) or truthy(block.get(key)):
            return True
    text = collect_text(report)
    return any(re.search(pattern, text) for pattern in CLAIM_PATTERNS)


def has_boundary(report: Dict[str, Any]) -> bool:
    text = collect_text(report)
    return any(re.search(pattern, text) for pattern in BOUNDARY_PATTERNS)


def docs_present(block: Dict[str, Any]) -> Dict[str, bool]:
    docs = block.get("docsUpdatedFiles") or block.get("docsUpdated") or block.get("documentationUpdated")
    normalized = {str(item).replace("\\", "/").strip().lower() for item in as_list(docs)}
    checks: Dict[str, bool] = {}
    for required in DOC_REQUIRED:
        required_norm = required.lower()
        checks[required] = any(required_norm == item or item.endswith("/" + required_norm) for item in normalized)
    if isinstance(docs, dict):
        for required in DOC_REQUIRED:
            checks[required] = checks[required] or truthy(docs.get(required)) or truthy(docs.get(required.replace("/", "\\")))
    return checks


def action_ids(block: Dict[str, Any], report: Dict[str, Any]) -> List[str]:
    values: List[Any] = []
    for key in ("actions", "actionIds", "newActions", "changedActions", "proposedActions"):
        values.extend(as_list(block.get(key)))
        values.extend(as_list(report.get(key)))
    names: List[str] = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("name") or value.get("action") or value.get("id")
        text = meaningful_text(value)
        if text:
            names.append(text)
    return names


def field(block: Dict[str, Any], report: Dict[str, Any], key: str) -> Any:
    if key in block:
        return block.get(key)
    return report.get(key)


def visible_runner_versions(block: Dict[str, Any], report: Dict[str, Any]) -> List[Dict[str, str]]:
    values: List[Dict[str, str]] = []
    for source, container in (("workflow", block), ("report", report)):
        for key in VISIBLE_RUNNER_VERSION_FIELDS:
            if key not in container:
                continue
            text = meaningful_text(container.get(key))
            if text:
                values.append({"source": source, "field": key, "version": text})
    return values


def visible_version_mismatches(block: Dict[str, Any], report: Dict[str, Any], trusted_versions: Iterable[Any]) -> List[Dict[str, str]]:
    versions = visible_runner_versions(block, report)
    trusted = [value for value in trusted_versions if meaningful_text(value)]
    if not versions or not trusted:
        return []
    return [item for item in versions if not version_matches(item["version"], trusted)]


def visible_mismatch_handled(block: Dict[str, Any], report: Dict[str, Any], mismatches: Sequence[Dict[str, str]]) -> bool:
    if not mismatches:
        return True
    return (
        truthy(field(block, report, "liveHealthUsedAsVersionSource"))
        and truthy(field(block, report, "staleVisibleVersionLabeled"))
        and evidence_present(field(block, report, "visibleVersionMismatchExplained"))
    )


def shipped_checks(report: Dict[str, Any], block: Dict[str, Any]) -> Dict[str, bool]:
    checks: Dict[str, bool] = {}
    checks["actionIdsPresent"] = bool(action_ids(block, report))
    before = field(block, report, "runnerVersionBefore") or field(block, report, "apiVersionBefore")
    after = field(block, report, "runnerVersionAfter") or field(block, report, "apiVersionAfter")
    checks["runnerVersionBeforeAfterPresent"] = bool(meaningful_text(before) and meaningful_text(after))
    checks["runnerVersionIncreased"] = version_increased(before, after)
    for key in SHIPPED_BOOL_FIELDS:
        checks[key] = truthy(field(block, report, key))
    doc_checks = docs_present(block)
    for name, ok in doc_checks.items():
        checks[f"doc.{name}"] = ok
    post_health_version = field(block, report, "postUpdateHealthRunnerVersion")
    checks["postUpdateHealthVersionMatches"] = bool(meaningful_text(post_health_version) and meaningful_text(after) and str(post_health_version) == str(after))
    mismatches = visible_version_mismatches(block, report, (after, post_health_version))
    for key in VISIBLE_VERSION_MISMATCH_FIELDS:
        checks[key] = True if not mismatches else evidence_present(field(block, report, key))
    checks["visibleRunnerVersionMismatchHandled"] = visible_mismatch_handled(block, report, mismatches)
    return checks


def design_checks(report: Dict[str, Any], block: Dict[str, Any]) -> Dict[str, bool]:
    checks: Dict[str, bool] = {}
    checks["actionIdsPresent"] = bool(action_ids(block, report))
    checks["problemStatementPresent"] = bool(meaningful_text(field(block, report, "problemStatement")))
    for key in DESIGN_BOOL_FIELDS:
        checks[key] = truthy(field(block, report, key))
    checks["boundaryPresent"] = has_boundary(report)
    return checks


def analyze_report(path: Path, report: Dict[str, Any]) -> Dict[str, Any]:
    block = workflow_block(report)
    shipped = truthy(field(block, report, "shipped") or field(block, report, "behaviorChanged") or field(block, report, "runnerApiChanged"))
    design_only = truthy(field(block, report, "designOnly") or field(block, report, "notShipped"))
    claim = has_claim(report, block)
    shipped_result = shipped_checks(report, block)
    design_result = design_checks(report, block)
    shipped_missing = [key for key, value in shipped_result.items() if not value]
    design_missing = [key for key, value in design_result.items() if not value]
    return {
        "path": str(path),
        "runId": report.get("runId"),
        "actions": action_ids(block, report),
        "visibleRunnerVersions": visible_runner_versions(block, report),
        "visibleRunnerVersionMismatches": visible_version_mismatches(
            block,
            report,
            (
                field(block, report, "runnerVersionAfter") or field(block, report, "apiVersionAfter"),
                field(block, report, "postUpdateHealthRunnerVersion"),
            ),
        ),
        "workflowPresent": bool(block),
        "shipped": shipped,
        "designOnly": design_only,
        "claimDependsOnApi": claim,
        "boundaryPresent": has_boundary(report),
        "shippedChecks": shipped_result,
        "designChecks": design_result,
        "shippedWorkflowPass": not shipped_missing,
        "designOnlyPass": not design_missing,
        "missingShippedWorkflow": shipped_missing,
        "missingDesignWorkflow": design_missing,
    }


def validate_reports(
    analyses: Sequence[Dict[str, Any]],
    load_errors: Sequence[str],
    *,
    require_shipped: bool,
    allow_design_only: bool,
) -> Dict[str, Any]:
    errors: List[str] = list(load_errors)
    warnings: List[str] = []
    if not analyses:
        errors.append("no reports were loaded")
    for analysis in analyses:
        label = analysis.get("runId") or analysis.get("path")
        if not analysis["workflowPresent"]:
            errors.append(f"{label}: missing runner API workflow block")
            continue
        if require_shipped and not analysis["shippedWorkflowPass"]:
            errors.append(f"{label}: shipped runner API workflow required but incomplete: {', '.join(analysis['missingShippedWorkflow'])}")
        if analysis["shipped"] and not analysis["shippedWorkflowPass"]:
            errors.append(f"{label}: runner API behavior changed without complete version/docs/tests/self-update evidence: {', '.join(analysis['missingShippedWorkflow'])}")
        if analysis["claimDependsOnApi"] and not analysis["shippedWorkflowPass"]:
            errors.append(f"{label}: profiler evidence or recommendation depends on a runner API change without complete shipped workflow evidence: {', '.join(analysis['missingShippedWorkflow'])}")
        if analysis["designOnly"]:
            if not allow_design_only:
                errors.append(f"{label}: design-only runner API proposal requires --allow-design-only")
            elif not analysis["designOnlyPass"]:
                errors.append(f"{label}: design-only runner API proposal is missing boundaries: {', '.join(analysis['missingDesignWorkflow'])}")
            elif analysis["claimDependsOnApi"]:
                errors.append(f"{label}: design-only runner API proposal cannot be used as profiler evidence or recommendation support")
            else:
                warnings.append(f"{label}: accepted as design-only API gap; do not use as profiler evidence until shipped and self-updated")
        if not analysis["shipped"] and not analysis["designOnly"]:
            errors.append(f"{label}: runner API workflow must declare shipped behavior change or design-only proposal")
    return {
        "ok": not errors,
        "checkedAt": utc_now(),
        "reportsChecked": len(analyses),
        "shippedWorkflowPassCount": sum(1 for item in analyses if item["shippedWorkflowPass"]),
        "designOnlyPassCount": sum(1 for item in analyses if item["designOnlyPass"]),
        "errors": errors,
        "warnings": warnings,
        "analyses": list(analyses),
    }


def verify_paths(
    paths: Sequence[Path],
    *,
    require_shipped: bool = False,
    allow_design_only: bool = False,
) -> Dict[str, Any]:
    analyses: List[Dict[str, Any]] = []
    load_errors: List[str] = []
    for path in paths:
        report, errors, actual_path = load_report(path)
        load_errors.extend(errors)
        if report is None:
            continue
        analyses.append(analyze_report(actual_path, report))
    return validate_reports(analyses, load_errors, require_shipped=require_shipped, allow_design_only=allow_design_only)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Structured runner API workflow report JSON files or directories.")
    parser.add_argument("--out-json", default="")
    parser.add_argument("--require-shipped", action="store_true", help="Require complete shipped version/docs/tests/self-update workflow evidence.")
    parser.add_argument("--allow-design-only", action="store_true", help="Allow a bounded design-only API proposal that is not used as profiler evidence.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = verify_paths(
        [Path(path) for path in args.paths],
        require_shipped=args.require_shipped,
        allow_design_only=args.allow_design_only,
    )
    if args.out_json:
        write_json(Path(args.out_json), result)
    print(json.dumps({"ok": result["ok"], "errors": result["errors"], "warnings": result["warnings"]}, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
