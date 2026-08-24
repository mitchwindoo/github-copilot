import argparse
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path


WRAPPER_RE = re.compile(r"(^|/)wrapper\.log(\.\d+)?$", re.IGNORECASE)
SYSTEM_LOGS_RE = re.compile(r"(^|/)system[_-]?logs?.*\.idb$", re.IGNORECASE)
METRICS_RE = re.compile(r"(^|/).*metrics.*\.idb$", re.IGNORECASE)
THREAD_RE = re.compile(r"(^|/).*(thread[-_ ]?dump|threaddump|threads?).*\.(json|txt|log)$", re.IGNORECASE)
GATEWAY_INFO_RE = re.compile(r"(^|/).*(gateway[-_ ]?info|gatewayinfo|system[-_ ]?info).*\.(json|txt)$", re.IGNORECASE)
AUDIT_RE = re.compile(r"(^|/).*audit.*\.(json|csv|txt|log|idb)$", re.IGNORECASE)
ALARM_RE = re.compile(r"(^|/).*(alarm[-_ ]?journal|journal|alarms?).*\.(json|csv|txt|log|idb)$", re.IGNORECASE)
BROWSER_RE = re.compile(r"(^|/).*(browser|console|client).*\.log$", re.IGNORECASE)
MANIFEST_RE = re.compile(r"(^|/)manifest\.json$", re.IGNORECASE)


def classify(name):
    normalized = name.replace("\\", "/").strip("/")
    lower = normalized.lower()

    if not normalized or lower.endswith("/"):
        return None
    if MANIFEST_RE.search(normalized):
        return entry_class("BundleManifest", "manifest", "manual review")
    if SYSTEM_LOGS_RE.search(normalized):
        return entry_class("GatewayDiagnosticLogsIdb", "diagnostic_log", "scripts/query_gateway_idb.py")
    if METRICS_RE.search(normalized):
        return entry_class("MetricsIdb", "metrics_context", "manual review")
    if WRAPPER_RE.search(normalized):
        return entry_class("WrapperLog", "diagnostic_log", "scripts/query_wrapper_logs.py")
    if THREAD_RE.search(normalized):
        return entry_class("ThreadDump", "thread_state", "manual compare thread signatures")
    if GATEWAY_INFO_RE.search(normalized):
        return entry_class("GatewayInfoSnapshot", "environment_snapshot", "scripts/route_module_sources.py when modules are present")
    if AUDIT_RE.search(normalized):
        return entry_class("AuditLog", "change_context", "manual review or runner auditQuery context")
    if ALARM_RE.search(normalized):
        return entry_class("AlarmJournal", "alarm_history", "manual review or runner alarmJournalQuery context")
    if BROWSER_RE.search(normalized):
        return entry_class("PerspectiveBrowserConsole", "client_log", "manual review with source label")
    return entry_class("Unknown", "unknown", "manual classification required")


def entry_class(source_type, evidence_class, tool_hint):
    return {
        "sourceType": source_type,
        "evidenceClass": evidence_class,
        "toolHint": tool_hint,
    }


def sha256_stream(stream, max_bytes):
    digest = hashlib.sha256()
    read_total = 0
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        read_total += len(chunk)
        if read_total > max_bytes:
            return None, read_total, True
        digest.update(chunk)
    return digest.hexdigest().upper(), read_total, False


def inspect_zip(path, args):
    entries = []
    with zipfile.ZipFile(path, "r") as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        if len(infos) > args.max_entries:
            raise ValueError("entry count %d exceeds max_entries %d" % (len(infos), args.max_entries))
        for info in infos:
            classified = classify(info.filename)
            if not classified:
                continue
            entry = {
                "name": info.filename.replace("\\", "/"),
                "size": info.file_size,
                "compressedSize": info.compress_size,
                "modified": "%04d-%02d-%02dT%02d:%02d:%02d" % info.date_time,
                "container": "zip",
            }
            entry.update(classified)
            if args.hash_files:
                with zf.open(info, "r") as stream:
                    digest, read_total, skipped = sha256_stream(stream, args.max_hash_bytes)
                entry["sha256"] = digest
                entry["hashBytesRead"] = read_total
                entry["hashSkippedByMaxBytes"] = skipped
            entries.append(entry)
    return entries


