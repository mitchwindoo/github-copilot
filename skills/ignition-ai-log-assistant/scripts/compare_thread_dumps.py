#!/usr/bin/env python3
"""Compare Ignition/JVM thread dumps by repeated thread name/state/top-frame signatures."""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


MAX_INPUT_BYTES = 4 * 1024 * 1024


def fail(message):
    print(json.dumps({"ok": False, "error": message}, indent=2, sort_keys=True))
    return 2


def read_text(path, max_bytes=MAX_INPUT_BYTES):
    size = path.stat().st_size
    with path.open("rb") as handle:
        data = handle.read(max_bytes)
    return data.decode("utf-8", errors="replace"), size, size > max_bytes


def parse_json_maybe(text):
    stripped = text.lstrip("\ufeff\r\n\t ")
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except Exception:
        return None


def clean_frame(frame):
    text = str(frame or "").strip()
    text = re.sub(r"^(?:at\s+)+", "", text)
    return text


def first_stack_frame(stack):
    if isinstance(stack, list):
        for frame in stack:
            cleaned = clean_frame(frame)
            if cleaned:
                return cleaned
    text = str(stack or "")
    for line in text.splitlines():
        cleaned = clean_frame(line)
        if cleaned:
            return cleaned
    return "<no-stack-frame>"


def normalize_state(value):
    text = str(value or "UNKNOWN").strip().upper()
    return text if text else "UNKNOWN"


def thread_signature(thread):
    name = str(thread.get("name") or "<unnamed>").strip()
    state = normalize_state(thread.get("state"))
    top_frame = thread.get("topFrame") or first_stack_frame(thread.get("stacktrace") or thread.get("stack") or thread.get("frames"))
    return "%s|%s|%s" % (name, state, top_frame)


def json_threads(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("threads"), list):
            return obj.get("threads")
        if isinstance(obj.get("threadDump"), dict) and isinstance(obj["threadDump"].get("threads"), list):
            return obj["threadDump"]["threads"]
    if isinstance(obj, list):
        return obj
    return None


def parse_json_dump(obj):
    threads = []
    for idx, row in enumerate(json_threads(obj) or []):
        if not isinstance(row, dict):
            continue
        stack = row.get("stacktrace", row.get("stack", row.get("frames", [])))
        threads.append(
            {
                "name": str(row.get("name") or row.get("threadName") or "thread-%s" % idx),
                "state": normalize_state(row.get("state") or row.get("threadState")),
                "topFrame": first_stack_frame(stack),
                "scope": row.get("scope"),
                "id": row.get("id"),
                "daemon": row.get("daemon"),
                "cpuUsage": row.get("cpuUsage"),
                "waitingFor": row.get("waitingFor"),
            }
        )
    return threads


HEADER_QUOTED_RE = re.compile(r'^"(?P<name>[^"]+)".*\b(?P<state>RUNNABLE|WAITING|TIMED_WAITING|BLOCKED|NEW|TERMINATED)\b', re.IGNORECASE)
HEADER_THREAD_RE = re.compile(r"^(?:Thread\s+)?(?P<name>[A-Za-z0-9_.:/# -]+?)\s+(?:state=|State:\s*)?(?P<state>RUNNABLE|WAITING|TIMED_WAITING|BLOCKED|NEW|TERMINATED)\b", re.IGNORECASE)
STATE_LINE_RE = re.compile(r"java\.lang\.Thread\.State:\s*(?P<state>RUNNABLE|WAITING|TIMED_WAITING|BLOCKED|NEW|TERMINATED)", re.IGNORECASE)


def parse_text_dump(text):
    threads = []
    current = None

    def flush():
        if current:
            threads.append(
                {
                    "name": current["name"],
                    "state": normalize_state(current.get("state")),
                    "topFrame": first_stack_frame(current.get("stacktrace", [])),
                }
            )

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r\n")
        stripped = line.strip()
        state_match = STATE_LINE_RE.search(stripped)
        if stripped.startswith("java.lang.Thread.State:"):
            if current and state_match:
                current["state"] = normalize_state(state_match.group("state"))
            continue
        if current and state_match:
            current["state"] = normalize_state(state_match.group("state"))
            continue
        match = HEADER_QUOTED_RE.match(stripped) or HEADER_THREAD_RE.match(stripped)
        if match:
            flush()
            current = {
                "name": match.group("name").strip(),
                "state": normalize_state(match.group("state")),
                "stacktrace": [],
            }
            continue
        if current and (line.lstrip().startswith("at ") or line.lstrip().startswith("- ")):
            current["stacktrace"].append(line.strip())
    flush()
    return threads


