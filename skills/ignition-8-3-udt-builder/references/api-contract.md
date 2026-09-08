# API contract and request discipline

## Contents

- [Official Gateway routes](#official-gateway-routes)
- [Tag import result](#tag-import-result)
- [Guarded llmImport tag actions](#guarded-llmimport-tag-actions)
- [Guarded exact tag deletion](#guarded-exact-tag-deletion)
- [Guarded grouped UDT file action](#guarded-grouped-udt-file-action)
- [Unknown-mutation rule](#unknown-mutation-rule)
- [Read and write UDT instance parameters](#read-and-write-udt-instance-parameters)

## Official Gateway routes

Always read the authenticated live OpenAPI first. The verified 8.3.8 contract exposed:

| Purpose | Method and path | Important inputs |
|---|---|---|
| Contract | `GET /openapi.json` | Gateway API token header |
| Tag export | `GET /data/api/v1/tags/export` | `provider`, `path`, `type=json` |
| Tag import | `POST /data/api/v1/tags/import` | `provider`, `path`, `type=json`, `collisionPolicy`; octet-stream JSON body |
| Project export | `GET /data/api/v1/projects/export/{name}` | project name |
| Project import | `POST /data/api/v1/projects/import/{name}` | `overwrite=true`; ZIP body |
| Config scan lock | `POST /data/api/v1/scan-lock/config` | JSON `acquireTimeout`, `holdTimeout` |
| Config scan | `POST /data/api/v1/scan/config` | releases config scan lock and requests one scan |
| Config scan status | `GET /data/api/v1/scan/config` | bounded polling of `scanActive` |
| Logs | `GET /data/api/v1/logs` | bounded time, logger, level, search, limit |

Do not assume the configured authentication header name; take it from the live security scheme or the operator's approved configuration. Never put the token in a URL.

The JSON tag-import document must contain one root object. To import several siblings in one request, wrap them in a `Folder` object's `tags` array. The verified route rejected document-root arrays, including a one-element array, while still returning HTTP 200.

The generic resource API on the verified target exposed tag-provider configuration but did not register tag content resources for `tag-definition` or `tag-type-definition`. Do not invent generic resource POSTs for UDT content.

## Tag import result

Parse both transport and semantic outcome. A verified response shape is:

```json
{
  "successCount": 0,
  "failureCount": 1,
  "failures": [
    {
      "level": "...",
      "userCode": 0,
      "diagnosticMessage": "..."
    }
  ]
}
```

Treat nonzero failure count, a nonempty failure array, unexpected counts, or a missing body as failure or unknown mutation even when HTTP status is 200.

`successCount` is structural. For a Folder payload it counted the Folder plus imported descendants on the verified build; calculate the expected count from the submitted tree.

## Guarded `llmImport` tag actions

Use these only when they appear in the target's `llmImport` health response. The caller must provide one to eight non-provider-root `allowedTagPathPrefixes`. Prefixes prevent accidental spillover but do not grant or enforce user authorization.

Prefer the operator's established consolidated `llmImport` project for all advertised actions. Do not create a new project merely to isolate a test. Use an existing isolated project only when the required action is absent from the consolidated health response and the isolated route is already approved, or when integration would put unrelated project resources at material risk. If neither exists, prove the missing capability and test a minimal isolated project before proposing consolidation.

### `tag-read-v1`

```json
{
  "action": "tag-read-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "paths": ["[Provider]Approved Root/Pump-001/PV"]
}
```

Maximum 64 paths. Require `accepted`, `ok`, exact `count`, and per-item `quality`, `isGood`, `valueType`, `timestampMillis`, and `valueTruncated`.

### `tag-read-complex-v1`

Use this read-only action only when the health response advertises it and exact array elements, document fields, or dataset cells are required:

```json
{
  "action": "tag-read-complex-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "paths": ["[Provider]Approved Root/Asset/Table"],
  "maxRows": 20,
  "maxColumns": 20,
  "maxElements": 64,
  "maxDocumentBytes": 16384
}
```

Maximums are 32 paths, 100 rows, 64 columns, 256 array/document elements per container, and 65,536 UTF-8 document bytes. The action performs no writes and rejects unknown fields, provider-root prefixes, prefix escape, invalid paths, and out-of-range caps. Require `accepted`, `ok`, exact `count`, per-item exact `quality`/`isGood`/`timestampMillis`, `truncated: false`, and the expected representation:

- `kind: "array"`: `elementCount` plus structured `value` elements; dates are `{"dateTimeMillis": ...}`.
- `kind: "document"`: `documentBytes` plus structured `value`.
- `kind: "dataset"`: `rowCount`, `columnCount`, typed `columns`, and `rows`.
- `kind: "scalar"`: scalar `value`, including null.

`truncated: true` is a bounded partial read, not full-value proof. Caller prefixes prevent accidental spillover but are not authorization. See `complex-values.md` for import and override shapes.

The verified consolidated `llm-tools` 0.60.0 advertises this action directly; no separate test project is required. Its consolidation passed 25 offline guardrails, Jython parsing and compilation, live exact Dataset and truncation reads, negative scope/cap checks, regressions for existing tag/alarm actions, post-export comparison, and a bounded zero-ERROR deployment interval.

When extending a large WebDev handler, force a clean embedded-Jython compile before deployment. A previously cached 94 KB handler continued serving until a small edit forced recompilation and exposed the JVM method-size limit. Move a complete action into a Gateway-scoped Project Library module, compile the refactored handler, and regression-test the extracted action. Do not assume that a currently running cached handler can be re-imported successfully.

### `tag-browse-v1`

```json
{
  "action": "tag-browse-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "basePath": "[Provider]Approved Root",
  "recursive": true,
  "tagType": "UdtInstance",
  "typeId": "Equipment/Pump",
  "maxResults": 100
}
```

Maximum 500 returned rows. Treat `complete: false`, `truncated: true`, or a continuation marker as incomplete discovery. Query each concrete `typeId` separately and deduplicate normalized full paths.

### `tag-write-v1`

Dry-run request:

```json
{
  "action": "tag-write-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "writes": [
    {"path": "[Provider]Approved Root/Pump-001/Command", "value": true}
  ]
}
```

Applied request:

```json
{
  "action": "tag-write-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "dryRun": false,
  "apply": true,
  "writes": [
    {"path": "[Provider]Approved Root/Pump-001/Command", "value": true}
  ]
}
```

Maximum 32 scalar writes. The action validates the supplied Gateway API token against an official API route, rejects unknown fields and out-of-prefix paths, reads before, writes once, reads after, and reports per-item write/read qualities and `verified`. It does not make caller prefixes an authorization boundary.

Do not treat a batch as atomic. On the verified build, one valid path in a two-item batch wrote `Good` and executed its UDT event script while a nonexistent in-prefix sibling path returned `Bad_NotFound`; the response correctly reported `ok: false`, `allVerified: false`, and distinct per-item results. Read every intended target and its observable effect before recovery, then retry only the missing operation. A same-value retry can return `verified: true` without firing `valueChanged`, so transport readback is not execution evidence. Use a monotonically increasing application sequence plus `LastAppliedSequence`, result/counter tags, and exact logs when a command must be idempotent.

Items from one `writeBlocking` batch also do not impose callback order across independent tags. Two sibling Folder scripts logged in either A/B order at the same timestamp. Verify an exact marker set and per-branch completion barriers; do not infer cross-branch causality from request-array order. Require `allVerified: true` for transport success, but inventory before any retry whenever it is false or the response is missing.

### `alarm-query-status-v1`

```json
{
  "action": "alarm-query-status-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "states": ["ActiveUnacked", "ActiveAcked"],
  "priorities": ["High", "Critical"],
  "propertyNames": ["ContextGeneration", "ContextToken"],
  "maxResults": 100
}
```

The action converts qualified tag prefixes into provider/source filters and queries only current alarm status. It rejects provider-root, wildcard, traversal, unknown-field, state, and priority escapes. Maximum 200 returned rows. Optional `propertyNames` accepts at most 16 exact identifier names. Each matching item then has a separate read-only `data` object; requested but absent values are explicit null. The response echoes the accepted list in `filters.propertyNames`. Require `complete: true` before claiming a full population.

On the verified build, the returned dataset represented `State` and `Priority` numerically (`0..3` and `0..4`) even though scripting documentation also describes string names. Preserve raw values and normalize explicitly:

```text
State: 0 ClearUnacked, 1 ClearAcked, 2 ActiveUnacked, 3 ActiveAcked
Priority: 0 Diagnostic, 1 Low, 2 Medium, 3 High, 4 Critical
```

Status associated data preserves serialized value types. On the verified 8.3.8 build, a direct Int4 binding was a JSON integer and a `concat(..., toStr(...))` binding was a JSON string. Three UDT runs proved that one event UUID retained the same explicitly latched generation/token in ActiveUnacked, ActiveAcked, ClearUnacked, and ClearAcked status, including after a denied re-arm. Correlate that UUID and data with bounded Alarm Journal rows when historical proof is required.

Status rows prove current event state only. By themselves they do not prove alarm history, notification delivery, or acknowledgement behavior.

### `alarm-query-shelved-v1`

```json
{
  "action": "alarm-query-shelved-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "maxResults": 100
}
```

This read-only action filters `system.alarm.getShelvedPaths()` to the caller's qualified prefixes. Maximum 200 rows. Require `complete: true`; inspect exact `path`, expiration, user, and expired state.

### `alarm-query-journal-v1`

Use this read-only `llm-tools` action when the official OpenAPI exposes Alarm Journal configuration but no bounded event-query route:

```json
{
  "action": "alarm-query-journal-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "journalName": "Sample_Alarm_Journal_Profile",
  "startTimeMillis": 1784585906748,
  "endTimeMillis": 1784585930545,
  "eventIds": ["11111111-1111-4111-8111-111111111111"],
  "propertyNames": ["AreaCode", "AssetCode", "WorkOrder"],
  "maxResults": 50
}
```

The caller must provide 1-16 strict event UUIDs, 1-8 qualified non-root prefixes, a valid journal name, and an epoch-millisecond interval no longer than one hour. Optional `propertyNames` accepts at most 16 exact identifier names; each returned item then has a separate `data` object mapping those names to their serialized values or null. Results are post-filtered again by exact UUID and prefix, capped at 200, sorted by event time/state/UUID, and always report `writesAttempted: false`. Require `ok: true`, `complete: true`, and `truncated: false`.

Each journal item includes `eventId`, `source`, `state`, `eventTimeMillis`, `priority`, `acked`, `cleared`, `ackUser`, `ackNotes`, and `configuredNotes`. On the verified 8.3.8 journal, one manually acknowledged alarm occurrence produced separate `Active`, `Ack`, and `Clear` rows. `ackUser` and the per-call `ackNotes` appeared only on the `Ack` row. For a clear-before-ack occurrence, the order was `Active`, `Clear`, `Ack`. The reconstructed journal event returned null `configuredNotes`; do not use that field to infer the UDT alarm's configured Notes. Correlate by exact event UUID and source, and retry briefly for store-and-forward journal latency.

Dynamic associated data was transition-specific on the verified build: after three bound sibling values changed while an event remained active, its Active row retained the original values but later Ack and Clear rows returned the changed values under the same UUID. Treat each row's `data` object as evidence for that transition, not as proof of one immutable activation snapshot.

Do not coerce values in `data` merely because associated-data documentation describes strings. On live 8.3.8, a direct Int4 Expression binding returned JSON integers `1` and `2`, while `concat(..., toStr(...))` returned a JSON string. Preserve and validate the returned JSON type; request an explicit string-producing expression in the UDT when a downstream schema requires strings.

### `alarm-acknowledge-v1`

Dry-run first:

```json
{
  "action": "alarm-acknowledge-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "eventIds": ["11111111-1111-4111-8111-111111111111"],
  "notes": "Verified response",
  "username": "agent.test"
}
```

Apply only after inspecting the dry-run event source and state:

```json
{
  "action": "alarm-acknowledge-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "eventIds": ["11111111-1111-4111-8111-111111111111"],
  "notes": "Verified response",
  "username": "agent.test",
  "dryRun": false,
  "apply": true
}
```

The action accepts at most 16 strict UUIDs, resolves every event through an exact in-scope status query before writing, caps notes at 512 characters and usernames at 64, invokes native acknowledgement once, and reads every event back. It validates note shape, not the target alarm's `ackNotesReqd` configuration; when notes are required, always supply a non-empty note in both dry-run and apply. Require `allAcknowledged: true`, empty `failedEventIds`, and the expected acknowledged state. Acknowledgement is an event mutation and cannot be undone.

### `alarm-shelve-v1` and `alarm-unshelve-v1`

Dry-run/apply uses exact alarm source paths, not qualified tag paths:

```json
{
  "action": "alarm-shelve-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "sources": ["prov:Provider:/tag:Approved Root/Pump-001/PV:/alm:High"],
  "timeoutSeconds": 300,
  "dryRun": false,
  "apply": true
}
```

```json
{
  "action": "alarm-unshelve-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root"],
  "sources": ["prov:Provider:/tag:Approved Root/Pump-001/PV:/alm:High"],
  "dryRun": false,
  "apply": true
}
```

Both actions default to dry-run, require a verified API token and explicit apply, accept at most 16 exact sources, reject wildcards/traversal/backslashes, and perform shelved-path readback. Shelve timeouts must be integer seconds from 1 through 3600. Require `allVerified: true`; `accepted: true` with a failed source means the native operation did not take effect, including when alarm configuration disallows shelving. Prove hidden/visible status behavior by comparing exact-source results with `includeShelved` false/true; do not require an `IsShelved` column that the status dataset may not expose. Unshelve in cleanup even after a failed test.

## Guarded exact tag deletion

The verified official OpenAPI has tag import/export routes but no tag-content delete route. Use optional `tag-delete-v1` only when its isolated health response advertises that action and an exact delete is truly required, such as fully removing nested instance overrides before recreation.

Dry-run first:

```json
{
  "action": "tag-delete-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root/Test Family"],
  "paths": ["[Provider]Approved Root/Test Family/Asset"]
}
```

Apply only after matching the exact path and pre-state:

```json
{
  "action": "tag-delete-v1",
  "allowedTagPathPrefixes": ["[Provider]Approved Root/Test Family"],
  "paths": ["[Provider]Approved Root/Test Family/Asset"],
  "dryRun": false,
  "apply": true
}
```

The action verifies the native API token, accepts at most eight exact qualified paths and eight prefixes, requires each target to be a strict child of an allowed prefix with at least four relative path segments, rejects `_types_` definitions, traversal, backslashes, control characters, duplicates, overlaps, and unknown fields, and checks existence before and after deletion. It defaults to dry-run and requires the exact `dryRun: false` plus `apply: true` pair for mutation. Require successful deletion quality codes and `allDeleted: true`, then recreate through official tag import and verify runtime state. Caller prefixes are scope guards, not authorization.

## Guarded grouped UDT file action

Use `grouped-udt-file-v1` only when its health response advertises the action and the official tag import/export routes cannot perform the required grouped-file conflict or recovery operation. Do not assume the WebDev project name; use the approved route whose health advertises the action.

The action supports only `inspect`, `create`, and `replace` beneath the Gateway's `tag-type-definition/<provider>` resource root. It has no delete operation. Mutations require a verified native API token, default to dry-run, require explicit `apply: true`, validate provider and path segments, require one to eight `allowedGroupPathPrefixes`, cap the file at 524,288 bytes and 128 UDT definitions, reject unknown fields, and use a same-directory atomic move. `replace` requires the exact current `expectedSha256`; a mismatch returns `stale_sha256` with `writeAttempted: false`.

Inspection example:

```json
{
  "action": "grouped-udt-file-v1",
  "operation": "inspect",
  "provider": "Provider",
  "groupPath": "ApprovedTypes/GroupedResource",
  "allowedGroupPathPrefixes": ["ApprovedTypes/Grouped"]
}
```

Replacement dry-run example:

```json
{
  "action": "grouped-udt-file-v1",
  "operation": "replace",
  "provider": "Provider",
  "groupPath": "ApprovedTypes/GroupedResource",
  "allowedGroupPathPrefixes": ["ApprovedTypes/Grouped"],
  "expectedSha256": "64_UPPERCASE_HEX_CHARACTERS",
  "content": [{"name": "TypeA", "tagType": "UdtType", "tags": []}]
}
```

Apply only while the caller holds the official configuration scan lock. After one successful write, call `POST /data/api/v1/scan/config` once to release the lock and request a scan, poll scan status to idle, then verify through official tag export/runtime reads. The action deliberately does not acquire or release the official lock itself; this keeps lock ownership and scan evidence visible to the orchestrating agent.

Read `grouped-resource-recovery.md` before using this action. Caller prefixes are scope guards, not authorization. Route authentication, network restrictions, TLS, project security, and least-privilege API-token configuration remain separate requirements.

## Unknown-mutation rule

If a mutating request times out, returns malformed JSON, omits expected item counts, or loses connection after submission:

1. Mark the operation `unknown-mutated`.
2. Export and browse the exact target and its grouped siblings.
3. Compare against the pre-state snapshot.
4. Produce a dry-run recovery plan.
5. Apply recovery only with explicit authorization.
## Read and write UDT instance parameters

Use the canonical tag path `[provider]instance/Parameters/ParameterName`. Recursive tag browse may omit this virtual parameter path even when `tag-read-v1` returns a Good value. Run `tag-write-v1` with `dryRun: true` first; require `writesAttempted: false` and `externalSideEffects: none`. Then apply, verify the readback value, compare an untouched Control instance, and restore the original value before closing the bounded log interval.

Do not compare parameter-path QualifiedValue timestamps to prove dry-run inactivity. Consecutive reads can advance the timestamp while the value stays unchanged and the API reports zero writes. Use response metadata plus unchanged value. Timestamp equality remains useful only on tag classes already proven to retain it, such as the tested memory DataSet when an event script omitted that tag from `writeBlocking`.
