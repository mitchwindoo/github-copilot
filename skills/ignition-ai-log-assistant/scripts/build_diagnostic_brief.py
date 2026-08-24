#!/usr/bin/env python3
"""Build a source-labeled Ignition diagnostic brief from helper outputs.

This helper is intentionally conservative: it organizes evidence that has
already been parsed/grouped and calls out missing evidence, but it does not
fetch current bug sources or invent root cause beyond supplied findings.
"""

import argparse
import json
import re
import sys
from pathlib import Path


MAX_GROUPS = 50
MAX_CONTEXT_ROWS = 50
MAX_TEXT = 360

SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd|token|secret|api[_-]?key)\s*=\s*([^;\s,'\"]+)"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)([A-Za-z0-9._\-]+)"),
    re.compile(r"(?i)(jdbc:[^\s]+://)([^/@\s]+):([^/@\s]+)@"),
]


def fail(message):
    print(json.dumps({"ok": False, "error": str(message)}, indent=2, sort_keys=True))
    return 1


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ValueError("could not read JSON %s: %s" % (path, exc))


def clamp_text(value, limit=MAX_TEXT):
    text = "" if value is None else str(value)
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)(jdbc:"):
            text = pattern.sub(r"\1<redacted>:<redacted>@", text)
        else:
            text = pattern.sub(r"\1=<redacted>", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def as_list(value):
    if isinstance(value, list):
        return value
    return []


def normalize_grouped(data):
    if not isinstance(data, dict):
        raise ValueError("grouped findings JSON must be an object")
    if data.get("ok") is not True:
        raise ValueError("grouped findings JSON has ok != true")
    groups = as_list(data.get("groups"))
    if len(groups) > MAX_GROUPS:
        raise ValueError("group count %d exceeds safety cap %d" % (len(groups), MAX_GROUPS))
    return {
        "rowCount": data.get("rowCount"),
        "diagnosticRowCount": data.get("diagnosticRowCount"),
        "contextRowCount": data.get("contextRowCount"),
        "noiseRowCount": data.get("noiseRowCount"),
        "groupCount": data.get("groupCount", len(groups)),
        "groups": groups,
        "contextRows": as_list(data.get("contextRows"))[:MAX_CONTEXT_ROWS],
        "noiseRows": as_list(data.get("noiseRows"))[:MAX_CONTEXT_ROWS],
        "boundaries": as_list(data.get("boundaries")),
    }


def normalize_environment(data):
    if not isinstance(data, dict):
        return {"provided": False}
    return {
        "provided": True,
        "ignitionVersion": data.get("ignitionVersion") or data.get("version") or data.get("gatewayVersion"),
        "timezone": data.get("timezone") or data.get("timeZone"),
        "os": data.get("os") or data.get("osName"),
        "java": data.get("java") or data.get("javaVersion"),
        "runnerVersion": data.get("runnerVersion"),
        "stackVersion": data.get("stackVersion"),
        "modules": data.get("modules") if isinstance(data.get("modules"), list) else None,
    }


def normalize_source_checks(data):
    if not data:
        return {"provided": False, "checks": [], "summary": "No current bug/release source checks were provided."}
    checks = data.get("checks") if isinstance(data, dict) else data
    checks = checks if isinstance(checks, list) else []
    normalized = []
    for item in checks[:25]:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "source": clamp_text(item.get("source") or item.get("id") or item.get("url") or "source", 160),
                "url": item.get("url"),
                "status": item.get("status") or item.get("result"),
                "matched": bool(item.get("matched") or item.get("match") or item.get("exactVersionMatch")),
                "notes": clamp_text(item.get("notes") or item.get("summary") or item.get("message"), 220),
            }
        )
    if not normalized:
        return {"provided": False, "checks": [], "summary": "No current bug/release source checks were provided."}
    matches = [item for item in normalized if item["matched"]]
    if matches:
        summary = "Current source checks included %d matching item(s)." % len(matches)
    else:
        summary = "Current source checks were provided, but no matching fix/bug evidence was marked."
    return {"provided": True, "checks": normalized, "summary": summary}


def group_title(group):
    bits = [
        group.get("groupId") or "group",
        group.get("category") or "unclassified",
        group.get("level") or "",
        group.get("source") or "",
    ]
    return " / ".join([str(bit) for bit in bits if bit])


def summarize_evidence_rows(rows):
    summaries = []
    for row in as_list(rows)[:3]:
        summaries.append(
            {
                "timestamp": row.get("timestampIsoUtc"),
                "source": row.get("source"),
                "level": row.get("level"),
                "logger": clamp_text(row.get("logger"), 140),
                "message": clamp_text(row.get("message")),
            }
        )
    return summaries


