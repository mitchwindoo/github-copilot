#!/usr/bin/env python3
"""Run guarded Perspective chart count/point-count scaling fixtures."""

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


def profile_run_id(run_id: str, variant: str) -> str:
    base = compact(run_id)[:22].strip("-_") or "run"
    digest = sha256_text(f"{run_id}:{variant}")[:8]
    return f"{base}-{variant[:18]}-{digest}"


def write_json(path: Path, data: Any) -> None:
    common.write_json(path, data)


def read_json(path: Path) -> Dict[str, Any]:
    return common.read_json(path)


def component(
    component_type: str,
    *,
    meta: Dict[str, Any] | None = None,
    props: Dict[str, Any] | None = None,
    position: Dict[str, Any] | None = None,
    children: List[Dict[str, Any]] | None = None,
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


def parse_int_list(raw: str, label: str) -> List[int]:
    values: List[int] = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            value = int(text)
        except ValueError as exc:
            raise ValueError(f"{label} contains a non-integer value: {text!r}") from exc
        if value <= 0:
            raise ValueError(f"{label} values must be positive")
        values.append(value)
    if not values:
        raise ValueError(f"{label} must contain at least one value")
    return sorted(dict.fromkeys(values))


def parse_sizes(args: argparse.Namespace) -> List[Tuple[int, int, int]]:
    if args.sizes.strip():
        sizes: List[Tuple[int, int, int]] = []
        for part in args.sizes.split(","):
            text = part.strip().lower()
            if not text:
                continue
            bits = text.split("x")
            if len(bits) != 3:
                raise ValueError(f"--sizes entries must look like CHARTSxSERIESxPOINTS or GAUGESxAXESxRANGES: {text!r}")
            charts, series, points = (int(bit.strip()) for bit in bits)
            sizes.append((charts, series, points))
    else:
        if args.chart_kind == "gauge":
            if args.series_per_chart == 3:
                args.series_per_chart = 1
            if args.point_counts == "100,500,1000":
                args.point_counts = "2,4,8"
        chart_counts = parse_int_list(args.chart_counts, "--chart-counts")
        point_counts = parse_int_list(args.point_counts, "--point-counts")
        sizes = [(charts, args.series_per_chart, points) for charts in chart_counts for points in point_counts]
    sizes = sorted(dict.fromkeys(sizes), key=lambda item: (item[0], item[2], item[1]))
    if not sizes:
        raise ValueError("No chart sizes selected")
    for charts, series, points in sizes:
        if charts > args.max_charts:
            raise ValueError(f"chart count {charts} exceeds --max-charts {args.max_charts}")
        if args.chart_kind == "gauge":
            if series < 1 or series > args.max_axes_per_gauge:
                raise ValueError(f"gauge axis count {series} must be between 1 and --max-axes-per-gauge {args.max_axes_per_gauge}")
            if points > args.max_ranges_per_axis:
                raise ValueError(f"gauge range count {points} exceeds --max-ranges-per-axis {args.max_ranges_per_axis}")
        else:
            if series > args.max_series_per_chart:
                raise ValueError(f"series count {series} exceeds --max-series-per-chart {args.max_series_per_chart}")
            if points > args.max_points_per_series:
                raise ValueError(f"point count {points} exceeds --max-points-per-series {args.max_points_per_series}")
    return sizes


def variant_label(chart_count: int, series_per_chart: int, points_per_series: int, chart_kind: str = "timeseries") -> str:
    if chart_kind == "gauge":
        return f"gauge-{chart_count:02d}g-{series_per_chart:02d}a-{points_per_series:04d}r"
    if chart_kind == "xy":
        return f"xy-{chart_count:02d}c-{series_per_chart:02d}s-{points_per_series:04d}p"
    return f"chart-{chart_count:02d}c-{series_per_chart:02d}s-{points_per_series:04d}p"


def chart_kind_title(chart_kind: str) -> str:
    if chart_kind == "gauge":
        return "Gauge"
    if chart_kind == "xy":
        return "XY Chart"
    return "Time Series Chart"


def build_route(prefix: str, run_slug: str, variant: str) -> str:
    normalized = prefix.strip() or DEFAULT_ALLOWED_ROUTE_PREFIX
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    suffix = f"{run_slug}-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def make_series(chart_index: int, series_per_chart: int, points_per_series: int) -> List[Dict[str, Any]]:
    base_time = 1700000000000 + chart_index * 86400000
    series_rows: List[Dict[str, Any]] = []
    for series_index in range(series_per_chart):
        data: List[List[float]] = []
        multiplier = chart_index + series_index + 1
        for point_index in range(points_per_series):
            timestamp = base_time + point_index * 1000
            value = ((point_index * multiplier) % 101) + (series_index * 3) + (chart_index * 0.5)
            data.append([timestamp, value])
        series_rows.append({"name": f"chart-{chart_index + 1}-series-{series_index + 1}", "data": data})
    return series_rows


def make_xy_data_sources(chart_index: int, series_per_chart: int, points_per_series: int) -> Dict[str, List[Dict[str, Any]]]:
    source_name = f"source_{chart_index + 1}"
    rows: List[Dict[str, Any]] = []
    for point_index in range(points_per_series):
        row: Dict[str, Any] = {"x": point_index}
        for series_index in range(series_per_chart):
            multiplier = chart_index + series_index + 1
            row[f"value_{series_index + 1:02d}"] = ((point_index * multiplier) % 101) + (series_index * 4) + chart_index
        rows.append(row)
    return {source_name: rows}


def make_xy_series(chart_index: int, series_per_chart: int) -> List[Dict[str, Any]]:
    palette = ["#2563eb", "#16a34a", "#dc2626", "#7c3aed", "#ea580c", "#0891b2"]
    source_name = f"source_{chart_index + 1}"
    series_rows: List[Dict[str, Any]] = []
    for series_index in range(series_per_chart):
        color = palette[series_index % len(palette)]
        series_rows.append(
            {
                "name": f"xy-{chart_index + 1}-series-{series_index + 1}",
                "label": {"text": f"Series {series_index + 1}"},
                "visible": True,
                "data": {"source": source_name, "x": "x", "y": f"value_{series_index + 1:02d}"},
                "xAxis": "x",
                "yAxis": "y",
                "render": "line",
                "line": {
                    "appearance": {
                        "connect": True,
                        "tensionX": 1,
                        "tensionY": 1,
                        "minDistance": 0.5,
                        "stroke": {"width": 2, "opacity": 1, "color": color},
                    },
                    "bullets": [{"enabled": False}],
                },
            }
        )
    return series_rows


def gauge_ranges(range_count: int, max_value: int, width: int) -> List[Dict[str, Any]]:
    palette = ["#22c55e", "#84cc16", "#f59e0b", "#f97316", "#ef4444", "#a855f7"]
    ranges: List[Dict[str, Any]] = []
    low = 0
    for index in range(range_count):
        high = max_value if index == range_count - 1 else int(round((index + 1) * float(max_value) / range_count))
        ranges.append({"start": low, "end": high, "width": width, "color": palette[index % len(palette)]})
        low = high
    return ranges


def gauge_component(chart_index: int, axis_count: int, ranges_per_axis: int) -> Dict[str, Any]:
    value = (chart_index * 17 + 43) % 121
    props: Dict[str, Any] = {
        "value": value,
        "startAngle": 135 if axis_count > 1 else 180,
        "endAngle": 405 if axis_count > 1 else 360,
        "animate": False,
        "outerAxis": {
            "data": "value",
            "show": True,
            "minValue": 0,
            "maxValue": 120,
            "width": 14,
            "color": "#94a3b8",
            "percentRadius": 95,
            "ranges": gauge_ranges(ranges_per_axis, 120, 14),
            "needle": {"origin": 0, "reach": 88, "color": "#111827"},
            "tickMarks": {"color": "#475569", "thickness": 1, "length": 9},
        },
        "style": {
            "backgroundColor": "#ffffff",
            "borderColor": "#cbd5e1",
            "borderRadius": 4,
            "borderStyle": "solid",
            "borderWidth": "1px",
            "color": "#111827",
            "fontSize": 12,
        },
    }
    if axis_count > 1:
        props["secondaryValue"] = (value * 0.65) % 80
        props["innerAxis"] = {
            "data": "secondaryValue",
            "show": True,
            "minValue": 0,
            "maxValue": 80,
            "width": 8,
            "color": "#38bdf8",
            "percentRadius": 72,
            "ranges": gauge_ranges(ranges_per_axis, 80, 8),
            "needle": {"origin": 0, "reach": 68, "color": "#0369a1"},
            "tickMarks": {"color": "#0f766e", "thickness": 1, "length": 6},
        }
    return component(
        "ia.chart.gauge",
        meta={"name": f"Gauge {chart_index + 1}"},
        position={"basis": "240px", "grow": 1, "shrink": 1},
        props=props,
    )


def chart_component(args: argparse.Namespace, chart_index: int, series_per_chart: int, points_per_series: int) -> Dict[str, Any]:
    if args.chart_kind == "gauge":
        return gauge_component(chart_index, series_per_chart, points_per_series)
    if args.chart_kind == "xy":
        return component(
            "ia.chart.xy",
            meta={"name": f"XY Chart {chart_index + 1}"},
            position={"basis": "360px", "grow": 1, "shrink": 1},
            props={
                "dataSources": make_xy_data_sources(chart_index, series_per_chart, points_per_series),
                "title": {"text": f"XY Chart {chart_index + 1}", "appearance": {"font": {"size": 14, "weight": "700"}}},
                "subtitle": {"text": f"{series_per_chart} series x {points_per_series} points"},
                "legend": {"enabled": points_per_series <= 500, "position": "bottom"},
                "enableTransitions": False,
                "xAxes": [
                    {
                        "name": "x",
                        "label": {"enabled": True, "text": "X"},
                        "render": "value",
                        "value": {"range": {"min": 0, "max": max(points_per_series - 1, 1), "useStrict": False}},
                    }
                ],
                "yAxes": [
                    {
                        "name": "y",
                        "label": {"enabled": True, "text": "Value"},
                        "render": "value",
                        "value": {"range": {"min": 0, "max": 130, "useStrict": False}},
                    }
                ],
                "series": make_xy_series(chart_index, series_per_chart),
                "style": {
                    "backgroundColor": "#ffffff",
                    "borderColor": "#cbd5e1",
                    "borderRadius": 4,
                    "borderStyle": "solid",
                    "borderWidth": "1px",
                },
            },
        )
    series = make_series(chart_index, series_per_chart, points_per_series)
    return component(
        "ia.chart.timeseries",
        meta={"name": f"Time Series {chart_index + 1}"},
        position={"basis": "360px", "grow": 1, "shrink": 1},
        props={
            "enablePanZoom": False,
            "autoGenerateSeriesNames": False,
            "series": series,
            "title": {"text": f"Chart {chart_index + 1}", "appearance": {"font": {"size": 14, "weight": "700"}}},
            "subtitle": {"text": f"{series_per_chart} series x {points_per_series} points"},
            "legend": {"enabled": points_per_series <= 500, "position": "bottom"},
            "style": {
                "backgroundColor": "#ffffff",
                "borderColor": "#cbd5e1",
                "borderRadius": 4,
                "borderStyle": "solid",
                "borderWidth": "1px",
            },
        },
    )


def make_view_json(args: argparse.Namespace, chart_count: int, series_per_chart: int, points_per_series: int, variant: str) -> Dict[str, Any]:
    charts = [chart_component(args, index, series_per_chart, points_per_series) for index in range(chart_count)]
    if args.chart_kind == "gauge":
        chart_payload = [
            {
                "value": chart["props"].get("value"),
                "secondaryValue": chart["props"].get("secondaryValue"),
                "outerAxis": chart["props"].get("outerAxis"),
                "innerAxis": chart["props"].get("innerAxis"),
            }
            for chart in charts
        ]
        total_series = chart_count * series_per_chart
        total_points = chart_count * series_per_chart * points_per_series
        scenario_text = (
            f"A-13 gauge scaling fixture: {chart_count} gauges, {series_per_chart} axes per gauge, "
            f"{points_per_series} ranges per axis, {total_points} total ranges"
        )
    elif args.chart_kind == "xy":
        chart_payload = [
            {
                "dataSources": chart["props"]["dataSources"],
                "series": chart["props"]["series"],
                "xAxes": chart["props"]["xAxes"],
                "yAxes": chart["props"]["yAxes"],
            }
            for chart in charts
        ]
        total_series = chart_count * series_per_chart
        total_points = total_series * points_per_series
        scenario_text = (
            f"A-13 XY chart scaling fixture: {chart_count} charts, {series_per_chart} series per chart, "
            f"{points_per_series} points per series, {total_points} total plotted points"
        )
    else:
        chart_payload = [chart["props"]["series"] for chart in charts]
        total_series = chart_count * series_per_chart
        total_points = total_series * points_per_series
        scenario_text = (
            f"A-13 chart scaling fixture: {chart_count} charts, {series_per_chart} series per chart, "
            f"{points_per_series} points per series, {total_points} total points"
        )
    payload_sha = sha256_text(canonical_json(chart_payload))
    ready = f"{args.run_id} {variant.upper()} READY"
    return {
        "custom": {
            "runId": args.run_id,
            "variant": variant,
            "chartKind": args.chart_kind,
            "chartCount": chart_count,
            "seriesPerChart": series_per_chart,
            "pointsPerSeries": points_per_series,
            "totalSeries": total_series,
            "totalPoints": total_points,
            "payloadSha256": payload_sha,
            "seriesSha256": payload_sha,
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 760}},
        "root": component(
            "ia.container.flex",
            meta={"name": "chart-scaling-root"},
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
                    position={"basis": "36px", "grow": 0, "shrink": 0},
                    props={
                        "text": (
                            scenario_text
                        ),
                        "style": {"color": "#1f2937", "fontSize": 13, "padding": "7px 2px", "whiteSpace": "pre-wrap"},
                    },
                ),
                component(
                    "ia.container.flex",
                    meta={"name": "Chart Grid"},
                    position={"basis": "auto", "grow": 1, "shrink": 1},
                    props={
                        "direction": "row",
                        "alignItems": "stretch",
                        "justify": "flex-start",
                        "wrap": "wrap",
                        "style": {"gap": "10px", "overflow": "auto"},
                    },
                    children=charts,
                ),
            ],
        ),
        "permissions": {},
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
    chart_count: int,
    series_per_chart: int,
    points_per_series: int,
    view_path: str,
    route: str,
) -> Dict[str, Any]:
    variant = variant_label(chart_count, series_per_chart, points_per_series, args.chart_kind)
    zip_dir = out_dir / "package"
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = f"perf-profiler-{args.chart_kind}-scaling"
    view_json = make_view_json(args, chart_count, series_per_chart, points_per_series, variant)
    zip_path = zip_dir / "fixture.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-chart-scale-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler chart scaling fixture", "enabled": True, "inheritable": False})
        write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"{chart_kind_title(args.chart_kind)} Scaling {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", table_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    package_base64 = common.zip_file_base64(zip_path)
    return {
        "variant": variant,
        "chartKind": args.chart_kind,
        "chartCount": chart_count,
        "seriesPerChart": series_per_chart,
        "pointsPerSeries": points_per_series,
        "totalSeries": chart_count * series_per_chart,
        "totalPoints": chart_count * series_per_chart * points_per_series,
        "route": route,
        "viewPath": view_path,
        "zipPath": str(zip_path),
        "zipBytes": zip_path.stat().st_size,
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": package_base64,
        "packageBase64Bytes": len(package_base64),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "payloadSha256": view_json["custom"]["payloadSha256"],
        "seriesSha256": view_json["custom"]["seriesSha256"],
        "readyText": f"{args.run_id} {variant.upper()} READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"{str(package.get('chartKind', 'chart')).title()} Scaling {package['variant']}"}],
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
        f"{args.chart_kind} count and payload scaling A-13 fixture",
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


def readback_ok(record: Dict[str, Any], package: Dict[str, Any]) -> bool:
    response_text = canonical_json(cp.response(record))
    expected_types = {"gauge": "ia.chart.gauge", "xy": "ia.chart.xy", "timeseries": "ia.chart.timeseries"}
    expected_type = expected_types.get(str(package.get("chartKind") or "timeseries"), "ia.chart.timeseries")
    return (
        cp.ok(record)
        and f'"chartKind":"{package.get("chartKind", "timeseries")}"' in response_text
        and f'"chartCount":{package["chartCount"]}' in response_text
        and f'"seriesPerChart":{package["seriesPerChart"]}' in response_text
        and f'"pointsPerSeries":{package["pointsPerSeries"]}' in response_text
        and f'"totalPoints":{package["totalPoints"]}' in response_text
        and str(package["readyText"]) in response_text
        and str(package["payloadSha256"]) in response_text
        and f'"type":"{expected_type}"' in response_text
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


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    profile = read_json(profile_dir / "static-profile.json")
    summary = profile.get("summary", {}) if isinstance(profile.get("summary"), dict) else {}
    heavy = profile.get("heavyData", []) if isinstance(profile.get("heavyData"), list) else []
    chart_rows = [
        row
        for row in heavy
        if isinstance(row, dict)
        and row.get("kind") in {"series", "dataSources", "points", "gauge"}
        and any(token in str(row.get("componentType", "")).lower() for token in ("chart", "timeseries", "sparkline", "powerchart", "gauge"))
    ]
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "chartLikeCount": summary.get("chartLikeCount"),
        "viewJsonBytes": summary.get("viewJsonBytes"),
        "chartPayloadRows": len(chart_rows),
        "chartSeriesRows": len([row for row in chart_rows if row.get("kind") == "series"]),
        "chartDataSourceCount": sum(row.get("count", 0) or 0 for row in chart_rows if row.get("kind") == "dataSources"),
        "chartDataSourceRows": sum(row.get("rows", 0) or 0 for row in chart_rows if row.get("kind") == "dataSources"),
        "chartSeriesCount": sum(row.get("count", 0) or 0 for row in chart_rows if row.get("kind") in {"series", "gauge"}),
        "chartPointCount": sum(row.get("points", 0) or 0 for row in chart_rows),
        "gaugeAxisCount": sum(row.get("count", 0) or 0 for row in chart_rows if row.get("kind") == "gauge"),
        "gaugeRangeCount": sum(row.get("points", 0) or 0 for row in chart_rows if row.get("kind") == "gauge"),
        "chartPayloadBytes": sum(row.get("bytes", 0) or 0 for row in chart_rows),
    }


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
        "resourceTransferSizeDelta": delta(browser, "resourceTransferSize"),
    }


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    chart_kind = str(summary.get("chartKind") or "timeseries")
    if chart_kind == "gauge":
        title = "Gauge Scaling Fixture"
        count_label = "Gauges"
        series_label = "Axes"
        points_label = "Ranges"
    elif chart_kind == "xy":
        title = "XY Chart Scaling Fixture"
        count_label = "XY Charts"
        series_label = "Series"
        points_label = "Plotted Points"
    else:
        title = "Chart Scaling Fixture"
        count_label = "Charts"
        series_label = "Series"
        points_label = "Points"
    lines = [
        f"# {title}",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Component kind: `{chart_kind}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        "",
        "## Variant Summary",
        "",
        f"| Variant | OK | {count_label} | {series_label} | {points_label} | View bytes | Payload bytes | DOM | LCP ms | Long task ms | JS heap | WS recv | Cleanup |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("variants", []):
        static = row.get("static", {})
        browser = row.get("browser", {})
        network = row.get("network", {})
        lines.append(
            "| {variant} | `{ok}` | {charts} | {series} | {points} | {view_bytes} | {chart_bytes} | {dom} | {lcp} | {long_task} | {heap} | {ws_recv} | `{cleanup}` |".format(
                variant=row.get("variant"),
                ok=str(row.get("ok", False)).lower(),
                charts=static.get("chartLikeCount"),
                series=static.get("chartSeriesCount"),
                points=static.get("chartPointCount"),
                view_bytes=static.get("viewJsonBytes"),
                chart_bytes=static.get("chartPayloadBytes"),
                dom=browser.get("domNodeCount"),
                lcp=browser.get("largestContentfulPaintMs"),
                long_task=browser.get("longTaskTotalMs"),
                heap=browser.get("usedJSHeapBytes"),
                ws_recv=network.get("webSocketBytesReceived"),
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
    sizes = parse_sizes(args)
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
    base = compact(args.run_id)
    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    compare_records: List[Dict[str, Any]] = []

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    health_response = cp.response(health)
    health_ok = cp.ok(health)
    feature_set = cp.enabled_name_set(health_response.get("features", []))
    action_set = cp.enabled_name_set(health_response.get("supportedActions", []))
    baseline_capability_set = feature_set | action_set if action_set else feature_set

    for chart_count, series_per_chart, points_per_series in sizes:
        variant = variant_label(chart_count, series_per_chart, points_per_series, args.chart_kind)
        variant_dir = out_dir / variant
        route = build_route(args.route_prefix, run_slug, variant)
        view_kind = "Gauge" if args.chart_kind == "gauge" else ("XYChart" if args.chart_kind == "xy" else "Chart")
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/{view_kind}{chart_count:02d}c{series_per_chart:02d}s{points_per_series:04d}p"
        package = build_package(variant_dir, project, args, chart_count, series_per_chart, points_per_series, view_path, route)
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
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
            dry = client.call(f"{args.run_id}-{variant}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant}-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry)
            gate_details["dryRun"] = gate_detail(dry)
            if not gates["dryRun"]:
                raise RuntimeError(gate_failure_message("dryRun", dry))
            apply = client.call(f"{args.run_id}-{variant}-apply", package_payload("apply", f"{args.run_id}-{variant}-apply", project, package, args), timeout=args.timeout_sec)
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
            row = {
                "variant": variant,
                "chartKind": args.chart_kind,
                "chartCount": chart_count,
                "seriesPerChart": series_per_chart,
                "pointsPerSeries": points_per_series,
                "totalSeries": package["totalSeries"],
                "totalPoints": package["totalPoints"],
                "ok": all(gates.values()),
                "gates": gates,
                "gateDetails": gate_details,
                "baselineWait": baseline,
                "route": route,
                "viewPath": view_path,
                "backupName": backup_name,
                "profileDir": str(profile_dir),
                "browser": browser_metrics(profile_dir),
                "gateway": gateway_metrics(profile_dir),
                "network": network_metrics(profile_dir),
                "static": static_summary(profile_dir),
                "metricFamilies": hidden_common.metric_family_samples(profile_dir),
                "profileCommand": profile_result,
            }
            baseline_variant = variant_label(*sizes[0], chart_kind=args.chart_kind)
            baseline_dir = out_dir / baseline_variant / "profile"
            if (chart_count, series_per_chart, points_per_series) != sizes[0] and baseline_dir.exists() and gates["profile"]:
                comparison = compare_to_baseline(out_dir, baseline_dir, profile_dir, variant)
                if comparison.get("ok"):
                    comparison["primary"] = comparison_primary(Path(str(comparison["comparisonDir"])))
                compare_records.append(comparison)
        except Exception as exc:
            row = {
                "variant": variant,
                "chartKind": args.chart_kind,
                "chartCount": chart_count,
                "seriesPerChart": series_per_chart,
                "pointsPerSeries": points_per_series,
                "totalSeries": chart_count * series_per_chart,
                "totalPoints": chart_count * series_per_chart * points_per_series,
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
            if args.pause_sec > 0 and (chart_count, series_per_chart, points_per_series) != sizes[-1]:
                time.sleep(args.pause_sec)

    summary = {
        "ok": bool(health_ok and variants and all(row.get("ok") for row in variants) and all(row.get("ok") for row in compare_records)),
        "runId": args.run_id,
        "chartKind": args.chart_kind,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": health_response.get("runnerVersion"),
        "stackVersion": health_response.get("stackVersion"),
        "sizes": [{"chartKind": args.chart_kind, "chartCount": c, "seriesPerChart": s, "pointsPerSeries": p, "totalPoints": c * s * p} for c, s, p in sizes],
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "healthOk": health_ok,
        "variants": variants,
        "comparisons": compare_records,
        "packages": package_records,
        "interpretation": [
            f"This is a controlled A-13 {args.chart_kind} fixture, not a customer route conclusion.",
            "The fixture keeps the same component family and surrounding view shape while varying component count and payload shape.",
            "Use component count, payload bytes, browser long tasks, heap, transfer/WebSocket bytes, and Gateway/session signals separately.",
            "A single matrix pass characterizes the tested fixture only; repeated clean-baseline evidence is required before claiming a chart-family remediation rule.",
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
    parser.add_argument("--chart-kind", choices=("timeseries", "gauge", "xy"), default="timeseries", help="Fixture component family to generate. Gauge interprets sizes as GAUGESxAXESxRANGES; XY uses CHARTSxSERIESxPOINTS with props.dataSources.")
    parser.add_argument("--sizes", default="", help="Comma-separated CHARTSxSERIESxPOINTS values, or GAUGESxAXESxRANGES with --chart-kind gauge. Overrides --chart-counts/--point-counts.")
    parser.add_argument("--chart-counts", default="1,4,8")
    parser.add_argument("--series-per-chart", type=int, default=3)
    parser.add_argument("--point-counts", default="100,500,1000")
    parser.add_argument("--max-charts", type=int, default=12)
    parser.add_argument("--max-series-per-chart", type=int, default=6)
    parser.add_argument("--max-points-per-series", type=int, default=2000)
    parser.add_argument("--max-axes-per-gauge", type=int, default=2)
    parser.add_argument("--max-ranges-per-axis", type=int, default=12)
    parser.add_argument("--route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
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
    summary = run(args)
    print(json.dumps({"ok": summary.get("ok"), "summaryPath": str(Path(args.out_dir) / "summary.json")}, indent=2, sort_keys=True))
    raise SystemExit(0 if summary.get("ok") else 1)


if __name__ == "__main__":
    main()
