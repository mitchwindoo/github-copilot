#!/usr/bin/env python3
"""Run guarded Perspective tag-history Cache & Share off/on fixtures."""

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
import run_query_cache_share_ab as query_common
import run_refresh_binding_ab as refresh_common
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
MULTISESSION_SCRIPT = SCRIPT_DIR / "run_multisession_profile.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
DEFAULT_TAG_PROVIDER = "default"
DEFAULT_TAG_FOLDER = "LLM Tests/PerformanceProfiler"
MIN_CONSOLIDATION_REDUCTION_COUNT = 3.0
MIN_CONSOLIDATION_REDUCTION_RATIO = 0.20


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
    return query_common.format_number(value)


def to_float(value: Any) -> Optional[float]:
    return query_common.to_float(value)


def delta(before: Any, after: Any) -> Optional[float]:
    return query_common.delta(before, after)


def label(text: str, name: str, basis: str = "34px", style: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    merged = {
        "color": "#111827",
        "fontSize": 13,
        "overflow": "hidden",
        "padding": "7px 8px",
        "textOverflow": "ellipsis",
        "whiteSpace": "nowrap",
    }
    if style:
        merged.update(style)
    return refresh_common.component(
        "ia.display.label",
        meta={"name": name},
        position={"basis": basis, "grow": 0, "shrink": 0},
        props={"text": text, "style": merged},
    )


def fully_qualified_tag_path(base_path: str, tag_name: str) -> str:
    return f"{base_path.rstrip('/')}/{tag_name}"


def default_tag_base_path(args: argparse.Namespace) -> str:
    if args.tag_base_path:
        return args.tag_base_path.rstrip("/")
    provider = args.tag_provider.strip() or DEFAULT_TAG_PROVIDER
    return f"[{provider}]{DEFAULT_TAG_FOLDER}/{compact(args.run_id)}/HistoryTags"


def default_allowed_tag_prefix(args: argparse.Namespace) -> str:
    if args.allowed_tag_path_prefix:
        return args.allowed_tag_path_prefix.rstrip("/")
    provider = args.tag_provider.strip() or DEFAULT_TAG_PROVIDER
    return f"[{provider}]{DEFAULT_TAG_FOLDER}"


def history_tag_definitions(tag_count: int, history_provider: str) -> List[Dict[str, Any]]:
    tags: List[Dict[str, Any]] = []
    for index in range(1, tag_count + 1):
        offset = (index - 1) * 100
        expression = 'toFloat(dateExtract(now(1000), "second"))'
        if offset:
            expression = f'toFloat(dateExtract(now(1000), "second") + {offset})'
        tags.append(
            {
                "name": f"HistExpr{index:03d}",
                "tagType": "AtomicTag",
                "valueSource": "expr",
                "dataType": "Float8",
                "expression": expression,
                "executionMode": "FixedRate",
                "executionRate": 1000,
                "historyEnabled": True,
                "historyProvider": history_provider,
                "sampleMode": "Periodic",
                "historySampleRate": 1,
                "historySampleRateUnits": "SEC",
                "historicalDeadbandMode": "Off",
                "historicalDeadbandStyle": "Discrete",
                "historyMaxAge": 1,
                "historyMaxAgeUnits": "SEC",
            }
        )
    return tags


def tag_configure_payload(
    request_id: str,
    base_path: str,
    allowed_prefix: str,
    tags: List[Dict[str, Any]],
    collision_policy: str,
    dry_run: bool,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "tagConfigure",
        "requestId": request_id,
        "basePath": base_path,
        "allowedTagPathPrefixes": [allowed_prefix],
        "tags": tags,
        "collisionPolicy": collision_policy,
        "dryRun": dry_run,
        "maxItems": max(10, len(tags) + 2),
    }
    if not dry_run:
        payload["confirmTagConfigure"] = "CONFIGURE_TAGS"
    return payload


def tag_read_payload(request_id: str, paths: List[str]) -> Dict[str, Any]:
    return {"action": "tagRead", "requestId": request_id, "paths": paths, "maxResults": max(10, len(paths) + 2)}


def history_probe_payload(request_id: str, paths: List[str], args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "action": "historyProbe",
        "requestId": request_id,
        "paths": paths,
        "maxPaths": len(paths),
        "rangeMinutes": args.history_range_minutes,
        "returnSize": args.history_return_rows,
        "sampleRows": min(5, args.history_return_rows),
        "aggregationMode": args.history_aggregation,
    }


def tag_read_ok(record: Dict[str, Any], paths: List[str]) -> bool:
    response = cp.response(record)
    reads = response.get("reads", [])
    if not cp.ok(record) or not isinstance(reads, list):
        return False
    good_paths = {
        str(item.get("path"))
        for item in reads
        if isinstance(item, dict) and str(item.get("quality", "")).lower().startswith("good")
    }
    return all(path in good_paths for path in paths)


def history_probe_ok(record: Dict[str, Any], paths: List[str]) -> bool:
    response = cp.response(record)
    stats = response.get("tagStats", [])
    if not cp.ok(record) or response.get("historyAvailable") is not True:
        return False
    if not isinstance(stats, list):
        return False
    if response.get("historyAvailabilityMode") == "storedSamples" or any(
        isinstance(item, dict) and "storedSampleCount" in item for item in stats
    ):
        paths_with_samples = {
            str(item.get("path"))
            for item in stats
            if isinstance(item, dict) and to_float(item.get("storedSampleCount")) not in (None, 0.0)
        }
        return all(path in paths_with_samples for path in paths)
    paths_with_data = {
        str(item.get("path"))
        for item in stats
        if isinstance(item, dict) and item.get("hasData") is True and to_float(item.get("nonNullCount")) not in (None, 0.0)
    }
    return all(path in paths_with_data for path in paths)


def wait_for_history(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    run_id: str,
    paths: List[str],
    out_dir: Path,
) -> Dict[str, Any]:
    started = time.time()
    attempts: List[Dict[str, Any]] = []
    if args.history_warmup_sec > 0:
        time.sleep(args.history_warmup_sec)
    attempt = 0
    while True:
        request_id = f"{run_id}-historyProbe-{attempt:03d}"
        record = client.call(request_id, history_probe_payload(request_id, paths, args), timeout=args.timeout_sec)
        response = cp.response(record)
        row = {
            "attempt": attempt,
            "sampledAt": utc_now(),
            "elapsedSeconds": round(time.time() - started, 3),
            "ok": cp.ok(record),
            "historyAvailable": response.get("historyAvailable"),
            "historyAvailabilityMode": response.get("historyAvailabilityMode"),
            "storedSampleCount": response.get("storedSampleCount"),
            "sampleCountQueryOk": response.get("sampleCountQueryOk"),
            "rowCount": response.get("rowCount"),
            "tagStats": response.get("tagStats"),
        }
        cp.append_ndjson(out_dir / "history-wait-samples.ndjson", row)
        attempts.append(row)
        if history_probe_ok(record, paths):
            return {"ok": True, "record": record, "attempts": attempts, "timedOut": False}
        if time.time() - started >= args.history_wait_timeout_sec:
            return {"ok": False, "record": record, "attempts": attempts, "timedOut": True}
        attempt += 1
        time.sleep(max(args.history_wait_interval_sec, 0.5))


def history_transform(prefix: str) -> str:
    return (
        "\ttry:\n"
        "\t\tif value is not None and hasattr(value, 'getRowCount'):\n"
        "\t\t\trows = value.getRowCount()\n"
        "\t\t\tcols = value.getColumnCount() if hasattr(value, 'getColumnCount') else 0\n"
        "\t\t\tif rows > 0:\n"
        "\t\t\t\tcol = 1 if cols > 1 else 0\n"
        "\t\t\t\tlast = value.getValueAt(rows - 1, col)\n"
        f"\t\t\t\treturn '{prefix}: rows=' + str(rows) + ' cols=' + str(cols) + ' last=' + str(last)\n"
        "\t\texcept_msg = ''\n"
        "\texcept Exception as err:\n"
        "\t\texcept_msg = ' error: ' + str(err)\n"
        f"\treturn '{prefix}: pending' + except_msg\n"
    )


def tag_history_binding(
    paths: List[str],
    cache_enabled: bool,
    polling_rate_sec: int,
    return_rows: int,
    range_minutes: int,
    aggregation: str,
    prefix: str,
) -> Dict[str, Any]:
    return {
        "binding": {
            "type": "tag-history",
            "config": {
                "aggregate": aggregation,
                "avoidScanClassValidation": True,
                "cacheAndShare": cache_enabled,
                "dateRange": {
                    "endDate": "now(0)",
                    "startDate": f"dateArithmetic(now(0), -{range_minutes}, 'minute')",
                },
                "ignoreBadQuality": False,
                "polling": {"enabled": True, "rate": str(polling_rate_sec)},
                "preventInterpolation": False,
                "returnFormat": "Wide",
                "returnSize": {"numRows": str(return_rows), "type": "FIXED"},
                "tags": [{"path": path} for path in paths],
                "valueFormat": "DATASET",
            },
            "transforms": [{"type": "script", "code": history_transform(prefix)}],
        }
    }


def history_label(
    index: int,
    variant: str,
    paths: List[str],
    cache_enabled: bool,
    polling_rate_sec: int,
    return_rows: int,
    range_minutes: int,
    aggregation: str,
) -> Dict[str, Any]:
    title = "History cache on" if cache_enabled else "History cache off"
    prefix = f"{title} {index:03d}"
    return refresh_common.component(
        "ia.display.label",
        meta={"name": f"HistoryLabel{index:03d}"},
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
            "props.text": tag_history_binding(
                paths,
                cache_enabled,
                polling_rate_sec,
                return_rows,
                range_minutes,
                aggregation,
                prefix,
            )
        },
    )


