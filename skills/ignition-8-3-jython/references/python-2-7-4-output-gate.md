# Jython 2.7.4 output gate

Use this gate before returning or installing generated Ignition code. It supplements the detailed rules in `SKILL.md`; it does not replace scope-specific Ignition testing.

## Contents

- [Pin the target](#1-pin-the-target)
- [Audit for Python 3 drift](#2-audit-for-python-3-drift)
- [Compile with Jython 2.7.4](#3-compile-with-jython-274)
- [Review semantics the compiler cannot catch](#4-review-semantics-the-compiler-cannot-catch)
- [Run the permanent regression set](#5-run-the-permanent-regression-set)
- [Final response contract](#6-final-response-contract)

## 1. Pin the target

Record all three facts:

- Ignition version: `8.3.8`
- script runtime: `Jython 2.7.4` with Python 2.7 semantics
- exact execution scope: Gateway, Perspective, Vision, tag event, alarm pipeline, project library, Web Dev, or Designer

If any fact is unknown, stop and discover it. Do not silently target CPython or Python 3.

Keep the three runtime roles separate:

| Role | Required runtime | What it proves |
| --- | --- | --- |
| Host drift scan | A pinned, verified CPython 3 executable | Only the bundled auditor's bounded static findings |
| Target syntax gate | The verified Jython 2.7.4 standalone JAR | Compile-only acceptance or rejection under the target language runtime |
| Target behavior | Ignition 8.3.8 embedded Jython 2.7.4 in the exact script scope | Only the focused imports, APIs, resources, permissions, and behavior actually exercised |

Using CPython 3 for the host-only scan never authorizes Python 3 syntax, module names, APIs, packaging, or semantics in generated Ignition code.

## 2. Audit for Python 3 drift

Pin a CPython 3 executable, verify its implementation and major version, and run the read-only host auditor against each draft:

```powershell
$jythonAuditPython = "C:\path\to\verified\python.exe"
& $jythonAuditPython -c "import platform, sys; assert platform.python_implementation() == 'CPython' and sys.version_info[0] == 3"
& $jythonAuditPython scripts\audit_python3_drift.py path\to\draft.py
```

Use the same verified executable for the auditor's `--self-test`. The auditor checks the maintained Python 3-only syntax families, including async forms, unpacking extensions, `except*`, parenthesized `with`/decorator forms, and type-alias/type-parameter syntax, plus tested Python 3 module spellings, selected absent modern APIs, zero-argument `super()`, and a small set of ambiguous text-I/O patterns. A clean result is only a bounded static first pass; it cannot prove the complete grammar, receiver types, imports, Java overloads, Ignition scope, permissions, or runtime behavior.

The bundled host auditor is intentionally incomplete. It does not currently flag `list.copy()`, `collections.abc` import or attribute use, or dictionary union such as `left | right`; review those manually and keep `python3-api-guardrails-v1` in the applicable embedded regression set. A clean host audit cannot waive the Jython compile, semantic, import, scope, or runtime gates.

## 3. Compile with Jython 2.7.4

Run the compile-only gate with a verified Jython 2.7.4 runtime:

```powershell
java -jar path\to\jython-standalone-2.7.4.jar scripts\jython_compile_gate.py --self-test
java -jar path\to\jython-standalone-2.7.4.jar scripts\jython_compile_gate.py path\to\draft.py
```

The gate decodes UTF-8 source and calls `compile(..., "exec")`; it does not execute target code or import its dependencies. Its self-test contains 29 fixed Python 3-invalid cases and 25 accepted controls. Acceptance of legacy Python 2 spellings is syntax recognition, not a recommendation to generate backticks, comma exception/raise syntax, `<>`, legacy octal, print statements, or tuple parameters. A successful compile is necessary but not sufficient.

## 4. Review semantics the compiler cannot catch

- Use `unicode` for internal human-readable text and explicit `.encode(codec)`/`.decode(codec)` at byte boundaries.
- Account for `int` and `long`, Python 2 integer division, eager `range`/`map`/`filter`/`zip`, `xrange`, list-returning `dict.items()`, two-argument `super`, and mutable-default persistence.
- Use verified Python 2 module spellings. Do not add Python 3/Python 2 fallback chains to a fixed Jython target.
- Validate every non-Ignition import and required member. Do not infer pip, a binary wheel, C-extension support, NumPy, pandas, dataclasses, or a modern backport.
- Validate every `system.*` function in the exact execution scope, then validate resource names, authorization, input schema, result/quality semantics, limits, and cleanup.
- Treat Java class presence, dependency version, overload resolution, callback lifetime, and returned Java collection behavior as target facts requiring focused evidence.

## 5. Run the permanent regression set

When the local fixed-action API is available, keep these actions passing after relevant skill or API changes:

- `runtime-profile-v2`
- `python2-guardrails-v1`
- `python2-module-names-v1`
- `python3-api-guardrails-v1`
- `builtin-surface-v1`
- `text-byte-boundaries-v1`
- `import-fallback-guardrails-v1`

`builtin-surface-v1` keeps the eager Python 2 `map`/`filter`/`zip`, `map(None, ...)` padding, `reduce`, Python 2 built-in names, and `__builtin__`/`builtins` distinction inside the permanent floor. These actions accept no caller-provided code. They prove only their fixed matrices. Do not turn them into a general claim that all Python 2 code, packages, or Ignition scopes are compatible.

## 6. Final response contract

Before returning code, state:

- target and execution scope;
- static-audit result;
- Jython compile result;
- imports and target evidence;
- positive and negative runtime checks;
- untested boundaries.

Do not label a draft production-ready if either gate was unavailable or any scope/import/runtime boundary remains unverified.

Use this compact response shape:

```markdown
Target: Ignition 8.3.8 / Jython 2.7.4
Scope: <exact execution scope>

Compatibility gates:
- Python 3 drift audit: <passed, failed, or not run>
- Jython 2.7.4 compile: <passed, failed, or not run>

Dependencies and boundaries:
- Imports/Java classes: <verified facts and source>
- Ignition resources/permissions: <verified facts>
- Untested: <every remaining boundary>

Verification:
- Positive: <case and result>
- Negative: <case and result>
- Completion/readback: <what proves success, or not applicable>
```

Replace every placeholder. If a gate was not run, say why and keep the code labeled as a draft.
