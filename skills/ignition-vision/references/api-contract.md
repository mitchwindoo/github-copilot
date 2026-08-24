# Ignition Runner API Contract For Vision Work

## Contents

- [Connection and capability discovery](#connection-and-capability-discovery)
- [Runner HTTP 402 and the Gateway shell](#runner-http-402-and-the-gateway-shell)
- [Common request and response rules](#common-request-and-response-rules)
- [Read-only discovery](#read-only-discovery)
- [Expression binding initialization diagnostics](#expression-binding-initialization-diagnostics)
- [Resource lifecycle](#resource-lifecycle)
- [Gateway and client logs](#gateway-and-client-logs)
- [Fixed Vision Client actions](#fixed-vision-client-actions)
- [State guards, restoration, and retries](#state-guards-restoration-and-retries)
- [Safe fallbacks](#safe-fallbacks)
- [Shipped API helpers](#shipped-api-helpers)

## Connection And Capability Discovery

Supply connection data through environment variables:

```text
IGNITION_RUNNER_URL=<approved runner endpoint>
IGNITION_RUNNER_TOKEN=<runner token>
IGNITION_TARGET_PROJECT=<exact project name>
IGNITION_RUNNER_OUTPUT_DIR=<optional evidence directory>
```

Send JSON over `POST` and place the token only in `X-LLM-Runner-Token`. Never print, store, or embed the token in a package, project resource, screenshot, log, or handoff.

Start every workflow with:

```json
{
  "action": "health",
  "requestId": "vision-health-001"
}
```

Require `ok:true`, a runner at or above the skill minimum, `tokenConfigured:true`, the intended action in `supportedActions`, and every required capability in `features`. Use the recommended runner when available. Live health is authoritative.

## Runner HTTP 402 And The Gateway Shell

An expired trial or license gate can reject the Web Dev runner route with HTTP 402 while the Gateway shell remains reachable. This is a separate control plane, not evidence that the runner executed or changed version.

For an operator-authorized direct shell workflow:

1. Read `GET /data/status/trial` and proceed only when the response explicitly reports an expired trial.
2. Authenticate through the Gateway's configured IdP flow; keep credentials, cookies, challenge tokens, and OIDC tokens in memory only.
3. Read `GET /data/status/permissions` and require `config:true` for the authenticated session.
4. Require a separate exact reset confirmation before `PUT /data/status/trial`.
5. Re-read `GET /data/status/trial` and require an active, positive remaining duration.
6. Discard the authenticated session and re-run runner `health`, capability, performance, client-session, and project-state gates before resuming.

If the Gateway version, IdP flow, permissions response, or trial endpoint differs, stop. This package does not ship a reset/recovery executable or a desktop fallback. Never use runner self-update as a workaround because HTTP 402 rejects the request before runner dispatch.

## Common Request And Response Rules

- Include an explicit `action` and a stable, unique `requestId` in every request.
- Send a JSON object. Treat malformed JSON, an empty object, an unknown action, a non-object body, and an oversized body as failures.
- Use the exact project name returned by `projectsList`.
- Use fully qualified tag paths and exact project-resource paths.
- Set conservative result caps. Reject truncated evidence when completeness is required.
- Treat HTTP status and the response envelope separately. HTTP 200 does not override `ok:false`, an illegal-name result, a failed quality, truncation, or recovery-required state.
- Correlate client responses by project, client ID, handler, request ID, mailbox, resource state, and fixed resource-marker identity where the action requires them.
- Redact authorization, cookies, identity tokens, credentials, package bodies, script bodies, and usernames when the workflow does not need them.

A successful read should identify its source, cap, returned count, truncation state, and relevant hashes. A successful guarded write should also report the dry-run/apply mode, files changed, backup, project scan, verification, and recovery state.

## Read-Only Discovery

Use these actions before mutation:

| Area | Actions | Required decision |
|---|---|---|
| Gateway/project | `gatewayInfo`, `projectsList`, `projectInfoRead` | Select the exact project and record live connection defaults. |
| Tags | `tagProviders`, `tagBrowse`, `tagRead`, `historyProbe` | Prove provider availability, concrete paths, values, and quality. |
| Data | `databaseConnectionsList`, `namedQueriesList`, `namedQueryRead`, eligible `namedQueryPreview` | Prove database health and query identity without unrestricted SQL. |
| Resources | `projectResourcesList`, `projectResourceNameValidate`, `projectResourceRead`, `projectResourceExport` | Prove legal names, exact files, metadata, state hashes, and exportability. |
| Vision | `visionWindowInspect`, `visionTemplateInspect`, `visionWindowDependencyPreflight` | Prove bounded structure, bindings/scripts, hierarchy, layout, and dependencies. |
| Clients | `visionClientSessionsQuery` | Select one exact non-Designer client or require zero clients before a resource change. |
| Operations | `logQuery`, `alarmStatusQuery`, `alarmJournalQuery`, `auditQuery` | Collect focused Gateway evidence with bounded filters. |

For `projectInfoRead`, request connection defaults only when the live feature is present. A blank or unavailable default tag provider means unqualified tag paths are not portable.

For `projectResourceNameValidate`, require every segment to pass the installed Gateway validator and `allPathsLegal:true`. Do not replace this with a guessed regular expression.

For `visionWindowInspect` and template inspection, require the expected serialization format, complete non-truncated component/interaction evidence, valid local and absolute bounds, and a state hash. Binary transcode is structural evidence only; it does not execute scripts or prove pixels.

## Expression Binding Initialization Diagnostics

Use serialized inspection before opening a generated or transformed window in Designer when an expression binding reads tags. Require `visionWindowInspect` in `supportedActions` and `visionExpressionBindingInitialValueInspection` in `features`.

```json
{
  "action": "visionWindowInspect",
  "requestId": "vision-expression-init-001",
  "targetProject": "<project>",
  "resourcePath": "com.inductiveautomation.vision/windows/<window>",
  "allowedResourcePrefix": "com.inductiveautomation.vision/windows/<window>",
  "maxFiles": 20,
  "maxBytes": 2097152,
  "maxDecompressedBytes": 8388608,
  "maxComponents": 500,
  "maxInteractions": 500
}
```

For a window with bound-tag expressions, require all of the following before claiming strict pre-open initialization safety:

- `ok:true`, the expected resource/state hash, `componentsTruncated:false`, and `interactionsTruncated:false`;
- `interactionDiagnosticsAvailable:true` and `expressionInitialQualifiedValueInspectionAvailable:true`;
- for binary-v2, `binaryTranscodedForInspection:true` through the installed target runtime;
- `bindingEvidence.expressionInitialQualifiedValueEvidenceComplete:true` and `expressionInitialQualifiedValueAggregateIncludesAllBindings:true`;
- `bindingEvidence.expressionInitialQualifiedValueStatus:"safe"`;
- all six `expressionAdapterInitialQualifiedValue*Count` and `boundTagInitialQualifiedValue*Count` missing/explicit-null/unresolved counters equal zero;
- `bindingEvidence.designerInitializationRiskDetected:false` and `bindingEvidence.boundTagPreSubscriptionNullRiskDetected:false`;
- `bindingEvidence.expressionInitialQualifiedValueWarningCodes:[]` and `bindingEvidence.expressionInitialQualifiedValueAdvisoryCodes:[]`.

Treat `unknown`, `at-risk`, unavailable transcode, truncated evidence, a missing aggregate, or any nonzero listener missing/null/unresolved count as a failed gate. A `not-applicable` status is acceptable only when complete evidence proves the resource has no relevant bound-tag expression binding. The inspector reads serialized state; it does not execute the expression or prove its later runtime value.

Gateway `logQuery` cannot read an error dialog or Log Viewer entry from the Designer JVM. `visionClientLogQuery` targets a correlated non-Designer Vision Client, and `visionDesignerSessionsQuery` inventories Designer sessions but does not retrieve Designer logs. When this inspection feature is unavailable, export the exact resource and use the matching Ignition/IA Jython serializer to inspect both adapter and nested-listener initial `QualifiedValue` state. If that cannot be done, do not claim the resource is Designer-safe and do not substitute Gateway logs or successful tag reads.

## Resource Lifecycle

### Export

Use `projectResourceExport` for a bounded read-only ZIP representation of one resource. Set the exact project, resource path, allowed prefix, file cap, and byte cap. `includePackageBase64:false` is sufficient for readiness and hash evidence; request package bytes only when the workflow explicitly needs them and can protect the payload.

### Import

Dry-run first:

```json
{
  "action": "projectResourceImportZip",
  "requestId": "vision-import-dry-001",
  "targetProject": "<project>",
  "allowedResourcePrefix": "com.inductiveautomation.vision",
  "packageBase64": "<redacted package>",
  "dryRun": true
}
```

Review normalized destinations, illegal names, duplicates, conflicts, unchanged files, manifest validation, and expected final files. Apply only with:

```json
{
  "dryRun": false,
  "confirmProjectResourceImport": "IMPORT_PROJECT_RESOURCE_ZIP"
}
```

If overwriting an existing file is intentional, also require `overwriteExisting:true`, `confirmOverwrite:"OVERWRITE_PROJECT_RESOURCES"`, and current-state evidence. Do not retry after a lost response until readback and backup inventory reconcile the actual state.

### Delete

Use `projectResourceDelete` only for one exact manifest-backed resource. Dry-run, review every affected file, then apply with the dry-run `resourceStateSha256` as `expectedResourceStateSha256` and:

```json
{
  "confirmProjectResourceDelete": "DELETE_PROJECT_RESOURCE"
}
```

Reject nested-resource deletion, stale state, ambiguous scope, missing backup, failed scan, or failed absence verification. Use normal backup inventory and `rollback` with confirmation `ROLLBACK` when restoration is required.

### Relocate

Use `visionWindowRelocate` only when the live action and all relocation features are present. It is for a same-version, manifest-backed, relocatable window format—not arbitrary binary renaming.

Dry-run with exact source and destination resource paths. Review identity rewrite and dependency impact. Apply with the dry-run source state as `expectedSourceResourceStateSha256`, an absent/expected destination state, and:

```json
{
  "confirmVisionWindowRelocate": "RELOCATE_VISION_WINDOW"
}
```

After apply, require source absence, destination identity and state, backup presence, scan completion, and dependency preflight on the destination.

## Gateway And Client Logs

`logQuery` reads Gateway wrapper logs. Keep it narrow with a bounded time range, levels, `maxResults`, and at least one of `loggerContains`, `messageContains`, or `textContains`. An intentionally broad query additionally requires:

```json
{
  "allowBroad": true,
  "confirmBroadLogQuery": "ALLOW_BROAD_LOG_QUERY"
}
```

`visionClientLogQuery` reads one selected Vision client's bounded log appender through a fixed handler. It requires confirmation `QUERY_VISION_CLIENT_LOG`, exact client selection, a dedicated mailbox, a Good baseline, and `mailboxRestored:true` on success. Broad client-log queries require their separate broad-query confirmation.

Gateway and client logs are different evidence planes. Never infer clean client logs from a clean Gateway query.

## Client Session Versus Bridge Readiness

`visionClientSessionsQuery` proves that the Gateway registered a client session. It does not prove that the Vision application finished opening, the target project finished activation, Project Client Event Scripts installed their handlers, or the mailbox for a particular fixed bridge is ready.

For every fresh-client workflow:

1. Record the launch timestamp and the timestamp when one exact non-Designer session first appears.
2. Use a bounded total readiness deadline and bounded polling interval for the exact fixed read-only bridge needed by the workflow. Do not send a mutating client request while readiness is unknown.
3. Record `sessionReady` and `bridgeReady` separately. A message-send receipt without the correlated typed response is not bridge readiness.
4. Treat a bridge timeout as an observed diagnostic state, not as a clean client result and not automatically as a defective window.
5. Before stopping the owned client, preserve the exact session inventory, attempted action and error code, focused client-log result or its own timeout, bounded Gateway logs, captured launcher stdout/stderr when the workflow owns that process, resource path and state hash, and all timestamps.
6. Mark every source as `collected`, `unavailable`, `not-ready`, `not-applicable`, or `collection-failed`. Silence from an unavailable source is not a clean result.

The current recommended runner has no standalone bridge-readiness action. Until live `health` advertises one, readiness is the first successful correlated response from the exact fixed bridge being used. Do not document or call a proposed readiness action as though it exists.

## Fixed Vision Client Actions

Fixed actions are allowlisted bridges, not generic remote-control surfaces. Require the exact action, all action-specific feature flags, structural/dependency preflight, one selected client, fixed handler identity, a current resource hash, bounded response limits, zero unexpected side effects, and verified mailbox restoration.

| Action | Confirmation | Bounded purpose |
|---|---|---|
| `visionClientRuntimeQuery` | `QUERY_VISION_CLIENT_RUNTIME` | Open-window inventory, allowlisted component state/geometry/dataset shape, and optional root screenshot/text fit. |
| `visionClientLogQuery` | `QUERY_VISION_CLIENT_LOG` | Focused client log rows. |
| `visionClientAlarmStatusTableQuery` | `QUERY_VISION_CLIENT_ALARM_STATUS_TABLE` | One exact table's bounded alarm rows under fixed temporary query settings. |
| `visionClientPowerTableQuery` | `QUERY_VISION_CLIENT_POWER_TABLE` | One exact table's bounded loaded dataset after fixed dependency checks. |
| `visionClientPowerTableSelectionProbe` | `PROBE_VISION_CLIENT_POWER_TABLE_SELECTION` | One fixed Power Table selection, clear, sort/mapping, mapped selection, and exact sort/selection restoration sequence. |
| `visionClientEasyChartQuery` | `QUERY_VISION_CLIENT_EASY_CHART` | Fixed chart configuration and bounded loaded-data state. |
| `visionClientEquipmentScheduleQuery` | `QUERY_VISION_CLIENT_EQUIPMENT_SCHEDULE` | Fixed schedule datasets and read-only component state. |
| `visionClientStatusChartQuery` | `QUERY_VISION_CLIENT_STATUS_CHART` | Fixed series/state/color datasets and read-only state. |
| `visionClientGanttChartQuery` | `QUERY_VISION_CLIENT_GANTT_CHART` | Fixed task dataset and read-only chart configuration. |
| `visionClientBoxWhiskerQuery` | `QUERY_VISION_CLIENT_BOX_WHISKER` | One fixed typed distribution dataset and read-only Box-and-Whisker configuration after exact structural/dependency preflight. |
| `visionClientTemplateCanvasQuery` | `QUERY_VISION_CLIENT_TEMPLATE_CANVAS` | Fixed template instances, parameters, geometry, and binding quality. |
| `visionClientProjectUpdate` status | `QUERY_VISION_CLIENT_PROJECT_UPDATE` | Fixed client project-update status tags. |
| `visionClientProjectUpdate` apply | `APPLY_VISION_CLIENT_PROJECT_UPDATE` | Schedule only the fixed Vision project update operation. |
| `visionClientLayoutProbe` | `PROBE_VISION_CLIENT_LAYOUT` | One fixed resize/restore geometry probe. |
| `visionClientTagSessionProbe` | `PROBE_VISION_CLIENT_TAG_SESSION` | One fixed Client Tag session-isolation probe. |
| `visionClientButtonActionProbe` | `TRIGGER_VISION_BUTTON_ACTION` | One fixed button event and expected navigation transition. |

Do not widen these payloads to accept caller-selected scripts, methods, expressions, components, properties, templates, queries, or tag paths. If the fixed contract does not match the customer resource, design a new bounded action and validate it before use.

Dispatch each action through the exact Client Event Script handler and response mailbox declared by its live capability contract. A healthy mailbox for another fixed bridge is not interchangeable; a send receipt without the correlated response is transport evidence only.

## State Guards, Restoration, And Retries

- Use state hashes from the immediately preceding read or dry-run.
- Reject state drift before writing.
- Snapshot every temporary mailbox or component setting and verify Good quality before dispatch.
- Restore on request-write failure, send failure, timeout, malformed response, negative response, handler failure, and success.
- Return `recoveryRequired:true` when restoration cannot be verified; do not surface an otherwise successful client payload as success.
- Treat a message receipt such as `SENT` as transport evidence only.
- For a lost HTTP response, reconcile resource state, backups, session state, and mailbox state before retrying.
- Require project scan completion and post-scan readback for resource changes.

## Safe Fallbacks

- Missing resource-name validation: stop the write and upgrade the runner.
- Missing structural inspector: use bounded read/export and state clearly that hierarchy and bindings were not verified.
- Missing dependency preflight: resolve each declared dependency individually and do not mutate while any dependency is unknown.
- Missing client action: build and validate a new fixed bridge or stop; never use arbitrary `scriptEval` or desktop control as a substitute.
- Ambiguous clients: stop or require an exact client ID.
- Missing screenshot/text-fit capability: stop the pixel/text-fit claim until the fixed API capability is available.
- Failed restore or scan: stop, reconcile, and use the recorded backup path.

## Shipped API Helpers

`scripts/runner_client.py` provides authenticated JSON calls, stable request evidence, summary output, and recursive secret redaction. By default it writes outside the installed skill under the current working directory; set `IGNITION_RUNNER_OUTPUT_DIR` to choose another evidence root.

`scripts/export-validation.py` uses that client to inventory Vision resources, read file/hash metadata, request bounded export metadata, and write a read-only manifest. It never imports, deletes, relocates, or updates project resources.
