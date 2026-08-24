#!/usr/bin/env python3
"""Run guarded parameterized query Cache & Share sensitivity fixtures.

This helper tests whether same-path Named Query bindings behave differently
when their Value parameters are identical versus distinct, and whether Cache &
Share changes the selected runtime query metric for each parameter shape.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_query_cache_share_ab as cache_common


SCRIPT_DIR = Path(__file__).resolve().parent
MULTISESSION_SCRIPT = SCRIPT_DIR / "run_multisession_profile.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
DEFAULT_ALLOWED_NAMED_QUERY_PREFIX = "LLM Tests/"
VARIANTS = (
    "same-param-cache-off",
    "same-param-cache-on",
    "distinct-param-cache-off",
    "distinct-param-cache-on",
)
MIN_MEANINGFUL_COUNT = 3.0
MIN_MEANINGFUL_RATIO = 0.20


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


def format_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def delta(before: Any, after: Any) -> Optional[float]:
    before_float = to_float(before)
    after_float = to_float(after)
    if before_float is None or after_float is None:
        return None
    return after_float - before_float


def meaningful_change_delta(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None or right is None:
        return None
    return right - left


def meaningful_threshold(base: Optional[float]) -> Optional[float]:
    if base is None:
        return None
    return max(MIN_MEANINGFUL_COUNT, abs(base) * MIN_MEANINGFUL_RATIO)


def cache_enabled_for_variant(variant: str) -> bool:
    return variant.endswith("cache-on")


def distinct_params_for_variant(variant: str) -> bool:
    return variant.startswith("distinct-param")


def child_profile_run_id(parent_run_id: str, variant: str) -> str:
    variant_code = {
        "same-param-cache-off": "same-off",
        "same-param-cache-on": "same-on",
        "distinct-param-cache-off": "dist-off",
        "distinct-param-cache-on": "dist-on",
    }.get(variant, compact(variant)[:14])
    return f"{compact(parent_run_id)[:18]}-{variant_code}"


def title_for_variant(variant: str) -> str:
    return {
        "same-param-cache-off": "Same param, Cache off",
        "same-param-cache-on": "Same param, Cache on",
        "distinct-param-cache-off": "Distinct params, Cache off",
        "distinct-param-cache-on": "Distinct params, Cache on",
    }.get(variant, variant)


def bucket_for_label(variant: str, index: int) -> str:
    if distinct_params_for_variant(variant):
        return f"bucket-{index:03d}"
    return "bucket-shared"


def bucket_values_for_variant(variant: str, query_count: int) -> List[str]:
    return [bucket_for_label(variant, index) for index in range(1, query_count + 1)]


def parameter_literal(value: str) -> str:
    return json.dumps(value)


def parameter_tick_transform(prefix: str) -> str:
    return (
        "\ttry:\n"
        "\t\tif value is not None and hasattr(value, 'getRowCount') and value.getRowCount() > 0:\n"
        "\t\t\tbucket = value.getValueAt(0, 'bucket')\n"
        "\t\t\ttick = value.getValueAt(0, 'refresh_tick')\n"
        f"\t\t\treturn '{prefix}: ' + str(bucket) + ' ' + str(tick)\n"
        "\t\tif value is not None and hasattr(value, '__len__') and len(value) > 0:\n"
        "\t\t\trow = value[0]\n"
        "\t\t\tbucket = row.get('bucket') if hasattr(row, 'get') else ''\n"
        "\t\t\ttick = row.get('refresh_tick') if hasattr(row, 'get') else ''\n"
        f"\t\t\treturn '{prefix}: ' + str(bucket) + ' ' + str(tick)\n"
        "\texcept Exception as err:\n"
        f"\t\treturn '{prefix} error: ' + str(err)\n"
        f"\treturn '{prefix}: <none>'\n"
    )


def parameter_query_binding(query_path: str, cache_enabled: bool, polling_rate_sec: int, bucket: str, prefix: str) -> Dict[str, Any]:
    return {
        "binding": {
            "type": "query",
            "config": {
                "parameters": {"bucket": parameter_literal(bucket)},
                "polling": {"enabled": True, "rate": str(polling_rate_sec)},
                "queryPath": query_path,
                "cacheAndShare": cache_enabled,
            },
            "transforms": [{"type": "script", "code": parameter_tick_transform(prefix)}],
        }
    }


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-query-param-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def label_component(index: int, variant: str, query_path: str, polling_rate_sec: int) -> Dict[str, Any]:
    bucket = bucket_for_label(variant, index)
    prefix = f"{title_for_variant(variant)} {index:03d}"
    return cache_common.refresh_common.component(
        "ia.display.label",
        meta={"name": f"ParamQueryLabel{index:03d}"},
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
        prop_config={
            "props.text": parameter_query_binding(
                query_path,
                cache_enabled_for_variant(variant),
                polling_rate_sec,
                bucket,
                prefix,
            )
        },
    )


def make_view_json(run_id: str, variant: str, query_path: str, query_count: int, polling_rate_sec: int) -> Dict[str, Any]:
    cache_enabled = cache_enabled_for_variant(variant)
    parameter_shape = "distinct" if distinct_params_for_variant(variant) else "identical"
    marker = f"{run_id} {variant.upper()} READY"
    children: List[Dict[str, Any]] = [
        cache_common.label(
            marker,
            "Ready Marker",
            "42px",
            {
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
        ),
        cache_common.label(
            (
                f"Parameterized query fixture: {query_count} query-bound labels, "
                f"{parameter_shape} Value parameters, Cache & Share {str(cache_enabled).lower()}, "
                f"{polling_rate_sec}s polling."
            ),
            "Fixture Summary",
            "54px",
            {"color": "#1f2937", "whiteSpace": "pre-wrap"},
        ),
        cache_common.label(
            "Purpose: distinguish same-path identical-parameter work from same-path distinct-parameter work before interpreting Cache & Share.",
            "Parameter Purpose",
            "42px",
            {"backgroundColor": "#eef2ff", "borderColor": "#c7d2fe", "borderStyle": "solid", "borderWidth": "1px", "whiteSpace": "pre-wrap"},
        ),
    ]
    children.extend(label_component(index, variant, query_path, polling_rate_sec) for index in range(1, query_count + 1))
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "queryCount": query_count,
            "pollingEnabled": True,
            "pollingRateSec": polling_rate_sec,
            "cacheAndShare": cache_enabled,
            "parameterShape": parameter_shape,
            "namedQueryParameter": "bucket",
            "testPurpose": "parameterized query Cache & Share sensitivity",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": cache_common.refresh_common.component(
            "ia.container.flex",
            meta={"name": "query-parameter-sensitivity-root"},
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


def parameterized_named_query_resource(actor: str, database: str) -> Dict[str, Any]:
    resource = cache_common.refresh_common.named_query_resource(actor, database)
    resource["attributes"]["parameters"] = [
        {
            "databaseParameter": False,
            "identifier": "bucket",
            "sqlType": 7,
            "type": "Parameter",
            "unsafeQueryString": False,
        }
    ]
    return resource


def write_named_query(project_root: Path, query_path: str, query_sql: str, database: str, actor: str) -> None:
    query_dir = project_root / "ignition" / "named-query" / Path(*query_path.split("/"))
    query_dir.mkdir(parents=True, exist_ok=True)
    (query_dir / "query.sql").write_text(query_sql, encoding="utf-8", newline="\n")
    write_json(query_dir / "resource.json", parameterized_named_query_resource(actor, database))


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
    # Keep the generated package path short enough for Windows workspaces with long vault roots.
    zip_dir = out_dir / "pkg"
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-query-params"
    view_json = make_view_json(run_id, variant, query_path, query_count, polling_rate_sec)
    query_sql = "SELECT :bucket AS bucket, strftime('%Y%m%dT%H%M%f','now') || '-' || hex(randomblob(4)) AS refresh_tick LIMIT 1"
    zip_path = zip_dir / "package.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-query-params-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler query parameter sensitivity fixture", "enabled": True, "inheritable": False})
        cache_common.refresh_common.write_view(project_root, view_path, view_json, actor)
        write_named_query(project_root, query_path, query_sql, database, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Query Parameter Sensitivity {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", cache_common.fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    bucket_values = bucket_values_for_variant(variant, query_count)
    first_prefix = f"{title_for_variant(variant)} 001:"
    first_ready_text = f"{first_prefix} {bucket_values[0]}"
    return {
        "variant": variant,
        "queryCount": query_count,
        "cacheAndShare": cache_enabled_for_variant(variant),
        "parameterShape": "distinct" if distinct_params_for_variant(variant) else "same",
        "bucketValues": bucket_values,
        "uniqueBucketCount": len(set(bucket_values)),
        "pollingRateSec": polling_rate_sec,
        "viewPath": view_path,
        "route": route,
        "queryPath": query_path,
        "database": database,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "querySqlSha256": sha256_text(query_sql),
        "readyText": first_ready_text,
        "markerText": f"{run_id} {variant.upper()} READY",
        "previewBuckets": sorted(set([bucket_values[0], bucket_values[-1], "preview-bucket"])),
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Query Parameter Sensitivity {package['variant']}"}],
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


def named_query_preview_payload(request_id: str, project: str, query_path: str, bucket: str, args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "action": "namedQueryPreview",
        "requestId": request_id,
        "targetProject": project,
        "queryPath": query_path,
        "namedQueryPrefix": args.allowed_named_query_prefix,
        "parameters": {"bucket": bucket},
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


def query_read_ok(record: Dict[str, Any]) -> bool:
    response = cp.response(record)
    params = response.get("parameters", [])
    if not isinstance(params, list):
        return False
    return cp.ok(record) and any(isinstance(row, dict) and row.get("identifier") == "bucket" for row in params)


def collect_query_bindings(value: Any, out: List[Dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if value.get("type") == "query" and isinstance(value.get("config"), dict):
            out.append(value)
        for child in value.values():
            collect_query_bindings(child, out)
    elif isinstance(value, list):
        for child in value:
            collect_query_bindings(child, out)


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    response = cp.response(record)
    bindings: List[Dict[str, Any]] = []
    collect_query_bindings(response.get("view", response), bindings)
    query_path = str(package.get("queryPath", ""))
    expected_cache = bool(package.get("cacheAndShare"))
    expected_count = int(package.get("queryCount") or 0)
    expected_buckets = [parameter_literal(str(item)) for item in package.get("bucketValues", [])]
    matched = []
    for binding in bindings:
        config = binding.get("config", {})
        if not isinstance(config, dict):
            continue
        params = config.get("parameters", {})
        if not isinstance(params, dict):
            continue
        if config.get("queryPath") == query_path and bool(config.get("cacheAndShare")) == expected_cache:
            matched.append(str(params.get("bucket", "")))
    return len(matched) >= expected_count and sorted(matched) == sorted(expected_buckets)


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(MULTISESSION_SCRIPT),
        "--run-id",
        child_profile_run_id(args.run_id, str(package["variant"])),
        "--project",
        project,
        "--route",
        package["route"],
        "--view",
        package["viewPath"],
        "--session-counts",
        str(args.session_count),
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
        "--launch-stagger-ms",
        str(args.launch_stagger_ms),
        "--pre-samples",
        str(args.pre_samples),
        "--during-samples",
        str(args.during_samples),
        "--post-samples",
        str(args.post_samples),
        "--interval-sec",
        str(args.interval_sec),
        "--max-metrics",
        str(args.max_metrics),
        "--gateway-alias",
        args.gateway_alias,
        "--out-dir",
        str(profile_dir.resolve()),
    ]
    for item in args.metric_name_contains:
        command.extend(["--metric-name-contains", item])
    for item in args.metric_prefix:
        command.extend(["--metric-prefix", item])
    if args.browser_node_modules:
        command.extend(["--browser-node-modules", args.browser_node_modules])
    if args.wait_for_clean_baseline:
        command.extend(
            [
                "--wait-for-clean-baseline",
                "--baseline-max-browser-sessions",
                str(args.baseline_max_browser_sessions),
                "--baseline-wait-timeout-sec",
                str(args.baseline_wait_timeout_sec),
                "--baseline-wait-interval-sec",
                str(args.baseline_wait_interval_sec),
            ]
        )
        if args.fail_on_baseline_timeout:
            command.append("--fail-on-baseline-timeout")
    return command


def preview_runtime_ready(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    project: str,
    run_id: str,
    variant_name: str,
    package: Dict[str, Any],
) -> Dict[str, Any]:
    deadline = time.time() + max(args.named_query_runtime_wait_timeout_sec, 0.0)
    attempt = 0
    last_results: List[Dict[str, Any]] = []
    while True:
        attempt += 1
        results = []
        for index, preview_bucket in enumerate(package["previewBuckets"], start=1):
            results.append(
                client.call(
                    f"{run_id}-{variant_name}-namedQueryPreview-{attempt:02d}-{index:03d}",
                    named_query_preview_payload(f"{run_id}-{variant_name}-namedQueryPreview-{attempt:02d}-{index:03d}", project, package["queryPath"], preview_bucket, args),
                )
            )
        last_results = results
        if all(cp.ok(record) for record in results):
            return {"ok": True, "attempts": attempt, "records": results}
        if time.time() >= deadline:
            return {"ok": False, "attempts": attempt, "records": last_results}
        time.sleep(max(args.named_query_runtime_wait_interval_sec, 0.1))


def cleanup_checks(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    project: str,
    run_id: str,
    variant_name: str,
    package: Dict[str, Any],
    backup_name: str,
) -> Dict[str, Any]:
    rb_dry = client.call(f"{run_id}-{variant_name}-rollback-dryRun", rollback_payload(f"{run_id}-{variant_name}-rollback-dryRun", project, backup_name, package, True), timeout=args.timeout_sec)
    rb_apply = client.call(f"{run_id}-{variant_name}-rollback-apply", rollback_payload(f"{run_id}-{variant_name}-rollback-apply", project, backup_name, package, False), timeout=args.timeout_sec)
    time.sleep(2)
    routes_check = client.call(
        f"{run_id}-{variant_name}-post-cleanup-routesList",
        {"action": "routesList", "requestId": f"{run_id}-{variant_name}-post-cleanup-routesList", "targetProject": project, "routePrefix": package["route"], "maxResults": 25},
    )
    routes = cp.response(routes_check).get("routes", [])
    routes_list = routes if isinstance(routes, list) else []
    route_still_present = any(isinstance(item, dict) and item.get("pagePath") == package["route"] for item in routes_list)
    after_read = client.call(f"{run_id}-{variant_name}-post-cleanup-viewRead", cache_common.view_read_payload(f"{run_id}-{variant_name}-post-cleanup-viewRead", project, package["viewPath"], args))
    query_after = client.call(f"{run_id}-{variant_name}-post-cleanup-namedQueryRead", cache_common.named_query_read_payload(f"{run_id}-{variant_name}-post-cleanup-namedQueryRead", project, package["queryPath"], args))
    return {
        "rollbackOk": cp.ok(rb_dry) and cp.ok(rb_apply),
        "cleanupRouteAbsent": cp.ok(routes_check) and not route_still_present,
        "cleanupViewAbsent": not cp.ok(after_read),
        "cleanupNamedQueryAbsent": not cp.ok(query_after),
    }


def metric_delta(row: Dict[str, Any]) -> Optional[float]:
    metrics = row.get("metricSummary", {}) if isinstance(row.get("metricSummary"), dict) else {}
    return to_float(metrics.get("primaryDatabaseQueryDuringDelta"))


def reduction_summary(off_value: Optional[float], on_value: Optional[float]) -> Dict[str, Any]:
    reduction = None
    ratio = None
    threshold = meaningful_threshold(off_value)
    if off_value is not None and on_value is not None:
        reduction = off_value - on_value
        ratio = on_value / off_value if off_value else None
    return {
        "off": off_value,
        "on": on_value,
        "onMinusOff": delta(off_value, on_value),
        "reductionFromOff": reduction,
        "onVsOffRatio": ratio,
        "minimumReduction": threshold,
        "observedReduction": bool(reduction is not None and threshold is not None and reduction >= threshold),
    }


def compare_variants(variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_name = {str(row.get("variant")): row for row in variants}
    same_off = metric_delta(by_name.get("same-param-cache-off", {}))
    same_on = metric_delta(by_name.get("same-param-cache-on", {}))
    distinct_off = metric_delta(by_name.get("distinct-param-cache-off", {}))
    distinct_on = metric_delta(by_name.get("distinct-param-cache-on", {}))
    off_shape_delta = meaningful_change_delta(same_off, distinct_off)
    on_shape_delta = meaningful_change_delta(same_on, distinct_on)
    off_shape_threshold = meaningful_threshold(same_off)
    on_shape_threshold = meaningful_threshold(same_on)
    return {
        "sameParamCacheOffDatabaseQueryDuringDelta": same_off,
        "sameParamCacheOnDatabaseQueryDuringDelta": same_on,
        "distinctParamCacheOffDatabaseQueryDuringDelta": distinct_off,
        "distinctParamCacheOnDatabaseQueryDuringDelta": distinct_on,
        "sameParamCacheReduction": reduction_summary(same_off, same_on),
        "distinctParamCacheReduction": reduction_summary(distinct_off, distinct_on),
        "distinctMinusSameCacheOffDatabaseQueryDuringDelta": off_shape_delta,
        "distinctMinusSameCacheOnDatabaseQueryDuringDelta": on_shape_delta,
        "minimumDifferenceForParameterShapeOff": off_shape_threshold,
        "minimumDifferenceForParameterShapeOn": on_shape_threshold,
        "parameterShapeVisibleWithCacheOff": bool(off_shape_delta is not None and off_shape_threshold is not None and abs(off_shape_delta) >= off_shape_threshold),
        "parameterShapeVisibleWithCacheOn": bool(on_shape_delta is not None and on_shape_threshold is not None and abs(on_shape_delta) >= on_shape_threshold),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Query Parameter Sensitivity Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        f"Stack: `{summary.get('stackVersion')}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | Param shape | Cache & Share | OK | Browser query-ready | DB query delta | Property-change delta | Cleanup |",
        "|---|---|---:|---|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        metrics = row.get("metricSummary", {}) if isinstance(row.get("metricSummary"), dict) else {}
        profile = row.get("profileSummary", {}) if isinstance(row.get("profileSummary"), dict) else {}
        cleanup = row.get("cleanup", {}) if isinstance(row.get("cleanup"), dict) else {}
        cleanup_ok = cleanup.get("rollbackOk") and cleanup.get("cleanupRouteAbsent") and cleanup.get("cleanupViewAbsent") and cleanup.get("cleanupNamedQueryAbsent")
        lines.append(
            "| {variant} | {shape} | `{cache}` | `{ok}` | {ready}/{total} | {db_delta} | {prop_delta} | `{cleanup}` |".format(
                variant=row.get("variant"),
                shape=row.get("parameterShape"),
                cache=str(row.get("cacheAndShare")).lower(),
                ok=str(row.get("ok", False)).lower(),
                ready=format_number(profile.get("browserReadyTextMatchedCount")),
                total=format_number(profile.get("browserProbeCount")),
                db_delta=format_number(metrics.get("primaryDatabaseQueryDuringDelta")),
                prop_delta=format_number(metrics.get("primaryPerspectivePropertyChangesDuringDelta")),
                cleanup=str(bool(cleanup_ok)).lower(),
            )
        )
    comparison = summary.get("comparison", {})
    lines.extend(["", "## Comparison", ""])
    for key in [
        "sameParamCacheOffDatabaseQueryDuringDelta",
        "sameParamCacheOnDatabaseQueryDuringDelta",
        "distinctParamCacheOffDatabaseQueryDuringDelta",
        "distinctParamCacheOnDatabaseQueryDuringDelta",
        "distinctMinusSameCacheOffDatabaseQueryDuringDelta",
        "distinctMinusSameCacheOnDatabaseQueryDuringDelta",
        "minimumDifferenceForParameterShapeOff",
        "minimumDifferenceForParameterShapeOn",
        "parameterShapeVisibleWithCacheOff",
        "parameterShapeVisibleWithCacheOn",
    ]:
        lines.append(f"- `{key}`: `{format_number(comparison.get(key))}`")
    for label, value in [
        ("sameParamCacheReduction", comparison.get("sameParamCacheReduction", {})),
        ("distinctParamCacheReduction", comparison.get("distinctParamCacheReduction", {})),
    ]:
        lines.append(f"- `{label}`: `{canonical_json(value)}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    env = common.collect_env(endpoint, token, project)
    base = compact(args.run_id)

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    feature_set = cache_common.feature_set_from_health(health)
    db_record = client.call(f"{args.run_id}-databaseConnectionsList", {"action": "databaseConnectionsList", "requestId": f"{args.run_id}-databaseConnectionsList"})
    database = cache_common.refresh_common.choose_database(db_record, args.database)
    if not database:
        raise RuntimeError("No database connection available for disposable Named Query fixture")

    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    for variant_name in VARIANTS:
        variant_dir = out_dir / variant_name
        variant_dir.mkdir(parents=True, exist_ok=True)
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        view_suffix = "".join(part.title() for part in variant_name.split("-"))
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/QueryParameter{view_suffix}"
        query_path = f"{args.named_query_path_prefix.rstrip('/')}/{base}/QueryParameter{view_suffix}"
        package = build_package(variant_dir, project, args.run_id, variant_name, view_path, route, query_path, database, args.query_count, args.polling_rate_sec)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        backup_name = ""
        gates: Dict[str, bool] = {}
        variant: Dict[str, Any]
        try:
            dry = client.call(f"{args.run_id}-{variant_name}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant_name}-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry)
            if not gates["dryRun"]:
                raise RuntimeError("dryRun failed")
            apply = client.call(f"{args.run_id}-{variant_name}-apply", package_payload("apply", f"{args.run_id}-{variant_name}-apply", project, package, args), timeout=args.timeout_sec)
            backup_name = common.backup_name_from_response(cp.response(apply))
            gates["apply"] = cp.ok(apply) and bool(backup_name)
            if not gates["apply"]:
                raise RuntimeError("apply failed")
            time.sleep(args.runtime_route_wait_sec)
            query_read = client.call(f"{args.run_id}-{variant_name}-namedQueryRead", cache_common.named_query_read_payload(f"{args.run_id}-{variant_name}-namedQueryRead", project, query_path, args))
            gates["namedQueryRead"] = query_read_ok(query_read)
            preview_wait = preview_runtime_ready(client, args, project, args.run_id, variant_name, package)
            gates["namedQueryPreview"] = preview_wait.get("ok") is True
            readback = client.call(f"{args.run_id}-{variant_name}-viewRead", cache_common.view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, view_path, args))
            gates["viewRead"] = cp.ok(readback) and readback_ok(readback, package)
            page = client.call(f"{args.run_id}-{variant_name}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = (variant_dir / "profile").resolve()
            profile_label = f"profile-{child_profile_run_id('qparam', variant_name)}"
            profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), profile_label, variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and cache_common.profile_ok(profile_dir)
            variant = {
                "variant": variant_name,
                "parameterShape": package["parameterShape"],
                "uniqueBucketCount": package["uniqueBucketCount"],
                "cacheAndShare": package["cacheAndShare"],
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "queryPath": query_path,
                "backupName": backup_name,
                "namedQueryPreviewWait": {"ok": preview_wait.get("ok"), "attempts": preview_wait.get("attempts")},
                "profileDir": str(profile_dir),
                "profileSummary": cache_common.profile_summary(profile_dir),
                "metricSummary": cache_common.summarize_metric_counts(profile_dir),
                "profileCommand": profile_result,
            }
        except Exception as exc:
            variant = {
                "variant": variant_name,
                "parameterShape": package["parameterShape"],
                "uniqueBucketCount": package["uniqueBucketCount"],
                "cacheAndShare": package["cacheAndShare"],
                "ok": False,
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "queryPath": query_path,
                "backupName": backup_name,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                cleanup = cleanup_checks(client, args, project, args.run_id, variant_name, package, backup_name)
                variant["cleanup"] = cleanup
                variant["ok"] = bool(
                    variant.get("ok")
                    and cleanup.get("rollbackOk")
                    and cleanup.get("cleanupRouteAbsent")
                    and cleanup.get("cleanupViewAbsent")
                    and cleanup.get("cleanupNamedQueryAbsent")
                )
            variants.append(variant)
            if args.pause_sec > 0 and variant_name != VARIANTS[-1]:
                time.sleep(args.pause_sec)

    comparison = compare_variants(variants)
    same_reduction = comparison.get("sameParamCacheReduction", {})
    distinct_reduction = comparison.get("distinctParamCacheReduction", {})
    summary = {
        "ok": bool(cp.ok(health) and cp.ok(db_record) and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "features": sorted(feature_set),
        "database": "<databaseConnection>",
        "actualDatabaseEvidence": database,
        "queryCount": args.query_count,
        "pollingRateSec": args.polling_rate_sec,
        "sessionCount": args.session_count,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "runtimeRouteWaitSeconds": args.runtime_route_wait_sec,
        "variants": variants,
        "comparison": comparison,
        "packages": package_records,
        "interpretation": [
            "This is a controlled parameterized-query fixture, not a customer route conclusion.",
            "All variants use one read-only Query-type Named Query path, the same number of visible query-bound labels, one required Value parameter named bucket, and the same polling/session cadence.",
            "Perspective binding parameters are authored as expression strings; literal bucket values are JSON-encoded string literals in config.parameters.bucket.",
            "The browser-ready text includes the expected query-returned bucket value, so a transform fallback or empty/error label cannot satisfy readiness by prefix alone.",
            "Treat Cache & Share consolidation as observed only when the database query-count delta falls by the declared meaningful threshold for the same parameter shape.",
            "Treat parameter-shape sensitivity as observed only when distinct-parameter deltas differ from identical-parameter deltas by the declared meaningful threshold.",
            f"Same-parameter cache reduction observed: {bool(isinstance(same_reduction, dict) and same_reduction.get('observedReduction'))}.",
            f"Distinct-parameter cache reduction observed: {bool(isinstance(distinct_reduction, dict) and distinct_reduction.get('observedReduction'))}.",
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
    parser.add_argument("--database", default="", help="Database connection for disposable read-only Named Query. Defaults to first valid connection.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--query-count", type=int, default=8)
    parser.add_argument("--polling-rate-sec", type=int, default=1)
    parser.add_argument("--session-count", type=int, default=5)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--named-query-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--allowed-named-query-prefix", default=DEFAULT_ALLOWED_NAMED_QUERY_PREFIX)
    parser.add_argument("--pre-samples", type=int, default=2)
    parser.add_argument("--during-samples", type=int, default=7)
    parser.add_argument("--post-samples", type=int, default=2)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=40)
    parser.add_argument(
        "--metric-name-contains",
        action="append",
        default=["Perspective", "perspective", "database", "Database", "databases"],
        help="Metric substring filter passed to run_multisession_profile.py. Repeatable.",
    )
    parser.add_argument("--metric-prefix", action="append", default=[], help="Metric prefix filter passed to run_multisession_profile.py. Repeatable.")
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=900)
    parser.add_argument("--named-query-runtime-wait-timeout-sec", type=float, default=30.0, help="Maximum seconds to wait for a newly imported Named Query to be executable by namedQueryPreview.")
    parser.add_argument("--named-query-runtime-wait-interval-sec", type=float, default=2.0, help="Seconds between namedQueryPreview runtime readiness attempts.")
    parser.add_argument("--runtime-route-wait-sec", type=float, default=2.0, help="Seconds to wait after page validation before browser runtime profiling.")
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=75.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=18000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--launch-stagger-ms", type=int, default=250)
    parser.add_argument("--pause-sec", type=float, default=5.0)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each session group, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline per variant session group.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Mark the variant failed when a clean baseline is requested but not reached.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.query_count < 1:
        raise SystemExit("--query-count must be >= 1")
    if args.polling_rate_sec < 1:
        raise SystemExit("--polling-rate-sec must be >= 1")
    if args.session_count < 1:
        raise SystemExit("--session-count must be >= 1")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0:
        raise SystemExit("--baseline-wait-timeout-sec must be >= 0")
    if args.baseline_wait_interval_sec < 0:
        raise SystemExit("--baseline-wait-interval-sec must be >= 0")
    if args.named_query_runtime_wait_timeout_sec < 0:
        raise SystemExit("--named-query-runtime-wait-timeout-sec must be >= 0")
    if args.named_query_runtime_wait_interval_sec < 0:
        raise SystemExit("--named-query-runtime-wait-interval-sec must be >= 0")
    if args.runtime_route_wait_sec < 0:
        raise SystemExit("--runtime-route-wait-sec must be >= 0")
    summary = run(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
