#!/usr/bin/env python3
"""Verify Perspective profiler evidence-bundle integrity.

This checker is local and read-only by default. It hashes evidence files,
validates JSON and NDJSON parseability, checks that missing evidence is explicit
in the manifest, and verifies that reports keep interpretation boundaries
visible. It does not call a Gateway or mutate runner state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


HASH_CHUNK_SIZE = 1024 * 1024
INTEGRITY_OUTPUT_NAMES = {"evidence-integrity.json", "evidence-integrity.md"}
CORE_COLLECT_FILES = [
    "manifest.json",
    "summary.json",
    "static-profile.json",
    "gateway-samples.ndjson",
    "perspective-session-samples.ndjson",
    "logs.json",
    "report.md",
]
CORE_LIFECYCLE_FILES = [
    "manifest.json",
    "summary.json",
    "static-profile.json",
    "lifecycle-samples.ndjson",
    "browser-summary.json",
    "browser-console.json",
    "network-summary.json",
    "logs.json",
    "report.md",
]
CORE_MULTISESSION_FILES = [
    "manifest.json",
    "summary.json",
    "static-profile.json",
    "multi-session-samples.ndjson",
    "logs.json",
    "report.md",
]
CORE_INTERACTION_FILES = [
    "manifest.json",
    "summary.json",
    "summary.md",
]
CORE_PAIRED_FILES = [
    "manifest.json",
    "summary.json",
    "summary.md",
]
CORE_COMPOSITE_WRAPPER_FILES = [
    "manifest.json",
    "summary.json",
    "summary.md",
]
CORE_FIXTURE_WRAPPER_FILES = [
    "manifest.json",
    "summary.json",
    "summary.md",
    "packages.json",
]
CORE_FILES_BY_BUNDLE_TYPE = {
    "collect-profile": CORE_COLLECT_FILES,
    "lifecycle-profile": CORE_LIFECYCLE_FILES,
    "multi-session-profile": CORE_MULTISESSION_FILES,
    "interaction-profile": CORE_INTERACTION_FILES,
    "paired-profile": CORE_PAIRED_FILES,
    "composite-wrapper": CORE_COMPOSITE_WRAPPER_FILES,
    "fixture-wrapper": CORE_FIXTURE_WRAPPER_FILES,
}
EXPECTED_REPORT_LABELS = {
    "observed": [r"\bdirect observations\b", r"\bdirectly observed\b", r"\bobserved\b"],
    "interpretation": [r"\binterpretation\b", r"\binferred\b", r"\bhypothes", r"\bboundary\b"],
    "unproven": [r"\bunproven\b", r"\bdo not claim\b", r"\bnot proof\b", r"\bnot a .*conclusion\b"],
}
SENSITIVE_PATTERNS = [
    ("authorization-header", re.compile(r"\bAuthorization\s*[:=]", re.IGNORECASE)),
    ("cookie-header", re.compile(r"\bCookie\s*[:=]", re.IGNORECASE)),
    ("bearer-token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)),
    ("runner-token-env", re.compile(r"\bIGNITION_(?:LLM_)?RUNNER_TOKEN\b", re.IGNORECASE)),
    ("password-field", re.compile(r"\bpassword\s*[:=]\s*[^,\s}]+", re.IGNORECASE)),
]
CLAIM_TERMS = (
    "root cause",
    "caused by",
    "causal improvement",
    "proved improvement",
    "proven improvement",
)
CLAIM_BOUNDARY_TERMS = (
    "do not claim",
    "not claim",
    "does not prove",
    "not proof",
    "not a",
    "unproven",
    "suggestive",
    "hypothesis",
    "boundary",
    "until",
    "without",
    "requires",
    "candidate",
)


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def filesystem_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    resolved = path if path.is_absolute() else path.resolve()
    text = str(resolved)
    if text.startswith("\\\\?\\"):
        return Path(text)
    if text.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + text[2:])
    return Path("\\\\?\\" + text)


def display_path(path: Path) -> Path:
    text = str(path)
    if os.name == "nt":
        if text.startswith("\\\\?\\UNC\\"):
            return Path("\\\\" + text[8:])
        if text.startswith("\\\\?\\"):
            return Path(text[4:])
    return path


def path_exists(path: Path) -> bool:
    return filesystem_path(path).exists()


def path_is_file(path: Path) -> bool:
    return filesystem_path(path).is_file()


def path_is_dir(path: Path) -> bool:
    return filesystem_path(path).is_dir()


def write_json(path: Path, data: Dict[str, Any]) -> None:
    target = filesystem_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n")


def write_text_file(path: Path, text: str) -> None:
    target = filesystem_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def relpath(path: Path, root: Path) -> str:
    return display_path(path).relative_to(display_path(root)).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with filesystem_path(path).open("rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_json_any(path: Path) -> Tuple[bool, Any, str]:
    try:
        with filesystem_path(path).open("r", encoding="utf-8") as handle:
            return True, json.load(handle), ""
    except Exception as exc:  # noqa: BLE001 - report exact parse failure
        return False, None, f"{type(exc).__name__}: {exc}"


def read_text(path: Path, max_chars: int = 250_000) -> str:
    try:
        return filesystem_path(path).read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception:
        return ""


def parse_ndjson(path: Path) -> Dict[str, Any]:
    rows = 0
    first_error = ""
    with filesystem_path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except Exception as exc:  # noqa: BLE001 - report exact parse failure
                first_error = f"line {line_number}: {type(exc).__name__}: {exc}"
                break
            if not isinstance(value, dict):
                first_error = f"line {line_number}: expected JSON object row"
                break
            rows += 1
    return {"ok": not first_error, "lineCount": rows, "error": first_error}


def iter_bundle_files(bundle: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, _dirnames, filenames in os.walk(filesystem_path(bundle)):
        for filename in filenames:
            path = Path(dirpath) / filename
            if not path_is_file(path):
                continue
            if path.name in INTEGRITY_OUTPUT_NAMES:
                continue
            files.append(path)
    return sorted(files, key=lambda item: relpath(item, bundle).lower())


def manifest_missing_names(manifest: Dict[str, Any]) -> List[str]:
    missing = manifest.get("missingEvidence")
    names: List[str] = []
    if not isinstance(missing, list):
        return names
    for item in missing:
        if not isinstance(item, dict):
            continue
        for key in ("file", "name"):
            value = item.get(key)
            if value:
                names.append(str(value).replace("\\", "/"))
    return names


def is_explicitly_missing(rel_name: str, manifest: Dict[str, Any]) -> bool:
    names = manifest_missing_names(manifest)
    normalized = rel_name.replace("\\", "/")
    base_name = Path(normalized).name
    for name in names:
        if name == normalized or name == base_name:
            return True
    return False


def listed_manifest_paths(manifest: Dict[str, Any]) -> List[str]:
    files = manifest.get("files")
    if not isinstance(files, list):
        return []
    return [str(item).replace("\\", "/") for item in files if item]


def manifest_path_exists(bundle: Path, rel_name: str) -> bool:
    normalized = rel_name.replace("\\", "/")
    candidate = normalized.rstrip("/")
    has_glob = any(char in candidate for char in "*?[")
    if has_glob:
        matches = list(bundle.glob(candidate))
        if normalized.endswith("/"):
            return any(path_is_dir(path) for path in matches)
        return any(path_exists(path) for path in matches)
    path = bundle / candidate
    return path_is_dir(path) if normalized.endswith("/") else path_exists(path)


def extract_manifest_hashes(manifest: Dict[str, Any]) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    evidence_hashes = manifest.get("evidenceHashes")
    if isinstance(evidence_hashes, dict):
        for key, value in evidence_hashes.items():
            rel_name = str(key).replace("\\", "/")
            if isinstance(value, str):
                hashes[rel_name] = value.lower()
            elif isinstance(value, dict) and isinstance(value.get("sha256"), str):
                hashes[rel_name] = str(value["sha256"]).lower()
    file_hashes = manifest.get("fileHashes")
    if isinstance(file_hashes, dict):
        for key, value in file_hashes.items():
            rel_name = str(key).replace("\\", "/")
            if isinstance(value, str):
                hashes[rel_name] = value.lower()
            elif isinstance(value, dict) and isinstance(value.get("sha256"), str):
                hashes[rel_name] = str(value["sha256"]).lower()
    static_file_hash = manifest.get("staticProfileFileSha256")
    if isinstance(static_file_hash, str):
        hashes["static-profile.json"] = static_file_hash.lower()
    return hashes


def check_sensitive_patterns(path: Path) -> List[str]:
    if filesystem_path(path).stat().st_size > 2_000_000:
        return []
    text = read_text(path)
    matches = []
    for label, pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            matches.append(label)
    return matches


def unlabeled_causal_claim_lines(text: str) -> List[str]:
    claims: List[str] = []
    chunks = re.split(r"[\r\n]+|(?<=[.!?])\s+", text)
    for chunk in chunks:
        line = chunk.strip()
        lower = line.lower()
        if not any(term in lower for term in CLAIM_TERMS):
            continue
        if any(term in lower for term in CLAIM_BOUNDARY_TERMS):
            continue
        if any(term in lower for term in ("causal", "proven", "proved")):
            continue
        claims.append(line[:240])
    return claims


def validate_json_and_ndjson(bundle: Path, files: Sequence[Path]) -> Tuple[List[Dict[str, Any]], List[str]]:
    records: List[Dict[str, Any]] = []
    errors: List[str] = []
    for path in files:
        rel_name = relpath(path, bundle)
        stat = filesystem_path(path).stat()
        record: Dict[str, Any] = {
            "path": rel_name,
            "bytes": stat.st_size,
            "sha256": sha256_file(path),
        }
        suffix = path.suffix.lower()
        if suffix == ".json":
            ok, data, error = read_json_any(path)
            record["jsonOk"] = ok
            if ok:
                record["jsonType"] = type(data).__name__
            else:
                record["jsonError"] = error
                errors.append(f"{rel_name} is not parseable JSON: {error}")
        elif suffix == ".ndjson":
            ndjson = parse_ndjson(path)
            record["ndjsonOk"] = ndjson["ok"]
            record["lineCount"] = ndjson["lineCount"]
            if not ndjson["ok"]:
                record["ndjsonError"] = ndjson["error"]
                errors.append(f"{rel_name} is not parseable NDJSON: {ndjson['error']}")
            elif ndjson["lineCount"] == 0:
                errors.append(f"{rel_name} has zero NDJSON rows")
        sensitive = check_sensitive_patterns(path)
        if sensitive:
            record["sensitivePatternWarnings"] = sensitive
        records.append(record)
    return records, errors


def load_manifest(bundle: Path) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    path = bundle / "manifest.json"
    if not path_exists(path):
        return None, []
    ok, data, error = read_json_any(path)
    if not ok:
        return None, [f"manifest.json is not parseable JSON: {error}"]
    if not isinstance(data, dict):
        return None, ["manifest.json must be a JSON object"]
    return data, []


def classify_manifest_bundle_type(bundle: Path, manifest: Dict[str, Any]) -> str:
    scenario = str(manifest.get("scenario", "")).lower()
    bundle_type = str(manifest.get("bundleType", "")).lower()
    listed_paths = set(listed_manifest_paths(manifest))
    if bundle_type == "composite-wrapper" or "composite-wrapper" in scenario:
        return "composite-wrapper"
    if path_exists(bundle / "summary.md") and (path_exists(bundle / "repetition-01") or "repeated click/action" in scenario or "interaction" in scenario):
        return "interaction-profile"
    if path_exists(bundle / "summary.md") and (path_exists(bundle / "pair-01") or manifest.get("comparisonKind") or manifest.get("pairsRequested")):
        return "paired-profile"
    if path_exists(bundle / "summary.md") and path_exists(bundle / "packages.json") and ("fixture" in scenario or "variants" in listed_paths or path_exists(bundle / "summary.json")):
        return "fixture-wrapper"
    if path_exists(bundle / "multi-session-samples.ndjson") or "multi-session-samples.ndjson" in listed_paths or "multi-session" in scenario:
        return "multi-session-profile"
    if path_exists(bundle / "lifecycle-samples.ndjson") or "lifecycle-samples.ndjson" in listed_paths or "lifecycle" in scenario:
        return "lifecycle-profile"
    return "collect-profile"


def validate_manifest(bundle: Path, manifest: Optional[Dict[str, Any]], require_files: Sequence[str]) -> Tuple[List[str], List[str], str]:
    errors: List[str] = []
    warnings: List[str] = []
    if manifest is None:
        if path_exists(bundle / "summary.json"):
            bundle_type = "summary-wrapper"
            if not path_exists(bundle / "summary.md") and not path_exists(bundle / "report.md"):
                errors.append("summary-wrapper bundle has summary.json but no report.md or summary.md")
        else:
            bundle_type = "unknown"
            errors.append("bundle has no manifest.json or summary.json")
        for rel_name in require_files:
            if not path_exists(bundle / rel_name):
                errors.append(f"required file is missing: {rel_name}")
        return errors, warnings, bundle_type

    bundle_type = classify_manifest_bundle_type(bundle, manifest)
    missing_evidence = manifest.get("missingEvidence")
    changed_resources = manifest.get("changedResources")
    if not isinstance(missing_evidence, list):
        errors.append("manifest.missingEvidence must be a list, even when empty")
    else:
        for index, item in enumerate(missing_evidence):
            if not isinstance(item, dict):
                errors.append(f"manifest.missingEvidence[{index}] must be an object")
            elif not item.get("reason"):
                errors.append(f"manifest.missingEvidence[{index}] is missing reason")
    if not isinstance(changed_resources, list):
        errors.append("manifest.changedResources must be a list, even when empty")
    grade = manifest.get("evidenceGrade")
    if grade and grade not in ("Observed", "Correlated", "Causal", "Unproven"):
        warnings.append(f"manifest.evidenceGrade has unexpected value: {grade}")
    for rel_name in CORE_FILES_BY_BUNDLE_TYPE.get(bundle_type, CORE_COLLECT_FILES):
        if not path_exists(bundle / rel_name) and not is_explicitly_missing(rel_name, manifest):
            errors.append(f"core evidence file is missing without manifest.missingEvidence entry: {rel_name}")
    for rel_name in listed_manifest_paths(manifest):
        if not manifest_path_exists(bundle, rel_name) and not is_explicitly_missing(rel_name, manifest):
            if rel_name.endswith("/"):
                errors.append(f"manifest-listed directory is missing: {rel_name}")
            else:
                errors.append(f"manifest-listed file is missing without missingEvidence entry: {rel_name}")
    for rel_name in require_files:
        if not manifest_path_exists(bundle, rel_name) and not is_explicitly_missing(rel_name, manifest):
            errors.append(f"required file is missing without manifest.missingEvidence entry: {rel_name}")
    return errors, warnings, bundle_type


def validate_hashes(bundle: Path, manifest: Optional[Dict[str, Any]], file_records: Sequence[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if manifest is None:
        return errors, warnings
    actual = {str(item["path"]).replace("\\", "/"): str(item["sha256"]).lower() for item in file_records}
    expected = extract_manifest_hashes(manifest)
    for rel_name, expected_hash in sorted(expected.items()):
        actual_hash = actual.get(rel_name)
        if actual_hash is None:
            errors.append(f"manifest hash references missing file: {rel_name}")
        elif actual_hash != expected_hash:
            errors.append(f"manifest hash mismatch for {rel_name}: expected {expected_hash}, actual {actual_hash}")

    static_path = bundle / "static-profile.json"
    static_manifest_hash = manifest.get("staticProfileSha256")
    if isinstance(static_manifest_hash, str) and path_exists(static_path):
        static_file_hash = actual.get("static-profile.json")
        ok, static_profile, _ = read_json_any(static_path)
        static_view_hash = static_profile.get("viewSha256") if ok and isinstance(static_profile, dict) else None
        manifest_view_hash = manifest.get("viewSha256")
        if static_manifest_hash.lower() == str(static_file_hash).lower():
            pass
        elif static_view_hash and static_manifest_hash.lower() == str(static_view_hash).lower():
            warnings.append("manifest.staticProfileSha256 stores the analyzed view hash, not the static-profile.json file hash; evidence-integrity output records the file hash separately")
        elif manifest_view_hash and static_manifest_hash.lower() == str(manifest_view_hash).lower():
            warnings.append("manifest.staticProfileSha256 matches manifest.viewSha256, not the static-profile.json file hash")
        else:
            warnings.append("manifest.staticProfileSha256 does not match static-profile.json hash or static profile view hash")
    return errors, warnings


def validate_report(bundle: Path, bundle_type: str, manifest: Optional[Dict[str, Any]]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    errors: List[str] = []
    warnings: List[str] = []
    report_path = bundle / "report.md"
    if not path_exists(report_path) and bundle_type in ("summary-wrapper", "interaction-profile", "paired-profile", "composite-wrapper", "fixture-wrapper"):
        report_path = bundle / "summary.md"
    report_info: Dict[str, Any] = {"path": relpath(report_path, bundle) if path_exists(report_path) else ""}
    if not path_exists(report_path):
        errors.append("report.md or summary.md is missing")
        return errors, warnings, report_info

    raw_text = read_text(report_path)
    text = raw_text.lower()
    label_results: Dict[str, bool] = {}
    for label, patterns in EXPECTED_REPORT_LABELS.items():
        label_results[label] = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
    report_info["labels"] = label_results
    if bundle_type in ("collect-profile", "lifecycle-profile", "multi-session-profile", "interaction-profile", "paired-profile", "composite-wrapper", "fixture-wrapper"):
        if not label_results["observed"]:
            errors.append(f"{report_info['path']} does not label direct observed evidence")
        if not label_results["interpretation"]:
            errors.append(f"{report_info['path']} does not include an interpretation/inference boundary")
        if not label_results["unproven"]:
            errors.append(f"{report_info['path']} does not mark unproven or non-causal limits")
        if manifest and manifest.get("evidenceGrade") and "evidence grade" not in text:
            errors.append(f"{report_info['path']} does not include the manifest evidence grade")
    else:
        if not label_results["interpretation"]:
            warnings.append(f"{report_info['path']} does not include an explicit Interpretation section")

    causal_claim_lines = unlabeled_causal_claim_lines(raw_text)
    if causal_claim_lines:
        report_info["unlabeledCausalClaims"] = causal_claim_lines
        errors.append(f"{report_info['path']} appears to make a causal claim without causal/proven wording")
    return errors, warnings, report_info


def directory_summary(bundle: Path, manifest: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    dirs: List[str] = []
    if manifest:
        dirs.extend(item.rstrip("/") for item in listed_manifest_paths(manifest) if item.endswith("/"))
    summaries: List[Dict[str, Any]] = []
    for rel_name in sorted(set(dirs)):
        candidates = list(bundle.glob(rel_name)) if any(char in rel_name for char in "*?[") else [bundle / rel_name]
        for path in sorted(candidates):
            if not path_is_dir(path):
                continue
            files = iter_bundle_files(path)
            summaries.append({"path": relpath(path, bundle) + "/", "fileCount": len(files)})
    return summaries


def verify_bundle(bundle: Path, require_files: Sequence[str]) -> Dict[str, Any]:
    bundle = bundle.resolve()
    errors: List[str] = []
    warnings: List[str] = []
    if not path_exists(bundle) or not path_is_dir(bundle):
        return {
            "ok": False,
            "bundle": str(bundle),
            "errors": [f"bundle path is not a directory: {bundle}"],
            "warnings": [],
        }

    manifest, manifest_errors = load_manifest(bundle)
    errors.extend(manifest_errors)
    manifest_check_errors, manifest_warnings, bundle_type = validate_manifest(bundle, manifest, require_files)
    errors.extend(manifest_check_errors)
    warnings.extend(manifest_warnings)

    files = iter_bundle_files(bundle)
    file_records, parse_errors = validate_json_and_ndjson(bundle, files)
    errors.extend(parse_errors)
    hash_errors, hash_warnings = validate_hashes(bundle, manifest, file_records)
    errors.extend(hash_errors)
    warnings.extend(hash_warnings)
    report_errors, report_warnings, report_info = validate_report(bundle, bundle_type, manifest)
    errors.extend(report_errors)
    warnings.extend(report_warnings)

    missing_declared = manifest.get("missingEvidence", []) if isinstance(manifest, dict) else []
    changed_resources = manifest.get("changedResources", []) if isinstance(manifest, dict) else []
    return {
        "ok": not errors,
        "bundle": str(bundle),
        "bundleType": bundle_type,
        "checkedAt": utc_now(),
        "runId": manifest.get("runId") if isinstance(manifest, dict) else None,
        "evidenceGrade": manifest.get("evidenceGrade") if isinstance(manifest, dict) else None,
        "fileCount": len(file_records),
        "totalBytes": sum(int(item.get("bytes", 0)) for item in file_records),
        "files": file_records,
        "directories": directory_summary(bundle, manifest),
        "report": report_info,
        "missingEvidence": missing_declared if isinstance(missing_declared, list) else None,
        "changedResources": changed_resources if isinstance(changed_resources, list) else None,
        "errors": errors,
        "warnings": warnings,
    }


def make_markdown(results: Sequence[Dict[str, Any]]) -> str:
    lines = ["# Evidence Bundle Integrity", ""]
    ok_count = sum(1 for item in results if item.get("ok"))
    lines.append(f"Bundles checked: `{len(results)}`")
    lines.append(f"Bundles passed: `{ok_count}`")
    lines.append("")
    for item in results:
        status = "PASS" if item.get("ok") else "FAIL"
        lines.append(f"## {status}: {item.get('runId') or item.get('bundle')}")
        lines.append("")
        lines.append(f"- Bundle type: `{item.get('bundleType', 'unknown')}`")
        lines.append(f"- Files hashed: `{item.get('fileCount', 0)}`")
        lines.append(f"- Bytes hashed: `{item.get('totalBytes', 0)}`")
        missing = item.get("missingEvidence")
        if isinstance(missing, list):
            lines.append(f"- Missing evidence entries: `{len(missing)}`")
        changed = item.get("changedResources")
        if isinstance(changed, list):
            lines.append(f"- Changed resources entries: `{len(changed)}`")
        errors = item.get("errors") or []
        warnings = item.get("warnings") or []
        if errors:
            lines.append("")
            lines.append("Errors:")
            for error in errors:
                lines.append(f"- {error}")
        if warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in warnings:
                lines.append(f"- {warning}")
        lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify Perspective profiler evidence-bundle integrity.")
    parser.add_argument("bundles", nargs="+", help="Evidence bundle directories to verify.")
    parser.add_argument("--out-dir", help="Optional output directory for evidence-integrity.json and evidence-integrity.md.")
    parser.add_argument("--require-file", action="append", default=[], help="Additional relative file path that must exist or be explicitly listed as missing. Repeatable.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    results = [verify_bundle(Path(bundle), args.require_file) for bundle in args.bundles]
    output = {
        "ok": all(item.get("ok") for item in results),
        "checkedAt": utc_now(),
        "bundleCount": len(results),
        "bundles": results,
    }
    if args.out_dir:
        out_dir = Path(args.out_dir)
        write_json(out_dir / "evidence-integrity.json", output)
        write_text_file(out_dir / "evidence-integrity.md", make_markdown(results))
    print(json.dumps({"ok": output["ok"], "bundleCount": len(results), "failed": [item.get("bundle") for item in results if not item.get("ok")]}, indent=2, sort_keys=True))
    if not output["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
