#!/usr/bin/env python3
"""Fail-open secrets scanner hook for Copilot session end."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

LOG_FILE = Path("logs/copilot/secrets/scan.log")

PATTERNS = [
    ("AWS_ACCESS_KEY", "critical", r"AKIA[0-9A-Z]{16}"),
    ("AWS_SECRET_KEY", "critical", r"aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}"),
    ("GCP_SERVICE_ACCOUNT", "critical", r"\"type\"[[:space:]]*:[[:space:]]*\"service_account\""),
    ("GCP_API_KEY", "high", r"AIza[0-9A-Za-z_-]{35}"),
    ("AZURE_CLIENT_SECRET", "critical", r"azure[_-]?client[_-]?secret\s*[:=]\s*['\"]?[A-Za-z0-9_~.-]{34,}"),
    ("GITHUB_PAT", "critical", r"ghp_[0-9A-Za-z]{36}"),
    ("GITHUB_OAUTH", "critical", r"gho_[0-9A-Za-z]{36}"),
    ("GITHUB_APP_TOKEN", "critical", r"ghs_[0-9A-Za-z._-]{36,}"),
    ("GITHUB_REFRESH_TOKEN", "critical", r"ghr_[0-9A-Za-z]{36}"),
    ("GITHUB_FINE_GRAINED_PAT", "critical", r"github_pat_[0-9A-Za-z_]{82}"),
    ("PRIVATE_KEY", "critical", r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    ("PGP_PRIVATE_BLOCK", "critical", r"-----BEGIN PGP PRIVATE KEY BLOCK-----"),
    ("GENERIC_SECRET", "high", r"(secret|token|password|passwd|pwd|api[_-]?key|apikey|access[_-]?key|auth[_-]?token|client[_-]?secret)\s*[:=]\s*['\"]?[A-Za-z0-9_/+=~.-]{8,}"),
    ("CONNECTION_STRING", "high", r"(mongodb(\+srv)?|postgres(ql)?|mysql|redis|amqp|mssql)://[^\s'\"]{10,}"),
    ("BEARER_TOKEN", "medium", r"[Bb]earer[[:space:]]+[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
    ("SLACK_TOKEN", "high", r"xox[baprs]-[0-9]{10,}-[0-9A-Za-z-]+"),
    ("SLACK_WEBHOOK", "high", r"https://hooks\.slack\.com/services/T[0-9A-Z]{8,}/B[0-9A-Z]{8,}/[0-9A-Za-z]{24}"),
    ("DISCORD_TOKEN", "high", r"[MN][A-Za-z0-9]{23,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,}"),
    ("TWILIO_API_KEY", "high", r"SK[0-9a-fA-F]{32}"),
    ("SENDGRID_API_KEY", "high", r"SG\.[0-9A-Za-z_-]{22}\.[0-9A-Za-z_-]{43}"),
    ("STRIPE_SECRET_KEY", "critical", r"sk_live_[0-9A-Za-z]{24,}"),
    ("STRIPE_RESTRICTED_KEY", "high", r"rk_live_[0-9A-Za-z]{24,}"),
    ("NPM_TOKEN", "high", r"npm_[0-9A-Za-z]{36}"),
    ("JWT_TOKEN", "medium", r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    (
        "INTERNAL_IP_PORT",
        "medium",
        r"(^|[^.0-9])(10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3}):[0-9]{2,5}([^0-9]|$)",
    ),
]


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_log_dir() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def append_json(entry: dict) -> None:
    ensure_log_dir()
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_git(*args: str) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def collect_files(scope: str) -> list[str]:
    files = []
    if scope == "staged":
        files.extend(run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR"))
    else:
        files.extend(run_git("diff", "--name-only", "--diff-filter=ACMR", "HEAD"))
        if not files:
            files.extend(run_git("diff", "--name-only", "--diff-filter=ACMR"))
        files.extend(run_git("ls-files", "--others", "--exclude-standard"))
    seen = set()
    result = []
    for file_name in files:
        if file_name and file_name not in seen:
            seen.add(file_name)
            result.append(file_name)
    return result


def is_text_file(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return b"\0" not in data


def is_placeholder(match: str) -> bool:
    return bool(
        re.search(
            r"(example|placeholder|your[_-]|xxx|changeme|TODO|FIXME|replace[_-]?me|dummy|fake|test[_-]?key|sample)",
            match,
            re.IGNORECASE,
        )
    )


def load_allowlist() -> list[str]:
    raw = os.environ.get("SECRETS_ALLOWLIST", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def scan_file(path: Path, allowlist: list[str]) -> list[dict]:
    if not path.exists() or not path.is_file() or not is_text_file(path):
        return []
    if path.name.endswith(".lock") or path.name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "go.sum"}:
        return []

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    findings = []
    for line_number, line in enumerate(lines, start=1):
        for pattern_name, severity, regex in PATTERNS:
            match = re.search(regex, line, flags=re.IGNORECASE)
            if not match:
                continue
            value = match.group(0)
            if any(token in value for token in allowlist):
                continue
            if is_placeholder(value):
                continue
            if pattern_name == "INTERNAL_IP_PORT":
                ip_match = re.search(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+", value)
                if not ip_match:
                    continue
                value = ip_match.group(0)
            redacted = "[REDACTED]" if len(value) <= 12 else f"{value[:4]}...{value[-4:]}"
            findings.append(
                {
                    "file": str(path),
                    "line": line_number,
                    "pattern": pattern_name,
                    "severity": severity,
                    "match": redacted,
                }
            )
    return findings


def main() -> int:
    mode = os.environ.get("SCAN_MODE", "warn").strip().lower() or "warn"
    scope = os.environ.get("SCAN_SCOPE", "diff").strip().lower() or "diff"
    allowlist = load_allowlist()
    timestamp = now_utc()

    try:
        files = collect_files(scope)
        if not files:
            append_json(
                {
                    "timestamp": timestamp,
                    "event": "scan_complete",
                    "mode": mode,
                    "scope": scope,
                    "status": "clean",
                    "files_scanned": 0,
                }
            )
            print("✨ No modified files to scan")
            return 0

        findings: list[dict] = []
        for file_name in files:
            findings.extend(scan_file(Path(file_name), allowlist))

        if findings:
            append_json(
                {
                    "timestamp": timestamp,
                    "event": "secrets_found",
                    "mode": mode,
                    "scope": scope,
                    "files_scanned": len(files),
                    "finding_count": len(findings),
                    "findings": findings,
                }
            )
            print(f"⚠️  Found {len(findings)} potential secret(s) in modified files:")
            print()
            print(f"{'FILE':40} {'LINE':6} {'PATTERN':28} SEVERITY")
            print(f"{'----':40} {'----':6} {'-------':28} {'--------'}")
            for finding in findings:
                print(
                    f"{finding['file'][:40]:40} {finding['line']:<6} "
                    f"{finding['pattern'][:28]:28} {finding['severity']}"
                )
            print()
            if mode == "block":
                return 1
            print("💡 Review the findings above. Set SCAN_MODE=block to prevent commits with secrets.")
            return 0

        append_json(
            {
                "timestamp": timestamp,
                "event": "scan_complete",
                "mode": mode,
                "scope": scope,
                "status": "clean",
                "files_scanned": len(files),
            }
        )
        print(f"✅ No secrets detected in {len(files)} scanned file(s)")
        return 0
    except Exception as exc:
        print(f"secrets-scanner: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
