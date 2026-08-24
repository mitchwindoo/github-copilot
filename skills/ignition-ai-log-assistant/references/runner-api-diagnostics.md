# Runner API Diagnostics

Use this reference when the approved Web Dev runner is part of the diagnostic path.

## Transport And Authentication

Use an installed connection profile or `ignition-perspective-host-builder` when available. If neither is available, obtain the exact Gateway URL, Web Dev project name, Web Dev resource name, and runner token from the user or the customer's approved runtime configuration. Never guess them.

The common Web Dev transport is:

```text
POST <gatewayUrl>/system/webdev/<projectName>/<webDevResource>
X-LLM-Runner-Token: <token>
Content-Type: application/json
```

Send the runner action object as the JSON request body and include a caller-generated `requestId`. Require a JSON response, verify that the response corresponds to the requested action and echoes the expected `requestId` when supported, and preserve HTTP status and error bodies for diagnosis. Keep tokens and private endpoints in runtime input or an approved connection profile; never write them into the skill, diagnostic report, or reusable evidence. If the configured transport differs, follow the customer's deployed Web Dev contract rather than changing or probing routes.

## Health And Gateway Snapshot

- Call `health` first and inspect `runnerVersion`, `stackVersion`, `supportedActions`, `features`, `mutationLockedActions`, and `tokenConfigured`.
- Include a caller-generated `requestId` in every call.
- Call `gatewayInfo` to capture Ignition version/build, system properties, current time/timezone, target project existence, module IDs/names/states/license statuses, module versions, and runner action/feature advertising.
- Runner `0.3.55+` enriches modules from the documented Gateway-scope `system.util.getModules` dataset when `health.features` includes `gatewayInfoModuleVersions`.

## Log Query Rules

- Use `logQuery` only with a time window, cap, and at least one narrow `loggerContains`, `messageContains`, or `textContains` filter unless a deliberate broad diagnostic uses explicit confirmation.
- Prefer numeric `sinceMinutes` values or a captured `sinceEpochMillis`. After the call, verify the returned `sinceEpochMillis` and current-time fields so the saved evidence proves the actual queried window.
- Treat current-only `logQuery` as wrapper-log evidence from the runner, not as a complete replacement for exported Gateway Diagnostic Logs.
- On runner `0.3.61+`, set `includeRotated: true` with `maxLogFiles` only when rotated wrapper context is needed. Keep the same time/level/logger/message filters or explicit broad-query confirmation, respect the total-tail-byte cap, and preserve `sourceFiles`/`sourceFileName`.
- On runner `0.3.56+`, set `includeNonPrimary: true` when diagnosing bare `print` or other timestamped wrapper lines that do not have an Ignition logger prefix.
- When saving `logQuery` evidence, preserve `source`, `sourcePath` when requested, `sourceLength`, `sourceLastModifiedEpochMillis`, `sourceFiles`, `sourceFileName`, `tailBytes`, `maxTotalTailBytes`, `tailWindowTruncated`, `lineScanCount`, `matchedCountBeforeCap`, filters used, `includeRotated`, `maxLogFiles`, `includeNonPrimary`, and whether the result was capped/truncated.
- If a query returns capped results or `tailWindowTruncated: true`, narrow again before reading the sample as representative: reduce the time window, add a logger suffix, add distinctive message text, or exclude known follow-on noise while preserving the source label.
- A zero-entry result with `sourceAvailable` and `sourceFiles` means no match inside the selected source, time window, filters, and tail window. It does not prove the event is absent from rotated files, older wrapper history, Gateway Diagnostic Logs, browser/client logs, audit rows, or alarm journal rows.

## Tag Event Probe

