#!/usr/bin/env python3
"""Run a guarded Perspective session queue-backlog fixture for I-02."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_property_change_chain as storm_common
import run_table_ab_remediation as table_common
import run_tab_runwhilehidden_ab as tab_common


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
COUNTER_TEXT_RE = re.compile(r"expected=(\d+).*started=(\d+).*accepted=(\d+).*completed=(\d+).*last=(\d+)")


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


def parse_task_counts(raw: str, max_tasks: int) -> List[int]:
    counts: List[int] = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            value = int(text)
        except ValueError as exc:
            raise ValueError(f"--task-counts contains a non-integer value: {text!r}") from exc
        if value <= 0:
            raise ValueError("--task-counts values must be positive")
        if value > max_tasks:
            raise ValueError(f"task count {value} exceeds --max-tasks {max_tasks}")
        counts.append(value)
    if not counts:
        raise ValueError("--task-counts must contain at least one positive integer")
    return sorted(dict.fromkeys(counts))


def variant_label(task_count: int) -> str:
    return f"queue-{task_count:04d}"


def profile_run_id(run_id: str, variant: str) -> str:
    base = compact(run_id)[:22].strip("-_") or "run"
    digest = sha256_text(f"{run_id}:{variant}")[:8]
    return f"{base}-{variant[:18]}-{digest}"


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-queue-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def component(
    component_type: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    props: Optional[Dict[str, Any]] = None,
    custom: Optional[Dict[str, Any]] = None,
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


def button_script() -> str:
    return "\n".join(
        [
            "\timport time",
            "\ttry:",
            "\t\texpected = int(self.view.custom.expectedTasks)",
            "\texcept:",
            "\t\texpected = 1",
            "\ttry:",
            "\t\twork_millis = int(self.view.custom.workMillis)",
            "\texcept:",
            "\t\twork_millis = 0",
            "\ttry:",
            "\t\tmax_work_millis = int(self.view.custom.maxWorkMillis)",
            "\texcept:",
            "\t\tmax_work_millis = 0",
            "\tif expected < 1:",
            "\t\texpected = 1",
            "\tif work_millis < 0:",
            "\t\twork_millis = 0",
            "\tif max_work_millis < 0:",
            "\t\tmax_work_millis = 0",
            "\tif work_millis > max_work_millis:",
            "\t\twork_millis = max_work_millis",
            "\ttry:",
            "\t\tstarted = int(self.view.custom.startedActions)",
            "\texcept:",
            "\t\tstarted = 0",
            "\ttry:",
            "\t\taccepted = int(self.view.custom.acceptedActions)",
            "\texcept:",
            "\t\taccepted = 0",
            "\ttry:",
            "\t\tcompleted = int(self.view.custom.completedActions)",
            "\texcept:",
            "\t\tcompleted = 0",
            "\tstarted = started + 1",
            "\taccepted = accepted + 1",
            "\tself.view.custom.startedActions = started",
            "\tself.view.custom.acceptedActions = accepted",
            "\ttry:",
            "\t\tcount = int(self.view.custom.handledTasks)",
            "\texcept:",
            "\t\tcount = 0",
            "\tif count < 0:",
            "\t\tcount = 0",
            "\tif count == 0:",
            "\t\tself.view.custom.doneText = 'I-02 RUNNING 0'",
            "\tif work_millis > 0:",
            "\t\ttime.sleep(float(work_millis) / 1000.0)",
            "\tcount = count + 1",
            "\tcompleted = completed + 1",
            "\tself.view.custom.handledTasks = count",
            "\tself.view.custom.completedActions = completed",
            "\tself.view.custom.lastHandledIndex = count",
            "\tif expected > 0 and count >= expected:",
            "\t\tself.view.custom.doneText = 'I-02 DONE ' + str(expected)",
            "\telif count % 50 == 0:",
            "\t\tself.view.custom.doneText = 'I-02 HANDLED ' + str(count)",
        ]
    ) + "\n"


def status_label(name: str, text: str, bind_path: str, basis: str = "34px") -> Dict[str, Any]:
    return component(
        "ia.display.label",
        meta={"name": name},
        position={"basis": basis, "grow": 0, "shrink": 0},
        props={
            "text": text,
            "style": {
                "backgroundColor": "#ffffff",
                "borderColor": "#d1d5db",
                "borderRadius": 4,
                "borderStyle": "solid",
                "borderWidth": "1px",
                "color": "#111827",
                "fontSize": 13,
                "overflow": "hidden",
                "padding": "6px 8px",
                "textOverflow": "ellipsis",
                "whiteSpace": "nowrap",
            },
        },
        prop_config={"props.text": property_binding(bind_path, text_transform(f"{text.split(':')[0]}: "))},
    )


def make_view_json(args: argparse.Namespace, task_count: int, variant: str) -> Dict[str, Any]:
    ready = f"{args.run_id} {variant.upper()} READY"
    done = f"I-02 DONE {task_count}"
    root = component(
        "ia.container.flex",
        meta={"name": "queue-backlog-root"},
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
                meta={"name": "Ready Marker", "domId": "perf-ready"},
                position={"basis": "38px", "grow": 0, "shrink": 0},
                props={
                    "text": ready,
                    "style": {
                        "backgroundColor": "#eef2ff",
                        "borderColor": "#c7d2fe",
                        "borderRadius": 4,
                        "borderStyle": "solid",
                        "borderWidth": "1px",
                        "color": "#1f2937",
                        "fontSize": 14,
                        "fontWeight": "700",
                        "padding": "8px 10px",
                    },
                },
            ),
            component(
                "ia.input.button",
                meta={"name": "Enqueue Bounded Tasks"},
                position={"basis": "46px", "grow": 0, "shrink": 0},
                props={
                    "text": "Enqueue bounded tasks",
                    "style": {
                        "backgroundColor": "#2563eb",
                        "borderRadius": 4,
                        "color": "#ffffff",
                        "fontSize": 14,
                        "fontWeight": "700",
                    },
                },
                events={"component": {"onActionPerformed": {"type": "script", "scope": "G", "config": {"script": button_script()}}}},
            ),
            component(
                "ia.display.label",
                meta={"name": "Done Marker"},
                position={"basis": "42px", "grow": 0, "shrink": 0},
                props={
                    "text": "I-02 PENDING",
                    "style": {
                        "backgroundColor": "#ecfdf5",
                        "borderColor": "#86efac",
                        "borderRadius": 4,
                        "borderStyle": "solid",
                        "borderWidth": "1px",
                        "color": "#064e3b",
                        "fontSize": 15,
                        "fontWeight": "700",
                        "padding": "7px 10px",
                    },
                },
                prop_config={"props.text": property_binding("view.custom.doneText")},
            ),
            status_label("Expected Tasks", "Expected: 0", "view.custom.expectedTasks"),
            status_label("Handled Tasks", "Handled: 0", "view.custom.handledTasks"),
            status_label("Started Actions", "Started: 0", "view.custom.startedActions"),
            status_label("Accepted Actions", "Accepted: 0", "view.custom.acceptedActions"),
            status_label("Completed Actions", "Completed: 0", "view.custom.completedActions"),
            status_label("Last Index", "Last Index: 0", "view.custom.lastHandledIndex"),
            component(
                "ia.display.label",
                meta={"name": "Fixture Counter Snapshot", "domId": "perf-counters"},
                position={"basis": "34px", "grow": 0, "shrink": 0},
                props={
                    "text": f"Fixture Counters: expected={task_count} started=0 accepted=0 completed=0 last=0",
                    "style": {
                        "backgroundColor": "#ffffff",
                        "borderColor": "#d1d5db",
                        "borderRadius": 4,
                        "borderStyle": "solid",
                        "borderWidth": "1px",
                        "color": "#111827",
                        "fontSize": 13,
                        "overflow": "hidden",
                        "padding": "6px 8px",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                    },
                },
                prop_config={
                    "props.text": {
                        "binding": {
                            "type": "expr",
                            "config": {
                                "expression": "'Fixture Counters: expected=' + toStr({view.custom.expectedTasks}) + ' started=' + toStr({view.custom.startedActions}) + ' accepted=' + toStr({view.custom.acceptedActions}) + ' completed=' + toStr({view.custom.completedActions}) + ' last=' + toStr({view.custom.lastHandledIndex})"
                            },
                        }
                    }
                },
            ),
            component(
                "ia.display.label",
                meta={"name": "Fixture Note"},
                position={"basis": "auto", "grow": 1, "shrink": 1},
                props={
                    "text": f"Bounded I-02 queue backlog fixture: {task_count} browser-originated button actions x {args.work_millis} ms each.",
                    "style": {
                        "backgroundColor": "#ffffff",
                        "borderColor": "#e5e7eb",
                        "borderRadius": 4,
                        "borderStyle": "solid",
                        "borderWidth": "1px",
                        "color": "#374151",
                        "fontSize": 13,
                        "padding": "8px 10px",
                        "whiteSpace": "pre-wrap",
                    },
                },
            ),
        ],
    )
    return {
        "custom": {
            "runId": args.run_id,
            "variant": variant,
            "taskCount": task_count,
            "maxTasks": args.max_tasks,
            "workMillis": args.work_millis,
            "maxWorkMillis": args.max_work_millis,
            "expectedTasks": task_count,
            "handledTasks": 0,
            "startedActions": 0,
            "acceptedActions": 0,
            "completedActions": 0,
            "lastHandledIndex": 0,
            "lastError": "",
            "doneText": "I-02 PENDING",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": root,
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
    task_count: int,
    is_backlog_variant: bool,
    view_path: str,
    route: str,
) -> Dict[str, Any]:
    variant = variant_label(task_count)
    zip_dir = out_dir / "package"
    if zip_dir.exists():
        safe_rmtree(zip_dir, out_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-queue-backlog"
    view_json = make_view_json(args, task_count, variant)
    zip_path = zip_dir / "fixture.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-queue-backlog-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            project_root / "project.json",
            {
                "title": project,
                "description": "Performance profiler queue-backlog fixture",
                "enabled": True,
                "inheritable": False,
            },
        )
        write_view(project_root, view_path, view_json, actor)
        write_json(
            page_dir / "config.json",
            {"pages": {route: {"title": f"Queue Backlog {variant}", "viewPath": view_path}}, "sharedDocks": {}},
        )
        write_json(page_dir / "resource.json", table_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    package_base64 = common.zip_file_base64(zip_path)
    return {
        "variant": variant,
        "taskCount": task_count,
        "isBacklogVariant": is_backlog_variant,
        "maxTasks": args.max_tasks,
        "workMillis": args.work_millis,
        "maxWorkMillis": args.max_work_millis,
        "route": route,
        "viewPath": view_path,
        "zipPath": str(zip_path),
        "zipBytes": zip_path.stat().st_size,
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": package_base64,
        "packageBase64Bytes": len(package_base64),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": f"{args.run_id} {variant.upper()} READY",
        "doneText": f"I-02 DONE {task_count}",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Queue Backlog {package['variant']}"}],
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
    return storm_common.rollback_payload(request_id, project, backup_name, view_path, dry_run)


def collect_env(endpoint: str, token: str, project: str) -> Dict[str, str]:
    env = dict(os.environ)
    env["IGNITION_LLM_RUNNER_ENDPOINT"] = endpoint
    env["IGNITION_LLM_RUNNER_TOKEN"] = token
    env["IGNITION_TARGET_PROJECT"] = project
    return env


def browser_network_throttle_configured(args: argparse.Namespace) -> bool:
    return bool(
        args.browser_network_throttle_after_ready
        or args.browser_network_latency_ms
        or args.browser_network_download_kbps
        or args.browser_network_upload_kbps
    )


def browser_network_throttle_applies(args: argparse.Namespace, package: Dict[str, Any]) -> bool:
    if not browser_network_throttle_configured(args):
        return False
    scope = getattr(args, "browser_network_throttle_scope", "all") or "all"
    if scope == "all":
        return True
    if scope == "backlog":
        return bool(package.get("isBacklogVariant"))
    return False


def browser_network_throttle_evidence(args: argparse.Namespace, package: Dict[str, Any]) -> Dict[str, Any]:
    value_requested = bool(
        args.browser_network_latency_ms
        or args.browser_network_download_kbps
        or args.browser_network_upload_kbps
    )
    return {
        "configured": browser_network_throttle_configured(args),
        "valueRequested": value_requested,
        "applied": browser_network_throttle_applies(args, package),
        "scope": getattr(args, "browser_network_throttle_scope", "all") or "all",
        "afterReady": bool(args.browser_network_throttle_after_ready),
        "latencyMs": args.browser_network_latency_ms,
        "downloadKbps": args.browser_network_download_kbps,
        "uploadKbps": args.browser_network_upload_kbps,
    }


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
        "bounded queue backlog I-02 fixture",
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
        "Enqueue bounded tasks",
        "--browser-click-label",
        "bounded-queue-backlog",
        "--browser-click-after-ready-delay-ms",
        str(args.browser_click_after_ready_delay_ms),
        "--browser-click-repeat-count",
        str(package["taskCount"]),
        "--browser-click-repeat-interval-ms",
        str(args.browser_click_repeat_interval_ms),
        "--browser-click-repeat-mode",
        args.browser_click_repeat_mode,
        "--browser-click-result-text",
        package["doneText"],
        "--browser-click-timeout-sec",
        str(args.browser_click_timeout_sec),
        "--browser-post-interaction-wait-ms",
        str(args.browser_post_interaction_wait_ms),
        "--browser-watch-text-selector",
        '[data-component-path="C.0:9"]',
        "--browser-watch-text-regex",
        r"(expected=\d+.*started=\d+.*accepted=\d+.*completed=\d+.*last=\d+)",
        "--browser-watch-text-label",
        "queue-fixture-counters",
        "--browser-watch-text-timeout-sec",
        str(args.browser_click_timeout_sec),
    ]
    apply_network_throttle = browser_network_throttle_applies(args, package)
    if apply_network_throttle and args.browser_network_throttle_after_ready:
        command.append("--browser-network-throttle-after-ready")
    if apply_network_throttle and args.browser_network_latency_ms:
        command.extend(["--browser-network-latency-ms", str(args.browser_network_latency_ms)])
    if apply_network_throttle and args.browser_network_download_kbps:
        command.extend(["--browser-network-download-kbps", str(args.browser_network_download_kbps)])
    if apply_network_throttle and args.browser_network_upload_kbps:
        command.extend(["--browser-network-upload-kbps", str(args.browser_network_upload_kbps)])
    if args.browser_node:
        command.extend(["--browser-node", args.browser_node])
    if args.browser_node_modules:
        command.extend(["--browser-node-modules", args.browser_node_modules])
    return command


def profile_ok(profile_dir: Path) -> bool:
    manifest = read_json(profile_dir / "manifest.json")
    browser = read_json(profile_dir / "browser-summary.json")
    interaction = browser.get("interaction", {}) if isinstance(browser.get("interaction"), dict) else {}
    proof = browser_interaction(profile_dir)
    watch_text = proof.get("watchText", {}) if isinstance(proof.get("watchText"), dict) else {}
    return bool(
        manifest.get("changedResources") == []
        and not manifest.get("missingEvidence")
        and browser.get("ok") is True
        and browser.get("ready") is True
        and browser.get("readyTextMatched") is True
        and interaction.get("configured") is True
        and interaction.get("ok") is True
        and interaction.get("resultAlreadyMatchedBeforeClick") is False
        and watch_text.get("changed") is True
        and proof.get("fixtureCountersOk") is True
    )


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    response_text = canonical_json(cp.response(record))
    return (
        cp.ok(record)
        and f'"taskCount":{package["taskCount"]}' in response_text
        and f'"maxTasks":{package["maxTasks"]}' in response_text
        and f'"workMillis":{package["workMillis"]}' in response_text
        and '"startedActions":0' in response_text
        and '"acceptedActions":0' in response_text
        and '"completedActions":0' in response_text
        and str(package["readyText"]) in response_text
        and "Enqueue bounded tasks" in response_text
        and "Fixture Counters" in response_text
        and "I-02 DONE" in response_text
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


def first_number(*values: Any) -> Optional[float]:
    for value in values:
        parsed = common.number(value)
        if parsed is not None:
            return float(parsed)
    return None


def queue_length_timeseries(profile_dir: Path) -> Dict[str, Any]:
    samples_path = profile_dir / "gateway-samples.ndjson"
    by_token: Dict[str, Dict[str, Any]] = {}
    by_sample: List[Dict[str, Any]] = []
    if not samples_path.exists():
        return {"tokens": [], "samples": [], "max": None, "first": None, "last": None, "sustainedSamples": 0}
    for line in samples_path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        sample_index = row.get("sampleIndex")
        snapshot = row.get("metricsSnapshot", {}) if isinstance(row.get("metricsSnapshot"), dict) else {}
        metrics = snapshot.get("metrics", []) if isinstance(snapshot.get("metrics"), list) else []
        sample_values: List[float] = []
        for metric in metrics:
            if not isinstance(metric, dict) or metric.get("ok") is not True:
                continue
            name = str(metric.get("name") or "").lower()
            if "queue-length" not in name:
                continue
            value = first_number(metric.get("value"), metric.get("count"))
            if value is None:
                continue
            token = str(metric.get("token") or metric.get("name") or "queue-length")
            bucket = by_token.setdefault(
                token,
                {"token": token, "name": metric.get("name"), "first": None, "last": None, "max": None, "samples": []},
            )
            if bucket["first"] is None:
                bucket["first"] = value
            bucket["last"] = value
            bucket["max"] = value if bucket["max"] is None else max(float(bucket["max"]), value)
            bucket["samples"].append({"sampleIndex": sample_index, "value": value})
            sample_values.append(value)
        if sample_values:
            by_sample.append({"sampleIndex": sample_index, "max": max(sample_values), "sum": sum(sample_values)})
    tokens = list(by_token.values())
    tokens.sort(key=lambda item: float(item.get("max") or 0), reverse=True)
    first = tokens[0].get("first") if tokens else None
    last = tokens[0].get("last") if tokens else None
    max_value = tokens[0].get("max") if tokens else None
    sustained = 0
    if tokens:
        peak_token = tokens[0]
        for sample in peak_token.get("samples", []):
            if first_number(sample.get("value")) and float(sample["value"]) > 0:
                sustained += 1
    return {"tokens": tokens, "samples": by_sample, "max": max_value, "first": first, "last": last, "sustainedSamples": sustained}


def metric_name_matches_family(name: str, family: str) -> bool:
    return name == family or name.endswith("." + family)


def metric_family_samples(profile_dir: Path) -> Dict[str, Any]:
    samples_path = profile_dir / "gateway-samples.ndjson"
    families = ("property-changes", "scripts", "queue-tasks", "messages-sent")
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
        sample_index = row.get("sampleIndex")
        snapshot = row.get("metricsSnapshot", {}) if isinstance(row.get("metricsSnapshot"), dict) else {}
        metrics = snapshot.get("metrics", []) if isinstance(snapshot.get("metrics"), list) else []
        for metric in metrics:
            if not isinstance(metric, dict) or metric.get("ok") is not True:
                continue
            name = str(metric.get("name") or "")
            name_l = name.lower()
            family = next((item for item in families if metric_name_matches_family(name_l, item)), None)
            if family is None:
                continue
            value = first_number(metric.get("count"), metric.get("value"))
            if value is None:
                continue
            token = str(metric.get("token") or metric.get("name") or name_l)
            bucket = result[family].setdefault(
                token,
                {
                    "token": token,
                    "name": name,
                    "first": None,
                    "last": None,
                    "rawDelta": None,
                    "delta": None,
                    "counterReset": False,
                    "maxOneMinuteRate": None,
                    "sampleCount": 0,
                    "firstSampleIndex": None,
                    "lastSampleIndex": None,
                },
            )
            if bucket["first"] is None:
                bucket["first"] = value
                bucket["firstSampleIndex"] = sample_index
            bucket["last"] = value
            bucket["lastSampleIndex"] = sample_index
            bucket["sampleCount"] = int(bucket.get("sampleCount") or 0) + 1
            rate = first_number(metric.get("maxOneMinuteRate"), metric.get("oneMinuteRate"), metric.get("meanRate"))
            if rate is not None:
                current = bucket.get("maxOneMinuteRate")
                bucket["maxOneMinuteRate"] = rate if current is None else max(float(current), rate)
    compacted: Dict[str, Any] = {}
    for family, by_token in result.items():
        rows = []
        for bucket in by_token.values():
            first = common.number(bucket.get("first"))
            last = common.number(bucket.get("last"))
            raw_delta = None if first is None or last is None else last - first
            bucket["rawDelta"] = raw_delta
            bucket["counterReset"] = raw_delta is not None and raw_delta < 0
            bucket["delta"] = raw_delta if raw_delta is not None and raw_delta >= 0 else None
            rows.append(bucket)
        rows.sort(key=lambda row: (common.number(row.get("delta")) or 0.0, str(row.get("name"))), reverse=True)
        compacted[family] = rows
    return compacted


def family_rollup(metric_families: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for family in ("property-changes", "scripts", "queue-tasks", "messages-sent"):
        rows = metric_families.get(family, []) if isinstance(metric_families.get(family), list) else []
        deltas = [common.number(row.get("delta")) for row in rows if isinstance(row, dict)]
        rates = [common.number(row.get("maxOneMinuteRate")) for row in rows if isinstance(row, dict)]
        resets = [row for row in rows if isinstance(row, dict) and row.get("counterReset") is True]
        numeric_deltas = [float(value) for value in deltas if value is not None]
        positive_deltas = [value for value in numeric_deltas if value > 0]
        numeric_rates = [float(value) for value in rates if value is not None]
        key = family.replace("-", "")
        result[f"{key}DeltaMax"] = max(numeric_deltas) if numeric_deltas else None
        result[f"{key}PositiveDeltaSum"] = sum(positive_deltas) if positive_deltas else 0.0
        result[f"{key}RateMax"] = max(numeric_rates) if numeric_rates else None
        result[f"{key}CounterResetCount"] = len(resets)
    return result


def parse_fixture_counters(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, str) or not raw.strip():
        return {"ok": False, "raw": raw if isinstance(raw, str) else None, "reason": "missing-counter-text"}
    match = COUNTER_TEXT_RE.search(raw)
    if not match:
        return {"ok": False, "raw": raw, "reason": "counter-pattern-not-found"}
    keys = ("expected", "started", "accepted", "completed", "last")
    parsed = {key: int(match.group(index + 1)) for index, key in enumerate(keys)}
    parsed.update({"ok": True, "raw": match.group(0)})
    return parsed


def watch_snapshot(summary: Dict[str, Any], key: str) -> Dict[str, Any]:
    snapshot = summary.get(key, {}) if isinstance(summary.get(key), dict) else {}
    return {
        "matched": snapshot.get("matched"),
        "value": snapshot.get("value"),
        "textLength": snapshot.get("textLength"),
        "error": snapshot.get("error"),
    }


def exact_int(value: Any) -> Optional[int]:
    number = common.number(value)
    if number is None:
        return None
    integer = int(number)
    return integer if float(number) == float(integer) else None


def final_counters_match(counters: Dict[str, Any], repeat_count: Optional[int]) -> bool:
    if counters.get("ok") is not True:
        return False
    expected = exact_int(counters.get("expected"))
    return bool(
        expected is not None
        and repeat_count == expected
        and exact_int(counters.get("started")) == expected
        and exact_int(counters.get("accepted")) == expected
        and exact_int(counters.get("completed")) == expected
        and exact_int(counters.get("last")) == expected
    )


def initial_counters_match(counters: Dict[str, Any], expected: Optional[int]) -> bool:
    if counters.get("ok") is not True or expected is None:
        return False
    return bool(
        exact_int(counters.get("expected")) == expected
        and exact_int(counters.get("started")) == 0
        and exact_int(counters.get("accepted")) == 0
        and exact_int(counters.get("completed")) == 0
        and exact_int(counters.get("last")) == 0
    )


def browser_interaction(profile_dir: Path) -> Dict[str, Any]:
    browser = read_json(profile_dir / "browser-summary.json")
    interaction = browser.get("interaction", {}) if isinstance(browser.get("interaction"), dict) else {}
    raw_watch = interaction.get("watchText", {}) if isinstance(interaction.get("watchText"), dict) else {}
    watch = {
        "configured": raw_watch.get("configured"),
        "label": raw_watch.get("label"),
        "selector": raw_watch.get("selector"),
        "regexConfigured": raw_watch.get("regexConfigured"),
        "changed": raw_watch.get("changed"),
        "before": watch_snapshot(raw_watch, "before"),
        "after": watch_snapshot(raw_watch, "after"),
    }
    before_counters = parse_fixture_counters(watch["before"].get("value"))
    after_counters = parse_fixture_counters(watch["after"].get("value"))
    repeat_count = exact_int(interaction.get("clickRepeatCount"))
    after_expected = exact_int(after_counters.get("expected")) if after_counters.get("ok") is True else None
    fixture_initial_ok = initial_counters_match(before_counters, after_expected)
    fixture_final_ok = final_counters_match(after_counters, repeat_count)
    return {
        "configured": interaction.get("configured"),
        "ok": interaction.get("ok"),
        "clickOk": interaction.get("clickOk"),
        "resultOk": interaction.get("resultOk"),
        "resultElapsedMs": interaction.get("resultElapsedMs"),
        "clickElapsedMs": interaction.get("clickElapsedMs"),
        "clickRepeatCount": interaction.get("clickRepeatCount"),
        "clickRepeatIntervalMs": interaction.get("clickRepeatIntervalMs"),
        "clickRepeatMode": interaction.get("clickRepeatMode"),
        "resultAlreadyMatchedBeforeClick": interaction.get("resultAlreadyMatchedBeforeClick"),
        "label": interaction.get("label"),
        "watchText": watch,
        "fixtureCounters": {"before": before_counters, "after": after_counters},
        "fixtureCountersInitialOk": fixture_initial_ok,
        "fixtureCountersFinalOk": fixture_final_ok,
        "fixtureCountersOk": fixture_initial_ok and fixture_final_ok,
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


def counter_report_label(proof: Dict[str, Any]) -> str:
    counters = proof.get("fixtureCounters", {}) if isinstance(proof.get("fixtureCounters"), dict) else {}
    after = counters.get("after", {}) if isinstance(counters.get("after"), dict) else {}
    if after.get("ok") is not True:
        return "missing"
    return "{completed}/{expected}".format(completed=after.get("completed"), expected=after.get("expected"))


def evaluate_i02(rows: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    passing_rows = [row for row in rows if row.get("ok")]
    if len(passing_rows) < 2:
        return {"ok": False, "reason": "Need at least two passing variants to correlate queue length and interaction delay."}
    baseline = passing_rows[0]
    target = passing_rows[-1]
    baseline_interaction = baseline.get("browserInteraction", {}) if isinstance(baseline.get("browserInteraction"), dict) else {}
    target_interaction = target.get("browserInteraction", {}) if isinstance(target.get("browserInteraction"), dict) else {}
    baseline_elapsed = first_number(baseline_interaction.get("resultElapsedMs"))
    target_elapsed = first_number(target_interaction.get("resultElapsedMs"))
    baseline_queue = baseline.get("queueLength", {}) if isinstance(baseline.get("queueLength"), dict) else {}
    target_queue = target.get("queueLength", {}) if isinstance(target.get("queueLength"), dict) else {}
    baseline_queue_max = first_number(baseline_queue.get("max")) or 0.0
    target_queue_max = first_number(target_queue.get("max")) or 0.0
    target_queue_last = first_number(target_queue.get("last"))
    target_sustained = int(target_queue.get("sustainedSamples") or 0)
    delay_delta = None if baseline_elapsed is None or target_elapsed is None else target_elapsed - baseline_elapsed
    checks = {
        "queueRose": target_queue_max >= args.min_queue_length,
        "queueExceededBaseline": target_queue_max > baseline_queue_max,
        "queueSustained": target_sustained >= args.min_sustained_queue_samples,
        "queueRecovered": target_queue_last is not None and target_queue_last <= args.recovered_queue_length,
        "interactionDelayIncreased": delay_delta is not None and delay_delta >= args.min_interaction_delay_delta_ms,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "baselineVariant": baseline.get("variant"),
        "targetVariant": target.get("variant"),
        "baselineInteractionMs": baseline_elapsed,
        "targetInteractionMs": target_elapsed,
        "interactionDelayDeltaMs": delay_delta,
        "baselineQueueMax": baseline_queue_max,
        "targetQueueMax": target_queue_max,
        "targetQueueLast": target_queue_last,
        "targetQueueSustainedSamples": target_sustained,
        "thresholds": {
            "minQueueLength": args.min_queue_length,
            "minSustainedQueueSamples": args.min_sustained_queue_samples,
            "recoveredQueueLength": args.recovered_queue_length,
            "minInteractionDelayDeltaMs": args.min_interaction_delay_delta_ms,
        },
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Queue Backlog Incident Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Mechanics OK: `{str(summary.get('mechanicsOk', False)).lower()}`",
        f"Strict I-02 OK: `{str(summary.get('strictI02Ok', False)).lower()}`",
        f"Negative I-02 accepted: `{str(summary.get('negativeI02Accepted', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        "",
        "## Browser Network Throttle",
        "",
    ]
    throttle = summary.get("browserNetworkThrottle", {})
    if isinstance(throttle, dict):
        lines.extend(
            [
                f"- Configured: `{str(throttle.get('configured', False)).lower()}`",
                f"- Scope: `{throttle.get('scope')}`",
                f"- After ready: `{str(throttle.get('afterReady', False)).lower()}`",
                f"- Latency/download/upload: `{throttle.get('latencyMs')}` ms / `{throttle.get('downloadKbps')}` kbps / `{throttle.get('uploadKbps')}` kbps",
                "",
            ]
        )
    lines.extend(
        [
        "## Variant Summary",
        "",
        "| Variant | OK | Tasks | Work ms | Throttle | Counters | Counters OK | Queue max | Queue last | Sustained samples | Queue tasks delta | Result ms | Cleanup |",
        "|---|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in summary.get("variants", []):
        rollup = row.get("metricRollup", {})
        queue = row.get("queueLength", {})
        proof = row.get("browserInteraction", {})
        row_throttle = row.get("networkThrottle", {}) if isinstance(row.get("networkThrottle"), dict) else {}
        lines.append(
            "| {variant} | `{ok}` | {tasks} | {work} | `{throttle}` | {counters} | `{counters_ok}` | {qmax} | {qlast} | {sustained} | {qdelta} | {elapsed} | `{cleanup}` |".format(
                variant=row.get("variant"),
                ok=str(row.get("ok", False)).lower(),
                tasks=row.get("taskCount"),
                work=row.get("workMillis"),
                throttle=str(row_throttle.get("applied", False)).lower(),
                counters=counter_report_label(proof),
                counters_ok=str(proof.get("fixtureCountersOk", False)).lower(),
                qmax=queue.get("max"),
                qlast=queue.get("last"),
                sustained=queue.get("sustainedSamples"),
                qdelta=rollup.get("queuetasksDeltaMax"),
                elapsed=proof.get("resultElapsedMs"),
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewsAbsent", False)).lower(),
            )
        )
    i02 = summary.get("i02Evaluation", {})
    lines.extend(["", "## I-02 Evaluation", ""])
    lines.append(f"- I-02 pass: `{str(i02.get('ok', False)).lower()}`")
    for key, value in (i02.get("checks", {}) if isinstance(i02.get("checks"), dict) else {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- Interaction delay delta ms: `{i02.get('interactionDelayDeltaMs')}`")
    lines.append(f"- Target queue max/last: `{i02.get('targetQueueMax')}` / `{i02.get('targetQueueLast')}`")
    lines.extend(["", "## Fixture Counter Evidence", ""])
    for row in summary.get("variants", []):
        proof = row.get("browserInteraction", {}) if isinstance(row.get("browserInteraction"), dict) else {}
        counters = proof.get("fixtureCounters", {}) if isinstance(proof.get("fixtureCounters"), dict) else {}
        before = counters.get("before", {}) if isinstance(counters.get("before"), dict) else {}
        after = counters.get("after", {}) if isinstance(counters.get("after"), dict) else {}
        lines.append(
            "- `{variant}` counters ok `{ok}`; before `{before}`; after `{after}`".format(
                variant=row.get("variant"),
                ok=str(proof.get("fixtureCountersOk", False)).lower(),
                before=before.get("raw"),
                after=after.get("raw"),
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
    task_counts = parse_task_counts(args.task_counts, args.max_tasks)
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
    feature_set = cp.enabled_name_set(health_response.get("features", []))
    action_set = cp.enabled_name_set(health_response.get("supportedActions", []))
    baseline_capability_set = feature_set | action_set if action_set else feature_set

    for task_count in task_counts:
        variant = variant_label(task_count)
        variant_dir = out_dir / variant
        route = build_route(args.route_prefix, run_slug, variant)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/QueueBacklog{task_count:04d}"
        package = build_package(variant_dir, project, args, task_count, task_count == task_counts[-1], view_path, route)
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
            profile_dir = (variant_dir / "profile").resolve()
            command = profile_command(args, package, project, browser_url, profile_dir)
            profile_result = common.run_command(command, f"profile-{variant}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            metric_families = metric_family_samples(profile_dir)
            row = {
                "variant": variant,
                "taskCount": task_count,
                "maxTasks": package["maxTasks"],
                "workMillis": package["workMillis"],
                "maxWorkMillis": package["maxWorkMillis"],
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
                "networkThrottle": browser_network_throttle_evidence(args, package),
                "static": static_summary(profile_dir),
                "queueLength": queue_length_timeseries(profile_dir),
                "metricFamilies": metric_families,
                "metricRollup": family_rollup(metric_families),
                "profileCommand": profile_result,
            }
            baseline_variant = variant_label(task_counts[0])
            baseline_dir = out_dir / baseline_variant / "profile"
            if task_count != task_counts[0] and baseline_dir.exists() and gates["profile"]:
                comparison = compare_to_baseline(out_dir, baseline_dir, profile_dir, variant)
                comparisons.append(comparison)
        except Exception as exc:
            row = {
                "variant": variant,
                "taskCount": task_count,
                "maxTasks": package.get("maxTasks"),
                "workMillis": package.get("workMillis"),
                "maxWorkMillis": package.get("maxWorkMillis"),
                "ok": False,
                "gates": gates,
                "gateDetails": gate_details,
                "baselineWait": baseline,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "networkThrottle": browser_network_throttle_evidence(args, package),
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
            if args.pause_sec > 0 and task_count != task_counts[-1]:
                time.sleep(args.pause_sec)

    i02_evaluation = evaluate_i02(variants, args)
    interpretation = [
        "The fixture dispatches a bounded number of browser-originated Perspective button actions; task count and per-task sleep are clamped in the handler script.",
        "The browser profile also watches a visible fixture counter label and requires started, accepted, completed, and last-index counters to match the requested click repeat count before treating the fixture mechanics as complete.",
        "Optional browser network throttling can be applied after the ready marker to all variants or only the largest/backlog variant to test whether session queue length responds to outbound/backpressure conditions.",
        "I-02 is considered proven only when the backlog variant shows sustained queue-length samples, recovers before the final sample, and its click-to-done latency exceeds the baseline variant.",
        "This is dev/staging mechanics evidence. Do not use it as customer root-cause proof unless the same pattern is captured on the customer route or a customer-approved fixture.",
    ]
    mechanics_ok = bool(health_ok and variants and all(row.get("ok") for row in variants) and all(row.get("ok") for row in comparisons))
    strict_i02_ok = bool(i02_evaluation.get("ok"))
    negative_i02_accepted = bool(mechanics_ok and args.allow_negative_i02 and not strict_i02_ok)
    summary = {
        "ok": bool(mechanics_ok and (strict_i02_ok or args.allow_negative_i02)),
        "mechanicsOk": mechanics_ok,
        "strictI02Ok": strict_i02_ok,
        "negativeI02Accepted": negative_i02_accepted,
        "runId": args.run_id,
        "project": project,
        "runnerVersion": health_response.get("runnerVersion"),
        "stackVersion": health_response.get("stackVersion"),
        "features": sorted(feature_set),
        "supportedActions": sorted(action_set),
        "createdAt": common.utc_now(),
        "taskCounts": task_counts,
        "workMillis": args.work_millis,
        "maxTasks": args.max_tasks,
        "maxWorkMillis": args.max_work_millis,
        "browserNetworkThrottle": {
            "configured": browser_network_throttle_configured(args),
            "scope": args.browser_network_throttle_scope,
            "afterReady": bool(args.browser_network_throttle_after_ready),
            "latencyMs": args.browser_network_latency_ms,
            "downloadKbps": args.browser_network_download_kbps,
            "uploadKbps": args.browser_network_upload_kbps,
        },
        "healthOk": health_ok,
        "packages": packages,
        "variants": variants,
        "comparisons": comparisons,
        "i02Evaluation": i02_evaluation,
        "interpretation": interpretation,
    }
    write_json(out_dir / "summary.json", summary)
    write_report(out_dir, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--task-counts", default="5,40", help="Comma-separated bounded button-action counts.")
    parser.add_argument("--max-tasks", type=int, default=200)
    parser.add_argument("--work-millis", type=int, default=25)
    parser.add_argument("--max-work-millis", type=int, default=100)
    parser.add_argument("--route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=18.0)
    parser.add_argument("--interval-sec", type=float, default=0.25)
    parser.add_argument("--max-metrics", type=int, default=80)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--command-timeout-sec", type=int, default=600)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default='[data-component-path="C.0:0"]')
    parser.add_argument("--browser-timeout-sec", type=float, default=120.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=1500)
    parser.add_argument("--browser-click-after-ready-delay-ms", type=int, default=500)
    parser.add_argument("--browser-click-repeat-interval-ms", type=int, default=0)
    parser.add_argument("--browser-click-repeat-mode", default="playwright", choices=["playwright", "mouse", "dom"])
    parser.add_argument("--browser-click-timeout-sec", type=float, default=90.0)
    parser.add_argument("--browser-post-interaction-wait-ms", type=int, default=3500)
    parser.add_argument("--browser-network-throttle-after-ready", action="store_true")
    parser.add_argument(
        "--browser-network-throttle-scope",
        default="all",
        choices=["all", "backlog"],
        help="Apply configured browser network throttle to all variants or only the largest/backlog variant.",
    )
    parser.add_argument("--browser-network-latency-ms", type=float, default=0.0)
    parser.add_argument("--browser-network-download-kbps", type=float, default=0.0)
    parser.add_argument("--browser-network-upload-kbps", type=float, default=0.0)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node", default="")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--min-queue-length", type=float, default=1.0)
    parser.add_argument("--min-sustained-queue-samples", type=int, default=2)
    parser.add_argument("--recovered-queue-length", type=float, default=0.0)
    parser.add_argument("--min-interaction-delay-delta-ms", type=float, default=100.0)
    parser.add_argument(
        "--allow-negative-i02",
        action="store_true",
        help="Exit successfully when fixture/profile/cleanup mechanics pass but strict queue-length proof is not observed.",
    )
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
    if args.max_tasks < 1:
        raise SystemExit("--max-tasks must be >= 1")
    if args.work_millis < 0:
        raise SystemExit("--work-millis must be >= 0")
    if args.max_work_millis < 0:
        raise SystemExit("--max-work-millis must be >= 0")
    if args.work_millis > args.max_work_millis:
        raise SystemExit("--work-millis cannot exceed --max-work-millis")
    if args.profile_duration_sec <= 0:
        raise SystemExit("--profile-duration-sec must be > 0")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.browser_click_timeout_sec <= 0:
        raise SystemExit("--browser-click-timeout-sec must be > 0")
    if args.browser_click_repeat_interval_ms < 0:
        raise SystemExit("--browser-click-repeat-interval-ms must be >= 0")
    if args.browser_network_latency_ms < 0:
        raise SystemExit("--browser-network-latency-ms must be >= 0")
    if args.browser_network_download_kbps < 0:
        raise SystemExit("--browser-network-download-kbps must be >= 0")
    if args.browser_network_upload_kbps < 0:
        raise SystemExit("--browser-network-upload-kbps must be >= 0")
    if args.min_sustained_queue_samples < 1:
        raise SystemExit("--min-sustained-queue-samples must be >= 1")
    summary = run(args)
    print(json.dumps({"ok": summary.get("ok"), "summaryPath": str(Path(args.out_dir) / "summary.json")}, indent=2, sort_keys=True))
    raise SystemExit(0 if summary.get("ok") else 1)


if __name__ == "__main__":
    main()
