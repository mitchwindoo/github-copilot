---
name: ignition-8-3-udt-builder
description: Build, modify, discover, and verify Ignition 8.3 UDT definitions, UDT instances, scalar and complex member tags, parameters, expressions, references, OPC members, arrays, Documents, DataSets, Text, history configuration, tag security, query members, nested UDTs, inheritance, scripts, and alarms through the Gateway OpenAPI or a guarded WebDev API. Use for API-first Ignition tag engineering, JSON tag imports/exports, collision-policy decisions, runtime QualityCode verification, bounded bulk work, or extending llmImport.py when the official contract lacks a required operation. Do not use for Designer or Gateway UI automation.
---

# Ignition 8.3 UDT Builder

Skill version: `1.1.0`

Build UDTs and tags through machine interfaces and prove both persisted configuration and runtime behavior. Treat transport success as delivery evidence, never as proof that the UDT works.

## Non-negotiable rules

- Do not drive the Designer, Gateway web UI, mouse, keyboard, screenshots, or browser controls.
- Fetch the target Gateway's authenticated `/openapi.json` before choosing a route. Do not assume an endpoint or response shape from another build.
- Prefer official OpenAPI routes. Extend the approved WebDev API only for a concrete missing capability.
- Use the consolidated approved `llm-tools` project for runtime testing whenever it already exposes the required guarded action. Create a separate test project only when the capability cannot be tested safely or faithfully in `llm-tools`, and record that reason.
- Never print, paste into commands, commit, or save an API token in evidence. Load it from the caller's secret store and send it only in the declared authentication header.
- Restrict every test to a caller-approved provider and bounded tag root. A path prefix is an accidental-scope guard, not authorization.
- Snapshot existing configuration before writes. Use a sacrificial namespace for discovery and destructive collision-policy tests.
- Inspect the response body even when HTTP status is 200. A tag import can return semantic failures inside a success/failure envelope.
- Verify configuration, runtime values, exact qualities, and diagnostics. Keep failed attempts; contradictions are findings.
- For every new or changed UDT test, inspect the bounded Gateway log window surrounding creation and exercised runtime transitions. This is a pass gate on successful and failed attempts: never assume Good values mean clean scripts. Retain the exact start/end, logger and severity filters, relevant rows/counts, and an explicit zero-ERROR-or-higher result.

## Route the task

1. Read `references/api-contract.md` for discovery, authentication, import/export, and optional `llmImport` actions.
2. Read `references/udt-json.md` before creating or changing UDT JSON.
3. Read `references/verification.md` before asserting success or troubleshooting.
4. Run `scripts/validate_tag_payload.py` on authored JSON before contacting the Gateway.
5. For scripts or alarms, also read the corresponding section in `references/advanced-features.md`. When a UDT event script calls Project Library code, runs on a member inside a Folder, or crosses nested UDT levels, also read `references/project-library-scripts.md` and validate the helper-project ZIP with `scripts/validate_project_library_zip.py`.
6. For nested command/interlock or analog/digital faceplate UDTs, read `references/reusable-models.md`.
7. For OPC members, parameterized OPC paths, or OPC write verification, read `references/opc-members.md`.
8. For bulk creation, browse/read sizing, or multiple writers, read `references/scale-and-concurrency.md`.
9. For scaling, engineering limits, derived members, or database-query members, read `references/member-sources.md`.
10. For history-enabled members, historian providers, sampling modes, or stored-history verification, read `references/history.md`.
11. For `readOnly`, read/write permission trees, security levels, or instance security overrides, read `references/tag-security.md`.
12. For grouped `udts.json` files, external configuration scans, stale-writer detection, or deterministic recovery, read `references/grouped-resource-recovery.md` and run `scripts/validate_grouped_udts_file.py` on the grouped file.
13. For array, `Document`, `DataSet`, or `Text` members and overrides, read `references/complex-values.md`.
14. For base-type, derived-type, or concrete-instance overrides—including event scripts, alarms, parameters, and members below Folders—read `references/inheritance-overrides.md`.
15. For one-level or multi-level nested `UdtInstance` composition and parent-to-child parameter propagation, read `references/nested-udt-composition.md`.
16. When an import fails or succeeds suspiciously, read `references/failure-modes.md` before retrying.

## Execute the API-first workflow

### 1. Discover and freeze the target

Authenticate to `GET /openapi.json`. Record the Gateway version/build, OpenAPI version, chosen provider, exact lab root, and available tag routes. Confirm these official routes exist before using them:

- `GET /data/api/v1/tags/export`
- `POST /data/api/v1/tags/import`

Discover enabled providers and browse only the approved root. If browse reports truncation or a continuation point, treat the inventory as incomplete and partition the browse.

### 2. Capture pre-state

Export the exact target path. A nonexistent path may export an `Unknown` sentinel rather than return 404; interpret content, not status alone. Hash and preserve the export. If modifying a grouped folder, inventory every sibling because UDT definitions and instances are stored in grouped `udts.json` resources.

### 3. Author the smallest payload

Send exactly one top-level JSON object. The verified official import rejected arrays, including a one-element array, with `Not a JSON Object`. To import siblings together, wrap them in one `Folder` object and put the siblings in its `tags` array. Use explicit `tagType`, `name`, parameter types, member data types, and value sources. Keep a known-good control fixture beside any experimental shape.

Validate locally:

```text
python scripts/validate_tag_payload.py payload.json
```

If the payload contains event scripts, also compile the exact bodies with the target Gateway's Jython jar before import:

```text
python scripts/validate_jython_event_scripts.py payload.json --java <java> --jython-jar <jython-jar>
```

