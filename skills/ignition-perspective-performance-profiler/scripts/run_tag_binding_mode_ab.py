#!/usr/bin/env python3
"""Run guarded Perspective tag binding mode fixtures.

This A-15 harness compares direct local tag bindings, indirect tag bindings,
and reference-tag bindings on the same Gateway. It creates bounded memory-tag
fixtures, imports one route/view per binding mode, proves an initial and updated
tag value in a browser, runs a synchronized multi-session profile, and rolls
back the Perspective route/view resources. The tag fixture is retained under
the allowed test prefix because the runner does not expose a tag-delete action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import collect_profile as cp
import run_embedded_breadth_scaling as common
import run_query_cache_share_ab as query_common
import run_refresh_binding_ab as refresh_common
import run_table_ab_remediation as fixture_common


SCRIPT_DIR = Path(__file__).resolve().parent
MULTISESSION_SCRIPT = SCRIPT_DIR / "run_multisession_profile.py"
UPDATE_PROBE_SCRIPT = SCRIPT_DIR / "browser_tag_update_probe.mjs"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"
DEFAULT_TAG_PROVIDER = "default"
DEFAULT_TAG_FOLDER = "LLM Tests/PerformanceProfiler"
VARIANTS = ["direct", "indirect", "reference"]


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


def format_number(value: Any) -> str:
    return query_common.format_number(value)


def format_report_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def to_float(value: Any) -> Optional[float]:
    return query_common.to_float(value)


def feature_set_from_health(health: Dict[str, Any]) -> set[str]:
    return refresh_common.feature_set_from_health(health)


def action_set_from_health(health: Dict[str, Any]) -> set[str]:
    return cp.enabled_name_set(cp.response(health).get("supportedActions", []))


def title_case_variant(variant: str) -> str:
    return "".join(part.title() for part in variant.split("-"))


def label(
    text: str,
    name: str,
    *,
    basis: str = "32px",
    style: Optional[Dict[str, Any]] = None,
    prop_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    merged = {
        "color": "#111827",
        "fontSize": 12,
        "overflow": "hidden",
        "padding": "6px 8px",
        "textOverflow": "ellipsis",
        "whiteSpace": "nowrap",
    }
    if style:
        merged.update(style)
    return refresh_common.component(
        "ia.display.label",
        meta={"name": name},
        position={"basis": basis, "grow": 0, "shrink": 0},
        props={"text": text, "style": merged},
        prop_config=prop_config,
    )


def tag_provider(args: argparse.Namespace) -> str:
    return args.tag_provider.strip() or DEFAULT_TAG_PROVIDER


def default_tag_base_path(args: argparse.Namespace) -> str:
    if args.tag_base_path:
        return args.tag_base_path.rstrip("/")
    return f"[{tag_provider(args)}]{DEFAULT_TAG_FOLDER}/{compact(args.run_id)}/TagBindingModes"


def default_allowed_tag_prefix(args: argparse.Namespace) -> str:
    if args.allowed_tag_path_prefix:
        return args.allowed_tag_path_prefix.rstrip("/")
    return f"[{tag_provider(args)}]{DEFAULT_TAG_FOLDER}"


def value_tag_name(index: int) -> str:
    return f"Value{index:03d}"


def source_folder_for(base_path: str, variant: str) -> str:
    if variant == "reference":
        leaf = "ReferenceSource"
    else:
        leaf = title_case_variant(variant)
    return f"{base_path.rstrip('/')}/Source/{leaf}"


def reference_folder(base_path: str) -> str:
    return f"{base_path.rstrip('/')}/Reference"


def tag_path(base_path: str, name: str) -> str:
    return f"{base_path.rstrip('/')}/{name}"


def initial_value(variant: str, index: int) -> str:
    return f"A15-{variant.upper()}-{index:03d}"


def updated_value(variant: str, index: int) -> str:
    return f"A15-{variant.upper()}-UPDATED-{index:03d}"


def source_tag_paths(base_path: str, variant: str, tag_count: int) -> List[str]:
    source_base = source_folder_for(base_path, variant)
    return [tag_path(source_base, value_tag_name(index)) for index in range(1, tag_count + 1)]


def display_tag_paths(base_path: str, variant: str, tag_count: int) -> List[str]:
    display_base = reference_folder(base_path) if variant == "reference" else source_folder_for(base_path, variant)
    return [tag_path(display_base, value_tag_name(index)) for index in range(1, tag_count + 1)]


def memory_tag_definitions(variant: str, tag_count: int) -> List[Dict[str, Any]]:
    return [
        {
            "name": value_tag_name(index),
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "String",
            "value": initial_value(variant, index),
        }
        for index in range(1, tag_count + 1)
    ]


def reference_tag_definitions(base_path: str, tag_count: int) -> List[Dict[str, Any]]:
    source_base = source_folder_for(base_path, "reference")
    return [
        {
            "name": value_tag_name(index),
            "tagType": "AtomicTag",
            "valueSource": "reference",
            "dataType": "String",
            "sourceTagPath": tag_path(source_base, value_tag_name(index)),
        }
        for index in range(1, tag_count + 1)
    ]


def update_tag_definition(variant: str, index: int = 1) -> List[Dict[str, Any]]:
    return [
        {
            "name": value_tag_name(index),
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "String",
            "value": updated_value(variant, index),
        }
    ]


def tag_configure_payload(
    request_id: str,
    base_path: str,
    allowed_prefix: str,
    tags: List[Dict[str, Any]],
    collision_policy: str,
    dry_run: bool,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "tagConfigure",
        "requestId": request_id,
        "basePath": base_path,
        "allowedTagPathPrefixes": [allowed_prefix],
        "tags": tags,
        "collisionPolicy": collision_policy,
        "dryRun": dry_run,
        "maxItems": max(10, len(tags) + 2),
    }
    if not dry_run:
        payload["confirmTagConfigure"] = "CONFIGURE_TAGS"
    return payload


def tag_read_payload(request_id: str, paths: List[str]) -> Dict[str, Any]:
    return {"action": "tagRead", "requestId": request_id, "paths": paths, "maxResults": max(10, len(paths) + 2)}


def tag_read_values(record: Dict[str, Any]) -> Dict[str, Any]:
    reads = cp.response(record).get("reads", [])
    out: Dict[str, Any] = {}
    if isinstance(reads, list):
        for item in reads:
            if isinstance(item, dict) and item.get("path"):
                out[str(item.get("path"))] = item.get("value")
    return out


def tag_read_quality_ok(record: Dict[str, Any], paths: List[str]) -> bool:
    reads = cp.response(record).get("reads", [])
    if not cp.ok(record) or not isinstance(reads, list):
        return False
    good = {
        str(item.get("path"))
        for item in reads
        if isinstance(item, dict) and str(item.get("quality", "")).lower().startswith("good")
    }
    return all(path in good for path in paths)


def tag_read_values_ok(record: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    values = tag_read_values(record)
    return tag_read_quality_ok(record, list(expected.keys())) and all(values.get(path) == value for path, value in expected.items())


def tag_binding_for_variant(variant: str, index: int, display_path: str) -> Dict[str, Any]:
    if variant == "indirect":
        return {
            "binding": {
                "type": "tag",
                "config": {
                    "mode": "indirect",
                    "tagPath": f"{{base}}/{value_tag_name(index)}",
                    "fallbackDelay": 2.5,
                    "references": {"base": "{view.params.baseTagPath}"},
                },
            }
        }
    return {"binding": {"type": "tag", "config": {"tagPath": display_path}}}


def tag_label(variant: str, index: int, display_path: str) -> Dict[str, Any]:
    return label(
        f"{title_case_variant(variant)} {index:03d}: pending",
        f"TagLabel{index:03d}",
        basis="30px",
        style={
            "backgroundColor": "#ffffff",
            "borderColor": "#cbd5e1",
            "borderRadius": 4,
            "borderStyle": "solid",
            "borderWidth": "1px",
        },
        prop_config={"props.text": tag_binding_for_variant(variant, index, display_path)},
    )


def make_view_json(
    run_id: str,
    variant: str,
    source_base_path: str,
    display_base_path: str,
    display_paths: List[str],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    marker = f"{run_id} {variant.upper()} TAG-BINDING READY"
    mode_label = {
        "direct": "Direct local tag bindings",
        "indirect": "Indirect tag bindings through view.params.baseTagPath",
        "reference": "Direct bindings to reference tags backed by local source tags",
    }[variant]
    children: List[Dict[str, Any]] = [
        label(
            marker,
            "Ready Marker",
            basis="42px",
            style={
                "backgroundColor": "#ffffff",
                "borderColor": "#64748b",
                "borderRadius": 4,
                "borderStyle": "solid",
                "borderWidth": "1px",
                "fontSize": 16,
                "fontWeight": "700",
                "padding": "9px 10px",
                "whiteSpace": "pre-wrap",
            },
        ),
        label(
            f"A-15 tag binding mode fixture: {mode_label}; {args.binding_count} labels.",
            "Fixture Summary",
            basis="38px",
            style={"color": "#1f2937", "whiteSpace": "pre-wrap"},
        ),
        label(
            "Runtime proof requires browser-visible initial and updated tag values, not only static view JSON.",
            "Proof Boundary",
            basis="38px",
            style={"backgroundColor": "#ecfeff", "borderColor": "#a5f3fc", "borderStyle": "solid", "borderWidth": "1px", "whiteSpace": "pre-wrap"},
        ),
    ]
    children.extend(tag_label(variant, index, display_paths[index - 1]) for index in range(1, args.binding_count + 1))
    params: Dict[str, Any] = {}
    prop_config: Dict[str, Any] = {}
    if variant == "indirect":
        params["baseTagPath"] = source_base_path
        prop_config["params.baseTagPath"] = {"paramDirection": "input"}
    return {
        "custom": {
            "runId": run_id,
            "a15Variant": variant,
            "bindingMode": variant,
            "bindingCount": args.binding_count,
            "sourceTagBasePath": source_base_path,
            "displayTagBasePath": display_base_path,
            "tagPathsSha256": sha256_text(canonical_json(display_paths)),
            "remediationCandidate": "Choose direct, indirect, or reference tag bindings based on measured route behavior and provider latency, not static binding shape alone.",
        },
        "params": params,
        "propConfig": prop_config,
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": refresh_common.component(
            "ia.container.flex",
            meta={"name": "tag-binding-mode-root"},
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
    suffix = f"{run_slug}-tag-binding-{variant}"
    if normalized.endswith("-") or normalized.endswith("/"):
        return normalized + suffix
    return normalized.rstrip("/") + "/" + suffix


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    view_path: str,
    route: str,
    source_base_path: str,
    display_base_path: str,
    display_paths: List[str],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = "perf-profiler-tag-binding-mode"
    view_json = make_view_json(run_id, variant, source_base_path, display_base_path, display_paths, args)
    zip_path = zip_dir / "package.zip"
    with tempfile.TemporaryDirectory(prefix="perfprof-tag-binding-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = package_root / project
        page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
        page_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_root / "project.json", {"title": project, "description": "Performance profiler tag binding mode fixture", "enabled": True, "inheritable": False})
        common.write_view(project_root, view_path, view_json, actor)
        write_json(page_dir / "config.json", {"pages": {route: {"title": f"Tag Binding {variant}", "viewPath": view_path}}, "sharedDocks": {}})
        write_json(page_dir / "resource.json", fixture_common.resource_json(actor, ["config.json"]))
        common.make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "bindingMode": variant,
        "bindingCount": args.binding_count,
        "sourceTagBasePath": source_base_path,
        "displayTagBasePath": display_base_path,
        "displayTagPaths": display_paths,
        "sourceTagPaths": source_tag_paths(default_tag_base_path(args), variant, args.tag_count),
        "viewPath": view_path,
        "route": route,
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": common.zip_file_base64(zip_path),
        "viewSha256": sha256_text(canonical_json(view_json)),
        "initialText": initial_value(variant, 1),
        "updatedText": updated_value(variant, 1),
        "profileReadyText": updated_value(variant, 1),
        "staticReadyText": f"{run_id} {variant.upper()} TAG-BINDING READY",
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
        "routes": [{"pagePath": package["route"], "viewPath": package["viewPath"], "title": f"Tag Binding {package['variant']}"}],
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


def rollback_payload(request_id: str, project: str, backup_name: str, package: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "rollback",
        "requestId": request_id,
        "targetProject": project,
        "backupName": backup_name,
        "viewPaths": [package["viewPath"]],
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


def readback_ok(record: Dict[str, Any], package: Dict[str, Any], binding_count: int) -> bool:
    text = canonical_json(cp.response(record))
    if text.count('"type":"tag"') < binding_count:
        return False
    variant = package["variant"]
    if variant == "indirect":
        return (
            '"mode":"indirect"' in text
            and '"references":{"base":"{view.params.baseTagPath}"}' in text
            and '"baseTagPath":"' in text
            and f'"tagPath":"{{base}}/{value_tag_name(1)}"' in text
        )
    return all(path in text for path in package["displayTagPaths"][:binding_count])


def static_summary_for_readback(record: Dict[str, Any], label_name: str) -> Dict[str, Any]:
    try:
        profile_view = cp.ensure_profile_function()
        profile = profile_view(cp.response(record), label_name)
        summary = profile.get("summary", {}) if isinstance(profile, dict) else {}
        return {
            "componentCount": summary.get("componentCount"),
            "bindingCount": summary.get("bindingCount"),
            "tagBindingModes": profile.get("tagBindingModes"),
            "bindingTypes": profile.get("bindingTypes"),
            "riskCount": len(profile.get("riskSignals", [])) if isinstance(profile.get("riskSignals"), list) else 0,
        }
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}


def redact_probe_command(command: List[str]) -> List[str]:
    redacted = list(command)
    for index, value in enumerate(redacted[:-1]):
        if value in {"--url", "--initial-text", "--updated-text"}:
            redacted[index + 1] = "<redacted>"
        elif value in {"--browser-node-modules", "--initial-ready-file", "--update-signal-file"}:
            redacted[index + 1] = "<redacted-local-path>"
    return redacted


def wait_for_json_file(path: Path, timeout_sec: float) -> Dict[str, Any]:
    started = time.time()
    while time.time() - started <= timeout_sec:
        if path.exists():
            try:
                data = read_json(path)
            except Exception:
                data = {}
            return {"ok": True, "elapsedSeconds": round(time.time() - started, 3), "data": data}
        time.sleep(0.1)
    return {"ok": False, "elapsedSeconds": round(time.time() - started, 3), "data": {}}


def start_update_browser(command: List[str], out_dir: Path, args: argparse.Namespace) -> Dict[str, Any]:
    stdout_path = out_dir / "browser-tag-update.stdout.txt"
    stderr_path = out_dir / "browser-tag-update.stderr.txt"
    stdout_handle = stdout_path.open("w", encoding="utf-8", newline="\n")
    stderr_handle = stderr_path.open("w", encoding="utf-8", newline="\n")
    record: Dict[str, Any] = {
        "startedAt": utc_now(),
        "command": redact_probe_command(command),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
    }
    try:
        process = subprocess.Popen(command, stdout=stdout_handle, stderr=stderr_handle, env=cp.browser_env(args))
        record.update({"started": True, "process": process, "stdoutHandle": stdout_handle, "stderrHandle": stderr_handle})
    except Exception as exc:
        stdout_handle.close()
        stderr_handle.close()
        record.update({"started": False, "error": repr(exc)})
    return record


def finish_update_browser(record: Dict[str, Any], timeout_sec: float) -> Dict[str, Any]:
    process = record.get("process")
    if process is None:
        return {key: value for key, value in record.items() if key not in {"stdoutHandle", "stderrHandle"}}
    timed_out = False
    try:
        exit_code = process.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        exit_code = process.wait(timeout=5)
    finally:
        for key in ["stdoutHandle", "stderrHandle"]:
            handle = record.get(key)
            if handle:
                handle.close()
    out = {key: value for key, value in record.items() if key not in {"process", "stdoutHandle", "stderrHandle"}}
    out.update({"exitCode": exit_code, "timedOut": timed_out, "finishedAt": utc_now()})
    return out


def run_update_probe(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    project: str,
    package: Dict[str, Any],
    browser_url: str,
    out_dir: Path,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    variant = package["variant"]
    source_base = str(package["sourceTagBasePath"])
    allowed_prefix = default_allowed_tag_prefix(args)
    update_request_id = f"{args.run_id}-{variant}-tag-update"
    dry = client.call(
        f"{update_request_id}-dryRun",
        tag_configure_payload(f"{update_request_id}-dryRun", source_base, allowed_prefix, update_tag_definition(variant), "o", True),
        timeout=args.timeout_sec,
    )
    if not cp.ok(dry):
        return {"ok": False, "dryRun": dry, "reason": "Update tagConfigure dry-run failed"}

    initial_ready_file = out_dir / "initial-ready.json"
    update_signal_file = out_dir / "update-signal.json"
    command = [
        args.browser_node,
        str(UPDATE_PROBE_SCRIPT),
        "--url",
        browser_url,
        "--out-dir",
        str(out_dir),
        "--url-alias",
        args.browser_url_alias or args.gateway_alias,
        "--ready-selector",
        args.browser_ready_selector,
        "--initial-text",
        str(package["initialText"]),
        "--updated-text",
        str(package["updatedText"]),
        "--initial-ready-file",
        str(initial_ready_file),
        "--update-signal-file",
        str(update_signal_file),
        "--timeout-ms",
        str(int(args.browser_timeout_sec * 1000)),
        "--signal-timeout-ms",
        str(int(args.browser_signal_timeout_sec * 1000)),
        "--update-timeout-ms",
        str(int(args.browser_update_timeout_sec * 1000)),
        "--wait-after-update-ms",
        str(args.browser_wait_after_update_ms),
        "--viewport",
        args.browser_viewport,
    ]
    browser = start_update_browser(command, out_dir, args)
    initial_wait = wait_for_json_file(initial_ready_file, args.browser_timeout_sec + 5)
    if not initial_wait.get("ok"):
        browser_finish = finish_update_browser(browser, 1)
        summary = read_json(out_dir / "browser-tag-update-summary.json")
        return {
            "ok": False,
            "dryRun": dry,
            "browser": browser_finish,
            "initialWait": initial_wait,
            "browserSummary": summary,
            "reason": "Browser did not observe initial tag text",
        }

    signal = {
        "ok": True,
        "variant": variant,
        "requestId": update_request_id,
        "tagConfigureAboutToStartAt": utc_now(),
        "sourceTagPath": tag_path(source_base, value_tag_name(1)),
        "displayTagPath": package["displayTagPaths"][0],
    }
    write_json(update_signal_file, signal)
    update_started = time.time()
    apply = client.call(
        f"{update_request_id}-apply",
        tag_configure_payload(f"{update_request_id}-apply", source_base, allowed_prefix, update_tag_definition(variant), "o", False),
        timeout=args.timeout_sec,
    )
    update_elapsed = round(time.time() - update_started, 3)
    readback_paths = [str(package["displayTagPaths"][0]), tag_path(source_base, value_tag_name(1))]
    readback = client.call(f"{update_request_id}-tagRead", tag_read_payload(f"{update_request_id}-tagRead", readback_paths), timeout=args.timeout_sec)
    browser_finish = finish_update_browser(browser, args.browser_signal_timeout_sec + args.browser_update_timeout_sec + 20)
    browser_summary = read_json(out_dir / "browser-tag-update-summary.json")
    network_summary = read_json(out_dir / "network-summary.json")
    expected_display = {str(package["displayTagPaths"][0]): package["updatedText"]}
    ok = bool(
        cp.ok(apply)
        and cp.response(apply).get("allGood") is True
        and tag_read_values_ok(readback, expected_display)
        and browser_finish.get("exitCode") == 0
        and browser_summary.get("ok") is True
    )
    result = {
        "ok": ok,
        "dryRunOk": cp.ok(dry),
        "applyOk": cp.ok(apply),
        "applyAllGood": cp.response(apply).get("allGood"),
        "updateApplyElapsedSeconds": update_elapsed,
        "initialWait": initial_wait,
        "browser": browser_finish,
        "browserSummary": browser_summary,
        "networkSummary": {
            "responseCount": network_summary.get("responseCount"),
            "statusCounts": network_summary.get("statusCounts"),
            "knownTransferBytes": network_summary.get("knownTransferBytes"),
            "webSockets": network_summary.get("webSockets"),
        },
        "tagReadOk": tag_read_values_ok(readback, expected_display),
        "tagReadValues": tag_read_values(readback),
        "sourceTagPath": tag_path(source_base, value_tag_name(1)),
        "displayTagPath": package["displayTagPaths"][0],
    }
    write_json(out_dir / "update-probe-result.json", result)
    return result


def profile_command(args: argparse.Namespace, package: Dict[str, Any], project: str, browser_url: str, profile_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(MULTISESSION_SCRIPT),
        "--run-id",
        f"{args.run_id}-tag-binding-{package['variant']}",
        "--project",
        project,
        "--route",
        package["route"],
        "--view",
        package["viewPath"],
        "--out-dir",
        str(profile_dir),
        "--session-counts",
        str(args.session_count),
        "--max-session-count",
        str(max(args.session_count, 1)),
        "--pre-samples",
        str(args.pre_samples),
        "--during-samples",
        str(args.during_samples),
        "--post-samples",
        str(args.post_samples),
        "--interval-sec",
        str(args.interval_sec),
        "--max-metrics",
        str(args.max_metrics),
        "--gateway-alias",
        args.gateway_alias,
        "--browser-url",
        browser_url,
        "--browser-url-alias",
        args.browser_url_alias,
        "--browser-ready-selector",
        args.browser_ready_selector,
        "--browser-ready-text",
        package["profileReadyText"],
        "--browser-timeout-sec",
        str(args.browser_timeout_sec),
        "--browser-wait-after-ready-ms",
        str(args.browser_wait_after_ready_ms),
        "--browser-viewport",
        args.browser_viewport,
        "--launch-stagger-ms",
        str(args.launch_stagger_ms),
        "--timeout-sec",
        str(args.timeout_sec),
    ]
    for item in args.metric_name_contains:
        command.extend(["--metric-name-contains", item])
    for item in args.metric_prefix:
        command.extend(["--metric-prefix", item])
    if args.browser_node_modules:
        command.extend(["--browser-node-modules", args.browser_node_modules])
    if args.wait_for_clean_baseline:
        command.append("--wait-for-clean-baseline")
        command.extend(["--baseline-max-browser-sessions", str(args.baseline_max_browser_sessions)])
        command.extend(["--baseline-wait-timeout-sec", str(args.baseline_wait_timeout_sec)])
        command.extend(["--baseline-wait-interval-sec", str(args.baseline_wait_interval_sec)])
        if args.fail_on_baseline_timeout:
            command.append("--fail-on-baseline-timeout")
    return command


def profile_ok(profile_dir: Path) -> bool:
    data = read_json(profile_dir / "summary.json")
    if data.get("ok") is not True:
        return False
    groups = data.get("groups", []) if isinstance(data.get("groups"), list) else []
    for group in groups:
        browser = group.get("browserProbes", {}) if isinstance(group, dict) and isinstance(group.get("browserProbes"), dict) else {}
        probe_count = browser.get("probeCount")
        if probe_count is None:
            continue
        if browser.get("readyCount") != probe_count:
            return False
        if browser.get("readyTextMatchedCount") != probe_count:
            return False
    return True


def profile_summary(profile_dir: Path) -> Dict[str, Any]:
    data = read_json(profile_dir / "summary.json")
    groups = data.get("groups", []) if isinstance(data.get("groups"), list) else []
    group = groups[0] if groups else {}
    browser = group.get("browserProbes", {}) if isinstance(group.get("browserProbes"), dict) else {}
    deltas = group.get("deltas", {}) if isinstance(group.get("deltas"), dict) else {}
    baseline = group.get("baselineWait", {}) if isinstance(group.get("baselineWait"), dict) else {}
    return {
        "ok": data.get("ok"),
        "browserProbeCount": browser.get("probeCount"),
        "browserReadyCount": browser.get("readyCount"),
        "browserReadyTextMatchedCount": browser.get("readyTextMatchedCount"),
        "browserTimedOutCount": browser.get("timedOutCount"),
        "domNodeCountAvg": browser.get("domNodeCountAvg"),
        "longTaskTotalMsAvg": browser.get("longTaskTotalMsAvg"),
        "largestContentfulPaintStartMsAvg": browser.get("largestContentfulPaintStartMsAvg"),
        "duringMinusPreBrowserSessionsAvg": deltas.get("duringMinusPreBrowserSessionsAvg"),
        "duringMinusPreBrowserPagesAvg": deltas.get("duringMinusPreBrowserPagesAvg"),
        "duringMinusPreHeapUsedBytesAvg": deltas.get("duringMinusPreHeapUsedBytesAvg"),
        "duringMinusPreProcessCpuLoadAvg": deltas.get("duringMinusPreProcessCpuLoadAvg"),
        "baselineWait": baseline,
    }


def static_summary(profile_dir: Path) -> Dict[str, Any]:
    data = read_json(profile_dir / "static-profile.json")
    summary = data.get("summary", {}) if isinstance(data.get("summary"), dict) else {}
    return {
        "componentCount": summary.get("componentCount"),
        "bindingCount": summary.get("bindingCount"),
        "bindingTypes": data.get("bindingTypes"),
        "tagBindingModes": data.get("tagBindingModes"),
    }


def metric_family_samples(profile_dir: Path) -> List[Dict[str, Any]]:
    data = read_json(profile_dir / "metrics-list.json")
    metrics = data.get("metrics", []) if isinstance(data.get("metrics"), list) else []
    samples: List[Dict[str, Any]] = []
    for item in metrics[:15]:
        if isinstance(item, dict):
            samples.append({"name": item.get("name"), "token": item.get("token"), "type": item.get("type")})
    return samples


def cleanup_checks(client: cp.RunnerClient, args: argparse.Namespace, project: str, variant: str, package: Dict[str, Any], backup_name: str) -> Dict[str, Any]:
    dry = client.call(f"{args.run_id}-{variant}-rollback-dryRun", rollback_payload(f"{args.run_id}-{variant}-rollback-dryRun", project, backup_name, package, True), timeout=args.timeout_sec)
    apply = client.call(f"{args.run_id}-{variant}-rollback-apply", rollback_payload(f"{args.run_id}-{variant}-rollback-apply", project, backup_name, package, False), timeout=args.timeout_sec)
    time.sleep(2)
    routes_check = client.call(
        f"{args.run_id}-{variant}-post-cleanup-routesList",
        {"action": "routesList", "requestId": f"{args.run_id}-{variant}-post-cleanup-routesList", "targetProject": project, "routePrefix": package["route"], "maxResults": 25},
    )
    routes = cp.response(routes_check).get("routes", [])
    routes_list = routes if isinstance(routes, list) else []
    route_still_present = any(isinstance(item, dict) and item.get("pagePath") == package["route"] for item in routes_list)
    after_read = client.call(f"{args.run_id}-{variant}-post-cleanup-viewRead", view_read_payload(f"{args.run_id}-{variant}-post-cleanup-viewRead", project, package["viewPath"], args), timeout=args.timeout_sec)
    return {
        "rollbackDryRunOk": cp.ok(dry),
        "rollbackApplyOk": cp.ok(apply),
        "rollbackOk": cp.ok(dry) and cp.ok(apply),
        "routesListOk": cp.ok(routes_check),
        "cleanupRouteAbsent": cp.ok(routes_check) and not route_still_present,
        "cleanupViewAbsent": not cp.ok(after_read),
    }


def configure_variant_tags(
    client: cp.RunnerClient,
    args: argparse.Namespace,
    base_path: str,
    variant: str,
    out_dir: Path,
) -> Dict[str, Any]:
    source_base = source_folder_for(base_path, variant)
    display_paths = display_tag_paths(base_path, variant, args.tag_count)
    source_paths = source_tag_paths(base_path, variant, args.tag_count)
    allowed_prefix = default_allowed_tag_prefix(args)
    source_defs = memory_tag_definitions(variant, args.tag_count)
    dry = client.call(
        f"{args.run_id}-{variant}-source-tags-dryRun",
        tag_configure_payload(f"{args.run_id}-{variant}-source-tags-dryRun", source_base, allowed_prefix, source_defs, args.tag_collision_policy, True),
        timeout=args.timeout_sec,
    )
    apply = client.call(
        f"{args.run_id}-{variant}-source-tags-apply",
        tag_configure_payload(f"{args.run_id}-{variant}-source-tags-apply", source_base, allowed_prefix, source_defs, args.tag_collision_policy, False),
        timeout=args.timeout_sec,
    )
    source_read = client.call(f"{args.run_id}-{variant}-source-tags-read", tag_read_payload(f"{args.run_id}-{variant}-source-tags-read", source_paths), timeout=args.timeout_sec)
    expected = {path: initial_value(variant, index) for index, path in enumerate(source_paths, start=1)}
    gates = {
        "sourceDryRun": cp.ok(dry),
        "sourceApply": cp.ok(apply) and cp.response(apply).get("allGood") is True,
        "sourceRead": tag_read_values_ok(source_read, expected),
    }
    reference_records: Dict[str, Any] = {}
    if variant == "reference":
        reference_defs = reference_tag_definitions(base_path, args.tag_count)
        ref_base = reference_folder(base_path)
        ref_dry = client.call(
            f"{args.run_id}-{variant}-reference-tags-dryRun",
            tag_configure_payload(f"{args.run_id}-{variant}-reference-tags-dryRun", ref_base, allowed_prefix, reference_defs, args.tag_collision_policy, True),
            timeout=args.timeout_sec,
        )
        ref_apply = client.call(
            f"{args.run_id}-{variant}-reference-tags-apply",
            tag_configure_payload(f"{args.run_id}-{variant}-reference-tags-apply", ref_base, allowed_prefix, reference_defs, args.tag_collision_policy, False),
            timeout=args.timeout_sec,
        )
        ref_read = client.call(f"{args.run_id}-{variant}-reference-tags-read", tag_read_payload(f"{args.run_id}-{variant}-reference-tags-read", display_paths), timeout=args.timeout_sec)
        gates["referenceDryRun"] = cp.ok(ref_dry)
        gates["referenceApply"] = cp.ok(ref_apply) and cp.response(ref_apply).get("allGood") is True
        gates["referenceRead"] = tag_read_values_ok(ref_read, {path: initial_value(variant, index) for index, path in enumerate(display_paths, start=1)})
        reference_records = {
            "referenceDryRunOk": cp.ok(ref_dry),
            "referenceApplyOk": cp.ok(ref_apply),
            "referenceApplyAllGood": cp.response(ref_apply).get("allGood"),
            "referenceReadOk": gates["referenceRead"],
            "referenceReadValues": tag_read_values(ref_read),
        }
    result = {
        "ok": all(gates.values()),
        "variant": variant,
        "sourceTagBasePath": source_base,
        "displayTagBasePath": reference_folder(base_path) if variant == "reference" else source_base,
        "sourceTagPaths": source_paths,
        "displayTagPaths": display_paths,
        "gates": gates,
        "sourceDryRunOk": cp.ok(dry),
        "sourceApplyOk": cp.ok(apply),
        "sourceApplyAllGood": cp.response(apply).get("allGood"),
        "sourceReadOk": gates["sourceRead"],
        "sourceReadValues": tag_read_values(source_read),
        **reference_records,
    }
    write_json(out_dir / f"{variant}-tag-fixture.json", result)
    return result


def compare_variants(variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_variant = {str(row.get("variant")): row for row in variants}
    direct = by_variant.get("direct", {})

    def update_ms(row: Dict[str, Any]) -> Optional[float]:
        probe = row.get("updateProbe", {}) if isinstance(row.get("updateProbe"), dict) else {}
        browser = probe.get("browserSummary", {}) if isinstance(probe.get("browserSummary"), dict) else {}
        return to_float(browser.get("updateVisibleElapsedMs"))

    def profile_value(row: Dict[str, Any], key: str) -> Optional[float]:
        summary = row.get("profileSummary", {}) if isinstance(row.get("profileSummary"), dict) else {}
        return to_float(summary.get(key))

    comparison: Dict[str, Any] = {
        "updateVisibleElapsedMs": {name: update_ms(row) for name, row in by_variant.items()},
        "directAsReferenceMode": "direct",
        "referenceTagMode": "direct-binding-to-reference-tag",
    }
    direct_update = update_ms(direct)
    for variant in ["indirect", "reference"]:
        row = by_variant.get(variant, {})
        comparison[f"{variant}MinusDirectUpdateVisibleMs"] = None if direct_update is None or update_ms(row) is None else update_ms(row) - direct_update
        for key in ["domNodeCountAvg", "duringMinusPreHeapUsedBytesAvg", "duringMinusPreProcessCpuLoadAvg", "longTaskTotalMsAvg"]:
            direct_value = profile_value(direct, key)
            variant_value = profile_value(row, key)
            comparison[f"{variant}MinusDirect{key[0].upper()}{key[1:]}"] = None if direct_value is None or variant_value is None else variant_value - direct_value
    return comparison


def write_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Tag Binding Mode Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        f"Runner API: `{summary.get('runnerVersion')}`",
        f"Binding count: `{summary.get('bindingCount')}`",
        f"Tag fixture persisted: `{str(summary.get('tagFixturePersisted')).lower()}`",
        f"Tag cleanup available in current runner: `{str(summary.get('tagCleanupAvailable')).lower()}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | Tag fixture | Update probe | Update visible ms | Profile | Browser ready | Static tag modes | Cleanup |",
        "|---|---|---|---:|---|---:|---|---|",
    ]
    for row in summary.get("variants", []):
        update_probe = row.get("updateProbe", {}) if isinstance(row.get("updateProbe"), dict) else {}
        browser = update_probe.get("browserSummary", {}) if isinstance(update_probe.get("browserSummary"), dict) else {}
        profile = row.get("profileSummary", {}) if isinstance(row.get("profileSummary"), dict) else {}
        static = row.get("staticSummary", {}) if isinstance(row.get("staticSummary"), dict) else {}
        cleanup = row.get("cleanup", {}) if isinstance(row.get("cleanup"), dict) else {}
        cleanup_ok = cleanup.get("rollbackOk") and cleanup.get("cleanupRouteAbsent") and cleanup.get("cleanupViewAbsent")
        lines.append(
            "| {variant} | `{fixture}` | `{update}` | {update_ms} | `{profile_ok}` | {ready}/{total} | `{modes}` | `{cleanup}` |".format(
                variant=row.get("variant"),
                fixture=str(row.get("tagFixtureOk")).lower(),
                update=str(update_probe.get("ok")).lower(),
                update_ms=format_number(browser.get("updateVisibleElapsedMs")),
                profile_ok=str(row.get("profileOk")).lower(),
                ready=format_number(profile.get("browserReadyTextMatchedCount")),
                total=format_number(profile.get("browserProbeCount")),
                modes=format_report_value(static.get("tagBindingModes")),
                cleanup=str(bool(cleanup_ok)).lower(),
            )
        )
    lines.extend(["", "## Comparison", ""])
    for key, value in summary.get("comparison", {}).items():
        lines.append(f"- `{key}`: `{format_report_value(value)}`")
    lines.extend(["", "## Interpretation", ""])
    for item in summary.get("interpretation", []):
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


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
    base = compact(args.run_id)

    health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
    feature_set = feature_set_from_health(health)
    action_set = action_set_from_health(health)
    required_actions = {
        "tagConfigure",
        "tagRead",
        "projectResourceImportZip",
        "pageValidate",
        "viewRead",
        "routesList",
        "rollback",
        "metricsList",
        "metricsSnapshot",
        "gatewayPerformanceSnapshot",
        "perspectiveSessionsQuery",
    }
    missing_actions = sorted(action for action in required_actions if not cp.supports_action(action_set, feature_set, action))
    if missing_actions:
        raise RuntimeError(f"Runner is missing required supported actions: {', '.join(missing_actions)}")

    providers_record = client.call(f"{args.run_id}-tagProviders", {"action": "tagProviders", "requestId": f"{args.run_id}-tagProviders"}, timeout=args.timeout_sec)
    tag_base_path = default_tag_base_path(args)
    allowed_tag_prefix = default_allowed_tag_prefix(args)
    args.tag_count = max(args.tag_count, args.binding_count)

    tag_fixtures: Dict[str, Dict[str, Any]] = {}
    for variant_name in VARIANTS:
        tag_fixtures[variant_name] = configure_variant_tags(client, args, tag_base_path, variant_name, out_dir / "tag-fixtures")

    variants: List[Dict[str, Any]] = []
    package_records: List[Dict[str, Any]] = []
    for variant_name in VARIANTS:
        fixture = tag_fixtures[variant_name]
        variant_dir = out_dir / variant_name
        variant_dir.mkdir(parents=True, exist_ok=True)
        route = build_route(args.route_prefix, slug(args.run_id), variant_name)
        view_path = f"{args.view_path_prefix.rstrip('/')}/{base}/TagBindingMode{title_case_variant(variant_name)}"
        package = build_package(
            variant_dir,
            project,
            args.run_id,
            variant_name,
            view_path,
            route,
            fixture["sourceTagBasePath"],
            fixture["displayTagBasePath"],
            fixture["displayTagPaths"],
            args,
        )
        package_records.append({key: value for key, value in package.items() if key != "packageBase64"})
        backup_name = ""
        gates: Dict[str, bool] = {"tagFixture": bool(fixture.get("ok"))}
        variant: Dict[str, Any]
        try:
            if not fixture.get("ok"):
                raise RuntimeError("tag fixture setup failed")
            dry_run = client.call(f"{args.run_id}-{variant_name}-dryRun", package_payload("dryRun", f"{args.run_id}-{variant_name}-dryRun", project, package, args), timeout=args.timeout_sec)
            gates["dryRun"] = cp.ok(dry_run)
            if not gates["dryRun"]:
                raise RuntimeError("dryRun failed")
            apply_package = client.call(f"{args.run_id}-{variant_name}-apply", package_payload("apply", f"{args.run_id}-{variant_name}-apply", project, package, args), timeout=args.timeout_sec)
            backup_name = common.backup_name_from_response(cp.response(apply_package))
            gates["apply"] = cp.ok(apply_package) and bool(backup_name)
            if not gates["apply"]:
                raise RuntimeError("apply failed")
            time.sleep(2)
            readback = client.call(f"{args.run_id}-{variant_name}-viewRead", view_read_payload(f"{args.run_id}-{variant_name}-viewRead", project, view_path, args), timeout=args.timeout_sec)
            gates["viewRead"] = cp.ok(readback) and readback_ok(readback, package, args.binding_count)
            page = client.call(f"{args.run_id}-{variant_name}-pageValidate", page_validate_payload(f"{args.run_id}-{variant_name}-pageValidate", project, package, args), timeout=args.timeout_sec)
            gates["pageValidate"] = cp.ok(page) and cp.response(page).get("routeMatchesExpectedView") is True
            browser_url = common.browser_url_from_endpoint(endpoint, project, route)
            update_probe = run_update_probe(client, args, project, package, browser_url, variant_dir / "update-probe")
            gates["updateProbe"] = bool(update_probe.get("ok"))
            profile_dir = (variant_dir / "profile").resolve()
            profile_result = common.run_command(profile_command(args, package, project, browser_url, profile_dir), f"profile-tag-binding-{variant_name}", variant_dir, args.command_timeout_sec, env)
            gates["profile"] = bool(profile_result.get("ok")) and profile_ok(profile_dir)
            variant = {
                "variant": variant_name,
                "ok": all(gates.values()),
                "gates": gates,
                "tagFixtureOk": fixture.get("ok"),
                "tagFixture": fixture,
                "route": route,
                "viewPath": view_path,
                "sourceTagBasePath": fixture["sourceTagBasePath"],
                "displayTagBasePath": fixture["displayTagBasePath"],
                "displayTagPathCount": len(fixture["displayTagPaths"]),
                "backupName": backup_name,
                "readbackStaticSummary": static_summary_for_readback(readback, f"{variant_name}-viewRead"),
                "updateProbe": update_probe,
                "profileOk": gates["profile"],
                "profileDir": str(profile_dir),
                "profileSummary": profile_summary(profile_dir),
                "staticSummary": static_summary(profile_dir),
                "metricFamilySamples": metric_family_samples(profile_dir),
                "profileCommand": profile_result,
            }
        except Exception as exc:
            variant = {
                "variant": variant_name,
                "ok": False,
                "gates": gates,
                "tagFixtureOk": fixture.get("ok"),
                "tagFixture": fixture,
                "route": route,
                "viewPath": view_path,
                "sourceTagBasePath": fixture.get("sourceTagBasePath"),
                "displayTagBasePath": fixture.get("displayTagBasePath"),
                "backupName": backup_name,
                "error": repr(exc),
            }
        finally:
            if backup_name:
                cleanup = cleanup_checks(client, args, project, variant_name, package, backup_name)
                variant["cleanup"] = cleanup
                variant["ok"] = bool(
                    variant.get("ok")
                    and cleanup.get("rollbackOk")
                    and cleanup.get("cleanupRouteAbsent")
                    and cleanup.get("cleanupViewAbsent")
                )
            variants.append(variant)
            if args.pause_sec > 0 and variant_name != VARIANTS[-1]:
                time.sleep(args.pause_sec)

    comparison = compare_variants(variants)
    summary = {
        "ok": bool(cp.ok(health) and cp.ok(providers_record) and variants and all(row.get("ok") for row in variants)),
        "runId": args.run_id,
        "createdAt": utc_now(),
        "project": project,
        "gatewayAlias": args.gateway_alias,
        "runnerVersion": cp.response(health).get("runnerVersion"),
        "stackVersion": cp.response(health).get("stackVersion"),
        "features": sorted(feature_set),
        "supportedActions": sorted(action_set),
        "tagProvider": tag_provider(args),
        "tagBasePath": tag_base_path,
        "allowedTagPathPrefix": allowed_tag_prefix,
        "tagCount": args.tag_count,
        "bindingCount": args.binding_count,
        "sessionCount": args.session_count,
        "waitForCleanBaseline": args.wait_for_clean_baseline,
        "baselineMaxBrowserSessions": args.baseline_max_browser_sessions if args.wait_for_clean_baseline else None,
        "routeViewCleanupAutomatic": True,
        "tagCleanupAvailable": False,
        "tagFixturePersisted": True,
        "variants": variants,
        "comparison": comparison,
        "packages": package_records,
        "interpretation": [
            "This is a controlled A-15 fixture, not a customer route conclusion.",
            "Direct and indirect modes use the same source memory tags; reference mode binds to reference tags that point at the same style of source memory tags.",
            "The browser update probe proves initial and updated text for the first bound tag in each variant before multi-session profiling starts.",
            "The generated route/view resources are rolled back and verified absent; current runner builds do not expose tag deletion, so the bounded tag fixture remains under the allowed test prefix.",
            "Remote or reference-provider behavior still needs a target that actually has those providers; this harness separates UI binding shape from the provider path that supplies the value.",
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
    parser.add_argument("--binding-count", type=int, default=8)
    parser.add_argument("--tag-count", type=int, default=8)
    parser.add_argument("--tag-provider", default=DEFAULT_TAG_PROVIDER)
    parser.add_argument("--tag-base-path", default="", help="Fully qualified base path for generated tag fixtures. Defaults under the allowed test prefix and run id.")
    parser.add_argument("--allowed-tag-path-prefix", default="", help="Fully qualified allowed tag prefix. Defaults to the provider-specific performance-profiler test prefix.")
    parser.add_argument("--tag-collision-policy", default="o", choices=["a", "o", "m", "i"], help="system.tag.configure collision policy for initial fixture tags.")
    parser.add_argument("--route-prefix", default="/llm-")
    parser.add_argument("--view-path-prefix", default="LLM Tests/PerformanceProfiler")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--session-count", type=int, default=5)
    parser.add_argument("--pre-samples", type=int, default=2)
    parser.add_argument("--during-samples", type=int, default=7)
    parser.add_argument("--post-samples", type=int, default=2)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=80)
    parser.add_argument(
        "--metric-name-contains",
        action="append",
        default=["Perspective", "perspective", "tag", "Tag"],
        help="Metric substring filter passed to run_multisession_profile.py. Repeatable.",
    )
    parser.add_argument("--metric-prefix", action="append", default=[], help="Metric prefix filter passed to run_multisession_profile.py. Repeatable.")
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--command-timeout-sec", type=int, default=900)
    parser.add_argument("--gateway-alias", default="target-gateway")
    parser.add_argument("--browser-url-alias", default="target-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=60.0)
    parser.add_argument("--browser-signal-timeout-sec", type=float, default=45.0)
    parser.add_argument("--browser-update-timeout-sec", type=float, default=45.0)
    parser.add_argument("--browser-wait-after-update-ms", type=int, default=1000)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=16000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node", default="node")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--launch-stagger-ms", type=int, default=250)
    parser.add_argument("--wait-for-clean-baseline", action="store_true", help="Before each session group, wait until existing browser sessions are at or below the configured threshold.")
    parser.add_argument("--baseline-max-browser-sessions", type=int, default=0)
    parser.add_argument("--baseline-wait-timeout-sec", type=float, default=300.0)
    parser.add_argument("--baseline-wait-interval-sec", type=float, default=5.0)
    parser.add_argument("--fail-on-baseline-timeout", action="store_true")
    parser.add_argument("--pause-sec", type=float, default=3.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.binding_count < 1:
        raise SystemExit("--binding-count must be >= 1")
    if args.tag_count < 1:
        raise SystemExit("--tag-count must be >= 1")
    if args.session_count < 1:
        raise SystemExit("--session-count must be >= 1")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.pre_samples < 0 or args.during_samples < 0 or args.post_samples < 0:
        raise SystemExit("--pre-samples, --during-samples, and --post-samples must be >= 0")
    if args.baseline_max_browser_sessions < 0:
        raise SystemExit("--baseline-max-browser-sessions must be >= 0")
    if args.baseline_wait_timeout_sec < 0:
        raise SystemExit("--baseline-wait-timeout-sec must be >= 0")
    if args.baseline_wait_interval_sec < 0:
        raise SystemExit("--baseline-wait-interval-sec must be >= 0")
    if args.browser_timeout_sec <= 0 or args.browser_signal_timeout_sec <= 0 or args.browser_update_timeout_sec <= 0:
        raise SystemExit("Browser timeouts must be > 0")
    summary = run(args)
    print(json.dumps({"ok": summary.get("ok"), "summary": str(Path(args.out_dir) / "summary.json")}, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
