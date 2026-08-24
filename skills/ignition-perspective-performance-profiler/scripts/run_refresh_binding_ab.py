#!/usr/bin/env python3
"""Run guarded Perspective query polling versus refreshBinding() fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_hidden_content_ab as hidden_common
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
DEFAULT_ALLOWED_NAMED_QUERY_PREFIX = "LLM Tests/"


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


def component(
    component_type: str,
    *,
    meta: Dict[str, Any] | None = None,
    props: Dict[str, Any] | None = None,
    position: Dict[str, Any] | None = None,
    prop_config: Dict[str, Any] | None = None,
    events: Dict[str, Any] | None = None,
    children: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {"type": component_type}
    if events is not None:
        row["events"] = events
    if meta is not None:
        row["meta"] = meta
    if position is not None:
        row["position"] = position
    if prop_config is not None:
        row["propConfig"] = prop_config
    if props is not None:
        row["props"] = props
    if children is not None:
        row["children"] = children
    return row


def property_binding(path: str, transform_code: str = "") -> Dict[str, Any]:
    binding: Dict[str, Any] = {"type": "property", "config": {"path": path}}
    if transform_code:
        binding["transforms"] = [{"type": "script", "code": transform_code}]
    return {"binding": binding}


def tick_transform(prefix: str) -> str:
    return (
        "\ttry:\n"
        "\t\tif value is not None and hasattr(value, 'getRowCount') and value.getRowCount() > 0:\n"
        f"\t\t\treturn '{prefix}: ' + str(value.getValueAt(0, 'refresh_tick'))\n"
        "\t\tif value is not None and hasattr(value, '__len__') and len(value) > 0:\n"
        f"\t\t\treturn '{prefix}: ' + str(value[0].get('refresh_tick'))\n"
        "\texcept Exception as err:\n"
        f"\t\treturn '{prefix} error: ' + str(err)\n"
        f"\treturn '{prefix}: <none>'\n"
    )


def query_binding(query_path: str, polling_enabled: bool, polling_rate_sec: int, prefix: str) -> Dict[str, Any]:
    return {
        "binding": {
            "type": "query",
            "config": {
                "parameters": {},
                "polling": {"enabled": polling_enabled, "rate": str(polling_rate_sec)},
                "queryPath": query_path,
            },
            "transforms": [{"type": "script", "code": tick_transform(prefix)}],
        }
    }


def make_tick_label(index: int, variant: str, query_path: str, polling_enabled: bool, polling_rate_sec: int) -> Dict[str, Any]:
    title = "Polling" if variant == "polling" else "Manual"
    prefix = f"{title} tick {index:03d}"
    return component(
        "ia.display.label",
        meta={"name": f"TickLabel{index:03d}"},
        position={"basis": "30px", "grow": 0, "shrink": 0},
        props={
            "text": f"{prefix}: pending",
            "style": {
                "backgroundColor": "#ffffff",
                "borderColor": "#cbd5e1",
                "borderRadius": 4,
                "borderStyle": "solid",
                "borderWidth": "1px",
                "color": "#111827",
                "fontSize": 12,
                "overflow": "hidden",
                "padding": "6px 8px",
                "textOverflow": "ellipsis",
                "whiteSpace": "nowrap",
            },
        },
        prop_config={"props.text": query_binding(query_path, polling_enabled, polling_rate_sec, prefix)},
    )


def refresh_button_script(variant: str, query_count: int) -> str:
    lines = [
        "\ttry:",
        "\t\tclicks = int(self.view.custom.refreshClicks)",
        "\texcept:",
        "\t\tclicks = 0",
        "\tself.view.custom.refreshClicks = clicks + 1",
    ]
    if variant == "manual":
        lines.extend(
            [
                "\tfor name in [",
                *[f"\t\t'TickLabel{index:03d}'," for index in range(1, query_count + 1)],
                "\t]:",
                "\t\ttry:",
                "\t\t\tself.getSibling(name).refreshBinding('props.text')",
                "\t\texcept Exception as err:",
                "\t\t\tself.view.custom.lastRefreshError = str(err)",
            ]
        )
    else:
        lines.append("\tself.view.custom.lastRefreshError = ''")
    return "\n".join(lines) + "\n"


def make_view_json(run_id: str, variant: str, query_path: str, query_count: int, polling_rate_sec: int) -> Dict[str, Any]:
    title = "Polling" if variant == "polling" else "Manual"
    marker = f"{run_id} {variant.upper()} READY"
    polling_enabled = variant == "polling"
    children: List[Dict[str, Any]] = [
        component(
            "ia.display.label",
            meta={"name": "Ready Marker"},
            position={"basis": "40px", "grow": 0, "shrink": 0},
            props={
                "text": marker,
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
            meta={"name": "Fixture Summary"},
            position={"basis": "38px", "grow": 0, "shrink": 0},
            props={
                "text": (
                    f"A-03 query fixture: {query_count} query-bound labels, "
                    f"{'polling every ' + str(polling_rate_sec) + 's' if polling_enabled else 'polling disabled; button refreshBinding()'}"
                ),
                "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
            },
        ),
        component(
            "ia.input.button",
            meta={"name": "RefreshButton"},
            position={"basis": "46px", "grow": 0, "shrink": 0},
            props={
                "primary": variant == "manual",
                "style": {
                    "alignSelf": "flex-start",
                    "fontSize": 14,
                    "fontWeight": "700",
                    "marginBottom": "4px",
                    "maxWidth": "220px",
                },
                "text": "Manual refresh" if variant == "manual" else "Polling control",
            },
            events={
                "component": {
                    "onActionPerformed": {
                        "scope": "G",
                        "type": "script",
                        "config": {"script": refresh_button_script(variant, query_count)},
                    }
                }
            },
        ),
        component(
            "ia.display.label",
            meta={"name": "ClickCount"},
            position={"basis": "32px", "grow": 0, "shrink": 0},
            props={
                "text": "Refresh clicks: 0",
                "style": {"color": "#1f2937", "fontSize": 12, "overflow": "hidden", "padding": "6px 8px", "whiteSpace": "nowrap"},
            },
            prop_config={"props.text": property_binding("view.custom.refreshClicks", "\treturn 'Refresh clicks: ' + str(value)\n")},
        ),
    ]
    children.extend(make_tick_label(index, variant, query_path, polling_enabled, polling_rate_sec) for index in range(1, query_count + 1))
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "queryCount": query_count,
            "pollingEnabled": polling_enabled,
            "pollingRateSec": polling_rate_sec if polling_enabled else None,
            "refreshClicks": 0,
            "lastRefreshError": "",
            "remediationCandidate": "Disable continuous polling and call refreshBinding() from bounded user events when data freshness allows it.",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "refresh-binding-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {"backgroundColor": "#f8fafc", "overflow": "hidden", "padding": "12px"},
            },
            children=children,
        ),
        "permissions": {},
    }


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-refresh-binding-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def named_query_resource(actor: str, database: str) -> Dict[str, Any]:
    timestamp = utc_now()
    return {
        "attributes": {
            "autoBatchEnabled": False,
            "cacheAmount": 1,
            "cacheEnabled": False,
            "cacheUnit": "SEC",
            "database": database,
            "enabled": True,
            "fallbackEnabled": False,
            "fallbackValue": "",
            "lastModification": {"actor": actor, "timestamp": timestamp},
            "maxReturnSize": 100,
            "parameters": [],
            "permissions": [{"role": "", "zone": ""}],
            "type": "Query",
            "useMaxReturnSize": False,
        },
        "files": ["query.sql"],
        "overridable": True,
        "restricted": False,
        "scope": "DG",
        "version": 2,
    }


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", fixture_common.resource_json(actor, ["view.json"]))


def write_named_query(project_root: Path, query_path: str, query_sql: str, database: str, actor: str) -> None:
    query_dir = project_root / "ignition" / "named-query" / Path(*query_path.split("/"))
    query_dir.mkdir(parents=True, exist_ok=True)
    (query_dir / "query.sql").write_text(query_sql, encoding="utf-8", newline="\n")
    write_json(query_dir / "resource.json", named_query_resource(actor, database))


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    view_path: str,
    route: str,
    query_path: str,
    database: str,
    query_count: int,
    polling_rate_sec: int,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-refresh-binding"
    view_json = make_view_json(run_id, variant, query_path, query_count, polling_rate_sec)
    query_sql = "SELECT strftime('%Y%m%dT%H%M%f','now') || '-' || hex(randomblob(4)) AS refresh_tick LIMIT 1"
    zip_path = zip_dir / f"{slug(run_id)}-refresh-binding-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-refresh-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler refreshBinding fixture", "enabled": True, "inheritable": False})
        write_view(project_root, view_path, view_json, actor)
        write_named_query(project_root, query_path, query_sql, database, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Refresh Binding {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    title = "Polling" if variant == "polling" else "Manual"
    return {
        "variant": variant,
        "queryCount": query_count,
        "pollingRateSec": polling_rate_sec if variant == "polling" else None,
        "viewPath": view_path,
        "route": route,
        "queryPath": query_path,
        "database": database,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "querySqlSha256": sha256_text(query_sql),
        "readyText": f"{run_id} {variant.upper()} READY",
        "secondaryReadyText": f"{title} tick 001:",
        "watchTextRegex": rf"{title} tick 001:\s*([^\s]+)",
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
        "allowedNamedQueryPrefix": args.allowed_named_query_prefix,
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Refresh Binding {package['variant']}"}],
        "dependencyViewPaths": [],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [package["queryPath"]],
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
        "dependencyNamedQueryPaths": [package["queryPath"]],
    }


def view_read_payload(request_id: str, project: str, view_path: str, args: argparse.Namespace) -> Dict[str, Any]:
    return common.view_read_payload(request_id, project, view_path, args)


def named_query_read_payload(request_id: str, project: str, query_path: str, args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "action": "namedQueryRead",
        "requestId": request_id,
        "targetProject": project,
        "queryPath": query_path,
        "namedQueryPrefix": args.allowed_named_query_prefix,
    }


def named_query_preview_payload(request_id: str, project: str, query_path: str, args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "action": "namedQueryPreview",
        "requestId": request_id,
        "targetProject": project,
        "queryPath": query_path,
        "namedQueryPrefix": args.allowed_named_query_prefix,
        "parameters": {},
        "maxRows": 5,
    }


def rollback_payload(request_id: str, project: str, backup_name: str, package: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "rollback",
        "requestId": request_id,
        "targetProject": project,
        "backupName": backup_name,
        "viewPaths": [package["viewPath"]],
        "scriptPaths": [],
        "namedQueryPaths": [package["queryPath"]],
        "dryRun": dry_run,
        "removeMissingViews": True,
        "removeMissingScripts": False,
        "removeMissingNamedQueries": True,
    }
    if not dry_run:
        payload["confirmRollback"] = "ROLLBACK"
    return payload


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    duration_ms = int(max(args.profile_duration_sec + args.interval_sec, 1.0) * 1000)
    variant = str(package["variant"])
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        f"{args.run_id}-refresh-binding-{variant}",
        "--project",
        project,
        "--route",
        package["route"],
        "--view",
        package["viewPath"],
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
        f"query {variant} refreshBinding fixture",
        "--browser-url",
        browser_url,
        "--browser-url-alias",
        args.browser_url_alias,
        "--browser-ready-selector",
        args.browser_ready_selector,
        "--browser-ready-text",
        package["readyText"],
        "--browser-secondary-ready-text",
        package["secondaryReadyText"],
        "--browser-timeout-sec",
        str(args.browser_timeout_sec),
        "--browser-viewport",
        args.browser_viewport,
    ]
    for prefix in args.metric_prefix or []:
        command.extend(["--metric-prefix", prefix])
    for contains in args.metric_name_contains or []:
        command.extend(["--metric-name-contains", contains])
    if variant == "manual":
        click_delay_ms = min(max(args.manual_click_delay_ms, 0), max(duration_ms - 1000, 0))
        post_wait_ms = max(duration_ms - click_delay_ms, 0)
        command.extend(
            [
                "--browser-wait-after-ready-ms",
                str(click_delay_ms),
                "--browser-click-selector",
                "button",
                "--browser-click-text",
                "Manual refresh",
                "--browser-click-label",
                "manual refreshBinding",
                "--browser-click-result-text",
                "Refresh clicks: 1",
                "--browser-click-timeout-sec",
                str(args.browser_click_timeout_sec),
                "--browser-post-interaction-wait-ms",
                str(post_wait_ms),
                "--browser-watch-text-selector",
                "body",
                "--browser-watch-text-regex",
                package["watchTextRegex"],
                "--browser-watch-text-label",
                "TickLabel001",
                "--browser-watch-text-timeout-sec",
                str(args.browser_click_timeout_sec),
            ]
        )
    else:
        command.extend(["--browser-wait-after-ready-ms", str(duration_ms)])
    if args.browser_node_modules:
        command.extend(["--browser-node-modules", args.browser_node_modules])
    return command


def profile_ok(profile_dir: Path) -> bool:
    return hidden_common.profile_ok(profile_dir)


def feature_set_from_health(health: Dict[str, Any]) -> set[str]:
    features = cp.response(health).get("features", [])
    if isinstance(features, dict):
        return {str(key) for key, value in features.items() if value}
    if isinstance(features, list):
        return {str(item) for item in features}
    return set()


def to_float(value: Any) -> float | None:
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
            "reason": "perspectiveSessionsQuery feature not present",
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


def choose_database(record: Dict[str, Any], requested: str) -> str:
    if requested:
        return requested
    connections = cp.response(record).get("connections", [])
    if isinstance(connections, list):
        for connection in connections:
            if not isinstance(connection, dict):
                continue
            if str(connection.get("status", "")).lower() == "valid" and connection.get("name"):
                return str(connection["name"])
        for connection in connections:
            if isinstance(connection, dict) and connection.get("name"):
                return str(connection["name"])
    return ""


def readback_ok(record: Dict[str, Any], package: Dict[str, Any], query_count: int) -> bool:
    text = canonical_json(cp.response(record))
    variant = str(package["variant"])
    expected_polling = '"enabled":true' if variant == "polling" else '"enabled":false'
    manual_refresh_present = variant != "manual" or "refreshBinding" in text
    return (
        package["queryPath"] in text
        and expected_polling in text
        and text.count('"type":"query"') >= query_count
        and manual_refresh_present
    )


def browser_refresh_proof(profile_dir: Path) -> Dict[str, Any]:
    data = read_json(profile_dir / "browser-summary.json")
    interaction = data.get("interaction", {}) if isinstance(data.get("interaction"), dict) else {}
    watch = interaction.get("watchText", {}) if isinstance(interaction.get("watchText"), dict) else {}
    return {
        "configured": bool(interaction.get("configured")),
        "ok": interaction.get("ok"),
        "resultAlreadyMatchedBeforeClick": interaction.get("resultAlreadyMatchedBeforeClick"),
        "clickElapsedMs": interaction.get("clickElapsedMs"),
        "resultElapsedMs": interaction.get("resultElapsedMs"),
        "watchedTextChanged": watch.get("changed"),
        "watchedTextBefore": (watch.get("before") or {}).get("value") if isinstance(watch.get("before"), dict) else None,
        "watchedTextAfter": (watch.get("after") or {}).get("value") if isinstance(watch.get("after"), dict) else None,
    }


def compare_profiles(out_dir: Path, manual_dir: Path, polling_dir: Path) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparison-polling-minus-manual"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(manual_dir), "--target-dir", str(polling_dir), "--out-dir", str(comparison_dir)]
    result = common.run_command(cmd, "compare-polling-minus-manual", out_dir, 180)
    return {"ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}


def comparison_primary(comparison_dir: Path) -> Dict[str, Any]:
    data = read_json(comparison_dir / "comparison.json")
    browser = data.get("browserDeltas", {}) if isinstance(data.get("browserDeltas"), dict) else {}
    static = data.get("staticDeltas", {}) if isinstance(data.get("staticDeltas"), dict) else {}
    gateway = data.get("gatewayDeltas", {}) if isinstance(data.get("gatewayDeltas"), dict) else {}

    def delta(bucket: Dict[str, Any], key: str) -> Any:
        row = bucket.get(key)
        return row.get("delta") if isinstance(row, dict) else None

    return {
        "componentCountDelta": delta(static, "componentCount"),
        "bindingCountDelta": delta(static, "bindingCount"),
        "largestContentfulPaintMsDelta": delta(browser, "largestContentfulPaintMs"),
        "longTaskTotalMsDelta": delta(browser, "longTaskTotalMs"),
        "domNodeCountDelta": delta(browser, "domNodeCount"),
        "usedJSHeapBytesDelta": delta(browser, "usedJSHeapBytes"),
        "processCpuLoadAvgDelta": delta(gateway, "processCpuLoad"),
        "heapUsedBytesAvgDelta": delta(gateway, "heapUsedBytes"),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Query Polling vs refreshBinding Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Evidence grade: `{summary.get('evidenceGrade', 'Observed')}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        "",
        "## Direct Observations",
        "",
        "- The helper applied disposable manual and polling query-binding fixtures, read the views and Named Queries back, validated each route, captured synchronized profiles, then rolled the fixtures back.",
        "- Both variants use the same visible query-bound label count and the same read-only Named Query SQL shape.",
        "- The manual variant records browser click proof that `refreshBinding()` changed the watched query label after the event.",
        "- Cleanup status is recorded per variant so retained disposable route, view, or Named Query resources are visible evidence failures.",
        "",
        "## Variant Summary",
        "",
        "| Variant | Baseline | OK | Components | Bindings | DOM | DB queries delta | Fetches delta | WS recv | Long task ms | CPU median | Manual proof | Cleanup |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary.get("variants", []):
        browser = row.get("browser", {})
        static = row.get("static", {})
        gateway = row.get("gateway", {})
        baseline = row.get("baselineWait", {})
        network = row.get("network", {})
        query_metrics = row.get("queryMetrics", {})
        proof = row.get("manualRefreshProof", {})
        if baseline.get("enabled"):
            baseline_text = "clean" if baseline.get("ok") else "timeout"
            baseline_text += f" ({baseline.get('finalBrowserSessions')})"
        else:
            baseline_text = "not requested"
        manual_proof = "n/a"
        if row.get("variant") == "manual":
            manual_proof = f"click={proof.get('ok')} changed={proof.get('watchedTextChanged')}"
        lines.append(
            "| {variant} | {baseline} | `{ok}` | {components} | {bindings} | {dom} | {db_queries} | {fetches} | {ws_recv} | {long_task} | {cpu} | {proof} | `{cleanup}` |".format(
                variant=row.get("variant"),
                baseline=baseline_text,
                ok=str(row.get("ok", False)).lower(),
                components=static.get("componentCount"),
                bindings=static.get("bindingCount"),
                dom=browser.get("domNodeCount"),
                db_queries=query_metrics.get("databaseQueriesDelta"),
                fetches=query_metrics.get("perspectiveFetchesDelta"),
                ws_recv=network.get("webSocketFramesReceived"),
                long_task=browser.get("longTaskTotalMs"),
                cpu=gateway.get("processCpuLoadMedian"),
                proof=manual_proof,
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewAbsent", False) and row.get("cleanupNamedQueryAbsent", False)).lower(),
            )
        )
    lines.extend(["", "## Comparison", ""])
    comparison = summary.get("comparison", {})
    lines.append(f"Polling minus manual comparison OK: `{comparison.get('ok')}`")
    for key, value in summary.get("comparisonPrimary", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Unproven Limits",
            "",
            "- This fixture is observed local mechanics, not proof of a customer freshness requirement or final diagnosis.",
            "- Single-run Gateway and browser deltas are not proof that polling should be disabled on every route.",
            "- Repeat clean-baseline paired runs on the target route before promoting event-driven refresh as causal remediation.",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_manifest(out_dir: Path, summary: Dict[str, Any]) -> None:
    files = ["summary.json", "summary.md", "packages.json", "api/"]
    for row in summary.get("variants", []):
        variant = row.get("variant")
        if variant:
            files.append(f"{variant}/")
    comparison = summary.get("comparison", {})
    if comparison.get("comparisonDir"):
        files.append("comparison-polling-minus-manual/")
    manifest = {
        "runId": summary.get("runId"),
        "scenario": "query polling versus refreshBinding fixture",
        "evidenceGrade": summary.get("evidenceGrade", "Observed"),
        "createdAt": summary.get("createdAt"),
        "project": summary.get("project"),
        "gatewayAlias": summary.get("gatewayAlias"),
        "runnerVersion": summary.get("runnerVersion"),
        "stackVersion": summary.get("stackVersion"),
        "variantCount": len(summary.get("variants", [])),
        "queryCount": summary.get("queryCount"),
        "pollingRateSec": summary.get("pollingRateSec"),
        "metricPrefixes": summary.get("metricPrefixes", []),
        "metricNameContains": summary.get("metricNameContains", []),
        "changedResources": [],
        "missingEvidence": [],
        "files": files,
    }
    write_json(out_dir / "manifest.json", manifest)


def network_summary(profile_dir: Path) -> Dict[str, Any]:
    data = read_json(profile_dir / "network-summary.json")
    return {
        "requestCount": data.get("requestCount"),
        "webSocketCount": data.get("webSocketCount"),
        "webSocketFramesSent": data.get("webSocketFramesSent"),
        "webSocketFramesReceived": data.get("webSocketFramesReceived"),
        "webSocketBytesSent": data.get("webSocketBytesSent"),
        "webSocketBytesReceived": data.get("webSocketBytesReceived"),
    }


def metric_count_delta(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"first": None, "last": None, "delta": None}
    return {"first": values[0], "last": values[-1], "delta": values[-1] - values[0]}


def query_metric_summary(profile_dir: Path) -> Dict[str, Any]:
    samples_path = profile_dir / "gateway-samples.ndjson"
    database_queries: List[float] = []
    database_token_queries: List[float] = []
    perspective_fetches: List[float] = []
    if not samples_path.exists():
        return {
            "sampleCount": 0,
            "databaseQueriesDelta": None,
            "databaseTokenQueriesDelta": None,
            "perspectiveFetchesDelta": None,
        }
    for line in samples_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        snapshot = row.get("metricsSnapshot", {}) if isinstance(row, dict) else {}
        metrics = snapshot.get("metrics", []) if isinstance(snapshot, dict) else []
        if not isinstance(metrics, list):
            continue
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            count = metric.get("count")
            if count is None:
                continue
            try:
                value = float(count)
            except (TypeError, ValueError):
                continue
            name = str(metric.get("name", ""))
            if name == "databases.queries":
                database_queries.append(value)
            elif name == "databases.<token>.queries":
                database_token_queries.append(value)
            elif name == "perspective.fetches":
                perspective_fetches.append(value)
    database = metric_count_delta(database_queries)
    database_token = metric_count_delta(database_token_queries)
    fetches = metric_count_delta(perspective_fetches)
    return {
        "sampleCount": max(len(database_queries), len(database_token_queries), len(perspective_fetches)),
        "databaseQueriesFirst": database["first"],
        "databaseQueriesLast": database["last"],
        "databaseQueriesDelta": database["delta"],
        "databaseTokenQueriesFirst": database_token["first"],
        "databaseTokenQueriesLast": database_token["last"],
        "databaseTokenQueriesDelta": database_token["delta"],
        "perspectiveFetchesFirst": fetches["first"],
        "perspectiveFetchesLast": fetches["last"],
        "perspectiveFetchesDelta": fetches["delta"],
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    env = common.collect_env(endpoint, token, project)
    base = compact(args.run_id)
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    feature_set = feature_set_from_health(health)
    db_record = client.call(f"{args.run_id}-databaseConnectionsList", {"action": "databaseConnectionsList", "requestId": f"{args.run_id}-databaseConnectionsList"})
    database = choose_database(db_record, args.database)
    if not database:
        raise RuntimeError("No database connection available for disposable Named Query fixture")

    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    for variant_name in ["manual", "polling"]:
        variant_dir = out_dir / variant_name
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/RefreshBinding{variant_name.title()}"
        query_path = f"{args.named_query_path_prefix.rstrip('/')}/{base}/{variant_name.title()}Tick"
        package = build_package(variant_dir, project, args.run_id, variant_name, view_path, route, query_path, database, args.query_count, args.polling_rate_sec)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        backup_name = ""
        gates: Dict[str, bool] = {}
        baseline_wait: Dict[str, Any] = {"enabled": False}
        try:
            if args.wait_for_clean_baseline:
                baseline_wait = wait_for_clean_baseline(
                    client,
                    variant_dir,
                    args.run_id,
                    project,
                    variant_name,
                    feature_set,
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
            query_read = client.call(f"{args.run_id}-{variant_name}-namedQueryRead", named_query_read_payload(f"{args.run_id}-{variant_name}-namedQueryRead", project, query_path, args))
            gates["namedQueryRead"] = cp.ok(query_read)
            query_preview = client.call(f"{args.run_id}-{variant_name}-namedQueryPreview", named_query_preview_payload(f"{args.run_id}-{variant_name}-namedQueryPreview", project, query_path, args))
            gates["namedQueryPreview"] = cp.ok(query_preview)
            readback = client.call(f"{args.run_id}-{variant_name}-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, view_path, args))
            gates["viewRead"] = cp.ok(readback) and readback_ok(readback, package, args.query_count)
            page = client.call(f"{args.run_id}-{variant_name}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = variant_dir / "profile"
            profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), f"profile-refresh-binding-{variant_name}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            proof = browser_refresh_proof(profile_dir) if variant_name == "manual" else {}
            if variant_name == "manual":
                gates["manualRefreshProof"] = bool(proof.get("ok") is True and proof.get("watchedTextChanged") is True)
            variant = {
                "variant": variant_name,
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "queryPath": query_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "profileDir": str(profile_dir),
                "browser": hidden_common.browser_metrics(profile_dir),
                "network": network_summary(profile_dir),
                "queryMetrics": query_metric_summary(profile_dir),
                "gateway": hidden_common.gateway_metrics(profile_dir),
                "static": hidden_common.static_summary(profile_dir),
                "metricFamilies": hidden_common.metric_family_samples(profile_dir),
                "manualRefreshProof": proof,
                "profileCommand": profile_result,
            }
        except Exception as exc:
            variant = {
                "variant": variant_name,
                "ok": False,
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "queryPath": query_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                rb_dry = client.call(f"{args.run_id}-{variant_name}-rollback-dryRun", rollback_payload(f"{args.run_id}-{variant_name}-rollback-dryRun", project, backup_name, package, True), timeout=args.timeout_sec)
                rb_apply = client.call(f"{args.run_id}-{variant_name}-rollback-apply", rollback_payload(f"{args.run_id}-{variant_name}-rollback-apply", project, backup_name, package, False), timeout=args.timeout_sec)
                time.sleep(2)
                routes_check = client.call(
                    f"{args.run_id}-{variant_name}-post-cleanup-routesList",
                    {"action": "routesList", "requestId": f"{args.run_id}-{variant_name}-post-cleanup-routesList", "targetProject": project, "routePrefix": route, "maxResults": 25},
                )
                routes = cp.response(routes_check).get("routes", [])
                routes_list = routes if isinstance(routes, list) else []
                route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes_list)
                after_read = client.call(f"{args.run_id}-{variant_name}-post-cleanup-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-post-cleanup-viewRead", project, view_path, args))
                query_after = client.call(f"{args.run_id}-{variant_name}-post-cleanup-namedQueryRead", named_query_read_payload(f"{args.run_id}-{variant_name}-post-cleanup-namedQueryRead", project, query_path, args))
                variant["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                variant["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                variant["cleanupViewAbsent"] = not cp.ok(after_read)
                variant["cleanupNamedQueryAbsent"] = not cp.ok(query_after)
                variant["ok"] = bool(variant.get("ok") and variant["rollbackOk"] and variant["cleanupRouteAbsent"] and variant["cleanupViewAbsent"] and variant["cleanupNamedQueryAbsent"])
            variants.append(variant)
            if args.pause_sec > 0 and variant_name != "polling":
                time.sleep(args.pause_sec)

    manual_profile = next((Path(row["profileDir"]) for row in variants if row.get("variant") == "manual" and row.get("profileDir")), None)
    polling_profile = next((Path(row["profileDir"]) for row in variants if row.get("variant") == "polling" and row.get("profileDir")), None)
    comparison: Dict[str, Any] = {}
    comparison_primary_data: Dict[str, Any] = {}
    if manual_profile and polling_profile and manual_profile.exists() and polling_profile.exists():
        comparison = compare_profiles(out_dir, manual_profile, polling_profile)
        if comparison.get("ok"):
            comparison_primary_data = comparison_primary(Path(str(comparison["comparisonDir"])))

    summary = {
        "ok": bool(cp.ok(health) and cp.ok(db_record) and variants and all(row.get("ok") for row in variants) and (not comparison or comparison.get("ok"))),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "scenario": "query polling versus refreshBinding fixture",
        "evidenceGrade": "Observed",
        "features": sorted(feature_set),
        "database": "<databaseConnection>",
        "actualDatabaseEvidence": database,
        "queryCount": args.query_count,
        "pollingRateSec": args.polling_rate_sec,
        "metricPrefixes": args.metric_prefix or [],
        "metricNameContains": args.metric_name_contains or [],
        "manualClickDelayMs": args.manual_click_delay_ms,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "baselineWaitIntervalSeconds": args.baseline_wait_interval_sec if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparison": comparison,
        "comparisonPrimary": comparison_primary_data,
        "packages": package_records,
        "interpretation": [
            "This is a controlled query-binding fixture, not a customer route conclusion.",
            "Both variants use the same number of visible query-bound labels and the same read-only Named Query SQL shape.",
            "The polling variant leaves query polling enabled; the manual variant disables polling and proves a button click changed the watched query label after refreshBinding().",
            "Compare continuous websocket/property-change/Gateway deltas against the manual click proof before recommending event-driven refresh.",
            "Treat single-run Gateway and browser deltas as observed only; repeat clean-baseline pairs when the route is noisy or the decision is high impact.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "packages.json", package_records)
    write_report(out_dir, summary)
    write_manifest(out_dir, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--database", default="", help="Database connection for disposable read-only Named Query. Defaults to first valid connection.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--query-count", type=int, default=8)
    parser.add_argument("--polling-rate-sec", type=int, default=1)
    parser.add_argument("--manual-click-delay-ms", type=int, default=8000)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--named-query-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--allowed-named-query-prefix", default=DEFAULT_ALLOWED_NAMED_QUERY_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=18.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--metric-prefix", action="append", default=[], help="Metric prefix filter forwarded to collect_profile.py. Repeatable.")
    parser.add_argument("--metric-name-contains", action="append", default=[], help="Metric substring filter forwarded to collect_profile.py. Repeatable.")
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=420)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-click-timeout-sec", type=float, default=12.0)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--pause-sec", type=float, default=5.0)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each variant, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline per variant.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Mark the variant failed before import when the requested clean baseline is not reached.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.query_count < 1:
        raise SystemExit("--query-count must be >= 1")
    if args.polling_rate_sec < 1:
        raise SystemExit("--polling-rate-sec must be >= 1")
    if args.manual_click_delay_ms < 0:
        raise SystemExit("--manual-click-delay-ms must be >= 0")
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
