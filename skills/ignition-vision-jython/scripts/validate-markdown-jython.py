#!/usr/bin/env python
"""Compile fenced Jython snippets in Markdown without executing them."""

import sys


def fenced_blocks(text):
    """Return fenced Jython blocks without requiring the optional Jython stdlib."""
    blocks = []
    current = None
    for line in text.splitlines():
        marker = line.strip()
        if current is None:
            if marker == "```jython":
                current = []
        elif marker == "```":
            blocks.append("\n".join(current))
            current = None
        else:
            current.append(line)
    return blocks


def validate(path):
    handle = open(path, "rb")
    try:
        text = handle.read()
    finally:
        handle.close()
    if not isinstance(text, str):
        text = text.decode("utf-8")
    elif hasattr(text, "decode"):
        text = text.decode("utf-8")
    blocks = fenced_blocks(text)
    failures = []
    for index, source in enumerate(blocks, 1):
        label = "%s#jython-%s" % (path, index)
        try:
            compile(source, label, "exec")
        except Exception as exc:
            failures.append("%s: %s" % (label, exc))
    return len(blocks), failures


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: validate-markdown-jython.py FILE.md [FILE.md ...]\n")
        return 2
    total = 0
    failures = []
    for path in argv[1:]:
        count, path_failures = validate(path)
        total += count
        failures.extend(path_failures)
    for failure in failures:
        sys.stderr.write(failure + "\n")
    if total == 0:
        sys.stderr.write("no fenced jython snippets found\n")
        return 1
    if failures:
        sys.stderr.write("FAIL snippets=%s failures=%s\n" % (total, len(failures)))
        return 1
    print("PASS snippets=%s" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
