#!/usr/bin/env python3
"""Run guarded Perspective Embedded View nesting-depth scaling fixtures."""

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
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"


def component(component_type: str, *, meta: Dict[str, Any] | None = None, props: Dict[str, Any] | None = None, position: Dict[str, Any] | None = None, children: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
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


def build_depth_route(prefix: str, run_slug: str, depth: int) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-depth-{depth:03d}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def make_level_view(run_id: str, depth: int, level: int, next_view_path: str) -> Dict[str, Any]:
    is_leaf = level == depth
    role = "leaf" if is_leaf else "branch"
    children: List[Dict[str, Any]] = [
        component(
            "ia.display.label",
            meta={"name": f"Level {level:03d} Marker"},
            position={"basis": "34px", "grow": 0, "shrink": 0},
            props={
                "text": f"{run_id} DEPTH {depth} LEVEL {level} {role.upper()}",
                "style": {
                    "backgroundColor": "#ffffff",
                    "borderColor": "#64748b",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "color": "#111827",
                    "fontSize": 14,
                    "fontWeight": "700",
                    "padding": "7px 10px",
                    "whiteSpace": "pre-wrap",
                },
            },
        )
    ]
    if is_leaf:
        children.append(
            component(
                "ia.display.label",
                meta={"name": "Leaf Ready"},
                position={"basis": "40px", "grow": 0, "shrink": 0},
                props={
                    "text": f"{run_id} DEPTH {depth} LEAF READY",
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
        )
        for index in range(1, 5):
            children.append(
                component(
                    "ia.display.label",
                    meta={"name": f"Leaf Payload {index}"},
                    position={"basis": "22px", "grow": 0, "shrink": 0},
                    props={"text": f"leaf payload {index}", "style": {"color": "#334155", "fontSize": 12}},
                )
            )
    else:
        children.append(
            component(
                "ia.display.view",
                meta={"name": f"Embedded Level {level + 1:03d}"},
                position={"basis": "auto", "grow": 1, "shrink": 1},
                props={
                    "path": next_view_path,
                    "params": {"runId": run_id, "depth": depth, "level": level + 1},
                    "style": {
                        "borderColor": "#cbd5e1",
                        "borderRadius": 4,
                        "borderStyle": "solid",
                        "borderWidth": "1px",
                        "margin": "6px 0 0 16px",
                        "minHeight": "120px",
                    },
                },
            )
        )
    return {
        "custom": {
            "runId": run_id,
            "variant": f"depth-{depth}",
            "depth": depth,
            "level": level,
            "role": role,
            "nextViewPath": next_view_path,
        },
        "params": {"runId": "", "depth": 0, "level": 0},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": f"depth-level-{level:03d}"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {
                    "backgroundColor": "#f8fafc",
                    "overflow": "auto",
                    "padding": "10px",
                },
            },
            children=children,
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


def view_chain(prefix: str, base: str, depth: int) -> List[str]:
    root = f"{prefix.rstrip('/')}/{base}/Depth{depth:03d}"
    return [f"{root}/Level{level:03d}" for level in range(1, depth + 1)]


def build_package(out_dir: Path, project: str, run_id: str, depth: int, view_paths: List[str], route: str) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / f"depth-{depth:03d}"
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-embedded-depth"
    view_jsons: List[Dict[str, Any]] = []
    for index, view_path in enumerate(view_paths):
        next_view_path = view_paths[index + 1] if index + 1 < len(view_paths) else ""
        view_jsons.append(make_level_view(run_id, depth, index + 1, next_view_path))
    zip_path = zip_dir / f"{slug(run_id)}-depth-{depth:03d}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-depth-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler embedded depth fixture", "enabled": True, "inheritable": False})
        for view_path, view_json in zip(view_paths, view_jsons):
            write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Embedded Depth {depth}", "viewPath": view_paths[0]}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        make_zip(package_root, zip_path)
    return {
        "depth": depth,
        "topViewPath": view_paths[0],
        "dependencyViewPaths": view_paths[1:],
        "viewPaths": view_paths,
        "route": route,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": [sha256_text(canonical_json(item)) for item in view_jsons],
        "totalViewJsonBytes": sum(len(canonical_json(item).encode("utf-8")) for item in view_jsons),
        "readyText": f"{run_id} DEPTH {depth} LEAF READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["topViewPath"], "title": f"Embedded Depth {package['depth']}"}],
        "dependencyViewPaths": package["dependencyViewPaths"],
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
        "expectedViewPath": package["topViewPath"],
        "allowedViewPrefix": args.allowed_view_prefix,
        "allowedRoutePrefix": args.allowed_route_prefix,
        "dependencyViewPaths": package["dependencyViewPaths"],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [],
    }


