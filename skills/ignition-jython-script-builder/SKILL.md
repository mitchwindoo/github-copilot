---
name: ignition-jython-script-builder
description: Create, review, and repair safe Ignition 8.1 Jython scripts for Project Library, Gateway, Perspective, tags, historian, alarms, MES, databases, and validation.
---

# Ignition Jython Script Builder

Skill version: `1.1.131`

Stack version: `starter-2026.07.06.04`

Create production-ready Ignition 8.1 scripts for the Jython 2.7 runtime. Support offline authoring and review by default. Use a live API or runner only when the user has access and authorizes it.

## Intake

Before writing code, establish:

- the Ignition version, installed modules, and execution scope
- the event or caller, inputs, expected output, and failure behavior
- exact tag providers and paths, project and resource names, database connections, and Named Query paths
- whether the task is read-only, dry-run, or explicitly authorized to mutate a live system
- whether a Designer, Gateway, approved runner, or no live validation target is available

Do not guess deployment-specific identifiers. Ask for them or provide clearly marked placeholders and discovery steps.

## Select References

Read only the references needed for the current workflow:

- [Runtime and Project Library](runtime-and-project-library.md): Jython syntax, imports, lifecycle, scope, external runtimes, and asynchronous execution.
- [Tags, UDTs, and Browsing](tags-udts-and-browsing.md): tag paths, reads/writes, configuration, event scripts, UDT parameters, and discovery.
- [Perspective Scripting](perspective-scripting.md): Perspective context, events, transforms, messages, navigation, popups, and components.
- [Data, Serialization, and Files](data-serialization-and-files.md): dates, datasets, JSON, Document values, logging, globals, files, CSV, and XML.
- [Database, Messaging, and HTTP](database-messaging-and-http.md): Named Queries, SQL, transactions, project messaging, and outbound HTTP.
- [Historian, Alarms, and MES](historian-alarms-and-mes.md): tag history, alarm journals, historian SQL, MES, and OEE patterns.
- [Runner Validation](runner-validation.md): optional API capability discovery, dry-run/apply controls, execution validation, and fallbacks.
- [Ignition Documentation Links](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-jython-script-builder/references/ignition-doc-links.md): official Ignition 8.1 documentation routes.
- [Runtime Reference Index](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-jython-script-builder/references/complete-runtime-details.md): compact routing index for detailed and comprehensive runtime references.
- [Jython Guardrails](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-jython-script-builder/references/jython-guardrails.md): comprehensive Ignition Jython runtime guardrails and verified behavior.
- [Historian and MES Patterns](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-jython-script-builder/references/historian-mes-patterns.md): focused historian SQL, MES counting, OEE, and validation patterns.

## Workflow

1. Classify the target scope and confirm Jython 2.7 constraints.
2. Discover exact resources instead of inventing names or paths.
3. Read the relevant topical references.
4. Separate pure transformation logic from Ignition I/O.
5. Design bounded error handling, logging, timeouts, and readback proof.
6. Produce a read-only or dry-run form before any mutating form.
7. Validate syntax and behavior in the real target context when available.
8. Report assumptions, required configuration, side effects, and evidence.

## Core Guardrails

- Use Python 2.7/Jython-compatible syntax. Do not use Python 3-only syntax, modules, or package-manager assumptions.
- Prefer Ignition `system.*` APIs, Jython-compatible pure-Python code, and Java libraries available on the Gateway.
- Do not assume CPython native-extension packages such as NumPy, pandas, SciPy, or `requests` can load inside Ignition Jython.
- Treat Gateway, Perspective, Vision, tag-event, project-library, and Web Dev scopes as different runtimes with different available APIs.
- Never use Vision-only UI APIs in Gateway, Perspective, tag-event, or Web Dev code.
- Keep Project Library modules import-safe: avoid writes, network calls, tag reads, database access, and long work at module top level.
- Call saved Project Library resources by their exact project path. Do not rely on ordinary CPython reload behavior.
- Build fully qualified tag paths from configurable parts in Gateway-side code. Use `[.]` or `[~]` only in a genuinely tag-relative context.
- Validate tag read quality before using values. Validate each write result and read back critical changes.
- Treat QualifiedValue, QualityCode, Date, Dataset, PyDataSet, Document, TagPath, and other Java-backed values explicitly at JSON or API boundaries.
- Preserve `None`, empty string, and literal `"null"` as distinct states unless the contract says otherwise.
- Use parameterized Named Queries by default. Use prepared SQL only when a Named Query is unsuitable and the user authorizes the connection and operation.
- Keep transactions bounded; always commit or roll back, and always close them in `finally`.
- Catch narrow Python exceptions where possible. For Java-backed Ignition failures, use the documented Java exception boundary and re-raise or log diagnostic context.
- Keep time windows, pagination, browse depth, polling intervals, retries, and returned row counts bounded.
- Do not treat successful packaging, import, or structural validation as proof that a script executes correctly.
- Keep filesystem paths configurable. Gateway-side file operations use the Gateway host filesystem, not the Designer or client machine.
- Specify UTF-8 explicitly for text I/O and normalize Java/Jython values before serialization.
- Require explicit site approval before spawning external processes. Capture return code, stdout, and stderr when behavior depends on them.
- Use `system.util.getLogger(...)` for Gateway-side diagnostics; do not depend on an attached Perspective session unless one is confirmed.
- Avoid destructive, security-sensitive, or production mutations unless the user explicitly authorizes them and a rollback/readback plan exists.

## Script Design Contract

Structure nontrivial scripts as:

1. constants and documented configuration
2. validation and conversion helpers
3. pure transformation functions
4. bounded Ignition I/O functions
5. one small entry point for the actual event or caller

For each configurable input, state its type, example form, and source. For each mutation, identify what changes, how dry-run differs, how success is verified, and how failure is surfaced.

Avoid shared mutable module globals. Use documented Gateway global storage only when cross-execution state is intentional, synchronized, bounded, and recoverable.

## Validation

Match validation to risk:

- For offline work, perform a Jython 2.7 compatibility review and provide a target-execution checklist.
- With a Designer or Gateway, execute in the actual intended scope and verify return values, tag quality, database rows, UI state, files, or focused logs.
- With an approved runner, read [Runner Validation](runner-validation.md), discover supported actions first, use dry-run before apply, and perform execution/readback validation after structural checks.
- For mutations, test a bounded fixture or nonproduction target first whenever possible.

Never claim live success without live evidence. Clearly distinguish authored code, static review, structural validation, target execution, and readback proof.

## Output Format

Return:

1. assumptions and required configuration
2. the complete Jython 2.7-compatible script
3. installation location and calling instructions
4. read/write behavior and safety controls
5. validation steps and observed evidence
6. limitations, fallbacks, and unresolved deployment-specific values

Keep the answer self-contained, but route lengthy or specialized explanations to the relevant bundled reference.
