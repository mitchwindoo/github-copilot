#!/usr/bin/env python3
"""Run guarded Perspective Embedded View loading-mode fixtures."""

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


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
MODES = ("with-parent", "after-parent")


def component(component_type: str, *, meta: Optional[Dict[str, Any]] = None, props: Optional[Dict[str, Any]] = None, position: Optional[Dict[str, Any]] = None, children: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    return common.component(component_type, meta=meta, props=props, position=position, children=children)


def write_json(path: Path, data: Any) -> None:
    common.write_json(path, data)


def canonical_json(data: Any) -> str:
    return common.canonical_json(data)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(value: str) -> str:
    return cp.slug(value).lower()


def compact(value: str) -> str:
    return common.compact(value)


def mode_slug(mode: str) -> str:
    return mode.replace("-", "")


def build_route(prefix: str, run_slug: str, mode: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-loading-{mode}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def make_child_view(run_id: str, mode: str, payload_labels: int) -> Dict[str, Any]:
    children: List[Dict[str, Any]] = [
        component(
            "ia.display.label",
            meta={"name": "Child Ready"},
            position={"basis": "40px", "grow": 0, "shrink": 0},
            props={
                "text": f"{run_id} {mode} CHILD READY",
                "style": {
                    "backgroundColor": "#ecfeff",
                    "borderColor": "#0891b2",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "color": "#0f172a",
                    "fontSize": 15,
                    "fontWeight": "700",
                    "padding": "8px 10px",
                    "whiteSpace": "pre-wrap",
                },
            },
        )
    ]
    for index in range(1, payload_labels + 1):
        children.append(
            component(
                "ia.display.label",
                meta={"name": f"Payload {index:03d}"},
                position={"basis": "18px", "grow": 0, "shrink": 0},
                props={
                    "text": f"loading-mode payload {index:03d}",
                    "style": {
                        "color": "#334155",
                        "fontSize": 11,
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                    },
                },
            )
        )
    return {
        "custom": {"runId": run_id, "role": "loading-mode-child", "mode": mode, "payloadLabels": payload_labels},
        "params": {"runId": "", "mode": ""},
        "propConfig": {},
        "props": {"defaultSize": {"width": 960, "height": 900}},
        "root": component(
            "ia.container.flex",
            meta={"name": "loading-mode-child-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {"backgroundColor": "#ffffff", "overflow": "auto", "padding": "8px"},
            },
            children=children,
        ),
        "permissions": {},
    }


def make_parent_view(run_id: str, mode: str, child_view_path: str, payload_labels: int) -> Dict[str, Any]:
    return {
        "custom": {
            "runId": run_id,
            "mode": mode,
            "childViewPath": child_view_path,
            "payloadLabels": payload_labels,
            "childViewSha256": sha256_text(canonical_json(make_child_view(run_id, mode, payload_labels))),
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "loading-mode-parent-root"},
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
                    meta={"name": "Parent Ready"},
                    position={"basis": "42px", "grow": 0, "shrink": 0},
                    props={
                        "text": f"{run_id} {mode} PARENT READY",
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
                    meta={"name": "Mode Summary"},
                    position={"basis": "32px", "grow": 0, "shrink": 0},
                    props={
                        "text": f"Embedded View props.loading.order = {mode}",
                        "style": {"color": "#1f2937", "fontSize": 13, "padding": "7px 2px"},
                    },
                ),
                component(
                    "ia.display.view",
                    meta={"name": "Loading Mode Embedded View"},
                    position={"basis": "auto", "grow": 1, "shrink": 1},
                    props={
                        "path": child_view_path,
                        "params": {"runId": run_id, "mode": mode},
                        "loading": {"order": mode},
                        "style": {
                            "borderColor": "#cbd5e1",
                            "borderRadius": 4,
                            "borderStyle": "solid",
                            "borderWidth": "1px",
                            "marginTop": "6px",
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
    common.make_zip(root, zip_path)


def build_package(out_dir: Path, project: str, run_id: str, mode: str, parent_view_path: str, child_view_path: str, route: str, payload_labels: int) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / mode
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-embedded-loading"
    parent_view = make_parent_view(run_id, mode, child_view_path, payload_labels)
    child_view = make_child_view(run_id, mode, payload_labels)
    zip_path = zip_dir / f"{mode_slug(mode)}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-loading-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler embedded loading-mode fixture", "enabled": True, "inheritable": False})
        write_view(project_root, child_view_path, child_view, actor)
        write_view(project_root, parent_view_path, parent_view, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Embedded Loading {mode}", "viewPath": parent_view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        make_zip(package_root, zip_path)
    return {
        "mode": mode,
        "parentViewPath": parent_view_path,
        "childViewPath": child_view_path,
        "route": route,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "parentViewSha256": sha256_text(canonical_json(parent_view)),
        "childViewSha256": sha256_text(canonical_json(child_view)),
        "parentReadyText": f"{run_id} {mode} PARENT READY",
        "childReadyText": f"{run_id} {mode} CHILD READY",
        "payloadLabels": payload_labels,
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
        "routes": [{"pagePath": package["route"], "viewPath": package["parentViewPath"], "title": f"Embedded Loading {package['mode']}"}],
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
        f"{args.run_id}-loading-{package['mode']}",
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
        "embedded view loading mode fixture",
        "--browser-url",
        browser_url,
        "--browser-url-alias",
        args.browser_url_alias,
        "--browser-ready-selector",
        args.browser_ready_selector,
        "--browser-ready-text",
        package["parentReadyText"],
        "--browser-secondary-ready-text",
        package["childReadyText"],
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


def read_json(path: Path) -> Dict[str, Any]:
    return common.read_json(path)


def profile_ok(profile_dir: Path) -> bool:
    manifest = read_json(profile_dir / "manifest.json")
    browser = read_json(profile_dir / "browser-summary.json")
    return bool(
        manifest.get("changedResources") == []
        and not manifest.get("missingEvidence")
        and browser.get("ok") is True
        and browser.get("ready") is True
        and browser.get("readyTextMatched") is True
        and browser.get("secondaryReadyConfigured") is True
        and browser.get("secondaryReadyTextMatched") is True
        and common.number(browser.get("primaryReadyElapsedBrowserMs")) is not None
        and common.number(browser.get("secondaryReadyElapsedBrowserMs")) is not None
    )


def wait_for_clean_baseline(
    client: cp.RunnerClient,
    out_dir: Path,
    run_id: str,
    project: str,
    mode: str,
    feature_set: set[str],
    max_browser_sessions: int,
    timeout_sec: float,
    interval_sec: float,
) -> Dict[str, Any]:
    started = time.time()
    attempt = 0
    rows: List[Dict[str, Any]] = []
    if "perspectiveSessionsQuery" not in feature_set:
        result = {
            "enabled": True,
            "ok": False,
            "reason": "perspectiveSessionsQuery feature not present",
            "sampleCount": 0,
            "maxBrowserSessions": max_browser_sessions,
        }
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"mode": mode, "sampledAt": common.utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-loading-{mode}-baselineWait-{attempt:03d}"
        query = cp.response(
            client.call(
                request_id,
                {
                    "action": "perspectiveSessionsQuery",
                    "requestId": request_id,
                    "targetProject": project,
                    "maxResults": 50,
                },
            )
        )
        counts = common.browser_counts_from_query(query)
        elapsed = time.time() - started
        row = {
            "mode": mode,
            "attempt": attempt,
            "sampledAt": common.utc_now(),
            "elapsedSeconds": elapsed,
            "browserSessions": counts["browserSessions"],
            "browserPages": counts["browserPages"],
        }
        rows.append(row)
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", row)
        if counts["browserSessions"] <= max_browser_sessions:
            return {
                "enabled": True,
                "ok": True,
                "sampleCount": len(rows),
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
                "maxBrowserSessions": max_browser_sessions,
                "elapsedSeconds": elapsed,
            }
        if elapsed >= timeout_sec:
            return {
                "enabled": True,
                "ok": False,
                "reason": "timeout",
                "sampleCount": len(rows),
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
                "maxBrowserSessions": max_browser_sessions,
                "elapsedSeconds": elapsed,
            }
        attempt += 1
        time.sleep(interval_sec)


def browser_metrics(profile_dir: Path) -> Dict[str, Any]:
    data = common.browser_metrics(profile_dir)
    browser = read_json(profile_dir / "browser-summary.json")
    primary = common.number(browser.get("primaryReadyElapsedBrowserMs"))
    secondary = common.number(browser.get("secondaryReadyElapsedBrowserMs"))
    data.update(
        {
            "primaryReadyElapsedBrowserMs": primary,
            "secondaryReadyElapsedBrowserMs": secondary,
            "readyGapMs": None if primary is None or secondary is None else secondary - primary,
        }
    )
    return data


def loading_order_present(record: Dict[str, Any], mode: str) -> bool:
    response_text = canonical_json(cp.response(record))
    return f'"loading":{{"order":"{mode}"}}' in response_text


def compare_to_baseline(out_dir: Path, baseline_dir: Path, profile_dir: Path, mode: str) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparisons" / f"{mode}-minus-with-parent"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(baseline_dir), "--target-dir", str(profile_dir), "--out-dir", str(comparison_dir)]
    result = common.run_command(cmd, f"compare-{mode}", out_dir, 180)
    return {"mode": mode, "ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}


def parse_modes(raw: str) -> List[str]:
    modes: List[str] = []
    for part in raw.split(","):
        mode = part.strip()
        if not mode:
            continue
        if mode not in MODES:
            raise ValueError(f"Unsupported mode {mode!r}; expected one of {', '.join(MODES)}")
        modes.append(mode)
    return list(dict.fromkeys(modes))


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Embedded View Loading Mode Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Scenario: `{summary.get('scenario', 'embedded view loading mode fixture')}`",
        f"Evidence grade: `{summary.get('evidenceGrade', 'Observed')}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Modes: `{','.join(summary.get('modes', []))}`",
        f"Runner version: `{summary.get('runnerVersion')}`",
        f"Stack version: `{summary.get('stackVersion')}`",
        "",
        "## Direct Observations",
        "",
        "- Each loading-order variant is applied with dry-run/apply, read back for exact `props.loading.order`, browser-profiled to both parent and child ready markers, compared to the first mode when applicable, and rolled back before the next variant.",
        "- Parent-first-ready, child-total-ready, ready gap, browser DOM/heap/timing metrics, Gateway CPU samples, route cleanup, and view cleanup are recorded per variant.",
        "",
        "## Variant Summary",
        "",
        "| Mode | Baseline | OK | Parent ready ms | Child ready ms | Ready gap ms | DOM | Long task ms | LCP ms | JS heap | CPU median | Cleanup |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        browser = row.get("browser", {})
        gateway = row.get("gateway", {})
        baseline = row.get("baselineWait", {})
        if baseline.get("enabled"):
            baseline_text = "clean" if baseline.get("ok") else "timeout"
            baseline_text += f" ({baseline.get('finalBrowserSessions')})"
        else:
            baseline_text = "not requested"
        lines.append(
            "| {mode} | {baseline} | `{ok}` | {parent_ready} | {child_ready} | {gap} | {dom} | {long_task} | {lcp} | {heap} | {cpu} | `{cleanup}` |".format(
                mode=row.get("mode"),
                baseline=baseline_text,
                ok=str(row.get("ok", False)).lower(),
                parent_ready=browser.get("primaryReadyElapsedBrowserMs"),
                child_ready=browser.get("secondaryReadyElapsedBrowserMs"),
                gap=browser.get("readyGapMs"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                lcp=browser.get("largestContentfulPaintMs"),
                heap=browser.get("usedJSHeapBytes"),
                cpu=gateway.get("processCpuLoadMedian"),
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewsAbsent", False)).lower(),
            )
        )
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Unproven Limits",
            "",
            "- This fixture does not establish a universal Embedded View loading-order preference.",
            "- Single-run deltas do not prove a customer remediation; repeat on the target route or customer-like fixture before recommending `with-parent` or `after-parent`.",
            "- Parent and child marker timing separates perceived first render from total child readiness for this fixture only.",
        ]
    )
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_manifest(out_dir: Path, summary: Dict[str, Any]) -> None:
    files = [
        "summary.json",
        "summary.md",
        "packages.json",
        "comparisons.json",
        "api/",
    ]
    if (out_dir / "comparisons").exists():
        files.append("comparisons/")
    for row in summary.get("variants", []):
        mode = row.get("mode")
        if mode:
            files.append(f"loading-{mode}/")
    manifest = {
        "runId": summary.get("runId"),
        "scenario": summary.get("scenario", "embedded view loading mode fixture"),
        "evidenceGrade": summary.get("evidenceGrade", "Observed"),
        "createdAt": summary.get("createdAt"),
        "project": summary.get("project"),
        "gatewayAlias": summary.get("gatewayAlias"),
        "runnerVersion": summary.get("runnerVersion"),
        "stackVersion": summary.get("stackVersion"),
        "modes": summary.get("modes", []),
        "waitForCleanBaseline": summary.get("waitForCleanBaseline"),
        "baselineMaxBrowserSessions": summary.get("baselineMaxBrowserSessions"),
        "variantCount": len(summary.get("variants", [])),
        "comparisonCount": len(summary.get("comparisons", [])),
        "changedResources": [],
        "missingEvidence": [],
        "files": files,
    }
    write_json(out_dir / "manifest.json", manifest)


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
    modes = parse_modes(args.modes)
    base = compact(args.run_id)
    variants: List[Dict[str, Any]] = []
    compare_records: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_ok = cp.ok(health)
    feature_set = common.feature_set_from_health(health)

    for mode in modes:
        variant_label = f"loading-{mode}"
        variant_dir = out_dir / variant_label
        route = build_route(args.route_prefix, slug(args.run_id), mode)
        root = f"{args.view_path_prefix.rstrip('/')}/{base}/Loading{mode_slug(mode)}"
        parent_view_path = f"{root}/Parent"
        child_view_path = f"{root}/Child"
        package = build_package(variant_dir, project, args.run_id, mode, parent_view_path, child_view_path, route, args.payload_labels)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        gates: Dict[str, bool] = {}
        backup_name = ""
        baseline_wait: Dict[str, Any] = {"enabled": False}
        try:
            if args.wait_for_clean_baseline:
                baseline_wait = wait_for_clean_baseline(
                    client,
                    variant_dir,
                    args.run_id,
                    project,
                    mode,
                    feature_set,
                    args.baseline_max_browser_sessions,
                    args.baseline_wait_timeout_sec,
                    args.baseline_wait_interval_sec,
                )
                write_json(variant_dir / "baseline-wait.json", baseline_wait)
                gates["cleanBaseline"] = bool(baseline_wait.get("ok"))
                if args.fail_on_baseline_timeout and not baseline_wait.get("ok"):
                    raise RuntimeError("clean baseline was not reached before timeout")
            dry = client.call(f"{args.run_id}-{variant_label}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant_label}-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry)
            if not gates["dryRun"]:
                raise RuntimeError("dryRun failed")
            apply = client.call(f"{args.run_id}-{variant_label}-apply", package_payload("apply", f"{args.run_id}-{variant_label}-apply", project, package, args), timeout=args.timeout_sec)
            backup_name = common.backup_name_from_response(cp.response(apply))
            gates["apply"] = cp.ok(apply) and bool(backup_name)
            if not gates["apply"]:
                raise RuntimeError("apply failed")
            time.sleep(2)
            parent_read = client.call(f"{args.run_id}-{variant_label}-parent-viewRead", view_read_payload(f"{args.run_id}-{variant_label}-parent-viewRead", project, parent_view_path, args))
            child_read = client.call(f"{args.run_id}-{variant_label}-child-viewRead", view_read_payload(f"{args.run_id}-{variant_label}-child-viewRead", project, child_view_path, args))
            gates["viewRead"] = cp.ok(parent_read) and cp.ok(child_read) and loading_order_present(parent_read, mode)
            page = client.call(f"{args.run_id}-{variant_label}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_label}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = variant_dir / "profile"
            command = profile_command(args, package, project, browser_url, profile_dir)
            profile_result = common.run_command(command, f"profile-{variant_label}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            variant = {
                "mode": mode,
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "parentViewPath": parent_view_path,
                "childViewPath": child_view_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "profileDir": str(profile_dir),
                "browser": browser_metrics(profile_dir),
                "gateway": common.gateway_metrics(profile_dir),
                "static": common.static_metrics(profile_dir),
                "profileCommand": profile_result,
            }
            if modes and mode != modes[0]:
                baseline_dir = out_dir / f"loading-{modes[0]}" / "profile"
                if baseline_dir.exists() and gates["profile"]:
                    compare_records.append(compare_to_baseline(out_dir, baseline_dir, profile_dir, mode))
        except Exception as exc:
            variant = {
                "mode": mode,
                "ok": False,
                "gates": gates,
                "route": route,
                "parentViewPath": parent_view_path,
                "childViewPath": child_view_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                rb_dry = client.call(
                    f"{args.run_id}-{variant_label}-rollback-dryRun",
                    rollback_payload(f"{args.run_id}-{variant_label}-rollback-dryRun", project, backup_name, [parent_view_path, child_view_path], True),
                    timeout=args.timeout_sec,
                )
                rb_apply = client.call(
                    f"{args.run_id}-{variant_label}-rollback-apply",
                    rollback_payload(f"{args.run_id}-{variant_label}-rollback-apply", project, backup_name, [parent_view_path, child_view_path], False),
                    timeout=args.timeout_sec,
                )
                time.sleep(2)
                routes_check = client.call(
                    f"{args.run_id}-{variant_label}-post-cleanup-routesList",
                    {
                        "action": "routesList",
                        "requestId": f"{args.run_id}-{variant_label}-post-cleanup-routesList",
                        "targetProject": project,
                        "routePrefix": route,
                        "maxResults": 25,
                    },
                )
                routes = cp.response(routes_check).get("routes", [])
                routes_list = routes if isinstance(routes, list) else []
                route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes_list)
                parent_after = client.call(f"{args.run_id}-{variant_label}-post-cleanup-parent-viewRead", view_read_payload(f"{args.run_id}-{variant_label}-post-cleanup-parent-viewRead", project, parent_view_path, args))
                child_after = client.call(f"{args.run_id}-{variant_label}-post-cleanup-child-viewRead", view_read_payload(f"{args.run_id}-{variant_label}-post-cleanup-child-viewRead", project, child_view_path, args))
                variant["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                variant["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                variant["cleanupViewsAbsent"] = not cp.ok(parent_after) and not cp.ok(child_after)
                variant["ok"] = bool(variant.get("ok") and variant["rollbackOk"] and variant["cleanupRouteAbsent"] and variant["cleanupViewsAbsent"])
            variants.append(variant)
            if args.pause_sec > 0 and mode != modes[-1]:
                time.sleep(args.pause_sec)

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": common.utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "scenario": "embedded view loading mode fixture",
        "evidenceGrade": "Observed",
        "modes": modes,
        "healthOk": health_ok,
        "features": sorted(feature_set),
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "baselineWaitIntervalSeconds": args.baseline_wait_interval_sec if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparisons": compare_records,
        "packages": package_records,
        "officialSource": "https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-embedded-view",
        "interpretation": [
            "This is a controlled Embedded View loading.order fixture, not a customer route conclusion.",
            "Primary ready measures the parent marker; secondary ready measures the child marker and approximates total ready for this fixture.",
            "Report perceived-first-render and total-load tradeoffs separately; do not declare a universal winner from one fixture.",
            "Each variant is applied through dry-run/apply, profiled, and rolled back before the next variant.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "packages.json", package_records)
    write_json(out_dir / "comparisons.json", compare_records)
    write_report(out_dir, summary)
    write_manifest(out_dir, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--modes", default="with-parent,after-parent")
    parser.add_argument("--payload-labels", type=int, default=120)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=8.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=240)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=5000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--pause-sec", type=float, default=2.0)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each loading-mode variant, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline per mode.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Mark the variant failed before import when the requested clean baseline is not reached.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.payload_labels < 1:
        raise SystemExit("--payload-labels must be >= 1")
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