Structural validation does not replace this gate. A syntactically malformed body persisted on the verified Gateway, its trigger remained Good, and no ERROR-level log exposed the failure.

### 4. Choose collision policy deliberately

- `Abort`: creation and idempotency probe; expect an existing-name failure and no change.
- `MergeOverwrite`: targeted patch while preserving omitted siblings; still export and diff afterward.
- `Overwrite`: full replacement only at the submitted hierarchy. Omitted direct members can be deleted, but do not assume it recursively clears inherited nested-UDT overrides; read `references/nested-udt-composition.md` for the proven reset procedure.
- `Rename` or `Ignore`: use only when duplicate handling is the requested behavior.

Serialize configuration writes that can touch the same provider and grouped parent. Two concurrent writes to the same property both reported success in testing, but either submitted value could win.

Send JSON bytes as `application/octet-stream` to the import route with `provider`, `path`, `type=json`, and `collisionPolicy` query parameters. URL-encode provider and path values.

### 5. Classify the native result

On the tested 8.3.8 build, the import body was:

```json
{"successCount": 1, "failureCount": 0, "failures": []}
```

The live OpenAPI description incorrectly described an array, and HTTP 200 accompanied invalid tag types and duplicate `Abort` attempts. Require all of the following:

- expected `successCount`;
- zero `failureCount`;
- empty `failures`;
- no timeout or unknown-mutation state.

If the response is missing, truncated, or ambiguous, do not retry automatically. Re-export and inventory first.

For a `Folder` payload, `successCount` included the folder plus each successfully imported descendant on the verified build. A `UdtType` root with ten member definitions returned `successCount: 1`; its members were not counted separately. Derive the expected count by root kind and verified target behavior rather than applying the Folder rule universally.

### 6. Verify persisted configuration

Export the exact type or instance. Normalize object-key order and omitted defaults before semantic comparison. Verify names, `tagType`, `typeId`, parameters, member definitions, bindings, alarms, and event scripts. Do not demand byte equality: the Gateway can reorder members and normalize JSON escapes or newlines.

### 7. Verify runtime behavior

Read direct members, parameter properties, dependent expressions/references, and alarm runtime properties. Capture value, raw value type, exact quality string, timestamp, and diagnostic message when available. A configured expression with `Good` transport/import results can still read `Error_Config`, `Error_ExpressionEval`, `Error_TypeConversion`, `Uncertain_InitialValue`, or `Bad_NotFound`.

Use a runtime write only through an official route exposed by the live contract or the guarded `tag-write-v1` extension described in `references/api-contract.md`. Dry-run first, then require explicit apply and post-write readback.

Treat multi-tag writes as independently reported operations, not transactions. If any item fails or the response is ambiguous, read every target plus its UDT-side sequence/result evidence before retrying. Recover only missing work. A write that reads back the requested trigger value does not prove `valueChanged` executed.

Record a log-window start timestamp before importing the UDT. After the final runtime transition and observable script/alarm marker has settled, record the end timestamp and query only that bounded Gateway log interval. Inspect relevant test logger rows plus ERROR-or-higher rows. Correlate script errors to the exact tag path and event, distinguish unrelated concurrent errors, and save the query bounds even when the result is empty. Do this for every creation/change attempt, including a functionally passing run and a stopped or failed run. A new UDT test does not pass without this log check; tag values and qualities cannot waive it.

### 8. Repeat and close out

Run a clean repeat, including a fresh bounded log window. Re-export and compare the target plus grouped siblings. Scan all generated artifacts for credentials. Report proven behavior, environment-specific behavior, contradictions, and unexecuted lifecycle tests separately.

## Extend `llmImport` only when necessary

Before changing the WebDev API, prove the required operation is absent from the live OpenAPI. Follow this sequence:

1. Export the complete live project as the packaging baseline.
2. Add one fixed-shape, bounded action; do not accept arbitrary code.
3. For writes, validate the native API token, default to dry-run, require `apply: true`, cap item counts, reject unknown fields and traversal, and return pre/write/post state.
4. Compile with the Gateway's Jython generation and run offline positive, negative, boundary, and no-mutation tests.
5. Prefer adding and testing the bounded action in the consolidated `llm-tools` project after offline validation. Use a minimal isolated project first only when project creation is genuinely necessary to contain an unproven persistence, replacement, or scan risk; record the reason and merge the proven action back into `llm-tools` rather than leaving a growing set of one-off projects.
6. For integration, overlay only changed resources onto the authenticated full export with a ZIP-aware tool that preserves entry names. Reject package removals, backslash ZIP entry names, directory-only shells, and a missing root `project.json`. Do not rebuild a large live project with an unverified generic archiver.
7. Import through the official project route, wait on health readiness, export immediately, request one bounded project scan, export again, and require the same complete resource inventory. Rerun live and prior-action regression tests.
8. If the post-import export collapses or the collection manager rejects replacement, stop. Restore from the authenticated backup. If the project is already an empty shell and in-place replacement remains illegal, delete only that confirmed shell and recreate it immediately from the verified backup.

Do not expose a broadly reachable WebDev write route merely because it validates a token internally. Configure route authentication, TLS, network restrictions, and least-privilege API-key security separately.

## Scope of claims

The detailed rules in the references were validated on Ignition 8.3.8 build 2026071409 with Jython 2.7.4. Revalidate after a Gateway, module, provider, or API version change. Restart behavior, deployment-mode overrides, migrated 8.1 equivalence, alarm history/notification delivery, audit-profile coverage, and OPC write-through for the target device are not generalized by this skill without fresh target evidence.
