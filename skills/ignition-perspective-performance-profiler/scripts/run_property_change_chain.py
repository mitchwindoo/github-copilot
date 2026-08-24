#!/usr/bin/env python3
"""Run guarded Perspective property-change storm fixtures for A-18."""

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
from typing import Any, Dict, List, Tuple

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_hidden_content_ab as hidden_common
import run_table_ab_remediation as table_common
import run_tab_runwhilehidden_ab as tab_common


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
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


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_rmtree(path: Path, *allowed_roots: Path) -> None:
    target = path.resolve()
    roots = [root.resolve() for root in allowed_roots if root]
    if not roots or not any(is_relative_to(target, root) for root in roots):
        raise RuntimeError(f"Refusing recursive delete outside intended output roots: {target}")
    if target.exists():
        shutil.rmtree(target)


def profile_run_id(run_id: str, variant: str) -> str:
    base = compact(run_id)[:22].strip("-_") or "run"
    digest = sha256_text(f"{run_id}:{variant}")[:8]
    return f"{base}-{variant[:18]}-{digest}"


def component(
    component_type: str,
    *,
    meta: Dict[str, Any] | None = None,
    props: Dict[str, Any] | None = None,
    custom: Dict[str, Any] | None = None,
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


def property_binding(path: str, transform_code: str = "") -> Dict[str, Any]:
    binding: Dict[str, Any] = {"type": "property", "config": {"path": path}}
    if transform_code:
        binding["transforms"] = [{"type": "script", "code": transform_code}]
    return {"binding": binding}


def text_transform(prefix: str) -> str:
    return f"\treturn '{prefix}' + str(value)\n"


def parse_targets(raw: str, max_changes: int) -> List[int]:
    targets: List[int] = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            value = int(text)
        except ValueError as exc:
            raise ValueError(f"--targets contains a non-integer value: {text!r}") from exc
        if value <= 0:
            raise ValueError("--targets values must be positive")
        if value > max_changes:
            raise ValueError(f"target {value} exceeds --max-changes {max_changes}")
        targets.append(value)
    if not targets:
        raise ValueError("--targets must contain at least one positive integer")
    return sorted(dict.fromkeys(targets))


def variant_label(target_changes: int) -> str:
    return f"storm-{target_changes:04d}"


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-property-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def action_script() -> str:
    return "\n".join(
        [
            "\ttry:",
            "\t\ttarget = int(self.view.custom.targetChanges)",
            "\texcept:",
            "\t\ttarget = 1",
            "\ttry:",
            "\t\tmax_changes = int(self.view.custom.maxChanges)",
            "\texcept:",
            "\t\tmax_changes = 1",
            "\tif target < 1:",
            "\t\ttarget = 1",
            "\tif max_changes < 1:",
            "\t\tmax_changes = 1",
            "\tif target > max_changes:",
            "\t\ttarget = max_changes",
            "\tself.custom.targetChanges = target",
            "\tself.custom.maxChanges = max_changes",
            "\tself.custom.running = True",
            "\tself.custom.eventStepCount = 0",
            "\tself.custom.chainIndex = 0",
            "\tself.view.custom.completedChanges = 0",
            "\tself.view.custom.stormCounter = 0",
            "\tself.view.custom.stormMirror = 'starting'",
            "\tself.view.custom.lastPropertyName = 'bounded-button-loop'",
            "\tself.view.custom.lastError = ''",
            "\tself.view.custom.doneText = 'A-18 RUNNING 0'",
            "\tfor index in range(target):",
            "\t\tcurrent = index + 1",
            "\t\tself.custom.eventStepCount = current",
            "\t\tself.custom.chainIndex = current",
            "\t\tself.view.custom.stormCounter = current",
            "\t\tself.view.custom.stormMirror = 'event-' + str(current)",
            "\t\tself.view.custom.completedChanges = current",
            "\t\tif current == target or current % 25 == 0:",
            "\t\t\tself.view.custom.doneText = 'A-18 RUNNING ' + str(current)",
            "\tself.custom.running = False",
            "\tself.view.custom.doneText = 'A-18 DONE ' + str(target)",
        ]
    ) + "\n"


def observer_label(index: int) -> Dict[str, Any]:
    return component(
        "ia.display.label",
        meta={"name": f"Observer{index:03d}"},
        position={"basis": "28px", "grow": 1, "shrink": 1},
        props={
            "text": f"observer {index:03d}: 0",
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
        },
        prop_config={"props.text": property_binding("view.custom.stormCounter", text_transform(f"observer {index:03d}: "))},
    )


def make_view_json(args: argparse.Namespace, target_changes: int, variant: str) -> Dict[str, Any]:
    ready = f"{args.run_id} {variant.upper()} READY"
    observers = [observer_label(index) for index in range(1, args.observer_count + 1)]
    return {
        "custom": {
            "runId": args.run_id,
            "variant": variant,
            "targetChanges": target_changes,
            "maxChanges": args.max_changes,
            "observerCount": args.observer_count,
            "stormCounter": 0,
            "stormMirror": "pending",
            "completedChanges": 0,
            "lastPropertyName": "",
            "lastError": "",
            "doneText": "A-18 PENDING",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "property-storm-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {"backgroundColor": "#f8fafc", "overflow": "auto", "padding": "12px"},
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
                    position={"basis": "44px", "grow": 0, "shrink": 0},
                    props={
                        "text": (
                            f"A-18 bounded property-change storm fixture: target {target_changes} writes, "
                            f"hard cap {args.max_changes}, {args.observer_count} bound observers"
                        ),
                        "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
                    },
                ),
                component(
                    "ia.input.button",
                    meta={"name": "RunChainButton"},
                    custom={
                        "chainIndex": 0,
                        "targetChanges": target_changes,
                        "maxChanges": args.max_changes,
                        "running": False,
                        "eventStepCount": 0,
                    },
                    position={"basis": "46px", "grow": 0, "shrink": 0},
                    props={
                        "primary": True,
                        "style": {"alignSelf": "flex-start", "fontSize": 14, "fontWeight": "700", "maxWidth": "240px"},
                        "text": "Run bounded storm",
                    },
                    events={
                        "component": {
                            "onActionPerformed": {"scope": "G", "type": "script", "config": {"script": action_script()}}
                        }
                    },
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Done Marker"},
                    position={"basis": "36px", "grow": 0, "shrink": 0},
                    props={
                        "text": "A-18 PENDING",
                        "style": {
                            "backgroundColor": "#ecfdf5",
                            "borderColor": "#10b981",
                            "borderRadius": 4,
                            "borderStyle": "solid",
                            "borderWidth": "1px",
                            "color": "#064e3b",
                            "fontSize": 15,
                            "fontWeight": "700",
                            "padding": "7px 10px",
                            "whiteSpace": "pre-wrap",
                        },
                    },
                    prop_config={"props.text": property_binding("view.custom.doneText")},
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Counter Marker"},
                    position={"basis": "32px", "grow": 0, "shrink": 0},
                    props={"text": "counter: 0", "style": {"color": "#111827", "fontSize": 13, "padding": "6px 2px"}},
                    prop_config={"props.text": property_binding("view.custom.completedChanges", text_transform("counter: "))},
                ),
                component(
                    "ia.container.flex",
                    meta={"name": "Observer Grid"},
                    position={"basis": "auto", "grow": 1, "shrink": 1},
                    props={
                        "direction": "row",
                        "alignItems": "stretch",
                        "justify": "flex-start",
                        "wrap": "wrap",
                        "style": {"gap": "6px", "overflow": "auto"},
                    },
                    children=observers,
                ),
            ],
        ),
    }


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", table_common.resource_json(actor, ["view.json"]))


