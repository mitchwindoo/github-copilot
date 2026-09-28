#!/usr/bin/env python3
"""Self-check for copilot-credit-rollup.py. Run: python bin/copilot-credit-rollup-selftest.py"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location("rollup", Path(__file__).resolve().parent / "copilot-credit-rollup.py")
rollup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollup)


def record(key: str, created: str, credits: float | None = 1.0, **overrides) -> dict:
    base = {
        "schema_version": 1,
        "recorded_at_utc": created,
        "record_key": key,
        "session_created_at_utc": created,
        "estimated_ai_credits": credits,
        "actual_ai_credits": None,
        "estimate_basis": {"usd_per_ai_credit": 0.01},
    }
    base.update(overrides)
    return base


def summarize(lines: list[str], tmp: Path) -> dict:
    ledger = tmp / "ledger.jsonl"
    ledger.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return rollup.build_summary(ledger)


def by_period(summary: dict) -> dict[str, dict]:
    return {p["billed_on"]: p for p in summary["billing_periods"]}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Billing-period boundaries: the 21st opens a new period billed on the next 21st.
        boundaries = [
            ("2026-08-20T23:59:59Z", "2026-08-21"),
            ("2026-08-21T00:00:00Z", "2026-09-21"),
            ("2026-08-22T12:00:00Z", "2026-09-21"),
            ("2026-09-20T23:59:59Z", "2026-09-21"),
            ("2026-09-21T00:00:00Z", "2026-10-21"),
            ("2026-09-22T00:00:00Z", "2026-10-21"),
            ("2026-12-21T00:00:00Z", "2027-01-21"),
            ("2027-01-01T00:00:00Z", "2027-01-21"),
        ]
        for stamp, expected in boundaries:
            got = rollup.billing_bucket(rollup.parse_utc(stamp))[0]
            assert got == expected, f"{stamp}: expected billed_on {expected}, got {got}"

        # ISO weeks run Monday through Sunday in UTC.
        assert rollup.week_bucket(rollup.parse_utc("2026-09-21T00:00:00Z")) == ("2026-W39", "2026-09-21", "2026-09-27")
        assert rollup.week_bucket(rollup.parse_utc("2026-09-27T23:59:59Z"))[0] == "2026-W39"
        assert rollup.week_bucket(rollup.parse_utc("2026-09-28T00:00:00Z"))[0] == "2026-W40"

        # Duplicates are skipped once, malformed and unknown-estimate records are reported not dropped.
        lines = [
            json.dumps(record("a", "2026-08-21T00:00:00Z", 10.0)),
            json.dumps(record("a", "2026-08-22T00:00:00Z", 99.0)),  # duplicate key
            json.dumps(record("unknown", "2026-08-23T00:00:00Z", 5.0)),
            json.dumps(record("unknown", "2026-08-24T00:00:00Z", 5.0)),  # "unknown" never dedupes
            json.dumps(record("b", "2026-09-20T00:00:00Z", None)),  # unknown estimate
            json.dumps(record("c", "2026-09-21T00:00:00Z", 2.5, actual_ai_credits=3.0)),
            json.dumps(record("d", "not-a-date", 1.0)),  # unparseable timestamp
            "{not json",
        ]
        summary = summarize(lines, tmp)
        assert summary["records_counted"] == 5, summary["records_counted"]
        assert len(summary["duplicate_record_keys_skipped"]) == 1
        assert [i["line"] for i in summary["invalid_records"]] == [7, 8], summary["invalid_records"]
        totals = summary["totals"]
        assert totals["estimated_ai_credits"] == 22.5, totals
        assert totals["estimated_cost_usd"] == 0.23, totals
        assert totals["records_without_estimate"] == 1
        assert totals["records_with_actual"] == 1 and totals["actual_ai_credits"] == 3.0
        periods = by_period(summary)
        assert periods["2026-09-21"]["estimated_ai_credits"] == 20.0, periods
        assert periods["2026-09-21"]["records_without_estimate"] == 1
        assert periods["2026-10-21"]["estimated_ai_credits"] == 2.5

        # Records without a session timestamp fall back to recorded_at_utc rather than being dropped.
        fallback = summarize(
            [json.dumps(record("e", "2026-09-21T00:00:00Z", 1.0, session_created_at_utc="unknown"))], tmp
        )
        assert fallback["records_counted"] == 1 and fallback["records_bucketed_by_fallback_timestamp"] == 1

        # Rendering is deterministic, so regeneration is idempotent.
        assert rollup.render(summary) == rollup.render(summarize(lines, tmp))

        # Real ledger: rollup totals must equal a direct sum of the source records.
        ledger = rollup.DEFAULT_LEDGER
        if ledger.is_file():
            live = rollup.build_summary(ledger)
            records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
            keys = [r["record_key"] for r in records]
            assert len(keys) == len(set(keys)), "ledger contains duplicate record_key values"
            assert not live["invalid_records"], live["invalid_records"]
            direct = round(sum(r["estimated_ai_credits"] for r in records if r["estimated_ai_credits"] is not None), 4)
            assert live["totals"]["estimated_ai_credits"] == direct, (live["totals"], direct)
            assert live["records_counted"] == len(records)
            assert sum(w["records"] for w in live["weekly"]) == len(records)
            assert sum(p["records"] for p in live["billing_periods"]) == len(records)
            assert rollup.render(live) == rollup.render(rollup.build_summary(ledger))

    print("ok: all copilot-credit-rollup self-checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
