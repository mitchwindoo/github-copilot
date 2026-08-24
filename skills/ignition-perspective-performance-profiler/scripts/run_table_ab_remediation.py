#!/usr/bin/env python3
"""Run a guarded table virtualization A/B remediation fixture.

This script creates one disposable Perspective route/view, profiles a large
table with row virtualization disabled, overwrites the same view with
virtualization enabled using a live viewSha256 drift guard, profiles again,
compares the bundles, then rolls the Gateway back to the pre-test state.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import collect_profile as cp


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_SCRIPT = SCRIPT_DIR / "collect_profile.py"
COMPARE_SCRIPT = SCRIPT_DIR / "compare_profiles.py"
DEFAULT_ALLOWED_VIEW_PREFIX = "LLM Tests/"
DEFAULT_ALLOWED_ROUTE_PREFIX = "/llm-"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug(value: str) -> str:
    return cp.slug(value).lower()


def write_json(path: Path, data: Any) -> None:
    cp.write_json(path, data)


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def zip_file_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def response(record: Dict[str, Any]) -> Dict[str, Any]:
    return cp.response(record)


def response_ok(record: Dict[str, Any]) -> bool:
    return cp.ok(record)


def backup_name_from_response(data: Dict[str, Any]) -> str:
    raw = str(data.get("backupDir", "") or data.get("backupName", "")).strip()
    if not raw:
        return ""
    return re.split(r"[\\/]+", raw.rstrip("\\/"))[-1]


def browser_url_from_endpoint(endpoint: str, project: str, route: str) -> str:
    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        return ""
    normalized_route = "/" + route.strip("/")
    if normalized_route == "/":
        normalized_route = "/"
    return f"{parsed.scheme}://{parsed.netloc}/data/perspective/client/{project}{normalized_route}"


def make_columns(column_count: int) -> List[Dict[str, Any]]:
    columns = []
    for index in range(column_count):
        field = f"col_{index + 1:02d}"
        columns.append(
            {
                "field": field,
                "header": {"title": f"C{index + 1:02d}"},
                "visible": True,
                "editable": False,
                "sortable": True,
                "resizable": True,
            }
        )
    return columns


def make_rows(row_count: int, column_count: int) -> List[Dict[str, Any]]:
    rows = []
    for row_index in range(row_count):
        row: Dict[str, Any] = {
            "row_id": f"row-{row_index:04d}",
            "status": "Normal" if row_index % 7 else "Attention",
        }
        for col_index in range(column_count):
            field = f"col_{col_index + 1:02d}"
            row[field] = f"R{row_index:04d}-C{col_index + 1:02d}-{(row_index * (col_index + 3)) % 997:03d}"
        rows.append(row)
    return rows


def make_view_json(
    run_id: str,
    variant: str,
    rows: List[Dict[str, Any]],
    columns: List[Dict[str, Any]],
    virtualized: bool,
) -> Dict[str, Any]:
    marker = f"{run_id} {variant.upper()} READY"
    row_count = len(rows)
    col_count = len(columns)
    return {
        "custom": {
            "runId": run_id,
            "variant": variant,
            "rowCount": row_count,
            "columnCount": col_count,
            "dataSha256": sha256_text(canonical_json(rows)),
            "columnSha256": sha256_text(canonical_json(columns)),
            "remediationCandidate": "Enable Perspective table row virtualization.",
        },
        "params": {},
        "propConfig": {},
        "props": {"defaultSize": {"width": 1280, "height": 720}},
        "root": {
            "type": "ia.container.flex",
            "meta": {"name": "root"},
            "props": {
                "direction": "column",
                "alignItems": "stretch",
                "justify": "flex-start",
                "wrap": "nowrap",
                "style": {
                    "backgroundColor": "#f7faf9",
                    "overflow": "hidden",
                    "padding": "12px",
                },
            },
            "children": [
                {
                    "type": "ia.display.label",
                    "meta": {"name": "Ready Marker"},
                    "position": {"basis": "36px", "grow": 0, "shrink": 0},
                    "props": {
                        "text": marker,
                        "style": {
                            "backgroundColor": "#ffffff",
                            "borderColor": "#94a3b8",
                            "borderRadius": 4,
                            "borderStyle": "solid",
                            "borderWidth": "1px",
                            "color": "#111827",
                            "fontSize": 16,
                            "fontWeight": "700",
                            "padding": "7px 10px",
                            "whiteSpace": "pre-wrap",
                        },
                    },
                },
                {
                    "type": "ia.display.label",
                    "meta": {"name": "Functional Equivalence"},
                    "position": {"basis": "34px", "grow": 0, "shrink": 0},
                    "props": {
                        "text": (
                            f"Rows {row_count}, columns {col_count}, first row {rows[0]['row_id']}, "
                            f"last row {rows[-1]['row_id']}, virtualized {str(virtualized).lower()}"
                        ),
                        "style": {
                            "color": "#1f2937",
                            "fontSize": 13,
                            "padding": "7px 2px",
                            "whiteSpace": "pre-wrap",
                        },
                    },
                },
                {
                    "type": "ia.display.table",
                    "meta": {"name": "A B Table"},
                    "position": {"basis": "auto", "grow": 1, "shrink": 1},
                    "props": {
                        "data": rows,
                        "columns": columns,
                        "virtualized": virtualized,
                        "selection": {"enableRowSelection": True, "mode": "single"},
                        "style": {
                            "backgroundColor": "#ffffff",
                            "borderColor": "#cbd5e1",
                            "borderRadius": 4,
                            "borderStyle": "solid",
                            "borderWidth": "1px",
                        },
                    },
                },
            ],
        },
        "permissions": {},
    }


def resource_json(actor: str, files: List[str]) -> Dict[str, Any]:
    timestamp = utc_now()
    signature = sha256_text(f"{actor}:{timestamp}:{','.join(files)}")
    return {
        "attributes": {
            "lastModification": {"actor": actor, "timestamp": timestamp},
            "lastModificationSignature": signature,
        },
        "files": files,
        "overridable": True,
        "restricted": False,
        "scope": "G",
        "version": 1,
    }


def write_package_tree(
    package_root: Path,
    project: str,
    view_path: str,
    page_path: str,
    title: str,
    view_json: Dict[str, Any],
    actor: str,
) -> Path:
    project_root = package_root / project
    view_dir = project_root / "com.inductiveautomation.perspective" / "views" / Path(*view_path.split("/"))
    page_dir = project_root / "com.inductiveautomation.perspective" / "page-config"
    view_dir.mkdir(parents=True, exist_ok=True)
    page_dir.mkdir(parents=True, exist_ok=True)
    write_json(project_root / "project.json", {"title": project, "description": "Performance profiler A/B fixture", "enabled": True, "inheritable": False})
    write_json(view_dir / "view.json", view_json)
    write_json(view_dir / "resource.json", resource_json(actor, ["view.json"]))
    write_json(
        page_dir / "config.json",
        {"pages": {page_path: {"title": title, "viewPath": view_path}}, "sharedDocks": {}},
    )
    write_json(page_dir / "resource.json", resource_json(actor, ["config.json"]))
    return project_root


def make_zip(root: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())


def build_package(
    out_dir: Path,
    project: str,
    run_id: str,
    variant: str,
    view_path: str,
    page_path: str,
    title: str,
    rows: List[Dict[str, Any]],
    columns: List[Dict[str, Any]],
    virtualized: bool,
) -> Dict[str, Any]:
    zip_dir = out_dir / "packages" / variant
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)
    actor = f"perf-profiler-{variant}"
    view_json = make_view_json(run_id, variant, rows, columns, virtualized)
    zip_path = zip_dir / f"{slug(run_id)}-{variant}.zip"
    with tempfile.TemporaryDirectory(prefix=f"perfprof-{variant}-") as temp_root:
        package_root = Path(temp_root) / "root"
        project_root = write_package_tree(package_root, project, view_path, page_path, title, view_json, actor)
        make_zip(package_root, zip_path)
    return {
        "variant": variant,
        "virtualized": virtualized,
        "packageRoot": str(project_root),
        "packageStaging": "temporary",
        "zipPath": str(zip_path),
        "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "packageBase64": zip_file_base64(zip_path),
        "viewJsonSha256": sha256_text(canonical_json(view_json)),
        "dataSha256": view_json["custom"]["dataSha256"],
        "columnSha256": view_json["custom"]["columnSha256"],
        "readyText": f"{run_id} {variant.upper()} READY",
    }


def package_payload(
    action: str,
    request_id: str,
    project: str,
    package: Dict[str, Any],
    view_path: str,
    page_path: str,
    title: str,
    args: argparse.Namespace,
    expected_sha: Optional[str] = None,
) -> Dict[str, Any]:
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
        "routes": [{"pagePath": page_path, "viewPath": view_path, "title": title}],
        "dependencyViewPaths": [],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [],
        "allowUnsafeNamedQueryParameters": False,
        "unsafeNamedQueryParameterPaths": [],
        "sharedDockKeys": [],
        "allowOverwrite": bool(expected_sha),
    }
    if expected_sha:
        payload["requireViewSha256ForOverwrite"] = True
        payload["expectedViewSha256ByViewPath"] = {view_path: expected_sha}
    if action == "apply":
        payload["confirmApply"] = "APPLY"
    return payload


def page_validate_payload(request_id: str, project: str, view_path: str, page_path: str, args: argparse.Namespace, expected_sha: str = "") -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "pageValidate",
        "requestId": request_id,
        "targetProject": project,
        "pagePath": page_path,
        "expectedViewPath": view_path,
        "allowedViewPrefix": args.allowed_view_prefix,
        "allowedRoutePrefix": args.allowed_route_prefix,
        "dependencyViewPaths": [],
        "dependencyScriptPaths": [],
        "dependencyNamedQueryPaths": [],
    }
    if expected_sha:
        payload["expectedViewSha256ByViewPath"] = {view_path: expected_sha}
    return payload


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


def rollback_payload(
    request_id: str,
    project: str,
    backup_name: str,
    view_path: str,
    dry_run: bool,
    remove_missing_views: bool,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": "rollback",
        "requestId": request_id,
        "targetProject": project,
        "backupName": backup_name,
        "viewPaths": [view_path],
        "scriptPaths": [],
        "namedQueryPaths": [],
        "dryRun": dry_run,
        "removeMissingViews": remove_missing_views,
        "removeMissingScripts": False,
        "removeMissingNamedQueries": False,
    }
    if not dry_run:
        payload["confirmRollback"] = "ROLLBACK"
    return payload


def run_command(cmd: List[str], label: str, out_dir: Path, timeout_sec: int, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    log_dir = out_dir / "command-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{label}.stdout.txt"
    stderr_path = log_dir / f"{label}.stderr.txt"
    record: Dict[str, Any] = {
        "label": label,
        "startedAt": utc_now(),
        "command": redact_command(cmd),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
    }
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_sec if timeout_sec > 0 else None,
            env=env,
        )
        stdout_path.write_text(completed.stdout or "", encoding="utf-8", newline="\n")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8", newline="\n")
        record.update({"ok": completed.returncode == 0, "returnCode": completed.returncode, "timedOut": False, "finishedAt": utc_now()})
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text((exc.stdout or "") if isinstance(exc.stdout, str) else "", encoding="utf-8", newline="\n")
        stderr_path.write_text((exc.stderr or "") if isinstance(exc.stderr, str) else "", encoding="utf-8", newline="\n")
        record.update({"ok": False, "returnCode": None, "timedOut": True, "finishedAt": utc_now()})
    return record


def redact_command(cmd: List[str]) -> List[str]:
    redacted = list(cmd)
    for index, value in enumerate(redacted[:-1]):
        if value in ("--endpoint", "--token", "--browser-url"):
            redacted[index + 1] = "<redacted>"
        elif value == "--browser-node-modules":
            redacted[index + 1] = "<redacted-node-modules>"
    return redacted


def profile_command(args: argparse.Namespace, run_id: str, route: str, ready_text: str, browser_url: str, out_dir: Path) -> List[str]:
    command = [
        sys.executable,
        str(COLLECT_SCRIPT),
        "--run-id",
        run_id,
        "--project",
        args.project_resolved,
        "--route",
        route,
        "--view",
        args.view_path_resolved,
        "--duration-sec",
        str(args.profile_duration_sec),
        "--interval-sec",
        str(args.interval_sec),
        "--max-metrics",
        str(args.max_metrics),
        "--out-dir",
        str(out_dir),
        "--gateway-alias",
        args.gateway_alias,
        "--scenario",
        "table virtualization remediation A/B profile",
        "--browser-url",
        browser_url,
        "--browser-url-alias",
        args.browser_url_alias,
        "--browser-ready-selector",
        args.browser_ready_selector,
        "--browser-ready-text",
        ready_text,
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


def collect_env(endpoint: str, token: str, project: str) -> Dict[str, str]:
    env = dict(os.environ)
    env["IGNITION_LLM_RUNNER_ENDPOINT"] = endpoint
    env["IGNITION_LLM_RUNNER_TOKEN"] = token
    env["IGNITION_TARGET_PROJECT"] = project
    return env


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


def static_table_shape(profile_dir: Path) -> Dict[str, Any]:
    static = read_json(profile_dir / "static-profile.json")
    rows = static.get("heavyData", [])
    if not isinstance(rows, list):
        return {}
    for item in rows:
        if isinstance(item, dict) and item.get("kind") == "static-data":
            return item
    return {}


def comparison_primary(comparison_dir: Path) -> Dict[str, Any]:
    data = read_json(comparison_dir / "comparison.json")
    browser = data.get("browserDeltas", {}) if isinstance(data.get("browserDeltas"), dict) else {}
    return {
        "largestContentfulPaintMsDelta": browser.get("largestContentfulPaintMs", {}).get("delta") if isinstance(browser.get("largestContentfulPaintMs"), dict) else None,
        "longTaskTotalMsDelta": browser.get("longTaskTotalMs", {}).get("delta") if isinstance(browser.get("longTaskTotalMs"), dict) else None,
        "domNodeCountDelta": browser.get("domNodeCount", {}).get("delta") if isinstance(browser.get("domNodeCount"), dict) else None,
        "resourceTransferSizeDelta": browser.get("resourceTransferSize", {}).get("delta") if isinstance(browser.get("resourceTransferSize"), dict) else None,
    }


def make_report(out_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Table Virtualization A/B Remediation Fixture",
        "",
        f"Run ID: `{summary['runId']}`",
        f"Project: `{summary['project']}`",
        f"Route: `{summary['route']}`",
        f"View: `{summary['view']}`",
        f"Overall OK: `{str(summary.get('ok', False)).lower()}`",
        "",
        "## Gates",
        "",
    ]
    for name, item in summary.get("gates", {}).items():
        lines.append(f"- `{name}`: `{str(item.get('ok', False)).lower()}` {item.get('note', '')}")
    lines.extend(
        [
            "",
            "## Functional Equivalence",
            "",
            f"- Data hash equal: `{str(summary.get('functionalEquivalence', {}).get('dataHashEqual', False)).lower()}`.",
            f"- Column hash equal: `{str(summary.get('functionalEquivalence', {}).get('columnHashEqual', False)).lower()}`.",
            f"- Before virtualized: `{summary.get('before', {}).get('virtualized')}`.",
            f"- After virtualized: `{summary.get('after', {}).get('virtualized')}`.",
            "",
            "## Primary Browser Deltas",
            "",
        ]
    )
    for key, value in summary.get("comparisonPrimary", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This is one controlled fixture pass. It demonstrates the guarded A/B and rollback mechanics on the sampled Gateway. Treat performance deltas as observed/suggestive until repeated paired fixture runs meet the declared comparison policy.",
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def add_gate(gates: Dict[str, Dict[str, Any]], name: str, ok_value: bool, note: str = "", extra: Optional[Dict[str, Any]] = None) -> None:
    row: Dict[str, Any] = {"ok": bool(ok_value)}
    if note:
        row["note"] = note
    if extra:
        row.update(extra)
    gates[name] = row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a guarded Perspective table virtualization A/B remediation fixture.")
    parser.add_argument("--endpoint", help="Runner endpoint. Env/profile fallback matches collect_profile.py.")
    parser.add_argument("--token", help="Runner token. Env/profile fallback matches collect_profile.py.")
    parser.add_argument("--project", help="Target project. Env/profile fallback matches collect_profile.py.")
    parser.add_argument("--run-id", required=True, help="Stable run identifier.")
    parser.add_argument("--out-dir", required=True, help="Evidence output root.")
    parser.add_argument("--route", help="Disposable route. Default: /llm-<run-id>.")
    parser.add_argument("--view-path", help="Disposable view path. Default: LLM Tests/PerformanceProfiler/<run-id>.")
    parser.add_argument("--allowed-view-prefix", default=DEFAULT_ALLOWED_VIEW_PREFIX)
    parser.add_argument("--allowed-route-prefix", default=DEFAULT_ALLOWED_ROUTE_PREFIX)
    parser.add_argument("--rows", type=int, default=500, help="Table rows. Default: 500.")
    parser.add_argument("--columns", type=int, default=30, help="Table columns. Default: 30.")
    parser.add_argument("--profile-duration-sec", type=float, default=10.0)
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-metrics", type=int, default=25)
    parser.add_argument("--timeout-sec", type=int, default=45)
    parser.add_argument("--command-timeout-sec", type=int, default=180)
    parser.add_argument("--gateway-alias", default="configured-gateway")
    parser.add_argument("--browser-url-alias", default="configured-gateway")
    parser.add_argument("--browser-ready-selector", default="body")
    parser.add_argument("--browser-timeout-sec", type=float, default=45.0)
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=5000)
    parser.add_argument("--browser-viewport", default="1366x768")
    parser.add_argument("--browser-node-modules", default="")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip rollback cleanup. Use only for debugging.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.rows <= 0 or args.columns <= 0:
        raise SystemExit("--rows and --columns must be positive")
    if args.rows > 2000 or args.columns > 80:
        raise SystemExit("This fixture caps at 2000 rows and 80 columns")

    endpoint, token, project = cp.resolve_config(args)
    args.project_resolved = project
    route = args.route or f"/llm-{slug(args.run_id)}"
    view_path = args.view_path or f"{args.allowed_view_prefix.rstrip('/')}/PerformanceProfiler/{cp.slug(args.run_id).replace('-', '_')}"
    args.view_path_resolved = view_path
    browser_url = browser_url_from_endpoint(endpoint, project, route)
    if not browser_url:
        raise SystemExit("Could not derive browser URL from runner endpoint. Pass a normal HTTP(S) runner endpoint.")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "api"
    raw_dir.mkdir(parents=True, exist_ok=True)

    client = cp.RunnerClient(endpoint, token, raw_dir, args.timeout_sec)
    gates: Dict[str, Dict[str, Any]] = {}
    commands: List[Dict[str, Any]] = []
    rows = make_rows(args.rows, args.columns)
    columns = make_columns(args.columns)

    before_package = build_package(out_dir, project, args.run_id, "before", view_path, route, "Profiler Table A/B Before", rows, columns, False)
    after_package = build_package(out_dir, project, args.run_id, "after", view_path, route, "Profiler Table A/B After", rows, columns, True)
    package_info = {
        "before": {key: value for key, value in before_package.items() if key != "packageBase64"},
        "after": {key: value for key, value in after_package.items() if key != "packageBase64"},
    }
    write_json(out_dir / "package-info.json", package_info)

    env = collect_env(endpoint, token, project)
    before_backup = ""
    after_backup = ""
    before_hash = ""
    after_hash = ""

    try:
        health = client.call(f"{args.run_id}-health", {"action": "health", "requestId": f"{args.run_id}-health"})
        health_response = response(health)
        add_gate(gates, "health", response_ok(health), f"runner {health_response.get('runnerVersion', '<unknown>')}")

        dry_before = client.call(
            f"{args.run_id}-before-dryRun",
            package_payload("dryRun", f"{args.run_id}-before-dryRun", project, before_package, view_path, route, "Profiler Table A/B Before", args),
            timeout=args.timeout_sec,
        )
        add_gate(gates, "beforeDryRun", response_ok(dry_before), "", {"routeConflictCount": response(dry_before).get("routeConflictCount")})
        if not response_ok(dry_before):
            raise RuntimeError("before dry-run failed")

        apply_before = client.call(
            f"{args.run_id}-before-apply",
            package_payload("apply", f"{args.run_id}-before-apply", project, before_package, view_path, route, "Profiler Table A/B Before", args),
            timeout=args.timeout_sec,
        )
        before_backup = backup_name_from_response(response(apply_before))
        add_gate(gates, "beforeApply", response_ok(apply_before), f"backup {before_backup}")
        if not response_ok(apply_before):
            raise RuntimeError("before apply failed")
        time.sleep(2)

        before_read = client.call(f"{args.run_id}-before-viewRead", view_read_payload(f"{args.run_id}-before-viewRead", project, view_path, args))
        before_hash = str(response(before_read).get("viewSha256", ""))
        add_gate(gates, "beforeViewRead", response_ok(before_read) and bool(before_hash), f"hash {before_hash[:12]}")

        before_validate = client.call(
            f"{args.run_id}-before-pageValidate",
            page_validate_payload(f"{args.run_id}-before-pageValidate", project, view_path, route, args, before_hash),
        )
        add_gate(gates, "beforePageValidate", response_ok(before_validate) and response(before_validate).get("routeMatchesExpectedView") is True)

        before_profile_dir = out_dir / "before-profile"
        before_cmd = profile_command(args, f"{args.run_id}-before-profile", route, str(before_package["readyText"]), browser_url, before_profile_dir)
        before_result = run_command(before_cmd, "before-profile", out_dir, args.command_timeout_sec, env)
        commands.append(before_result)
        add_gate(gates, "beforeProfile", bool(before_result.get("ok")) and profile_ok(before_profile_dir))
        if not gates["beforeProfile"]["ok"]:
            raise RuntimeError("before profile failed")

        dry_after = client.call(
            f"{args.run_id}-after-dryRun",
            package_payload("dryRun", f"{args.run_id}-after-dryRun", project, after_package, view_path, route, "Profiler Table A/B After", args, before_hash),
            timeout=args.timeout_sec,
        )
        dry_after_resp = response(dry_after)
        checked_hashes = dry_after_resp.get("checkedViewHashes", [])
        add_gate(
            gates,
            "afterDryRunDriftGuard",
            response_ok(dry_after) and bool(checked_hashes),
            "",
            {"routeConflictCount": dry_after_resp.get("routeConflictCount"), "checkedViewHashes": checked_hashes},
        )
        if not response_ok(dry_after):
            raise RuntimeError("after dry-run failed")

        apply_after = client.call(
            f"{args.run_id}-after-apply",
            package_payload("apply", f"{args.run_id}-after-apply", project, after_package, view_path, route, "Profiler Table A/B After", args, before_hash),
            timeout=args.timeout_sec,
        )
        after_backup = backup_name_from_response(response(apply_after))
        add_gate(gates, "afterApply", response_ok(apply_after), f"backup {after_backup}")
        if not response_ok(apply_after):
            raise RuntimeError("after apply failed")
        time.sleep(2)

        after_read = client.call(f"{args.run_id}-after-viewRead", view_read_payload(f"{args.run_id}-after-viewRead", project, view_path, args))
        after_hash = str(response(after_read).get("viewSha256", ""))
        add_gate(gates, "afterViewRead", response_ok(after_read) and bool(after_hash) and after_hash != before_hash, f"hash {after_hash[:12]}")

        after_validate = client.call(
            f"{args.run_id}-after-pageValidate",
            page_validate_payload(f"{args.run_id}-after-pageValidate", project, view_path, route, args, after_hash),
        )
        add_gate(gates, "afterPageValidate", response_ok(after_validate) and response(after_validate).get("routeMatchesExpectedView") is True)

        after_profile_dir = out_dir / "after-profile"
        after_cmd = profile_command(args, f"{args.run_id}-after-profile", route, str(after_package["readyText"]), browser_url, after_profile_dir)
        after_result = run_command(after_cmd, "after-profile", out_dir, args.command_timeout_sec, env)
        commands.append(after_result)
        add_gate(gates, "afterProfile", bool(after_result.get("ok")) and profile_ok(after_profile_dir))
        if not gates["afterProfile"]["ok"]:
            raise RuntimeError("after profile failed")

        comparison_dir = out_dir / "comparison"
        compare_cmd = [
            sys.executable,
            str(COMPARE_SCRIPT),
            "--control-dir",
            str(before_profile_dir),
            "--target-dir",
            str(after_profile_dir),
            "--out-dir",
            str(comparison_dir),
        ]
        compare_result = run_command(compare_cmd, "compare-before-after", out_dir, args.command_timeout_sec)
        commands.append(compare_result)
        add_gate(gates, "comparison", bool(compare_result.get("ok")) and (comparison_dir / "comparison.json").exists())

    except Exception as exc:
        add_gate(gates, "scriptException", False, repr(exc))

    rollback_records: Dict[str, Any] = {}
    if not args.no_cleanup:
        if after_backup:
            rb_after_dry = client.call(
                f"{args.run_id}-rollback-after-dryRun",
                rollback_payload(f"{args.run_id}-rollback-after-dryRun", project, after_backup, view_path, True, False),
                timeout=args.timeout_sec,
            )
            rb_after_apply = client.call(
                f"{args.run_id}-rollback-after-apply",
                rollback_payload(f"{args.run_id}-rollback-after-apply", project, after_backup, view_path, False, False),
                timeout=args.timeout_sec,
            )
            rollback_records["afterDryRun"] = response(rb_after_dry)
            rollback_records["afterApply"] = response(rb_after_apply)
            add_gate(gates, "rollbackAfterToBefore", response_ok(rb_after_dry) and response_ok(rb_after_apply))
            time.sleep(2)
            verify_before = client.call(f"{args.run_id}-rollback-after-viewRead", view_read_payload(f"{args.run_id}-rollback-after-viewRead", project, view_path, args))
            restored_hash = str(response(verify_before).get("viewSha256", ""))
            add_gate(gates, "rollbackAfterReadback", response_ok(verify_before) and restored_hash == before_hash, f"hash {restored_hash[:12]}")
        if before_backup:
            rb_before_dry = client.call(
                f"{args.run_id}-rollback-before-dryRun",
                rollback_payload(f"{args.run_id}-rollback-before-dryRun", project, before_backup, view_path, True, True),
                timeout=args.timeout_sec,
            )
            rb_before_apply = client.call(
                f"{args.run_id}-rollback-before-apply",
                rollback_payload(f"{args.run_id}-rollback-before-apply", project, before_backup, view_path, False, True),
                timeout=args.timeout_sec,
            )
            rollback_records["beforeDryRun"] = response(rb_before_dry)
            rollback_records["beforeApply"] = response(rb_before_apply)
            add_gate(gates, "rollbackBeforeCleanup", response_ok(rb_before_dry) and response_ok(rb_before_apply))
            time.sleep(2)
            routes_check = client.call(
                f"{args.run_id}-post-cleanup-routesList",
                {
                    "action": "routesList",
                    "requestId": f"{args.run_id}-post-cleanup-routesList",
                    "targetProject": project,
                    "routePrefix": route,
                    "maxResults": 25,
                },
            )
            routes = response(routes_check).get("routes", [])
            route_still_present = any(isinstance(item, dict) and item.get("pagePath") == route for item in routes if isinstance(routes, list))
            add_gate(gates, "cleanupRouteAbsent", response_ok(routes_check) and not route_still_present)
    else:
        add_gate(gates, "rollbackSkipped", False, "--no-cleanup was supplied")

    write_json(out_dir / "commands.json", commands)
    write_json(out_dir / "rollback.json", rollback_records)

    before_shape = static_table_shape(out_dir / "before-profile")
    after_shape = static_table_shape(out_dir / "after-profile")
    comparison = comparison_primary(out_dir / "comparison")
    summary = {
        "ok": all(item.get("ok") for item in gates.values()),
        "runId": args.run_id,
        "project": project,
        "route": route,
        "view": view_path,
        "gatewayAlias": args.gateway_alias,
        "rows": args.rows,
        "columns": args.columns,
        "before": {
            "virtualized": False,
            "viewSha256": before_hash,
            "backupName": before_backup,
            "staticTableShape": before_shape,
        },
        "after": {
            "virtualized": True,
            "viewSha256": after_hash,
            "backupName": after_backup,
            "staticTableShape": after_shape,
        },
        "functionalEquivalence": {
            "dataHashEqual": before_package["dataSha256"] == after_package["dataSha256"],
            "columnHashEqual": before_package["columnSha256"] == after_package["columnSha256"],
            "rowCountEqual": before_shape.get("rows") == after_shape.get("rows"),
            "columnCountEqual": before_shape.get("columns") == after_shape.get("columns"),
        },
        "comparisonPrimary": comparison,
        "gates": gates,
        "packageInfoPath": "package-info.json",
        "commandsPath": "commands.json",
        "rollbackPath": "rollback.json",
        "interpretation": [
            "This is a controlled table virtualization fixture, not a customer route conclusion.",
            "The before and after variants keep the same table data and columns and change only props.virtualized.",
            "A single before/after pass demonstrates mechanics and can be suggestive; repeat paired fixture runs are required for causal performance claims.",
        ],
    }
    write_json(out_dir / "summary.json", summary)
    make_report(out_dir, summary)
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
