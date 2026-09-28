#!/usr/bin/env python3
"""Roll up the Copilot AI Credits ledger into weekly and billing-period totals.

Source of truth is the append-only JSONL ledger. This script never writes to it;
it regenerates a deterministic summary file that is safe to re-run at any time.

Weeks are ISO calendar weeks (Monday 00:00:00Z through Sunday 23:59:59Z).
Billing periods run from the 21st of one month (inclusive) to the 21st of the
next month (exclusive) and are named by the date they are billed on (the end).

Every bucket is also broken down by repository and then by branch, with the ACS
billing project code taken from copilot-usage/acs-billing-projects.json.

All credit values are ESTIMATES unless reported in `actual_ai_credits`; the
authoritative source is always the GitHub billing usage report.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
DEFAULT_USD_PER_AI_CREDIT = 0.01
BILLING_DAY = 21

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_USAGE_DIR = REPO_ROOT / "copilot-usage"
DEFAULT_LEDGER = DEFAULT_USAGE_DIR / "copilot-credit-usage.jsonl"
DEFAULT_SUMMARY = DEFAULT_USAGE_DIR / "copilot-credit-usage-summary.json"
DEFAULT_PROJECTS = DEFAULT_USAGE_DIR / "acs-billing-projects.json"
UNKNOWN = "unknown"


def normalize_repo_origin(value: str | None) -> str | None:
    """Canonicalize HTTPS, SSH, and scp-style remotes to one credential-free origin."""
    if not isinstance(value, str) or not value.strip() or value == UNKNOWN:
        return None

    remote = value.strip()
    if "://" not in remote:
        match = re.fullmatch(r"(?:[^@/]+@)?([^:/]+):(.+)", remote)
        if match is None:
            return None
        host, path = match.groups()
        port = None
    else:
        try:
            parsed = urlsplit(remote)
            if parsed.scheme.lower() not in {"https", "http", "ssh", "git"} or not parsed.hostname:
                return None
            host = parsed.hostname
            path = parsed.path
            port = parsed.port
        except ValueError:
            return None

    host = host.lower()
    if port is not None and port not in {22, 80, 443, 9418}:
        host = f"{host}:{port}"
    path = "/" + "/".join(part for part in path.split("/") if part)
    if path == "/":
        return None
    path = re.sub(r"\.git$", "", path, flags=re.IGNORECASE)
    if host == "github.com":
        path = path.lower()
    return f"https://{host}{path}"


def repo_name_from_origin(origin: str | None) -> str:
    if not origin:
        return UNKNOWN
    path = urlsplit(origin).path.strip("/")
    return path or UNKNOWN


def load_projects(path: Path) -> dict[str, dict]:
    """Index the billing-code map by origin, repo_name, and workspace_path."""
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    index: dict[str, dict] = {}
    for entry in data.get("projects", []):
        if not isinstance(entry, dict):
            continue
        code = entry.get("billing_code")
        details = {
            "billing_code": None if code is None else str(code),
            "project_name": entry.get("project_name"),
            "client": entry.get("client"),
        }
        origin = normalize_repo_origin(entry.get("repo_origin"))
        if origin:
            index[origin] = details
        for key in (entry.get("repo_name"), entry.get("workspace_path")):
            if isinstance(key, str) and key and key != UNKNOWN:
                index[key] = details
    return index


def text_or_unknown(value) -> str:
    return value if isinstance(value, str) and value else UNKNOWN


def parse_utc(value: str) -> datetime:
    """Parse an ISO 8601 timestamp into an aware UTC datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def week_bucket(moment: datetime) -> tuple[str, str, str]:
    iso_year, iso_week, iso_weekday = moment.isocalendar()
    start = moment.date() - timedelta(days=iso_weekday - 1)
    return f"{iso_year}-W{iso_week:02d}", start.isoformat(), (start + timedelta(days=6)).isoformat()


def billing_bucket(moment: datetime) -> tuple[str, str, str]:
    """Return (billed_on, period_start, period_end_exclusive) for a timestamp."""
    day = moment.date()
    if day.day >= BILLING_DAY:
        start = date(day.year, day.month, BILLING_DAY)
    else:
        start = date(day.year - 1, 12, BILLING_DAY) if day.month == 1 else date(day.year, day.month - 1, BILLING_DAY)
    end = date(start.year + 1, 1, BILLING_DAY) if start.month == 12 else date(start.year, start.month + 1, BILLING_DAY)
    return end.isoformat(), start.isoformat(), end.isoformat()


TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_tokens", "output_tokens")


