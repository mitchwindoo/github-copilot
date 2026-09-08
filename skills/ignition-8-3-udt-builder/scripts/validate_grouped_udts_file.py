#!/usr/bin/env python3
"""Validate an Ignition 8.3 grouped tag-type-definition udts.json file."""

import argparse
import json
from pathlib import Path

from validate_tag_payload import validate_node


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("grouped_file", type=Path)
    args = parser.parse_args()
    try:
        with args.grouped_file.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "errors": [f"root: invalid JSON: {error}"]}, indent=2))
        raise SystemExit(1)

    errors = []
    if not isinstance(payload, list):
        errors.append("root: grouped udts.json requires an array of UdtType objects")
    elif not payload:
        errors.append("root: grouped udts.json must contain at least one UdtType")
    else:
        names = set()
        for index, node in enumerate(payload):
            location = f"root[{index}]"
            validate_node(node, location, errors)
            if isinstance(node, dict):
                if node.get("tagType") != "UdtType":
                    errors.append(f"{location}.tagType: grouped file entries must be UdtType")
                name = node.get("name")
                if isinstance(name, str):
                    if name in names:
                        errors.append(f"{location}.name: duplicate grouped UDT name {name!r}")
                    names.add(name)

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "groupedUdtCount": len(payload)}, indent=2))


if __name__ == "__main__":
    main()
