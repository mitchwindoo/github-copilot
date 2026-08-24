#!/usr/bin/env python3
"""Run a guarded I-04 repeated memory-growth suspicion fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_table_ab_remediation as table_common


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"


def utc_now() -> str:
    return common.utc_now()


def canonical_json(data: Any) -> str:
    return common.canonical_json(data)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(value: str) -> str:
    return cp.slug(value).lower()


def compact(value: str) -> str:
    return common.compact(value)


def write_json(path: Path, data: Any) -> None:
    cp.write_json(path, data)


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def append_ndjson(path: Path, row: Dict[str, Any]) -> None:
    cp.append_ndjson(path, row)


def number(value: Any) -> Optional[float]:
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


def component(
    component_type: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    props: Optional[Dict[str, Any]] = None,
    position: Optional[Dict[str, Any]] = None,
    children: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {"type": component_type}
    if meta is not None:
        row["meta"] = meta
    if props is not None:
        row["props"] = props
    if position is not None:
        row["position"] = position
    if children is not None:
        row["children"] = children
    return row


def build_route(prefix: str, run_slug: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-memory-growth"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def make_view_json(args: argparse.Namespace, ready_text: str) -> Dict[str, Any]:
    rows = table_common.make_rows(args.rows, args.columns)
    columns = table_common.make_columns(args.columns)
    return {
        "custom": {
            "runId": args.run_id,
            "incidentCase": "I-04 memory-growth suspicion mechanics",
            "rowCount": args.rows,
            "columnCount": args.columns,
            "cycleCount": args.cycles,
            "dataSha256": sha256_text(canonical_json(rows)),
            "columnSha256": sha256_text(canonical_json(columns)),
            "expectedReadyText": ready_text,
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "memory-growth-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {"backgroundColor": "#f8fafc", "overflow": "hidden", "padding": "12px"},
            },
            children=[
                component(
                    "ia.display.label",
                    meta={"name": "Ready Marker"},
                    position={"basis": "40px", "grow": 0, "shrink": 0},
                    props={
                        "text": ready_text,
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
                    position={"basis": "36px", "grow": 0, "shrink": 0},
                    props={
                        "text": f"I-04 memory-growth fixture: {args.cycles} open/close cycles, table {args.rows} x {args.columns}",
                        "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
                    },
                ),
                component(
                    "ia.display.table",
                    meta={"name": "Lifecycle Table"},
                    position={"basis": "auto", "grow": 1, "shrink": 1},
                    props={
                        "data": rows,
                        "columns": columns,
                        "virtualized": args.virtualized,
                        "selection": {"enableRowSelection": True, "mode": "single"},
                        "style": {
                            "backgroundColor": "#ffffff",
                            "borderColor": "#cbd5e1",
                            "borderRadius": 4,
                            "borderStyle": "solid",
                            "borderWidth": "1px",
                        },
                    },
                ),
            ],
        ),
        "permissions": {},
    }


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", table_common.resource_json(actor, ["view.json"]))


def build_package(out_dir: Path, project: str, args: argparse.Namespace, view_path: str, route: str) -> Dict[str, Any]:
    zip_dir = out_dir / "packages"
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-memory-growth"
    ready_text = f"{args.run_id} I-04 MEMORY READY"
    view_json = make_view_json(args, ready_text)
    zip_path = zip_dir / f"{slug(args.run_id)}-memory-growth.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-memory-growth-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler memory-growth fixture", "enabled": True, "inheritable": False})
        write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": "Memory Growth Fixture", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", table_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "route": route,
        "viewPath": view_path,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": ready_text,
        "rowCount": args.rows,
        "columnCount": args.columns,
        "virtualized": args.virtualized,
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": "Memory Growth Fixture"}],
        "dependencyViewPaths": [],
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
        "expectedViewPath": package["viewPath"],
        "allowedViewPrefix": args.allowed_view_prefix,
        "allowedRoutePrefix": args.allowed_route_prefix,
        "dependencyViewPaths": [],
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


def rollback_payload(request_id: str, project: str, backup_name: str, view_path: str, dry_run: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "rollback",
        "requestId": request_id,
        "targetProject": project,
        "backupName": backup_name,
        "viewPaths": [view_path],
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


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    data = cp.response(record)
    if not cp.ok(record):
        return False
    view = data.get("view") if isinstance(data.get("view"), dict) else {}
    custom = view.get("custom") if isinstance(view.get("custom"), dict) else {}
    if not custom and isinstance(data.get("custom"), dict):
        custom = data["custom"]
    if custom.get("incidentCase") != "I-04 memory-growth suspicion mechanics":
        return False
    return (
        custom.get("expectedReadyText") == package.get("readyText")
        and custom.get("rowCount") == package.get("rowCount")
        and custom.get("columnCount") == package.get("columnCount")
    )


def metric_tokens_from_health(client: cp.RunnerClient, run_id: str, max_metrics: int, feature_set: set) -> List[str]:
    if "metricsList" not in feature_set:
        return []
    record = client.call(
        f"{run_id}-metricsList-memory",
        {
            "action": "metricsList",
            "requestId": f"{run_id}-metricsList-memory",
            "nameContains": ["Perspective", "perspective", "memory", "Memory", "heap", "Heap", "gc", "GC", "Garbage"],
            "maxResults": min(max(max_metrics * 3, max_metrics), 250),
        },
    )
    return cp.metric_tokens(cp.response(record), max(0, min(max_metrics, 100)))


def browser_inventory(row: Dict[str, Any]) -> Dict[str, Any]:
    query = row.get("perspectiveSessionsQuery", {})
    browser_count = 0
    page_count = 0
    recent_bytes: List[float] = []
    session_tokens: List[str] = []
    page_tokens: List[str] = []
    sessions = query.get("sessions", []) if isinstance(query, dict) else []
    if not isinstance(sessions, list):
        return {
            "sessionCount": browser_count,
            "pageCount": page_count,
            "recentBytes": recent_bytes,
            "sessionTokens": session_tokens,
            "pageTokens": page_tokens,
        }
    for session in sessions:
        if not isinstance(session, dict):
            continue
        if str(session.get("sessionScope", "")).lower() != "browser":
            continue
        browser_count += 1
        page_count += int(number(session.get("activePages")) or 0)
        token = str(session.get("sessionToken", "")).strip()
        if token:
            session_tokens.append(token)
        raw_page_tokens = session.get("pageTokens", [])
        if isinstance(raw_page_tokens, list):
            page_tokens.extend(str(item).strip() for item in raw_page_tokens if str(item).strip())
        recent = number(session.get("recentBytesSent"))
        if recent is not None:
            recent_bytes.append(recent)
    return {
        "sessionCount": browser_count,
        "pageCount": page_count,
        "recentBytes": recent_bytes,
        "sessionTokens": sorted(set(session_tokens)),
        "pageTokens": sorted(set(page_tokens)),
    }


def sample_once(client: cp.RunnerClient, args: argparse.Namespace, project: str, cycle: int, phase: str, sample_index: int, tokens: List[str], feature_set: set) -> Dict[str, Any]:
    sample_id = f"{args.run_id}-c{cycle:02d}-{phase}-{sample_index:03d}"
    row: Dict[str, Any] = {"cycle": cycle, "phase": phase, "sampleIndex": sample_index, "sampledAt": utc_now()}
    if tokens and "metricsSnapshot" in feature_set:
        record = client.call(
            f"{sample_id}-metricsSnapshot",
            {"action": "metricsSnapshot", "requestId": f"{sample_id}-metricsSnapshot", "metricTokens": tokens, "maxMetrics": len(tokens)},
        )
        row["metricsSnapshot"] = cp.response(record)
    else:
        row["metricsSnapshot"] = {"ok": False, "missing": True, "reason": "metricsSnapshot unavailable or no metric tokens selected"}
    if "gatewayPerformanceSnapshot" in feature_set:
        record = client.call(f"{sample_id}-gatewayPerformanceSnapshot", {"action": "gatewayPerformanceSnapshot", "requestId": f"{sample_id}-gatewayPerformanceSnapshot"})
        row["gatewayPerformanceSnapshot"] = cp.response(record)
    else:
        row["gatewayPerformanceSnapshot"] = {"ok": False, "missing": True, "reason": "gatewayPerformanceSnapshot feature not present"}
    if "perspectiveSessionsQuery" in feature_set:
        record = client.call(
            f"{sample_id}-perspectiveSessionsQuery",
            {"action": "perspectiveSessionsQuery", "requestId": f"{sample_id}-perspectiveSessionsQuery", "targetProject": project, "maxResults": 100},
        )
        row["perspectiveSessionsQuery"] = cp.response(record)
    else:
        row["perspectiveSessionsQuery"] = {"ok": False, "missing": True, "reason": "perspectiveSessionsQuery feature not present"}
    inventory = browser_inventory(row)
    row["browserSessionCount"] = inventory["sessionCount"]
    row["browserPageCount"] = inventory["pageCount"]
    row["browserSessionTokens"] = inventory["sessionTokens"]
    row["browserPageTokens"] = inventory["pageTokens"]
    row["browserSessionTokenCount"] = len(inventory["sessionTokens"])
    row["browserPageTokenCount"] = len(inventory["pageTokens"])
    recent_bytes = inventory["recentBytes"]
    row["browserRecentBytesSentMax"] = max(recent_bytes) if recent_bytes else None
    return row


def sample_phase(client: cp.RunnerClient, out_dir: Path, args: argparse.Namespace, project: str, cycle: int, phase: str, count: int, interval_sec: float, tokens: List[str], feature_set: set) -> List[Dict[str, Any]]:
    rows = []
    for index in range(count):
        row = sample_once(client, args, project, cycle, phase, index, tokens, feature_set)
        rows.append(row)
        append_ndjson(out_dir / "memory-growth-samples.ndjson", row)
        if index < count - 1:
            time.sleep(interval_sec)
    return rows


def values(rows: Iterable[Dict[str, Any]], phase: str, path: Tuple[str, ...]) -> List[float]:
    found: List[float] = []
    for row in rows:
        if row.get("phase") != phase:
            continue
        current: Any = row
        for part in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        parsed = number(current)
        if parsed is not None:
            found.append(parsed)
    return found


def avg(nums: List[float]) -> Optional[float]:
    return statistics.mean(nums) if nums else None


def summarize_phase(rows: List[Dict[str, Any]], phase: str) -> Dict[str, Any]:
    phase_rows = [row for row in rows if row.get("phase") == phase]
    sessions = [float(row.get("browserSessionCount", 0)) for row in phase_rows]
    pages = [float(row.get("browserPageCount", 0)) for row in phase_rows]
    heap = values(rows, phase, ("gatewayPerformanceSnapshot", "heap", "usedBytes"))
    non_heap = values(rows, phase, ("gatewayPerformanceSnapshot", "nonHeap", "usedBytes"))
    cpu = values(rows, phase, ("gatewayPerformanceSnapshot", "cpu", "processCpuLoad"))
    return {
        "sampleCount": len(phase_rows),
        "heapUsedBytesAvg": avg(heap),
        "heapUsedBytesFirst": heap[0] if heap else None,
        "heapUsedBytesLast": heap[-1] if heap else None,
        "heapUsedBytesMax": max(heap) if heap else None,
        "nonHeapUsedBytesAvg": avg(non_heap),
        "processCpuLoadAvg": avg(cpu),
        "browserSessionCountAvg": avg(sessions),
        "browserSessionCountLast": sessions[-1] if sessions else None,
        "browserPageCountAvg": avg(pages),
        "browserPageCountLast": pages[-1] if pages else None,
    }


def phase_row(rows: List[Dict[str, Any]], phase: str, *, last: bool) -> Dict[str, Any]:
    phase_rows = [row for row in rows if row.get("phase") == phase]
    if not phase_rows:
        return {}
    return phase_rows[-1] if last else phase_rows[0]


def token_set(row: Dict[str, Any], field: str) -> set:
    values = row.get(field, [])
    if not isinstance(values, list):
        return set()
    return {str(item) for item in values if str(item)}


def browser_args(args: argparse.Namespace, browser_url: str, ready_text: str, wait_after_ready_ms: int) -> argparse.Namespace:
    return argparse.Namespace(
        browser_url=browser_url,
        browser_node=args.browser_node,
        browser_node_modules=args.browser_node_modules,
        browser_ready_selector=args.browser_ready_selector,
        browser_ready_text=ready_text,
        browser_secondary_ready_selector="",
        browser_secondary_ready_text="",
        browser_timeout_sec=args.browser_timeout_sec,
        browser_viewport=args.browser_viewport,
        browser_wait_after_ready_ms=wait_after_ready_ms,
        browser_url_alias=args.browser_url_alias,
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
        browser_start_delay_sec=args.browser_start_delay_sec,
    )


def run_cycle(client: cp.RunnerClient, out_dir: Path, args: argparse.Namespace, project: str, package: Dict[str, Any], browser_url: str, cycle: int, tokens: List[str], feature_set: set) -> Dict[str, Any]:
    cycle_dir = out_dir / f"cycle-{cycle:02d}"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    cycle_rows: List[Dict[str, Any]] = []
    cycle_rows.extend(sample_phase(client, out_dir, args, project, cycle, "pre", args.pre_samples, args.interval_sec, tokens, feature_set))
    wait_ms = args.browser_wait_after_ready_ms
    if wait_ms < 0:
        wait_ms = int(max(args.during_samples * args.interval_sec + 1, 1) * 1000)
    b_args = browser_args(args, browser_url, str(package["readyText"]), wait_ms)
    probe = cp.start_browser_probe(b_args, cycle_dir)
    cycle_rows.extend(sample_phase(client, out_dir, args, project, cycle, "during", args.during_samples, args.interval_sec, tokens, feature_set))
    browser_info = cp.finish_browser_probe(probe, b_args, cycle_dir)
    cycle_rows.extend(sample_phase(client, out_dir, args, project, cycle, "post", args.post_samples, args.interval_sec, tokens, feature_set))
    browser_summary = read_json(cycle_dir / "browser-summary.json")
    network_summary = read_json(cycle_dir / "network-summary.json")
    browser_heap = browser_summary.get("heap") if isinstance(browser_summary.get("heap"), dict) else {}
    phases = {phase: summarize_phase(cycle_rows, phase) for phase in ("pre", "during", "post")}
    pre_first = phase_row(cycle_rows, "pre", last=False)
    post_last = phase_row(cycle_rows, "post", last=True)
    baseline_session_tokens = token_set(pre_first, "browserSessionTokens")
    baseline_page_tokens = token_set(pre_first, "browserPageTokens")
    post_session_tokens = token_set(post_last, "browserSessionTokens")
    post_page_tokens = token_set(post_last, "browserPageTokens")
    post_new_session_count = len(post_session_tokens - baseline_session_tokens)
    post_new_page_count = len(post_page_tokens - baseline_page_tokens)
    post_sessions_last = phases["post"].get("browserSessionCountLast")
    post_pages_last = phases["post"].get("browserPageCountLast")
    return {
        "cycle": cycle,
        "ok": bool(browser_info.get("exitCode") == 0 and browser_summary.get("ready") is True and browser_summary.get("readyTextMatched") is not False),
        "cycleDir": str(cycle_dir),
        "browserProbe": browser_info,
        "browser": {
            "ready": browser_summary.get("ready"),
            "readyTextMatched": browser_summary.get("readyTextMatched"),
            "elapsedBrowserMs": browser_summary.get("elapsedBrowserMs"),
            "domNodeCount": browser_summary.get("domNodeCount"),
            "largestContentfulPaintMs": browser_summary.get("largestContentfulPaintMs"),
            "longTaskTotalMs": browser_summary.get("longTaskTotalMs"),
            "usedJSHeapBytes": browser_heap.get("usedJSHeapSize"),
            "totalJSHeapBytes": browser_heap.get("totalJSHeapSize"),
            "jsHeapSizeLimitBytes": browser_heap.get("jsHeapSizeLimit"),
        },
        "network": {
            "requestCount": network_summary.get("requestCount"),
            "resourceTransferSize": network_summary.get("resourceTransferSize"),
            "webSocketBytesReceived": network_summary.get("webSocketBytesReceived"),
            "webSocketBytesSent": network_summary.get("webSocketBytesSent"),
        },
        "phases": phases,
        "postRetainedBrowserSessions": post_sessions_last,
        "postRetainedBrowserPages": post_pages_last,
        "preExistingBrowserSessionTokens": len(baseline_session_tokens),
        "preExistingBrowserPageTokens": len(baseline_page_tokens),
        "postNewBrowserSessions": post_new_session_count,
        "postNewBrowserPages": post_new_page_count,
        "postLastHeapUsedBytes": phases["post"].get("heapUsedBytesLast"),
        "postMaxHeapUsedBytes": phases["post"].get("heapUsedBytesMax"),
    }


def cleanup_route_present(routes_response: Dict[str, Any], route: str) -> bool:
    routes = routes_response.get("routes", [])
    if not isinstance(routes, list):
        return False
    return any(isinstance(item, dict) and item.get("pagePath") == route for item in routes)


def slope(values_in: List[float]) -> Optional[float]:
    if len(values_in) < 2:
        return None
    return values_in[-1] - values_in[0]


def monotonic_non_decreasing(values_in: List[float]) -> bool:
    return len(values_in) >= 2 and all(values_in[index] >= values_in[index - 1] for index in range(1, len(values_in)))


def classify_i04(cycles: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    post_heap = [number(row.get("postLastHeapUsedBytes")) for row in cycles]
    post_heap_values = [float(value) for value in post_heap if value is not None]
    browser_heap = [number(row.get("browser", {}).get("usedJSHeapBytes")) for row in cycles]
    browser_heap_values = [float(value) for value in browser_heap if value is not None]
    post_sessions = [number(row.get("postRetainedBrowserSessions")) for row in cycles]
    post_pages = [number(row.get("postRetainedBrowserPages")) for row in cycles]
    post_new_sessions = [number(row.get("postNewBrowserSessions")) for row in cycles]
    post_new_pages = [number(row.get("postNewBrowserPages")) for row in cycles]
    retained_final_sessions = float(post_new_sessions[-1]) if post_new_sessions and post_new_sessions[-1] is not None else None
    retained_final_pages = float(post_new_pages[-1]) if post_new_pages and post_new_pages[-1] is not None else None
    post_observed = max(args.post_samples - 1, 0) * args.interval_sec
    heap_delta = slope(post_heap_values)
    browser_heap_delta = slope(browser_heap_values)
    heap_growth = bool(heap_delta is not None and heap_delta > args.heap_growth_threshold_bytes and monotonic_non_decreasing(post_heap_values))
    browser_heap_growth = bool(browser_heap_delta is not None and browser_heap_delta > args.browser_heap_growth_threshold_bytes and monotonic_non_decreasing(browser_heap_values))
    retained_after_timeout = bool(
        args.expected_session_timeout_sec > 0
        and post_observed >= args.expected_session_timeout_sec
        and ((retained_final_sessions or 0) > 0 or (retained_final_pages or 0) > 0)
    )
    if retained_after_timeout and heap_growth:
        label = "memory-growth-suspicion-with-retention"
    elif heap_growth and not retained_after_timeout:
        label = "heap-growth-without-retention-proof"
    elif browser_heap_growth and not heap_growth:
        label = "browser-heap-growth-candidate"
    elif (retained_final_sessions or 0) > 0 or (retained_final_pages or 0) > 0:
        label = "retention-observed-within-post-window"
    else:
        label = "no-memory-growth-suspicion-from-this-fixture"
    return {
        "label": label,
        "postSettleObservedSecondsPerCycle": post_observed,
        "expectedSessionTimeoutSeconds": args.expected_session_timeout_sec or None,
        "postLastHeapUsedBytesByCycle": post_heap_values,
        "postLastHeapDeltaBytes": heap_delta,
        "postLastHeapMonotonicNonDecreasing": monotonic_non_decreasing(post_heap_values),
        "browserHeapBytesByCycle": browser_heap_values,
        "browserHeapDeltaBytes": browser_heap_delta,
        "browserHeapMonotonicNonDecreasing": monotonic_non_decreasing(browser_heap_values),
        "postRetainedBrowserSessionsByCycle": post_sessions,
        "postRetainedBrowserPagesByCycle": post_pages,
        "postNewBrowserSessionsByCycle": post_new_sessions,
        "postNewBrowserPagesByCycle": post_new_pages,
        "retainedAfterDeclaredTimeout": retained_after_timeout,
        "heapGrowthThresholdBytes": args.heap_growth_threshold_bytes,
        "browserHeapGrowthThresholdBytes": args.browser_heap_growth_threshold_bytes,
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# I-04 Memory-Growth Suspicion Fixture",
        "",
        f"Run ID: `{summary.get('runId')}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Classification: `{summary.get('classification', {}).get('label')}`",
        "",
        "## Cycles",
        "",
        "| Cycle | OK | Browser heap | DOM | Long task ms | Post heap last | Raw post sessions | Raw post pages | New post sessions | New post pages |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.get("cycles", []):
        browser = row.get("browser", {})
        phases = row.get("phases", {})
        post = phases.get("post", {}) if isinstance(phases, dict) else {}
        lines.append(
            "| {cycle} | `{ok}` | {browser_heap} | {dom} | {long_task} | {post_heap} | {sessions} | {pages} | {new_sessions} | {new_pages} |".format(
                cycle=row.get("cycle"),
                ok=str(row.get("ok", False)).lower(),
                browser_heap=browser.get("usedJSHeapBytes"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                post_heap=post.get("heapUsedBytesLast"),
                sessions=post.get("browserSessionCountLast"),
                pages=post.get("browserPageCountLast"),
                new_sessions=row.get("postNewBrowserSessions"),
                new_pages=row.get("postNewBrowserPages"),
            )
        )
    lines.extend(["", "## Classification Detail", ""])
    for key, value in summary.get("classification", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    run_slug = slug(args.run_id)
    base = compact(args.run_id)
    route = build_route(args.route_prefix, run_slug)
    view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/MemoryGrowth"
    package = build_package(out_dir, project, args, view_path, route)
    package_record = {key: value for key, value in package.items() if key != "packageBase64"}
    backup_name = ""
    gates: Dict[str, bool] = {}
    cycles: List[Dict[str, Any]] = []
    cleanup: Dict[str, Any] = {}

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_response = cp.response(health)
    health_ok = cp.ok(health)
    feature_set = set(health_response.get("features", []) if isinstance(health_response.get("features"), list) else [])
    tokens = metric_tokens_from_health(client, args.run_id, args.max_metrics, feature_set)
    browser_url = common.browser_url_from_endpoint(endpoint, project, route)
    if not browser_url:
        raise SystemExit("Could not derive browser URL from runner endpoint")

    try:
        dry = client.call(f"{args.run_id}-dryRun", package_payload("dryRun", f"{args.run_id}-dryRun", project, package, args), timeout=args.timeout_sec)
        gates["dryRun"] = cp.ok(dry)
        if not gates["dryRun"]:
            raise RuntimeError("dryRun failed")
        apply = client.call(f"{args.run_id}-apply", package_payload("apply", f"{args.run_id}-apply", project, package, args), timeout=args.timeout_sec)
        backup_name = common.backup_name_from_response(cp.response(apply))
        gates["apply"] = cp.ok(apply) and bool(backup_name)
        if not gates["apply"]:
            raise RuntimeError("apply failed")
        time.sleep(args.apply_settle_sec)
        readback = client.call(f"{args.run_id}-viewRead", view_read_payload(f"{args.run_id}-viewRead", project, view_path, args))
        gates["viewRead"] = readback_ok(readback, package)
        page = client.call(f"{args.run_id}-pageValidate", page_validate_payload(f"{args.run_id}-pageValidate", project, package, args))
        gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
        if not (gates["viewRead"] and gates["pageValidate"]):
            raise RuntimeError("readback or pageValidate failed")
        for cycle in range(1, args.cycles + 1):
            cycles.append(run_cycle(client, out_dir, args, project, package, browser_url, cycle, tokens, feature_set))
            if cycle < args.cycles and args.pause_sec > 0:
                time.sleep(args.pause_sec)
        gates["cycles"] = bool(cycles and all(row.get("ok") for row in cycles))
    except Exception as exc:
        gates.setdefault("cycles", False)
        cycles.append({"cycle": len(cycles) + 1, "ok": False, "error": repr(exc)})
    finally:
        if backup_name:
            rb_dry = client.call(f"{args.run_id}-rollback-dryRun", rollback_payload(f"{args.run_id}-rollback-dryRun", project, backup_name, view_path, True), timeout=args.timeout_sec)
            rb_apply = client.call(f"{args.run_id}-rollback-apply", rollback_payload(f"{args.run_id}-rollback-apply", project, backup_name, view_path, False), timeout=args.timeout_sec)
            time.sleep(args.apply_settle_sec)
            routes_check = client.call(
                f"{args.run_id}-post-cleanup-routesList",
                {"action": "routesList", "requestId": f"{args.run_id}-post-cleanup-routesList", "targetProject": project, "routePrefix": route, "maxResults": 25},
            )
            after_read = client.call(f"{args.run_id}-post-cleanup-viewRead", view_read_payload(f"{args.run_id}-post-cleanup-viewRead", project, view_path, args))
            cleanup = {
                "rollbackOk": cp.ok(rb_dry) and cp.ok(rb_apply),
                "cleanupRouteAbsent": cp.ok(routes_check) and not cleanup_route_present(cp.response(routes_check), route),
                "cleanupViewAbsent": not cp.ok(after_read),
            }

    classification = classify_i04([row for row in cycles if row.get("phases")], args)
    interpretation = [
        "This is a controlled I-04 mechanics fixture, not a customer leak conclusion.",
        "JVM heap, retained Perspective browser session/page counts, and browser JavaScript heap are reported separately.",
        "Instantaneous JVM heap peaks are allocation/GC evidence only; leak language requires retained Perspective counts after the declared timeout or stronger target-specific evidence.",
    ]
    if classification.get("label") == "heap-growth-without-retention-proof":
        interpretation.append("Post-settle JVM heap rose across cycles, but retained Perspective sessions/pages after the declared timeout were not proven.")
    if classification.get("label") == "retention-observed-within-post-window":
        interpretation.append("Perspective retention remained in the observed post window; compare the window to the configured Perspective timeout before calling it abnormal.")
    if classification.get("label") == "no-memory-growth-suspicion-from-this-fixture":
        interpretation.append("The repeated fixture did not produce memory-growth suspicion under the configured thresholds.")

    summary = {
        "ok": bool(health_ok and all(gates.values()) and cleanup.get("rollbackOk") and cleanup.get("cleanupRouteAbsent") and cleanup.get("cleanupViewAbsent")),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": health_response.get("runnerVersion"),
        "stackVersion": health_response.get("stackVersion"),
        "features": sorted(feature_set),
        "route": route,
        "viewPath": view_path,
        "cyclesRequested": args.cycles,
        "preSamples": args.pre_samples,
        "duringSamples": args.during_samples,
        "postSamples": args.post_samples,
        "intervalSeconds": args.interval_sec,
        "expectedSessionTimeoutSeconds": args.expected_session_timeout_sec or None,
        "metricTokenCount": len(tokens),
        "gates": gates,
        "cleanup": cleanup,
        "package": package_record,
        "cycles": cycles,
        "classification": classification,
        "interpretation": interpretation,
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "package.json", package_record)
    write_report(out_dir, summary)
    print(json.dumps({"ok": summary["ok"], "outDir": str(out_dir), "classification": classification.get("label")}, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--rows", type=int, default=500)
    parser.add_argument("--columns", type=int, default=30)
    parser.add_argument("--virtualized", action="store_true")
    parser.add_argument("--pre-samples", type=int, default=2)
    parser.add_argument("--during-samples", type=int, default=4)
    parser.add_argument("--post-samples", type=int, default=8)
    parser.add_argument("--interval-sec", type=float, default=3.0)
    parser.add_argument("--expected-session-timeout-sec", type=float, default=0.0)
    parser.add_argument("--heap-growth-threshold-bytes", type=float, default=64 * 1024 * 1024)
    parser.add_argument("--browser-heap-growth-threshold-bytes", type=float, default=32 * 1024 * 1024)
    parser.add_argument("--max-metrics", type=int, default=70)
    parser.add_argument("--timeout-sec", type=int, default=90)
    parser.add_argument("--command-timeout-sec", type=int, default=420)
    parser.add_argument("--apply-settle-sec", type=float, default=3.0)
    parser.add_argument("--pause-sec", type=float, default=3.0)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-node", default="node")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=75.0)
    parser.add_argument("--browser-start-delay-sec", type=float, default=1.5)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=-1)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.cycles <= 0:
        raise SystemExit("--cycles must be positive")
    if args.rows <= 0 or args.columns <= 0:
        raise SystemExit("--rows and --columns must be positive")
    if args.pre_samples <= 0 or args.during_samples <= 0 or args.post_samples <= 0:
        raise SystemExit("--pre-samples, --during-samples, and --post-samples must be positive")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be positive")
    run(args)


if __name__ == "__main__":
    main()