def new_bucket(extra: dict) -> dict:
    bucket = dict(extra)
    bucket.update(
        {
            "records": 0,
            "records_with_estimate": 0,
            "records_without_estimate": 0,
            "records_with_actual": 0,
            "estimated_ai_credits": 0.0,
            "estimated_cost_usd": 0.0,
            "actual_ai_credits": 0.0,
            "records_with_token_data": 0,
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 0,
        }
    )
    return bucket


def add_totals(
    bucket: dict, credits: float | None, rate: float, actual: float | None, tokens: dict | None = None
) -> None:
    bucket["records"] += 1
    if credits is None:
        bucket["records_without_estimate"] += 1
    else:
        bucket["records_with_estimate"] += 1
        bucket["estimated_ai_credits"] += credits
        bucket["estimated_cost_usd"] += credits * rate
    if actual is not None:
        bucket["records_with_actual"] += 1
        bucket["actual_ai_credits"] += actual
    if tokens and any(tokens.get(field) is not None for field in TOKEN_FIELDS):
        bucket["records_with_token_data"] += 1
        for field in TOKEN_FIELDS:
            value = tokens.get(field)
            if value is not None:
                bucket[field] += value


def accumulate(
    bucket: dict,
    credits: float | None,
    rate: float,
    actual: float | None,
    scope: dict | None = None,
    model: str | None = None,
    tokens: dict | None = None,
) -> None:
    """Add one record to a bucket and to its repository/branch and model breakdowns."""
    add_totals(bucket, credits, rate, actual, tokens)
    if scope is not None:
        repos = bucket.setdefault("_repos", {})
        repo = repos.get(scope["repo_key"])
        if repo is None:
            repo = new_bucket(
                {
                    "repo_name": scope["repo_name"],
                    "repo_origin": scope["repo_origin"],
                    "billing_code": scope["billing_code"],
                    "project_name": scope["project_name"],
                    "client": scope["client"],
                }
            )
            repo["_workspace_paths"] = set()
            repo["_branches"] = {}
            repos[scope["repo_key"]] = repo
        repo["_workspace_paths"].add(scope["workspace_path"])
        add_totals(repo, credits, rate, actual, tokens)
        branch = repo["_branches"].get(scope["branch"])
        if branch is None:
            branch = new_bucket({"branch": scope["branch"]})
            repo["_branches"][scope["branch"]] = branch
        add_totals(branch, credits, rate, actual, tokens)
    if model is not None:
        models = bucket.setdefault("_models", {})
        model_bucket = models.get(model)
        if model_bucket is None:
            model_bucket = new_bucket({"model": model})
            models[model] = model_bucket
        add_totals(model_bucket, credits, rate, actual, tokens)


def round_totals(bucket: dict) -> dict:
    bucket["estimated_ai_credits"] = round(bucket["estimated_ai_credits"], 4)
    bucket["estimated_cost_usd"] = round(bucket["estimated_cost_usd"], 2)
    bucket["actual_ai_credits"] = round(bucket["actual_ai_credits"], 4)
    return bucket


def finalize(bucket: dict) -> dict:
    round_totals(bucket)
    repos = bucket.pop("_repos", {})
    bucket["repositories"] = [
        round_totals(
            {
                **{k: v for k, v in repo.items() if not k.startswith("_")},
                "workspace_paths": sorted(repo["_workspace_paths"]),
                "branches": [round_totals(repo["_branches"][b]) for b in sorted(repo["_branches"])],
            }
        )
        for _, repo in sorted(repos.items(), key=lambda item: item[0])
    ]
    models = bucket.pop("_models", {})
    bucket["models"] = [round_totals(dict(models[m])) for m in sorted(models)]
    return bucket


def numeric_or_none(value, field: str, errors: list[str]) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{field} is not numeric")
        return None
    return float(value)


