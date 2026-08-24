#!/usr/bin/env python3
"""Rank live Perspective routes by static performance triage signals.

This script is read-only. It uses the runner to list routes, read bounded view
JSON, run the local static analyzer, and suggest candidate routes for runtime
profiling. The score is a prioritization hint, not causal evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from collect_profile import (  # noqa: E402
    RunnerClient,
    ensure_profile_function,
    ok,
    resolve_config,
    response,
    slug,
    utc_now,
    write_json,
)


SEVERITY_POINTS = {"high": 45.0, "medium": 18.0, "info": 3.0}


def append_ndjson(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def metric(summary: Dict[str, Any], key: str) -> float:
    value = summary.get(key, 0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def profile_score(profile: Dict[str, Any]) -> float:
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    risk_points = sum(
        SEVERITY_POINTS.get(str(item.get("severity", "")).lower(), 0.0)
        for item in profile.get("riskSignals", [])
        if isinstance(item, dict)
    )
    dependency_count = 0
    dependencies = profile.get("dependencies", {})
    if isinstance(dependencies, dict) and isinstance(dependencies.get("viewDependencies"), list):
        dependency_count = len(dependencies["viewDependencies"])
    return round(
        metric(summary, "componentCount")
        + metric(summary, "bindingCount") * 3.0
        + metric(summary, "embeddedViewCount") * 12.0
        + metric(summary, "flexRepeaterCount") * 15.0
        + metric(summary, "tableLikeCount") * 12.0
        + metric(summary, "chartLikeCount") * 10.0
        + metric(summary, "maxComponentDepth") * 2.0
        + metric(summary, "scriptCount") * 8.0
        + metric(summary, "transformCount") * 8.0
        + metric(summary, "viewJsonBytes") / 1024.0
        + dependency_count * 6.0
        + risk_points,
        3,
    )


def add_summaries(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    keys = [
        "viewJsonBytes",
        "componentCount",
        "bindingCount",
        "maxComponentDepth",
        "eventBlockCount",
        "scriptCount",
        "scriptChars",
        "transformCount",
        "embeddedViewCount",
        "flexRepeaterCount",
        "tableLikeCount",
        "chartLikeCount",
    ]
    total: Dict[str, Any] = {key: 0 for key in keys}
    max_depth = 0
    for row in rows:
        summary = row.get("summary", {}) if isinstance(row.get("summary"), dict) else {}
        for key in keys:
            value = summary.get(key, 0)
            if isinstance(value, (int, float)):
                if key == "maxComponentDepth":
                    max_depth = max(max_depth, int(value))
                else:
                    total[key] += value
    total["maxComponentDepth"] = max_depth
    return total


def aggregate_score(primary: Dict[str, Any], dependencies: List[Dict[str, Any]]) -> float:
    primary_score = profile_score(primary)
    dependency_score = sum(profile_score(item) for item in dependencies) * 0.6
    return round(primary_score + dependency_score, 3)


def route_view_pairs(routes: List[Any], route_prefix: str, max_routes: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in routes:
        if not isinstance(item, dict):
            continue
        page_path = str(item.get("pagePath", "") or "")
        view_path = str(item.get("viewPath", "") or "")
        if route_prefix and not page_path.startswith(route_prefix):
            continue
        if not page_path or not view_path:
            continue
        rows.append({"pagePath": page_path, "viewPath": view_path})
        if max_routes and len(rows) >= max_routes:
            break
    return rows


def static_dependencies(profile: Dict[str, Any]) -> List[str]:
    dependencies = profile.get("dependencies", {})
    if not isinstance(dependencies, dict):
        return []
    rows = dependencies.get("viewDependencies", [])
    found: List[str] = []
    for item in rows if isinstance(rows, list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("dynamic"):
            continue
        view_path = str(item.get("viewPath", "") or "").strip()
        if view_path and "{" not in view_path and "[" not in view_path:
            found.append(view_path)
    return sorted(set(found))


def read_and_profile_view(
    client: RunnerClient,
    profile_view,
    run_id: str,
    project: str,
    view_path: str,
    cache: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    if view_path in cache:
        return cache[view_path]
    record = client.call(
        f"{run_id}-viewRead-{slug(view_path)}",
        {
            "action": "viewRead",
            "requestId": f"{run_id}-viewRead-{slug(view_path)}",
            "targetProject": project,
            "viewPath": view_path,
            "allowedViewPrefix": "",
            "includeViewJson": True,
            "includeResourceJson": True,
        },
    )
    view_response = response(record)
    if not ok(record):
        profile = {
            "ok": False,
            "viewPath": view_path,
            "error": view_response.get("error") or view_response.get("message") or "viewRead failed",
        }
    else:
        profile = profile_view(view_response, view_path)
        profile["viewPath"] = view_path
        profile["viewReadOk"] = True
    cache[view_path] = profile
    return profile


def make_report(path: Path, manifest: Dict[str, Any], ranked: List[Dict[str, Any]]) -> None:
    lines = [
        "# Perspective Route Static Ranking",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Project: `{manifest.get('project', '')}`",
        f"Routes ranked: `{manifest.get('routeCount', 0)}`",
        f"Unique views read: `{manifest.get('uniqueViewCount', 0)}`",
        "",
        "Scores are static triage hints only. Use synchronized Gateway/browser profiling before claiming a cause.",
        "",
        "## Top Routes",
        "",
        "| Rank | Score | Route | View | Components | Bindings | Embedded | Tables | Charts | View JSON bytes | Risk count |",
        "|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for index, row in enumerate(ranked[:20], start=1):
        summary = row.get("aggregateSummary", {})
        lines.append(
            "| {rank} | {score} | `{route}` | `{view}` | {components} | {bindings} | {embedded} | {tables} | {charts} | {bytes} | {risks} |".format(
                rank=index,
                score=row.get("score", 0),
                route=row.get("pagePath", ""),
                view=row.get("viewPath", ""),
                components=summary.get("componentCount", 0),
                bindings=summary.get("bindingCount", 0),
                embedded=summary.get("embeddedViewCount", 0),
                tables=summary.get("tableLikeCount", 0),
                charts=summary.get("chartLikeCount", 0),
                bytes=summary.get("viewJsonBytes", 0),
                risks=row.get("riskSignalCount", 0),
            )
        )
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "Profile one top candidate with `scripts/collect_profile.py --browser-url ...` using a route-specific stable selector or visible text when available.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank Perspective routes by static performance triage signals.")
    parser.add_argument("--endpoint", help="Runner Web Dev endpoint. Env fallback matches collect_profile.py.")
    parser.add_argument("--token", help="Runner token. Env fallback matches collect_profile.py.")
    parser.add_argument("--project", help="Target project. Env fallback matches collect_profile.py.")
    parser.add_argument("--run-id", help="Stable run identifier.")
    parser.add_argument("--out-dir", help="Evidence output directory.")
    parser.add_argument("--timeout-sec", type=int, default=30, help="HTTP timeout. Default: 30.")
    parser.add_argument("--gateway-alias", default="configured-gateway", help="Non-secret Gateway alias for manifest.")
    parser.add_argument("--route-prefix", default="", help="Optional route prefix filter.")
    parser.add_argument("--max-routes", type=int, default=250, help="Maximum route rows to inspect. Default: 250.")
    parser.add_argument("--max-dependency-views", type=int, default=75, help="Maximum static dependency views to read. Default: 75.")
    parser.add_argument("--top", type=int, default=20, help="Number of ranked rows to print. Default: 20.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    endpoint, token, project = resolve_config(args)
    run_id = args.run_id or f"PERFROUTES-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out_dir = Path(args.out_dir) if args.out_dir else Path.cwd() / "perf-route-rankings" / slug(run_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = RunnerClient(endpoint, token, out_dir, args.timeout_sec)
    profile_view = ensure_profile_function()
    profile_cache: Dict[str, Dict[str, Any]] = {}
    dependency_reads = 0

    health_record = client.call(f"{run_id}-health", {"action": "health", "requestId": f"{run_id}-health"})
    projects_record = client.call(f"{run_id}-projectsList", {"action": "projectsList", "requestId": f"{run_id}-projectsList", "maxResults": 100})
    if not project:
        projects = response(projects_record).get("projects", [])
        if projects and isinstance(projects[0], dict):
            project = str(projects[0].get("projectName") or projects[0].get("name") or "")
        elif projects:
            project = str(projects[0])
    if not project:
        raise SystemExit("Target project could not be resolved. Use --project or IGNITION_TARGET_PROJECT.")

    routes_record = client.call(
        f"{run_id}-routesList",
        {"action": "routesList", "requestId": f"{run_id}-routesList", "targetProject": project, "maxResults": max(args.max_routes, 1)},
    )
    routes = route_view_pairs(response(routes_record).get("routes", []), args.route_prefix, max(args.max_routes, 0))

    ranked: List[Dict[str, Any]] = []
    for route in routes:
        primary = read_and_profile_view(client, profile_view, run_id, project, route["viewPath"], profile_cache)
        dependencies: List[Dict[str, Any]] = []
        for dependency in static_dependencies(primary):
            if dependency_reads >= max(args.max_dependency_views, 0):
                break
            if dependency == route["viewPath"]:
                continue
            dependencies.append(read_and_profile_view(client, profile_view, run_id, project, dependency, profile_cache))
            dependency_reads += 1
        profile_rows = [primary] + dependencies
        aggregate = add_summaries(profile_rows)
        risk_count = sum(len(item.get("riskSignals", [])) for item in profile_rows if isinstance(item.get("riskSignals"), list))
        ranked.append(
            {
                "pagePath": route["pagePath"],
                "viewPath": route["viewPath"],
                "score": aggregate_score(primary, dependencies),
                "primaryScore": profile_score(primary),
                "dependencyScore": round(sum(profile_score(item) for item in dependencies) * 0.6, 3),
                "aggregateSummary": aggregate,
                "primarySummary": primary.get("summary", {}),
                "dependencyViews": [item.get("viewPath") for item in dependencies],
                "riskSignalCount": risk_count,
                "topRiskSignals": [
                    signal
                    for item in profile_rows
                    for signal in (item.get("riskSignals", []) if isinstance(item.get("riskSignals"), list) else [])
                ][:10],
                "viewSha256": primary.get("viewSha256"),
                "staticOnly": True,
            }
        )

    ranked = sorted(ranked, key=lambda row: (-float(row.get("score", 0)), row.get("pagePath", "")))
    for view_path, profile in sorted(profile_cache.items()):
        append_ndjson(out_dir / "view-static-profiles.ndjson", {"viewPath": view_path, "profile": profile})

    manifest = {
        "ok": True,
        "runId": run_id,
        "createdAt": utc_now(),
        "gatewayAlias": args.gateway_alias,
        "project": project,
        "runnerVersion": response(health_record).get("runnerVersion"),
        "stackVersion": response(health_record).get("stackVersion"),
        "routePrefix": args.route_prefix,
        "routeCount": len(routes),
        "rankedRouteCount": len(ranked),
        "uniqueViewCount": len(profile_cache),
        "dependencyReads": dependency_reads,
        "changedResources": [],
        "note": "Read-only static triage. Scores prioritize routes for runtime profiling; they do not prove performance causes.",
        "files": ["manifest.json", "summary.json", "route-static-ranking.json", "view-static-profiles.ndjson", "route-static-ranking.md", "raw/"],
    }
    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "route-static-ranking.json", {"ok": True, "rankedRoutes": ranked})
    summary = {
        "ok": True,
        "runId": run_id,
        "project": project,
        "outDir": str(out_dir),
        "routeCount": len(routes),
        "uniqueViewCount": len(profile_cache),
        "topRoutes": ranked[: max(args.top, 0)],
    }
    write_json(out_dir / "summary.json", summary)
    make_report(out_dir / "route-static-ranking.md", manifest, ranked)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