def make_view_json(run_id: str, variant: str, paths: List[str], args: argparse.Namespace) -> Dict[str, Any]:
    cache_enabled = variant == "cache-on"
    title = "History cache on" if cache_enabled else "History cache off"
    marker = f"{run_id} {variant.upper()} READY"
    children: List[Dict[str, Any]] = [
        label(
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
        label(
            (
                f"A-02 tag-history Cache & Share fixture: {args.binding_count} identical tag-history labels, "
                f"{len(paths)} history tags, {args.polling_rate_sec}s polling, {title}."
            ),
            "Fixture Summary",
            "38px",
            {"color": "#1f2937", "whiteSpace": "pre-wrap"},
        ),
        label(
            f"Binding config hypothesis: cacheAndShare={str(cache_enabled).lower()}; runtime proof comes from historian/database activity.",
            "Cache State",
            "38px",
            {"backgroundColor": "#ecfeff", "borderColor": "#a5f3fc", "borderStyle": "solid", "borderWidth": "1px"},
        ),
    ]
    children.extend(
        history_label(
            index,
            variant,
            paths,
            cache_enabled,
            args.polling_rate_sec,
            args.history_return_rows,
            args.history_range_minutes,
            args.history_aggregation,
        )
        for index in range(1, args.binding_count + 1)
    )
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "bindingCount": args.binding_count,
            "historyTagCount": len(paths),
            "pollingEnabled": True,
            "pollingRateSec": args.polling_rate_sec,
            "cacheAndShare": cache_enabled,
            "tagPathsSha256": sha256_text(canonical_json(paths)),
            "remediationCandidate": "Enable tag-history Cache & Share only when identical history bindings are safe to share and runtime historian activity proves consolidation.",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": refresh_common.component(
            "ia.container.flex",
            meta={"name": "tag-history-cache-share-root"},
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
    suffix = f"{run_slug}-tag-history-cache-share-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    view_path: str,
    route: str,
    paths: List[str],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-tag-history-cache-share"
    view_json = make_view_json(run_id, variant, paths, args)
    zip_path = zip_dir / "package.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-history-cache-share-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler tag history Cache Share fixture", "enabled": True, "inheritable": False})
        refresh_common.write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Tag History Cache Share {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "cacheAndShare": variant == "cache-on",
        "bindingCount": args.binding_count,
        "pollingRateSec": args.polling_rate_sec,
        "historyReturnRows": args.history_return_rows,
        "historyRangeMinutes": args.history_range_minutes,
        "historyAggregation": args.history_aggregation,
        "tagPaths": paths,
        "viewPath": view_path,
        "route": route,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": ("History cache on" if variant == "cache-on" else "History cache off") + " 001: rows=",
        "staticReadyText": f"{run_id} {variant.upper()} READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Tag History Cache Share {package['variant']}"}],
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
    return common.view_read_payload(request_id, project, view_path, args)


