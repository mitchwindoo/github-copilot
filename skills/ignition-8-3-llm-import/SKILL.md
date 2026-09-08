---
name: ignition-8-3-llm-import
description: Use and maintain the llmImport API for Ignition 8.3.8/Jython 2.7.4. Use for discovery, bounded tests, guarded fixture writes, project-folder mutations, packaging, or extensions.
---

# Use Ignition llmImport

Skill version: `0.3.9`

Operate the local Ignition 8.3.8 `llmImport` Web Dev resource as an allowlisted compatibility-test and fixture-maintenance API. Keep customer Jython-writing guidance separate from this API-maintenance skill.

## Locate the implementation

- Web Dev project source: `./llm-tools-project`
- Resource folder: `./llm-tools-project/com.inductiveautomation.webdev/resources/llmImport`
- Executable GET method: `doGet.py`
- Executable POST method: `doPost.py`
- Compatibility helpers: `./llm-tools-project/ignition/script-python/llmImportFixtures/code.py`
- Import-fallback compatibility helper: `./llm-tools-project/ignition/script-python/LLMImportFallbackGuardrails/code.py`
- Perspective helpers: `./llm-tools-project/ignition/script-python/LLMPerspectiveFixtures/code.py`
- Project-folder helpers and central action inventory: `./llm-tools-project/ignition/script-python/LLMProjectFolderFixtures/code.py`
- Alarm query and guarded mutation helper: `./llm-tools-project/ignition/script-python/LLMAlarmApi/code.py`
- Caller-scoped tag read, browse, history, and guarded write helper: `./llm-tools-project/ignition/script-python/LLMTagApi/code.py`
- Complex tag-value read helper: `./llm-tools-project/ignition/script-python/LLMComplexTagRead/code.py`
- Grouped UDT resource-file helper: `./llm-tools-project/ignition/script-python/LLMGroupedUdtFiles/code.py`
- Guarded Document-tag compare-and-set helper: `./llm-tools-project/ignition/script-python/LLMDocumentTagWrite/code.py`
- Expression-tag and Event Stream expression fixture helper: `./llm-tools-project/ignition/script-python/LLMExpressionApi/code.py`
- Perspective Named Query expression fixture helper: `./llm-tools-project/ignition/script-python/LLMPerspectiveNamedQueryExpression/code.py`
- SFC transition-expression fixture helper: `./llm-tools-project/ignition/script-python/LLMSfcExpressionFixture/code.py`
- SFC parallel-cancel expression fixture helper: `./llm-tools-project/ignition/script-python/LLMSfcParallelExpressionFixture/code.py`
- SFC parallel-expression suite helper: `./llm-tools-project/ignition/script-python/LLMSfcParallelExpressionSuite/code.py`
- Vision skill-lab fixture user helper: `./llm-tools-project/ignition/script-python/LLMVisionSkillLab/code.py`
- Vision session inventory helper: `./llm-tools-project/ignition/script-python/LLMVisionSessions/code.py`
- Readable POST-code backup: `./llmImport.py` at the API-skill root, outside `llm-tools-project`
- Copy-ready method files: `./COPY TO WEBDEV - doGet.py` and `./COPY TO WEBDEV - doPost.py`
- Current portable import archive: `./llm-tools-api-v0.103.0.zip`
- Live project name: `llm-tools`
- Local resource route: `/system/webdev/llm-tools/llmImport`

Ignition requires the case-sensitive resource folder `llmImport` and method filenames `doGet.py` and `doPost.py`. Do not rename those executable files. The root-level `./llmImport.py` is a backup mirror of `doPost.py`, not a file inside the Web Dev resource and not the live Web Dev entry point.

## Complete every documentation or release pass

Treat any request to update this API skill or its documentation as a complete release synchronization unless the user explicitly narrows the scope. Do not finish after editing Markdown.

1. Discover the current live version/action list and inspect every handler/helper import.
2. Rebuild the exact customer project allowlist from the live/current source plus the normalized two-method Web Dev metadata. Restore any missing required helper and exclude unrelated or temporary resources.
3. Refresh `COPY TO WEBDEV - doGet.py` from packaged `doGet.py`. Refresh both `COPY TO WEBDEV - doPost.py` and `llmImport.py` from packaged `doPost.py`. Require byte-for-byte SHA-256 equality with live/current handlers.
4. Update `SKILL.md`, the action-result reference, and UI metadata when affected. Require exact action-name parity among live GET, the skill bullets, and the contract table.
5. Compile-check both handlers and every packaged helper with Ignition Jython 2.7.4, then remove/reject `$py.class`, `.pyc`, and `__pycache__` artifacts.
6. Rebuild the versioned `llm-tools-api-v<API_VERSION>.zip` in the skill root. Put `project.json` at the ZIP root, use forward-slash entry names, include only the project allowlist, and never include the skill documentation or root backup files.
7. Extract the ZIP into an isolated internal validation directory and require exact file-list, byte-count, and SHA-256 parity with `./llm-tools-project`. Copy the validated ZIP and manifest into the internal `outputs` directory.
8. Report the archive name, SHA-256, entry count, script/helper hash parity, and any intentionally untested live behavior.

An API/documentation pass is incomplete when the current import ZIP or either copy-ready Web Dev method is stale or missing.

## Configure access without embedding values

Require the caller to provide access configuration through environment variables:

