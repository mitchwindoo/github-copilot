#!/usr/bin/env python3
"""Run guarded Perspective hidden-content versus removed-content fixtures."""

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
VARIANTS = ("hidden", "removed")
OFFICIAL_SOURCE = "https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/perspective-component-properties"


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
    custom: Optional[Dict[str, Any]] = None,
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
    if custom is not None:
        row["custom"] = custom
    if prop_config is not None:
        row["propConfig"] = prop_config
    if children is not None:
        row["children"] = children
    return row


def expression_binding(expression: str) -> Dict[str, Any]:
    return {"binding": {"type": "expr", "config": {"expression": expression}}}


def make_workload_label(index: int, expression_rate_ms: int) -> Dict[str, Any]:
    expression = f"now({expression_rate_ms})"
    return component(
        "ia.display.label",
        meta={"name": f"Hidden Workload {index:03d}"},
        position={"basis": "18px", "grow": 0, "shrink": 0},
        props={
            "text": f"hidden workload seed {index:03d}",
            "style": {
                "color": "#334155",
                "fontSize": 11,
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "whiteSpace": "nowrap",
            },
        },
        prop_config={"props.text": expression_binding(expression)},
    )


def make_view_json(run_id: str, variant: str, hidden_labels: int, expression_rate_ms: int) -> Dict[str, Any]:
    if variant not in VARIANTS:
        raise ValueError(f"Unsupported variant: {variant}")
    marker = f"{run_id} {variant.upper()} READY"
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
                "text": f"A-16 hidden-content fixture: variant {variant}, labels {hidden_labels}, expression rate {expression_rate_ms} ms",
                "style": {"color": "#1f2937", "fontSize": 13, "padding": "8px 2px", "whiteSpace": "pre-wrap"},
            },
        ),
    ]
    if variant == "hidden":
        children.append(
            component(
                "ia.container.flex",
                meta={"name": "Hidden Workload Container", "visible": False},
                position={"basis": "0px", "grow": 0, "shrink": 0},
                props={
                    "direction": "column",
                    "alignItems": "stretch",
                    "justify": "flex-start",
                    "wrap": "nowrap",
                    "style": {
                        "backgroundColor": "#fef2f2",
                        "borderColor": "#ef4444",
                        "borderStyle": "solid",
                        "borderWidth": "1px",
                        "height": 0,
                        "overflow": "hidden",
                    },
                },
                children=[make_workload_label(index, expression_rate_ms) for index in range(1, hidden_labels + 1)],
            )
        )
    else:
        children.append(
            component(
                "ia.display.label",
                meta={"name": "Removed Workload Marker"},
                position={"basis": "32px", "grow": 0, "shrink": 0},
                props={
                    "text": "Hidden workload subtree removed for this variant.",
                    "style": {"color": "#475569", "fontSize": 12, "padding": "7px 2px", "whiteSpace": "pre-wrap"},
                },
            )
        )
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "hiddenLabels": hidden_labels if variant == "hidden" else 0,
            "expressionRateMs": expression_rate_ms if variant == "hidden" else None,
            "expectedHiddenContent": variant == "hidden",
            "remediationCandidate": "Remove hidden component subtrees instead of relying on visibility alone when runtime work persists.",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": component(
            "ia.container.flex",
            meta={"name": "hidden-content-root"},
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
    suffix = f"{run_slug}-hidden-content-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def write_view(project_root: Path, view_path: str, view_json: Dict[str, Any], actor: str) -> None:
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    view_dir.mkdir(parents=True, exist_ok=True)
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", fixture_common.resource_json(actor, ["view.json"]))


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    view_path: str,
    route: str,
    hidden_labels: int,
    expression_rate_ms: int,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-hidden-content"
    view_json = make_view_json(run_id, variant, hidden_labels, expression_rate_ms)
    zip_path = zip_dir / f"{slug(run_id)}-hidden-content-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-hidden-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler hidden-content fixture", "enabled": True, "inheritable": False})
        write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Hidden Content {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "viewPath": view_path,
        "route": route,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "readyText": f"{run_id} {variant.upper()} READY",
        "hiddenLabels": hidden_labels if variant == "hidden" else 0,
        "expressionRateMs": expression_rate_ms if variant == "hidden" else None,
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Hidden Content {package['variant']}"}],
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
        f"{args.run_id}-hidden-content-{package['variant']}",
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
        "hidden content versus removed content fixture",
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


def feature_set_from_health(health: Dict[str, Any]) -> set[str]:
    features = cp.response(health).get("features", [])
    if isinstance(features, dict):
        return {str(key) for key, value in features.items() if value}
    if isinstance(features, list):
        return {str(item) for item in features}
    return set()


def to_float(value: Any) -> Optional[float]:
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
    variant: str,
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
        cp.append_ndjson(out_dir / "baseline-wait-samples.ndjson", {"variant": variant, "sampledAt": utc_now(), **result})
        return result
    while True:
        request_id = f"{run_id}-{variant}-baselineWait-{attempt:03d}"
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
            "variant": variant,
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


def variant_readback_ok(record: Dict[str, Any], variant: str) -> bool:
    text = canonical_json(cp.response(record))
    if variant == "hidden":
        return '"visible":false' in text and '"binding"' in text and "Hidden Workload" in text
    return '"visible":false' not in text and "Hidden Workload" not in text


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    profile = read_json(profile_dir / "static-profile.json")
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    hidden = profile.get("hiddenContent", []) if isinstance(profile.get("hiddenContent"), list) else []
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "scriptCount": summary.get("scriptCount"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
        "hiddenContentCount": len(hidden),
    }


def browser_metrics(profile_dir: Path) -> Dict[str, Any]:
    return common.browser_metrics(profile_dir)


def gateway_metrics(profile_dir: Path) -> Dict[str, Any]:
    return common.gateway_metrics(profile_dir)


def metric_family_samples(profile_dir: Path) -> Dict[str, Any]:
    samples_path = profile_dir / "gateway-samples.ndjson"
    families = ("bindings", "expressions", "property-changes", "scripts", "fetches", "messages-sent", "queue-tasks")
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
                value = common.first_number(metric.get("count"), metric.get("value"))
                if value is None:
                    continue
                bucket = result[family].setdefault(name, {"name": name, "first": None, "last": None, "delta": None, "maxOneMinuteRate": None})
                if bucket["first"] is None:
                    bucket["first"] = value
                bucket["last"] = value
                rate = common.number(metric.get("oneMinuteRate"))
                if rate is not None:
                    current = bucket.get("maxOneMinuteRate")
                    bucket["maxOneMinuteRate"] = rate if current is None else max(float(current), rate)
    compacted: Dict[str, Any] = {}
    for family, by_name in result.items():
        rows = []
        for bucket in by_name.values():
            first = common.number(bucket.get("first"))
            last = common.number(bucket.get("last"))
            bucket["delta"] = None if first is None or last is None else last - first
            rows.append(bucket)
        rows.sort(key=lambda row: str(row.get("name")))
        compacted[family] = rows
    return compacted


def compare_to_baseline(out_dir: Path, hidden_dir: Path, removed_dir: Path) -> Dict[str, Any]:
    comparison_dir = out_dir / "comparison-removed-minus-hidden"
    cmd = [sys.executable, str(COMPARE_SCRIPT), "--control-dir", str(hidden_dir), "--target-dir", str(removed_dir), "--out-dir", str(comparison_dir)]
    result = common.run_command(cmd, "compare-removed-minus-hidden", out_dir, 180)
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
        "# Hidden Content A/B Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Scenario: `{summary.get('scenario', 'hidden content ab fixture')}`",
        f"Evidence grade: `{summary.get('evidenceGrade', 'Observed')}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner version: `{summary.get('runnerVersion')}`",
        f"Stack version: `{summary.get('stackVersion')}`",
        "",
        "## Direct Observations",
        "",
        "- Each variant is applied with dry-run/apply, read back, browser-profiled, compared, and rolled back with route/view cleanup verification.",
        "- Static hidden-content and binding deltas are recorded separately from browser DOM/heap/timing and Gateway CPU evidence.",
        "",
        "## Variant Summary",
        "",
        "| Variant | Baseline | OK | Components | Bindings | Hidden flags | DOM | Long task ms | LCP ms | JS heap | CPU median | Cleanup |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
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
            "| {variant} | {baseline} | `{ok}` | {components} | {bindings} | {hidden} | {dom} | {long_task} | {lcp} | {heap} | {cpu} | `{cleanup}` |".format(
                variant=row.get("variant"),
                baseline=baseline_text,
                ok=str(row.get("ok", False)).lower(),
                components=static.get("componentCount"),
                bindings=static.get("bindingCount"),
                hidden=static.get("hiddenContentCount"),
                dom=browser.get("domNodeCount"),
                long_task=browser.get("longTaskTotalMs"),
                lcp=browser.get("largestContentfulPaintMs"),
                heap=browser.get("usedJSHeapBytes"),
                cpu=gateway.get("processCpuLoadMedian"),
                cleanup=str(row.get("cleanupRouteAbsent", False) and row.get("cleanupViewAbsent", False)).lower(),
            )
        )
    lines.extend(["", "## Removed Minus Hidden Deltas", ""])
    for key, value in summary.get("comparisonPrimary", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Unproven Limits",
            "",
            "- This fixture does not prove invisible components are always active or always costly.",
            "- This fixture does not prove a customer remediation unless repeated on the target design with the same workflow, data shape, session baseline, and functional checks.",
            "- If runtime metrics are noisy or mixed, report hidden-content removal as a candidate to test rather than a proven fix.",
        ]
    )
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_manifest(out_dir: Path, summary: Dict[str, Any]) -> None:
    files = [
        "summary.json",
        "summary.md",
        "packages.json",
        "api/",
    ]
    if (out_dir / "comparison-removed-minus-hidden").exists():
        files.append("comparison-removed-minus-hidden/")
    if (out_dir / "baseline-wait-samples.ndjson").exists():
        files.append("baseline-wait-samples.ndjson")
    for row in summary.get("variants", []):
        variant = row.get("variant")
        if variant:
            files.append(f"{variant}/")
    manifest = {
        "runId": summary.get("runId"),
        "scenario": summary.get("scenario", "hidden content ab fixture"),
        "evidenceGrade": summary.get("evidenceGrade", "Observed"),
        "createdAt": summary.get("createdAt"),
        "project": summary.get("project"),
        "gatewayAlias": summary.get("gatewayAlias"),
        "runnerVersion": summary.get("runnerVersion"),
        "stackVersion": summary.get("stackVersion"),
        "variants": [row.get("variant") for row in summary.get("variants", [])],
        "waitForCleanBaseline": summary.get("waitForCleanBaseline"),
        "baselineMaxBrowserSessions": summary.get("baselineMaxBrowserSessions"),
        "changedResources": summary.get("changedResources", []),
        "missingEvidence": summary.get("missingEvidence", []),
        "files": files,
    }
    write_json(out_dir / "manifest.json", manifest)


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
    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    write_json(out_dir / "baseline-health.json", cp.response(health))
    health_ok = cp.ok(health)
    feature_set = feature_set_from_health(health)
    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []

    for variant_name in variants_to_run:
        variant_dir = out_dir / variant_name
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/HiddenContent{variant_name.title()}"
        package = build_package(variant_dir, project, args.run_id, variant_name, view_path, route, args.hidden_labels, args.expression_rate_ms)
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
            time.sleep(2)
            readback = client.call(f"{args.run_id}-{variant_name}-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, view_path, args))
            gates["viewRead"] = cp.ok(readback) and variant_readback_ok(readback, variant_name)
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
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "profileDir": str(profile_dir),
                "browser": browser_metrics(profile_dir),
                "gateway": gateway_metrics(profile_dir),
                "static": static_summary(profile_dir),
                "metricFamilies": metric_family_samples(profile_dir),
                "profileCommand": profile_result,
                "baselineWait": baseline_wait,
            }
        except Exception as exc:
            variant = {
                "variant": variant_name,
                "ok": False,
                "gates": gates,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "error": repr(exc),
                "baselineWait": baseline_wait,
            }
        finally:
            if backup_name:
                rb_dry = client.call(
                    f"{args.run_id}-{variant_name}-rollback-dryRun",
                    rollback_payload(f"{args.run_id}-{variant_name}-rollback-dryRun", project, backup_name, [view_path], True),
                    timeout=args.timeout_sec,
                )
                rb_apply = client.call(
                    f"{args.run_id}-{variant_name}-rollback-apply",
                    rollback_payload(f"{args.run_id}-{variant_name}-rollback-apply", project, backup_name, [view_path], False),
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
                after_read = client.call(f"{args.run_id}-{variant_name}-post-cleanup-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-post-cleanup-viewRead", project, view_path, args))
                variant["rollbackOk"] = cp.ok(rb_dry) and cp.ok(rb_apply)
                variant["cleanupRouteAbsent"] = cp.ok(routes_check) and not route_still_present
                variant["cleanupViewAbsent"] = not cp.ok(after_read)
                variant["ok"] = bool(variant.get("ok") and variant["rollbackOk"] and variant["cleanupRouteAbsent"] and variant["cleanupViewAbsent"])
            variants.append(variant)
            if args.pause_sec > 0 and variant_name != variants_to_run[-1]:
                time.sleep(args.pause_sec)

    comparison: Dict[str, Any] = {"ok": False, "reason": "hidden and removed profiles were not both available"}
    comparison_primary_data: Dict[str, Any] = {}
    hidden_profile = next((Path(row["profileDir"]) for row in variants if row.get("variant") == "hidden" and row.get("profileDir")), None)
    removed_profile = next((Path(row["profileDir"]) for row in variants if row.get("variant") == "removed" and row.get("profileDir")), None)
    if hidden_profile and removed_profile and hidden_profile.exists() and removed_profile.exists():
        comparison = compare_to_baseline(out_dir, hidden_profile, removed_profile)
        if comparison.get("ok"):
            comparison_primary_data = comparison_primary(Path(str(comparison["comparisonDir"])))

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants) and comparison.get("ok")),
        "runId": args.run_id,
        "scenario": "hidden-content-ab-fixture",
        "evidenceGrade": "Observed",
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "waitForCleanBaseline": bool(args.wait_for_clean_baseline),
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "variants": variants,
        "comparison": comparison,
        "comparisonPrimary": comparison_primary_data,
        "packages": package_records,
        "changedResources": [],
        "missingEvidence": [],
        "officialSource": OFFICIAL_SOURCE,
        "interpretation": [
            "This is a controlled static hidden-subtree versus removed-subtree fixture, not a customer route conclusion.",
            "The hidden variant uses Perspective meta.visible false because component visibility is a Meta property in the official component-properties documentation.",
            "Static hidden content and binding counts are hypotheses; runtime metrics and browser evidence decide whether hidden content has material cost in the tested design.",
            "Each variant is applied through dry-run/apply, profiled, and rolled back with route/view cleanup verification.",
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
    parser.add_argument("--variants", default="hidden,removed")
    parser.add_argument("--hidden-labels", type=int, default=120)
    parser.add_argument("--expression-rate-ms", type=int, default=250)
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--profile-duration-sec", type=float, default=12.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=300)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=8000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--pause-sec", type=float, default=5.0)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each variant, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=2, help="Maximum browser sessions allowed before proceeding when clean-baseline waiting is enabled.")
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0, help="Maximum seconds to wait for a clean baseline per variant.")
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0, help="Seconds between clean-baseline samples.")
    parser.add_argument("--fail-on-baseline-timeout", action="store_true", help="Fail the run if clean-baseline waiting times out.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.hidden_labels < 1:
        raise SystemExit("--hidden-labels must be >= 1")
    if args.expression_rate_ms < 100:
        raise SystemExit("--expression-rate-ms must be >= 100")
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
