#!/usr/bin/env python3
"""Read-only query helper for copied/exported Ignition Gateway Diagnostic Logs IDBs."""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_EVENT_COLUMNS = {
    "event_id",
    "timestmp",
    "level_string",
    "logger_name",
    "thread_name",
    "formatted_message",
}
OPTIONAL_TABLES = ("logging_event_exception", "logging_event_property", "logging_sys_info")
MAX_LIMIT = 500


def fail(message):
    print(json.dumps({"ok": False, "error": message}, indent=2, sort_keys=True))
    return 2


def sqlite_ro(path):
    uri_path = str(path.resolve()).replace("\\", "/")
    con = sqlite3.connect("file:%s?mode=ro" % uri_path, uri=True)
    con.execute("pragma query_only=ON")
    return con


def table_exists(con, table):
    row = con.execute(
        "select name from sqlite_master where type='table' and name=?",
        [table],
    ).fetchone()
    return row is not None


def table_columns(con, table):
    return [row[1] for row in con.execute('pragma table_info("%s")' % table).fetchall()]


def table_count(con, table):
    if not table_exists(con, table):
        return None
    return con.execute('select count(*) from "%s"' % table).fetchone()[0]


def parse_time(value):
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


def parse_key_value(items, arg_name):
    pairs = []
    for item in items or []:
        if "=" not in item:
            raise ValueError("%s requires KEY=VALUE, got %r" % (arg_name, item))
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("%s requires a non-empty key, got %r" % (arg_name, item))
        pairs.append((key, value))
    return pairs


def inspect_schema(con):
    tables = {}
    for table in ("logging_event",) + OPTIONAL_TABLES:
        exists = table_exists(con, table)
        tables[table] = {
            "exists": exists,
            "columns": table_columns(con, table) if exists else [],
            "rowCount": table_count(con, table) if exists else None,
        }
    bounds = {}
    if tables["logging_event"]["exists"]:
        row = con.execute("select min(timestmp), max(timestmp) from logging_event").fetchone()
        bounds = {
            "minEpochMillis": row[0],
            "minIsoUtc": ms_to_iso(row[0]),
            "maxEpochMillis": row[1],
            "maxIsoUtc": ms_to_iso(row[1]),
        }
    return {"tables": tables, "bounds": bounds}


def build_where(args, has_property_table):
    clauses = []
    params = []
    since_ms = parse_time(args.since)
    until_ms = parse_time(args.until)
    if since_ms is not None:
        clauses.append("timestmp >= ?")
        params.append(since_ms)
    if until_ms is not None:
        clauses.append("timestmp <= ?")
        params.append(until_ms)
    if args.level:
        levels = [item.upper() for item in args.level]
        clauses.append("upper(level_string) in (%s)" % ",".join(["?"] * len(levels)))
        params.extend(levels)
    if args.logger_contains:
        clauses.append("logger_name like ?")
        params.append("%" + args.logger_contains + "%")
    if args.thread_contains:
        clauses.append("thread_name like ?")
        params.append("%" + args.thread_contains + "%")
    if args.message_contains:
        clauses.append("formatted_message like ?")
        params.append("%" + args.message_contains + "%")
    property_equals = parse_key_value(args.property, "--property")
    property_contains = parse_key_value(args.property_contains, "--property-contains")
    if (property_equals or property_contains) and not has_property_table:
        raise ValueError("MDC/property filters were requested but logging_event_property is absent")
    for key, value in property_equals:
        clauses.append(
            "exists (select 1 from logging_event_property p "
            "where p.event_id = logging_event.event_id and p.mapped_key = ? and p.mapped_value = ?)"
        )
        params.extend([key, value])
    for key, value in property_contains:
        clauses.append(
            "exists (select 1 from logging_event_property p "
            "where p.event_id = logging_event.event_id and p.mapped_key = ? and p.mapped_value like ?)"
        )
        params.extend([key, "%" + value + "%"])
    return clauses or ["1 = 1"], params


def fetch_related(con, event_ids, table, columns, order_column):
    if not event_ids or not table_exists(con, table):
        return {}
    placeholders = ",".join(["?"] * len(event_ids))
    sql = "select %s from %s where event_id in (%s) order by event_id, %s" % (
        ", ".join(columns),
        table,
        placeholders,
        order_column,
    )
    related = {}
    for row in con.execute(sql, event_ids).fetchall():
        event_id = row[0]
        related.setdefault(event_id, []).append(dict(zip(columns, row)))
    return related


