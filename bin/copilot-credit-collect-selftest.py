#!/usr/bin/env python3
"""Focused self-checks for cross-session collection and origin matching."""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

collector = importlib.import_module("copilot-credit-collect")
rollup = importlib.import_module("copilot-credit-rollup")
report = importlib.import_module("copilot-credit-report")


def main() -> int:
    # Step 1: Ensure URL transports and credentials normalize to one origin.
    expected_origin = "https://github.com/nxedge/shd-ignition-boi1"
    for remote in (
        "https://github.com/NXEdge/SHD-Ignition-BOI1.git",
        "git@github.com:NXEdge/SHD-Ignition-BOI1.git",
        "ssh://git@github.com/NXEdge/SHD-Ignition-BOI1",
        "https://user:secret@github.com/NXEdge/SHD-Ignition-BOI1.git",
    ):
        assert rollup.normalize_repo_origin(remote) == expected_origin
    assert rollup.normalize_repo_origin("https://github.com/NXEdge/SHD-Ignition-BOI1-Fork") != expected_origin
    assert rollup.normalize_repo_origin("https://github.com.evil.test/NXEdge/SHD-Ignition-BOI1") != expected_origin

    # Step 2: Parse live-format official pricing tables and verify model/tier selection.
    html = """
    <p>1 AI credit = $0.01 USD</p>
    <table><tr><th>Model</th><th>Tier</th><th>Threshold (input tokens)</th><th>Input</th>
    <th>Cached input</th><th>Cache write</th><th>Output</th></tr>
    <tr><td>GPT-6 Luna</td><td>Default</td><td>≤ 272K</td><td>$0.10</td><td>$0.01</td><td>$0.125</td><td>$0.50</td></tr>
    <tr><td>GPT-6 Luna</td><td>Long context</td><td>&gt; 272K</td><td>$0.20</td><td>$0.02</td><td>$0.25</td><td>$0.75</td></tr></table>
    """
    prices = collector.parse_pricing_page(html)
    assert collector.select_price(prices, "gpt-6-luna", 272_000)["tier"] == "Default"
    assert collector.select_price(prices, "gpt-6-luna", 272_001)["tier"] == "Long context"
    event = {
        "model": "gpt-6-luna",
        "copilot_usage_model": "gpt-6-luna",
        "input_tokens": 100,
        "cache_read_tokens": 40,
        "cache_write_tokens": 10,
        "output_tokens": 20,
    }
    estimate, basis, issue = collector.estimate_event(event, prices)
    assert issue is None
    assert estimate == 0.0017
    assert basis["usd_per_1m"]["cache_write"] == 0.125
    event_identity = {
        "event_id": 7,
        "created_at": "2026-09-22T12:01:00Z",
        "turn_index": 0,
        **event,
    }
    changed_identity = {**event_identity, "output_tokens": 21}
    assert collector.usage_record_key("active-session", event_identity) != collector.usage_record_key(
        "active-session", changed_identity
    )
    assert collector.legacy_usage_record_key("active-session", 7) == "active-session:usage:7"

    # Step 3: Roll up rows from multiple worktrees by remote origin, not workspace.
    with tempfile.TemporaryDirectory() as directory:
        ledger = Path(directory) / "usage.jsonl"
        common = {
            "schema_version": 1,
            "session_id": "session-one",
            "turn_id": "0",
            "branch": "main",
            "session_created_at_utc": "2026-09-22T12:00:00Z",
            "estimated_ai_credits": 1.0,
            "actual_ai_credits": None,
            "estimate_basis": {"usd_per_ai_credit": 0.01},
            "repo_name": "NXEdge/SHD-Ignition-BOI1",
        }
        usage = [
            {
                **common,
                "record_kind": "usage_event",
                "record_key": "session-one:usage:1",
                "repo_remote": "https://github.com/NXEdge/SHD-Ignition-BOI1.git",
                "workspace_path": "/worktree/a",
            },
            {
                **common,
                "session_id": "session-two",
                "record_kind": "usage_event",
                "record_key": "session-two:usage:1",
                "repo_remote": "git@github.com:NXEdge/SHD-Ignition-BOI1.git",
                "workspace_path": "/worktree/b",
            },
            {
                **common,
                "session_id": "unknown-origin",
                "record_kind": "usage_event",
                "record_key": "unknown-origin:usage:1",
                "repo_remote": "unknown",
                "workspace_path": "/worktree/other",
            },
            {
                **common,
                "session_id": "empty-session",
                "record_kind": "session_marker",
                "record_key": "empty-session:session-marker:no-usage-events",
                "repo_remote": expected_origin,
                "workspace_path": "/worktree/c",
                "estimated_ai_credits": None,
                "estimate_basis": None,
                "notes": "usage unknown",
            },
        ]
        ledger.write_text("".join(json.dumps(record) + "\n" for record in usage), encoding="utf-8")
        parsed = rollup.read_ledger(
            ledger,
            {expected_origin: {"billing_code": "11384", "project_name": "SHD Ignition BOI1", "client": "NxEdge"}},
        )
        summary = rollup.build_summary(
            ledger,
            {expected_origin: {"billing_code": "11384", "project_name": "SHD Ignition BOI1", "client": "NxEdge"}},
        )
        payload = report.build_payload(summary, parsed, ledger)

        assert summary["records_counted"] == 3
        assert summary["session_coverage"] == {
            "sessions_observed": 4,
            "sessions_with_usage_records": 3,
            "sessions_without_usage_records": 1,
        }
        grouped = summary["totals"]["repositories"]
        origin_group = next(item for item in grouped if item["repo_origin"] == expected_origin)
        assert origin_group["records"] == 2
        assert origin_group["estimated_ai_credits"] == 2.0
        assert origin_group["billing_code"] == "11384"
        fallback_group = next(item for item in grouped if item["repo_origin"] is None)
        assert fallback_group["records"] == 1
        assert len(payload["sessions"]) == 4
        assert sum(not item["has_usage"] for item in payload["sessions"]) == 1

    # Step 4: Exercise append, unknown markers, and idempotent collection against a local fixture DB.
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        database = root / "session-store.db"
        ledger = root / "copilot-usage.jsonl"
        connection = sqlite3.connect(database)
        connection.execute(
            """
            CREATE TABLE sessions (
                id TEXT, cwd TEXT, repository TEXT, branch TEXT, created_at TEXT, host_type TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE assistant_usage_events (
                id INTEGER, session_id TEXT, turn_index INTEGER, model TEXT, copilot_usage_model TEXT,
                input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER,
                cache_write_tokens INTEGER, created_at TEXT
            )
            """
        )
        connection.executemany(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    "active-session",
                    str(root / "missing-worktree"),
                    "NXEdge/SHD-Ignition-BOI1",
                    "feature/test",
                    "2026-09-22T12:00:00Z",
                    "github",
                ),
                (
                    "unknown-session",
                    str(root / "missing-worktree-2"),
                    "NXEdge/SHD-Ignition-BOI1",
                    "main",
                    "2026-09-23T12:00:00Z",
                    "github",
                ),
            ],
        )
        connection.execute(
            "INSERT INTO assistant_usage_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (7, "active-session", 0, "gpt-6-luna", "gpt-6-luna", 100, 20, 40, 10, "2026-09-22T12:01:00Z"),
        )
        connection.commit()
        connection.close()
        original_fetch_pricing = collector.fetch_pricing
        collector.fetch_pricing = lambda timeout=20: (prices, "2026-09-28", "fixture")
        try:
            arguments = [
                "--repo-origin",
                expected_origin,
                "--workspace",
                str(root),
                "--session-db",
                str(database),
                "--ledger",
                str(ledger),
            ]
            with redirect_stdout(StringIO()):
                assert collector.main(arguments) == 0
                first_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
                assert len(first_rows) == 2
                assert sum(row["record_kind"] == "usage_event" for row in first_rows) == 1
                assert sum(row["record_kind"] == "session_marker" for row in first_rows) == 1
                assert next(row for row in first_rows if row["record_kind"] == "usage_event")["estimated_ai_credits"] == 0.0017

                assert collector.main(arguments) == 0
                second_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
                assert second_rows == first_rows
        finally:
            collector.fetch_pricing = original_fetch_pricing

    print("ok: copilot-credit-collect self-checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