def rollback_payload(request_id: str, project: str, backup_name: str, package: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "rollback",
        "requestId": request_id,
        "targetProject": project,
        "backupName": backup_name,
        "viewPaths": [package["viewPath"]],
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


def feature_set_from_health(health: Dict[str, Any]) -> set[str]:
    return refresh_common.feature_set_from_health(health)


def action_set_from_health(health: Dict[str, Any]) -> set[str]:
    return cp.enabled_name_set(cp.response(health).get("supportedActions", []))


def readback_ok(record: Dict[str, Any], package: Dict[str, Any], binding_count: int) -> bool:
    text = canonical_json(cp.response(record))
    expected_cache = '"cacheAndShare":true' if package["cacheAndShare"] else '"cacheAndShare":false'
    return (
        expected_cache in text
        and all(path in text for path in package["tagPaths"])
        and text.count('"type":"tag-history"') >= binding_count
        and '"polling":{"enabled":true' in text
    )


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(MULTISESSION_SCRIPT),
        "--run-id",
        f"{args.run_id}-tag-history-cache-share-{package['variant']}",
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


def profile_ok(profile_dir: Path) -> bool:
    return query_common.profile_ok(profile_dir)


def profile_summary(profile_dir: Path) -> Dict[str, Any]:
    return query_common.profile_summary(profile_dir)


def summarize_metric_counts(profile_dir: Path) -> Dict[str, Any]:
    return query_common.summarize_metric_counts(profile_dir)


def compare_variants(variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_name = {str(row.get("variant")): row for row in variants}
    off = by_name.get("cache-off", {})
    on = by_name.get("cache-on", {})
    off_metrics = off.get("metricSummary", {}) if isinstance(off.get("metricSummary"), dict) else {}
    on_metrics = on.get("metricSummary", {}) if isinstance(on.get("metricSummary"), dict) else {}
    off_delta = to_float(off_metrics.get("primaryDatabaseQueryDuringDelta"))
    on_delta = to_float(on_metrics.get("primaryDatabaseQueryDuringDelta"))
    reduction = None
    ratio = None
    if off_delta is not None and on_delta is not None:
        reduction = off_delta - on_delta
        ratio = on_delta / off_delta if off_delta else None
    minimum_reduction = None
    if off_delta is not None and off_delta > 0:
        minimum_reduction = max(MIN_CONSOLIDATION_REDUCTION_COUNT, off_delta * MIN_CONSOLIDATION_REDUCTION_RATIO)
    lower = off_delta is not None and on_delta is not None and off_delta > 0 and on_delta < off_delta
    observed = bool(lower and reduction is not None and minimum_reduction is not None and reduction >= minimum_reduction)
    return {
        "primaryDatabaseMetricOff": off_metrics.get("primaryDatabaseQueryMetric"),
        "primaryDatabaseMetricOn": on_metrics.get("primaryDatabaseQueryMetric"),
        "cacheOffDatabaseQueryDuringDelta": off_delta,
        "cacheOnDatabaseQueryDuringDelta": on_delta,
        "cacheOnMinusOffDatabaseQueryDuringDelta": delta(off_delta, on_delta),
        "cacheOnReductionFromOff": reduction,
        "cacheOnVsOffRatio": ratio,
        "minimumReductionForConsolidation": minimum_reduction,
        "cacheOnLowerDatabaseQueries": bool(lower),
        "observedConsolidationSignal": bool(observed),
        "interpretation": (
            "Cache-on had a meaningfully lower primary database query-count delta during the multi-session history-binding window."
            if observed
            else "No meaningful primary database query-count reduction was observed for cache-on in this single tag-history run."
        ),
    }


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
    after_read = client.call(f"{run_id}-{variant_name}-post-cleanup-viewRead", view_read_payload(f"{run_id}-{variant_name}-post-cleanup-viewRead", project, package["viewPath"], args))
    return {
        "rollbackOk": cp.ok(rb_dry) and cp.ok(rb_apply),
        "cleanupRouteAbsent": cp.ok(routes_check) and not route_still_present,
        "cleanupViewAbsent": not cp.ok(after_read),
        "tagFixturePersisted": True,
        "tagCleanupAvailable": False,
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Tag History Cache & Share Multi-session Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        f"Stack: `{summary.get('stackVersion')}`",
        "",
        "## Fixture",
        "",
        f"- History provider evidence: `{summary.get('actualHistoryProviderEvidence')}`",
        f"- Tag fixture base path: `{summary.get('tagBasePath')}`",
        f"- History available before runtime profile: `{str(summary.get('historyFixture', {}).get('historyAvailable')).lower()}`",
        f"- Route/view cleanup automatic: `{str(summary.get('routeViewCleanupAutomatic')).lower()}`",
        f"- Tag cleanup available in current runner: `{str(summary.get('tagCleanupAvailable')).lower()}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | Cache & Share | OK | Browser ready | DB query delta | Perspective fetch delta | Property-change delta | Cleanup |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        metrics = row.get("metricSummary", {}) if isinstance(row.get("metricSummary"), dict) else {}
        profile = row.get("profileSummary", {}) if isinstance(row.get("profileSummary"), dict) else {}
        cleanup = row.get("cleanup", {}) if isinstance(row.get("cleanup"), dict) else {}
        cleanup_ok = cleanup.get("rollbackOk") and cleanup.get("cleanupRouteAbsent") and cleanup.get("cleanupViewAbsent")
        lines.append(
            "| {variant} | `{cache}` | `{ok}` | {ready}/{total} | {db_delta} | {fetch_delta} | {prop_delta} | `{cleanup}` |".format(
                variant=row.get("variant"),
                cache=str(row.get("cacheAndShare")).lower(),
                ok=str(row.get("ok", False)).lower(),
                ready=format_number(profile.get("browserReadyTextMatchedCount")),
                total=format_number(profile.get("browserProbeCount")),
                db_delta=format_number(metrics.get("primaryDatabaseQueryDuringDelta")),
                fetch_delta=format_number(metrics.get("primaryPerspectiveFetchDuringDelta")),
                prop_delta=format_number(metrics.get("primaryPerspectivePropertyChangesDuringDelta")),
                cleanup=str(bool(cleanup_ok)).lower(),
            )
        )
    lines.extend(["", "## Comparison", ""])
    comparison = summary.get("comparison", {})
    for key in [
        "cacheOffDatabaseQueryDuringDelta",
        "cacheOnDatabaseQueryDuringDelta",
        "cacheOnMinusOffDatabaseQueryDuringDelta",
        "cacheOnReductionFromOff",
        "cacheOnVsOffRatio",
        "minimumReductionForConsolidation",
        "cacheOnLowerDatabaseQueries",
        "observedConsolidationSignal",
    ]:
        lines.append(f"- `{key}`: `{format_number(comparison.get(key))}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


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
    action_set = action_set_from_health(health)
    required_actions = {"tagConfigure", "tagRead", "historyProbe", "projectResourceImportZip", "pageValidate", "viewRead", "rollback"}
    missing_actions = sorted(action for action in required_actions if not cp.supports_action(action_set, feature_set, action))
    if missing_actions:
        raise RuntimeError(f"Runner is missing required supported actions: {', '.join(missing_actions)}")

    db_record = client.call(f"{args.run_id}-databaseConnectionsList", {"action": "databaseConnectionsList", "requestId": f"{args.run_id}-databaseConnectionsList"})
    history_provider = refresh_common.choose_database(db_record, args.history_provider)
    if not history_provider:
        raise RuntimeError("No database/history provider connection available for tag-history fixture")
    providers_record = client.call(f"{args.run_id}-tagProviders", {"action": "tagProviders", "requestId": f"{args.run_id}-tagProviders"})

    tag_base_path = default_tag_base_path(args)
    allowed_tag_prefix = default_allowed_tag_prefix(args)
    tag_defs = history_tag_definitions(args.history_tag_count, history_provider)
    tag_paths = [fully_qualified_tag_path(tag_base_path, tag["name"]) for tag in tag_defs]
    history_dir = out_dir / "history-fixture"
    history_dir.mkdir(parents=True, exist_ok=True)
    dry = client.call(
        f"{args.run_id}-tagConfigure-dryRun",
        tag_configure_payload(f"{args.run_id}-tagConfigure-dryRun", tag_base_path, allowed_tag_prefix, tag_defs, args.tag_collision_policy, True),
        timeout=args.timeout_sec,
    )
    apply = client.call(
        f"{args.run_id}-tagConfigure-apply",
        tag_configure_payload(f"{args.run_id}-tagConfigure-apply", tag_base_path, allowed_tag_prefix, tag_defs, args.tag_collision_policy, False),
        timeout=args.timeout_sec,
    )
    tag_read = client.call(f"{args.run_id}-tagRead-created", tag_read_payload(f"{args.run_id}-tagRead-created", tag_paths), timeout=args.timeout_sec)
    history_wait = wait_for_history(client, args, args.run_id, tag_paths, history_dir)
    history_gates = {
        "databaseConnectionsList": cp.ok(db_record),
        "tagProviders": cp.ok(providers_record),
        "tagConfigureDryRun": cp.ok(dry),
        "tagConfigureApply": cp.ok(apply) and cp.response(apply).get("allGood") is True,
        "tagRead": tag_read_ok(tag_read, tag_paths),
        "historyProbe": bool(history_wait.get("ok")),
    }
    if not all(history_gates.values()) and not args.continue_without_history:
        summary = {
            "ok": False,
            "runId": args.run_id,
            "createdAt": utc_now(),
            "project": project,
            "runnerVersion": cp.response(health).get("runnerVersion"),
            "stackVersion": cp.response(health).get("stackVersion"),
            "features": sorted(feature_set),
            "supportedActions": sorted(action_set),
            "historyFixture": {
                "gates": history_gates,
                "historyAvailable": bool(history_wait.get("ok")),
                "lastProbe": cp.response(history_wait.get("record", {})),
            },
            "tagBasePath": tag_base_path,
            "tagPaths": tag_paths,
            "tagCleanupAvailable": False,
            "routeViewCleanupAutomatic": True,
            "variants": [],
            "comparison": {},
            "interpretation": ["History fixture setup failed, so runtime tag-history Cache & Share profiling was not started."],
        }
        write_json(out_dir / "summary.json", summary)
        write_report(out_dir, summary)
        return summary

    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    for variant_name in ["cache-off", "cache-on"]:
        variant_dir = out_dir / variant_name
        variant_dir.mkdir(parents=True, exist_ok=True)
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/TagHistoryCacheShare{''.join(part.title() for part in variant_name.split('-'))}"
        package = build_package(variant_dir, project, args.run_id, variant_name, view_path, route, tag_paths, args)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        backup_name = ""
        gates: Dict[str, bool] = {}
        variant: Dict[str, Any]
        try:
            dry_run = client.call(f"{args.run_id}-{variant_name}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant_name}-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry_run)
            if not gates["dryRun"]:
                raise RuntimeError("dryRun failed")
            apply_package = client.call(f"{args.run_id}-{variant_name}-apply", package_payload("apply", f"{args.run_id}-{variant_name}-apply", project, package, args), timeout=args.timeout_sec)
            backup_name = common.backup_name_from_response(cp.response(apply_package))
            gates["apply"] = cp.ok(apply_package) and bool(backup_name)
            if not gates["apply"]:
                raise RuntimeError("apply failed")
            time.sleep(2)
            readback = client.call(f"{args.run_id}-{variant_name}-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, view_path, args))
            gates["viewRead"] = cp.ok(readback) and readback_ok(readback, package, args.binding_count)
            page = client.call(f"{args.run_id}-{variant_name}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = (variant_dir / "profile").resolve()
            profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), f"profile-tag-history-cache-share-{variant_name}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            variant = {
                "variant": variant_name,
                "cacheAndShare": package["cacheAndShare"],
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "tagPathCount": len(tag_paths),
                "backupName": backup_name,
                "profileDir": str(profile_dir),
                "profileSummary": profile_summary(profile_dir),
                "metricSummary": summarize_metric_counts(profile_dir),
                "profileCommand": profile_result,
            }
        except Exception as exc:
            variant = {
                "variant": variant_name,
                "cacheAndShare": package["cacheAndShare"],
                "ok": False,
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "tagPathCount": len(tag_paths),
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
                )
            variants.append(variant)
            if args.pause_sec > 0 and variant_name != "cache-on":
                time.sleep(args.pause_sec)

    comparison = compare_variants(variants)
    summary = {
        "ok": bool(cp.ok(health) and cp.ok(db_record) and history_gates and all(history_gates.values()) and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "features": sorted(feature_set),
        "supportedActions": sorted(action_set),
        "historyProvider": "<historyProviderConnection>",
        "actualHistoryProviderEvidence": history_provider,
        "tagBasePath": tag_base_path,
        "allowedTagPathPrefix": allowed_tag_prefix,
        "tagPaths": tag_paths,
        "historyTagCount": args.history_tag_count,
        "bindingCount": args.binding_count,
        "pollingRateSec": args.polling_rate_sec,
        "sessionCount": args.session_count,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "historyFixture": {
            "gates": history_gates,
            "historyAvailable": bool(history_wait.get("ok")),
            "tagReadSample": cp.response(tag_read).get("reads"),
            "lastProbe": cp.response(history_wait.get("record", {})),
            "attemptCount": len(history_wait.get("attempts", [])),
        },
        "routeViewCleanupAutomatic": True,
        "tagCleanupAvailable": False,
        "tagFixturePersisted": True,
        "variants": variants,
        "comparison": comparison,
        "packages": package_records,
        "interpretation": [
            "This is a controlled A-02 fixture, not a customer route conclusion.",
            "Both variants use the same number of visible tag-history labels, identical tag paths, identical historian query shape, polling cadence, browser count, and sampler cadence.",
            "The fixture writes the Perspective tag-history binding Cache & Share state as cacheAndShare and verifies that exact field by viewRead before runtime profiling.",
            "The generated route/view resources are rolled back and verified absent; current runner builds do not expose tag deletion, so the bounded history tag fixture remains under the allowed test prefix.",
            "Treat tag-history Cache & Share as proven only when database or historian query-activity counters change, not from static config alone.",
            "Use repeated clean-baseline pairs before promoting a customer remediation rule; this single run is mechanics and signal evidence.",
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
    parser.add_argument("--history-provider", default="", help="History provider connection for generated history-enabled tags. Defaults to first valid database connection.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--history-tag-count", type=int, default=3)
    parser.add_argument("--binding-count", type=int, default=8)
    parser.add_argument("--polling-rate-sec", type=int, default=1)
    parser.add_argument("--history-return-rows", type=int, default=20)
    parser.add_argument("--history-range-minutes", type=int, default=5)
    parser.add_argument("--history-aggregation", default="LastValue")
    parser.add_argument("--history-warmup-sec", type=float, default=15.0)
    parser.add_argument("--history-wait-timeout-sec", type=float, default=90.0)
    parser.add_argument("--history-wait-interval-sec", type=float, default=5.0)
    parser.add_argument("--continue-without-history", action="store_true", help="Continue into runtime profiling even if the history warmup probe does not show data.")
    parser.add_argument("--tag-provider", default=DEFAULT_TAG_PROVIDER)
    parser.add_argument("--tag-base-path", default="", help="Fully qualified base path for generated history tags. Defaults under the allowed test prefix and run id.")
    parser.add_argument("--allowed-tag-path-prefix", default="", help="Fully qualified allowed tag prefix. Defaults to the provider-specific performance-profiler test prefix.")
    parser.add_argument("--tag-collision-policy", default="o", choices=["a", "o", "m", "i"], help="system.tag.configure collision policy for history tag fixture.")
    parser.add_argument("--session-count", type=int, default=5)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--pre-samples", type=int, default=2)
    parser.add_argument("--during-samples", type=int, default=7)
    parser.add_argument("--post-samples", type=int, default=2)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=48)
    parser.add_argument(
        "--metric-name-contains",
        action="append",
        default=["Perspective", "perspective", "database", "Database", "databases", "history", "History", "Historian", "tag", "Tag"],
        help="Metric substring filter passed to run_multisession_profile.py. Repeatable.",
    )
    parser.add_argument("--metric-prefix", action="append", default=[], help="Metric prefix filter passed to run_multisession_profile.py. Repeatable.")
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=900)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=90.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=18000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--launch-stagger-ms", type=int, default=250)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each session group, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline per variant session group.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Mark the variant failed when a clean baseline is requested but not reached.")
    parser.add_argument("--pause-sec", type=float, default=3.0, help="Pause between cache-off and cache-on variants.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.history_tag_count < 1:
        raise SystemExit("--history-tag-count must be >= 1")
    if args.binding_count < 1:
        raise SystemExit("--binding-count must be >= 1")
    if args.session_count < 1:
        raise SystemExit("--session-count must be >= 1")
    if args.history_return_rows < 1:
        raise SystemExit("--history-return-rows must be >= 1")
    if args.history_range_minutes < 1:
        raise SystemExit("--history-range-minutes must be >= 1")
    if args.history_warmup_sec < 0:
        raise SystemExit("--history-warmup-sec must be >= 0")
    if args.history_wait_timeout_sec < 0:
        raise SystemExit("--history-wait-timeout-sec must be >= 0")
    if args.history_wait_interval_sec < 0:
        raise SystemExit("--history-wait-interval-sec must be >= 0")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0:
        raise SystemExit("--baseline-wait-timeout-sec must be >= 0")
    if args.baseline_wait_interval_sec < 0:
        raise SystemExit("--baseline-wait-interval-sec must be >= 0")
    summary = run(args)
    print(json.dumps({"ok": summary.get("ok"), "summary": str(Path(args.out_dir) / "summary.json")}, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
