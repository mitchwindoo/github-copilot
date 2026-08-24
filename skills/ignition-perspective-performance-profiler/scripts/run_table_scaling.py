#!/usr/bin/env python3
"""Run guarded Perspective table row/column scaling fixtures."""

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
from typing import Any, Dict, List, Optional, Tuple

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_table_ab_remediation as table_common
import run_tab_runwhilehidden_ab as tab_common


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
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
    common.write_json(path, data)


def read_json(path: Path) -> Dict[str, Any]:
    return common.read_json(path)


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


def parse_int_list(raw: str, label: str) -> List[int]:
    values: List[int] = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            value = int(text)
        except ValueError as exc:
            raise ValueError(f"{label} contains a non-integer value: {text!r}") from exc
        if value <= 0:
            raise ValueError(f"{label} values must be positive")
        values.append(value)
    if not values:
        raise ValueError(f"{label} must contain at least one value")
    return sorted(dict.fromkeys(values))


def parse_sizes(args: argparse.Namespace) -> List[Tuple[int, int]]:
    if args.sizes.strip():
        pairs: List[Tuple[int, int]] = []
        for part in args.sizes.split(","):
            text = part.strip().lower()
            if not text:
                continue
            if "x" not in text:
                raise ValueError(f"--sizes entries must look like ROWSxCOLUMNS: {text!r}")
            left, right = text.split("x", 1)
            rows = int(left.strip())
            columns = int(right.strip())
            if rows <= 0 or columns <= 0:
                raise ValueError("--sizes rows and columns must be positive")
            pairs.append((rows, columns))
    else:
        rows_list = parse_int_list(args.row_counts, "--row-counts")
        columns_list = parse_int_list(args.column_counts, "--column-counts")
        pairs = [(rows, columns) for rows in rows_list for columns in columns_list]
    pairs = sorted(dict.fromkeys(pairs), key=lambda item: (item[0], item[1]))
    if not pairs:
        raise ValueError("No table sizes selected")
    for rows, columns in pairs:
        if rows > args.max_rows:
            raise ValueError(f"row count {rows} exceeds --max-rows {args.max_rows}")
        if columns > args.max_columns:
            raise ValueError(f"column count {columns} exceeds --max-columns {args.max_columns}")
    return pairs


def variant_label(rows: int, columns: int) -> str:
    return f"table-{rows:04d}x{columns:03d}"


def build_route(prefix: str, run_slug: str, rows: int, columns: int) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-{variant_label(rows, columns)}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def make_view_json(args: argparse.Namespace, rows: int, columns: int, variant: str) -> Dict[str, Any]:
    table_rows = table_common.make_rows(rows, columns)
    table_columns = table_common.make_columns(columns)
    ready = f"{args.run_id} {variant.upper()} READY"
    return {
        "custom": {
            "runId": args.run_id,
            "variant": variant,
            "rowCount": rows,
            "columnCount": columns,
            "cellCount": rows * columns,
            "virtualized": args.virtualized,
            "dataSha256": sha256_text(canonical_json(table_rows)),
            "columnSha256": sha256_text(canonical_json(table_columns)),
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "table-scaling-root"},
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
                    position={"basis": "34px", "grow": 0, "shrink": 0},
                    props={
                        "text": (
                            f"A-10 table scaling fixture: rows {rows}, columns {columns}, "
                            f"cells {rows * columns}, virtualized {str(args.virtualized).lower()}"
                        ),
                        "style": {"color": "#1f2937", "fontSize": 13, "padding": "7px 2px", "whiteSpace": "pre-wrap"},
                    },
                ),
                component(
                    "ia.display.table",
                    meta={"name": "Scaling Table"},
                    position={"basis": "auto", "grow": 1, "shrink": 1},
                    props={
                        "data": table_rows,
                        "columns": table_columns,
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


def build_package(out_dir: Path, project: str, args: argparse.Namespace, rows: int, columns: int, view_path: str, route: str) -> Dict[str, Any]:
    variant = variant_label(rows, columns)
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-table-scaling"
    view_json = make_view_json(args, rows, columns, variant)
    zip_path = zip_dir / f"{slug(args.run_id)}-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-table-scale-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler table scaling fixture", "enabled": True, "inheritable": False})
        write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Table Scaling {rows}x{columns}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", table_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "rows": rows,
        "columns": columns,
        "cellCount": rows * columns,
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Table Scaling {package['rows']}x{package['columns']}"}],
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
    profile_dir_arg = profile_dir.resolve()
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        f"{args.run_id}-{package['variant']}",
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
        str(profile_dir_arg),
        "--gateway-alias",
        args.gateway_alias,
        "--scenario",
        "table row/column scaling A-10 fixture",
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
    return (
        cp.ok(record)
        and f'"rowCount":{package["rows"]}' in response_text
        and f'"columnCount":{package["columns"]}' in response_text
        and str(package["readyText"]) in response_text
        and str(package["dataSha256"]) in response_text
        and str(package["columnSha256"]) in response_text
    )


def browser_metrics(profile_dir: Path) -> Dict[str, Any]:
    return common.browser_metrics(profile_dir)


def gateway_metrics(profile_dir: Path) -> Dict[str, Any]:
    return common.gateway_metrics(profile_dir)


