#!/usr/bin/env python3
"""Small end-to-end self-check for the generated Copilot usage report."""

from __future__ import annotations

import importlib
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

    print("ok: copilot-credit-report self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