```powershell
$env:IGNITION_BASE_URL = "http://localhost:8088"
$env:IGNITION_API_TOKEN = "<provided outside source and prompts>"

$headers = @{
    "X-Ignition-API-Token" = $env:IGNITION_API_TOKEN
}
```

Never print, persist, normalize, split, or partially reproduce the access value. Use the full supplied value exactly as the header value.

The packaged Web Dev resource currently has route-level `require-auth: false`. Do not treat a supplied header as proof that Web Dev authenticated the request. Actions capable of mutation validate the token against the native Gateway API before continuing, but read-only compatibility actions remain reachable wherever the Web Dev route is reachable. Restrict this local harness by network boundary or configure and retest Web Dev authentication and HTTPS before any broader deployment.

## Discover before acting

1. Read `$env:IGNITION_BASE_URL/openapi.json` with the configured header when using Gateway management endpoints.
2. GET `$env:IGNITION_BASE_URL/system/webdev/llm-tools/llmImport` to discover the live API version and `availableActions`.
3. Confirm `acceptsArbitraryCode == false` before running fixtures. Treat the GET-level `externalSideEffects == "none"` as a route summary, not permission to apply every POST action: v0.103.0 retains guarded mutations. Tag, alarm, grouped-UDT, Perspective, Document-tag, expression-tag, Event Stream, SFC, Vision skill-lab, and Vision session actions validate the native API token, default to dry-run where mutation is possible, restrict targets, and return action-level side-effect and attempt fields. The project-folder update actions require exact current hashes and scan/readback checks. Grouped UDT create/replace requires an externally held configuration scan lock, uses compare-and-swap for replace, and does not perform the project/configuration scan itself. Never apply one from generic health or regression code.
4. Treat the in-memory compatibility fixtures separately. The project-library state action intentionally increments one fixed in-memory counter. The import/reference/member/signature/return fixtures temporarily mutate only owned in-memory module state and restore it in `finally`. The callback fixture leaves its fixed registry empty. The tag-event reconciliation action uses only injected in-memory stand-ins and performs no real tag or event operation.
5. Treat the live GET response as authoritative when it differs from this skill's recorded version.

PowerShell discovery example:

```powershell
$route = "$($env:IGNITION_BASE_URL)/system/webdev/llm-tools/llmImport"
$health = Invoke-RestMethod -Method Get -Uri $route -Headers $headers
$health | Select-Object api, version, availableActions, acceptsArbitraryCode, externalSideEffects, sideEffects, tagApi, complexTagReadApi, alarmApi, groupedUdtFileApi
```

## Run one fixed action

POST exactly one discovered action name as JSON:

```powershell
$body = @{ action = "runtime-profile-v2" } | ConvertTo-Json -Compress
$result = Invoke-RestMethod `
    -Method Post `
    -Uri $route `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $body

