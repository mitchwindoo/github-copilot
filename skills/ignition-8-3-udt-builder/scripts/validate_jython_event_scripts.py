#!/usr/bin/env python3
"""Compile Ignition tag event-script bodies with a caller-selected Jython jar."""

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def collect_event_scripts(value, location="root"):
    found = []
    if isinstance(value, dict):
        scripts = value.get("eventScripts")
        if isinstance(scripts, list):
            for index, event in enumerate(scripts):
                if isinstance(event, dict) and isinstance(event.get("script"), str):
                    found.append((f"{location}.eventScripts[{index}]", event["script"]))
        for key, child in value.items():
            if key != "eventScripts":
                found.extend(collect_event_scripts(child, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(collect_event_scripts(child, f"{location}[{index}]"))
    return found


def build_wrapper(scripts):
    chunks = ["# Generated only for Jython syntax compilation.\n"]
    for index, (location, script) in enumerate(scripts):
        chunks.append(f"# {location}\n")
        chunks.append(f"def event_{index}(*args, **kwargs):\n")
        chunks.append(script)
        if not script.endswith("\n"):
            chunks.append("\n")
        chunks.append("\n")
    return "".join(chunks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    parser.add_argument("--jython-jar", required=True, type=Path)
    parser.add_argument("--java", default="java")
    args = parser.parse_args()

    try:
        with args.payload.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "errors": [f"payload: {error}"]}, indent=2))
        raise SystemExit(1)

    java = args.java
    if Path(java).is_file():
        java = str(Path(java).resolve())
    elif shutil.which(java) is None:
        print(json.dumps({"ok": False, "errors": [f"java executable not found: {java}"]}, indent=2))
        raise SystemExit(1)
    if not args.jython_jar.is_file():
        print(json.dumps({"ok": False, "errors": [f"Jython jar not found: {args.jython_jar}"]}, indent=2))
        raise SystemExit(1)

    scripts = collect_event_scripts(payload)
    wrapper = build_wrapper(scripts)
    with tempfile.TemporaryDirectory(prefix="ignition-jython-event-") as temp_dir:
        wrapper_path = Path(temp_dir) / "event_scripts_compile.py"
        wrapper_path.write_text(wrapper, encoding="utf-8", newline="\n")
        completed = subprocess.run(
            [java, "-jar", str(args.jython_jar.resolve()), "-S", str(wrapper_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    result = {
        "ok": completed.returncode == 0,
        "scriptCount": len(scripts),
        "locations": [location for location, _ in scripts],
        "compiler": "Jython jar",
        "exitCode": completed.returncode,
    }
    if completed.returncode != 0:
        result["errors"] = [line for line in (completed.stderr or completed.stdout).splitlines() if line.strip()]
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
