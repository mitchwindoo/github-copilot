#!/usr/bin/env python3
"""Fail-open governance audit hook for Copilot sessions."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

LOG_FILE = Path("logs/copilot/governance/audit.log")

THREAT_PATTERNS = [
    ("data_exfiltration", 0.8, "Bulk data transfer", r"send\s+(all|every|entire)\s+\w+\s+to\s+"),
    ("data_exfiltration", 0.9, "External export", r"export\s+.*\s+to\s+(external|outside|third[_-]?party)"),
    ("data_exfiltration", 0.7, "HTTP POST with data", r"curl\s+.*\s+-d\s+"),
    ("data_exfiltration", 0.95, "Credential upload", r"upload\s+.*\s+(credentials|secrets|keys)"),
    ("privilege_escalation", 0.8, "Elevated privileges", r"(sudo|as\s+root|admin\s+access|runas\s+/user)"),
    ("privilege_escalation", 0.9, "World-writable permissions", r"chmod\s+777"),
    ("privilege_escalation", 0.95, "Adding admin access", r"add\s+.*\s+(sudoers|administrators)"),
    ("system_destruction", 0.95, "Destructive command", r"(rm\s+-rf\s+/|del\s+/[sq]|format\s+c:)"),
    ("system_destruction", 0.9, "Database destruction", r"(drop\s+database|truncate\s+table|delete\s+from\s+\w+\s*(;|\s*$))"),
    ("system_destruction", 0.9, "Mass deletion", r"wipe\s+(all|entire|every)"),
    ("prompt_injection", 0.9, "Instruction override", r"ignore\s+(previous|above|all)\s+(instructions?|rules?|prompts?)"),
    ("prompt_injection", 0.7, "Role reassignment", r"you\s+are\s+now\s+(a|an)\s+(assistant|ai|bot|system|expert|language\s+model)\b"),
    ("prompt_injection", 0.6, "System prompt injection", r"(^|\n)\s*system\s*:\s*you\s+are"),
    ("credential_exposure", 0.9, "Possible hardcoded credential", r"(api[_-]?key|secret[_-]?key|password|token)\s*[:=]\s*['\"]?\w{8,}"),
    ("credential_exposure", 0.95, "AWS key exposure", r"(aws_access_key|AKIA[0-9A-Z]{16})"),
]


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_payload() -> tuple[dict, str]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}, raw
    try:
        return json.loads(raw), raw
    except ValueError:
        return {}, raw


def ensure_log_dir() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def append_json(entry: dict) -> None:
    ensure_log_dir()
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def prompt_text(payload: dict, raw: str) -> str:
    for key in ("userMessage", "prompt", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return raw


def scan_prompt(text: str) -> list[dict]:
    threats = []
    for category, severity, description, pattern in THREAT_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            threats.append(
                {
                    "category": category,
                    "severity": severity,
                    "description": description,
                    "evidence": match.group(0)[:160],
                }
            )
    return threats


def load_recent_session_start() -> str:
    if not LOG_FILE.exists():
        return ""
    try:
        starts = []
        for line in LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("event") == "session_start" and isinstance(entry.get("timestamp"), str):
                starts.append(entry["timestamp"])
        return starts[-1] if starts else ""
    except OSError:
        return ""


def summarize_session() -> tuple[int, int]:
    session_start = load_recent_session_start()
    if not LOG_FILE.exists():
        return 0, 0
    total = 0
    threats = 0
    try:
        for line in LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            timestamp = entry.get("timestamp")
            if not isinstance(timestamp, str):
                continue
            if session_start and timestamp < session_start:
                continue
            total += 1
            if entry.get("event") == "threat_detected":
                threats += 1
    except OSError:
        return 0, 0
    return total, threats


def main() -> int:
    payload, raw = read_payload()
    event = os.environ.get("GOVERNANCE_EVENT", "prompt").strip().lower()
    level = os.environ.get("GOVERNANCE_LEVEL", "standard").strip() or "standard"
    block_on_threat = os.environ.get("BLOCK_ON_THREAT", "false").strip().lower() == "true"
    timestamp = now_utc()
    cwd = os.getcwd()

    try:
        if event == "session_start":
            append_json(
                {
                    "timestamp": timestamp,
                    "event": "session_start",
                    "governance_level": level,
                    "cwd": cwd,
                }
            )
            print(f"🛡️ Governance audit active (level: {level})")
            return 0

        if event == "session_end":
            total, threats = summarize_session()
            append_json(
                {
                    "timestamp": timestamp,
                    "event": "session_end",
                    "total_events": total,
                    "threats_detected": threats,
                }
            )
            if threats > 0:
                print(f"⚠️ Session ended: {threats} threat(s) detected in {total} events")
            else:
                print(f"✅ Session ended: {total} events, no threats")
            return 0

        prompt = prompt_text(payload, raw)
        threats = scan_prompt(prompt)
        if threats:
            append_json(
                {
                    "timestamp": timestamp,
                    "event": "threat_detected",
                    "governance_level": level,
                    "threat_count": len(threats),
                    "max_severity": max(item["severity"] for item in threats),
                    "threats": threats,
                }
            )
            print(
                f"⚠️ Governance: {len(threats)} threat signal(s) detected "
                f"(max severity: {max(item['severity'] for item in threats):.2f})"
            )
        else:
            append_json(
                {
                    "timestamp": timestamp,
                    "event": "prompt_scanned",
                    "governance_level": level,
                    "status": "clean",
                }
            )
        if block_on_threat and threats:
            return 1
        return 0
    except Exception as exc:
        print(f"governance-audit: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
