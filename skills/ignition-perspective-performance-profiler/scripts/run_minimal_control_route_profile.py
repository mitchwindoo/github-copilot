#!/usr/bin/env python3
"""Run R-01 minimal/control route cold-warm and lifecycle evidence."""

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
from typing import Any, Dict, List, Optional, Set

import collect_profile as cp


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
COLD_WARM_SCRIPT = SCRIPT_DIR / "run_cold_warm_load_profiles.py"
LIFECYCLE_SCRIPT = SCRIPT_DIR / "run_lifecycle_profile.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_rmtree(path: Path, *allowed_roots: Path) -> None:
    target = path.resolve()
    roots = [root.resolve() for root in allowed_roots if root]
    if not roots or not any(is_relative_to(target, root) for root in roots):
        raise RuntimeError(f"Refusing recursive delete outside intended output roots: {target}")
    if target.exists():
        shutil.rmtree(target)


def fmt(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    try:
        parsed = float(value)
    except Exception:
        return ""
    if not math.isfinite(parsed):
        return ""
    if abs(parsed) >= 1000:
        return f"{parsed:,.0f}"
    return f"{parsed:.4f}".rstrip("0").rstrip(".")


def redact_command(command: List[str]) -> List[str]:
    redacted: List[str] = []
    redact_next = {
        "--browser-url",
        "--endpoint",
        "--token",
        "--browser-ready-text",
        "--browser-node-modules",
    }
    index = 0
    while index < len(command):
        part = command[index]
        redacted.append(part)
        if part in redact_next and index + 1 < len(command):
            redacted.append("<redacted>")
            index += 2
            continue
        index += 1
    return redacted


def to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if math.isfinite(parsed) else None


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
    label: str,
    project: str,
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
            "label": label,
            "enabled": True,
            "ok": False,
            "reason": "perspectiveSessionsQuery feature not present",
            "sampleCount": 0,
            "maxBrowserSessions": max_browser_sessions,
        }
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"sampledAt": utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-{label}-baselineWait-{attempt:03d}"
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
            "label": label,
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
                "label": label,
                "enabled": True,
                "ok": True,
                "timedOut": False,
                "sampleCount": len(rows),
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
                "elapsedSeconds": round(elapsed, 3),
                "maxBrowserSessions": max_browser_sessions,
            }
        if elapsed >= timeout_sec:
            return {
                "label": label,
                "enabled": True,
                "ok": False,
                "timedOut": True,
                "sampleCount": len(rows),
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
                "elapsedSeconds": round(elapsed, 3),
                "maxBrowserSessions": max_browser_sessions,
            }
        attempt += 1
        time.sleep(max(interval_sec, 0.1))


def run_command(command: List[str], out_dir: Path, label: str, timeout_sec: int) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = out_dir / f"{label}.stdout.txt"
    stderr_path = out_dir / f"{label}.stderr.txt"
    record: Dict[str, Any] = {
        "label": label,
        "command": redact_command(command),
        "startedAt": utc_now(),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
    }
    try:
        completed = subprocess.run(
            command,
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_sec if timeout_sec > 0 else None,
        )
        stdout_path.write_text(completed.stdout or "", encoding="utf-8", newline="\n")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8", newline="\n")
        record.update(
            {
                "ok": completed.returncode == 0,
                "returnCode": completed.returncode,
                "timedOut": False,
                "finishedAt": utc_now(),
            }
        )
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text((exc.stdout or "").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or ""), encoding="utf-8", newline="\n")
        stderr_path.write_text((exc.stderr or "").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or ""), encoding="utf-8", newline="\n")
        record.update({"ok": False, "returnCode": None, "timedOut": True, "finishedAt": utc_now()})
    return record


def add_common_browser_args(command: List[str], args: argparse.Namespace) -> None:
    command.extend(
        [
            "--route",
            args.route,
            "--browser-url",
            args.browser_url,
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
            "--gateway-alias",
            args.gateway_alias,
        ]
    )
    optional_args = (
        ("--project", args.project),
        ("--view", args.view),
        ("--endpoint", args.endpoint),
        ("--token", args.token),
        ("--browser-ready-text", args.browser_ready_text),
        ("--browser-node", args.browser_node),
        ("--browser-node-modules", args.browser_node_modules),
    )
    for flag, value in optional_args:
        if value:
            command.extend([flag, value])


