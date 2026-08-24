#!/usr/bin/env python3
"""Run guarded Perspective expression poll-rate scaling fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_hidden_content_ab as hidden_common
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
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


def expression_binding(expression: str) -> Dict[str, Any]:
    return {"binding": {"type": "expr", "config": {"expression": expression}}}


def component(
    component_type: str,
    *,
    meta: Dict[str, Any] | None = None,
    props: Dict[str, Any] | None = None,
    position: Dict[str, Any] | None = None,
    prop_config: Dict[str, Any] | None = None,
    children: List[Dict[str, Any]] | None = None,
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


def make_rate_label(index: int, rate_ms: int) -> Dict[str, Any]:
    return component(
        "ia.display.label",
        meta={"name": f"Poll Workload {index:03d}"},
        position={"basis": "18px", "grow": 0, "shrink": 0},
        props={
            "text": f"poll workload seed {index:03d}",
            "style": {
                "color": "#1f2937",
                "fontSize": 11,
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "whiteSpace": "nowrap",
            },
        },
        prop_config={"props.text": expression_binding(f"now({rate_ms})")},
    )


def make_view_json(run_id: str, rate_ms: int, label_count: int) -> Dict[str, Any]:
    marker = f"{run_id} RATE {rate_ms}MS READY"
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
            position={"basis": "36px", "grow": 0, "shrink": 0},
            props={
                "text": f"A-04 expression poll-rate fixture: {label_count} labels at {rate_ms} ms",
                "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
            },
        ),
        component(
            "ia.container.flex",
            meta={"name": "Poll Workload Container"},
            position={"basis": "auto", "grow": 1, "shrink": 1},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {
                    "backgroundColor": "#f8fafc",
                    "borderColor": "#cbd5e1",
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                    "overflow": "hidden",
                    "padding": "8px",
                },
            },
            children=[make_rate_label(index, rate_ms) for index in range(1, label_count + 1)],
        ),
    ]
    return {
        "custom": {
            "runId": run_id,
            "rateMs": rate_ms,
            "labelCount": label_count,
            "remediationCandidate": "Reduce high-frequency expression polling only when freshness requirements allow it.",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "poll-rate-root"},
            props={
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {"backgroundColor": "#f7fafc", "overflow": "hidden", "padding": "12px"},
            },
            children=children,
        ),
        "permissions": {},
    }


def build_route(prefix: str, run_slug: str, rate_ms: int) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-poll-rate-{rate_ms}ms"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", fixture_common.resource_json(actor, ["view.json"]))


def build_package(out_dir: Path, project: str, run_id: str, rate_ms: int, label_count: int, view_path: str, route: str) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / f"rate-{rate_ms}ms"
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-poll-rate"
    view_json = make_view_json(run_id, rate_ms, label_count)
    zip_path = zip_dir / f"{slug(run_id)}-poll-rate-{rate_ms}ms.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-pollrate-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler poll-rate fixture", "enabled": True, "inheritable": False})
        write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Poll Rate {rate_ms}ms", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "rateMs": rate_ms,
        "labelCount": label_count,
        "viewPath": view_path,
        "route": route,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": f"{run_id} RATE {rate_ms}MS READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Poll Rate {package['rateMs']}ms"}],
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
    return common.view_read_payload(request_id, project, view_path, args)


def rollback_payload(request_id: str, project: str, backup_name: str, view_paths: List[str], dry_run: bool) -> Dict[str, Any]:
    return common.rollback_payload(request_id, project, backup_name, view_paths, dry_run)


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        f"{args.run_id}-poll-rate-{package['rateMs']}ms",
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
        "expression poll-rate scaling fixture",
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
    return hidden_common.profile_ok(profile_dir)


def rate_readback_ok(record: Dict[str, Any], rate_ms: int, label_count: int) -> bool:
    text = canonical_json(cp.response(record))
    return f"now({rate_ms})" in text and text.count('"binding"') >= label_count


def feature_set_from_health(health: Dict[str, Any]) -> set[str]:
    response = cp.response(health)
    capabilities: set[str] = set()
    for key in ("features", "supportedActions"):
        values = response.get(key, [])
        if isinstance(values, dict):
            capabilities.update(str(item) for item, enabled in values.items() if enabled)
        elif isinstance(values, list):
            capabilities.update(str(item) for item in values)
    return capabilities


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def browser_counts_from_query(query: Dict[str, Any]) -> Dict[str, int]:
    sessions = query.get("sessions", [])
    browser_sessions = 0
    browser_pages = 0
    if isinstance(sessions, list):
        for session in sessions:
            if not isinstance(session, dict):
                continue
            if str(session.get("sessionScope", "")).lower() != "browser":
                continue
            browser_sessions += 1
            browser_pages += int(to_float(session.get("activePages")) or 0)
    return {"browserSessions": browser_sessions, "browserPages": browser_pages}


def wait_for_clean_baseline(
    client: cp.RunnerClient,
    out_dir: Path,
    run_id: str,
    project: str,
    rate_ms: int,
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
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"rateMs": rate_ms, "sampledAt": utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-rate-{rate_ms}ms-baselineWait-{attempt:03d}"
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
        counts = browser_counts_from_query(query)
        elapsed = time.time() - started
        row = {
            "rateMs": rate_ms,
            "attempt": attempt,
            "sampledAt": utc_now(),
            "elapsedSeconds": round(elapsed, 3),
            "maxBrowserSessions": max_browser_sessions,
            **counts,
            "ok": query.get("ok") is not False,
            "clean": counts["browserSessions"] <= max_browser_sessions,
        }
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", row)
        rows.append(row)
        if row["clean"]:
            return {
                "enabled": True,
                "ok": True,
                "timedOut": False,
                "sampleCount": len(rows),
                "elapsedSeconds": round(elapsed, 3),
                "maxBrowserSessions": max_browser_sessions,
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
            }
        if elapsed >= timeout_sec:
            return {
                "enabled": True,
                "ok": False,
                "timedOut": True,
                "sampleCount": len(rows),
                "elapsedSeconds": round(elapsed, 3),
                "maxBrowserSessions": max_browser_sessions,
                "finalBrowserSessions": counts["browserSessions"],
                "finalBrowserPages": counts["browserPages"],
            }
        attempt += 1
        time.sleep(max(interval_sec, 0.1))


def compare_to_baseline(out_dir: Path, baseline_dir: Path, target_dir: Path, baseline_rate: int, target_rate: int) -> Dict[str, Any]:
    comparison_dir = out_dir / f"comparison-rate-{target_rate}ms-minus-{baseline_rate}ms"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(baseline_dir), "--target-dir", str(target_dir), "--out-dir", str(comparison_dir)]
    result = common.run_command(cmd, f"compare-rate-{target_rate}ms-minus-{baseline_rate}ms", out_dir, 180)
    return {"ok": bool(result.get("ok")), "comparisonDir": str(comparison_dir), "command": result}


def comparison_primary(comparison_dir: Path) -> Dict[str, Any]:
    data = read_json(comparison_dir / "comparison.json")
    browser = data.get("browserDeltas", {}) if isinstance(data.get("browserDeltas"), dict) else {}
    static = data.get("staticDeltas", {}) if isinstance(data.get("staticDeltas"), dict) else {}
    gateway = data.get("gatewayDeltas", {}) if isinstance(data.get("gatewayDeltas"), dict) else {}

    def delta(bucket: Dict[str, Any], key: str) -> Any:
        row = bucket.get(key)
        return row.get("delta") if isinstance(row, dict) else None

    return {
        "componentCountDelta": delta(static, "componentCount"),
        "bindingCountDelta": delta(static, "bindingCount"),
        "largestContentfulPaintMsDelta": delta(browser, "largestContentfulPaintMs"),
        "longTaskTotalMsDelta": delta(browser, "longTaskTotalMs"),
        "domNodeCountDelta": delta(browser, "domNodeCount"),
        "usedJSHeapBytesDelta": delta(browser, "usedJSHeapBytes"),
        "processCpuLoadAvgDelta": delta(gateway, "processCpuLoad"),
        "heapUsedBytesAvgDelta": delta(gateway, "heapUsedBytes"),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Expression Poll-Rate Scaling Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Evidence grade: `{summary.get('evidenceGrade', 'Observed')}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        "",
        "## Direct Observations",
        "",
        "- The helper applied one disposable fixture per poll rate, read the view back, validated the route, captured a synchronized profile, then rolled the fixture back.",
        "- Each variant keeps the same visible component and binding count; only the expression `now(rate)` cadence changes.",
        "- Cleanup status is recorded per variant so retained disposable route/view resources are visible evidence failures.",
        "",
        "## Variant Summary",
        "",
        "| Rate ms | Baseline | OK | Components | Bindings | DOM | Long task ms | LCP ms | JS heap | CPU median | Cleanup |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        browser = row.get("browser", {})
        static = row.get("static", {})
        gateway = row.get("gateway", {})
        baseline = row.get("baselineWait", {})
        if baseline.get("enabled"):
            baseline_text = "clean" if baseline.get("ok") else "timeout"
            baseline_text += f" ({baseline.get('finalBrowserSessions')})"
        else:
            baseline_text = "not requested"
        lines.append(
            "| {rate} | {baseline} | `{ok}` | {components} | {bindings} | {dom} | {long_task} | {lcp} | {heap} | {cpu} | `{cleanup}` |".format(
                rate=row.get("rateMs"),
                baseline=baseline_text,
                ok=str(row.get("ok", False)).lower(),
                components=static.get("componentCount"),
                bindings=static.get("bindingCount"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                lcp=browser.get("largestContentfulPaintMs"),
                heap=browser.get("usedJSHeapBytes"),
                cpu=gateway.get("processCpuLoadMedian"),
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewAbsent", False)).lower(),
            )
        )
    lines.extend(["", "## Comparisons", ""])
    for row in summary.get("comparisons", []):
        lines.append(f"### {row.get('label')}")
        primary = row.get("primary", {})
        for key, value in primary.items():
            lines.append(f"- `{key}`: `{value}`")
        lines.append("")
    lines.extend(["## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Unproven Limits",
            "",
            "- This fixture is observed local mechanics, not proof of a customer freshness requirement or final diagnosis.",
            "- Single-run Gateway and browser deltas are not proof of a universal poll-rate recommendation.",
            "- Repeat clean-baseline paired runs on the target route before promoting a rate change as causal.",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_manifest(out_dir: Path, summary: Dict[str, Any]) -> None:
    files = ["summary.json", "summary.md", "packages.json", "api/"]
    for row in summary.get("variants", []):
        rate = row.get("rateMs")
        if rate is not None:
            files.append(f"rate-{rate}ms/")
    for row in summary.get("comparisons", []):
        label = row.get("label")
        if label:
            files.append(f"comparison-rate-{label.replace('ms-minus-', 'ms-minus-')}/")
    manifest = {
        "runId": summary.get("runId"),
        "scenario": "expression poll-rate scaling fixture",
        "evidenceGrade": summary.get("evidenceGrade", "Observed"),
        "createdAt": summary.get("createdAt"),
        "project": summary.get("project"),
        "gatewayAlias": summary.get("gatewayAlias"),
        "runnerVersion": summary.get("runnerVersion"),
        "stackVersion": summary.get("stackVersion"),
        "rates": summary.get("rates", []),
        "baselineRateMs": summary.get("baselineRateMs"),
        "variantCount": len(summary.get("variants", [])),
        "comparisonCount": len(summary.get("comparisons", [])),
        "changedResources": [],
        "missingEvidence": [],
        "files": files,
    }
    write_json(out_dir / "manifest.json", manifest)


def parse_rates(raw: str) -> List[int]:
    rates: List[int] = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        rate = int(text)
        if rate < 100:
            raise ValueError("poll rates must be >= 100 ms")
        rates.append(rate)
    return list(dict.fromkeys(rates))


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
    rates = parse_rates(args.rates)
    base = compact(args.run_id)
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    feature_set = feature_set_from_health(health)
    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []

    for rate_ms in rates:
        variant_dir = out_dir / f"rate-{rate_ms}ms"
        route = build_route(args.route_prefix, slug(args.run_id), rate_ms)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/PollRate{rate_ms}ms"
        package = build_package(variant_dir, project, args.run_id, rate_ms, args.label_count, view_path, route)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        backup_name = ""
        gates: Dict[str, bool] = {}
        baseline_wait: Dict[str, Any] = {"enabled": False}
        try:
            if args.wait_for_clean_baseline:
                baseline_wait = wait_for_clean_baseline(
                    client,
                    variant_dir,
                    args.run_id,
                    project,
                    rate_ms,
                    feature_set,
                    args.baseline_max_browser_sessions,
                    args.baseline_wait_timeout_sec,
                    args.baseline_wait_interval_sec,
                )
                write_json(variant_dir / "baseline-wait.json", baseline_wait)
                gates["cleanBaseline"] = bool(baseline_wait.get("ok"))
                if args.fail_on_baseline_timeout and not baseline_wait.get("ok"):
                    raise RuntimeError("clean baseline was not reached before timeout")
            dry = client.call(f"{args.run_id}-rate-{rate_ms}ms-dryRun", package_payload("dryRun", f"{args.run_id}-rate-{rate_ms}ms-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry)
            if not gates["dryRun"]:
                raise RuntimeError("dryRun failed")
            apply = client.call(f"{args.run_id}-rate-{rate_ms}ms-apply", package_payload("apply", f"{args.run_id}-rate-{rate_ms}ms-apply", project, package, args), timeout=args.timeout_sec)
            backup_name = common.backup_name_from_response(cp.response(apply))
            gates["apply"] = cp.ok(apply) and bool(backup_name)
            if not gates["apply"]:
                raise RuntimeError("apply failed")
            time.sleep(2)
            readback = client.call(f"{args.run_id}-rate-{rate_ms}ms-viewRead", view_read_payload(f"{args.run_id}-rate-{rate_ms}ms-viewRead", project, view_path, args))
            gates["viewRead"] = cp.ok(readback) and rate_readback_ok(readback, rate_ms, args.label_count)
            page = client.call(f"{args.run_id}-rate-{rate_ms}ms-pageValidate", page_validate_payload(f"{args.run_id}-rate-{rate_ms}ms-pageValidate", project, package, args))
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            profile_dir = variant_dir / "profile"
            profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), f"profile-rate-{rate_ms}ms", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            variant = {
                "rateMs": rate_ms,
                "ok": all(gates.values()),
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "profileDir": str(profile_dir),
                "browser": hidden_common.browser_metrics(profile_dir),
                "gateway": hidden_common.gateway_metrics(profile_dir),
                "static": hidden_common.static_summary(profile_dir),
                "metricFamilies": hidden_common.metric_family_samples(profile_dir),
                "profileCommand": profile_result,
            }
        except Exception as exc:
            variant = {
                "rateMs": rate_ms,
                "ok": False,
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "baselineWait": baseline_wait,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                rb_dry = client.call(f"{args.run_id}-rate-{rate_ms}ms-rollback-dryRun", rollback_payload(f"{args.run_id}-rate-{rate_ms}ms-rollback-dryRun", project, backup_name, [view_path], True), timeout=args.timeout_sec)
                rb_apply = client.call(f"{args.run_id}-rate-{rate_ms}ms-rollback-apply", rollback_payload(f"{args.run_id}-rate-{rate_ms}ms-rollback-apply", project, backup_name, [view_path], False), timeout=args.timeout_sec)
                time.sleep(2)
                routes_check = client.call(
                    f"{args.run_id}-rate-{rate_ms}ms-post-cleanup-routesList",
                    {"action": "routesList", "requestId": f"{args.run_id}-rate-{rate_ms}ms-post-cleanup-routesList", "targetProject": project, "routePrefix": route, "maxResults": 25},
                )
                routes = cp.response(routes_check).get("routes", [])
                routes_list = routes if isinstance(routes, list) else []
                route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes_list)
                after_read = client.call(f"{args.run_id}-rate-{rate_ms}ms-post-cleanup-viewRead", view_read_payload(f"{args.run_id}-rate-{rate_ms}ms-post-cleanup-viewRead", project, view_path, args))
                variant["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                variant["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                variant["cleanupViewAbsent"] = not cp.ok(after_read)
                variant["ok"] = bool(variant.get("ok") and variant["rollbackOk"] and variant["cleanupRouteAbsent"] and variant["cleanupViewAbsent"])
            variants.append(variant)
            if args.pause_sec > 0 and rate_ms != rates[-1]:
                time.sleep(args.pause_sec)

    baseline_rate = max(rates)
    baseline_profile = next((Path(row["profileDir"]) for row in variants if row.get("rateMs") == baseline_rate and row.get("profileDir")), None)
    comparisons: List[Dict[str, Any]] = []
    if baseline_profile and baseline_profile.exists():
        for row in variants:
            rate_ms = int(row.get("rateMs"))
            if rate_ms == baseline_rate or not row.get("profileDir"):
                continue
            target_profile = Path(str(row["profileDir"]))
            if not target_profile.exists():
                continue
            comparison = compare_to_baseline(out_dir, baseline_profile, target_profile, baseline_rate, rate_ms)
            primary: Dict[str, Any] = {}
            if comparison.get("ok"):
                primary = comparison_primary(Path(str(comparison["comparisonDir"])))
            comparisons.append({"label": f"{rate_ms}ms-minus-{baseline_rate}ms", "rateMs": rate_ms, "baselineRateMs": baseline_rate, "ok": comparison.get("ok"), "comparison": comparison, "primary": primary})

    summary = {
        "ok": bool(cp.ok(health) and variants and all(row.get("ok") for row in variants) and (len(rates) <= 1 or all(row.get("ok") for row in comparisons))),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "scenario": "expression poll-rate scaling fixture",
        "evidenceGrade": "Observed",
        "features": sorted(feature_set),
        "rates": rates,
        "baselineRateMs": baseline_rate,
        "labelCount": args.label_count,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "baselineWaitTimeoutSeconds": args.baseline_wait_timeout_sec if args.wait_for_clean_baseline else None,
        "baselineWaitIntervalSeconds": args.baseline_wait_interval_sec if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparisons": comparisons,
        "packages": package_records,
        "interpretation": [
            "This is a controlled expression poll-rate fixture, not a customer route conclusion.",
            "Each variant keeps the same visible component and binding count; only now(rate) changes.",
            "Use expression/property-change/session queue deltas to quantify refresh cost versus freshness.",
            "Use --wait-for-clean-baseline for rate comparisons so retained browser sessions do not contaminate per-session deltas.",
            "Treat single-run browser and Gateway deltas as observed only; repeat clean-baseline pairs before recommending a rate.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "packages.json", package_records)
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
    parser.add_argument("--rates", default="250,1000,5000")
    parser.add_argument("--label-count", type=int, default=60)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=18.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=360)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=8000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--pause-sec", type=float, default=5.0)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each rate variant, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0, help="Clean-baseline browser-session threshold.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline per rate.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Mark the variant failed before import when the requested clean baseline is not reached.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.label_count < 1:
        raise SystemExit("--label-count must be >= 1")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0:
        raise SystemExit("--baseline-wait-timeout-sec must be >= 0")
    if args.baseline_wait_interval_sec < 0:
        raise SystemExit("--baseline-wait-interval-sec must be >= 0")
    parse_rates(args.rates)
    summary = run(args)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
