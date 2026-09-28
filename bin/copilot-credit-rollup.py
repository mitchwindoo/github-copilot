#!/usr/bin/env python3
"""Roll up the Copilot AI Credits ledger into weekly and billing-period totals.

Source of truth is the append-only JSONL ledger. This script never writes to it;
it regenerates a deterministic summary file that is safe to re-run at any time.

Weeks are ISO calendar weeks (Monday 00:00:00Z through Sunday 23:59:59Z).
Billing periods run from the 21st of one month (inclusive) to the 21st of the
next month (exclusive) and are named by the date they are billed on (the end).

All credit values are ESTIMATES unless reported in `actual_ai_credits`; the
authoritative source is always the GitHub billing usage report.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_USD_PER_AI_CREDIT = 0.01
BILLING_DAY = 21

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER = REPO_ROOT / "local-data" / "copilot-credit-usage.jsonl"
DEFAULT_SUMMARY = REPO_ROOT / "local-data" / "copilot-credit-usage-summary.json"


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
        }
    )
    return bucket


def accumulate(bucket: dict, credits: float | None, rate: float, actual: float | None) -> None:
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


def finalize(bucket: dict) -> dict:
    bucket["estimated_ai_credits"] = round(bucket["estimated_ai_credits"], 4)
    bucket["estimated_cost_usd"] = round(bucket["estimated_cost_usd"], 2)
    bucket["actual_ai_credits"] = round(bucket["actual_ai_credits"], 4)
    return bucket


def numeric_or_none(value, field: str, errors: list[str]) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{field} is not numeric")
        return None
    return float(value)


def build_summary(ledger_path: Path) -> dict:
    weeks: dict[str, dict] = {}
    periods: dict[str, dict] = {}
    invalid: list[dict] = []
    duplicates: list[dict] = []
    seen_keys: dict[str, int] = {}
    counted = 0
    fallback_timestamps = 0
    totals = new_bucket({})

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

            credits = numeric_or_none(record.get("estimated_ai_credits"), "estimated_ai_credits", errors)
            actual = numeric_or_none(record.get("actual_ai_credits"), "actual_ai_credits", errors)
            basis = record.get("estimate_basis")
            rate = DEFAULT_USD_PER_AI_CREDIT
            if isinstance(basis, dict):
                basis_rate = numeric_or_none(basis.get("usd_per_ai_credit"), "usd_per_ai_credit", errors)
                if basis_rate:
                    rate = basis_rate

            if errors or moment is None:
                invalid.append({"line": line_number, "reason": "; ".join(errors) or "unusable record"})
                continue

            if stamp_source != "session_created_at_utc":
                fallback_timestamps += 1

            week_key, week_start, week_end = week_bucket(moment)
            billed_on, period_start, period_end = billing_bucket(moment)
            week = weeks.setdefault(week_key, new_bucket({"iso_week": week_key, "start_utc": week_start, "end_utc": week_end}))
            period = periods.setdefault(
                billed_on,
                new_bucket({"billed_on": billed_on, "start_utc_inclusive": period_start, "end_utc_exclusive": period_end}),
            )
            for bucket in (week, period, totals):
                accumulate(bucket, credits, rate, actual)
            counted += 1

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
        "records_counted": counted,
        "records_bucketed_by_fallback_timestamp": fallback_timestamps,
        "duplicate_record_keys_skipped": duplicates,
        "invalid_records": invalid,
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
    parser.add_argument("--check", action="store_true", help="fail if the summary on disk is out of date")
    parser.add_argument("--strict", action="store_true", help="fail if any record is invalid or duplicated")
    args = parser.parse_args(argv)

    if not args.ledger.is_file():
        print(f"ledger not found: {args.ledger}", file=sys.stderr)
        return 2

    summary = build_summary(args.ledger)
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

    totals = summary["totals"]
    print(
        f"{summary['records_counted']} records -> {len(summary['weekly'])} weeks, "
        f"{len(summary['billing_periods'])} billing periods; "
        f"estimated {totals['estimated_ai_credits']} credits (~${totals['estimated_cost_usd']}), "
        f"{totals['records_without_estimate']} without an estimate"
    )

    if args.strict and (summary["invalid_records"] or summary["duplicate_record_keys_skipped"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
