#!/usr/bin/env python3
"""Build a source-specific Ignition log evidence request from incident metadata."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


MAX_INPUT_BYTES = 512 * 1024

SECRET_PATTERNS = [
    (re.compile(r"(?i)(password|passwd|pwd|token|secret|authorization|cookie|apikey|api_key)=\S+"), r"\1=<redacted>"),
    (re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<redacted>"),
    (re.compile(r"jdbc:[^\s,;]+(?:[^\s]*)"), "jdbc:<redacted>"),
    (re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"), "<email:redacted>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<ip:redacted>"),
]


def fail(message):
    print(json.dumps({"ok": False, "error": message}, indent=2, sort_keys=True))
    return 2


def read_json(path):
    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError("incident file does not exist or is not a file: %s" % file_path)
    if file_path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("incident file exceeds %s bytes" % MAX_INPUT_BYTES)
    with file_path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("incident JSON must be an object")
    return data


def text_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value is not None:
            if isinstance(value, (list, tuple)):
                return " ".join(str(item) for item in value if item is not None)
            return str(value)
    return ""


def list_value(data, *keys):
    values = []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value if item is not None)
        elif value:
            values.extend(re.split(r"[,;/]", str(value)))
    return [item.strip() for item in values if item.strip()]


def redact(text):
    result = str(text or "")
    for pattern, replacement in SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def norm(data):
    haystack = " ".join(
        [
            text_value(data, "symptom", "description", "issue", "error", "message"),
            text_value(data, "subsystem", "scope", "affectedScope", "component"),
            " ".join(list_value(data, "source", "sources", "knownSources", "logSource", "logSources")),
        ]
    ).lower()
    return haystack


def has_any(haystack, words):
    return any(word in haystack for word in words)


def incident_window(data):
    start = text_value(data, "start", "startTime", "from", "windowStart")
    end = text_value(data, "end", "endTime", "to", "windowEnd")
    window = text_value(data, "timeWindow", "issueWindow", "window")
    timezone_text = text_value(data, "timezone", "timeZone", "tz")
    if start or end:
        bits = []
        if start:
            bits.append("start %s" % redact(start))
        if end:
            bits.append("end %s" % redact(end))
        if timezone_text:
            bits.append(timezone_text)
        return ", ".join(bits)
    if window:
        return redact(window if not timezone_text else "%s %s" % (window, timezone_text))
    return ""


def add_request(requests, source, priority, why, ask, keep, max_sample):
    requests.append(
        {
            "source": source,
            "priority": priority,
            "why": why,
            "ask": ask,
            "preserve": keep,
            "maxSample": max_sample,
        }
    )


def classify(data):
    haystack = norm(data)
    sources = [item.lower() for item in list_value(data, "source", "sources", "knownSources", "logSource", "logSources")]
    flags = {
        "startup": has_any(haystack, ["startup", "start up", "gateway won't start", "gateway wont start", "service", "reboot", "restart", "crash", "unexpectedly stopped"]),
        "database": has_any(haystack, ["database", "datasource", "jdbc", "sql", "named query", "namedquery", "db pool"]),
        "perspective": has_any(haystack, ["perspective", "browser", "session", "view", "binding", "websocket"]),
        "vision": has_any(haystack, ["vision", "client diagnostics"]),
        "designer": has_any(haystack, ["designer", "script console", "output console", "design-time", "design time"]),
        "thread": has_any(haystack, ["hang", "hung", "freeze", "frozen", "deadlock", "high cpu", "thread", "blocked", "slow gateway"]),
        "alarm": has_any(haystack, ["alarm", "journal", "pipeline", "notification"]),
        "audit": has_any(haystack, ["audit", "who changed", "changed by", "change attribution", "user changed"]),
        "tag": has_any(haystack, ["tag event", "valuechanged", "value changed", "opc", "device", "tag script"]),
        "report": has_any(haystack, ["report", "reporting"]),
        "auth": has_any(haystack, ["auth", "login", "idp", "security", "saml", "openid"]),
    }
    if any("wrapper" in source for source in sources):
        flags["startup"] = True
    if any("thread" in source for source in sources):
        flags["thread"] = True
    if any("browser" in source or "perspective" in source for source in sources):
        flags["perspective"] = True
    if any("vision" in source for source in sources):
        flags["vision"] = True
    if any("designer" in source for source in sources):
        flags["designer"] = True
    if any("audit" in source for source in sources):
        flags["audit"] = True
    if any("alarm" in source for source in sources):
        flags["alarm"] = True
    return flags, sources


def missing_fields(data, flags, sources):
    missing = []
    if not text_value(data, "ignitionVersion", "version", "gatewayVersion"):
        missing.append("exact Ignition version/build")
    if not incident_window(data):
        missing.append("issue time window")
    if not text_value(data, "timezone", "timeZone", "tz") and not re.search(r"\b(?:utc|cst|cdt|est|edt|pst|pdt|[+-]\d{2}:?\d{2})\b", text_value(data, "timeWindow", "issueWindow", "window"), re.IGNORECASE):
        missing.append("timezone")
    if not text_value(data, "status", "issueStatus"):
        missing.append("whether the issue is ongoing, intermittent, after restart, after deploy, or historical")
    if not text_value(data, "changedRecently", "recentChange", "change"):
        missing.append("what changed shortly before the first symptom")
    if not sources and not any(flags.values()):
        missing.append("which evidence source is available: Gateway log export/paste, wrapper log, browser console, Designer/Vision output, thread dump, audit, alarm journal, or diagnostic bundle")
    return missing


def build_requests(data):
    flags, sources = classify(data)
    requests = []
    window_text = incident_window(data) or "the smallest window covering before, during, and after the first symptom"
    gateway_keep = "timestamps, levels, logger names, first exception line, first stack frame, project/resource/query names when relevant"

    if not any(flags.values()) and not sources:
        add_request(
            requests,
            "Evidence source identification",
            "required",
            "Ignition diagnostics depend on source scope; Gateway, wrapper, browser, Designer, Vision, audit, alarm-journal, and thread-dump evidence cannot be treated as one stream.",
            "First identify which evidence source is available, then send the smallest sanitized sample from that source for %s." % window_text,
            "source name, timestamp/timezone, exact first symptom, and whether the issue is ongoing or historical",
            "a short source description plus 20-100 relevant lines only after the source is known",
        )

    if flags["startup"]:
        add_request(
            requests,
            "Wrapper logs",
            "required",
            "Startup, restart, service, and Gateway-scoped print output are best verified from wrapper logs.",
            "Send `wrapper.log` plus rotated numeric siblings that cover %s. Include file names, sizes, and modified times if available." % window_text,
            "wrapper timestamps, restart markers, service messages, embedded Ignition severity/logger text",
            "the relevant window or last 1-2 MB per file, not the whole log set unless needed",
        )

    if flags["thread"]:
        add_request(
            requests,
            "Thread dumps",
            "required",
            "Hangs, high CPU, deadlocks, and blocked execution need point-in-time thread-state evidence while the issue is happening.",
            "Capture at least three thread dumps 10-30 seconds apart during the symptom, then include any Gateway/wrapper log lines from %s." % window_text,
            "thread names, states, top frames, capture timestamps",
            "all dumps captured for that short incident window",
        )

    if flags["perspective"]:
        add_request(
            requests,
            "Perspective/browser evidence",
            "required",
            "Perspective client/session and binding symptoms can be browser-side or Gateway-side; the browser console prevents guessing.",
            "Send browser console errors and failed request details from %s, plus the affected project/page/view path with sensitive path segments redacted." % window_text,
            "browser timestamp, URL/page/view route, component or binding path shape, first error line",
            "20-100 console lines around the first error plus any failed request detail",
        )

    if flags["vision"]:
        add_request(
            requests,
            "Vision Client Diagnostics",
            "required",
            "Vision client evidence is session-local and is not verified by Gateway logs alone.",
            "Copy the Vision Client Diagnostics/Console evidence from %s before closing the client." % window_text,
            "client timestamp, logger, level, first error line, client/project context",
            "20-100 lines around the first client-side error",
        )

    if flags["designer"]:
        add_request(
            requests,
            "Designer output",
            "required",
            "Designer Script Console and Output Console are separate from Gateway/runtime logs.",
            "Copy the Designer Script Console or Output Console evidence from %s and label which console it came from." % window_text,
            "console name, timestamp if shown, logger/output line, resource path",
            "20-100 lines around the first design-time error",
        )

    if flags["audit"]:
        add_request(
            requests,
            "Audit log context",
            "context",
            "Audit rows can confirm change attribution, but they are not diagnostic exception logs.",
            "Send bounded audit rows around %s filtered to the actor/action/target/value if known." % window_text,
            "actor, action, target, value, timestamp, system/user fields",
            "only rows tied to the suspected change window",
        )

    if flags["alarm"]:
        add_request(
            requests,
            "Alarm journal context",
            "context",
            "Alarm journals confirm historical alarm behavior and property snapshots, not general Gateway diagnostic errors.",
            "Send bounded alarm-journal rows around %s for the affected provider/source/path/displayPath/state/priority." % window_text,
            "event time, state, priority, source/path/displayPath, associated data",
            "only affected alarms and the short surrounding window",
        )

    needs_gateway = (
        flags["database"]
        or flags["tag"]
        or flags["report"]
        or flags["auth"]
        or flags["alarm"]
        or flags["perspective"]
        or not requests
    )
    if needs_gateway:
        why = "Gateway Diagnostic Logs are the primary evidence for Gateway-scoped database, tag, auth, alarm, reporting, module, and project-resource errors."
        if flags["perspective"]:
            why = "Gateway logs can show server-side Perspective/script/binding follow-ons, while browser evidence captures client-side symptoms."
        add_request(
            requests,
            "Gateway Diagnostic Logs export or pasted excerpt",
            "required" if not flags["startup"] else "supporting",
            why,
            "Send either an exported `system_logs_*.idb` or 20-100 sanitized pasted lines around the first relevant ERROR/WARN from %s." % window_text,
            gateway_keep,
            "20-100 lines around the first relevant event, or a copied/exported `.idb` for the bounded window",
        )

    if not any(request["source"] == "Wrapper logs" for request in requests) and (flags["database"] or flags["perspective"] or flags["tag"] or flags["auth"]):
        add_request(
            requests,
            "Wrapper logs",
            "optional",
            "Wrapper logs are useful if the symptom includes restart/startup, Gateway-scoped bare print output, or missing Gateway-log context.",
            "Only include wrapper logs if the Gateway restarted, startup failed, or bare `print` output is part of the symptom.",
            "wrapper timestamps, restart markers, embedded Ignition logger text",
            "bounded window only",
        )

    return requests, flags, sources


def text_report(result):
    lines = [
        "# Ignition Evidence Request",
        "",
        "Purpose: request the smallest useful sanitized evidence set before diagnosis.",
        "",
        "## Missing Fields",
        "",
    ]
    if result["missingFields"]:
        lines.extend("- %s" % item for item in result["missingFields"])
    else:
        lines.append("- None for the next triage step.")
    lines.extend(["", "## Evidence To Request", ""])
    for item in result["evidenceRequests"]:
        lines.extend(
            [
                "### %s (%s)" % (item["source"], item["priority"]),
                "",
                "- Why: %s" % item["why"],
                "- Ask: %s" % item["ask"],
                "- Preserve: %s" % item["preserve"],
                "- Size: %s" % item["maxSample"],
                "",
            ]
        )
    lines.extend(["## Sanitization", ""])
    lines.extend("- %s" % item for item in result["sanitizationChecklist"])
    lines.extend(["", "## Do Not Include", ""])
    lines.extend("- %s" % item for item in result["doNotInclude"])
    lines.extend(["", "## Boundary", "", result["boundary"], ""])
    return "\n".join(lines)


def build(data):
    sanitized_summary = redact(text_value(data, "symptom", "description", "issue", "error", "message"))[:500]
    requests, flags, sources = build_requests(data)
    missing = missing_fields(data, flags, sources)
    result = {
        "ok": True,
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "incidentSummary": sanitized_summary,
        "detectedSignals": {key: value for key, value in sorted(flags.items()) if value},
        "knownSources": sources,
        "missingFields": missing,
        "evidenceRequests": requests,
        "sanitizationChecklist": [
            "Redact passwords, tokens, cookies, license keys, private keys, and JDBC URLs with credentials.",
            "Redact user PII, customer hostnames, public/private IPs, VPN details, and full production tag paths.",
            "Preserve timestamps, timezone, levels, logger names, exception classes, first stack frames, project/resource/query names, and consistently redacted path shape.",
            "Send the smallest relevant sample first; expand only if the first sample cannot confirm timing or source.",
        ],
        "doNotInclude": [
            "Credentials, token values, cookies, license/private-key material, or unredacted JDBC URLs.",
            "Full customer hostnames/IPs or full production tag paths when a stable redacted shape is enough.",
            "Thousands of unrelated log lines when 20-100 lines around the first relevant event will do.",
        ],
        "boundary": "This helper builds a safe evidence request, not a diagnosis. Root-cause claims still require review of the returned evidence.",
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a source-specific Ignition evidence request from incident JSON.")
    parser.add_argument("incident_json", help="Incident metadata JSON object.")
    parser.add_argument("--json-out", help="Write JSON result to this path.")
    parser.add_argument("--text-out", help="Write Markdown request to this path.")
    args = parser.parse_args(argv)

    try:
        data = read_json(args.incident_json)
        result = build(data)
    except Exception as exc:
        return fail(str(exc))

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
        result["jsonOut"] = str(Path(args.json_out))
    if args.text_out:
        Path(args.text_out).write_text(text_report(result), encoding="utf-8", newline="\n")
        result["textOut"] = str(Path(args.text_out))

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