def inspect_dir(path, args):
    all_files = [p for p in path.rglob("*") if p.is_file()]
    if len(all_files) > args.max_entries:
        raise ValueError("entry count %d exceeds max_entries %d" % (len(all_files), args.max_entries))
    entries = []
    for file_path in sorted(all_files):
        rel = file_path.relative_to(path).as_posix()
        classified = classify(rel)
        if not classified:
            continue
        stat = file_path.stat()
        entry = {
            "name": rel,
            "size": stat.st_size,
            "modifiedEpochMillis": int(stat.st_mtime * 1000),
            "container": "directory",
        }
        entry.update(classified)
        if args.hash_files:
            with file_path.open("rb") as stream:
                digest, read_total, skipped = sha256_stream(stream, args.max_hash_bytes)
            entry["sha256"] = digest
            entry["hashBytesRead"] = read_total
            entry["hashSkippedByMaxBytes"] = skipped
        entries.append(entry)
    return entries


def summarize(entries):
    by_type = {}
    by_class = {}
    for entry in entries:
        by_type[entry["sourceType"]] = by_type.get(entry["sourceType"], 0) + 1
        by_class[entry["evidenceClass"]] = by_class.get(entry["evidenceClass"], 0) + 1
    return {
        "bySourceType": dict(sorted(by_type.items())),
        "byEvidenceClass": dict(sorted(by_class.items())),
    }


def recommendations(entries):
    source_types = {entry["sourceType"] for entry in entries}
    steps = []
    if "GatewayInfoSnapshot" in source_types:
        steps.append("Use the Gateway info snapshot to record Ignition version, timezone, OS/Java, module states, and module versions; use route_module_sources.py only as a routing plan.")
    if "GatewayDiagnosticLogsIdb" in source_types:
        steps.append("Run query_gateway_idb.py against copied/exported system_logs*.idb files for level/logger/message/MDC filtering.")
    if "WrapperLog" in source_types:
        steps.append("Run query_wrapper_logs.py against wrapper.log files or their containing folder for wrapper severity/logger/time filtering.")
    if "PerspectiveBrowserConsole" in source_types:
        steps.append("Keep browser-console evidence source-labeled; treat it as client evidence, not Gateway diagnostic logs.")
    if "AuditLog" in source_types:
        steps.append("Keep audit evidence as change-attribution context, separate from diagnostic log rows.")
    if "AlarmJournal" in source_types:
        steps.append("Keep alarm journal evidence as process/alarm-history context, separate from diagnostic log rows.")
    if "ThreadDump" in source_types:
        steps.append("Compare multiple thread dumps by repeated thread name/state/top frame before calling a hang root cause.")
    if not ({"GatewayDiagnosticLogsIdb", "WrapperLog", "PerspectiveBrowserConsole"} & source_types):
        steps.append("No recognized diagnostic log source was found; request Gateway Diagnostic Logs, wrapper logs, or browser-console evidence before assigning root cause.")
    if "Unknown" in source_types:
        steps.append("Review unknown files manually before ignoring them; vendor bundles often use install-specific names.")
    return steps


def inspect_bundle(path, args):
    if not path.exists():
        return {
            "ok": False,
            "error": {"code": "PATH_NOT_FOUND", "message": "Input path does not exist: %s" % path},
        }
    if path.is_dir():
        input_kind = "directory"
        entries = inspect_dir(path, args)
    elif zipfile.is_zipfile(path):
        input_kind = "zip"
        entries = inspect_zip(path, args)
    else:
        return {
            "ok": False,
            "error": {"code": "UNSUPPORTED_INPUT", "message": "Input must be a directory or zip archive: %s" % path},
        }

    return {
        "ok": True,
        "inputPath": str(path),
        "inputKind": input_kind,
        "generatedAtEpochMillis": int(time.time() * 1000),
        "entryCount": len(entries),
        "entries": entries,
        "summary": summarize(entries),
        "recommendedNextSteps": recommendations(entries),
        "boundaries": [
            "This helper enumerates and classifies files only; it does not extract archives or parse log contents.",
            "Classification is filename-pattern based and must not be treated as confirmation of official Gateway UI bundle names or layouts.",
            "Run the source-specific helper or manual review before making root-cause, bug, fix, or compatibility claims.",
        ],
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Inspect an Ignition diagnostic/support archive or directory without extracting it.")
    parser.add_argument("path", help="Zip archive or directory to inspect.")
    parser.add_argument("--hash-files", action="store_true", help="Include SHA-256 for entries up to --max-hash-bytes.")
    parser.add_argument("--max-hash-bytes", type=int, default=64 * 1024 * 1024, help="Maximum bytes to hash per file before skipping the hash.")
    parser.add_argument("--max-entries", type=int, default=2000, help="Reject bundles with more than this many files.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        result = inspect_bundle(Path(args.path), args)
    except Exception as exc:
        result = {
            "ok": False,
            "error": {"code": exc.__class__.__name__, "message": str(exc)},
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
