#!/usr/bin/env python3
"""Run a read-only Perspective browser close/lifecycle profile.

The script opens one browser probe, samples Gateway/session evidence before,
during, and after the browser context closes, and reports whether sessions/pages
and heap move back toward baseline in the observed post-close window.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime
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
    redact_browser_command,
    resolve_config,
    response,
    slug,
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


def values(rows: Iterable[Dict[str, Any]], phase: str, path: Tuple[str, ...]) -> List[float]:
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


def avg(nums: List[float]) -> Optional[float]:
    return mean(nums) if nums else None


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


def summarize_phase(rows: List[Dict[str, Any]], phase: str) -> Dict[str, Any]:
    returned_counts: List[float] = []
    browser_sessions: List[float] = []
    browser_pages: List[float] = []
    browser_recent_bytes: List[float] = []
    queue_lengths: List[float] = []
    for row in rows:
        if row.get("phase") != phase:
            continue
        query = row.get("perspectiveSessionsQuery", {})
        if isinstance(query, dict):
            returned = to_float(query.get("returnedCount"))
            if returned is not None:
                returned_counts.append(returned)
            browser_count, page_count, recent = browser_counts(row)
            browser_recent_bytes.extend(recent)
            browser_sessions.append(float(browser_count))
            browser_pages.append(float(page_count))
        metrics = row.get("metricsSnapshot", {})
        if isinstance(metrics, dict):
            for item in metrics.get("metrics", []) if isinstance(metrics.get("metrics"), list) else []:
                if isinstance(item, dict) and str(item.get("name", "")).endswith(".queue-length"):
                    queue = to_float(item.get("value"))
                    if queue is not None:
                        queue_lengths.append(queue)
    return {
        "sampleCount": sum(1 for row in rows if row.get("phase") == phase),
        "heapUsedBytesAvg": avg(values(rows, phase, ("gatewayPerformanceSnapshot", "heap", "usedBytes"))),
        "processCpuLoadAvg": avg(values(rows, phase, ("gatewayPerformanceSnapshot", "cpu", "processCpuLoad"))),
        "threadTotalAvg": avg(values(rows, phase, ("gatewayPerformanceSnapshot", "threads", "total"))),
        "sessionReturnedCountAvg": avg(returned_counts),
        "browserSessionCountAvg": avg(browser_sessions),
        "browserActivePagesAvg": avg(browser_pages),
        "browserRecentBytesSentAvg": avg(browser_recent_bytes),
        "sessionQueueLengthAvg": avg(queue_lengths),
    }


def parse_sample_time(row: Dict[str, Any]) -> Optional[datetime]:
    sampled_at = row.get("sampledAt")
    if not isinstance(sampled_at, str):
        return None
    try:
        return datetime.strptime(sampled_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def seconds_between(start: Optional[datetime], end: Optional[datetime]) -> Optional[float]:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 3)


def summarize_post_release(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    post_rows = [row for row in rows if row.get("phase") == "post"]
    if not post_rows:
        return {"sampleCount": 0}
    first_post_time = parse_sample_time(post_rows[0])
    samples: List[Dict[str, Any]] = []
    for row in post_rows:
        sessions, pages, _recent = browser_counts(row)
        sample_time = parse_sample_time(row)
        returned = None
        query = row.get("perspectiveSessionsQuery", {})
        if isinstance(query, dict):
            returned = to_float(query.get("returnedCount"))
        samples.append(
            {
                "sampleIndex": row.get("sampleIndex"),
                "sampledAt": row.get("sampledAt"),
                "secondsAfterPostStart": seconds_between(first_post_time, sample_time),
                "browserSessions": sessions,
                "browserPages": pages,
                "returnedCount": returned,
            }
        )

    first_pages_zero = next((item for item in samples if item["browserPages"] == 0), None)
    last_pages_nonzero = next((item for item in reversed(samples) if item["browserPages"] > 0), None)
    first_sessions_zero = next((item for item in samples if item["browserSessions"] == 0), None)
    last_sessions_nonzero = next((item for item in reversed(samples) if item["browserSessions"] > 0), None)
    stable_sessions_zero = False
    if first_sessions_zero is not None:
        start_index = samples.index(first_sessions_zero)
        stable_sessions_zero = all(item["browserSessions"] == 0 for item in samples[start_index:])
    stable_pages_zero = False
    if first_pages_zero is not None:
        start_index = samples.index(first_pages_zero)
        stable_pages_zero = all(item["browserPages"] == 0 for item in samples[start_index:])

    return {
        "sampleCount": len(samples),
        "firstPostSampleAt": samples[0].get("sampledAt"),
        "lastPostSampleAt": samples[-1].get("sampledAt"),
        "firstBrowserPagesZeroAt": first_pages_zero.get("sampledAt") if first_pages_zero else None,
        "firstBrowserPagesZeroSecondsAfterPostStart": first_pages_zero.get("secondsAfterPostStart") if first_pages_zero else None,
        "lastBrowserPagesNonZeroAt": last_pages_nonzero.get("sampledAt") if last_pages_nonzero else None,
        "lastBrowserPagesNonZeroSecondsAfterPostStart": last_pages_nonzero.get("secondsAfterPostStart") if last_pages_nonzero else None,
        "stableBrowserPagesZeroAfterFirstZero": stable_pages_zero,
        "firstBrowserSessionsZeroAt": first_sessions_zero.get("sampledAt") if first_sessions_zero else None,
        "firstBrowserSessionsZeroSecondsAfterPostStart": first_sessions_zero.get("secondsAfterPostStart") if first_sessions_zero else None,
        "lastBrowserSessionsNonZeroAt": last_sessions_nonzero.get("sampledAt") if last_sessions_nonzero else None,
        "lastBrowserSessionsNonZeroSecondsAfterPostStart": last_sessions_nonzero.get("secondsAfterPostStart") if last_sessions_nonzero else None,
        "stableBrowserSessionsZeroAfterFirstZero": stable_sessions_zero,
    }


def summarize_post_heap(rows: List[Dict[str, Any]], pre_heap_avg: Optional[float]) -> Dict[str, Any]:
    post_values = values(rows, "post", ("gatewayPerformanceSnapshot", "heap", "usedBytes"))
    if not post_values:
        return {}
    post_last = post_values[-1]
    out = {
        "postFirstHeapUsedBytes": post_values[0],
        "postMaxHeapUsedBytes": max(post_values),
        "postMinHeapUsedBytes": min(post_values),
        "postLastHeapUsedBytes": post_last,
    }
    if pre_heap_avg is not None:
        out["postLastMinusPreAvgHeapUsedBytes"] = post_last - pre_heap_avg
    return out


def last_post_counts(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    post_rows = [row for row in rows if row.get("phase") == "post"]
    if not post_rows:
        return {"browserSessions": None, "browserPages": None}
    sessions, pages, _recent = browser_counts(post_rows[-1])
    return {"browserSessions": sessions, "browserPages": pages, "sampledAt": post_rows[-1].get("sampledAt")}


def timeout_coverage(args: argparse.Namespace, post_observed: float, post_release: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    expected = args.expected_session_timeout_sec or None
    grace = args.timeout_grace_sec
    last_counts = last_post_counts(rows)
    out: Dict[str, Any] = {
        "expectedSessionTimeoutSeconds": expected,
        "timeoutGraceSeconds": grace,
        "postCloseObservedSeconds": post_observed,
        "requiredObservedSeconds": (expected + grace) if expected is not None else None,
        "coversTimeoutPlusGrace": None,
        "lastPostBrowserSessions": last_counts.get("browserSessions"),
        "lastPostBrowserPages": last_counts.get("browserPages"),
        "lastPostSampleAt": last_counts.get("sampledAt"),
        "browserSessionsReleasedByTimeoutPlusGrace": None,
        "browserPagesReleasedByTimeoutPlusGrace": None,
        "releaseClassification": "timeout-not-declared",
    }
    if expected is None:
        return out

    required = expected + grace
    covers = post_observed >= required
    out["coversTimeoutPlusGrace"] = covers

    session_zero = post_release.get("firstBrowserSessionsZeroSecondsAfterPostStart")
    pages_zero = post_release.get("firstBrowserPagesZeroSecondsAfterPostStart")
    if isinstance(session_zero, (int, float)):
        out["browserSessionsReleasedByTimeoutPlusGrace"] = session_zero <= required and bool(post_release.get("stableBrowserSessionsZeroAfterFirstZero"))
    elif covers:
        out["browserSessionsReleasedByTimeoutPlusGrace"] = False
    if isinstance(pages_zero, (int, float)):
        out["browserPagesReleasedByTimeoutPlusGrace"] = pages_zero <= required and bool(post_release.get("stableBrowserPagesZeroAfterFirstZero"))
    elif covers:
        out["browserPagesReleasedByTimeoutPlusGrace"] = False

    if not covers:
        out["releaseClassification"] = "observed-window-too-short"
    elif out["browserSessionsReleasedByTimeoutPlusGrace"] and out["browserPagesReleasedByTimeoutPlusGrace"]:
        out["releaseClassification"] = "released-by-timeout-plus-grace"
    elif (last_counts.get("browserSessions") or 0) > 0 or (last_counts.get("browserPages") or 0) > 0:
        out["releaseClassification"] = "retained-after-timeout-plus-grace"
    else:
        out["releaseClassification"] = "counts-zero-by-final-sample-with-partial-release-timing"
    return out


def delta(first: Optional[float], second: Optional[float]) -> Optional[float]:
    if first is None or second is None:
        return None
    return second - first


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


def start_browser(args: argparse.Namespace, out_dir: Path) -> Dict[str, Any]:
    stdout_path = out_dir / "browser-probe.stdout.txt"
    stderr_path = out_dir / "browser-probe.stderr.txt"
    command = build_browser_command(args, out_dir)
    stdout_handle = stdout_path.open("w", encoding="utf-8", newline="\n")
    stderr_handle = stderr_path.open("w", encoding="utf-8", newline="\n")
    info: Dict[str, Any] = {
        "startedAt": utc_now(),
        "command": redact_browser_command(command),
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


def sample_once(client: RunnerClient, run_id: str, project: str, phase: str, index: int, tokens: List[str], feature_set: set[str]) -> Dict[str, Any]:
    row: Dict[str, Any] = {"phase": phase, "sampleIndex": index, "sampledAt": utc_now()}
    if tokens and "metricsSnapshot" in feature_set:
        row["metricsSnapshot"] = response(
            client.call(
                f"{run_id}-{phase}-metricsSnapshot-{index:03d}",
                {
                    "action": "metricsSnapshot",
                    "requestId": f"{run_id}-{phase}-metricsSnapshot-{index:03d}",
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
                f"{run_id}-{phase}-gatewayPerformanceSnapshot-{index:03d}",
                {"action": "gatewayPerformanceSnapshot", "requestId": f"{run_id}-{phase}-gatewayPerformanceSnapshot-{index:03d}"},
            )
        )
    else:
        row["gatewayPerformanceSnapshot"] = {"ok": False, "missing": True, "reason": "feature not present"}
    if "perspectiveSessionsQuery" in feature_set:
        row["perspectiveSessionsQuery"] = response(
            client.call(
                f"{run_id}-{phase}-perspectiveSessionsQuery-{index:03d}",
                {
                    "action": "perspectiveSessionsQuery",
                    "requestId": f"{run_id}-{phase}-perspectiveSessionsQuery-{index:03d}",
                    "targetProject": project,
                    "maxResults": 50,
                },
            )
        )
    else:
        row["perspectiveSessionsQuery"] = {"ok": False, "missing": True, "reason": "feature not present"}
    return row


def sample_phase(client: RunnerClient, out_dir: Path, run_id: str, project: str, phase: str, count: int, interval_sec: float, tokens: List[str], feature_set: set[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index in range(max(count, 0)):
        row = sample_once(client, run_id, project, phase, index, tokens, feature_set)
        append_ndjson(out_dir / "lifecycle-samples.ndjson", row)
        rows.append(row)
        if index < count - 1:
            time.sleep(interval_sec)
    return rows


def make_report(out_dir: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    lines = [
        "# Perspective Lifecycle Profile",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Project: `{manifest.get('project', '')}`",
        f"Route: `{manifest.get('route', '')}`",
        f"View: `{manifest.get('view', '')}`",
        f"Evidence grade: `{manifest.get('evidenceGrade', '')}`",
        f"Post-close observed seconds: `{manifest.get('postCloseObservedSeconds')}`",
        "",
        "## Evidence Boundary",
        "",
        "- Direct observations: synchronized Gateway/session samples, browser route evidence, static view readback, logs, and post-close release timing for this run.",
        "- Interpretation: timeout retention and heap movement are interpreted against the declared scenario and configured timeout.",
        "- Unproven/non-causal limits: this lifecycle profile is not proof of a leak, no-leak condition, or remediation impact by itself.",
        "",
        "## Phase Summary",
        "",
        "| Phase | Samples | Browser sessions avg | Browser pages avg | Heap used avg | CPU avg |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for phase in ("pre", "during", "post"):
        item = summary.get("phases", {}).get(phase, {})
        lines.append(
            "| {phase} | {samples} | {sessions} | {pages} | {heap} | {cpu} |".format(
                phase=phase,
                samples=item.get("sampleCount", 0),
                sessions=format_number(item.get("browserSessionCountAvg")),
                pages=format_number(item.get("browserActivePagesAvg")),
                heap=format_number(item.get("heapUsedBytesAvg")),
                cpu=format_number(item.get("processCpuLoadAvg")),
            )
        )
    lines.extend(["", "## Deltas", ""])
    for name, value in summary.get("deltas", {}).items():
        lines.append(f"- `{name}`: `{format_number(value)}`")
    release = summary.get("postRelease", {})
    if release:
        lines.extend(["", "## Post-Close Release", ""])
        lines.append(f"- First browser pages zero: `{format_number(release.get('firstBrowserPagesZeroSecondsAfterPostStart'))}` seconds after post-close sampling started.")
        lines.append(f"- Last browser pages non-zero: `{format_number(release.get('lastBrowserPagesNonZeroSecondsAfterPostStart'))}` seconds after post-close sampling started.")
        lines.append(f"- First browser sessions zero: `{format_number(release.get('firstBrowserSessionsZeroSecondsAfterPostStart'))}` seconds after post-close sampling started.")
        lines.append(f"- Last browser sessions non-zero: `{format_number(release.get('lastBrowserSessionsNonZeroSecondsAfterPostStart'))}` seconds after post-close sampling started.")
        lines.append(f"- Stable page zero after first zero: `{release.get('stableBrowserPagesZeroAfterFirstZero')}`")
        lines.append(f"- Stable session zero after first zero: `{release.get('stableBrowserSessionsZeroAfterFirstZero')}`")
    coverage = summary.get("timeoutCoverage", {})
    if coverage:
        lines.extend(["", "## Timeout Coverage", ""])
        lines.append(f"- Expected timeout: `{format_number(coverage.get('expectedSessionTimeoutSeconds'))}` seconds")
        lines.append(f"- Grace: `{format_number(coverage.get('timeoutGraceSeconds'))}` seconds")
        lines.append(f"- Required observation: `{format_number(coverage.get('requiredObservedSeconds'))}` seconds")
        lines.append(f"- Covered timeout plus grace: `{coverage.get('coversTimeoutPlusGrace')}`")
        lines.append(f"- Release classification: `{coverage.get('releaseClassification')}`")
        lines.append(f"- Last post browser sessions/pages: `{coverage.get('lastPostBrowserSessions')}` / `{coverage.get('lastPostBrowserPages')}`")
    post_heap = summary.get("postHeap", {})
    if post_heap:
        lines.extend(["", "## Post-Close Heap", ""])
        for name, value in post_heap.items():
            lines.append(f"- `{name}`: `{format_number(value)}`")
    lines.extend(["", "## Interpretation", ""])
    for note in summary.get("interpretation", []):
        lines.append(f"- {note}")
    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def format_number(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a read-only Perspective browser close lifecycle profile.")
    parser.add_argument("--endpoint", help="Runner Web Dev endpoint. Env fallback matches collect_profile.py.")
    parser.add_argument("--token", help="Runner token. Env fallback matches collect_profile.py.")
    parser.add_argument("--project", help="Target project. Env fallback matches collect_profile.py.")
    parser.add_argument("--route", required=True, help="Perspective route/page path.")
    parser.add_argument("--view", help="Perspective view path. Defaults to route inventory match.")
    parser.add_argument("--run-id", required=True, help="Stable run identifier.")
    parser.add_argument("--out-dir", required=True, help="Evidence output directory.")
    parser.add_argument("--browser-url", required=True, help="Perspective route URL to open and close.")
    parser.add_argument("--browser-ready-selector", default="body", help="CSS selector for browser readiness.")
    parser.add_argument("--browser-ready-text", default="", help="Optional text that must be visible before readiness.")
    parser.add_argument("--browser-viewport", default="1366x768", help="Browser viewport.")
    parser.add_argument("--browser-timeout-sec", type=float, default=45.0, help="Browser route timeout.")
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=5000, help="How long the browser remains open after ready.")
    parser.add_argument("--browser-node", default="node", help="Node executable for browser_route_probe.mjs.")
    parser.add_argument("--browser-node-modules", default="", help="Optional node_modules path for Playwright.")
    parser.add_argument("--browser-url-alias", default="", help="Non-secret browser URL alias.")
    parser.add_argument("--gateway-alias", default="configured-gateway", help="Non-secret Gateway alias.")
    parser.add_argument("--timeout-sec", type=int, default=30, help="Runner HTTP timeout.")
    parser.add_argument("--max-metrics", type=int, default=25, help="Maximum metric tokens to sample.")
    parser.add_argument("--pre-samples", type=int, default=2, help="Samples before browser open.")
    parser.add_argument("--during-samples", type=int, default=4, help="Samples while browser is open.")
    parser.add_argument("--post-samples", type=int, default=8, help="Samples after browser closes.")
    parser.add_argument("--interval-sec", type=float, default=2.0, help="Sample interval.")
    parser.add_argument("--expected-session-timeout-sec", type=float, default=0.0, help="Configured Perspective session timeout for interpretation only.")
    parser.add_argument("--timeout-grace-sec", type=float, default=15.0, help="Grace period added to the expected timeout for coverage checks.")
    parser.add_argument("--require-timeout-coverage", action="store_true", help="Fail when expected timeout plus grace is not covered by post-close samples.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.timeout_grace_sec < 0:
        raise SystemExit("--timeout-grace-sec must be >= 0")
    if args.require_timeout_coverage and args.expected_session_timeout_sec <= 0:
        raise SystemExit("--require-timeout-coverage requires --expected-session-timeout-sec > 0")
    endpoint, token, project = resolve_config(args)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = RunnerClient(endpoint, token, out_dir, args.timeout_sec)
    profile_view = ensure_profile_function()

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

    rows: List[Dict[str, Any]] = []
    rows.extend(sample_phase(client, out_dir, args.run_id, project, "pre", args.pre_samples, args.interval_sec, tokens, feature_set))
    browser_info = start_browser(args, out_dir)
    rows.extend(sample_phase(client, out_dir, args.run_id, project, "during", args.during_samples, args.interval_sec, tokens, feature_set))
    browser_timeout = int(args.browser_timeout_sec + (args.browser_wait_after_ready_ms / 1000.0) + 15)
    browser_info = finish_browser(browser_info, browser_timeout)
    browser_closed_at = utc_now()
    rows.extend(sample_phase(client, out_dir, args.run_id, project, "post", args.post_samples, args.interval_sec, tokens, feature_set))

    log_record = client.call(
        f"{args.run_id}-logQuery",
        {
            "action": "logQuery",
            "requestId": f"{args.run_id}-logQuery",
            "sinceMinutes": 10,
            "levels": ["ERROR", "WARN"],
            "textContains": "Perspective",
            "maxResults": 50,
            "tailBytes": 262144,
        },
    )
    write_json(out_dir / "logs.json", response(log_record))

    phases = {phase: summarize_phase(rows, phase) for phase in ("pre", "during", "post")}
    deltas = {
        "duringMinusPreBrowserSessionsAvg": delta(phases["pre"].get("browserSessionCountAvg"), phases["during"].get("browserSessionCountAvg")),
        "postMinusPreBrowserSessionsAvg": delta(phases["pre"].get("browserSessionCountAvg"), phases["post"].get("browserSessionCountAvg")),
        "postMinusDuringBrowserSessionsAvg": delta(phases["during"].get("browserSessionCountAvg"), phases["post"].get("browserSessionCountAvg")),
        "postMinusPreBrowserPagesAvg": delta(phases["pre"].get("browserActivePagesAvg"), phases["post"].get("browserActivePagesAvg")),
        "postMinusDuringBrowserPagesAvg": delta(phases["during"].get("browserActivePagesAvg"), phases["post"].get("browserActivePagesAvg")),
        "postMinusPreHeapUsedBytesAvg": delta(phases["pre"].get("heapUsedBytesAvg"), phases["post"].get("heapUsedBytesAvg")),
        "postMinusDuringHeapUsedBytesAvg": delta(phases["during"].get("heapUsedBytesAvg"), phases["post"].get("heapUsedBytesAvg")),
    }
    post_observed = max(args.post_samples - 1, 0) * args.interval_sec
    post_release = summarize_post_release(rows)
    post_heap = summarize_post_heap(rows, phases["pre"].get("heapUsedBytesAvg"))
    coverage = timeout_coverage(args, post_observed, post_release, rows)
    interpretation = [
        "This is lifecycle observation, not leak proof.",
        "A retained session/page during a post-close window shorter than the configured Perspective timeout is expected retention, not a leak.",
    ]
    if args.expected_session_timeout_sec and post_observed < args.expected_session_timeout_sec:
        interpretation.append("Post-close observation is shorter than the declared session timeout; do not classify retained sessions as leaks.")
    if deltas.get("postMinusDuringBrowserSessionsAvg") is not None and deltas["postMinusDuringBrowserSessionsAvg"] < 0:
        interpretation.append("Browser session count decreased after browser close in the observed window.")
    pages_zero = post_release.get("firstBrowserPagesZeroSecondsAfterPostStart")
    if isinstance(pages_zero, (int, float)):
        interpretation.append(f"Browser page count reached zero after about {format_number(pages_zero)} seconds of post-close sampling.")
    sessions_zero = post_release.get("firstBrowserSessionsZeroSecondsAfterPostStart")
    if isinstance(sessions_zero, (int, float)):
        interpretation.append(f"Browser session count reached zero after about {format_number(sessions_zero)} seconds of post-close sampling.")
    if coverage.get("coversTimeoutPlusGrace") is True:
        interpretation.append("Post-close observation covered the declared session timeout plus grace.")
    elif coverage.get("coversTimeoutPlusGrace") is False:
        interpretation.append("Post-close observation did not cover the declared session timeout plus grace; timeout-retention conclusions remain gated.")
    if coverage.get("releaseClassification") == "retained-after-timeout-plus-grace":
        interpretation.append("Browser sessions or pages were still present after the declared timeout plus grace; this is retained lifecycle evidence, not proof of a leak without retained work/cost correlation.")
    if deltas.get("postMinusDuringHeapUsedBytesAvg") is not None and deltas["postMinusDuringHeapUsedBytesAvg"] > 0:
        interpretation.append("Average heap-used remained higher after close than during the open window; this needs longer post-settle/GC-aware evidence before leak language.")
    last_minus_pre = post_heap.get("postLastMinusPreAvgHeapUsedBytes")
    if isinstance(last_minus_pre, (int, float)) and last_minus_pre <= 0:
        interpretation.append("The final post-close heap sample was at or below the pre-phase average, which weakens leak suspicion for this short observation.")

    browser_summary = read_json(out_dir / "browser-summary.json")
    summary = {
        "ok": bool(ok(health_record) and ok(view_record) and browser_info.get("exitCode") == 0),
        "runId": args.run_id,
        "project": project,
        "route": route,
        "view": view,
        "phases": phases,
        "deltas": deltas,
        "postRelease": post_release,
        "postHeap": post_heap,
        "timeoutCoverage": coverage,
        "postCloseObservedSeconds": post_observed,
        "expectedSessionTimeoutSeconds": args.expected_session_timeout_sec or None,
        "timeoutGraceSeconds": args.timeout_grace_sec,
        "timeoutCoverageOk": (coverage.get("coversTimeoutPlusGrace") is not False) if args.expected_session_timeout_sec else None,
        "strictTimeoutCoverageRequired": bool(args.require_timeout_coverage),
        "browserProbe": browser_info,
        "browserReady": browser_summary.get("ready"),
        "browserReadyTextMatched": browser_summary.get("readyTextMatched"),
        "interpretation": interpretation,
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
        "features": sorted(feature_set),
        "evidenceGrade": "Observed",
        "scenario": "browser close lifecycle",
        "browserClosedAt": browser_closed_at,
        "preSamples": args.pre_samples,
        "duringSamples": args.during_samples,
        "postSamples": args.post_samples,
        "intervalSeconds": args.interval_sec,
        "postCloseObservedSeconds": post_observed,
        "expectedSessionTimeoutSeconds": args.expected_session_timeout_sec or None,
        "timeoutGraceSeconds": args.timeout_grace_sec,
        "timeoutCoverage": coverage,
        "viewSha256": view_response.get("viewSha256") or static_profile.get("viewSha256"),
        "changedResources": [],
        "missingEvidence": [],
        "browserProbe": browser_info,
        "files": [
            "manifest.json",
            "summary.json",
            "report.md",
            "view-read.json",
            "static-profile.json",
            "metrics-list.json",
            "lifecycle-samples.ndjson",
            "browser-summary.json",
            "browser-console.json",
            "network-summary.json",
            "logs.json",
            "raw/",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)
    make_report(out_dir, manifest, summary)
    print(json.dumps({"ok": summary["ok"], "outDir": str(out_dir), "summary": str(out_dir / "summary.json")}, indent=2, sort_keys=True))
    if args.require_timeout_coverage and coverage.get("coversTimeoutPlusGrace") is not True:
        raise SystemExit("Post-close samples did not cover expected timeout plus grace")
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
