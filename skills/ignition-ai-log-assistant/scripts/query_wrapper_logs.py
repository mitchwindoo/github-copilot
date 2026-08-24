#!/usr/bin/env python3
"""Read-only query helper for local/exported Ignition wrapper logs."""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


WRAPPER_RE = re.compile(
    r"^(?P<wrapper_level>[A-Z]+)\s+\|\s+(?P<stream>[^|]+?)\s+\|\s+"
    r"(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+\|\s?(?P<body>.*)$"
)
EMBEDDED_RE = re.compile(
    r"^(?P<letter>[A-Z])\s+\[(?P<logger>[^\]]+)\]\s+\[[^\]]+\]:\s?(?P<message>.*)$"
)
LEVEL_MAP = {
    "T": "TRACE",
    "D": "DEBUG",
    "I": "INFO",
    "W": "WARN",
    "E": "ERROR",
    "F": "FATAL",
}
MAX_LIMIT = 1000
DEFAULT_MAX_BYTES_PER_FILE = 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 8 * 1024 * 1024


def fail(message):
    print(json.dumps({"ok": False, "error": message}, indent=2, sort_keys=True))
    return 2


def parse_tz(value):
    text = str(value or "").strip()
    if not text or text.lower() == "local":
        offset = datetime.now().astimezone().utcoffset() or timedelta(0)
        return timezone(offset)
    if text.upper() == "UTC" or text == "Z":
        return timezone.utc
    match = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", text)
    if not match:
        raise ValueError("--timezone-offset must be local, UTC, Z, or +/-HH:MM")
    sign = 1 if match.group(1) == "+" else -1
    hours = int(match.group(2))
    minutes = int(match.group(3))
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def offset_label(tzinfo):
    offset = tzinfo.utcoffset(None)
    if offset is None:
        return "local"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    return "%s%02d:%02d" % (sign, total_minutes // 60, total_minutes % 60)


def parse_time_filter(value):
    if value is None:
        return None
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
        raise ValueError("invalid timestamp %r; use ISO-8601 or epoch milliseconds" % value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def wrapper_timestamp_to_ms(text, tzinfo):
    parsed = datetime.strptime(text, "%Y/%m/%d %H:%M:%S").replace(tzinfo=tzinfo)
    return int(parsed.timestamp() * 1000)


def ms_to_iso(epoch_millis):
    if epoch_millis is None:
        return None
    return datetime.fromtimestamp(int(epoch_millis) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def sanitize_message(message):
    text = str(message or "")
    text = re.sub(r"(?i)(password|passwd|pwd|token|secret|authorization|cookie)=\S+", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1<redacted>", text)
    text = re.sub(r"jdbc:[^\s]+", "jdbc:<redacted>", text)
    return text[:1200]


def rotation_index(path):
    name = path.name
    if name == "wrapper.log":
        return 0
    match = re.fullmatch(r"wrapper\.log\.(\d+)", name)
    if match:
        return int(match.group(1))
    return None


def discover_paths(paths, include_rotated, max_log_files):
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            candidates = [path / "wrapper.log"]
            if include_rotated:
                candidates.extend(path.glob("wrapper.log.*"))
            found.extend(c for c in candidates if c.is_file() and rotation_index(c) is not None)
        elif path.is_file():
            found.append(path)
            if include_rotated and path.name == "wrapper.log":
                found.extend(c for c in path.parent.glob("wrapper.log.*") if c.is_file() and rotation_index(c) is not None)
        else:
            raise ValueError("path does not exist or is not readable: %s" % path)
    unique = {}
    for path in found:
        unique[str(path.resolve())] = path.resolve()
    ordered = sorted(unique.values(), key=lambda p: rotation_index(p) if rotation_index(p) is not None else 9999)
    return ordered[: max(1, int(max_log_files))]


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tail(path, max_bytes):
    size = path.stat().st_size
    read_size = min(size, max(1, int(max_bytes)))
    with path.open("rb") as handle:
        handle.seek(size - read_size)
        data = handle.read(read_size)
    if read_size < size:
        first_newline = data.find(b"\n")
        if first_newline >= 0:
            data = data[first_newline + 1 :]
    return data.decode("utf-8", errors="replace"), read_size, read_size < size, size


def parse_line(path, line_number, line, tzinfo, no_redact):
    match = WRAPPER_RE.match(line.rstrip("\r\n"))
    if not match:
        return {
            "sourceFile": path.name,
            "lineNumber": line_number,
            "parsed": False,
            "primary": False,
            "raw": sanitize_message(line.rstrip("\r\n")) if not no_redact else line.rstrip("\r\n"),
        }
    body = match.group("body")
    embedded = EMBEDDED_RE.match(body)
    timestamp = match.group("timestamp")
    epoch_millis = wrapper_timestamp_to_ms(timestamp, tzinfo)
    row = {
        "sourceFile": path.name,
        "lineNumber": line_number,
        "parsed": True,
        "timestamp": timestamp,
        "timestampIsoUtc": ms_to_iso(epoch_millis),
        "epochMillis": epoch_millis,
        "wrapperLevel": match.group("wrapper_level"),
        "wrapperStream": match.group("stream").strip(),
        "primary": embedded is not None,
    }
    if embedded:
        letter = embedded.group("letter")
        row["level"] = LEVEL_MAP.get(letter, letter)
        row["logger"] = embedded.group("logger").strip()
        row["message"] = embedded.group("message").strip()
    else:
        row["level"] = match.group("wrapper_level")
        row["logger"] = None
        row["message"] = body.strip()
    if not no_redact:
        row["message"] = sanitize_message(row["message"])
    return row


def matches_filters(row, args, since_ms, until_ms):
    if not row.get("parsed"):
        return False
    if since_ms is not None and row.get("epochMillis", -1) < since_ms:
        return False
    if until_ms is not None and row.get("epochMillis", 10**20) > until_ms:
        return False
    if args.level and str(row.get("level", "")).upper() not in {item.upper() for item in args.level}:
        return False
    if args.wrapper_level and str(row.get("wrapperLevel", "")).upper() not in {item.upper() for item in args.wrapper_level}:
        return False
    if args.primary_only and not row.get("primary"):
        return False
    if not args.include_non_primary and not row.get("primary"):
        return False
    if args.logger_contains and args.logger_contains not in str(row.get("logger") or ""):
        return False
    text = "%s %s %s" % (row.get("logger") or "", row.get("message") or "", row.get("sourceFile") or "")
    if args.message_contains and args.message_contains not in str(row.get("message") or ""):
        return False
    if args.text_contains and args.text_contains not in text:
        return False
    if args.source_file_contains and args.source_file_contains not in str(row.get("sourceFile") or ""):
        return False
    return True


def query_wrapper_logs(args):
    tzinfo = parse_tz(args.timezone_offset)
    paths = discover_paths(args.paths, args.include_rotated, args.max_log_files)
    if not paths:
        raise ValueError("no wrapper log files found")
    if sum(min(p.stat().st_size, args.max_bytes_per_file) for p in paths) > args.max_total_bytes:
        raise ValueError("requested tail bytes exceed --max-total-bytes; reduce --max-log-files or --max-bytes-per-file")
    since_ms = parse_time_filter(args.since)
    until_ms = parse_time_filter(args.until)
    limit = max(1, min(int(args.limit), MAX_LIMIT))
    source_files = []
    matched_rows = []
    matched_count = 0
    level_counts = {}
    logger_counts = {}
    for path in paths:
        text, read_bytes, truncated, source_bytes = read_tail(path, args.max_bytes_per_file)
        source_info = {
            "name": path.name,
            "path": str(path),
            "rotationIndex": rotation_index(path),
            "sourceBytes": source_bytes,
            "readBytes": read_bytes,
            "tailWindowTruncated": truncated,
            "sha256": sha256_file(path) if args.hash_files else None,
            "lineScanCount": 0,
            "parsedLineCount": 0,
            "primaryLineCount": 0,
            "matchedCountBeforeCap": 0,
            "firstEpochMillis": None,
            "firstIsoUtc": None,
            "lastEpochMillis": None,
            "lastIsoUtc": None,
        }
        for index, line in enumerate(text.splitlines(), start=1):
            source_info["lineScanCount"] += 1
            row = parse_line(path, index, line, tzinfo, args.no_redact)
            if row.get("parsed"):
                source_info["parsedLineCount"] += 1
                epoch = row.get("epochMillis")
                if source_info["firstEpochMillis"] is None or epoch < source_info["firstEpochMillis"]:
                    source_info["firstEpochMillis"] = epoch
                    source_info["firstIsoUtc"] = row.get("timestampIsoUtc")
                if source_info["lastEpochMillis"] is None or epoch > source_info["lastEpochMillis"]:
                    source_info["lastEpochMillis"] = epoch
                    source_info["lastIsoUtc"] = row.get("timestampIsoUtc")
            if row.get("primary"):
                source_info["primaryLineCount"] += 1
            if matches_filters(row, args, since_ms, until_ms):
                matched_count += 1
                source_info["matchedCountBeforeCap"] += 1
                level = row.get("level") or "<none>"
                logger = row.get("logger") or "<non-primary>"
                level_counts[level] = level_counts.get(level, 0) + 1
                logger_counts[logger] = logger_counts.get(logger, 0) + 1
                matched_rows.append(row)
        source_files.append(source_info)
    matched_rows.sort(key=lambda item: (item.get("epochMillis") or 0, item.get("sourceFile") or "", item.get("lineNumber") or 0))
    rows = matched_rows[:limit]
    return {
        "ok": True,
        "source": "WrapperLog",
        "timezoneOffsetUsed": offset_label(tzinfo),
        "query": {
            "paths": [str(Path(p)) for p in args.paths],
            "includeRotated": args.include_rotated,
            "maxLogFiles": args.max_log_files,
            "maxBytesPerFile": args.max_bytes_per_file,
            "maxTotalBytes": args.max_total_bytes,
            "since": args.since,
            "until": args.until,
            "levels": args.level or [],
            "wrapperLevels": args.wrapper_level or [],
            "loggerContains": args.logger_contains,
            "messageContains": args.message_contains,
            "textContains": args.text_contains,
            "sourceFileContains": args.source_file_contains,
            "includeNonPrimary": args.include_non_primary,
            "primaryOnly": args.primary_only,
            "limit": limit,
            "redacted": not args.no_redact,
        },
        "sourceFiles": source_files,
        "lineScanCount": sum(item["lineScanCount"] for item in source_files),
        "parsedLineCount": sum(item["parsedLineCount"] for item in source_files),
        "primaryLineCount": sum(item["primaryLineCount"] for item in source_files),
        "matchedCountBeforeCap": matched_count,
        "returnedCount": len(rows),
        "truncated": matched_count > len(rows),
        "levelCounts": dict(sorted(level_counts.items())),
        "topLoggers": sorted(logger_counts.items(), key=lambda item: (-item[1], item[0]))[:20],
        "rows": rows,
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="wrapper.log file(s) or directories containing wrapper.log files")
    parser.add_argument("--include-rotated", action="store_true", help="include numeric wrapper.log.N siblings")
    parser.add_argument("--max-log-files", type=int, default=6, help="maximum discovered wrapper files")
    parser.add_argument("--max-bytes-per-file", type=int, default=DEFAULT_MAX_BYTES_PER_FILE)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    parser.add_argument("--timezone-offset", default="local", help="local, UTC, Z, or +/-HH:MM for wrapper timestamps")
    parser.add_argument("--since", help="ISO-8601 or epoch milliseconds")
    parser.add_argument("--until", help="ISO-8601 or epoch milliseconds")
    parser.add_argument("--level", action="append", help="embedded Ignition level, repeatable")
    parser.add_argument("--wrapper-level", action="append", help="outer wrapper level, repeatable")
    parser.add_argument("--logger-contains")
    parser.add_argument("--message-contains")
    parser.add_argument("--text-contains")
    parser.add_argument("--source-file-contains")
    parser.add_argument("--include-non-primary", action="store_true")
    parser.add_argument("--primary-only", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--no-redact", action="store_true")
    parser.add_argument("--hash-files", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = query_wrapper_logs(args)
    except Exception as exc:
        return fail(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
