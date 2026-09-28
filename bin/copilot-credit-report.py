#!/usr/bin/env python3
"""Compile the Copilot AI Credits ledger into the summary JSON and an HTML report.

Run this by hand whenever you want a fresh report:

    python bin/copilot-credit-report.py --open

It regenerates copilot-usage/copilot-credit-usage-summary.json (same output as
copilot-credit-rollup.py), writes a self-contained HTML report next to it, and
always writes copilot-usage/copilot-credit-usage-by-repo.csv -- one row per
repository (branches aggregated) with the ACS billing code, for expensing.
The report needs no network access: every row is embedded, and the ACS billing
cycle / custom date range / repository / branch filters run in the browser.

All credit values are ESTIMATES unless reported in `actual_ai_credits`; the
authoritative source is always the GitHub billing usage report.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib

rollup = importlib.import_module("copilot-credit-rollup")

DEFAULT_REPORT = rollup.DEFAULT_USAGE_DIR / "copilot-credit-usage-report.html"
DEFAULT_REPO_CSV = rollup.DEFAULT_USAGE_DIR / "copilot-credit-usage-by-repo.csv"
TEMPLATE = Path(__file__).resolve().parent / "copilot-credit-report-template.html"

REPO_CSV_COLUMNS = (
    "billing_code",
    "project_name",
    "client",
    "repo_origin",
    "repo_name",
    "records",
    "records_with_estimate",
    "coverage_pct",
    "estimated_credits",
    "estimated_cost_usd",
    "input_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "output_tokens",
    "first_date",
    "last_date",
)


def build_repo_csv_rows(parsed: dict) -> list[dict]:
    """Aggregate the ledger into one row per repository identity, branches folded in.

    Session markers carry no usage telemetry, so they raise `records` (the ledger
    row count) without touching credits or tokens. `coverage_pct` therefore stays
    honest: unknown usage is never rendered as zero spend.
    """
    buckets: dict[str, dict] = {}

    def bucket_for(scope: dict) -> dict:
        entry = buckets.get(scope["repo_key"])
        if entry is None:
            entry = {
                "billing_code": scope.get("billing_code") or "unmapped",
                "project_name": scope.get("project_name") or "",
                "client": scope.get("client") or "",
                "repo_origin": scope.get("repo_origin") or rollup.UNKNOWN,
                "repo_name": scope.get("repo_name") or rollup.UNKNOWN,
                "records": 0,
                "records_with_estimate": 0,
                "coverage_pct": 0.0,
                "estimated_credits": 0.0,
                "estimated_cost_usd": 0.0,
                "first_date": "",
                "last_date": "",
                **{field: 0 for field in rollup.TOKEN_FIELDS},
            }
            buckets[scope["repo_key"]] = entry
        return entry

    def observe(entry: dict, date_utc: str) -> None:
        entry["records"] += 1
        if not entry["first_date"] or date_utc < entry["first_date"]:
            entry["first_date"] = date_utc
        if date_utc > entry["last_date"]:
            entry["last_date"] = date_utc

    for row in parsed["rows"]:
        entry = bucket_for(row["scope"])
        observe(entry, row["date_utc"])
        for field in rollup.TOKEN_FIELDS:
            entry[field] += int(row["tokens"].get(field) or 0)
        if row["credits"] is None:
            continue
        entry["records_with_estimate"] += 1
        entry["estimated_credits"] += row["credits"]
        entry["estimated_cost_usd"] += row["credits"] * row["rate"]

    for marker in parsed["session_markers"]:
        observe(bucket_for(marker["scope"]), marker["date_utc"])

    rows = []
    for entry in buckets.values():
        entry["coverage_pct"] = round(entry["records_with_estimate"] / entry["records"] * 100, 2)
        entry["estimated_credits"] = round(entry["estimated_credits"], 4)
        entry["estimated_cost_usd"] = round(entry["estimated_cost_usd"], 6)
        rows.append(entry)
    rows.sort(key=lambda item: (-item["estimated_cost_usd"], item["repo_name"], item["repo_origin"]))
    return rows


def write_repo_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPO_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in REPO_CSV_COLUMNS})


def build_rows(parsed: dict) -> list[dict]:
    """Flatten parsed ledger rows into the shape the browser filters over."""
    rows = []
    for row in parsed["rows"]:
        scope = row["scope"]
        credits = row["credits"]
        tokens = row.get("tokens") or {}
        rows.append(
            {
                "date": row["date_utc"],
                "repo": scope["repo_name"],
                "repo_identity": scope["repo_key"],
                "repo_origin": scope["repo_origin"],
                "branch": scope["branch"],
                "workspace": scope["workspace_path"],
                "session_id": row["session_id"],
                "billing_code": scope["billing_code"],
                "project_name": scope["project_name"],
                "client": scope["client"],
                "model": row.get("model", "unknown"),
                "app_client": row.get("app_client", "unknown"),
                "input_tokens": tokens.get("input_tokens"),
                "cached_input_tokens": tokens.get("cached_input_tokens"),
                "cache_write_tokens": tokens.get("cache_write_tokens"),
                "output_tokens": tokens.get("output_tokens"),
                "iso_week": row["iso_week"],
                "week_start": row["week_start_utc"],
                "billed_on": row["billed_on"],
                "credits": credits,
                "cost_usd": None if credits is None else round(credits * row["rate"], 6),
                "actual_credits": row["actual"],
            }
        )
    rows.sort(key=lambda item: (item["date"], item["repo"], item["branch"]))
    return rows


def build_sessions(parsed: dict) -> list[dict]:
    """Combine usage events and no-telemetry markers into one row per session."""
    sessions: dict[str, dict] = {}
    for marker in parsed["session_markers"]:
        scope = marker["scope"]
        sessions[marker["session_id"]] = {
            "session_id": marker["session_id"],
            "date": marker["date_utc"],
            "repo": scope["repo_name"],
            "repo_identity": scope["repo_key"],
            "repo_origin": scope["repo_origin"],
            "branch": scope["branch"],
            "has_usage": False,
        }

    for row in parsed["rows"]:
        session_id = row["session_id"]
        if session_id == "unknown":
            continue
        scope = row["scope"]
        sessions[session_id] = {
            "session_id": session_id,
            "date": row["date_utc"],
            "repo": scope["repo_name"],
            "repo_identity": scope["repo_key"],
            "repo_origin": scope["repo_origin"],
            "branch": scope["branch"],
            "has_usage": True,
        }
    return sorted(sessions.values(), key=lambda item: (item["date"], item["repo_identity"], item["session_id"]))


def build_periods(summary: dict) -> list[dict]:
    return [
        {
            "billed_on": period["billed_on"],
            "start": period["start_utc_inclusive"],
            "end_exclusive": period["end_utc_exclusive"],
        }
        for period in summary["billing_periods"]
    ]


def build_payload(summary: dict, parsed: dict, ledger_path: Path) -> dict:
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_ledger": ledger_path.name,
        "disclaimer": summary["disclaimer"],
        "usd_per_ai_credit_default": summary["usd_per_ai_credit_default"],
        "week_definition": summary["week_definition"],
        "billing_period_definition": summary["billing_period_definition"],
        "billing_code_source": summary["billing_code_source"],
        "unmapped_repositories": summary["unmapped_repositories"],
        "invalid_records": summary["invalid_records"],
        "duplicate_record_keys_skipped": summary["duplicate_record_keys_skipped"],
        "records_bucketed_by_fallback_timestamp": summary["records_bucketed_by_fallback_timestamp"],
        "session_coverage": summary["session_coverage"],
        "billing_periods": build_periods(summary),
        "sessions": build_sessions(parsed),
        "rows": build_rows(parsed),
    }


def render_html(payload: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    # Escaping "<" keeps a repo or branch name from ever closing the script tag.
    data = json.dumps(payload, sort_keys=True).replace("<", "\\u003c")
    return template.replace("/*__REPORT_DATA__*/null", data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger", type=Path, default=rollup.DEFAULT_LEDGER, help="source JSONL ledger")
    parser.add_argument("--summary", type=Path, default=rollup.DEFAULT_SUMMARY, help="summary JSON to write")
    parser.add_argument("--projects", type=Path, default=rollup.DEFAULT_PROJECTS, help="repo -> ACS billing code map")
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT, help="HTML report to write")
    parser.add_argument("--repo-csv", type=Path, default=DEFAULT_REPO_CSV, help="per-repository spend CSV to write")
    parser.add_argument("--no-summary", action="store_true", help="build the report without rewriting the summary")
    parser.add_argument("--open", action="store_true", help="open the report in the default browser when done")
    args = parser.parse_args(argv)

    if not args.ledger.is_file():
        print(f"ledger not found: {args.ledger}", file=sys.stderr)
        return 2
    if not TEMPLATE.is_file():
        print(f"report template not found: {TEMPLATE}", file=sys.stderr)
        return 2

    projects = rollup.load_projects(args.projects)
    parsed = rollup.read_ledger(args.ledger, projects)
    summary = rollup.build_summary(args.ledger, projects)

    if not args.no_summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(rollup.render(summary), encoding="utf-8")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_html(build_payload(summary, parsed, args.ledger)), encoding="utf-8")

    repo_csv_rows = build_repo_csv_rows(parsed)
    write_repo_csv(args.repo_csv, repo_csv_rows)

    for item in summary["invalid_records"]:
        print(f"warning: line {item['line']}: {item['reason']}", file=sys.stderr)
    for item in summary["duplicate_record_keys_skipped"]:
        print(
            f"warning: line {item['line']}: duplicate record_key {item['record_key']} "
            f"(first seen on line {item['first_seen_line']})",
            file=sys.stderr,
        )
    for repo in summary["unmapped_repositories"]:
        print(f"warning: no ACS billing code mapped for {repo} (add it to {args.projects.name})", file=sys.stderr)

    totals = summary["totals"]
    if not args.no_summary:
        print(f"summary -> {args.summary}")
    print(f"report  -> {args.out}")
    print(f"csv     -> {args.repo_csv}")
    print(
        f"{summary['records_counted']} records, {len(totals['repositories'])} repositories, "
        f"{len(summary['billing_periods'])} billing periods; "
        f"estimated {totals['estimated_ai_credits']} credits (~${totals['estimated_cost_usd']})"
    )
    unmapped_csv_rows = sum(1 for row in repo_csv_rows if row["billing_code"] == "unmapped")
    print(
        f"csv: {len(repo_csv_rows)} repository rows (one row per repository, branches aggregated); "
        f"{unmapped_csv_rows} with billing_code=unmapped"
    )
    print(
        "csv values are ESTIMATES only; the authoritative source is the GitHub billing usage report. "
        "Records without usage telemetry count toward `records` but never toward credits - see `coverage_pct`."
    )

    if args.open:
        webbrowser.open(args.out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
