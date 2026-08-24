#!/usr/bin/env python3
"""Run guarded query-binding multiplicity sensitivity fixtures.

This A-01b helper checks whether the selected database query metric responds
to a larger number of query-bound Perspective properties before Cache & Share
deltas are interpreted.
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
VARIANTS = ["one-bound", "same-path", "distinct-paths"]
MIN_SENSITIVITY_INCREASE_COUNT = 3.0
MIN_SENSITIVITY_INCREASE_RATIO = 0.50
MIN_DISTINCT_PATH_DIFFERENCE_COUNT = 3.0
MIN_DISTINCT_PATH_DIFFERENCE_RATIO = 0.20


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


def title_for_variant(variant: str) -> str:
    return {
        "one-bound": "One bound query",
        "same-path": "Many bindings, one query path",
        "distinct-paths": "Many bindings, distinct query paths",
    }.get(variant, variant)


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-query-sensitivity-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def query_paths_for_variant(base_query_path: str, variant: str, label_count: int) -> List[str]:
    if variant == "distinct-paths":
        return [f"{base_query_path}/Tick{index:03d}" for index in range(1, label_count + 1)]
    return [f"{base_query_path}/Tick"]


def query_path_for_label(query_paths: List[str], variant: str, index: int) -> str:
    if variant == "distinct-paths":
        return query_paths[index - 1]
    return query_paths[0]


def binding_enabled_for_label(variant: str, index: int) -> bool:
    return variant != "one-bound" or index == 1


def label_component(
    index: int,
    variant: str,
    query_paths: List[str],
    polling_rate_sec: int,
) -> Dict[str, Any]:
    label_name = f"TickLabel{index:03d}"
    bound = binding_enabled_for_label(variant, index)
    prefix = f"{title_for_variant(variant)} {index:03d}"
    props = {
        "text": f"{prefix}: {'pending' if bound else 'static placeholder'}",
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
    }
    prop_config = None
    if bound:
        prop_config = {
            "props.text": cache_common.cache_query_binding(
                query_path_for_label(query_paths, variant, index),
                False,
                polling_rate_sec,
                prefix,
            )
        }
    return cache_common.refresh_common.component(
        "ia.display.label",
        meta={"name": label_name},
        position={"basis": "30px", "grow": 0, "shrink": 0},
        props=props,
        prop_config=prop_config,
    )


def make_view_json(
    run_id: str,
    variant: str,
    query_paths: List[str],
    label_count: int,
    polling_rate_sec: int,
) -> Dict[str, Any]:
    marker = f"{run_id} {variant.upper()} READY"
    query_bound_count = 1 if variant == "one-bound" else label_count
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
                f"A-01b query metric sensitivity fixture: {label_count} visible labels, "
                f"{query_bound_count} query-bound labels, {len(query_paths)} named query path(s), "
                f"{polling_rate_sec}s polling, cacheAndShare=false."
            ),
            "Fixture Summary",
            "54px",
            {"color": "#1f2937", "whiteSpace": "pre-wrap"},
        ),
        cache_common.label(
            "Purpose: prove whether the database query metric rises when query-binding multiplicity rises.",
            "Sensitivity Purpose",
            "38px",
            {"backgroundColor": "#eef2ff", "borderColor": "#c7d2fe", "borderStyle": "solid", "borderWidth": "1px"},
        ),
    ]
    children.extend(label_component(index, variant, query_paths, polling_rate_sec) for index in range(1, label_count + 1))
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "labelCount": label_count,
            "queryBoundCount": query_bound_count,
            "namedQueryPathCount": len(query_paths),
            "pollingEnabled": True,
            "pollingRateSec": polling_rate_sec,
            "cacheAndShare": False,
            "testPurpose": "database query metric sensitivity before Cache & Share interpretation",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": cache_common.refresh_common.component(
            "ia.container.flex",
            meta={"name": "query-multiplicity-sensitivity-root"},
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


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    view_path: str,
    route: str,
    query_paths: List[str],
    database: str,
    label_count: int,
    polling_rate_sec: int,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-query-sensitivity"
    view_json = make_view_json(run_id, variant, query_paths, label_count, polling_rate_sec)
    query_sql = "SELECT strftime('%Y%m%dT%H%M%f','now') || '-' || hex(randomblob(4)) AS refresh_tick LIMIT 1"
    zip_path = zip_dir / f"qs-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-query-sens-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler query multiplicity sensitivity fixture", "enabled": True, "inheritable": False})
        cache_common.refresh_common.write_view(project_root, view_path, view_json, actor)
        for query_path in query_paths:
            cache_common.refresh_common.write_named_query(project_root, query_path, query_sql, database, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Query Sensitivity {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", cache_common.fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    query_bound_count = 1 if variant == "one-bound" else label_count
    return {
        "variant": variant,
        "labelCount": label_count,
        "queryBoundCount": query_bound_count,
        "namedQueryPathCount": len(query_paths),
        "pollingRateSec": polling_rate_sec,
        "cacheAndShare": False,
        "viewPath": view_path,
        "route": route,
        "queryPaths": query_paths,
        "database": database,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "querySqlSha256": sha256_text(query_sql),
        "readyText": f"{run_id} {variant.upper()} READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Query Sensitivity {package['variant']}"}],
        "dependencyViewPaths": [],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": list(package["queryPaths"]),
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
        "dependencyNamedQueryPaths": list(package["queryPaths"]),
    }


def rollback_payload(request_id: str, project: str, backup_name: str, package: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "rollback",
        "requestId": request_id,
        "targetProject": project,
        "backupName": backup_name,
        "viewPaths": [package["viewPath"]],
        "scriptPaths": [],
        "namedQueryPaths": list(package["queryPaths"]),
        "dryRun": dry_run,
        "removeMissingViews": True,
        "removeMissingScripts": False,
        "removeMissingNamedQueries": True,
    }
    if not dry_run:
        payload["confirmRollback"] = "ROLLBACK"
    return payload


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    text = canonical_json(cp.response(record))
    query_paths = package.get("queryPaths", [])
    if not isinstance(query_paths, list):
        return False
    expected_cache = '"cacheAndShare":false'
    expected_bindings = int(package.get("queryBoundCount") or 0)
    return (
        all(str(query_path) in text for query_path in query_paths)
        and expected_cache in text
        and text.count('"type":"query"') >= expected_bindings
    )


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(MULTISESSION_SCRIPT),
        "--run-id",
        f"{args.run_id}-query-sensitivity-{package['variant']}",
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
        str(profile_dir),
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
    query_results = []
    for index, query_path in enumerate(package.get("queryPaths", []), start=1):
        query_results.append(
            client.call(
                f"{run_id}-{variant_name}-post-cleanup-namedQueryRead-{index:03d}",
                cache_common.named_query_read_payload(f"{run_id}-{variant_name}-post-cleanup-namedQueryRead-{index:03d}", project, str(query_path), args),
            )
        )
    return {
        "rollbackOk": cp.ok(rb_dry) and cp.ok(rb_apply),
        "cleanupRouteAbsent": cp.ok(routes_check) and not route_still_present,
        "cleanupViewAbsent": not cp.ok(after_read),
        "cleanupNamedQueriesAbsent": all(not cp.ok(record) for record in query_results),
        "cleanupNamedQueryCount": len(query_results),
    }


def compare_variants(variants: List[Dict[str, Any]], label_count: int) -> Dict[str, Any]:
    by_name = {str(row.get("variant")): row for row in variants}

    def db_delta(variant: str) -> Optional[float]:
        metrics = by_name.get(variant, {}).get("metricSummary", {})
        if not isinstance(metrics, dict):
            return None
        return to_float(metrics.get("primaryDatabaseQueryDuringDelta"))

    one_delta = db_delta("one-bound")
    shared_delta = db_delta("same-path")
    distinct_delta = db_delta("distinct-paths")
    shared_minus_one = delta(one_delta, shared_delta)
    distinct_minus_shared = delta(shared_delta, distinct_delta)
    minimum_increase = None
    if one_delta is not None:
        minimum_increase = max(MIN_SENSITIVITY_INCREASE_COUNT, abs(one_delta) * MIN_SENSITIVITY_INCREASE_RATIO)
    counter_sensitive = (
        one_delta is not None
        and shared_delta is not None
        and shared_minus_one is not None
        and shared_delta > one_delta
        and minimum_increase is not None
        and shared_minus_one >= minimum_increase
    )
    distinct_difference_threshold = None
    if shared_delta is not None:
        distinct_difference_threshold = max(MIN_DISTINCT_PATH_DIFFERENCE_COUNT, abs(shared_delta) * MIN_DISTINCT_PATH_DIFFERENCE_RATIO)
    distinct_path_difference = (
        distinct_minus_shared is not None
        and distinct_difference_threshold is not None
        and abs(distinct_minus_shared) >= distinct_difference_threshold
    )
    distinct_path_increase = bool(distinct_path_difference and distinct_delta is not None and shared_delta is not None and distinct_delta > shared_delta)
    same_path_extra_bindings_visible = bool(counter_sensitive)
    return {
        "oneBoundDatabaseQueryDuringDelta": one_delta,
        "samePathDatabaseQueryDuringDelta": shared_delta,
        "distinctPathsDatabaseQueryDuringDelta": distinct_delta,
        "samePathMinusOneBoundDatabaseQueryDuringDelta": shared_minus_one,
        "distinctPathsMinusSamePathDatabaseQueryDuringDelta": distinct_minus_shared,
        "expectedManyVsOneBindingRatio": label_count,
        "observedSamePathVsOneBoundRatio": (shared_delta / one_delta) if one_delta not in (None, 0) and shared_delta is not None else None,
        "observedDistinctPathsVsOneBoundRatio": (distinct_delta / one_delta) if one_delta not in (None, 0) and distinct_delta is not None else None,
        "minimumIncreaseForCounterSensitivity": minimum_increase,
        "counterSensitiveToBindingMultiplicity": bool(counter_sensitive),
        "samePathExtraBindingsVisibleInDatabaseMetric": same_path_extra_bindings_visible,
        "minimumDifferenceForDistinctPathEffect": distinct_difference_threshold,
        "distinctPathsMeaningfullyDifferentFromSamePath": bool(distinct_path_difference),
        "counterSensitiveToDistinctPathMultiplicity": distinct_path_increase,
        "interpretation": (
            "The primary database query metric rose meaningfully from one bound query label to many same-path query labels."
            if counter_sensitive
            else (
                "The primary database query metric did not show a meaningful one-bound to many same-path binding increase, but it did rise for distinct query paths."
                if distinct_path_increase
                else "The primary database query metric did not show a meaningful one-bound to many-bound increase in this run."
            )
        ),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Query Multiplicity Sensitivity Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        f"Stack: `{summary.get('stackVersion')}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | Labels | Query-bound labels | Query paths | OK | Browser ready | DB query delta | Property-change delta | Cleanup |",
        "|---|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        metrics = row.get("metricSummary", {}) if isinstance(row.get("metricSummary"), dict) else {}
        profile = row.get("profileSummary", {}) if isinstance(row.get("profileSummary"), dict) else {}
        cleanup = row.get("cleanup", {}) if isinstance(row.get("cleanup"), dict) else {}
        cleanup_ok = cleanup.get("rollbackOk") and cleanup.get("cleanupRouteAbsent") and cleanup.get("cleanupViewAbsent") and cleanup.get("cleanupNamedQueriesAbsent")
        lines.append(
            "| {variant} | {labels} | {bound} | {paths} | `{ok}` | {ready}/{total} | {db_delta} | {prop_delta} | `{cleanup}` |".format(
                variant=row.get("variant"),
                labels=row.get("labelCount"),
                bound=row.get("queryBoundCount"),
                paths=row.get("namedQueryPathCount"),
                ok=str(row.get("ok", False)).lower(),
                ready=format_number(profile.get("browserReadyTextMatchedCount")),
                total=format_number(profile.get("browserProbeCount")),
                db_delta=format_number(metrics.get("primaryDatabaseQueryDuringDelta")),
                prop_delta=format_number(metrics.get("primaryPerspectivePropertyChangesDuringDelta")),
                cleanup=str(bool(cleanup_ok)).lower(),
            )
        )
    lines.extend(["", "## Comparison", ""])
    comparison = summary.get("comparison", {})
    for key in [
        "oneBoundDatabaseQueryDuringDelta",
        "samePathDatabaseQueryDuringDelta",
        "distinctPathsDatabaseQueryDuringDelta",
        "samePathMinusOneBoundDatabaseQueryDuringDelta",
        "distinctPathsMinusSamePathDatabaseQueryDuringDelta",
        "observedSamePathVsOneBoundRatio",
        "observedDistinctPathsVsOneBoundRatio",
        "minimumIncreaseForCounterSensitivity",
        "counterSensitiveToBindingMultiplicity",
        "samePathExtraBindingsVisibleInDatabaseMetric",
        "minimumDifferenceForDistinctPathEffect",
        "distinctPathsMeaningfullyDifferentFromSamePath",
        "counterSensitiveToDistinctPathMultiplicity",
    ]:
        lines.append(f"- `{key}`: `{format_number(comparison.get(key))}`")
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
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/QuerySensitivity{view_suffix}"
        query_base = f"{args.named_query_path_prefix.rstrip('/')}/{base}/QuerySensitivity{view_suffix}"
        query_paths = query_paths_for_variant(query_base, variant_name, args.label_count)
        package = build_package(variant_dir, project, args.run_id, variant_name, view_path, route, query_paths, database, args.label_count, args.polling_rate_sec)
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
            time.sleep(2)
            read_results = []
            preview_results = []
            for index, query_path in enumerate(query_paths, start=1):
                read_results.append(client.call(f"{args.run_id}-{variant_name}-namedQueryRead-{index:03d}", cache_common.named_query_read_payload(f"{args.run_id}-{variant_name}-namedQueryRead-{index:03d}", project, query_path, args)))
                preview_results.append(client.call(f"{args.run_id}-{variant_name}-namedQueryPreview-{index:03d}", cache_common.named_query_preview_payload(f"{args.run_id}-{variant_name}-namedQueryPreview-{index:03d}", project, query_path, args)))
            gates["namedQueryRead"] = all(cp.ok(record) for record in read_results)
            gates["namedQueryPreview"] = all(cp.ok(record) for record in preview_results)
            readback = client.call(f"{args.run_id}-{variant_name}-viewRead", cache_common.view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, view_path, args))
            gates["viewRead"] = cp.ok(readback) and readback_ok(readback, package)
            page = client.call(f"{args.run_id}-{variant_name}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = (variant_dir / "profile").resolve()
            profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), f"profile-query-sensitivity-{variant_name}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and cache_common.profile_ok(profile_dir)
            variant = {
                "variant": variant_name,
                "labelCount": package["labelCount"],
                "queryBoundCount": package["queryBoundCount"],
                "namedQueryPathCount": package["namedQueryPathCount"],
                "cacheAndShare": False,
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "queryPaths": query_paths,
                "backupName": backup_name,
                "profileDir": str(profile_dir),
                "profileSummary": cache_common.profile_summary(profile_dir),
                "metricSummary": cache_common.summarize_metric_counts(profile_dir),
                "profileCommand": profile_result,
            }
        except Exception as exc:
            variant = {
                "variant": variant_name,
                "labelCount": package["labelCount"],
                "queryBoundCount": package["queryBoundCount"],
                "namedQueryPathCount": package["namedQueryPathCount"],
                "cacheAndShare": False,
                "ok": False,
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "queryPaths": query_paths,
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
                    and cleanup.get("cleanupNamedQueriesAbsent")
                )
            variants.append(variant)
            if args.pause_sec > 0 and variant_name != VARIANTS[-1]:
                time.sleep(args.pause_sec)

    comparison = compare_variants(variants, args.label_count)
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
        "labelCount": args.label_count,
        "pollingRateSec": args.polling_rate_sec,
        "sessionCount": args.session_count,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparison": comparison,
        "packages": package_records,
        "interpretation": [
            "This is a controlled A-01b sensitivity fixture, not a customer route conclusion.",
            "All variants keep the same visible label count; the intended workload change is the number and shape of query bindings.",
            "Cache & Share is disabled in every variant so this run measures database-query counter sensitivity, not a Cache & Share remediation.",
            "Use the one-bound to same-path increase to decide whether the primary database metric is sensitive enough for later Cache & Share interpretation.",
            "Use the distinct-paths versus same-path difference only as a path-shape observation; it is not by itself an optimization rule.",
            str(comparison.get("interpretation", "")),
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
    parser.add_argument("--label-count", type=int, default=8)
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
    if args.label_count < 2:
        raise SystemExit("--label-count must be >= 2")
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
    summary = run(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