def build_package(
    out_dir: Path,
    project: str,
    args: argparse.Namespace,
    target_changes: int,
    view_path: str,
    route: str,
) -> Dict[str, Any]:
    variant = variant_label(target_changes)
    zip_dir = out_dir / "package"
    if zip_dir.exists():
        safe_rmtree(zip_dir, out_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-property-storm"
    view_json = make_view_json(args, target_changes, variant)
    zip_path = zip_dir / "fixture.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-property-storm-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            project_root / "project.json",
            {
                "title": project,
                "description": "Performance profiler property-change storm fixture",
                "enabled": True,
                "inheritable": False,
            },
        )
        write_view(project_root, view_path, view_json, actor)
        write_json(
            page_dir / "config.json",
            {"pages": {route: {"title": f"Property Storm {variant}", "viewPath": view_path}}, "sharedDocks": {}},
        )
        write_json(page_dir / "resource.json", table_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    package_base64 = common.zip_file_base64(zip_path)
    return {
        "variant": variant,
        "targetChanges": target_changes,
        "maxChanges": args.max_changes,
        "observerCount": args.observer_count,
        "route": route,
        "viewPath": view_path,
        "zipPath": str(zip_path),
        "zipBytes": zip_path.stat().st_size,
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": package_base64,
        "packageBase64Bytes": len(package_base64),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": f"{args.run_id} {variant.upper()} READY",
        "doneText": f"A-18 DONE {target_changes}",
        "profileRunId": profile_run_id(args.run_id, variant),
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Property Storm {package['variant']}"}],
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
        "bounded property-change storm A-18 fixture",
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
        "--browser-click-selector",
        "button",
        "--browser-click-text",
        "Run bounded storm",
        "--browser-click-label",
        "bounded-property-storm",
        "--browser-click-after-ready-delay-ms",
        str(args.browser_click_after_ready_delay_ms),
        "--browser-click-result-text",
        package["doneText"],
        "--browser-click-timeout-sec",
        str(args.browser_click_timeout_sec),
        "--browser-post-interaction-wait-ms",
        str(args.browser_post_interaction_wait_ms),
    ]
    if args.browser_node_modules:
        command.extend(["--browser-node-modules", args.browser_node_modules])
    return command


def profile_ok(profile_dir: Path) -> bool:
    manifest = read_json(profile_dir / "manifest.json")
    browser = read_json(profile_dir / "browser-summary.json")
    interaction = browser.get("interaction", {}) if isinstance(browser.get("interaction"), dict) else {}
    return bool(
        manifest.get("changedResources") == []
        and not manifest.get("missingEvidence")
        and browser.get("ok") is True
        and browser.get("ready") is True
        and browser.get("readyTextMatched") is True
        and interaction.get("configured") is True
        and interaction.get("ok") is True
    )


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    response_text = canonical_json(cp.response(record))
    return (
        cp.ok(record)
        and f'"targetChanges":{package["targetChanges"]}' in response_text
        and f'"maxChanges":{package["maxChanges"]}' in response_text
        and f'"observerCount":{package["observerCount"]}' in response_text
        and str(package["readyText"]) in response_text
        and "Run bounded storm" in response_text
        and "bounded-button-loop" in response_text
        and "A-18 DONE" in response_text
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
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "eventBlockCount": summary.get("eventBlockCount"),
        "scriptCount": summary.get("scriptCount"),
        "scriptChars": summary.get("scriptChars"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
    }


def family_rollup(metric_families: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for family in ("property-changes", "scripts", "queue-tasks", "messages-sent"):
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


def browser_interaction(profile_dir: Path) -> Dict[str, Any]:
    browser = read_json(profile_dir / "browser-summary.json")
    interaction = browser.get("interaction", {}) if isinstance(browser.get("interaction"), dict) else {}
    return {
        "configured": interaction.get("configured"),
        "ok": interaction.get("ok"),
        "clickOk": interaction.get("clickOk"),
        "resultOk": interaction.get("resultOk"),
        "label": interaction.get("label"),
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


def gate_failure_message(gate: str, record: Dict[str, Any]) -> str:
    detail = gate_detail(record)
    return "%s failed: httpStatus=%s responseKind=%s error=%s" % (
        gate,
        detail.get("httpStatus"),
        detail.get("responseKind"),
        detail.get("error"),
    )


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


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Property-Change Storm Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | OK | Target | Static scripts | Prop delta max | Script delta max | Queue rate max | DOM | Long task ms | WS recv | Click proof | Cleanup |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary.get("variants", []):
        static = row.get("static", {})
        browser = row.get("browser", {})
        network = row.get("network", {})
        rollup = row.get("metricRollup", {})
        proof = row.get("browserInteraction", {})
        lines.append(
            "| {variant} | `{ok}` | {target} | {scripts} | {prop_delta} | {script_delta} | {queue_rate} | {dom} | {long_task} | {ws_recv} | `{proof}` | `{cleanup}` |".format(
                variant=row.get("variant"),
                ok=str(row.get("ok", False)).lower(),
                target=row.get("targetChanges"),
                scripts=static.get("scriptCount"),
                prop_delta=rollup.get("propertychangesDeltaMax"),
                script_delta=rollup.get("scriptsDeltaMax"),
                queue_rate=rollup.get("queuetasksRateMax"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                ws_recv=network.get("webSocketBytesReceived"),
                proof=proof.get("ok"),
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
    targets = parse_targets(args.targets, args.max_changes)
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
    variants: List[Dict[str, Any]] = []
    packages: List[Dict[str, Any]] = []
    comparisons: List[Dict[str, Any]] = []

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_response = cp.response(health)
    health_ok = cp.ok(health)
    feature_set: set[str] = set()
    for capability_key in ("features", "supportedActions"):
        values = health_response.get(capability_key, [])
        if isinstance(values, dict):
            feature_set.update(str(item) for item, enabled in values.items() if enabled)
        elif isinstance(values, list):
            feature_set.update(str(item) for item in values)

    for target_changes in targets:
        variant = variant_label(target_changes)
        variant_dir = out_dir / variant
        route = build_route(args.route_prefix, run_slug, variant)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/PropertyStorm{target_changes:04d}"
        package = build_package(variant_dir, project, args, target_changes, view_path, route)
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
                    feature_set,
                    args.baseline_max_browser_sessions,
                    args.baseline_wait_timeout_sec,
                    args.baseline_wait_interval_sec,
                )
                gates["cleanBaseline"] = baseline.get("ok") is True
                if args.fail_on_baseline_timeout and not gates["cleanBaseline"]:
                    raise RuntimeError("clean baseline wait failed")
            dry = client.call(
                f"{args.run_id}-{variant}-dryRun",
                package_payload("dryRun", f"{args.run_id}-{variant}-dryRun", project, package, args),
                timeout=args.timeout_sec,
            )
            gates["dryRun"] = cp.ok(dry)
            gate_details["dryRun"] = gate_detail(dry)
            if not gates["dryRun"]:
                raise RuntimeError(gate_failure_message("dryRun", dry))
            apply = client.call(
                f"{args.run_id}-{variant}-apply",
                package_payload("apply", f"{args.run_id}-{variant}-apply", project, package, args),
                timeout=args.timeout_sec,
            )
            backup_name = common.backup_name_from_response(cp.response(apply))
            gates["apply"] = cp.ok(apply) and bool(backup_name)
            gate_details["apply"] = gate_detail(apply)
            if not gates["apply"]:
                raise RuntimeError(gate_failure_message("apply", apply))
            time.sleep(2)
            view_read = client.call(f"{args.run_id}-{variant}-viewRead", view_read_payload(f"{args.run_id}-{variant}-viewRead", project, view_path, args))
            gates["viewRead"] = readback_ok(view_read, package)
            gate_details["viewRead"] = gate_detail(view_read)
            page = client.call(f"{args.run_id}-{variant}-pageValidate", page_validate_payload(f"{args.run_id}-{variant}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            gate_details["pageValidate"] = gate_detail(page)
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = variant_dir / "profile"
            command = profile_command(args, package, project, browser_url, profile_dir)
            profile_result = common.run_command(command, f"profile-{variant}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            metric_families = hidden_common.metric_family_samples(profile_dir)
            row = {
                "variant": variant,
                "targetChanges": target_changes,
                "maxChanges": package["maxChanges"],
                "observerCount": package["observerCount"],
                "ok": all(gates.values()),
                "gates": gates,
                "gateDetails": gate_details,
                "baselineWait": baseline,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "profileDir": str(profile_dir),
                "browser": browser_metrics(profile_dir),
                "browserInteraction": browser_interaction(profile_dir),
                "gateway": gateway_metrics(profile_dir),
                "network": network_metrics(profile_dir),
                "static": static_summary(profile_dir),
                "metricFamilies": metric_families,
                "metricRollup": family_rollup(metric_families),
                "profileCommand": profile_result,
            }
            baseline_variant = variant_label(targets[0])
            baseline_dir = out_dir / baseline_variant / "profile"
            if target_changes != targets[0] and baseline_dir.exists() and gates["profile"]:
                comparison = compare_to_baseline(out_dir, baseline_dir, profile_dir, variant)
                if comparison.get("ok"):
                    comparison["primary"] = comparison_primary(Path(str(comparison["comparisonDir"])))
                comparisons.append(comparison)
        except Exception as exc:
            row = {
                "variant": variant,
                "targetChanges": target_changes,
                "maxChanges": package.get("maxChanges"),
                "observerCount": package.get("observerCount"),
                "ok": False,
                "gates": gates,
                "gateDetails": gate_details,
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
            if args.pause_sec > 0 and target_changes != targets[-1]:
                time.sleep(args.pause_sec)

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants) and all(row.get("ok") for row in comparisons)),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": health_response.get("runnerVersion"),
        "stackVersion": health_response.get("stackVersion"),
        "targets": targets,
        "maxChanges": args.max_changes,
        "observerCount": args.observer_count,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "healthOk": health_ok,
        "variants": variants,
        "comparisons": comparisons,
        "packages": packages,
        "interpretation": [
            "This is a controlled A-18 property-change storm fixture, not a customer route conclusion.",
            "The button starts a bounded Perspective script that writes custom properties up to maxChanges; it avoids unproven component propertyChange event JSON while still exercising property propagation and session queues.",
            "Use browser click proof, Perspective property-change counters, script counters, queue-task rates, browser long tasks, and Gateway/session metrics together.",
            "A completed browser marker proves the bounded storm terminated; missing marker, rising queue metrics, or logs after the timeout should be treated as a runaway-risk signal.",
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
    parser.add_argument("--targets", default="10,250", help="Comma-separated bounded property-write counts.")
    parser.add_argument("--max-changes", type=int, default=750)
    parser.add_argument("--observer-count", type=int, default=24)
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
    parser.add_argument("--browser-click-after-ready-delay-ms", type=int, default=1000)
    parser.add_argument("--browser-click-timeout-sec", type=float, default=25.0)
    parser.add_argument("--browser-post-interaction-wait-ms", type=int, default=3000)
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
    if args.max_changes < 1:
        raise SystemExit("--max-changes must be >= 1")
    if args.observer_count < 0:
        raise SystemExit("--observer-count must be >= 0")
    if args.profile_duration_sec <= 0:
        raise SystemExit("--profile-duration-sec must be > 0")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.browser_click_timeout_sec <= 0:
        raise SystemExit("--browser-click-timeout-sec must be > 0")
    summary = run(args)
    print(json.dumps({"ok": summary.get("ok"), "summaryPath": str(Path(args.out_dir) / "summary.json")}, indent=2, sort_keys=True))
    raise SystemExit(0 if summary.get("ok") else 1)


if __name__ == "__main__":
    main()