def parse_dump(path):
    text, size, truncated = read_text(path)
    obj = parse_json_maybe(text)
    if obj is not None and json_threads(obj) is not None:
        threads = parse_json_dump(obj)
        input_kind = "json"
    else:
        threads = parse_text_dump(text)
        input_kind = "text"
    rows = []
    for thread in threads:
        rows.append(
            {
                "name": thread.get("name"),
                "state": normalize_state(thread.get("state")),
                "topFrame": thread.get("topFrame") or first_stack_frame(thread.get("stacktrace")),
                "signature": thread_signature(thread),
                "scope": thread.get("scope"),
                "id": thread.get("id"),
                "daemon": thread.get("daemon"),
                "cpuUsage": thread.get("cpuUsage"),
                "waitingFor": thread.get("waitingFor"),
            }
        )
    return {
        "path": str(path),
        "fileName": path.name,
        "inputKind": input_kind,
        "inputBytes": size,
        "inputTruncated": truncated,
        "threadCount": len(rows),
        "stateCounts": dict(sorted(Counter(row["state"] for row in rows).items())),
        "threads": rows,
    }


def signature_record(signature, entries, dump_count):
    first = entries[0]
    dump_indexes = sorted({entry["dumpIndex"] for entry in entries})
    return {
        "signature": signature,
        "name": first["name"],
        "state": first["state"],
        "topFrame": first["topFrame"],
        "dumpIndexes": dump_indexes,
        "dumpFiles": [entry["dumpFile"] for entry in sorted(entries, key=lambda item: item["dumpIndex"])],
        "observedDumpCount": len(dump_indexes),
        "sampleCount": len(entries),
        "presentInAllDumps": len(dump_indexes) == dump_count,
    }


def compare(dumps, max_rows):
    by_signature = defaultdict(list)
    for dump_index, dump in enumerate(dumps):
        for row in dump["threads"]:
            by_signature[row["signature"]].append(
                {
                    "dumpIndex": dump_index,
                    "dumpFile": dump["fileName"],
                    "name": row["name"],
                    "state": row["state"],
                    "topFrame": row["topFrame"],
                }
            )
    dump_count = len(dumps)
    persistent = []
    repeated = []
    transient = []
    for signature, entries in by_signature.items():
        record = signature_record(signature, entries, dump_count)
        if record["presentInAllDumps"]:
            persistent.append(record)
        elif record["observedDumpCount"] >= 2:
            repeated.append(record)
        else:
            transient.append(record)
    key = lambda item: (-item["observedDumpCount"], item["name"], item["state"], item["topFrame"])
    persistent.sort(key=key)
    repeated.sort(key=key)
    transient.sort(key=key)
    return {
        "persistentAcrossAll": persistent[:max_rows],
        "repeatedNotPersistent": repeated[:max_rows],
        "transient": transient[:max_rows],
        "persistentCount": len(persistent),
        "repeatedNotPersistentCount": len(repeated),
        "transientCount": len(transient),
        "uniqueSignatureCount": len(by_signature),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare Ignition/JVM thread dumps by repeated signatures.")
    parser.add_argument("dumps", nargs="+", help="Thread dump JSON/text files in capture order.")
    parser.add_argument("--json-out", help="Write JSON result to this path.")
    parser.add_argument("--max-rows", type=int, default=50)
    args = parser.parse_args(argv)

    if len(args.dumps) < 2:
        return fail("provide at least two thread dump files")
    if args.max_rows < 1:
        return fail("--max-rows must be at least 1")

    parsed_dumps = []
    for raw in args.dumps:
        path = Path(raw)
        if not path.is_file():
            return fail("thread dump file does not exist or is not a file: %s" % path)
        try:
            dump = parse_dump(path)
        except Exception as exc:
            return fail("failed to parse %s: %s" % (path, exc))
        if dump["threadCount"] == 0:
            return fail("no thread rows parsed from %s" % path)
        parsed_dumps.append(dump)

    comparison = compare(parsed_dumps, args.max_rows)
    result = {
        "ok": True,
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "dumpCount": len(parsed_dumps),
        "dumps": [
            {k: v for k, v in dump.items() if k != "threads"}
            for dump in parsed_dumps
        ],
        "comparison": comparison,
        "boundary": "Thread dumps are thread-state evidence. Persistent signatures require correlation with logs or metrics before root-cause claims.",
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
        result["jsonOut"] = str(Path(args.json_out))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
