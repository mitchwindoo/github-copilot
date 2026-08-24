#!/usr/bin/env python3
"""Portable HTTP client helpers for the approved Ignition runner API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_TIMEOUT_SECONDS = 30
RAW_BODY_RECORD_LIMIT = 4096
SENSITIVE_RECORD_KEYS = {
    "authorization",
    "cookie",
    "identitytoken",
    "packagebase64",
    "passwd",
    "password",
    "scriptbase64",
    "set-cookie",
    "sourcecodebase64",
    "token",
    "username",
    "x-llm-runner-token",
}


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def runner_url() -> str:
    return env_required("IGNITION_RUNNER_URL")


def runner_token() -> str:
    return env_required("IGNITION_RUNNER_TOKEN")


def target_project(default: str = "") -> str:
    return os.environ.get("IGNITION_TARGET_PROJECT", default).strip()


def timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def default_run_dir(prefix: str) -> Path:
    safe_prefix = "".join(
        char if char.isalnum() or char in "._-" else "-" for char in prefix.strip()
    ).strip(".-")
    if not safe_prefix:
        raise ValueError("run directory prefix must contain a letter or number")
    configured_root = os.environ.get("IGNITION_RUNNER_OUTPUT_DIR", "").strip()
    root = (
        Path(configured_root).expanduser()
        if configured_root
        else Path.cwd() / "ignition-vision-runs"
    )
    path = root / f"{safe_prefix}_{timestamp()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, child in value.items():
            if key.lower() in SENSITIVE_RECORD_KEYS:
                out[key] = "<redacted>"
            else:
                out[key] = redact(child)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class RunnerClient:
    def __init__(self, endpoint: str, token: str, run_dir: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.endpoint = endpoint
        self.token = token
        self.run_dir = run_dir
        self.timeout = timeout
        self.counter = 0
        self.summary = {
            "endpointConfigured": bool(endpoint),
            "runDir": str(run_dir),
            "steps": [],
        }

    def post(self, name: str, payload: Dict[str, Any], auth: bool = True, raw_body: Optional[bytes] = None) -> Dict[str, Any]:
        return self.request("POST", name, payload, auth=auth, raw_body=raw_body)

    def request(
        self,
        method: str,
        name: str,
        payload: Dict[str, Any],
        auth: bool = True,
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        self.counter += 1
        method = method.upper()
        payload = dict(payload)
        payload.setdefault("requestId", f"{name.upper()}-{self.counter:02d}")
        body = raw_body if raw_body is not None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["X-LLM-Runner-Token"] = self.token
        request = urllib.request.Request(self.endpoint, data=body, headers=headers, method=method)
        record: Dict[str, Any] = {
            "name": name,
            "method": method,
            "requestId": payload.get("requestId", ""),
            "request": redact(payload),
        }
        if raw_body is not None:
            record["rawRequestBodyLength"] = len(raw_body)
            record["rawRequestBodyRecorded"] = False
            record["rawRequestBodyRecordLimit"] = RAW_BODY_RECORD_LIMIT
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", "replace")
                record["httpStatus"] = response.status
                record["response"] = redact(_decode_response(raw))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            record["httpStatus"] = exc.code
            record["response"] = redact(_decode_response(raw))
        except Exception as exc:  # pragma: no cover - evidence should retain transport failures.
            record["error"] = repr(exc)

        path = self.run_dir / f"{self.counter:02d}_{name}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        response_obj = record.get("response", {})
        if not isinstance(response_obj, dict):
            response_obj = {}
        self.summary["steps"].append({
            "name": name,
            "requestId": payload.get("requestId", ""),
            "httpStatus": record.get("httpStatus"),
            "ok": response_obj.get("ok"),
            "runnerVersion": response_obj.get("runnerVersion"),
            "error": response_obj.get("error") or record.get("error"),
            "file": str(path),
        })
        return record

    def save_summary(self) -> Path:
        path = self.run_dir / "summary.json"
        path.write_text(json.dumps(self.summary, indent=2, sort_keys=True), encoding="utf-8")
        return path


def _decode_response(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw}
