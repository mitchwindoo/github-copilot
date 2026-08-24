#!/usr/bin/env python3
"""Run a read-only repeated Perspective navigation lifecycle profile."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple

from collect_profile import (  # noqa: E402
    RunnerClient,
    append_ndjson,
    browser_env,
    choose_route,
    ensure_profile_function,
    metric_tokens,
    ok,
    resolve_config,
    response,
    utc_now,
    write_json,
)


SCRIPT_DIR = Path(__file__).resolve().parent


def epoch_millis() -> int:
    return int(time.time() * 1000)


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def avg(values: Iterable[float]) -> Optional[float]:
    nums = list(values)
    return mean(nums) if nums else None


def numeric_summary(values: Iterable[Any]) -> Dict[str, Any]:
    nums = sorted(value for value in (to_float(item) for item in values) if value is not None)
    if not nums:
        return {"count": 0}
    return {
        "count": len(nums),
        "min": nums[0],
        "median": nums[int((len(nums) - 1) * 0.5)],
        "p95": nums[int((len(nums) - 1) * 0.95)],
        "max": nums[-1],
    }


def delta(first: Optional[float], second: Optional[float]) -> Optional[float]:
    if first is None or second is None:
        return None
    return second - first


def format_number(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def browser_counts(row: Dict[str, Any]) -> Tuple[int, int, List[float]]:
    query = row.get("perspectiveSessionsQuery", {})
    browser_count = 0
    page_count = 0
    recent_bytes: List[float] = []
    if not isinstance(query, dict):
        return browser_count, page_count, recent_bytes
    sessions = query.get("sessions", [])
    if not isinstance(sessions, list):
        return browser_count, page_count, recent_bytes
    for session in sessions:
        if not isinstance(session, dict):
            continue
        if str(session.get("sessionScope", "")).lower() != "browser":
            continue
        browser_count += 1
        page_count += int(to_float(session.get("activePages")) or 0)
        recent = to_float(session.get("recentBytesSent"))
        if recent is not None:
            recent_bytes.append(recent)
    return browser_count, page_count, recent_bytes


def browser_counts_from_query(query: Dict[str, Any]) -> Dict[str, int]:
    sessions = query.get("sessions", [])
    browser_sessions = 0
    browser_pages = 0
    if isinstance(sessions, list):
        for session in sessions:
            if not isinstance(session, dict):
                continue
            if str(session.get("sessionScope", "")).lower() == "browser":
                browser_sessions += 1
                browser_pages += int(to_float(session.get("activePages")) or 0)
    return {"browserSessions": browser_sessions, "browserPages": browser_pages}


def wait_for_clean_baseline(
    client: RunnerClient,
    out_dir: Path,
    run_id: str,
    project: str,
    feature_set: set[str],
    max_browser_sessions: int,
    timeout_sec: float,
    interval_sec: float,
) -> Dict[str, Any]:
    started = time.time()
    attempt = 0
    if "perspectiveSessionsQuery" not in feature_set:
        result = {
            "enabled": True,
            "ok": False,
            "reason": "perspectiveSessionsQuery feature not present",
            "sampleCount": 0,
            "maxBrowserSessions": max_browser_sessions,
        }
        append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"sampledAt": utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-baselineWait-{attempt:03d}"
        query = response(
            client.call(
                request_id,
                {
                    "action": "perspectiveSessionsQuery",
                    "requestId": request_id,
                    "targetProject": project,
                    "maxResults": 50,
                },
            )
        )
        counts = browser_counts_from_query(query)
        elapsed = time.time() - started
        row = {
            "attempt": attempt,
            "sampledAt": utc_now(),
            "elapsedSeconds": round(elapsed, 3),
            "maxBrowserSessions": max_browser_sessions,
            **counts,
            "ok": query.get("ok") is not False,
            "clean": counts["browserSessions"] <= max_browser_sessions,
        }
        append_ndjson(out_dir / "baseline-wait-samples.ndjson", row)
        if row["clean"]:
            return {
                "enabled": True,
                "ok": True,
                "timedOut": False,
                "sampleCount": attempt + 1,
                "elapsedSeconds": round(elapsed, 3),
                "maxBrowserSessions": max_browser_sessions,
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
            }
        if elapsed >= timeout_sec:
            return {
                "enabled": True,
                "ok": False,
                "timedOut": True,
                "sampleCount": attempt + 1,
                "elapsedSeconds": round(elapsed, 3),
                "maxBrowserSessions": max_browser_sessions,
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
            }
        attempt += 1
        time.sleep(max(interval_sec, 0.1))


def metric_items(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    snapshot = row.get("metricsSnapshot", {})
    if not isinstance(snapshot, dict):
        return []
    items = snapshot.get("metrics", [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def metric_value(item: Dict[str, Any]) -> Optional[float]:
    for key in ("value", "count", "meanRate", "p95"):
        parsed = to_float(item.get(key))
        if parsed is not None:
            return parsed
    return None


def summarize_metric_family(rows: List[Dict[str, Any]], phase: str, contains: Tuple[str, ...]) -> Dict[str, Any]:
    values: List[float] = []
    names: List[str] = []
    for row in rows:
        if row.get("phase") != phase:
            continue
        for item in metric_items(row):
            name = str(item.get("name", "")).lower()
            if not all(part in name for part in contains):
                continue
            value = metric_value(item)
            if value is not None:
                values.append(value)
                if len(names) < 10:
                    names.append(str(item.get("name", "")))
    return {"avg": avg(values), "count": len(values), "sampleNames": sorted(set(names))}


def summarize_phase(rows: List[Dict[str, Any]], phase: str) -> Dict[str, Any]:
    heap_values: List[float] = []
    cpu_values: List[float] = []
    thread_values: List[float] = []
    returned_counts: List[float] = []
    browser_sessions: List[float] = []
    browser_pages: List[float] = []
    browser_recent_bytes: List[float] = []
    queue_lengths: List[float] = []
    for row in rows:
        if row.get("phase") != phase:
            continue
        perf = row.get("gatewayPerformanceSnapshot", {})
        if isinstance(perf, dict):
            heap = perf.get("heap", {})
            cpu = perf.get("cpu", {})
            threads = perf.get("threads", {})
            heap_used = to_float(heap.get("usedBytes")) if isinstance(heap, dict) else None
            process_cpu = to_float(cpu.get("processCpuLoad")) if isinstance(cpu, dict) else None
            thread_total = to_float(threads.get("total")) if isinstance(threads, dict) else None
            if heap_used is not None:
                heap_values.append(heap_used)
            if process_cpu is not None:
                cpu_values.append(process_cpu)
            if thread_total is not None:
                thread_values.append(thread_total)
        query = row.get("perspectiveSessionsQuery", {})
        if isinstance(query, dict):
            returned = to_float(query.get("returnedCount"))
            if returned is not None:
                returned_counts.append(returned)
            session_count, page_count, recent_bytes = browser_counts(row)
            browser_sessions.append(float(session_count))
            browser_pages.append(float(page_count))
            browser_recent_bytes.extend(recent_bytes)
        for item in metric_items(row):
            if str(item.get("name", "")).endswith(".queue-length"):
                queue = to_float(item.get("value"))
                if queue is not None:
                    queue_lengths.append(queue)
    return {
        "sampleCount": sum(1 for row in rows if row.get("phase") == phase),
        "heapUsedBytesAvg": avg(heap_values),
        "processCpuLoadAvg": avg(cpu_values),
        "threadTotalAvg": avg(thread_values),
        "sessionReturnedCountAvg": avg(returned_counts),
        "browserSessionCountAvg": avg(browser_sessions),
        "browserActivePagesAvg": avg(browser_pages),
        "browserRecentBytesSentAvg": avg(browser_recent_bytes),
        "sessionQueueLengthAvg": avg(queue_lengths),
        "metricSignals": {
            "page": summarize_metric_family(rows, phase, ("perspective", "page")),
            "view": summarize_metric_family(rows, phase, ("perspective", "view")),
            "component": summarize_metric_family(rows, phase, ("perspective", "component")),
            "binding": summarize_metric_family(rows, phase, ("perspective", "binding")),
            "message": summarize_metric_family(rows, phase, ("perspective", "message")),
            "queue": summarize_metric_family(rows, phase, ("queue",)),
        },
    }


def changed_resource(label: str, before: Dict[str, Any], after: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    before_hash = before.get("viewSha256")
    after_hash = after.get("viewSha256")
    if before_hash and after_hash and before_hash != after_hash:
        return {"resource": label, "beforeViewSha256": before_hash, "afterViewSha256": after_hash}
    return None


def active_step_for_sample(steps: List[Dict[str, Any]], sampled_epoch_millis: int) -> Optional[Dict[str, Any]]:
    for step in steps:
        start = to_float(step.get("startedEpochMillis"))
        finish = to_float(step.get("finishedEpochMillis"))
        if start is not None and finish is not None and start <= sampled_epoch_millis <= finish:
            return step
    return None


def annotate_samples_with_steps(rows: List[Dict[str, Any]], steps: List[Dict[str, Any]]) -> None:
    for row in rows:
        sampled = to_float(row.get("sampledEpochMillis"))
        if sampled is None:
            continue
        step = active_step_for_sample(steps, int(sampled))
        if step:
            row["browserStep"] = {"cycle": step.get("cycle"), "phase": step.get("phase")}


def build_browser_command(args: argparse.Namespace, out_dir: Path) -> List[str]:
    command = [
        args.browser_node,
        str(SCRIPT_DIR / "browser_navigation_cycles.mjs"),
        "--control-url",
        args.browser_control_url,
        "--target-url",
        args.browser_target_url,
        "--cycles",
        str(args.cycles),
        "--out-dir",
        str(out_dir),
        "--control-ready-selector",
        args.control_ready_selector,
        "--target-ready-selector",
        args.target_ready_selector,
        "--timeout-ms",
        str(int(args.browser_timeout_sec * 1000)),
        "--settle-ms",
        str(args.browser_settle_ms),
        "--viewport",
        args.browser_viewport,
        "--url-alias",
        args.browser_url_alias or args.gateway_alias,
    ]
    if args.control_ready_text:
        command.extend(["--control-ready-text", args.control_ready_text])
    if args.target_ready_text:
        command.extend(["--target-ready-text", args.target_ready_text])
    return command


def redact_navigation_command(command: List[str]) -> List[str]:
    redacted = list(command)
    redact_next = {"--control-url", "--target-url"}
    for index, value in enumerate(redacted[:-1]):
        if value in redact_next:
            redacted[index + 1] = "<redacted-browser-url>"
    return redacted


def start_browser(args: argparse.Namespace, out_dir: Path) -> Dict[str, Any]:
    stdout_path = out_dir / "browser-navigation.stdout.txt"
    stderr_path = out_dir / "browser-navigation.stderr.txt"
    command = build_browser_command(args, out_dir)
    stdout_handle = stdout_path.open("w", encoding="utf-8", newline="\n")
    stderr_handle = stderr_path.open("w", encoding="utf-8", newline="\n")
    info: Dict[str, Any] = {
        "startedAt": utc_now(),
        "command": redact_navigation_command(command),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
    }
    try:
        process = subprocess.Popen(command, stdout=stdout_handle, stderr=stderr_handle, env=browser_env(args))
    except Exception as exc:
        stdout_handle.close()
        stderr_handle.close()
        info.update({"started": False, "error": repr(exc)})
        return info
    info.update({"started": True, "process": process, "stdoutHandle": stdout_handle, "stderrHandle": stderr_handle})
    return info


def finish_browser(info: Dict[str, Any], timeout_sec: int) -> Dict[str, Any]:
    process = info.get("process")
    if process is None:
        return {key: value for key, value in info.items() if key not in {"stdoutHandle", "stderrHandle"}}
    timed_out = False
    try:
        exit_code = process.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        exit_code = process.wait(timeout=5)
    finally:
        for key in ("stdoutHandle", "stderrHandle"):
            handle = info.get(key)
            if handle:
                handle.close()
    out = {key: value for key, value in info.items() if key not in {"process", "stdoutHandle", "stderrHandle"}}
    out.update({"finishedAt": utc_now(), "exitCode": exit_code, "timedOut": timed_out})
    return out


def sample_once(
    client: RunnerClient,
    run_id: str,
    project: str,
    phase: str,
    index: int,
    tokens: List[str],
    feature_set: set[str],
) -> Dict[str, Any]:
    prefix = f"{run_id}-{phase}-{index:03d}"
    row: Dict[str, Any] = {
        "phase": phase,
        "sampleIndex": index,
        "sampledAt": utc_now(),
        "sampledEpochMillis": epoch_millis(),
    }
    if tokens and "metricsSnapshot" in feature_set:
        row["metricsSnapshot"] = response(
            client.call(
                f"{prefix}-metricsSnapshot",
                {
                    "action": "metricsSnapshot",
                    "requestId": f"{prefix}-metricsSnapshot",
                    "metricTokens": tokens,
                    "maxMetrics": len(tokens),
                },
            )
        )
    else:
        row["metricsSnapshot"] = {"ok": False, "missing": True, "reason": "No metric tokens or feature not present"}
    if "gatewayPerformanceSnapshot" in feature_set:
        row["gatewayPerformanceSnapshot"] = response(
            client.call(
                f"{prefix}-gatewayPerformanceSnapshot",
                {"action": "gatewayPerformanceSnapshot", "requestId": f"{prefix}-gatewayPerformanceSnapshot"},
            )
        )
    else:
        row["gatewayPerformanceSnapshot"] = {"ok": False, "missing": True, "reason": "feature not present"}
    if "perspectiveSessionsQuery" in feature_set:
        row["perspectiveSessionsQuery"] = response(
            client.call(
                f"{prefix}-perspectiveSessionsQuery",
                {
                    "action": "perspectiveSessionsQuery",
                    "requestId": f"{prefix}-perspectiveSessionsQuery",
                    "targetProject": project,
                    "maxResults": 50,
                },
            )
        )
    else:
        row["perspectiveSessionsQuery"] = {"ok": False, "missing": True, "reason": "feature not present"}
    return row


def append_sample_files(out_dir: Path, row: Dict[str, Any]) -> None:
    append_ndjson(out_dir / "navigation-samples.ndjson", row)
    append_ndjson(
        out_dir / "gateway-samples.ndjson",
        {
            "phase": row.get("phase"),
            "sampleIndex": row.get("sampleIndex"),
            "sampledAt": row.get("sampledAt"),
            "sampledEpochMillis": row.get("sampledEpochMillis"),
            "browserStep": row.get("browserStep"),
            "metricsSnapshot": row.get("metricsSnapshot"),
            "gatewayPerformanceSnapshot": row.get("gatewayPerformanceSnapshot"),
        },
    )
    append_ndjson(
        out_dir / "perspective-session-samples.ndjson",
        {
            "phase": row.get("phase"),
            "sampleIndex": row.get("sampleIndex"),
            "sampledAt": row.get("sampledAt"),
            "sampledEpochMillis": row.get("sampledEpochMillis"),
            "browserStep": row.get("browserStep"),
            "perspectiveSessionsQuery": row.get("perspectiveSessionsQuery"),
        },
    )


def sample_phase(
    client: RunnerClient,
    out_dir: Path,
    run_id: str,
    project: str,
    phase: str,
    count: int,
    interval_sec: float,
    tokens: List[str],
    feature_set: set[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index in range(max(count, 0)):
        row = sample_once(client, run_id, project, phase, index, tokens, feature_set)
        append_sample_files(out_dir, row)
        rows.append(row)
        if index < count - 1:
            time.sleep(interval_sec)
    return rows


def sample_while_browser_runs(
    client: RunnerClient,
    out_dir: Path,
    run_id: str,
    project: str,
    browser_info: Dict[str, Any],
    interval_sec: float,
    tokens: List[str],
    feature_set: set[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    process = browser_info.get("process")
    index = 0
    if process is None:
        row = sample_once(client, run_id, project, "during", index, tokens, feature_set)
        append_sample_files(out_dir, row)
        return [row]
    while process.poll() is None:
        row = sample_once(client, run_id, project, "during", index, tokens, feature_set)
        append_sample_files(out_dir, row)
        rows.append(row)
        index += 1
        time.sleep(interval_sec)
    if not rows:
        row = sample_once(client, run_id, project, "during", index, tokens, feature_set)
        append_sample_files(out_dir, row)
        rows.append(row)
    return rows


def summarize_browser_steps(browser_summary: Dict[str, Any]) -> Dict[str, Any]:
    steps = browser_summary.get("cycles", [])
    if not isinstance(steps, list):
        steps = []
    targets = [step for step in steps if isinstance(step, dict) and step.get("phase") == "target"]
    control_before = [step for step in steps if isinstance(step, dict) and step.get("phase") == "control-before"]
    control_after = [step for step in steps if isinstance(step, dict) and step.get("phase") == "control-after"]
    target_elapsed = [step.get("elapsedWallMs") for step in targets]
    target_dom = [step.get("domNodeCount") for step in targets]
    target_heap = [
        step.get("heap", {}).get("usedJSHeapSize")
        for step in targets
        if isinstance(step.get("heap"), dict)
    ]
    control_return_elapsed: List[float] = []
    control_return_dom: List[float] = []
    for after in control_after:
        before = next((item for item in control_before if item.get("cycle") == after.get("cycle")), None)
        if not before:
            continue
        elapsed_delta = delta(to_float(before.get("elapsedWallMs")), to_float(after.get("elapsedWallMs")))
        dom_delta = delta(to_float(before.get("domNodeCount")), to_float(after.get("domNodeCount")))
        if elapsed_delta is not None:
            control_return_elapsed.append(elapsed_delta)
        if dom_delta is not None:
            control_return_dom.append(dom_delta)
    aggregate = browser_summary.get("aggregate", {}) if isinstance(browser_summary.get("aggregate"), dict) else {}
    return {
        "cyclesRequested": browser_summary.get("cyclesRequested"),
        "cyclesCompleted": browser_summary.get("cyclesCompleted"),
        "stepCount": browser_summary.get("stepCount"),
        "readyStepCount": aggregate.get("readyStepCount"),
        "targetElapsedMs": numeric_summary(target_elapsed),
        "targetDomNodeCount": numeric_summary(target_dom),
        "targetJSHeapUsedBytes": numeric_summary(target_heap),
        "controlAfterMinusBeforeElapsedMs": numeric_summary(control_return_elapsed),
        "controlAfterMinusBeforeDomNodes": numeric_summary(control_return_dom),
        "targetElapsedStrictlyIncreasing": aggregate.get("targetElapsedStrictlyIncreasing"),
        "targetElapsedLastMinusFirstMs": aggregate.get("targetElapsedLastMinusFirstMs"),
        "targetDomLastMinusFirst": aggregate.get("targetDomLastMinusFirst"),
        "maxControlAfterMinusBeforeElapsedMs": aggregate.get("maxControlAfterMinusBeforeElapsedMs"),
        "maxControlAfterMinusBeforeDomNodes": aggregate.get("maxControlAfterMinusBeforeDomNodes"),
    }


def build_interpretation(summary: Dict[str, Any]) -> List[str]:
    notes = [
        "This is repeated-navigation lifecycle observation, not leak proof and not remediation causality.",
        "Use control-after-minus-control-before deltas to separate route-specific retention from general Gateway/session background noise.",
    ]
    browser = summary.get("browser", {})
    target_stats = browser.get("targetElapsedMs", {})
    if browser.get("targetElapsedStrictlyIncreasing"):
        notes.append("Target ready time increased strictly across completed cycles; repeat and correlate with Gateway/session counts before calling it a lifecycle problem.")
    target_delta = to_float(browser.get("targetElapsedLastMinusFirstMs"))
    median = to_float(target_stats.get("median"))
    if target_delta is not None and median and target_delta > median * 0.15:
        notes.append("Target final-minus-first ready time exceeded 15% of median target ready time; this is a flag for repeat testing, not a root cause.")
    phases = summary.get("phases", {})
    pre_pages = phases.get("pre", {}).get("browserActivePagesAvg")
    post_pages = phases.get("post", {}).get("browserActivePagesAvg")
    if pre_pages is not None and post_pages is not None and post_pages > pre_pages:
        notes.append("Post-navigation browser active pages averaged above pre; compare to configured Perspective timeout before using leak language.")
    control_dom = browser.get("controlAfterMinusBeforeDomNodes", {})
    if to_float(control_dom.get("max")) is not None and to_float(control_dom.get("max")) > 0:
        notes.append("At least one control return had more DOM nodes than the matching control-before step; inspect per-cycle browser evidence for retained UI state.")
    return notes


def make_report(out_dir: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    lines = [
        "# Perspective Repeated Navigation Lifecycle Profile",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Project: `{manifest.get('project', '')}`",
        f"Control route: `{manifest.get('controlRoute', '')}`",
        f"Target route: `{manifest.get('targetRoute', '')}`",
        f"Target view: `{manifest.get('targetView', '')}`",
        f"Cycles completed: `{summary.get('browser', {}).get('cyclesCompleted')}` / `{summary.get('browser', {}).get('cyclesRequested')}`",
        "",
        "## Browser Cycle Summary",
        "",
        "| Signal | Count | Min | Median | P95 | Max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    baseline_wait = summary.get("baselineWait", {})
    if baseline_wait.get("enabled"):
        lines.insert(
            8,
            "Baseline wait: `{}` after `{}` seconds, final browser sessions `{}`.".format(
                "clean" if baseline_wait.get("ok") else "timeout",
                format_number(baseline_wait.get("elapsedSeconds")),
                format_number(baseline_wait.get("finalBrowserSessions")),
            ),
        )
    for label, key in [
        ("Target ready wall ms", "targetElapsedMs"),
        ("Target DOM nodes", "targetDomNodeCount"),
        ("Target JS heap bytes", "targetJSHeapUsedBytes"),
        ("Control return ready delta ms", "controlAfterMinusBeforeElapsedMs"),
        ("Control return DOM delta", "controlAfterMinusBeforeDomNodes"),
    ]:
        item = summary.get("browser", {}).get(key, {})
        lines.append(
            "| {label} | {count} | {min} | {median} | {p95} | {max} |".format(
                label=label,
                count=item.get("count", 0),
                min=format_number(item.get("min")),
                median=format_number(item.get("median")),
                p95=format_number(item.get("p95")),
                max=format_number(item.get("max")),
            )
        )
    lines.extend(["", "## Gateway And Session Phases", ""])
    lines.extend(
        [
            "| Phase | Samples | Browser sessions avg | Browser pages avg | Heap used avg | CPU avg | Queue avg |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for phase in ("pre", "during", "post"):
        item = summary.get("phases", {}).get(phase, {})
        lines.append(
            "| {phase} | {samples} | {sessions} | {pages} | {heap} | {cpu} | {queue} |".format(
                phase=phase,
                samples=item.get("sampleCount", 0),
                sessions=format_number(item.get("browserSessionCountAvg")),
                pages=format_number(item.get("browserActivePagesAvg")),
                heap=format_number(item.get("heapUsedBytesAvg")),
                cpu=format_number(item.get("processCpuLoadAvg")),
                queue=format_number(item.get("sessionQueueLengthAvg")),
            )
        )
    lines.extend(["", "## Interpretation", ""])
    for note in summary.get("interpretation", []):
        lines.append(f"- {note}")
    lines.extend(["", "## Integrity", ""])
    lines.append(f"- Changed resources: `{len(summary.get('changedResources', []))}`")
    lines.append(f"- Missing evidence entries: `{len(manifest.get('missingEvidence', []))}`")
    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a read-only repeated Perspective navigation lifecycle profile.")
    parser.add_argument("--endpoint", help="Runner Web Dev endpoint. Env fallback matches collect_profile.py.")
    parser.add_argument("--token", help="Runner token. Env fallback matches collect_profile.py.")
    parser.add_argument("--project", help="Target project. Env fallback matches collect_profile.py.")
    parser.add_argument("--control-route", default="/", help="Control Perspective route/page path. Default: /")
    parser.add_argument("--target-route", required=True, help="Target Perspective route/page path.")
    parser.add_argument("--control-view", help="Control view path. Defaults to route inventory match.")
    parser.add_argument("--target-view", help="Target view path. Defaults to route inventory match.")
    parser.add_argument("--run-id", required=True, help="Stable run identifier.")
    parser.add_argument("--out-dir", required=True, help="Evidence output directory.")
    parser.add_argument("--browser-control-url", required=True, help="Control route URL for browser navigation.")
    parser.add_argument("--browser-target-url", required=True, help="Target route URL for browser navigation.")
    parser.add_argument("--cycles", type=int, default=20, help="Control -> target -> control cycles. Default: 20.")
    parser.add_argument("--control-ready-selector", default="body", help="CSS selector for control readiness.")
    parser.add_argument("--target-ready-selector", default="body", help="CSS selector for target readiness.")
    parser.add_argument("--control-ready-text", default="", help="Optional control page body text readiness marker.")
    parser.add_argument("--target-ready-text", default="", help="Optional target page body text readiness marker.")
    parser.add_argument("--browser-viewport", default="1366x768", help="Browser viewport.")
    parser.add_argument("--browser-timeout-sec", type=float, default=45.0, help="Per-navigation browser timeout.")
    parser.add_argument("--browser-settle-ms", type=int, default=500, help="Post-ready settle wait per navigation.")
    parser.add_argument("--browser-node", default="node", help="Node executable for browser_navigation_cycles.mjs.")
    parser.add_argument("--browser-node-modules", default="", help="Optional node_modules path for Playwright.")
    parser.add_argument("--browser-url-alias", default="", help="Non-secret browser URL alias.")
    parser.add_argument("--gateway-alias", default="configured-gateway", help="Non-secret Gateway alias.")
    parser.add_argument("--timeout-sec", type=int, default=30, help="Runner HTTP timeout.")
    parser.add_argument("--max-metrics", type=int, default=25, help="Maximum metric tokens to sample.")
    parser.add_argument("--pre-samples", type=int, default=2, help="Samples before navigation starts.")
    parser.add_argument("--post-samples", type=int, default=4, help="Samples after navigation completes.")
    parser.add_argument("--interval-sec", type=float, default=2.0, help="Gateway/session sample interval.")
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Wait for retained browser sessions to fall below the configured threshold before pre samples.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=180.0, help="Maximum seconds to wait for a clean baseline.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Abort when clean baseline is requested but not reached.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.cycles <= 0:
        raise SystemExit("--cycles must be > 0")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0:
        raise SystemExit("--baseline-wait-timeout-sec must be >= 0")
    endpoint, token, project = resolve_config(args)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = RunnerClient(endpoint, token, out_dir, args.timeout_sec)
    profile_view = ensure_profile_function()
    missing: List[Dict[str, str]] = []

    health_record = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health = response(health_record)
    features = health.get("features", [])
    feature_set = set(features if isinstance(features, list) else [key for key, value in features.items() if value])

    projects_record = client.call(f"{args.run_id}-projectsList", {"action": "projectsList", "requestId": f"{args.run_id}-projectsList", "maxResults": 100})
    if not project:
        projects = response(projects_record).get("projects", [])
        if projects and isinstance(projects[0], dict):
            project = str(projects[0].get("projectName") or projects[0].get("name") or "")
        elif projects:
            project = str(projects[0])
    if not project:
        raise SystemExit("Target project could not be resolved. Use --project or IGNITION_TARGET_PROJECT.")

    routes_record = client.call(
        f"{args.run_id}-routesList",
        {"action": "routesList", "requestId": f"{args.run_id}-routesList", "targetProject": project, "maxResults": 250},
    )
    routes = response(routes_record).get("routes", [])
    routes_list = routes if isinstance(routes, list) else []
    control_route, control_view = choose_route(routes_list, args.control_route, args.control_view or "")
    target_route, target_view = choose_route(routes_list, args.target_route, args.target_view or "")
    if not control_view:
        raise SystemExit("Control view could not be resolved. Use --control-view.")
    if not target_view:
        raise SystemExit("Target view could not be resolved. Use --target-view.")

    control_view_record = client.call(
        f"{args.run_id}-control-viewRead-before",
        {
            "action": "viewRead",
            "requestId": f"{args.run_id}-control-viewRead-before",
            "targetProject": project,
            "viewPath": control_view,
            "allowedViewPrefix": "",
            "includeViewJson": True,
            "includeResourceJson": True,
        },
    )
    target_view_record = client.call(
        f"{args.run_id}-target-viewRead-before",
        {
            "action": "viewRead",
            "requestId": f"{args.run_id}-target-viewRead-before",
            "targetProject": project,
            "viewPath": target_view,
            "allowedViewPrefix": "",
            "includeViewJson": True,
            "includeResourceJson": True,
        },
    )
    for label, route, view in [("control", control_route, control_view), ("target", target_route, target_view)]:
        client.call(
            f"{args.run_id}-{label}-pageValidate-before",
            {
                "action": "pageValidate",
                "requestId": f"{args.run_id}-{label}-pageValidate-before",
                "targetProject": project,
                "pagePath": route,
                "expectedViewPath": view,
                "allowedRoutePrefix": "",
                "allowedViewPrefix": "",
                "includeHashes": True,
            },
        )

    control_view_response = response(control_view_record)
    target_view_response = response(target_view_record)
    write_json(out_dir / "control-view-read.json", control_view_response)
    write_json(out_dir / "target-view-read.json", target_view_response)
    control_static = profile_view(control_view_response, "control-view-read.json")
    target_static = profile_view(target_view_response, "target-view-read.json")
    write_json(out_dir / "control-static-profile.json", control_static)
    write_json(out_dir / "target-static-profile.json", target_static)
    write_json(out_dir / "static-profile.json", target_static)

    tokens: List[str] = []
    if "metricsList" in feature_set:
        metrics_record = client.call(
            f"{args.run_id}-metricsList",
            {
                "action": "metricsList",
                "requestId": f"{args.run_id}-metricsList",
                "nameContains": ["Perspective", "perspective"],
                "maxResults": min(max(args.max_metrics * 3, args.max_metrics), 250),
            },
        )
        write_json(out_dir / "metrics-list.json", response(metrics_record))
        tokens = metric_tokens(response(metrics_record), max(0, min(args.max_metrics, 100)))
        if not tokens:
            missing.append({"name": "metricsSnapshot", "reason": "metricsList returned no metric tokens"})
    else:
        missing.append({"name": "metricsList", "reason": "runner health.features does not include metricsList"})

    baseline_wait: Dict[str, Any] = {"enabled": False}
    if args.wait_for_clean_baseline:
        baseline_wait = wait_for_clean_baseline(
            client,
            out_dir,
            args.run_id,
            project,
            feature_set,
            args.baseline_max_browser_sessions,
            args.baseline_wait_timeout_sec,
            args.baseline_wait_interval_sec,
        )
        write_json(out_dir / "baseline-wait.json", baseline_wait)
        if args.fail_on_baseline_timeout and not baseline_wait.get("ok"):
            raise SystemExit("Clean baseline was not reached before timeout.")

    rows: List[Dict[str, Any]] = []
    rows.extend(sample_phase(client, out_dir, args.run_id, project, "pre", args.pre_samples, args.interval_sec, tokens, feature_set))
    browser_info = start_browser(args, out_dir)
    rows.extend(sample_while_browser_runs(client, out_dir, args.run_id, project, browser_info, args.interval_sec, tokens, feature_set))
    browser_timeout = int((args.browser_timeout_sec + (args.browser_settle_ms / 1000.0) + 5) * args.cycles * 3)
    browser_info = finish_browser(browser_info, browser_timeout)
    rows.extend(sample_phase(client, out_dir, args.run_id, project, "post", args.post_samples, args.interval_sec, tokens, feature_set))

    browser_summary = read_json(out_dir / "browser-summary.json")
    browser_steps = browser_summary.get("cycles", []) if isinstance(browser_summary.get("cycles"), list) else []
    annotate_samples_with_steps(rows, [step for step in browser_steps if isinstance(step, dict)])
    write_json(out_dir / "navigation-samples.annotated.json", rows)

    control_after_record = client.call(
        f"{args.run_id}-control-viewRead-after",
        {
            "action": "viewRead",
            "requestId": f"{args.run_id}-control-viewRead-after",
            "targetProject": project,
            "viewPath": control_view,
            "allowedViewPrefix": "",
            "includeViewJson": False,
            "includeResourceJson": True,
        },
    )
    target_after_record = client.call(
        f"{args.run_id}-target-viewRead-after",
        {
            "action": "viewRead",
            "requestId": f"{args.run_id}-target-viewRead-after",
            "targetProject": project,
            "viewPath": target_view,
            "allowedViewPrefix": "",
            "includeViewJson": False,
            "includeResourceJson": True,
        },
    )
    for label, route, view in [("control", control_route, control_view), ("target", target_route, target_view)]:
        client.call(
            f"{args.run_id}-{label}-pageValidate-after",
            {
                "action": "pageValidate",
                "requestId": f"{args.run_id}-{label}-pageValidate-after",
                "targetProject": project,
                "pagePath": route,
                "expectedViewPath": view,
                "allowedRoutePrefix": "",
                "allowedViewPrefix": "",
                "includeHashes": True,
            },
        )

    log_record = client.call(
        f"{args.run_id}-logQuery",
        {
            "action": "logQuery",
            "requestId": f"{args.run_id}-logQuery",
            "sinceMinutes": 15,
            "levels": ["ERROR", "WARN"],
            "textContains": "Perspective",
            "maxResults": 50,
            "tailBytes": 262144,
        },
    )
    write_json(out_dir / "logs.json", response(log_record))
    write_json(out_dir / "thread-excerpts.json", {"ok": False, "missing": True, "reason": "No active freeze/backlog/CPU-spike trigger requested"})
    write_json(out_dir / "comparison.json", {"ok": False, "missing": True, "reason": "No remediation A/B comparison requested"})

    changed_resources = [
        item
        for item in [
            changed_resource("control view", control_view_response, response(control_after_record)),
            changed_resource("target view", target_view_response, response(target_after_record)),
        ]
        if item
    ]
    if browser_info.get("exitCode") not in (0, None):
        missing.append({"name": "browserNavigationProbe", "reason": "Browser navigation probe exited non-zero"})
    for feature in ("metricsSnapshot", "gatewayPerformanceSnapshot", "perspectiveSessionsQuery"):
        if feature not in feature_set:
            missing.append({"name": feature, "reason": "runner health.features does not include this feature"})

    phases = {phase: summarize_phase(rows, phase) for phase in ("pre", "during", "post")}
    summary: Dict[str, Any] = {
        "ok": bool(ok(health_record) and ok(control_view_record) and ok(target_view_record) and browser_info.get("exitCode") == 0 and not changed_resources),
        "runId": args.run_id,
        "project": project,
        "controlRoute": control_route,
        "targetRoute": target_route,
        "controlView": control_view,
        "targetView": target_view,
        "browser": summarize_browser_steps(browser_summary),
        "phases": phases,
        "deltas": {
            "duringMinusPreBrowserSessionsAvg": delta(phases["pre"].get("browserSessionCountAvg"), phases["during"].get("browserSessionCountAvg")),
            "postMinusPreBrowserSessionsAvg": delta(phases["pre"].get("browserSessionCountAvg"), phases["post"].get("browserSessionCountAvg")),
            "duringMinusPreBrowserPagesAvg": delta(phases["pre"].get("browserActivePagesAvg"), phases["during"].get("browserActivePagesAvg")),
            "postMinusPreBrowserPagesAvg": delta(phases["pre"].get("browserActivePagesAvg"), phases["post"].get("browserActivePagesAvg")),
            "duringMinusPreHeapUsedBytesAvg": delta(phases["pre"].get("heapUsedBytesAvg"), phases["during"].get("heapUsedBytesAvg")),
            "postMinusPreHeapUsedBytesAvg": delta(phases["pre"].get("heapUsedBytesAvg"), phases["post"].get("heapUsedBytesAvg")),
        },
        "browserProbe": browser_info,
        "browserOk": browser_summary.get("ok"),
        "baselineWait": baseline_wait,
        "changedResources": changed_resources,
    }
    summary["interpretation"] = build_interpretation(summary)
    write_json(out_dir / "summary.json", summary)

    manifest = {
        "ok": summary["ok"],
        "runId": args.run_id,
        "createdAt": utc_now(),
        "gatewayAlias": args.gateway_alias,
        "project": project,
        "controlRoute": control_route,
        "targetRoute": target_route,
        "controlView": control_view,
        "targetView": target_view,
        "runnerVersion": health.get("runnerVersion"),
        "stackVersion": health.get("stackVersion"),
        "features": sorted(feature_set),
        "evidenceGrade": "Observed",
        "scenario": "repeated navigation lifecycle",
        "cycles": args.cycles,
        "preSamples": args.pre_samples,
        "duringSampleIntervalSeconds": args.interval_sec,
        "postSamples": args.post_samples,
        "browserSettleMillis": args.browser_settle_ms,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "baselineWaitIntervalSeconds": args.baseline_wait_interval_sec if args.wait_for_clean_baseline else None,
        "controlViewSha256": control_view_response.get("viewSha256") or control_static.get("viewSha256"),
        "targetViewSha256": target_view_response.get("viewSha256") or target_static.get("viewSha256"),
        "changedResources": changed_resources,
        "missingEvidence": missing,
        "browserProbe": browser_info,
        "files": [
            "manifest.json",
            "summary.json",
            "report.md",
            "control-view-read.json",
            "target-view-read.json",
            "control-static-profile.json",
            "target-static-profile.json",
            "static-profile.json",
            "metrics-list.json",
            "baseline-wait.json",
            "baseline-wait-samples.ndjson",
            "navigation-samples.ndjson",
            "navigation-samples.annotated.json",
            "gateway-samples.ndjson",
            "perspective-session-samples.ndjson",
            "browser-summary.json",
            "browser-navigation-cycles.json",
            "browser-console.json",
            "network-summary.json",
            "logs.json",
            "thread-excerpts.json",
            "comparison.json",
            "raw/",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)
    make_report(out_dir, manifest, summary)
    print(json.dumps({"ok": summary["ok"], "outDir": str(out_dir), "summary": str(out_dir / "summary.json")}, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