def view_read_payload(request_id: str, project: str, view_path: str, args: argparse.Namespace) -> Dict[str, Any]:
    return common.view_read_payload(request_id, project, view_path, args)


def rollback_payload(request_id: str, project: str, backup_name: str, view_paths: List[str], dry_run: bool) -> Dict[str, Any]:
    return common.rollback_payload(request_id, project, backup_name, view_paths, dry_run)


def collect_env(endpoint: str, token: str, project: str) -> Dict[str, str]:
    return common.collect_env(endpoint, token, project)


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        f"{args.run_id}-depth-{package['depth']:03d}",
        "--project",
        project,
        "--route",
        package["route"],
        "--view",
        package["topViewPath"],
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
        "embedded view nesting depth scaling fixture",
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
    return common.profile_ok(profile_dir)


def wait_for_clean_baseline(
    client: cp.RunnerClient,
    out_dir: Path,
    run_id: str,
    project: str,
    depth: int,
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
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"depth": depth, "sampledAt": common.utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-depth-{depth:03d}-baselineWait-{attempt:03d}"
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
            "depth": depth,
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


def compare_to_baseline(out_dir: Path, baseline_dir: Path, profile_dir: Path, depth: int) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparisons" / f"depth-{depth:03d}-minus-baseline"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(baseline_dir), "--target-dir", str(profile_dir), "--out-dir", str(comparison_dir)]
    result = common.run_command(cmd, f"compare-depth-{depth:03d}", out_dir, 180)
    return {"depth": depth, "ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}


def parse_depths(raw: str) -> List[int]:
    depths: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value <= 0:
            raise ValueError("depths must be positive")
        depths.append(value)
    return sorted(dict.fromkeys(depths))


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Embedded View Depth Scaling Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Scenario: `{summary.get('scenario', 'embedded view nesting depth scaling fixture')}`",
        f"Evidence grade: `{summary.get('evidenceGrade', 'Observed')}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Depths: `{','.join(str(item) for item in summary.get('depths', []))}`",
        f"Runner version: `{summary.get('runnerVersion')}`",
        f"Stack version: `{summary.get('stackVersion')}`",
        "",
        "## Direct Observations",
        "",
        "- Each depth variant is applied with dry-run/apply, read back, browser-profiled to the leaf ready marker, compared to the depth-one baseline when applicable, and rolled back before the next variant.",
        "- Chain view count, top-level Embedded View count, browser DOM/heap/timing metrics, Gateway CPU samples, route cleanup, and view cleanup are recorded per variant.",
        "",
        "## Variant Summary",
        "",
        "| Depth | Baseline | OK | Chain views | Top embedded | DOM | Long task ms | LCP ms | JS heap | CPU median | Route cleanup | View cleanup |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary.get("variants", []):
        browser = row.get("browser", {})
        gateway = row.get("gateway", {})
        static = row.get("static", {})
        baseline = row.get("baselineWait", {})
        if baseline.get("enabled"):
            baseline_text = "clean" if baseline.get("ok") else "timeout"
            baseline_text += f" ({baseline.get('finalBrowserSessions')})"
        else:
            baseline_text = "not requested"
        lines.append(
            "| {depth} | {baseline} | `{ok}` | {chain} | {embedded} | {dom} | {long_task} | {lcp} | {heap} | {cpu} | `{route_cleanup}` | `{view_cleanup}` |".format(
                depth=row.get("depth"),
                baseline=baseline_text,
                ok=str(row.get("ok", False)).lower(),
                chain=static.get("chainViewCount"),
                embedded=static.get("topEmbeddedViewCount"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                lcp=browser.get("largestContentfulPaintMs"),
                heap=browser.get("usedJSHeapBytes"),
                cpu=gateway.get("processCpuLoadMedian"),
                route_cleanup=str(row.get("cleanupRouteAbsent", False)).lower(),
                view_cleanup=str(row.get("cleanupViewsAbsent", False)).lower(),
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
            "- This fixture does not establish a universal Embedded View nesting-depth limit.",
            "- Single-run deltas do not prove a customer remediation; repeat on the target route or customer-like fixture before recommending a nesting-depth threshold.",
            "- Correct leaf-marker rendering proves the static chain loaded, but it does not prove every customer parameter path or dynamic view path behaves the same way.",
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
        depth = row.get("depth")
        if depth is not None:
            files.append(f"depth-{int(depth):03d}/")
    manifest = {
        "runId": summary.get("runId"),
        "scenario": summary.get("scenario", "embedded view nesting depth scaling fixture"),
        "evidenceGrade": summary.get("evidenceGrade", "Observed"),
        "createdAt": summary.get("createdAt"),
        "project": summary.get("project"),
        "gatewayAlias": summary.get("gatewayAlias"),
        "runnerVersion": summary.get("runnerVersion"),
        "stackVersion": summary.get("stackVersion"),
        "depths": summary.get("depths", []),
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
    env = collect_env(endpoint, token, project)
    depths = parse_depths(args.depths)
    base = compact(args.run_id)
    variants: List[Dict[str, Any]] = []
    compare_records: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_ok = cp.ok(health)
    feature_set = common.feature_set_from_health(health)

    for depth in depths:
        variant_label = f"depth-{depth:03d}"
        variant_dir = out_dir / variant_label
        route = build_depth_route(args.route_prefix, slug(args.run_id), depth)
        paths = view_chain(args.view_path_prefix, base, depth)
        package = build_package(variant_dir, project, args.run_id, depth, paths, route)
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
                    depth,
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
            reads = [
                client.call(f"{args.run_id}-{variant_label}-viewRead-{index:03d}", view_read_payload(f"{args.run_id}-{variant_label}-viewRead-{index:03d}", project, view_path, args))
                for index, view_path in enumerate(paths, start=1)
            ]
            gates["viewRead"] = all(cp.ok(item) for item in reads)
            page = client.call(f"{args.run_id}-{variant_label}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_label}-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = variant_dir / "profile"
            command = profile_command(args, package, project, browser_url, profile_dir)
            profile_result = common.run_command(command, f"profile-{variant_label}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            top_static = common.static_metrics(profile_dir)
            static = {
                "chainViewCount": len(paths),
                "declaredDepth": depth,
                "topComponentCount": top_static.get("componentCount"),
                "topEmbeddedViewCount": top_static.get("embeddedViewCount"),
                "topViewJsonBytes": top_static.get("viewJsonBytes"),
                "totalViewJsonBytes": package["totalViewJsonBytes"],
            }
            variant = {
                "depth": depth,
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "topViewPath": paths[0],
                "viewPaths": paths,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "profileDir": str(profile_dir),
                "browser": common.browser_metrics(profile_dir),
                "gateway": common.gateway_metrics(profile_dir),
                "static": static,
                "profileCommand": profile_result,
            }
            if depths and depth != depths[0]:
                baseline_dir = out_dir / f"depth-{depths[0]:03d}" / "profile"
                if baseline_dir.exists() and gates["profile"]:
                    compare_records.append(compare_to_baseline(out_dir, baseline_dir, profile_dir, depth))
        except Exception as exc:
            variant = {
                "depth": depth,
                "ok": False,
                "gates": gates,
                "route": route,
                "topViewPath": paths[0] if paths else "",
                "viewPaths": paths,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                rb_dry = client.call(
                    f"{args.run_id}-{variant_label}-rollback-dryRun",
                    rollback_payload(f"{args.run_id}-{variant_label}-rollback-dryRun", project, backup_name, paths, True),
                    timeout=args.timeout_sec,
                )
                rb_apply = client.call(
                    f"{args.run_id}-{variant_label}-rollback-apply",
                    rollback_payload(f"{args.run_id}-{variant_label}-rollback-apply", project, backup_name, paths, False),
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
                route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes if isinstance(routes, list))
                post_reads = [
                    client.call(f"{args.run_id}-{variant_label}-post-cleanup-viewRead-{index:03d}", view_read_payload(f"{args.run_id}-{variant_label}-post-cleanup-viewRead-{index:03d}", project, view_path, args))
                    for index, view_path in enumerate(paths, start=1)
                ]
                variant["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                variant["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                variant["cleanupViewsAbsent"] = all(not cp.ok(item) for item in post_reads)
                variant["ok"] = bool(variant.get("ok") and variant["rollbackOk"] and variant["cleanupRouteAbsent"] and variant["cleanupViewsAbsent"])
            variants.append(variant)
            if args.pause_sec > 0 and depth != depths[-1]:
                time.sleep(args.pause_sec)

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": common.utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "scenario": "embedded view nesting depth scaling fixture",
        "evidenceGrade": "Observed",
        "depths": depths,
        "healthOk": health_ok,
        "features": sorted(feature_set),
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "baselineWaitIntervalSeconds": args.baseline_wait_interval_sec if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparisons": compare_records,
        "packages": package_records,
        "interpretation": [
            "This is a controlled Embedded View nesting-depth scaling fixture, not a customer route conclusion.",
            "The browser waits for the leaf ready marker, so ready evidence requires the full static nested chain to render.",
            "Rising ready time, DOM, long-task, heap, or Gateway/session metrics across depths indicates nesting behavior to investigate; it is not a universal platform limit.",
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
    parser.add_argument("--depths", default="1,2,4,6")
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
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each depth variant, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline per depth.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Mark the variant failed before import when the requested clean baseline is not reached.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
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