def cold_warm_command(args: argparse.Namespace, out_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLD_WARM_SCRIPT),
        "--run-id",
        f"{args.run_id}-coldwarm",
        "--out-dir",
        str((out_dir / "cold-warm").resolve()),
        "--duration-sec",
        str(args.profile_duration_sec),
        "--interval-sec",
        str(args.profile_interval_sec),
        "--cold-repetitions",
        str(args.cold_repetitions),
        "--warm-repetitions",
        str(args.warm_repetitions),
        "--command-timeout-sec",
        str(args.child_command_timeout_sec),
        "--pause-sec",
        str(args.pause_sec),
    ]
    add_common_browser_args(command, args)
    return command


def lifecycle_command(args: argparse.Namespace, out_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(LIFECYCLE_SCRIPT),
        "--run-id",
        f"{args.run_id}-lifecycle",
        "--out-dir",
        str((out_dir / "lifecycle").resolve()),
        "--timeout-sec",
        str(args.timeout_sec),
        "--max-metrics",
        str(args.max_metrics),
        "--pre-samples",
        str(args.lifecycle_pre_samples),
        "--during-samples",
        str(args.lifecycle_during_samples),
        "--post-samples",
        str(args.lifecycle_post_samples),
        "--interval-sec",
        str(args.lifecycle_interval_sec),
        "--expected-session-timeout-sec",
        str(args.expected_session_timeout_sec),
        "--timeout-grace-sec",
        str(args.timeout_grace_sec),
    ]
    if args.require_timeout_coverage:
        command.append("--require-timeout-coverage")
    add_common_browser_args(command, args)
    return command


def phase_count(summary: Dict[str, Any], phase: str) -> int:
    by_phase = summary.get("aggregates", {}).get("byPhase", {})
    item = by_phase.get(phase, {}) if isinstance(by_phase, dict) else {}
    return int(item.get("count") or 0) if isinstance(item, dict) else 0


def phase_ok_count(summary: Dict[str, Any], phase: str) -> int:
    by_phase = summary.get("aggregates", {}).get("byPhase", {})
    item = by_phase.get(phase, {}) if isinstance(by_phase, dict) else {}
    return int(item.get("okCount") or 0) if isinstance(item, dict) else 0


def metric_median(summary: Dict[str, Any], phase: str, metric: str) -> Optional[float]:
    by_phase = summary.get("aggregates", {}).get("byPhase", {})
    phase_item = by_phase.get(phase, {}) if isinstance(by_phase, dict) else {}
    metrics = phase_item.get("metrics", {}) if isinstance(phase_item, dict) else {}
    item = metrics.get(metric, {}) if isinstance(metrics, dict) else {}
    value = item.get("median") if isinstance(item, dict) else None
    return float(value) if isinstance(value, (int, float)) else None


