#!/usr/bin/env python3
"""Run guarded Perspective query Cache & Share off/on multi-session fixtures."""

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
import run_refresh_binding_ab as refresh_common
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
MULTISESSION_SCRIPT = SCRIPT_DIR / "run_multisession_profile.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
DEFAULT_ALLOWED_NAMED_QUERY_PREFIX = "LLM Tests/"
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


def avg(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def delta(before: Any, after: Any) -> Optional[float]:
    before_float = to_float(before)
    after_float = to_float(after)
    if before_float is None or after_float is None:
        return None
    return after_float - before_float


def cache_query_binding(query_path: str, cache_enabled: bool, polling_rate_sec: int, prefix: str) -> Dict[str, Any]:
    return {
        "binding": {
            "type": "query",
            "config": {
                "parameters": {},
                "polling": {"enabled": True, "rate": str(polling_rate_sec)},
                "queryPath": query_path,
                "cacheAndShare": cache_enabled,
            },
            "transforms": [{"type": "script", "code": refresh_common.tick_transform(prefix)}],
        }
    }


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


def tick_label(index: int, variant: str, query_path: str, cache_enabled: bool, polling_rate_sec: int) -> Dict[str, Any]:
    title = "Cache on" if cache_enabled else "Cache off"
    prefix = f"{title} tick {index:03d}"
    return refresh_common.component(
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
        prop_config={"props.text": cache_query_binding(query_path, cache_enabled, polling_rate_sec, prefix)},
    )


def make_view_json(run_id: str, variant: str, query_path: str, query_count: int, polling_rate_sec: int) -> Dict[str, Any]:
    cache_enabled = variant == "cache-on"
    title = "Cache on" if cache_enabled else "Cache off"
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
            f"A-01 query Cache & Share fixture: {query_count} identical query-bound labels, {polling_rate_sec}s polling, {title.lower()}",
            "Fixture Summary",
            "38px",
            {"color": "#1f2937", "whiteSpace": "pre-wrap"},
        ),
        label(
            f"Binding config hypothesis: cacheAndShare={str(cache_enabled).lower()}; runtime proof comes from DB query timers.",
            "Cache State",
            "38px",
            {"backgroundColor": "#eef2ff", "borderColor": "#c7d2fe", "borderStyle": "solid", "borderWidth": "1px"},
        ),
    ]
    children.extend(tick_label(index, variant, query_path, cache_enabled, polling_rate_sec) for index in range(1, query_count + 1))
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "queryCount": query_count,
            "pollingEnabled": True,
            "pollingRateSec": polling_rate_sec,
            "cacheAndShare": cache_enabled,
            "remediationCandidate": "Enable Cache & Share only when identical query/history bindings are safe to share and runtime query counts prove consolidation.",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": refresh_common.component(
            "ia.container.flex",
            meta={"name": "query-cache-share-root"},
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
    suffix = f"{run_slug}-query-cache-share-{variant}"
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
    query_path: str,
    database: str,
    query_count: int,
    polling_rate_sec: int,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-query-cache-share"
    view_json = make_view_json(run_id, variant, query_path, query_count, polling_rate_sec)
    query_sql = "SELECT strftime('%Y%m%dT%H%M%f','now') || '-' || hex(randomblob(4)) AS refresh_tick LIMIT 1"
    zip_path = zip_dir / "package.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-cache-share-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler query Cache Share fixture", "enabled": True, "inheritable": False})
        refresh_common.write_view(project_root, view_path, view_json, actor)
        refresh_common.write_named_query(project_root, query_path, query_sql, database, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Query Cache Share {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "cacheAndShare": variant == "cache-on",
        "queryCount": query_count,
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
        "readyText": f"{run_id} {variant.upper()} READY",
        "secondaryReadyText": ("Cache on" if variant == "cache-on" else "Cache off") + " tick 001:",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Query Cache Share {package['variant']}"}],
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
    return refresh_common.named_query_read_payload(request_id, project, query_path, args)


def named_query_preview_payload(request_id: str, project: str, query_path: str, args: argparse.Namespace) -> Dict[str, Any]:
    return refresh_common.named_query_preview_payload(request_id, project, query_path, args)


def rollback_payload(request_id: str, project: str, backup_name: str, package: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    return refresh_common.rollback_payload(request_id, project, backup_name, package, dry_run)


def feature_set_from_health(health: Dict[str, Any]) -> set[str]:
    return refresh_common.feature_set_from_health(health)


def action_set_from_health(health: Dict[str, Any]) -> set[str]:
    return cp.enabled_name_set(cp.response(health).get("supportedActions", []))


def readback_ok(record: Dict[str, Any], package: Dict[str, Any], query_count: int) -> bool:
    text = canonical_json(cp.response(record))
    expected_cache = '"cacheAndShare":true' if package["cacheAndShare"] else '"cacheAndShare":false'
    return package["queryPath"] in text and expected_cache in text and text.count('"type":"query"') >= query_count


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(MULTISESSION_SCRIPT),
        "--run-id",
        f"{args.run_id}-query-cache-share-{package['variant']}",
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


def read_ndjson(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def metric_items_by_name(row: Dict[str, Any], field: str) -> Dict[str, float]:
    snapshot = row.get("metricsSnapshot", {})
    if not isinstance(snapshot, dict):
        return {}
    metrics = snapshot.get("metrics", [])
    if not isinstance(metrics, list):
        return {}
    out: Dict[str, float] = {}
    for item in metrics:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        value = to_float(item.get(field))
        if value is None:
            continue
        out[name] = out.get(name, 0.0) + value
    return out


def field_by_phase(rows: List[Dict[str, Any]], field: str) -> Dict[str, List[Dict[str, float]]]:
    phases: Dict[str, List[Dict[str, float]]] = {"pre": [], "during": [], "post": []}
    for row in rows:
        phase = str(row.get("phase", ""))
        if phase not in phases:
            continue
        phases[phase].append(metric_items_by_name(row, field))
    return phases


def first_last_delta(values: List[Dict[str, float]], name: str, before: Optional[float]) -> Dict[str, Any]:
    present = [row[name] for row in values if name in row]
    first = present[0] if present else None
    last = present[-1] if present else None
    return {"first": first, "last": last, "deltaFromBefore": delta(before, last)}


def summarize_metric_counts(profile_dir: Path) -> Dict[str, Any]:
    rows = read_ndjson(profile_dir / "multi-session-samples.ndjson")
    count_phases = field_by_phase(rows, "count")
    value_phases = field_by_phase(rows, "value")
    names = sorted({name for phase_rows in count_phases.values() for row in phase_rows for name in row})
    value_names = sorted({name for phase_rows in value_phases.values() for row in phase_rows for name in row})
    count_rollups: Dict[str, Dict[str, Any]] = {}
    for name in names:
        pre_last = first_last_delta(count_phases["pre"], name, None)["last"]
        count_rollups[name] = {
            "pre": first_last_delta(count_phases["pre"], name, None),
            "during": first_last_delta(count_phases["during"], name, pre_last),
            "post": first_last_delta(count_phases["post"], name, pre_last),
        }
    value_rollups: Dict[str, Dict[str, Any]] = {}
    for name in value_names:
        for_phase = {}
        for phase in ("pre", "during", "post"):
            present = [row[name] for row in value_phases[phase] if name in row]
            for_phase[phase] = {
                "first": present[0] if present else None,
                "last": present[-1] if present else None,
                "avg": avg(present),
                "max": max(present) if present else None,
            }
        value_rollups[name] = for_phase

    preferred_db = "databases.queries" if "databases.queries" in count_rollups else ""
    if not preferred_db:
        preferred_db = next((name for name in names if name.startswith("databases.") and name.endswith(".queries")), "")
    preferred_fetch = "perspective.fetches" if "perspective.fetches" in count_rollups else ""
    if not preferred_fetch:
        preferred_fetch = next((name for name in names if name.startswith("perspective.") and name.endswith(".fetches")), "")
    preferred_property_changes = "perspective.property-changes" if "perspective.property-changes" in count_rollups else ""
    return {
        "sampleCount": len(rows),
        "countMetricNames": names,
        "valueMetricNames": value_names,
        "counts": count_rollups,
        "values": value_rollups,
        "primaryDatabaseQueryMetric": preferred_db,
        "primaryDatabaseQueryDuringDelta": count_rollups.get(preferred_db, {}).get("during", {}).get("deltaFromBefore") if preferred_db else None,
        "primaryDatabaseQueryPostDelta": count_rollups.get(preferred_db, {}).get("post", {}).get("deltaFromBefore") if preferred_db else None,
        "primaryPerspectiveFetchMetric": preferred_fetch,
        "primaryPerspectiveFetchDuringDelta": count_rollups.get(preferred_fetch, {}).get("during", {}).get("deltaFromBefore") if preferred_fetch else None,
        "primaryPerspectivePropertyChangesMetric": preferred_property_changes,
        "primaryPerspectivePropertyChangesDuringDelta": count_rollups.get(preferred_property_changes, {}).get("during", {}).get("deltaFromBefore") if preferred_property_changes else None,
    }


def profile_summary(profile_dir: Path) -> Dict[str, Any]:
    data = read_json(profile_dir / "summary.json")
    groups = data.get("groups", []) if isinstance(data.get("groups"), list) else []
    group = groups[0] if groups and isinstance(groups[0], dict) else {}
    probes = group.get("browserProbes", {}) if isinstance(group.get("browserProbes"), dict) else {}
    deltas = group.get("deltas", {}) if isinstance(group.get("deltas"), dict) else {}
    phases = group.get("phases", {}) if isinstance(group.get("phases"), dict) else {}
    return {
        "ok": data.get("ok"),
        "sessionCount": group.get("sessionCount"),
        "browserReadyCount": probes.get("readyCount"),
        "browserReadyTextMatchedCount": probes.get("readyTextMatchedCount"),
        "browserProbeCount": probes.get("probeCount"),
        "browserExitCodes": probes.get("exitCodes"),
        "browserTimedOutCount": probes.get("timedOutCount"),
        "duringMinusPreBrowserSessionsAvg": deltas.get("duringMinusPreBrowserSessionsAvg"),
        "duringMinusPreBrowserPagesAvg": deltas.get("duringMinusPreBrowserPagesAvg"),
        "duringMinusPreHeapUsedBytesAvg": deltas.get("duringMinusPreHeapUsedBytesAvg"),
        "duringMinusPreProcessCpuLoadAvg": deltas.get("duringMinusPreProcessCpuLoadAvg"),
        "pre": phases.get("pre", {}),
        "during": phases.get("during", {}),
        "post": phases.get("post", {}),
    }


def profile_ok(profile_dir: Path) -> bool:
    return read_json(profile_dir / "summary.json").get("ok") is True


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
            "Cache-on had a meaningfully lower primary database query-count delta during the five-session window."
            if observed
            else "No meaningful primary database query-count reduction was observed for cache-on in this single run."
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
    query_after = client.call(f"{run_id}-{variant_name}-post-cleanup-namedQueryRead", named_query_read_payload(f"{run_id}-{variant_name}-post-cleanup-namedQueryRead", project, package["queryPath"], args))
    return {
        "rollbackOk": cp.ok(rb_dry) and cp.ok(rb_apply),
        "cleanupRouteAbsent": cp.ok(routes_check) and not route_still_present,
        "cleanupViewAbsent": not cp.ok(after_read),
        "cleanupNamedQueryAbsent": not cp.ok(query_after),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Query Cache & Share Multi-session Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        f"Stack: `{summary.get('stackVersion')}`",
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
        cleanup_ok = cleanup.get("rollbackOk") and cleanup.get("cleanupRouteAbsent") and cleanup.get("cleanupViewAbsent") and cleanup.get("cleanupNamedQueryAbsent")
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
    feature_set = feature_set_from_health(health)
    action_set = action_set_from_health(health)
    db_record = client.call(f"{args.run_id}-databaseConnectionsList", {"action": "databaseConnectionsList", "requestId": f"{args.run_id}-databaseConnectionsList"})
    database = refresh_common.choose_database(db_record, args.database)
    if not database:
        raise RuntimeError("No database connection available for disposable Named Query fixture")

    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    for variant_name in ["cache-off", "cache-on"]:
        variant_dir = out_dir / variant_name
        variant_dir.mkdir(parents=True, exist_ok=True)
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/QueryCacheShare{''.join(part.title() for part in variant_name.split('-'))}"
        query_path = f"{args.named_query_path_prefix.rstrip('/')}/{base}/{''.join(part.title() for part in variant_name.split('-'))}Tick"
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
            profile_dir = (variant_dir / "profile").resolve()
            profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), f"profile-query-cache-share-{variant_name}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            variant = {
                "variant": variant_name,
                "cacheAndShare": package["cacheAndShare"],
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "queryPath": query_path,
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
            if args.pause_sec > 0 and variant_name != "cache-on":
                time.sleep(args.pause_sec)

    comparison = compare_variants(variants)
    summary = {
        "ok": bool(cp.ok(health) and cp.ok(db_record) and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "features": sorted(feature_set),
        "supportedActions": sorted(action_set),
        "database": "<databaseConnection>",
        "actualDatabaseEvidence": database,
        "queryCount": args.query_count,
        "pollingRateSec": args.polling_rate_sec,
        "sessionCount": args.session_count,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparison": comparison,
        "packages": package_records,
        "interpretation": [
            "This is a controlled A-01 fixture, not a customer route conclusion.",
            "Both variants use the same number of visible query-bound labels, identical Named Query SQL shape, polling cadence, browser count, and sampler cadence.",
            "The fixture writes the Perspective query binding Cache & Share state as cacheAndShare and verifies that exact field by viewRead before runtime profiling.",
            "Treat Cache & Share as proven only when the database query-count delta or equivalent query activity counter changes, not from static config alone.",
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
    parser.add_argument("--command-timeout-sec", type=int, default=720)
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
    summary = run(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
