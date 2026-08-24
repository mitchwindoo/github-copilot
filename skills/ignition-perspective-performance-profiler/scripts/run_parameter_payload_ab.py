#!/usr/bin/env python3
"""Run guarded Perspective parameter-payload A/B fixtures."""

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
from typing import Any, Dict, List, Optional

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_table_ab_remediation as fixture_common
import run_tab_runwhilehidden_ab as tab_common


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
VARIANTS = ("scalar-params", "deep-params")
CARRIERS = ("embedded-view", "flex-repeater", "view-canvas")


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


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-param-payload-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def make_deep_payload(index: int, group_count: int, width: int, depth: int) -> Dict[str, Any]:
    def nested(level: int, seed: int) -> Dict[str, Any]:
        node: Dict[str, Any] = {
            "level": level,
            "label": f"nested-{seed:03d}-{level:02d}",
            "values": [seed + offset for offset in range(width)],
        }
        if level > 1:
            node["child"] = nested(level - 1, seed + 1)
        return node

    groups = []
    for group_index in range(group_count):
        readings = []
        for item_index in range(width):
            readings.append(
                {
                    "name": f"P{index:03d}_G{group_index:03d}_R{item_index:03d}",
                    "value": (index + 1) * (group_index + 1) * (item_index + 1),
                    "quality": "Good",
                    "units": "count",
                    "limits": {"lo": 0, "hi": 100000},
                }
            )
        groups.append(
            {
                "groupId": f"group-{group_index:03d}",
                "display": f"Parameter Group {group_index:03d}",
                "readings": readings,
                "nested": nested(max(depth, 1), index + group_index),
            }
        )
    return {
        "schema": "perf-profiler-parameter-payload-v1",
        "source": "fixture",
        "asset": f"asset-{index:03d}",
        "groups": groups,
        "flags": {"operatorVisible": True, "diagnosticPayload": True},
    }


def params_for_variant(args: argparse.Namespace, variant: str, index: int, ready_text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "readyText": ready_text,
        "mode": variant,
        "index": index,
        "assetId": f"asset-{index:03d}",
        "line": "LineA",
        "cell": "Cell01",
    }
    if variant == "deep-params":
        params["deepPayload"] = make_deep_payload(index, args.deep_groups, args.deep_width, args.deep_depth)
    return params


def make_child_view(run_id: str) -> Dict[str, Any]:
    input_params = {
        f"params.{name}": {"paramDirection": "input"}
        for name in ("readyText", "mode", "index", "assetId", "line", "cell", "deepPayload")
    }
    return {
        "custom": {"runId": run_id, "role": "parameter-payload-child"},
        "params": {"readyText": "", "mode": "", "index": 0, "assetId": "", "line": "", "cell": "", "deepPayload": {}},
        "propConfig": input_params,
        "props": {"defaultSize": {"width": 260, "height": 96}},
        "root": component(
            "ia.container.flex",
            meta={"name": "param-child-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "style": {
                    "backgroundColor": "#ffffff",
                    "borderColor": "#cbd5e1",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "overflow": "hidden",
                    "padding": "6px",
                },
            },
            children=[
                component(
                    "ia.display.label",
                    meta={"name": "Child Ready From Param"},
                    position={"basis": "32px", "grow": 0, "shrink": 0},
                    props={
                        "text": "waiting for params",
                        "style": {"color": "#111827", "fontSize": 13, "fontWeight": "700", "whiteSpace": "pre-wrap"},
                    },
                    prop_config={"props.text": expression_binding("{view.params.readyText}")},
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Static Child Shape Marker"},
                    position={"basis": "24px", "grow": 0, "shrink": 0},
                    props={
                        "text": "same child view and visible component shape",
                        "style": {"color": "#475569", "fontSize": 11, "whiteSpace": "pre-wrap"},
                    },
                ),
            ],
        ),
        "permissions": {},
    }


def instance_count(args: argparse.Namespace) -> int:
    value = getattr(args, "instance_count", None)
    return int(value if value is not None else args.embedded_count)


def carrier_label(carrier: str) -> str:
    return {
        "embedded-view": "Embedded View",
        "flex-repeater": "Flex Repeater",
        "view-canvas": "View Canvas",
    }.get(carrier, carrier)


