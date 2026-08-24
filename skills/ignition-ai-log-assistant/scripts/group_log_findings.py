#!/usr/bin/env python3
"""Group source-labeled Ignition log rows into diagnostic findings."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


MAX_ROWS = 5000
MAX_RETURNED_ROWS = 200
ERROR_LEVELS = {"ERROR", "FATAL", "SEVERE"}
WARN_LEVELS = {"WARN", "WARNING"}
CONTEXT_SOURCE_RE = re.compile(r"(audit|alarm.?journal|thread.?dump|thread_state)", re.IGNORECASE)
CLIENT_SOURCE_RE = re.compile(r"(perspective|browser|client|designer|vision)", re.IGNORECASE)
EXCEPTION_RE = re.compile(
    r"\b((?:[A-Za-z_$][\w$]*\.)*[A-Za-z_$][\w$]*(?:Exception|Error))\b"
)
STACK_RE = re.compile(r"\bat\s+([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+)\([^)]*\)")
SECRET_PATTERNS = [
    (re.compile(r"(?i)(password|passwd|pwd|token|secret|authorization|cookie)=\S+"), r"\1=<redacted>"),
    (re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<redacted>"),
    (re.compile(r"jdbc:[^\s]+"), "jdbc:<redacted>"),
]


def fail(message):
    print(json.dumps({"ok": False, "error": message}, indent=2, sort_keys=True))
    return 2


def load_json(path):
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def extract_rows(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError("input JSON must be a row list or object containing rows")
    for key in ("rows", "entries", "events", "logs"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    datasets = data.get("datasets")
    if isinstance(datasets, dict):
        rows = []
        for source_name, values in sorted(datasets.items()):
            if isinstance(values, list):
                for row in values:
                    if isinstance(row, dict) and "source" not in row:
                        item = dict(row)
                        item["source"] = source_name
                        rows.append(item)
                    else:
                        rows.append(row)
        if rows:
            return rows
    raise ValueError("could not find rows, entries, events, logs, or datasets[] in input JSON")


def parse_time(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = int(value)
        return number if number > 9999999999 else number * 1000
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{10,}", text):
        number = int(text)
        return number if number > 9999999999 else number * 1000
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def ms_to_iso(epoch_millis):
    if epoch_millis is None:
        return None
    return datetime.fromtimestamp(int(epoch_millis) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def compact(value, limit=1200):
    text = str(value or "")
    for regex, replacement in SECRET_PATTERNS:
        text = regex.sub(replacement, text)
    return text[:limit]


def row_message(row):
    parts = [row.get("message"), row.get("formattedMessage"), row.get("raw")]
    exception = row.get("exception") or row.get("stackTrace")
    if exception:
        parts.append(exception)
    preview = row.get("exceptionPreview")
    if isinstance(preview, list):
        parts.extend(item.get("trace_line", item) if isinstance(item, dict) else item for item in preview)
    return "\n".join(str(part) for part in parts if part is not None)


def normalize_message(text):
    text = compact(text, 1200).lower()
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}[t ][0-9:.+-z]+\b", "<ts>", text)
    text = re.sub(r"\b\d{4}/\d{2}/\d{2} [0-9:]+\b", "<ts>", text)
    text = re.sub(r"\b[0-9a-f]{8}-[0-9a-f-]{27,36}\b", "<uuid>", text)
    text = re.sub(r"\b\d+\b", "<n>", text)
    text = re.sub(r"line\s+<n>", "line <n>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]


def exception_class(text):
    matches = EXCEPTION_RE.findall(text or "")
    if not matches:
        return ""
    return matches[0].split(".")[-1]


def first_stack_frame(text):
    match = STACK_RE.search(text or "")
    return match.group(1) if match else ""


def source_name(row):
    for key in ("source", "sourceType", "sourceLog", "sourceName", "evidenceSource"):
        if row.get(key):
            return str(row.get(key))
    if row.get("sourceFileName") or row.get("sourceFile"):
        return "WrapperLog"
    return "Unknown"


def level_name(row):
    for key in ("level", "level_string", "severity"):
        if row.get(key):
            return str(row.get(key)).upper()
    return "INFO"


def timestamp_ms(row):
    for key in ("timestampEpochMillis", "epochMillis", "timestmp", "timestampMillis"):
        if row.get(key) is not None:
            parsed = parse_time(row.get(key))
            if parsed is not None:
                return parsed
    for key in ("timestampIsoUtc", "timestamp", "time", "eventTime"):
        if row.get(key):
            parsed = parse_time(row.get(key))
            if parsed is not None:
                return parsed
    return None


def category_for(row, text, source):
    haystack = " ".join(
        [
            str(source or ""),
            str(row.get("logger") or row.get("loggerName") or ""),
            text or "",
        ]
    ).lower()
    if CONTEXT_SOURCE_RE.search(source or ""):
        if "audit" in haystack:
            return "audit context"
        if "alarm" in haystack or "journal" in haystack:
            return "alarm-history context"
        return "thread-state context"
    if "perspective" in haystack or "binding" in haystack or CLIENT_SOURCE_RE.search(source or ""):
        return "Perspective client/session"
    if "jython" in haystack or "pythontraceback" in haystack or "script" in haystack:
        return "script/Jython"
    if "namedquery" in haystack or "named query" in haystack or "runnamedquery" in haystack:
        return "database/Named Query"
    if "sql" in haystack or "jdbc" in haystack or "datasource" in haystack or "database" in haystack:
        return "database/Named Query"
    if "opc" in haystack or "device" in haystack or "tag" in haystack:
        return "tag/OPC/device"
    if "alarm" in haystack:
        return "alarm"
    if "auth" in haystack or "security" in haystack:
        return "auth/security"
    if "trial" in haystack or "license" in haystack:
        return "license/trial"
    if "runner" in haystack or "web dev" in haystack:
        return "runner/tooling"
    if "module" in haystack or "startup" in haystack:
        return "startup/module"
    return "unclassified diagnostic"


def is_context_source(source):
    return bool(CONTEXT_SOURCE_RE.search(source or ""))


def is_noise(level, text):
    if level in ERROR_LEVELS or level in WARN_LEVELS:
        return False
    suspicious = re.search(r"(exception|error|failed|timeout|traceback|sql|binding|gatewayexception)", text or "", re.IGNORECASE)
    return not suspicious


def root_rank(group):
    if group["contextOnly"]:
        return 999
    if group.get("followOnOf"):
        return 900
    category = group["category"]
    level = group["level"]
    if category == "database/Named Query" and level in ERROR_LEVELS:
        return 1
    if level in ERROR_LEVELS:
        return 10
    if category == "database/Named Query":
        return 20
    if level in WARN_LEVELS:
        return 40
    return 80


def confidence_for(group):
    if group.get("followOnOf"):
        return "medium"
    if group["level"] in ERROR_LEVELS and group["count"] > 1:
        return "high"
    if group["level"] in ERROR_LEVELS:
        return "medium"
    return "low"


def row_summary(row, index):
    text = compact(row_message(row), 800)
    epoch = timestamp_ms(row)
    return {
        "rowIndex": index,
        "timestampEpochMillis": epoch,
        "timestampIsoUtc": ms_to_iso(epoch),
        "source": source_name(row),
        "level": level_name(row),
        "logger": str(row.get("logger") or row.get("loggerName") or ""),
        "message": text.splitlines()[0] if text else "",
    }


def build_groups(rows, max_returned_rows):
    context_rows = []
    noise_rows = []
    groups_by_key = {}
    group_order = []
    normalized_rows = []

    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            noise_rows.append({"rowIndex": index, "reason": "non-object row"})
            continue
        source = source_name(raw)
        level = level_name(raw)
        text = row_message(raw)
        epoch = timestamp_ms(raw)
        category = category_for(raw, text, source)
        summary = row_summary(raw, index)
        if is_context_source(source):
            summary["category"] = category
            context_rows.append(summary)
            continue
        if is_noise(level, text):
            summary["reason"] = "non-warning informational row"
            noise_rows.append(summary)
            continue
        exc = exception_class(text)
        stack = first_stack_frame(text)
        logger = str(raw.get("logger") or raw.get("loggerName") or "").strip()
        message_shape = normalize_message(text)
        key = (
            source.lower(),
            category,
            level,
            logger.lower(),
            exc,
            stack,
            message_shape,
        )
        if key not in groups_by_key:
            group_id = "G%03d" % (len(group_order) + 1)
            groups_by_key[key] = {
                "groupId": group_id,
                "source": source,
                "category": category,
                "level": level,
                "logger": logger,
                "exceptionClass": exc,
                "firstStackFrame": stack,
                "messageShape": message_shape,
                "firstTimestampEpochMillis": epoch,
                "lastTimestampEpochMillis": epoch,
                "count": 0,
                "evidenceRows": [],
                "linkedFollowOns": [],
                "contextOnly": False,
            }
            group_order.append(key)
        group = groups_by_key[key]
        group["count"] += 1
        if epoch is not None:
            if group["firstTimestampEpochMillis"] is None or epoch < group["firstTimestampEpochMillis"]:
                group["firstTimestampEpochMillis"] = epoch
            if group["lastTimestampEpochMillis"] is None or epoch > group["lastTimestampEpochMillis"]:
                group["lastTimestampEpochMillis"] = epoch
        if len(group["evidenceRows"]) < max_returned_rows:
            group["evidenceRows"].append(summary)
        normalized_rows.append((group, text.lower()))

    groups = list(groups_by_key.values())
    link_follow_ons(groups, normalized_rows)
    for group in groups:
        group["firstTimestampIsoUtc"] = ms_to_iso(group["firstTimestampEpochMillis"])
        group["lastTimestampIsoUtc"] = ms_to_iso(group["lastTimestampEpochMillis"])
        group["rootCauseRank"] = root_rank(group)
        group["confidence"] = confidence_for(group)
    groups.sort(
        key=lambda item: (
            item["rootCauseRank"],
            item["firstTimestampEpochMillis"] if item["firstTimestampEpochMillis"] is not None else 10**20,
            item["groupId"],
        )
    )
    return groups, context_rows[:max_returned_rows], noise_rows[:max_returned_rows]


def link_follow_ons(groups, normalized_rows):
    root_candidates = [
        group
        for group in groups
        if group["category"] == "database/Named Query" and group["level"] in ERROR_LEVELS
    ]
    root_candidates.sort(key=lambda item: item["firstTimestampEpochMillis"] if item["firstTimestampEpochMillis"] is not None else 10**20)
    for group, lower_text in normalized_rows:
        if group["category"] not in {"Perspective client/session", "script/Jython", "unclassified diagnostic"}:
            continue
        if group.get("followOnOf"):
            continue
        group_ts = group["firstTimestampEpochMillis"]
        for root in root_candidates:
            root_ts = root["firstTimestampEpochMillis"]
            if group_ts is not None and root_ts is not None and group_ts < root_ts:
                continue
            shared_exception = root["exceptionClass"] and root["exceptionClass"].lower() in lower_text
            shared_query = ("runnamedquery" in lower_text or "named query" in lower_text) and root["category"] == "database/Named Query"
            shared_sql = "sql" in lower_text and root["exceptionClass"].lower().startswith("sql")
            if shared_exception or shared_query or shared_sql:
                group["followOnOf"] = root["groupId"]
                if group["groupId"] not in root["linkedFollowOns"]:
                    root["linkedFollowOns"].append(group["groupId"])
                break


def group_findings(args):
    data = load_json(args.input_json)
    rows = extract_rows(data)
    if len(rows) > MAX_ROWS:
        raise ValueError("row count %d exceeds safety cap %d" % (len(rows), MAX_ROWS))
    max_returned_rows = max(1, min(int(args.max_evidence_rows), MAX_RETURNED_ROWS))
    groups, context_rows, noise_rows = build_groups(rows, max_returned_rows)
    diagnostic_count = sum(group["count"] for group in groups)
    result = {
        "ok": True,
        "source": "IgnitionLogFindingGroups",
        "inputPath": str(Path(args.input_json)),
        "rowCount": len(rows),
        "diagnosticRowCount": diagnostic_count,
        "contextRowCount": len(context_rows),
        "noiseRowCount": len(noise_rows),
        "groupCount": len(groups),
        "groups": groups,
        "contextRows": context_rows,
        "noiseRows": noise_rows,
        "boundaries": [
            "This helper groups source-labeled rows deterministically; it is not a final diagnosis.",
            "Audit, alarm-journal, and thread-dump rows are retained as context, not diagnostic log groups.",
            "Follow-on links are heuristic and must be checked against timestamps and source evidence before a root-cause claim.",
        ],
    }
    return result


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", help="JSON list/object containing source-labeled log rows")
    parser.add_argument("--max-evidence-rows", type=int, default=5, help="Evidence rows retained per group/context/noise list")
    parser.add_argument("--json-out", help="Optional path to write JSON output. Stdout is always written.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = group_findings(args)
    except Exception as exc:
        return fail(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
