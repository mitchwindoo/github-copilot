#!/usr/bin/env python3
"""Run a bounded long-running Perspective script incident fixture for I-03/I-01.

The fixture is development/staging oriented. It imports one disposable
Perspective route/view with a button whose Gateway-scoped action script sleeps
in short bounded intervals, logs run-marker start/end lines, and updates a
visible result marker. While the browser-triggered script is expected to be
active, the harness captures metrics, sessions, Gateway performance, logs, and
one bounded thread dump. It also records an active-window screenshot/timestamp
and checks the same route in a second browser context while the first session is
still waiting for the script result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_property_change_chain as storm_common
import run_table_ab_remediation as table_common


SCRIPT_DIR = Path(__file__).resolve().parent
BROWSER_PROBE = SCRIPT_DIR / "browser_long_script_probe.mjs"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"


def utc_now() -> str:
    return common.utc_now()


def canonical_json(data: Any) -> str:
    return common.canonical_json(data)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, data: Any) -> None:
    common.write_json(path, data)


def read_json(path: Path) -> Dict[str, Any]:
    return common.read_json(path)


def safe_rmtree(path: Path, *allowed_roots: Path) -> None:
    storm_common.safe_rmtree(path, *allowed_roots)


def component(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return storm_common.component(*args, **kwargs)


def property_binding(path: str, transform_code: str = "") -> Dict[str, Any]:
    return storm_common.property_binding(path, transform_code)


def text_transform(prefix: str) -> str:
    return storm_common.text_transform(prefix)


def action_script() -> str:
    return "\n".join(
        [
            "\timport time",
            "\tlogger = system.util.getLogger('perfprof.longscript')",
            "\ttry:",
            "\t\ttarget_ms = int(self.view.custom.targetMillis)",
            "\texcept:",
            "\t\ttarget_ms = 1000",
            "\ttry:",
            "\t\tmax_ms = int(self.view.custom.maxMillis)",
            "\texcept:",
            "\t\tmax_ms = 1000",
            "\tif target_ms < 1:",
            "\t\ttarget_ms = 1",
            "\tif max_ms < 1:",
            "\t\tmax_ms = 1",
            "\tif target_ms > max_ms:",
            "\t\ttarget_ms = max_ms",
            "\tmarker = str(self.view.custom.runId) + ' ' + str(self.view.custom.variant)",
            "\tself.view.custom.doneText = 'I-03 RUNNING ' + str(target_ms)",
            "\tself.view.custom.loopCount = 0",
            "\tself.view.custom.lastError = ''",
            "\tlogger.info(marker + ' I-03 bounded long script START targetMillis=' + str(target_ms))",
            "\tdeadline = time.time() + (float(target_ms) / 1000.0)",
            "\tloops = 0",
            "\ttry:",
            "\t\twhile time.time() < deadline:",
            "\t\t\tloops += 1",
            "\t\t\tremaining = deadline - time.time()",
            "\t\t\tif remaining > 0:",
            "\t\t\t\ttime.sleep(min(0.05, remaining))",
            "\t\tself.view.custom.loopCount = loops",
            "\t\tself.view.custom.doneText = 'I-03 DONE ' + str(target_ms)",
            "\t\tlogger.info(marker + ' I-03 bounded long script DONE loops=' + str(loops))",
            "\texcept Exception as err:",
            "\t\tself.view.custom.lastError = str(err)",
            "\t\tself.view.custom.doneText = 'I-03 ERROR ' + str(err)",
            "\t\tlogger.warn(marker + ' I-03 bounded long script ERROR ' + str(err))",
        ]
    ) + "\n"


def make_view_json(args: argparse.Namespace) -> Dict[str, Any]:
    ready = f"{args.run_id} I-03 READY"
    return {
        "custom": {
            "runId": args.run_id,
            "variant": "long-script",
            "targetMillis": args.target_millis,
            "maxMillis": args.max_millis,
            "doneText": "I-03 PENDING",
            "loopCount": 0,
            "lastError": "",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "long-script-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "style": {"backgroundColor": "#f8fafc", "overflow": "auto", "padding": "12px"},
            },
            children=[
                component(
                    "ia.display.label",
                    meta={"name": "Ready Marker"},
                    position={"basis": "38px", "grow": 0, "shrink": 0},
                    props={
                        "text": ready,
                        "style": {
                            "backgroundColor": "#ffffff",
                            "borderColor": "#64748b",
                            "borderRadius": 4,
                            "borderStyle": "solid",
                            "borderWidth": "1px",
                            "color": "#111827",
                            "fontSize": 16,
                            "fontWeight": "700",
                            "padding": "8px 10px",
                        },
                    },
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Scenario Summary"},
                    position={"basis": "52px", "grow": 0, "shrink": 0},
                    props={
                        "text": f"I-03 bounded long-running script fixture: target {args.target_millis} ms, hard cap {args.max_millis} ms",
                        "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
                    },
                ),
                component(
                    "ia.input.button",
                    meta={"name": "RunLongScriptButton"},
                    position={"basis": "46px", "grow": 0, "shrink": 0},
                    props={
                        "primary": True,
                        "style": {"alignSelf": "flex-start", "fontSize": 14, "fontWeight": "700", "maxWidth": "260px"},
                        "text": "Run bounded long script",
                    },
                    events={
                        "component": {
                            "onActionPerformed": {"scope": "G", "type": "script", "config": {"script": action_script()}}
                        }
                    },
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Done Marker"},
                    position={"basis": "38px", "grow": 0, "shrink": 0},
                    props={
                        "text": "I-03 PENDING",
                        "style": {
                            "backgroundColor": "#ecfdf5",
                            "borderColor": "#10b981",
                            "borderRadius": 4,
                            "borderStyle": "solid",
                            "borderWidth": "1px",
                            "color": "#064e3b",
                            "fontSize": 15,
                            "fontWeight": "700",
                            "padding": "7px 10px",
                        },
                    },
                    prop_config={"props.text": property_binding("view.custom.doneText")},
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Loop Marker"},
                    position={"basis": "34px", "grow": 0, "shrink": 0},
                    props={"text": "loops: 0", "style": {"color": "#111827", "fontSize": 13, "padding": "6px 2px"}},
                    prop_config={"props.text": property_binding("view.custom.loopCount", text_transform("loops: "))},
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Error Marker"},
                    position={"basis": "34px", "grow": 0, "shrink": 0},
                    props={"text": "", "style": {"color": "#991b1b", "fontSize": 13, "padding": "6px 2px"}},
                    prop_config={"props.text": property_binding("view.custom.lastError", text_transform("error: "))},
                ),
            ],
        ),
    }


def build_package(out_dir: Path, project: str, args: argparse.Namespace, view_path: str, route: str) -> Dict[str, Any]:
    zip_dir = out_dir / "package"
    if zip_dir.exists():
        safe_rmtree(zip_dir, out_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-long-script"
    view_json = make_view_json(args)
    zip_path = zip_dir / "fixture.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-long-script-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            project_root / "project.json",
            {"title": project, "description": "Performance profiler long-running script fixture", "enabled": True, "inheritable": False},
        )
        storm_common.write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": "Long Script Incident", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", table_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    package_base64 = common.zip_file_base64(zip_path)
    return {
        "route": route,
        "viewPath": view_path,
        "zipPath": str(zip_path),
        "zipBytes": zip_path.stat().st_size,
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": package_base64,
        "packageBase64Bytes": len(package_base64),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": f"{args.run_id} I-03 READY",
        "resultText": f"I-03 DONE {args.target_millis}",
        "buttonText": "Run bounded long script",
    }


def package_payload(action: str, request_id: str, project: str, package: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": action,
        "requestId": request_id,
        "targetProject": project,
        "packageName": Path(str(package["zipPath"])).name,
        "packageBase64": package["packageBase64"],
        "allowedViewPrefix": args.allowed_view_prefix,
        "allowedRoutePrefix": args.allowed_route_prefix,
        "allowedScriptPrefix": "llm",
        "allowedNamedQueryPrefix": args.allowed_view_prefix,
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": "Long Script Incident"}],
        "dependencyViewPaths": [],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [],
        "sharedDockKeys": [],
        "allowOverwrite": False,
    }
    if action == "apply":
        payload["confirmApply"] = "APPLY"
    return payload


def view_read_payload(request_id: str, project: str, view_path: str, args: argparse.Namespace) -> Dict[str, Any]:
    return storm_common.view_read_payload(request_id, project, view_path, args)


def page_validate_payload(request_id: str, project: str, package: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    return storm_common.page_validate_payload(request_id, project, package, args)


def rollback_payload(request_id: str, project: str, backup_name: str, view_path: str, dry_run: bool) -> Dict[str, Any]:
    return storm_common.rollback_payload(request_id, project, backup_name, view_path, dry_run)


def readback_ok(record: Dict[str, Any], package: Dict[str, Any], args: argparse.Namespace) -> bool:
    response_text = canonical_json(cp.response(record))
    return (
        cp.ok(record)
        and str(package["readyText"]) in response_text
        and str(package["buttonText"]) in response_text
        and "I-03 DONE " in response_text
        and "perfprof.longscript" in response_text
        and f'"targetMillis":{args.target_millis}' in response_text
        and f'"maxMillis":{args.max_millis}' in response_text
    )


def feature_set_from_health(health: Dict[str, Any]) -> set[str]:
    response = cp.response(health)
    features = response.get("features", [])
    if not isinstance(features, list):
        return set()
    return {str(item) for item in features}


def metric_value(row: Dict[str, Any]) -> Optional[float]:
    for key in ("count", "value", "meanRate", "oneMinuteRate"):
        value = row.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def metric_counts(snapshot: Dict[str, Any]) -> Dict[str, float]:
    rows = snapshot.get("metrics", [])
    if not isinstance(rows, list):
        return {}
    result: Dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("ok") is not True:
            continue
        name = str(row.get("name") or row.get("token") or "")
        if not name:
            continue
        value = metric_value(row)
        if value is not None:
            result[name] = value
    return result


def metric_delta(first: Dict[str, Any], last: Dict[str, Any], contains: str) -> Optional[float]:
    before = metric_counts(first)
    after = metric_counts(last)
    keys = [key for key in after if contains.lower() in key.lower() and key in before]
    if not keys:
        return None
    return max(after[key] - before[key] for key in keys)


def call_metric_sample(client: cp.RunnerClient, run_id: str, index: int, project: str, tokens: List[str], feature_set: set[str]) -> Dict[str, Any]:
    sample: Dict[str, Any] = {"sampleIndex": index, "capturedAt": utc_now()}
    if tokens and "metricsSnapshot" in feature_set:
        record = client.call(
            f"{run_id}-metricsSnapshot-{index:03d}",
            {"action": "metricsSnapshot", "requestId": f"{run_id}-metricsSnapshot-{index:03d}", "metricTokens": tokens, "maxMetrics": len(tokens)},
        )
        sample["metricsSnapshot"] = cp.response(record)
    if "gatewayPerformanceSnapshot" in feature_set:
        record = client.call(
            f"{run_id}-gatewayPerformanceSnapshot-{index:03d}",
            {"action": "gatewayPerformanceSnapshot", "requestId": f"{run_id}-gatewayPerformanceSnapshot-{index:03d}"},
        )
        sample["gatewayPerformanceSnapshot"] = cp.response(record)
    if "perspectiveSessionsQuery" in feature_set:
        record = client.call(
            f"{run_id}-perspectiveSessionsQuery-{index:03d}",
            {
                "action": "perspectiveSessionsQuery",
                "requestId": f"{run_id}-perspectiveSessionsQuery-{index:03d}",
                "targetProject": project,
                "includeIdentifiers": False,
                "includeUserAgent": False,
                "includeClientAddress": False,
                "maxResults": 50,
            },
        )
        sample["perspectiveSessionsQuery"] = cp.response(record)
    return sample


def thread_dump_payload(request_id: str, args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "threadDumpQuery",
        "requestId": request_id,
        "threadNameContains": args.thread_name_contains,
        "stackContains": args.stack_contains,
        "maxThreads": args.max_threads,
        "maxFramesPerThread": args.max_frames_per_thread,
        "redact": True,
        "confirmSensitiveDiagnostic": "READ_BOUNDED_THREAD_DUMP",
    }
    if not args.stack_contains:
        payload.pop("stackContains", None)
    return payload


def run_browser_probe(args: argparse.Namespace, browser_url: str, package: Dict[str, Any], out_dir: Path, signal_file: Path) -> subprocess.Popen:
    env = dict(os.environ)
    if args.browser_node_modules:
        roots = [Path(args.browser_node_modules).resolve()]
        pnpm_root = roots[0] / ".pnpm" / "node_modules"
        if pnpm_root.exists():
            roots.append(pnpm_root)
        current = env.get("NODE_PATH", "")
        entries = [str(root) for root in roots]
        if current:
            entries.append(current)
        env["NODE_PATH"] = os.pathsep.join(entries)
    browser_out_dir = out_dir.resolve()
    click_signal_file = signal_file.resolve()
    command = [
        args.browser_node,
        str(BROWSER_PROBE),
        "--url",
        browser_url,
        "--out-dir",
        str(browser_out_dir),
        "--url-alias",
        args.browser_url_alias,
        "--ready-selector",
        args.browser_ready_selector,
        "--ready-text",
        package["readyText"],
        "--button-text",
        package["buttonText"],
        "--result-text",
        package["resultText"],
        "--click-signal-file",
        str(click_signal_file),
        "--timeout-ms",
        str(int(args.browser_timeout_sec * 1000)),
        "--result-timeout-ms",
        str(int(args.browser_result_timeout_sec * 1000)),
        "--wait-after-result-ms",
        str(args.browser_wait_after_result_ms),
        "--viewport",
        args.browser_viewport,
    ]
    write_json(
        out_dir / "browser-command.json",
        {
            "command": [item if item != browser_url else "<browser-url-redacted>" for item in command],
            "cwd": str(SCRIPT_DIR),
            "nodePathEntries": env.get("NODE_PATH", "").split(os.pathsep) if env.get("NODE_PATH") else [],
            "outDir": str(browser_out_dir),
            "clickSignalFile": str(click_signal_file),
        },
    )
    stdout = (out_dir / "browser-probe.stdout.txt").open("w", encoding="utf-8", newline="\n")
    stderr = (out_dir / "browser-probe.stderr.txt").open("w", encoding="utf-8", newline="\n")
    try:
        return subprocess.Popen(command, cwd=str(SCRIPT_DIR), env=env, stdout=stdout, stderr=stderr)
    finally:
        stdout.close()
        stderr.close()


def wait_for_signal(signal_file: Path, timeout_sec: float) -> Dict[str, Any]:
    started = time.time()
    while time.time() - started <= timeout_sec:
        if signal_file.exists():
            try:
                data = read_json(signal_file)
            except Exception as exc:
                data = {"ok": False, "error": repr(exc)}
            data["waitElapsedSec"] = time.time() - started
            return data
        time.sleep(0.1)
    return {"ok": False, "error": "timed out waiting for click signal", "waitElapsedSec": time.time() - started}


def session_local_probe_args(args: argparse.Namespace, browser_url: str, ready_text: str) -> argparse.Namespace:
    return argparse.Namespace(
        browser_url=browser_url,
        browser_node=args.browser_node,
        browser_node_modules=args.browser_node_modules,
        browser_ready_selector=args.browser_ready_selector,
        browser_ready_text=ready_text,
        browser_secondary_ready_selector="",
        browser_secondary_ready_text="",
        browser_timeout_sec=args.session_local_timeout_sec,
        browser_viewport=args.browser_viewport,
        browser_wait_after_ready_ms=args.session_local_wait_after_ready_ms,
        browser_url_alias=args.browser_url_alias or args.gateway_alias,
        gateway_alias=args.gateway_alias,
        browser_click_selector="",
        browser_click_text="",
        browser_click_label="",
        browser_click_after_ready_delay_ms=0,
        browser_click_result_selector="",
        browser_click_result_text="",
        browser_click_timeout_sec=0,
        browser_post_interaction_wait_ms=0,
        browser_watch_text_selector="",
        browser_watch_text_regex="",
        browser_watch_text_label="",
        browser_watch_text_timeout_sec=0,
        browser_start_delay_sec=0.0,
        duration_sec=0,
        interval_sec=0,
    )


def start_session_local_check(args: argparse.Namespace, browser_url: str, ready_text: str, out_dir: Path) -> Dict[str, Any]:
    check_dir = out_dir / "session-local-check"
    check_dir.mkdir(parents=True, exist_ok=True)
    if args.skip_session_local_check:
        return {"skipped": True, "ok": True, "outDir": str(check_dir)}
    probe_args = session_local_probe_args(args, browser_url, ready_text)
    probe = cp.start_browser_probe(probe_args, check_dir)
    return {"skipped": False, "args": probe_args, "probe": probe, "outDir": str(check_dir)}


def finish_session_local_check(check: Dict[str, Any]) -> Dict[str, Any]:
    if check.get("skipped"):
        return {"ok": True, "skipped": True, "reason": "session-local check skipped by argument"}
    check_dir = Path(str(check.get("outDir") or ""))
    probe_args = check.get("args")
    probe = check.get("probe")
    if not isinstance(probe_args, argparse.Namespace):
        return {"ok": False, "error": "session-local probe args missing", "outDir": str(check_dir)}
    probe_info = cp.finish_browser_probe(probe, probe_args, check_dir)
    summary_path = check_dir / "browser-summary.json"
    browser_summary = read_json(summary_path) if summary_path.exists() else {"ok": False, "missing": True}
    route_ready = (
        probe_info.get("exitCode") == 0
        and browser_summary.get("ok") is True
        and browser_summary.get("ready") is True
        and browser_summary.get("readyTextMatched") is True
    )
    return {
        "ok": bool(route_ready),
        "skipped": False,
        "routeReady": bool(route_ready),
        "probe": probe_info,
        "browserSummary": browser_summary,
        "outDir": str(check_dir),
    }


def annotate_session_local_overlap(session_local: Dict[str, Any], browser_summary: Dict[str, Any]) -> Dict[str, Any]:
    if session_local.get("skipped"):
        return session_local
    local_browser = session_local.get("browserSummary", {}) if isinstance(session_local.get("browserSummary"), dict) else {}
    clicked_at = browser_summary.get("clickedAtEpochMs")
    result_at = browser_summary.get("resultMatchedAtEpochMs")
    local_ready_at = local_browser.get("primaryReadyEpochMillis")
    overlap_ok = (
        isinstance(clicked_at, int)
        and isinstance(result_at, int)
        and isinstance(local_ready_at, int)
        and clicked_at <= local_ready_at <= result_at
    )
    session_local["activeWindowOverlap"] = {
        "ok": bool(overlap_ok),
        "originalClickedAtEpochMs": clicked_at,
        "originalResultMatchedAtEpochMs": result_at,
        "sessionLocalPrimaryReadyEpochMs": local_ready_at,
    }
    session_local["ok"] = bool(session_local.get("routeReady") and overlap_ok)
    return session_local


def active_freeze_capture_summary(
    click_signal: Dict[str, Any],
    browser_summary: Dict[str, Any],
    immediate_sample: Dict[str, Any],
    thread_dump: Dict[str, Any],
    session_local: Dict[str, Any],
) -> Dict[str, Any]:
    screenshot = browser_summary.get("activeWindowScreenshot", {}) if isinstance(browser_summary.get("activeWindowScreenshot"), dict) else {}
    sample_has_gateway_context = any(
        key in immediate_sample for key in ["metricsSnapshot", "gatewayPerformanceSnapshot", "perspectiveSessionsQuery"]
    )
    return {
        "ok": bool(click_signal.get("ok") is True and screenshot.get("ok") is True and sample_has_gateway_context),
        "browserClickedAtEpochMs": click_signal.get("clickedAtEpochMs"),
        "screenshot": screenshot,
        "immediateSampleCapturedAt": immediate_sample.get("capturedAt"),
        "immediateSampleHasGatewayContext": sample_has_gateway_context,
        "threadDumpOk": thread_dump.get("ok") is True,
        "sessionLocalOk": session_local.get("ok") is True,
        "activeWindowOverlap": session_local.get("activeWindowOverlap"),
    }


def summarize_metrics(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    snapshots = [sample.get("metricsSnapshot", {}) for sample in samples if isinstance(sample.get("metricsSnapshot"), dict)]
    if len(snapshots) < 2:
        return {"ok": False, "reason": "fewer than two metric snapshots"}
    return {
        "ok": True,
        "scriptDelta": metric_delta(snapshots[0], snapshots[-1], "scripts"),
        "propertyChangeDelta": metric_delta(snapshots[0], snapshots[-1], "property-changes"),
        "queueTaskDelta": metric_delta(snapshots[0], snapshots[-1], "queue-tasks"),
        "sampleCount": len(snapshots),
    }


def thread_dump_evidence_found(thread_dump: Dict[str, Any]) -> bool:
    if thread_dump.get("ok") is not True:
        return False
    if int(thread_dump.get("returnedCount") or 0) < 1:
        return False
    text = canonical_json(thread_dump).lower()
    return any(token in text for token in ["org.python", "perspective", "script"])


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    browser = summary.get("browserSummary", {}) if isinstance(summary.get("browserSummary"), dict) else {}
    metrics = summary.get("metricSummary", {}) if isinstance(summary.get("metricSummary"), dict) else {}
    thread = summary.get("threadDump", {}) if isinstance(summary.get("threadDump"), dict) else {}
    active_capture = summary.get("activeFreezeCapture", {}) if isinstance(summary.get("activeFreezeCapture"), dict) else {}
    session_local = summary.get("sessionLocalCheck", {}) if isinstance(summary.get("sessionLocalCheck"), dict) else {}
    overlap = session_local.get("activeWindowOverlap", {}) if isinstance(session_local.get("activeWindowOverlap"), dict) else {}
    screenshot = active_capture.get("screenshot", {}) if isinstance(active_capture.get("screenshot"), dict) else {}
    lines = [
        "# Long Script / Active Freeze Incident Fixture",
        "",
        f"Run ID: `{summary.get('runId')}`",
        f"Overall OK: `{str(summary.get('ok')).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        f"Target millis: `{summary.get('targetMillis')}`",
        f"Max millis: `{summary.get('maxMillis')}`",
        "",
        "## Evidence",
        "",
        f"- Browser result: `{str(browser.get('ok')).lower()}`; click-to-result `{browser.get('clickToResultElapsedMs')}` ms.",
        f"- Active-window screenshot: `{str(screenshot.get('ok')).lower()}` at `{screenshot.get('atEpochMs')}`; file `{screenshot.get('file')}`.",
        f"- Immediate active sample: `{str(active_capture.get('immediateSampleHasGatewayContext')).lower()}` at `{active_capture.get('immediateSampleCapturedAt')}`.",
        f"- Metric summary: scripts `{metrics.get('scriptDelta')}`, property changes `{metrics.get('propertyChangeDelta')}`, queue tasks `{metrics.get('queueTaskDelta')}`.",
        f"- Thread dump: ok `{str(thread.get('ok')).lower()}`, returned `{thread.get('returnedCount')}` matching threads, relevant `{str(summary.get('threadDumpEvidenceFound')).lower()}`.",
        f"- Same-route second context: `{str(session_local.get('ok')).lower()}`; route ready `{str(session_local.get('routeReady')).lower()}`, active-window overlap `{str(overlap.get('ok')).lower()}`.",
        f"- Log markers found: `{str(summary.get('logMarkersFound')).lower()}`.",
        f"- Route/view cleanup: `{str(summary.get('cleanupOk')).lower()}`.",
        "",
        "## Interpretation",
        "",
        "- This is I-03 long-running script and I-01 active-freeze capture mechanics evidence, not a customer freeze conclusion.",
        "- Thread evidence is useful only because it was captured during the click/result window; late thread dumps must be labeled lower confidence.",
        "- The same-route second-context check helps distinguish a session-local stall from a route-wide outage for this fixture only.",
        "- The fixture writes only its disposable Perspective route/view resources and view custom properties, then rolls back route/view resources.",
        "",
    ]
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.overwrite:
        safe_rmtree(out_dir, Path.cwd(), SCRIPT_DIR.parent, out_dir.parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api" / "raw", args.timeout_sec)
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    features = feature_set_from_health(health)
    run_slug = common.compact(args.run_id)[:32].strip("-_") or "longscript"
    route = storm_common.build_route(args.route_prefix, run_slug, "long-script")
    view_path = f"{args.view_path_prefix.rstrip('/')}/{run_slug}/LongScriptIncident"
    package = build_package(out_dir, project, args, view_path, route)
    backup_name = ""
    gates: Dict[str, bool] = {"health": cp.ok(health)}
    gate_details: Dict[str, Any] = {"health": {"ok": cp.ok(health), "status": health.get("httpStatus")}}
    browser_proc: Optional[subprocess.Popen] = None
    session_local_check: Dict[str, Any] = {"ok": False, "missing": True, "reason": "not started"}
    session_local_probe: Optional[Dict[str, Any]] = None
    try:
        dry = client.call(f"{args.run_id}-dryRun", package_payload("dryRun", f"{args.run_id}-dryRun", project, package, args), timeout=args.timeout_sec)
        gates["dryRun"] = cp.ok(dry)
        gate_details["dryRun"] = {"ok": cp.ok(dry), "status": dry.get("httpStatus")}
        if not gates["dryRun"]:
            raise RuntimeError("dryRun failed")
        apply = client.call(f"{args.run_id}-apply", package_payload("apply", f"{args.run_id}-apply", project, package, args), timeout=args.timeout_sec)
        backup_name = common.backup_name_from_response(cp.response(apply))
        gates["apply"] = cp.ok(apply) and bool(backup_name)
        gate_details["apply"] = {"ok": cp.ok(apply), "status": apply.get("httpStatus"), "backupName": backup_name}
        if not gates["apply"]:
            raise RuntimeError("apply failed")
        time.sleep(args.post_apply_wait_sec)
        view_read = client.call(f"{args.run_id}-viewRead", view_read_payload(f"{args.run_id}-viewRead", project, view_path, args), timeout=args.timeout_sec)
        gates["viewRead"] = readback_ok(view_read, package, args)
        gate_details["viewRead"] = {"ok": cp.ok(view_read), "readbackOk": gates["viewRead"]}
        page = client.call(f"{args.run_id}-pageValidate", page_validate_payload(f"{args.run_id}-pageValidate", project, package, args), timeout=args.timeout_sec)
        gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
        gate_details["pageValidate"] = {"ok": cp.ok(page), "routeMatchesExpectedView": cp.response(page).get("routeMatchesExpectedView")}

        metrics_list_record = client.call(
            f"{args.run_id}-metricsList",
            {
                "action": "metricsList",
                "requestId": f"{args.run_id}-metricsList",
                "nameContains": args.metric_name_contains,
                "maxResults": min(max(args.max_metrics * 3, args.max_metrics), 250),
            },
        )
        metrics_list = cp.response(metrics_list_record)
        write_json(out_dir / "metrics-list.json", metrics_list)
        tokens = cp.metric_tokens(metrics_list, min(args.max_metrics, 100))

        samples: List[Dict[str, Any]] = []
        samples.append(call_metric_sample(client, args.run_id, 0, project, tokens, features))
        browser_dir = out_dir / "browser"
        browser_dir.mkdir(parents=True, exist_ok=True)
        signal_file = out_dir / "click-signal.json"
        browser_url = common.browser_url_from_endpoint(endpoint, project, route)
        browser_proc = run_browser_probe(args, browser_url, package, browser_dir, signal_file)
        click_signal = wait_for_signal(signal_file, args.click_signal_timeout_sec)
        gates["browserClicked"] = click_signal.get("ok") is True
        gate_details["browserClicked"] = click_signal
        if gates["browserClicked"]:
            session_local_probe = start_session_local_check(args, browser_url, package["readyText"], out_dir)
        immediate_sample = call_metric_sample(client, args.run_id, 1, project, tokens, features)
        samples.append(immediate_sample)
        if args.thread_capture_delay_sec > 0:
            time.sleep(args.thread_capture_delay_sec)
        thread_dump: Dict[str, Any] = {"ok": False, "missing": True, "reason": "threadDumpQuery feature not present"}
        if "threadDumpQuery" in features:
            thread_record = client.call(f"{args.run_id}-threadDumpQuery", thread_dump_payload(f"{args.run_id}-threadDumpQuery", args), timeout=args.timeout_sec)
            thread_dump = cp.response(thread_record)
        write_json(out_dir / "thread-excerpts.json", thread_dump)
        if session_local_probe is not None:
            session_local_check = finish_session_local_check(session_local_probe)
            session_local_probe = None
        for index in range(2, args.active_samples + 1):
            samples.append(call_metric_sample(client, args.run_id, index, project, tokens, features))
            if index < args.active_samples:
                time.sleep(args.active_sample_interval_sec)
        try:
            browser_code = browser_proc.wait(timeout=args.browser_result_timeout_sec + 10)
        except subprocess.TimeoutExpired:
            browser_proc.kill()
            browser_code = -1
        gates["browserProbe"] = browser_code == 0
        samples.append(call_metric_sample(client, args.run_id, args.active_samples + 1, project, tokens, features))
        write_json(out_dir / "incident-samples.json", samples)
        metric_summary = summarize_metrics(samples)
        browser_summary = read_json(browser_dir / "browser-long-script-summary.json") if (browser_dir / "browser-long-script-summary.json").exists() else {"ok": False, "missing": True}
        if session_local_probe is not None:
            session_local_check = finish_session_local_check(session_local_probe)
            session_local_probe = None
        session_local_check = annotate_session_local_overlap(session_local_check, browser_summary)
        active_capture = active_freeze_capture_summary(click_signal, browser_summary, immediate_sample, thread_dump, session_local_check)
        log_record = client.call(
            f"{args.run_id}-logQuery",
            {
                "action": "logQuery",
                "requestId": f"{args.run_id}-logQuery",
                "sinceMinutes": 10,
                "levels": ["INFO", "WARN", "ERROR"],
                "textContains": args.run_id,
                "maxResults": 50,
                "tailBytes": 2097152,
            },
        )
        logs = cp.response(log_record)
        write_json(out_dir / "logs.json", logs)
        log_text = canonical_json(logs)
        log_markers_found = args.run_id in log_text and "bounded long script START" in log_text and "bounded long script DONE" in log_text
        thread_evidence = thread_dump_evidence_found(thread_dump)
        gates["metrics"] = metric_summary.get("ok") is True
        gates["threadDump"] = thread_evidence
        gates["activeFreezeCapture"] = active_capture.get("ok") is True
        gates["sessionLocalCheck"] = session_local_check.get("ok") is True
        gate_details["activeFreezeCapture"] = active_capture
        gate_details["sessionLocalCheck"] = {
            "ok": session_local_check.get("ok"),
            "routeReady": session_local_check.get("routeReady"),
            "activeWindowOverlap": session_local_check.get("activeWindowOverlap"),
        }
        gates["logMarkers"] = log_markers_found
        gates["browserResult"] = browser_summary.get("ok") is True and browser_summary.get("resultTextMatched") is True
        row = {
            "runId": args.run_id,
            "createdAt": utc_now(),
            "project": project,
            "gatewayAlias": args.gateway_alias,
            "runnerVersion": cp.response(health).get("runnerVersion"),
            "stackVersion": cp.response(health).get("stackVersion"),
            "features": sorted(features),
            "route": route,
            "viewPath": view_path,
            "targetMillis": args.target_millis,
            "maxMillis": args.max_millis,
            "package": {key: value for key, value in package.items() if key != "packageBase64"},
            "gates": gates,
            "gateDetails": gate_details,
            "clickSignal": click_signal,
            "browserSummary": browser_summary,
            "activeFreezeCapture": active_capture,
            "sessionLocalCheck": session_local_check,
            "metricSummary": metric_summary,
            "threadDump": thread_dump,
            "threadDumpEvidenceFound": thread_evidence,
            "logMarkersFound": log_markers_found,
            "ok": False,
        }
    except Exception as exc:
        row = {
            "runId": args.run_id,
            "createdAt": utc_now(),
            "project": project,
            "gatewayAlias": args.gateway_alias,
            "runnerVersion": cp.response(health).get("runnerVersion"),
            "stackVersion": cp.response(health).get("stackVersion"),
            "route": route,
            "viewPath": view_path,
            "targetMillis": args.target_millis,
            "maxMillis": args.max_millis,
            "gates": gates,
            "gateDetails": gate_details,
            "sessionLocalCheck": session_local_check,
            "error": repr(exc),
            "ok": False,
        }
    finally:
        if session_local_probe is not None:
            try:
                session_local_check = finish_session_local_check(session_local_probe)
                row["sessionLocalCheck"] = session_local_check
            except Exception as exc:
                row["sessionLocalCheck"] = {"ok": False, "error": repr(exc)}
            session_local_probe = None
        if browser_proc is not None and browser_proc.poll() is None:
            try:
                browser_proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                browser_proc.kill()
                try:
                    browser_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        cleanup_ok = False
        if backup_name:
            rb_dry = client.call(f"{args.run_id}-rollback-dryRun", rollback_payload(f"{args.run_id}-rollback-dryRun", project, backup_name, view_path, True), timeout=args.timeout_sec)
            rb_apply = client.call(f"{args.run_id}-rollback-apply", rollback_payload(f"{args.run_id}-rollback-apply", project, backup_name, view_path, False), timeout=args.timeout_sec)
            time.sleep(args.post_apply_wait_sec)
            routes_check = client.call(
                f"{args.run_id}-post-cleanup-routesList",
                {"action": "routesList", "requestId": f"{args.run_id}-post-cleanup-routesList", "targetProject": project, "routePrefix": route, "maxResults": 25},
            )
            routes = cp.response(routes_check).get("routes", [])
            routes_list = routes if isinstance(routes, list) else []
            route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes_list)
            after_read = client.call(f"{args.run_id}-post-cleanup-viewRead", view_read_payload(f"{args.run_id}-post-cleanup-viewRead", project, view_path, args))
            cleanup_ok = cp.ok(rb_dry) and cp.ok(rb_apply) and cp.ok(routes_check) and not route_still_present and not cp.ok(after_read)
            row["rollback"] = {"dryRunOk": cp.ok(rb_dry), "applyOk": cp.ok(rb_apply), "routeAbsent": not route_still_present, "viewAbsent": not cp.ok(after_read)}
        row["cleanupOk"] = cleanup_ok
        row["ok"] = bool(row.get("ok") or (all(row.get("gates", {}).values()) and cleanup_ok))
        write_json(out_dir / "summary.json", row)
        write_report(out_dir, row)
    return row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--target-millis", type=int, default=5000)
    parser.add_argument("--max-millis", type=int, default=7000)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--timeout-sec", type=int, default=90)
    parser.add_argument("--post-apply-wait-sec", type=float, default=2.0)
    parser.add_argument("--metric-name-contains", action="append", default=["Perspective", "perspective", "script", "Script", "queue", "Queue"])
    parser.add_argument("--max-metrics", type=int, default=80)
    parser.add_argument("--active-samples", type=int, default=3)
    parser.add_argument("--active-sample-interval-sec", type=float, default=1.0)
    parser.add_argument("--thread-capture-delay-sec", type=float, default=0.5)
    parser.add_argument("--thread-name-contains", action="append", default=["Perspective", "perspective", "script", "Script", "WebSocket"])
    parser.add_argument("--stack-contains", action="append", default=["org.python", "com.inductiveautomation.perspective"])
    parser.add_argument("--max-threads", type=int, default=16)
    parser.add_argument("--max-frames-per-thread", type=int, default=24)
    parser.add_argument("--browser-node", default="node")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-result-timeout-sec", type=float, default=45.0)
    parser.add_argument("--browser-wait-after-result-ms", type=int, default=1000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--click-signal-timeout-sec", type=float, default=60.0)
    parser.add_argument("--session-local-timeout-sec", type=float, default=25.0)
    parser.add_argument("--session-local-wait-after-ready-ms", type=int, default=250)
    parser.add_argument("--skip-session-local-check", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.target_millis < 1:
        raise SystemExit("--target-millis must be >= 1")
    if args.max_millis < args.target_millis:
        raise SystemExit("--max-millis must be >= --target-millis")
    if args.active_samples < 1:
        raise SystemExit("--active-samples must be >= 1")
    if args.session_local_timeout_sec <= 0:
        raise SystemExit("--session-local-timeout-sec must be > 0")
    if args.session_local_wait_after_ready_ms < 0:
        raise SystemExit("--session-local-wait-after-ready-ms must be >= 0")
    summary = run(args)
    print(json.dumps({"ok": summary.get("ok"), "summary": str(Path(args.out_dir) / "summary.json")}, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