def make_carrier_component(args: argparse.Namespace, variant: str, child_view_path: str, ready_text: str) -> Dict[str, Any]:
    count = instance_count(args)
    if args.carrier == "embedded-view":
        embedded_children = []
        for index in range(1, count + 1):
            embedded_children.append(
                component(
                    "ia.display.view",
                    meta={"name": f"Embedded Param Child {index:03d}"},
                    position={"basis": "96px", "grow": 0, "shrink": 0},
                    props={
                        "path": child_view_path,
                        "params": params_for_variant(args, variant, index, ready_text),
                        "style": {"margin": "3px"},
                    },
                )
            )
        return component(
            "ia.container.flex",
            meta={"name": "Embedded Param Grid"},
            position={"basis": "auto", "grow": 1, "shrink": 1},
            props={
                "direction": "row",
                "alignItems": "flex-start",
                "justify": "flex-start",
                "wrap": "wrap",
                "style": {"overflow": "auto", "padding": "4px"},
            },
            children=embedded_children,
        )

    if args.carrier == "flex-repeater":
        instances = []
        for index in range(1, count + 1):
            instance = params_for_variant(args, variant, index, ready_text)
            instance["instancePosition"] = {"basis": "96px", "grow": 0, "shrink": 0}
            instance["instanceStyle"] = {"margin": "3px"}
            instances.append(instance)
        return component(
            "ia.display.flex-repeater",
            meta={"name": "Flex Repeater Param Carrier"},
            position={"basis": "auto", "grow": 1, "shrink": 1},
            props={
                "path": child_view_path,
                "instances": instances,
                "direction": "row",
                "alignItems": "flex-start",
                "justify": "flex-start",
                "wrap": "wrap",
                "style": {"overflow": "auto", "padding": "4px"},
            },
        )

    if args.carrier == "view-canvas":
        canvas_instances = []
        columns = max(1, int(args.canvas_columns))
        cell_width = 280
        cell_height = 112
        for index in range(1, count + 1):
            zero_index = index - 1
            row = zero_index // columns
            column = zero_index % columns
            canvas_instances.append(
                {
                    "viewPath": child_view_path,
                    "viewParams": params_for_variant(args, variant, index, ready_text),
                    "position": "absolute",
                    "style": {"backgroundColor": "#ffffff", "overflow": "hidden"},
                    "top": row * cell_height,
                    "left": column * cell_width,
                    "width": 260,
                    "height": 96,
                    "zIndex": index,
                }
            )
        return component(
            "ia.display.viewcanvas",
            meta={"name": "View Canvas Param Carrier"},
            position={"basis": "auto", "grow": 1, "shrink": 1},
            props={
                "instances": canvas_instances,
                "style": {"backgroundColor": "#ffffff", "overflow": "auto"},
                "transitionSettings": {"duration": "0.15s", "timingFunction": "ease-out"},
                "useDefaultViewHeight": False,
                "useDefaultViewWidth": False,
            },
        )

    raise ValueError(f"Unsupported carrier {args.carrier!r}")


def make_parent_view(args: argparse.Namespace, run_id: str, variant: str, child_view_path: str) -> Dict[str, Any]:
    ready_text = f"{run_id} {variant.upper()} CHILD READY"
    count = instance_count(args)
    label = carrier_label(args.carrier)
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "carrier": args.carrier,
            "instanceCount": count,
            "embeddedCount": count,
            "childViewPath": child_view_path,
            "deepGroups": args.deep_groups if variant == "deep-params" else 0,
            "deepWidth": args.deep_width if variant == "deep-params" else 0,
            "deepDepth": args.deep_depth if variant == "deep-params" else 0,
            "expectedReadyText": ready_text,
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "parameter-payload-root"},
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
                    meta={"name": "Parent Summary"},
                    position={"basis": "42px", "grow": 0, "shrink": 0},
                    props={
                        "text": f"A-14 parameter payload fixture: {variant}, carrier {label}, instances {count}",
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
                make_carrier_component(args, variant, child_view_path, ready_text),
            ],
        ),
        "permissions": {},
    }


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", fixture_common.resource_json(actor, ["view.json"]))


