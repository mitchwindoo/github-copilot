#!/usr/bin/env python3
"""Run a read-only Perspective multi-session scaling profile."""

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
    enabled_name_set,
    ensure_profile_function,
    metric_tokens,
    ok,
    redact_browser_command,
    resolve_config,
    response,
    supports_action,
    utc_now,
    write_json,
)


SCRIPT_DIR = Path(__file__).resolve().parent


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


def avg(nums: Iterable[float]) -> Optional[float]:
    values = list(nums)
    return mean(values) if values else None


def delta(first: Optional[float], second: Optional[float]) -> Optional[float]:
    if first is None or second is None:
        return None
    return second - first


def per_requested_session(value: Optional[float], session_count: int) -> Optional[float]:
    if value is None or session_count <= 0:
        return None
    return value / float(session_count)


def format_number(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def metric_values(rows: List[Dict[str, Any]], phase: str, path: Tuple[str, ...]) -> List[float]:
    out: List[float] = []
    for row in rows:
        if row.get("phase") != phase:
            continue
        current: Any = row
        for part in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        parsed = to_float(current)
        if parsed is not None:
            out.append(parsed)
    return out


def summarize_phase(rows: List[Dict[str, Any]], phase: str) -> Dict[str, Any]:
    returned_counts: List[float] = []
    browser_sessions: List[float] = []
    browser_pages: List[float] = []
    browser_recent_bytes: List[float] = []
    queue_lengths: List[float] = []
    global_perspective_counts: List[float] = []
    for row in rows:
        if row.get("phase") != phase:
            continue
        query = row.get("perspectiveSessionsQuery", {})
        if isinstance(query, dict):
            returned = to_float(query.get("returnedCount"))
            if returned is not None:
                returned_counts.append(returned)
            sessions = query.get("sessions", [])
            browser_count = 0
            page_count = 0
            if isinstance(sessions, list):
                for session in sessions:
                    if not isinstance(session, dict):
                        continue
                    if str(session.get("sessionScope", "")).lower() == "browser":
                        browser_count += 1
                        page_count += int(to_float(session.get("activePages")) or 0)
                        recent = to_float(session.get("recentBytesSent"))
                        if recent is not None:
                            browser_recent_bytes.append(recent)
            browser_sessions.append(float(browser_count))
            browser_pages.append(float(page_count))
        metrics = row.get("metricsSnapshot", {})
        if isinstance(metrics, dict):
            for item in metrics.get("metrics", []) if isinstance(metrics.get("metrics"), list) else []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", ""))
                if name.endswith(".queue-length"):
                    queue = to_float(item.get("value"))
                    if queue is not None:
                        queue_lengths.append(queue)
                if name.endswith(".sessions") or name.endswith(".session-count"):
                    count = to_float(item.get("value"))
                    if count is not None:
                        global_perspective_counts.append(count)
    return {
        "sampleCount": sum(1 for row in rows if row.get("phase") == phase),
        "heapUsedBytesAvg": avg(metric_values(rows, phase, ("gatewayPerformanceSnapshot", "heap", "usedBytes"))),
        "processCpuLoadAvg": avg(metric_values(rows, phase, ("gatewayPerformanceSnapshot", "cpu", "processCpuLoad"))),
        "threadTotalAvg": avg(metric_values(rows, phase, ("gatewayPerformanceSnapshot", "threads", "total"))),
        "sessionReturnedCountAvg": avg(returned_counts),
        "browserSessionCountAvg": avg(browser_sessions),
        "browserActivePagesAvg": avg(browser_pages),
        "browserRecentBytesSentAvg": avg(browser_recent_bytes),
        "sessionQueueLengthAvg": avg(queue_lengths),
        "globalPerspectiveSessionMetricAvg": avg(global_perspective_counts),
    }


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
    session_count: int,
    action_set: set[str],
    feature_set: set[str],
    max_browser_sessions: int,
    timeout_sec: float,
    interval_sec: float,
) -> Dict[str, Any]:
    started = time.time()
    attempt = 0
    rows: List[Dict[str, Any]] = []
    if not supports_action(action_set, feature_set, "perspectiveSessionsQuery"):
        result = {
            "enabled": True,
            "ok": False,
            "reason": "runner health.supportedActions does not include perspectiveSessionsQuery",
            "sampleCount": 0,
            "maxBrowserSessions": max_browser_sessions,
        }
        append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"sessionCount": session_count, **result, "sampledAt": utc_now()})
        return result
    while True:
        request_id = f"{run_id}-s{session_count:02d}-baselineWait-{attempt:03d}"
        query = response(
            client.call(
                request_id,
                {
                    "action": "perspectiveSessionsQuery",
                    "requestId": request_id,
                    "targetProject": project,
                    "maxResults": max(50, session_count + 10),
                },
            )
        )
        counts = browser_counts_from_query(query)
        elapsed = time.time() - started
        row = {
            "sessionCount": session_count,
            "attempt": attempt,
            "sampledAt": utc_now(),
            "elapsedSeconds": round(elapsed, 3),
            "maxBrowserSessions": max_browser_sessions,
            **counts,
            "ok": query.get("ok") is not False,
            "clean": counts["browserSessions"] <= max_browser_sessions,
        }
        append_ndjson(out_dir / "baseline-wait-samples.ndjson", row)
        rows.append(row)
        if row["clean"]:
            return {
                "enabled": True,
                "ok": True,
                "timedOut": False,
                "sampleCount": len(rows),
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
                "sampleCount": len(rows),
                "elapsedSeconds": round(elapsed, 3),
                "maxBrowserSessions": max_browser_sessions,
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
            }
        attempt += 1
        time.sleep(max(interval_sec, 0.1))


