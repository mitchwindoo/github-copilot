#!/usr/bin/env python3
"""Run guarded Perspective transform-cost fixtures for A-05."""

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
import run_property_change_chain as storm_common
import run_table_ab_remediation as table_common
import run_tab_runwhilehidden_ab as tab_common


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
VARIANTS = ("document-data", "expression-only", "script-transform")


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


def safe_rmtree(path: Path, *allowed_roots: Path) -> None:
    storm_common.safe_rmtree(path, *allowed_roots)


def component(
    component_type: str,
    *,
    meta: Dict[str, Any] | None = None,
    props: Dict[str, Any] | None = None,
    custom: Dict[str, Any] | None = None,
    position: Dict[str, Any] | None = None,
    prop_config: Dict[str, Any] | None = None,
    children: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {"type": component_type}
    if meta is not None:
        row["meta"] = meta
    if custom is not None:
        row["custom"] = custom
    if position is not None:
        row["position"] = position
    if prop_config is not None:
        row["propConfig"] = prop_config
    if props is not None:
        row["props"] = props
    if children is not None:
        row["children"] = children
    return row


def expression_binding(expression: str) -> Dict[str, Any]:
    return {"binding": {"type": "expr", "config": {"expression": expression}}}


def property_binding(path: str, transform_code: str = "") -> Dict[str, Any]:
    binding: Dict[str, Any] = {"type": "property", "config": {"path": path}}
    if transform_code:
        binding["transforms"] = [{"type": "script", "script": transform_code}]
    return {"binding": binding}


def transform_code(work_iterations: int) -> str:
    return "\n".join(
        [
            "\ttry:",
            "\t\tbase = int(value)",
            "\texcept:",
            "\t\tbase = 0",
            "\tacc = 0",
            f"\tfor n in range({work_iterations}):",
            "\t\tacc = (acc + ((base + n) * 17)) % 9973",
            "\treturn 'A-05 VALUE ' + str(base) + ' checksum ' + str(acc)",
        ]
    ) + "\n"


def expected_text(index: int, work_iterations: int) -> str:
    acc = 0
    for n in range(work_iterations):
        acc = (acc + ((index + n) * 17)) % 9973
    return f"A-05 VALUE {index} checksum {acc}"


def expression_text(index: int, work_iterations: int) -> str:
    return "'" + expected_text(index, work_iterations).replace("'", "\\'") + "'"


def make_workload_label(index: int, variant: str, work_iterations: int) -> Dict[str, Any]:
    props = {
        "text": f"A-05 seed {index:03d}",
        "style": {
            "backgroundColor": "#ffffff",
            "borderColor": "#d1d5db",
            "borderRadius": 4,
            "borderStyle": "solid",
            "borderWidth": "1px",
            "color": "#1f2937",
            "fontSize": 12,
            "overflow": "hidden",
            "padding": "5px 7px",
            "textOverflow": "ellipsis",
            "whiteSpace": "nowrap",
        },
    }
    if variant == "document-data":
        prop_config = {"props.text": property_binding(f"view.custom.rows.row{index:03d}.text")}
    elif variant == "expression-only":
        prop_config = {"props.text": expression_binding(expression_text(index, work_iterations))}
    elif variant == "script-transform":
        prop_config = {"props.text": property_binding(f"view.custom.inputs.row{index:03d}.value", transform_code(work_iterations))}
    else:
        raise ValueError(f"Unsupported variant: {variant}")
    return component(
        "ia.display.label",
        meta={"name": f"Transform Workload {index:03d}"},
        position={"basis": "28px", "grow": 1, "shrink": 1},
        props=props,
        prop_config=prop_config,
    )


def make_view_json(args: argparse.Namespace, variant: str) -> Dict[str, Any]:
    if variant not in VARIANTS:
        raise ValueError(f"Unsupported variant: {variant}")
    ready = f"{args.run_id} {variant.upper()} READY"
    rows = {f"row{index:03d}": {"value": index, "text": expected_text(index, args.work_iterations)} for index in range(1, args.label_count + 1)}
    inputs = {f"row{index:03d}": {"value": index} for index in range(1, args.label_count + 1)}
    children: List[Dict[str, Any]] = [
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
            position={"basis": "44px", "grow": 0, "shrink": 0},
            props={
                "text": (
                    f"A-05 transform-cost fixture: {variant}, {args.label_count} labels, "
                    f"{args.work_iterations} script-loop iterations where applicable"
                ),
                "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
            },
        ),
        component(
            "ia.container.flex",
            meta={"name": "Workload Grid"},
            position={"basis": "auto", "grow": 1, "shrink": 1},
            props={
                "direction": "row",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "wrap",
                "style": {"gap": "6px", "overflow": "auto"},
            },
            children=[make_workload_label(index, variant, args.work_iterations) for index in range(1, args.label_count + 1)],
        ),
    ]
    return {
        "custom": {
            "runId": args.run_id,
            "variant": variant,
            "labelCount": args.label_count,
            "workIterations": args.work_iterations,
            "rows": rows,
            "inputs": inputs,
            "firstExpected": expected_text(1, args.work_iterations),
            "lastExpected": expected_text(args.label_count, args.work_iterations),
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "transform-cost-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {"backgroundColor": "#f8fafc", "overflow": "auto", "padding": "12px"},
            },
            children=children,
        ),
        "permissions": {},
    }


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-transform-cost-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", table_common.resource_json(actor, ["view.json"]))