def build_package(out_dir: Path, project: str, args: argparse.Namespace, variant: str, parent_view_path: str, child_view_path: str, route: str) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-parameter-payload"
    parent_view = make_parent_view(args, args.run_id, variant, child_view_path)
    child_view = make_child_view(args.run_id)
    zip_path = zip_dir / f"{slug(args.run_id)}-param-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-param-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler parameter payload fixture", "enabled": True, "inheritable": False})
        write_view(project_root, child_view_path, child_view, actor)
        write_view(project_root, parent_view_path, parent_view, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Parameter Payload {variant}", "viewPath": parent_view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "parentViewPath": parent_view_path,
        "childViewPath": child_view_path,
        "route": route,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "parentViewSha256": sha256_text(canonical_json(parent_view)),
        "childViewSha256": sha256_text(canonical_json(child_view)),
        "readyText": f"{args.run_id} {variant.upper()} CHILD READY",
        "carrier": args.carrier,
        "instanceCount": instance_count(args),
        "embeddedCount": instance_count(args),
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
        "routes": [{"pagePath": package["route"], "viewPath": package["parentViewPath"], "title": f"Parameter Payload {package['variant']}"}],
        "dependencyViewPaths": [package["childViewPath"]],
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
        "expectedViewPath": package["parentViewPath"],
        "allowedViewPrefix": args.allowed_view_prefix,
        "allowedRoutePrefix": args.allowed_route_prefix,
        "dependencyViewPaths": [package["childViewPath"]],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [],
    }


def view_read_payload(request_id: str, project: str, view_path: str, args: argparse.Namespace) -> Dict[str, Any]:
    return common.view_read_payload(request_id, project, view_path, args)


def rollback_payload(request_id: str, project: str, backup_name: str, view_paths: List[str], dry_run: bool) -> Dict[str, Any]:
    return common.rollback_payload(request_id, project, backup_name, view_paths, dry_run)


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        f"{args.run_id}-param-payload-{package['variant']}",
        "--project",
        project,
        "--route",
        package["route"],
        "--view",
        package["parentViewPath"],
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
        "parameter payload A-14 fixture",
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


def readback_ok(parent_record: Dict[str, Any], child_record: Dict[str, Any], variant: str, package: Dict[str, Any]) -> bool:
    parent_text = canonical_json(cp.response(parent_record))
    child_text = canonical_json(cp.response(child_record))
    expected_mode = f'"mode":"{variant}"'
    has_expected_mode = expected_mode in parent_text
    has_ready = str(package["readyText"]) in parent_text
    has_child_binding = "{view.params.readyText}" in child_text
    if variant == "deep-params":
        return has_expected_mode and has_ready and has_child_binding and '"deepPayload"' in parent_text and '"groups"' in parent_text
    return has_expected_mode and has_ready and has_child_binding and '"deepPayload"' not in parent_text


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    profile = read_json(profile_dir / "static-profile.json")
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    payloads = profile.get("parameterPayloads", []) if isinstance(profile.get("parameterPayloads"), list) else []
    view_instantiation = profile.get("viewInstantiation", []) if isinstance(profile.get("viewInstantiation"), list) else []
    payload_bytes = [common.number(row.get("bytes")) for row in payloads if isinstance(row, dict)]
    payload_depths = [common.number(row.get("maxObjectDepth")) for row in payloads if isinstance(row, dict)]
    clean_bytes = [float(value) for value in payload_bytes if value is not None]
    clean_depths = [float(value) for value in payload_depths if value is not None]
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "embeddedViewCount": summary.get("embeddedViewCount"),
        "flexRepeaterCount": summary.get("flexRepeaterCount"),
        "viewInstantiation": view_instantiation,
        "viewJsonBytes": summary.get("viewJsonBytes"),
        "parameterPayloadCount": len(payloads),
        "parameterPayloadSources": sorted({str(row.get("source")) for row in payloads if isinstance(row, dict) and row.get("source")}),
        "parameterPayloadBytesTotal": sum(clean_bytes) if clean_bytes else 0,
        "parameterPayloadBytesMax": max(clean_bytes) if clean_bytes else 0,
        "parameterPayloadDepthMax": max(clean_depths) if clean_depths else 0,
        "findingCodes": [row.get("code") for row in profile.get("findings", []) if isinstance(row, dict)],
    }


def browser_metrics(profile_dir: Path) -> Dict[str, Any]:
    return common.browser_metrics(profile_dir)


def gateway_metrics(profile_dir: Path) -> Dict[str, Any]:
    return common.gateway_metrics(profile_dir)


def network_metrics(profile_dir: Path) -> Dict[str, Any]:
    network = read_json(profile_dir / "network-summary.json")
    return {
        "requestCount": network.get("requestCount"),
        "knownContentLengthBytes": network.get("knownContentLengthBytes"),
        "webSocketFramesSent": network.get("webSocketFramesSent"),
        "webSocketFramesReceived": network.get("webSocketFramesReceived"),
        "webSocketBytesSent": network.get("webSocketBytesSent"),
        "webSocketBytesReceived": network.get("webSocketBytesReceived"),
    }