def top_findings(grouped):
    findings = []
    for group in grouped["groups"]:
        if not isinstance(group, dict):
            continue
        follow_on = group.get("followOnOf")
        first_message = ""
        evidence = summarize_evidence_rows(group.get("evidenceRows"))
        if evidence:
            first_message = evidence[0].get("message") or ""
        finding = {
            "id": group.get("groupId"),
            "title": group_title(group),
            "confidence": group.get("confidence") or "unknown",
            "category": group.get("category") or "unclassified",
            "source": group.get("source"),
            "level": group.get("level"),
            "count": group.get("count"),
            "firstTimestamp": group.get("firstTimestampIsoUtc"),
            "lastTimestamp": group.get("lastTimestampIsoUtc"),
            "logger": clamp_text(group.get("logger"), 180),
            "exceptionClass": group.get("exceptionClass") or "",
            "firstStackFrame": clamp_text(group.get("firstStackFrame"), 220),
            "message": first_message,
            "linkedFollowOns": as_list(group.get("linkedFollowOns")),
            "followOnOf": follow_on,
            "evidenceRows": evidence,
            "interpretation": interpretation_for(group, first_message),
        }
        findings.append(finding)
    return findings


def interpretation_for(group, first_message):
    category = group.get("category") or "unclassified"
    confidence = group.get("confidence") or "unknown"
    if group.get("followOnOf"):
        return "Treat as a follow-on to %s until timestamps and upstream evidence say otherwise." % group.get("followOnOf")
    if confidence == "high" and category == "database/Named Query":
        return "High-confidence root-cause candidate for a database or Named Query failure."
    if confidence in {"high", "medium"} and category == "script/Jython":
        return "Script/Jython error candidate; verify inputs and calling context before calling root cause."
    if confidence in {"high", "medium"}:
        return "%s candidate; keep source and timestamp alignment visible." % category
    if first_message:
        return "Low-confidence or contextual finding; do not promote to root cause without more evidence."
    return "Finding needs human review."


def evidence_window(grouped, evidence_path):
    timestamps = []
    sources = set()
    levels = set()
    for group in grouped["groups"]:
        if not isinstance(group, dict):
            continue
        if group.get("firstTimestampIsoUtc"):
            timestamps.append(group.get("firstTimestampIsoUtc"))
        if group.get("lastTimestampIsoUtc"):
            timestamps.append(group.get("lastTimestampIsoUtc"))
        if group.get("source"):
            sources.add(str(group.get("source")))
        if group.get("level"):
            levels.add(str(group.get("level")))
    for row in grouped["contextRows"]:
        if not isinstance(row, dict):
            continue
        if row.get("timestampIsoUtc"):
            timestamps.append(row.get("timestampIsoUtc"))
        if row.get("source"):
            sources.add(str(row.get("source")))
        if row.get("level"):
            levels.add(str(row.get("level")))
    timestamps = sorted(set(timestamps))
    return {
        "start": timestamps[0] if timestamps else None,
        "end": timestamps[-1] if timestamps else None,
        "sources": sorted(sources),
        "levels": sorted(levels),
        "diagnosticRowCount": grouped["diagnosticRowCount"],
        "contextRowCount": grouped["contextRowCount"],
        "noiseRowCount": grouped["noiseRowCount"],
        "rawEvidencePath": evidence_path,
    }


def context_section(grouped):
    rows = []
    for row in grouped["contextRows"]:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "timestamp": row.get("timestampIsoUtc"),
                "source": row.get("source"),
                "category": row.get("category"),
                "message": clamp_text(row.get("message")),
            }
        )
    return rows


def build_next_steps(findings, source_checks):
    steps = []
    categories = {finding.get("category") for finding in findings}
    if "database/Named Query" in categories:
        steps.append("Inspect the named query/database schema and parameters named in the earliest database evidence before chasing Perspective follow-ons.")
    if "script/Jython" in categories:
        steps.append("Open the referenced project script and verify wrapper-passed context, null inputs, and first failing stack frame.")
    if "tag/OPC/device" in categories:
        steps.append("Read the affected tag qualities/history around the warning window and compare with OPC/device logs before assigning device root cause.")
    if any((finding.get("category") or "").startswith("Perspective") for finding in findings):
        steps.append("Check browser console and binding diagnostics for the Perspective route, but keep upstream Gateway/database groups separate.")
    if not source_checks.get("provided"):
        steps.append("Run current Ignition/module release-source checks before making version-specific bug or fixed-in-version claims.")
    if not steps:
        steps.append("Collect a narrower source-labeled excerpt around the first symptom and regroup before diagnosis.")
    return steps[:4]


