#!/usr/bin/env python3
"""Run guarded Tab Container runWhileHidden A/B fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
BROWSER_TAB_PROBE = SCRIPT_DIR / "browser_tab_switch_probe.mjs"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
VARIANTS = ("unload-hidden", "persist-hidden")
CONTENT_MODES = ("direct", "viewpath")
OFFICIAL_SOURCE = "https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-container-palette/perspective-tab-container"


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
    common.write_json(path, data)


def read_json(path: Path) -> Dict[str, Any]:
    return common.read_json(path)


def append_ndjson(path: Path, row: Dict[str, Any]) -> None:
    cp.append_ndjson(path, row)


def to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
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
    variant: str,
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
            "reason": "runner health.supportedActions/features does not include perspectiveSessionsQuery",
            "sampleCount": 0,
            "maxBrowserSessions": max_browser_sessions,
        }
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"variant": variant, "sampledAt": utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-{variant}-baselineWait-{attempt:03d}"
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
            "variant": variant,
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


def component(
    component_type: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    props: Optional[Dict[str, Any]] = None,
    position: Optional[Dict[str, Any]] = None,
    prop_config: Optional[Dict[str, Any]] = None,
    children: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {"type": component_type}
    if meta is not None:
        row["meta"] = meta
    if props is not None:
        row["props"] = props
    if position is not None:
        row["position"] = position
    if prop_config is not None:
        row["propConfig"] = prop_config
    if children is not None:
        row["children"] = children
    return row


def expression_binding(expression: str) -> Dict[str, Any]:
    return {"binding": {"type": "expr", "config": {"expression": expression}}}


def variant_run_while_hidden(variant: str) -> bool:
    if variant == "persist-hidden":
        return True
    if variant == "unload-hidden":
        return False
    raise ValueError(f"Unsupported variant: {variant}")


def make_work_label(index: int, expression_rate_ms: int) -> Dict[str, Any]:
    return component(
        "ia.display.label",
        meta={"name": f"Work Tick {index:03d}"},
        position={"basis": "20px", "grow": 0, "shrink": 0},
        props={
            "text": f"work tick {index:03d}",
            "style": {
                "color": "#1f2937",
                "fontSize": 11,
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "whiteSpace": "nowrap",
            },
        },
        prop_config={"props.text": expression_binding(f"now({expression_rate_ms})")},
    )


def make_control_children(run_id: str, variant: str, work_labels: int, expression_rate_ms: int) -> List[Dict[str, Any]]:
    initial_ready = f"{run_id} {variant.upper()} CONTROL READY"
    return [
        component(
            "ia.display.label",
            meta={"name": "Control Ready Marker"},
            position={"basis": "42px", "grow": 0, "shrink": 0},
            props={
                "text": initial_ready,
                "style": {
                    "backgroundColor": "#ffffff",
                    "borderColor": "#64748b",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "fontSize": 16,
                    "fontWeight": "700",
                    "padding": "9px 10px",
                    "whiteSpace": "pre-wrap",
                },
            },
        ),
        component(
            "ia.display.label",
            meta={"name": "Control Summary"},
            position={"basis": "44px", "grow": 0, "shrink": 0},
            props={
                "text": f"Tab runWhileHidden fixture: variant {variant}, work labels {work_labels}, expression rate {expression_rate_ms} ms.",
                "style": {"color": "#334155", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
            },
        ),
    ]


def make_work_children(run_id: str, variant: str, work_labels: int, expression_rate_ms: int) -> List[Dict[str, Any]]:
    work_ready = f"{run_id} {variant.upper()} WORK READY"
    work_children = [
        component(
            "ia.display.label",
            meta={"name": "Work Ready Marker"},
            position={"basis": "42px", "grow": 0, "shrink": 0},
            props={
                "text": work_ready,
                "style": {
                    "backgroundColor": "#eef2ff",
                    "borderColor": "#818cf8",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "fontSize": 16,
                    "fontWeight": "700",
                    "padding": "9px 10px",
                    "whiteSpace": "pre-wrap",
                },
            },
        ),
        component(
            "ia.display.label",
            meta={"name": "Work Summary"},
            position={"basis": "40px", "grow": 0, "shrink": 0},
            props={
                "text": f"Work tab has {work_labels} expression-bound labels. After activation, the browser switches back to Control Tab and Gateway metrics are sampled during the background hold.",
                "style": {"color": "#334155", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
            },
        ),
    ]
    work_children.extend(make_work_label(index, expression_rate_ms) for index in range(1, work_labels + 1))
    return work_children


def make_direct_view_json(run_id: str, variant: str, work_labels: int, expression_rate_ms: int) -> Dict[str, Any]:
    run_while_hidden = variant_run_while_hidden(variant)
    tabs = [
        {"text": "Control Tab", "runWhileHidden": run_while_hidden},
        {"text": "Work Tab", "runWhileHidden": run_while_hidden},
    ]
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "runWhileHidden": run_while_hidden,
            "contentMode": "direct",
            "workLabels": work_labels,
            "expressionRateMs": expression_rate_ms,
            "testPurpose": "Tab Container runWhileHidden background-work measurement",
            "officialSource": OFFICIAL_SOURCE,
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.tab",
            meta={"name": "tab-runwhilehidden-root"},
            props={
                "currentTabIndex": 0,
                "tabs": tabs,
                "menuType": "modern",
                "tabSize": {"width": 170, "height": 42},
                "contentStyle": {"overflow": "hidden"},
                "style": {"backgroundColor": "#f8fafc"},
            },
            children=[
                component(
                    "ia.container.flex",
                    meta={"name": "Control Tab Content"},
                    position={"tabIndex": 0},
                    props={
                        "direction": "column",
                        "alignItems": "stretch",
                        "justify": "flex-start",
                        "style": {"backgroundColor": "#f8fafc", "overflow": "hidden", "padding": "12px"},
                    },
                    children=make_control_children(run_id, variant, work_labels, expression_rate_ms),
                ),
                component(
                    "ia.container.flex",
                    meta={"name": "Work Tab Content"},
                    position={"tabIndex": 1},
                    props={
                        "direction": "column",
                        "alignItems": "stretch",
                        "justify": "flex-start",
                        "style": {"backgroundColor": "#ffffff", "overflow": "auto", "padding": "12px"},
                    },
                    children=make_work_children(run_id, variant, work_labels, expression_rate_ms),
                ),
            ],
        ),
        "permissions": {},
    }


def make_child_view_json(
    run_id: str,
    variant: str,
    work_labels: int,
    expression_rate_ms: int,
    child_kind: str,
) -> Dict[str, Any]:
    children = make_control_children(run_id, variant, work_labels, expression_rate_ms) if child_kind == "control" else make_work_children(run_id, variant, work_labels, expression_rate_ms)
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "contentMode": "viewpath",
            "childKind": child_kind,
            "workLabels": work_labels,
            "expressionRateMs": expression_rate_ms,
            "testPurpose": "Tab Container viewPath child runWhileHidden background-work measurement",
            "officialSource": OFFICIAL_SOURCE,
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 640}},
        "root": component(
            "ia.container.flex",
            meta={"name": f"tab-{child_kind}-child-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "style": {"backgroundColor": "#ffffff" if child_kind == "work" else "#f8fafc", "overflow": "auto", "padding": "12px"},
            },
            children=children,
        ),
        "permissions": {},
    }


def make_viewpath_parent_json(
    run_id: str,
    variant: str,
    work_labels: int,
    expression_rate_ms: int,
    control_child_view_path: str,
    work_child_view_path: str,
) -> Dict[str, Any]:
    run_while_hidden = variant_run_while_hidden(variant)
    tabs = [
        {"runWhileHidden": run_while_hidden, "viewPath": control_child_view_path, "viewParams": {}},
        {"runWhileHidden": run_while_hidden, "viewPath": work_child_view_path, "viewParams": {}},
    ]
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "runWhileHidden": run_while_hidden,
            "contentMode": "viewpath",
            "workLabels": work_labels,
            "expressionRateMs": expression_rate_ms,
            "testPurpose": "Tab Container viewPath child runWhileHidden background-work measurement",
            "officialSource": OFFICIAL_SOURCE,
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.tab",
            meta={"name": "tab-viewpath-runwhilehidden-root"},
            props={
                "currentTabIndex": 0,
                "runWhileHidden": run_while_hidden,
                "loadingMode": "with-parent",
                "tabs": tabs,
                "menuType": "modern",
                "tabSize": {"width": 170, "height": 42},
                "contentStyle": {"overflow": "hidden"},
                "style": {"backgroundColor": "#f8fafc"},
            },
            children=[],
        ),
        "permissions": {},
    }


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-tab-rwh-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", fixture_common.resource_json(actor, ["view.json"]))


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    parent_view_path: str,
    route: str,
    work_labels: int,
    expression_rate_ms: int,
    content_mode: str,
    control_child_view_path: str = "",
    work_child_view_path: str = "",
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-tab-runwhilehidden"
    if content_mode == "direct":
        parent_view = make_direct_view_json(run_id, variant, work_labels, expression_rate_ms)
        child_views: List[Dict[str, Any]] = []
        child_view_paths: List[str] = []
    elif content_mode == "viewpath":
        if not control_child_view_path or not work_child_view_path:
            raise ValueError("viewpath content mode requires control and work child view paths")
        parent_view = make_viewpath_parent_json(run_id, variant, work_labels, expression_rate_ms, control_child_view_path, work_child_view_path)
        child_view_paths = [control_child_view_path, work_child_view_path]
        child_views = [
            {"path": control_child_view_path, "json": make_child_view_json(run_id, variant, work_labels, expression_rate_ms, "control"), "kind": "control"},
            {"path": work_child_view_path, "json": make_child_view_json(run_id, variant, work_labels, expression_rate_ms, "work"), "kind": "work"},
        ]
    else:
        raise ValueError(f"Unsupported content mode: {content_mode}")
    zip_path = zip_dir / f"tab-rwh-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-tab-rwh-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler Tab runWhileHidden fixture", "enabled": True, "inheritable": False})
        for child in child_views:
            write_view(project_root, str(child["path"]), child["json"], actor)
        write_view(project_root, parent_view_path, parent_view, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Tab runWhileHidden {variant}", "viewPath": parent_view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    child_hashes = {str(child["path"]): sha256_text(canonical_json(child["json"])) for child in child_views}
    return {
        "variant": variant,
        "runWhileHidden": variant_run_while_hidden(variant),
        "contentMode": content_mode,
        "viewPath": parent_view_path,
        "parentViewPath": parent_view_path,
        "childViewPaths": child_view_paths,
        "viewPaths": [parent_view_path] + child_view_paths,
        "route": route,
        "workLabels": work_labels,
        "expressionRateMs": expression_rate_ms,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(parent_view)),
        "parentViewSha256": sha256_text(canonical_json(parent_view)),
        "childViewSha256": child_hashes,
        "controlReadyText": f"{run_id} {variant.upper()} CONTROL READY",
        "workReadyText": f"{run_id} {variant.upper()} WORK READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["parentViewPath"], "title": f"Tab runWhileHidden {package['variant']}"}],
        "dependencyViewPaths": package.get("childViewPaths", []),
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


def page_validate_payload(request_id: str, project: str, package: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "action": "pageValidate",
        "requestId": request_id,
        "targetProject": project,
        "pagePath": package["route"],
        "expectedViewPath": package["parentViewPath"],
        "allowedViewPrefix": args.allowed_view_prefix,
        "allowedRoutePrefix": args.allowed_route_prefix,
        "dependencyViewPaths": package.get("childViewPaths", []),
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [],
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


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    text = canonical_json(cp.response(record))
    expected = '"runWhileHidden":true' if package["runWhileHidden"] else '"runWhileHidden":false'
    if package.get("contentMode") == "viewpath":
        return (
            cp.ok(record)
            and '"type":"ia.container.tab"' in text
            and text.count(expected) >= 3
            and all(str(path) in text for path in package.get("childViewPaths", []))
            and '"loadingMode":"with-parent"' in text
        )
    return (
        cp.ok(record)
        and '"type":"ia.container.tab"' in text
        and text.count(expected) >= 2
        and text.count('"type":"expr"') >= int(package["workLabels"])
        and str(package["controlReadyText"]) in text
        and str(package["workReadyText"]) in text
    )


def child_readback_ok(record: Dict[str, Any], package: Dict[str, Any], child_path: str) -> bool:
    text = canonical_json(cp.response(record))
    if not cp.ok(record) or '"type":"ia.container.flex"' not in text:
        return False
    if child_path.endswith("WorkChild"):
        return str(package["workReadyText"]) in text and text.count('"type":"expr"') >= int(package["workLabels"])
    if child_path.endswith("ControlChild"):
        return str(package["controlReadyText"]) in text
    return str(package["controlReadyText"]) in text or str(package["workReadyText"]) in text


def browser_env(args: argparse.Namespace) -> Dict[str, str]:
    env = dict(os.environ)
    if args.browser_node_modules:
        existing = env.get("NODE_PATH", "")
        roots = [args.browser_node_modules]
        pnpm_root = Path(args.browser_node_modules) / ".pnpm" / "node_modules"
        if pnpm_root.exists():
            roots.append(str(pnpm_root))
        env["NODE_PATH"] = os.pathsep.join(roots + ([existing] if existing else []))
    return env


def redact_command(cmd: List[str]) -> List[str]:
    redacted = list(cmd)
    for index, value in enumerate(redacted[:-1]):
        if value == "--url":
            redacted[index + 1] = "<redacted-browser-url>"
        elif value == "--browser-node-modules":
            redacted[index + 1] = "<redacted-node-modules>"
        elif value.endswith("ready-text"):
            redacted[index + 1] = "<redacted-ready-text>"
    return redacted


def start_browser_probe(args: argparse.Namespace, package: Dict[str, Any], browser_url: str, profile_dir: Path) -> Dict[str, Any]:
    marker_path = profile_dir / "background-hold-start.json"
    use_index_tabs = package.get("contentMode") == "viewpath"
    command = [
        args.browser_node,
        str(BROWSER_TAB_PROBE),
        "--url",
        browser_url,
        "--out-dir",
        str(profile_dir),
        "--marker-path",
        str(marker_path),
        "--initial-ready-text",
        str(package["controlReadyText"]),
        "--work-ready-text",
        str(package["workReadyText"]),
        "--return-ready-text",
        str(package["controlReadyText"]),
        "--control-tab-text",
        "" if use_index_tabs else "Control Tab",
        "--work-tab-text",
        "" if use_index_tabs else "Work Tab",
        "--control-tab-index",
        "0",
        "--work-tab-index",
        "1",
        "--hold-ms",
        str(args.background_hold_ms),
        "--settle-ms",
        str(args.browser_settle_ms),
        "--timeout-ms",
        str(int(args.browser_timeout_sec * 1000)),
        "--viewport",
        args.browser_viewport,
        "--url-alias",
        args.browser_url_alias,
    ]
    stdout_path = profile_dir / "browser-tab-probe.stdout.txt"
    stderr_path = profile_dir / "browser-tab-probe.stderr.txt"
    stdout_handle = stdout_path.open("w", encoding="utf-8", newline="\n")
    stderr_handle = stderr_path.open("w", encoding="utf-8", newline="\n")
    try:
        process = subprocess.Popen(command, stdout=stdout_handle, stderr=stderr_handle, cwd=str(SCRIPT_DIR), env=browser_env(args))
    except Exception:
        stdout_handle.close()
        stderr_handle.close()
        raise
    return {
        "process": process,
        "stdoutHandle": stdout_handle,
        "stderrHandle": stderr_handle,
        "command": redact_command(command),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
        "markerPath": str(marker_path),
        "startedAt": utc_now(),
    }


def wait_for_marker(marker_path: Path, process: subprocess.Popen[Any], timeout_sec: float) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if marker_path.exists():
            return True
        if process.poll() is not None:
            return marker_path.exists()
        time.sleep(0.25)
    return marker_path.exists()


def finish_browser_probe(info: Dict[str, Any], timeout_sec: float) -> Dict[str, Any]:
    process = info.get("process")
    timed_out = False
    exit_code = None
    try:
        exit_code = process.wait(timeout=timeout_sec) if process is not None else None
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        exit_code = process.wait(timeout=5)
    finally:
        for key in ("stdoutHandle", "stderrHandle"):
            handle = info.get(key)
            if handle:
                handle.close()
    return {key: value for key, value in info.items() if key not in {"process", "stdoutHandle", "stderrHandle"}} | {"exitCode": exit_code, "timedOut": timed_out, "finishedAt": utc_now()}


def metric_tokens_from_list(metrics_response: Dict[str, Any], max_metrics: int) -> List[str]:
    return cp.metric_tokens(metrics_response, max_metrics)


def collect_profile_window(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    profile_dir: Path,
    project: str,
    run_id: str,
    feature_set: set[str],
) -> Dict[str, Any]:
    missing: List[Dict[str, str]] = []
    metric_filters = args.metric_name_contains or ["Perspective", "perspective"]
    tokens: List[str] = []
    metrics_list_record: Optional[Dict[str, Any]] = None
    if "metricsList" in feature_set:
        payload: Dict[str, Any] = {
            "action": "metricsList",
            "requestId": f"{run_id}-metricsList",
            "nameContains": metric_filters,
            "maxResults": min(max(args.max_metrics * 3, args.max_metrics), 250),
        }
        if args.metric_prefix:
            payload["namePrefixes"] = args.metric_prefix
        metrics_list_record = client.call(f"{run_id}-metricsList", payload)
        write_json(profile_dir / "metrics-list.json", cp.response(metrics_list_record))
        tokens = metric_tokens_from_list(cp.response(metrics_list_record), max(0, min(args.max_metrics, 100)))
        if not tokens:
            missing.append({"name": "metricsSnapshot", "reason": "metricsList returned no metric tokens for the configured filters"})
    else:
        missing.append({"name": "metricsList", "reason": "runner health.features does not include metricsList"})

    duration_sec = max(float(args.background_hold_ms) / 1000.0, args.interval_sec)
    sample_count = int(math.floor(duration_sec / args.interval_sec)) + 1
    for index in range(sample_count):
        started = utc_now()
        gateway_sample: Dict[str, Any] = {"sampleIndex": index, "phase": "background", "startedAt": started}
        if tokens and "metricsSnapshot" in feature_set:
            record = client.call(
                f"{run_id}-metricsSnapshot-{index:03d}",
                {"action": "metricsSnapshot", "requestId": f"{run_id}-metricsSnapshot-{index:03d}", "metricTokens": tokens, "maxMetrics": len(tokens)},
            )
            gateway_sample["metricsSnapshot"] = cp.response(record)
        elif "metricsSnapshot" not in feature_set:
            gateway_sample["metricsSnapshot"] = {"ok": False, "missing": True, "reason": "feature not present"}
        if "gatewayPerformanceSnapshot" in feature_set:
            record = client.call(
                f"{run_id}-gatewayPerformanceSnapshot-{index:03d}",
                {"action": "gatewayPerformanceSnapshot", "requestId": f"{run_id}-gatewayPerformanceSnapshot-{index:03d}"},
            )
            gateway_sample["gatewayPerformanceSnapshot"] = cp.response(record)
        else:
            gateway_sample["gatewayPerformanceSnapshot"] = {"ok": False, "missing": True, "reason": "feature not present"}
        gateway_sample["finishedAt"] = utc_now()
        append_ndjson(profile_dir / "gateway-samples.ndjson", gateway_sample)

        session_sample: Dict[str, Any] = {"sampleIndex": index, "phase": "background", "startedAt": started}
        if "perspectiveSessionsQuery" in feature_set:
            record = client.call(
                f"{run_id}-perspectiveSessionsQuery-{index:03d}",
                {"action": "perspectiveSessionsQuery", "requestId": f"{run_id}-perspectiveSessionsQuery-{index:03d}", "targetProject": project, "maxResults": 50},
            )
            session_sample["perspectiveSessionsQuery"] = cp.response(record)
        else:
            session_sample["perspectiveSessionsQuery"] = {"ok": False, "missing": True, "reason": "feature not present"}
        session_sample["finishedAt"] = utc_now()
        append_ndjson(profile_dir / "perspective-session-samples.ndjson", session_sample)
        if index < sample_count - 1:
            time.sleep(args.interval_sec)

    if "metricsSnapshot" not in feature_set:
        missing.append({"name": "metricsSnapshot", "reason": "runner health.features does not include metricsSnapshot"})
    if "gatewayPerformanceSnapshot" not in feature_set:
        missing.append({"name": "gatewayPerformanceSnapshot", "reason": "runner health.features does not include gatewayPerformanceSnapshot"})
    if "perspectiveSessionsQuery" not in feature_set:
        missing.append({"name": "perspectiveSessionsQuery", "reason": "runner health.features does not include perspectiveSessionsQuery"})
    return {
        "sampleCount": sample_count,
        "metricTokenCount": len(tokens),
        "metricsListOk": cp.ok(metrics_list_record) if metrics_list_record else False,
        "missingEvidence": missing,
    }


def metric_items_by_name(row: Dict[str, Any]) -> Dict[str, float]:
    snapshot = row.get("metricsSnapshot", {}) if isinstance(row.get("metricsSnapshot"), dict) else {}
    metrics = snapshot.get("metrics", []) if isinstance(snapshot.get("metrics"), list) else []
    result: Dict[str, float] = {}
    for item in metrics:
        if not isinstance(item, dict) or item.get("ok") is not True:
            continue
        name = str(item.get("name", "")).strip()
        value = to_float(item.get("count"))
        if name and value is not None:
            result[name] = result.get(name, 0.0) + value
    return result


def summarize_metric_counts(profile_dir: Path) -> Dict[str, Any]:
    rows = []
    path = profile_dir / "gateway-samples.ndjson"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    items = [metric_items_by_name(row) for row in rows]
    names = sorted({name for row in items for name in row})
    counts: Dict[str, Dict[str, Any]] = {}
    for name in names:
        values = [row[name] for row in items if name in row]
        counts[name] = {"first": values[0] if values else None, "last": values[-1] if values else None, "delta": (values[-1] - values[0]) if len(values) >= 2 else None}
    preferred_expr = "perspective.expressions" if "perspective.expressions" in counts else next((name for name in names if name.startswith("perspective.") and name.endswith(".expressions")), "")
    preferred_prop = "perspective.property-changes" if "perspective.property-changes" in counts else next((name for name in names if name.startswith("perspective.") and name.endswith(".property-changes")), "")
    preferred_scripts = "perspective.scripts" if "perspective.scripts" in counts else next((name for name in names if name.startswith("perspective.") and name.endswith(".scripts")), "")
    return {
        "sampleCount": len(rows),
        "countMetricNames": names,
        "counts": counts,
        "primaryPerspectiveExpressionsMetric": preferred_expr,
        "primaryPerspectiveExpressionsDelta": counts.get(preferred_expr, {}).get("delta") if preferred_expr else None,
        "primaryPerspectivePropertyChangesMetric": preferred_prop,
        "primaryPerspectivePropertyChangesDelta": counts.get(preferred_prop, {}).get("delta") if preferred_prop else None,
        "primaryPerspectiveScriptsMetric": preferred_scripts,
        "primaryPerspectiveScriptsDelta": counts.get(preferred_scripts, {}).get("delta") if preferred_scripts else None,
    }


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    profile = read_json(profile_dir / "static-profile.json")
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    hidden = profile.get("hiddenContent", []) if isinstance(profile.get("hiddenContent"), list) else []
    dependency_count = 0
    dependency_binding_count = 0
    dependency_component_count = 0
    dependency_path = profile_dir / "dependency-static-profiles.json"
    if dependency_path.exists():
        try:
            dependencies = json.loads(dependency_path.read_text(encoding="utf-8-sig"))
        except Exception:
            dependencies = []
        if isinstance(dependencies, list):
            dependency_count = len(dependencies)
            for item in dependencies:
                if not isinstance(item, dict):
                    continue
                dep_profile = item.get("staticProfile", {}) if isinstance(item.get("staticProfile"), dict) else {}
                dep_summary = dep_profile.get("summary", {}) if isinstance(dep_profile.get("summary"), dict) else {}
                dependency_binding_count += int(to_float(dep_summary.get("bindingCount")) or 0)
                dependency_component_count += int(to_float(dep_summary.get("componentCount")) or 0)
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
        "hiddenContentCount": len(hidden),
        "dependencyViewCount": dependency_count,
        "dependencyComponentCount": dependency_component_count,
        "dependencyBindingCount": dependency_binding_count,
    }


def browser_summary(profile_dir: Path) -> Dict[str, Any]:
    browser = read_json(profile_dir / "browser-summary.json")
    lcp = browser.get("largestContentfulPaint", {}) if isinstance(browser.get("largestContentfulPaint"), dict) else {}
    heap = browser.get("heap", {}) if isinstance(browser.get("heap"), dict) else {}
    interaction = browser.get("interaction", {}) if isinstance(browser.get("interaction"), dict) else {}
    return {
        "ok": browser.get("ok"),
        "domNodeCount": browser.get("domNodeCount"),
        "longTaskTotalMs": browser.get("longTaskTotalMs"),
        "longTaskCount": browser.get("longTaskCount"),
        "largestContentfulPaintMs": lcp.get("startTime"),
        "usedJSHeapBytes": heap.get("usedJSHeapSize"),
        "interactionOk": interaction.get("ok"),
        "phaseCount": len(interaction.get("phases", [])) if isinstance(interaction.get("phases"), list) else None,
    }


def gateway_summary(profile_dir: Path) -> Dict[str, Any]:
    rows = []
    path = profile_dir / "gateway-samples.ndjson"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    heaps: List[float] = []
    cpus: List[float] = []
    for row in rows:
        perf = row.get("gatewayPerformanceSnapshot", {}) if isinstance(row.get("gatewayPerformanceSnapshot"), dict) else {}
        heap = perf.get("heap", {}) if isinstance(perf.get("heap"), dict) else {}
        cpu = perf.get("cpu", {}) if isinstance(perf.get("cpu"), dict) else {}
        heap_value = to_float(perf.get("heapUsedBytes") or heap.get("usedBytes"))
        cpu_value = to_float(perf.get("processCpuLoad") or cpu.get("processCpuLoad"))
        if heap_value is not None:
            heaps.append(heap_value)
        if cpu_value is not None:
            cpus.append(cpu_value)
    return {"heapUsedBytesMedian": median(heaps) if heaps else None, "processCpuLoadMedian": median(cpus) if cpus else None}


def write_profile_manifest(
    profile_dir: Path,
    args: argparse.Namespace,
    package: Dict[str, Any],
    health: Dict[str, Any],
    feature_set: set[str],
    view_response: Dict[str, Any],
    static_profile: Dict[str, Any],
    window: Dict[str, Any],
    browser_probe: Dict[str, Any],
) -> None:
    missing = list(window.get("missingEvidence", []))
    if browser_probe.get("exitCode") != 0:
        missing.append({"name": "browserProbe", "reason": "Tab switch browser probe exited non-zero"})
    manifest = {
        "ok": not missing,
        "runId": f"{args.run_id}-tab-rwh-{package['variant']}",
        "createdAt": utc_now(),
        "gatewayAlias": args.gateway_alias,
        "project": args.project or "",
        "route": package["route"],
        "view": package["viewPath"],
        "scenario": "Tab Container runWhileHidden background hold",
        "sampleIntervalSeconds": args.interval_sec,
        "sampleDurationSeconds": float(args.background_hold_ms) / 1000.0,
        "sampleCount": window.get("sampleCount"),
        "runnerVersion": health.get("runnerVersion"),
        "stackVersion": health.get("stackVersion"),
        "features": sorted(feature_set),
        "viewSha256": view_response.get("viewSha256") or static_profile.get("viewSha256"),
        "staticProfileSha256": static_profile.get("viewSha256"),
        "evidenceGrade": "Observed",
        "changedResources": [],
        "missingEvidence": missing,
        "browserProbe": {key: value for key, value in browser_probe.items() if key not in {"command"}},
        "files": [
            "manifest.json",
            "summary.json",
            "view-read.json",
            "static-profile.json",
            "dependency-static-profiles.json",
            "metrics-list.json",
            "gateway-samples.ndjson",
            "perspective-session-samples.ndjson",
            "browser-summary.json",
            "browser-console.json",
            "network-summary.json",
            "logs.json",
            "thread-excerpts.json",
            "comparison.json",
        ],
    }
    write_json(profile_dir / "manifest.json", manifest)


def profile_variant(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    project: str,
    package: Dict[str, Any],
    profile_dir: Path,
    health: Dict[str, Any],
    feature_set: set[str],
) -> Dict[str, Any]:
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_view = cp.ensure_profile_function()
    readback = client.call(f"{args.run_id}-{package['variant']}-profile-viewRead", view_read_payload(f"{args.run_id}-{package['variant']}-profile-viewRead", project, package["viewPath"], args))
    view_response = cp.response(readback)
    write_json(profile_dir / "view-read.json", view_response)
    static_profile = profile_view(view_response, "view-read.json")
    write_json(profile_dir / "static-profile.json", static_profile)
    dependency_profiles: List[Dict[str, Any]] = []
    for index, child_path in enumerate(package.get("childViewPaths", [])):
        child_record = client.call(
            f"{args.run_id}-{package['variant']}-profile-child-viewRead-{index}",
            view_read_payload(f"{args.run_id}-{package['variant']}-profile-child-viewRead-{index}", project, child_path, args),
        )
        child_response = cp.response(child_record)
        dependency_profiles.append(
            {
                "viewPath": child_path,
                "viewRead": child_response,
                "staticProfile": profile_view(child_response, f"dependency-view-read-{index}.json"),
            }
        )
    if dependency_profiles:
        write_json(profile_dir / "dependency-static-profiles.json", dependency_profiles)
    browser_url = common.browser_url_from_endpoint(client.endpoint, project, package["route"])
    browser_info = start_browser_probe(args, package, browser_url, profile_dir)
    marker_ok = wait_for_marker(Path(str(browser_info["markerPath"])), browser_info["process"], args.browser_timeout_sec)
    window = {"sampleCount": 0, "metricTokenCount": 0, "metricsListOk": False, "missingEvidence": [{"name": "backgroundHold", "reason": "Browser did not reach background hold marker"}]}
    if marker_ok:
        window = collect_profile_window(client, args, profile_dir, project, f"{args.run_id}-{package['variant']}", feature_set)
    browser_result = finish_browser_probe(browser_info, max(args.browser_timeout_sec, args.background_hold_ms / 1000.0 + 10))
    log_record = client.call(
        f"{args.run_id}-{package['variant']}-logQuery",
        {"action": "logQuery", "requestId": f"{args.run_id}-{package['variant']}-logQuery", "sinceMinutes": 10, "levels": ["ERROR", "WARN"], "textContains": "Perspective", "maxResults": 50, "tailBytes": 262144},
    )
    write_json(profile_dir / "logs.json", cp.response(log_record))
    write_json(profile_dir / "thread-excerpts.json", {"ok": False, "missing": True, "reason": "No active freeze/backlog/CPU-spike trigger requested"})
    write_json(profile_dir / "comparison.json", {"ok": False, "missing": True, "reason": "No pair comparison in single variant profile"})
    write_profile_manifest(profile_dir, args, package, health, feature_set, view_response, static_profile, window, browser_result)
    summary = {
        "ok": marker_ok and browser_result.get("exitCode") == 0 and not read_json(profile_dir / "manifest.json").get("missingEvidence"),
        "runId": f"{args.run_id}-tab-rwh-{package['variant']}",
        "variant": package["variant"],
        "runWhileHidden": package["runWhileHidden"],
        "sampleCount": window.get("sampleCount"),
        "metricTokenCount": window.get("metricTokenCount"),
        "browserProbe": browser_result,
    }
    write_json(profile_dir / "summary.json", summary)
    return summary


def compare_profiles(out_dir: Path, control_dir: Path, target_dir: Path) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparison-persist-minus-unload"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(control_dir), "--target-dir", str(target_dir), "--out-dir", str(comparison_dir)]
    result = common.run_command(cmd, "compare-persist-minus-unload", out_dir, 180)
    return {"ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}


def compare_metric_summaries(variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_name = {str(row.get("variant")): row for row in variants}

    def metric_delta(variant: str, key: str) -> Optional[float]:
        metrics = by_name.get(variant, {}).get("metricSummary", {})
        if not isinstance(metrics, dict):
            return None
        return to_float(metrics.get(key))

    unload_expr = metric_delta("unload-hidden", "primaryPerspectiveExpressionsDelta")
    persist_expr = metric_delta("persist-hidden", "primaryPerspectiveExpressionsDelta")
    unload_prop = metric_delta("unload-hidden", "primaryPerspectivePropertyChangesDelta")
    persist_prop = metric_delta("persist-hidden", "primaryPerspectivePropertyChangesDelta")
    return {
        "unloadExpressionsDelta": unload_expr,
        "persistExpressionsDelta": persist_expr,
        "persistMinusUnloadExpressionsDelta": (persist_expr - unload_expr) if persist_expr is not None and unload_expr is not None else None,
        "unloadPropertyChangesDelta": unload_prop,
        "persistPropertyChangesDelta": persist_prop,
        "persistMinusUnloadPropertyChangesDelta": (persist_prop - unload_prop) if persist_prop is not None and unload_prop is not None else None,
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Tab Container runWhileHidden A/B Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        f"Content mode: `{summary.get('contentMode', 'direct')}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | Mode | runWhileHidden | OK | Browser | Samples | Expressions delta | Property changes delta | DOM | Child views | Cleanup |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        browser = row.get("browser", {}) if isinstance(row.get("browser"), dict) else {}
        metrics = row.get("metricSummary", {}) if isinstance(row.get("metricSummary"), dict) else {}
        baseline = row.get("baselineWait", {}) if isinstance(row.get("baselineWait"), dict) else {}
        cleanup_ok = row.get("rollbackOk") and row.get("cleanupRouteAbsent") and row.get("cleanupViewAbsent")
        baseline_note = ""
        if baseline.get("enabled"):
            baseline_note = f"; baseline {'clean' if baseline.get('ok') else 'timeout'} ({baseline.get('finalBrowserSessions')})"
        lines.append(
            "| {variant} | `{mode}` | `{rwh}` | `{ok}` | `{browser_ok}` | {samples} | {expr} | {prop} | {dom} | {child_views} | `{cleanup}` |".format(
                variant=f"{row.get('variant')}{baseline_note}",
                mode=row.get("contentMode", summary.get("contentMode", "direct")),
                rwh=str(row.get("runWhileHidden")).lower(),
                ok=str(row.get("ok", False)).lower(),
                browser_ok=str(browser.get("ok", False)).lower(),
                samples=metrics.get("sampleCount"),
                expr=metrics.get("primaryPerspectiveExpressionsDelta"),
                prop=metrics.get("primaryPerspectivePropertyChangesDelta"),
                dom=browser.get("domNodeCount"),
                child_views=len(row.get("childViewPaths", [])) if isinstance(row.get("childViewPaths"), list) else 0,
                cleanup=str(bool(cleanup_ok)).lower(),
            )
        )
    lines.extend(["", "## Background Window Comparison", ""])
    for key, value in summary.get("metricComparison", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def parse_variants(raw: str) -> List[str]:
    variants: List[str] = []
    for part in raw.split(","):
        variant = part.strip()
        if not variant:
            continue
        if variant not in VARIANTS:
            raise ValueError(f"Unsupported variant {variant!r}; expected one of {', '.join(VARIANTS)}")
        variants.append(variant)
    return list(dict.fromkeys(variants))


def run(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = cp.resolve_config(args)
    args.project = project
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    variants_to_run = parse_variants(args.variants)
    base = compact(args.run_id)
    health_record = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health = cp.response(health_record)
    feature_set = cp.enabled_name_set(health.get("features", []))
    action_set = cp.enabled_name_set(health.get("supportedActions", []))
    baseline_capability_set = feature_set | action_set if action_set else feature_set
    variants: List[Dict[str, Any]] = []
    packages: List[Dict[str, Any]] = []

    for variant_name in variants_to_run:
        variant_dir = out_dir / variant_name
        variant_dir.mkdir(parents=True, exist_ok=True)
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        variant_suffix = "".join(part.title() for part in variant_name.split("-"))
        view_base = f"{args.view_path_prefix.rstrip('/')}/{base}"
        view_path = f"{view_base}/TabRunWhileHidden{variant_suffix}"
        control_child_view_path = f"{view_base}/TabRunWhileHidden{variant_suffix}ControlChild" if args.content_mode == "viewpath" else ""
        work_child_view_path = f"{view_base}/TabRunWhileHidden{variant_suffix}WorkChild" if args.content_mode == "viewpath" else ""
        package = build_package(
            variant_dir,
            project,
            args.run_id,
            variant_name,
            view_path,
            route,
            args.work_labels,
            args.expression_rate_ms,
            args.content_mode,
            control_child_view_path,
            work_child_view_path,
        )
        packages.append({key: value for key, value in package.items() if key != "packageBase64"})
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
                    variant_name,
                    baseline_capability_set,
                    args.baseline_max_browser_sessions,
                    args.baseline_wait_timeout_sec,
                    args.baseline_wait_interval_sec,
                )
                write_json(variant_dir / "baseline-wait.json", baseline_wait)
                gates["cleanBaseline"] = bool(baseline_wait.get("ok"))
                if args.fail_on_baseline_timeout and not baseline_wait.get("ok"):
                    raise RuntimeError("clean baseline was not reached before timeout")
            dry = client.call(f"{args.run_id}-{variant_name}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant_name}-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry)
            if not gates["dryRun"]:
                raise RuntimeError("dryRun failed")
            apply = client.call(f"{args.run_id}-{variant_name}-apply", package_payload("apply", f"{args.run_id}-{variant_name}-apply", project, package, args), timeout=args.timeout_sec)
            backup_name = common.backup_name_from_response(cp.response(apply))
            gates["apply"] = cp.ok(apply) and bool(backup_name)
            if not gates["apply"]:
                raise RuntimeError("apply failed")
            time.sleep(2)
            readback = client.call(f"{args.run_id}-{variant_name}-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, view_path, args))
            gates["viewRead"] = cp.ok(readback) and readback_ok(readback, package)
            child_readbacks: Dict[str, bool] = {}
            for index, child_path in enumerate(package.get("childViewPaths", [])):
                child_record = client.call(
                    f"{args.run_id}-{variant_name}-child-viewRead-{index}",
                    view_read_payload(f"{args.run_id}-{variant_name}-child-viewRead-{index}", project, child_path, args),
                )
                child_readbacks[child_path] = child_readback_ok(child_record, package, child_path)
            if package.get("childViewPaths"):
                gates["childViewRead"] = bool(child_readbacks) and all(child_readbacks.values())
            page = client.call(f"{args.run_id}-{variant_name}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            profile_dir = variant_dir / "profile"
            profile_result = profile_variant(client, args, project, package, profile_dir, health, feature_set)
            gates["profile"] = bool(profile_result.get("ok"))
            variant = {
                "variant": variant_name,
                "runWhileHidden": package["runWhileHidden"],
                "contentMode": package["contentMode"],
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "childViewPaths": package.get("childViewPaths", []),
                "childReadbacks": child_readbacks,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "profileDir": str(profile_dir),
                "profileSummary": profile_result,
                "metricSummary": summarize_metric_counts(profile_dir),
                "static": static_summary(profile_dir),
                "browser": browser_summary(profile_dir),
                "gateway": gateway_summary(profile_dir),
            }
        except Exception as exc:
            variant = {
                "variant": variant_name,
                "runWhileHidden": package["runWhileHidden"],
                "contentMode": package["contentMode"],
                "ok": False,
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "childViewPaths": package.get("childViewPaths", []),
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                rb_dry = client.call(f"{args.run_id}-{variant_name}-rollback-dryRun", rollback_payload(f"{args.run_id}-{variant_name}-rollback-dryRun", project, backup_name, package["viewPaths"], True), timeout=args.timeout_sec)
                rb_apply = client.call(f"{args.run_id}-{variant_name}-rollback-apply", rollback_payload(f"{args.run_id}-{variant_name}-rollback-apply", project, backup_name, package["viewPaths"], False), timeout=args.timeout_sec)
                time.sleep(2)
                routes_check = client.call(
                    f"{args.run_id}-{variant_name}-post-cleanup-routesList",
                    {"action": "routesList", "requestId": f"{args.run_id}-{variant_name}-post-cleanup-routesList", "targetProject": project, "routePrefix": route, "maxResults": 25},
                )
                routes = cp.response(routes_check).get("routes", [])
                routes_list = routes if isinstance(routes, list) else []
                route_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes_list)
                cleanup_views: Dict[str, bool] = {}
                for index, cleanup_view_path in enumerate(package["viewPaths"]):
                    after_read = client.call(
                        f"{args.run_id}-{variant_name}-post-cleanup-viewRead-{index}",
                        view_read_payload(f"{args.run_id}-{variant_name}-post-cleanup-viewRead-{index}", project, cleanup_view_path, args),
                    )
                    cleanup_views[cleanup_view_path] = not cp.ok(after_read)
                variant["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                variant["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_present
                variant["cleanupViewsAbsent"] = cleanup_views
                variant["cleanupViewAbsent"] = bool(cleanup_views) and all(cleanup_views.values())
                variant["ok"] = bool(variant.get("ok") and variant["rollbackOk"] and variant["cleanupRouteAbsent"] and variant["cleanupViewAbsent"])
            variants.append(variant)
            if args.pause_sec > 0 and variant_name != variants_to_run[-1]:
                time.sleep(args.pause_sec)

    comparison: Dict[str, Any] = {"ok": False, "reason": "Both variants did not produce profile directories"}
    unload_profile = next((Path(row["profileDir"]) for row in variants if row.get("variant") == "unload-hidden" and row.get("profileDir")), None)
    persist_profile = next((Path(row["profileDir"]) for row in variants if row.get("variant") == "persist-hidden" and row.get("profileDir")), None)
    if unload_profile and persist_profile and unload_profile.exists() and persist_profile.exists():
        comparison = compare_profiles(out_dir, unload_profile, persist_profile)

    metric_comparison = compare_metric_summaries(variants)
    summary = {
        "ok": bool(cp.ok(health_record) and variants and all(row.get("ok") for row in variants) and comparison.get("ok")),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": health.get("runnerVersion"),
        "stackVersion": health.get("stackVersion"),
        "features": sorted(feature_set),
        "contentMode": args.content_mode,
        "workLabels": args.work_labels,
        "expressionRateMs": args.expression_rate_ms,
        "backgroundHoldMs": args.background_hold_ms,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparison": comparison,
        "metricComparison": metric_comparison,
        "packages": packages,
        "officialSource": OFFICIAL_SOURCE,
        "interpretation": [
            "This is a controlled A-09 Tab Container runWhileHidden fixture, not a customer route conclusion.",
            f"The fixture content mode is {args.content_mode}; viewpath mode verifies parent and child views separately before runtime profiling.",
            "The browser activates the work tab once, switches back to the control tab, and Gateway metrics are sampled during the background hold window.",
            "Use clean-baseline waiting for sequential variants so retained browser sessions do not contaminate background-work deltas.",
            "Treat runWhileHidden=false versus true as a hypothesis: compare retained browser content and Gateway work separately after the inactive-tab switch.",
            "Treat one fixture pass as mechanics and signal evidence only. Repeat clean-baseline pairs before making a causal remediation recommendation.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "packages.json", packages)
    write_report(out_dir, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--variants", default="unload-hidden,persist-hidden")
    parser.add_argument("--content-mode", choices=CONTENT_MODES, default="direct", help="Use direct tab child containers or tab props.tabs[].viewPath child views.")
    parser.add_argument("--work-labels", type=int, default=80)
    parser.add_argument("--expression-rate-ms", type=int, default=250)
    parser.add_argument("--background-hold-ms", type=int, default=15000)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=40)
    parser.add_argument("--metric-name-contains", action="append", default=["Perspective", "perspective"], help="Metric substring filter for background samples. Repeatable.")
    parser.add_argument("--metric-prefix", action="append", default=[])
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-node", default="node")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-settle-ms", type=int, default=600)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--pause-sec", type=float, default=5.0)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each variant, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for clean baseline per variant.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between baseline wait samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Mark the variant failed before import when the requested clean baseline is not reached.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.work_labels < 1:
        raise SystemExit("--work-labels must be >= 1")
    if args.expression_rate_ms < 100:
        raise SystemExit("--expression-rate-ms must be >= 100")
    if args.background_hold_ms < 1000:
        raise SystemExit("--background-hold-ms must be >= 1000")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
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
