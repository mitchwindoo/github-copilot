#!/usr/bin/env python3
"""Redact sensitive values from Ignition log evidence while preserving diagnostic shape."""

import argparse
import json
import re
import sys
from pathlib import Path


MAX_INPUT_BYTES = 2 * 1024 * 1024
SENSITIVE_KEY_RE = re.compile(
    r"(?i)(password|passwd|pwd|token|secret|api[_-]?key|apikey|client[_-]?secret|"
    r"access[_-]?token|refresh[_-]?token|sessionid|jsessionid|auth|cookie|"
    r"license(?:key)?)"
)
HOST_KEY_RE = re.compile(r"(?i)(host|hostname|server|gateway)")
HOST_VALUE_RE = re.compile(r"(?i)^([A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?::\d+)?$")


def error(message):
    print(json.dumps({"ok": False, "error": message}, indent=2, sort_keys=True))
    return 2


def add_count(counts, kind):
    counts[kind] = counts.get(kind, 0) + 1


def sub_count(pattern, replacement, text, counts, kind, flags=0):
    regex = re.compile(pattern, flags)

    def repl(match):
        add_count(counts, kind)
        if callable(replacement):
            return replacement(match)
        return match.expand(replacement)

    return regex.sub(repl, text)


def redact_tag_path(match):
    provider = match.group("provider")
    path = match.group("path")
    parts = [part for part in path.split("/") if part]
    leaf = parts[-1] if parts else "tag"
    return "[%s]<tag-path:redacted>/%s" % (provider, leaf)


def redact_url(match):
    scheme = match.group("scheme")
    suffix = match.group("suffix") or ""
    path = ""
    if "/" in suffix:
        path = suffix[suffix.find("/") :]
    if path and path != "/":
        return "%s://<host:redacted>%s" % (scheme, path)
    return "%s://<host:redacted>" % scheme


def sanitize_text(text, counts):
    result = str(text)

    result = sub_count(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        "<private-key:redacted>",
        result,
        counts,
        "private-key",
        re.DOTALL,
    )
    result = sub_count(
        r"(?i)\bjdbc:[^\s\"']+",
        "jdbc:<redacted>",
        result,
        counts,
        "jdbc-url",
    )
    result = sub_count(
        r"(?i)(Authorization\s*:\s*(?:Bearer|Basic)\s+)[^\s\r\n]+",
        r"\1<redacted>",
        result,
        counts,
        "authorization",
    )
    result = sub_count(
        r"(?i)\b(Bearer\s+)[A-Za-z0-9._~+/=-]+",
        r"\1<redacted>",
        result,
        counts,
        "authorization",
    )
    result = sub_count(
        r"(?i)((?:Cookie|Set-Cookie)\s*:\s*)[^\r\n]+",
        r"\1<cookie:redacted>",
        result,
        counts,
        "cookie",
    )
    result = sub_count(
        r"(?i)\b(license(?:Key)?|activationKey)\b\s*[:=]\s*['\"]?[^,\s;&'\"]+",
        r"\1=<license:redacted>",
        result,
        counts,
        "license-key",
    )
    result = sub_count(
        r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key|apikey|client[_-]?secret|"
        r"access[_-]?token|refresh[_-]?token|sessionid|jsessionid|auth|credential)\b"
        r"\s*[:=]\s*['\"]?[^,\s;&'\"]+",
        lambda m: "%s=<redacted>" % m.group(1),
        result,
        counts,
        "sensitive-key",
    )
    result = sub_count(
        r"(?i)(?P<scheme>https?)://(?:(?:[^:@/\s]+):(?:[^@/\s]+)@)?(?P<suffix>[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s\"']*)?)",
        redact_url,
        result,
        counts,
        "url-host",
    )
    result = sub_count(
        r"(?i)\b(host|hostname|server|serverName|gateway|clientHost)\b\s*[:=]\s*['\"]?"
        r"([A-Za-z0-9-]+\.)+[A-Za-z]{2,}",
        lambda m: "%s=<host:redacted>" % m.group(1),
        result,
        counts,
        "hostname",
    )
    result = sub_count(
        r"(?i)\\\\[A-Za-z0-9_.-]+\\",
        r"\\\\<host:redacted>\\",
        result,
        counts,
        "hostname",
    )
    result = sub_count(
        r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b",
        "<ip:redacted>",
        result,
        counts,
        "ip-address",
    )
    result = sub_count(
        r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "<email:redacted>",
        result,
        counts,
        "email",
    )
    result = sub_count(
        r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)",
        "<phone:redacted>",
        result,
        counts,
        "phone",
    )
    result = sub_count(
        r"\[(?P<provider>[^\]]+)\](?P<path>(?:[^\s/\]\r\n]+/){2,}[^\s/\]\r\n]+)",
        redact_tag_path,
        result,
        counts,
        "tag-path",
    )
    return result


def sanitize_value(value, counts):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                add_count(counts, "json-sensitive-key")
                sanitized[key] = "<redacted>"
            elif isinstance(item, str) and HOST_KEY_RE.search(str(key)) and HOST_VALUE_RE.match(item.strip()):
                add_count(counts, "json-hostname")
                sanitized[key] = "<host:redacted>"
            else:
                sanitized[key] = sanitize_value(item, counts)
        return sanitized
    if isinstance(value, list):
        return [sanitize_value(item, counts) for item in value]
    if isinstance(value, str):
        return sanitize_text(value, counts)
    return value


def load_input(path, max_bytes):
    size = path.stat().st_size
    with path.open("rb") as handle:
        data = handle.read(max_bytes)
    truncated = size > max_bytes
    return data.decode("utf-8", errors="replace"), size, truncated


def parse_json(text):
    stripped = text.lstrip("\ufeff\r\n\t ")
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except Exception:
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sanitize Ignition log evidence before AI review or handoff.")
    parser.add_argument("input", help="Text or JSON file to sanitize.")
    parser.add_argument("--json-out", help="Write the full JSON result to this path.")
    parser.add_argument("--text-out", help="Write only sanitized text to this path.")
    parser.add_argument("--max-input-bytes", type=int, default=MAX_INPUT_BYTES)
    args = parser.parse_args(argv)

    path = Path(args.input)
    if not path.is_file():
        return error("input file does not exist or is not a file: %s" % path)
    if args.max_input_bytes < 1024:
        return error("--max-input-bytes must be at least 1024")

    try:
        raw_text, raw_size, truncated = load_input(path, args.max_input_bytes)
    except Exception as exc:
        return error("failed to read input: %s" % exc)

    counts = {}
    parsed = parse_json(raw_text)
    if parsed is None:
        sanitized_text = sanitize_text(raw_text, counts)
        sanitized_object = None
        input_kind = "text"
    else:
        sanitized_object = sanitize_value(parsed, counts)
        sanitized_text = json.dumps(sanitized_object, indent=2, sort_keys=True)
        input_kind = "json"

    total_redactions = sum(counts.values())
    result = {
        "ok": True,
        "inputPath": str(path),
        "inputKind": input_kind,
        "inputBytes": raw_size,
        "inputTruncated": truncated,
        "maxInputBytes": args.max_input_bytes,
        "redactionCounts": dict(sorted(counts.items())),
        "totalRedactions": total_redactions,
        "sanitizedText": sanitized_text,
    }
    if sanitized_object is not None:
        result["sanitizedObject"] = sanitized_object

    if args.text_out:
        Path(args.text_out).write_text(sanitized_text, encoding="utf-8", newline="\n")
        result["textOut"] = str(Path(args.text_out))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
        result["jsonOut"] = str(Path(args.json_out))

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
