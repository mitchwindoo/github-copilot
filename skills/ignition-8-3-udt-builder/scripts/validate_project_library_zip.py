#!/usr/bin/env python3
"""Validate an Ignition project ZIP that contains Project Library scripts."""

import argparse
import json
import zipfile
from pathlib import Path, PurePosixPath


SCRIPT_ROOT = PurePosixPath("ignition/script-python")


def validate(path):
    errors = []
    try:
        archive = zipfile.ZipFile(path, "r")
    except (OSError, zipfile.BadZipFile) as error:
        return [f"root: invalid ZIP: {error}"]
    with archive:
        names = [item.filename for item in archive.infolist() if not item.is_dir()]
        name_set = set(names)
        if len(names) != len(name_set):
            errors.append("root: duplicate ZIP entry names")
        for name in names:
            if "\\" in name:
                errors.append(f"{name}: ZIP entry must use forward slashes")
            parts = PurePosixPath(name).parts
            if ".." in parts or (parts and parts[0] == ""):
                errors.append(f"{name}: unsafe ZIP entry path")
            if name.endswith(".class") or "$py.class" in name:
                errors.append(f"{name}: compiled Jython/Python files must not be packaged")
        if "project.json" not in name_set:
            errors.append("root: missing project.json")

        resource_names = sorted(
            name for name in names
            if name.startswith(str(SCRIPT_ROOT) + "/") and name.endswith("/resource.json")
        )
        resource_dirs = [PurePosixPath(name).parent for name in resource_names]
        if not resource_dirs:
            errors.append("ignition/script-python: no script resources found")
        for resource_name, resource_dir in zip(resource_names, resource_dirs):
            code_name = str(resource_dir / "code.py")
            if code_name not in name_set:
                errors.append(f"{resource_name}: missing sibling code.py")
            try:
                resource = json.loads(archive.read(resource_name).decode("utf-8"))
            except (KeyError, UnicodeError, json.JSONDecodeError) as error:
                errors.append(f"{resource_name}: invalid JSON: {error}")
                continue
            if resource.get("files") != ["code.py"]:
                errors.append(f"{resource_name}.files: expected exactly ['code.py']")
            if resource.get("scope") != "G":
                errors.append(f"{resource_name}.scope: expected 'G'")
            if resource.get("version") != 1:
                errors.append(f"{resource_name}.version: expected 1")
            for other_dir in resource_dirs:
                if other_dir != resource_dir and resource_dir in other_dir.parents:
                    errors.append(
                        f"{resource_name}: script resources must be leaves; contains descendant resource {other_dir}/resource.json"
                    )
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_zip", type=Path)
    args = parser.parse_args()
    errors = validate(args.project_zip)
    result = {"ok": not errors, "errors": errors}
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
