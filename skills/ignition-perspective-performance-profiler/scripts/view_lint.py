#!/usr/bin/env python3
"""Offline Perspective view performance analyzer.

The analyzer accepts a Perspective view.json file, a runner viewRead response,
or JSON from stdin. It reports static risk candidates only; runtime evidence is
still required before claiming a performance cause.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple


BINDING_RATE_KEYS = {
    "pollrate",
    "pollingrate",
    "refreshrate",
    "refreshinterval",
    "interval",
    "intervalmillis",
    "rate",
}

SCRIPT_PATTERNS = [
    ("loop", re.compile(r"\b(for|while)\b")),
    ("blocking-sleep", re.compile(r"\b(system\.util\.sleep|time\.sleep)\b", re.I)),
    ("tag-read-write", re.compile(r"\bsystem\.tag\.(read|write|configure|browse)", re.I)),
    ("db-call", re.compile(r"\bsystem\.db\.", re.I)),
    ("net-call", re.compile(r"\bsystem\.net\.", re.I)),
    ("json-work", re.compile(r"\b(jsonEncode|jsonDecode|system\.util\.json)", re.I)),
    ("async-call", re.compile(r"\bsystem\.util\.invokeAsynchronous\b", re.I)),
]

EXPR_RATE_PATTERNS = [
    ("now-rate", re.compile(r"\bnow\s*\(\s*(\d+)\s*\)", re.I)),
    ("runScript-rate", re.compile(r"\brunScript\s*\([^)]*,\s*(\d+)\s*\)", re.I)),
]

VIEW_KEYS = ("view", "viewJson", "viewResource", "resource", "resourceJson", "root", "definition")
VIEW_PATH_KEYS = {"path", "viewpath", "view", "viewname"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_json(args: argparse.Namespace) -> Tuple[str, Any]:
    if args.stdin:
        raw = sys.stdin.read()
        source = "<stdin>"
    else:
        if not args.path:
            raise SystemExit("Provide a view JSON path or use --stdin.")
        source = args.path
        with open(args.path, "r", encoding="utf-8-sig") as handle:
            raw = handle.read()
    return source, json.loads(raw)


def extract_view_payload(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    for key in VIEW_KEYS:
        child = data.get(key)
        if isinstance(child, (dict, list)):
            return child
    text = data.get("text") or data.get("jsonText")
    if isinstance(text, str):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, (dict, list)):
                return parsed
        except Exception:
            pass
    return data


def is_component(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("type"), str)
        and ("props" in value or "children" in value or "custom" in value or "meta" in value)
    )


def binding_type(binding: Any) -> str:
    if isinstance(binding, dict):
        return str(
            binding.get("type")
            or binding.get("bindingType")
            or binding.get("mode")
            or binding.get("binding")
            or "unknown"
        )
    if binding is None:
        return "unknown"
    return type(binding).__name__


def tag_binding_mode(binding: Any) -> str | None:
    if not isinstance(binding, dict):
        return None
    btype = binding_type(binding).lower()
    if "tag" not in btype:
        return None
    config = binding.get("config") if isinstance(binding.get("config"), dict) else {}
    explicit = str(config.get("mode") or config.get("tagPathType") or binding.get("mode") or "").lower()
    if explicit in {"direct", "indirect", "expression"}:
        return explicit
    expression = config.get("expression") or binding.get("expression")
    if isinstance(expression, str) and expression.strip():
        return "expression"
    path_value = (
        config.get("tagPath")
        or config.get("path")
        or config.get("tag")
        or binding.get("tagPath")
        or binding.get("path")
    )
    if isinstance(path_value, str):
        return "indirect" if "{" in path_value or "}" in path_value else "direct"
    if isinstance(path_value, list):
        return "indirect" if any(isinstance(item, str) and ("{" in item or "}" in item) for item in path_value) else "direct"
    return "unknown"


def compact_value(value: Any, max_len: int = 160) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = str(value)
    else:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def find_first_string(value: Any, keys: Iterable[str]) -> str | None:
    if not isinstance(value, dict):
        return None
    lowered = {str(k).lower(): v for k, v in value.items()}
    for key in keys:
        found = lowered.get(key.lower())
        if isinstance(found, str) and found.strip():
            return found
    return None


def nested_find_rate(value: Any, path: str, rows: List[Dict[str, Any]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            child_path = f"{path}.{key}"
            if lowered in BINDING_RATE_KEYS and isinstance(child, (int, float, str)):
                rows.append({"path": child_path, "key": str(key), "value": compact_value(child)})
            nested_find_rate(child, child_path, rows)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            nested_find_rate(child, f"{path}[{index}]", rows)


def nested_find_cache(value: Any, path: str, rows: List[Dict[str, Any]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            child_path = f"{path}.{key}"
            if "cache" in lowered or "share" in lowered or "shared" in lowered:
                rows.append({"path": child_path, "key": str(key), "value": compact_value(child)})
            nested_find_cache(child, child_path, rows)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            nested_find_cache(child, f"{path}[{index}]", rows)


def nested_find_view_paths(value: Any, path: str, rows: List[Dict[str, Any]], component_type: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            child_path = f"{path}.{key}"
            if lowered in VIEW_PATH_KEYS and isinstance(child, str) and child.strip():
                rows.append(
                    {
                        "path": child_path,
                        "componentType": component_type,
                        "viewPath": child,
                        "dynamic": "{" in child or "}" in child,
                    }
                )
            nested_find_view_paths(child, child_path, rows, component_type)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            nested_find_view_paths(child, f"{path}[{index}]", rows, component_type)


def nested_has_key_fragment(value: Any, fragments: Iterable[str]) -> bool:
    lowered_fragments = [fragment.lower() for fragment in fragments]
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in lowered_fragments):
                return True
            if nested_has_key_fragment(child, lowered_fragments):
                return True
    elif isinstance(value, list):
        return any(nested_has_key_fragment(child, lowered_fragments) for child in value)
    return False


def nested_find_key_fragment_value(value: Any, fragments: Iterable[str]) -> Any:
    lowered_fragments = [fragment.lower() for fragment in fragments]
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in lowered_fragments):
                return child
            found = nested_find_key_fragment_value(child, lowered_fragments)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = nested_find_key_fragment_value(child, lowered_fragments)
            if found is not None:
                return found
    return None


def object_metrics(value: Any, path: str = "$", depth: int = 0) -> Dict[str, Any]:
    best = {
        "maxObjectDepth": depth,
        "largestArrayPath": None,
        "largestArrayLength": 0,
        "largestObjectPath": None,
        "largestObjectKeys": 0,
    }
    if isinstance(value, dict):
        if len(value) > best["largestObjectKeys"]:
            best["largestObjectPath"] = path
            best["largestObjectKeys"] = len(value)
        for key, child in value.items():
            child_best = object_metrics(child, f"{path}.{key}", depth + 1)
            best = merge_object_metrics(best, child_best)
    elif isinstance(value, list):
        if len(value) > best["largestArrayLength"]:
            best["largestArrayPath"] = path
            best["largestArrayLength"] = len(value)
        for index, child in enumerate(value):
            child_best = object_metrics(child, f"{path}[{index}]", depth + 1)
            best = merge_object_metrics(best, child_best)
    return best


def merge_object_metrics(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(left)
    if right["maxObjectDepth"] > merged["maxObjectDepth"]:
        merged["maxObjectDepth"] = right["maxObjectDepth"]
    if right["largestArrayLength"] > merged["largestArrayLength"]:
        merged["largestArrayPath"] = right["largestArrayPath"]
        merged["largestArrayLength"] = right["largestArrayLength"]
    if right["largestObjectKeys"] > merged["largestObjectKeys"]:
        merged["largestObjectPath"] = right["largestObjectPath"]
        merged["largestObjectKeys"] = right["largestObjectKeys"]
    return merged


def counter_rows(counter: Counter, limit: int = 40) -> List[Dict[str, Any]]:
    return [{"name": str(key), "count": count} for key, count in sorted(counter.items(), key=lambda x: (-x[1], str(x[0])))[:limit]]


def data_shape(component: Dict[str, Any], path: str, component_type: str) -> List[Dict[str, Any]]:
    rows = []
    props = component.get("props") if isinstance(component.get("props"), dict) else {}
    data = props.get("data")
    columns = props.get("columns")
    filter_results_writeback = nested_find_key_fragment_value(props, ("filterresults", "filterResult", "filterWriteback"))
    table_filter = props.get("filter") if isinstance(props.get("filter"), dict) else {}
    table_filter_results = table_filter.get("results") if isinstance(table_filter.get("results"), dict) else {}
    if filter_results_writeback is None and "enabled" in table_filter_results:
        filter_results_writeback = table_filter_results.get("enabled")
    if isinstance(data, list):
        row_count = len(data)
        inferred_cols = 0
        if data and isinstance(data[0], dict):
            inferred_cols = max(len(row) for row in data[:50] if isinstance(row, dict))
        rows.append(
            {
                "path": path,
                "componentType": component_type,
                "kind": "static-data",
                "rows": row_count,
                "columns": len(columns) if isinstance(columns, list) else inferred_cols,
                "bytes": len(canonical_bytes(data)),
                "virtualized": compact_value(nested_find_key_fragment_value(props, ("virtual",))),
                "filterResultsWriteback": compact_value(filter_results_writeback),
            }
        )
    if isinstance(columns, list) and len(columns) > 0:
        rows.append(
            {
                "path": path + ".props.columns",
                "componentType": component_type,
                "kind": "columns",
                "columns": len(columns),
                "bytes": len(canonical_bytes(columns)),
            }
        )
    for key in ("series", "plots", "pens"):
        child = props.get(key)
        if isinstance(child, list):
            point_count = 0
            for item in child:
                if isinstance(item, dict):
                    for point_key in ("data", "points", "values"):
                        points = item.get(point_key)
                        if isinstance(points, list):
                            point_count += len(points)
                            break
            rows.append(
                {
                    "path": f"{path}.props.{key}",
                    "componentType": component_type,
                    "kind": key,
                    "count": len(child),
                    "points": point_count or None,
                    "bytes": len(canonical_bytes(child)),
                }
            )
    data_sources = props.get("dataSources")
    if isinstance(data_sources, dict):
        source_rows: Dict[str, int] = {}
        for source_name, source in data_sources.items():
            if isinstance(source, list):
                source_rows[str(source_name)] = len(source)
            elif isinstance(source, dict):
                data_points = source.get("data")
                if isinstance(data_points, list):
                    source_rows[str(source_name)] = len(data_points)
        series_refs = 0
        plotted_points = 0
        series_configs = props.get("series")
        if isinstance(series_configs, list):
            for item in series_configs:
                if not isinstance(item, dict):
                    continue
                data_config = item.get("data")
                if not isinstance(data_config, dict):
                    continue
                source_name = str(data_config.get("source") or "")
                if source_name and source_name in source_rows:
                    series_refs += 1
                    plotted_points += source_rows[source_name]
        row_count = sum(source_rows.values())
        rows.append(
            {
                "path": f"{path}.props.dataSources",
                "componentType": component_type,
                "kind": "dataSources",
                "count": len(data_sources),
                "rows": row_count or None,
                "seriesReferences": series_refs or None,
                "points": plotted_points or row_count or None,
                "bytes": len(canonical_bytes(data_sources)),
            }
        )
    points = props.get("points")
    if isinstance(points, list):
        rows.append(
            {
                "path": f"{path}.props.points",
                "componentType": component_type,
                "kind": "points",
                "count": None,
                "points": len(points),
                "bytes": len(canonical_bytes(points)),
            }
        )
    if "gauge" in component_type.lower():
        gauge_payload = {
            key: props.get(key)
            for key in ("value", "secondaryValue", "startAngle", "endAngle", "outerAxis", "innerAxis")
            if key in props
        }
        range_count = 0
        axis_count = 0
        for axis_key in ("outerAxis", "innerAxis"):
            axis = props.get(axis_key)
            if isinstance(axis, dict):
                axis_count += 1
                ranges = axis.get("ranges")
                if isinstance(ranges, list):
                    range_count += len(ranges)
        rows.append(
            {
                "path": path,
                "componentType": component_type,
                "kind": "gauge",
                "count": axis_count or None,
                "points": range_count or None,
                "bytes": len(canonical_bytes(gauge_payload)),
            }
        )
    if any(token in component_type.lower() for token in ("svg", "image")):
        payload_bytes = 0
        for child in props.values():
            if isinstance(child, str):
                payload_bytes = max(payload_bytes, len(child.encode("utf-8")))
        if payload_bytes:
            rows.append(
                {
                    "path": path,
                    "componentType": component_type,
                    "kind": "static-media-payload",
                    "bytes": payload_bytes,
                }
            )
    return rows


def make_parameter_payload(value: Any, path: str, component_type: str, source: str) -> Dict[str, Any] | None:
    if not isinstance(value, (dict, list)):
        return None
    stats = object_metrics(value, path)
    return {
        "path": path,
        "componentType": component_type,
        "source": source,
        "bytes": len(canonical_bytes(value)),
        "maxObjectDepth": stats["maxObjectDepth"],
        "largestArrayLength": stats["largestArrayLength"],
        "largestObjectKeys": stats["largestObjectKeys"],
    }


def parameter_payloads(component: Dict[str, Any], path: str, component_type: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    props = component.get("props") if isinstance(component.get("props"), dict) else {}
    params = props.get("params")
    payload = make_parameter_payload(params, path + ".props.params", component_type, "props.params")
    if payload:
        rows.append(payload)

    lowered_type = component_type.lower()
    instances = props.get("instances")
    if isinstance(instances, list):
        if "flex-repeater" in lowered_type or "flexrepeater" in lowered_type:
            metadata_keys = {"instanceStyle", "instancePosition", "style", "position"}
            for index, instance in enumerate(instances):
                if not isinstance(instance, dict):
                    continue
                instance_params = {key: value for key, value in instance.items() if key not in metadata_keys}
                payload = make_parameter_payload(instance_params, f"{path}.props.instances[{index}]", component_type, "props.instances[]")
                if payload and instance_params:
                    rows.append(payload)
        if "view-canvas" in lowered_type or "viewcanvas" in lowered_type:
            for index, instance in enumerate(instances):
                if not isinstance(instance, dict):
                    continue
                view_params = instance.get("viewParams")
                source = "props.instances[].viewParams"
                payload_path = f"{path}.props.instances[{index}].viewParams"
                if view_params is None and "params" in instance:
                    view_params = instance.get("params")
                    source = "props.instances[].params"
                    payload_path = f"{path}.props.instances[{index}].params"
                payload = make_parameter_payload(view_params, payload_path, component_type, source)
                if payload:
                    rows.append(payload)

    for collection_key in ("views", "tabs"):
        collection = props.get(collection_key)
        if not isinstance(collection, list):
            continue
        for index, entry in enumerate(collection):
            if not isinstance(entry, dict):
                continue
            view_params = entry.get("viewParams")
            payload = make_parameter_payload(view_params, f"{path}.props.{collection_key}[{index}].viewParams", component_type, f"props.{collection_key}[].viewParams")
            if payload:
                rows.append(payload)
    return rows


def view_dependency(component: Dict[str, Any], path: str, component_type: str) -> Dict[str, Any] | None:
    props = component.get("props") if isinstance(component.get("props"), dict) else {}
    view_path = find_first_string(props, ("path", "viewPath", "view", "viewName"))
    if not view_path and "view" in component and isinstance(component["view"], str):
        view_path = component["view"]
    if not view_path:
        return None
    dynamic = "{" in view_path or "}" in view_path or "[" in view_path and "]" in view_path
    return {
        "path": path,
        "componentType": component_type,
        "viewPath": view_path,
        "dynamic": bool(dynamic),
    }


def view_instantiation_family(component_type: str) -> str | None:
    lowered = component_type.lower()
    if "view-canvas" in lowered or "viewcanvas" in lowered:
        return "view-canvas"
    if "flex-repeater" in lowered or "flexrepeater" in lowered:
        return "flex-repeater"
    if "carousel" in lowered:
        return "carousel"
    if "container.tab" in lowered or lowered.endswith(".tabcontainer") or lowered.endswith(".tabs"):
        return "tab"
    if "display.view" in lowered or "embedded" in lowered:
        return "embedded-view"
    return None


def script_findings(script: str, path: str) -> Dict[str, Any]:
    indicators = []
    for name, pattern in SCRIPT_PATTERNS:
        if pattern.search(script):
            indicators.append(name)
    return {
        "path": path,
        "chars": len(script),
        "lines": script.count("\n") + 1,
        "indicators": sorted(indicators),
    }


def expression_rate_findings(text: str, path: str) -> List[Dict[str, Any]]:
    rows = []
    for name, pattern in EXPR_RATE_PATTERNS:
        for match in pattern.finditer(text):
            rows.append({"path": path, "kind": name, "rate": int(match.group(1))})
    return rows


def walk(value: Any, state: Dict[str, Any], path: str = "$", component_depth: int = 0) -> None:
    if isinstance(value, dict):
        next_depth = component_depth
        if is_component(value):
            next_depth = component_depth + 1
            component_type = value.get("type", "unknown")
            state["componentCount"] += 1
            state["componentTypes"][component_type] += 1
            state["maxComponentDepth"] = max(state["maxComponentDepth"], next_depth)
            lowered_type = component_type.lower()
            family = view_instantiation_family(component_type)
            if family == "embedded-view":
                state["embeddedViewCount"] += 1
            if "flex-repeater" in lowered_type or "flexrepeater" in lowered_type:
                state["flexRepeaterCount"] += 1
            if "table" in lowered_type:
                state["tableLikeCount"] += 1
            if any(token in lowered_type for token in ("chart", "timeseries", "sparkline", "powerchart", "gauge")):
                state["chartLikeCount"] += 1
            if family:
                state["viewInstantiation"][family] += 1
                dependencies: List[Dict[str, Any]] = []
                props = value.get("props") if isinstance(value.get("props"), dict) else {}
                nested_find_view_paths(props, path + ".props", dependencies, component_type)
                dependency = view_dependency(value, path, component_type)
                if dependency and not dependencies:
                    dependencies.append(dependency)
                for dependency_row in dependencies:
                    if dependency_row not in state["viewDependencies"]:
                        state["viewDependencies"].append(dependency_row)
                state["parameterPayloads"].extend(parameter_payloads(value, path, component_type))
            state["heavyData"].extend(data_shape(value, path, component_type))

        if "binding" in value:
            btype = binding_type(value.get("binding"))
            state["bindingCount"] += 1
            state["bindingTypes"][btype] += 1
            tag_mode = tag_binding_mode(value.get("binding"))
            if tag_mode:
                state["tagBindingModes"][tag_mode] += 1
                state["tagBindingPaths"].append({"path": path, "type": btype, "mode": tag_mode})
            state["bindingPaths"].append({"path": path, "type": btype, "tagMode": tag_mode})
            nested_find_rate(value.get("binding"), path + ".binding", state["polling"])
            nested_find_cache(value.get("binding"), path + ".binding", state["cacheAndShare"])

        if "events" in value and isinstance(value.get("events"), dict):
            state["eventBlockCount"] += 1

        is_script_transform = str(value.get("type", "")).lower() == "script"
        for key, child in value.items():
            lowered = str(key).lower()
            child_path = f"{path}.{key}"
            if isinstance(child, str) and (lowered == "script" or (lowered == "code" and is_script_transform)):
                state["scriptCount"] += 1
                state["scriptChars"] += len(child)
                state["scripts"].append(script_findings(child, child_path))
            if lowered in ("transform", "transforms"):
                state["transformCount"] += 1
            if lowered == "runwhilehidden":
                state["hiddenContent"].append({"path": child_path, "key": str(key), "value": compact_value(child)})
                state["persistentContent"].append({"path": child_path, "key": str(key), "value": compact_value(child)})
            if lowered == "visible" and child is False:
                state["hiddenContent"].append({"path": child_path, "key": str(key), "value": False})
            if lowered in ("persistent", "persist", "lazy", "lazyload", "loadingmode", "loading") or "persist" in lowered:
                state["persistentContent"].append({"path": child_path, "key": str(key), "value": compact_value(child)})
            if isinstance(child, str):
                state["expressionRates"].extend(expression_rate_findings(child, child_path))
            walk(child, state, child_path, next_depth)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk(child, state, f"{path}[{index}]", component_depth)


def risk_signals(state: Dict[str, Any], object_stats: Dict[str, Any]) -> List[Dict[str, str]]:
    signals = []
    component_count = state["componentCount"]
    binding_count = state["bindingCount"]
    bindings_per_component = float(binding_count) / component_count if component_count else 0.0

    def add(code: str, severity: str, message: str) -> None:
        signals.append({"code": code, "severity": severity, "message": message})

    if component_count > 250:
        add("many-components", "high", "Candidate render/editing risk: more than 250 components; verify with browser timing and DOM/heap evidence.")
    elif component_count > 120:
        add("many-components", "medium", "Candidate render/editing risk: more than 120 components; inspect repeated containers and hidden complexity.")
    if state["maxComponentDepth"] > 16:
        add("deep-nesting", "medium", "Candidate layout risk: high component nesting depth; compare route load and browser long tasks.")
    if binding_count > 150:
        add("many-bindings", "high", "Candidate Gateway/session work risk: more than 150 bindings; look for duplicated polling or shared-data opportunities.")
    elif binding_count > 75:
        add("many-bindings", "medium", "Candidate binding-load risk: more than 75 bindings; review refresh rates and shared-data opportunities.")
    if bindings_per_component > 2.5 and component_count > 20:
        add("dense-bindings", "medium", "Candidate repeated-work risk: bindings per component are high; inspect transforms and per-row/per-cell data work.")
    if state["embeddedViewCount"] > 10:
        add("many-embedded-views", "high", "Candidate view-instantiation risk: many Embedded View components can multiply child bindings and startup work.")
    elif state["embeddedViewCount"] > 0:
        add("embedded-views-present", "info", "Embedded Views are present; profile child views and parameter-driven binding load.")
    if state["flexRepeaterCount"] > 0:
        add("flex-repeaters-present", "info", "Flex Repeaters are present; verify instance count and repeated child binding cost.")
    if state["scriptCount"] > 20:
        add("many-scripts", "medium", "Candidate script-work risk: many script blocks are present; inspect event frequency, loops, and blocking calls.")
    if any(item.get("indicators") for item in state["scripts"]):
        add("script-cost-indicators", "medium", "Candidate script-cost indicators found; validate against script timing, logs, and action latency.")
    if state["polling"] or state["expressionRates"]:
        add("polling-present", "medium", "Polling or expression-rate candidates found; quantify refresh cost and required freshness before recommending changes.")
    if not state["cacheAndShare"]:
        add("cache-share-not-observed", "info", "No obvious Cache & Share fields were detected statically; verify eligible query/history bindings before assuming no sharing.")
    if state["tableLikeCount"] > 0:
        add("tables-present", "info", "Table-like components are present; verify row limits, column count, virtualization, and browser long tasks.")
    if state["chartLikeCount"] > 0:
        add("charts-present", "info", "Chart-like components are present; verify history/query range, sample count, and refresh behavior.")
    if object_stats["largestArrayLength"] > 1000:
        add("large-static-array", "medium", "Large static arrays are present; check payload size and whether data should be paged or queried lazily.")
    if object_stats["maxObjectDepth"] > 40:
        add("deep-json", "medium", "Deep JSON structure is present; inspect embedded parameters/custom payloads and browser parse cost.")
    if any(row["bytes"] > 4000 or row["maxObjectDepth"] > 8 for row in state["parameterPayloads"]):
        add("heavy-view-params", "medium", "Candidate parameter-payload risk: embedded/repeated child views receive large or deep params; compare payload bytes and child load cost.")
    return sorted(signals, key=lambda row: ({"high": 0, "medium": 1, "info": 2}.get(row["severity"], 3), row["code"]))


def profile(data: Any, source: str) -> Dict[str, Any]:
    view = extract_view_payload(data)
    state = {
        "componentCount": 0,
        "componentTypes": Counter(),
        "maxComponentDepth": 0,
        "bindingCount": 0,
        "bindingTypes": Counter(),
        "bindingPaths": [],
        "tagBindingModes": Counter(),
        "tagBindingPaths": [],
        "eventBlockCount": 0,
        "scriptCount": 0,
        "scriptChars": 0,
        "scripts": [],
        "transformCount": 0,
        "embeddedViewCount": 0,
        "flexRepeaterCount": 0,
        "tableLikeCount": 0,
        "chartLikeCount": 0,
        "viewInstantiation": Counter(),
        "viewDependencies": [],
        "polling": [],
        "expressionRates": [],
        "cacheAndShare": [],
        "hiddenContent": [],
        "persistentContent": [],
        "heavyData": [],
        "parameterPayloads": [],
    }
    walk(view, state)
    view_bytes = canonical_bytes(view)
    object_stats = object_metrics(view)

    return {
        "ok": True,
        "source": source,
        "viewSha256": hashlib.sha256(view_bytes).hexdigest(),
        "summary": {
            "viewJsonBytes": len(view_bytes),
            "componentCount": state["componentCount"],
            "bindingCount": state["bindingCount"],
            "maxComponentDepth": state["maxComponentDepth"],
            "eventBlockCount": state["eventBlockCount"],
            "scriptCount": state["scriptCount"],
            "scriptChars": state["scriptChars"],
            "transformCount": state["transformCount"],
            "embeddedViewCount": state["embeddedViewCount"],
            "flexRepeaterCount": state["flexRepeaterCount"],
            "tableLikeCount": state["tableLikeCount"],
            "chartLikeCount": state["chartLikeCount"],
        },
        "componentTypes": counter_rows(state["componentTypes"]),
        "bindingTypes": counter_rows(state["bindingTypes"]),
        "tagBindingModes": counter_rows(state["tagBindingModes"]),
        "tagBindingPaths": sorted(state["tagBindingPaths"], key=lambda row: (row["path"], row["mode"], row["type"]))[:50],
        "sampleBindingPaths": state["bindingPaths"][:50],
        "viewInstantiation": counter_rows(state["viewInstantiation"]),
        "dependencies": {
            "viewDependencies": sorted(state["viewDependencies"], key=lambda row: (row["path"], row["viewPath"])),
            "unresolvedDynamicViewPaths": sorted(
                [row for row in state["viewDependencies"] if row["dynamic"]],
                key=lambda row: (row["path"], row["viewPath"]),
            ),
        },
        "polling": {
            "bindingRates": sorted(state["polling"], key=lambda row: (row["path"], row["key"])),
            "expressionRates": sorted(state["expressionRates"], key=lambda row: (row["path"], row["kind"], row["rate"])),
        },
        "cacheAndShare": sorted(state["cacheAndShare"], key=lambda row: (row["path"], row["key"])),
        "scripts": sorted(state["scripts"], key=lambda row: row["path"]),
        "hiddenContent": sorted(state["hiddenContent"], key=lambda row: (row["path"], row["key"])),
        "persistentContent": sorted(state["persistentContent"], key=lambda row: (row["path"], row["key"])),
        "heavyData": sorted(state["heavyData"], key=lambda row: (row["path"], row["kind"])),
        "parameterPayloads": sorted(state["parameterPayloads"], key=lambda row: row["path"]),
        "objectStats": object_stats,
        "riskSignals": risk_signals(state, object_stats),
        "note": "Static profile only. Treat findings as candidates until synchronized Gateway, session, browser, or A/B evidence confirms impact.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze static Perspective view JSON performance candidates.")
    parser.add_argument("path", nargs="?", help="Path to view.json or runner viewRead JSON.")
    parser.add_argument("--stdin", action="store_true", help="Read JSON from standard input.")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON.")
    args = parser.parse_args()
    source, data = load_json(args)
    indent = None if args.compact else 2
    print(json.dumps(profile(data, source), indent=indent, sort_keys=True))


if __name__ == "__main__":
    main()
