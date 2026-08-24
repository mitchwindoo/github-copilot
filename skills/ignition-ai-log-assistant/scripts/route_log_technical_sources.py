#!/usr/bin/env python3
"""Route Ignition log evidence to official technical source references.

This helper suggests reading sources for interpreting supplied grouped findings
or source-labeled rows. It does not fetch web pages, diagnose root cause, or
make version-specific bug/fix claims.
"""

import argparse
import json
import re
import sys
from pathlib import Path


MAX_ITEMS = 2000

SOURCES = {
    "gateway-diagnostics-logs": {
        "title": "Gateway Diagnostics Logs",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/gateway/status/diagnostics-logs",
        "useFor": "Gateway-side log location, UI filters, and Gateway event scope.",
    },
    "wrapper-logs": {
        "title": "Wrapper Logs",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/gateway/status/diagnostics-logs/wrapper-logs",
        "useFor": "Wrapper file location and wrapper-vs-Gateway log evidence.",
    },
    "logback-wrapper-reference": {
        "title": "Logback XML File Reference",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/logback-xml-file-reference",
        "useFor": "Wrapper/logback output structure and rotation context.",
    },
    "script-logging-output": {
        "title": "Script Logging and Print Statement Output",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/scripting/scripting-in-ignition/script-logging-print-statement-output",
        "useFor": "Where script logger and print output appears by scope.",
    },
    "system-util-getLogger": {
        "title": "system.util.getLogger",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-util/system-util-getLogger",
        "useFor": "Logger creation, log levels, and script log stream expectations.",
    },
    "system-util-setLoggingLevel": {
        "title": "system.util.setLoggingLevel",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-util/system-util-setLoggingLevel",
        "useFor": "Temporary logger-level change mechanics and limits.",
    },
    "named-queries": {
        "title": "Named Queries",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/sql-in-ignition/named-queries",
        "useFor": "Named Query definition and caller relationships.",
    },
    "named-query-parameters": {
        "title": "Named Query Parameters",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/sql-in-ignition/named-queries/named-query-parameters",
        "useFor": "Parameter binding and caller-supplied values.",
    },
    "perspective-query-bindings": {
        "title": "Perspective Query Bindings",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/query-bindings-in-perspective",
        "useFor": "Perspective query-binding and Named Query binding behavior.",
    },
    "database-connections": {
        "title": "Database Connections",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/database-connections",
        "useFor": "Datasource dependency scope and connection status context.",
    },
    "quality-codes": {
        "title": "Quality Codes and Overlays",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/quality-codes-and-overlays",
        "useFor": "Good/Bad/Error/Uncertain tag quality interpretation.",
    },
    "tag-event-scripts": {
        "title": "Tag Event Scripts",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/tag-event-scripts",
        "useFor": "Tag-event execution scope and logging behavior.",
    },
    "opc-connections": {
        "title": "OPC Connections",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/gateway/status/connections/connections-opc-connections",
        "useFor": "OPC connection status and diagnostics context.",
    },
    "device-status": {
        "title": "Connections - Devices",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/gateway/status/connections/connections-devices",
        "useFor": "Device connection state and request-load context.",
    },
    "alarm-journal": {
        "title": "Alarm Journal",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/alarming/alarm-journal",
        "useFor": "Historical alarm source/time/property context.",
    },
    "configuring-alarms": {
        "title": "Configuring Alarms",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/alarming/configuring-alarms",
        "useFor": "Alarm configuration, bindings, and property context.",
    },
    "audit-log-and-profiles": {
        "title": "Audit Log and Profiles",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/audit-log-and-profiles",
        "useFor": "Audit profile and change-attribution context.",
    },
    "audit-log-display": {
        "title": "Audit Log Displays",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/audit-log-and-profiles/audit-log-display",
        "useFor": "Audit display/query workflow context.",
    },
    "system-util-threadDump": {
        "title": "system.util.threadDump",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-util/system-util-threadDump",
        "useFor": "Thread dump collection scope and return shape.",
    },
    "gateway-status-systems": {
        "title": "Gateway Status Systems",
        "url": "https://www.docs.inductiveautomation.com/docs/8.1/platform/gateway/status/systems",
        "useFor": "Gateway task/system status and slow response context.",
    },
}


def fail(message):
    print(json.dumps({"ok": False, "error": str(message)}, indent=2, sort_keys=True))
    return 2


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ValueError("could not read JSON %s: %s" % (path, exc))