def network_metrics(profile_dir: Path) -> Dict[str, Any]:
    network = read_json(profile_dir / "network-summary.json")
    return {
        "requestCount": network.get("requestCount"),
        "resourceTransferSize": read_json(profile_dir / "browser-summary.json").get("resourceTransferSize"),
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
    }


def compare_to_baseline(out_dir: Path, baseline_dir: Path, profile_dir: Path, variant: str) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparisons" / f"{variant}-minus-baseline"
    cmd = [
        sys.executable,
        str(COMPARE_SCRIPT),
        "--control-dir",
        str(baseline_dir.resolve()),
        "--target-dir",
        str(profile_dir.resolve()),
        "--out-dir",
        str(comparison_dir.resolve()),
    ]
    result = common.run_command(cmd, f"compare-{variant}", out_dir, 240)
    return {"variant": variant, "ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}


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
        "# Table Row/Column Scaling Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Virtualized: `{str(summary.get('virtualized', False)).lower()}`",
        "",
        "## Variant Summary",
        "",
        "| Size | OK | Rows | Columns | View bytes | Data bytes | DOM | LCP ms | Long task ms | JS heap | WS recv | Cleanup |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        static = row.get("static", {})
        browser = row.get("browser", {})
        network = row.get("network", {})
        lines.append(
            "| {variant} | `{ok}` | {rows} | {columns} | {view_bytes} | {data_bytes} | {dom} | {lcp} | {long_task} | {heap} | {ws_recv} | `{cleanup}` |".format(
                variant=row.get("variant"),
                ok=str(row.get("ok", False)).lower(),
                rows=static.get("tableRows"),
                columns=static.get("tableColumns"),
                view_bytes=static.get("viewJsonBytes"),
                data_bytes=static.get("tableDataBytes"),
                dom=browser.get("domNodeCount"),
                lcp=browser.get("largestContentfulPaintMs"),
                long_task=browser.get("longTaskTotalMs"),
                heap=browser.get("usedJSHeapBytes"),
                ws_recv=network.get("webSocketBytesReceived"),
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewsAbsent", False)).lower(),
            )
        )
    lines.extend(["", "## Baseline Comparisons", ""])
    for row in summary.get("comparisons", []):
        lines.append(f"- `{row.get('variant')}`: comparison ok `{str(row.get('ok', False)).lower()}` at `{row.get('comparisonDir')}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    sizes = parse_sizes(args)
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir)
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
    compare_records: List[Dict[str, Any]] = []

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_response = cp.response(health)
    health_ok = cp.ok(health)
    feature_set = set(health_response.get("features", []) if isinstance(health_response.get("features"), list) else [])

    for rows, columns in sizes:
        variant = variant_label(rows, columns)
        variant_dir = out_dir / variant
        route = build_route(args.route_prefix, run_slug, rows, columns)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/Table{rows:04d}x{columns:03d}"
        package = build_package(variant_dir, project, args, rows, columns, view_path, route)
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
                "rows": rows,
                "columns": columns,
                "cellCount": rows * columns,
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
                "profileCommand": profile_result,
            }
            baseline_dir = out_dir / variant_label(sizes[0][0], sizes[0][1]) / "profile"
            if (rows, columns) != sizes[0] and baseline_dir.exists() and gates["profile"]:
                comparison = compare_to_baseline(out_dir, baseline_dir, profile_dir, variant)
                if comparison.get("ok"):
                    comparison["primary"] = comparison_primary(Path(str(comparison["comparisonDir"])))
                compare_records.append(comparison)
        except Exception as exc:
            row = {
                "variant": variant,
                "rows": rows,
                "columns": columns,
                "cellCount": rows * columns,
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
            if args.pause_sec > 0 and (rows, columns) != sizes[-1]:
                time.sleep(args.pause_sec)

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": health_response.get("runnerVersion"),
        "stackVersion": health_response.get("stackVersion"),
        "virtualized": args.virtualized,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "sizes": [{"rows": rows, "columns": columns, "cellCount": rows * columns} for rows, columns in sizes],
        "healthOk": health_ok,
        "variants": variants,
        "comparisons": compare_records,
        "packages": package_records,
        "interpretation": [
            "This is a controlled A-10 table row/column scaling fixture, not a customer route conclusion.",
            "The fixture changes static table row and column counts while keeping the surrounding view shape fixed.",
            "Use browser timing, DOM, heap, WebSocket/network bytes, and static payload size together; a single matrix pass is scaling characterization, not a causal remediation claim.",
            "Run a separate A-11 virtualization or A-12 filter-writeback fixture before recommending a specific table setting.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "packages.json", package_records)
    write_json(out_dir / "comparisons.json", compare_records)
    write_report(out_dir, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--sizes", default="", help="Comma-separated ROWSxCOLUMNS pairs. Overrides --row-counts/--column-counts.")
    parser.add_argument("--row-counts", default="100,500,1000")
    parser.add_argument("--column-counts", default="10,30,50")
    parser.add_argument("--max-rows", type=int, default=2000)
    parser.add_argument("--max-columns", type=int, default=80)
    parser.add_argument("--virtualized", action="store_true", help="Enable table virtualization for every scaling variant.")
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