def build_package(out_dir: Path, project: str, args: argparse.Namespace, variant: str, view_path: str, route: str) -> Dict[str, Any]:
    zip_dir = out_dir / "package"
    if zip_dir.exists():
        safe_rmtree(zip_dir, out_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-transform-cost"
    view_json = make_view_json(args, variant)
    zip_path = zip_dir / "fixture.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-transform-cost-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            project_root / "project.json",
            {"title": project, "description": "Performance profiler transform-cost fixture", "enabled": True, "inheritable": False},
        )
        write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Transform Cost {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", table_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    package_base64 = common.zip_file_base64(zip_path)
    return {
        "variant": variant,
        "labelCount": args.label_count,
        "workIterations": args.work_iterations,
        "route": route,
        "viewPath": view_path,
        "zipPath": str(zip_path),
        "zipBytes": zip_path.stat().st_size,
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": package_base64,
        "packageBase64Bytes": len(package_base64),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": f"{args.run_id} {variant.upper()} READY",
        "firstExpected": expected_text(1, args.work_iterations),
        "lastExpected": expected_text(args.label_count, args.work_iterations),
        "profileRunId": storm_common.profile_run_id(args.run_id, variant),
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Transform Cost {package['variant']}"}],
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
        "routePaths": [],
        "dryRun": dry_run,
        "removeMissingViews": True,
        "removeMissingScripts": False,
        "removeMissingNamedQueries": False,
    }
    if not dry_run:
        payload["confirmRollback"] = "ROLLBACK"
    return payload


def backup_name_from_record(record: Dict[str, Any]) -> str:
    return table_common.backup_name_from_response(cp.response(record))


def collect_env(endpoint: str, token: str, project: str) -> Dict[str, str]:
    env = os.environ.copy()
    if endpoint:
        env["IGNITION_RUNNER_ENDPOINT"] = endpoint
    if token:
        env["IGNITION_RUNNER_TOKEN"] = token
    if project:
        env["IGNITION_PROJECT"] = project
    return env


def browser_url_from_endpoint(endpoint: str, project: str, route: str) -> str:
    return table_common.browser_url_from_endpoint(endpoint, project, route)


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        str(package["profileRunId"]),
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
        "transform-cost A-05 fixture",
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
    variant = str(package["variant"])
    script_expected = variant == "script-transform"
    script_present = '"type":"script"' in response_text or '"type": "script"' in response_text
    return (
        cp.ok(record)
        and f'"variant":"{variant}"' in response_text
        and f'"labelCount":{package["labelCount"]}' in response_text
        and f'"workIterations":{package["workIterations"]}' in response_text
        and str(package["readyText"]) in response_text
        and str(package["firstExpected"]) in response_text
        and str(package["lastExpected"]) in response_text
        and ("rows" in response_text if variant == "document-data" else True)
        and (script_present if script_expected else not script_present)
    )


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    profile = read_json(profile_dir / "static-profile.json")
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "scriptCount": summary.get("scriptCount"),
        "scriptChars": summary.get("scriptChars"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
    }


def family_rollup(metric_families: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for family in ("expressions", "property-changes", "scripts", "queue-tasks", "messages-sent"):
        rows = metric_families.get(family, []) if isinstance(metric_families.get(family), list) else []
        deltas = [common.number(row.get("delta")) for row in rows if isinstance(row, dict)]
        rates = [common.number(row.get("maxOneMinuteRate")) for row in rows if isinstance(row, dict)]
        numeric_deltas = [float(value) for value in deltas if value is not None]
        positive_deltas = [value for value in numeric_deltas if value > 0]
        numeric_rates = [float(value) for value in rates if value is not None]
        key = family.replace("-", "")
        result[f"{key}DeltaMax"] = max(numeric_deltas) if numeric_deltas else None
        result[f"{key}PositiveDeltaSum"] = sum(positive_deltas) if positive_deltas else 0.0
        result[f"{key}RateMax"] = max(numeric_rates) if numeric_rates else None
    return result


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
    gateway = data.get("gatewayDeltas", {}) if isinstance(data.get("gatewayDeltas"), dict) else {}

    def delta(bucket: Dict[str, Any], key: str) -> Any:
        row = bucket.get(key)
        return row.get("delta") if isinstance(row, dict) else None

    return {
        "scriptCountDelta": delta(static, "scriptCount"),
        "viewJsonBytesDelta": delta(static, "viewJsonBytes"),
        "domNodeCountDelta": delta(browser, "domNodeCount"),
        "largestContentfulPaintMsDelta": delta(browser, "largestContentfulPaintMs"),
        "longTaskTotalMsDelta": delta(browser, "longTaskTotalMs"),
        "usedJSHeapBytesDelta": delta(browser, "usedJSHeapBytes"),
        "processCpuLoadAvgDelta": delta(gateway, "processCpuLoad"),
        "heapUsedBytesAvgDelta": delta(gateway, "heapUsedBytes"),
    }


def gate_detail(record: Dict[str, Any]) -> Dict[str, Any]:
    data = cp.response(record)
    return {
        "httpStatus": record.get("httpStatus"),
        "ok": cp.ok(record),
        "requestId": data.get("requestId") or (record.get("request") or {}).get("requestId"),
        "responseOk": data.get("ok"),
        "responseKind": "raw" if "raw" in data else "json",
        "error": record.get("error"),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Transform Cost A/B Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | OK | Labels | Static scripts | Script delta max | Expression delta max | Queue rate max | DOM | Long task ms | WS recv | Cleanup |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        static = row.get("static", {})
        browser = row.get("browser", {})
        network = row.get("network", {})
        rollup = row.get("metricRollup", {})
        lines.append(
            "| {variant} | `{ok}` | {labels} | {scripts} | {script_delta} | {expr_delta} | {queue_rate} | {dom} | {long_task} | {ws_recv} | `{cleanup}` |".format(
                variant=row.get("variant"),
                ok=str(row.get("ok", False)).lower(),
                labels=row.get("labelCount"),
                scripts=static.get("scriptCount"),
                script_delta=rollup.get("scriptsDeltaMax"),
                expr_delta=rollup.get("expressionsDeltaMax"),
                queue_rate=rollup.get("queuetasksRateMax"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                ws_recv=network.get("webSocketBytesReceived"),
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewsAbsent", False)).lower(),
            )
        )
    lines.extend(["", "## Baseline Comparisons", ""])
    for row in summary.get("comparisons", []):
        lines.append(f"- `{row.get('variant')}`: comparison ok `{str(row.get('ok', False)).lower()}` at `{row.get('comparisonDir')}`")
        primary = row.get("primary", {}) if isinstance(row.get("primary"), dict) else {}
        for key, value in primary.items():
            lines.append(f"  - `{key}`: `{value}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        safe_rmtree(out_dir, Path.cwd(), SKILL_DIR)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    env = collect_env(endpoint, token, project)
    run_slug = slug(args.run_id)
    base = compact(args.run_id)
    requested_variants = [part.strip() for part in args.variants.split(",") if part.strip()]
    if not requested_variants:
        raise SystemExit("--variants must contain at least one variant")
    unsupported = sorted(set(requested_variants) - set(VARIANTS))
    if unsupported:
        raise SystemExit(f"Unsupported variants: {', '.join(unsupported)}")

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_response = cp.response(health)
    feature_set = cp.enabled_name_set(health_response.get("features", []))
    action_set = cp.enabled_name_set(health_response.get("supportedActions", []))
    baseline_capability_set = feature_set | action_set if action_set else feature_set
    variants: List[Dict[str, Any]] = []
    packages: List[Dict[str, Any]] = []
    comparisons: List[Dict[str, Any]] = []
    baseline_profile_dir: Path | None = None

    for variant in requested_variants:
        variant_dir = out_dir / variant
        route = build_route(args.route_prefix, run_slug, variant)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/TransformCost{variant.replace('-', '').title()}"
        package = build_package(variant_dir, project, args, variant, view_path, route)
        packages.append({key: value for key, value in package.items() if key != "packageBase64"})
        backup_name = ""
        gates: Dict[str, bool] = {}
        gate_details: Dict[str, Any] = {}
        baseline: Dict[str, Any] = {"enabled": False}
        try:
            if args.wait_for_clean_baseline:
                baseline = tab_common.wait_for_clean_baseline(
                    client,
                    out_dir,
                    args.run_id,
                    project,
                    variant,
                    baseline_capability_set,
                    args.baseline_max_browser_sessions,
                    args.baseline_wait_timeout_sec,
                    args.baseline_wait_interval_sec,
                )
                gates["cleanBaseline"] = baseline.get("ok") is True
                if args.fail_on_baseline_timeout and not gates["cleanBaseline"]:
                    raise RuntimeError(f"clean baseline wait failed for {variant}: {baseline.get('lastCounts')}")

            dry = client.call(f"{args.run_id}-{variant}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant}-dryRun", project, package, args))
            gates["dryRun"] = cp.ok(dry)
            gate_details["dryRun"] = gate_detail(dry)
            if not gates["dryRun"]:
                raise RuntimeError(f"dryRun failed for {variant}: {gate_details['dryRun']}")

            apply = client.call(f"{args.run_id}-{variant}-apply", package_payload("apply", f"{args.run_id}-{variant}-apply", project, package, args))
            gates["apply"] = cp.ok(apply)
            gate_details["apply"] = gate_detail(apply)
            backup_name = backup_name_from_record(apply)
            if not gates["apply"]:
                raise RuntimeError(f"apply failed for {variant}: {gate_details['apply']}")

            view_read = client.call(f"{args.run_id}-{variant}-viewRead", view_read_payload(f"{args.run_id}-{variant}-viewRead", project, view_path, args))
            gates["viewRead"] = readback_ok(view_read, package)
            gate_details["viewRead"] = gate_detail(view_read)
            if not gates["viewRead"]:
                raise RuntimeError(f"viewRead failed for {variant}: {gate_details['viewRead']}")

            page_validate = client.call(f"{args.run_id}-{variant}-pageValidate", page_validate_payload(f"{args.run_id}-{variant}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page_validate)
            gate_details["pageValidate"] = gate_detail(page_validate)
            if not gates["pageValidate"]:
                raise RuntimeError(f"pageValidate failed for {variant}: {gate_details['pageValidate']}")

            browser_url = browser_url_from_endpoint(endpoint, project, route)
            profile_dir = (variant_dir / "profile").resolve()
            profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), f"profile-{variant}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            if not gates["profile"]:
                raise RuntimeError(f"profile failed for {variant}: {profile_result}")

            metric_families = hidden_common.metric_family_samples(profile_dir)
            row: Dict[str, Any] = {
                "variant": variant,
                "labelCount": args.label_count,
                "workIterations": args.work_iterations,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "baselineWait": baseline,
                "gates": gates,
                "gateDetails": gate_details,
                "profileCommand": profile_result,
                "profileDir": str(profile_dir),
                "static": static_summary(profile_dir),
                "browser": common.browser_metrics(profile_dir),
                "gateway": common.gateway_metrics(profile_dir),
                "network": network_metrics(profile_dir),
                "metricFamilies": metric_families,
                "metricRollup": family_rollup(metric_families),
                "ok": all(gates.values()),
            }
            if baseline_profile_dir is None:
                baseline_profile_dir = profile_dir
            elif baseline_profile_dir is not None:
                comparison = compare_to_baseline(out_dir, baseline_profile_dir, profile_dir, variant)
                if comparison.get("ok"):
                    comparison["primary"] = comparison_primary(Path(str(comparison["comparisonDir"])))
                comparisons.append(comparison)
                row["ok"] = bool(row["ok"] and comparison.get("ok"))
            variants.append(row)
        except Exception as exc:
            variants.append(
                {
                    "variant": variant,
                    "labelCount": args.label_count,
                    "workIterations": args.work_iterations,
                    "route": route,
                    "viewPath": view_path,
                    "backupName": backup_name,
                    "baselineWait": baseline,
                    "gates": gates,
                    "gateDetails": gate_details,
                    "ok": False,
                    "error": str(exc),
                }
            )
        finally:
            if backup_name:
                rb_dry = client.call(
                    f"{args.run_id}-{variant}-rollback-dryRun",
                    rollback_payload(f"{args.run_id}-{variant}-rollback-dryRun", project, backup_name, view_path, True),
                )
                rb_apply = client.call(
                    f"{args.run_id}-{variant}-rollback-apply",
                    rollback_payload(f"{args.run_id}-{variant}-rollback-apply", project, backup_name, view_path, False),
                )
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
                after_read = client.call(
                    f"{args.run_id}-{variant}-post-cleanup-viewRead",
                    view_read_payload(f"{args.run_id}-{variant}-post-cleanup-viewRead", project, view_path, args),
                )
                row = variants[-1]
                row["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                row["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                row["cleanupViewsAbsent"] = not cp.ok(after_read)
                row["ok"] = bool(row.get("ok") and row["rollbackOk"] and row["cleanupRouteAbsent"] and row["cleanupViewsAbsent"])
            if args.pause_sec > 0 and variant != requested_variants[-1]:
                time.sleep(args.pause_sec)

    summary = {
        "ok": bool(cp.ok(health) and variants and all(row.get("ok") for row in variants) and all(row.get("ok") for row in comparisons)),
        "runId": args.run_id,
        "createdAt": common.utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": health_response.get("runnerVersion"),
        "stackVersion": health_response.get("stackVersion"),
        "features": sorted(feature_set),
        "supportedActions": sorted(action_set),
        "variantsRequested": requested_variants,
        "labelCount": args.label_count,
        "workIterations": args.work_iterations,
        "healthOk": cp.ok(health),
        "variants": variants,
        "comparisons": comparisons,
        "packages": packages,
        "interpretation": [
            "This is a controlled A-05 transform-cost fixture, not a customer route conclusion.",
            "The variants render the same visible values using Document/custom-property data, expression-only bindings, or property bindings with script transforms.",
            "Use static script count, Perspective script/expression/property/queue metrics, browser timing, network bytes, and cleanup gates together.",
            "Promote a remediation only when the same customer behavior is proven and repeated clean-baseline pairs meet the declared comparison rule.",
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
    parser.add_argument("--variants", default="document-data,expression-only,script-transform")
    parser.add_argument("--label-count", type=int, default=80)
    parser.add_argument("--work-iterations", type=int, default=250)
    parser.add_argument("--route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=12.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--command-timeout-sec", type=int, default=600)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=120.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=3000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--wait-for-clean-baseline", action="store_true")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0)
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=420.0)
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0)
    parser.add_argument("--fail-on-baseline-timeout", action="store_true")
    parser.add_argument("--pause-sec", type=float, default=0.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.label_count < 1:
        raise SystemExit("--label-count must be >= 1")
    if args.work_iterations < 0:
        raise SystemExit("--work-iterations must be >= 0")
    if args.profile_duration_sec <= 0:
        raise SystemExit("--profile-duration-sec must be > 0")
    summary = run(args)
    print(json.dumps({"ok": summary.get("ok"), "summaryPath": str(Path(args.out_dir) / "summary.json")}, indent=2))
    if not summary.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