def extract_items(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object or list")
    if isinstance(data.get("groups"), list):
        return data["groups"]
    if isinstance(data.get("topFindings"), list):
        return data["topFindings"]
    for key in ("rows", "events", "entries", "logs"):
        if isinstance(data.get(key), list):
            return data[key]
    raise ValueError("could not find groups, topFindings, rows, events, entries, or logs")


def item_text(item):
    parts = []
    for key in (
        "source",
        "sourceType",
        "category",
        "level",
        "logger",
        "loggerName",
        "message",
        "formatted_message",
        "exceptionClass",
        "firstStackFrame",
    ):
        value = item.get(key) if isinstance(item, dict) else None
        if value:
            parts.append(str(value))
    if isinstance(item, dict):
        for row in item.get("evidenceRows") or []:
            if isinstance(row, dict):
                parts.extend(str(row.get(key) or "") for key in ("source", "logger", "message"))
    return " ".join(parts).lower()


def add(routes, source_id, row_index, item, reason):
    route = routes.setdefault(
        source_id,
        {
            "id": source_id,
            "title": SOURCES[source_id]["title"],
            "url": SOURCES[source_id]["url"],
            "useFor": SOURCES[source_id]["useFor"],
            "reasons": [],
            "matchedItems": [],
        },
    )
    if reason not in route["reasons"]:
        route["reasons"].append(reason)
    route["matchedItems"].append(
        {
            "rowIndex": row_index,
            "groupId": item.get("groupId") or item.get("id"),
            "source": item.get("source") or item.get("sourceType"),
            "category": item.get("category"),
            "logger": item.get("logger") or item.get("loggerName"),
        }
    )


def route_item(routes, row_index, item):
    text = item_text(item)
    if not text:
        return

    if "gatewaydiagnosticlogsidb" in text or "gateway diagnostic" in text:
        add(routes, "gateway-diagnostics-logs", row_index, item, "Gateway diagnostic log evidence")
    if "wrapperlog" in text or "wrapper" in text:
        add(routes, "wrapper-logs", row_index, item, "Wrapper log evidence")
        add(routes, "logback-wrapper-reference", row_index, item, "Wrapper/logback structure may matter")
    if re.search(r"(script|jython|pythontraceback|projectscript|tagevent|tag event)", text):
        add(routes, "script-logging-output", row_index, item, "Script logging or print-output context")
        add(routes, "system-util-getLogger", row_index, item, "Script logger behavior may matter")
    if re.search(r"(debug|trace|setlogginglevel|logging level|logger level)", text):
        add(routes, "system-util-setLoggingLevel", row_index, item, "Logger-level mechanics may matter")
    if re.search(r"(named query|namedquery|runnamedquery)", text):
        add(routes, "named-queries", row_index, item, "Named Query execution/caller context")
        add(routes, "named-query-parameters", row_index, item, "Named Query parameter context may matter")
    if re.search(r"(perspective|binding|session)", text):
        add(routes, "perspective-query-bindings", row_index, item, "Perspective binding/session context")
    if re.search(r"(sql|jdbc|datasource|database|connection pool)", text):
        add(routes, "database-connections", row_index, item, "Database connection or datasource context")
    if re.search(r"(tagmanager|tag/|tag path|bad_stale|bad stale|quality|opc|device)", text):
        add(routes, "quality-codes", row_index, item, "Tag quality interpretation may matter")
    if re.search(r"(tag event|tagevent|tag change)", text):
        add(routes, "tag-event-scripts", row_index, item, "Tag event script scope/logging may matter")
    if re.search(r"(opc|ua server|subscription)", text):
        add(routes, "opc-connections", row_index, item, "OPC connection status may matter")
    if re.search(r"(device|driver|overload)", text):
        add(routes, "device-status", row_index, item, "Device connection status may matter")
    if re.search(r"(alarm|journal|pipeline)", text):
        add(routes, "alarm-journal", row_index, item, "Alarm history/journal context")
        add(routes, "configuring-alarms", row_index, item, "Alarm configuration/property context")
    if "audit" in text:
        add(routes, "audit-log-and-profiles", row_index, item, "Audit profile/change context")
        add(routes, "audit-log-display", row_index, item, "Audit display/query context")
    if re.search(r"(thread.?dump|threadstate|deadlock|blocked|waiting|high cpu|slow response)", text):
        add(routes, "system-util-threadDump", row_index, item, "Thread dump collection/shape context")
        add(routes, "gateway-status-systems", row_index, item, "Gateway system/task status context")


def route_sources(path):
    data = load_json(path)
    items = extract_items(data)
    if len(items) > MAX_ITEMS:
        raise ValueError("item count %d exceeds safety cap %d" % (len(items), MAX_ITEMS))
    routes = {}
    for index, item in enumerate(items):
        if isinstance(item, dict):
            route_item(routes, index, item)
    ordered = sorted(routes.values(), key=lambda route: (-len(route["matchedItems"]), route["id"]))
    return {
        "ok": True,
        "source": "IgnitionLogTechnicalSourceRoutes",
        "inputPath": str(Path(path)),
        "itemCount": len(items),
        "routeCount": len(ordered),
        "routes": ordered,
        "boundaries": [
            "This helper routes supplied log evidence to technical reading sources; it does not fetch web pages.",
            "Use these sources to interpret log categories and evidence locations, not to prove root cause.",
            "Browse current official/vendor release sources separately before making version-specific bug, fix, latest-version, or compatibility claims.",
        ],
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", help="Grouped findings, diagnostic brief, or source-labeled row JSON.")
    parser.add_argument("--json-out", help="Optional output path. Stdout is always written.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = route_sources(args.input_json)
    except Exception as exc:
        return fail(exc)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
