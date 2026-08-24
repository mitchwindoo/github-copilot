#!/usr/bin/env python3
"""Clone an existing Perspective view into a guarded route and profile it.

Use this when a component shape should come from a real Designer/seed/customer
view instead of a guessed fixture. The source view is read-only; only the cloned
view and temporary route under the configured allowlists are written.
"""

from __future__ import annotations

import argparse
import copy
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
import run_table_ab_remediation as table_common


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


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
    children: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {"type": component_type}
    if meta is not None:
        row["meta"] = meta
    if props is not None:
        row["props"] = props
    if position is not None:
        row["position"] = position
    if children is not None:
        row["children"] = children
    return row


def build_route(prefix: str, run_slug: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + run_slug
    return normalized.rstrip("/") + "/" + run_slug


def walk_components(node: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            component_type = value.get("type")
            if isinstance(component_type, str) and component_type:
                rows.append({"path": path, "type": component_type, "name": ((value.get("meta") or {}).get("name") if isinstance(value.get("meta"), dict) else None)})
            for index, child in enumerate(value.get("children") or []):
                walk(child, f"{path}.children[{index}]")

    walk(node, "root")
    return rows


def find_view_json(response: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("view", "viewJson"):
        value = response.get(key)
        if isinstance(value, dict):
            return value
    raise RuntimeError("viewRead response did not include a view JSON object")


def add_ready_marker(view_json: Dict[str, Any], ready_text: str, source_view: str, source_sha: str) -> Dict[str, Any]:
    clone = copy.deepcopy(view_json)
    clone_custom = clone.get("custom") if isinstance(clone.get("custom"), dict) else {}
    clone_custom = dict(clone_custom)
    clone_custom["perfProfilerClone"] = {"sourceViewPath": source_view, "sourceViewSha256": source_sha}
    clone["custom"] = clone_custom

    marker = component(
        "ia.display.label",
        meta={"name": "Profiler Ready Marker"},
        position={"basis": "38px", "grow": 0, "shrink": 0},
        props={
            "text": ready_text,
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
    )

    root = clone.get("root")
    if isinstance(root, dict):
        children = root.get("children")
        if isinstance(children, list):
            root["children"] = [marker] + children
            return clone
        clone["root"] = component(
            "ia.container.flex",
            meta={"name": "profiler-clone-root"},
            props={"direction": "column", "alignItems": "stretch", "justify": "flex-start", "style": {"overflow": "auto", "padding": "8px"}},
            children=[marker, root],
        )
        return clone

    clone["root"] = component(
        "ia.container.flex",
        meta={"name": "profiler-clone-root"},
        props={"direction": "column", "alignItems": "stretch", "justify": "flex-start", "style": {"overflow": "auto", "padding": "8px"}},
        children=[marker],
    )
    return clone


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", table_common.resource_json(actor, ["view.json"]))


def build_package(out_dir: Path, project: str, args: argparse.Namespace, view_json: Dict[str, Any], clone_view_path: str, route: str, ready_text: str) -> Dict[str, Any]:
    zip_dir = out_dir / "package"
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / "seed-view-clone.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-seed-clone-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler seeded-view clone", "enabled": True, "inheritable": False})
        write_view(project_root, clone_view_path, view_json, f"perf-profiler-seed-clone-{compact(args.run_id)[:20]}")
        write_json(page_dir / "config.json", {"pages": {route: {"title": args.route_title, "viewPath": clone_view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", table_common.resource_json("perf-profiler-seed-clone", ["config.json"]))
        common.make_zip(package_root, zip_path)
    package_base64 = common.zip_file_base64(zip_path)
    return {
        "route": route,
        "viewPath": clone_view_path,
        "zipPath": str(zip_path),
        "zipBytes": zip_path.stat().st_size,
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": package_base64,
        "packageBase64Bytes": len(package_base64),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": ready_text,
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": args.route_title}],
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


def view_read_payload(request_id: str, project: str, view_path: str, allowed_view_prefix: str) -> Dict[str, Any]:
    return {
        "action": "viewRead",
        "requestId": request_id,
        "targetProject": project,
        "viewPath": view_path,
        "allowedViewPrefix": allowed_view_prefix,
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
        f"{compact(args.run_id)[:26]}-profile",
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
        args.scenario,
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


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    profile = read_json(profile_dir / "static-profile.json")
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    heavy = profile.get("heavyData", []) if isinstance(profile.get("heavyData"), list) else []
    component_types = profile.get("componentTypes", []) if isinstance(profile.get("componentTypes"), list) else []
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "chartLikeCount": summary.get("chartLikeCount"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
        "componentTypes": component_types,
        "heavyData": heavy,
    }


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


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    static = summary.get("static", {}) if isinstance(summary.get("static"), dict) else {}
    browser = summary.get("browser", {}) if isinstance(summary.get("browser"), dict) else {}
    network = summary.get("network", {}) if isinstance(summary.get("network"), dict) else {}
    lines = [
        "# Seed View Clone Profile",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Source view: `{summary['sourceViewPath']}`",
        f"Clone view: `{summary.get('cloneViewPath')}`",
        f"Route: `{summary.get('route')}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        "",
        "## Evidence",
        "",
        f"- Runner: `{summary.get('runnerVersion')}` / `{summary.get('stackVersion')}`.",
        f"- Source component count: `{summary.get('sourceComponentCount')}`.",
        f"- Expected component type: `{summary.get('expectedComponentType') or '<none>'}`.",
        f"- Static clone components: `{static.get('componentCount')}`, chart-like: `{static.get('chartLikeCount')}`, view bytes: `{static.get('viewJsonBytes')}`.",
        f"- Browser DOM: `{browser.get('domNodeCount')}`, LCP: `{browser.get('largestContentfulPaintMs')}`, long-task total: `{browser.get('longTaskTotalMs')}`, heap: `{browser.get('usedJSHeapBytes')}`.",
        f"- Network transfer: `{network.get('resourceTransferSize')}`, WebSocket received: `{network.get('webSocketBytesReceived')}`.",
        f"- Cleanup route absent: `{summary.get('cleanupRouteAbsent')}`, clone view absent: `{summary.get('cleanupViewAbsent')}`.",
        "",
        "## Interpretation",
        "",
        "- This profiles a disposable clone of an existing view. It proves clone/import/profile/rollback mechanics for that source shape.",
        "- It does not prove a universal remediation rule or any hidden data-source behavior that the source view did not exercise.",
        "- A browser `body` selector alone is not sufficient render proof; this helper injects and matches a run-specific ready marker in the cloned view.",
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = cp.resolve_config(args)
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory already exists; use --overwrite or choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = cp.RunnerClient(endpoint, token, out_dir / "api", args.timeout_sec)
    env = collect_env(endpoint, token, project)
    run_slug = slug(args.run_id)
    route = build_route(args.route_prefix, run_slug)
    clone_view_path = f"{args.clone_view_prefix.rstrip('/')}/{compact(args.run_id)}"
    ready_text = args.ready_text or f"{args.run_id} SEED CLONE READY"
    gates: Dict[str, bool] = {}
    gate_details: Dict[str, Any] = {}
    backup_name = ""
    row: Dict[str, Any] = {}

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_response = cp.response(health)
    source_read = client.call(
        f"{args.run_id}-source-viewRead",
        view_read_payload(f"{args.run_id}-source-viewRead", project, args.source_view, args.source_allowed_view_prefix),
    )
    gates["sourceViewRead"] = cp.ok(source_read)
    gate_details["sourceViewRead"] = gate_detail(source_read)
    if not gates["sourceViewRead"]:
        raise RuntimeError(gate_failure_message("sourceViewRead", source_read))
    source_response = cp.response(source_read)
    source_view_json = find_view_json(source_response)
    source_sha = str(source_response.get("viewSha256") or sha256_text(canonical_json(source_view_json)))
    source_components = walk_components(source_view_json.get("root") or source_view_json)
    expected_type_present = True
    if args.expected_component_type:
        expected_type_present = any(row.get("type") == args.expected_component_type for row in source_components)
        if not expected_type_present:
            raise RuntimeError(f"Expected component type not found in source view: {args.expected_component_type}")

    clone_json = add_ready_marker(source_view_json, ready_text, args.source_view, source_sha)
    package = build_package(out_dir, project, args, clone_json, clone_view_path, route, ready_text)
    package_record = {key: value for key, value in package.items() if key != "packageBase64"}
    write_json(out_dir / "package.json", package_record)

    try:
        dry = client.call(f"{args.run_id}-dryRun", package_payload("dryRun", f"{args.run_id}-dryRun", project, package, args), timeout=args.timeout_sec)
        gates["dryRun"] = cp.ok(dry)
        gate_details["dryRun"] = gate_detail(dry)
        if not gates["dryRun"]:
            raise RuntimeError(gate_failure_message("dryRun", dry))

        apply = client.call(f"{args.run_id}-apply", package_payload("apply", f"{args.run_id}-apply", project, package, args), timeout=args.timeout_sec)
        backup_name = common.backup_name_from_response(cp.response(apply))
        gates["apply"] = cp.ok(apply) and bool(backup_name)
        gate_details["apply"] = gate_detail(apply)
        if not gates["apply"]:
            raise RuntimeError(gate_failure_message("apply", apply))

        time.sleep(2)
        clone_read = client.call(f"{args.run_id}-clone-viewRead", view_read_payload(f"{args.run_id}-clone-viewRead", project, clone_view_path, args.allowed_view_prefix))
        response_text = canonical_json(cp.response(clone_read))
        gates["cloneViewRead"] = cp.ok(clone_read) and ready_text in response_text and source_sha in response_text
        if args.expected_component_type:
            gates["cloneViewRead"] = gates["cloneViewRead"] and f'"type":"{args.expected_component_type}"' in response_text
        gate_details["cloneViewRead"] = gate_detail(clone_read)
        if not gates["cloneViewRead"]:
            raise RuntimeError(gate_failure_message("cloneViewRead", clone_read))

        page = client.call(f"{args.run_id}-pageValidate", page_validate_payload(f"{args.run_id}-pageValidate", project, package, args))
        gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
        gate_details["pageValidate"] = gate_detail(page)
        if not gates["pageValidate"]:
            raise RuntimeError(gate_failure_message("pageValidate", page))

        browser_url = common.browser_url_from_endpoint(endpoint, project, route)
        profile_dir = out_dir / "profile"
        profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), "profile", out_dir, args.command_timeout_sec, env)
        gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
        if not gates["profile"]:
            raise RuntimeError("profile failed")

        static = static_summary(profile_dir)
        if args.expected_component_type:
            component_rows = static.get("componentTypes", []) if isinstance(static.get("componentTypes"), list) else []
            gates["expectedComponentType"] = any(isinstance(item, dict) and item.get("name") == args.expected_component_type for item in component_rows)
        else:
            gates["expectedComponentType"] = True

        row = {
            "runId": args.run_id,
            "createdAt": common.utc_now(),
            "project": project,
            "gatewayAlias": args.gateway_alias,
            "sourceViewPath": args.source_view,
            "sourceViewSha256": source_sha,
            "sourceComponentCount": len(source_components),
            "expectedComponentType": args.expected_component_type,
            "expectedComponentTypePresentInSource": expected_type_present,
            "cloneViewPath": clone_view_path,
            "route": route,
            "backupName": backup_name,
            "runnerVersion": health_response.get("runnerVersion"),
            "stackVersion": health_response.get("stackVersion"),
            "healthOk": cp.ok(health),
            "gates": gates,
            "gateDetails": gate_details,
            "profileDir": str(profile_dir),
            "profileCommand": profile_result,
            "static": static,
            "browser": browser_metrics(profile_dir),
            "gateway": gateway_metrics(profile_dir),
            "network": network_metrics(profile_dir),
            "package": package_record,
        }
    except Exception as exc:
        row = {
            "runId": args.run_id,
            "createdAt": common.utc_now(),
            "project": project,
            "gatewayAlias": args.gateway_alias,
            "sourceViewPath": args.source_view,
            "sourceViewSha256": source_sha if "source_sha" in locals() else None,
            "sourceComponentCount": len(source_components) if "source_components" in locals() else None,
            "expectedComponentType": args.expected_component_type,
            "cloneViewPath": clone_view_path,
            "route": route,
            "backupName": backup_name,
            "runnerVersion": health_response.get("runnerVersion"),
            "stackVersion": health_response.get("stackVersion"),
            "healthOk": cp.ok(health),
            "gates": gates,
            "gateDetails": gate_details,
            "error": repr(exc),
            "package": package_record if "package_record" in locals() else None,
        }
    finally:
        if backup_name:
            rb_dry = client.call(
                f"{args.run_id}-rollback-dryRun",
                rollback_payload(f"{args.run_id}-rollback-dryRun", project, backup_name, clone_view_path, True),
                timeout=args.timeout_sec,
            )
            rb_apply = client.call(
                f"{args.run_id}-rollback-apply",
                rollback_payload(f"{args.run_id}-rollback-apply", project, backup_name, clone_view_path, False),
                timeout=args.timeout_sec,
            )
            time.sleep(2)
            row["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
            row["rollbackDetails"] = {"dryRun": gate_detail(rb_dry), "apply": gate_detail(rb_apply)}
        else:
            row["rollbackOk"] = None

        routes_check = client.call(
            f"{args.run_id}-post-cleanup-routesList",
            {"action": "routesList", "requestId": f"{args.run_id}-post-cleanup-routesList", "targetProject": project, "routePrefix": route, "maxResults": 25},
        )
        routes = cp.response(routes_check).get("routes", [])
        routes_list = routes if isinstance(routes, list) else []
        row["cleanupRouteAbsent"] = cp.ok(routes_check) and not any(isinstance(item, dict) and item.get("pagePath") == route for item in routes_list)
        after_read = client.call(f"{args.run_id}-post-cleanup-viewRead", view_read_payload(f"{args.run_id}-post-cleanup-viewRead", project, clone_view_path, args.allowed_view_prefix))
        row["cleanupViewAbsent"] = not cp.ok(after_read)
        row["cleanupDetails"] = {"routesList": gate_detail(routes_check), "viewRead": gate_detail(after_read)}
        row["ok"] = bool(
            row.get("healthOk")
            and row.get("gates")
            and all(row["gates"].values())
            and row.get("rollbackOk") is True
            and row.get("cleanupRouteAbsent") is True
            and row.get("cleanupViewAbsent") is True
        )

    write_json(out_dir / "summary.json", row)
    write_report(out_dir, row)
    return row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--source-view", required=True)
    parser.add_argument("--source-allowed-view-prefix", default="Components/")
    parser.add_argument("--expected-component-type", default="")
    parser.add_argument("--clone-view-prefix", default="LLM Tests/PerformanceProfiler/SeedClones")
    parser.add_argument("--route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--route-title", default="Seed View Clone Profile")
    parser.add_argument("--ready-text", default="")
    parser.add_argument("--scenario", default="Seeded Perspective view clone profile")
    parser.add_argument("--profile-duration-sec", type=float, default=8.0)
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
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        summary = run(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": repr(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps({"ok": summary.get("ok"), "summaryPath": str(Path(args.out_dir) / "summary.json")}, indent=2, sort_keys=True))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
