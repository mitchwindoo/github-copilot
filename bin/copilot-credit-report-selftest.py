#!/usr/bin/env python3
"""Small end-to-end self-check for the generated Copilot usage report."""

from __future__ import annotations

import importlib
import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

report = importlib.import_module("copilot-credit-report")
rollup = importlib.import_module("copilot-credit-rollup")


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        ledger = root / "ledger.jsonl"
        ledger.write_text(
            json.dumps(
                {
                    "record_key": "selftest:1",
                    "session_created_at_utc": "2026-09-22T12:00:00Z",
                    "estimated_ai_credits": 12.5,
                    "actual_ai_credits": None,
                    "estimate_basis": {"usd_per_ai_credit": 0.01},
                    "repo_name": "org/repo",
                    "workspace_path": "C:\\repo",
                    "branch": "feature/report",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        projects = {"org/repo": {"billing_code": "11384", "project_name": "Report", "client": "ACS"}}
        parsed = rollup.read_ledger(ledger, projects)
        summary = rollup.build_summary(ledger, projects)
        payload = report.build_payload(summary, parsed, ledger)
        html = report.render_html(payload)

        assert "/*__REPORT_DATA__*/null" not in html
        assert "ACS billing cycle" in html
        assert "Manual date range" in html
        assert '"branch": "feature/report"' in html
        assert '"billing_code": "11384"' in html
        assert '"cost_usd": 0.125' in html
        assert payload["billing_periods"] == [
            {"billed_on": "2026-10-21", "start": "2026-09-21", "end_exclusive": "2026-10-21"}
        ]

    check_repo_csv()
    print("ok: copilot-credit-report self-check passed")
    return 0


def check_repo_csv() -> None:
    """Cover per-repo aggregation, billing-code mapping, unmapped rows, and unknown usage."""
    records = [
        {
            "record_key": "csv:1", "session_id": "s1", "session_created_at_utc": "2026-09-22T12:00:00Z",
            "estimated_ai_credits": 10.0, "estimate_basis": {"usd_per_ai_credit": 0.01},
            "repo_remote": "https://github.com/org/repo.git", "branch": "main",
            "input_tokens": 100, "output_tokens": 20,
        },
        {   # same repo, different branch and remote spelling: must fold into one row
            "record_key": "csv:2", "session_id": "s1", "session_created_at_utc": "2026-09-23T12:00:00Z",
            "estimated_ai_credits": 5.0, "estimate_basis": {"usd_per_ai_credit": 0.01},
            "repo_remote": "git@github.com:org/repo.git", "branch": "feature/x",
            "input_tokens": 50, "output_tokens": 10,
        },
        {   # no ACS mapping: must appear, explicitly flagged, never dropped or guessed
            "record_key": "csv:3", "session_id": "s2", "session_created_at_utc": "2026-09-24T12:00:00Z",
            "estimated_ai_credits": 2.0, "estimate_basis": {"usd_per_ai_credit": 0.01},
            "repo_remote": "https://github.com/other/thing", "branch": "main",
        },
        {   # usage telemetry present but no estimate: counts as a record, never as spend
            "record_key": "csv:4", "session_id": "s3", "session_created_at_utc": "2026-09-25T12:00:00Z",
            "estimated_ai_credits": None,
            "repo_remote": "https://github.com/org/repo", "branch": "main",
        },
        {   # session marker: unknown usage, not zero usage
            "record_kind": "session_marker", "record_key": "csv:5", "session_id": "s4",
            "session_created_at_utc": "2026-09-26T12:00:00Z",
            "repo_remote": "https://github.com/org/repo", "branch": "main",
        },
        {   # no resolvable origin: keeps its own row rather than merging into a real repo
            "record_key": "csv:6", "session_id": "s5", "session_created_at_utc": "2026-09-27T12:00:00Z",
            "estimated_ai_credits": 1.0, "estimate_basis": {"usd_per_ai_credit": 0.01},
            "workspace_path": "C:\\orphan", "branch": "main",
        },
    ]
    projects = {"https://github.com/org/repo": {"billing_code": "11384", "project_name": "Report", "client": "ACS"}}

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        ledger = root / "ledger.jsonl"
        ledger.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
        parsed = rollup.read_ledger(ledger, projects)
        summary = rollup.build_summary(ledger, projects)

        rows = report.build_repo_csv_rows(parsed)
        by_origin = {row["repo_origin"]: row for row in rows}
        assert len(rows) == 3, rows
        assert [row["estimated_cost_usd"] for row in rows] == sorted(
            (row["estimated_cost_usd"] for row in rows), reverse=True
        )

        mapped = by_origin["https://github.com/org/repo"]
        assert mapped["billing_code"] == "11384"
        assert mapped["project_name"] == "Report"
        assert mapped["records"] == 4, mapped  # 2 estimated + 1 without estimate + 1 session marker
        assert mapped["records_with_estimate"] == 2
        assert mapped["coverage_pct"] == 50.0
        assert mapped["estimated_credits"] == 15.0
        assert mapped["estimated_cost_usd"] == 0.15
        assert mapped["input_tokens"] == 150 and mapped["output_tokens"] == 30
        assert mapped["first_date"] == "2026-09-22" and mapped["last_date"] == "2026-09-26"

        assert by_origin["https://github.com/other/thing"]["billing_code"] == "unmapped"
        assert by_origin["https://github.com/other/thing"]["project_name"] == ""
        assert by_origin[rollup.UNKNOWN]["repo_name"] == rollup.UNKNOWN
        assert by_origin[rollup.UNKNOWN]["estimated_credits"] == 1.0

        totals = summary["totals"]
        assert round(sum(row["estimated_credits"] for row in rows), 4) == totals["estimated_ai_credits"]
        assert round(sum(row["estimated_cost_usd"] for row in rows), 6) == totals["estimated_cost_usd"]
        assert sum(row["records"] for row in rows) == summary["records_counted"] + len(parsed["session_markers"])

        destination = root / "by-repo.csv"
        report.write_repo_csv(destination, rows)
        text = destination.read_text(encoding="utf-8")
        assert not text.startswith("#"), "a comment line above the header would break CSV parsers"
        parsed_csv = list(csv.DictReader(text.splitlines()))
        assert list(parsed_csv[0]) == list(report.REPO_CSV_COLUMNS)
        assert len(parsed_csv) == len(rows)
        assert round(sum(float(row["estimated_credits"]) for row in parsed_csv), 4) == totals["estimated_ai_credits"]


if __name__ == "__main__":
    raise SystemExit(main())
