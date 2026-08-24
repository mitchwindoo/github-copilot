#!/usr/bin/env python3
"""Analyze an Ignition tag export JSON file for UDT configuration risk."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


NUMERIC_STRING_RE = re.compile(r"^-?(?:\d+\.\d+|\d+)$")
FRACTION_STRING_RE = re.compile(r"^-?\d+\.\d+$")
BOOLEAN_STRING_RE = re.compile(r"^(true|false)$", re.IGNORECASE)
PARAM_TOKEN_RE = re.compile(r"\{[^{}]+\}")
TAG_PATH_RE = re.compile(r"\[(?:\.|[A-Za-z_][A-Za-z0-9_ -]*)\][^'\"\],)\r\n]*")
TAG_CALL_RE = re.compile(r"\bsystem\.tag\.([A-Za-z_][A-Za-z0-9_]*)\b")
PROVIDER_PREFIX_RE = re.compile(r"^\[([^\]]+)\]")
SCRIPT_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_][A-Za-z0-9_.]*)\s+import|import\s+([A-Za-z_][A-Za-z0-9_.]*))", re.MULTILINE)
SCRIPT_LIBRARY_CALL_RE = re.compile(r"\b((?:shared|project|app|gateway|scripts|lib|site)\.[A-Za-z_][A-Za-z0-9_.]*)\s*\(")
COMMAND_TOKENS = {
    "bypass",
    "cmd",
    "command",
    "disable",
    "enable",
    "mode",
    "output",
    "override",
    "reset",
    "setpoint",
    "sp",
    "start",
    "stop",
}
COMMAND_COMPACT_MARKERS = {"setpoint"}
COMPARISON_IGNORED_FIELDS = {"children", "name", "tags", "tagType", "type"}
ALARM_NUMERIC_KEYS = {
    "activedelay",
    "cleardelay",
    "deadband",
    "delay",
    "shelveduration",
    "setpoint",
    "setpointa",
    "setpointb",
    "timeoffdelayseconds",
    "timeondelayseconds",
}
SEVERITY_ORDER = ("Critical", "High", "Medium", "Low")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def root_nodes(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        tags = data.get("tags")
        if isinstance(tags, list):
            return [item for item in tags if isinstance(item, dict)]
        return [data]
    return []


def child_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    for key in ("tags", "children"):
        value = node.get(key)
        if isinstance(value, list):
            children.extend(item for item in value if isinstance(item, dict))
    return children


def walk(node: dict[str, Any], parent_path: str = ""):
    name = str(node.get("name") or "<unnamed>")
    path = f"{parent_path}/{name}" if parent_path else name
    yield path, node
    for child in child_nodes(node):
        yield from walk(child, path)


def iter_nodes(data: Any):
    for root in root_nodes(data):
        yield from walk(root)


def tag_type(node: dict[str, Any]) -> str:
    raw = node.get("tagType") or node.get("type") or ""
    return str(raw)


def value_source(node: dict[str, Any]) -> str:
    raw = node.get("valueSource") or node.get("value_source") or ""
    return str(raw)


def bool_value(raw: Any) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def has_value(mapping: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if key in mapping and mapping.get(key) not in (None, ""):
            return True
    return False


def parameter_items(raw: Any):
    if isinstance(raw, dict):
        for name, value in raw.items():
            yield str(name), value
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and "name" in item:
                yield str(item.get("name")), item.get("value")


def is_udt_type(node: dict[str, Any]) -> bool:
    return tag_type(node).lower() == "udttype"


def is_udt_instance(node: dict[str, Any]) -> bool:
    return tag_type(node).lower() == "udtinstance" or "typeId" in node


def is_atomic(node: dict[str, Any]) -> bool:
    lowered = tag_type(node).lower()
    return lowered in {"atomictag", ""} and "name" in node and not child_nodes(node)


def add_finding(findings: list[dict[str, str]], severity: str, category: str, path: str, message: str) -> None:
    findings.append(
        {
            "severity": severity,
            "category": category,
            "path": path,
            "message": message,
            "evidenceSource": "exported-json",
        }
    )


def name_tokens(name: str) -> list[str]:
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", spaced)
    return [part.lower() for part in re.split(r"[^A-Za-z0-9]+", spaced) if part]


def is_command_like(name: str) -> bool:
    tokens = name_tokens(name)
    if any(token in COMMAND_TOKENS for token in tokens):
        return True
    compact = re.sub(r"[^a-z0-9]+", "", name.lower())
    return any(marker in compact for marker in COMMAND_COMPACT_MARKERS)


def alarm_numeric_key(key: str) -> bool:
    parts = [part for part in re.split(r"[.\[\]]+", key) if part and not part.isdigit()]
    normalized_parts = [re.sub(r"[^a-z0-9]+", "", part.lower()) for part in parts]
    return any(part in ALARM_NUMERIC_KEYS or part.endswith(("setpoint", "delay", "deadband")) for part in normalized_parts)


def string_fields(value: Any, prefix: str = ""):
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from string_fields(child, next_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            yield from string_fields(child, next_prefix)


def current_node_fields(node: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in node.items() if key not in {"tags", "children"}}


def udt_relative_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if "_types_" in parts:
        index = parts.index("_types_")
        return "/".join(parts[index + 1 :])
    return parts[-1] if parts else path


def normalize_type_id(type_id: str) -> str:
    cleaned = re.sub(r"^\[[^\]]+\]", "", type_id.strip()).strip("/")
    parts = [part for part in cleaned.split("/") if part and part != "_types_"]
    return "/".join(parts)


def resolve_type_path(type_id: str, rel_paths: set[str], leaf_paths: dict[str, set[str]]) -> tuple[str | None, str]:
    normalized_type = normalize_type_id(type_id)
    type_leaf = normalized_type.split("/")[-1]
    if normalized_type in rel_paths:
        return normalized_type, "exact"
    leaf_matches = leaf_paths.get(type_leaf, set())
    if "/" not in normalized_type and len(leaf_matches) == 1:
        return next(iter(leaf_matches)), "unique-leaf"
    if leaf_matches:
        return None, "ambiguous"
    return None, "missing"


def member_paths(container_path: str, node: dict[str, Any]) -> dict[str, dict[str, Any]]:
    members: dict[str, dict[str, Any]] = {}
    prefix = container_path.rstrip("/") + "/"
    for child in child_nodes(node):
        for path, child_node in walk(child, container_path):
            if path.startswith(prefix):
                members[path[len(prefix) :]] = child_node
    return members


def comparable_fields(node: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in current_node_fields(node).items() if key not in COMPARISON_IGNORED_FIELDS}


def changed_fields(instance_node: dict[str, Any], definition_node: dict[str, Any]) -> list[str]:
    instance_fields = comparable_fields(instance_node)
    definition_fields = comparable_fields(definition_node)
    common_keys = set(instance_fields) & set(definition_fields)
    return sorted(key for key in common_keys if instance_fields.get(key) != definition_fields.get(key))


def instance_only_fields(instance_node: dict[str, Any], definition_node: dict[str, Any] | None) -> list[str]:
    instance_fields = comparable_fields(instance_node)
    definition_fields = comparable_fields(definition_node or {})
    return sorted(key for key in instance_fields if key not in definition_fields)


def provider_bucket(reference: str) -> str:
    match = PROVIDER_PREFIX_RE.match(reference.strip())
    if not match:
        return "unqualified"
    provider = match.group(1)
    return "relative" if provider == "." else provider


def top_counts(counter: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def unique_sorted(values) -> list[str]:
    return sorted({str(value) for value in values if str(value)})


def ordered_counts(counter: Counter[str], preferred_order: tuple[str, ...] = ()) -> dict[str, int]:
    ordered: dict[str, int] = {}
    for key in preferred_order:
        if key in counter:
            ordered[key] = counter[key]
    for key in sorted(counter):
        if key not in ordered:
            ordered[key] = counter[key]
    return ordered


def summarize_findings(findings: list[dict[str, str]]) -> dict[str, Any]:
    by_severity: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_evidence_source: Counter[str] = Counter()
    by_path: Counter[str] = Counter()

    for finding in findings:
        severity = finding.get("severity", "")
        category = finding.get("category", "")
        evidence_source = finding.get("evidenceSource", "")
        path = finding.get("path", "")
        if severity:
            by_severity[severity] += 1
        if category:
            by_category[category] += 1
        if evidence_source:
            by_evidence_source[evidence_source] += 1
        if path:
            by_path[path] += 1

    return {
        "totalFindings": len(findings),
        "countsBySeverity": ordered_counts(by_severity, SEVERITY_ORDER),
        "countsByCategory": ordered_counts(by_category),
        "countsByEvidenceSource": ordered_counts(by_evidence_source),
        "topAffectedPaths": top_counts(by_path),
    }


def script_imports(text: str) -> list[str]:
    imports: list[str] = []
    for match in SCRIPT_IMPORT_RE.finditer(text):
        module = match.group(1) or match.group(2) or ""
        root = module.split(".")[0]
        if root not in {"com", "java", "javax", "org", "system"}:
            imports.append(module)
    return unique_sorted(imports)


def script_blocking_indicators(text: str) -> list[str]:
    lowered = text.lower()
    indicators: list[str] = []
    if "system.tag.readblocking" in lowered:
        indicators.append("system.tag.readBlocking")
    if "system.tag.writeblocking" in lowered or "writeblocking" in lowered:
        indicators.append("system.tag.writeBlocking")
    if "sleep(" in lowered:
        indicators.append("sleep")
    return unique_sorted(indicators)


def script_async_indicators(text: str) -> list[str]:
    lowered = text.lower()
    indicators: list[str] = []
    if "system.util.invokeasynchronous" in lowered:
        indicators.append("system.util.invokeAsynchronous")
    if "system.tag.writeasync" in lowered or "writeasync" in lowered:
        indicators.append("system.tag.writeAsync")
    return unique_sorted(indicators)


def script_exception_handling(text: str) -> dict[str, Any]:
    has_try = bool(re.search(r"^\s*try\s*:", text, re.MULTILINE))
    except_headers = re.findall(r"^\s*except(?:\s+([^:]+))?\s*:", text, re.MULTILINE)
    has_except = bool(except_headers)
    broad_except = any(not header.strip() or header.strip() in {"Exception", "BaseException"} for header in except_headers)
    swallows = bool(re.search(r"^\s*except(?:\s+[^:]+)?\s*:\s*(?:\r?\n\s*)+(?:pass|return|continue)\b", text, re.MULTILINE))
    logs = any(marker in text for marker in ("system.util.getLogger", ".error(", ".warn(", ".warning(", "logger."))
    signal = "no-exception-handler-token-detected"
    if has_try or has_except:
        signal = "exception-handler-token-detected"
    if swallows:
        signal = "swallow-exception-candidate"
    return {
        "signal": signal,
        "hasTry": has_try,
        "hasExcept": has_except,
        "hasBroadExcept": broad_except,
        "maySwallowException": swallows,
        "hasLoggingCall": logs,
    }


def script_review_record(path: str, field: str, text: str) -> dict[str, Any]:
    tag_calls = unique_sorted(f"system.tag.{match}" for match in TAG_CALL_RE.findall(text))
    tag_paths = unique_sorted(TAG_PATH_RE.findall(text))
    blocking = script_blocking_indicators(text)
    async_indicators = script_async_indicators(text)
    imports = script_imports(text)
    library_calls = unique_sorted(SCRIPT_LIBRARY_CALL_RE.findall(text))
    exception = script_exception_handling(text)
    lowered_calls = {call.lower() for call in tag_calls}
    writes_tags = any(call.startswith("system.tag.write") for call in lowered_calls) or "writeblocking" in text.lower() or "writeasync" in text.lower()

    flags: list[str] = []
    if writes_tags:
        flags.append("tag-write")
    if blocking:
        flags.append("blocking-call")
    if async_indicators:
        flags.append("async-call")
    if any(reference.startswith("[.]") for reference in tag_paths):
        flags.append("relative-tag-path")
    if any(not reference.startswith("[.]") for reference in tag_paths):
        flags.append("external-tag-path")
    if (writes_tags or tag_calls) and exception.get("signal") == "no-exception-handler-token-detected":
        flags.append("no-exception-handler-token-detected")
    if exception.get("hasBroadExcept"):
        flags.append("broad-except-candidate")
    if exception.get("maySwallowException"):
        flags.append("swallow-exception-candidate")
    if imports or library_calls:
        flags.append("candidate-project-library-reference")

    return {
        "path": path,
        "field": field,
        "evidenceSource": "exported-json",
        "evidenceKind": "script-review-signal",
        "tagCalls": tag_calls,
        "tagPaths": tag_paths,
        "writesTags": writes_tags,
        "blockingIndicators": blocking,
        "asyncIndicators": async_indicators,
        "errorHandlingSignal": exception.get("signal"),
        "exceptionHandlerTokens": exception,
        "projectLibraryReferenceCandidates": unique_sorted([*(f"import:{item}" for item in imports), *(f"call:{item}" for item in library_calls)]),
        "scriptReviewSignals": unique_sorted(flags),
        "message": "Static exported-script review signal only; verify error handling and Project Library availability in the target Gateway/project.",
    }


def summarize_script_review(script_review_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    flag_counts: Counter[str] = Counter()
    for item in script_review_evidence:
        flag_counts.update(str(flag) for flag in item.get("scriptReviewSignals", []))
    return {
        "scriptBlockCount": len(script_review_evidence),
        "scriptsWithTagWriteSignal": sum(1 for item in script_review_evidence if item.get("writesTags")),
        "scriptsWithBlockingCallSignal": sum(1 for item in script_review_evidence if item.get("blockingIndicators")),
        "scriptsWithAsyncCallSignal": sum(1 for item in script_review_evidence if item.get("asyncIndicators")),
        "scriptsWithTagPathSignal": sum(1 for item in script_review_evidence if item.get("tagPaths")),
        "scriptsWithoutExceptionHandlerSignal": sum(1 for item in script_review_evidence if item.get("errorHandlingSignal") == "no-exception-handler-token-detected"),
        "scriptsWithExceptionHandlerSignal": sum(1 for item in script_review_evidence if item.get("errorHandlingSignal") == "exception-handler-token-detected"),
        "scriptsWithSwallowExceptionSignal": sum(1 for item in script_review_evidence if item.get("errorHandlingSignal") == "swallow-exception-candidate"),
        "projectLibraryReferenceCandidateCount": sum(1 for item in script_review_evidence if item.get("projectLibraryReferenceCandidates")),
        "countsByReviewSignal": dict(sorted(flag_counts.items())),
    }


def summarize_dependencies(dependencies: list[dict[str, str]]) -> dict[str, Any]:
    by_kind: Counter[str] = Counter()
    by_provider: Counter[str] = Counter()
    by_source_path: Counter[str] = Counter()
    by_target: Counter[str] = Counter()

    for dependency in dependencies:
        kind = dependency.get("kind", "")
        reference = dependency.get("reference", "")
        path = dependency.get("path", "")
        if kind:
            by_kind[kind] += 1
        if reference:
            by_provider[provider_bucket(reference)] += 1
            by_target[reference] += 1
        if path:
            by_source_path[path] += 1

    hard_coded_providers = sorted(provider for provider in by_provider if provider not in {"relative", "unqualified"})
    return {
        "totalEdges": len(dependencies),
        "uniqueTargets": len(by_target),
        "countsByKind": dict(sorted(by_kind.items())),
        "countsByProvider": dict(sorted(by_provider.items())),
        "hardCodedProviders": hard_coded_providers,
        "relativeReferenceCount": by_provider.get("relative", 0),
        "unqualifiedReferenceCount": by_provider.get("unqualified", 0),
        "topTargets": top_counts(by_target),
        "topSourcePaths": top_counts(by_source_path),
    }


def summarize_member_review(instance_member_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    instance_paths: set[str] = set()
    for item in instance_member_evidence:
        status = str(item.get("comparisonStatus") or "")
        if status:
            status_counts[status] += 1
        instance_path = str(item.get("instancePath") or "")
        if instance_path:
            instance_paths.add(instance_path)
    return {
        "exportedInstanceMemberCount": len(instance_member_evidence),
        "instancesWithExportedMembers": len(instance_paths),
        "comparedToDefinitionCount": status_counts.get("definition-member-found", 0),
        "definitionMemberNotFoundCount": status_counts.get("definition-member-not-found", 0),
        "unresolvedDefinitionCount": status_counts.get("definition-not-resolved", 0),
        "countsByComparisonStatus": dict(sorted(status_counts.items())),
    }


def analyze(data: Any, source_name: str) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    udt_type_rel_paths: set[str] = set()
    udt_type_leaf_paths: dict[str, set[str]] = {}
    udt_type_nodes: dict[str, dict[str, Any]] = {}
    udt_type_export_paths: dict[str, str] = {}
    instances: list[tuple[str, dict[str, Any]]] = []
    dependencies: list[dict[str, str]] = []
    dependency_keys: set[tuple[str, str, str, str]] = set()
    instance_member_evidence: list[dict[str, Any]] = []
    script_review_evidence: list[dict[str, Any]] = []
    member_review_boundaries = [
        "Exported instance members confirm only configuration materialized in the export.",
        "Definition members absent from an instance export are not reported as deleted or missing inherited members without live Gateway configuration evidence or an export format that explicitly encodes deletion.",
    ]
    script_review_boundaries = [
        "Exported JSON can surface static script-review signals, but cannot confirm runtime exception behavior, Gateway Scripting Project configuration, importability, or Project Library availability.",
    ]

    def add_dependency(path: str, field: str, reference: str, kind: str) -> None:
        cleaned = reference.strip()
        if not cleaned:
            return
        key = (path, field, cleaned, kind)
        if key in dependency_keys:
            return
        dependency_keys.add(key)
        dependencies.append({"path": path, "field": field, "reference": cleaned, "kind": kind, "evidenceSource": "exported-json"})

    all_nodes = list(iter_nodes(data))
    counts["nodes"] = len(all_nodes)

    for path, node in all_nodes:
        ttype = tag_type(node)
        lowered_type = ttype.lower()
        if ttype:
            counts[f"tagType:{ttype}"] += 1

        if is_udt_type(node):
            counts["udt_types"] += 1
            rel_path = udt_relative_path(path)
            udt_type_rel_paths.add(rel_path)
            udt_type_nodes[rel_path] = node
            udt_type_export_paths[rel_path] = path
            leaf = rel_path.split("/")[-1]
            udt_type_leaf_paths.setdefault(leaf, set()).add(rel_path)

        if is_udt_instance(node):
            counts["udt_instances"] += 1
            instances.append((path, node))

        if is_atomic(node):
            counts["atomic_tags"] += 1

        if child_nodes(node):
            counts["containers"] += 1

        if node.get("enabled") is False:
            add_finding(findings, "Low", "Disabled", path, "Tag or UDT element is disabled.")

        params = node.get("parameters")
        for param_name, param_value in parameter_items(params):
            counts["parameters"] += 1
            param_path = f"{path}.parameters.{param_name}"
            if isinstance(param_value, str) and NUMERIC_STRING_RE.match(param_value.strip()):
                severity = "Medium" if FRACTION_STRING_RE.match(param_value.strip()) else "Low"
                add_finding(
                    findings,
                    severity,
                    "Parameters",
                    param_path,
                    "Numeric parameter is stored as a string; preserve the intended numeric type.",
                )
            if isinstance(param_value, str) and BOOLEAN_STRING_RE.match(param_value.strip()):
                add_finding(
                    findings,
                    "Medium",
                    "Parameters",
                    param_path,
                    "Boolean parameter is stored as a string; preserve the intended boolean type.",
                )
            if isinstance(param_value, dict):
                if "value" in param_value and isinstance(param_value.get("value"), str):
                    raw_value = str(param_value.get("value")).strip()
                    if NUMERIC_STRING_RE.match(raw_value):
                        add_finding(
                            findings,
                            "Medium",
                            "Parameters",
                            param_path,
                            "Typed parameter object contains a numeric string value.",
                        )
                    if BOOLEAN_STRING_RE.match(raw_value):
                        add_finding(
                            findings,
                            "Medium",
                            "Parameters",
                            param_path,
                            "Typed parameter object contains a boolean string value.",
                        )
                if "value" in param_value and "dataType" not in param_value and "datatype" not in param_value:
                    add_finding(
                        findings,
                        "Low",
                        "Parameters",
                        param_path,
                        "Parameter object has a value but no explicit dataType.",
                    )

        alarms = node.get("alarms")
        if isinstance(alarms, list):
            counts["alarms"] += len(alarms)
            for index, alarm in enumerate(alarms):
                alarm_path = f"{path}.alarms[{index}]"
                if not isinstance(alarm, dict):
                    continue
                if bool_value(alarm.get("enabled")) is False:
                    add_finding(findings, "Low", "Alarms", alarm_path, "Alarm is disabled.")
                if not alarm.get("name") and not alarm.get("label"):
                    add_finding(findings, "Medium", "Alarms", alarm_path, "Alarm has no explicit name or label.")
                if not alarm.get("priority"):
                    add_finding(findings, "Medium", "Alarms", alarm_path, "Alarm has no explicit priority.")
                if not alarm.get("pipeline"):
                    add_finding(findings, "Medium", "Alarms", alarm_path, "Alarm has no explicit pipeline.")
                if not alarm.get("displayPath"):
                    add_finding(findings, "Low", "Alarms", alarm_path, "Alarm has no explicit displayPath.")
                for key, value in string_fields(alarm):
                    if alarm_numeric_key(key) and NUMERIC_STRING_RE.match(value.strip()):
                        add_finding(
                            findings,
                            "Medium",
                            "Alarms",
                            f"{alarm_path}.{key}",
                            "Numeric alarm property is stored as a string.",
                        )

        scripts = node.get("eventScripts")
        if isinstance(scripts, (dict, list)):
            counts["event_script_blocks"] += 1
            for key, value in string_fields(scripts):
                lowered = value.lower()
                script_field = f"eventScripts.{key}"
                script_path = f"{path}.{script_field}"
                script_review_evidence.append(script_review_record(path, script_field, value))
                for match in TAG_PATH_RE.findall(value):
                    add_dependency(path, script_field, match, "scriptTagPath")
                for match in TAG_CALL_RE.findall(value):
                    add_dependency(path, script_field, f"system.tag.{match}", "scriptTagCall")
                if "system.tag.write" in lowered or "writeblocking" in lowered or "writeasync" in lowered:
                    add_finding(findings, "High", "Scripts", script_path, "Tag event script appears to write tags.")
                if "sleep(" in lowered or "system.util.invokeasynchronous" in lowered:
                    add_finding(findings, "Medium", "Scripts", script_path, "Tag event script may have blocking or asynchronous behavior to review.")

        if bool_value(node.get("historyEnabled")) is True:
            counts["history_enabled_tags"] += 1
            if not node.get("historyProvider"):
                add_finding(findings, "Medium", "Historian", path, "History is enabled without an explicit historyProvider.")
            if not has_value(node, "historySampleMode", "sampleMode"):
                add_finding(findings, "Low", "Historian", path, "History is enabled without an explicit sample mode.")
            if not has_value(node, "historyDeadband", "deadband"):
                add_finding(findings, "Low", "Historian", path, "History is enabled without an explicit deadband.")
            if not has_value(node, "tagGroup", "scanClass"):
                add_finding(findings, "Low", "Historian", path, "History is enabled without an explicit tag group or scan class.")
            if is_command_like(str(node.get("name") or "")):
                add_finding(findings, "Medium", "Historian", path, "Command-like tag appears to have history enabled.")

        source = value_source(node).lower()
        if source in {"memory", "opc", "derived"} and is_command_like(str(node.get("name") or "")):
            counts["writable_review_candidates"] += 1
            if bool_value(node.get("readOnly")) is not True:
                add_finding(
                    findings,
                    "Medium",
                    "Writable Surface",
                    path,
                    "Command-like tag should be reviewed for write permissions and audit expectations.",
                )

        for field_path, text in string_fields(current_node_fields(node)):
            if field_path.endswith("sourceTagPath") and PARAM_TOKEN_RE.search(text):
                add_finding(
                    findings,
                    "High",
                    "Reference Tags",
                    f"{path}.{field_path}",
                    "Reference sourceTagPath contains a parameter token; do not rely on parameterized Reference source paths.",
                )
            if field_path.endswith("opcItemPath"):
                add_dependency(path, field_path, text, "opcItemPath")
            if field_path.endswith("sourceTagPath"):
                add_dependency(path, field_path, text, "sourceTagPath")
            if field_path.endswith("typeId"):
                add_dependency(path, field_path, normalize_type_id(text), "typeId")
            if field_path.endswith(("expression", "sourceTagPath", "opcItemPath")):
                for match in TAG_PATH_RE.findall(text):
                    add_dependency(path, field_path, match, "tagPath")

        if lowered_type == "folder":
            counts["folders"] += 1

    udt_type_members = {rel_path: member_paths(rel_path, node) for rel_path, node in udt_type_nodes.items()}

    for path, node in instances:
        type_id = str(node.get("typeId") or "").strip()
        if not type_id:
            add_finding(findings, "High", "Type Relationship", path, "UDT instance has no typeId.")
            continue
        resolved_type, resolution = resolve_type_path(type_id, udt_type_rel_paths, udt_type_leaf_paths)
        if resolution == "ambiguous":
            add_finding(
                findings,
                "High",
                "Type Relationship",
                path,
                f"UDT instance typeId has an ambiguous leaf match: {type_id}",
            )
        elif resolution == "missing":
            add_finding(
                findings,
                "High",
                "Type Relationship",
                path,
                f"UDT instance references a typeId not found in this export: {type_id}",
            )

        override_nodes = member_paths(path, node)
        overrides = sorted(override_nodes)
        if overrides:
            counts["instances_with_exported_members"] += 1
            counts["exported_instance_members"] += len(overrides)
            known_members = udt_type_members.get(resolved_type or "", {})
            for member in overrides:
                definition_node = known_members.get(member)
                definition_path = ""
                status = "definition-not-resolved"
                message = "Export contains explicit instance member configuration, but the UDT definition was not resolved in this export."
                changed = []
                only_fields = instance_only_fields(override_nodes[member], definition_node)
                if definition_node is not None:
                    status = "definition-member-found"
                    definition_path = f"{udt_type_export_paths.get(resolved_type or '', resolved_type or '')}/{member}"
                    changed = changed_fields(override_nodes[member], definition_node)
                    message = "Export contains explicit instance member configuration that can be compared to the matching UDT definition member."
                elif resolved_type:
                    status = "definition-member-not-found"
                    counts["definition_member_not_found"] += 1
                    message = "Export contains an instance member with no matching member in the exported UDT definition."

                instance_member_evidence.append(
                    {
                        "instancePath": path,
                        "typeId": type_id,
                        "memberPath": member,
                        "definitionMemberPath": definition_path,
                        "evidenceSource": "exported-json",
                        "evidenceKind": "exported-instance-member-config",
                        "comparisonStatus": status,
                        "changedFields": changed,
                        "instanceOnlyFields": only_fields,
                        "message": message,
                    }
                )
                if status == "definition-member-not-found":
                    add_finding(
                        findings,
                        "Medium",
                        "Member Overrides",
                        f"{path}/{member}",
                        "UDT instance exports a member with no matching member in the resolved definition; review before bulk changes.",
                    )

    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    findings.sort(key=lambda item: (severity_order.get(item["severity"], 9), item["category"], item["path"], item["message"]))
    dependencies.sort(key=lambda item: (item["path"], item["field"], item["kind"], item["reference"]))

    return {
        "source": source_name,
        "mode": "exported-json",
        "counts": dict(sorted(counts.items())),
        "findingSummary": summarize_findings(findings),
        "dependencySummary": summarize_dependencies(dependencies),
        "memberReviewSummary": summarize_member_review(instance_member_evidence),
        "instanceMemberEvidence": instance_member_evidence,
        "memberReviewBoundaries": member_review_boundaries,
        "scriptReviewSummary": summarize_script_review(script_review_evidence),
        "scriptReviewEvidence": script_review_evidence,
        "scriptReviewBoundaries": script_review_boundaries,
        "dependencies": dependencies,
        "findings": findings,
        "boundaries": [
            "Exported JSON cannot confirm live tag quality, OPC permissions, historian writes, subscriptions, or script execution.",
            "Runtime-only claims require API reads or other live Gateway evidence.",
            *member_review_boundaries,
            *script_review_boundaries,
        ],
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "Ignition UDT Forensic Export Audit",
        f"Source: {report['source']}",
        "",
        "Counts:",
    ]
    counts = report.get("counts", {})
    if counts:
        for key, value in counts.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No tag nodes found.")

    lines.extend(["", "Finding Summary:"])
    finding_summary = report.get("findingSummary", {})
    if finding_summary:
        lines.append(f"- totalFindings: {finding_summary.get('totalFindings', 0)}")
        counts_by_severity = finding_summary.get("countsBySeverity", {})
        if counts_by_severity:
            lines.append("- countsBySeverity: " + ", ".join(f"{key}={value}" for key, value in counts_by_severity.items()))
        counts_by_category = finding_summary.get("countsByCategory", {})
        if counts_by_category:
            lines.append("- countsByCategory: " + ", ".join(f"{key}={value}" for key, value in counts_by_category.items()))
        counts_by_evidence = finding_summary.get("countsByEvidenceSource", {})
        if counts_by_evidence:
            lines.append("- countsByEvidenceSource: " + ", ".join(f"{key}={value}" for key, value in counts_by_evidence.items()))
    else:
        lines.append("- No finding summary available.")

    lines.extend(["", "Member Review Summary:"])
    member_summary = report.get("memberReviewSummary", {})
    if member_summary:
        lines.append(f"- exportedInstanceMemberCount: {member_summary.get('exportedInstanceMemberCount', 0)}")
        lines.append(f"- instancesWithExportedMembers: {member_summary.get('instancesWithExportedMembers', 0)}")
        lines.append(f"- comparedToDefinitionCount: {member_summary.get('comparedToDefinitionCount', 0)}")
        lines.append(f"- definitionMemberNotFoundCount: {member_summary.get('definitionMemberNotFoundCount', 0)}")
        for item in report.get("instanceMemberEvidence", [])[:10]:
            changed = ", ".join(item.get("changedFields", []))
            instance_only = ", ".join(item.get("instanceOnlyFields", []))
            lines.append(
                f"- {item.get('comparisonStatus', '')} | {item.get('evidenceSource', 'unknown')} | "
                f"{item.get('instancePath', '')}/{item.get('memberPath', '')} | "
                f"definition={item.get('definitionMemberPath', '')} | "
                f"changedFields={changed} | instanceOnlyFields={instance_only}"
            )
    else:
        lines.append("- No member review summary available.")

    lines.extend(["", "Script Review Summary:"])
    script_summary = report.get("scriptReviewSummary", {})
    if script_summary:
        lines.append(f"- scriptBlockCount: {script_summary.get('scriptBlockCount', 0)}")
        lines.append(f"- scriptsWithoutExceptionHandlerSignal: {script_summary.get('scriptsWithoutExceptionHandlerSignal', 0)}")
        lines.append(f"- scriptsWithExceptionHandlerSignal: {script_summary.get('scriptsWithExceptionHandlerSignal', 0)}")
        lines.append(f"- scriptsWithSwallowExceptionSignal: {script_summary.get('scriptsWithSwallowExceptionSignal', 0)}")
        lines.append(f"- projectLibraryReferenceCandidateCount: {script_summary.get('projectLibraryReferenceCandidateCount', 0)}")
        for item in report.get("scriptReviewEvidence", [])[:10]:
            candidates = ", ".join(item.get("projectLibraryReferenceCandidates", []))
            signals = ", ".join(item.get("scriptReviewSignals", []))
            lines.append(
                f"- {item.get('evidenceSource', 'unknown')} | {item.get('path', '')} | "
                f"{item.get('field', '')} | errorHandlingSignal={item.get('errorHandlingSignal', '')} | "
                f"signals={signals} | projectLibraryReferenceCandidates={candidates}"
            )
    else:
        lines.append("- No script review summary available.")

    lines.extend(["", "Findings:"])
    findings = report.get("findings", [])
    if findings:
        for finding in findings:
            lines.append(
                f"- {finding['severity']} | {finding['category']} | {finding.get('evidenceSource', 'unknown')} | {finding['path']} | {finding['message']}"
            )
    else:
        lines.append("- No findings from exported configuration inspection.")

    lines.extend(["", "Dependency Summary:"])
    summary = report.get("dependencySummary", {})
    if summary:
        lines.append(f"- totalEdges: {summary.get('totalEdges', 0)}")
        lines.append(f"- uniqueTargets: {summary.get('uniqueTargets', 0)}")
        counts_by_kind = summary.get("countsByKind", {})
        if counts_by_kind:
            lines.append("- countsByKind: " + ", ".join(f"{key}={value}" for key, value in counts_by_kind.items()))
        counts_by_provider = summary.get("countsByProvider", {})
        if counts_by_provider:
            lines.append("- countsByProvider: " + ", ".join(f"{key}={value}" for key, value in counts_by_provider.items()))
        hard_coded = summary.get("hardCodedProviders", [])
        if hard_coded:
            lines.append("- hardCodedProviders: " + ", ".join(hard_coded))
        top_targets = summary.get("topTargets", [])
        if top_targets:
            rendered = ", ".join(f"{item['value']} ({item['count']})" for item in top_targets[:5])
            lines.append("- topTargets: " + rendered)
    else:
        lines.append("- No dependency summary available.")

    lines.extend(["", "Dependencies:"])
    dependencies = report.get("dependencies", [])
    if dependencies:
        for dependency in dependencies[:25]:
            lines.append(
                f"- {dependency['kind']} | {dependency.get('evidenceSource', 'unknown')} | {dependency['path']} | {dependency['field']} | {dependency['reference']}"
            )
        if len(dependencies) > 25:
            lines.append(f"- ... {len(dependencies) - 25} more dependencies omitted from text output.")
    else:
        lines.append("- No dependencies extracted from exported configuration inspection.")

    lines.extend(["", "Boundaries:"])
    for boundary in report.get("boundaries", []):
        lines.append(f"- {boundary}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze Ignition UDT/tag export JSON for configuration risk.")
    parser.add_argument("export_json", help="Path to an Ignition tag export JSON file.")
    parser.add_argument("--json-out", help="Optional path for machine-readable report JSON.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format for stdout.")
    args = parser.parse_args(argv)

    export_path = Path(args.export_json).resolve()
    data = load_json(export_path)
    report = analyze(data, str(export_path))

    if args.json_out:
        json_out = Path(args.json_out).resolve()
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.format == "json":
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