def summarize(
    cold_warm_summary: Dict[str, Any],
    lifecycle_summary: Dict[str, Any],
    baseline_waits: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    timeout = lifecycle_summary.get("timeoutCoverage", {})
    post_release = lifecycle_summary.get("postRelease", {})
    cold_count = phase_count(cold_warm_summary, "cold")
    warm_count = phase_count(cold_warm_summary, "warm")
    cold_ok_count = phase_ok_count(cold_warm_summary, "cold")
    warm_ok_count = phase_ok_count(cold_warm_summary, "warm")
    coverage = {
        "baselineWaitsOk": all(bool(item.get("ok")) for item in baseline_waits) if baseline_waits else None,
        "coldRepetitionsMet": cold_count >= args.cold_repetitions and cold_ok_count >= args.cold_repetitions,
        "warmRepetitionsMet": warm_count >= args.warm_repetitions and warm_ok_count >= args.warm_repetitions,
        "warmPrimeOk": bool(cold_warm_summary.get("warmPrimeOk")),
        "lifecycleOk": bool(lifecycle_summary.get("ok")),
        "timeoutCoverageOk": bool(lifecycle_summary.get("timeoutCoverageOk")),
        "coversTimeoutPlusGrace": bool(timeout.get("coversTimeoutPlusGrace")) if isinstance(timeout, dict) else False,
        "browserPagesStableZeroAfterFirstZero": bool(post_release.get("stableBrowserPagesZeroAfterFirstZero")) if isinstance(post_release, dict) else False,
        "browserSessionsStableZeroAfterFirstZero": bool(post_release.get("stableBrowserSessionsZeroAfterFirstZero")) if isinstance(post_release, dict) else False,
        "lastPostBrowserPages": timeout.get("lastPostBrowserPages") if isinstance(timeout, dict) else None,
        "lastPostBrowserSessions": timeout.get("lastPostBrowserSessions") if isinstance(timeout, dict) else None,
        "releaseClassification": timeout.get("releaseClassification") if isinstance(timeout, dict) else "",
    }
    coverage["stableZeroByFinalPostSample"] = coverage["lastPostBrowserPages"] == 0 and coverage["lastPostBrowserSessions"] == 0
    ok = all(
        [
            bool(cold_warm_summary.get("ok")),
            coverage["baselineWaitsOk"] is not False,
            coverage["coldRepetitionsMet"],
            coverage["warmRepetitionsMet"],
            coverage["warmPrimeOk"],
            coverage["lifecycleOk"],
            coverage["timeoutCoverageOk"],
            coverage["coversTimeoutPlusGrace"],
            coverage["stableZeroByFinalPostSample"],
        ]
    )
    return {
        "ok": ok,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "route": args.route,
        "view": args.view,
        "browserUrlAlias": args.browser_url_alias,
        "gatewayAlias": args.gateway_alias,
        "coldWarm": {
            "ok": bool(cold_warm_summary.get("ok")),
            "coldCount": cold_count,
            "coldOkCount": cold_ok_count,
            "warmCount": warm_count,
            "warmOkCount": warm_ok_count,
            "warmPrimeOk": bool(cold_warm_summary.get("warmPrimeOk")),
            "coldReadyWallMedianMs": metric_median(cold_warm_summary, "cold", "primaryReadyElapsedWallMs"),
            "warmReadyWallMedianMs": metric_median(cold_warm_summary, "warm", "primaryReadyElapsedWallMs"),
            "warmMinusColdMedianDeltas": cold_warm_summary.get("aggregates", {}).get("warmMinusColdMedianDeltas", {}),
        },
        "lifecycle": {
            "ok": bool(lifecycle_summary.get("ok")),
            "timeoutCoverageOk": bool(lifecycle_summary.get("timeoutCoverageOk")),
            "postCloseObservedSeconds": lifecycle_summary.get("postCloseObservedSeconds"),
            "expectedSessionTimeoutSeconds": lifecycle_summary.get("expectedSessionTimeoutSeconds"),
            "timeoutGraceSeconds": lifecycle_summary.get("timeoutGraceSeconds"),
            "timeoutCoverage": timeout,
            "postRelease": post_release,
            "postHeap": lifecycle_summary.get("postHeap", {}),
        },
        "baselineWaits": baseline_waits,
        "coverage": coverage,
        "notes": [
            "Read-only R-01 control-route wrapper.",
            "Cold observations use fresh Chromium profile directories; warm observations use one primed shared profile.",
            "Lifecycle interpretation is timeout-aware and does not claim leak/no-leak proof.",
        ],
    }


def write_report(out_dir: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    cold = summary.get("coldWarm", {})
    lifecycle = summary.get("lifecycle", {})
    coverage = summary.get("coverage", {})
    timeout = lifecycle.get("timeoutCoverage", {}) if isinstance(lifecycle, dict) else {}
    lines = [
        "# R-01 Minimal Control Route Profile",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Route: `{manifest['route']}`",
        f"View: `{manifest.get('view') or '<resolved by route inventory>'}`",
        f"Evidence grade: `{manifest.get('evidenceGrade')}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        "",
        "## Direct Observations",
        "",
        f"- Cold route loads: `{cold.get('coldOkCount')}` / `{cold.get('coldCount')}` counted observations passed.",
        f"- Warm route loads: `{cold.get('warmOkCount')}` / `{cold.get('warmCount')}` counted observations passed after an uncounted warm prime.",
        f"- Cold ready wall median: `{fmt(cold.get('coldReadyWallMedianMs'))}` ms.",
        f"- Warm ready wall median: `{fmt(cold.get('warmReadyWallMedianMs'))}` ms.",
        f"- Post-close observed window: `{fmt(lifecycle.get('postCloseObservedSeconds'))}` seconds.",
        f"- Timeout coverage classification: `{coverage.get('releaseClassification')}`.",
        f"- Last post browser sessions/pages: `{coverage.get('lastPostBrowserSessions')}` / `{coverage.get('lastPostBrowserPages')}`.",
        "",
        "## Coverage Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for key in (
        "baselineWaitsOk",
        "coldRepetitionsMet",
        "warmRepetitionsMet",
        "warmPrimeOk",
        "lifecycleOk",
        "timeoutCoverageOk",
        "coversTimeoutPlusGrace",
        "stableZeroByFinalPostSample",
    ):
        lines.append(f"| `{key}` | `{coverage.get(key)}` |")
    lines.extend(
        [
            "",
            "## Timeout Details",
            "",
            f"- Expected timeout: `{fmt(timeout.get('expectedSessionTimeoutSeconds'))}` seconds.",
            f"- Grace: `{fmt(timeout.get('timeoutGraceSeconds'))}` seconds.",
            f"- Required observation: `{fmt(timeout.get('requiredObservedSeconds'))}` seconds.",
            f"- Covered timeout plus grace: `{timeout.get('coversTimeoutPlusGrace')}`.",
            "",
            "## Baseline Waits",
            "",
        ]
    )
    waits = summary.get("baselineWaits", [])
    if waits:
        lines.extend(["| Label | OK | Samples | Final browser sessions | Final browser pages |", "|---|---|---:|---:|---:|"])
        for item in waits:
            if isinstance(item, dict):
                lines.append(
                    "| {label} | `{ok}` | {samples} | {sessions} | {pages} |".format(
                        label=item.get("label", ""),
                        ok=item.get("ok"),
                        samples=item.get("sampleCount", ""),
                        sessions=item.get("finalBrowserSessions", ""),
                        pages=item.get("finalBrowserPages", ""),
                    )
                )
    else:
        lines.append("- Baseline wait was not enabled.")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This bundle is a minimal/control baseline for the selected Gateway and route, not a customer-wide performance conclusion.",
            "- Cold/warm deltas describe browser profile/cache state for this route only.",
            "- Session/page release is interpreted against the declared timeout plus grace.",
            "",
            "## Unproven / Non-Causal Limits",
            "",
            "- This run is not proof that a customer target route is healthy or unhealthy.",
            "- This run does not prove a leak or no-leak condition by itself.",
            "- Remediation claims still require a separate guarded A/B run against the real candidate change.",
            "",
            "## Child Evidence",
            "",
            "- `cold-warm/summary.json` and `cold-warm/summary.md`",
            "- `lifecycle/summary.json` and `lifecycle/report.md`",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--route", default="/")
    parser.add_argument("--view", default="")
    parser.add_argument("--browser-url", required=True)
    parser.add_argument("--browser-url-alias", default="configured-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-ready-text", default="")
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=3000)
    parser.add_argument("--browser-node", default="node")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--gateway-alias", default="configured-gateway")
    parser.add_argument("--profile-duration-sec", type=float, default=8.0)
    parser.add_argument("--profile-interval-sec", type=float, default=2.0)
    parser.add_argument("--cold-repetitions", type=int, default=5)
    parser.add_argument("--warm-repetitions", type=int, default=5)
    parser.add_argument("--pause-sec", type=float, default=0.0)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--max-metrics", type=int, default=40)
    parser.add_argument("--lifecycle-pre-samples", type=int, default=2)
    parser.add_argument("--lifecycle-during-samples", type=int, default=4)
    parser.add_argument("--lifecycle-post-samples", type=int, default=20)
    parser.add_argument("--lifecycle-interval-sec", type=float, default=5.0)
    parser.add_argument("--expected-session-timeout-sec", type=float, default=75.0)
    parser.add_argument("--timeout-grace-sec", type=float, default=15.0)
    parser.add_argument("--require-timeout-coverage", action="store_true")
    parser.add_argument("--wait-for-clean-baseline", action="store_true")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0)
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=120.0)
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0)
    parser.add_argument("--fail-on-baseline-timeout", action="store_true")
    parser.add_argument("--child-command-timeout-sec", type=int, default=900)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.cold_repetitions < 1 or args.warm_repetitions < 1:
        raise SystemExit("Cold and warm repetitions must be >= 1")
    if args.profile_duration_sec < 0 or args.profile_interval_sec <= 0:
        raise SystemExit("Profile duration must be >= 0 and profile interval must be > 0")
    if args.lifecycle_interval_sec <= 0:
        raise SystemExit("--lifecycle-interval-sec must be > 0")
    if args.expected_session_timeout_sec < 0 or args.timeout_grace_sec < 0:
        raise SystemExit("Timeout and grace values must be >= 0")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0 or args.baseline_wait_interval_sec <= 0:
        raise SystemExit("Baseline wait timeout must be >= 0 and interval must be > 0")
    observed = max(args.lifecycle_post_samples - 1, 0) * args.lifecycle_interval_sec
    required = args.expected_session_timeout_sec + args.timeout_grace_sec
    if args.require_timeout_coverage and observed < required:
        raise SystemExit(
            "--require-timeout-coverage needs lifecycle post observation to cover expected timeout plus grace "
            f"({observed} observed seconds < {required} required seconds)"
        )


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        safe_rmtree(out_dir, Path.cwd(), SKILL_DIR)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, Any] = {
        "ok": False,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "bundleType": "composite-wrapper",
        "scenario": "R-01 minimal control route composite-wrapper",
        "route": args.route,
        "view": args.view,
        "gatewayAlias": args.gateway_alias,
        "browserUrlAlias": args.browser_url_alias,
        "evidenceGrade": "Observed",
        "changedResources": [],
        "missingEvidence": [],
        "evidenceFiles": [
            "summary.json",
            "summary.md",
            "child-commands.json",
            "baseline-wait-samples.ndjson",
            "api/",
            "cold-warm/",
            "lifecycle/",
        ],
        "notes": [
            "Read-only wrapper around cold/warm route-load and lifecycle timeout evidence.",
            "Raw browser URLs, tokens, endpoints, and node_modules paths are redacted from wrapper command evidence.",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)

    child_commands: List[Dict[str, Any]] = []
    baseline_waits: List[Dict[str, Any]] = []
    client: Optional[cp.RunnerClient] = None
    feature_set: Set[str] = set()
    project = args.project
    if args.wait_for_clean_baseline:
        endpoint, token, project = cp.resolve_config(args)
        client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
        health = cp.response(client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"}))
        features = health.get("features", [])
        feature_set = set(features if isinstance(features, list) else [key for key, value in features.items() if value])
        if not project:
            projects = cp.response(client.call(f"{args.run_id}-projectsList", {"action": "projectsList", "requestId": f"{args.run_id}-projectsList", "maxResults": 100})).get("projects", [])
            if projects and isinstance(projects[0], dict):
                project = str(projects[0].get("projectName") or projects[0].get("name") or "")
            elif projects:
                project = str(projects[0])
        baseline_waits.append(
            wait_for_clean_baseline(
                client,
                out_dir,
                args.run_id,
                "before-cold-warm",
                project,
                feature_set,
                args.baseline_max_browser_sessions,
                args.baseline_wait_timeout_sec,
                args.baseline_wait_interval_sec,
            )
        )
        if args.fail_on_baseline_timeout and not baseline_waits[-1].get("ok"):
            write_json(out_dir / "baseline-waits.json", baseline_waits)
            raise SystemExit("Clean baseline was not reached before cold/warm profiling")
    cold_result = run_command(cold_warm_command(args, out_dir), out_dir / "driver-logs", "cold-warm", args.child_command_timeout_sec)
    child_commands.append(cold_result)
    if args.wait_for_clean_baseline and client is not None:
        baseline_waits.append(
            wait_for_clean_baseline(
                client,
                out_dir,
                args.run_id,
                "before-lifecycle",
                project,
                feature_set,
                args.baseline_max_browser_sessions,
                args.baseline_wait_timeout_sec,
                args.baseline_wait_interval_sec,
            )
        )
        if args.fail_on_baseline_timeout and not baseline_waits[-1].get("ok"):
            write_json(out_dir / "baseline-waits.json", baseline_waits)
            write_json(out_dir / "child-commands.json", child_commands)
            raise SystemExit("Clean baseline was not reached before lifecycle profiling")
    lifecycle_result = run_command(lifecycle_command(args, out_dir), out_dir / "driver-logs", "lifecycle", args.child_command_timeout_sec)
    child_commands.append(lifecycle_result)
    write_json(out_dir / "child-commands.json", child_commands)
    write_json(out_dir / "baseline-waits.json", baseline_waits)

    cold_warm_summary = read_json(out_dir / "cold-warm" / "summary.json")
    lifecycle_summary = read_json(out_dir / "lifecycle" / "summary.json")
    summary = summarize(cold_warm_summary, lifecycle_summary, baseline_waits, args)
    summary["childCommandsOk"] = all(bool(item.get("ok")) for item in child_commands)
    summary["ok"] = bool(summary["ok"] and summary["childCommandsOk"])
    manifest["ok"] = summary["ok"]
    manifest["finishedAt"] = utc_now()
    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "summary.json", summary)
    write_report(out_dir, manifest, summary)
    print(json.dumps({"ok": summary["ok"], "summaryPath": str(out_dir / "summary.json")}, indent=2, sort_keys=True))
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
