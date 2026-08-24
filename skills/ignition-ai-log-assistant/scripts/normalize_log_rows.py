#!/usr/bin/env python3
"""Normalize Ignition log helper outputs into source-labeled rows.

This helper bridges parser outputs such as query_gateway_idb.py and
query_wrapper_logs.py into the row shape expected by group_log_findings.py.
It preserves source labels and parser metadata, but does not diagnose.
"""

import argparse
import json
import re
import sys
from pathlib import Path


MAX_ROWS = 10000
SECRET_PATTERNS = [
    (re.compile(r"(?i)(password|passwd|pwd|token|secret|authorization|cookie)=\S+"), r"\1=<redacted>"),
    (re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<redacted>"),
    (re.compile(r"jdbc:[^\s]+"), "jdbc:<redacted>"),
]


def fail(message):
    print(json.dumps({"ok": False, "error": str(message)}, indent=2, sort_keys=True))
    return 2


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ValueError("could not read JSON %s: %s" % (path, exc))


def redact_text(value):
    if value is None:
        return value
    text = str(value)
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text[:1200]


def unwrap_payload(data):
    if isinstance(data, dict) and isinstance(data.get("parsed"), dict):
        return data["parsed"], "processWrapper.parsed"
    if isinstance(data, dict) and isinstance(data.get("stdout"), str):
        try:
            parsed = json.loads(data["stdout"])
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            return parsed, "processWrapper.stdout"
    return data, "direct"


def rows_from_payload(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError("payload must be a row list or JSON object")
    if data.get("ok") is False:
        raise ValueError("input helper output has ok=false: %s" % data.get("error"))
    for key in ("rows", "entries", "events", "logs"):
        if isinstance(data.get(key), list):
            return data[key]
    datasets = data.get("datasets")
    if isinstance(datasets, dict):
        rows = []
        for source_name, values in sorted(datasets.items()):
            if not isinstance(values, list):
                continue
            for row in values:
                if isinstance(row, dict) and "source" not in row:
                    item = dict(row)
                    item["source"] = source_name
                    rows.append(item)
                else:
                    rows.append(row)
        if rows:
            return rows
    raise ValueError("could not find rows, entries, events, logs, or datasets[]")


def source_file_map(payload):
    mapping = {}
    if not isinstance(payload, dict):
        return mapping
    for item in payload.get("sourceFiles") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if name:
            mapping[str(name)] = item
    return mapping


def timestamp_fields(row):
    timestamp = None
    epoch = None
    for key in ("timestampIsoUtc", "timestamp", "time", "eventTime"):
        if row.get(key):
            timestamp = row.get(key)
            break
    for key in ("timestampEpochMillis", "epochMillis", "timestmp", "timestampMillis"):
        if row.get(key) is not None:
            epoch = row.get(key)
            break
    return timestamp, epoch


def normalize_row(row, source, path, index, file_map):
    if not isinstance(row, dict):
        return None
    item = dict(row)
    item["source"] = str(item.get("source") or source or "Unknown")
    item["inputPath"] = str(path)
    item["inputRowIndex"] = index

    timestamp, epoch = timestamp_fields(item)
    if timestamp is not None:
        item["timestampIsoUtc"] = timestamp
    if epoch is not None:
        item["timestampEpochMillis"] = epoch

    if item["source"] == "GatewayDiagnosticLogsIDB":
        if item.get("logger_name") and not item.get("logger"):
            item["logger"] = item.get("logger_name")
        if item.get("level_string") and not item.get("level"):
            item["level"] = item.get("level_string")
        if item.get("formatted_message") and not item.get("message"):
            item["message"] = item.get("formatted_message")

    if item["source"] == "WrapperLog":
        if item.get("sourceFile") and not item.get("sourceFileName"):
            item["sourceFileName"] = item.get("sourceFile")
        if item.get("sourceFileName") in file_map:
            meta = file_map[item.get("sourceFileName")]
            if meta.get("path") and not item.get("sourcePath"):
                item["sourcePath"] = meta.get("path")
            if meta.get("rotationIndex") is not None and item.get("rotationIndex") is None:
                item["rotationIndex"] = meta.get("rotationIndex")
        if item.get("primary") is False and not item.get("logger"):
            item["logger"] = "<non-primary wrapper>"

    for key in ("message", "raw", "formattedMessage", "exception", "stackTrace"):
        if key in item:
            item[key] = redact_text(item[key])
    preview = item.get("exceptionPreview")
    if isinstance(preview, list):
        clean = []
        for value in preview:
            if isinstance(value, dict):
                sub = dict(value)
                if "trace_line" in sub:
                    sub["trace_line"] = redact_text(sub["trace_line"])
                clean.append(sub)
            else:
                clean.append(redact_text(value))
        item["exceptionPreview"] = clean
    return item


def normalize(paths):
    all_rows = []
    inputs = []
    for raw_path in paths:
        path = Path(raw_path)
        data = load_json(path)
        payload, mode = unwrap_payload(data)
        source = payload.get("source") if isinstance(payload, dict) else "Unknown"
        rows = rows_from_payload(payload)
        files = source_file_map(payload)
        before = len(all_rows)
        for index, row in enumerate(rows):
            item = normalize_row(row, source, path, index, files)
            if item is not None:
                all_rows.append(item)
            if len(all_rows) > MAX_ROWS:
                raise ValueError("normalized row count exceeds safety cap %d" % MAX_ROWS)
        inputs.append(
            {
                "path": str(path),
                "unwrapMode": mode,
                "source": source or "Unknown",
                "inputRowCount": len(rows),
                "normalizedRowCount": len(all_rows) - before,
            }
        )
    return {
        "ok": True,
        "source": "IgnitionNormalizedLogRows",
        "inputCount": len(inputs),
        "rowCount": len(all_rows),
        "inputs": inputs,
        "rows": all_rows,
        "boundaries": [
            "This helper normalizes supplied helper outputs into source-labeled rows; it does not fetch logs or diagnose.",
            "Source labels and parser metadata are preserved so group_log_findings.py can classify rows without merging evidence classes.",
            "Only common secret-like message fields are redacted; human review is still required before sharing externally.",
        ],
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", nargs="+", help="Parser/helper JSON output files or source-labeled row lists.")
    parser.add_argument("--json-out", help="Optional output path. Stdout is always written.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = normalize(args.input_json)
    except Exception as exc:
        return fail(exc)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
