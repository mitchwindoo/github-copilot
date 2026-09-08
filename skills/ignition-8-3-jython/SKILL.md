---
name: ignition-8-3-jython
description: Write and review Jython 2.7.4 scripts for Ignition 8.3.8. Use for Gateway, Perspective, Vision, tag, alarm, database, project-library, Web Dev, or Python compatibility work.
---

# Write Ignition Jython

Skill version: `0.49.0`

Write scripts for Ignition 8.3.8's Jython 2.7.4 runtime. Treat the execution scope and installed modules as part of the script contract.

## Stop Python 3 drift before output

Before returning, saving, or installing any generated `.py` code:

1. State `Ignition 8.3.8`, `Jython 2.7.4 / Python 2.7 semantics`, and the exact execution scope.
2. Run `scripts/audit_python3_drift.py` against the draft. Resolve every finding; do not dismiss a finding merely because the code works in CPython 3.
3. Run `scripts/jython_compile_gate.py` with a verified Jython 2.7.4 runtime. Its `--self-test` must pass, and the draft must compile without being executed.
4. Review the Python 2 runtime semantics, imports, third-party dependencies, Java boundaries, and Ignition scope rules that a syntax compiler cannot prove.
5. Run the applicable focused positive and negative runtime checks. Keep the permanent Python 2/Python 3 fixed-action regression set passing when the local API is available.
6. Report any unavailable gate or untested boundary. Never label an uncompiled or scope-unverified draft production-ready.

Read `references/python-2-7-4-output-gate.md` for the exact commands, maintained regression actions, and final response contract. The host auditor is a bounded first pass, not a parser/runtime guarantee; the Jython compile gate is a syntax check, not import or Ignition behavior proof.

When translating a Python 3-oriented request, example, or draft, read `references/python-2-7-4-patterns.md`. Use its replacements only when their narrower contracts match; never treat a syntax rewrite as proof of scope, dependency, Java, or Ignition behavior.

## Follow the workflow

1. Identify the execution scope: Gateway event, tag event, alarm pipeline, Perspective, Vision, project library, named query, Web Dev, or Designer console.
2. Discover the available project resources, tag providers, database connections, modules, and object schemas instead of guessing names.
3. State inputs, outputs, side effects, permissions, timing, and retry behavior before writing code.
4. Write Python 2.7-compatible syntax and use Ignition APIs available in the identified scope.
5. Separate pure transformation logic from Ignition reads, writes, and UI calls so the logic can be tested independently.
6. Design a focused positive case and negative case. Prefer a supported test runner or disposable fixture; otherwise provide exact manual verification steps.
7. For writes, preserve each per-item result, reject pending or bad results, perform an independent qualified readback, and report partial failure explicitly. Do not claim success from a returned call or matching value alone.

## Apply the non-negotiable generation gate

Treat generated code as a draft until every applicable item below is satisfied:

- Name the target as Ignition 8.3.8 running Jython 2.7.4 and name the execution scope. Never silently target CPython or Python 3.
- Reject Python 3-only syntax and APIs. In particular, do not emit f-strings, `async def`/`async for`/`async with`/`await` or async comprehensions, annotations or type-parameter/type-alias syntax, `nonlocal`, `yield from`, keyword-only or positional-only parameters, repeated positional call unpacking, dictionary/set/tuple literal unpacking, assignment expressions, `match`/`case`, `except*`, exception chaining with `raise ... from`, parenthesized `with` items, parenthesized decorator expressions, starred list literals or assignment targets, matrix multiplication, numeric separators, `builtins`, or an unverified modern standard-library name.
- Verify every non-Ignition import in the target scope. Treat import as code execution; a probe name, discovery hit, or successful import is not package-support proof. Require exact identity, required members, focused behavior, and a deployment contract. Do not invent pip or `ensurepip` installation steps, assume NumPy/pandas/dataclasses, or recommend a CPython binary wheel or C extension as ordinary Jython code.
- Preserve Python 2 semantics deliberately: `unicode` versus `str`, `long`, `basestring`, integer division, eager `range`/`map`/`filter`/`zip`, `xrange`, and two-argument `super` where applicable.
- Verify each `system.*` call is legal in the named Gateway, Perspective, Vision, event, or Designer scope. Name availability alone is not permission or behavior proof.
- Treat Java class availability, dependency version, overload selection, and returned collection behavior as target-scope facts that require a focused probe. Do not infer them from an upstream Jython release or an installed filename.
- Treat every callable signature as an API contract: positional arity and order, keyword names, required/defaulted parameters, accepted types, return shape, and side effects. Do not infer compatibility merely because the module, function, or method name still exists.
- Treat every returned value as an exact API contract before using it: top-level type, required and allowed keys, schema/generation, field types and null policy, status, quality, completeness, expected count, item identity/order, and error/effect meaning. Never infer success from truthiness, a non-empty collection, or a present value.
- Put explicit limits and cleanup around I/O, queries, loops, returned data, threads, and retries. For writes, validate exact request/result counts, preserve index-to-item mapping, handle pending/bad/partial results, and read back the intended result with acceptable quality.
- When evidence is missing, label the point unproven and provide a bounded discovery or verification step. Do not fill the gap with Python 3, CPython, Java, or Ignition assumptions.

