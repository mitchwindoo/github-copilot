#!/usr/bin/env python3
"""Collect a read-only Perspective performance evidence bundle.

The collector orchestrates existing runner actions. It does not write Gateway
resources, open browser sessions, capture thread dumps, or claim causality.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_METRIC_CONTAINS = ["Perspective", "perspective"]
REQUIRED_PERF_ACTIONS = [
    "metricsList",
    "metricsSnapshot",
    "gatewayPerformanceSnapshot",
    "perspectiveSessionsQuery",
]
REQUIRED_PERF_FEATURE_FLAGS = [
    "perspectiveSessionsQueryMatchedCount",
]
REQUIRED_PERF_FEATURES = REQUIRED_PERF_ACTIONS + REQUIRED_PERF_FEATURE_FLAGS
SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "packagebase64",
    "scriptbase64",
    "sourcecodebase64",
    "x-llm-runner-token",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def epoch_millis() -> int:
    return int(time.time() * 1000)


def slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    text = text.strip("-._")
    return text or "profile"


def raw_file_name(counter: int, name: str) -> str:
    clean = slug(name)
    if len(clean) > 44:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        clean = f"{clean[:31].rstrip('-._')}-{digest}"
    return f"{counter:02d}-{clean}.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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


def enabled_name_set(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key, enabled in value.items() if enabled}
    if isinstance(value, list):
        return {str(item) for item in value}
    return set()


def runner_capabilities(health: Dict[str, Any]) -> Tuple[set[str], set[str]]:
    feature_set = enabled_name_set(health.get("features", []))
    action_set = enabled_name_set(health.get("supportedActions", []))
    return feature_set, action_set


def supports_action(action_set: set[str], feature_set: set[str], action: str) -> bool:
    return action in action_set or (not action_set and action in feature_set)


class RunnerClient:
    def __init__(self, endpoint: str, token: str, out_dir: Path, timeout: int) -> None:
        self.endpoint = endpoint
        self.token = token
        self.out_dir = out_dir
        self.timeout = timeout
        self.counter = 0
        self.raw_dir = out_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def call(self, name: str, payload: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
        self.counter += 1
        payload = dict(payload)
        payload.setdefault("requestId", name)
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json", "X-LLM-Runner-Token": self.token},
            method="POST",
        )
        record: Dict[str, Any] = {
            "name": name,
            "request": redact(payload),
            "startedAt": utc_now(),
        }
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
                record["httpStatus"] = response.status
                record["response"] = parse_json(text)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            record["httpStatus"] = exc.code
            record["response"] = parse_json(text)
        except Exception as exc:
            record["error"] = repr(exc)
            record["response"] = {"ok": False, "error": repr(exc)}
        record["finishedAt"] = utc_now()
        record["response"] = redact(record.get("response"))
        path = self.raw_dir / raw_file_name(self.counter, name)
        write_json(path, record)
        return record


def parse_json(text: str) -> Any:
    try:
        return json.loads(text) if text.strip() else {}
    except Exception:
        return {"raw": text}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n")


def append_ndjson(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def response(record: Dict[str, Any]) -> Dict[str, Any]:
    data = record.get("response", {})
    return data if isinstance(data, dict) else {}


def ok(record: Dict[str, Any]) -> bool:
    data = response(record)
    return bool(record.get("httpStatus", 0) < 400 and data.get("ok") is not False)


def ensure_profile_function():
    path = SCRIPT_DIR / "view_lint.py"
    spec = importlib.util.spec_from_file_location("perfprof_view_lint", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load view_lint.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.profile


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


def metric_tokens(metrics_response: Dict[str, Any], max_metrics: int) -> List[str]:
    tokens: List[str] = []
    for item in metrics_response.get("metrics", []):
        if not isinstance(item, dict):
            continue
        token = str(item.get("token", "")).strip()
        if token:
            tokens.append(token)
        if len(tokens) >= max_metrics:
            break
    return tokens


def write_missing_browser_files(out_dir: Path, reason: str) -> List[Dict[str, str]]:
    missing = []
    for name in ["browser-summary.json", "browser-console.json", "network-summary.json"]:
        path = out_dir / name
        write_json(path, {"ok": False, "missing": True, "reason": reason})
        missing.append({"file": name, "reason": reason})
    return missing


def browser_wait_after_ms(args: argparse.Namespace) -> int:
    if args.browser_wait_after_ready_ms >= 0:
        return args.browser_wait_after_ready_ms
    return int(max(args.duration_sec + args.interval_sec, 1) * 1000)


def build_browser_command(args: argparse.Namespace, out_dir: Path) -> List[str]:
    command = [
        args.browser_node,
        str(SCRIPT_DIR / "browser_route_probe.mjs"),
        "--url",
        args.browser_url,
        "--out-dir",
        str(out_dir),
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
    if args.browser_secondary_ready_selector:
        command.extend(["--secondary-ready-selector", args.browser_secondary_ready_selector])
    if args.browser_secondary_ready_text:
        command.extend(["--secondary-ready-text", args.browser_secondary_ready_text])
    if args.browser_click_selector:
        command.extend(["--click-selector", args.browser_click_selector])
    if args.browser_click_text:
        command.extend(["--click-text", args.browser_click_text])
    if args.browser_click_label:
        command.extend(["--click-label", args.browser_click_label])
    if args.browser_click_after_ready_delay_ms:
        command.extend(["--click-after-ready-delay-ms", str(args.browser_click_after_ready_delay_ms)])
    if args.browser_click_repeat_count and args.browser_click_repeat_count != 1:
        command.extend(["--click-repeat-count", str(args.browser_click_repeat_count)])
    if args.browser_click_repeat_interval_ms:
        command.extend(["--click-repeat-interval-ms", str(args.browser_click_repeat_interval_ms)])
    if args.browser_click_repeat_mode and args.browser_click_repeat_mode != "playwright":
        command.extend(["--click-repeat-mode", args.browser_click_repeat_mode])
    if args.browser_click_result_selector:
        command.extend(["--click-result-selector", args.browser_click_result_selector])
    if args.browser_click_result_text:
        command.extend(["--click-result-text", args.browser_click_result_text])
    if args.browser_click_timeout_sec:
        command.extend(["--click-timeout-ms", str(int(args.browser_click_timeout_sec * 1000))])
    if args.browser_post_interaction_wait_ms:
        command.extend(["--post-interaction-wait-ms", str(args.browser_post_interaction_wait_ms)])
    if args.browser_network_throttle_after_ready:
        command.append("--network-throttle-after-ready")
    if args.browser_network_latency_ms:
        command.extend(["--network-latency-ms", str(args.browser_network_latency_ms)])
    if args.browser_network_download_kbps:
        command.extend(["--network-download-kbps", str(args.browser_network_download_kbps)])
    if args.browser_network_upload_kbps:
        command.extend(["--network-upload-kbps", str(args.browser_network_upload_kbps)])
    if args.browser_timeline_sample_interval_ms:
        command.extend(["--timeline-sample-interval-ms", str(args.browser_timeline_sample_interval_ms)])
    if args.browser_user_data_dir:
        command.extend(["--user-data-dir", args.browser_user_data_dir])
    if args.browser_watch_text_selector:
        command.extend(["--watch-text-selector", args.browser_watch_text_selector])
    if args.browser_watch_text_regex:
        command.extend(["--watch-text-regex", args.browser_watch_text_regex])
    if args.browser_watch_text_label:
        command.extend(["--watch-text-label", args.browser_watch_text_label])
    if args.browser_watch_text_timeout_sec:
        command.extend(["--watch-text-timeout-ms", str(int(args.browser_watch_text_timeout_sec * 1000))])
    return command


def redact_browser_command(command: List[str]) -> List[str]:
    redacted = list(command)
    for index, value in enumerate(redacted[:-1]):
        if value == "--url":
            redacted[index + 1] = "<redacted-browser-url>"
        elif value == "--browser-node-modules":
            redacted[index + 1] = "<redacted-node-modules>"
        elif value == "--user-data-dir":
            redacted[index + 1] = "<redacted-user-data-dir>"
        elif value in ("--click-text", "--click-result-text", "--secondary-ready-text", "--watch-text-regex"):
            redacted[index + 1] = "<redacted-text>"
    return redacted


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


def start_browser_probe(args: argparse.Namespace, out_dir: Path) -> Optional[Dict[str, Any]]:
    if not args.browser_url:
        return None
    stdout_path = out_dir / "browser-probe.stdout.txt"
    stderr_path = out_dir / "browser-probe.stderr.txt"
    command = build_browser_command(args, out_dir)
    stdout_handle = stdout_path.open("w", encoding="utf-8", newline="\n")
    stderr_handle = stderr_path.open("w", encoding="utf-8", newline="\n")
    try:
        process = subprocess.Popen(command, stdout=stdout_handle, stderr=stderr_handle, env=browser_env(args))
    except Exception as exc:
        stdout_handle.close()
        stderr_handle.close()
        write_json(out_dir / "browser-summary.json", {"ok": False, "error": repr(exc), "missing": True})
        write_json(out_dir / "browser-console.json", [])
        write_json(out_dir / "network-summary.json", {"ok": False, "error": repr(exc), "missing": True})
        return {
            "started": False,
            "error": repr(exc),
            "command": redact_browser_command(command),
            "stdoutPath": str(stdout_path),
            "stderrPath": str(stderr_path),
        }
    time.sleep(max(args.browser_start_delay_sec, 0))
    return {
        "started": True,
        "process": process,
        "stdoutHandle": stdout_handle,
        "stderrHandle": stderr_handle,
        "command": redact_browser_command(command),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
        "startedAt": utc_now(),
    }


def finish_browser_probe(browser_probe: Optional[Dict[str, Any]], args: argparse.Namespace, out_dir: Path) -> Dict[str, Any]:
    if not browser_probe:
        return {"started": False, "reason": "Browser probe not requested"}
    process = browser_probe.get("process")
    if process is None:
        return {key: value for key, value in browser_probe.items() if key not in {"stdoutHandle", "stderrHandle"}}
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
            handle = browser_probe.get(key)
            if handle:
                handle.close()
    info = {key: value for key, value in browser_probe.items() if key not in {"process", "stdoutHandle", "stderrHandle"}}
    info.update({"exitCode": exit_code, "timedOut": timed_out, "finishedAt": utc_now()})
    for name in ["browser-summary.json", "browser-console.json", "network-summary.json"]:
        if not (out_dir / name).exists():
            write_json(out_dir / name, {"ok": False, "missing": True, "reason": "Browser probe did not write this file"})
    return info


def make_report(out_dir: Path, manifest: Dict[str, Any], static_profile: Dict[str, Any], summary: Dict[str, Any]) -> None:
    lines = [
        "# Perspective Performance Profile",
        "",
        f"Run ID: `{manifest['runId']}`",
        f"Evidence grade: `{manifest['evidenceGrade']}`",
        f"Project: `{manifest.get('project') or '<not set>'}`",
        f"Route: `{manifest.get('route') or '<not selected>'}`",
        f"View: `{manifest.get('view') or '<not selected>'}`",
        "",
        "## Direct Observations",
        "",
        f"- Runner: `{manifest.get('runnerVersion', '<unknown>')}` / `{manifest.get('stackVersion', '<unknown>')}`.",
        f"- Samples collected: `{summary.get('sampleCount', 0)}`.",
        f"- Metric tokens sampled: `{summary.get('metricTokenCount', 0)}`.",
        f"- Static component count: `{static_profile.get('summary', {}).get('componentCount', '<missing>')}`.",
        f"- Static binding count: `{static_profile.get('summary', {}).get('bindingCount', '<missing>')}`.",
        "",
        "## Candidate Static Risks",
        "",
    ]
    risks = static_profile.get("riskSignals", [])
    if risks:
        for item in risks[:20]:
            lines.append(f"- `{item.get('severity', 'info')}` `{item.get('code', 'unknown')}`: {item.get('message', '')}")
    else:
        lines.append("- No static risk signals were reported.")
    lines.extend(
        [
            "",
            "## Missing Evidence",
            "",
        ]
    )
    missing = manifest.get("missingEvidence", [])
    if missing:
        for item in missing:
            lines.append(f"- `{item.get('name', item.get('file', 'evidence'))}`: {item.get('reason', '')}")
    else:
        lines.append("- None recorded.")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This read-only collector produces observed and correlated evidence only. Do not claim a root cause or improvement until an identical A/B or before/after run proves it.",
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect a read-only Perspective performance evidence bundle.")
    parser.add_argument("--endpoint", help="Runner Web Dev endpoint. Env fallback: IGNITION_LLM_RUNNER_URL, IGNITION_LLM_RUNNER_ENDPOINT, or IGNITION_RUNNER_URL.")
    parser.add_argument("--token", help="Runner token. Env fallback: IGNITION_LLM_RUNNER_TOKEN or IGNITION_RUNNER_TOKEN.")
    parser.add_argument("--project", help="Target project. Env fallback: IGNITION_TARGET_PROJECT.")
    parser.add_argument("--route", help="Perspective route/page path. If omitted, the first discovered route with a view is used.")
    parser.add_argument("--view", help="Perspective view path. If omitted, the route's view is used.")
    parser.add_argument("--run-id", help="Stable run identifier.")
    parser.add_argument("--out-dir", help="Evidence output directory.")
    parser.add_argument("--duration-sec", type=float, default=10.0, help="Runtime sample duration. Default: 10.")
    parser.add_argument("--interval-sec", type=float, default=2.0, help="Runtime sample interval. Default: 2.")
    parser.add_argument("--max-metrics", type=int, default=25, help="Maximum metric tokens to sample. Default: 25.")
    parser.add_argument("--metric-name-contains", action="append", default=[], help="Metric substring filter. Repeatable.")
    parser.add_argument("--metric-prefix", action="append", default=[], help="Metric prefix filter. Repeatable.")
    parser.add_argument("--timeout-sec", type=int, default=30, help="HTTP timeout. Default: 30.")
    parser.add_argument("--gateway-alias", default="configured-gateway", help="Non-secret Gateway alias for manifest.")
    parser.add_argument("--scenario", default="read-only route profile", help="Scenario label for manifest.")
    parser.add_argument("--browser-url", help="Optional Perspective route URL to probe in parallel with Gateway samples.")
    parser.add_argument("--browser-ready-selector", default='[data-testid="perf-ready"]', help="CSS selector for browser readiness. Use body only when no better stable marker exists.")
    parser.add_argument("--browser-ready-text", default="", help="Optional body text that must be visible before browser readiness is accepted.")
    parser.add_argument("--browser-secondary-ready-selector", default="", help="Optional second selector for total-ready timing after primary readiness.")
    parser.add_argument("--browser-secondary-ready-text", default="", help="Optional second body text for total-ready timing after primary readiness.")
    parser.add_argument("--browser-viewport", default="1366x768", help="Browser viewport for the route probe. Default: 1366x768.")
    parser.add_argument("--browser-timeout-sec", type=float, default=30.0, help="Browser route probe timeout. Default: 30.")
    parser.add_argument("--browser-wait-after-ready-ms", type=int, default=-1, help="Browser collection time after ready. Default: sample duration plus one interval.")
    parser.add_argument("--browser-start-delay-sec", type=float, default=1.5, help="Seconds to let the browser begin loading before Gateway sampling. Default: 1.5.")
    parser.add_argument("--browser-node", default="node", help="Node executable for browser_route_probe.mjs. Default: node.")
    parser.add_argument("--browser-node-modules", default="", help="Optional node_modules path to prepend to NODE_PATH for Playwright.")
    parser.add_argument("--browser-url-alias", default="", help="Non-secret browser URL alias recorded in browser evidence. Defaults to --gateway-alias.")
    parser.add_argument("--browser-click-selector", default="", help="Optional selector to click after browser route readiness for R-04 interaction latency.")
    parser.add_argument("--browser-click-text", default="", help="Optional text filter for the click target. Redacted from stored command evidence.")
    parser.add_argument("--browser-click-label", default="", help="Non-secret interaction label for reports.")
    parser.add_argument("--browser-click-after-ready-delay-ms", type=int, default=0, help="Delay after route readiness before clicking. Default: 0.")
    parser.add_argument("--browser-click-repeat-count", type=int, default=1, help="Dispatch the configured browser click this many times. Default: 1.")
    parser.add_argument("--browser-click-repeat-interval-ms", type=int, default=0, help="Delay between repeated browser clicks. Default: 0.")
    parser.add_argument("--browser-click-repeat-mode", default="playwright", choices=["playwright", "mouse", "dom"], help="Repeated click dispatch mode. Default: playwright.")
    parser.add_argument("--browser-click-result-selector", default="", help="Selector that must become visible after click.")
    parser.add_argument("--browser-click-result-text", default="", help="Body text that must appear after click. Redacted from stored command evidence.")
    parser.add_argument("--browser-click-timeout-sec", type=float, default=10.0, help="Click/result timeout. Default: 10.")
    parser.add_argument("--browser-post-interaction-wait-ms", type=int, default=0, help="Keep browser session open after click evidence. Default: 0.")
    parser.add_argument("--browser-network-throttle-after-ready", action="store_true", help="Apply browser network throttle after primary readiness instead of before navigation.")
    parser.add_argument("--browser-network-latency-ms", type=float, default=0.0, help="Optional browser network latency for Chromium CDP. Default: 0.")
    parser.add_argument("--browser-network-download-kbps", type=float, default=0.0, help="Optional browser download throughput cap in kbps. Default: 0.")
    parser.add_argument("--browser-network-upload-kbps", type=float, default=0.0, help="Optional browser upload throughput cap in kbps. Default: 0.")
    parser.add_argument("--browser-timeline-sample-interval-ms", type=int, default=0, help="Optional browser timeline sample interval during wait-after-ready. Default: 0.")
    parser.add_argument("--browser-user-data-dir", default="", help="Optional persistent Chromium profile/cache directory for warm-load evidence. Redacted from stored command evidence.")
    parser.add_argument("--browser-watch-text-selector", default="", help="Optional selector whose text must change after browser click.")
    parser.add_argument("--browser-watch-text-regex", default="", help="Optional watched-text regex; first capture group is compared and redacted from stored command evidence.")
    parser.add_argument("--browser-watch-text-label", default="", help="Non-secret label for watched text in browser evidence.")
    parser.add_argument("--browser-watch-text-timeout-sec", type=float, default=10.0, help="Watched-text change timeout. Default: 10.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.duration_sec < 0:
        raise SystemExit("--duration-sec must be >= 0")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be > 0")
    if args.browser_click_repeat_count < 1:
        raise SystemExit("--browser-click-repeat-count must be >= 1")
    if args.browser_click_repeat_interval_ms < 0:
        raise SystemExit("--browser-click-repeat-interval-ms must be >= 0")
    if args.browser_network_latency_ms < 0:
        raise SystemExit("--browser-network-latency-ms must be >= 0")
    if args.browser_network_download_kbps < 0:
        raise SystemExit("--browser-network-download-kbps must be >= 0")
    if args.browser_network_upload_kbps < 0:
        raise SystemExit("--browser-network-upload-kbps must be >= 0")
    endpoint, token, project = resolve_config(args)
    run_id = args.run_id or f"PERFPROFILE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out_dir = Path(args.out_dir) if args.out_dir else Path.cwd() / "perf-profile-runs" / slug(run_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = RunnerClient(endpoint, token, out_dir, args.timeout_sec)
    profile_view = ensure_profile_function()
    missing: List[Dict[str, str]] = []

    health_record = client.call(f"{run_id}-health", {"action": "health", "requestId": f"{run_id}-health"})
    health = response(health_record)
    feature_set, action_set = runner_capabilities(health)

    gateway_record = client.call(f"{run_id}-gatewayInfo", {"action": "gatewayInfo", "requestId": f"{run_id}-gatewayInfo"})
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
        {"action": "routesList", "requestId": f"{run_id}-routesList", "targetProject": project, "maxResults": 250},
    )
    routes = response(routes_record).get("routes", [])
    route, view = choose_route(routes if isinstance(routes, list) else [], args.route or "", args.view or "")
    if not view:
        raise SystemExit("Target view could not be resolved from route inventory. Use --view.")

    views_record = client.call(
        f"{run_id}-viewsList",
        {"action": "viewsList", "requestId": f"{run_id}-viewsList", "targetProject": project, "maxResults": 250},
    )
    view_record = client.call(
        f"{run_id}-viewRead",
        {
            "action": "viewRead",
            "requestId": f"{run_id}-viewRead",
            "targetProject": project,
            "viewPath": view,
            "allowedViewPrefix": "",
            "includeViewJson": True,
            "includeResourceJson": True,
        },
    )
    page_record = client.call(
        f"{run_id}-pageValidate",
        {
            "action": "pageValidate",
            "requestId": f"{run_id}-pageValidate",
            "targetProject": project,
            "pagePath": route or args.route or "",
            "expectedViewPath": view,
            "allowedRoutePrefix": "",
            "allowedViewPrefix": "",
            "includeHashes": True,
        },
    )

    view_response = response(view_record)
    write_json(out_dir / "view-read.json", view_response)
    static_profile = profile_view(view_response, "view-read.json")
    write_json(out_dir / "static-profile.json", static_profile)

    browser_probe = start_browser_probe(args, out_dir)

    metric_filters = args.metric_name_contains or DEFAULT_METRIC_CONTAINS
    metrics_list_record: Optional[Dict[str, Any]] = None
    tokens: List[str] = []
    if supports_action(action_set, feature_set, "metricsList"):
        metrics_payload: Dict[str, Any] = {
            "action": "metricsList",
            "requestId": f"{run_id}-metricsList",
            "nameContains": metric_filters,
            "maxResults": min(max(args.max_metrics * 3, args.max_metrics), 250),
        }
        if args.metric_prefix:
            metrics_payload["namePrefixes"] = args.metric_prefix
        metrics_list_record = client.call(f"{run_id}-metricsList", metrics_payload)
        write_json(out_dir / "metrics-list.json", response(metrics_list_record))
        tokens = metric_tokens(response(metrics_list_record), max(0, min(args.max_metrics, 100)))
        if not tokens:
            missing.append({"name": "metricsSnapshot", "reason": "metricsList returned no metric tokens for the configured filters"})
    else:
        missing.append({"name": "metricsList", "reason": "runner health.supportedActions does not include metricsList"})

    sample_count = int(math.floor(args.duration_sec / args.interval_sec)) + 1 if args.duration_sec > 0 else 1
    for index in range(sample_count):
        started = utc_now()
        gateway_sample: Dict[str, Any] = {"sampleIndex": index, "startedAt": started}
        if tokens and supports_action(action_set, feature_set, "metricsSnapshot"):
            metric_record = client.call(
                f"{run_id}-metricsSnapshot-{index:03d}",
                {
                    "action": "metricsSnapshot",
                    "requestId": f"{run_id}-metricsSnapshot-{index:03d}",
                    "metricTokens": tokens,
                    "maxMetrics": len(tokens),
                },
            )
            gateway_sample["metricsSnapshot"] = response(metric_record)
        elif not supports_action(action_set, feature_set, "metricsSnapshot"):
            gateway_sample["metricsSnapshot"] = {"ok": False, "missing": True, "reason": "action not present"}

        if supports_action(action_set, feature_set, "gatewayPerformanceSnapshot"):
            perf_record = client.call(
                f"{run_id}-gatewayPerformanceSnapshot-{index:03d}",
                {"action": "gatewayPerformanceSnapshot", "requestId": f"{run_id}-gatewayPerformanceSnapshot-{index:03d}"},
            )
            gateway_sample["gatewayPerformanceSnapshot"] = response(perf_record)
        else:
            gateway_sample["gatewayPerformanceSnapshot"] = {"ok": False, "missing": True, "reason": "action not present"}
        gateway_sample["finishedAt"] = utc_now()
        append_ndjson(out_dir / "gateway-samples.ndjson", gateway_sample)

        session_sample: Dict[str, Any] = {"sampleIndex": index, "startedAt": started}
        if supports_action(action_set, feature_set, "perspectiveSessionsQuery"):
            session_record = client.call(
                f"{run_id}-perspectiveSessionsQuery-{index:03d}",
                {
                    "action": "perspectiveSessionsQuery",
                    "requestId": f"{run_id}-perspectiveSessionsQuery-{index:03d}",
                    "targetProject": project,
                    "maxResults": 50,
                },
            )
            session_sample["perspectiveSessionsQuery"] = response(session_record)
        else:
            session_sample["perspectiveSessionsQuery"] = {"ok": False, "missing": True, "reason": "action not present"}
        session_sample["finishedAt"] = utc_now()
        append_ndjson(out_dir / "perspective-session-samples.ndjson", session_sample)

        if index < sample_count - 1:
            time.sleep(args.interval_sec)

    log_record = client.call(
        f"{run_id}-logQuery",
        {
            "action": "logQuery",
            "requestId": f"{run_id}-logQuery",
            "sinceMinutes": 10,
            "levels": ["ERROR", "WARN"],
            "textContains": "Perspective",
            "maxResults": 50,
            "tailBytes": 262144,
        },
    )
    write_json(out_dir / "logs.json", response(log_record))
    write_json(out_dir / "thread-excerpts.json", {"ok": False, "missing": True, "reason": "No active freeze/backlog/CPU-spike trigger requested"})
    write_json(out_dir / "comparison.json", {"ok": False, "missing": True, "reason": "No A/B or before/after comparison requested"})
    browser_probe_info = finish_browser_probe(browser_probe, args, out_dir)
    if not args.browser_url:
        missing.extend(write_missing_browser_files(out_dir, "Browser probe not requested; pass --browser-url for render evidence"))
    elif browser_probe_info.get("exitCode") not in [0, None]:
        missing.append({"name": "browserProbe", "reason": "Browser probe exited non-zero; inspect browser-summary.json and browser-probe.stderr.txt"})

    for action in REQUIRED_PERF_ACTIONS:
        if not supports_action(action_set, feature_set, action):
            missing.append({"name": action, "reason": "runner health.supportedActions does not include this action"})
    for feature in REQUIRED_PERF_FEATURE_FLAGS:
        if feature not in feature_set:
            missing.append({"name": feature, "reason": "runner health.features does not include this feature flag"})

    summary = {
        "ok": True,
        "runId": run_id,
        "project": project,
        "route": route,
        "view": view,
        "sampleCount": sample_count,
        "metricTokenCount": len(tokens),
        "outDir": str(out_dir),
        "healthOk": ok(health_record),
        "viewReadOk": ok(view_record),
        "pageValidateOk": ok(page_record),
        "metricsListOk": ok(metrics_list_record) if metrics_list_record else False,
        "browserProbe": browser_probe_info,
    }
    write_json(out_dir / "summary.json", summary)

    manifest = {
        "ok": True,
        "runId": run_id,
        "createdAt": utc_now(),
        "gatewayAlias": args.gateway_alias,
        "project": project,
        "route": route,
        "view": view,
        "scenario": args.scenario,
        "sampleIntervalSeconds": args.interval_sec,
        "sampleDurationSeconds": args.duration_sec,
        "sampleCount": sample_count,
        "runnerVersion": health.get("runnerVersion"),
        "stackVersion": health.get("stackVersion"),
        "features": sorted(feature_set),
        "supportedActions": sorted(action_set),
        "gatewayInfoCaptured": ok(gateway_record),
        "routesCaptured": ok(routes_record),
        "viewsCaptured": ok(views_record),
        "viewSha256": view_response.get("viewSha256") or static_profile.get("viewSha256"),
        "staticProfileSha256": static_profile.get("viewSha256"),
        "staticProfileFileSha256": sha256_file(out_dir / "static-profile.json"),
        "evidenceGrade": "Observed",
        "changedResources": [],
        "missingEvidence": missing,
        "browserProbe": browser_probe_info,
        "files": [
            "manifest.json",
            "summary.json",
            "view-read.json",
            "static-profile.json",
            "metrics-list.json",
            "gateway-samples.ndjson",
            "perspective-session-samples.ndjson",
            "browser-summary.json",
            "browser-console.json",
            "network-summary.json",
            "logs.json",
            "thread-excerpts.json",
            "comparison.json",
            "report.md",
            "raw/",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)
    make_report(out_dir, manifest, static_profile, summary)
    print(json.dumps({"ok": True, "runId": run_id, "outDir": str(out_dir), "summary": summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
