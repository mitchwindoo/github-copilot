#!/usr/bin/env python3
"""Create a read-only Vision resource manifest for export/import planning."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runner_client import RunnerClient, default_run_dir, runner_token, runner_url, target_project  # noqa: E402


def main() -> int:
    project = target_project()
    if not project:
        raise SystemExit("IGNITION_TARGET_PROJECT is required")
    run_dir = default_run_dir("vision-export-validation")
    client = RunnerClient(runner_url(), runner_token(), run_dir)

    health_record = client.post("health", {"action": "health"})
    health = _response(health_record)
    required_actions = {
        "projectResourcesList",
        "projectResourceRead",
        "projectResourceExport",
    }
    available_actions = set(health.get("supportedActions", []))
    if health.get("ok") is not True or not required_actions.issubset(available_actions):
        client.save_summary()
        missing = sorted(required_actions - available_actions)
        raise SystemExit(
            "Runner health/capability gate failed; missing actions: " + ", ".join(missing)
        )

    listing = client.post("project_resources_list", {
        "action": "projectResourcesList",
        "targetProject": project,
        "resourcePrefix": "com.inductiveautomation.vision",
        "allowedResourcePrefix": "com.inductiveautomation.vision",
        "includeFiles": True,
        "maxResults": 1000,
    })

    manifest = {
        "targetProject": project,
        "resourcePrefix": "com.inductiveautomation.vision",
        "categoryCounts": {},
        "resources": [],
        "notes": [
            "Read-only manifest for planning. It is not a project export.",
            "Gateway dependencies such as tags, database connections, image libraries, users, roles, and alarm journals must be validated separately.",
        ],
    }
    response = _response(listing)
    for item in response.get("items", []):
        if item.get("type") != "resource":
            continue
        resource_path = item.get("resourcePath", "")
        category = _resource_category(resource_path)
        manifest["categoryCounts"][category] = manifest["categoryCounts"].get(category, 0) + 1
        record = client.post("read_" + _safe_name(resource_path), {
            "action": "projectResourceRead",
            "targetProject": project,
            "resourcePath": resource_path,
            "allowedResourcePrefix": "com.inductiveautomation.vision",
            "includeResourceJson": True,
            "includeHashes": True,
            "includeText": False,
        })
        read_response = _response(record)
        export_record = client.post("export_" + _safe_name(resource_path), {
            "action": "projectResourceExport",
            "targetProject": project,
            "resourcePath": resource_path,
            "allowedResourcePrefix": "com.inductiveautomation.vision",
            "includePackageBase64": False,
            "maxFiles": 200,
            "maxBytes": 5 * 1024 * 1024,
        })
        export_response = _response(export_record)
        manifest["resources"].append({
            "resourcePath": resource_path,
            "category": category,
            "ok": read_response.get("ok"),
            "fileCount": read_response.get("fileCount"),
            "files": read_response.get("files", []),
            "hasResourceJson": "resourceJson" in read_response,
            "exportOk": export_response.get("ok"),
            "exportFileCount": export_response.get("fileCount"),
            "exportZipBytes": export_response.get("zipBytes"),
            "exportZipSha256": export_response.get("zipSha256"),
        })

    manifest["resourceCount"] = len(manifest["resources"])
    manifest_path = run_dir / "vision-resource-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    summary_path = client.save_summary()
    checks = {
        "healthOk": health.get("ok") is True,
        "requiredActionsAvailable": required_actions.issubset(available_actions),
        "listingOk": response.get("ok") is True,
        "manifestWritten": manifest_path.exists(),
        "allReadsOk": all(item.get("ok") is True for item in manifest["resources"]),
        "allExportsOk": all(item.get("exportOk") is True for item in manifest["resources"]),
        "allExportsHashed": all(len(str(item.get("exportZipSha256") or "")) == 64 and int(item.get("exportZipBytes") or 0) > 0 for item in manifest["resources"]),
        "categoryCountsWritten": isinstance(manifest.get("categoryCounts"), dict),
    }
    (run_dir / "checks.json").write_text(json.dumps(checks, indent=2, sort_keys=True), encoding="utf-8")
    print(f"runDir={run_dir}")
    print(f"summary={summary_path}")
    print(f"manifest={manifest_path}")
    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 1


def _response(record: dict) -> dict:
    response = record.get("response", {})
    return response if isinstance(response, dict) else {}


def _safe_name(value: str) -> str:
    out = []
    for ch in value:
        if ch.isalnum():
            out.append(ch.lower())
        else:
            out.append("_")
    return "".join(out).strip("_")[:80] or "resource"


def _resource_category(resource_path: str) -> str:
    normalized = resource_path.lower().replace("\\", "/")
    if "/windows" in normalized or normalized.endswith("/windows"):
        return "window"
    if "/templates" in normalized or normalized.endswith("/templates"):
        return "template"
    if "client-tags" in normalized:
        return "client-tags"
    if "client-event" in normalized or "event-script" in normalized:
        return "client-event-script"
    return "other"


if __name__ == "__main__":
    raise SystemExit(main())