def query_idb(args):
    path = Path(args.idb)
    if not path.exists():
        raise ValueError("IDB path does not exist: %s" % path)
    if not path.is_file():
        raise ValueError("IDB path is not a file: %s" % path)
    limit = max(1, min(int(args.limit), MAX_LIMIT))
    with sqlite_ro(path) as con:
        schema = inspect_schema(con)
        if not schema["tables"]["logging_event"]["exists"]:
            raise ValueError("logging_event table missing")
        event_columns = set(schema["tables"]["logging_event"]["columns"])
        missing = sorted(REQUIRED_EVENT_COLUMNS - event_columns)
        if missing:
            raise ValueError("logging_event missing required columns: %s" % ", ".join(missing))
        has_property_table = schema["tables"]["logging_event_property"]["exists"]
        where_clauses, params = build_where(args, has_property_table)
        where_sql = " and ".join("(%s)" % clause for clause in where_clauses)
        count_sql = "select count(*) from logging_event where %s" % where_sql
        matched_count = con.execute(count_sql, params).fetchone()[0]
        rows = con.execute(
            """
            select event_id, timestmp, level_string, logger_name, thread_name, formatted_message, marker
            from logging_event
            where %s
            order by timestmp asc, event_id asc
            limit ?
            """ % where_sql,
            params + [limit],
        ).fetchall()
        event_ids = [row[0] for row in rows]
        properties = {}
        if has_property_table and event_ids:
            property_rows = fetch_related(
                con,
                event_ids,
                "logging_event_property",
                ["event_id", "mapped_key", "mapped_value"],
                "mapped_key",
            )
            for event_id, items in property_rows.items():
                properties[event_id] = {item["mapped_key"]: item["mapped_value"] for item in items}
        exceptions = fetch_related(
            con,
            event_ids,
            "logging_event_exception",
            ["event_id", "i", "trace_line"],
            "i",
        )
    result_rows = []
    for row in rows:
        event_id = row[0]
        message = row[5] if args.no_redact else sanitize_message(row[5])
        result_rows.append(
            {
                "eventId": event_id,
                "timestampEpochMillis": row[1],
                "timestampIsoUtc": ms_to_iso(row[1]),
                "level": row[2],
                "logger": row[3],
                "thread": row[4],
                "message": message,
                "marker": row[6],
                "properties": properties.get(event_id, {}),
                "exceptionPreview": exceptions.get(event_id, [])[: int(args.exception_lines)],
            }
        )
    return {
        "ok": True,
        "source": "GatewayDiagnosticLogsIDB",
        "idbPath": str(path),
        "schema": schema,
        "query": {
            "since": args.since,
            "until": args.until,
            "levels": args.level or [],
            "loggerContains": args.logger_contains,
            "threadContains": args.thread_contains,
            "messageContains": args.message_contains,
            "property": args.property or [],
            "propertyContains": args.property_contains or [],
            "limit": limit,
            "maxLimit": MAX_LIMIT,
            "redacted": not args.no_redact,
        },
        "matchedCount": matched_count,
        "returnedCount": len(result_rows),
        "capped": matched_count > len(result_rows),
        "rows": result_rows,
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("idb", help="Copied/exported system_logs*.idb path. Do not point this at a live file.")
    parser.add_argument("--since", help="Inclusive ISO-8601 timestamp or epoch milliseconds.")
    parser.add_argument("--until", help="Inclusive ISO-8601 timestamp or epoch milliseconds.")
    parser.add_argument("--level", action="append", help="Level filter. May be repeated, for example --level ERROR --level WARN.")
    parser.add_argument("--logger-contains", help="Case-sensitive logger substring filter.")
    parser.add_argument("--thread-contains", help="Case-sensitive thread substring filter.")
    parser.add_argument("--message-contains", help="Case-sensitive message substring filter.")
    parser.add_argument("--property", action="append", help="MDC/context exact filter as KEY=VALUE. May be repeated.")
    parser.add_argument("--property-contains", action="append", help="MDC/context substring filter as KEY=VALUE. May be repeated.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum rows to return, capped at 500.")
    parser.add_argument("--exception-lines", type=int, default=5, help="Exception preview lines per selected event.")
    parser.add_argument("--no-redact", action="store_true", help="Return messages without built-in redaction.")
    parser.add_argument("--json-out", help="Optional path to write JSON output. Stdout is always written.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = query_idb(args)
    except Exception as exc:
        return fail(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
