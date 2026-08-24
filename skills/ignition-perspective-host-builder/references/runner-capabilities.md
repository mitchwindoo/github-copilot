# Runner Capabilities

Use this reference before selecting or calling an approved Ignition host-runner action.

## Contents

- Connection contract
- Capability discovery
- Current capability groups
- Required safety features
- Compatibility decisions

## Connection Contract

Use the approved connection profile whenever one is configured. The Web Dev transport commonly uses:

```text
POST <gatewayUrl>/system/webdev/<projectName>/<webDevResource>
Content-Type: application/json
X-LLM-Runner-Token: <token>
```

Keep the token and private connection values in runtime input or the approved profile. Include a stable caller-generated `requestId` and require it to be echoed in success, validation-error, authentication-error, and write responses.

## Capability Discovery

Treat live `health.supportedActions` and `health.features` as authoritative. The current tested contract is `0.3.148`, but version text alone does not prove that a deployed runner exposes every action.

Before each workflow:

1. Require `health.ok: true`.
2. Confirm the exact callable actions needed.
3. Confirm the safety features needed for the intended mutation or diagnostic.
4. Stop or choose a narrower documented workflow if a capability is unavailable.
5. Never infer an action from a similarly named feature flag. For example, the callable branding action is `perspectiveBrandingRead`; `perspectiveBrandingMetadataRead` is a feature name, not a callable action.

## Current Capability Groups

### Package and project resources

- `dryRun` and `apply`: validate and apply allowlisted packages, dependencies, routes, shared docks, and overwrites.
- `routesList`, `viewsList`, `viewRead`, and `pageValidate`: discover and verify live project structure.
- `projectResourcesList`, `projectResourceRead`, and supported import actions when advertised: inspect or manage bounded project resources.
- `backupList` and `rollback`: inspect and restore runner-created backups.

### Project discovery

- `gatewayInfo`: Gateway, Ignition/module, project, environment, and runner diagnostics.
- `styleResourcesList`: style classes, themes, project images, and reusable view metadata.
- `seedViewsList`, `seedViewRead`, and `componentSeedRead`: Designer-created component seed discovery.
- `namedQueriesList`, `namedQueryRead`, and `namedQueryPreview`: allowlisted Named Query discovery and bounded read-only previews.

### Tags, history, alarms, audit, and logs

- `tagProviders`, `tagBrowse`, and `tagRead`: read-only tag discovery and current-value readback.
- `historyProbe`: bounded historian availability and good-sample evidence.
- `alarmStatusQuery` and `alarmJournalQuery`: bounded current and historical alarm diagnostics.
- `auditQuery`: bounded change-attribution diagnostics with explicit profile and narrow filters.
- `logQuery`: recent filtered Gateway/Perspective log diagnostics.
- `tagConfigure`, `udtScaffold`, and `udtTagEventScriptProbe`: guarded fixture/scaffold workflows only when explicitly supported and required.

### Live Perspective runtime

- `perspectiveSessionsQuery`: discover live sessions using tokens by default.
- `perspectiveSessionPagesList`: list pages for one selected session token.
- `perspectivePageViewsList`: inspect live view instances using strict session/page matching.
- `perspectiveSessionTerminate`: guarded session close. Dry-run first; apply requires the expected token and `confirmTerminateSession: "TERMINATE_PERSPECTIVE_SESSION"`. `closeSessionCalled` proves only the attempt; require `terminated: true` or successful termination verification.

### Gateway-level Perspective assets

- Theme list/read/upsert actions
- Font list/read/upsert actions
- Icon-library list/read/upsert actions
- `perspectiveBrandingRead`

List or read before every upsert. Upserts default to dry-run, reject built-in names where applicable, require exact confirmation strings, create `_gateway` backups, and skip project scans. Verify through the matching list/read action and expect client, Gateway, or Designer refresh to be necessary.

## Required Safety Features

For ordinary package apply, require the live equivalents of:

- exact-or-child prefix boundary matching
- mutation locking
- atomic project-resource file writes
- project-resource attribute preservation
- scan failure reported as failure
- package work-directory cleanup
- unique generated work/backup identifiers
- overwrite hash checks
- final merged resource-manifest validation
- stale managed view-file pruning when intentional
- non-view final-state validation when scripts, Named Queries, or page config are included
- unfinished backup recovery metadata and structured rollback failure envelopes

Use feature names from live health rather than assuming they exist from this summary. When a required feature is absent, do not emulate it with direct filesystem writes.

For backend diagnostics, require bounded-work features before alarm, audit, or Named Query queries. Narrow source/path/display-path, actor/action/target/value/system, time-window, and row-limit inputs before execution.

## Compatibility Decisions

- Prefer the current tested runner contract, `0.3.148`.
- Keep only actionable minimums in customer work. The exhaustive `0.3.x` development matrix is internal evidence, not runtime instruction.
- Parse structured JSON bodies on non-2xx responses; status alone may omit recovery context.
- Treat `MUTATION_LOCK_BUSY` as retryable only after rediscovery and a fresh dry-run.
- Treat `PROJECT_SCAN_FAILED`, `ROLLBACK_WRITE_FAILED`, `MID_WRITE_FAILURE`, unknown-mutation recovery, and any `recoveryRequired: true` as stop-and-preserve-evidence conditions.
- Do not claim support for an action or feature combination that live health does not advertise and the workflow has not tested.

