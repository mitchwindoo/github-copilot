#!/usr/bin/env python3
"""Check proposed Ignition alarm notification actions before live sends.

The script is intentionally conservative. It does not contact Ignition or send
messages; it classifies a JSON plan and emits blockers plus a redacted copy.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


EXTERNAL_CHANNELS = {"email", "sms", "voice", "phone", "webhook", "http", "remote-gateway"}
SAFE_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "invalid",
    "test",
    "localhost",
}
SAFE_URL_HOSTS = {"localhost", "127.0.0.1", "::1"}
SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|authorization|api[_-]?key|credential)", re.I)
EMAIL_RE = re.compile(r"(?P<local>[A-Za-z0-9._%+-]+)@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,}|localhost)")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)")
URL_RE = re.compile(r"\bhttps?://([^/\s:]+)(?::\d+)?[^\s]*", re.I)
HOST_RE = re.compile(r"\b(?:[A-Za-z0-9-]+\.){2,}[A-Za-z]{2,}\b")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def lower_text(value: Any) -> str:
    return str(value or "").strip().lower()


def channel_names(plan: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("channel", "channels", "profileType", "profileTypes"):
        for value in as_list(plan.get(key)):
            if isinstance(value, dict):
                value = value.get("type") or value.get("name")
            text = lower_text(value).replace("_", "-")
            if text:
                names.add(text)
    for profile in as_list(plan.get("notificationProfiles")):
        if isinstance(profile, dict):
            text = lower_text(profile.get("type") or profile.get("profileType") or profile.get("name"))
            if text:
                names.add(text.replace("_", "-"))
    return names


def collect_strings(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            out.extend(collect_strings(item))
    elif isinstance(value, list):
        for item in value:
            out.extend(collect_strings(item))
    elif value is not None:
        out.append(str(value))
    return out


def email_domain(email: str) -> str:
    match = EMAIL_RE.search(email)
    return match.group("domain").lower() if match else ""


def is_safe_email(email: str) -> bool:
    domain = email_domain(email)
    if not domain:
        return True
    return domain in SAFE_EMAIL_DOMAINS or domain.endswith(".test") or domain.endswith(".invalid")


def is_safe_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits.startswith("555") or digits in {"0000000000", "1111111111"}


def is_safe_url(url: str) -> bool:
    match = URL_RE.search(url)
    if not match:
        return True
    host = match.group(1).lower()
    return host in SAFE_URL_HOSTS or host.endswith(".test") or host.endswith(".invalid")


def redact_string(text: str) -> str:
    text = EMAIL_RE.sub("<redacted-email>", text)
    text = URL_RE.sub("<redacted-url>", text)
    text = HOST_RE.sub("<redacted-host>", text)
    text = PHONE_RE.sub("<redacted-phone>", text)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1<redacted>", text, flags=re.I)
    return text


def redact(value: Any, key: str = "") -> Any:
    if SENSITIVE_KEY_RE.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {item_key: redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_string(value)
    return value


def classify(plan: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    channels = channel_names(plan)
    external = sorted(name for name in channels if name in EXTERNAL_CHANNELS)
    send_mode = lower_text(plan.get("sendMode") or plan.get("mode") or plan.get("intent"))
    live_send = send_mode in {"live", "real", "production", "send", "apply"}
    sandbox_approved = bool(plan.get("sandboxApproved"))
    sandbox_target = str(plan.get("sandboxTarget") or "").strip()
    live_approved = bool(plan.get("liveSendApproved"))
    approval_ref = str(plan.get("approvalRef") or "").strip()

    if external and not sandbox_target and not live_approved:
        blockers.append("External notification channel requires a named sandboxTarget or explicit liveSendApproved approval.")
    if external and live_send and not live_approved:
        blockers.append("Live external send mode requires liveSendApproved and approvalRef.")
    if live_approved and not approval_ref:
        blockers.append("liveSendApproved requires a concrete approvalRef.")

    all_text = "\n".join(collect_strings(plan))
    real_emails = sorted({m.group(0) for m in EMAIL_RE.finditer(all_text) if not is_safe_email(m.group(0))})
    real_phones = sorted({m.group(0) for m in PHONE_RE.finditer(all_text) if not is_safe_phone(m.group(0))})
    real_urls = sorted({m.group(0) for m in URL_RE.finditer(all_text) if not is_safe_url(m.group(0))})

    if real_emails and not live_approved:
        blockers.append("Real-looking email recipients require explicit live approval.")
    if real_phones and not live_approved:
        blockers.append("Real-looking phone/SMS/voice recipients require explicit live approval.")
    if real_urls and not sandbox_approved and not live_approved:
        blockers.append("External webhook URLs require sandbox approval or explicit live approval.")
    if external and sandbox_approved and not sandbox_target:
        blockers.append("sandboxApproved is true but sandboxTarget is blank.")
    if external and not live_approved and sandbox_approved:
        warnings.append("Sandbox path accepted only for the named sandbox target; do not substitute production recipients.")

    return {
        "ok": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
        "channels": sorted(channels),
        "externalChannels": external,
        "realEmailCount": len(real_emails),
        "realPhoneCount": len(real_phones),
        "externalUrlCount": len(real_urls),
        "redactedPlan": redact(plan),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a proposed alarm notification plan before external sends.")
    parser.add_argument("plan", type=Path, help="JSON file describing the proposed notification action.")
    parser.add_argument("--out", type=Path, help="Optional output JSON path.")
    args = parser.parse_args()

    plan = load_json(args.plan)
    if not isinstance(plan, dict):
        raise SystemExit("Plan JSON must be an object.")
    result = classify(plan)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