- On runner `0.3.57+`, use `tagEventScriptProbe` only with a fixed, preapproved tag-event fixture.
- Set `emitSuccessMarkers: true` plus a unique `successMarker`.
- On runner `0.3.94+`, inspect `tagEventProbeSynchronousWaitCap`, `requestedPollAttempts`, effective `pollAttempts`, `pollAttemptsCapped`, and `probeSyncWaitMaxMs` before applying a live probe; do not estimate call duration from the raw requested attempts.
- On runner `0.3.95+`, inspect `tagEventProbeFailureCleanup` and `failureCleanupPaths` before applying a live probe. If a probe apply fails after fixture creation starts, preserve `failureCleanup` as best-effort cleanup evidence for the fresh planned probe paths while keeping the original failure as the primary diagnostic.
- On runner `0.3.139+`, inspect `tagProbeCleanupRecoveryFields` and use top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired` to decide whether cleanup follow-up is needed; keep nested `failureCleanup` for per-path details.
- On runner `0.3.140+`, inspect `projectResourceImportZipFinalManifestValidation` when diagnosing import failures; `RESOURCE_MANIFEST_INVALID` with `manifestValidationPhase:"finalMergedResourceState"` means the final overlaid `resource.json.files` state would be invalid before any write.
- On runner `0.3.141+`, inspect `rollbackWriteFailureEnvelope` when diagnosing rollback failures; `ROLLBACK_WRITE_FAILED` preserves backup identity, backup format, pre-rollback backup state, failed stage/path, completed work lists, nested `rollbackFailure`, and `recoveryRequired`.
- On runner `0.3.144+`, inspect `unfinishedFileChangeBackupRollbackRecovery` when diagnosing rollback after failed mid-write file changes. Preserve `afterStateKnown`, `backupManifestComplete`, `rollbackDriftCheckMode`, and `driftCheckSkipped`; unfinished backups can skip strict drift checks, but completed backups still use `ROLLBACK_DRIFT_DETECTED`.
- Primary-only `logQuery` captures the `system.util.getLogger` marker.
- `includeNonPrimary: true` is required to capture the bare `print` marker.

## Audit Query

- On runner `0.3.82+`, use `auditQuery` for bounded audit/change-attribution context with explicit audit profile names.
- Provide `profile`, `auditProfileName`, or `profiles`; do not omit the audit profile in WebDev/Gateway scope.
- Do not send `useDefaultProfile` or `useConfiguredAuditProfile`; runner `0.3.82+` rejects those client-scope shortcuts before calling Ignition.
- Always include a bounded time window, caps, and a narrow actor/action/target/value/system filter. On runner `0.3.96+`, the maximum window is `1440` minutes and `contextFilter` alone does not bound backend work.
- Runner `0.3.96+` rejects broad audit scans before execution; do not use `allowBroad` / `confirmBroadAuditQuery` as a bypass.
- `contextFilter` must be an integer bitmask, not a string wildcard.
- Poll briefly after writing a controlled audit marker because audit readback can lag.

## Alarm Journal Query

- On runner `0.3.60+`, use `alarmJournalQuery` for bounded historical alarm context.
- On runner `0.3.97+`, provide explicit `journalName`, `journal`, or `alarmJournal`; the runner rejects default/omitted journal flags because it cannot verify Ignition's exactly-one-journal omission condition.
- Always include a bounded time window, caps, and at least one narrow source/path/displayPath filter. On runner `0.3.96+`, provider/state/priority/isSystem filters are supplemental, the maximum window is `1440` minutes, and broad confirmation bypasses are removed.
- Keep Alarm Journal rows separate from diagnostic logs, current `alarmStatusQuery` rows, and audit rows.
- Do not guess audit or journal profile names after a clear profile-related failure; discover or ask for the exact target profile instead.

## Script Output Routing

- Prefer `system.util.getLogger` as the server-side breadcrumb.
- In Web Dev/Gateway scope, capture bare `print` or other non-primary wrapper output with `logQuery includeNonPrimary: true`.
- In the fixed tag-event fixture, `tagEventScriptProbe emitSuccessMarkers` can produce both a primary `system.util.getLogger` marker and a non-primary bare `print` marker. On runner `0.3.94+`, the probe response also reports capped synchronous wait metadata for evidence timing. On runner `0.3.95+`, failed post-create probe applies may also report `failureCleanup`; on runner `0.3.139+`, those failures also expose top-level cleanup recovery fields.
- In a live Perspective session, use `system.perspective.print(destination="client")` for browser-console evidence, `destination="gateway"` for wrapper evidence, and `destination="all"` only when both are needed.
- Do not use `system.perspective.print` for Gateway/Web Dev diagnostics unless an attached Perspective session/page is confirmed.

Use `scriptEval` only for bounded diagnostics with explicit confirmation. A dry-run compile is not execution confirmation. Do not use `scriptEval` as the general write or repair path.

## Runner Maintenance Boundary

- If a needed action is absent from `health.supportedActions`, or a needed capability flag is absent from `health.features`, do not invent the action or assume another runner has it.
- Runner updates are a separate maintenance workflow: coordinate the live test, use dry-run/self-update safeguards when available, then rerun `health`, `gatewayInfo`, representative read-only calls, expected validation-rejection probes, and the new capability before relying on it.
- For runner `0.3.141+` rollback diagnostics, preserve the full `ROLLBACK_WRITE_FAILED` body before summarizing logs; the response itself is the primary recovery evidence and log rows are only supporting context.
- For runner `0.3.144+` unfinished file-change rollback diagnostics, preserve the full rollback body before summarizing logs; `driftCheckSkipped:true` is intentional only when `afterStateKnown:false` and `rollbackDriftCheckMode:"unknown-after-state"`.