def read_ledger(ledger_path: Path, projects: dict[str, dict] | None = None) -> dict:
    """Parse the ledger once into usable rows plus the problems found along the way.

    Both the summary and the HTML report read from this so there is a single
    interpretation of the ledger.
    """
    if projects is None:
        projects = load_projects(DEFAULT_PROJECTS)
    rows: list[dict] = []
    invalid: list[dict] = []
    duplicates: list[dict] = []
    session_markers: list[dict] = []
    seen_keys: dict[str, int] = {}
    unmapped: set[str] = set()
    fallback_timestamps = 0

    with ledger_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                invalid.append({"line": line_number, "reason": f"invalid JSON: {exc.msg}"})
                continue
            if not isinstance(record, dict):
                invalid.append({"line": line_number, "reason": "record is not a JSON object"})
                continue

            key = record.get("record_key")
            if isinstance(key, str) and key and key != "unknown":
                first_seen = seen_keys.get(key)
                if first_seen is not None:
                    duplicates.append({"line": line_number, "record_key": key, "first_seen_line": first_seen})
                    continue
                seen_keys[key] = line_number

            errors: list[str] = []
            stamp_source = "session_created_at_utc"
            stamp = record.get("session_created_at_utc")
            if not isinstance(stamp, str) or not stamp or stamp == "unknown":
                stamp = record.get("recorded_at_utc")
                stamp_source = "recorded_at_utc"
            if not isinstance(stamp, str) or not stamp:
                errors.append("no usable session_created_at_utc or recorded_at_utc")
                moment = None
            else:
                try:
                    moment = parse_utc(stamp)
                except ValueError:
                    errors.append(f"unparseable timestamp {stamp!r}")
                    moment = None

            session_id = text_or_unknown(record.get("session_id"))
            repo_name = text_or_unknown(record.get("repo_name"))
            workspace_path = text_or_unknown(record.get("workspace_path"))
            repo_origin = normalize_repo_origin(record.get("repo_remote") or record.get("repo_origin"))
            if repo_name == UNKNOWN:
                repo_name = repo_name_from_origin(repo_origin)
            repo_key = (
                f"origin:{repo_origin}"
                if repo_origin
                else f"workspace:{workspace_path}"
                if workspace_path != UNKNOWN
                else f"session:{session_id}"
                if session_id != UNKNOWN
                else f"record:{key or line_number}"
            )
            mapping = projects.get(repo_origin) or projects.get(repo_name) or projects.get(workspace_path)
            if mapping is None:
                mapping = {"billing_code": None, "project_name": None, "client": None}
                unmapped.add(repo_origin or (repo_name if repo_name != UNKNOWN else repo_key))

            if errors or moment is None:
                invalid.append({"line": line_number, "reason": "; ".join(errors) or "unusable record"})
                continue
            if stamp_source != "session_created_at_utc":
                fallback_timestamps += 1

            scope = {
                "repo_key": repo_key,
                "repo_name": repo_name,
                "repo_origin": repo_origin,
                "workspace_path": workspace_path,
                "branch": text_or_unknown(record.get("branch")),
                **mapping,
            }

            if record.get("record_kind") == "session_marker":
                if session_id == UNKNOWN:
                    invalid.append({"line": line_number, "reason": "session marker has no session_id"})
                    continue
                session_markers.append(
                    {
                        "session_id": session_id,
                        "date_utc": moment.date().isoformat(),
                        "scope": scope,
                    }
                )
                continue

            errors = []
            credits = numeric_or_none(record.get("estimated_ai_credits"), "estimated_ai_credits", errors)
            actual = numeric_or_none(record.get("actual_ai_credits"), "actual_ai_credits", errors)
            basis = record.get("estimate_basis")
            rate = DEFAULT_USD_PER_AI_CREDIT
            if isinstance(basis, dict):
                basis_rate = numeric_or_none(basis.get("usd_per_ai_credit"), "usd_per_ai_credit", errors)
                if basis_rate:
                    rate = basis_rate
            model = text_or_unknown(record.get("model"))
            tokens = {field: numeric_or_none(record.get(field), field, errors) for field in TOKEN_FIELDS}
            if errors:
                invalid.append({"line": line_number, "reason": "; ".join(errors)})
                continue

            week_key, week_start, week_end = week_bucket(moment)
            billed_on, period_start, period_end = billing_bucket(moment)
            rows.append(
                {
                    "line": line_number,
                    "moment": moment,
                    "session_id": session_id,
                    "date_utc": moment.date().isoformat(),
                    "credits": credits,
                    "rate": rate,
                    "actual": actual,
                    "model": model,
                    "app_client": text_or_unknown(record.get("client")),
                    "tokens": tokens,
                    "iso_week": week_key,
                    "week_start_utc": week_start,
                    "week_end_utc": week_end,
                    "billed_on": billed_on,
                    "period_start_utc_inclusive": period_start,
                    "period_end_utc_exclusive": period_end,
                    "scope": scope,
                }
            )

    return {
        "rows": rows,
        "invalid_records": invalid,
        "duplicate_record_keys_skipped": duplicates,
        "session_markers": session_markers,
        "unmapped_repositories": sorted(unmapped),
        "records_bucketed_by_fallback_timestamp": fallback_timestamps,
    }


