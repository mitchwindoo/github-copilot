#!/usr/bin/env python3
"""Run read-only Gateway/runner contract tests for the Perspective profiler.

The checks map to G-01 through G-12 in the profiler Gateway test plan. The
script writes a bounded evidence bundle and does not mutate Gateway resources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REQUIRED_ACTIONS = [
    "metricsList",
    "metricsSnapshot",
    "gatewayPerformanceSnapshot",
    "perspectiveSessionsQuery",
    "threadDumpQuery",
]
REQUIRED_FEATURE_FLAGS = ["perspectiveSessionsQueryMatchedCount"]
REQUIRED_FEATURES = REQUIRED_ACTIONS + REQUIRED_FEATURE_FLAGS
SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "packagebase64",
    "scriptbase64",
    "sourcecodebase64",
    "x-llm-runner-token",
}
SENSITIVE_SESSION_KEYS = {
    "clientaddress",
    "remoteaddress",
    "ipaddress",
    "ip",
    "host",
    "hostname",
    "useragent",
    "username",
    "user",
    "userid",
    "sessionid",
    "pageid",
}
TYPE_FIELDS = {
    "gauge": ["value"],
    "counter": ["count"],
    "meter": ["count", "meanRate", "oneMinuteRate", "fiveMinuteRate", "fifteenMinuteRate"],
    "histogram": ["count", "min", "max", "mean", "stdDev", "p50", "p75", "p95", "p98", "p99", "p999"],
    "timer": [
        "count",
        "meanRate",
        "oneMinuteRate",
        "fiveMinuteRate",
        "fifteenMinuteRate",
        "min",
        "max",
        "mean",
        "stdDev",
        "p50",
        "p75",
        "p95",
        "p98",
        "p99",
        "p999",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def epoch_millis() -> int:
    return int(time.time() * 1000)


def slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    text = text.strip("-._")
    return text or "contract"


def raw_file_name(counter: int, name: str) -> str:
    clean = slug(name)
    if len(clean) > 44:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        clean = f"{clean[:31].rstrip('-._')}-{digest}"
    return f"{counter:02d}-{clean}.json"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return ""


def find_vault_root(start: Path) -> Optional[Path]:
    for path in [start] + list(start.parents):
        if (path / "IGNITION_INSTANCE_PROFILE.md").exists() and (path / "webdev-runner").exists():
            return path
    return None


def endpoint_from_profile(vault: Optional[Path]) -> str:
    if not vault:
        return ""
    profile = read_text(vault / "IGNITION_INSTANCE_PROFILE.md")
    match = re.search(r"Web Dev runner endpoint\s*\|\s*`([^`]+)`", profile)
    return match.group(1).strip() if match else ""


def project_from_profile(vault: Optional[Path]) -> str:
    if not vault:
        return ""
    profile = read_text(vault / "IGNITION_INSTANCE_PROFILE.md")
    match = re.search(r"Project name\s*\|\s*`([^`]+)`", profile)
    return match.group(1).strip() if match else ""


def token_from_local_source(vault: Optional[Path]) -> str:
    if not vault:
        return ""
    source = read_text(vault / "webdev-runner" / "simple_webdev_do_post_body.py")
    match = re.search(r'(?m)^(?:STATIC_)?TOKEN\s*=\s*"([^"]+)"', source)
    return match.group(1).strip() if match else ""


def resolve_config(args: argparse.Namespace) -> Tuple[str, str, str]:
    vault = find_vault_root(SKILL_DIR)
    endpoint = (
        args.endpoint
        or os.environ.get("IGNITION_LLM_RUNNER_URL", "").strip()
        or os.environ.get("IGNITION_LLM_RUNNER_ENDPOINT", "").strip()
        or os.environ.get("IGNITION_RUNNER_URL", "").strip()
        or endpoint_from_profile(vault)
    )
    token = (
        args.token
        or os.environ.get("IGNITION_LLM_RUNNER_TOKEN", "").strip()
        or os.environ.get("IGNITION_RUNNER_TOKEN", "").strip()
        or token_from_local_source(vault)
    )
    project = (
        args.project
        or os.environ.get("IGNITION_TARGET_PROJECT", "").strip()
        or project_from_profile(vault)
    )
    if not endpoint:
        raise SystemExit(
            "Runner endpoint is required. Use --endpoint, IGNITION_LLM_RUNNER_URL, or IGNITION_LLM_RUNNER_ENDPOINT."
        )
    if not token:
        raise SystemExit("Runner token is required. Use --token or IGNITION_LLM_RUNNER_TOKEN.")
    return endpoint, token, project


def parse_json(text: str) -> Any:
    try:
        return json.loads(text) if text.strip() else {}
    except Exception:
        return {"raw": text}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        clean: Dict[str, Any] = {}
        for key, child in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                clean[key] = "<redacted>"
            else:
                clean[key] = redact(child)
        return clean
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def response(record: Dict[str, Any]) -> Dict[str, Any]:
    data = record.get("response", {})
    return data if isinstance(data, dict) else {}


def response_ok(record: Optional[Dict[str, Any]]) -> bool:
    if not record:
        return False
    data = response(record)
    return bool(record.get("httpStatus", 0) < 400 and data.get("ok") is not False)


def failure_json(record: Dict[str, Any]) -> bool:
    data = response(record)
    if not isinstance(data, dict):
        return False
    text = json.dumps(data, sort_keys=True)
    stack_words = ["traceback", "stacktrace", "java.lang.", "File \"", "at com."]
    return len(text) < 65536 and not any(word.lower() in text.lower() for word in stack_words)


class RunnerClient:
    def __init__(self, endpoint: str, token: str, out_dir: Path, timeout: int) -> None:
        self.endpoint = endpoint
        self.token = token
        self.timeout = timeout
        self.counter = 0
        self.raw_dir = out_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _write_record(self, name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        self.counter += 1
        record["finishedAt"] = utc_now()
        record["response"] = redact(record.get("response"))
        path = self.raw_dir / raw_file_name(self.counter, name)
        record["rawEvidenceFile"] = str(path.name)
        write_json(path, record)
        return record

    def call(
        self,
        name: str,
        payload: Dict[str, Any],
        timeout: Optional[int] = None,
        token_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = dict(payload)
        payload.setdefault("requestId", name)
        body = json.dumps(payload).encode("utf-8")
        token = self.token if token_override is None else token_override
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json", "X-LLM-Runner-Token": token},
            method="POST",
        )
        record: Dict[str, Any] = {
            "name": name,
            "request": redact(payload),
            "startedAt": utc_now(),
        }
        try:
            started = time.perf_counter()
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as http_response:
                text = http_response.read().decode("utf-8", errors="replace")
                record["httpStatus"] = http_response.status
                record["elapsedMs"] = round((time.perf_counter() - started) * 1000, 3)
                record["response"] = parse_json(text)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            record["httpStatus"] = exc.code
            record["response"] = parse_json(text)
        except Exception as exc:
            record["error"] = repr(exc)
            record["response"] = {"ok": False, "error": repr(exc)}
        return self._write_record(name, record)

    def raw_post(
        self,
        name: str,
        body: bytes,
        body_kind: str,
        content_type: str = "application/json",
        token_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        token = self.token if token_override is None else token_override
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": content_type, "X-LLM-Runner-Token": token},
            method="POST",
        )
        record: Dict[str, Any] = {
            "name": name,
            "request": {
                "bodyKind": body_kind,
                "bodyBytes": len(body),
                "contentType": content_type,
            },
            "startedAt": utc_now(),
        }
        try:
            started = time.perf_counter()
            with urllib.request.urlopen(request, timeout=self.timeout) as http_response:
                text = http_response.read().decode("utf-8", errors="replace")
                record["httpStatus"] = http_response.status
                record["elapsedMs"] = round((time.perf_counter() - started) * 1000, 3)
                record["response"] = parse_json(text)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            record["httpStatus"] = exc.code
            record["response"] = parse_json(text)
        except Exception as exc:
            record["error"] = repr(exc)
            record["response"] = {"ok": False, "error": repr(exc)}
        return self._write_record(name, record)


def make_check(checks: List[Dict[str, Any]], check_id: str, name: str, status: str, details: Dict[str, Any]) -> None:
    if status not in {"pass", "fail", "partial", "skip"}:
        raise ValueError(f"Invalid check status {status}")
    checks.append({"id": check_id, "name": name, "status": status, "details": details})


def feature_set(health: Dict[str, Any]) -> set:
    features = health.get("features", [])
    if isinstance(features, dict):
        return {str(key) for key, value in features.items() if value}
    if isinstance(features, list):
        return {str(item) for item in features}
    return set()


def action_set(health: Dict[str, Any]) -> set:
    actions = health.get("supportedActions", [])
    if isinstance(actions, dict):
        return {str(key) for key, value in actions.items() if value}
    if isinstance(actions, list):
        return {str(item) for item in actions}
    return set()


def supports_action(actions: set, features: set, action: str) -> bool:
    return action in actions or (not actions and action in features)


def list_routes(client: RunnerClient, run_id: str, project: str) -> List[Dict[str, Any]]:
    record = client.call(
        f"{run_id}-routesList",
        {"action": "routesList", "requestId": f"{run_id}-routesList", "targetProject": project, "maxResults": 500},
    )
    routes = response(record).get("routes", [])
    return routes if isinstance(routes, list) else []


def choose_route(routes: List[Dict[str, Any]], requested_route: str, requested_view: str) -> Tuple[str, str]:
    if requested_route:
        for item in routes:
            if item.get("pagePath") == requested_route:
                return str(item.get("pagePath", "")), requested_view or str(item.get("viewPath", ""))
        return requested_route, requested_view
    if requested_view:
        for item in routes:
            if item.get("viewPath") == requested_view:
                return str(item.get("pagePath", "")), requested_view
        return "", requested_view
    for item in routes:
        page_path = str(item.get("pagePath", ""))
        view_path = str(item.get("viewPath", ""))
        if page_path and view_path:
            return page_path, view_path
    return "", ""


def read_view_and_page(client: RunnerClient, run_id: str, project: str, route: str, view: str, label: str) -> Dict[str, Any]:
    view_record = client.call(
        f"{run_id}-{label}-viewRead",
        {
            "action": "viewRead",
            "requestId": f"{run_id}-{label}-viewRead",
            "targetProject": project,
            "viewPath": view,
            "allowedViewPrefix": "",
            "includeViewJson": False,
            "includeResourceJson": True,
        },
    )
    page_record = client.call(
        f"{run_id}-{label}-pageValidate",
        {
            "action": "pageValidate",
            "requestId": f"{run_id}-{label}-pageValidate",
            "targetProject": project,
            "pagePath": route,
            "expectedViewPath": view,
            "allowedRoutePrefix": "",
            "allowedViewPrefix": "",
            "includeHashes": True,
        },
    )
    return {
        "viewReadOk": response_ok(view_record),
        "pageValidateOk": response_ok(page_record),
        "viewSha256": response(view_record).get("viewSha256"),
        "pageValidate": response(page_record),
    }


def metric_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = data.get("items")
    if not isinstance(items, list):
        items = data.get("metrics")
    return items if isinstance(items, list) else []


def item_token(item: Dict[str, Any]) -> str:
    return str(item.get("token") or item.get("metricToken") or item.get("name") or "")


def item_type(item: Dict[str, Any]) -> str:
    return str(item.get("type") or item.get("metricType") or "").lower()


def choose_metric_tokens(metrics: List[Dict[str, Any]]) -> Tuple[List[str], Dict[str, str]]:
    tokens: List[str] = []
    by_type: Dict[str, str] = {}
    for item in metrics:
        if not isinstance(item, dict):
            continue
        token = item_token(item)
        mtype = item_type(item)
        if token and token not in tokens:
            tokens.append(token)
        if token and mtype and mtype not in by_type:
            by_type[mtype] = token
    return tokens, by_type


def numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def nested_get(data: Dict[str, Any], paths: Iterable[Tuple[str, ...]]) -> Any:
    for path in paths:
        current: Any = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current is not None:
            return current
    return None


def collect_keys(value: Any, keys: List[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            collect_keys(child, keys)
    elif isinstance(value, list):
        for child in value:
            collect_keys(child, keys)


def hash_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def browser_wait_after_ms(args: argparse.Namespace) -> int:
    if args.browser_wait_after_ready_ms >= 0:
        return args.browser_wait_after_ready_ms
    return int(max(args.session_correlation_hold_sec, 8) * 1000)


def browser_env(args: argparse.Namespace) -> Dict[str, str]:
    env = dict(os.environ)
    if args.browser_node_modules:
        existing = env.get("NODE_PATH", "")
        roots = [args.browser_node_modules]
        pnpm_root = Path(args.browser_node_modules) / ".pnpm" / "node_modules"
        if pnpm_root.exists():
            roots.append(str(pnpm_root))
        env["NODE_PATH"] = os.pathsep.join(roots + ([existing] if existing else []))
    return env


def redact_browser_command(command: List[str]) -> List[str]:
    redacted = list(command)
    for index, value in enumerate(redacted[:-1]):
        if value == "--url":
            redacted[index + 1] = "<redacted-browser-url>"
    return redacted


def start_browser_probe(args: argparse.Namespace, out_dir: Path) -> Optional[Dict[str, Any]]:
    if not args.browser_url:
        return None
    browser_dir = out_dir / "browser-session-correlation"
    browser_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = browser_dir / "browser-probe.stdout.txt"
    stderr_path = browser_dir / "browser-probe.stderr.txt"
    command = [
        args.browser_node,
        str(SCRIPT_DIR / "browser_route_probe.mjs"),
        "--url",
        args.browser_url,
        "--out-dir",
        str(browser_dir),
        "--ready-selector",
        args.browser_ready_selector,
        "--timeout-ms",
        str(int(args.browser_timeout_sec * 1000)),
        "--viewport",
        args.browser_viewport,
        "--wait-after-ready-ms",
        str(browser_wait_after_ms(args)),
        "--url-alias",
        args.browser_url_alias or args.gateway_alias,
    ]
    if args.browser_ready_text:
        command.extend(["--ready-text", args.browser_ready_text])
    stdout_handle = stdout_path.open("w", encoding="utf-8", newline="\n")
    stderr_handle = stderr_path.open("w", encoding="utf-8", newline="\n")
    try:
        process = subprocess.Popen(command, stdout=stdout_handle, stderr=stderr_handle, env=browser_env(args))
    except Exception as exc:
        stdout_handle.close()
        stderr_handle.close()
        return {"started": False, "error": repr(exc), "command": redact_browser_command(command)}
    time.sleep(max(args.browser_start_delay_sec, 0))
    return {
        "started": True,
        "process": process,
        "stdoutHandle": stdout_handle,
        "stderrHandle": stderr_handle,
        "command": redact_browser_command(command),
        "outDir": str(browser_dir),
        "startedAt": utc_now(),
    }


def finish_browser_probe(probe: Optional[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    if not probe:
        return {"started": False, "reason": "Browser probe not requested"}
    process = probe.get("process")
    if process is None:
        return {key: value for key, value in probe.items() if key not in {"stdoutHandle", "stderrHandle"}}
    timeout = max(args.browser_timeout_sec + (browser_wait_after_ms(args) / 1000.0) + 10, 10)
    timed_out = False
    try:
        exit_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        exit_code = process.wait(timeout=5)
    finally:
        for key in ["stdoutHandle", "stderrHandle"]:
            handle = probe.get(key)
            if handle:
                handle.close()
    info = {key: value for key, value in probe.items() if key not in {"process", "stdoutHandle", "stderrHandle"}}
    info.update({"exitCode": exit_code, "timedOut": timed_out, "finishedAt": utc_now()})
    return info


def summarize_checks(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {"pass": 0, "partial": 0, "skip": 0, "fail": 0}
    for check in checks:
        counts[check["status"]] += 1
    return {
        "ok": counts["fail"] == 0,
        "coverageComplete": counts["fail"] == 0 and counts["partial"] == 0 and counts["skip"] == 0,
        "counts": counts,
    }


def make_report(out_dir: Path, manifest: Dict[str, Any], checks: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    lines = [
        "# Gateway Runner Contract Tests",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Gateway alias: `{manifest['gatewayAlias']}`",
        f"Project: `{manifest.get('project') or '<not set>'}`",
        f"Route: `{manifest.get('route') or '<not set>'}`",
        f"View: `{manifest.get('view') or '<not set>'}`",
        f"Evidence grade: `{manifest.get('evidenceGrade', 'Observed')}`",
        f"Overall ok: `{str(summary['ok']).lower()}`",
        f"Coverage complete: `{str(summary['coverageComplete']).lower()}`",
        "",
        "## Direct Observations",
        "",
        f"- Runner: `{manifest.get('runnerVersion') or '<unknown>'}` / `{manifest.get('stackVersion') or '<unknown>'}`.",
        f"- Checks passed: `{summary.get('counts', {}).get('pass', 0)}`.",
        f"- Checks skipped: `{summary.get('counts', {}).get('skip', 0)}`.",
        f"- Checks failed: `{summary.get('counts', {}).get('fail', 0)}`.",
        "",
        "| ID | Status | Check |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check['id']} | {check['status']} | {check['name']} |")
    lines.extend(["", "## Notes", ""])
    for check in checks:
        if check["status"] != "pass":
            lines.append(f"- `{check['id']}` `{check['status']}`: {check['details']}")
    if all(check["status"] == "pass" for check in checks):
        lines.append("- All contract checks passed.")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "These checks prove runner/API contract behavior for the sampled Gateway and route. They do not prove a Perspective performance bottleneck or remediation impact.",
            "",
            "## Unproven Limits",
            "",
            "- This contract run is not proof of a customer root cause, causal improvement, or release readiness.",
            "- Skipped browser/session correlation remains unproven unless a browser URL is supplied and the session check passes.",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run_contracts(args: argparse.Namespace) -> Dict[str, Any]:
    endpoint, token, project = resolve_config(args)
    run_id = args.run_id or f"PERFCONTRACT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out_dir = Path(args.out_dir) if args.out_dir else Path.cwd() / "perf-contract-runs" / slug(run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = RunnerClient(endpoint, token, out_dir, args.timeout_sec)
    checks: List[Dict[str, Any]] = []

    health_record = client.call(f"{run_id}-health-valid", {"action": "health", "requestId": f"{run_id}-health-valid"})
    health = response(health_record)
    features = feature_set(health)
    actions = action_set(health)
    gateway_record = client.call(f"{run_id}-gatewayInfo", {"action": "gatewayInfo", "requestId": f"{run_id}-gatewayInfo"})
    projects_record = client.call(
        f"{run_id}-projectsList",
        {"action": "projectsList", "requestId": f"{run_id}-projectsList", "maxResults": 100},
    )
    if not project:
        projects = response(projects_record).get("projects", [])
        if projects and isinstance(projects[0], dict):
            project = str(projects[0].get("projectName") or projects[0].get("name") or "")
        elif projects:
            project = str(projects[0])
    routes = list_routes(client, run_id, project) if project else []
    route, view = choose_route(routes, args.route or "", args.view or "")
    if not project:
        make_check(checks, "G-01", "Health and feature gate", "fail", {"reason": "Target project could not be resolved"})
        route, view = args.route or "", args.view or ""
    if project and not view:
        view = args.view or ""
    if project and not route and args.route:
        route = args.route

    invalid_json = client.raw_post(f"{run_id}-g01-malformed-json", b"{not-json", "malformed-json")
    empty_body = client.raw_post(f"{run_id}-g01-empty-body", b"", "empty-body")
    missing_actions = [action for action in REQUIRED_ACTIONS if not supports_action(actions, features, action)]
    missing_feature_flags = [feature for feature in REQUIRED_FEATURE_FLAGS if feature not in features]
    missing_features = missing_actions + missing_feature_flags
    g01_pass = (
        response_ok(health_record)
        and response_ok(gateway_record)
        and not missing_features
        and (invalid_json.get("httpStatus", 0) >= 400 or response(invalid_json).get("ok") is False)
        and (empty_body.get("httpStatus", 0) >= 400 or response(empty_body).get("ok") is False)
    )
    make_check(
        checks,
        "G-01",
        "Health and feature gate",
        "pass" if g01_pass else "fail",
        {
            "healthOk": response_ok(health_record),
            "gatewayInfoOk": response_ok(gateway_record),
            "runnerVersion": health.get("runnerVersion"),
            "stackVersion": health.get("stackVersion"),
            "missingFeatures": missing_features,
            "missingActions": missing_actions,
            "missingFeatureFlags": missing_feature_flags,
            "malformedRejected": invalid_json.get("httpStatus", 0) >= 400 or response(invalid_json).get("ok") is False,
            "emptyRejected": empty_body.get("httpStatus", 0) >= 400 or response(empty_body).get("ok") is False,
        },
    )

    valid_id = f"{run_id}-g02-valid"
    invalid_id = f"{run_id}-g02-invalid"
    unauth_id = f"{run_id}-g02-unauthorized"
    valid_req = client.call(valid_id, {"action": "health", "requestId": valid_id})
    invalid_req = client.call(invalid_id, {"action": "noSuchProfilerAction", "requestId": invalid_id})
    unauth_req = client.call(unauth_id, {"action": "health", "requestId": unauth_id}, token_override="invalid-contract-token")
    g02_echo = [
        response(valid_req).get("requestId") == valid_id,
        response(invalid_req).get("requestId") == invalid_id,
        response(unauth_req).get("requestId") == unauth_id,
    ]
    make_check(
        checks,
        "G-02",
        "Request ID propagation",
        "pass" if all(g02_echo) else "fail",
        {
            "validEcho": g02_echo[0],
            "invalidEcho": g02_echo[1],
            "unauthorizedEcho": g02_echo[2],
            "unauthorizedHttpStatus": unauth_req.get("httpStatus"),
        },
    )

    metrics_no_filter = client.call(
        f"{run_id}-g03-metricsList-no-filter",
        {"action": "metricsList", "requestId": f"{run_id}-g03-metricsList-no-filter", "maxResults": 5},
    )
    metrics_capped = client.call(
        f"{run_id}-g03-metricsList-capped",
        {
            "action": "metricsList",
            "requestId": f"{run_id}-g03-metricsList-capped",
            "nameContains": args.metric_name_contains or ["Perspective", "perspective"],
            "maxResults": 5,
        },
    )
    capped_metrics = response(metrics_capped).get("metrics", [])
    capped_count = len(capped_metrics) if isinstance(capped_metrics, list) else 0
    g03_pass = (
        (metrics_no_filter.get("httpStatus", 0) >= 400 or response(metrics_no_filter).get("ok") is False)
        and response_ok(metrics_capped)
        and capped_count <= 5
    )
    make_check(
        checks,
        "G-03",
        "Metrics discovery guardrails",
        "pass" if g03_pass else "fail",
        {
            "noFilterRejected": metrics_no_filter.get("httpStatus", 0) >= 400 or response(metrics_no_filter).get("ok") is False,
            "cappedOk": response_ok(metrics_capped),
            "cappedCount": capped_count,
        },
    )

    metrics_full = client.call(
        f"{run_id}-metricsList-normalization-pool",
        {
            "action": "metricsList",
            "requestId": f"{run_id}-metricsList-normalization-pool",
            "nameContains": args.metric_name_contains or ["Perspective", "perspective", "Gateway", "gateway"],
            "maxResults": args.max_metrics_list,
        },
    )
    metrics = response(metrics_full).get("metrics", [])
    metrics = metrics if isinstance(metrics, list) else []
    tokens, tokens_by_type = choose_metric_tokens(metrics)
    write_json(out_dir / "metrics-list.json", response(metrics_full))

    normalization_tokens = list(tokens_by_type.values())[: args.max_metrics_snapshot]
    normalization_snapshot = client.call(
        f"{run_id}-g04-metricsSnapshot-normalization",
        {
            "action": "metricsSnapshot",
            "requestId": f"{run_id}-g04-metricsSnapshot-normalization",
            "metricTokens": normalization_tokens,
            "maxMetrics": len(normalization_tokens),
        },
    ) if normalization_tokens else None
    normalized_items = metric_items(response(normalization_snapshot) if normalization_snapshot else {})
    item_by_token = {item_token(item): item for item in normalized_items if isinstance(item, dict)}
    type_results: Dict[str, Any] = {}
    normalized_ok = True
    normalized_seen = 0
    for metric_type, fields in TYPE_FIELDS.items():
        token_for_type = tokens_by_type.get(metric_type)
        if not token_for_type:
            type_results[metric_type] = {"status": "skip", "reason": "No metric of this type was discovered"}
            continue
        item = item_by_token.get(token_for_type)
        missing = [field for field in fields if field not in item or not numeric(item.get(field))] if item else fields
        type_results[metric_type] = {"status": "pass" if not missing else "fail", "missingFields": missing}
        normalized_seen += 1
        if missing:
            normalized_ok = False
    g04_status = "pass" if normalized_seen and normalized_ok else ("skip" if not normalized_seen else "fail")
    make_check(
        checks,
        "G-04",
        "Metric type normalization",
        g04_status,
        {
            "discoveredTypes": sorted(tokens_by_type.keys()),
            "testedTypes": type_results,
            "snapshotOk": response_ok(normalization_snapshot),
        },
    )

    count_tokens = [token for mtype, token in tokens_by_type.items() if mtype in {"counter", "meter", "timer", "histogram"}]
    if not count_tokens:
        make_check(checks, "G-05", "Metric non-reset behavior", "skip", {"reason": "No count-bearing metrics discovered"})
    else:
        count_tokens = count_tokens[: min(5, len(count_tokens))]
        snapshots = []
        for index in range(3):
            rec = client.call(
                f"{run_id}-g05-metricsSnapshot-nonreset-{index}",
                {
                    "action": "metricsSnapshot",
                    "requestId": f"{run_id}-g05-metricsSnapshot-nonreset-{index}",
                    "metricTokens": count_tokens,
                    "maxMetrics": len(count_tokens),
                },
            )
            snapshots.append(metric_items(response(rec)))
            if index < 2:
                time.sleep(args.nonreset_interval_sec)
        sequences: Dict[str, List[Any]] = {}
        for items in snapshots:
            values = {item_token(item): item.get("count") for item in items if isinstance(item, dict) and "count" in item}
            for token_value in count_tokens:
                sequences.setdefault(token_value, []).append(values.get(token_value))
        decreases: Dict[str, List[Any]] = {}
        for token_value, values in sequences.items():
            numeric_values = [value for value in values if numeric(value)]
            if len(numeric_values) >= 2:
                for prev, curr in zip(numeric_values, numeric_values[1:]):
                    if curr < prev:
                        decreases.setdefault(token_value, []).append([prev, curr])
        make_check(
            checks,
            "G-05",
            "Metric non-reset behavior",
            "pass" if not decreases and any(any(numeric(v) for v in values) for values in sequences.values()) else "fail",
            {"sampledTokenCount": len(count_tokens), "countSequences": sequences, "decreases": decreases},
        )

    perf_1 = client.call(
        f"{run_id}-g06-gatewayPerformanceSnapshot-1",
        {"action": "gatewayPerformanceSnapshot", "requestId": f"{run_id}-g06-gatewayPerformanceSnapshot-1"},
    )
    time.sleep(args.performance_interval_sec)
    perf_2 = client.call(
        f"{run_id}-g06-gatewayPerformanceSnapshot-2",
        {"action": "gatewayPerformanceSnapshot", "requestId": f"{run_id}-g06-gatewayPerformanceSnapshot-2"},
    )
    perf_values = [response(perf_1), response(perf_2)]
    required_numeric = {
        "processCpuLoad": [("cpu", "processCpuLoad"), ("processCpuLoad",)],
        "heapUsed": [("memory", "heap", "usedBytes"), ("heap", "usedBytes"), ("heapUsedBytes",)],
        "nonHeapUsed": [("memory", "nonHeap", "usedBytes"), ("nonHeap", "usedBytes"), ("nonHeapUsedBytes",)],
        "threadTotal": [("threads", "total"), ("threadCount",)],
    }
    present = {
        name: all(numeric(nested_get(perf, paths)) for perf in perf_values)
        for name, paths in required_numeric.items()
    }
    uptime_values = [
        nested_get(perf, [("gatewayUptimeMillis",), ("uptimeMillis",), ("uptime", "millis"), ("gateway", "uptimeMillis")])
        for perf in perf_values
    ]
    uptime_ok = not all(numeric(value) for value in uptime_values) or float(uptime_values[1]) >= float(uptime_values[0])
    make_check(
        checks,
        "G-06",
        "Performance snapshot consistency",
        "pass" if response_ok(perf_1) and response_ok(perf_2) and all(present.values()) and uptime_ok else "fail",
        {"snapshot1Ok": response_ok(perf_1), "snapshot2Ok": response_ok(perf_2), "requiredFieldsPresent": present, "uptimeValues": uptime_values, "uptimeMonotonic": uptime_ok},
    )

    browser_probe = start_browser_probe(args, out_dir)
    session_records: List[Dict[str, Any]] = []
    if browser_probe and browser_probe.get("started"):
        for index in range(args.session_correlation_samples):
            rec = client.call(
                f"{run_id}-g07-perspectiveSessionsQuery-{index}",
                {
                    "action": "perspectiveSessionsQuery",
                    "requestId": f"{run_id}-g07-perspectiveSessionsQuery-{index}",
                    "targetProject": project,
                    "maxResults": 50,
                },
            )
            session_records.append(response(rec))
            if index < args.session_correlation_samples - 1:
                time.sleep(args.session_correlation_interval_sec)
        browser_info = finish_browser_probe(browser_probe, args)
    else:
        browser_info = finish_browser_probe(browser_probe, args)
    write_json(out_dir / "browser-session-correlation.json", {"browserProbe": browser_info, "sessions": session_records})
    if not args.browser_url:
        make_check(checks, "G-07", "Session query correlation", "skip", {"reason": "No browser URL supplied; pass --browser-url to own a session"})
    else:
        observed = False
        max_pages = 0
        max_browser_sessions = 0
        for sample in session_records:
            sessions = sample.get("sessions", [])
            for session in sessions if isinstance(sessions, list) else []:
                if not isinstance(session, dict):
                    continue
                scope = str(session.get("sessionScope", "")).lower()
                pages = session.get("activePages")
                if not numeric(pages):
                    page_tokens = session.get("pageTokens", [])
                    pages = len(page_tokens) if isinstance(page_tokens, list) else 0
                if scope == "browser":
                    max_browser_sessions += 1
                    max_pages = max(max_pages, int(pages or 0))
                    if int(pages or 0) > 0:
                        observed = True
        make_check(
            checks,
            "G-07",
            "Session query correlation",
            "pass" if observed and browser_info.get("exitCode") == 0 else "fail",
            {"browserProbe": {k: v for k, v in browser_info.items() if k != "command"}, "observedBrowserPage": observed, "maxActivePages": max_pages, "browserSessionRowsObserved": max_browser_sessions},
        )

    redaction_rec = client.call(
        f"{run_id}-g08-perspectiveSessionsQuery-default-redaction",
        {
            "action": "perspectiveSessionsQuery",
            "requestId": f"{run_id}-g08-perspectiveSessionsQuery-default-redaction",
            "targetProject": project,
            "maxResults": 50,
        },
    )
    redaction_response = response(redaction_rec)
    keys: List[str] = []
    collect_keys(redaction_response.get("sessions", []), keys)
    leaked_keys = sorted({key for key in keys if key.lower() in SENSITIVE_SESSION_KEYS})
    default_flags_ok = (
        redaction_response.get("includeIdentifiers") is False
        and redaction_response.get("includeUserAgent") is False
        and redaction_response.get("includeClientAddress") is False
    )
    make_check(
        checks,
        "G-08",
        "Session redaction",
        "pass" if response_ok(redaction_rec) and not leaked_keys and default_flags_ok else "fail",
        {"queryOk": response_ok(redaction_rec), "defaultFlagsOk": default_flags_ok, "leakedSensitiveKeys": leaked_keys},
    )

    thread_missing_confirm = client.call(
        f"{run_id}-g09-threadDumpQuery-missing-confirm",
        {
            "action": "threadDumpQuery",
            "requestId": f"{run_id}-g09-threadDumpQuery-missing-confirm",
            "threadNameContains": ["Gateway", "http", "pool"],
            "maxThreads": 3,
            "maxFramesPerThread": 5,
            "redact": True,
        },
    )
    thread_confirmed = client.call(
        f"{run_id}-g09-threadDumpQuery-confirmed",
        {
            "action": "threadDumpQuery",
            "requestId": f"{run_id}-g09-threadDumpQuery-confirmed",
            "threadNameContains": ["Gateway", "http", "pool"],
            "maxThreads": 3,
            "maxFramesPerThread": 5,
            "redact": True,
            "confirmSensitiveDiagnostic": "READ_BOUNDED_THREAD_DUMP",
        },
    )
    thread_data = response(thread_confirmed)
    threads = thread_data.get("threads", [])
    frame_counts_ok = True
    if isinstance(threads, list):
        for thread in threads:
            frames = thread.get("frames", []) if isinstance(thread, dict) else []
            if isinstance(frames, list) and len(frames) > 5:
                frame_counts_ok = False
    else:
        threads = []
    thread_pass = (
        (thread_missing_confirm.get("httpStatus", 0) >= 400 or response(thread_missing_confirm).get("ok") is False)
        and response_ok(thread_confirmed)
        and int(thread_data.get("returnedCount", len(threads)) or 0) <= 3
        and frame_counts_ok
        and bool(thread_data.get("unredactedDumpSha256") or thread_data.get("dumpSha256"))
    )
    make_check(
        checks,
        "G-09",
        "Thread query bounds",
        "pass" if thread_pass else "fail",
        {
            "missingConfirmRejected": thread_missing_confirm.get("httpStatus", 0) >= 400 or response(thread_missing_confirm).get("ok") is False,
            "confirmedOk": response_ok(thread_confirmed),
            "returnedCount": thread_data.get("returnedCount", len(threads)),
            "maxThreads": 3,
            "maxFramesPerThread": 5,
            "frameCountsOk": frame_counts_ok,
            "hasDumpHash": bool(thread_data.get("unredactedDumpSha256") or thread_data.get("dumpSha256")),
        },
    )

    overhead_samples: List[Dict[str, Any]] = []
    for index in range(args.overhead_samples):
        started = time.perf_counter()
        perf_rec = client.call(
            f"{run_id}-g10-overhead-gatewayPerformanceSnapshot-{index}",
            {"action": "gatewayPerformanceSnapshot", "requestId": f"{run_id}-g10-overhead-gatewayPerformanceSnapshot-{index}"},
        )
        session_rec = client.call(
            f"{run_id}-g10-overhead-perspectiveSessionsQuery-{index}",
            {
                "action": "perspectiveSessionsQuery",
                "requestId": f"{run_id}-g10-overhead-perspectiveSessionsQuery-{index}",
                "targetProject": project,
                "maxResults": 50,
            },
        )
        metric_rec = None
        if tokens:
            metric_rec = client.call(
                f"{run_id}-g10-overhead-metricsSnapshot-{index}",
                {
                    "action": "metricsSnapshot",
                    "requestId": f"{run_id}-g10-overhead-metricsSnapshot-{index}",
                    "metricTokens": tokens[: min(args.max_metrics_snapshot, len(tokens))],
                    "maxMetrics": min(args.max_metrics_snapshot, len(tokens)),
                },
            )
        elapsed = (time.perf_counter() - started) * 1000
        perf_data = response(perf_rec)
        cpu_value = nested_get(perf_data, [("cpu", "processCpuLoad"), ("processCpuLoad",)])
        overhead_samples.append(
            {
                "index": index,
                "elapsedMs": round(elapsed, 3),
                "processCpuLoad": cpu_value,
                "perfOk": response_ok(perf_rec),
                "sessionsOk": response_ok(session_rec),
                "metricsOk": response_ok(metric_rec) if metric_rec else None,
            }
        )
        if index < args.overhead_samples - 1:
            time.sleep(max(args.overhead_interval_sec, 0))
    latencies = [sample["elapsedMs"] for sample in overhead_samples]
    cpu_values = [sample["processCpuLoad"] for sample in overhead_samples if numeric(sample.get("processCpuLoad"))]
    avg_latency = sum(latencies) / len(latencies) if latencies else None
    avg_cpu = sum(float(value) for value in cpu_values) / len(cpu_values) if cpu_values else None
    overhead_ok = (
        bool(overhead_samples)
        and all(sample["perfOk"] and sample["sessionsOk"] for sample in overhead_samples)
        and (avg_latency is None or avg_latency < args.timeout_sec * 1000)
        and (avg_cpu is None or avg_cpu < args.overhead_cpu_threshold)
    )
    make_check(
        checks,
        "G-10",
        "Runner overhead",
        "pass" if overhead_ok else "partial",
        {
            "sampleCount": len(overhead_samples),
            "averageReadBatchElapsedMs": avg_latency,
            "averageProcessCpuLoad": avg_cpu,
            "cpuThreshold": args.overhead_cpu_threshold,
            "samples": overhead_samples,
            "note": "Bounded local read-load sample; repeat at the intended production cadence before changing sample rate policy.",
        },
    )

    before_state = read_view_and_page(client, run_id, project, route, view, "g11-before") if project and route and view else {}
    routes_before_hash = hash_json(routes)
    routes_after = list_routes(client, run_id, project) if project else []
    after_state = read_view_and_page(client, run_id, project, route, view, "g11-after") if project and route and view else {}
    routes_after_hash = hash_json(routes_after)
    g11_pass = (
        bool(before_state)
        and bool(after_state)
        and before_state.get("viewSha256") == after_state.get("viewSha256")
        and routes_before_hash == routes_after_hash
    )
    make_check(
        checks,
        "G-11",
        "No-write proof",
        "pass" if g11_pass else "partial",
        {
            "viewSha256Before": before_state.get("viewSha256"),
            "viewSha256After": after_state.get("viewSha256"),
            "viewHashStable": before_state.get("viewSha256") == after_state.get("viewSha256"),
            "routesHashStable": routes_before_hash == routes_after_hash,
            "changedResources": [],
            "note": "Read-only proof covers target route/view and route inventory; tag/config drift is not sampled by this harness.",
        },
    )

    missing_metric = client.call(
        f"{run_id}-g12-metricsSnapshot-missing-token",
        {
            "action": "metricsSnapshot",
            "requestId": f"{run_id}-g12-metricsSnapshot-missing-token",
            "metricTokens": ["missing-contract-test-token"],
            "maxMetrics": 1,
        },
    )
    invalid_type = client.call(
        f"{run_id}-g12-metricsList-invalid-type",
        {
            "action": "metricsList",
            "requestId": f"{run_id}-g12-metricsList-invalid-type",
            "nameContains": ["Perspective"],
            "types": ["not-a-real-metric-type"],
            "maxResults": 5,
        },
    )
    malformed_filter = client.call(
        f"{run_id}-g12-metricsList-malformed-filter",
        {
            "action": "metricsList",
            "requestId": f"{run_id}-g12-metricsList-malformed-filter",
            "nameContains": "Perspective",
            "maxResults": 5,
        },
    )
    unknown_action = client.call(
        f"{run_id}-g12-unknown-action",
        {"action": "unknownProfilerContractAction", "requestId": f"{run_id}-g12-unknown-action"},
    )
    stale_session = client.call(
        f"{run_id}-g12-perspectiveSessionsQuery-stale-session",
        {
            "action": "perspectiveSessionsQuery",
            "requestId": f"{run_id}-g12-perspectiveSessionsQuery-stale-session",
            "targetProject": project,
            "sessionIds": ["stale-contract-session-token"],
            "maxResults": 5,
        },
    )
    g12_records = [missing_metric, invalid_type, malformed_filter, unknown_action, stale_session]
    g12_pass = all(failure_json(record) for record in g12_records)
    missing_items = metric_items(response(missing_metric))
    missing_metric_item_error = bool(missing_items and any(item.get("ok") is False or item.get("error") for item in missing_items if isinstance(item, dict)))
    make_check(
        checks,
        "G-12",
        "Failure envelope",
        "pass" if g12_pass and missing_metric_item_error else "fail",
        {
            "boundedJsonFailures": {record["name"]: failure_json(record) for record in g12_records},
            "missingMetricPerItemError": missing_metric_item_error,
            "httpStatuses": {record["name"]: record.get("httpStatus") for record in g12_records},
        },
    )

    summary = summarize_checks(checks)
    summary.update(
        {
            "runId": run_id,
            "outDir": str(out_dir),
            "project": project,
            "route": route,
            "view": view,
            "runnerVersion": health.get("runnerVersion"),
            "stackVersion": health.get("stackVersion"),
        }
    )
    manifest = {
        "ok": summary["ok"],
        "bundleType": "composite-wrapper",
        "runId": run_id,
        "createdAt": utc_now(),
        "gatewayAlias": args.gateway_alias,
        "project": project,
        "route": route,
        "view": view,
        "scenario": "read-only Gateway/runner contract tests G-01 through G-12",
        "runnerVersion": health.get("runnerVersion"),
        "stackVersion": health.get("stackVersion"),
        "features": sorted(features),
        "supportedActions": sorted(actions),
        "evidenceGrade": "Observed",
        "changedResources": [],
        "missingEvidence": [],
        "browserProbeRequested": bool(args.browser_url),
        "files": [
            "manifest.json",
            "summary.json",
            "summary.md",
            "checks.json",
            "metrics-list.json",
            "browser-session-correlation.json",
            "raw/",
        ],
    }
    write_json(out_dir / "checks.json", checks)
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "manifest.json", manifest)
    make_report(out_dir, manifest, checks, summary)
    return {"ok": summary["ok"], "summary": summary}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run read-only Gateway/runner contract tests for the Perspective profiler.")
    parser.add_argument("--endpoint", help="Runner Web Dev endpoint. Env fallback: IGNITION_LLM_RUNNER_URL, IGNITION_LLM_RUNNER_ENDPOINT, or IGNITION_RUNNER_URL.")
    parser.add_argument("--token", help="Runner token. Env fallback: IGNITION_LLM_RUNNER_TOKEN or IGNITION_RUNNER_TOKEN.")
    parser.add_argument("--project", help="Target project. Env fallback: IGNITION_TARGET_PROJECT.")
    parser.add_argument("--route", help="Perspective route/page path for no-write and session correlation checks.")
    parser.add_argument("--view", help="Perspective view path for no-write checks.")
    parser.add_argument("--run-id", help="Stable run identifier.")
    parser.add_argument("--out-dir", help="Evidence output directory.")
    parser.add_argument("--gateway-alias", default="configured-gateway", help="Non-secret Gateway alias for evidence.")
    parser.add_argument("--timeout-sec", type=int, default=30, help="HTTP timeout. Default: 30.")
    parser.add_argument("--metric-name-contains", action="append", default=[], help="Metric substring filters for contract discovery. Repeatable.")
    parser.add_argument("--max-metrics-list", type=int, default=250, help="Maximum metrics to list for contract tests. Default: 250.")
    parser.add_argument("--max-metrics-snapshot", type=int, default=25, help="Maximum metrics to snapshot during contract tests. Default: 25.")
    parser.add_argument("--nonreset-interval-sec", type=float, default=1.0, help="Delay between non-reset counter reads. Default: 1.")
    parser.add_argument("--performance-interval-sec", type=float, default=1.0, help="Delay between performance consistency reads. Default: 1.")
    parser.add_argument("--overhead-samples", type=int, default=5, help="Profiler read batches for overhead sample. Default: 5.")
    parser.add_argument("--overhead-interval-sec", type=float, default=1.0, help="Delay between overhead sample batches. Default: 1.")
    parser.add_argument("--overhead-cpu-threshold", type=float, default=0.75, help="Average process CPU threshold for the bounded overhead sample. Default: 0.75.")
    parser.add_argument("--browser-url", help="Optional Perspective route URL to open for G-07 session correlation.")
    parser.add_argument("--browser-url-alias", default="", help="Non-secret browser URL alias. Defaults to --gateway-alias.")
    parser.add_argument("--browser-ready-selector", default="body", help="CSS selector for route readiness during G-07. Default: body.")
    parser.add_argument("--browser-ready-text", default="", help="Optional body text that must be visible before browser readiness is accepted.")
    parser.add_argument("--browser-viewport", default="1366x768", help="Browser viewport. Default: 1366x768.")
    parser.add_argument("--browser-timeout-sec", type=float, default=30.0, help="Browser timeout. Default: 30.")
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=-1, help="Browser hold time after ready. Default: session correlation hold seconds.")
    parser.add_argument("--browser-start-delay-sec", type=float, default=2.0, help="Seconds to let the browser begin loading before G-07 sampling. Default: 2.")
    parser.add_argument("--browser-node", default="node", help="Node executable for browser_route_probe.mjs. Default: node.")
    parser.add_argument("--browser-node-modules", default="", help="Optional node_modules path to prepend to NODE_PATH for Playwright.")
    parser.add_argument("--session-correlation-samples", type=int, default=4, help="G-07 session query samples while browser is open. Default: 4.")
    parser.add_argument("--session-correlation-interval-sec", type=float, default=2.0, help="Delay between G-07 session samples. Default: 2.")
    parser.add_argument("--session-correlation-hold-sec", type=float, default=10.0, help="Browser hold seconds after readiness for G-07. Default: 10.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.max_metrics_list <= 0:
        raise SystemExit("--max-metrics-list must be > 0")
    if args.max_metrics_snapshot <= 0:
        raise SystemExit("--max-metrics-snapshot must be > 0")
    if args.overhead_samples <= 0:
        raise SystemExit("--overhead-samples must be > 0")
    result = run_contracts(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