def build_browser_command(args: argparse.Namespace, out_dir: Path) -> List[str]:
    command = [
        args.browser_node,
        str(SCRIPT_DIR / "browser_route_probe.mjs"),
        "--url",
        args.browser_url,
        "--out-dir",
        str(out_dir),
        "--ready-selector",
        args.browser_ready_selector,
        "--timeout-ms",
        str(int(args.browser_timeout_sec * 1000)),
        "--viewport",
        args.browser_viewport,
        "--wait-after-ready-ms",
        str(args.browser_wait_after_ready_ms),
        "--url-alias",
        args.browser_url_alias or args.gateway_alias,
    ]
    if args.browser_ready_text:
        command.extend(["--ready-text", args.browser_ready_text])
    return command


def start_browser(args: argparse.Namespace, out_dir: Path, session_index: int) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = out_dir / "browser-probe.stdout.txt"
    stderr_path = out_dir / "browser-probe.stderr.txt"
    command = build_browser_command(args, out_dir)
    stdout_handle = stdout_path.open("w", encoding="utf-8", newline="\n")
    stderr_handle = stderr_path.open("w", encoding="utf-8", newline="\n")
    info: Dict[str, Any] = {
        "sessionIndex": session_index,
        "startedAt": utc_now(),
        "command": redact_browser_command(command),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
        "outDir": str(out_dir),
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


def sample_once(client: RunnerClient, run_id: str, project: str, session_count: int, phase: str, index: int, tokens: List[str], action_set: set[str], feature_set: set[str]) -> Dict[str, Any]:
    prefix = f"{run_id}-s{session_count:02d}-{phase}-{index:03d}"
    row: Dict[str, Any] = {
        "sessionCount": session_count,
        "phase": phase,
        "sampleIndex": index,
        "sampledAt": utc_now(),
    }
    if tokens and supports_action(action_set, feature_set, "metricsSnapshot"):
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
        reason = "No metric tokens" if not tokens else "runner health.supportedActions does not include metricsSnapshot"
        row["metricsSnapshot"] = {"ok": False, "missing": True, "reason": reason}
    if supports_action(action_set, feature_set, "gatewayPerformanceSnapshot"):
        row["gatewayPerformanceSnapshot"] = response(
            client.call(
                f"{prefix}-gatewayPerformanceSnapshot",
                {"action": "gatewayPerformanceSnapshot", "requestId": f"{prefix}-gatewayPerformanceSnapshot"},
            )
        )
    else:
        row["gatewayPerformanceSnapshot"] = {"ok": False, "missing": True, "reason": "runner health.supportedActions does not include gatewayPerformanceSnapshot"}
    if supports_action(action_set, feature_set, "perspectiveSessionsQuery"):
        row["perspectiveSessionsQuery"] = response(
            client.call(
                f"{prefix}-perspectiveSessionsQuery",
                {
                    "action": "perspectiveSessionsQuery",
                    "requestId": f"{prefix}-perspectiveSessionsQuery",
                    "targetProject": project,
                    "maxResults": max(50, session_count + 10),
                },
            )
        )
    else:
        row["perspectiveSessionsQuery"] = {"ok": False, "missing": True, "reason": "runner health.supportedActions does not include perspectiveSessionsQuery"}
    return row


def sample_phase(client: RunnerClient, out_dir: Path, run_id: str, project: str, session_count: int, phase: str, count: int, interval_sec: float, tokens: List[str], action_set: set[str], feature_set: set[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index in range(max(count, 0)):
        row = sample_once(client, run_id, project, session_count, phase, index, tokens, action_set, feature_set)
        append_ndjson(out_dir / "multi-session-samples.ndjson", row)
        rows.append(row)
        if index < count - 1:
            time.sleep(interval_sec)
    return rows


def parse_session_counts(value: str) -> List[int]:
    counts: List[int] = []
    for part in value.split(","):
        stripped = part.strip()
        if not stripped:
            continue
        try:
            count = int(stripped)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Invalid session count: {stripped}") from exc
        if count <= 0:
            raise argparse.ArgumentTypeError("Session counts must be positive")
        counts.append(count)
    if not counts:
        raise argparse.ArgumentTypeError("At least one session count is required")
    return counts


def collect_browser_summaries(browser_infos: List[Dict[str, Any]]) -> Dict[str, Any]:
    summaries: List[Dict[str, Any]] = []
    exit_codes: List[Any] = []
    timed_out = 0
    ready_count = 0
    ready_text_count = 0
    dom_nodes: List[float] = []
    long_task_totals: List[float] = []
    lcp_starts: List[float] = []
    transfer_sizes: List[float] = []
    for info in browser_infos:
        exit_codes.append(info.get("exitCode"))
        if info.get("timedOut"):
            timed_out += 1
        summary = read_json(Path(str(info.get("outDir", ""))) / "browser-summary.json")
        if summary:
            summaries.append(summary)
            if summary.get("ready"):
                ready_count += 1
            if summary.get("readyTextMatched"):
                ready_text_count += 1
            nodes = to_float(summary.get("domNodeCount"))
            if nodes is not None:
                dom_nodes.append(nodes)
            long_total = to_float(summary.get("longTaskTotalMs"))
            if long_total is not None:
                long_task_totals.append(long_total)
            lcp = summary.get("largestContentfulPaint", {})
            if isinstance(lcp, dict):
                start_time = to_float(lcp.get("startTime"))
                if start_time is not None:
                    lcp_starts.append(start_time)
            transfer = to_float(summary.get("resourceTransferSize"))
            if transfer is not None:
                transfer_sizes.append(transfer)
    return {
        "probeCount": len(browser_infos),
        "exitCodes": exit_codes,
        "timedOutCount": timed_out,
        "readyCount": ready_count,
        "readyTextMatchedCount": ready_text_count,
        "domNodeCountAvg": avg(dom_nodes),
        "longTaskTotalMsAvg": avg(long_task_totals),
        "largestContentfulPaintStartMsAvg": avg(lcp_starts),
        "resourceTransferSizeAvg": avg(transfer_sizes),
    }


def summarize_group(session_count: int, rows: List[Dict[str, Any]], browser_infos: List[Dict[str, Any]], baseline_wait: Dict[str, Any]) -> Dict[str, Any]:
    phases = {phase: summarize_phase(rows, phase) for phase in ("pre", "during", "post")}
    during_minus_pre_sessions = delta(phases["pre"].get("browserSessionCountAvg"), phases["during"].get("browserSessionCountAvg"))
    during_minus_pre_pages = delta(phases["pre"].get("browserActivePagesAvg"), phases["during"].get("browserActivePagesAvg"))
    during_minus_pre_heap = delta(phases["pre"].get("heapUsedBytesAvg"), phases["during"].get("heapUsedBytesAvg"))
    during_minus_pre_cpu = delta(phases["pre"].get("processCpuLoadAvg"), phases["during"].get("processCpuLoadAvg"))
    post_minus_pre_sessions = delta(phases["pre"].get("browserSessionCountAvg"), phases["post"].get("browserSessionCountAvg"))
    return {
        "sessionCount": session_count,
        "baselineWait": baseline_wait,
        "phases": phases,
        "browserProbes": collect_browser_summaries(browser_infos),
        "deltas": {
            "duringMinusPreBrowserSessionsAvg": during_minus_pre_sessions,
            "duringMinusPreBrowserPagesAvg": during_minus_pre_pages,
            "duringMinusPreHeapUsedBytesAvg": during_minus_pre_heap,
            "duringMinusPreProcessCpuLoadAvg": during_minus_pre_cpu,
            "postMinusPreBrowserSessionsAvg": post_minus_pre_sessions,
            "duringMinusPreHeapUsedBytesPerRequestedSession": per_requested_session(during_minus_pre_heap, session_count),
            "duringMinusPreProcessCpuLoadPerRequestedSession": per_requested_session(during_minus_pre_cpu, session_count),
            "duringMinusPreBrowserSessionsPerRequestedSession": per_requested_session(during_minus_pre_sessions, session_count),
        },
    }


def build_interpretation(groups: List[Dict[str, Any]]) -> List[str]:
    notes = [
        "This is read-only multi-session scaling observation, not a causal remediation proof.",
        "Use during-minus-pre deltas because pre-existing Perspective browser sessions can confound absolute session counts.",
        "Heap and CPU deltas are coarse Gateway-level signals; repeat on an isolated staging Gateway before declaring a per-session cost curve.",
    ]
    contaminated = [
        group
        for group in groups
        if (group.get("phases", {}).get("pre", {}).get("browserSessionCountAvg") or 0) > 0
    ]
    negative_session_deltas = [
        group
        for group in groups
        if (group.get("deltas", {}).get("duringMinusPreBrowserSessionsAvg") or 0) < 0
    ]
    baseline_timeouts = [
        group
        for group in groups
        if group.get("baselineWait", {}).get("enabled") and not group.get("baselineWait", {}).get("ok")
    ]
    if contaminated:
        notes.append("At least one pre phase already had retained browser sessions; treat that group as baseline-contaminated unless the retained sessions were intentionally part of the scenario.")
    if negative_session_deltas:
        notes.append("A negative browser-session delta means retained session population changed during the group; do not interpret it as the requested session count scaling cleanly.")
    if baseline_timeouts:
        notes.append("At least one baseline wait did not reach the requested browser-session threshold before timeout; keep the affected group observational.")
    requested = [group.get("sessionCount") for group in groups]
    observed = [group.get("deltas", {}).get("duringMinusPreBrowserSessionsAvg") for group in groups]
    if requested and all(isinstance(value, (int, float)) for value in observed):
        notes.append("Observed browser-session deltas were captured for every requested session count; compare slope, not only maximum values.")
    return notes


def make_report(out_dir: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    lines = [
        "# Perspective Multi-Session Scaling Profile",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Project: `{manifest.get('project', '')}`",
        f"Route: `{manifest.get('route', '')}`",
        f"View: `{manifest.get('view', '')}`",
        f"Evidence grade: `{manifest.get('evidenceGrade', 'Observed')}`",
        "",
        "## Session Groups",
        "",
        "| Requested sessions | Baseline wait | Ready probes | Browser sessions delta | Browser pages delta | Heap delta | CPU delta | LCP avg | Long-task avg |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group in summary.get("groups", []):
        probes = group.get("browserProbes", {})
        deltas = group.get("deltas", {})
        baseline = group.get("baselineWait", {})
        if baseline.get("enabled"):
            baseline_text = "clean" if baseline.get("ok") else "timeout"
            baseline_text += f" ({format_number(baseline.get('finalBrowserSessions'))})"
        else:
            baseline_text = "not requested"
        lines.append(
            "| {sessions} | {baseline} | {ready}/{total} | {session_delta} | {page_delta} | {heap_delta} | {cpu_delta} | {lcp} | {long_tasks} |".format(
                sessions=group.get("sessionCount"),
                baseline=baseline_text,
                ready=probes.get("readyCount"),
                total=probes.get("probeCount"),
                session_delta=format_number(deltas.get("duringMinusPreBrowserSessionsAvg")),
                page_delta=format_number(deltas.get("duringMinusPreBrowserPagesAvg")),
                heap_delta=format_number(deltas.get("duringMinusPreHeapUsedBytesAvg")),
                cpu_delta=format_number(deltas.get("duringMinusPreProcessCpuLoadAvg")),
                lcp=format_number(probes.get("largestContentfulPaintStartMsAvg")),
                long_tasks=format_number(probes.get("longTaskTotalMsAvg")),
            )
        )
    lines.extend(
        [
            "",
            "## Direct Observations",
            "",
            "- Browser probes, Gateway performance snapshots, Perspective session samples, and metric snapshots were collected under the same run ID.",
            "- Each requested session group records clean-baseline status, ready-probe count, during-minus-pre deltas, and per-group browser evidence.",
            "- `changedResources` is empty because this helper is read-only.",
        ]
    )
    lines.extend(["", "## Interpretation", ""])
    for note in summary.get("interpretation", []):
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Unproven Limits",
            "",
            "- This run is not proof of a platform-wide or customer-wide per-session cost curve.",
            "- Do not claim causal improvement or regression from this observational scaling bundle alone.",
            "- Repeat on an isolated staging Gateway or the customer target route before converting the slope into remediation guidance.",
        ]
    )
    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a read-only Perspective multi-session scaling profile.")
    parser.add_argument("--endpoint", help="Runner Web Dev endpoint. Env fallback matches collect_profile.py.")
    parser.add_argument("--token", help="Runner token. Env fallback matches collect_profile.py.")
    parser.add_argument("--project", help="Target project. Env fallback matches collect_profile.py.")
    parser.add_argument("--route", required=True, help="Perspective route/page path.")
    parser.add_argument("--view", help="Perspective view path. Defaults to route inventory match.")
    parser.add_argument("--run-id", required=True, help="Stable run identifier.")
    parser.add_argument("--out-dir", required=True, help="Evidence output directory.")
    parser.add_argument("--session-counts", type=parse_session_counts, default=parse_session_counts("1,5,10"), help="Comma-separated concurrent browser counts, such as 1,5,10.")
    parser.add_argument("--max-session-count", type=int, default=20, help="Hard guardrail for the largest requested session group.")
    parser.add_argument("--browser-url", required=True, help="Perspective route URL to open for each session.")
    parser.add_argument("--browser-ready-selector", default="body", help="CSS selector for browser readiness.")
    parser.add_argument("--browser-ready-text", default="", help="Optional text that must be visible before readiness.")
    parser.add_argument("--browser-viewport", default="1366x768", help="Browser viewport.")
    parser.add_argument("--browser-timeout-sec", type=float, default=45.0, help="Browser route timeout.")
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=20000, help="How long each browser remains open after ready.")
    parser.add_argument("--browser-node", default="node", help="Node executable for browser_route_probe.mjs.")
    parser.add_argument("--browser-node-modules", default="", help="Optional node_modules path for Playwright.")
    parser.add_argument("--browser-url-alias", default="", help="Non-secret browser URL alias.")
    parser.add_argument("--gateway-alias", default="configured-gateway", help="Non-secret Gateway alias.")
    parser.add_argument("--timeout-sec", type=int, default=30, help="Runner HTTP timeout.")
    parser.add_argument("--max-metrics", type=int, default=25, help="Maximum metric tokens to sample.")
    parser.add_argument(
        "--metric-name-contains",
        action="append",
        default=[],
        help="Metric substring filter for metricsList. Repeatable; defaults to Perspective filters.",
    )
    parser.add_argument(
        "--metric-prefix",
        action="append",
        default=[],
        help="Metric prefix filter for metricsList. Repeatable.",
    )
    parser.add_argument("--pre-samples", type=int, default=2, help="Samples before browser launch.")
    parser.add_argument("--during-samples", type=int, default=4, help="Samples while browsers are open.")
    parser.add_argument("--post-samples", type=int, default=2, help="Samples after browsers close.")
    parser.add_argument("--interval-sec", type=float, default=2.0, help="Sample interval.")
    parser.add_argument("--launch-stagger-ms", type=int, default=250, help="Delay between browser probe launches.")
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each session group, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for clean baseline per group.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between baseline wait samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Abort when a clean baseline is requested but not reached before timeout.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.max_session_count <= 0:
        raise SystemExit("--max-session-count must be > 0")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0:
        raise SystemExit("--baseline-wait-timeout-sec must be >= 0")
    if max(args.session_counts) > args.max_session_count:
        raise SystemExit(f"Largest requested session count exceeds --max-session-count ({args.max_session_count})")
    endpoint, token, project = resolve_config(args)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = RunnerClient(endpoint, token, out_dir, args.timeout_sec)
    profile_view = ensure_profile_function()

    health_record = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health = response(health_record)
    feature_set = enabled_name_set(health.get("features", []))
    action_set = enabled_name_set(health.get("supportedActions", []))
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
    route, view = choose_route(response(routes_record).get("routes", []), args.route, args.view or "")
    if not view:
        raise SystemExit("Target view could not be resolved. Use --view.")
    view_record = client.call(
        f"{args.run_id}-viewRead",
        {
            "action": "viewRead",
            "requestId": f"{args.run_id}-viewRead",
            "targetProject": project,
            "viewPath": view,
            "allowedViewPrefix": "",
            "includeViewJson": True,
            "includeResourceJson": True,
        },
    )
    view_response = response(view_record)
    write_json(out_dir / "view-read.json", view_response)
    static_profile = profile_view(view_response, "view-read.json")
    write_json(out_dir / "static-profile.json", static_profile)

    tokens: List[str] = []
    metric_filters = args.metric_name_contains or ["Perspective", "perspective"]
    if supports_action(action_set, feature_set, "metricsList"):
        metrics_payload: Dict[str, Any] = {
            "action": "metricsList",
            "requestId": f"{args.run_id}-metricsList",
            "nameContains": metric_filters,
            "maxResults": min(max(args.max_metrics * 3, args.max_metrics), 250),
        }
        if args.metric_prefix:
            metrics_payload["namePrefixes"] = args.metric_prefix
        metrics_record = client.call(
            f"{args.run_id}-metricsList",
            metrics_payload,
        )
        write_json(out_dir / "metrics-list.json", response(metrics_record))
        tokens = metric_tokens(response(metrics_record), max(0, min(args.max_metrics, 100)))

    groups: List[Dict[str, Any]] = []
    browser_timeout = int(args.browser_timeout_sec + (args.browser_wait_after_ready_ms / 1000.0) + 30)
    for session_count in args.session_counts:
        group_dir = out_dir / f"sessions-{session_count:02d}"
        group_dir.mkdir(parents=True, exist_ok=True)
        rows: List[Dict[str, Any]] = []
        baseline_wait: Dict[str, Any] = {"enabled": False}
        if args.wait_for_clean_baseline:
            baseline_wait = wait_for_clean_baseline(
                client,
                out_dir,
                args.run_id,
                project,
                session_count,
                action_set,
                feature_set,
                args.baseline_max_browser_sessions,
                args.baseline_wait_timeout_sec,
                args.baseline_wait_interval_sec,
            )
            if args.fail_on_baseline_timeout and not baseline_wait.get("ok"):
                write_json(group_dir / "baseline-wait.json", baseline_wait)
                raise SystemExit(f"Clean baseline was not reached before timeout for session group {session_count}.")
            write_json(group_dir / "baseline-wait.json", baseline_wait)
        rows.extend(sample_phase(client, out_dir, args.run_id, project, session_count, "pre", args.pre_samples, args.interval_sec, tokens, action_set, feature_set))
        browser_infos: List[Dict[str, Any]] = []
        for index in range(session_count):
            browser_infos.append(start_browser(args, group_dir / f"browser-{index + 1:02d}", index + 1))
            if args.launch_stagger_ms and index < session_count - 1:
                time.sleep(args.launch_stagger_ms / 1000.0)
        rows.extend(sample_phase(client, out_dir, args.run_id, project, session_count, "during", args.during_samples, args.interval_sec, tokens, action_set, feature_set))
        finished = [finish_browser(info, browser_timeout) for info in browser_infos]
        rows.extend(sample_phase(client, out_dir, args.run_id, project, session_count, "post", args.post_samples, args.interval_sec, tokens, action_set, feature_set))
        group_summary = summarize_group(session_count, rows, finished, baseline_wait)
        groups.append(group_summary)
        write_json(group_dir / "summary.json", group_summary)

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

    summary = {
        "ok": bool(ok(health_record) and ok(view_record) and all(all(code == 0 for code in group.get("browserProbes", {}).get("exitCodes", [])) for group in groups)),
        "runId": args.run_id,
        "project": project,
        "route": route,
        "view": view,
        "sessionCounts": args.session_counts,
        "groups": groups,
        "interpretation": build_interpretation(groups),
    }
    write_json(out_dir / "summary.json", summary)
    manifest = {
        "ok": summary["ok"],
        "runId": args.run_id,
        "createdAt": utc_now(),
        "gatewayAlias": args.gateway_alias,
        "project": project,
        "route": route,
        "view": view,
        "runnerVersion": health.get("runnerVersion"),
        "stackVersion": health.get("stackVersion"),
        "supportedActions": sorted(action_set),
        "features": sorted(feature_set),
        "evidenceGrade": "Observed",
        "scenario": "multi-session scaling",
        "sessionCounts": args.session_counts,
        "preSamples": args.pre_samples,
        "duringSamples": args.during_samples,
        "postSamples": args.post_samples,
        "intervalSeconds": args.interval_sec,
        "launchStaggerMillis": args.launch_stagger_ms,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "baselineWaitIntervalSeconds": args.baseline_wait_interval_sec if args.wait_for_clean_baseline else None,
        "viewSha256": view_response.get("viewSha256") or static_profile.get("viewSha256"),
        "changedResources": [],
        "missingEvidence": [],
        "files": [
            "manifest.json",
            "summary.json",
            "report.md",
            "view-read.json",
            "static-profile.json",
            "metrics-list.json",
            "baseline-wait-samples.ndjson",
            "multi-session-samples.ndjson",
            "logs.json",
            "sessions-*/",
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
