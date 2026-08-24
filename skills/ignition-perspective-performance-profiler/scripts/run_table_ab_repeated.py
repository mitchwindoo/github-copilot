#!/usr/bin/env python3
"""Run repeated guarded table virtualization A/B remediation fixtures."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Set

import collect_profile as cp


SCRIPT_DIR = Path(__file__).resolve().parent
SINGLE_RUN_SCRIPT = SCRIPT_DIR / "run_table_ab_remediation.py"
DEFAULT_METRICS = [
    "largestContentfulPaintMs",
    "longTaskTotalMs",
    "domNodeCount",
    "resourceTransferSize",
    "usedJSHeapBytes",
]
LOWER_IS_BETTER = set(DEFAULT_METRICS + ["elapsedBrowserMs", "loadEventEndMs", "domContentLoadedMs"])
SAFETY_REGRESSION_LIMIT_PCT = 10.0
GATEWAY_SAFETY_METRICS = ["processCpuLoad", "heapUsedBytes", "nonHeapUsedBytes"]
SESSION_SAFETY_METRICS = ["browserRecentBytesSent", "browserTotalBytesSent"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    text = text.strip("-._")
    return text or "table-ab"


def compact_identifier(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "", value)
    return text or "TableAB"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def feature_set_from_health(health: Dict[str, Any]) -> Set[str]:
    features = health.get("features")
    if isinstance(features, list):
        return {str(item) for item in features}
    return set()


def finite_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    return number if math.isfinite(number) else None


def redact_command(command: List[str], token: str) -> List[str]:
    clean: List[str] = []
    skip_next = False
    for index, part in enumerate(command):
        if skip_next:
            skip_next = False
            continue
        if part == "--token" and index + 1 < len(command):
            clean.extend([part, "<redacted>"])
            skip_next = True
        elif token and part == token:
            clean.append("<redacted>")
        else:
            clean.append(part)
    return clean


def to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def browser_counts_from_query(query: Dict[str, Any]) -> Dict[str, int]:
    sessions = query.get("sessions", [])
    browser_sessions = 0
    browser_pages = 0
    if isinstance(sessions, list):
        for session in sessions:
            if not isinstance(session, dict):
                continue
            if str(session.get("sessionScope", "")).lower() != "browser":
                continue
            browser_sessions += 1
            browser_pages += int(to_float(session.get("activePages")) or 0)
    return {"browserSessions": browser_sessions, "browserPages": browser_pages}


def wait_for_clean_baseline(
    client: cp.RunnerClient,
    out_dir: Path,
    run_id: str,
    project: str,
    repetition: int,
    feature_set: Set[str],
    max_browser_sessions: int,
    timeout_sec: float,
    interval_sec: float,
) -> Dict[str, Any]:
    started = time.time()
    attempt = 0
    rows: List[Dict[str, Any]] = []
    if "perspectiveSessionsQuery" not in feature_set:
        result = {
            "enabled": True,
            "ok": False,
            "reason": "perspectiveSessionsQuery feature not present",
            "sampleCount": 0,
            "maxBrowserSessions": max_browser_sessions,
        }
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"repetition": repetition, "sampledAt": utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-tableab-r{repetition:02d}-baselineWait-{attempt:03d}"
        query = cp.response(
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
            "repetition": repetition,
            "attempt": attempt,
            "sampledAt": utc_now(),
            "elapsedSeconds": round(elapsed, 3),
            "maxBrowserSessions": max_browser_sessions,
            **counts,
            "ok": query.get("ok") is not False,
            "clean": counts["browserSessions"] <= max_browser_sessions,
        }
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", row)
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


def build_route(prefix: str, run_slug: str, index: int) -> str:
    prefix = prefix.strip() or "/llm-"
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    return f"{prefix}{run_slug.lower()}-r{index:02d}"


def build_view_path(prefix: str, run_id: str, index: int) -> str:
    prefix = prefix.strip().rstrip("/") or "LLM Tests/PerformanceProfiler"
    return f"{prefix}/{compact_identifier(run_id)}R{index:02d}"


def metric_direction(metric: str) -> str:
    return "lower-is-better" if metric in LOWER_IS_BETTER else "neutral"


def summarize_metric(rows: List[Dict[str, Any]], metric: str) -> Dict[str, Any]:
    deltas: List[float] = []
    pct_deltas: List[float] = []
    controls: List[float] = []
    targets: List[float] = []
    improved = 0
    regressed = 0
    equal = 0
    missing = 0
    for row in rows:
        browser = row.get("comparison", {}).get("browserDeltas", {})
        values = browser.get(metric, {}) if isinstance(browser, dict) else {}
        delta = finite_number(values.get("delta") if isinstance(values, dict) else None)
        pct_delta = finite_number(values.get("pctDelta") if isinstance(values, dict) else None)
        control = finite_number(values.get("control") if isinstance(values, dict) else None)
        target = finite_number(values.get("target") if isinstance(values, dict) else None)
        if delta is None:
            missing += 1
            continue
        deltas.append(delta)
        if pct_delta is not None:
            pct_deltas.append(pct_delta)
        if control is not None:
            controls.append(control)
        if target is not None:
            targets.append(target)
        if metric in LOWER_IS_BETTER:
            if delta < 0:
                improved += 1
            elif delta > 0:
                regressed += 1
            else:
                equal += 1
        else:
            equal += 1
    return {
        "metric": metric,
        "direction": metric_direction(metric),
        "observedCount": len(deltas),
        "missingCount": missing,
        "improvedCount": improved,
        "regressedCount": regressed,
        "equalCount": equal,
        "medianControl": median(controls) if controls else None,
        "medianTarget": median(targets) if targets else None,
        "medianDelta": median(deltas) if deltas else None,
        "medianPctDelta": median(pct_deltas) if pct_deltas else None,
        "minDelta": min(deltas) if deltas else None,
        "maxDelta": max(deltas) if deltas else None,
    }


def summarize_comparison_delta(rows: List[Dict[str, Any]], section: str, metric: str, lower_is_better: bool = True) -> Dict[str, Any]:
    deltas: List[float] = []
    pct_deltas: List[float] = []
    controls: List[float] = []
    targets: List[float] = []
    improved = 0
    regressed = 0
    equal = 0
    missing = 0
    for row in rows:
        bucket = row.get("comparison", {}).get(section, {})
        values = bucket.get(metric, {}) if isinstance(bucket, dict) else {}
        delta = finite_number(values.get("delta") if isinstance(values, dict) else None)
        pct_delta = finite_number(values.get("pctDelta") if isinstance(values, dict) else None)
        control = finite_number(values.get("control") if isinstance(values, dict) else None)
        target = finite_number(values.get("target") if isinstance(values, dict) else None)
        if delta is None:
            missing += 1
            continue
        deltas.append(delta)
        if pct_delta is not None:
            pct_deltas.append(pct_delta)
        if control is not None:
            controls.append(control)
        if target is not None:
            targets.append(target)
        if lower_is_better:
            if delta < 0:
                improved += 1
            elif delta > 0:
                regressed += 1
            else:
                equal += 1
        else:
            equal += 1
    return {
        "metric": metric,
        "section": section,
        "direction": "lower-is-better" if lower_is_better else "neutral",
        "observedCount": len(deltas),
        "missingCount": missing,
        "improvedCount": improved,
        "regressedCount": regressed,
        "equalCount": equal,
        "medianControl": median(controls) if controls else None,
        "medianTarget": median(targets) if targets else None,
        "medianDelta": median(deltas) if deltas else None,
        "medianPctDelta": median(pct_deltas) if pct_deltas else None,
        "minDelta": min(deltas) if deltas else None,
        "maxDelta": max(deltas) if deltas else None,
    }


def evaluate_policy(metric_summary: Dict[str, Any], repetitions: int) -> Dict[str, Any]:
    median_pct = metric_summary.get("medianPctDelta")
    improved_count = metric_summary.get("improvedCount") or 0
    observed_count = metric_summary.get("observedCount") or 0
    return {
        "repetitionsRequired": 7,
        "observedRequired": 7,
        "improvedPairsRequired": 6,
        "medianImprovementPctRequired": 15.0,
        "repetitionsMet": repetitions >= 7,
        "observedMet": observed_count >= 7,
        "improvedPairsMet": improved_count >= 6,
        "medianImprovementMet": median_pct is not None and median_pct <= -15.0,
        "passes": bool(
            repetitions >= 7
            and observed_count >= 7
            and improved_count >= 6
            and median_pct is not None
            and median_pct <= -15.0
        ),
    }


def build_single_command(args: argparse.Namespace, repetition: int, rep_dir: Path) -> List[str]:
    run_slug = slug(args.run_id)
    rep_run_id = f"{run_slug}-r{repetition:02d}"
    command = [
        sys.executable,
        str(SINGLE_RUN_SCRIPT),
        "--run-id",
        rep_run_id,
        "--out-dir",
        str(rep_dir),
        "--route",
        build_route(args.route_prefix, run_slug, repetition),
        "--view-path",
        build_view_path(args.view_path_prefix, args.run_id, repetition),
        "--rows",
        str(args.rows),
        "--columns",
        str(args.columns),
        "--profile-duration-sec",
        str(args.profile_duration_sec),
        "--interval-sec",
        str(args.interval_sec),
        "--max-metrics",
        str(args.max_metrics),
        "--timeout-sec",
        str(args.timeout_sec),
        "--command-timeout-sec",
        str(args.command_timeout_sec),
        "--gateway-alias",
        args.gateway_alias,
        "--browser-url-alias",
        args.browser_url_alias,
        "--browser-ready-selector",
        args.browser_ready_selector,
        "--browser-timeout-sec",
        str(args.browser_timeout_sec),
        "--browser-wait-after-ready-ms",
        str(args.browser_wait_after_ready_ms),
        "--browser-viewport",
        args.browser_viewport,
    ]
    optional_pairs = [
        ("--endpoint", args.endpoint),
        ("--token", args.token),
        ("--project", args.project),
        ("--browser-node-modules", args.browser_node_modules),
    ]
    for flag, value in optional_pairs:
        if value:
            command.extend([flag, value])
    return command


def run_repetitions(args: argparse.Namespace) -> Dict[str, Any]:
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists() and not args.overwrite:
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    commands: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    baseline_client: Optional[cp.RunnerClient] = None
    feature_set: Set[str] = set()
    baseline_health: Dict[str, Any] = {}
    resolved_project = args.project
    if args.wait_for_clean_baseline:
        endpoint, token, project = cp.resolve_config(args)
        resolved_project = project or args.project
        baseline_client = cp.RunnerClient(endpoint, token, out_dir / "baseline-api", args.timeout_sec)
        health_record = baseline_client.call(
            f"{args.run_id}-baseline-health",
            {"action": "health", "requestId": f"{args.run_id}-baseline-health"},
        )
        baseline_health = cp.response(health_record)
        feature_set = feature_set_from_health(baseline_health)
        write_json(out_dir / "baseline-health.json", cp.redact(baseline_health))
    for repetition in range(1, args.repetitions + 1):
        rep_dir = out_dir / f"rep-{repetition:02d}"
        command = build_single_command(args, repetition, rep_dir)
        started = utc_now()
        baseline_wait: Dict[str, Any] = {"enabled": False}
        if args.wait_for_clean_baseline and baseline_client is not None:
            baseline_wait = wait_for_clean_baseline(
                baseline_client,
                out_dir,
                args.run_id,
                resolved_project,
                repetition,
                feature_set,
                args.baseline_max_browser_sessions,
                args.baseline_wait_timeout_sec,
                args.baseline_wait_interval_sec,
            )
            write_json(out_dir / "baseline-waits" / f"rep-{repetition:02d}.json", baseline_wait)
            if args.fail_on_baseline_timeout and not baseline_wait.get("ok"):
                failure = {
                    "repetition": repetition,
                    "reason": "clean baseline was not reached before timeout",
                    "baselineWait": baseline_wait,
                    "repDir": str(rep_dir),
                }
                failures.append(failure)
                rows.append({
                    "repetition": repetition,
                    "repDir": str(rep_dir),
                    "returnCode": None,
                    "baselineWait": baseline_wait,
                    "ok": False,
                })
                break
        result = subprocess.run(
            command,
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=args.repetition_timeout_sec,
        )
        finished = utc_now()
        write_text(out_dir / "command-logs" / f"rep-{repetition:02d}.stdout.txt", result.stdout)
        write_text(out_dir / "command-logs" / f"rep-{repetition:02d}.stderr.txt", result.stderr)
        command_record = {
            "repetition": repetition,
            "startedAt": started,
            "finishedAt": finished,
            "returnCode": result.returncode,
            "command": redact_command(command, args.token or ""),
            "repDir": str(rep_dir),
            "baselineWait": baseline_wait,
        }
        commands.append(command_record)
        summary_path = rep_dir / "summary.json"
        comparison_path = rep_dir / "comparison" / "comparison.json"
        row: Dict[str, Any] = {
            "repetition": repetition,
            "repDir": str(rep_dir),
            "returnCode": result.returncode,
            "summaryPath": str(summary_path),
            "comparisonPath": str(comparison_path),
            "baselineWait": baseline_wait,
        }
        if result.returncode != 0:
            failure = dict(row)
            failure["reason"] = "subprocess returned non-zero"
            failures.append(failure)
            rows.append(row)
            if not args.continue_on_failure:
                break
        elif not summary_path.exists() or not comparison_path.exists():
            failure = dict(row)
            failure["reason"] = "missing summary or comparison output"
            failures.append(failure)
            rows.append(row)
            if not args.continue_on_failure:
                break
        else:
            summary = read_json(summary_path)
            comparison = read_json(comparison_path)
            row["summary"] = summary
            row["comparison"] = comparison
            row["ok"] = bool(summary.get("ok") and comparison.get("ok"))
            if not row["ok"]:
                failures.append({"repetition": repetition, "reason": "summary or comparison not ok", "repDir": str(rep_dir)})
                if not args.continue_on_failure:
                    rows.append(row)
                    break
            rows.append(row)
        if repetition < args.repetitions and args.pause_sec > 0:
            time.sleep(args.pause_sec)

    metric_summaries = {metric: summarize_metric(rows, metric) for metric in args.metrics}
    primary = metric_summaries.get(args.primary_metric, summarize_metric(rows, args.primary_metric))
    policy = evaluate_policy(primary, args.repetitions)
    secondary_regressions = summarize_secondary_regressions(metric_summaries, args.primary_metric)
    safety_coverage = summarize_safety_coverage(rows, metric_summaries, args.primary_metric)
    secondary_regressions["safetyCoverageStatus"] = safety_coverage.get("status")
    secondary_regressions["safetyCoverageRegressionCount"] = safety_coverage.get("regressionCount")
    secondary_regressions["uncovered"] = safety_coverage.get("uncovered", [])
    all_functional = all(
        row.get("summary", {}).get("functionalEquivalence", {}).get("dataHashEqual")
        and row.get("summary", {}).get("functionalEquivalence", {}).get("columnHashEqual")
        and row.get("summary", {}).get("gates", {}).get("cleanupRouteAbsent", {}).get("ok")
        for row in rows
        if row.get("summary")
    )
    drift_guard_all = all(
        row.get("summary", {}).get("gates", {}).get("afterDryRunDriftGuard", {}).get("ok")
        for row in rows
        if row.get("summary")
    )
    rollback_all = all(
        row.get("summary", {}).get("gates", {}).get("rollbackAfterToBefore", {}).get("ok")
        and row.get("summary", {}).get("gates", {}).get("rollbackBeforeCleanup", {}).get("ok")
        for row in rows
        if row.get("summary")
    )
    baseline_waits = [row.get("baselineWait", {}) for row in rows]
    summary = {
        "ok": not failures and len(rows) == args.repetitions and all(row.get("ok") for row in rows),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "scenario": "repeated-table-virtualization-ab",
        "repetitionsRequested": args.repetitions,
        "repetitionsCompleted": len(rows),
        "rows": args.rows,
        "columns": args.columns,
        "primaryMetric": args.primary_metric,
        "causalPolicy": policy,
        "functionalEquivalenceAll": bool(all_functional),
        "driftGuardAll": bool(drift_guard_all),
        "rollbackAll": bool(rollback_all),
        "secondaryRegressionSummary": secondary_regressions,
        "safetyCoverage": safety_coverage,
        "baselineWaits": baseline_waits,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "runnerVersion": baseline_health.get("runnerVersion") if baseline_health else None,
        "stackVersion": baseline_health.get("stackVersion") if baseline_health else None,
        "metricSummaries": metric_summaries,
        "failures": failures,
        "evidenceGrade": "Causal" if policy["passes"] and not failures and all_functional else "Observed",
        "missingEvidence": [],
        "changedResources": [],
        "interpretation": [
            "Repeated table virtualization fixture; each repetition uses a disposable route/view and rolls it back.",
            "Causal wording requires the policy gates to pass plus functional-equivalence and rollback gates.",
            "Safety coverage is explicit for browser, Gateway, session, console, and focused-log evidence; operator latency and business-message checks need workflow-specific fixtures.",
            "Clean-baseline waits reduce retained session contamination, but this remains a local fixture until repeated on a customer-like table and workflow.",
        ],
    }
    write_json(out_dir / "commands.json", commands)
    write_json(out_dir / "runs.json", rows)
    write_json(out_dir / "packages.json", build_packages_index(rows))
    write_json(out_dir / "summary.json", summary)
    write_text(out_dir / "summary.md", render_report(summary))
    write_json(out_dir / "manifest.json", build_manifest(summary))
    return summary


def summarize_secondary_regressions(metric_summaries: Dict[str, Dict[str, Any]], primary_metric: str) -> Dict[str, Any]:
    regressions: List[Dict[str, Any]] = []
    for metric, item in metric_summaries.items():
        if metric == primary_metric:
            continue
        pct_delta = finite_number(item.get("medianPctDelta"))
        if pct_delta is None:
            continue
        if item.get("direction") == "lower-is-better" and pct_delta > SAFETY_REGRESSION_LIMIT_PCT:
            regressions.append({"metric": metric, "medianPctDelta": pct_delta, "limitPct": SAFETY_REGRESSION_LIMIT_PCT})
    return {"regressionCount": len(regressions), "regressions": regressions}


def count_console_entries(profile_dir: Path) -> int:
    path = profile_dir / "browser-console.json"
    if not path.exists():
        return 0
    try:
        data = read_json(path)
    except Exception:
        return 0
    return len(data) if isinstance(data, list) else 0


def count_log_entries(profile_dir: Path) -> int:
    path = profile_dir / "logs.json"
    if not path.exists():
        return 0
    try:
        data = read_json(path)
    except Exception:
        return 0
    if isinstance(data, dict):
        count = finite_number(data.get("count"))
        if count is not None:
            return int(count)
        entries = data.get("entries")
        if isinstance(entries, list):
            return len(entries)
    return 0


def profile_path(row: Dict[str, Any], side: str) -> Optional[Path]:
    comparison = row.get("comparison", {})
    item = comparison.get(side, {}) if isinstance(comparison, dict) else {}
    path = item.get("path") if isinstance(item, dict) else None
    return Path(path) if path else None


def summarize_artifact_counts(rows: List[Dict[str, Any]], filename_label: str, counter) -> Dict[str, Any]:
    control_counts: List[int] = []
    target_counts: List[int] = []
    regressions: List[Dict[str, Any]] = []
    missing = 0
    for row in rows:
        control = profile_path(row, "control")
        target = profile_path(row, "target")
        if control is None or target is None:
            missing += 1
            continue
        control_count = counter(control)
        target_count = counter(target)
        control_counts.append(control_count)
        target_counts.append(target_count)
        if target_count > control_count:
            regressions.append({
                "repetition": row.get("repetition"),
                "control": control_count,
                "target": target_count,
                "delta": target_count - control_count,
            })
    return {
        "artifact": filename_label,
        "observedCount": len(control_counts),
        "missingCount": missing,
        "controlTotal": sum(control_counts),
        "targetTotal": sum(target_counts),
        "medianControl": median(control_counts) if control_counts else None,
        "medianTarget": median(target_counts) if target_counts else None,
        "regressionCount": len(regressions),
        "regressions": regressions,
    }


def summarize_safety_coverage(rows: List[Dict[str, Any]], metric_summaries: Dict[str, Dict[str, Any]], primary_metric: str) -> Dict[str, Any]:
    browser_secondary = summarize_secondary_regressions(metric_summaries, primary_metric)
    gateway = {metric: summarize_comparison_delta(rows, "gatewayDeltas", metric) for metric in GATEWAY_SAFETY_METRICS}
    sessions = {metric: summarize_comparison_delta(rows, "sessionDeltas", metric) for metric in SESSION_SAFETY_METRICS}
    console = summarize_artifact_counts(rows, "browser-console.json", count_console_entries)
    logs = summarize_artifact_counts(rows, "logs.json", count_log_entries)
    regressions: List[Dict[str, Any]] = []
    for metric, item in gateway.items():
        pct_delta = finite_number(item.get("medianPctDelta"))
        if pct_delta is not None and pct_delta > SAFETY_REGRESSION_LIMIT_PCT:
            regressions.append({"dimension": "gateway", "metric": metric, "medianPctDelta": pct_delta, "limitPct": SAFETY_REGRESSION_LIMIT_PCT})
    for metric, item in sessions.items():
        pct_delta = finite_number(item.get("medianPctDelta"))
        if pct_delta is not None and pct_delta > SAFETY_REGRESSION_LIMIT_PCT:
            regressions.append({"dimension": "session", "metric": metric, "medianPctDelta": pct_delta, "limitPct": SAFETY_REGRESSION_LIMIT_PCT})
    if console["regressionCount"]:
        regressions.append({"dimension": "browser-console", "artifact": "browser-console.json", "regressionCount": console["regressionCount"]})
    if logs["regressionCount"]:
        regressions.append({"dimension": "focused-logs", "artifact": "logs.json", "regressionCount": logs["regressionCount"]})
    regressions.extend({"dimension": "browser", **item} for item in browser_secondary.get("regressions", []))
    uncovered = [
        "operator click/action latency is not exercised by this table-render fixture",
        "duplicate process writes or business messages are scenario-specific and not exercised by this fixture",
        "customer workflow correctness beyond table data/column equivalence is not exercised by this fixture",
    ]
    status = "regression-detected" if regressions else "partial"
    return {
        "status": status,
        "limitPct": SAFETY_REGRESSION_LIMIT_PCT,
        "regressionCount": len(regressions),
        "regressions": regressions,
        "covered": {
            "browserMetrics": browser_secondary,
            "gatewayMetrics": gateway,
            "sessionMetrics": sessions,
            "browserConsole": console,
            "focusedLogs": logs,
        },
        "uncovered": uncovered,
        "interpretation": [
            "This safety coverage is explicit for the repeated table fixture, but it does not close V-07 by itself.",
            "Use it to prevent hidden secondary regressions in repeated table A/B runs; add workflow-specific operator latency and message/write checks before V-07 release wording.",
        ],
    }


def build_packages_index(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    packages: List[Dict[str, Any]] = []
    for row in rows:
        summary = row.get("summary")
        if not isinstance(summary, dict):
            continue
        package_info_path = Path(str(row.get("repDir", ""))) / str(summary.get("packageInfoPath", "package-info.json"))
        package_info = read_json(package_info_path) if package_info_path.exists() else {}
        packages.append({
            "repetition": row.get("repetition"),
            "repDir": row.get("repDir"),
            "packageInfoPath": str(package_info_path),
            "packageInfo": package_info,
        })
    return {"packages": packages}


def build_manifest(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "runId": summary.get("runId"),
        "createdAt": utc_now(),
        "scenario": summary.get("scenario"),
        "evidenceGrade": summary.get("evidenceGrade"),
        "runnerVersion": summary.get("runnerVersion"),
        "stackVersion": summary.get("stackVersion"),
        "files": [
            "summary.json",
            "summary.md",
            "runs.json",
            "commands.json",
            "packages.json",
            "command-logs/",
            "rep-*/",
        ],
        "missingEvidence": summary.get("missingEvidence", []),
        "changedResources": summary.get("changedResources", []),
        "waitForCleanBaseline": summary.get("waitForCleanBaseline"),
        "baselineMaxBrowserSessions": summary.get("baselineMaxBrowserSessions"),
    }


def render_report(summary: Dict[str, Any]) -> str:
    lines = [
        "# Repeated Table Virtualization A/B Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary['ok']).lower()}`",
        f"Evidence grade: `{summary['evidenceGrade']}`",
        f"Repetitions: `{summary['repetitionsCompleted']}/{summary['repetitionsRequested']}`",
        f"Primary metric: `{summary['primaryMetric']}`",
        "",
        "## Causal Policy",
        "",
    ]
    policy = summary["causalPolicy"]
    for key in [
        "repetitionsMet",
        "observedMet",
        "improvedPairsMet",
        "medianImprovementMet",
        "passes",
    ]:
        lines.append(f"- `{key}`: `{str(policy.get(key)).lower()}`")
    lines.extend([
        "",
        "## Direct Observations",
        "",
        f"- Completed repetitions: `{summary['repetitionsCompleted']}/{summary['repetitionsRequested']}`.",
        f"- Functional-equivalence gates all passed: `{str(summary.get('functionalEquivalenceAll')).lower()}`.",
        f"- Current-hash drift guard gates all passed: `{str(summary.get('driftGuardAll')).lower()}`.",
        f"- Rollback and cleanup gates all passed: `{str(summary.get('rollbackAll')).lower()}`.",
        f"- Secondary regression count over declared browser safety metrics: `{summary.get('secondaryRegressionSummary', {}).get('regressionCount')}`.",
        f"- Safety coverage status: `{summary.get('safetyCoverage', {}).get('status')}` with `{summary.get('safetyCoverage', {}).get('regressionCount')}` declared safety regressions.",
    ])
    if summary.get("waitForCleanBaseline"):
        starts = [
            item.get("finalBrowserSessions")
            for item in summary.get("baselineWaits", [])
            if isinstance(item, dict) and item.get("enabled")
        ]
        lines.append(f"- Clean-baseline waits were enabled with max browser sessions `{summary.get('baselineMaxBrowserSessions')}`; final browser-session counts were `{starts}`.")
    lines.extend(["", "## Browser Metric Summary", ""])
    lines.append("| Metric | Improved | Median delta | Median pct delta |")
    lines.append("|---|---:|---:|---:|")
    for metric, item in summary["metricSummaries"].items():
        lines.append(
            "| `{}` | `{}/{}` | `{}` | `{}` |".format(
                metric,
                item.get("improvedCount"),
                item.get("observedCount"),
                item.get("medianDelta"),
                item.get("medianPctDelta"),
            )
        )
    safety = summary.get("safetyCoverage", {})
    lines.extend(["", "## Safety Coverage", ""])
    lines.append(f"- Status: `{safety.get('status')}`.")
    lines.append(f"- Regression limit: `{safety.get('limitPct')}` percent median regression for lower-is-better safety metrics.")
    lines.append(f"- Declared safety regression count: `{safety.get('regressionCount')}`.")
    browser = safety.get("covered", {}).get("browserMetrics", {}) if isinstance(safety.get("covered"), dict) else {}
    lines.append(f"- Browser secondary regression count: `{browser.get('regressionCount')}`.")
    console = safety.get("covered", {}).get("browserConsole", {}) if isinstance(safety.get("covered"), dict) else {}
    logs = safety.get("covered", {}).get("focusedLogs", {}) if isinstance(safety.get("covered"), dict) else {}
    lines.append(f"- Browser console entries control/target totals: `{console.get('controlTotal')}/{console.get('targetTotal')}`.")
    lines.append(f"- Focused WARN/ERROR log entries control/target totals: `{logs.get('controlTotal')}/{logs.get('targetTotal')}`.")
    uncovered = safety.get("uncovered", [])
    if uncovered:
        lines.append("- Not covered by this fixture:")
        for item in uncovered:
            lines.append(f"  - {item}")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Unproven Limits",
        "",
        "- Do not claim table virtualization is a universal improvement from this fixture.",
        "- Do not claim customer-route benefit without the same scenario, data shape, cache state, session baseline, functional checks, and repeated paired evidence.",
        "- Treat causal policy failure as a rejected local improvement claim for the declared primary metric, not as proof that virtualization never helps.",
    ])
    if summary.get("failures"):
        lines.extend(["", "## Failures", ""])
        for failure in summary["failures"]:
            lines.append(f"- Repetition `{failure.get('repetition')}`: {failure.get('reason')}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--rows", type=int, default=500)
    parser.add_argument("--columns", type=int, default=30)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--metrics", nargs="+", default=DEFAULT_METRICS)
    parser.add_argument("--primary-metric", default="longTaskTotalMs")
    parser.add_argument("--profile-duration-sec", type=float, default=8.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=300)
    parser.add_argument("--repetition-timeout-sec", type=int, default=900)
    parser.add_argument("--pause-sec", type=float, default=0.0)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=int, default=60)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=5000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each repetition, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline before each repetition.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Fail before the repetition when the requested clean baseline is not reached.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--continue-on-failure", action="store_true")
    args = parser.parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")
    if args.rows < 1 or args.columns < 1:
        raise SystemExit("--rows and --columns must be >= 1")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0:
        raise SystemExit("--baseline-wait-timeout-sec must be >= 0")
    if args.baseline_wait_interval_sec < 0:
        raise SystemExit("--baseline-wait-interval-sec must be >= 0")
    if args.primary_metric not in args.metrics:
        args.metrics = list(args.metrics) + [args.primary_metric]
    return args


def main() -> int:
    args = parse_args()
    summary = run_repetitions(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
