#!/usr/bin/env python3
"""Run guarded Perspective Table filter-results writeback A/B fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_hidden_content_ab as hidden_common
import run_table_ab_remediation as table_common
import run_tab_runwhilehidden_ab as tab_common


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
VARIANTS = ("writeback-off", "writeback-on")


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


def profile_run_id(run_id: str, variant: str) -> str:
    base = compact(run_id)[:22].strip("-_") or "run"
    variant_code = {"writeback-off": "wb-off", "writeback-on": "wb-on"}.get(variant, slug(variant)[:10] or "variant")
    digest = sha256_text(f"{run_id}:{variant}")[:8]
    return f"{base}-{variant_code}-{digest}"


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
    children: List[Dict[str, Any]] | None = None,
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


def writeback_enabled(variant: str) -> bool:
    if variant == "writeback-on":
        return True
    if variant == "writeback-off":
        return False
    raise ValueError(f"Unsupported variant: {variant}")


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-table-filter-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def make_rows(row_count: int, column_count: int, filter_text: str, match_every: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row_index in range(row_count):
        matched = row_index % max(match_every, 1) == 0
        row: Dict[str, Any] = {
            "row_id": f"row-{row_index:04d}",
            "filter_key": filter_text if matched else "ordinary",
            "status": "Attention" if matched else "Normal",
        }
        for col_index in range(column_count):
            field = f"col_{col_index + 1:02d}"
            row[field] = f"R{row_index:04d}-C{col_index + 1:02d}-{(row_index * (col_index + 5)) % 997:03d}"
        rows.append(row)
    return rows


def make_columns(column_count: int) -> List[Dict[str, Any]]:
    columns = [
        {
            "field": "filter_key",
            "header": {"title": "Filter Key"},
            "visible": True,
            "editable": False,
            "sortable": True,
            "resizable": True,
        },
        {
            "field": "status",
            "header": {"title": "Status"},
            "visible": True,
            "editable": False,
            "sortable": True,
            "resizable": True,
        },
    ]
    for index in range(column_count):
        field = f"col_{index + 1:02d}"
        columns.append(
            {
                "field": field,
                "header": {"title": f"C{index + 1:02d}"},
                "visible": True,
                "editable": False,
                "sortable": True,
                "resizable": True,
            }
        )
    return columns


def make_view_json(args: argparse.Namespace, variant: str) -> Dict[str, Any]:
    enabled = writeback_enabled(variant)
    rows = make_rows(args.rows, args.columns, args.filter_text, args.match_every)
    columns = make_columns(args.columns)
    expected_filtered_rows = sum(1 for row in rows if args.filter_text in json.dumps(row, sort_keys=True))
    ready = f"{args.run_id} {variant.upper()} READY"
    return {
        "custom": {
            "runId": args.run_id,
            "variant": variant,
            "rowCount": args.rows,
            "columnCount": args.columns + 2,
            "configuredDataColumns": args.columns,
            "filterText": args.filter_text,
            "expectedFilteredRows": expected_filtered_rows,
            "filterResultsWritebackEnabled": enabled,
            "dataSha256": sha256_text(canonical_json(rows)),
            "columnSha256": sha256_text(canonical_json(columns)),
            "remediationCandidate": "Disable Table filter result writeback unless another binding or script consumes the filtered result set.",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "table-filter-writeback-root"},
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
                    position={"basis": "48px", "grow": 0, "shrink": 0},
                    props={
                        "text": (
                            f"A-12 table filter writeback fixture: {args.rows} rows, {args.columns + 2} columns, "
                            f"filter text {args.filter_text}, expected filtered rows {expected_filtered_rows}, "
                            f"results writeback {str(enabled).lower()}"
                        ),
                        "style": {"color": "#1f2937", "fontSize": 13, "padding": "7px 2px", "whiteSpace": "pre-wrap"},
                    },
                ),
                component(
                    "ia.display.table",
                    meta={"name": "FilterWritebackTable"},
                    position={"basis": "auto", "grow": 1, "shrink": 1},
                    props={
                        "data": rows,
                        "columns": columns,
                        "virtualized": args.virtualized,
                        "filter": {
                            "enabled": True,
                            "text": args.filter_text,
                            "results": {"enabled": enabled, "data": []},
                        },
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


def build_package(out_dir: Path, project: str, args: argparse.Namespace, variant: str, view_path: str, route: str) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-table-filter-writeback"
    view_json = make_view_json(args, variant)
    zip_path = zip_dir / f"{slug(args.run_id)}-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-table-filter-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler table filter writeback fixture", "enabled": True, "inheritable": False})
        write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Table Filter {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", table_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "writebackEnabled": writeback_enabled(variant),
        "rows": args.rows,
        "columns": args.columns + 2,
        "configuredDataColumns": args.columns,
        "filterText": args.filter_text,
        "expectedFilteredRows": view_json["custom"]["expectedFilteredRows"],
        "route": route,
        "viewPath": view_path,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "dataSha256": view_json["custom"]["dataSha256"],
        "columnSha256": view_json["custom"]["columnSha256"],
        "readyText": f"{args.run_id} {variant.upper()} READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Table Filter {package['variant']}"}],
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


def collect_env(endpoint: str, token: str, project: str) -> Dict[str, str]:
    env = dict(os.environ)
    env["IGNITION_LLM_RUNNER_ENDPOINT"] = endpoint
    env["IGNITION_LLM_RUNNER_TOKEN"] = token
    env["IGNITION_TARGET_PROJECT"] = project
    return env


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        str(package.get("profileRunId") or profile_run_id(args.run_id, str(package["variant"]))),
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
        str(profile_dir.resolve()),
        "--gateway-alias",
        args.gateway_alias,
        "--scenario",
        "table filter-results writeback A-12 fixture",
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


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    response_text = canonical_json(cp.response(record))
    expected_enabled = "true" if package["writebackEnabled"] else "false"
    return (
        cp.ok(record)
        and f'"rowCount":{package["rows"]}' in response_text
        and f'"columnCount":{package["columns"]}' in response_text
        and str(package["readyText"]) in response_text
        and str(package["filterText"]) in response_text
        and str(package["dataSha256"]) in response_text
        and str(package["columnSha256"]) in response_text
        and '"filter":{"enabled":true' in response_text
        and f'"filterResultsWritebackEnabled":{expected_enabled}' in response_text
        and f'"results":{{"data":[],"enabled":{expected_enabled}}}' in response_text
    )


def browser_metrics(profile_dir: Path) -> Dict[str, Any]:
    return common.browser_metrics(profile_dir)


def gateway_metrics(profile_dir: Path) -> Dict[str, Any]:
    return common.gateway_metrics(profile_dir)


def network_metrics(profile_dir: Path) -> Dict[str, Any]:
    network = read_json(profile_dir / "network-summary.json")
    browser = read_json(profile_dir / "browser-summary.json")
    return {
        "requestCount": network.get("requestCount"),
        "resourceTransferSize": browser.get("resourceTransferSize"),
        "knownContentLengthBytes": network.get("knownContentLengthBytes"),
        "webSocketFramesSent": network.get("webSocketFramesSent"),
        "webSocketFramesReceived": network.get("webSocketFramesReceived"),
        "webSocketBytesSent": network.get("webSocketBytesSent"),
        "webSocketBytesReceived": network.get("webSocketBytesReceived"),
    }


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    profile = read_json(profile_dir / "static-profile.json")
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    heavy = profile.get("heavyData", []) if isinstance(profile.get("heavyData"), list) else []
    table_data: Dict[str, Any] = {}
    columns_data: Dict[str, Any] = {}
    for row in heavy:
        if not isinstance(row, dict):
            continue
        if row.get("kind") == "static-data" and not table_data:
            table_data = row
        if row.get("kind") == "columns" and not columns_data:
            columns_data = row
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "tableLikeCount": summary.get("tableLikeCount"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
        "tableRows": table_data.get("rows"),
        "tableColumns": table_data.get("columns"),
        "tableDataBytes": table_data.get("bytes"),
        "columnBytes": columns_data.get("bytes"),
        "virtualized": table_data.get("virtualized"),
        "filterResultsWriteback": table_data.get("filterResultsWriteback"),
    }


def compare_profiles(out_dir: Path, off_dir: Path, on_dir: Path) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparison-writeback-on-minus-off"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(off_dir), "--target-dir", str(on_dir), "--out-dir", str(comparison_dir)]
    result = common.run_command(cmd, "compare-writeback-on-minus-off", out_dir, 240)
    record: Dict[str, Any] = {"ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}
    if record["ok"]:
        record["primary"] = comparison_primary(comparison_dir)
    return record


def comparison_primary(comparison_dir: Path) -> Dict[str, Any]:
    data = read_json(comparison_dir / "comparison.json")
    browser = data.get("browserDeltas", {}) if isinstance(data.get("browserDeltas"), dict) else {}
    static = data.get("staticDeltas", {}) if isinstance(data.get("staticDeltas"), dict) else {}

    def delta(bucket: Dict[str, Any], key: str) -> Any:
        row = bucket.get(key)
        return row.get("delta") if isinstance(row, dict) else None

    return {
        "componentCountDelta": delta(static, "componentCount"),
        "bindingCountDelta": delta(static, "bindingCount"),
        "viewJsonBytesDelta": delta(static, "viewJsonBytes"),
        "domNodeCountDelta": delta(browser, "domNodeCount"),
        "largestContentfulPaintMsDelta": delta(browser, "largestContentfulPaintMs"),
        "longTaskTotalMsDelta": delta(browser, "longTaskTotalMs"),
        "usedJSHeapBytesDelta": delta(browser, "usedJSHeapBytes"),
        "resourceTransferSizeDelta": delta(browser, "resourceTransferSize"),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Table Filter Results Writeback Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Rows: `{summary.get('rows')}`",
        f"Columns: `{summary.get('columns')}`",
        f"Filter text: `{summary.get('filterText')}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | OK | Writeback | Filtered rows | View bytes | Data bytes | DOM | LCP ms | Long task ms | JS heap | WS sent | WS recv | Cleanup |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        static = row.get("static", {})
        browser = row.get("browser", {})
        network = row.get("network", {})
        lines.append(
            "| {variant} | `{ok}` | `{writeback}` | {filtered} | {view_bytes} | {data_bytes} | {dom} | {lcp} | {long_task} | {heap} | {ws_sent} | {ws_recv} | `{cleanup}` |".format(
                variant=row.get("variant"),
                ok=str(row.get("ok", False)).lower(),
                writeback=str(row.get("writebackEnabled", False)).lower(),
                filtered=row.get("expectedFilteredRows"),
                view_bytes=static.get("viewJsonBytes"),
                data_bytes=static.get("tableDataBytes"),
                dom=browser.get("domNodeCount"),
                lcp=browser.get("largestContentfulPaintMs"),
                long_task=browser.get("longTaskTotalMs"),
                heap=browser.get("usedJSHeapBytes"),
                ws_sent=network.get("webSocketBytesSent"),
                ws_recv=network.get("webSocketBytesReceived"),
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewsAbsent", False)).lower(),
            )
        )
    comparison = summary.get("comparison", {})
    lines.extend(["", "## Comparison", ""])
    if comparison:
        lines.append(f"- Writeback-on minus writeback-off comparison ok: `{str(comparison.get('ok', False)).lower()}`.")
        lines.append(f"- Comparison directory: `{comparison.get('comparisonDir')}`.")
        primary = comparison.get("primary", {}) if isinstance(comparison.get("primary"), dict) else {}
        for key, value in primary.items():
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if args.rows <= 0 or args.columns <= 0:
        raise SystemExit("--rows and --columns must be positive")
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    env = collect_env(endpoint, token, project)
    run_slug = slug(args.run_id)
    base = compact(args.run_id)
    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_response = cp.response(health)
    health_ok = cp.ok(health)
    feature_set = set(health_response.get("features", []) if isinstance(health_response.get("features"), list) else [])

    for variant in VARIANTS:
        variant_dir = out_dir / variant
        route = build_route(args.route_prefix, run_slug, variant)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/TableFilter{''.join(part.title() for part in variant.split('-'))}"
        package = build_package(variant_dir, project, args, variant, view_path, route)
        package["profileRunId"] = profile_run_id(args.run_id, variant)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        backup_name = ""
        gates: Dict[str, bool] = {}
        baseline: Dict[str, Any] = {"enabled": False}
        try:
            if args.wait_for_clean_baseline:
                baseline = tab_common.wait_for_clean_baseline(
                    client,
                    out_dir,
                    args.run_id,
                    project,
                    variant,
                    feature_set,
                    args.baseline_max_browser_sessions,
                    args.baseline_wait_timeout_sec,
                    args.baseline_wait_interval_sec,
                )
                gates["cleanBaseline"] = baseline.get("ok") is True
                if args.fail_on_baseline_timeout and not gates["cleanBaseline"]:
                    raise RuntimeError("clean baseline wait failed")
            dry = client.call(f"{args.run_id}-{variant}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant}-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry)
            if not gates["dryRun"]:
                raise RuntimeError("dryRun failed")
            apply = client.call(f"{args.run_id}-{variant}-apply", package_payload("apply", f"{args.run_id}-{variant}-apply", project, package, args), timeout=args.timeout_sec)
            backup_name = common.backup_name_from_response(cp.response(apply))
            gates["apply"] = cp.ok(apply) and bool(backup_name)
            if not gates["apply"]:
                raise RuntimeError("apply failed")
            time.sleep(2)
            view_read = client.call(f"{args.run_id}-{variant}-viewRead", view_read_payload(f"{args.run_id}-{variant}-viewRead", project, view_path, args))
            gates["viewRead"] = readback_ok(view_read, package)
            page = client.call(f"{args.run_id}-{variant}-pageValidate", page_validate_payload(f"{args.run_id}-{variant}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = variant_dir / "profile"
            command = profile_command(args, package, project, browser_url, profile_dir)
            profile_result = common.run_command(command, f"profile-{variant}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            row = {
                "variant": variant,
                "writebackEnabled": package["writebackEnabled"],
                "rows": package["rows"],
                "columns": package["columns"],
                "expectedFilteredRows": package["expectedFilteredRows"],
                "ok": all(gates.values()),
                "gates": gates,
                "baselineWait": baseline,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "profileDir": str(profile_dir),
                "browser": browser_metrics(profile_dir),
                "gateway": gateway_metrics(profile_dir),
                "network": network_metrics(profile_dir),
                "static": static_summary(profile_dir),
                "metricFamilies": hidden_common.metric_family_samples(profile_dir),
                "profileCommand": profile_result,
            }
        except Exception as exc:
            row = {
                "variant": variant,
                "writebackEnabled": package["writebackEnabled"],
                "rows": package["rows"],
                "columns": package["columns"],
                "expectedFilteredRows": package["expectedFilteredRows"],
                "ok": False,
                "gates": gates,
                "baselineWait": baseline,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                rb_dry = client.call(
                    f"{args.run_id}-{variant}-rollback-dryRun",
                    rollback_payload(f"{args.run_id}-{variant}-rollback-dryRun", project, backup_name, view_path, True),
                    timeout=args.timeout_sec,
                )
                rb_apply = client.call(
                    f"{args.run_id}-{variant}-rollback-apply",
                    rollback_payload(f"{args.run_id}-{variant}-rollback-apply", project, backup_name, view_path, False),
                    timeout=args.timeout_sec,
                )
                time.sleep(2)
                routes_check = client.call(
                    f"{args.run_id}-{variant}-post-cleanup-routesList",
                    {
                        "action": "routesList",
                        "requestId": f"{args.run_id}-{variant}-post-cleanup-routesList",
                        "targetProject": project,
                        "routePrefix": route,
                        "maxResults": 25,
                    },
                )
                routes = cp.response(routes_check).get("routes", [])
                routes_list = routes if isinstance(routes, list) else []
                route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes_list)
                after_read = client.call(f"{args.run_id}-{variant}-post-cleanup-viewRead", view_read_payload(f"{args.run_id}-{variant}-post-cleanup-viewRead", project, view_path, args))
                row["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                row["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                row["cleanupViewsAbsent"] = not cp.ok(after_read)
                row["ok"] = bool(row.get("ok") and row["rollbackOk"] and row["cleanupRouteAbsent"] and row["cleanupViewsAbsent"])
            variants.append(row)
            if args.pause_sec > 0 and variant != VARIANTS[-1]:
                time.sleep(args.pause_sec)

    comparison: Dict[str, Any] = {}
    by_variant = {row.get("variant"): row for row in variants}
    off_profile = Path(str(by_variant.get("writeback-off", {}).get("profileDir", "")))
    on_profile = Path(str(by_variant.get("writeback-on", {}).get("profileDir", "")))
    if off_profile.exists() and on_profile.exists() and by_variant.get("writeback-off", {}).get("gates", {}).get("profile") and by_variant.get("writeback-on", {}).get("gates", {}).get("profile"):
        comparison = compare_profiles(out_dir, off_profile, on_profile)

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants) and comparison.get("ok")),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": health_response.get("runnerVersion"),
        "stackVersion": health_response.get("stackVersion"),
        "rows": args.rows,
        "columns": args.columns + 2,
        "configuredDataColumns": args.columns,
        "filterText": args.filter_text,
        "virtualized": args.virtualized,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "healthOk": health_ok,
        "variants": variants,
        "comparison": comparison,
        "packages": package_records,
        "interpretation": [
            "This is a controlled A-12 table filter-results writeback fixture, not a customer route conclusion.",
            "The fixture keeps the same table data, columns, filter text, and visible shape while changing only props.filter.results.enabled.",
            "The documented writeback property writes filtered rows back to the Table props tree and may add payload/property-change/browser-memory cost when enabled.",
            "Use WebSocket/network bytes, browser heap, property-change counters, and functional need for the filtered result set together; a single pair is mechanics evidence, not a causal remediation rule.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "packages.json", package_records)
    write_report(out_dir, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--columns", type=int, default=30, help="Generated data columns; two extra metadata/filter columns are added.")
    parser.add_argument("--filter-text", default="FILTER_MATCH")
    parser.add_argument("--match-every", type=int, default=5)
    parser.add_argument("--virtualized", action="store_true", help="Enable table virtualization for both variants.")
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=8.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=300)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=75.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=5000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--wait-for-clean-baseline", action="store_true")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0)
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=420.0)
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0)
    parser.add_argument("--fail-on-baseline-timeout", action="store_true")
    parser.add_argument("--pause-sec", type=float, default=5.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