if (-not $result.accepted -or -not $result.passed) {
    throw "The fixed compatibility action did not pass."
}
```

Treat that check as control flow, not as a universal evidence claim. `accepted` means the fixed request was recognized; `passed` is an action-specific aggregate over only the conditions named by that action's source contract. Before promoting a claim, map it to the exact returned fields and expected values, record whether those fields participate in `passed`, and preserve any separate scope/boundary note. A missing field, unexpected schema, or version mismatch is unproven even when both top-level Booleans are true.

Read [`references/action-result-contracts.md`](references/action-result-contracts.md) before interpreting an action result. It maps every v0.103.0 source action's aggregate inputs, observation-only fields, side-effect gates, and prohibited inference. Treat the live GET version as authoritative and stop as unproven when the reference version does not match.

Never send executable Jython/Python code, arbitrary filesystem paths, arbitrary URLs, or caller-selected module/class names. The expression-tag batch action accepts only its source-enforced, side-effect-free Ignition expression subset; do not treat that bounded expression grammar as permission to send `runScript`, dynamic tag calls, or arbitrary code. For a parameterized v0.103.0 action, send only its documented bounded fields, begin mutations with `dryRun: true`, reconcile returned hashes and state, and require explicit user authority before changing a fixture. For caller-scoped tag and alarm actions, require explicit qualified prefixes but never treat those prefixes as authorization. For grouped UDT files, use only validated providers/group paths beneath explicit group-path prefixes and treat those prefixes as accidental-scope guards. Missing and unknown actions must remain rejected.

## Understand the current actions

The recorded source API version is `0.103.0` with 72 allowlisted actions. This source version must not be described as live until GET health reports the same version and action count:

- `runtime-profile-v2`: Jython version, Python 2 syntax/types, numeric behavior, explicit UTF-8 boundaries, and Java availability.
- `python2-guardrails-v1`: a fixed 17-invalid/7-valid syntax matrix plus Python 2 text, iteration, class, numeric, and default-argument behavior. The syntax outcomes match standalone Jython 2.7.3, standalone Jython 2.7.4, and embedded Ignition Jython 2.7.4; the action accepts no caller-provided code.
- `python2-module-names-v1`: fixed positive Python 2 and negative Python 3 standard-library name imports plus bounded Queue, ConfigParser, URL, HTTP-object, and SocketServer behavior. It accepts no caller-controlled name, URL, host, or data and performs no network I/O.
- `import-fallback-guardrails-v1`: fixed absent-module, absent-member, nested-import, broad-fallback, direct-module, and explicit-member-validation cases. It accepts no caller-controlled module/member name, code, path, or value and performs no filesystem, network, process, thread, or Gateway-resource operation.
- `text-byte-boundaries-v1`: fixed explicit UTF-8 encode/decode, invalid-codec, implicit `str`/`unicode`, mixed concatenation/join, and Unicode formatting cases. It accepts no caller-controlled value, encoding, code, path, or payload and performs no filesystem, network, process, thread, or Gateway-resource operation.
- `deadline-budget-v1`: fixed Python-clock availability, `System.nanoTime()` type/order, non-negative integer-millisecond validation, deadline rounding/clamping, and one-deadline allocation cases. It accepts no caller-controlled timeout, delay, code, or path and performs no sleep, retry, network, write, scheduling, or cancellation operation.
- `async-ownership-contract-v1`: fixed Java Future success, worker-failure observation, timeout-then-late-completion, running/queued cancellation, cooperative interruption, interrupt-flag restoration, and executor cleanup cases plus bounded embedded `system.util.invokeAsynchronous` completion/interruption probes. It accepts no caller input, uses only fixed in-memory latches and threads with 1000-millisecond cleanup bounds, performs no external I/O or write, and does not establish interruption behavior for arbitrary Ignition calls or third-party libraries.
- `tag-event-lifecycle-contract-v1`: fixed Gateway Tag Change versus tag Value Changed family selection, initial-execution, missed-event reconciliation, quality/timestamp, project startup/update/shutdown, Boolean/type, and simulated state-reload cases. It accepts no caller input and performs no tag, project, message, database, filesystem, or external operation. Its reload case is explicitly a simulation; current Ignition documentation, not the fixture, supports the event variables and project restart behavior.
- `tag-event-reconciliation-contract-v1`: fixed injected in-memory tag-delivery policy covering normal claim/completion, stable-ID duplicate suppression, same-observation deduplication, stale and same-timestamp-conflict routing, initial/overflow/quality reconciliation, Gateway initial-count validation, effect-then-completion failure, outcome-unknown duplicate suppression and explicit proof, empty-module-state startup, durable-checkpoint match/divergence, unacceptable authoritative value, and outstanding-outcome startup cases. It accepts no input; uses only fixed scalar values and qualified-value stand-ins; and performs no tag read/write, event delivery, project/Gateway restart, database, filesystem, network, process, UI, or external effect. Its module restart and authoritative reads are simulations, its bounds/fingerprint/states are fixture policy, and matching 2.7.3/2.7.4 behavior is a shared guardrail rather than a new 2.7.4 feature.
- `project-library-state-v1`: fixed generation and thread-safe module-counter observation for a two-phase authenticated project-import protocol. Repeated calls in phase A produced counts 1 then 2; changing the helper produced phase B/count 1; a later import changing only Web Dev GET left the unchanged helper at phase B/count 2. It accepts no input and performs no tag, database, message, configuration, filesystem, network, process, UI, or external operation, but it intentionally retains one ephemeral in-memory counter inside the loaded project-library module.
- `project-library-import-contract-v1`: fixed in-memory failing-initializer, missing-dependency, early-binding circular-import, acyclic-import, and successful-cache cases. It accepts no input; uses only fixed source strings and module names; temporarily replaces only its owned `sys.meta_path` entry and `sys.modules` names under a lock; restores them in `finally`; and performs no project-resource, tag, database, message, configuration, filesystem, network, process, UI, or external operation. Its Jython-core result is not an Ignition Project Library loader guarantee: the separate authenticated live phase-A test wrapped a top-level `RuntimeError` and a cycle as `ImportError`, retained module-present state, and repeatedly re-entered the cycle until a fixed guard; corrected phase-B resources then imported and cached successfully. Those temporary live resources were evidence fixtures and are not shipped in the current customer project.
- `project-library-reference-contract-v1`: fixed in-memory module replacement/removal and held module, function, and object-reference cases. It accepts no input; temporarily owns one fixed `sys.modules` name under a lock; restores its prior state in `finally`; and performs no project-resource, tag, database, message, configuration, filesystem, network, process, UI, or external operation. Its passing Jython-core result is not an Ignition Project Library loader guarantee. Separate authenticated live evidence renamed temporary Project Library resources and observed one already-running Web Dev request retain its captured generation while a fresh request saw the replacement; those temporary resources and overlap-only actions are not shipped.
- `project-library-member-contract-v1`: fixed same-module member deletion with captured function/bound-method versus later module/object lookup cases. It accepts no input; temporarily owns one fixed `sys.modules` name under a lock; deletes only its fixed module attribute and fixed class method; removes the fixed module in `finally`; and performs no project-resource, tag, database, message, configuration, filesystem, network, process, UI, or external operation. Its Jython-core result is not an Ignition Project Library loader guarantee. Separate authenticated live evidence updated one temporary resource in place, removed its function/method, and observed an already-running Web Dev request retain its old module/function/class/object/bound-method paths while a fresh request saw the new generation and missing members; the temporary resource and overlap-only actions are not shipped.
- `project-library-signature-contract-v1`: fixed same-module function/method signature replacement with old defaults and keywords, new required arguments and keyword names, positional reordering, captured functions, and captured bound methods. It accepts no input; temporarily owns one fixed `sys.modules` name under a lock; mutates only its fixed owned module/class objects; removes the fixed module in `finally`; and performs no project-resource, tag, database, message, configuration, filesystem, network, process, UI, or external operation. Separate authenticated live evidence updated one temporary Project Library resource in place: an in-flight request retained the old signature generation, a fresh request used the new one, old default/keyword calls raised `TypeError`, and same-arity positional calls could succeed or silently change meaning. The temporary resource and overlap-only actions are not shipped.
- `project-library-return-contract-v1`: fixed same-module migration from scalar/list/`None` results to exact versioned reading and batch envelopes, with required/allowed keys, generation/schema, status, quality, completeness/count, captured functions, truthiness, `None`, length, iteration, indexing, and malformed-envelope rejection cases. It accepts no input; temporarily owns one fixed `sys.modules` name under a lock; mutates only its fixed owned module functions; removes the fixed module in `finally`; and performs no project-resource, tag, database, message, configuration, filesystem, network, process, UI, or external operation. Separate authenticated live evidence updated one temporary Project Library resource in place: an in-flight request retained old list/`None` return shapes while a fresh request used the new exact envelopes. The fixture's quality strings test consumer policy only; they are not actual Ignition `QualityCode` behavior. The temporary resource and overlap-only actions are not shipped.
- `project-library-callback-contract-v1`: fixed owned in-memory callback-registry lifecycle with a stable registration ID, idempotent same-generation registration, different-generation conflict, expected-generation replacement/unregister, stored-owner reassignment, captured-callback survival, exact call counts, and empty final registry. It accepts no input; uses only fixed callbacks and one fixed registry under a lock; performs no Project Library, globals, event, message, tag, database, filesystem, network, process, UI, or external operation. Separate authenticated live evidence used one temporary Project Library callback target and one fixed `system.util.getGlobals()` key: a fresh request replaced `old` with `new`, while an already-running request retained its old callback and old globals view even after reacquiring `getGlobals()`. The temporary target/actions and globals key are not shipped; cleanup removed the key and passed again when already absent. This exact test does not prove a universal registrar, loader, restart, redundancy, cluster, queue, or event-delivery contract.
- `write-readback-state-v1`: fixed `QualityCode`/`QualifiedValue` write-result and readback classification cases, including exact-count validation, pending write/read states, bad quality, stale matching value after a rejected write, mismatch, invalid objects, partial failure, and all-verified success. It performs no tag, database, configuration, project-resource, file, network, retry, or external write.
- `message-payload-contract-v1`: fixed exact-key, exact-type, null/scalar, count/length, duplicate-path, finite-float, and stable-error-code validation cases for one bounded message-payload schema. It includes the Python 2 `bool`/`int` trap, accepts no caller-provided payload, and performs no message send, I/O, Gateway-resource operation, or handler-completion test.
- `transaction-lifecycle-v1`: fixed prevalidation, begin/work/commit/rollback/close ordering, exact-count, Python/Java expected-failure, cleanup-failure, commit-outcome-unknown, committed-close-failure, and control-flow/Java-error propagation cases for an injected transaction adapter. It accepts no caller input and calls no `system.db` function, database, connection, statement, file, network, or external resource.
- `idempotency-state-v1`: fixed validation, claim-state, duplicate/conflict suppression, explicit retry authorization, bounded attempt, processor, completion-record, outcome-unknown, Python/Java failure, and propagation cases for an injected idempotency adapter. It accepts no caller input and calls no tag, message, database, durable store, file, network, or external resource; passing results do not prove exactly-once behavior or real store atomicity/durability.
- `scope-capability-contract-v1`: fixed exact-scope/operation/Boolean validation and ordered documented-scope, availability, resource, authorization, completion, and Vision UI-thread decisions for seven example operations. It includes current per-function Perspective file-scope cases, accepts no caller input, and calls no `system.*` function or external resource; passing results prove only the policy adapter, while official per-function pages support the recorded scope mappings.
- `date-time-contract-v1`: fixed epoch-unit, exact integer/Boolean, explicit-zone, unknown-zone fallback, strict/full parsing, DST gap/overlap, and elapsed-versus-calendar-day cases using Java date classes. It accepts no caller input, current time, path, network value, or external resource; the fixed `America/Chicago`, `UTC`, 1900-through-2099 validation range, locale, and Java 17 outcomes are fixture boundaries rather than universal time-zone guarantees.
- `logging-diagnostic-contract-v1`: fixed exact-schema, severity-policy, bounded-message, correlation-ID/control-character, debug-laziness, unknown-sensitive-field, logger-failure, and propagation cases plus a read-only embedded `LoggerEx` surface probe. It accepts no caller input, emits no real log message, changes no logging level, and performs no filesystem/network/Gateway-resource operation; its limits and four-event policy are fixture values rather than a universal observability schema.
- `python3-api-guardrails-v1`: fixed absence/error probes for 22 selected Python 3-only attributes, `collections.abc`, and dictionary merge with `|`, plus bounded in-memory Python 2 alternatives. It accepts no caller-controlled owner, attribute, module, path, command, or data and performs no filesystem, network, process, or Gateway-resource operation.
- `exception-boundaries-v1`: fixed routing, type-relation, exact/mixed catch, bare-catch, `finally`, and cleanup-failure masking probes for four Python and four Java exception objects. It accepts no caller-provided exception, class, code, or message and performs no thread interruption or external operation.
- `builtin-surface-v1`: selected Python 2/3 built-in names, `__builtin__` versus `builtins`, eager `map`/`filter`/`zip`, Python 2 `map(None, ...)` padding, `reduce`, and a bounded name-count/hash summary.
- `stdlib-inventory-v1`: read-only `pkgutil.iter_modules()` comparison against the fixed 227-name standalone allowlist plus `sys.builtin_module_names`. It returns no unallowlisted project/third-party names and imports no target module; the tested embedding discovered 226 allowlisted names, with only `ensurepip` missing.
- `dependency-resolution-v1`: fixed, non-initializing Java class probes through the thread-context and Jython-defining loaders. It returns only fixed class names, resolution booleans, package versions, loader labels, and sanitized code-source filenames; it accepts no caller-supplied class or path. A Java `ClassNotFoundException` is captured explicitly as a result because Java throwables can bypass a Python-only `except Exception` boundary.
- `ignition-basics-v1`: read-only availability of fixed database, transaction, tag, asynchronous, Vision, and Perspective function names in Gateway Web Dev scope; availability is not permission or behavior proof.
- `data-boundaries-v1`: current and legacy dataset-function availability, fixed Dataset/PyDataset iteration, JSON encode/decode and explicit malformed-input behavior, epoch-millisecond date round trip, timezone return type, and message-function availability. It performs no sends or project-resource writes.
- `secrets-availability-v1`: read-only name availability for the three Ignition 8.3.8 SecretConfig functions and five earlier provider/encryption functions. It calls no secret function and returns no provider, secret, configuration, ciphertext, or plaintext value.
- `java-interop-v1`: Python callback adaptation, callback arity rejection, ASCII and non-ASCII Java `char` typing, and Java compiler availability.
- `language-compat-v1`: syntax matrix, XML imports/parsing, and three fixed import attempts. Dataclasses, NumPy, and pandas all returned `ImportError` on the tested Gateway; the probes record bounded unavailability, not support. The top-level `passed` Boolean covers only the syntax/XML conditions in API v0.103.0 and excludes `environmentImports`; inspect each package's `available` and `exceptionType` fields directly and never infer package state from the overall pass.
- `embedded-runtime-v1`: warnings with restored `sys.argv`, protocol-2 pickle fixture, interactive compilation, and Java 17 wildcard imports.
- `native-compat-v1`: Jython import suffixes, extension-compiler refusal, a pure-Python calculation, and a Java-library alternative. In API v0.103.0, its top-level `passed` explicitly covers the fixed implementation, `.py`/`$py.class`, zero C-extension/binary suffixes, compiler/warning, pure-Python, and Java checks; it still does not cover an arbitrary package or optional native bridge, so inspect the fields and `scopeNote` before making the bounded baseline claim.
- `system-config-read-v1`: bounded fixed configuration discovery with no write calls or configuration/file values returned.
- `perspective-tag-read-v1`: read-only value, quality, and timestamp observations for exactly two retained `[Sample_Tags]LLM Tests/T05` memory tags plus one fixed missing-path negative case. It accepts no path or value and performs no write.
- `perspective-click-counter-v1`: fixed pure-function counter inputs and exact invalid type/range cases. It accepts no caller input and performs no Perspective session, component, tag, or external operation.
- `perspective-boolean-tag-write-v1`: authenticated access to exactly `[Sample_Tags]LLM Tests/T07/WriteTarget`. It accepts one Boolean, defaults to dry-run, requires `apply: true` when `dryRun: false`, verifies write quality and readback, and forbids caller-selected paths. A passing dry-run proves no write; inspect `dryRun`, `writeAttempted`, and action-level `externalSideEffects` before interpreting success.
- `perspective-session-navigate-v1`: authenticated, allowlisted navigation for one verified `llm-tools` browser session/page. It validates a UUID session, page ID, and one of three fixed page routes, defaults to dry-run, and requires apply. A successful apply proves only that `system.perspective.navigate` returned without throwing; it does not prove arrival, rendering, or component behavior. The tested Gateway had no browser UUID session, so positive live navigation remains unproven.
- `perspective-static-view-folder-v1`: authenticated create/update of one owned Perspective view shape beneath `LLM Tests/Folder Tests`. It restricts names and label text, defaults to dry-run, requires an exact prior view hash for updates, uses the project scan lock, performs atomic file replacement, requests a scan, and verifies the owned shape and label readback. It is a bounded project-folder mutation, not general Perspective authoring.
- `perspective-page-route-folder-v1`: authenticated create/update of an `/llm-tests/...` page route targeting an existing `LLM Tests/...` view. It defaults to dry-run, requires the exact current page-config hash, preserves the existing page configuration, uses the scan lock, and verifies the route and route count before reporting success. It is not a general page-config editor and HTTP shell success is not render proof.
- `perspective-project-script-folder-v1`: authenticated create/update of only the fixed top-level Gateway module `LLMTestsPerspectiveT11` using built-in revision-1 or revision-2 source. It defaults to dry-run, requires the exact current code hash for update, uses atomic folder/file changes plus scan, and verifies revision readback. It accepts no caller-provided source and does not support arbitrary or nested modules.
- `perspective-project-script-t11-invoke-v1`: authenticated invocation of the fixed T11 module's `build_status` with a bounded message and integer count. It validates the exact returned envelope and performs no write. It requires the fixed module to exist and proves Gateway-scope activation only, not Perspective client-event execution.
- `tag-read-v1`: read up to 64 caller-selected qualified tag paths after validating one to eight caller-supplied allowed prefixes, path length and traversal guards, exact result count, value serialization, quality, and timestamps. In v0.103.0 it preserves bounded arrays and JSON-like objects instead of stringifying them: arrays cap at 256 items, objects at 128 members, nested serialization at depth four, and text at 4096 characters, with per-item `kind` and `truncated` fields. It performs no write. Prefixes reduce accidental scope only; they are not authorization, so constrain the API key and Web Dev resource separately.
- `tag-browse-v1`: browse beneath one caller-scoped qualified base path with bounded recursive/type filters and at most 500 returned rows. It sorts and truncates the returned projection, reports continuation/truncation, and performs no write. Prefixes are not authorization, and a complete result applies only to that bounded call.
- `tag-write-v1`: validate the native API token, then dry-run or apply up to 32 caller-selected scalar tag writes beneath one to eight caller-supplied prefixes. It rejects unknown fields, traversal, provider-root prefixes, out-of-prefix paths, non-scalar or non-finite values, and missing explicit apply; applied calls read before, write once, read after, and report per-item qualities and equality. Prefixes are accidental-scope guards, not authorization. Require `allVerified: true`, and inventory before retry after any ambiguous or partial outcome.
- `tag-query-history-v1`: query raw history for one to eight exact qualified tag paths beneath one to eight caller prefixes. It requires integer epoch-millisecond bounds with a positive window no longer than 24 hours, caps rows at 200, uses TALL format, serializes timestamps, rejects unknown fields/root/traversal/prefix escape, and performs no write. Prefixes are accidental-scope guards, not authorization. Require the exact path/window and inspect every row; returned size can imply historian aggregation/interpolation and does not prove unqueried samples.
- `alarm-query-status-v1`: query current alarms only beneath one to eight caller-supplied qualified tag prefixes. It converts those prefixes to provider/source filters, accepts only allowlisted state and priority values plus up to 16 explicitly named associated-data properties, caps returned rows at 200, reports total/truncation, and performs no write. Requested properties are returned under each row's `data` object and missing properties serialize as null. Prefixes are not authorization. Returned `State` and `Priority` fields may be numeric even when documentation examples use names.
- `alarm-query-shelved-v1`: list up to 200 currently shelved alarm source paths beneath one to eight qualified tag prefixes. It returns path, expiration, expired state, and user with completeness/truncation fields and performs no write. Prefixes are accidental-scope guards, not authorization.
- `alarm-acknowledge-v1`: validate the native API token, one to eight qualified tag prefixes, one to 16 UUID event IDs, a required bounded username, and optional bounded notes. It defaults to dry-run, queries every event inside scope before apply, calls `system.alarm.acknowledge` once, then verifies each retained event is acknowledged. Require `dryRun: false`, `writesAttempted: true`, `ok: true`, `allAcknowledged: true`, and an empty `failedEventIds` list for a verified mutation; reconcile state before any retry after an exception or failed readback.
- `alarm-shelve-v1`: validate the native API token and apply one to 16 exact alarm source paths beneath one to eight prefixes for 1 to 3600 seconds. It defaults to dry-run and verifies every requested source appears in the scoped shelved-path readback. Require `allVerified: true` for applied success; prefixes are not authorization.
- `alarm-unshelve-v1`: validate the native API token and remove shelving for one to 16 exact scoped alarm source paths. It defaults to dry-run and verifies every requested source is absent from the scoped shelved-path readback. Require `allVerified: true` for applied success; prefixes are not authorization.
- `grouped-udt-file-v1`: inspect, create, or replace one validated grouped-UDT resource for a caller-supplied provider and one to eight allowed group-path prefixes. Every operation requires a verified native API token. The current prefix guard uses plain string `startswith`, not a path-segment boundary: a prefix such as `Area/A` also matches `Area/AB`. Treat it only as an accidental-scope guard, choose narrowly controlled paths, and never use it as authorization. Create/replace accepts exactly one JSON source, limits the canonical content to 128 `UdtType` rows and 524288 bytes, defaults to dry-run, uses same-directory atomic moves, forbids delete, and requires an exact uppercase SHA-256 for replace. The action does not acquire the configuration scan lock or perform a scan; the caller must hold the external lock through mutation and subsequent scan/readiness verification. After any applied exception, treat outcome as unknown and inspect the resource/hash before retrying even if `writeAttempted` is false.
- `alarm-query-journal-v1`: query one named alarm journal for one to 16 exact UUID event IDs beneath one to eight qualified tag prefixes. It requires integer epoch-millisecond bounds spanning at most one hour, allows up to 16 explicitly named associated-data properties, caps filtered rows at 200, includes shelved/data events but excludes system events, sorts by event time/state/ID, and performs no write. Prefixes are not authorization. Require the exact journal, event IDs, time window, properties, and `complete: true`; do not infer notification delivery, journal durability, or unqueried transitions.
- `tag-read-complex-v1`: read up to 32 exact qualified tag paths beneath one to eight segment-aware prefixes and serialize scalar, array, dataset, or document values without writing. Caller-selectable bounds cap datasets at 100 rows by 64 columns, arrays/collections at 256 elements, documents at 65536 UTF-8 bytes and depth 16, and text at 4096 characters. Inspect each item's `kind`, quality, type, dimensions/counts, `truncated`, and `value`; `ok: true` proves the bounded read/projection completed, not that `allGood` is true or that truncated/unsupported values are complete. Prefixes are accidental-scope guards, not authorization.
- `tag-document-cas-v1`: validate a native API token and one exact Document-tag path beneath one to eight segment-aware prefixes, then dry-run or write one bounded JSON object under an immediate timestamp-and-SHA-256 precondition. Applied calls use one `writeBlocking` call and verify the post-write Document hash/readback. This is optimistic precondition checking, not an atomic compare-and-swap primitive; reconcile current state before retry after any ambiguous result.
- `expression-tag-batch-v1`: dry-run or create one owned run folder beneath `[default]_expression_skill_tests` containing up to 100 bounded expression tags. Caller expressions are limited to the helper's side-effect-free subset; dynamic tag calls, `runScript`, arbitrary Jython, and bound references are rejected. Apply requires token verification, `apply: true`, a run ID, and an idempotency key, then reports configuration qualities and bounded readback.
- `expression-tag-fixture-suite-v1`: dry-run or create a server-owned fixed expression fixture profile beneath one owned run folder. The supported profiles exercise sibling/dynamic references, quality behavior, and fixed server-owned `runScript` exception controls without accepting caller-supplied expressions or Jython.
- `expression-tag-cleanup-v1`: inspect/dry-run or delete only the exact owned expression run folder after token verification, ownership metadata checks, explicit apply, and the fixed cleanup confirmation. Require verified absence; cleanup does not authorize deleting arbitrary tags or parent folders.
- `event-stream-expression-fixture-v1`: operate the fixed `expr83-event-stream-03b932b7` Event Stream expression fixture through `setup`, `trigger`, `inspect`, and `cleanup`. It owns one fixed run path, accepts only source values 42 or 43, defaults mutations to dry-run, and reports trigger completion/readback. It accepts no caller code, project, stream path, or tag path.
- `perspective-named-query-expression-fixture-v1`: operate a fixed Perspective view, three fixed Named Queries, fixed route, translation term, and owned tag run through `setup`, `navigate`, `select`, locale, inspection, navigation-away, and cleanup operations. Mutation paths require token verification and default to dry-run; mounted/browser observations are fixture-specific and do not prove arbitrary Perspective execution.
- `sfc-transition-expression-fixture-v1`: operate fixed SFC transition-expression projects, charts, cases, and tag fixtures through `setup`, `start`, `set-gate`, `retarget`, `inspect`, and `cleanup`. It accepts no caller Jython, project, chart, expression, or tag path; applied chart starts and variable/tag writes are real bounded Gateway effects.
- `sfc-parallel-expression-fixture-v1`: operate the fixed parallel-cancel SFC fixture through setup, tag-driven start, cancel writes, immediate start/cancel, inspection, and cleanup. It accepts no caller chart/project/tag path or Jython and reports bounded running-chart and tag observations.
- `sfc-parallel-expression-suite-v1`: operate nine allowlisted fixed SFC parallel-expression cases through setup, case start, trigger change, inspection, and cleanup. Caller-selected case IDs and the SFC-013 instance slot are allowlisted; chart paths, projects, tag paths, raw values, expressions, and Jython remain server-owned.
- `vision-skill-lab-v1`: manage only the fixed disposable `vision_skill_lab` internal user used by `V83_SKILL_LAB`. Setup and cleanup are authenticated, dry-run by default, ownership-marked, and read back. Contract 1.14.0 retains the fixed button, snapshot, window-state, runtime-profile, and Client `language-boundary` bridges and adds fixed `gateway-language-boundary`. The Gateway operation accepts no Client session or caller code, corpus, source, project, handler, payload, tag path, timing, scope, or expected result. It creates only `[default]_VisionSkillLabP06T01/LanguageBoundary`, dispatches the server-owned corpus to the fixed scope-`G` Shared handler `vision-p06-t01-gateway-language-boundary`, requires one Gateway `SENT` status, records the Gateway-specific bridge contract plus exact scope evidence (`handlerScope == "G"` and `systemFlagsAvailable == false`), accepts only a mapping-compatible decoded scope object with those exact two keys, normalizes its fixed native text/Boolean scalars before exact comparison, and deletes its temporary root in `finally`. Require `code == "gateway_language_boundary_observed"`, all eight fixed Python 2.7 cases accepted, all five fixed Python 3-only cases rejected with `SyntaxError`, exact runtime values, Good qualities, cleanup, and `validationFailure == null`. On a bounded schema failure, `languageBoundaryDiagnostic` may echo only the fixed server-owned candidate and `languageBoundaryValidationStage` may identify only a fixed allowlisted validation stage; neither is a passing result. The Gateway operation remains uncredited until its bounded live cycle passes.
- `vision-client-sessions-v1`: read the exact expected project's bounded Vision session rows from `system.util.getSessionInfo`. It defaults to excluding Designers, accepts only an optional Boolean `includeDesigners`, returns no address column, performs no write, and is an authenticated fallback when the official 8.3.8 Vision client-list route is unavailable. A successful query proves only current Gateway registration, not client readiness, open windows, component state, or rendering.
- `overload-resolution-v1`: fixed in-memory Java overload fixture loaded from two embedded class-byte constants. It adds no path, file, or external fixture; the result verifies the exact fixed/varargs cases, two embedded classes, no external fixture, and unchanged `sys.path`.
- `socket-unicode-v1`: bounded localhost-only raw-socket encoding, timeout, error, and cleanup cases.
- `http-client-v1`: fixed localhost `system.net.httpClient` health/refused-connection checks, separate from raw sockets.
- `unicode-data-v1`: selected Unicode 15.1 names, data version, invalid-name behavior, and no Python 3 inference.
- `sys-readonly-v1`: literal and constructed-name protection for fixed `sys.exec_prefix`, plus complete temporary-state cleanup.

Treat every result as fixture-scoped. Do not convert a passing bounded check into a general guarantee about all libraries, hosts, JVMs, Unicode behavior, concurrency, or Ignition resources.

## Preserve the Python 2.7.4 regression floor

After any relevant customer-skill or API change, keep the fixed `runtime-profile-v2`, `python2-guardrails-v1`, `python2-module-names-v1`, `python3-api-guardrails-v1`, `builtin-surface-v1`, `text-byte-boundaries-v1`, and `import-fallback-guardrails-v1` actions passing. The syntax contract must continue to reject all 17 maintained Python 3-only forms and accept all seven maintained valid Python 2.7 forms. The module and API actions must continue to distinguish verified Python 2 spellings and alternatives from the fixed Python 3 names and attributes. The built-in action must continue to prove the fixed eager `map`/`filter`/`zip`, `map(None, ...)`, `reduce`, Python 2 built-in-name, and `__builtin__`/`builtins` conditions.

Do not add an endpoint that accepts caller-provided source code merely to lint or compile a draft. Use the customer skill's local read-only `scripts/audit_python3_drift.py` and compile-only `scripts/jython_compile_gate.py` outside the Gateway, then use fixed API actions for embedded evidence. A clean local audit, a successful compile, and a passing embedded matrix are separate evidence layers; none proves the others or establishes arbitrary package or scope compatibility.

## Extend the API only with a fixed fixture

When a needed capability is absent:

1. Establish the exact upstream change or official Ignition API surface.
2. Design a focused success case, a failure-path case, strict time/size/count limits, and explicit cleanup.
3. Add a new hard-coded action branch to `doPost.py`; accept no caller-controlled executable behavior or sensitive inputs. Keep the branch to fixed dispatch when the implementation is large.
4. Add the action to the current versioned inventory in `LLMProjectFolderFixtures`, keep both Web Dev methods delegated to that same inventory function, and increment the API version and versioned inventory name together when the contract changes. Preserve the prior inventory function only when older source/tests still need it.
5. Update any existing action that asserts the live API version.
6. Compile-check both method files and all 16 shipped helper modules with standalone Jython 2.7.4. The v0.25.0 preflight proved that a large inline `doPost` can exceed Jython's JVM method-size limit. Keep large implementations in explicit Project Library resources and verify each import live.
7. Create a project ZIP with `project.json` at the root and forward-slash entry names. Include the normalized two-method Web Dev resource plus the 16 helper modules listed under **Locate the implementation**; the v0.103.0 customer project allowlist has 37 exact entries. Do not ship disabled method placeholders, generated fixture targets, retained Perspective test views/page config, Named Query, SFC, or Vision project fixtures, tags, client tags, compiled `$py.class` files, or temporary overlap resources.
8. Export the current `llm-tools` project before import, then use the authenticated project-import endpoint discovered from `/openapi.json` with `overwrite=true`.
9. Treat HTTP 200 from project import as acknowledgement, not live-route readiness. Poll the fixed GET route with one bounded shared deadline until it reports the exact expected API version, action set, and safety fields; fail closed if an older generation remains. Prior measured imports have briefly served an older API generation after HTTP acknowledgement.
10. Run the new action, the safe compatibility regressions, prescribed no-write validation/dry-run cases for every parameterized mutation, the unknown-action rejection, and the trial-state check only after that readiness gate. Do not expect a fresh package's fixed T11 invocation to pass before its explicit create workflow.
11. Promote only the exact observed behavior to the customer Jython-writing skill.
12. Update internal evidence, claim coverage, testing, and handoff records.

Never replace the bundled Ignition Jython runtime or modify unrelated projects.

## Synchronize the Python backup

After `doPost.py` is final and all regressions pass, refresh `llmImport.py` and `COPY TO WEBDEV - doPost.py` as exact byte-for-byte copies of `doPost.py`, and refresh `COPY TO WEBDEV - doGet.py` from `doGet.py`. Verify each SHA-256 pair. This backup mirrors POST dispatch code only; separately package and verify all 16 helper resources referenced by the Web Dev methods.

Resolve both paths from the directory containing this `SKILL.md`:

```powershell
$skillRoot = Resolve-Path "<directory containing SKILL.md>"
$resourceDir = Join-Path $skillRoot `
    "llm-tools-project\com.inductiveautomation.webdev\resources\llmImport"
$doPost = Join-Path $resourceDir "doPost.py"
$backup = Join-Path $skillRoot "llmImport.py"

Copy-Item -LiteralPath $doPost -Destination $backup -Force

$sourceHash = (Get-FileHash -LiteralPath $doPost -Algorithm SHA256).Hash
$backupHash = (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash
if ($sourceHash -cne $backupHash) {
    throw "llmImport.py is stale; the iteration is incomplete."
}
```

`doGet.py` remains separately preserved inside `llm-tools-project`; `llmImport.py` mirrors POST because POST contains the fixed test implementation.

## Return an evidence-oriented result

Report:

- live API version and discovered action count
- action names executed
- `accepted` and the action-specific meaning of `passed` for every action
- exact returned fields and expected values supporting each promoted claim, including whether each field participates in `passed`
- rejected unknown-action result
- trial state at test time
- fixture boundaries and untested areas
- source, live, and backup hash agreement
- package validation and cleanup status

Do not include access values, raw sensitive configuration, or unrelated Gateway data.