def build_missing_evidence(grouped, environment, source_checks):
    missing = []
    if not environment.get("provided") or not environment.get("ignitionVersion"):
        missing.append("Ignition version/build and environment snapshot.")
    if not environment.get("timezone"):
        missing.append("Timezone for timestamp alignment.")
    if not source_checks.get("provided"):
        missing.append("Current bug/release source checks for installed Ignition/modules.")
    if not grouped["groups"]:
        missing.append("ERROR/WARN source-labeled diagnostic rows around the issue window.")
    if not any(group.get("source") == "GatewayDiagnosticLogsIDB" for group in grouped["groups"] if isinstance(group, dict)):
        missing.append("Gateway Diagnostic Logs export/IDB rows if Gateway-side errors are suspected.")
    if not any(group.get("source") == "PerspectiveBrowserConsole" for group in grouped["groups"] if isinstance(group, dict)):
        missing.append("Perspective/browser console evidence if the symptom is visible only in a session.")
    return missing


def render_markdown(result):
    env = result["environment"]
    lines = [
        "# %s" % result["title"],
        "",
        "## Environment Snapshot",
        "",
        "- Ignition: `%s`" % (env.get("ignitionVersion") or "<missing>"),
        "- Timezone: `%s`" % (env.get("timezone") or "<missing>"),
        "- OS/Java: `%s` / `%s`" % (env.get("os") or "<missing>", env.get("java") or "<missing>"),
        "- Runner/Stack: `%s` / `%s`" % (env.get("runnerVersion") or "<missing>", env.get("stackVersion") or "<missing>"),
        "",
        "## Evidence Window",
        "",
        "- Window: `%s` to `%s`" % (result["evidenceWindow"].get("start") or "<unknown>", result["evidenceWindow"].get("end") or "<unknown>"),
        "- Sources: `%s`" % ", ".join(result["evidenceWindow"].get("sources") or []),
        "- Raw evidence: `%s`" % (result["evidenceWindow"].get("rawEvidencePath") or "<not provided>"),
        "",
        "## Top Findings",
        "",
    ]
    for finding in result["topFindings"][:8]:
        lines.append(
            "- `%s` `%s` `%s`: %s"
            % (
                finding.get("id") or "?",
                finding.get("confidence") or "unknown",
                finding.get("category") or "unclassified",
                clamp_text(finding.get("message"), 220),
            )
        )
        lines.append("  Evidence: `%s` `%s`; %s" % (finding.get("source"), finding.get("firstTimestamp"), finding.get("interpretation")))
    if not result["topFindings"]:
        lines.append("- No diagnostic groups were supplied.")
    lines.extend(["", "## Bug/Release Check", "", "- %s" % result["bugReleaseCheck"]["summary"], ""])
    lines.extend(["## Next Steps", ""])
    for step in result["nextSteps"]:
        lines.append("- %s" % step)
    lines.extend(["", "## Missing Evidence", ""])
    for item in result["missingEvidence"] or ["No immediate missing-evidence items were inferred from the provided inputs."]:
        lines.append("- %s" % item)
    lines.extend(["", "## Boundaries", ""])
    for item in result["boundaries"]:
        lines.append("- %s" % item)
    return "\n".join(lines) + "\n"


def build_brief(args):
    grouped = normalize_grouped(load_json(args.grouped_findings_json))
    environment = normalize_environment(load_json(args.environment_json)) if args.environment_json else {"provided": False}
    source_checks = normalize_source_checks(load_json(args.source_checks_json)) if args.source_checks_json else normalize_source_checks(None)
    findings = top_findings(grouped)
    result = {
        "ok": True,
        "source": "IgnitionDiagnosticBrief",
        "title": args.title,
        "inputPath": str(Path(args.grouped_findings_json)),
        "environment": environment,
        "evidenceWindow": evidence_window(grouped, args.evidence_path),
        "topFindings": findings,
        "contextRows": context_section(grouped),
        "bugReleaseCheck": source_checks,
        "nextSteps": build_next_steps(findings, source_checks),
        "missingEvidence": build_missing_evidence(grouped, environment, source_checks),
        "boundaries": [
            "This helper formats a diagnostic brief from supplied helper output; it does not fetch logs or current web sources.",
            "Treat grouped findings as triage evidence. Root-cause wording still requires timestamp/source correlation and, when relevant, current release-source checks.",
            "Audit and alarm-journal rows remain context unless the supplied evidence confirms they are the diagnostic source.",
        ],
    }
    result["markdown"] = render_markdown(result)
    return result


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grouped_findings_json", help="JSON output from group_log_findings.py")
    parser.add_argument("--environment-json", help="Optional JSON object with Ignition/version/module/environment fields")
    parser.add_argument("--source-checks-json", help="Optional JSON source-check summary for current release/bug evidence")
    parser.add_argument("--evidence-path", default="", help="Raw evidence folder/path label to include in the brief")
    parser.add_argument("--title", default="Ignition Diagnostic Brief", help="Markdown/report title")
    parser.add_argument("--json-out", help="Optional path to write JSON output")
    parser.add_argument("--markdown-out", help="Optional path to write Markdown output")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = build_brief(args)
    except Exception as exc:
        return fail(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8", newline="\n")
    if args.markdown_out:
        Path(args.markdown_out).write_text(result["markdown"], encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
