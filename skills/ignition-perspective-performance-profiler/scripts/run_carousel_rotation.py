#!/usr/bin/env python3
"""Run guarded Perspective Carousel repeated-rotation fixtures.

This helper covers A-17-style Carousel rotation checks. It compares eager and
lazy Carousel loading with the same child views, advances activePane through a
bounded button event, samples Gateway/session metrics while the browser cycles,
and rolls back all disposable route/view resources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_table_ab_remediation as fixture_common
import run_tab_runwhilehidden_ab as tab_common


SCRIPT_DIR = Path(__file__).resolve().parent
BROWSER_CAROUSEL_PROBE = SCRIPT_DIR / "browser_carousel_cycle_probe.mjs"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
VARIANTS = ("lazy-load-off", "lazy-load-on")
OFFICIAL_SOURCE = "https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-carousel"


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


def append_ndjson(path: Path, row: Dict[str, Any]) -> None:
    cp.append_ndjson(path, row)


def zip_file_base64(path: Path) -> str:
    return common.zip_file_base64(path)


def to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


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


def expression_binding(expression: str) -> Dict[str, Any]:
    return {"binding": {"type": "expr", "config": {"expression": expression}}}


def property_binding(path: str, transform_code: str = "") -> Dict[str, Any]:
    binding: Dict[str, Any] = {"type": "property", "config": {"path": path}}
    if transform_code:
        binding["transforms"] = [{"type": "script", "code": transform_code}]
    return {"binding": binding}


def text_transform(prefix: str) -> str:
    return f"\treturn '{prefix}' + str(value)\n"


def lazy_load_for_variant(variant: str) -> bool:
    if variant == "lazy-load-on":
        return True
    if variant == "lazy-load-off":
        return False
    raise ValueError(f"Unsupported variant: {variant}")


def title_for_variant(variant: str) -> str:
    return "Lazy Load on" if lazy_load_for_variant(variant) else "Lazy Load off"


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-carousel-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def action_script() -> str:
    return "\n".join(
        [
            "\ttry:",
            "\t\tslide_count = int(self.view.custom.slideCount)",
            "\texcept:",
            "\t\tslide_count = 1",
            "\ttry:",
            "\t\tcount = int(self.view.custom.rotationCount)",
            "\texcept:",
            "\t\tcount = 0",
            "\tif slide_count < 1:",
            "\t\tslide_count = 1",
            "\tcount = count + 1",
            "\tactive = count % slide_count",
            "\ttry:",
            "\t\tself.getSibling('CycleCarousel').props.activePane = active",
            "\texcept Exception as err:",
            "\t\tself.view.custom.rotationText = 'Rotation error: ' + str(err)",
            "\t\treturn",
            "\tself.view.custom.rotationCount = count",
            "\tself.view.custom.activePaneIndex = active",
            "\tself.view.custom.rotationText = 'Rotation count: ' + str(count) + ' active pane: ' + str(active)",
        ]
    )


def make_child_view(run_id: str, work_labels: int, expression_rate_ms: int) -> Dict[str, Any]:
    children: List[Dict[str, Any]] = [
        component(
            "ia.display.label",
            meta={"name": "Slide Label From Param"},
            position={"basis": "46px", "grow": 0, "shrink": 0},
            props={
                "text": "Carousel slide waiting",
                "style": {
                    "backgroundColor": "#ffffff",
                    "borderColor": "#64748b",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "color": "#111827",
                    "fontSize": 18,
                    "fontWeight": "700",
                    "padding": "10px",
                    "whiteSpace": "pre-wrap",
                },
            },
            prop_config={"props.text": expression_binding("{view.params.slideLabel}")},
        )
    ]
    for index in range(1, work_labels + 1):
        children.append(
            component(
                "ia.display.label",
                meta={"name": f"Carousel Work Tick {index:03d}"},
                position={"basis": "20px", "grow": 0, "shrink": 0},
                props={
                    "text": f"work tick {index:03d}",
                    "style": {
                        "color": "#334155",
                        "fontSize": 11,
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                    },
                },
                prop_config={"props.text": expression_binding(f"now({expression_rate_ms})")},
            )
        )
    return {
        "custom": {"runId": run_id, "role": "carousel-child", "workLabels": work_labels, "expressionRateMs": expression_rate_ms},
        "params": {"slideLabel": ""},
        "propConfig": {"params.slideLabel": {"paramDirection": "input"}},
        "props": {"defaultSize": {"width": 420, "height": 260}},
        "root": component(
            "ia.container.flex",
            meta={"name": "carousel-child-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {"backgroundColor": "#f8fafc", "overflow": "hidden", "padding": "8px"},
            },
            children=children,
        ),
        "permissions": {},
    }


def make_parent_view(
    run_id: str,
    variant: str,
    child_view_path: str,
    slide_count: int,
    rotation_delay_ms: int,
) -> Dict[str, Any]:
    lazy_load = lazy_load_for_variant(variant)
    marker = f"{run_id} {variant.upper()} READY"
    views = [
        {
            "viewPath": child_view_path,
            "viewParams": {"slideLabel": f"Carousel slide {index:03d}"},
            "direction": "column",
            "justify": "center",
            "alignItems": "stretch",
        }
        for index in range(1, slide_count + 1)
    ]
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "slideCount": slide_count,
            "rotationCount": 0,
            "activePaneIndex": 0,
            "rotationText": "Rotation count: 0 active pane: 0",
            "lazyLoad": lazy_load,
            "testPurpose": "Repeated Perspective Carousel activePane rotation",
            "officialSource": OFFICIAL_SOURCE,
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "carousel-rotation-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {"backgroundColor": "#eef2f7", "overflow": "hidden", "padding": "12px"},
            },
            children=[
                component(
                    "ia.display.label",
                    meta={"name": "Ready Marker"},
                    position={"basis": "42px", "grow": 0, "shrink": 0},
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
                            "padding": "9px 10px",
                            "whiteSpace": "pre-wrap",
                        },
                    },
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Fixture Summary"},
                    position={"basis": "38px", "grow": 0, "shrink": 0},
                    props={
                        "text": f"A-17 Carousel rotation fixture: {title_for_variant(variant)}, {slide_count} slides, button-driven activePane changes.",
                        "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
                    },
                ),
                component(
                    "ia.input.button",
                    meta={"name": "Next Slide Button"},
                    position={"basis": "40px", "grow": 0, "shrink": 0},
                    props={"text": "Next slide", "style": {"fontSize": 14, "fontWeight": "700"}},
                    events={"component": {"onActionPerformed": {"scope": "G", "type": "script", "config": {"script": action_script()}}}},
                ),
                component(
                    "ia.display.label",
                    meta={"name": "Rotation Counter"},
                    position={"basis": "34px", "grow": 0, "shrink": 0},
                    props={
                        "text": "Rotation count: 0 active pane: 0",
                        "style": {"color": "#0f172a", "fontSize": 14, "fontWeight": "700", "padding": "7px 2px", "whiteSpace": "pre-wrap"},
                    },
                    prop_config={"props.text": property_binding("view.custom.rotationText")},
                ),
                component(
                    "ia.display.carousel",
                    meta={"name": "CycleCarousel"},
                    position={"basis": "384px", "grow": 0, "shrink": 0},
                    props={
                        "views": views,
                        "activePane": 0,
                        "lazyLoad": lazy_load,
                        "autoplay": {
                            "enabled": False,
                            "transitionDelay": rotation_delay_ms,
                            "pauseOnHover": False,
                            "pauseOnFocus": False,
                            "pauseOnDotHover": False,
                        },
                        "behavior": {
                            "transitionSpeed": max(50, min(rotation_delay_ms, 400)),
                            "fade": False,
                            "mobileSwipeable": False,
                            "desktopDraggable": False,
                        },
                        "appearance": {
                            "dots": {"enabled": True},
                            "arrows": {"enabled": False},
                        },
                        "useDefaultViewWidth": False,
                        "useDefaultViewHeight": False,
                        "slidesToShow": 1,
                        "slidePadding": 0,
                        "style": {
                            "backgroundColor": "#ffffff",
                            "borderColor": "#94a3b8",
                            "borderRadius": 4,
                            "borderStyle": "solid",
                            "borderWidth": "1px",
                            "overflow": "hidden",
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
    write_json(view_dir / "resource.json", fixture_common.resource_json(actor, ["view.json"]))


def make_zip(root: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    parent_view_path: str,
    child_view_path: str,
    route: str,
    slide_count: int,
    work_labels: int,
    expression_rate_ms: int,
    rotation_delay_ms: int,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    parent_view = make_parent_view(run_id, variant, child_view_path, slide_count, rotation_delay_ms)
    child_view = make_child_view(run_id, work_labels, expression_rate_ms)
    zip_path = zip_dir / f"carousel-{slug(variant)}.zip"
    actor = "perf-profiler-carousel-rotation"
    with tempfile.TemporaryDirectory(prefix="perfprof-carousel-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler Carousel rotation fixture", "enabled": True, "inheritable": False})
        write_view(project_root, child_view_path, child_view, actor)
        write_view(project_root, parent_view_path, parent_view, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Carousel Rotation {variant}", "viewPath": parent_view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "lazyLoad": lazy_load_for_variant(variant),
        "parentViewPath": parent_view_path,
        "childViewPath": child_view_path,
        "viewPaths": [parent_view_path, child_view_path],
        "route": route,
        "slideCount": slide_count,
        "workLabels": work_labels,
        "expressionRateMs": expression_rate_ms,
        "rotationDelayMs": rotation_delay_ms,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": zip_file_base64(zip_path),
        "parentViewSha256": sha256_text(canonical_json(parent_view)),
        "childViewSha256": sha256_text(canonical_json(child_view)),
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
        "allowedNamedQueryPrefix": args.allowed_view_prefix,
        "routes": [{"pagePath": package["route"], "viewPath": package["parentViewPath"], "title": f"Carousel Rotation {package['variant']}"}],
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


def rollback_payload(request_id: str, project: str, backup_name: str, view_paths: List[str], dry_run: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "rollback",
        "requestId": request_id,
        "targetProject": project,
        "backupName": backup_name,
        "viewPaths": view_paths,
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


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    text = canonical_json(cp.response(record))
    return (
        cp.ok(record)
        and '"type":"ia.display.carousel"' in text
        and f'"lazyLoad":{str(package["lazyLoad"]).lower()}' in text
        and text.count('"viewPath"') >= package["slideCount"]
        and "onActionPerformed" in text
        and "activePane" in text
    )


def backup_name(data: Dict[str, Any]) -> str:
    return str(data.get("backupName", "") or data.get("backupDir", "")).replace("\\", "/").rstrip("/").split("/")[-1]


def browser_env(args: argparse.Namespace) -> Dict[str, str]:
    env = dict(os.environ)
    if args.browser_node_modules:
        roots = [args.browser_node_modules]
        pnpm_root = Path(args.browser_node_modules) / ".pnpm" / "node_modules"
        if pnpm_root.exists():
            roots.append(str(pnpm_root))
        existing = env.get("NODE_PATH", "")
        env["NODE_PATH"] = os.pathsep.join([item for item in roots + ([existing] if existing else []) if item])
    return env


def redact_command(command: List[str]) -> List[str]:
    redacted = list(command)
    for index, value in enumerate(redacted[:-1]):
        if value == "--url":
            redacted[index + 1] = "<redacted-browser-url>"
        elif value == "--browser-node-modules":
            redacted[index + 1] = "<redacted-node-modules>"
        elif value in ("--ready-text", "--click-text"):
            redacted[index + 1] = "<redacted-text>"
    return redacted


def run_browser_probe(args: argparse.Namespace, browser_url: str, package: Dict[str, Any], profile_dir: Path) -> Dict[str, Any]:
    profile_dir_abs = profile_dir.resolve()
    command = [
        args.browser_node,
        str(BROWSER_CAROUSEL_PROBE),
        "--url",
        browser_url,
        "--out-dir",
        str(profile_dir_abs),
        "--ready-selector",
        args.browser_ready_selector,
        "--ready-text",
        package["readyText"],
        "--click-text",
        "Next slide",
        "--cycles",
        str(args.cycles),
        "--cycle-delay-ms",
        str(args.cycle_delay_ms),
        "--timeout-ms",
        str(int(args.browser_timeout_sec * 1000)),
        "--viewport",
        args.browser_viewport,
        "--url-alias",
        args.browser_url_alias,
    ]
    stdout_path = profile_dir / "browser-carousel-probe.stdout.txt"
    stderr_path = profile_dir / "browser-carousel-probe.stderr.txt"
    started = utc_now()
    with stdout_path.open("w", encoding="utf-8", newline="\n") as stdout_handle, stderr_path.open("w", encoding="utf-8", newline="\n") as stderr_handle:
        process = subprocess.Popen(command, stdout=stdout_handle, stderr=stderr_handle, cwd=str(SCRIPT_DIR), env=browser_env(args))
        return {"process": process, "command": redact_command(command), "startedAt": started, "stdoutPath": str(stdout_path), "stderrPath": str(stderr_path)}


def collect_profile_window(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    profile_dir: Path,
    project: str,
    run_id: str,
    feature_set: set[str],
    browser_process: subprocess.Popen[Any],
) -> Dict[str, Any]:
    missing: List[Dict[str, str]] = []
    tokens: List[str] = []
    metrics_list_record: Optional[Dict[str, Any]] = None
    if "metricsList" in feature_set:
        payload: Dict[str, Any] = {
            "action": "metricsList",
            "requestId": f"{run_id}-metricsList",
            "nameContains": args.metric_name_contains,
            "maxResults": min(max(args.max_metrics * 3, args.max_metrics), 250),
        }
        if args.metric_prefix:
            payload["namePrefixes"] = args.metric_prefix
        metrics_list_record = client.call(f"{run_id}-metricsList", payload)
        write_json(profile_dir / "metrics-list.json", cp.response(metrics_list_record))
        tokens = cp.metric_tokens(cp.response(metrics_list_record), max(0, min(args.max_metrics, 100)))
        if not tokens:
            missing.append({"name": "metricsSnapshot", "reason": "metricsList returned no metric tokens for the configured filters"})
    else:
        missing.append({"name": "metricsList", "reason": "runner health.features does not include metricsList"})

    started_at = time.time()
    sample_index = 0
    while True:
        started = utc_now()
        phase = "rotation"
        gateway_sample: Dict[str, Any] = {"sampleIndex": sample_index, "phase": phase, "startedAt": started}
        if tokens and "metricsSnapshot" in feature_set:
            record = client.call(
                f"{run_id}-metricsSnapshot-{sample_index:03d}",
                {"action": "metricsSnapshot", "requestId": f"{run_id}-metricsSnapshot-{sample_index:03d}", "metricTokens": tokens, "maxMetrics": len(tokens)},
            )
            gateway_sample["metricsSnapshot"] = cp.response(record)
        elif "metricsSnapshot" not in feature_set:
            gateway_sample["metricsSnapshot"] = {"ok": False, "missing": True, "reason": "feature not present"}
        if "gatewayPerformanceSnapshot" in feature_set:
            record = client.call(
                f"{run_id}-gatewayPerformanceSnapshot-{sample_index:03d}",
                {"action": "gatewayPerformanceSnapshot", "requestId": f"{run_id}-gatewayPerformanceSnapshot-{sample_index:03d}"},
            )
            gateway_sample["gatewayPerformanceSnapshot"] = cp.response(record)
        else:
            gateway_sample["gatewayPerformanceSnapshot"] = {"ok": False, "missing": True, "reason": "feature not present"}
        gateway_sample["finishedAt"] = utc_now()
        append_ndjson(profile_dir / "gateway-samples.ndjson", gateway_sample)

        session_sample: Dict[str, Any] = {"sampleIndex": sample_index, "phase": phase, "startedAt": started}
        if "perspectiveSessionsQuery" in feature_set:
            record = client.call(
                f"{run_id}-perspectiveSessionsQuery-{sample_index:03d}",
                {"action": "perspectiveSessionsQuery", "requestId": f"{run_id}-perspectiveSessionsQuery-{sample_index:03d}", "targetProject": project, "maxResults": 50},
            )
            session_sample["perspectiveSessionsQuery"] = cp.response(record)
        else:
            session_sample["perspectiveSessionsQuery"] = {"ok": False, "missing": True, "reason": "feature not present"}
        session_sample["finishedAt"] = utc_now()
        append_ndjson(profile_dir / "perspective-session-samples.ndjson", session_sample)

        sample_index += 1
        elapsed = time.time() - started_at
        if browser_process.poll() is not None and sample_index >= args.min_samples:
            break
        if elapsed >= args.profile_timeout_sec:
            missing.append({"name": "browserProbe", "reason": "Browser probe exceeded profile timeout during sampling"})
            break
        time.sleep(max(args.interval_sec, 0.25))

    if "metricsSnapshot" not in feature_set:
        missing.append({"name": "metricsSnapshot", "reason": "runner health.features does not include metricsSnapshot"})
    if "gatewayPerformanceSnapshot" not in feature_set:
        missing.append({"name": "gatewayPerformanceSnapshot", "reason": "runner health.features does not include gatewayPerformanceSnapshot"})
    if "perspectiveSessionsQuery" not in feature_set:
        missing.append({"name": "perspectiveSessionsQuery", "reason": "runner health.features does not include perspectiveSessionsQuery"})
    return {
        "sampleCount": sample_index,
        "metricTokenCount": len(tokens),
        "metricsListOk": cp.ok(metrics_list_record) if metrics_list_record else False,
        "missingEvidence": missing,
    }


def finish_browser_probe(info: Dict[str, Any], timeout_sec: float) -> Dict[str, Any]:
    process: subprocess.Popen[Any] = info["process"]
    timed_out = False
    try:
        exit_code = process.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            exit_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            exit_code = process.wait(timeout=5)
    return {
        "exitCode": exit_code,
        "timedOut": timed_out,
        "startedAt": info.get("startedAt"),
        "finishedAt": utc_now(),
        "command": info.get("command"),
        "stdoutPath": info.get("stdoutPath"),
        "stderrPath": info.get("stderrPath"),
    }


def metric_items_by_name(row: Dict[str, Any]) -> Dict[str, float]:
    snapshot = row.get("metricsSnapshot", {}) if isinstance(row.get("metricsSnapshot"), dict) else {}
    metrics = snapshot.get("metrics", []) if isinstance(snapshot.get("metrics"), list) else []
    result: Dict[str, float] = {}
    for item in metrics:
        if not isinstance(item, dict) or item.get("ok") is not True:
            continue
        name = str(item.get("name", "")).strip()
        value = to_float(item.get("count"))
        if name and value is not None:
            result[name] = result.get(name, 0.0) + value
    return result


def summarize_metric_counts(profile_dir: Path) -> Dict[str, Any]:
    rows = []
    path = profile_dir / "gateway-samples.ndjson"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    items = [metric_items_by_name(row) for row in rows]
    names = sorted({name for row in items for name in row})
    counts: Dict[str, Dict[str, Any]] = {}
    for name in names:
        values = [row[name] for row in items if name in row]
        counts[name] = {"first": values[0] if values else None, "last": values[-1] if values else None, "delta": (values[-1] - values[0]) if len(values) >= 2 else None}
    preferred = {
        "expressions": "perspective.expressions",
        "propertyChanges": "perspective.property-changes",
        "scripts": "perspective.scripts",
        "messagesSent": "perspective.messages-sent",
        "messagesReceived": "perspective.messages-received",
    }
    result = {"sampleCount": len(rows), "countMetricNames": names, "counts": counts}
    for label, exact in preferred.items():
        metric_name = exact if exact in counts else next((name for name in names if name.startswith("perspective.") and name.endswith("." + exact.split(".")[-1])), "")
        result[f"primary{label[0].upper()}{label[1:]}Metric"] = metric_name
        result[f"primary{label[0].upper()}{label[1:]}Delta"] = counts.get(metric_name, {}).get("delta") if metric_name else None
    return result


def gateway_summary(profile_dir: Path) -> Dict[str, Any]:
    rows = []
    path = profile_dir / "gateway-samples.ndjson"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    heaps: List[float] = []
    cpus: List[float] = []
    for row in rows:
        perf = row.get("gatewayPerformanceSnapshot", {}) if isinstance(row.get("gatewayPerformanceSnapshot"), dict) else {}
        heap = perf.get("heap", {}) if isinstance(perf.get("heap"), dict) else {}
        used = to_float(heap.get("usedBytes") or heap.get("used"))
        cpu = to_float(perf.get("processCpuLoad") or perf.get("systemCpuLoad"))
        if used is not None:
            heaps.append(used)
        if cpu is not None:
            cpus.append(cpu)
    return {
        "sampleCount": len(rows),
        "heapUsedBytesFirst": heaps[0] if heaps else None,
        "heapUsedBytesLast": heaps[-1] if heaps else None,
        "heapUsedBytesMax": max(heaps) if heaps else None,
        "processCpuLoadAvg": (sum(cpus) / len(cpus)) if cpus else None,
    }


def named_row_count(value: Any, name: str) -> Optional[int]:
    if isinstance(value, dict):
        raw = value.get(name)
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None
    if isinstance(value, list):
        total = 0
        found = False
        for item in value:
            if not isinstance(item, dict) or item.get("name") != name:
                continue
            try:
                total += int(item.get("count", 0))
                found = True
            except (TypeError, ValueError):
                continue
        return total if found else None
    return None


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    profile = read_json(profile_dir / "static-profile.json")
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    instantiation = profile.get("viewInstantiation")
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "scriptCount": summary.get("scriptCount"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
        "carouselCount": named_row_count(instantiation, "carousel"),
    }


def browser_summary(profile_dir: Path) -> Dict[str, Any]:
    browser = read_json(profile_dir / "browser-summary.json")
    observation = browser.get("observationSummary", {}) if isinstance(browser.get("observationSummary"), dict) else {}
    network = browser.get("network", {}) if isinstance(browser.get("network"), dict) else {}
    websocket = network.get("websocket", {}) if isinstance(network.get("websocket"), dict) else {}
    return {
        "ok": browser.get("ok"),
        "cyclesRequested": browser.get("cyclesRequested"),
        "cyclesObserved": browser.get("cyclesObserved"),
        "domFirst": observation.get("domFirst"),
        "domLast": observation.get("domLast"),
        "domMax": observation.get("domMax"),
        "heapFirst": observation.get("heapFirst"),
        "heapLast": observation.get("heapLast"),
        "heapMax": observation.get("heapMax"),
        "uniqueActivePanes": observation.get("uniqueActivePanes"),
        "uniqueSlideLabels": observation.get("uniqueSlideLabels"),
        "consoleErrorCount": browser.get("consoleErrorCount"),
        "consoleWarningCount": browser.get("consoleWarningCount"),
        "renderWarningCount": browser.get("renderWarningCount"),
        "webSocketFramesSent": websocket.get("framesSent"),
        "webSocketFramesReceived": websocket.get("framesReceived"),
        "webSocketBytesSent": websocket.get("bytesSent"),
        "webSocketBytesReceived": websocket.get("bytesReceived"),
    }


def profile_variant(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    project: str,
    package: Dict[str, Any],
    profile_dir: Path,
    health: Dict[str, Any],
    feature_set: set[str],
) -> Dict[str, Any]:
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_view = cp.ensure_profile_function()
    readback = client.call(
        f"{args.run_id}-{package['variant']}-profile-viewRead",
        view_read_payload(f"{args.run_id}-{package['variant']}-profile-viewRead", project, package["parentViewPath"], args),
    )
    view_response = cp.response(readback)
    write_json(profile_dir / "view-read.json", view_response)
    static_profile = profile_view(view_response, "view-read.json")
    write_json(profile_dir / "static-profile.json", static_profile)
    browser_url = common.browser_url_from_endpoint(client.endpoint, project, package["route"])
    browser_info = run_browser_probe(args, browser_url, package, profile_dir)
    window = collect_profile_window(client, args, profile_dir, project, f"{args.run_id}-{package['variant']}", feature_set, browser_info["process"])
    browser_result = finish_browser_probe(browser_info, max(args.browser_timeout_sec, args.profile_timeout_sec + 10))
    log_record = client.call(
        f"{args.run_id}-{package['variant']}-logQuery",
        {"action": "logQuery", "requestId": f"{args.run_id}-{package['variant']}-logQuery", "sinceMinutes": 10, "levels": ["ERROR", "WARN"], "textContains": "Perspective", "maxResults": 50, "tailBytes": 262144},
    )
    write_json(profile_dir / "logs.json", cp.response(log_record))
    write_json(profile_dir / "thread-excerpts.json", {"ok": False, "missing": True, "reason": "No active freeze/backlog/CPU-spike trigger requested"})
    write_json(profile_dir / "comparison.json", {"ok": False, "missing": True, "reason": "No pair comparison in single Carousel variant profile"})
    manifest_missing = list(window.get("missingEvidence", []))
    browser_file = read_json(profile_dir / "browser-summary.json")
    if browser_result.get("exitCode") != 0 or browser_file.get("ok") is not True:
        manifest_missing.append({"name": "browserCarouselCycleProbe", "reason": "Browser Carousel cycle probe failed or did not observe requested cycles"})
    manifest = {
        "runId": f"{args.run_id}-carousel-{package['variant']}",
        "createdAt": utc_now(),
        "scenario": "Repeated Carousel activePane rotation",
        "runnerVersion": health.get("runnerVersion"),
        "stackVersion": health.get("stackVersion"),
        "gatewayAlias": args.gateway_alias,
        "project": project,
        "route": package["route"],
        "viewPath": package["parentViewPath"],
        "dependencyViewPaths": [package["childViewPath"]],
        "variant": package["variant"],
        "lazyLoad": package["lazyLoad"],
        "sampleIntervalSeconds": args.interval_sec,
        "sampleCount": window.get("sampleCount"),
        "metricTokenCount": window.get("metricTokenCount"),
        "missingEvidence": manifest_missing,
        "files": [
            "view-read.json",
            "static-profile.json",
            "gateway-samples.ndjson",
            "perspective-session-samples.ndjson",
            "browser-summary.json",
            "browser-carousel-cycles.json",
            "browser-console.json",
            "network-summary.json",
            "logs.json",
            "thread-excerpts.json",
            "comparison.json",
        ],
    }
    write_json(profile_dir / "manifest.json", manifest)
    summary = {
        "ok": not manifest_missing,
        "variant": package["variant"],
        "lazyLoad": package["lazyLoad"],
        "sampleCount": window.get("sampleCount"),
        "metricTokenCount": window.get("metricTokenCount"),
        "browserProbe": browser_result,
        "browser": browser_summary(profile_dir),
        "gateway": gateway_summary(profile_dir),
        "metrics": summarize_metric_counts(profile_dir),
        "static": static_summary(profile_dir),
    }
    write_json(profile_dir / "summary.json", summary)
    return summary


def cleanup(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    project: str,
    package: Dict[str, Any],
    backup: str,
) -> Dict[str, Any]:
    if not backup:
        return {"rollbackOk": False, "reason": "No backup name captured"}
    rb_dry = client.call(
        f"{args.run_id}-{package['variant']}-rollback-dryRun",
        rollback_payload(f"{args.run_id}-{package['variant']}-rollback-dryRun", project, backup, package["viewPaths"], True),
        timeout=args.timeout_sec,
    )
    rb_apply = client.call(
        f"{args.run_id}-{package['variant']}-rollback-apply",
        rollback_payload(f"{args.run_id}-{package['variant']}-rollback-apply", project, backup, package["viewPaths"], False),
        timeout=args.timeout_sec,
    )
    time.sleep(2)
    routes_check = client.call(
        f"{args.run_id}-{package['variant']}-post-cleanup-routesList",
        {"action": "routesList", "requestId": f"{args.run_id}-{package['variant']}-post-cleanup-routesList", "targetProject": project, "routePrefix": package["route"], "maxResults": 25},
    )
    routes = cp.response(routes_check).get("routes", [])
    route_still_present = any(isinstance(item, dict) and item.get("pagePath") == package["route"] for item in routes if isinstance(routes, list))
    view_absent = True
    for view_path in package["viewPaths"]:
        after = client.call(
            f"{args.run_id}-{package['variant']}-post-cleanup-{slug(view_path)}-viewRead",
            view_read_payload(f"{args.run_id}-{package['variant']}-post-cleanup-{slug(view_path)}-viewRead", project, view_path, args),
        )
        view_absent = view_absent and not cp.ok(after)
    return {
        "rollbackOk": cp.ok(rb_dry) and cp.ok(rb_apply),
        "cleanupRouteAbsent": cp.ok(routes_check) and not route_still_present,
        "cleanupViewsAbsent": view_absent,
    }


def compare_variants(variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    off = next((row for row in variants if row.get("variant") == "lazy-load-off"), {})
    on = next((row for row in variants if row.get("variant") == "lazy-load-on"), {})

    def nested(row: Dict[str, Any], *keys: str) -> Any:
        current: Any = row
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def diff(path: List[str]) -> Optional[float]:
        left = to_float(nested(off, *path))
        right = to_float(nested(on, *path))
        if left is None or right is None:
            return None
        return right - left

    return {
        "lazyOnMinusOffDomLast": diff(["browser", "domLast"]),
        "lazyOnMinusOffDomMax": diff(["browser", "domMax"]),
        "lazyOnMinusOffHeapLast": diff(["browser", "heapLast"]),
        "lazyOnMinusOffHeapMax": diff(["browser", "heapMax"]),
        "lazyOnMinusOffExpressionDelta": diff(["metrics", "primaryExpressionsDelta"]),
        "lazyOnMinusOffPropertyChangeDelta": diff(["metrics", "primaryPropertyChangesDelta"]),
        "lazyOnMinusOffScriptsDelta": diff(["metrics", "primaryScriptsDelta"]),
        "lazyOnMinusOffWebSocketBytesReceived": diff(["browser", "webSocketBytesReceived"]),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Carousel Rotation A-17 Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        "",
        "| Variant | Lazy load | OK | Browser cycles | DOM first/last/max | Heap first/last/max | Expr delta | Prop delta | Cleanup |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.get("variants", []):
        browser = row.get("browser", {}) if isinstance(row.get("browser"), dict) else {}
        metrics = row.get("metrics", {}) if isinstance(row.get("metrics"), dict) else {}
        cleanup_row = row.get("cleanup", {}) if isinstance(row.get("cleanup"), dict) else {}
        lines.append(
            "| {variant} | `{lazy}` | `{ok}` | {cycles} | {dom_first}/{dom_last}/{dom_max} | {heap_first}/{heap_last}/{heap_max} | {expr} | {prop} | `{cleanup}` |".format(
                variant=row.get("variant"),
                lazy=str(row.get("lazyLoad")).lower(),
                ok=str(row.get("ok", False)).lower(),
                cycles=browser.get("cyclesObserved"),
                dom_first=browser.get("domFirst"),
                dom_last=browser.get("domLast"),
                dom_max=browser.get("domMax"),
                heap_first=browser.get("heapFirst"),
                heap_last=browser.get("heapLast"),
                heap_max=browser.get("heapMax"),
                expr=metrics.get("primaryExpressionsDelta"),
                prop=metrics.get("primaryPropertyChangesDelta"),
                cleanup=str(cleanup_row.get("rollbackOk") and cleanup_row.get("cleanupRouteAbsent") and cleanup_row.get("cleanupViewsAbsent")).lower(),
            )
        )
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def parse_variants(raw: str) -> List[str]:
    variants = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = [item for item in variants if item not in VARIANTS]
    if invalid:
        raise ValueError(f"Unsupported variants: {', '.join(invalid)}")
    return variants or list(VARIANTS)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_dir = Path(args.out_dir)
    if out_dir.exists() and not args.overwrite:
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    endpoint, token, project = cp.resolve_config(args)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    health_record = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health = cp.response(health_record)
    feature_set = set(health.get("features", [])) if isinstance(health.get("features"), list) else set()
    health_ok = cp.ok(health_record)
    run_slug = slug(args.run_id)
    variants: List[Dict[str, Any]] = []
    selected_variants = parse_variants(args.variants)
    for variant_name in selected_variants:
        variant_dir = out_dir / variant_name
        variant_dir.mkdir(parents=True, exist_ok=True)
        parent_view_path = f"{args.view_path_prefix.rstrip('/')}/{compact(args.run_id)}/Carousel{compact(variant_name)}"
        child_view_path = f"{args.view_path_prefix.rstrip('/')}/{compact(args.run_id)}/CarouselChild{compact(variant_name)}"
        route = build_route(args.route_prefix, run_slug, variant_name)
        package = build_package(
            variant_dir,
            project,
            args.run_id,
            variant_name,
            parent_view_path,
            child_view_path,
            route,
            args.slide_count,
            args.work_labels,
            args.expression_rate_ms,
            args.rotation_delay_ms,
        )
        write_json(variant_dir / "package.json", {key: value for key, value in package.items() if key != "packageBase64"})
        gates: Dict[str, Any] = {}
        backup = ""
        row: Dict[str, Any] = {
            "variant": variant_name,
            "lazyLoad": package["lazyLoad"],
            "route": route,
            "parentViewPath": parent_view_path,
            "childViewPath": child_view_path,
            "package": {key: value for key, value in package.items() if key != "packageBase64"},
        }
        baseline_wait: Dict[str, Any] = {"enabled": False}
        try:
            if args.wait_for_clean_baseline:
                baseline_wait = tab_common.wait_for_clean_baseline(
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
            dry = client.call(
                f"{args.run_id}-{variant_name}-dryRun",
                package_payload("dryRun", f"{args.run_id}-{variant_name}-dryRun", project, package, args),
                timeout=args.timeout_sec,
            )
            write_json(variant_dir / "dry-run.json", cp.response(dry))
            gates["dryRun"] = cp.ok(dry)
            apply = client.call(
                f"{args.run_id}-{variant_name}-apply",
                package_payload("apply", f"{args.run_id}-{variant_name}-apply", project, package, args),
                timeout=args.timeout_sec,
            )
            apply_response = cp.response(apply)
            write_json(variant_dir / "apply.json", apply_response)
            gates["apply"] = cp.ok(apply)
            backup = backup_name(apply_response)
            time.sleep(args.post_apply_settle_sec)
            readback = client.call(
                f"{args.run_id}-{variant_name}-viewRead",
                view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, parent_view_path, args),
            )
            write_json(variant_dir / "readback.json", cp.response(readback))
            gates["viewRead"] = readback_ok(readback, package)
            page = client.call(
                f"{args.run_id}-{variant_name}-pageValidate",
                page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args),
            )
            write_json(variant_dir / "page-validate.json", cp.response(page))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            profile = profile_variant(client, args, project, package, variant_dir / "profile", health, feature_set)
            gates["profile"] = bool(profile.get("ok"))
            row.update(profile)
            row["ok"] = bool(all(gates.values()))
        except Exception as exc:
            row.update({"ok": False, "error": repr(exc)})
        finally:
            cleanup_result = cleanup(client, args, project, package, backup) if backup else {"rollbackOk": False, "cleanupRouteAbsent": False, "cleanupViewsAbsent": False}
            row["cleanup"] = cleanup_result
            row["gates"] = gates
            row["baselineWait"] = baseline_wait
            row["backupName"] = backup
            row["ok"] = bool(row.get("ok") and cleanup_result.get("rollbackOk") and cleanup_result.get("cleanupRouteAbsent") and cleanup_result.get("cleanupViewsAbsent"))
            variants.append(row)
            if args.pause_sec > 0 and variant_name != selected_variants[-1]:
                time.sleep(args.pause_sec)

    comparison = compare_variants(variants)
    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "runnerVersion": health.get("runnerVersion"),
        "stackVersion": health.get("stackVersion"),
        "features": sorted(feature_set),
        "gatewayAlias": args.gateway_alias,
        "project": project,
        "variants": variants,
        "comparison": comparison,
        "slideCount": args.slide_count,
        "workLabels": args.work_labels,
        "cycles": args.cycles,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "interpretation": [
            "This is a controlled A-17 Carousel rotation fixture, not a customer route conclusion.",
            "The button event changes Carousel props.activePane to avoid brittle browser selectors for Carousel arrows or dots.",
            "Compare lazyLoad off versus on for retained DOM/heap and Gateway/session work, but do not treat one fixture pass as a universal Carousel rule.",
            "Use clean-baseline waiting for sequential variants so retained sessions from the prior browser probe do not contaminate the next variant.",
            "Repeat clean-baseline pairs and use customer Carousel child views before making a causal remediation recommendation.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    write_report(out_dir, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint")
    parser.add_argument("--token")
    parser.add_argument("--project")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--variants", default="lazy-load-off,lazy-load-on")
    parser.add_argument("--slide-count", type=int, default=4)
    parser.add_argument("--work-labels", type=int, default=18)
    parser.add_argument("--expression-rate-ms", type=int, default=500)
    parser.add_argument("--rotation-delay-ms", type=int, default=350)
    parser.add_argument("--cycles", type=int, default=12)
    parser.add_argument("--cycle-delay-ms", type=int, default=500)
    parser.add_argument("--route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--metric-name-contains", action="append", default=["Perspective", "perspective"])
    parser.add_argument("--metric-prefix", action="append", default=[])
    parser.add_argument("--max-metrics", type=int, default=40)
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--min-samples", type=int, default=3)
    parser.add_argument("--profile-timeout-sec", type=float, default=90.0)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-node", default="node")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--post-apply-settle-sec", type=float, default=2.0)
    parser.add_argument("--wait-for-clean-baseline", action="store_true")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0)
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0)
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0)
    parser.add_argument("--fail-on-baseline-timeout", action="store_true")
    parser.add_argument("--pause-sec", type=float, default=0.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.slide_count < 2:
        raise SystemExit("--slide-count must be >= 2")
    if args.work_labels < 0:
        raise SystemExit("--work-labels must be >= 0")
    if args.cycles < 1:
        raise SystemExit("--cycles must be >= 1")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.min_samples < 1:
        raise SystemExit("--min-samples must be >= 1")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    parse_variants(args.variants)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)
    summary = run(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