## Run the basic Jython 2.7.4 checklist before every script

- Confirm `Ignition 8.3.8`, `Jython 2.7.4`, and the exact Gateway, Perspective, Vision, event, Web Dev, project-library, or Designer execution scope. Stop if any of those are unknown.
- Compile mentally against Python 2.7: reject Python 3 syntax, Python 3 module spellings, and modern methods that have not been verified in the target. Preserve `str`/`unicode`, `int`/`long`, eager built-ins, and Python 2 division deliberately.
- Inventory every import. Treat NumPy, pandas, dataclasses, pip, binary wheels, and C extensions as unavailable unless the exact target scope proves otherwise; choose a verified pure-Python or JVM dependency through an explicit deployment contract.
- Inventory every called function/method signature and every caller, callback, bound method, event hook, registration ID/token, registrar, and stored reference affected by a change. Preserve positional order, keyword names, defaults, input types, and the exact returned type/schema unless the change is explicitly migrated and tested. Record how each consumer uses truthiness, `None`, `len`, iteration, indexing, unpacking, serialization, status, quality, and partial results. For registrations, also record ownership, event/filter, generation, duplicate/replace/unregister policy, queued or in-flight delivery, and cleanup.
- Verify every `system.*` function's current per-function scope, then separately validate target availability, named resources, permissions, inputs, and result semantics. A callable name is not proof that the operation is legal or successful.
- Define inputs, outputs, side effects, ownership, completion, failure, timeout, cancellation, retry, cleanup, and logging before implementation. Keep shared deadlines and application-specific bounds explicit.
- Keep pure logic separate from Ignition and Java boundaries. Test at least one positive and one negative case, including the result/quality/error path that would disprove success.
- Require explicit authorization and readback for writes. Never turn returned, queued, submitted, pending, partially completed, or outcome-unknown work into a success claim or automatic retry.
- Promote a rule only from current official documentation plus a reproducible target test, direct Gateway observation, source proof, or a clearly labeled fixture. State the untested boundary instead of completing it with an assumption.

## Load only the references required by the task

Keep the core generation gate above in context for every script. Then load every reference whose boundary the requested script crosses:

| Task boundary | Required reference |
| --- | --- |
| Python 2 syntax/semantics, text/bytes, module names, imports, dependencies, sockets/HTTP, timing, Java interop, or pickle | `references/python-2-7-4-runtime-and-dependencies.md` |
| Ignition `system.*` scope, asynchronous ownership, event scripts, messaging, Perspective/Vision, configuration, secrets, or logging | `references/ignition-scope-and-concurrency.md` |
| Database transactions, tag reads/writes, datasets, JSON, date/time, Python/Java exception routing, or cleanup | `references/data-and-failure-boundaries.md` |

Load more than one reference when the task crosses boundaries. Do not copy a tested fixture's example limits into an unrelated application contract, and do not broaden a bounded observation into a general platform claim.
## Control side effects

- Default to read-only discovery and dry-run output.
- Require explicit authorization before changing live tags, alarms, databases, project resources, Gateway configuration, files, or external systems.
- Treat `system.config.copy`, `create`, `delete`, `move`, `rename`, and `replace` as writes. They are present but not mutation-tested by this skill; require a backup, a uniquely named disposable fixture, readback after every step, and verified cleanup before using them.
- Avoid `eval`, `exec`, and arbitrary-code endpoints. Prefer fixed, allowlisted operations with validated inputs.
- For asynchronous work, apply the tested ownership rules above: submission is not completion, timeout is not cancellation, cancellation is not cleanup acknowledgement, worker failure needs an observation channel, and every owned wait/thread/executor needs a bounded cleanup path.
- Restore temporarily changed interpreter globals in `finally`. A warning emitted successfully with an empty `sys.argv` in the tested runtime, and the original `sys.argv` object was restored.
- Do not mutate protected `sys` attributes or rely on a dynamically constructed name to bypass their guards. For the tested `sys.exec_prefix`, Jython 2.7.4 rejected literal and equal non-interned set/delete operations with `TypeError`; standalone 2.7.3 allowed the constructed-name bypass. If a task truly requires a temporary ordinary `sys` attribute, use a unique name and remove it in `finally`.

## Return a usable answer

Include:

- target Ignition and Jython versions
- execution scope and required modules/resources
- assumptions and discovered names
- the complete script or smallest relevant patch
- side effects and safety controls
- positive and negative verification steps
- any untested boundary or environment dependency

Do not present an untested hypothesis as a guaranteed Ignition behavior.
