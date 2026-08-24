#!/usr/bin/env python3
"""Run guarded Perspective Embedded View breadth scaling fixtures."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import collect_profile as cp
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug(value: str) -> str:
    return cp.slug(value).lower()


def compact(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value) or "EmbeddedBreadth"


def write_json(path: Path, data: Any) -> None:
    cp.write_json(path, data)


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def zip_file_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def browser_url_from_endpoint(endpoint: str, project: str, route: str) -> str:
    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        return ""
    normalized_route = "/" + route.strip("/")
    return f"{parsed.scheme}://{parsed.netloc}/data/perspective/client/{project}{normalized_route}"


def build_route(prefix: str, run_slug: str, count: int) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-breadth-{count:03d}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def backup_name_from_response(data: Dict[str, Any]) -> str:
    raw = str(data.get("backupDir", "") or data.get("backupName", "")).strip()
    if not raw:
        return ""
    return re.split(r"[\\/]+", raw.rstrip("\\/"))[-1]


def component(component_type: str, *, meta: Optional[Dict[str, Any]] = None, props: Optional[Dict[str, Any]] = None, position: Optional[Dict[str, Any]] = None, children: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {"type": component_type}
    if meta is not None:
        row["meta"] = meta
    if position is not None:
        row["position"] = position
    if props is not None:
        row["props"] = props
    if children is not None:
        row["children"] = children
    return row


def make_child_view(run_id: str) -> Dict[str, Any]:
    labels = []
    for index in range(1, 7):
        labels.append(
            component(
                "ia.display.label",
                meta={"name": f"Child Label {index}"},
                position={"basis": "18px", "grow": 0, "shrink": 0},
                props={
                    "text": f"{run_id} embedded child payload {index}",
                    "style": {
                        "color": "#1f2937",
                        "fontSize": 11,
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                    },
                },
            )
        )
    return {
        "custom": {"runId": run_id, "role": "embedded-child"},
        "params": {"index": 0, "runId": ""},
        "propConfig": {},
        "props": {"defaultSize": {"width": 220, "height": 112}},
        "root": component(
            "ia.container.flex",
            meta={"name": "child-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "style": {
                    "backgroundColor": "#ffffff",
                    "borderColor": "#cbd5e1",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "overflow": "hidden",
                    "padding": "6px",
                },
            },
            children=labels,
        ),
        "permissions": {},
    }


def make_parent_view(run_id: str, count: int, child_view_path: str) -> Dict[str, Any]:
    ready = f"{run_id} BREADTH {count} READY"
    children: List[Dict[str, Any]] = [
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
                    "whiteSpace": "pre-wrap",
                },
            },
        ),
        component(
            "ia.display.label",
            meta={"name": "Scenario Summary"},
            position={"basis": "34px", "grow": 0, "shrink": 0},
            props={
                "text": f"Embedded View breadth variant: {count} instances of {child_view_path}",
                "style": {"color": "#1f2937", "fontSize": 13, "padding": "7px 2px", "whiteSpace": "pre-wrap"},
            },
        ),
    ]
    embedded_children = []
    for index in range(count):
        embedded_children.append(
            component(
                "ia.display.view",
                meta={"name": f"Embedded {index + 1:03d}"},
                position={"basis": "112px", "grow": 0, "shrink": 0},
                props={
                    "path": child_view_path,
                    "params": {
                        "index": index + 1,
                        "runId": run_id,
                        "payload": {
                            "slot": index + 1,
                            "label": f"embedded-slot-{index + 1:03d}",
                            "values": [index, index + 1, index + 2],
                        },
                    },
                    "style": {"margin": "3px"},
                },
            )
        )
    children.append(
        component(
            "ia.container.flex",
            meta={"name": "Embedded Grid"},
            position={"basis": "auto", "grow": 1, "shrink": 1},
            props={
                "direction": "row",
                "alignItems": "flex-start",
                "justify": "flex-start",
                "wrap": "wrap",
                "style": {"overflow": "auto", "padding": "4px"},
            },
            children=embedded_children,
        )
    )
    return {
        "custom": {
            "runId": run_id,
            "variant": f"breadth-{count}",
            "embeddedCount": count,
            "childViewPath": child_view_path,
            "childViewSha256": sha256_text(canonical_json(make_child_view(run_id))),
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {
                    "backgroundColor": "#f8fafc",
                    "overflow": "hidden",
                    "padding": "12px",
                },
            },
            children=children,
        ),
        "permissions": {},
    }


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", fixture_common.resource_json(actor, ["view.json"]))


def make_zip(root: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())


def build_package(out_dir: Path, project: str, run_id: str, count: int, parent_view_path: str, child_view_path: str, route: str) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / f"breadth-{count:03d}"
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    parent_view = make_parent_view(run_id, count, child_view_path)
    child_view = make_child_view(run_id)
    zip_path = zip_dir / f"{slug(run_id)}-breadth-{count:03d}.zip"
    actor = "perf-profiler-embedded-breadth"
    with tempfile.TemporaryDirectory(prefix="perfprof-embed-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler embedded breadth fixture", "enabled": True, "inheritable": False})
        write_view(project_root, child_view_path, child_view, actor)
        write_view(project_root, parent_view_path, parent_view, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Embedded Breadth {count}", "viewPath": parent_view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        make_zip(package_root, zip_path)
    return {
        "count": count,
        "parentViewPath": parent_view_path,
        "childViewPath": child_view_path,
        "route": route,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": zip_file_base64(zip_path),
        "parentViewSha256": sha256_text(canonical_json(parent_view)),
        "childViewSha256": sha256_text(canonical_json(child_view)),
        "readyText": f"{run_id} BREADTH {count} READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["parentViewPath"], "title": f"Embedded Breadth {package['count']}"}],
        "dependencyViewPaths": [package["childViewPath"]],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [],
        "allowUnsafeNamedQueryParameters": False,
        "unsafeNamedQueryParameterPaths": [],
        "sharedDockKeys": [],
        "allowOverwrite": False,
    }
    if action == "apply":
        payload["confirmApply"] = "APPLY"
    return payload


def page_validate_payload(request_id: str, project: str, package: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "action": "pageValidate",
        "requestId": request_id,
        "targetProject": project,
        "pagePath": package["route"],
        "expectedViewPath": package["parentViewPath"],
        "allowedViewPrefix": args.allowed_view_prefix,
        "allowedRoutePrefix": args.allowed_route_prefix,
        "dependencyViewPaths": [package["childViewPath"]],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [],
    }


def view_read_payload(request_id: str, project: str, view_path: str, args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "action": "viewRead",
        "requestId": request_id,
        "targetProject": project,
        "viewPath": view_path,
        "allowedViewPrefix": args.allowed_view_prefix,
        "includeViewJson": True,
        "includeResourceJson": True,
    }


def rollback_payload(request_id: str, project: str, backup_name: str, view_paths: List[str], dry_run: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "rollback",
        "requestId": request_id,
        "targetProject": project,
        "backupName": backup_name,
        "viewPaths": view_paths,
        "scriptPaths": [],
        "namedQueryPaths": [],
        "dryRun": dry_run,
        "removeMissingViews": True,
        "removeMissingScripts": False,
        "removeMissingNamedQueries": False,
    }
    if not dry_run:
        payload["confirmRollback"] = "ROLLBACK"
    return payload


def collect_env(endpoint: str, token: str, project: str) -> Dict[str, str]:
    env = dict(os.environ)
    env["IGNITION_LLM_RUNNER_ENDPOINT"] = endpoint
    env["IGNITION_LLM_RUNNER_TOKEN"] = token
    env["IGNITION_TARGET_PROJECT"] = project
    return env


def redact_command(cmd: List[str]) -> List[str]:
    redacted = list(cmd)
    for index, value in enumerate(redacted[:-1]):
        if value in ("--endpoint", "--token", "--browser-url"):
            redacted[index + 1] = "<redacted>"
        elif value == "--browser-node-modules":
            redacted[index + 1] = "<redacted-node-modules>"
    return redacted


def run_command(cmd: List[str], label: str, out_dir: Path, timeout_sec: int, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    log_dir = out_dir / "command-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{label}.stdout.txt"
    stderr_path = log_dir / f"{label}.stderr.txt"
    record: Dict[str, Any] = {
        "label": label,
        "startedAt": utc_now(),
        "command": redact_command(cmd),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
    }
    try:
        completed = subprocess.run(cmd, cwd=str(SCRIPT_DIR), capture_output=True, text=True, timeout=timeout_sec, env=env)
        stdout_path.write_text(completed.stdout or "", encoding="utf-8", newline="\n")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8", newline="\n")
        record.update({"ok": completed.returncode == 0, "returnCode": completed.returncode, "timedOut": False, "finishedAt": utc_now()})
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text((exc.stdout or "") if isinstance(exc.stdout, str) else "", encoding="utf-8", newline="\n")
        stderr_path.write_text((exc.stderr or "") if isinstance(exc.stderr, str) else "", encoding="utf-8", newline="\n")
        record.update({"ok": False, "returnCode": None, "timedOut": True, "finishedAt": utc_now()})
    return record


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        f"{args.run_id}-breadth-{package['count']:03d}",
        "--project",
        project,
        "--route",
        package["route"],
        "--view",
        package["parentViewPath"],
        "--duration-sec",
        str(args.profile_duration_sec),
        "--interval-sec",
        str(args.interval_sec),
        "--max-metrics",
        str(args.max_metrics),
        "--out-dir",
        str(profile_dir),
        "--gateway-alias",
        args.gateway_alias,
        "--scenario",
        "embedded view breadth scaling fixture",
        "--browser-url",
        browser_url,
        "--browser-url-alias",
        args.browser_url_alias,
        "--browser-ready-selector",
        args.browser_ready_selector,
        "--browser-ready-text",
        package["readyText"],
        "--browser-timeout-sec",
        str(args.browser_timeout_sec),
        "--browser-wait-after-ready-ms",
        str(args.browser_wait_after_ready_ms),
        "--browser-viewport",
        args.browser_viewport,
    ]
    if args.browser_node_modules:
        command.extend(["--browser-node-modules", args.browser_node_modules])
    return command


def profile_ok(profile_dir: Path) -> bool:
    manifest = read_json(profile_dir / "manifest.json")
    browser = read_json(profile_dir / "browser-summary.json")
    return bool(
        manifest.get("changedResources") == []
        and not manifest.get("missingEvidence")
        and browser.get("ok") is True
        and browser.get("ready") is True
        and browser.get("readyTextMatched") is True
    )


def feature_set_from_health(health: Dict[str, Any]) -> set[str]:
    features = cp.response(health).get("features", [])
    if isinstance(features, dict):
        return {str(key) for key, value in features.items() if value}
    if isinstance(features, list):
        return {str(item) for item in features}
    return set()


def to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
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
    count: int,
    feature_set: set[str],
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
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"count": count, "sampledAt": utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-breadth-{count:03d}-baselineWait-{attempt:03d}"
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
            "count": count,
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


def number(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def first_number(*values: Any) -> Optional[float]:
    for value in values:
        parsed = number(value)
        if parsed is not None:
            return parsed
    return None


def browser_metrics(profile_dir: Path) -> Dict[str, Any]:
    browser = read_json(profile_dir / "browser-summary.json")
    lcp = browser.get("largestContentfulPaint", {}) if isinstance(browser.get("largestContentfulPaint"), dict) else {}
    heap = browser.get("heap", {}) if isinstance(browser.get("heap"), dict) else {}
    return {
        "elapsedBrowserMs": browser.get("elapsedBrowserMs"),
        "largestContentfulPaintMs": lcp.get("startTime"),
        "longTaskTotalMs": browser.get("longTaskTotalMs"),
        "longTaskCount": browser.get("longTaskCount"),
        "domNodeCount": browser.get("domNodeCount"),
        "resourceTransferSize": browser.get("resourceTransferSize"),
        "usedJSHeapBytes": heap.get("usedJSHeapSize"),
    }


def gateway_metrics(profile_dir: Path) -> Dict[str, Any]:
    samples_path = profile_dir / "gateway-samples.ndjson"
    heap_values: List[float] = []
    cpu_values: List[float] = []
    thread_values: List[float] = []
    if samples_path.exists():
        for line in samples_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            perf = row.get("gatewayPerformanceSnapshot", {})
            data = perf.get("response", perf) if isinstance(perf, dict) else {}
            heap_data = data.get("heap", {}) if isinstance(data.get("heap"), dict) else {}
            cpu_data = data.get("cpu", {}) if isinstance(data.get("cpu"), dict) else {}
            thread_data = data.get("threads", {}) if isinstance(data.get("threads"), dict) else {}
            heap = first_number(data.get("heapUsedBytes"), heap_data.get("usedBytes"))
            cpu = first_number(data.get("processCpuLoad"), cpu_data.get("processCpuLoad"))
            threads = first_number(data.get("threadCount"), thread_data.get("total"))
            if heap is not None:
                heap_values.append(heap)
            if cpu is not None:
                cpu_values.append(cpu)
            if threads is not None:
                thread_values.append(threads)
    return {
        "heapUsedBytesMedian": median(heap_values) if heap_values else None,
        "processCpuLoadMedian": median(cpu_values) if cpu_values else None,
        "threadCountMedian": median(thread_values) if thread_values else None,
    }


def static_metrics(profile_dir: Path) -> Dict[str, Any]:
    static = read_json(profile_dir / "static-profile.json")
    summary = static.get("summary", {}) if isinstance(static.get("summary"), dict) else {}
    return {
        "componentCount": summary.get("componentCount"),
        "embeddedViewCount": summary.get("embeddedViewCount"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
    }


def compare_to_baseline(out_dir: Path, baseline_dir: Path, profile_dir: Path, count: int) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparisons" / f"count-{count:03d}-minus-baseline"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(baseline_dir), "--target-dir", str(profile_dir), "--out-dir", str(comparison_dir)]
    result = run_command(cmd, f"compare-count-{count:03d}", out_dir, 180)
    return {"count": count, "ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Embedded View Breadth Scaling Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Scenario: `{summary.get('scenario', 'embedded view breadth scaling fixture')}`",
        f"Evidence grade: `{summary.get('evidenceGrade', 'Observed')}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Counts: `{','.join(str(item) for item in summary.get('counts', []))}`",
        f"Runner version: `{summary.get('runnerVersion')}`",
        f"Stack version: `{summary.get('stackVersion')}`",
        "",
        "## Direct Observations",
        "",
        "- Each count variant is applied with dry-run/apply, read back, browser-profiled, compared to the one-instance baseline when applicable, and rolled back before the next variant.",
        "- Static Embedded View counts, browser DOM/heap/timing metrics, Gateway CPU samples, route cleanup, and view cleanup are recorded per variant.",
        "",
        "## Variant Summary",
        "",
        "| Count | Baseline | OK | Embedded | DOM | Long task ms | LCP ms | JS heap | CPU median | Route cleanup | View cleanup |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary.get("variants", []):
        browser = row.get("browser", {})
        gateway = row.get("gateway", {})
        static = row.get("static", {})
        baseline = row.get("baselineWait", {})
        if baseline.get("enabled"):
            baseline_text = "clean" if baseline.get("ok") else "timeout"
            baseline_text += f" ({baseline.get('finalBrowserSessions')})"
        else:
            baseline_text = "not requested"
        lines.append(
            "| {count} | {baseline} | `{ok}` | {embedded} | {dom} | {long_task} | {lcp} | {heap} | {cpu} | `{cleanup}` | `{view_cleanup}` |".format(
                count=row.get("count"),
                baseline=baseline_text,
                ok=str(row.get("ok", False)).lower(),
                embedded=static.get("embeddedViewCount"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                lcp=browser.get("largestContentfulPaintMs"),
                heap=browser.get("usedJSHeapBytes"),
                cpu=gateway.get("processCpuLoadMedian"),
                cleanup=str(row.get("cleanupRouteAbsent", False)).lower(),
                view_cleanup=str(row.get("cleanupViewsAbsent", False)).lower(),
            )
        )
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Unproven Limits",
            "",
            "- This fixture does not establish a universal Embedded View count limit.",
            "- Single-run deltas do not prove a customer remediation; repeat on the target route or customer-like fixture before recommending a threshold.",
            "- Browser and Gateway metrics are interpreted as observed fixture behavior unless repeated paired runs meet the declared causal policy.",
        ]
    )
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_manifest(out_dir: Path, summary: Dict[str, Any]) -> None:
    files = [
        "summary.json",
        "summary.md",
        "packages.json",
        "comparisons.json",
        "api/",
    ]
    if (out_dir / "comparisons").exists():
        files.append("comparisons/")
    for row in summary.get("variants", []):
        count = row.get("count")
        if count is not None:
            files.append(f"breadth-{int(count):03d}/")
    manifest = {
        "runId": summary.get("runId"),
        "scenario": summary.get("scenario", "embedded view breadth scaling fixture"),
        "evidenceGrade": summary.get("evidenceGrade", "Observed"),
        "createdAt": summary.get("createdAt"),
        "project": summary.get("project"),
        "gatewayAlias": summary.get("gatewayAlias"),
        "runnerVersion": summary.get("runnerVersion"),
        "stackVersion": summary.get("stackVersion"),
        "counts": summary.get("counts", []),
        "waitForCleanBaseline": summary.get("waitForCleanBaseline"),
        "baselineMaxBrowserSessions": summary.get("baselineMaxBrowserSessions"),
        "variantCount": len(summary.get("variants", [])),
        "comparisonCount": len(summary.get("comparisons", [])),
        "changedResources": [],
        "missingEvidence": [],
        "files": files,
    }
    write_json(out_dir / "manifest.json", manifest)


def parse_counts(raw: str) -> List[int]:
    counts = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value <= 0:
            raise ValueError("counts must be positive")
        counts.append(value)
    return sorted(dict.fromkeys(counts))


def run(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    env = collect_env(endpoint, token, project)
    counts = parse_counts(args.counts)
    base = compact(args.run_id)
    child_view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/EmbeddedChild"
    variants: List[Dict[str, Any]] = []
    compare_records: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_ok = cp.ok(health)
    feature_set = feature_set_from_health(health)

    for count in counts:
        variant_label = f"breadth-{count:03d}"
        variant_dir = out_dir / variant_label
        route = build_route(args.route_prefix, slug(args.run_id), count)
        parent_view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/Breadth{count:03d}"
        package = build_package(variant_dir, project, args.run_id, count, parent_view_path, child_view_path, route)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        gates: Dict[str, bool] = {}
        backup_name = ""
        baseline_wait: Dict[str, Any] = {"enabled": False}
        try:
            if args.wait_for_clean_baseline:
                baseline_wait = wait_for_clean_baseline(
                    client,
                    variant_dir,
                    args.run_id,
                    project,
                    count,
                    feature_set,
                    args.baseline_max_browser_sessions,
                    args.baseline_wait_timeout_sec,
                    args.baseline_wait_interval_sec,
                )
                write_json(variant_dir / "baseline-wait.json", baseline_wait)
                gates["cleanBaseline"] = bool(baseline_wait.get("ok"))
                if args.fail_on_baseline_timeout and not baseline_wait.get("ok"):
                    raise RuntimeError("clean baseline was not reached before timeout")
            dry = client.call(f"{args.run_id}-{variant_label}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant_label}-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry)
            if not gates["dryRun"]:
                raise RuntimeError("dryRun failed")
            apply = client.call(f"{args.run_id}-{variant_label}-apply", package_payload("apply", f"{args.run_id}-{variant_label}-apply", project, package, args), timeout=args.timeout_sec)
            backup_name = backup_name_from_response(cp.response(apply))
            gates["apply"] = cp.ok(apply) and bool(backup_name)
            if not gates["apply"]:
                raise RuntimeError("apply failed")
            time.sleep(2)
            parent_read = client.call(f"{args.run_id}-{variant_label}-parent-viewRead", view_read_payload(f"{args.run_id}-{variant_label}-parent-viewRead", project, parent_view_path, args))
            child_read = client.call(f"{args.run_id}-{variant_label}-child-viewRead", view_read_payload(f"{args.run_id}-{variant_label}-child-viewRead", project, child_view_path, args))
            gates["viewRead"] = cp.ok(parent_read) and cp.ok(child_read)
            page = client.call(f"{args.run_id}-{variant_label}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_label}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = browser_url_from_endpoint(endpoint, project, route)
            profile_dir = variant_dir / "profile"
            command = profile_command(args, package, project, browser_url, profile_dir)
            profile_result = run_command(command, f"profile-{variant_label}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            variant = {
                "count": count,
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "parentViewPath": parent_view_path,
                "childViewPath": child_view_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "profileDir": str(profile_dir),
                "browser": browser_metrics(profile_dir),
                "gateway": gateway_metrics(profile_dir),
                "static": static_metrics(profile_dir),
                "profileCommand": profile_result,
            }
            if counts and count != counts[0]:
                baseline_dir = out_dir / f"breadth-{counts[0]:03d}" / "profile"
                if baseline_dir.exists() and gates["profile"]:
                    compare_records.append(compare_to_baseline(out_dir, baseline_dir, profile_dir, count))
        except Exception as exc:
            variant = {
                "count": count,
                "ok": False,
                "gates": gates,
                "route": route,
                "parentViewPath": parent_view_path,
                "childViewPath": child_view_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                rb_dry = client.call(
                    f"{args.run_id}-{variant_label}-rollback-dryRun",
                    rollback_payload(f"{args.run_id}-{variant_label}-rollback-dryRun", project, backup_name, [parent_view_path, child_view_path], True),
                    timeout=args.timeout_sec,
                )
                rb_apply = client.call(
                    f"{args.run_id}-{variant_label}-rollback-apply",
                    rollback_payload(f"{args.run_id}-{variant_label}-rollback-apply", project, backup_name, [parent_view_path, child_view_path], False),
                    timeout=args.timeout_sec,
                )
                time.sleep(2)
                routes_check = client.call(
                    f"{args.run_id}-{variant_label}-post-cleanup-routesList",
                    {
                        "action": "routesList",
                        "requestId": f"{args.run_id}-{variant_label}-post-cleanup-routesList",
                        "targetProject": project,
                        "routePrefix": route,
                        "maxResults": 25,
                    },
                )
                routes = cp.response(routes_check).get("routes", [])
                route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes if isinstance(routes, list))
                parent_after = client.call(
                    f"{args.run_id}-{variant_label}-post-cleanup-parent-viewRead",
                    view_read_payload(f"{args.run_id}-{variant_label}-post-cleanup-parent-viewRead", project, parent_view_path, args),
                )
                child_after = client.call(
                    f"{args.run_id}-{variant_label}-post-cleanup-child-viewRead",
                    view_read_payload(f"{args.run_id}-{variant_label}-post-cleanup-child-viewRead", project, child_view_path, args),
                )
                variant["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                variant["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                variant["cleanupViewsAbsent"] = not cp.ok(parent_after) and not cp.ok(child_after)
                variant["ok"] = bool(variant.get("ok") and variant["rollbackOk"] and variant["cleanupRouteAbsent"] and variant["cleanupViewsAbsent"])
            variants.append(variant)
            if args.pause_sec > 0 and count != counts[-1]:
                time.sleep(args.pause_sec)

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "scenario": "embedded view breadth scaling fixture",
        "evidenceGrade": "Observed",
        "counts": counts,
        "healthOk": health_ok,
        "features": sorted(feature_set),
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "baselineWaitIntervalSeconds": args.baseline_wait_interval_sec if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparisons": compare_records,
        "packages": package_records,
        "interpretation": [
            "This is a controlled Embedded View breadth scaling fixture, not a customer route conclusion.",
            "Rising DOM, long-task, heap, or Gateway/session metrics across counts indicates scaling behavior to investigate; it is not a universal platform limit.",
            "Each variant is applied through dry-run/apply, profiled, and rolled back before the next variant.",
            "Use --wait-for-clean-baseline to reduce retained browser-session contamination between count variants.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "packages.json", package_records)
    write_json(out_dir / "comparisons.json", compare_records)
    write_report(out_dir, summary)
    write_manifest(out_dir, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--counts", default="1,10,50,100")
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=8.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=240)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=5000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--pause-sec", type=float, default=2.0)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each count variant, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline per count.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Mark the variant failed before import when the requested clean baseline is not reached.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0:
        raise SystemExit("--baseline-wait-timeout-sec must be >= 0")
    if args.baseline_wait_interval_sec < 0:
        raise SystemExit("--baseline-wait-interval-sec must be >= 0")
    summary = run(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
