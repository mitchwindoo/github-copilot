#!/usr/bin/env python3
"""Run a guarded I-06 data-source-delay incident mechanics fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_hidden_content_ab as hidden_common
import run_refresh_binding_ab as refresh_common
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
DEFAULT_ALLOWED_NAMED_QUERY_PREFIX = "LLM Tests/"
VARIANTS = ("fast", "delayed")


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
    prop_config: Optional[Dict[str, Any]] = None,
    events: Optional[Dict[str, Any]] = None,
    children: Optional[List[Dict[str, Any]]] = None,
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


def query_transform(variant: str) -> str:
    prefix = f"I06 {variant} result"
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


def query_binding(query_path: str, variant: str) -> Dict[str, Any]:
    return {
        "binding": {
            "type": "query",
            "config": {
                "parameters": {},
                "polling": {"enabled": False, "rate": "60"},
                "queryPath": query_path,
            },
            "transforms": [{"type": "script", "code": query_transform(variant)}],
        }
    }


def property_binding(path: str, transform_code: str) -> Dict[str, Any]:
    return {"binding": {"type": "property", "config": {"path": path}, "transforms": [{"type": "script", "code": transform_code}]}}


def refresh_button_script() -> str:
    return (
        "\tself.view.custom.lastRefreshError = ''\n"
        "\ttry:\n"
        "\t\tclicks = int(self.view.custom.refreshClicks)\n"
        "\texcept:\n"
        "\t\tclicks = 0\n"
        "\tself.view.custom.refreshClicks = clicks + 1\n"
        "\ttry:\n"
        "\t\tself.getSibling('DelayQueryLabel').refreshBinding('props.text')\n"
        "\texcept Exception as err:\n"
        "\t\tself.view.custom.lastRefreshError = str(err)\n"
    )


def make_view_json(run_id: str, variant: str, query_path: str, delay_size: int) -> Dict[str, Any]:
    marker = f"{run_id} {variant.upper()} I-06 READY"
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
                    f"I-06 data-source delay fixture: {variant} read-only Named Query, "
                    f"polling disabled, manual refreshBinding(), delay size {delay_size if variant == 'delayed' else 0}"
                ),
                "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
            },
        ),
        component(
            "ia.display.label",
            meta={"name": "DelayQueryLabel"},
            position={"basis": "38px", "grow": 0, "shrink": 0},
            props={
                "text": f"I06 {variant} pending",
                "style": {
                    "backgroundColor": "#eef2ff",
                    "borderColor": "#94a3b8",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "color": "#111827",
                    "fontSize": 13,
                    "fontWeight": "700",
                    "overflow": "hidden",
                    "padding": "8px 10px",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                },
            },
            prop_config={"props.text": query_binding(query_path, variant)},
        ),
        component(
            "ia.input.button",
            meta={"name": "RefreshButton"},
            position={"basis": "46px", "grow": 0, "shrink": 0},
            props={
                "primary": variant == "delayed",
                "style": {"alignSelf": "flex-start", "fontSize": 14, "fontWeight": "700", "maxWidth": "220px"},
                "text": "Run query refresh",
            },
            events={"component": {"onActionPerformed": {"scope": "G", "type": "script", "config": {"script": refresh_button_script()}}}},
        ),
        component(
            "ia.display.label",
            meta={"name": "ClickCount"},
            position={"basis": "30px", "grow": 0, "shrink": 0},
            props={
                "text": "Refresh clicks: 0",
                "style": {"color": "#334155", "fontSize": 12, "overflow": "hidden", "padding": "6px 8px", "whiteSpace": "nowrap"},
            },
            prop_config={"props.text": property_binding("view.custom.refreshClicks", "\treturn 'Refresh clicks: ' + str(value)\n")},
        ),
        component(
            "ia.display.label",
            meta={"name": "LastRefreshError"},
            position={"basis": "30px", "grow": 0, "shrink": 0},
            props={
                "text": "",
                "style": {"color": "#991b1b", "fontSize": 12, "overflow": "hidden", "padding": "6px 8px", "whiteSpace": "nowrap"},
            },
            prop_config={"props.text": property_binding("view.custom.lastRefreshError", "\treturn '' if not value else 'Refresh error: ' + str(value)\n")},
        ),
    ]
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "delaySize": delay_size if variant == "delayed" else 0,
            "refreshClicks": 0,
            "lastRefreshError": "",
            "incidentCase": "I-06 data-source-only delay mechanics",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "datasource-delay-root"},
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
    suffix = f"{run_slug}-datasource-delay-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def fast_query_sql() -> str:
    return "SELECT 'fast' AS delay_kind, 0 AS delay_count, strftime('%Y%m%dT%H%M%f','now') || '-' || hex(randomblob(4)) AS refresh_tick LIMIT 1"


def delayed_query_sql(delay_size: int) -> str:
    return (
        "WITH RECURSIVE\n"
        "  a(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM a WHERE x < {size}),\n"
        "  b(y) AS (SELECT 1 UNION ALL SELECT y + 1 FROM b WHERE y < {size})\n"
        "SELECT 'delayed' AS delay_kind,\n"
        "       sum(length(randomblob(16))) AS delay_count,\n"
        "       strftime('%Y%m%dT%H%M%f','now') || '-' || hex(randomblob(4)) AS refresh_tick\n"
        "FROM a CROSS JOIN b\n"
        "LIMIT 1"
    ).format(size=delay_size)


def query_sql(variant: str, delay_size: int) -> str:
    if variant == "fast":
        return fast_query_sql()
    if variant == "delayed":
        return delayed_query_sql(delay_size)
    raise ValueError(f"Unsupported variant: {variant}")


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", fixture_common.resource_json(actor, ["view.json"]))


def write_named_query(project_root: Path, query_path: str, sql: str, database: str, actor: str) -> None:
    query_dir = project_root / "ignition" / "named-query" / Path(*query_path.split("/"))
    query_dir.mkdir(parents=True, exist_ok=True)
    (query_dir / "query.sql").write_text(sql, encoding="utf-8", newline="\n")
    write_json(query_dir / "resource.json", refresh_common.named_query_resource(actor, database))


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    view_path: str,
    route: str,
    query_path: str,
    database: str,
    delay_size: int,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-datasource-delay"
    view_json = make_view_json(run_id, variant, query_path, delay_size)
    sql = query_sql(variant, delay_size)
    zip_path = zip_dir / f"{slug(run_id)}-datasource-delay-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-i06-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler data-source delay fixture", "enabled": True, "inheritable": False})
        write_view(project_root, view_path, view_json, actor)
        write_named_query(project_root, query_path, sql, database, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Data Source Delay {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "delaySize": delay_size if variant == "delayed" else 0,
        "viewPath": view_path,
        "route": route,
        "queryPath": query_path,
        "database": database,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "querySqlSha256": sha256_text(sql),
        "readyText": f"{run_id} {variant.upper()} I-06 READY",
        "secondaryReadyText": f"I06 {variant} result:",
        "watchTextRegex": rf"I06 {variant} result:\s*([^\s]+)",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Data Source Delay {package['variant']}"}],
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


def timed_call(client: cp.RunnerClient, name: str, payload: Dict[str, Any], timeout: Optional[int] = None) -> Tuple[Dict[str, Any], int]:
    started = time.perf_counter()
    record = client.call(name, payload, timeout=timeout)
    elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    return record, elapsed_ms


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        f"{args.run_id}-datasource-delay-{package['variant']}",
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
        f"I-06 data-source-delay {package['variant']} fixture",
        "--metric-name-contains",
        "Perspective",
        "--metric-name-contains",
        "perspective",
        "--metric-name-contains",
        "database",
        "--metric-name-contains",
        "Database",
        "--metric-name-contains",
        "query",
        "--metric-name-contains",
        "Query",
        "--metric-name-contains",
        "fetch",
        "--metric-name-contains",
        "Fetch",
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
        "--browser-wait-after-ready-ms",
        str(args.browser_wait_after_ready_ms),
        "--browser-click-selector",
        "button",
        "--browser-click-text",
        "Run query refresh",
        "--browser-click-label",
        f"{package['variant']} query refresh",
        "--browser-click-timeout-sec",
        str(args.browser_click_timeout_sec),
        "--browser-post-interaction-wait-ms",
        str(args.browser_post_interaction_wait_ms),
        "--browser-watch-text-selector",
        "body",
        "--browser-watch-text-regex",
        package["watchTextRegex"],
        "--browser-watch-text-label",
        "DelayQueryLabel",
        "--browser-watch-text-timeout-sec",
        str(args.browser_watch_text_timeout_sec),
        "--browser-viewport",
        args.browser_viewport,
    ]
    if args.browser_node_modules:
        command.extend(["--browser-node-modules", args.browser_node_modules])
    return command


def profile_ok(profile_dir: Path) -> bool:
    return hidden_common.profile_ok(profile_dir)


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    text = canonical_json(cp.response(record))
    return (
        package["queryPath"] in text
        and '"enabled":false' in text
        and '"type":"query"' in text
        and "refreshBinding" in text
        and package["readyText"] in text
    )


def query_refresh_proof(profile_dir: Path) -> Dict[str, Any]:
    return refresh_common.browser_refresh_proof(profile_dir)


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


def first_number(*values: Any) -> Optional[float]:
    return common.first_number(*values)


def metric_family_samples(profile_dir: Path) -> Dict[str, Any]:
    samples_path = profile_dir / "gateway-samples.ndjson"
    families = ("fetches", "query", "queries", "database", "databases")
    result: Dict[str, Dict[str, Dict[str, Any]]] = {family: {} for family in families}
    if not samples_path.exists():
        return {family: [] for family in families}
    for line in samples_path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        snapshot = row.get("metricsSnapshot", {}) if isinstance(row.get("metricsSnapshot"), dict) else {}
        metrics = snapshot.get("metrics", []) if isinstance(snapshot.get("metrics"), list) else []
        for metric in metrics:
            if not isinstance(metric, dict) or metric.get("ok") is not True:
                continue
            name = str(metric.get("name") or "").lower()
            for family in families:
                if family not in name:
                    continue
                value = first_number(metric.get("count"), metric.get("value"))
                if value is None:
                    continue
                bucket = result[family].setdefault(name, {"name": name, "first": None, "last": None, "delta": None, "maxOneMinuteRate": None, "maxP95Ms": None})
                if bucket["first"] is None:
                    bucket["first"] = value
                bucket["last"] = value
                rate = common.number(metric.get("oneMinuteRate"))
                if rate is not None:
                    current_rate = bucket.get("maxOneMinuteRate")
                    bucket["maxOneMinuteRate"] = rate if current_rate is None else max(float(current_rate), rate)
                p95 = first_number(metric.get("p95"), metric.get("p95Ms"))
                if p95 is not None:
                    current_p95 = bucket.get("maxP95Ms")
                    bucket["maxP95Ms"] = p95 if current_p95 is None else max(float(current_p95), p95)
    compacted: Dict[str, Any] = {}
    for family, metrics in result.items():
        rows = []
        for item in metrics.values():
            if item["first"] is not None and item["last"] is not None:
                item["delta"] = item["last"] - item["first"]
            rows.append(item)
        compacted[family] = sorted(rows, key=lambda item: item.get("name", ""))[:12]
    return compacted


def number(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def delta(target: Any, control: Any) -> Optional[float]:
    target_number = number(target)
    control_number = number(control)
    if target_number is None or control_number is None:
        return None
    return target_number - control_number


def abs_lte(value: Optional[float], limit: float) -> Optional[bool]:
    if value is None:
        return None
    return abs(value) <= limit


def compare_variants(summary: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    variants = {row.get("variant"): row for row in summary.get("variants", [])}
    fast = variants.get("fast", {})
    delayed = variants.get("delayed", {})
    fast_proof = fast.get("queryRefreshProof", {}) if isinstance(fast.get("queryRefreshProof"), dict) else {}
    delayed_proof = delayed.get("queryRefreshProof", {}) if isinstance(delayed.get("queryRefreshProof"), dict) else {}
    preview_delta = delta(delayed.get("queryPreviewElapsedMs"), fast.get("queryPreviewElapsedMs"))
    interaction_delta = delta(delayed_proof.get("resultElapsedMs"), fast_proof.get("resultElapsedMs"))
    long_task_delta = delta(delayed.get("browser", {}).get("longTaskTotalMs"), fast.get("browser", {}).get("longTaskTotalMs"))
    dom_delta = delta(delayed.get("browser", {}).get("domNodeCount"), fast.get("browser", {}).get("domNodeCount"))
    heap_delta = delta(delayed.get("browser", {}).get("usedJSHeapBytes"), fast.get("browser", {}).get("usedJSHeapBytes"))
    cpu_delta = delta(delayed.get("gateway", {}).get("processCpuLoadMedian"), fast.get("gateway", {}).get("processCpuLoadMedian"))
    result = {
        "fastPreviewElapsedMs": fast.get("queryPreviewElapsedMs"),
        "delayedPreviewElapsedMs": delayed.get("queryPreviewElapsedMs"),
        "previewElapsedDeltaMs": preview_delta,
        "fastInteractionResultElapsedMs": fast_proof.get("resultElapsedMs"),
        "delayedInteractionResultElapsedMs": delayed_proof.get("resultElapsedMs"),
        "interactionResultElapsedDeltaMs": interaction_delta,
        "browserLongTaskDeltaMs": long_task_delta,
        "browserDomNodeDelta": dom_delta,
        "browserHeapDeltaBytes": heap_delta,
        "gatewayCpuMedianDelta": cpu_delta,
        "previewDelayMet": preview_delta is not None and preview_delta >= args.min_delay_delta_ms,
        "interactionDelayMet": interaction_delta is not None and interaction_delta >= args.min_delay_delta_ms,
        "browserLongTasksStable": abs_lte(long_task_delta, args.max_browser_long_task_delta_ms),
        "browserDomStable": abs_lte(dom_delta, args.max_dom_node_delta),
        "gatewayCpuStable": abs_lte(cpu_delta, args.max_cpu_median_delta),
    }
    result["i06SignalsOk"] = bool(
        result["previewDelayMet"]
        and result["interactionDelayMet"]
        and result["browserLongTasksStable"] is not False
        and result["browserDomStable"] is not False
        and result["gatewayCpuStable"] is not False
    )
    return result


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# I-06 Data-Source Delay Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | OK | Preview ms | Click-to-label ms | DOM | Long task ms | CPU median | Query proof | Cleanup |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary.get("variants", []):
        proof = row.get("queryRefreshProof", {})
        browser = row.get("browser", {})
        gateway = row.get("gateway", {})
        cleanup = row.get("cleanupRouteAbsent", False) and row.get("cleanupViewAbsent", False) and row.get("cleanupNamedQueryAbsent", False)
        lines.append(
            "| {variant} | `{ok}` | {preview} | {interaction} | {dom} | {long_task} | {cpu} | click={click} changed={changed} | `{cleanup}` |".format(
                variant=row.get("variant"),
                ok=str(row.get("ok", False)).lower(),
                preview=row.get("queryPreviewElapsedMs"),
                interaction=proof.get("resultElapsedMs"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                cpu=gateway.get("processCpuLoadMedian"),
                click=proof.get("ok"),
                changed=proof.get("watchedTextChanged"),
                cleanup=str(cleanup).lower(),
            )
        )
    comparison = summary.get("comparison", {})
    lines.extend(["", "## I-06 Signal Check", ""])
    for key in [
        "previewElapsedDeltaMs",
        "interactionResultElapsedDeltaMs",
        "browserLongTaskDeltaMs",
        "browserDomNodeDelta",
        "browserHeapDeltaBytes",
        "gatewayCpuMedianDelta",
        "previewDelayMet",
        "interactionDelayMet",
        "browserLongTasksStable",
        "browserDomStable",
        "gatewayCpuStable",
        "i06SignalsOk",
    ]:
        lines.append(f"- `{key}`: `{comparison.get(key)}`")
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
    run_base = compact(args.run_id)
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    feature_set = refresh_common.feature_set_from_health(health)
    db_record = client.call(f"{args.run_id}-databaseConnectionsList", {"action": "databaseConnectionsList", "requestId": f"{args.run_id}-databaseConnectionsList"})
    database = refresh_common.choose_database(db_record, args.database)
    if not database:
        raise RuntimeError("No database connection available for disposable read-only Named Query fixture")

    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    for variant_name in VARIANTS:
        variant_dir = out_dir / variant_name
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{run_base}/DataSourceDelay{variant_name.title()}"
        query_path = f"{args.named_query_path_prefix.rstrip('/')}/{run_base}/{variant_name.title()}DelayQuery"
        package = build_package(variant_dir, project, args.run_id, variant_name, view_path, route, query_path, database, args.delay_size)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        backup_name = ""
        gates: Dict[str, bool] = {}
        baseline_wait: Dict[str, Any] = {"enabled": False}
        try:
            if args.wait_for_clean_baseline:
                baseline_wait = refresh_common.wait_for_clean_baseline(
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
            time.sleep(args.apply_settle_sec)
            query_read = client.call(f"{args.run_id}-{variant_name}-namedQueryRead", named_query_read_payload(f"{args.run_id}-{variant_name}-namedQueryRead", project, query_path, args))
            gates["namedQueryRead"] = cp.ok(query_read)
            query_preview, preview_elapsed_ms = timed_call(
                client,
                f"{args.run_id}-{variant_name}-namedQueryPreview",
                named_query_preview_payload(f"{args.run_id}-{variant_name}-namedQueryPreview", project, query_path, args),
                timeout=args.timeout_sec,
            )
            gates["namedQueryPreview"] = cp.ok(query_preview)
            readback = client.call(f"{args.run_id}-{variant_name}-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, view_path, args))
            gates["viewRead"] = cp.ok(readback) and readback_ok(readback, package)
            page = client.call(f"{args.run_id}-{variant_name}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_attempts: List[Dict[str, Any]] = []
            profile_dir = variant_dir / "profile"
            profile_result: Dict[str, Any] = {}
            proof: Dict[str, Any] = {}
            profile_gate = False
            proof_gate = False
            for attempt in range(1, args.profile_retries + 1):
                attempt_dir = variant_dir / ("profile" if args.profile_retries == 1 else f"profile-attempt-{attempt}")
                profile_result = common.run_command(
                    profile_command(args, package, project, browser_url, attempt_dir),
                    f"profile-datasource-delay-{variant_name}-attempt-{attempt}",
                    variant_dir,
                    args.command_timeout_sec,
                    env,
                )
                attempt_profile_ok = bool(profile_result.get("ok")) and profile_ok(attempt_dir)
                attempt_proof = query_refresh_proof(attempt_dir)
                attempt_proof_ok = bool(attempt_proof.get("ok") is True and attempt_proof.get("watchedTextChanged") is True)
                profile_dir = attempt_dir
                proof = attempt_proof
                profile_attempts.append(
                    {
                        "attempt": attempt,
                        "profileDir": str(attempt_dir),
                        "profileOk": attempt_profile_ok,
                        "queryRefreshProofOk": attempt_proof_ok,
                        "queryRefreshProof": attempt_proof,
                        "command": profile_result,
                    }
                )
                if attempt_profile_ok and attempt_proof_ok:
                    profile_gate = True
                    proof_gate = True
                    break
                if attempt < args.profile_retries:
                    time.sleep(args.profile_retry_delay_sec)
            gates["profile"] = profile_gate
            gates["queryRefreshProof"] = proof_gate
            variant = {
                "variant": variant_name,
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "queryPath": query_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "queryPreviewElapsedMs": preview_elapsed_ms,
                "queryPreviewOk": cp.ok(query_preview),
                "profileDir": str(profile_dir),
                "browser": hidden_common.browser_metrics(profile_dir),
                "network": network_summary(profile_dir),
                "gateway": hidden_common.gateway_metrics(profile_dir),
                "static": hidden_common.static_summary(profile_dir),
                "metricFamilies": metric_family_samples(profile_dir),
                "queryRefreshProof": proof,
                "profileCommand": profile_result,
                "profileAttempts": profile_attempts,
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
                time.sleep(args.apply_settle_sec)
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
            if args.pause_sec > 0 and variant_name != VARIANTS[-1]:
                time.sleep(args.pause_sec)

    summary = {
        "ok": False,
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "features": sorted(feature_set),
        "database": "<databaseConnection>",
        "actualDatabaseEvidence": database,
        "delaySize": args.delay_size,
        "minDelayDeltaMs": args.min_delay_delta_ms,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "baselineWaitIntervalSeconds": args.baseline_wait_interval_sec if args.wait_for_clean_baseline else None,
        "variants": variants,
        "packages": package_records,
        "interpretation": [
            "This is a controlled I-06 mechanics fixture, not a customer route conclusion.",
            "Both variants use polling-disabled read-only Named Queries and the same manual refreshBinding() interaction path.",
            "The delayed variant uses bounded SQL with a literal LIMIT to satisfy runner-side DB safety checks.",
            "Treat the direct Named Query preview and the click-to-query-label latency as the primary data-source delay signals.",
            "Browser DOM/long-task and Gateway CPU stability are safety signals; if they move materially, classify the run as mixed rather than data-source-only.",
        ],
    }
    comparison = compare_variants(summary, args)
    summary["comparison"] = comparison
    summary["ok"] = bool(cp.ok(health) and cp.ok(db_record) and variants and all(row.get("ok") for row in variants) and comparison.get("i06SignalsOk"))
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
    parser.add_argument("--delay-size", type=int, default=2500, help="Bound for the delayed SQLite CTE fixture. Default: 2500.")
    parser.add_argument("--min-delay-delta-ms", type=float, default=500.0, help="Minimum delayed-minus-fast preview and interaction delta. Default: 500.")
    parser.add_argument("--max-browser-long-task-delta-ms", type=float, default=750.0, help="Allowed delayed-minus-fast browser long-task delta. Default: 750.")
    parser.add_argument("--max-dom-node-delta", type=float, default=75.0, help="Allowed delayed-minus-fast DOM node delta. Default: 75.")
    parser.add_argument("--max-cpu-median-delta", type=float, default=0.25, help="Allowed delayed-minus-fast Gateway process CPU median delta. Default: 0.25.")
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--named-query-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--allowed-named-query-prefix", default=DEFAULT_ALLOWED_NAMED_QUERY_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=12.0)
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--max-metrics", type=int, default=60)
    parser.add_argument("--timeout-sec", type=int, default=90)
    parser.add_argument("--command-timeout-sec", type=int, default=420)
    parser.add_argument("--apply-settle-sec", type=float, default=3.0, help="Seconds to wait after apply or rollback before browser/readback follow-up. Default: 3.")
    parser.add_argument("--profile-retries", type=int, default=2, help="Profile attempts per variant before failing the variant. Default: 2.")
    parser.add_argument("--profile-retry-delay-sec", type=float, default=5.0, help="Seconds to wait between profile attempts. Default: 5.")
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=75.0)
    parser.add_argument("--browser-click-timeout-sec", type=float, default=25.0)
    parser.add_argument("--browser-watch-text-timeout-sec", type=float, default=25.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=500)
    parser.add_argument("--browser-post-interaction-wait-ms", type=int, default=3000)
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
    if args.delay_size < 100 or args.delay_size > 4000:
        raise SystemExit("--delay-size must be between 100 and 4000")
    if args.min_delay_delta_ms < 0:
        raise SystemExit("--min-delay-delta-ms must be >= 0")
    if args.max_browser_long_task_delta_ms < 0:
        raise SystemExit("--max-browser-long-task-delta-ms must be >= 0")
    if args.max_dom_node_delta < 0:
        raise SystemExit("--max-dom-node-delta must be >= 0")
    if args.max_cpu_median_delta < 0:
        raise SystemExit("--max-cpu-median-delta must be >= 0")
    if args.browser_wait_after_ready_ms < 0:
        raise SystemExit("--browser-wait-after-ready-ms must be >= 0")
    if args.browser_post_interaction_wait_ms < 0:
        raise SystemExit("--browser-post-interaction-wait-ms must be >= 0")
    if args.apply_settle_sec < 0:
        raise SystemExit("--apply-settle-sec must be >= 0")
    if args.profile_retries < 1 or args.profile_retries > 5:
        raise SystemExit("--profile-retries must be between 1 and 5")
    if args.profile_retry_delay_sec < 0:
        raise SystemExit("--profile-retry-delay-sec must be >= 0")
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
