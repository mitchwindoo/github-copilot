#!/usr/bin/env python3
"""Append missing local Copilot usage events for one repository origin.

The session store is opened read-only. Usage-event keys include both the
session UUID and its stable local event ID, making repeated collection and
merging ledger copies idempotent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib

rollup = importlib.import_module("copilot-credit-rollup")

PRICING_URL = "https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing"
DEFAULT_HOME = Path(os.environ.get("COPILOT_HOME", Path.home() / ".copilot")).expanduser()
DEFAULT_SESSION_DB = DEFAULT_HOME / "session-store.db"
DEFAULT_LEDGER = DEFAULT_HOME / "copilot-usage" / "copilot-credit-usage.jsonl"
UNKNOWN = "unknown"
USD_PER_AI_CREDIT = 0.01


class PricingTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.page_text: list[str] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_data(self, data: str) -> None:
        self.page_text.append(data)
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._table is not None and self._row is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def utc_timestamp(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = value.strip().replace("Z", "+00:00")
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_model(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_price(value: str) -> float | None:
    if re.search(r"not applicable|n/?a|—|–", value, re.IGNORECASE):
        return 0.0
    match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", value)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def parse_threshold(value: str) -> int | None:
    match = re.search(r"([\d,]+(?:\.\d+)?)\s*([km]?)", value, re.IGNORECASE)
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    unit = match.group(2).lower()
    return int(amount * (1_000 if unit == "k" else 1_000_000 if unit == "m" else 1))


def fetch_pricing(timeout: int = 20) -> tuple[dict[str, list[dict]], str, str]:
    request = urllib.request.Request(
        PRICING_URL,
        headers={"Accept": "text/html", "User-Agent": "CopilotCreditTracker/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        source = response.read().decode("utf-8", "replace")

    prices = parse_pricing_page(source)
    retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return prices, retrieved, source


def parse_pricing_page(source: str) -> dict[str, list[dict]]:
    parser = PricingTableParser()
    parser.feed(source)
    page_text = " ".join(" ".join(parser.page_text).split())
    conversion = re.search(r"1\s+AI\s+credit\s*=\s*\$?\s*0\.01\b", page_text, re.IGNORECASE)
    if not conversion:
        raise ValueError("official pricing page no longer confirms 1 AI credit = $0.01")

    prices: dict[str, list[dict]] = {}
    for table in parser.tables:
        header_index = None
        columns: dict[str, int] = {}
        for index, row in enumerate(table):
            normalized = [re.sub(r"[^a-z]+", " ", cell.lower()).strip() for cell in row]
            model_column = next((i for i, value in enumerate(normalized) if value == "model"), None)
            input_column = next((i for i, value in enumerate(normalized) if value == "input"), None)
            cached_column = next((i for i, value in enumerate(normalized) if value == "cached input"), None)
            output_column = next((i for i, value in enumerate(normalized) if value == "output"), None)
            if None in (model_column, input_column, cached_column, output_column):
                continue
            columns = {
                "model": model_column,
                "input": input_column,
                "cached_input": cached_column,
                "output": output_column,
            }
            for i, value in enumerate(normalized):
                if value == "cache write":
                    columns["cache_write"] = i
                elif value == "tier":
                    columns["tier"] = i
                elif value.startswith("threshold"):
                    columns["threshold"] = i
            header_index = index
            break

        if header_index is None:
            continue
        for row in table[header_index + 1 :]:
            if len(row) <= max(columns[key] for key in ("model", "input", "cached_input", "output")):
                continue
            model = row[columns["model"]].strip()
            if not model:
                continue

            def cell(name: str) -> str:
                index = columns.get(name)
                return row[index].strip() if index is not None and index < len(row) else ""

            input_rate = parse_price(cell("input"))
            cached_rate = parse_price(cell("cached_input"))
            output_rate = parse_price(cell("output"))
            cache_write_rate = parse_price(cell("cache_write")) if "cache_write" in columns else 0.0
            if None in (input_rate, cached_rate, output_rate, cache_write_rate):
                continue
            threshold = parse_threshold(cell("threshold"))
            tier_name = cell("tier").lower()
            if "long" in tier_name or (threshold is not None and re.search(r">\s*[\d,.]+", cell("threshold"))):
                tier = "Long context"
            else:
                tier = "Default"
            prices.setdefault(normalize_model(model), []).append(
                {
                    "model": model,
                    "tier": tier,
                    "threshold_input_tokens": threshold,
                    "usd_per_1m": {
                        "input": input_rate,
                        "cached_input": cached_rate,
                        "cache_write": cache_write_rate,
                        "output": output_rate,
                    },
                }
            )

    if not prices:
        raise ValueError("official pricing page contained no parseable model pricing tables")
    return prices


def select_price(prices: dict[str, list[dict]], model: str, input_tokens: int) -> dict | None:
    rows = prices.get(normalize_model(model), [])
    if not rows:
        return None
    long_rows = [row for row in rows if row["tier"] == "Long context"]
    if long_rows:
        threshold = min(
            (row["threshold_input_tokens"] for row in long_rows if row["threshold_input_tokens"] is not None),
            default=None,
        )
        if threshold is not None and input_tokens > threshold:
            return next(
                (row for row in long_rows if row["threshold_input_tokens"] == threshold),
                long_rows[0],
            )
    return next((row for row in rows if row["tier"] == "Default"), rows[0])


def estimate_event(event: sqlite3.Row, prices: dict[str, list[dict]]) -> tuple[float | None, dict | None, str | None]:
    model = event["copilot_usage_model"] or event["model"]
    if not isinstance(model, str) or not model:
        return None, None, "model identifier is unavailable"
    fields = ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens")
    if any(event[field] is None for field in fields):
        return None, None, "one or more token deltas are unavailable"

    try:
        total_input = int(event["input_tokens"])
        cached_input = int(event["cache_read_tokens"])
        cache_write = int(event["cache_write_tokens"])
        output = int(event["output_tokens"])
    except (TypeError, ValueError, OverflowError):
        return None, None, "token deltas are not valid integers"
    uncached_input = total_input - cached_input - cache_write
    if min(total_input, cached_input, cache_write, output, uncached_input) < 0:
        return None, None, "input token total is smaller than its cache breakdown"

    price = select_price(prices, model, total_input)
    if price is None:
        return None, None, f"no matching official pricing row for {model}"
    rates = price["usd_per_1m"]
    usd = (
        uncached_input * rates["input"]
        + cached_input * rates["cached_input"]
        + cache_write * rates["cache_write"]
        + output * rates["output"]
    ) / 1_000_000
    credits = round(usd / USD_PER_AI_CREDIT, 4)
    basis = {
        "pricing_source_url": PRICING_URL,
        "pricing_retrieved_utc": "",
        "tier": price["tier"],
        "usd_per_1m": rates,
        "usd_per_ai_credit": USD_PER_AI_CREDIT,
    }
    return credits, basis, None


def git_origin(workspace: str | None) -> str | None:
    if not workspace or not Path(workspace).is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", workspace, "remote", "get-url", "origin"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return rollup.normalize_repo_origin(result.stdout.strip())


def repository_slug(origin: str) -> str:
    return rollup.repo_name_from_origin(origin).strip("/").lower()


def matches_repository(value: str | None, slug: str, host: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    candidate = value.strip().strip("/")
    return candidate.lower() == slug if host == "github.com" else candidate == slug


def discover_sessions(
    connection: sqlite3.Connection,
    origin: str,
    workspace_root: Path,
) -> tuple[dict[str, dict], int]:
    slug = repository_slug(origin)
    host = origin.split("/", 3)[2].split(":", 1)[0]
    rows = connection.execute(
        """
        SELECT id, cwd, repository, branch, created_at, host_type
        FROM sessions
        WHERE lower(repository) = lower(?) OR cwd = ?
        ORDER BY created_at, id
        """,
        (rollup.repo_name_from_origin(origin), str(workspace_root)),
    ).fetchall()
    sessions: dict[str, dict] = {}
    out_of_scope = 0
    origin_cache: dict[str, str | None] = {}

    for row in rows:
        cwd = row["cwd"]
        if cwd not in origin_cache:
            origin_cache[cwd or ""] = git_origin(cwd)
        discovered_origin = origin_cache[cwd or ""]
        has_matching_slug = matches_repository(row["repository"], slug, host)

        if discovered_origin and discovered_origin != origin:
            out_of_scope += 1
            continue
        if not discovered_origin and not has_matching_slug and Path(cwd or "").resolve() != workspace_root:
            out_of_scope += 1
            continue

        inferred_origin = not discovered_origin
        resolved_origin = discovered_origin or (origin if has_matching_slug or Path(cwd or "").resolve() == workspace_root else None)
        sessions[row["id"]] = {
            "session_id": row["id"],
            "workspace_path": cwd or UNKNOWN,
            "repo_name": row["repository"] or rollup.repo_name_from_origin(resolved_origin),
            "repo_remote": resolved_origin or UNKNOWN,
            "branch": row["branch"] or UNKNOWN,
            "session_created_at_utc": utc_timestamp(row["created_at"]),
            "client": "copilot-app",
            "origin_inferred": inferred_origin,
        }
    return sessions, out_of_scope


def read_ledger_index(path: Path) -> tuple[set[str], set[str], set[str]]:
    record_keys: set[str] = set()
    session_ids: set[str] = set()
    legacy_session_aggregates: set[str] = set()
    if not path.exists():
        return record_keys, session_ids, legacy_session_aggregates

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"ledger line {line_number} is invalid JSON; refusing to append") from exc
            if not isinstance(record, dict):
                raise ValueError(f"ledger line {line_number} is not an object; refusing to append")
            key = record.get("record_key")
            session_id = record.get("session_id")
            if isinstance(key, str) and key and key != UNKNOWN:
                record_keys.add(key)
            if isinstance(session_id, str) and session_id and session_id != UNKNOWN:
                session_ids.add(session_id)
                if (
                    record.get("record_kind") not in {"usage_event", "session_marker"}
                    and record.get("turn_id") in {None, UNKNOWN}
                    and str(key).startswith("historical-backfill:")
                ):
                    legacy_session_aggregates.add(session_id)
    return record_keys, session_ids, legacy_session_aggregates


def make_usage_record(
    event: sqlite3.Row,
    session: dict,
    prices: dict[str, list[dict]],
    retrieved: str,
    recorded_at: str,
) -> tuple[dict, str | None]:
    credits, basis, issue = estimate_event(event, prices)
    model = event["copilot_usage_model"] or event["model"] or UNKNOWN
    if basis is not None:
        basis["pricing_retrieved_utc"] = retrieved
    notes = (
        "Estimated from one local assistant_usage_event using official GitHub rates; actual billed credits are not exposed."
        if issue is None
        else f"Estimated credits unavailable: {issue}; actual billed credits are not exposed."
    )
    if session["origin_inferred"]:
        notes += " Repository origin inferred from the matching GitHub owner/repository metadata."
    uncached_input = None
    if all(event[field] is not None for field in ("input_tokens", "cache_read_tokens", "cache_write_tokens")):
        uncached_input = int(event["input_tokens"]) - int(event["cache_read_tokens"]) - int(event["cache_write_tokens"])
    record = {
        "schema_version": 1,
        "record_kind": "usage_event",
        "recorded_at_utc": recorded_at,
        "session_id": session["session_id"],
        "turn_id": UNKNOWN if event["turn_index"] is None else str(event["turn_index"]),
        "record_key": usage_record_key(session["session_id"], event),
        "client": session["client"],
        "workspace_path": session["workspace_path"],
        "repo_remote": session["repo_remote"],
        "repo_name": session["repo_name"],
        "branch": session["branch"],
        "model": model,
        "input_tokens": uncached_input if uncached_input is None or uncached_input >= 0 else None,
        "cached_input_tokens": event["cache_read_tokens"],
        "cache_write_tokens": event["cache_write_tokens"],
        "output_tokens": event["output_tokens"],
        "actual_ai_credits": None,
        "estimated_ai_credits": credits,
        "estimate_basis": basis,
        "session_created_at_utc": session["session_created_at_utc"],
        "notes": notes,
    }
    return record, issue


def usage_record_key(session_id: str, event: sqlite3.Row) -> str:
    identity = [
        event["event_id"],
        event["created_at"],
        event["turn_index"],
        event["model"],
        event["copilot_usage_model"],
        event["input_tokens"],
        event["cache_read_tokens"],
        event["cache_write_tokens"],
        event["output_tokens"],
    ]
    fingerprint = hashlib.sha256(
        json.dumps(identity, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{session_id}:usage:{event['event_id']}:{fingerprint}"


def legacy_usage_record_key(session_id: str, event_id: int) -> str:
    return f"{session_id}:usage:{event_id}"


def make_session_marker(session: dict, recorded_at: str) -> dict:
    note = "No assistant_usage_events in the local session store at collection time; usage is unknown, not confirmed zero."
    if session["origin_inferred"]:
        note += " Repository origin inferred from the matching GitHub owner/repository metadata."
    return {
        "schema_version": 1,
        "record_kind": "session_marker",
        "recorded_at_utc": recorded_at,
        "session_id": session["session_id"],
        "turn_id": UNKNOWN,
        "record_key": f"{session['session_id']}:session-marker:no-usage-events",
        "client": session["client"],
        "workspace_path": session["workspace_path"],
        "repo_remote": session["repo_remote"],
        "repo_name": session["repo_name"],
        "branch": session["branch"],
        "model": UNKNOWN,
        "input_tokens": None,
        "cached_input_tokens": None,
        "cache_write_tokens": None,
        "output_tokens": None,
        "actual_ai_credits": None,
        "estimated_ai_credits": None,
        "estimate_basis": None,
        "session_created_at_utc": session["session_created_at_utc"],
        "notes": note,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-origin", help="repository remote URL; defaults to the current workspace origin")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="workspace used to discover origin")
    parser.add_argument("--session-db", type=Path, default=DEFAULT_SESSION_DB, help="local Copilot session-store SQLite database")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER, help="append-only JSONL ledger")
    parser.add_argument("--dry-run", action="store_true", help="report planned records without appending")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # Step 1: Validate local paths and resolve the selected repository origin before mutation.
    args = parse_args(argv)
    started = datetime.now(timezone.utc)
    session_db = args.session_db.expanduser().resolve()
    ledger_path = args.ledger.expanduser().resolve()
    workspace_root = args.workspace.expanduser().resolve()

    if not session_db.is_file():
        print(f"error: session database not found: {session_db}", file=sys.stderr)
        return 2
    origin = rollup.normalize_repo_origin(args.repo_origin) if args.repo_origin else git_origin(str(workspace_root))
    if not origin:
        print("error: unable to resolve a repository origin; pass --repo-origin or run inside a Git workspace", file=sys.stderr)
        return 2
    if not rollup.repo_name_from_origin(origin):
        print(f"error: repository origin has no repository path: {origin}", file=sys.stderr)
        return 2

    # Step 2: Read matching session metadata and usage events from SQLite in read-only mode.
    try:
        connection = sqlite3.connect(f"{session_db.as_uri()}?mode=ro", uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        required_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('sessions', 'assistant_usage_events')"
            )
        }
        if required_tables != {"sessions", "assistant_usage_events"}:
            raise ValueError("session database is missing sessions or assistant_usage_events")
        sessions, out_of_scope = discover_sessions(connection, origin, workspace_root)
        event_rows = []
        session_ids = list(sessions)
        for offset in range(0, len(session_ids), 900):
            batch = session_ids[offset : offset + 900]
            if not batch:
                continue
            placeholders = ",".join("?" for _ in batch)
            event_rows.extend(
                connection.execute(
                    f"""
                    SELECT u.id AS event_id, u.session_id, u.turn_index, u.model,
                           u.copilot_usage_model, u.input_tokens, u.output_tokens,
                           u.cache_read_tokens, u.cache_write_tokens, u.created_at
                    FROM assistant_usage_events AS u
                    WHERE u.session_id IN ({placeholders})
                    ORDER BY u.session_id, u.id
                    """,
                    batch,
                ).fetchall()
            )
        connection.close()
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"error: unable to inspect session usage: {exc}", file=sys.stderr)
        return 2

    # Step 3: Fetch current official rates; a failure degrades estimates but never hides telemetry.
    try:
        prices, retrieved, _source = fetch_pricing()
    except (OSError, ValueError) as exc:
        prices = {}
        retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pricing_error = str(exc)
    else:
        pricing_error = None

    # Step 4: Plan only missing per-event rows and explicit unknown-usage session markers.
    events_by_session: dict[str, list[sqlite3.Row]] = {}
    for event in event_rows:
        events_by_session.setdefault(event["session_id"], []).append(event)

    recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        existing_keys, existing_sessions, legacy_aggregates = read_ledger_index(ledger_path)
        if not args.dry_run:
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        print(f"error: unable to read ledger: {exc}", file=sys.stderr)
        return 2

    records: list[dict] = []
    estimate_issues = 0
    skipped_legacy_sessions = 0
    usage_sessions = {session_id for session_id, events in events_by_session.items() if events}

    for session_id, session in sessions.items():
        if session_id in legacy_aggregates and session_id in usage_sessions:
            skipped_legacy_sessions += 1
            continue
        for event in events_by_session.get(session_id, []):
            key = usage_record_key(session_id, event)
            legacy_key = legacy_usage_record_key(session_id, event["event_id"])
            if key in existing_keys or legacy_key in existing_keys:
                continue
            record, issue = make_usage_record(event, session, prices, retrieved, recorded_at)
            if pricing_error:
                record["estimated_ai_credits"] = None
                record["estimate_basis"] = None
                record["notes"] = f"Estimated credits unavailable: official pricing fetch failed ({pricing_error}); actual billed credits are not exposed."
                issue = "official pricing fetch failed"
            if issue:
                estimate_issues += 1
            records.append(record)

        if not events_by_session.get(session_id) and session_id not in existing_sessions:
            records.append(make_session_marker(session, recorded_at))

    # Step 5: Append complete JSONL rows, sync the file, and verify their idempotency keys.
    try:
        if not args.dry_run and records:
            with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
                for record in records:
                    handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            written_keys, _, _ = read_ledger_index(ledger_path)
            missing_keys = sorted(record["record_key"] for record in records if record["record_key"] not in written_keys)
            if missing_keys:
                raise OSError(f"ledger verification failed for {len(missing_keys)} appended record keys")
    except OSError as exc:
        print(f"error: append failed after {len(records)} planned records: {exc}", file=sys.stderr)
        return 2

    newly_recorded_sessions = {
        record["session_id"] for record in records if record["record_kind"] == "usage_event"
    }
    marker_count = sum(record["record_kind"] == "session_marker" for record in records)
    estimated_records = sum(
        record["estimated_ai_credits"] is not None
        for record in records
        if record["record_kind"] == "usage_event"
    )
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    degraded = bool(pricing_error or estimate_issues or out_of_scope or not sessions)
    status = "degraded" if degraded else "success"
    print(
        f"status={status} origin={origin} sessions_found={len(sessions)} "
        f"sessions_with_usage={len(usage_sessions)} new_sessions={len(newly_recorded_sessions)} "
        f"usage_events_found={len(event_rows)} records_appended={0 if args.dry_run else len(records)} "
        f"records_planned={len(records)} estimated_events={estimated_records} "
        f"sessions_without_usage_events={marker_count} out_of_scope={out_of_scope} "
        f"legacy_aggregates_skipped={skipped_legacy_sessions} elapsed_seconds={elapsed:.2f}"
    )
    if pricing_error:
        print(f"warning: {pricing_error}", file=sys.stderr)
    if estimate_issues:
        print(f"warning: {estimate_issues} new usage events have no estimate; see ledger notes", file=sys.stderr)
    if out_of_scope:
        print(f"warning: {out_of_scope} candidate sessions had a different or unresolved repository identity", file=sys.stderr)
    if not sessions:
        print("warning: no local sessions matched this repository origin", file=sys.stderr)
    if marker_count:
        print(
            f"note: {marker_count} sessions were marked unknown because this session store had no usage events; "
            "that does not mean zero usage",
            file=sys.stderr,
        )
    if args.dry_run:
        print("dry-run: ledger was not changed")
    return 1 if degraded else 0


if __name__ == "__main__":
    raise SystemExit(main())