def build_summary(ledger_path: Path, projects: dict[str, dict] | None = None) -> dict:
    parsed = read_ledger(ledger_path, projects)
    weeks: dict[str, dict] = {}
    periods: dict[str, dict] = {}
    totals = new_bucket({})
    usage_session_ids = {row["session_id"] for row in parsed["rows"] if row["session_id"] != UNKNOWN}
    observed_session_ids = usage_session_ids | {item["session_id"] for item in parsed["session_markers"]}
    session_coverage = {
        "sessions_observed": len(observed_session_ids),
        "sessions_with_usage_records": len(usage_session_ids),
        "sessions_without_usage_records": len(observed_session_ids - usage_session_ids),
    }

    for row in parsed["rows"]:
        week = weeks.setdefault(
            row["iso_week"],
            new_bucket({"iso_week": row["iso_week"], "start_utc": row["week_start_utc"], "end_utc": row["week_end_utc"]}),
        )
        period = periods.setdefault(
            row["billed_on"],
            new_bucket(
                {
                    "billed_on": row["billed_on"],
                    "start_utc_inclusive": row["period_start_utc_inclusive"],
                    "end_utc_exclusive": row["period_end_utc_exclusive"],
                }
            ),
        )
        for bucket in (week, period, totals):
            accumulate(bucket, row["credits"], row["rate"], row["actual"], row["scope"], row["model"], row["tokens"])

    return {
        "schema_version": SCHEMA_VERSION,
        "disclaimer": (
            "Estimated credits and costs are best-effort and NOT a billed amount. "
            "The authoritative source is the GitHub billing usage report."
        ),
        "source_ledger": ledger_path.name,
        "usd_per_ai_credit_default": DEFAULT_USD_PER_AI_CREDIT,
        "week_definition": "ISO calendar week, Monday 00:00Z through Sunday 23:59Z",
        "billing_period_definition": "21st of a month (inclusive) through the 21st of the next month (exclusive), named by the billing date",
        "bucketed_by": "session_created_at_utc (falls back to recorded_at_utc)",
        "grouped_by": "repository, then branch, within totals and every week and billing period",
        "repository_identity": "normalized credential-free remote origin; workspace/session fallback when unavailable",
        "billing_code_source": DEFAULT_PROJECTS.name,
        "session_coverage": session_coverage,
        "unmapped_repositories": parsed["unmapped_repositories"],
        "records_counted": len(parsed["rows"]),
        "records_bucketed_by_fallback_timestamp": parsed["records_bucketed_by_fallback_timestamp"],
        "duplicate_record_keys_skipped": parsed["duplicate_record_keys_skipped"],
        "invalid_records": parsed["invalid_records"],
        "totals": finalize(totals),
        "weekly": [finalize(weeks[k]) for k in sorted(weeks)],
        "billing_periods": [finalize(periods[k]) for k in sorted(periods)],
    }


def render(summary: dict) -> str:
    return json.dumps(summary, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER, help="source JSONL ledger")
    parser.add_argument("--out", type=Path, default=DEFAULT_SUMMARY, help="summary JSON to write")
    parser.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS, help="repo -> ACS billing code map")
    parser.add_argument("--check", action="store_true", help="fail if the summary on disk is out of date")
    parser.add_argument("--strict", action="store_true", help="fail if any record is invalid or duplicated")
    args = parser.parse_args(argv)

    if not args.ledger.is_file():
        print(f"ledger not found: {args.ledger}", file=sys.stderr)
        return 2

    summary = build_summary(args.ledger, load_projects(args.projects))
    rendered = render(summary)

    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.is_file() else None
        if current != rendered:
            print(f"summary is out of date: {args.out}", file=sys.stderr)
            return 1
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")

    for item in summary["invalid_records"]:
        print(f"warning: line {item['line']}: {item['reason']}", file=sys.stderr)
    for item in summary["duplicate_record_keys_skipped"]:
        print(
            f"warning: line {item['line']}: duplicate record_key {item['record_key']} (first seen on line {item['first_seen_line']})",
            file=sys.stderr,
        )

    for repo in summary["unmapped_repositories"]:
        print(f"warning: no ACS billing code mapped for {repo} (add it to {args.projects.name})", file=sys.stderr)

    totals = summary["totals"]
    print(
        f"{summary['records_counted']} records -> {len(summary['weekly'])} weeks, "
        f"{len(summary['billing_periods'])} billing periods, "
        f"{len(totals['repositories'])} repositories; "
        f"estimated {totals['estimated_ai_credits']} credits (~${totals['estimated_cost_usd']}), "
        f"{totals['records_without_estimate']} without an estimate"
    )

    if args.strict and (summary["invalid_records"] or summary["duplicate_record_keys_skipped"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