def compare_profiles(out_dir: Path, scalar_dir: Path, deep_dir: Path) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparison-deep-minus-scalar"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(scalar_dir), "--target-dir", str(deep_dir), "--out-dir", str(comparison_dir)]
    result = common.run_command(cmd, "compare-deep-minus-scalar", out_dir, 180)
    return {"ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}


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
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Parameter Payload A/B Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Carrier: `{summary.get('carrier')}`",
        f"Instances: `{summary.get('instanceCount')}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | OK | Param sources | Param bytes total | Max depth | View bytes | DOM | WS recv bytes | Long task ms | LCP ms | Cleanup |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        static = row.get("static", {})
        browser = row.get("browser", {})
        network = row.get("network", {})
        lines.append(
            "| {variant} | `{ok}` | {sources} | {param_bytes} | {depth} | {view_bytes} | {dom} | {ws_recv} | {long_task} | {lcp} | `{cleanup}` |".format(
                variant=row.get("variant"),
                ok=str(row.get("ok", False)).lower(),
                sources=", ".join(static.get("parameterPayloadSources") or []),
                param_bytes=static.get("parameterPayloadBytesTotal"),
                depth=static.get("parameterPayloadDepthMax"),
                view_bytes=static.get("viewJsonBytes"),
                dom=browser.get("domNodeCount"),
                ws_recv=network.get("webSocketBytesReceived"),
                long_task=browser.get("longTaskTotalMs"),
                lcp=browser.get("largestContentfulPaintMs"),
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewsAbsent", False)).lower(),
            )
        )
    lines.extend(["", "## Deep Minus Scalar Deltas", ""])
    for key, value in summary.get("comparisonPrimary", {}).items():
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
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    env = common.collect_env(endpoint, token, project)
    variants_to_run = parse_variants(args.variants)
    base = compact(args.run_id)
    child_view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/ParamChild"
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_response = cp.response(health)
    health_ok = cp.ok(health)
    feature_set = set(health_response.get("features", []) if isinstance(health_response.get("features"), list) else [])
    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []

    for variant_name in variants_to_run:
        variant_dir = out_dir / variant_name
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        parent_view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/Param{''.join(part.title() for part in variant_name.split('-'))}"
        package = build_package(variant_dir, project, args, variant_name, parent_view_path, child_view_path, route)
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
                    variant_name,
                    feature_set,
                    args.baseline_max_browser_sessions,
                    args.baseline_wait_timeout_sec,
                    args.baseline_wait_interval_sec,
                )
                gates["cleanBaseline"] = baseline.get("ok") is True
                if args.fail_on_baseline_timeout and not gates["cleanBaseline"]:
                    raise RuntimeError("clean baseline wait failed")
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
            parent_read = client.call(f"{args.run_id}-{variant_name}-parent-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-parent-viewRead", project, parent_view_path, args))
            child_read = client.call(f"{args.run_id}-{variant_name}-child-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-child-viewRead", project, child_view_path, args))
            gates["viewRead"] = cp.ok(parent_read) and cp.ok(child_read) and readback_ok(parent_read, child_read, variant_name, package)
            page = client.call(f"{args.run_id}-{variant_name}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = variant_dir / "profile"
            command = profile_command(args, package, project, browser_url, profile_dir)
            profile_result = common.run_command(command, f"profile-{variant_name}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            variant = {
                "variant": variant_name,
                "ok": all(gates.values()),
                "gates": gates,
                "baselineWait": baseline,
                "route": route,
                "parentViewPath": parent_view_path,
                "childViewPath": child_view_path,
                "backupName": backup_name,
                "profileDir": str(profile_dir),
                "browser": browser_metrics(profile_dir),
                "gateway": gateway_metrics(profile_dir),
                "network": network_metrics(profile_dir),
                "static": static_summary(profile_dir),
                "profileCommand": profile_result,
            }
        except Exception as exc:
            variant = {
                "variant": variant_name,
                "ok": False,
                "gates": gates,
                "baselineWait": baseline,
                "route": route,
                "parentViewPath": parent_view_path,
                "childViewPath": child_view_path,
                "backupName": backup_name,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                rb_dry = client.call(
                    f"{args.run_id}-{variant_name}-rollback-dryRun",
                    rollback_payload(f"{args.run_id}-{variant_name}-rollback-dryRun", project, backup_name, [parent_view_path, child_view_path], True),
                    timeout=args.timeout_sec,
                )
                rb_apply = client.call(
                    f"{args.run_id}-{variant_name}-rollback-apply",
                    rollback_payload(f"{args.run_id}-{variant_name}-rollback-apply", project, backup_name, [parent_view_path, child_view_path], False),
                    timeout=args.timeout_sec,
                )
                time.sleep(2)
                routes_check = client.call(
                    f"{args.run_id}-{variant_name}-post-cleanup-routesList",
                    {
                        "action": "routesList",
                        "requestId": f"{args.run_id}-{variant_name}-post-cleanup-routesList",
                        "targetProject": project,
                        "routePrefix": route,
                        "maxResults": 25,
                    },
                )
                routes = cp.response(routes_check).get("routes", [])
                routes_list = routes if isinstance(routes, list) else []
                route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes_list)
                parent_after = client.call(f"{args.run_id}-{variant_name}-post-cleanup-parent-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-post-cleanup-parent-viewRead", project, parent_view_path, args))
                child_after = client.call(f"{args.run_id}-{variant_name}-post-cleanup-child-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-post-cleanup-child-viewRead", project, child_view_path, args))
                variant["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                variant["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                variant["cleanupViewsAbsent"] = not cp.ok(parent_after) and not cp.ok(child_after)
                variant["ok"] = bool(variant.get("ok") and variant["rollbackOk"] and variant["cleanupRouteAbsent"] and variant["cleanupViewsAbsent"])
            variants.append(variant)
            if args.pause_sec > 0 and variant_name != variants_to_run[-1]:
                time.sleep(args.pause_sec)

    comparison: Dict[str, Any] = {"ok": False, "reason": "scalar and deep profiles were not both available"}
    comparison_primary_data: Dict[str, Any] = {}
    scalar_profile = next((Path(row["profileDir"]) for row in variants if row.get("variant") == "scalar-params" and row.get("profileDir")), None)
    deep_profile = next((Path(row["profileDir"]) for row in variants if row.get("variant") == "deep-params" and row.get("profileDir")), None)
    if scalar_profile and deep_profile and scalar_profile.exists() and deep_profile.exists():
        comparison = compare_profiles(out_dir, scalar_profile, deep_profile)
        if comparison.get("ok"):
            comparison_primary_data = comparison_primary(Path(str(comparison["comparisonDir"])))

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants) and comparison.get("ok")),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": health_response.get("runnerVersion"),
        "stackVersion": health_response.get("stackVersion"),
        "carrier": args.carrier,
        "instanceCount": instance_count(args),
        "embeddedCount": instance_count(args),
        "deepGroups": args.deep_groups,
        "deepWidth": args.deep_width,
        "deepDepth": args.deep_depth,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "variants": variants,
        "comparison": comparison,
        "comparisonPrimary": comparison_primary_data,
        "packages": package_records,
        "interpretation": [
            "This is a controlled A-14 parameter payload fixture, not a customer route conclusion.",
            "The visible child view, carrier, and instance count stay constant; the tested variable is the params object shape and size.",
            "Use browser/network payload evidence and static parameterPayloads together; do not infer payload cost from view JSON size alone.",
            "Repeat clean-baseline pairs before making a causal remediation recommendation for a customer screen.",
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
    parser.add_argument("--variants", default="scalar-params,deep-params")
    parser.add_argument("--carrier", choices=CARRIERS, default="embedded-view", help="Component that carries repeated child-view params.")
    parser.add_argument("--embedded-count", type=int, default=12)
    parser.add_argument("--instance-count", type=int, default=None, help="Repeated child-view instance count. Defaults to --embedded-count for backward compatibility.")
    parser.add_argument("--canvas-columns", type=int, default=4)
    parser.add_argument("--deep-groups", type=int, default=18)
    parser.add_argument("--deep-width", type=int, default=10)
    parser.add_argument("--deep-depth", type=int, default=4)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=10.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=300)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
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
    if args.embedded_count < 1 or (args.instance_count is not None and args.instance_count < 1):
        raise SystemExit("--embedded-count and --instance-count must be >= 1")
    if args.canvas_columns < 1:
        raise SystemExit("--canvas-columns must be >= 1")
    if args.deep_groups < 1 or args.deep_width < 1 or args.deep_depth < 1:
        raise SystemExit("--deep-groups, --deep-width, and --deep-depth must be >= 1")
    summary = run(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
