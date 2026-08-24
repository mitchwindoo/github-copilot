#!/usr/bin/env python3
"""Build an Ignition module bug/release source-routing plan from gatewayInfo JSON."""

import argparse
import json
import re
import sys
from pathlib import Path


IA_RELEASE_NOTES_URL = "https://inductiveautomation.com/downloads/releasenotes"
CHARIOT_8X_NOTES_URL = (
    "https://docs.chariot.io/display/CLD80/"
    "Ignition%2B8.x%2BCompatible%2BRelease%2BNotes"
)
SEPASOFT_81_RELEASE_NOTES_URL = (
    "https://www.sepasoft.com/downloads/release-notes-ignition-8-1/"
)
SEPASOFT_ARCHIVE_SEARCH_URL = (
    "https://docs.sepasoft.com/articles/mes-3-0-modules-download-archive-publication/"
)


def fail(message):
    print(json.dumps({"ok": False, "error": message}, indent=2, sort_keys=True))
    return 2


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def first_version(value):
    match = re.search(r"\b(\d+\.\d+\.\d+)\b", str(value or ""))
    return match.group(1) if match else ""


def load_json(path):
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def extract_modules(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError("input JSON must be an object or a module list")
    modules_value = data.get("modules")
    if isinstance(modules_value, dict) and isinstance(modules_value.get("modules"), list):
        return modules_value["modules"]
    if isinstance(modules_value, list):
        return modules_value
    gateway_info = data.get("gatewayInfo")
    if isinstance(gateway_info, dict):
        return extract_modules(gateway_info)
    raise ValueError("could not find modules list; expected gatewayInfo.modules.modules[]")


def target_version_from(data, explicit):
    if explicit:
        return first_version(explicit)
    if isinstance(data, dict):
        for key in ("ignitionVersion", "targetIgnitionVersion"):
            found = first_version(data.get(key))
            if found:
                return found
    return ""


def clean_module(module):
    if not isinstance(module, dict):
        raise ValueError("module rows must be JSON objects")
    return {
        "moduleId": str(module.get("moduleId") or module.get("id") or "").strip(),
        "moduleName": str(module.get("moduleName") or module.get("name") or "").strip(),
        "moduleVersion": str(module.get("moduleVersion") or module.get("version") or "").strip(),
        "moduleState": str(module.get("moduleState") or module.get("state") or "").strip(),
        "moduleLicenseStatus": str(module.get("moduleLicenseStatus") or "").strip(),
        "moduleVersionSource": str(module.get("moduleVersionSource") or "").strip(),
    }


def is_ia(module):
    return normalize(module.get("moduleId")).startswith("com.inductiveautomation.")


def is_cirrus(module):
    haystack = normalize("%s %s" % (module.get("moduleId"), module.get("moduleName")))
    needles = [
        "cirruslink",
        "cirrus link",
        "chariot",
        "mqtt engine",
        "mqtt transmission",
        "mqtt distributor",
        "mqtt recorder",
        "aws injector",
        "azure injector",
        "google cloud injector",
        "efm abb totalflow",
        "efm emerson roc",
        "opto22 groov",
    ]
    return any(needle in haystack for needle in needles)


def is_sepasoft(module):
    haystack = normalize("%s %s" % (module.get("moduleId"), module.get("moduleName")))
    needles = [
        "com.sepasoft",
        "sepasoft",
        "production module",
        "mes production",
        "oee downtime",
        "batch procedure",
        "track & trace",
        "track and trace",
        "spc",
        "settings & changeover",
        "document management",
        "business connector",
        "web services",
        "interface for sap",
    ]
    return any(needle in haystack for needle in needles)


def cirrus_family(module):
    haystack = normalize("%s %s" % (module.get("moduleId"), module.get("moduleName")))
    mapping = [
        ("MQTT Engine", ["mqtt engine", ".mqtt.engine"]),
        ("MQTT Transmission", ["mqtt transmission", ".mqtt.transmission"]),
        ("MQTT Distributor", ["mqtt distributor", ".mqtt.distributor"]),
        ("MQTT Recorder", ["mqtt recorder", ".mqtt.recorder"]),
        ("AWS Injector", ["aws injector", ".aws"]),
        ("Azure Injector", ["azure injector", ".azure"]),
        ("Google Cloud Injector", ["google cloud injector", ".google"]),
        ("EFM ABB Totalflow", ["efm abb totalflow", "totalflow"]),
        ("EFM Emerson ROC", ["efm emerson roc", "emerson roc"]),
        ("Opto22 groov EPIC and SNAPPAC Driver", ["opto22 groov", "snappac"]),
    ]
    for family, needles in mapping:
        if any(needle in haystack for needle in needles):
            return family
    return "Cirrus Link module"


def sepasoft_family(module):
    haystack = normalize("%s %s" % (module.get("moduleId"), module.get("moduleName")))
    mapping = [
        ("Production Module", ["production module", "mes production"]),
        ("OEE Downtime", ["oee downtime"]),
        ("Batch Procedure", ["batch procedure"]),
        ("Track & Trace", ["track & trace", "track and trace"]),
        ("SPC", ["spc"]),
        ("Settings & Changeover", ["settings & changeover"]),
        ("Document Management", ["document management"]),
        ("Business Connector", ["business connector"]),
        ("Web Services", ["web services"]),
        ("Interface for SAP ERP", ["interface for sap"]),
    ]
    for family, needles in mapping:
        if any(needle in haystack for needle in needles):
            return family
    return module.get("moduleName") or "Sepasoft module"


def vendor_hint(module):
    module_id = module.get("moduleId") or ""
    parts = [part for part in module_id.split(".") if part]
    if len(parts) >= 2 and parts[0] == "com":
        return parts[1]
    if parts:
        return parts[0]
    return module.get("moduleName") or "vendor"


def route_modules(modules, target_ignition_version):
    clean_modules = [clean_module(module) for module in modules]
    exact_ia_url = (
        "%s/%s" % (IA_RELEASE_NOTES_URL, target_ignition_version)
        if target_ignition_version
        else ""
    )
    cirrus_versions = sorted(
        {
            module["moduleVersion"]
            for module in clean_modules
            if is_cirrus(module) and module["moduleVersion"]
        }
    )
    cirrus_version_mismatch = len(cirrus_versions) > 1

    routes = []
    for module in clean_modules:
        version = module["moduleVersion"]
        base = dict(module)
        base.update(
            {
                "targetIgnitionVersion": target_ignition_version,
                "moduleVersionEvidenceRequired": not bool(version),
                "currentSourceCheckRequired": True,
            }
        )
        if is_cirrus(module):
            family = cirrus_family(module)
            base.update(
                {
                    "vendorRoute": "Cirrus Link / Chariot",
                    "family": family,
                    "sourceUrls": [CHARIOT_8X_NOTES_URL],
                    "searchRequired": False,
                    "sourceConfidence": "high for route; browse current page before bug claims",
                    "versionMismatch": cirrus_version_mismatch,
                    "nonEmptyCirrusVersionsSeen": cirrus_versions,
                    "suggestedQueries": [
                        "%s %s Ignition 8.x release notes"
                        % (family, version or "module version"),
                        "%s %s known issue Ignition" % (family, version or ""),
                    ],
                    "boundary": (
                        "Use installed moduleVersion and family first; treat later source "
                        "blocks as later-fix evidence, not installed-version confirmation."
                    ),
                }
            )
        elif is_sepasoft(module):
            base.update(
                {
                    "vendorRoute": "Sepasoft",
                    "family": sepasoft_family(module),
                    "sourceUrls": [SEPASOFT_81_RELEASE_NOTES_URL, SEPASOFT_ARCHIVE_SEARCH_URL],
                    "searchRequired": False,
                    "sourceConfidence": "high for route; browse current pages before bug claims",
                    "versionMismatch": False,
                    "suggestedQueries": [
                        "Sepasoft %s %s Ignition 8.1 release notes"
                        % (sepasoft_family(module), version or ""),
                        "Sepasoft %s %s highest tested Ignition version"
                        % (sepasoft_family(module), version or ""),
                    ],
                    "boundary": (
                        "Record highest-tested and minimum-required Ignition evidence from "
                        "current Sepasoft pages when available."
                    ),
                }
            )
        elif is_ia(module):
            urls = [url for url in [exact_ia_url, IA_RELEASE_NOTES_URL] if url]
            base.update(
                {
                    "vendorRoute": "Inductive Automation",
                    "family": module["moduleName"] or module["moduleId"],
                    "sourceUrls": urls,
                    "searchRequired": False,
                    "sourceConfidence": "high for route; browse current release notes before bug claims",
                    "versionMismatch": False,
                    "suggestedQueries": [
                        "Ignition %s %s %s release notes"
                        % (target_ignition_version or "8.1", module["moduleName"], version),
                        "site:forum.inductiveautomation.com %s %s"
                        % (module["moduleName"], version or target_ignition_version or "Ignition"),
                    ],
                    "boundary": (
                        "Exact target-version release-note URL is target evidence; root/latest "
                        "release notes are current context only."
                    ),
                }
            )
        else:
            hint = vendor_hint(module)
            base.update(
                {
                    "vendorRoute": "Unknown third-party vendor",
                    "family": module["moduleName"] or module["moduleId"],
                    "sourceUrls": [],
                    "searchRequired": True,
                    "sourceConfidence": "unknown until official vendor source is found",
                    "versionMismatch": False,
                    "suggestedQueries": [
                        "%s %s Ignition 8.1 release notes" % (module["moduleName"], version),
                        "%s Ignition module %s support known issues" % (hint, module["moduleName"]),
                    ],
                    "boundary": (
                        "Find official vendor release notes, docs, support KB, or forum evidence "
                        "before making version-specific bug claims."
                    ),
                }
            )
        routes.append(base)
    return routes


def summarize(routes):
    counts = {}
    for route in routes:
        counts[route["vendorRoute"]] = counts.get(route["vendorRoute"], 0) + 1
    return {
        "moduleCount": len(routes),
        "routesByVendor": counts,
        "searchRequiredCount": sum(1 for route in routes if route["searchRequired"]),
        "missingModuleVersionCount": sum(1 for route in routes if route["moduleVersionEvidenceRequired"]),
        "cirrusVersionMismatch": any(
            route.get("versionMismatch") for route in routes if route["vendorRoute"] == "Cirrus Link / Chariot"
        ),
    }


def build_result(data, ignition_version):
    modules = extract_modules(data)
    target_ignition_version = target_version_from(data, ignition_version)
    routes = route_modules(modules, target_ignition_version)
    return {
        "ok": True,
        "source": "IgnitionModuleSourceRoutingPlan",
        "targetIgnitionVersion": target_ignition_version,
        "iaReleaseNotesRootUrl": IA_RELEASE_NOTES_URL,
        "exactIaReleaseNotesUrl": (
            "%s/%s" % (IA_RELEASE_NOTES_URL, target_ignition_version)
            if target_ignition_version
            else ""
        ),
        "routeSourceUrls": {
            "inductiveAutomation": IA_RELEASE_NOTES_URL,
            "cirrusChariot": CHARIOT_8X_NOTES_URL,
            "sepasoftReleaseNotes": SEPASOFT_81_RELEASE_NOTES_URL,
            "sepasoftArchive": SEPASOFT_ARCHIVE_SEARCH_URL,
        },
        "summary": summarize(routes),
        "routes": routes,
        "boundary": (
            "This is a routing plan only. Browse current vendor sources before claiming "
            "a specific bug, fix, latest version, or compatibility status."
        ),
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", help="gatewayInfo response JSON or a JSON module list.")
    parser.add_argument("--ignition-version", help="Override/seed target Ignition version, for example 8.1.53.")
    parser.add_argument("--json-out", help="Optional path to write the JSON result.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data = load_json(args.json_path)
        result = build_result(data, args.ignition_version)
    except Exception as exc:
        return fail(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
