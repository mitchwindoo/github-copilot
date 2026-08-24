# Ignition Web Dev Runner API Reference

Stack version: `starter-2026.07.14.01`
Runner API version: `0.3.200`
Ignition target: `8.1`
Updated: `2026-07-14`

This is the action-level reference for the Ignition Web Dev runner used by the AI skill stack. Use `00_START_HERE_API_SETUP.md` for the first install and health check, then use `WEBDEV_RUNNER_SETUP.md` for advanced deployment details. Use this file when writing requests, testing features, or reviewing runner behavior.

## Endpoint

```text
POST <gatewayUrl>/system/webdev/<automationProject>/<webDevFolder>/<webDevResource>
```

The common local test endpoint has been:

```text
POST http://localhost:8088/system/webdev/samplequickstart/llmImport
```

Call `health` first on every session and inspect `runnerVersion`, `stackVersion`, `supportedActions`, `features`, and `tokenConfigured`.

## Authentication

Send one of these with every request:

```text
X-LLM-Runner-Token: <token>
Authorization: Bearer <token>
```

Body token fallback is supported for development, but headers are preferred. In `0.3.50+`, `IGNITION_LLM_RUNNER_TOKEN` takes precedence over in-file fallback token constants, and token comparison uses constant-time comparison when the Java runtime path is available.

## Common Request Envelope

```json
{
  "action": "health",
  "requestId": "RUN-001"
}
```

Rules:

- Include `requestId` in every call.
- Use discovery/read actions before write actions.
- Use dry-run before every write.
- Send the exact confirmation string only for the real write.
- Keep request JSON UTF-8 without BOM.
- If the Gateway returns HTTP 402, check and reset Ignition Trial Mode before debugging code.

## Common Response Shape

Successful responses include:

```json
{
  "ok": true,
  "requestId": "RUN-001",
  "runnerVersion": "0.3.200",
  "stackVersion": "starter-2026.07.14.01"
}
```

Validation failures return JSON, normally with HTTP 400:

```json
{
  "ok": false,
  "requestId": "RUN-001",
  "error": "sinceMinutes must be between 1 and 1440"
}
```

Unauthorized calls return `ok: false` with `Unauthorized`.

Primary backend/query failures in read-query actions return a non-successful top-level envelope, normally with HTTP 500, while preserving action-specific diagnostics:

```json
{
  "ok": false,
  "requestId": "RUN-001",
  "runnerVersion": "0.3.200",
  "stackVersion": "starter-2026.07.14.01",
  "action": "historyProbe",
  "statusCode": 500,
  "errorCode": "HISTORY_QUERY_FAILED",
  "error": "historyProbe value query failed: <details>",
  "queryOk": false,
  "queryError": "<details>"
}
```

For `historyProbe`, `alarmStatusQuery`, `alarmJournalQuery`, and `auditQuery`, treat `ok: false` as the action failure signal and use fields such as `queryOk`, `sampleCountQueryOk`, `queryError`, `sampleCountQueryError`, `errorType`, and `attempts[]` for root-cause details.

When another writeful runner mutation is already active, mutation actions return a retryable busy response, normally with HTTP 409:

```json
{
  "ok": false,
  "requestId": "RUN-001",
  "runnerVersion": "0.3.200",
  "stackVersion": "starter-2026.07.14.01",
  "action": "tagConfigure",
  "statusCode": 409,
  "errorCode": "MUTATION_LOCK_BUSY",
  "mutationLockBusy": true,
  "busy": true,
  "retryable": true,
  "retryAfterMs": 1000,
  "lockName": "gatewayMutationLock",
  "error": "Runner mutation is busy; try again after the current mutation finishes."
}
```

## Current Features

Runner `0.3.200` supports these actions:

```text
health
gatewayInfo
gatewayNetworkPreflight
databaseConnectionsList
metricsList
metricsSnapshot
gatewayPerformanceSnapshot
perspectiveSessionsQuery
perspectiveSessionPagesList
perspectivePageViewsList
perspectiveSessionTerminate
perspectiveThemesList
perspectiveThemeRead
perspectiveThemeUpsert
perspectiveFontsList
perspectiveFontRead
perspectiveFontUpsert
perspectiveIconLibrariesList
perspectiveIconLibraryRead
perspectiveIconLibraryUpsert
perspectiveBrandingRead
threadDumpQuery
tagProviders
tagBrowse
tagRead
tagConfigure
tagEventScriptProbe
udtTagEventScriptProbe
udtScaffold
historyProbe
alarmStatusQuery
alarmJournalQuery
auditQuery
logQuery
projectsList
projectInfoRead
routesList
viewsList
viewRead
pageValidate
styleResourcesList
seedViewsList
seedViewRead
componentSeedRead
namedQueriesList
namedQueryRead
namedQueryPreview
projectResourcesList
projectResourceRead
visionWindowInspect
projectResourceExport
projectResourceImportZip
projectResourceDelete
scriptEval
backupList
rollback
runnerSelfUpdate
dryRun
apply
```

`health.supportedActions` is the authoritative action catalog; `health.features` is reserved for non-action capability flags.

`health.features` reports internal capability flags. Current 0.3.200 flags include request/body validation, supported action reporting, Gateway/module/metrics diagnostics, Perspective session tokens and live view discovery, Perspective session termination dry-run/verification, Perspective runtime project validation, theme/font/icon-library management, branding metadata readback, Perspective asset backup metadata, Vision window structural inspection, guarded project-resource delete dry-run/state checks/rollback backups, tag browse totals, reference/derived tag configuration, tag-event probe cleanup recovery, historian/alarm/audit/log query bounds, project target validation, import/apply manifest validation, mutation locking, rollback recovery metadata, runner self-update rollback, scan completion, Perspective view linting, Jython syntax/compile linting, expression linting, prop config linting, and shared dock handling. Read the exact `features` array from `health` instead of assuming a feature exists from docs alone.

`health` also reports grouped action lists. `mutationLockedActions` uses exact action names: `dryRun`, `apply`, `projectResourceImportZip`, `projectResourceDelete`, `rollback`, `runnerSelfUpdate`, `tagConfigure`, `tagEventScriptProbe`, `udtTagEventScriptProbe`, `udtScaffold`, `perspectiveSessionTerminate`, `perspectiveThemeUpsert`, `perspectiveFontUpsert`, and `perspectiveIconLibraryUpsert`. `mutationLockAppliesToConfirmedWritesOnly` lists actions where dry-runs do not acquire the lock: `projectResourceDelete`, `rollback`, `runnerSelfUpdate`, `tagConfigure`, `tagEventScriptProbe`, `udtTagEventScriptProbe`, `udtScaffold`, `perspectiveSessionTerminate`, `perspectiveThemeUpsert`, `perspectiveFontUpsert`, and `perspectiveIconLibraryUpsert`.

Runner `0.3.200` does not expose Project Gateway Event Script or Perspective Session Event Script resource actions. `tagEventScriptProbe` and `udtTagEventScriptProbe` are constrained tag-event fixtures, not general project Gateway/session handler APIs. Do not invent calls such as `sessionScriptsRead` or `gatewayEventScriptsRead`; unsupported actions return HTTP/status `400`, `ok:false`, `errorCode:"UNKNOWN_ACTION"`, and `error:"Unknown action: <action>"` unless a future `health.supportedActions` contract adds them.

## Runner 0.3.200 Vision Inspection And Resource Delete Notes

Runner `0.3.200` adds read-only `visionWindowInspect` plus guarded `projectResourceDelete`. The new feature flags are `visionWindowStructuralInspection`, `projectResourceDeleteDryRun`, `projectResourceDeleteStateGuard`, and `projectResourceDeleteRollbackBackup`.

`visionWindowInspect` is limited to one concrete resource below `com.inductiveautomation.vision/windows`. It returns a deterministic `resourceStateSha256`, bounded file metadata, manifest attributes, and serialization diagnostics. For gzip XML windows it reports window/root dimensions, component names/classes/text, preferred bounds, `fpmi.lc` layout constraints, layout coverage, and warnings such as `ROOT_WINDOW_SIZE_MISMATCH`, `CHILD_OUTSIDE_ROOT_BOUNDS`, or `WINDOW_PATH_MISMATCH`. For binary-v2 windows it reports only bounded format/version, known-token, component-class, and expected-text-marker evidence. Binary-v2 numeric layout still requires Designer or Vision-client verification. Every response sets `runtimeRenderVerified:false`; structural success never proves rendering or interaction.

`projectResourceDelete` defaults to dry-run and deletes exactly one manifest-backed resource directory. It rejects resource trees containing nested project resources. Apply requires both the current dry-run/inspection `resourceStateSha256` as `expectedResourceStateSha256` and `confirmProjectResourceDelete:"DELETE_PROJECT_RESOURCE"`. State drift returns HTTP/status `409` with `errorCode:"RESOURCE_STATE_DRIFT"` before writes. Confirmed delete snapshots every file into a `fileChanges-v1` backup, verifies directory absence, performs bounded project-scan waits, refreshes the backup manifest after scan, and can be restored through normal `rollback`. The deletion is guarded and recoverable, but is not a multi-file atomic transaction.

## Runner 0.3.148 Perspective Runtime And Asset Notes

Runner `0.3.148` exposes Perspective runtime/session actions plus Gateway-level Perspective asset management. Use `health.supportedActions` as the source of truth. The callable branding action is `perspectiveBrandingRead`; `perspectiveBrandingMetadataRead` is a feature flag, not an action.

Runtime actions:

- `perspectiveSessionsQuery`: tokenized live-session discovery; raw identifiers require `includeIdentifiers:true`.
- `perspectiveSessionPagesList`: list page tokens for a selected live session.
- `perspectivePageViewsList`: list live view instances for a selected session/page through internal Perspective Gateway session APIs. It requires strict session and page matching and never falls back to static routes or page-only matching.
- `perspectiveSessionTerminate`: defaults to dry-run. Apply requires `expectedSessionToken` plus `confirmTerminateSession:"TERMINATE_PERSPECTIVE_SESSION"`. `closeSessionCalled:true` means the Ignition close call was attempted; `terminated:true` now means a bounded follow-up session query no longer found the token. Inspect `terminationVerified`, `postCloseMatchedCount`, and `verificationAttempts`.

Asset read/write actions:

- Themes: `perspectiveThemesList`, `perspectiveThemeRead`, `perspectiveThemeUpsert`.
- Fonts: `perspectiveFontsList`, `perspectiveFontRead`, `perspectiveFontUpsert`.
- Icon libraries: `perspectiveIconLibrariesList`, `perspectiveIconLibraryRead`, `perspectiveIconLibraryUpsert`.
- Branding: `perspectiveBrandingRead`, metadata only; it never returns logo/favicon/app-icon bytes.

Asset writes are Gateway Perspective module file writes, not project resources. Upserts default to `dryRun:true`, reject built-in theme/icon names, require exact confirmations (`UPSERT_PERSPECTIVE_THEME`, `UPSERT_PERSPECTIVE_FONT`, `UPSERT_PERSPECTIVE_ICON_LIBRARY`), write `fileChanges-v1` backups with `targetProject:"_gateway"`, `targetRootKind:"perspectiveModule"`, and `scanMode:"none"`, and report `restartOrRefreshMayBeRequired:true`. Use `backupList` with `targetProject:"_gateway"` to discover those backups; entries report `type:"perspectiveModuleAsset"`, `assetAction`, `scanSkippedOnRollback:true`, and `restoreTargetProject:"_gateway"`. Roll asset backups back with `targetProject:"_gateway"` and normal rollback dry-run/apply confirmation.

## Runner 0.3.145 Apply Non-View Final-State Validation Notes

Runner `0.3.145` adds the `applyNonViewFinalStateValidation` feature flag. Confirmed package `apply` already validates package script, Named Query, and page-config manifests before writes; it now also validates destination Project Library script directories, Named Query directories, and the Perspective page-config directory after their mutation stages and before `finalizeFileChanges`, final backup manifest write, or project scan.

If a pre-existing target script, Named Query, or page-config directory contains an unsupported file/subdirectory, or a preserved page-config `resource.json.files` manifest would leave invalid final state, `apply` stops with `MID_WRITE_FAILURE`. The response includes `failedStage` plus `validationStage` (`validateCopiedScripts`, `validateCopiedNamedQueries`, or `validateMergedPageConfig`), `validationResourceType` (`projectLibraryScript`, `namedQuery`, or `perspectivePageConfig`), `validationFailure`, and `validationErrorCode:"RESOURCE_MANIFEST_INVALID"` when manifest validation produced the failure. Normal backup/write-failure recovery fields remain present.

This release intentionally does not prune unknown non-view files. Unlike view `thumbnail.png`, Project Library scripts, Named Queries, and page config have no runner-supported optional sibling files; unknown target files fail clearly before scan/success so operators can rollback or inspect.

## Runner 0.3.144 Unfinished File-Change Backup Rollback Recovery Notes

Runner `0.3.144` adds the `unfinishedFileChangeBackupRollbackRecovery` feature flag. Initial `fileChanges-v1` backup manifests written by confirmed `apply`, `projectResourceImportZip`, and `runnerSelfUpdate` before writes finish now record `afterStateKnown:false`, `backupManifestComplete:false`, and `rollbackDriftCheckMode:"unknown-after-state"`. Finalized/refreshed write backups and pre-rollback safety backups record `afterStateKnown:true`, `backupManifestComplete:true`, and `rollbackDriftCheckMode:"after-sha256"`.

Rollback of an unfinished backup whose after-state is unknown skips strict `afterSha256` drift blocking, reports `driftCheckSkipped:true` and `rollbackDriftCheckMode:"unknown-after-state"`, and no longer treats `afterSha256:null` as proof that a current file must be missing. This lets normal rollback recover from a failed mid-write mutation without requiring `forceDriftedRollback` solely because files exist after the failed write.

Completed backups still enforce the `0.3.118+` `ROLLBACK_DRIFT_DETECTED` guard. Legacy manifests that do not contain `afterStateKnown` default to strict `after-sha256` mode for compatibility, so old unfinished backups created before `0.3.144` may still require `forceDriftedRollback` or manual recovery after inspection.

## Runner 0.3.143 udtScaffold Unknown Failure Recovery Notes

Runner `0.3.143` adds the `udtScaffoldUnknownFailureRecovery` feature flag. When a confirmed non-dry-run `udtScaffold` nested `tagConfigure` step fails with missing, null, or empty `qualityCodes`, the runner treats the step as unknown-mutated and marks every step `recoveryPaths` entry as created or modified according to the preflight snapshot. The failure envelope then attempts the existing delete/restore recovery path instead of incorrectly reporting that no writes started.

This is intentionally conservative for the Ignition/Jython failure shape where `system.tag.configure` can throw after a partial write and the wrapper returns `ok:false` without per-tag QualityCodes. Dry-runs do not mark mutations or attempt recovery. The `0.3.138+` mismatched QualityCode behavior is preserved: mismatched non-empty `qualityCodes` mark all step recovery paths only when any returned QualityCode is Good, while equal-length failed steps keep index-based marking.

After any failed confirmed scaffold on `0.3.143+`, inspect `writesStarted`, `completedSteps`, `preflightExistingPaths`, `preflightNewPaths`, `recoveryAttempted`, `recoveryAllGood`, `recoveryRequired`, and nested `recovery` details such as `deletePaths` and `restorePaths`. A successful conservative recovery can return `recoveryAttempted:true`, `recoveryAllGood:true`, and `recoveryRequired:false`; if recovery is not all good, stop and manually reconcile the returned tag paths before issuing more writes.

## Runner 0.3.142 Apply Package Stale View File Pruning Notes

Runner `0.3.142` adds the `applyPackageStaleViewFilePruning` feature flag. Normal package `apply` now includes existing target Perspective view managed files in the file-change manifest before overwrite, so rollback can restore target files that the incoming package omits.

When overwriting a runner-managed Perspective view, if the target has an allowed stale-prunable optional managed file such as `thumbnail.png` and the package omits that file while the final `resource.json.files` list also omits it, confirmed `apply` deletes the stale target file instead of leaving disk inconsistent with `resource.json.files`. The apply response reports `prunedStaleViewFiles` and `prunedStaleViewFileCount`.

After copy/prune, `apply` validates destination view manifests. If copied view validation fails after writes begin, the mutation returns the existing `MID_WRITE_FAILURE` recovery envelope with failed stage `validateCopiedViews`.

Runner `0.3.145+` extends post-mutation final-state validation to Project Library scripts, Named Queries, and Perspective page config through `applyNonViewFinalStateValidation`; those non-view resources fail with validation metadata instead of pruning unknown files.

## Runner 0.3.141 Rollback Write-Failure Envelope Notes

Runner `0.3.141` adds the `rollbackWriteFailureEnvelope` feature flag. Rollback write/restore exceptions now return a controlled JSON failure instead of escaping as a generic top-level exception. This applies to `fileChanges-v1` rollback, legacy `projectResourceImportZip` rollback, and classic view/script/named-query rollback.

Failure responses use HTTP/status `500`, `ok:false`, and `errorCode:"ROLLBACK_WRITE_FAILED"`. They preserve the selected source backup as `backupName` / `backupDir` / `backupFormat`, the safety copy as `preRollbackBackupDir`, `preRollbackBackupCreated`, and recovery state such as `failedStage`, `failedPath`, `filesChanged`, `recoveryRequired:true`, `exceptionType`, `detail`, `completedRestoredFiles`, `completedRemovedFiles`, `completedPrunedDirs`, and nested `rollbackFailure`.

Stop further writes when this response appears. Inspect `rollbackFailure` and recover from the returned `preRollbackBackupDir`; the response deliberately reports `scanRequested:false` and `scanCompleted:false` because rollback failed before a trustworthy post-write scan.

## Runner 0.3.140 projectResourceImportZip Final Manifest Validation Notes

Runner `0.3.140` adds the `projectResourceImportZipFinalManifestValidation` feature flag. `projectResourceImportZip` now validates each touched managed resource against the final merged resource state before writes.

The runner overlays package entries onto the current target resource file set in memory, chooses the package `resource.json` when supplied and otherwise the existing target `resource.json`, then validates the final `resource.json.files` list against final managed files. Missing listed files and unlisted managed files are rejected before backup planning, file writes, or project scan.

Failures return HTTP/status `400`, `ok:false`, `errorCode:"RESOURCE_MANIFEST_INVALID"`, `manifestValidationPhase:"finalMergedResourceState"`, `filesChanged:false`, `scanRequested:false`, `scanCompleted:false`, and `recoveryRequired:false`.

## Runner 0.3.139 Tag Probe Cleanup Recovery Field Notes

Runner `0.3.139` adds the `tagProbeCleanupRecoveryFields` feature flag. Failed `tagEventScriptProbe` and `udtTagEventScriptProbe` responses still include the nested `failureCleanup` report, and now also promote cleanup recovery status to the top level:

```json
{
  "ok": false,
  "failureCleanup": {
    "attempted": true,
    "allGood": false
  },
  "recoveryAttempted": true,
  "recoveryAllGood": false,
  "recoveryRequired": true
}
```

When cleanup succeeds, `recoveryAllGood:true` and `recoveryRequired:false`. When there is nothing existing to clean up, `recoveryAttempted:false`, `recoveryAllGood:true`, and `recoveryRequired:false`. When cleanup delete QualityCodes are bad or cleanup raises, `recoveryAllGood:false` and `recoveryRequired:true`. Use `failureCleanup` for per-path details and the top-level recovery fields for caller control flow.

## Runner 0.3.138 udtScaffold Override Recovery Mismatch Notes

Runner `0.3.138` adds the `udtScaffoldOverrideRecoveryMismatch` feature flag. On failed `udtScaffold` member-override steps, Ignition may return one `QualityCode` per submitted member tag while the runner tracks one recovery path for the UDT instance root.

When a failed scaffold step has mismatched `recoveryPaths` and `qualityCodes` lengths, any Good returned `QualityCode` now marks every recovery path for that step as created or modified according to the preflight snapshot. Equal-length failed steps keep the existing index-based marking behavior. Successful steps still mark all recovery paths and append `completedSteps`.

## Runner 0.3.137 History Probe Good-Sample Terminology Notes

Runner `0.3.137` adds the `historyProbeGoodSampleTerminology` feature flag. The `historyProbe` sample-count availability query still uses `system.tag.queryTagHistory` with `aggregationMode: "Count"`, `includeBoundingValues: false`, `noInterpolation: true`, and `ignoreBadQuality: true`; the response now names that result as good-quality sample evidence.

Successful responses include top-level `goodSampleHistoryAvailable`, `goodStoredSampleCount`, `availabilityQualityMode: "goodOnly"`, `availabilityIgnoresBadQuality: true`, and `availabilityNoInterpolation: true`. Each `tagStats[]` item includes `goodSampleHistoryAvailable` and `goodStoredSampleCount`.

For compatibility, `historyAvailable`, `storedSampleCount`, and `tagStats[].sampleBackedHistoryAvailable` remain aliases of the good-sample fields. New clients should prefer the good-sample names. A false `goodSampleHistoryAvailable` or zero `goodStoredSampleCount` means no good-quality counted samples were returned by the availability query; it does not prove there are no bad-quality historical rows for the tag.

## Runner 0.3.136 Post-Write Project Scan Second Wait Notes

Runner `0.3.136` adds the `postWriteProjectScanSecondWait` feature flag. Ignition 8.1 documents that `system.project.requestScan([timeout])` has no effect if a project scan is already running and returns when that in-progress scan finishes. To avoid treating an older overlapping scan as the only post-write wait, the runner now attempts two bounded `system.project.requestScan(scanTimeoutSeconds)` waits after confirmed mutations that report `filesChanged:true`.

This applies to confirmed `apply`, confirmed `projectResourceImportZip`, confirmed `rollback`, and confirmed `runnerSelfUpdate`. When `filesChanged:false`, the runner keeps one bounded wait for compatibility with no-change paths.

Responses that attempt a scan now include:

```json
{
  "scanWaitsAttempted": 2,
  "scanWaitsCompleted": 2,
  "defensiveSecondScanWait": true
}
```

Do not interpret these fields as proof that an overlap was detected, a second scan started, or a specific changed resource loaded. This is not overlap detection; it only reports the runner's bounded wait sequence. The existing success/failure fields remain authoritative: `scanCompleted:true`, legacy `scanRequested:true`, `scanTimeoutSeconds`, `filesChanged`, and `recoveryRequired:false` after successful scan returns; any scan exception after changed files still returns `PROJECT_SCAN_FAILED` with `recoveryRequired:true`.

## Runner 0.3.135 Self-Update Scan Completion Message Notes

Runner `0.3.135` adds the `runnerSelfUpdateScanCompletionMessage` feature flag. Successful confirmed `runnerSelfUpdate` responses now report that the project scan returned successfully instead of telling callers to wait for a scan that has already returned.

The success message is:

```text
Runner self-update completed and the project scan returned successfully. Call health to verify the active runner version.
```

This matches Ignition 8.1 `system.project.requestScan([timeout])` semantics: the call blocks the runner thread until a project scan completes or times out. On runner `0.3.136+`, changed-file self-updates also include the post-write second-wait fields documented above. Dry-run behavior and the `Self-update dry run passed. No files were changed.` message are unchanged.

## Runner 0.3.134 Source Variant Dispatch Parity Notes

Runner `0.3.134` adds the `sourceVariantDispatchParity` feature flag. The direct-paste Web Dev body and Project Library runner now use the same public response contracts for source-variant dispatch edges.

Unknown actions return HTTP/status `400`, `ok:false`, `errorCode:"UNKNOWN_ACTION"`, and `error:"Unknown action: <action>"` in both variants. Confirmed package `apply` requests without the exact `confirmApply: "APPLY"` string return HTTP/status `400`, `ok:false`, `errorCode:"CONFIRMATION_REQUIRED"`, and `error:"apply action requires confirmApply set to APPLY"` before taking the mutation lock.

`health` includes both directory-exists alias families in both variants: `inboxExists`, `workExists`, `backupExists`, `inboxDirExists`, `workDirExists`, and `backupDirExists`, plus `runner`. Package `dryRun` and confirmed `apply` success responses include `mode` and `inboxDir` in both variants. When `packageName` is omitted, both variants default to `llm-perspective-package.zip`.

## Runner 0.3.133 Duplicate ZIP Entry Rejection Notes

Runner `0.3.133` adds the `zipDuplicateEntryRejection` feature flag. ZIP extraction now normalizes each entry name before writing and rejects duplicate normalized destinations so package meaning cannot depend on ZIP entry order.

This applies to package `dryRun`, confirmed `apply`, and `projectResourceImportZip`. Duplicate exact names, dot-segment equivalents such as `path/file.txt` and `path/./file.txt`, slash/backslash equivalents, and Windows case-only destination collisions are rejected before package validation, project-resource collection, backup planning, file writes, or project scan.

Duplicate-entry extraction failures return HTTP/status `400`, `ok:false`, and `errorCode: "PACKAGE_ZIP_INVALID"` with `filesChanged:false`, `scanRequested:false`, `scanCompleted:false`, and `recoveryRequired:false`. For `packageBase64` requests, `packageSource` is `packageBase64`.

## Runner 0.3.132 Filesystem Discovery Sort-Before-Cap Notes

Runner `0.3.132` adds the `filesystemDiscoverySortBeforeCap` feature flag. Filesystem-backed discovery actions now collect eligible candidates, sort by the public response path/name, and then apply `maxResults` so truncated responses are deterministic rather than dependent on filesystem enumeration order.

This applies to `projectsList.projectName`, `seedViewsList.viewPath`, `namedQueriesList.queryPath`, `projectResourcesList.path` / `resourcePath`, and `styleResourcesList` sublists for `styleClasses.stylePath`, `images.projectRelativePath`, and `reusableViews.viewPath`. Response fields and request fields are unchanged; clients should still narrow prefixes when `truncated: true`.

## Runner 0.3.131 Metrics Integral Number Precision Notes

Runner `0.3.131` completes the `metricsSnapshotIntegralNumberPrecision` feature flag. Metric counts, gauge values that are integral or integer strings, Java integral number values, memory byte counts, CPU nanosecond counters, and histogram `min` / `max` values are preserved through an exact integral path before any floating-point conversion.

Use runner `0.3.131+` as the floor for this behavior. Runner `0.3.130` introduced the helper path but did not route gauge metric values through it.

This fixes large values above the exact double integer range, such as JVM counters and nanosecond values above `2^53`, being rounded by the old `float(value)` path. Floating values such as rates, means, standard deviations, percentiles, and timer millisecond presentation fields continue to use the existing NaN/Infinity-safe floating conversion. JavaScript clients that need exact arithmetic on very large JSON numbers should parse with bigint-safe tooling.

## Runner 0.3.129 Metrics Snapshot JVM Global Sequence Notes

Runner `0.3.129` adds the `metricsSnapshotJvmGlobalSequence` feature flag. `metricsSnapshot.sequence` is stored in `system.util.getGlobals()` behind a Gateway JVM lock, so repeated direct-paste Web Dev requests and Project Library calls increment the same diagnostic sequence until the Gateway JVM restarts.

This corrects the older direct-paste assumption that a module-level `METRIC_CAPTURE_SEQUENCE = [0]` would survive repeated Web Dev resource executions. Ignition Web Dev Python resources run on each incoming request, so direct-paste request-local module state can reset. Use the `metricsSnapshotJvmGlobalSequence` feature flag when relying on sequence monotonicity across requests.

## Runner 0.3.128 Strict Query Input Validation Notes

Runner `0.3.128` adds the `strictQueryInputValidation` feature flag. `logQuery`, `alarmStatusQuery`, `alarmJournalQuery`, and `auditQuery` now reject invalid query filter inputs before log scanning or Ignition backend calls instead of silently truncating, rewriting, or dropping caller-supplied values.

The runner returns HTTP/status `400` with `ok:false` and one of these structured `errorCode` values:

- `FILTER_LIMIT_EXCEEDED`: list fields such as `auditQuery.profiles` or alarm filter arrays exceed their item cap. Responses include `field`, `maximum`, `supplied`, and `limitKind: "items"`.
- `FILTER_VALUE_TOO_LONG`: a filter string exceeds its character cap. Responses include `field`, optional `fieldPath` for list items, `maximum`, `supplied`, and `limitKind: "characters"`.
- `FILTER_CONTROL_CHARACTERS`: a filter string contains control characters such as LF, CR, or NUL. Responses include `field`, optional `fieldPath`, and `controlCharacters`.

Current request-input caps are:

- `logQuery` filter text fields `loggerContains`, `messageContains`, `textContains`, `excludeLoggerContains`, and `excludeTextContains`: maximum 160 characters and no control characters.
- `auditQuery.profiles`: maximum 10 unique non-empty profile names, each maximum 120 characters and no control characters. Audit string filters `actorFilter`, `actionFilter`, `targetFilter`, `valueFilter`, and `systemFilter`: maximum 160 characters and no control characters.
- `alarmStatusQuery` / `alarmJournalQuery` filter lists: `providers` maximum 10 items; `sources`, `paths`, `displayPaths`, `states`, and `priorities` maximum 20 items; each value maximum 300 characters and no control characters.
- `alarmJournalQuery.journalName` / `journal` / `alarmJournal`: explicit journal profile name maximum 120 characters and no control characters.

This change only affects request validation. Response truncation, response row caps, log tail caps, and existing `truncated` response metadata remain unchanged.

## Runner 0.3.126 auditQuery Global maxResults Notes

Runner `0.3.126` adds the `auditQueryGlobalMaxResults` feature flag. `auditQuery.maxResults` is now a global response row cap shared across all requested explicit audit profiles. This keeps top-level `returnedRowCount <= maxResults` and makes `responseMaxRows` truthful for the whole response.

The runner still queries each requested profile for diagnostics. Each successful `attempts[]` item includes `responseMaxRows`, `returnedRowCount`, `rowCount`, `columns`, `rows`, and `truncated`. When earlier profiles consume the global row budget, later successful profile attempts can have `rows: []`, `responseMaxRows: 0`, and `truncated: true` while preserving the profile's `rowCount` and column metadata. Top-level responses include `maxResultsScope: "global"` and aggregate `truncated`.

## Runner 0.3.127 Backend Scope/Row Bound Metadata Notes

Runner `0.3.127` adds the `backendScopeRowBoundMetadata` feature flag. Successful `alarmStatusQuery`, `alarmJournalQuery`, and `auditQuery` responses now split backend scope restriction from row bounding. These Ignition APIs accept filters and date ranges, but do not expose a backend row-limit argument like a SQL `LIMIT`, so the runner no longer claims the backend rowset is row-bounded.

For these three actions, successful responses include `backendScopeRestricted: true`, `backendScopeRestrictionSource`, `backendRowBounded: false`, `responseRowsBounded: true`, `minimumFilterLiteralChars: 2`, and compatibility fields `backendBounded: false` plus `backendBoundSource`. `backendBoundSource` is retained for older clients, but new clients should prefer the split fields. A too-short alarm or audit scope filter is rejected before calling Ignition with HTTP/status `400`, `errorCode: "BACKEND_SCOPE_FILTER_TOO_BROAD"`, and `minimumFilterLiteralChars: 2`.

`namedQueryPreview.previewSafety.backendBounded` is unchanged because Named Query preview still requires a DB-side row limiter or safe max-return-size setting before execution.

## Runner 0.3.125 Jython Script Literal-Aware Syntax Lint Notes

Runner `0.3.125` adds the `jythonScriptSyntaxLintLiteralAware` feature flag. Perspective view lint still rejects executable Python 3-only syntax in script text for Jython 2.7 compatibility, including f-strings, assignment expressions, `async`/`await`, `match`/`case`, and `def ... ->` return annotations.

The static syntax guard now masks comments and string literal bodies before scanning for executable markers. This means valid Jython script text may contain marker examples in `#` comments, normal strings, or triple-quoted strings without being rejected by raw substring matches. The compile fallback remains unchanged and still runs after the static guardrails when no static error has been found.

Action names, request fields, response fields, confirmation strings, supported action lists, package formats, and backup formats are unchanged.

## Runner 0.3.124 Apply Package Invalid Data Notes

Runner `0.3.124` adds the `applyPackageInvalidDataErrors` feature flag. Package `dryRun` and confirmed `apply` now validate `packageBase64` before creating the apply work directory, extracting package data, planning backups, writing files, or requesting a project scan.

Malformed Base64 returns HTTP/status `400`, `ok:false`, and `errorCode: "PACKAGE_BASE64_INVALID"`. The response includes `packageSource: "packageBase64"`, `filesChanged:false`, `scanRequested:false`, `scanCompleted:false`, and `recoveryRequired:false`.

```json
{
  "ok": false,
  "statusCode": 400,
  "errorCode": "PACKAGE_BASE64_INVALID",
  "error": "packageBase64 is not valid base64: <details>",
  "packageSource": "packageBase64",
  "filesChanged": false,
  "scanRequested": false,
  "scanCompleted": false,
  "recoveryRequired": false
}
```

If `packageBase64` decodes successfully but the bytes do not have a ZIP signature, package `dryRun` and confirmed `apply` return HTTP/status `400`, `ok:false`, and `errorCode: "PACKAGE_ZIP_INVALID"` with the same no-mutation fields before work-directory creation. Unreadable inbox ZIP failures can still be reported as `PACKAGE_ZIP_INVALID` during extraction and may include normal work-directory cleanup metadata such as `workDirCleaned:true`.

`projectResourceImportZip` already had controlled Base64 validation and is not changed by this release. Valid ZIP packages, inbox package lookup, no-root package validation, multi-root package validation, `RESOURCE_MANIFEST_INVALID`, action names, request fields, confirmation strings, and backup formats are unchanged.

## Runner 0.3.122 Atomic Copy Tree Destination Preservation Notes

Runner `0.3.122` adds the `atomicCopyTreeDestinationPreservation` feature flag. Directory copy/restore helpers used by runner backup and rollback paths no longer delete an existing destination directory before promoting the new tree.

When replacing a directory, the runner uses a three-path swap: copy source content to a sibling new-temp tree, move the existing destination to a sibling old-temp tree, then atomically move the new-temp tree to the final destination. If final promotion fails, the runner attempts to restore the old-temp tree back to the original destination. If that restore also fails, the error includes `original destination is preserved at <oldTempPath>` and the old-temp tree is left in place for manual recovery instead of being deleted.

Copy failures before the swap leave the existing destination untouched. Successful replacements delete the retired old-temp tree after the new tree is in place. Action names, request fields, response fields, confirmation strings, backup manifest formats, and supported action lists are unchanged.

## Runner 0.3.121 Project Resource Manifest Validation Notes

Runner `0.3.121` adds the `projectResourceManifestValidation` feature flag. For runner-managed Perspective views, Project Library scripts, Named Queries, and Perspective page config, the runner now validates the Ignition `resource.json.files` manifest before accepting package `dryRun`/`apply`, `projectResourceImportZip` entries that include `resource.json`, and `pageValidate` structural checks.

The runner validates only file-manifest shape and managed sibling data-file consistency. It does not rewrite Ignition-authored metadata fields such as `scope`, `version`, `restricted`, `overridable`, or `attributes`, and it preserves valid Ignition-authored Named Query resource shapes. `resource.json.files` must be a list of simple sibling file names, must not include `resource.json`, must include the required managed data file, and must not point at missing or unsupported data files.

Managed requirements:

- Perspective view resources require `view.json` and may list `thumbnail.png`.
- Project Library script resources require `code.py`.
- Named Query resources require `query.sql`.
- Perspective page config requires `config.json`.

Malformed manifests return HTTP/status `400`, `ok:false`, and `errorCode: "RESOURCE_MANIFEST_INVALID"` before writes, backup planning, or project scan. The response includes `resourcePath`, `manifestPath`, and `manifestIssues`.

```json
{
  "ok": false,
  "statusCode": 400,
  "errorCode": "RESOURCE_MANIFEST_INVALID",
  "error": "Resource manifest validation failed: Perspective view resource.json.files must list view.json",
  "resourcePath": "com.inductiveautomation.perspective/views/LLM Tests/Example",
  "manifestPath": "com.inductiveautomation.perspective/views/LLM Tests/Example/resource.json",
  "manifestIssues": [
    "Perspective view resource.json.files must list view.json"
  ]
}
```

`pageValidate` remains read-only and reports malformed page config or dependency manifests as structural issues such as `pageConfigResourceManifestInvalid`, `viewResourceManifestInvalid`, `scriptResourceManifestInvalid`, or `namedQueryResourceManifestInvalid`.

## Runner 0.3.120 Apply Package Single Project Root Notes

Runner `0.3.120` adds the `applyPackageSingleProjectRoot` feature flag. Package `dryRun` and `apply` ZIPs must contain exactly one directory with `project.json`, matching Ignition's project-scoped export/import model where `project.json` is the project root marker.

If the extracted package contains more than one project root, the runner returns HTTP/status `400`, `ok:false`, and `errorCode: "MULTIPLE_PACKAGE_PROJECT_ROOTS"` before route discovery, package validation, backup planning, file writes, or project scan. The response includes `packageProjectRootCount` and sorted relative `packageProjectRootCandidates` so the caller can rebuild the ZIP around the intended project.

```json
{
  "ok": false,
  "statusCode": 400,
  "errorCode": "MULTIPLE_PACKAGE_PROJECT_ROOTS",
  "error": "Package contains multiple project roots; include exactly one project.json root",
  "packageProjectRootCount": 2,
  "packageProjectRootCandidates": ["ProjectA", "ProjectB"]
}
```

No-root packages keep the existing `No project.json found in package` validation error. Single-root packages continue through the existing `dryRun`/`apply` path. `projectResourceImportZip` is unchanged by this release because it imports project-resource ZIPs, not whole project package roots.

## Runner 0.3.119 Project Target Validation Notes

Runner `0.3.119` adds the `projectTargetValidation` feature flag. Project-scoped actions now require `targetProject` to identify a real Ignition project directory, not merely an existing directory under or equal to the projects root.

The accepted project name shape is alphanumeric plus underscore only. Dot names such as `"."`, dot-only values, path separators, colons, whitespace-padded names, and other special characters are rejected before filesystem resolution.

After name validation, the runner resolves the target canonically and requires it to be a direct child of the configured `projectsRoot`. The target must exist as a directory, contain a regular-file `project.json`, and that `project.json` must parse as a JSON object. Invalid targets return the existing validation envelope shape, normally HTTP/status `400` with `ok:false` and an explanatory `error`.

This same target validation is used by `projectInfoRead`, route/view/style/seed/Named Query/project-resource read actions, `dryRun`, `apply`, `projectResourceImportZip`, `rollback`, and `runnerSelfUpdate`. `projectsList` also filters out child folders whose `project.json` is missing, not a file, malformed JSON, or not a JSON object. `gatewayInfo` keeps `ok:true` as a diagnostic action but reports `targetProjectValid:false`, `targetProjectExists:false`, and `targetProjectError` for invalid `targetProject` values.

## Runner 0.3.118 Rollback afterSha256 Drift Guard Notes

Runner `0.3.118` adds the `rollbackAfterSha256DriftGuard` feature flag. Before a `fileChanges-v1` rollback dry-run or apply can report success, the runner compares the current target state against each manifest row's recorded `afterSha256` state from the mutation that created the backup.

Runner `0.3.144+` keeps this strict check for completed backups, but an unfinished backup marked `afterStateKnown:false` uses `rollbackDriftCheckMode:"unknown-after-state"` and reports `driftCheckSkipped:true` instead of treating `afterSha256:null` as an expected-missing assertion.

If the current target has drifted, rollback returns HTTP/status `409`, `ok: false`, and `errorCode: "ROLLBACK_DRIFT_DETECTED"` before changing files, creating a pre-rollback backup, or requesting a project scan. The response includes `recoveryRequired:false`, `filesChanged:false`, `scanRequested:false`, `scanCompleted:false`, `preRollbackBackupCreated:false`, `driftedFiles`, `driftedFileCount`, and `forceDriftedRollback:false`.

Each `driftedFiles[]` item includes `targetPath`, `physicalPath`, `existedBefore`, `reason`, `afterSha256Present`, `expectedExists`, `currentExists`, `currentIsFile`, `expectedAfterSha256`, and `currentSha256`. Reasons include `missingAfterSha256`, `expectedMissingCurrentExists`, `expectedPresentCurrentMissing`, `expectedFileCurrentNonFile`, and `sha256Mismatch`.

To intentionally overwrite or remove drifted current files, send the normal rollback apply confirmation plus `forceDriftedRollback: "FORCE_ROLLBACK_DRIFT"`. Forced rollback responses still include `driftedFiles`, `driftedFileCount`, and `forceDriftedRollback:true`; confirmed forced applies create the usual pre-rollback backup of the current state before overwriting or removing files. Legacy `projectResourceImportZip` rollback is unchanged.

After a successful confirmed `apply`, `projectResourceImportZip`, or `runnerSelfUpdate` scan, runner `0.3.118+` refreshes the selected `fileChanges-v1` backup manifest and sets `backupAfterScanRefreshed:true`. The mid-write recovery stage name for this step is `refreshBackupManifestAfterScan`. This records Ignition-managed post-scan metadata such as updated `resource.json` hashes before a later rollback compares `afterSha256`, preventing clean rollback backups from being falsely treated as drifted. Pre-rollback recovery backups created by rollback are also finalized with current `afterSha256` values.

## Runner 0.3.116 Rollback Removal Failure Reporting Notes

Runner `0.3.116` adds the `rollbackRemovalFailureReporting` feature flag. Confirmed `fileChanges-v1` rollback now treats Java `File.delete()` postconditions as authoritative for files created by the selected backup. A rollback apply reports `removedFiles` only for files verified absent after deletion.

If a target file still exists after `delete()` returns false, or an empty parent directory still exists after prune deletion, rollback returns HTTP/status `500`, `ok: false`, and `errorCode: "ROLLBACK_REMOVAL_FAILED"`. The response includes `recoveryRequired: true`, `failedRemovals`, `failedRemovalCount`, `failedPrunes`, `failedPruneCount`, actual `removedFiles`, `removedFileCount`, `prunedDirs`, `prunedDirCount`, and `preRollbackBackupDir`.

Dry-run behavior is unchanged: `removedFiles` in a rollback dry-run is the planned removal set. Confirmed apply responses use verified actual removals. When a removal failure is detected before project scan, `scanRequested` and `scanCompleted` remain false; inspect `failedRemovals` and the pre-rollback backup before issuing more writes.

## Runner 0.3.115 Mid-Write Failure Recovery Metadata Notes

Runner `0.3.115` adds the `midWriteFailureRecoveryMetadata` feature flag. If `apply`, confirmed `projectResourceImportZip`, or confirmed `runnerSelfUpdate` raises after backup planning or file writes begin, the runner returns a controlled failure envelope instead of letting an exception escape or collapsing the result into a generic error.

Mid-write failure responses use HTTP/status `500`, `ok: false`, and `errorCode: "MID_WRITE_FAILURE"`. The response preserves recovery metadata at the top level and inside `writeFailure`: `backupCreated`, `backupName`, `backupDir`, `backupFormat`, `writesStarted`, `writtenPaths`, `failedStage`, `filesChanged`, `recoveryRequired`, `rollbackAvailable`, `afterStateKnown`, `backupManifestComplete`, `rollbackDriftCheckMode`, `recoveryAttempted: false`, `recoverySucceeded: false`, `exceptionType`, and `detail`.

`rollbackAvailable: true` means the runner created a rollback-compatible backup before or during the failed mutation. Stop further writes, inspect `writeFailure`, and use the normal `rollback` action with the returned `backupName` when recovery is appropriate. The runner does not attempt automatic rollback in this exception path.

Dry-runs do not mutate project files and do not produce mid-write recovery metadata. Validation failures before backup planning still return their existing validation envelopes rather than `MID_WRITE_FAILURE`.

## Runner 0.3.114 Tag Mutation Locking Notes

Runner `0.3.114` adds the `tagMutationLocking` feature flag. Confirmed tag mutation actions now enter the same Gateway-wide mutation lock used by project/package mutations: `tagConfigure`, `tagEventScriptProbe`, `udtTagEventScriptProbe`, and `udtScaffold`.

When another writeful runner mutation already holds the lock, confirmed tag writes return the standard retryable busy envelope with `statusCode: 409`, `errorCode: "MUTATION_LOCK_BUSY"`, `mutationLockBusy: true`, `busy: true`, `retryable: true`, `retryAfterMs`, and `lockName: "gatewayMutationLock"`. The requested callback is not executed while the lock is busy.

Tag dry-runs remain non-blocking. `health.mutationLockAppliesToConfirmedWritesOnly` documents this for `tagConfigure`, `tagEventScriptProbe`, `udtTagEventScriptProbe`, and `udtScaffold`, plus existing dry-run exceptions for `rollback` and `runnerSelfUpdate`.

`udtScaffold` acquires the lock once at the public action boundary and keeps its nested `tagConfigure` calls direct inside that critical section. This preserves the existing scaffold flow while preventing concurrent same-path tag probe/configure cleanup races.

## Runner 0.3.113 udtScaffold Partial Recovery Notes

Runner `0.3.113` adds the `udtScaffoldPartialFailureRecovery` feature flag. Before a confirmed scaffold write, `udtScaffold` preflights each UDT type/instance recovery root with `system.tag.exists`; existing roots are snapshotted with `system.tag.getConfiguration(path, True)`.

If a later scaffold step fails after earlier writes started, the runner attempts recovery before returning the failed response. Newly created recovery roots from completed or partially successful steps are deleted with `system.tag.deleteTags`; roots that existed before the scaffold are restored with `system.tag.configure(parentPath, snapshot, "o")`.

Failed scaffold responses include `preflightTargetCount`, `preflightExistingPaths`, `preflightNewPaths`, `snapshotPathCount`, `writesStarted`, `completedSteps`, `recoveryAttempted`, `recoveryAllGood`, `recoveryRequired`, and `recovery`. The `recovery` object includes `deletePaths`, `skippedDeletePaths`, `restorePaths`, `deleteQualityCodes`, `restoreQualityCodes`, `errors`, `attempted`, and `allGood`.

`recoveryRequired: true` means cleanup or restore failed or returned non-good quality, so stop and inspect Gateway state before issuing more UDT writes. Dry-runs do not snapshot or mutate tags. Duplicate UDT instance names/paths are rejected during planning before any nested `tagConfigure` call.

## Runner 0.3.112 udtScaffold Step Failure Notes

Runner `0.3.112` adds the `udtScaffoldStepAllGoodFailureOkFalse` feature flag. `udtScaffold` now stops after any nested `tagConfigure` step that returns either `ok: false` or `allGood: false`.

The top-level scaffold response for that path is `ok: false`, includes `failedStep`, `failedStepResult`, `stepResults`, and a 400-style `statusCode` when the nested step did not provide one. The failed nested step result is preserved, including fields such as `qualityCodes`, `allGood`, `errorCode`, `plannedPaths`, and conflict diagnostics.

The scaffold no longer returns the `"UDT scaffold completed"` message when any nested step reports bad quality under a top-level `ok: true` helper envelope. Dry-runs, successful scaffold applies, action names, request fields, and `confirmUdtScaffold: "SCAFFOLD_UDT"` are unchanged.

## Runner 0.3.111 tagConfigure QualityCode Failure Notes

Runner `0.3.111` adds the `tagConfigureQualityFailureOkFalse` feature flag. Confirmed `tagConfigure` applies now treat Ignition returned `QualityCode` failures as action failures instead of reporting a top-level success envelope.

If any returned `QualityCode` is non-good, the runner returns `ok: false`, `statusCode: 400`, `errorCode: "TAG_CONFIGURE_BAD_QUALITY"`, `error`, and `message`. The response still preserves `qualityCodes`, `allGood`, `qualityCodeCount`, `expectedQualityCodeCount`, `plannedPaths`, `plannedTagCount`, and conflict diagnostics.

If Ignition returns a number of `QualityCode` objects that differs from the number of top-level submitted `tags`, the runner returns `ok: false`, `statusCode: 400`, `errorCode: "TAG_CONFIGURE_QUALITY_CODE_COUNT_MISMATCH"`, plus the returned and expected counts. The expected count is the top-level submitted tag config count, not the recursive `plannedTagCount`.

Dry-runs, runner-side validation failures, exception handling, action names, request fields, and confirmation strings are unchanged.

## Runner 0.3.110 Project Library allowOverwrite Boolean Notes

Project Library `apply` now parses `allowOverwrite` through the runner boolean parser. `allowOverwrite` string values now parse through the runner boolean parser, so `"false"`, `"FALSE"`, `"0"`, `"no"`, empty string, missing, and `null` are false, while boolean `true` and strings such as `"true"`, `"1"`, `"yes"`, and `"y"` are true. This fixes Project Library deployments where a caller-provided `"allowOverwrite": "false"` string could previously behave like true because Jython/Python treats non-empty strings as truthy.

The direct-paste runner already used the same boolean parser for `allowOverwrite`; runner `0.3.110` keeps both variants aligned. No action names, request fields, response fields, confirmation strings, or feature flags changed.

## Runner 0.3.109 Project Library projectsList Helper Notes

Project Library `projectsList` now uses the defined `_safe_project_name` helper instead of the direct-paste-only `safe_name`/undefined `_safe_name` helper path. This fixes Project Library deployments where `projectsList` could raise a runtime `NameError` when the projects root contained a non-hidden directory. No action names, request fields, response fields, confirmation strings, or feature flags changed.

## Runner 0.3.108 Primary Query Failure Envelope Notes

Runner `0.3.108` adds the `primaryQueryFailureOkFalse` feature flag. Primary backend failures in `historyProbe`, `alarmStatusQuery`, `alarmJournalQuery`, and all-failed `auditQuery` now return top-level `ok: false`, `statusCode: 500`, `errorCode`, and `error`. Error codes are `HISTORY_QUERY_FAILED`, `HISTORY_SAMPLE_COUNT_QUERY_FAILED`, `ALARM_STATUS_QUERY_FAILED`, `ALARM_JOURNAL_QUERY_FAILED`, and `AUDIT_QUERY_FAILED`.

Action-specific diagnostic fields are preserved when the failing path has populated them. `historyProbe` value-query failures report `queryOk:false`, `queryError`, `sampleCountQueryOk:false`, the good-sample terminology mode fields added in runner `0.3.137`, and `goodSampleHistoryAvailable:false` / compatibility `historyAvailable:false`; the sample-count query has not run yet, so `goodStoredSampleCount`, compatibility `storedSampleCount`, and `tagStats` are not populated on that path. `historyProbe` sample-count-query failures occur after the value query succeeds and preserve `queryOk:true`, value-query diagnostics, `sampleCountQueryOk:false`, `sampleCountQueryError`, `goodStoredSampleCount:0`, compatibility `storedSampleCount:0`, and merged `tagStats`. `alarmStatusQuery` and `alarmJournalQuery` still report `queryOk` and `queryError`; `alarmJournalQuery` preserves `errorType`; `auditQuery` keeps per-profile `attempts[]`. A mixed `auditQuery` with at least one successful profile remains `ok: true` and records failed profiles in `attempts[]`.

Clients should parse the JSON body on non-2xx responses and should not rely on `queryOk: false` appearing under a top-level success envelope for these primary operations.

## Runner 0.3.107 Feature And Action Advertising Notes

Runner `0.3.107` separates action discovery from capability flags. `health.supportedActions` now lists the exact dispatchable action names, while `health.features` no longer includes direct action names. The `tagBrowseTotalAvailable` capability remains a feature flag and `tagBrowse` response field, but it is not an action. `mutationLockedActions` now contains exact action names rather than operation labels such as `rollback apply`.

## Runner 0.3.106 Dispatch Boundary Notes

Runner `0.3.106` moves action dispatch out of the Web Dev request entrypoints in both runner variants. `main()` in the simple one-paste body and `handle_post()` in the Project Library runner now parse the request, authorize it, call `dispatch_action` or `_dispatch_action`, wrap the response, and handle exceptions.

This release does not add a `health.features` flag, does not add or remove actions, and does not rename request or response fields. The dispatch maps preserve the existing mutation-lock wrappers, exact confirmation guards, and supported action surface. The simple Web Dev body remains self-contained for direct paste and self-update compatibility; the project-library unknown-action fallback was intentionally preserved and subsequently covered by the Bug #27 error-shape cleanup.

## Runner 0.3.105 Project Scan Timeout Control Notes

Runner `0.3.105` adds the `projectScanTimeoutControl` feature flag. Confirmed `apply`, confirmed `projectResourceImportZip`, confirmed `rollback`, and confirmed `runnerSelfUpdate` accepts optional `scanTimeoutSeconds`, an integer from `1` through `30`, default `10`.

The runner passes the effective value to `system.project.requestScan(timeout)`. Ignition 8.1 documents `requestScan([timeout])` as a blocking project-directory scan request with a default timeout of 10 seconds. Dry-runs validate `scanTimeoutSeconds` when present but do not request a project scan.

When a scan is attempted, responses continue to echo `scanTimeoutSeconds` with the effective value. Runner `0.3.136+` changed-file mutations attempt two bounded waits and report `scanWaitsAttempted`, `scanWaitsCompleted`, and `defensiveSecondScanWait`. Scan failure after files changed remains non-successful with `errorCode: "PROJECT_SCAN_FAILED"`, `scanCompleted: false`, and `recoveryRequired: true`.

## Runner 0.3.104 Runner Self-Update Exact Backup Notes

Runner `0.3.104` adds the `runnerSelfUpdateExactBackup` feature flag. Current `runnerSelfUpdate` backups still use `backupFormat: "fileChanges-v1"`, and the manifest records the exact pre-update Web Dev `doPost.py` source plus the sibling Web Dev `resource.json`.

Dry-run and apply responses include `backupExactSource: true` and `backupTokenRedacted: false`. Rollback of a current self-update backup restores the exact recorded `doPost.py` source instead of a redacted code-recovery snapshot.

Because exact runner source can include literal `TOKEN` or `STATIC_TOKEN` assignments on some installations, protect backup folders like runner source or other local secret-bearing project files. The product bundle still ships sanitized blank token constants; this note is about target-local backups created from whatever source is already running on the Gateway.

## Runner 0.3.103 Runner Self-Update Resource Metadata Rollback Notes

Runner `0.3.103` adds the `runnerSelfUpdateResourceJsonRollback` feature flag. `runnerSelfUpdate` backups still use `backupFormat: "fileChanges-v1"`, and the manifest records both the Web Dev `doPost.py` backup and a snapshot of the sibling Web Dev `resource.json`.

Dry-run and apply responses include `targetResourceFile` plus `backupIncludesResourceJson: true`. `backupList.targetPathSamples` for current self-update backups can include both `com.inductiveautomation.webdev/resources/<resource>/doPost.py` and `com.inductiveautomation.webdev/resources/<resource>/resource.json`.

Rollback of a current self-update backup restores or removes `resource.json` exactly as recorded by the selected `fileChanges-v1` manifest, so the metadata touched by `runnerSelfUpdate` is part of the rollback plan. Runner `0.3.104+` also makes the `doPost.py` backup exact source instead of a redacted code-recovery snapshot.

## Runner 0.3.102 Project Resource Import Rollback Compatibility Notes

Runner `0.3.102` adds the `projectResourceImportZipLegacyRollback` feature flag. Current `projectResourceImportZip` backups that use `backupFormat: "fileChanges-v1"` remain the primary rollback path for imports and already restore overwritten files and remove files created by the selected backup.

Damaged `fileChanges-v1` rollback manifests with required backup files missing now return a validation error before dry-run or apply can succeed. Treat that as a stop condition; do not apply a rollback that reports missing required backup file evidence.

Legacy `projectResourceImportZip` backup folders without `fileChanges` can now restore backed-up overwritten project-resource files. Their rollback dry-runs and applies report `backupFormat: "legacy-project-resource-import"`, `restoredFiles`, `restoredFileCount`, `createdFilesNotRemoved: true`, and explanatory `notes`. Files created by the original legacy import cannot be inferred from those backup folders, so this compatibility path does not remove created files.

## Runner 0.3.101 Explicit UTF-8 Text File I/O Notes

Runner `0.3.101` adds the `explicitUtf8TextFileIo` feature flag. Runner-managed text file reads and writes now encode and decode text explicitly as UTF-8 instead of depending on the Gateway JVM or host platform default charset.

This covers runner text helpers used for JSON manifests, Perspective `view.json`, `resource.json`, Project Library scripts, Named Query SQL, runner self-update source, backup/rollback manifest readback, and project-resource text responses. Binary flows remain binary: ZIP package bytes, log tail reads, backup file copies, and SHA-256 byte hashing are not text-decoded.

Request JSON should still be UTF-8 without BOM. The existing `jsonBomNormalization`, backup/rollback, mutation-lock, scan, redaction, and response contracts are otherwise unchanged.

## Runner 0.3.100 Thread Dump Streaming SHA-256 Notes

Runner `0.3.100` adds the `threadDumpStreamingSha256` feature flag. `threadDumpQuery` preserves the existing response shape and `unredactedDumpSha256` integrity field, but streams each canonical unredacted thread dump text into a SHA-256 digest instead of retaining a full raw dump list and joining it only for hashing.

The diagnostic confirmation, redaction defaults, thread filters, response character cap, `threads[]` payload, and truncation semantics are unchanged. The hash covers the same canonical per-thread text for the processed unredacted dump lines and is intended for target-local evidence correlation; raw thread text should still stay out of reusable docs.

## Runner 0.3.99 Named Query Top-Level Row Limit Notes

Runner `0.3.99` adds the `namedQueryTopLevelRowLimitScanner` feature flag. `namedQueryPreview` now treats SQL row-limit proof conservatively: only top-level outer-query numeric `LIMIT`, `TOP`, or `FETCH FIRST/NEXT` literals can prove the final rowset is DB-side bounded.

Nested-only row limiters no longer count as proof because an outer query can still multiply or expand the result. `TOP PERCENT`, `TOP WITH TIES`, `FETCH ... WITH TIES`, dynamic limits, and nonliteral limits are rejected before execution unless the Named Query has `useMaxReturnSize` with `maxReturnSize <= maxRows`.

Successful preview responses still include `previewSafety.backendBounded`, `previewSafety.backendBoundSource`, `previewSafety.backendRowLimit`, and `previewSafety.responseMaxRows`. The `backendBoundSource` is one of `LIMIT`, `TOP`, `FETCH`, or `maxReturnSize`.

## Runner 0.3.98 Prefix Boundary Notes

Runner `0.3.98` adds the `pathPrefixBoundaryMatching` feature flag. Logical path allowlists use exact-or-child prefix matching: prefix `LLM Tests/A` matches `LLM Tests/A` and `LLM Tests/A/Child`, but not `LLM Tests/ABC` or `LLM Tests/A2`.

This applies to view, seed view, style, reusable view, Named Query, dependency view, shared dock view, dependency script, package route, page validation, and list/read helper filters. Project-resource `allowedResourcePrefix` already used the same exact-or-child containment style and remains singular.

Compatibility notes: the default route prefix `/llm-` is a route namespace and still matches `/llm-example` and `/llm-equipment/:assetId`. The default `allowedScriptPrefix` of `llm` still allows root-level `llm...` Project Library script modules such as `llmCommandWriteback`; child script paths use exact-or-child matching.

## Runner 0.3.97 Alarm Journal Explicit Profile Notes

Runner `0.3.97` adds the `alarmJournalExplicitProfileRequired` feature flag. `alarmJournalQuery` now requires an explicit `journalName`, `journal`, or `alarmJournal` value and always passes that value to `system.alarm.queryJournal`.

useDefaultJournal is rejected, and the legacy `useConfiguredJournal` alias is rejected, before the runner calls Ignition. Ignition 8.1 documentation permits omitting `journalName` only when exactly one alarm journal exists on the Gateway, and this runner does not have a safe journal-profile inventory contract to verify that condition. Use the exact Alarm Journal profile from the Perspective Alarm Journal Table `props.name`, target documentation, or operator-provided Gateway configuration evidence.

Successful `alarmJournalQuery` responses include `journalNameRequired: true`, `journalName` set to the exact requested profile name, and `journalMode: "explicit"`.

## Runner 0.3.96 Backend Query Work Bound Notes

Runner `0.3.96` adds the `backendQueryWorkBounds` feature flag. The runner now rejects broad alarm, audit, and Named Query preview requests before calling Ignition/database APIs when a caller-provided returned-row cap would only trim results after backend work had already happened.

`alarmStatusQuery` now requires at least one narrow `source`, `path`, or `displayPath` value before calling `system.alarm.queryStatus`. `provider`, `state`, `priority`, and `includeShelved` remain useful filters, but they do not count as the backend work bound. Runner `0.3.127+` requires at least two non-wildcard characters in that scope filter and reports `backendScopeRestricted: true`, `backendRowBounded: false`, `responseRowsBounded: true`, `minimumFilterLiteralChars: 2`, `backendBounded: false`, and `backendBoundSource: "narrowAlarmIdentityFilter"` on successful responses.

`alarmJournalQuery` now requires at least one narrow `source`, `path`, or `displayPath` value before calling `system.alarm.queryJournal`. The old `allowBroad` plus `confirmBroadAlarmJournalQuery` bypass is removed, and the maximum window is `1440` minutes. Runner `0.3.127+` requires at least two non-wildcard characters in that scope filter and reports `responseMaxRows`, `backendScopeRestricted: true`, `backendRowBounded: false`, `responseRowsBounded: true`, `minimumFilterLiteralChars: 2`, `backendBounded: false`, `backendBoundSource: "narrowAlarmIdentityFilterAndTimeRange"`, and `maxRangeMinutes`.

`auditQuery` now requires at least one narrow `actorFilter`, `actionFilter`, `targetFilter`, `valueFilter`, or `systemFilter`; `contextFilter` alone is not enough to bound backend work. The old `allowBroad` plus `confirmBroadAuditQuery` bypass is removed, and the maximum window is `1440` minutes. Runner `0.3.127+` requires at least two non-wildcard characters in that scope filter and reports `responseMaxRows`, `backendScopeRestricted: true`, `backendRowBounded: false`, `responseRowsBounded: true`, `minimumFilterLiteralChars: 2`, `backendBounded: false`, `backendBoundSource: "narrowAuditFilterAndTimeRange"`, and `maxRangeMinutes`. Runner `0.3.126+` also reports `maxResultsScope: "global"` and caps returned rows globally across all requested profiles.

`namedQueryPreview` now compares DB-side `LIMIT`, `TOP`, `FETCH`, or Named Query max return size against the request's `maxRows`, not only the global runner preview cap. Successful preview responses include `previewSafety.backendBounded`, `previewSafety.backendBoundSource`, `previewSafety.backendRowLimit`, and `previewSafety.responseMaxRows`.

## Runner 0.3.95 Tag Event Probe Failure Cleanup Notes

Runner `0.3.95` adds the `tagEventProbeFailureCleanup` feature flag. When `tagEventScriptProbe` or `udtTagEventScriptProbe` fails after apply has started creating its constrained fixture tags, the runner attempts best-effort cleanup of the fresh planned probe paths with `system.tag.exists` and `system.tag.deleteTags`.

This cleanup is intentionally narrow. It applies only to the new probe folder for `tagEventScriptProbe` and to the two new UDT instances plus new UDT type for `udtTagEventScriptProbe` after those paths passed the normal pre-apply conflict checks. It is not a general delete API, it does not use `scriptEval`, and cleanup failure does not replace the original probe error.

Dry-runs include `failureCleanupPaths` so callers can see which paths would be cleaned on a post-create failure. Dry-runs never delete tags. Failed apply responses may include `failureCleanup` with `attempted`, `paths`, `skippedPaths`, `deleteQualityCodes`, `deleteAllGood`, `allGood`, and `errors`.

## Runner 0.3.94 Tag Event Probe Synchronous Wait Cap Notes

Runner `0.3.94` adds the `tagEventProbeSynchronousWaitCap` feature flag. `tagEventScriptProbe` and `udtTagEventScriptProbe` still accept caller `pollAttempts` up to the existing bounded input limit, but the runner calculates an effective `pollAttempts` so the synchronous wait budget stays bounded by `maxProbeSyncWaitMs` (`30000` ms). Use response `pollAttempts` as the effective value and `requestedPollAttempts` as the normalized caller request.

Probe responses now include `requestedPollAttempts`, effective `pollAttempts`, `pollAttemptsCapped`, `pollWindowCount`, `probeFixedDelayMs`, `probeNonPollWaitMs`, `probePollWaitMaxMs`, `probeSyncWaitMaxMs`, and `maxProbeSyncWaitMs`. Dry-runs return the same timing metadata, so callers can detect capped waits before applying a probe. Use `probeSyncWaitMaxMs` instead of multiplying raw request fields when estimating maximum call duration.

For `tagEventScriptProbe`, the single poll window is `pollAttempts * pollMs` after `activateDelayMs`. For `udtTagEventScriptProbe`, the cap covers two poll windows plus the fixed `500` ms settle delay.

## Runner 0.3.93 History Probe Sample-Backed Availability Notes

Runner `0.3.93` adds the `historyProbeSampleBackedAvailability` feature flag. `historyProbe.historyAvailable` is now driven by a separate strict sample-count query rather than by non-null cells in the displayed value query.

For availability, the runner calls `system.tag.queryTagHistory` with `returnSize: 1`, `aggregationMode: "Count"`, `returnFormat: "Wide"`, `includeBoundingValues: false`, `noInterpolation: true`, and `ignoreBadQuality: true`. Runner `0.3.137+` names this as good-quality sample evidence: top-level `goodSampleHistoryAvailable` is true only when at least one requested path reports a positive good-quality stored sample count. Top-level `goodStoredSampleCount`, `sampleCountQueryOk`, `sampleCountQueryError`, `sampleCountRowCount`, `sampleCountColumnCount`, `sampleCountColumns`, `availabilityQualityMode`, `availabilityIgnoresBadQuality`, and `availabilityNoInterpolation` describe that availability query. Compatibility `historyAvailable` and `storedSampleCount` remain aliases of the good-sample fields.

The original caller-selected value query still runs for diagnostics and sample rows. Its former availability signal is returned as `valueQueryHistoryAvailable`; `tagStats[].nonNullCount`, `tagStats[].hasData`, `tagStats[].firstTimestamp`, `tagStats[].lastTimestamp`, and `tagStats[].lastValue` describe the value query only. Each `tagStats[]` entry also includes `goodStoredSampleCount`, `sampleCountColumn`, `goodSampleHistoryAvailable`, and compatibility aliases `storedSampleCount`, `historyAvailable`, and `sampleBackedHistoryAvailable`; use the good-sample fields when deciding whether a trend/history component has good-quality counted historian samples. A false/zero good-sample result does not rule out bad-quality historical rows.

## Runner 0.3.92 Perspective Session Match Count Notes

Runner `0.3.92` adds the `perspectiveSessionsQueryMatchedCount` feature flag. `perspectiveSessionsQuery` now reports `matchedCount`, the number of project sessions that matched local `sessionIds` filters before `maxResults` is applied.

`truncated` is now true only when `matchedCount` is greater than `returnedCount`. This means filtered-out project sessions counted in `scannedCount` no longer make a filtered response look truncated when all matching sessions were returned.

## Runner 0.3.91 Unique ID Stamp Notes

Runner `0.3.91` adds the `uniqueIdStamps` feature flag. Runner-generated fallback `requestId` values and generated work/backup names now keep the sortable timestamp prefix and append an eight-character Java UUID prefix.

This applies to generated fallback `requestId` values, package `dryRun`/`apply` work directories and backups, `projectResourceImportZip` work directories and backups, rollback pre-backup directories, and `runnerSelfUpdate` backups. Valid caller-supplied `requestId` values are still echoed unchanged.

## Runner 0.3.90 Apply Work Directory Cleanup Notes

Runner `0.3.90` adds the `applyPackageWorkDirCleanup` feature flag. Package `dryRun` and `apply` now remove their temporary apply work directory in a `finally` block by default, including validation-error and post-extraction failure paths.

Set `keepWorkDir: true` only for target-local diagnostics when the extracted package work files must be inspected. Default responses annotate cleanup with `keepWorkDir: false`, `workDirKept: false`, `workDirCleaned: true`, and `workDirCleanupStatus: "cleaned"`. Diagnostic keep responses annotate `keepWorkDir: true`, `workDirKept: true`, `workDirCleaned: false`, and `workDirCleanupStatus: "kept"`. Cleanup failures keep the primary result shape and add `workDirCleanupStatus: "failed"` plus `workDirCleanupError`.

## Runner 0.3.89 Environment Path Override Notes

Runner `0.3.89` adds the `environmentPathOverrides` feature flag and makes both active runner variants honor the same path environment variables.

Path precedence is:

- `gatewayDataDir`: `IGNITION_LLM_GATEWAY_DATA_DIR`, then Gateway context discovery, then `ignition.home/data`, then `IGNITION_HOME/data`, then empty string if unavailable.
- `projectsRoot`: `IGNITION_LLM_PROJECTS_ROOT`, else `<gatewayDataDir>/projects` when `gatewayDataDir` is available.
- `runnerRoot`: `IGNITION_LLM_RUNNER_ROOT`, else `<gatewayDataDir>/llm-runner` when `gatewayDataDir` is available.
- `inboxDir`: `IGNITION_LLM_RUNNER_INBOX`, else `<runnerRoot>/inbox` when `runnerRoot` is available.
- `workDir`: `IGNITION_LLM_RUNNER_WORK`, else `<runnerRoot>/work` when `runnerRoot` is available.
- `backupDir`: `IGNITION_LLM_RUNNER_BACKUPS`, else `<runnerRoot>/backups` when `runnerRoot` is available.

`gatewayInfo.environment` reports `_configured` booleans for all six path override variables without exposing raw environment values. `health` reports resolved `projectsRootConfigured`, `inboxConfigured`, `workConfigured`, and `backupConfigured` booleans alongside the resolved paths and existence checks. Gateway service environment changes generally require restarting the Gateway process before the runner can read them.

## Runner 0.3.88 Project Scan Failure Recovery Notes

Runner `0.3.88` adds the `projectScanFailureIsFailure` feature flag.

Ignition `system.project.requestScan([timeout])` blocks until the project scan completes or times out. For post-write runner mutations, `scanCompleted` is therefore the authoritative completion field. The legacy `scanRequested` field is retained as a compatibility alias and is true only when the scan call returns successfully. Runner `0.3.136+` attempts two bounded waits after `filesChanged:true` to avoid treating an older overlapping scan as the only wait.

For `apply`, confirmed `projectResourceImportZip`, confirmed `rollback`, and confirmed `runnerSelfUpdate`, a scan exception after files changed returns a real mutation failure:

```json
{
  "ok": false,
  "statusCode": 500,
  "errorCode": "PROJECT_SCAN_FAILED",
  "filesChanged": true,
  "scanRequested": false,
  "scanCompleted": false,
  "recoveryRequired": true,
  "scanError": "<exception text>"
}
```

Treat `recoveryRequired: true` as a stop condition. Inspect `scanError`, use the reported backup metadata and `backupList`/`rollback` planning, and verify Designer/Gateway project state before relying on the changed resources. Dry-runs and no-write project-resource imports report `filesChanged: false` and do not escalate scan errors to recovery failures.

## Runner 0.3.87 Project Resource Attribute Preservation Notes

Runner `0.3.87` adds the `projectResourceAttributePreservation` feature flag.

When runner-managed writes stamp a project resource `resource.json`, the runner now preserves existing `attributes` keys and replaces only Ignition's automatic `lastModification` and `lastModificationSignature` entries. This applies to Perspective view resources, Project Library script resources, page-config resources, and the Web Dev runner resource touched by `runnerSelfUpdate`.

If an existing `attributes` value is missing or malformed, the runner normalizes it to an object before writing the automatic last-modification fields.

Named Query resources, `projectResourceImportZip`, and `rollback` remain exact-file paths: Named Query package copies preserve package `resource.json` metadata, import-zip writes the ZIP entry contents, and rollback restores or removes the files recorded in the selected backup manifest.

## Runner 0.3.86 Atomic Project Resource File Writes Notes

Runner `0.3.86` adds the `atomicProjectResourceFileWrites` feature flag.

Final project-resource file writes and file copies produced by `apply`, `projectResourceImportZip`, file-change rollback, and `runnerSelfUpdate` are staged to sibling temporary paths and committed with Java NIO `ATOMIC_MOVE` plus `REPLACE_EXISTING`. If the atomic move is unavailable or fails, the mutation fails instead of falling back to a direct non-atomic overwrite of the final file path.

Legacy directory restore/copy paths stage the source tree to a sibling temporary directory before replacing the final directory. This reduces partial final trees during legacy rollback, but it is not a full multi-file transactional rollback guarantee.

## Runner 0.3.85 Mutation Locking Notes

Runner `0.3.85` adds the `mutationLocking` feature flag and one Gateway-wide non-blocking mutation lock backed by `system.util.getGlobals()` and `java.util.concurrent.locks.ReentrantLock`.

The lock covers package `dryRun`, `apply`, `projectResourceImportZip` including its dry-run path, `rollback`, and `runnerSelfUpdate` at the action boundary. Confirmed rollback and self-update writes still require their exact confirmation strings.

If the lock is already held, the runner returns a clear busy response with `errorCode: "MUTATION_LOCK_BUSY"`, `mutationLockBusy: true`, `busy: true`, `retryable: true`, `retryAfterMs: 1000`, `lockName: "gatewayMutationLock"`, and `statusCode: 409`. Clients should back off, re-run discovery if state may have changed, and retry the dry-run before any later write.

## Runner 0.3.84 Backup/Rollback Notes

Runner `0.3.84` adds the `rollbackFileChangeManifest` feature flag and a unified `fileChanges-v1` backup manifest for mutating file writes from `apply`, `projectResourceImportZip`, and `runnerSelfUpdate`.

Each file-change manifest entry records the project-relative target path, whether it existed before the mutation, the backup file path when applicable, and before/after SHA-256 values. Rollback dry-run reports `backupFormat`, `fileChangeCount`, `existingFileCount`, `newFileCount`, `restoredFiles`, `removedFiles`, `missingBackupFiles`, and `skippedMissingNewFiles`. Rollback apply restores files that existed before the selected backup and removes files that the same backup recorded as newly created, then runs the post-write project scan sequence and reports scan fields.

`backupList` entries can now include `backupFormat`, file-change counts, and sample target paths. Runner `0.3.104+` current `runnerSelfUpdate` backups are exact-source rollback backups for `doPost.py`; protect backup folders like runner source if static token assignments are present.

## Runner 0.3.81 Gateway Network Preflight Notes

Runner `0.3.81` adds read-only `gatewayNetworkPreflight` for Gateway Network and remote alarming preparation. It does not mutate Gateway Network topology, security zones, service security, alarm pipelines, tags, projects, or notification profiles.

Useful request fields:

- `includeRawGatewayNames`: default `false`. When false, gateway names are represented by stable tokens in the response.
- `confirmSensitiveDiagnostic`: must be `INCLUDE_GATEWAY_NETWORK_NAMES` when `includeRawGatewayNames` is true.
- `maxMethodNames`: optional method-surface cap from `20` through `250`; default `120`.
- `maxSampleMethods`: optional zero-argument getter sample cap from `5` through `80`; default `40`.
- `maxPipelines`: optional alarm pipeline token cap from `0` through `500`; default `100`.

Expected response fields include `gatewayIdentity`, `methodSurfaces`, `managerSurfaces`, `remotePeerEvidence`, `securityZoneEvidence`, `serviceSecurityEvidence`, `remoteNotificationProfileEvidence`, `alarmNotificationModuleEvidence`, `alarmPipelineEvidence`, and `sensitiveFields`.

The action tokenizes gateway names and sampled connection/profile/pipeline text by default and redacts diagnostic errors. It returns surface counts, sampled getter status, value tokens, module matches, and booleans such as `defaultZoneMentioned`; it does not return raw peer addresses, URLs, JDBC strings, tokens, passwords, or connection text. A single-Gateway preflight can prove available methods and local module/pipeline evidence, but it cannot prove remote alarm delivery, remote acknowledgement, remote shelving, or two-Gateway routing. Treat those as separate live integration tests.

## Runner 0.3.80 Alarm Status Include Shelved Notes

Runner `0.3.80` adds read-only `includeShelved` support to `alarmStatusQuery`. When omitted, the runner preserves the prior request shape and does not send the argument to Ignition. When set to `true` or `false`, it passes the boolean through to `system.alarm.queryStatus(includeShelved=...)` and echoes `includeShelved` in the response.

## Runner 0.3.79 Perspective Performance Diagnostics Notes

Runner `0.3.78` introduced these read-only Perspective performance diagnostics for profiling workflows. Runner `0.3.79` added early direct-paste metric diagnostic fixes, but runner `0.3.129` is the first version whose `metricsSnapshot.sequence` uses Gateway JVM globals for monotonic direct-paste Web Dev request behavior. Runner `0.3.80` keeps those diagnostics and adds `alarmStatusQuery.includeShelved`.

- `metricsList`
- `metricsSnapshot`
- `gatewayPerformanceSnapshot`
- `perspectiveSessionsQuery`
- `threadDumpQuery`

These actions are discovery and evidence actions only. They do not write project resources, tags, scripts, sessions, or Gateway settings. Metric names, session identifiers, client addresses, and thread dump text are redacted or tokenized by default. Request raw identifiers only when target-local evidence requires them, and keep them out of reusable skill documentation.

## Runner 0.3.77 Tag Configure Notes

Runner `0.3.77` extends guarded `tagConfigure` validation to allow AtomicTag and UDT member `valueSource: "derived"` alongside the existing memory, expression, and Reference tag support. The runner still blocks OPC tag configuration and event-script injection through `tagConfigure`. `health.features` includes `derivedTagConfigure` when this contract is active.

## Runner 0.3.76 Project Resource Import Notes

Runner `0.3.76` adds `projectResourceImportZip`, a guarded project-resource ZIP import action. It is intended for already-valid Ignition 8 project-resource packages or resource-directory exports, not for generating Vision binaries or converting legacy `.proj` files.

Useful request fields:

- `targetProject`: exact project name returned by `projectsList`.
- `packageBase64`: ZIP payload. The runner redacts this field in bundled test evidence.
- `allowedResourcePrefix`: project-resource allowlist; default and recommended value for Vision work is `com.inductiveautomation.vision`.
- `resourcePath`: optional target resource directory for resource-relative ZIPs such as `projectResourceExport` output. Omit this for project-relative packages that already contain paths like `com.inductiveautomation.vision/templates/...`.
- `dryRun`: default `true`; no files are written in dry-run mode.
- `mode`: optional `dryRun` or `apply` alias for `dryRun`.
- `confirmProjectResourceImport`: must be `IMPORT_PROJECT_RESOURCE_ZIP` for apply.
- `overwriteExisting`: default `false`; exact-hash matches are reported as `same`, differing existing files are conflicts.
- `confirmOverwrite`: must be `OVERWRITE_PROJECT_RESOURCES` when `overwriteExisting` is true.
- `ignoreProjectJson`: default `true`; root `project.json` is ignored so a package can import resource files without replacing project metadata.
- `maxFiles`: integer from `1` through `2000`; default `200`.
- `maxBytes`: integer from `1` through `26214400`; default `5242880`.
- `scanTimeoutSeconds`: integer from `1` through `30`; default `10` on runner `0.3.105+`.

Expected response fields include `fileCount`, `totalBytes`, `resourcePaths`, `entries[]`, `writeCount`, `sameCount`, `conflictCount`, `overwriteCount`, `packageSha256`, `filesChanged`, `scanCompleted`, `recoveryRequired`, and, on apply with writes, `written`, `writtenCount`, legacy `scanRequested`, `scanWaitsAttempted`, `scanWaitsCompleted`, `defensiveSecondScanWait`, `backupName`, `backupFormat`, `fileChangeCount`, `existingFileCount`, and `newFileCount`.

The action rejects missing packages, invalid base64, traversal entries, colon/absolute paths, entries outside `allowedResourcePrefix`, packages without any importable resource files, and resource directories that lack `resource.json` unless that resource already exists in the target project. A successful import proves only that the resource files were written and scanned. It does not prove that a Vision window/template opens, renders, or behaves correctly.

## Runner 0.3.75 Project Info Read Notes

Runner `0.3.75` adds `projectInfoRead`, a read-only action for one project-level metadata snapshot. Use it after `projectsList` and before resource-level scans when you need the exact project directory name, `project.json` hash/parsed metadata, and module-root presence flags.

Useful request fields:

- `targetProject`: exact project name returned by `projectsList`.
- `includeProjectJson`: parse and return `project.json` when true; default `true`.
- `includeModuleRoots`: return capped module root entries when true; default `true`.
- `maxProjectJsonChars`: cap for parsed project JSON text; default `12000`, maximum `60000`.
- `maxModuleRoots`: integer from `1` through `200`; default `50`.

Expected response fields include `projectName`, `projectDirectoryName`, `hasProjectJson`, `projectJsonBytes`, `projectJsonSha256`, optional `projectJson`, `hasVisionResources`, `hasPerspectiveResources`, `hasWebDevResources`, `moduleRoots`, `moduleRootCount`, and `moduleRootsTruncated`.

Treat `projectInfoRead` as structural project metadata only. It does not prove Vision client runtime behavior, component state, event execution, or window navigation.

## Runner 0.3.74 Project Resource Export Notes

Runner `0.3.74` adds `projectResourceExport`, a read-only action that creates a bounded ZIP for one existing project resource directory. It uses the same `targetProject`, `resourcePath`, and `allowedResourcePrefix` guard model as `projectResourceRead`.

Useful request fields:

- `includePackageBase64`: include the ZIP payload in the response when true.
- `maxFiles`: integer from `1` through `2000`; default `200`.
- `maxBytes`: integer from `1` through `26214400`; default `5242880`.

Expected response fields include `fileCount`, `totalBytes`, `zipBytes`, `zipSha256`, and per-file `relativePath`, `bytes`, and `sha256`. Treat this as structural export evidence only; it does not prove Vision client runtime behavior or resource import compatibility.

## Runner 0.3.73 Project Inventory Notes

Runner `0.3.73` refines `projectsList` with `projectsListProjectJsonFilter`. It returns only hidden-free project directories that contain `project.json`, so system folders under the projects root are not scanned as projects. Each returned item includes:

- `projectName`
- `hasProjectJson`
- `hasVisionResources`
- `hasPerspectiveResources`
- `hasWebDevResources`
- `lastModifiedEpochMillis`

Use exact returned project names for subsequent project-scoped actions. `maxResults` must be an integer from `1` through `1000` when supplied.

## Runner 0.3.72 Project Inventory Notes

Runner `0.3.72` added the first `projectsList` read-only action for project discovery. Prefer `0.3.73+` because it excludes hidden/system folders and non-project directories before downstream resource scans.

## Runner 0.3.71 Request Body Size Notes

Runner `0.3.71` adds `requestBodySizeValidation`. The runner rejects request bodies larger than `41943040` bytes before action dispatch when `Content-Length` or raw `data`/`postData` length is visible to the Web Dev resource. Oversized requests return a normal JSON validation failure with an error beginning `Request body exceeds max size`.

The limit is intentionally above the supported `packageBase64` path for a 25 MB zip payload after base64 expansion. Treat this as a runner safety guard, not as a promise that every Gateway, proxy, or client will accept bodies up to that size.

## Runner 0.3.70 Project Resource Validation Notes

Runner `0.3.70` adds `projectResourcesListMaxResultsValidation`. `projectResourcesList.maxResults` must be an integer from `1` through `1000` when supplied. Invalid non-integer or out-of-range values return a normal JSON validation error instead of silently defaulting to the standard result cap.

## Runner 0.3.69 Request JSON Notes

Runner `0.3.69` requires an explicit `action` field in every request. It also rejects malformed JSON request bodies, non-object JSON bodies, and non-empty bodies that Ignition cannot expose as a parsed non-empty object before action dispatch. The canonical response is `ok: false` with HTTP 400 and an error beginning with `action is required`, `Malformed JSON request body`, or `JSON request body must be an object`. Send an explicit object with `action`; do not rely on `{}` or an empty body as a health alias.

## Runner 0.3.65 Project Resource Notes

Runner `0.3.65` adds read-only `projectResourcesList` and `projectResourceRead` for bounded project resource inspection. The default `allowedResourcePrefix` is `com.inductiveautomation.vision/`, so Vision resources can be discovered without using arbitrary `scriptEval`.

These actions are metadata/readback helpers only. They do not create, modify, delete, import, export, or synthesize Vision windows/templates. Binary files such as Vision `data.bin` are returned by size and hash only; text payloads are limited to known text file names and capped by `maxTextChars`.

## Runner 0.3.64 Named Query SQL Scanner Notes

Runner `0.3.64` makes the Named Query preview/package SQL scanner quote/comment-aware. It strips comments only outside quoted strings, ignores semicolons and SQL-looking keywords inside string literals, strips literals before stacked-statement and limit detection, and validates packaged `Query`/`ScalarQuery` dependency SQL for read-only preview eligibility during package `dryRun`/`apply`.

Validated behavior: CTE/`WITH` queries, SQL-looking line comments, SQL-looking string literals, and a single trailing statement semicolon were preview-eligible on the tested SQLite target. Semicolon-chained packaged `Query` SQL was rejected during package `dryRun` with a read-only preview eligibility error before execution. Treat this as runner-side safety classification; database execution and driver-specific syntax remain target-dependent.

## Runner 0.3.63 Database Connection Inventory Notes

Runner `0.3.63` adds the read-only `databaseConnectionsList` action, backed by Ignition's Gateway-scope `system.db.getConnections()` dataset. Use it before PostgreSQL historian work, non-SQLite driver tests, generated-key or transaction checks, DateTime driver behavior checks, or Database-parameter diagnostics.

The action returns capped connection metadata: total count, returned count, truncation flag, dataset columns, database type counts, status counts, and per-connection name, description, database type, status, and `problemPresent`. `includeProblem` defaults to `false`; set it only when problem text is needed for target-local diagnostics. Treat returned connection names and problem text as evidence, not reusable product examples.

## Runner 0.3.62 Named Query Raw Resource Notes

Runner `0.3.62` adds `namedQueryRead includeResourceJson` so callers can copy a raw Named Query `resource.json` when building packages. Validated behavior showed a reconstructed Named Query resource can pass package dry-run, apply, `pageValidate`, `viewRead`, and copied `namedQueryRead` while failing copied `namedQueryPreview` at runtime. Copying the raw `resource.json` returned by `namedQueryRead` with `includeResourceJson: true`, alongside `query.sql`, fixed the copied-query runtime preview on the tested target. Treat `pageValidate` as structural; use copied `namedQueryPreview` after apply before claiming query runtime success.

## Runner 0.3.61 LogQuery Rotated Notes

Runner `0.3.61` added `logQuery` rotated-wrapper support through `includeRotated: true`, `maxLogFiles`, `sourceFiles`, per-entry `sourceFileName`, and a total-tail-byte guard.

Validated behavior found `wrapper.log` plus numeric rotations, returned parsed primary matches from each available numeric rotation, rejected an unconfirmed broad rotated query, and rejected an oversized rotated scan when `tailBytes * sourceFileCount` exceeded `maxTotalTailBytes`. This confirms bounded runner API access to numeric wrapper-log siblings on the tested Gateway. It does not confirm Gateway Diagnostic Logs export parsing, every OS log path, or rotated-file presence on every target.

## Runner 0.3.60 Alarm Journal Query Notes

Runner `0.3.60` added read-only `alarmJournalQuery` for bounded historical alarm-journal context.

Validated behavior rejected missing journal/default opt-in, broad scans without `ALLOW_BROAD_ALARM_JOURNAL_QUERY`, invalid journal states, and oversized ranges. The original 0.3.60 live proof showed omitted-profile behavior on one local target, but runner `0.3.97+` supersedes that request shape with an explicit-profile requirement because the runner cannot verify the official single-journal condition safely. Runner `0.3.96+` supersedes the broad-scan bypass behavior: broad confirmations are removed, provider/state/priority/system filters are supplemental only, and callers must provide a narrow source/path/displayPath plus a `<= 1440` minute range before execution.

## Runner 0.3.59 Audit Query Notes

Runner `0.3.58` added read-only `auditQuery`; runner `0.3.59` briefly exposed configured-default mode through `useDefaultProfile: true`. Runner `0.3.82` rejects `useDefaultProfile` in WebDev/Gateway scope because Ignition 8.1 Gateway-scope `system.util.queryAuditLog` requires an explicit `auditProfileName`.

Validated behavior for `0.3.82` must reject missing/default audit profiles before calling Ignition, reject broad scans without `ALLOW_BROAD_AUDIT_QUERY`, and reject string `contextFilter` values. Callers should provide exact discovered profile names through `profile`, `auditProfileName`, or `profiles`. Runner `0.3.96+` supersedes the broad-scan bypass behavior: broad confirmations are removed, `contextFilter` alone is not a backend bound, and callers must provide a narrow actor/action/target/value/system filter plus a `<= 1440` minute range before execution.

## Runner 0.3.57 Tag Event Success Marker Notes

Runner `0.3.57` adds `tagEventScriptProbe emitSuccessMarkers` and exposes `tagEventScriptProbeSuccessMarkers` in `health.features`.

Validated behavior created fixed absolute and relative `valueChanged` tag-event fixtures under `[default]LLM Tests/...`. With `emitSuccessMarkers: true` and a unique `successMarker`, each fixture emitted a primary `system.util.getLogger("LLM.TagEventProbe").info(...)` wrapper entry and a non-primary bare `print` wrapper line after result-tag writes returned good quality. This confirms only the approved fixed fixture, not arbitrary/manual tag-event scripts.

## Runner 0.3.56 LogQuery Non-Primary Notes

Runner `0.3.56` adds `logQuery includeNonPrimary` and exposes `logQueryNonPrimaryLines` in `health.features`.

Validated behavior captured Web Dev/Gateway bare `print` output and Perspective session `system.perspective.print(destination="gateway")` output as non-primary wrapper entries. Normal `logQuery` behavior remains unchanged unless `includeNonPrimary: true` is set.

## Runner 0.3.55 GatewayInfo Module Version Notes

Runner `0.3.55` enriches `gatewayInfo.modules.modules[]` with `moduleName`, `moduleVersion`, `moduleState`, and `moduleLicenseStatus` from the documented Gateway-scope `system.util.getModules` dataset.

Validated behavior returned rows from `system.util.getModules` with columns `Id`, `Name`, `Version`, `State`, and `Status`; module IDs matched the lower-level module-manager IDs in `gatewayInfo`, and the final `gatewayInfo` response returned `moduleVersion` values.

## Runner 0.3.52 Named Query Dependency Notes

Runner `0.3.52` adds guarded package/apply/pageValidate handling for explicit Named Query dependencies.

The runner accepts `dependencyNamedQueryPaths` under the allowed Named Query prefix, validates packaged `ignition/named-query/<queryPath>/resource.json` plus `query.sql`, copies only those files, backs them up, restores them through rollback, and checks them through `pageValidate`. Named Query `resource.json` attributes are preserved as packaged because they contain query type, database, enabled state, files, and parameter metadata.

## Runner 0.3.54 Named Query Unsafe Parameter Notes

Runner `0.3.54` adds controlled unsafe-parameter allowlists for QueryString/Database Named Query diagnostics and package validation.

For `namedQueryPreview`, QueryString and Database params still reject by default. To run a controlled read-only QueryString preview, pass `allowQueryStringParameters: true` and `queryStringParameterAllowlist` keyed by parameter name. To test a Database parameter, pass `allowDatabaseParameters: true` and `databaseParameterAllowlist`. Non-allowlisted values fail before execution. Java-backed execution failures now return a normal JSON error envelope with `ok: false`, HTTP 400, `requestId`, and runner/stack versions instead of leaking HTTP 500.

For package dry-run/apply, QueryString/Database Named Query dependencies reject by default. The explicit override requires all three fields: `allowUnsafeNamedQueryParameters: true`, `unsafeNamedQueryParameterPaths: ["<queryPath>"]`, and `confirmUnsafeNamedQueryParameters: "ALLOW_UNSAFE_NAMED_QUERY_PARAMETERS"`. Override paths must also appear in `dependencyNamedQueryPaths`, and unsafe params may be allowed only on read-only query types. Validation executed an allowlisted QueryString column fragment successfully; Database `<Parameter>` metadata and rejection/error handling were confirmed. A follow-up package with `attributes.database: "<Parameter>"` and no manual `parameters` entry still made `system.db.runNamedQuery(..., {"database": "<connection>"})` look for a literal `<Parameter>` connection, so successful dynamic Database execution remains target-specific and unproven through package copy.

## Runner 0.3.52 Drift And Route Conflict Notes

For `viewDriftGuard` and `routeConflictDetails`, missing, wrong, and stale `expectedViewSha256ByViewPath` values failed dry-run before writes; a correct current hash allowed dry-run/apply and returned `checkedViewHashes`. Route-conflict dry-runs returned `routeConflicts[].packageRoute`, `targetRoute`, `willOverwrite`, and `resolutionOptions`; the intentional `allowOverwrite: true` case was verified as a dry-run before any apply.

## Reviewed Behavior Notes

Runner `0.3.50` completed a feature-by-feature behavior review. The run started with `health`, verified the stack, ran the local active-source harness against both runner variants, then exercised live API writes with dry-run/apply/rollback and exact confirmations.

The review covered these API bugfixes and decisions:

| Feature | Behavior shape |
|---|---|
| Strict `logQuery.sinceMinutes` validation | Live API rejects text, negative, and oversized values as JSON validation errors. |
| Script rollback support | Live package apply plus rollback dry-run/apply returns `restoredScripts`, `removedScripts`, and `missingBackupScripts`. |
| Correct zip directory detection | Local harness extracts extensionless `LICENSE`; live valid package includes extensionless `LICENSE` and `README`. |
| Clean route validation errors | Live dry-run rejects a route outside the allowlist as a normal JSON error. |
| Header version alignment | Live `health` and local source assertions match runner/stack markers. |
| Parseable log timestamps and binary-safe log tails | Local harness checks timestamp filtering and binary tail behavior; live valid `logQuery` passes. |
| Zip decompression limits | Local harness lowers the extracted-byte cap and verifies extraction fails safely. |
| Correct `packageSource` labeling | Local `None` normalization passes; live dry-run/apply with base64 reports `packageBase64`. |
| SQL preview keyword scanner | Local scanner allows `REPLACE(...)`, rejects `REPLACE INTO`, and ignores keywords inside string literals. |
| UDT helper cleanup | Local source assertions verify the dead branch and `request_payload` shadowing are absent. |
| Token env precedence and constant-time compare | Local source assertions verify env-token precedence and `MessageDigest.isEqual` usage. |
| Exact self-update backups | Local and live `runnerSelfUpdate` evidence report `backupExactSource: true` and `backupTokenRedacted: false`; rollback restores the recorded `doPost.py` source exactly. |
| Clean package extraction errors | Live dry-run with a traversal zip returns `Package extraction failed: Unsafe zip entry...`. |
| `scriptEval` guardrail | Live execution without `confirmScriptEval` is rejected; bounded confirmed diagnostics execute. |
| `queryStatus(provider=...)` decision | Live `alarmStatusQuery` with provider succeeds; Ignition 8.1 docs list optional `provider`. |
| Bounded `requestScan` timeout decision | Runner `0.3.105+` validates `scanTimeoutSeconds` as `1..30`, default `10`, and echoes the effective value when a scan is attempted. |

## Write Confirmations

| Action | Dry-run field | Confirmation field | Confirmation value |
|---|---|---|---|
| `apply` | `action: "dryRun"` or `dryRun: true` | `confirmApply` | `APPLY` |
| `tagConfigure` | `dryRun: true` | `confirmTagConfigure` | `CONFIGURE_TAGS` |
| `tagEventScriptProbe` | `dryRun: true` | `confirmTagEventScriptProbe` | `CREATE_TAG_EVENT_PROBE` |
| `udtTagEventScriptProbe` | `dryRun: true` | `confirmUdtTagEventScriptProbe` | `CREATE_UDT_TAG_EVENT_PROBE` |
| `udtScaffold` | `dryRun: true` | `confirmUdtScaffold` | `SCAFFOLD_UDT` |
| `scriptEval` | `dryRun: true` | `confirmScriptEval` | `RUN_JYTHON_EVAL` |
| `rollback` | `dryRun: true` | `confirmRollback` | `ROLLBACK` |
| `runnerSelfUpdate` | `dryRun: true` | `confirmSelfUpdate` | `UPDATE_RUNNER` |

Runner `0.3.118+` also accepts `forceDriftedRollback: "FORCE_ROLLBACK_DRIFT"` only when intentionally overriding a `ROLLBACK_DRIFT_DETECTED` `fileChanges-v1` rollback guard. Use it with `confirmRollback: "ROLLBACK"` on confirmed apply, never as a default rollback field.

Do not use rollback to delete unrelated resources. On runner `0.3.84+`, `fileChanges-v1` rollback removes only files that the selected backup recorded as newly created. Legacy `removeMissingViews`, `removeMissingScripts`, and `removeMissingNamedQueries` remain explicit deletion controls.

On runner `0.3.85+`, package `dryRun`, `apply`, `projectResourceImportZip`, `rollback`, and `runnerSelfUpdate` are serialized by the Gateway-wide mutation lock. On runner `0.3.114+`, confirmed `tagConfigure`, `tagEventScriptProbe`, `udtTagEventScriptProbe`, and `udtScaffold` calls share that lock too; their dry-runs remain non-blocking. Treat `MUTATION_LOCK_BUSY` as a retryable state, not as rollback/apply evidence.

On runner `0.3.86+`, final project-resource file writes and file copies are staged to sibling temporary paths before the final Java NIO atomic move. Treat atomic-move failures as mutation failures; do not retry by writing directly to final resource files.

On runner `0.3.87+`, runner-managed resource stamping preserves existing `resource.json` `attributes` keys and replaces only `lastModification` and `lastModificationSignature`.

## Package Actions: `dryRun` And `apply`

Use these for Perspective package validation and import.

Minimum payload:

```json
{
  "action": "dryRun",
  "requestId": "PKG-001",
  "targetProject": "samplequickstart",
  "packageName": "llm-page.zip",
  "packageBase64": "<base64 zip>",
  "allowedViewPrefix": "LLM Tests/",
  "allowedRoutePrefix": "/llm-",
  "routes": [
    {
      "pagePath": "/llm-example",
      "viewPath": "LLM Tests/Example",
      "title": "Example"
    }
  ],
  "dependencyViewPaths": [],
  "dependencyScriptPaths": [],
  "dependencyNamedQueryPaths": [],
  "allowUnsafeNamedQueryParameters": false,
  "unsafeNamedQueryParameterPaths": [],
  "sharedDockKeys": [],
  "keepWorkDir": false,
  "scanTimeoutSeconds": 10
}
```

Apply payload:

```json
{
  "action": "apply",
  "requestId": "PKG-002",
  "targetProject": "samplequickstart",
  "packageName": "llm-page.zip",
  "packageBase64": "<base64 zip>",
  "allowedViewPrefix": "LLM Tests/",
  "allowedRoutePrefix": "/llm-",
  "routes": [
    {
      "pagePath": "/llm-example",
      "viewPath": "LLM Tests/Example",
      "title": "Example"
    }
  ],
  "dependencyViewPaths": [],
  "dependencyScriptPaths": [],
  "dependencyNamedQueryPaths": [],
  "allowUnsafeNamedQueryParameters": false,
  "unsafeNamedQueryParameterPaths": [],
  "sharedDockKeys": [],
  "keepWorkDir": false,
  "scanTimeoutSeconds": 10,
  "confirmApply": "APPLY"
}
```

Important fields:

- `packageBase64`: preferred transfer path. In `0.3.50+`, `null` is treated as empty and `packageSource` reports `inbox`.
- `packageName`: optional simple safe zip name; defaults to `llm-perspective-package.zip` when omitted.
- `allowedViewPrefix`: default `LLM Tests/`.
- `allowedRoutePrefix`: default `/llm-`.
- `allowedScriptPrefix`: default `llm`.
- `allowedNamedQueryPrefix`: default `LLM Tests/`.
- Runner `0.3.98+` applies exact-or-child prefix matching for these logical paths. `LLM Tests/A` allows `LLM Tests/A` and `LLM Tests/A/Child`, not `LLM Tests/ABC`; `/llm-` remains a route namespace for `/llm-...` pages, and root-level `llm...` Project Library script modules remain allowed by the default script prefix.
- `allowOverwrite`: permits route/view overwrite only after validation.
- `requireViewSha256ForOverwrite`, `expectedViewSha256`, `expectedViewSha256ByViewPath`: use for drift guards.
- `dependencyViewPaths` or `extraViewPaths`: extra packaged views required by the page.
- `dependencyScriptPaths` or `extraScriptPaths`: Project Library scripts under `ignition/script-python`.
- `dependencyNamedQueryPaths` or `extraNamedQueryPaths`: packaged Named Queries under `ignition/named-query`; each path must stay under `allowedNamedQueryPrefix`.
- `allowUnsafeNamedQueryParameters`, `unsafeNamedQueryParameterPaths`, `confirmUnsafeNamedQueryParameters`: `0.3.54+` explicit override for packaged QueryString/Database params. Keep default false unless a tested read-only fixture has exact allowlists.
- `sharedDockKeys`: optional allowlist of top-level Perspective `sharedDocks` keys to merge from the package page-config. Allowed values are `top`, `bottom`, `left`, `right`, and `cornerPriority`.
- `keepWorkDir`: optional diagnostic flag. Default false removes temporary package apply work directories after `dryRun` and `apply`; set true only when target-local extraction artifacts must be inspected.
- `scanTimeoutSeconds`: optional post-write project scan timeout. Runner `0.3.105+` accepts integers `1..30`, default `10`, and validates the field in dry-run even though dry-run does not call `requestScan`.

Dynamic route pages use the route key in package and validation requests, for example `/llm-equipment/:assetId`. The primary view must declare the matching input param such as `params.assetId`; overview buttons should navigate to concrete page URLs such as `/llm-equipment/PMP-001`. Validate the dynamic key with `pageValidate`, then browser-open at least one concrete URL.

For shared docked navigation shells, put shared dock definitions under top-level page-config `sharedDocks`, not inside a single route. Pass `sharedDockKeys` so the runner merges only the requested shared dock edges and preserves other existing shared dock settings. The runner validates each requested shared dock key, validates each shared dock `viewPath` against `allowedViewPrefix`, copies those dock views as package dependencies, and reports `sharedDockViewPaths` plus `mergedSharedDockKeys`.

For Named Query dependencies, package `resource.json` and `query.sql` under `ignition/named-query/<queryPath>/` and list the query path in `dependencyNamedQueryPaths`. The runner rejects paths outside `allowedNamedQueryPrefix`, rejects unsafe `QueryString` and `Database` params for package-managed dependencies unless the `0.3.54+` unsafe-param override is explicit, and preserves the Named Query `resource.json` attributes instead of rewriting them with the generic project-resource helper. On runner `0.3.62+`, use `namedQueryRead` with `includeResourceJson: true` and copy the returned raw resource when cloning an existing target Named Query; do not reconstruct the resource from summary metadata when runtime preview matters.

`0.3.49` through `0.3.56` package hardening:

- Route validation returns normal JSON errors instead of unhandled exceptions.
- Zip directories are detected only by explicit directory entries or trailing `/`, preserving extensionless files.
- Compressed zip size, decompressed byte count, and entry count are capped during extraction.
- Extraction failures return `Package extraction failed: ...` JSON errors.
- Page config routes must use `viewPath`, not `view`.
- Project resource JSON is BOM-normalized before parsing.
- Shared dock merges require package page-config when `sharedDockKeys` is supplied and reject unsupported keys before writes.
- Named Query dependency copies preserve query metadata and report `validatedNamedQueries`, `dependencyNamedQueryPaths`, and `copiedNamedQueries`.
- QueryString/Database Named Query dependencies require explicit unsafe-param allowlists, and preview execution failures return JSON error envelopes.

`0.3.90+` package `dryRun` and `apply` responses include temporary work-directory cleanup metadata: `keepWorkDir`, `workDirKept`, `workDirCleaned`, and `workDirCleanupStatus`. Cleanup errors also include `workDirCleanupError`.

`0.3.91+` generated backup/work names include a short UUID suffix after the timestamp. Treat `backupName`, `backupDir`, and temporary work paths as opaque response values instead of reconstructing timestamp-only names.

`0.3.105+` package `apply` accepts `scanTimeoutSeconds` for the post-write project scan. The effective timeout is echoed in scan responses; scan failure after changed files still returns `PROJECT_SCAN_FAILED` with `recoveryRequired: true`.

`0.3.115+` package `apply` returns `MID_WRITE_FAILURE` with `writeFailure`, `backupName`, `failedStage`, `writesStarted`, `writtenPaths`, `recoveryRequired`, and `rollbackAvailable` metadata when an exception occurs after backup planning or after any package file copy/merge starts.

## `rollback`

Use rollback to restore a runner backup created by `apply`, `projectResourceImportZip`, `runnerSelfUpdate`, or rollback itself.

Dry-run:

```json
{
  "action": "rollback",
  "requestId": "RB-001",
  "targetProject": "samplequickstart",
  "backupName": "samplequickstart-20260612-181100-653",
  "viewPaths": ["LLM Tests/Example"],
  "scriptPaths": ["llm/example"],
  "namedQueryPaths": ["LLM Tests/Example/InsertActionLog"],
  "dryRun": true
}
```

Apply:

```json
{
  "action": "rollback",
  "requestId": "RB-002",
  "targetProject": "samplequickstart",
  "backupName": "samplequickstart-20260612-181100-653",
  "viewPaths": ["LLM Tests/Example"],
  "scriptPaths": ["llm/example"],
  "namedQueryPaths": ["LLM Tests/Example/InsertActionLog"],
  "dryRun": false,
  "scanTimeoutSeconds": 10,
  "confirmRollback": "ROLLBACK"
}
```

`0.3.49+` rollback behavior:

- Script paths can come from explicit `scriptPaths`, backup manifest `scriptPaths`, or the backup `script-python` folder.
- Responses include `restoredScripts`, `removedScripts`, and `missingBackupScripts`.
- Pre-rollback backups include selected script paths.
- `removeMissingScripts` removes target scripts missing from the backup only when explicitly requested.

`0.3.52+` rollback behavior:

- Named Query paths can come from explicit `namedQueryPaths`, backup manifest `namedQueryPaths`, or the backup `named-query` folder.
- Responses include `restoredNamedQueries`, `removedNamedQueries`, and `missingBackupNamedQueries`.
- Pre-rollback backups include selected Named Query paths.
- `removeMissingNamedQueries` removes target Named Queries missing from the backup only when explicitly requested.

`0.3.84+` rollback behavior:

- Backups with `backupFormat: "fileChanges-v1"` use the manifest instead of legacy view/script/Named Query folders.
- Dry-run reports `restoredFiles` and `removedFiles` before any write.
- Apply restores files that existed before the backup and removes files the backup recorded as new.
- Apply creates a pre-rollback `fileChanges-v1` backup of the current file state before changing files.
- A `backupName` that resolves to a single old self-update `.py` file is rejected with a clear file-backup error instead of attempting folder rollback.

`0.3.85+` rollback behavior:

- Rollback apply requests use the Gateway-wide mutation lock and return `MUTATION_LOCK_BUSY` if another runner mutation is active.
- Rollback dry-runs remain read/planning requests and do not acquire the mutation lock.

`0.3.86+` rollback behavior:

- File-change rollback restores existing files through sibling temporary files and Java NIO atomic moves.
- Legacy directory rollback stages copied trees to sibling temporary directories before replacing final directories. This is a safer restore path, not a full multi-file transaction.

`0.3.102+` rollback behavior:

- Damaged `fileChanges-v1` manifests with missing required backup files are rejected before dry-run or apply can succeed.
- Legacy `projectResourceImportZip` backup folders without `fileChanges` can restore backed-up overwritten project-resource files and report `backupFormat: "legacy-project-resource-import"`.
- Legacy import rollback reports `createdFilesNotRemoved: true` because files created by the original import cannot be inferred from those old backup folders.

`0.3.103+` rollback behavior:

- Current `runnerSelfUpdate` `fileChanges-v1` manifests include the sibling Web Dev `resource.json` touched by self-update, so rollback restores or removes that file according to the selected backup manifest.

`0.3.105+` rollback behavior:

- Confirmed rollback accepts `scanTimeoutSeconds` for the post-write project scan. The value must be an integer from `1` through `30`; default `10`.

`0.3.116+` rollback behavior:

- Confirmed `fileChanges-v1` rollback reports `removedFiles` as verified actual removals, not just planned removals.
- If a new-file rollback target or empty parent directory cannot be deleted, the response is `ok: false`, `statusCode: 500`, `errorCode: "ROLLBACK_REMOVAL_FAILED"`, and `recoveryRequired: true`.
- Failure responses include `failedRemovals`, `failedRemovalCount`, `failedPrunes`, `failedPruneCount`, actual `removedFiles`, `removedFileCount`, `prunedDirs`, `prunedDirCount`, and `preRollbackBackupDir`.
- Dry-runs still report planned `removedFiles` because no deletion is attempted.

`0.3.118+` rollback behavior:

- `fileChanges-v1` rollback checks current file existence/type/SHA-256 against manifest `afterSha256` before dry-run success or apply mutation.
- Drift returns `ok: false`, `statusCode: 409`, `errorCode: "ROLLBACK_DRIFT_DETECTED"`, `recoveryRequired:false`, `filesChanged:false`, `scanRequested:false`, `scanCompleted:false`, `preRollbackBackupCreated:false`, `driftedFiles`, and `driftedFileCount`.
- A caller can intentionally override the guard with exact token `forceDriftedRollback: "FORCE_ROLLBACK_DRIFT"` plus the normal apply confirmation; forced rollback still reports the drift set and creates a pre-rollback backup before changing files.
- Successful confirmed `apply`, `projectResourceImportZip`, and `runnerSelfUpdate` scans refresh the selected backup manifest and return `backupAfterScanRefreshed:true` when file changes were backed up, so scan-mutated `resource.json` metadata is recorded before later drift checks.

`0.3.141+` rollback behavior:

- Confirmed rollback write/restore exceptions return `ok:false`, `statusCode:500`, `errorCode:"ROLLBACK_WRITE_FAILED"`, `recoveryRequired:true`, `filesChanged`, `failedStage`, `failedPath`, `backupName`, `backupDir`, `backupFormat`, `preRollbackBackupDir`, `preRollbackBackupCreated`, `completedRestoredFiles`, `completedRemovedFiles`, `completedPrunedDirs`, and nested `rollbackFailure`.
- This envelope covers `fileChanges-v1`, legacy `projectResourceImportZip`, and classic rollback restore paths.
- `ROLLBACK_REMOVAL_FAILED` remains the specific error for verified delete/prune postcondition failures.
- When `ROLLBACK_WRITE_FAILED` appears, stop further writes and inspect the pre-rollback safety backup before attempting manual recovery.

`0.3.142+` apply stale-view pruning behavior:

- Confirmed package `apply` overwrites of runner-managed Perspective views prune stale optional managed files such as `thumbnail.png` when the package omits them and the final manifest omits them.
- Responses include `prunedStaleViewFiles` and `prunedStaleViewFileCount`; pruned files are included in file-change backup planning so rollback can restore them.
- If destination view manifest validation fails after copy/prune, the response uses the existing `MID_WRITE_FAILURE` envelope with failed stage `validateCopiedViews`.

`0.3.143+` UDT scaffold unknown-failure recovery behavior:

- Failed confirmed non-dry-run `udtScaffold` nested `tagConfigure` steps with missing, null, or empty `qualityCodes` mark all step `recoveryPaths` as unknown-mutated according to preflight.
- Recovery then attempts to delete freshly created paths or restore existing-path configurations rather than returning `writesStarted:false`.
- Dry-runs are unchanged. Non-empty mismatched QualityCodes keep the `0.3.138+` any-Good rule, and equal-length failed steps keep index-based marking.

`0.3.144+` unfinished file-change backup rollback behavior:

- Initial `fileChanges-v1` manifests written before `apply`, `projectResourceImportZip`, or `runnerSelfUpdate` finishes are marked `afterStateKnown:false`, `backupManifestComplete:false`, and `rollbackDriftCheckMode:"unknown-after-state"`.
- Rollback of those unfinished backups reports `driftCheckSkipped:true` and skips strict `afterSha256` drift blocking because `afterSha256:null` means unknown after-state, not expected missing.
- Completed backups remain strict and still return `ROLLBACK_DRIFT_DETECTED` when current files drift from their finalized `afterSha256` state.

`0.3.145+` apply non-view final-state validation behavior:

- Confirmed package `apply` validates final destination Project Library script, Named Query, and Perspective page-config resource state after `copyScripts`, `copyNamedQueries`, and `mergePageConfig`.
- Invalid stale files/subdirectories or a bad preserved page-config manifest return `MID_WRITE_FAILURE` before project scan/success, with `validationStage`, `validationResourceType`, `validationFailure`, and, for manifest failures, `validationErrorCode:"RESOURCE_MANIFEST_INVALID"`.
- Non-view unknown files are not pruned; inspect or rollback instead of expecting automatic cleanup.

## `backupList`

Lists runner backups.

Useful fields:

- `targetProject`
- `maxResults`

`0.3.49+` backup entries include script metadata such as `hasScripts`, `scriptCount`, and manifest `scriptPaths` when available. `0.3.52+` entries also include Named Query metadata such as `hasNamedQueries`, `namedQueryCount`, and manifest `namedQueryPaths`. `0.3.84+` entries can include `backupFormat: "fileChanges-v1"`, `fileChangeCount`, `existingFileCount`, `newFileCount`, and `targetPathSamples`; entries created by import or self-update report `type: "projectResourceImportZip"` or `type: "runnerSelfUpdate"`. `0.3.102+` legacy import-backup folders can report `type: "projectResourceImportZip"` and `backupFormat: "legacy-project-resource-import"` even when they predate `fileChanges-v1`. `0.3.103+` current `runnerSelfUpdate` entries include both the Web Dev `doPost.py` and sibling `resource.json` in `targetPathSamples` when those samples fit the response cap. `0.3.144+` `fileChanges-v1` entries also expose `afterStateKnown`, `backupManifestComplete`, and `rollbackDriftCheckMode`. `0.3.200+` guarded resource-delete backups report `type:"projectResourceDelete"` and restore through normal `rollback` with the selected project.

## `logQuery`

Use this after dry-run/apply/browser work to check recent Gateway/Perspective errors without dumping broad logs.

```json
{
  "action": "logQuery",
  "requestId": "LOG-001",
  "sinceMinutes": 10,
  "levels": ["WARN", "ERROR"],
  "loggerContains": "Perspective",
  "messageContains": "LLM Tests",
  "includeNonPrimary": false,
  "includeRotated": false,
  "maxLogFiles": 1,
  "maxResults": 20
}
```

Rules:

- Prefer `sinceEpochMillis` captured before the operation.
- Otherwise use `sinceMinutes` from `1` through `1440`.
- Include filters: `levels`, `loggerContains`, or `messageContains`.
- Set `includeNonPrimary: true` only when you need timestamped wrapper lines with no Ignition logger prefix, such as bare `print` output or Perspective gateway print output.
- Set `includeRotated: true` only when the failure may have rolled out of the current wrapper log. Pair it with `maxLogFiles`, narrow filters or an explicit broad confirmation, and a `tailBytes` value small enough to stay under `maxTotalTailBytes`.
- Preserve `sourceFiles` and each entry's `sourceFileName` when rotated evidence is used.
- Set `confirmBroadLogQuery` only for deliberate broad diagnostics.
- Runner `0.3.128+` rejects overlong or control-character text filters before scanning logs. `loggerContains`, `messageContains`, `textContains`, `excludeLoggerContains`, and `excludeTextContains` are limited to 160 characters and return `FILTER_VALUE_TOO_LONG` or `FILTER_CONTROL_CHARACTERS` instead of being modified.

`0.3.61` rotated log behavior:

- `includeRotated: true` scans the current wrapper log plus numeric siblings such as `wrapper.log.1`, up to `maxLogFiles`.
- `sourceFiles[]` reports `fileName`, `length`, `lastModifiedEpochMillis`, `lineScanCount`, `matchedCountBeforeCap`, and `tailWindowTruncated` per scanned file.
- Entries include `sourceFileName`; set `includeSourcePath: true` only when path evidence is needed.
- Requests are rejected when `tailBytes * sourceFileCount` exceeds `maxTotalTailBytes`; reduce `tailBytes` or `maxLogFiles`.

`0.3.56` log behavior:

- `includeNonPrimary: true` allows matched non-primary wrapper lines into `entries[]`.
- Non-primary entries have `primary: false`, an empty `logger`, parsed `timestamp`/`epochMillis` when available, and the wrapper-derived level.
- Use `textContains` or `messageContains` with a unique marker for non-primary lines; `loggerContains` cannot match an empty logger.

`0.3.49` log behavior:

- Non-integer, below-minimum, and above-maximum `sinceMinutes` values are rejected.
- Log entries with unparsable timestamps are excluded from time-windowed results.
- Log tails are read in binary mode and decoded with UTF-8 replacement fallback.

## `auditQuery`

Use this after operator-action tests, button logging, tag/security/Gateway change checks, or controlled `system.util.audit` probes to collect bounded change-attribution context. Audit rows are not diagnostic logs; keep them separate from `logQuery`, Gateway Diagnostic Logs, wrapper logs, and browser console evidence.

Explicit profile example:

```json
{
  "action": "auditQuery",
  "requestId": "AUDIT-002",
  "profile": "AuditLog",
  "startEpochMillis": 1781640000000,
  "endEpochMillis": 1781640600000,
  "valueFilter": "%RUN-123%",
  "maxResults": 20
}
```

Rules:

- Provide `profile`, `auditProfileName`, or `profiles`; WebDev/Gateway-scope calls require an explicit audit profile name.
- Do not send `useDefaultProfile`; runner `0.3.82+` rejects it before calling Ignition because configured-default audit profiles are only optional in Perspective/Vision client scope, not Gateway scope.
- Provide `sinceMinutes` or `startEpochMillis`; runner `0.3.96+` caps the range at `1440` minutes, and runner `0.3.126+` treats `maxResults` as a global response cap across all requested profiles.
- Include at least one narrow `actorFilter`, `actionFilter`, `targetFilter`, `valueFilter`, or `systemFilter`. Runner `0.3.96+` rejects broad audit scans before calling Ignition; runner `0.3.127+` requires at least two non-wildcard characters in that scope filter and returns `BACKEND_SCOPE_FILTER_TOO_BROAD` for shorter filters. `allowBroad` / `confirmBroadAuditQuery` is no longer a bypass for this action.
- Runner `0.3.128+` rejects invalid audit query input before calling Ignition. `profiles` is capped at 10 unique non-empty names, profile names are capped at 120 characters, and audit string filters are capped at 160 characters; control characters return `FILTER_CONTROL_CHARACTERS`, overlong values return `FILTER_VALUE_TOO_LONG`, and too many profiles return `FILTER_LIMIT_EXCEEDED`.
- Pass `contextFilter` only as an integer bitmask from `0` through `7`; do not pass string wildcards.
- Poll briefly after a controlled audit write because readback can lag by a few seconds.
- Treat unknown profile failures as normal target configuration evidence; do not guess profile names repeatedly after a clear `Error retrieving audit profile`.

Response fields include `profiles`, `profileCount`, `maxResults`, `responseMaxRows`, `maxResultsScope`, `totalRowCount`, `returnedRowCount`, `truncated`, `queryOk`, `backendScopeRestricted`, `backendScopeRestrictionSource`, `backendRowBounded`, `responseRowsBounded`, `minimumFilterLiteralChars`, and `attempts[]`. In runner `0.3.126+`, `maxResultsScope` is `"global"`. In runner `0.3.127+`, `backendRowBounded` is `false` and `responseRowsBounded` is `true` for audit because Ignition returns a filtered dataset before the runner applies the response row cap. `attempts[]` preserves per-profile diagnostics and can include `responseMaxRows: 0` with no returned rows after the global row budget is exhausted.

## Discovery And Read Actions

### `gatewayInfo`

Read-only Gateway/environment/module diagnostics. Use before assuming version, module, OS, Java, or project roots.

In runner `0.3.55+`, `health.features` includes `gatewayInfoModuleVersions`, and `gatewayInfo` enriches each module with fields from `system.util.getModules`:

- `moduleId`
- `moduleName`
- `moduleVersion`
- `moduleState`
- `moduleLicenseStatus`
- `moduleVersionSource: "system.util.getModules"`

The response also reports `modules.systemUtilGetModules` with the dataset columns/count/matched count. On older runners, `gatewayInfo` may only expose module IDs/states/license-state summaries; request module-version evidence before doing version-specific bug or release-note matching.

### `databaseConnectionsList`

Read-only database connection inventory. Use before SQL work that depends on a specific database type, connection status, Tag Historian/PostgreSQL availability, generated keys, transactions, DateTime driver behavior, or Database-parameter diagnostics.

Request fields:

- `maxResults`: optional cap; default 50 and runner-capped.
- `includeProblem`: optional boolean; default `false`. When true, the response includes clipped problem text for each connection.

Typical request:

```json
{
  "action": "databaseConnectionsList",
  "requestId": "DB-CONNECTIONS-001",
  "maxResults": 50,
  "includeProblem": false
}
```

Response fields include `connectionCount`, `returnedCount`, `truncated`, `columns`, `dbTypes`, `statuses`, and `connections[]`. Each connection row includes `name`, `description`, `dbType`, `status`, `problemPresent`, and optionally `problem`. Treat connection names and problem text as target-local evidence; use placeholders in reusable skills, examples, and customer-facing SQL.

## Performance Diagnostic Actions

These actions are read-only and intended for Perspective performance profiling evidence. Start with `health`, verify the feature flags are present, then gather a small baseline before making any project changes.

### `metricsList`

Lists metric names from the Gateway metric registry using bounded filters. The action requires at least one `namePrefixes` or `nameContains` filter so callers do not accidentally dump the entire registry.

Request fields:

- `namePrefixes`: optional list of metric name prefixes.
- `nameContains`: optional list of substrings.
- `types`: optional list of metric types: `counter`, `gauge`, `histogram`, `meter`, or `timer`.
- `maxResults`: optional cap; default 100, maximum 250.
- `includeRawNames`: optional boolean. Defaults to `false`; raw names require `confirmSensitiveDiagnostic: "INCLUDE_RAW_METRIC_NAMES"`.

Typical request:

```json
{
  "action": "metricsList",
  "requestId": "PERF-METRICS-001",
  "nameContains": ["Perspective", "perspective"],
  "types": ["timer", "gauge"],
  "maxResults": 50
}
```

Response fields include `matchedCount`, `returnedCount`, `truncated`, `filters`, and `metrics[]`. Each metric includes `type`, `token`, `name`, and `redacted`. Use `token` values with `metricsSnapshot` when the skill should avoid raw metric names.

### `metricsSnapshot`

Captures current values for explicit metric names or tokens returned by `metricsList`. This action does not accept broad filters.

Request fields:

- `metricNames`: optional exact metric names.
- `metricTokens`: optional metric tokens returned by `metricsList`.
- `includeRawNames`: optional boolean. Defaults to `false`; raw names require `confirmSensitiveDiagnostic: "INCLUDE_RAW_METRIC_NAMES"`.
- `maxMetrics`: optional cap; default 50, maximum 100.

Typical request:

```json
{
  "action": "metricsSnapshot",
  "requestId": "PERF-SNAPSHOT-001",
  "metricTokens": ["<metric-token-from-metricsList>"],
  "maxMetrics": 25
}
```

Response fields include `capturedAtEpochMillis`, `sequence`, `metrics[]`, and per-item `error` values when a requested metric cannot be found. Runner `0.3.129+` stores `sequence` in `system.util.getGlobals()` so it increments across repeated direct-paste Web Dev requests and Project Library calls for the Gateway JVM lifetime. Runner `0.3.131+` preserves exact integral precision for large metric counts, gauge values, JVM byte/nanosecond values, and histogram `min` / `max` fields before falling back to floating conversion for fractional metric values. Values are normalized for counters, gauges, histograms, meters, and timers where the underlying metric object exposes the standard Dropwizard-style methods.

### `gatewayPerformanceSnapshot`

Returns a bounded JVM and Gateway performance snapshot using Java management beans and the Gateway performance monitor when available.

Typical request:

```json
{
  "action": "gatewayPerformanceSnapshot",
  "requestId": "PERF-GATEWAY-001"
}
```

Response fields include `capturedAtEpochMillis`, `runtime`, `memory`, `threads`, `os`, and `performanceMonitor`. CPU load fields can be `null` on JVMs or platforms that do not expose them.

### `perspectiveSessionsQuery`

Returns a bounded Perspective session inventory through Gateway-scope Perspective session APIs.

Request fields:

- `targetProject`: required project name.
- `maxResults`: optional cap; default 50, maximum 100.
- `sessionIds`: optional list of raw session IDs or response `sessionToken` values to match after the project-filtered session scan.
- `includeIdentifiers`: optional boolean. Defaults to `false`; raw session/page identifiers should remain target-local evidence only.
- `includeUserAgent`: optional boolean. Defaults to `false`.
- `includeClientAddress`: optional boolean. Defaults to `false`; addresses are redacted when included.

Typical request:

```json
{
  "action": "perspectiveSessionsQuery",
  "requestId": "PERF-SESSIONS-001",
  "targetProject": "MyProject",
  "maxResults": 50
}
```

Response fields include `project`, `scannedCount`, `matchedCount`, `returnedCount`, `maxResults`, `truncated`, and `sessions[]`. `scannedCount` is the project-filtered sessions returned by Ignition before local `sessionIds` filtering, `matchedCount` is the local-filter match count before `maxResults`, and `truncated` is true only when `matchedCount > returnedCount`. Default session rows use stable tokens rather than raw session identifiers.

### `threadDumpQuery`

Returns a bounded thread dump excerpt for incident triage. This action requires an explicit confirmation and at least one narrow thread-name or stack-content filter.

Request fields:

- `threadNameContains`: optional list of thread name substrings.
- `stackContains`: optional list of stack text substrings.
- `maxThreads`: optional cap; default 20, maximum 50.
- `maxFramesPerThread`: optional cap per thread; default 40, maximum 100.
- `confirmSensitiveDiagnostic`: required value `READ_BOUNDED_THREAD_DUMP`.

Typical request:

```json
{
  "action": "threadDumpQuery",
  "requestId": "PERF-THREADS-001",
  "threadNameContains": ["Perspective", "gateway"],
  "maxThreads": 10,
  "maxFramesPerThread": 20,
  "confirmSensitiveDiagnostic": "READ_BOUNDED_THREAD_DUMP"
}
```

Response fields include `capturedAtEpochMillis`, `threadCount`, `matchedCount`, `returnedCount`, `truncated`, `maxThreads`, `maxFramesPerThread`, `maxResponseChars`, `unredactedDumpSha256`, `threads[]`, and `notes[]`. The default response redacts diagnostic text while preserving state, frame counts, and match metadata.

### `tagProviders`

Lists available tag providers. Use before building tag paths.

### `tagBrowse`

Browse tags under a provider/path with filters and caps. Use `includeValues` only when needed.

Common fields:

- `rootPath`
- `tagType`
- `recursive`
- `maxResults`
- `includeValues`

Response fields include `count`, `returnedCount`, `returnedSize`, `totalAvailable`, `truncated`, and `nodes[]`. Runner `0.3.83+` reads Ignition browse-result metadata through `getReturnedSize()` and `getTotalAvailableSize()` when available; if metadata is unavailable, `totalAvailable` falls back to the returned size. Treat `truncated: true` or `totalAvailable > returnedCount` as an incomplete capped browse and narrow the path/filter or increase `maxResults` before using the result as a complete tag inventory.

### `tagRead`

Reads explicit fully qualified tag paths such as `[Sample_Tags]Area/Pump/PV`. Unqualified paths are rejected.

UDT instance parameters are read with dot paths such as `[Sample_Tags]Area/Pump001/Parameters.ParamName`. In Ignition 8.1 tests, Boolean and numeric UDT parameters can read back as strings such as `"0"`, `"1"`, or `"120"`; normalize them before using the values as Boolean or numeric Perspective props.

### `historyProbe`

Checks whether selected fully qualified tag paths have historian data in a bounded window. A Good current value does not confirm history exists.

For trend pages, pair `historyProbe` with exact Perspective chart seeds such as Time Series Chart, Chart Range Selector, or Power Chart. `queryOk: true` with timestamp rows or non-null value-query cells does not by itself confirm stored historian samples. Use sample-backed availability fields when present, label sampled/current-value fallbacks honestly, and preserve the fully qualified tag paths used for the probe and chart bindings.

Runner `0.3.93+` advertises `historyProbeSampleBackedAvailability`; runner `0.3.137+` also advertises `historyProbeGoodSampleTerminology`. In the current contract, use `goodSampleHistoryAvailable: true` and positive `goodStoredSampleCount` / per-tag `tagStats[].goodStoredSampleCount` as good-quality stored-sample evidence. Treat compatibility `historyAvailable` and `storedSampleCount` as aliases, and treat `valueQueryHistoryAvailable`, `tagStats[].nonNullCount`, `tagStats[].hasData`, and `lastValue` as diagnostic context from the caller-selected value query, not as proof that good stored samples exist.

For Time Series Chart custom plots, `pageValidate` and `viewRead` are structural checks only. Browser verification should confirm rendered SVG/canvas marks and no relevant chart runtime errors. Use `props.plots[].trends[].columns` as object entries such as `{ "key": "PV" }` when each key matches a field in `props.series[].data`; plain string columns remain a known bad shape.

### `alarmStatusQuery`

Queries current alarm status, not alarm journal history.

Common fields:

- `providers`
- `displayPath`
- `source`
- `path`
- `states`
- `priorities`
- `includeShelved`
- `maxResults`

For Ignition 8.1, provider filtering uses the documented `system.alarm.queryStatus(provider=...)` argument. Revisit only if a target Gateway rejects it.

Runner `0.3.96+` requires at least one narrow `source`, `path`, or `displayPath` value before calling `system.alarm.queryStatus`. Runner `0.3.127+` requires at least two non-wildcard characters in that scope filter and returns `BACKEND_SCOPE_FILTER_TOO_BROAD` for shorter filters. Provider, state, priority, and shelved filters are supplemental and do not count as the backend work bound. Responses include `backendScopeRestricted`, `backendScopeRestrictionSource`, `backendRowBounded`, `responseRowsBounded`, `minimumFilterLiteralChars`, compatibility `backendBounded`, `backendBoundSource`, and `responseMaxRows`.

Runner `0.3.128+` rejects invalid alarm status filter inputs before calling `system.alarm.queryStatus`. `providers` is capped at 10 items; `sources`, `paths`, `displayPaths`, `states`, and `priorities` are capped at 20 items; each filter value is capped at 300 characters; and control characters return `FILTER_CONTROL_CHARACTERS` instead of dropping the value.

For Alarm Journal Table pages, discover an exact `ia.display.alarmjournaltable` seed and preserve its configured journal profile in `props.name`; do not guess `"Journal"`. `alarmStatusQuery` confirms only current alarm state. Use `alarmJournalQuery` when you need to confirm historical journal rows for the same profile the component will use.

For route-param alarm/history detail pages, bind Alarm Status Table `props.filters.active.conditions.displayPath` and Alarm Journal Table `props.filter.conditions.displayPath` from `view.params.<assetId>` or a derived display-path pattern. Verify the same concrete filter with `alarmStatusQuery`, `alarmJournalQuery`, `viewRead`, `pageValidate`, and browser evidence.

### `alarmJournalQuery`

Queries historical alarm journal rows, not current alarm status and not diagnostic logs.

Common fields:

- `journalName`, `journal`, or `alarmJournal`
- `sinceMinutes` or `startEpochMillis`/`endEpochMillis`
- `providers`
- `sources`
- `paths`
- `displayPaths`
- `states`
- `priorities`
- `includeData`
- `includeSystem`
- `includeShelved`
- `isSystem`
- `maxResults`

The action requires an explicit journal name and rejects wildcard journal names. useDefaultJournal is rejected on runner `0.3.97+`, and the legacy `useConfiguredJournal` alias is also rejected, because the runner cannot verify that exactly one Alarm Journal profile exists on the target Gateway. Runner `0.3.96+` caps the time range at `1440` minutes, keeps `maxResults` as a response cap, and requires at least one narrow `source`, `path`, or `displayPath` filter before calling `system.alarm.queryJournal`. Runner `0.3.127+` requires at least two non-wildcard characters in that scope filter and returns `BACKEND_SCOPE_FILTER_TOO_BROAD` for shorter filters. Provider, state, priority, and `isSystem` filters are supplemental and do not count as the backend work bound. Successful responses include `backendScopeRestricted`, `backendScopeRestrictionSource`, `backendRowBounded`, `responseRowsBounded`, `minimumFilterLiteralChars`, compatibility `backendBounded`, `backendBoundSource`, and `responseMaxRows`. The old `allowBroad` / `confirmBroadAlarmJournalQuery` bypass is removed.

Runner `0.3.128+` rejects invalid alarm journal query input before calling `system.alarm.queryJournal`. Explicit journal names are capped at 120 characters, alarm filter list caps match `alarmStatusQuery`, each filter value is capped at 300 characters, and control characters return `FILTER_CONTROL_CHARACTERS` instead of silently modifying the request.

Explicit profile example:

```json
{
  "action": "alarmJournalQuery",
  "requestId": "ALARM-JOURNAL-001",
  "journalName": "<exact discovered profile>",
  "displayPaths": ["Area 1/Line 3*"],
  "states": ["ActiveUnacked", "ActiveAcked"],
  "sinceMinutes": 1440,
  "maxResults": 25
}
```

If the profile name is unknown, discover it from the Alarm Journal Table `props.name`, target project configuration, or operator-provided Gateway configuration evidence. Do not guess `Journal`; a wrong profile can fail or return a different row set than the component will display.

### Shared Docked Views

Ignition 8.1 Page Configuration can define shared docked views for all pages and page-specific docked views for one page. Use `sharedDockKeys` only for the top-level shared settings contract. Page-specific `docks` can ride inside an explicit route page object, but top-level `sharedDocks` must be requested explicitly so the runner can validate, merge, and preserve other shared dock settings.

### `routesList`

Lists Perspective page routes under an optional route prefix.

### `viewsList`

Lists Perspective views under an optional view prefix.

### `viewRead`

Reads one allowlisted Perspective view, optionally including hashes and bounded JSON.

### `pageValidate`

Validates route-to-view structure, dependency views, dependency scripts, dependency Named Queries, hashes, and missing resources. It is read-only and does not confirm browser rendering or interaction behavior.

Common fields:

- `targetProject`
- `pagePath`
- `expectedViewPath`
- `dependencyViewPaths`
- `dependencyScriptPaths`
- `dependencyNamedQueryPaths`
- `allowedRoutePrefix`
- `allowedViewPrefix`
- `allowedScriptPrefix`
- `allowedNamedQueryPrefix`
- `expectedViewSha256ByViewPath`
- `expectedScriptSha256ByScriptPath`
- `includeHashes`

For shared docked pages, pass the dock view paths returned by dry-run/apply `sharedDockViewPaths` as `dependencyViewPaths` or verify each with `viewRead`. Use a bounded diagnostic readback only when you need to confirm the target page-config `sharedDocks` edge, `id`, `viewPath`, and `viewParams`; use browser verification for the actual dock render.

For Named Query dependencies, pass the same `dependencyNamedQueryPaths` used in dry-run/apply. Require `namedQueryChecks[].exists`, `hasResourceJson`, and `hasQuerySql` before relying on query-backed runtime behavior. Use `namedQueryRead` for parameter/type/database metadata and a workflow-specific readback for action/update queries. If the dependency used QueryString/Database params, keep the exact unsafe-param allowlist in the evidence and do not generalize Database runtime behavior without target verification.

### `styleResourcesList`

Discovers existing Perspective style classes, themes, images, thumbnails, and reusable views. It is metadata-first and capped.

### `seedViewsList`, `seedViewRead`, `componentSeedRead`

Read Designer-created seed views/components under allowlisted prefixes. Use these before guessing undocumented Perspective component JSON.

`componentSeedRead` requires a concrete `viewPath` and exact component selector such as `componentType` or `componentName`.

For View Canvas pages, discover and extract an exact `ia.display.viewcanvas` seed before authoring. Each `props.instances[]` entry uses `viewPath` plus `viewParams`; the `viewParams` keys must match the child view's declared `view.params`. Include every faceplate/detail child view in `dependencyViewPaths`, and pass the same list to `pageValidate`. `pageValidate` confirms route/dependency wiring only; browser-click evidence is required for `onInstanceClicked`, param flow, and parent/detail updates. In `onInstanceClicked`, prefer `event.index` to read `self.props.instances[idx].viewParams`, copy selected values into parent `view.custom`, then bind embedded detail `props.params.*` from that parent state.

For View Canvas selected-equipment command popups, let the parent view own selected state, but pass selected context into embedded detail views through `ia.display.view.props.params`. Event scripts inside that embedded child must read `self.view.params.*`, not the parent's `view.custom`. Open command popups with explicit `baseTagPath`, `expectedPrefix`, `popupId`, and action params; include the popup view in `dependencyViewPaths` and any Project Library command script in `dependencyScriptPaths`. Validate both a blocked interlock and an accepted writeback with browser evidence, final `tagRead`, and focused `logQuery`.

## Named Query Actions

### `namedQueriesList`

Lists Named Query metadata under `ignition/named-query`, including parameter metadata and read-only/bounded preview eligibility.

### `namedQueryRead`

Reads one allowlisted Named Query resource with bounded SQL body/hash metadata. In `0.3.54+`, a Named Query with `attributes.database` set to `<Parameter>` reports a synthetic `database` parameter when the resource does not explicitly declare one.

On runner `0.3.62+`, pass `includeResourceJson: true` when a package needs to copy an existing Named Query. The response includes `resource`, `resourceSha256`, and `resourceSizeBytes`; write the returned raw `resource` as `resource.json` beside the returned `query.sql`.

### `namedQueryPreview`

Runs a capped preview only when the Named Query is read-only and DB-side bounded within the requested preview cap. QueryString and Database params reject by default; use the `0.3.54+` exact allowlist fields only for controlled diagnostics.

Runner `0.3.96+` requires the DB-side `LIMIT`, `TOP`, `FETCH`, or Named Query max return size to be `<= maxRows` for the request. A query with `LIMIT 100` and `maxRows: 5` is rejected before execution; use `LIMIT 5`, `TOP 5`, `FETCH FIRST 5 ROWS`, or an equivalent Named Query max return size. Runner `0.3.99+` only counts top-level outer-query numeric SQL row limiters, so nested subquery/CTE limits do not make an outer query preview-eligible by themselves. Preview responses report `previewSafety.backendBounded`, `previewSafety.backendBoundSource`, `previewSafety.backendRowLimit`, and `previewSafety.responseMaxRows`.

`0.3.49` SQL scanner behavior:

- Allows read-only `REPLACE(...)` string function usage.
- Still rejects mutating `REPLACE INTO`.
- Strips SQL string literals before mutating keyword scans.
- Rejects mutating or executable keywords such as `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `CALL`, and `EXEC`.

## Project Resource Actions

### `projectResourcesList`

Lists project resources under a bounded project-relative prefix. By default, the action is constrained to Vision resources:

```json
{
  "action": "projectResourcesList",
  "requestId": "VISION-RESOURCES-001",
  "targetProject": "<project>",
  "resourcePrefix": "com.inductiveautomation.vision",
  "allowedResourcePrefix": "com.inductiveautomation.vision",
  "includeFiles": true,
  "maxResults": 200
}
```

The response includes `resourceCount`, `fileCount`, `returnedCount`, `truncated`, and `items`. Resource items report `resourcePath`, `hasResourceJson`, `fileCount`, and `fileNames`; file items report `resourcePath`, `fileName`, `path`, and byte size. Use this action to discover what the target already contains before reading or packaging resources.

On runner `0.3.70+`, `maxResults` must be an integer from `1` through `1000` when supplied. Invalid values return HTTP 400 JSON errors.

### `projectResourceRead`

Reads one resource directory under `allowedResourcePrefix`, returning file metadata, optional hashes, and capped text for known text resource files:

```json
{
  "action": "projectResourceRead",
  "requestId": "VISION-RESOURCE-READ-001",
  "targetProject": "<project>",
  "resourcePath": "com.inductiveautomation.vision/client-tags",
  "allowedResourcePrefix": "com.inductiveautomation.vision",
  "includeResourceJson": true,
  "includeHashes": true,
  "includeText": false,
  "maxTextChars": 12000
}
```

The action rejects traversal, absolute paths, colon paths, and paths outside `allowedResourcePrefix`. It reports binary files by byte size and SHA-256 only. Do not treat this as Vision authoring support; use it for inventory, drift detection, seed inspection, and evidence before using Designer-created exports/imports.

### `visionWindowInspect`

Inspects one concrete Vision window without opening Designer or launching a client:

```json
{
  "action": "visionWindowInspect",
  "requestId": "VISION-WINDOW-INSPECT-001",
  "targetProject": "<project>",
  "resourcePath": "com.inductiveautomation.vision/windows/<folder>/<window>",
  "allowedResourcePrefix": "com.inductiveautomation.vision/windows",
  "expectedTextMarkers": ["<expected marker>"],
  "maxFiles": 200,
  "maxBytes": 5242880,
  "maxDecompressedBytes": 10485760,
  "maxComponents": 200
}
```

The action rejects the windows root itself, paths outside the Vision windows root, missing/invalid `resource.json`, and missing `window.bin`. All limits are bounded: `maxFiles` is `1..2000`, `maxBytes` is `1..26214400`, `maxDecompressedBytes` is `1..52428800`, `maxComponents` is `1..1000`, and at most 20 expected markers of at most 240 characters each are accepted.

For gzip XML windows, inspect `windowSize`, `rootPreferredBounds`, `rootMatchesWindowSize`, `components[]`, `layoutCoverage`, and `warnings[]`. Positioned children should have both numeric bounds and a serialized `fpmi.lc` layout constraint. For binary-v2 windows, inspect `serializationVersion`, `componentClassNames`, `knownTokenPresence`, and expected marker results, but do not infer pixel geometry. In every format, preserve `resourceStateSha256` for a later guarded delete and treat `runtimeRenderVerified:false` as the boundary between API evidence and visual/runtime proof.

### `projectResourceExport`

Exports one existing resource directory as a bounded ZIP. The ZIP is resource-relative, so re-importing it to another resource directory requires `projectResourceImportZip.resourcePath`.

Common fields:

- `targetProject`
- `resourcePath`
- `allowedResourcePrefix`
- `includePackageBase64`
- `maxFiles`
- `maxBytes`

### `projectResourceImportZip`

Dry-run a project-relative Ignition 8 project-resource package:

```json
{
  "action": "projectResourceImportZip",
  "requestId": "VISION-IMPORT-DRY-001",
  "targetProject": "<project>",
  "allowedResourcePrefix": "com.inductiveautomation.vision",
  "packageBase64": "<zip>",
  "dryRun": true,
  "maxFiles": 200,
  "maxBytes": 5242880,
  "scanTimeoutSeconds": 10
}
```

Apply after reviewing dry-run counts:

```json
{
  "action": "projectResourceImportZip",
  "requestId": "VISION-IMPORT-APPLY-001",
  "targetProject": "<project>",
  "allowedResourcePrefix": "com.inductiveautomation.vision",
  "packageBase64": "<zip>",
  "dryRun": false,
  "confirmProjectResourceImport": "IMPORT_PROJECT_RESOURCE_ZIP",
  "maxFiles": 200,
  "maxBytes": 5242880,
  "scanTimeoutSeconds": 10
}
```

To import a resource-relative ZIP created by `projectResourceExport`, set `resourcePath` to the target resource directory. If the ZIP already contains `com.inductiveautomation.vision/...` paths, omit `resourcePath`.

Conflicts are reported before apply. Exact-hash existing files count as `same` and are not rewritten. Differing existing files require both `overwriteExisting: true` and `confirmOverwrite: "OVERWRITE_PROJECT_RESOURCES"`. On runner `0.3.84+`, all written or overwritten files are recorded in a `fileChanges-v1` backup so rollback can restore previous files and remove newly created files from the import.

On runner `0.3.102+`, rollback can also restore backed-up overwritten files from older `projectResourceImportZip` backup folders that predate `fileChanges-v1`. Those legacy backups cannot identify files created by the original import, so their rollback responses include `createdFilesNotRemoved: true`.

On runner `0.3.85+`, both `projectResourceImportZip` dry-runs and applies use the Gateway-wide mutation lock because ZIP validation extracts and stages work files.

On runner `0.3.133+`, duplicate normalized ZIP entry destinations are rejected before import validation, conflict detection, backup planning, or file writes. Exact duplicate names, dot-segment equivalents, slash/backslash equivalents, and Windows case-only destination collisions return `PACKAGE_ZIP_INVALID` with `filesChanged:false`, `scanRequested:false`, `scanCompleted:false`, and `recoveryRequired:false`.

On runner `0.3.140+`, `projectResourceImportZip` validates touched managed resources against the final merged resource state before writes. It overlays packaged files onto the current target file set, uses the packaged `resource.json` when supplied or the existing target manifest otherwise, and rejects missing listed files or unlisted managed files with `RESOURCE_MANIFEST_INVALID`, `manifestValidationPhase:"finalMergedResourceState"`, `filesChanged:false`, `scanRequested:false`, `scanCompleted:false`, and `recoveryRequired:false`.

On runner `0.3.86+`, import applies stage final file writes to sibling temporary paths and commit with Java NIO atomic moves. Backup manifests and conflict detection behavior are unchanged.

On runner `0.3.105+`, import validates `scanTimeoutSeconds` as `1..30`, default `10`, and echoes the effective timeout when apply requests a post-write project scan.

On runner `0.3.115+`, an exception after import backup planning or after any imported file write returns `MID_WRITE_FAILURE` with `writeFailure`, `backupName`, `failedStage`, `writesStarted`, `writtenPaths`, `recoveryRequired`, and `rollbackAvailable` metadata.

`projectResourceImportZip` writes resource files from the ZIP contents and does not run the runner metadata-stamping helper. Use the exported or authored `resource.json` as the source of truth for imported attributes.

Do not use this action to convert legacy Ignition 7 `.proj` files or to synthesize Vision `*.bin` payloads. Use Designer/Gateway import tooling for legacy conversion, then read/export the resulting Ignition 8 project resources through the runner.

### `projectResourceDelete`

Dry-run one exact project-resource deletion:

```json
{
  "action": "projectResourceDelete",
  "requestId": "RESOURCE-DELETE-DRY-001",
  "targetProject": "<project>",
  "resourcePath": "com.inductiveautomation.vision/windows/<folder>/<window>",
  "allowedResourcePrefix": "com.inductiveautomation.vision/windows",
  "dryRun": true,
  "maxFiles": 200,
  "maxBytes": 5242880,
  "scanTimeoutSeconds": 10
}
```

Review `resourceStateSha256`, `fileCount`, `totalBytes`, `files[]`, and `wouldDeletePaths`. Apply only against that current state:

```json
{
  "action": "projectResourceDelete",
  "requestId": "RESOURCE-DELETE-APPLY-001",
  "targetProject": "<project>",
  "resourcePath": "com.inductiveautomation.vision/windows/<folder>/<window>",
  "allowedResourcePrefix": "com.inductiveautomation.vision/windows",
  "dryRun": false,
  "expectedResourceStateSha256": "<current resourceStateSha256>",
  "confirmProjectResourceDelete": "DELETE_PROJECT_RESOURCE",
  "maxFiles": 200,
  "maxBytes": 5242880,
  "scanTimeoutSeconds": 10
}
```

Apply rejects a missing expected state with `EXPECTED_RESOURCE_STATE_REQUIRED`, a stale state with `RESOURCE_STATE_DRIFT`, a missing exact confirmation with `CONFIRMATION_REQUIRED`, and a tree containing nested project resources with `NESTED_RESOURCE_DELETE_BLOCKED`. Success returns `resourceDeleted:true`, `backupName`, `backupFormat:"fileChanges-v1"`, deleted-file metadata, scan-wait fields, and verified post-scan absence. Discover the backup through `backupList` (`type:"projectResourceDelete"`), dry-run `rollback`, apply rollback with its normal confirmation, then re-read or inspect the restored resource. Do not claim transaction-level atomicity: `atomicMultiFileTransaction` is false.

## Tag And UDT Write Helpers

### `tagConfigure`

Guarded tag configuration for safe fixtures. It supports memory, expression, Derived, and guarded Reference tags, plus UDT definitions and UDT instances. It blocks OPC writes.

Common fields:

- `basePath`
- `tags`
- `allowedTagPathPrefixes`
- `collisionPolicy`
- `dryRun`
- `confirmTagConfigure`
- `maxItems`

On runner `0.3.111+`, confirmed applies return top-level `ok: false` for bad returned `QualityCode`s or returned-code count mismatch. Successful applies include `qualityCodes`, `allGood: true`, `qualityCodeCount`, and `expectedQualityCodeCount`. On older runners, callers must still inspect `allGood` and `qualityCodes` because bad `QualityCode`s can coexist with `ok: true`.

On runner `0.3.114+`, confirmed applies share the Gateway-wide mutation lock and can return retryable `MUTATION_LOCK_BUSY` while another runner mutation is active. `tagConfigure` dry-runs remain non-blocking.

Use `tagConfigure` directly instead of `udtScaffold` when a test must verify explicit UDT instance `parameters` overrides. Verify both `Parameters.ParamName` paths and dependent members with `tagRead`.

### `udtScaffold`

Higher-level UDT fixture helper. It creates one UDT type, instances, and optional member overrides through guarded tag configuration.

Common fields:

- `provider`
- `typePath`
- `instanceFolder`
- `members`
- `instances`
- `memberOverrides`
- `requiredOverrideMembers`
- `allowedTypePathPrefix`
- `allowedInstancePathPrefix`
- `dryRun`
- `confirmUdtScaffold`

Omit `typeId` unless it exactly matches `typePath` as a relative `_types_` path.

On runner `0.3.112+`, `udtScaffold` fails fast when any nested `tagConfigure` step returns `ok: false` or `allGood: false`. Failure responses include `failedStep`, `failedStepResult`, and `stepResults`; do not treat a completed message or top-level `ok: true` on older runners as enough unless every nested step has `allGood: true` and good `qualityCodes`.

On runner `0.3.113+`, failed confirmed scaffold writes may also include partial-recovery fields: `preflightTargetCount`, `preflightExistingPaths`, `preflightNewPaths`, `snapshotPathCount`, `writesStarted`, `completedSteps`, `recoveryAttempted`, `recoveryAllGood`, `recoveryRequired`, and `recovery`. Treat `recoveryRequired: true` as a manual inspection stop condition before additional UDT writes. After any successful apply, read the returned instance member paths with `tagRead` before binding a Perspective page.

On runner `0.3.114+`, confirmed scaffolds share the Gateway-wide mutation lock and can return retryable `MUTATION_LOCK_BUSY` while another runner mutation is active. `udtScaffold` dry-runs remain non-blocking, and the runner acquires the lock once at the public scaffold action boundary rather than around each nested `tagConfigure` step.

### `tagEventScriptProbe`

Constrained fixture for testing tag event script behavior. It is not a general tag event writer.

Common fields:

- `basePath`: existing fully qualified folder such as `[default]LLM Tests/<runId>`.
- `probeName`: new child folder name; the runner rejects existing probe paths.
- `allowedTagPathPrefixes`: guarded fully qualified prefixes that must include `basePath`.
- `pathMode`: `absolute` or `relative`.
- `sourceValue`, `pollAttempts`, `pollMs`, `activateDelayMs`.
- `emitSuccessMarkers`: optional `0.3.57+` boolean; default `false`.
- `successMarker`: required when `emitSuccessMarkers` is true; max 120 characters, limited to letters, digits, underscore, hyphen, period, or colon.

On runner `0.3.94+`, `pollAttempts` in the response is the effective capped attempt count. The original normalized request is returned as `requestedPollAttempts`, and `pollAttemptsCapped` tells whether the effective value was reduced. Responses also include `pollWindowCount`, `probeFixedDelayMs`, `probeNonPollWaitMs`, `probePollWaitMaxMs`, `probeSyncWaitMaxMs`, and `maxProbeSyncWaitMs` for call-duration planning.

On runner `0.3.95+`, dry-run and apply responses include `failureCleanupPaths` containing the planned new probe folder. If an apply fails after fixture creation has started, the runner attempts best-effort cleanup of that fresh probe folder and returns `failureCleanup` while preserving the original error.

On runner `0.3.139+`, failed apply responses that include `failureCleanup` also promote cleanup status to top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired` fields. Use those top-level fields for caller control flow, and keep `failureCleanup` for per-path details.

On runner `0.3.114+`, confirmed probe applies share the Gateway-wide mutation lock and can return retryable `MUTATION_LOCK_BUSY` while another runner mutation is active. `tagEventScriptProbe` dry-runs remain non-blocking.

Dry-run first:

```json
{
  "action": "tagEventScriptProbe",
  "requestId": "TAG-EVENT-001",
  "basePath": "[default]LLM Tests/RUN001",
  "probeName": "AbsoluteMarkerProbe",
  "allowedTagPathPrefixes": ["[default]LLM Tests/RUN001"],
  "pathMode": "absolute",
  "sourceValue": 44,
  "emitSuccessMarkers": true,
  "successMarker": "RUN001_ABSOLUTE_SUCCESS",
  "dryRun": true
}
```

Apply:

```json
{
  "action": "tagEventScriptProbe",
  "requestId": "TAG-EVENT-002",
  "basePath": "[default]LLM Tests/RUN001",
  "probeName": "AbsoluteMarkerProbe",
  "allowedTagPathPrefixes": ["[default]LLM Tests/RUN001"],
  "pathMode": "absolute",
  "sourceValue": 44,
  "emitSuccessMarkers": true,
  "successMarker": "RUN001_ABSOLUTE_SUCCESS",
  "dryRun": false,
  "confirmTagEventScriptProbe": "CREATE_TAG_EVENT_PROBE"
}
```

When `emitSuccessMarkers` is true, the fixed fixture emits the marker only after its sibling result-tag writes report good quality. Use a primary-only `logQuery` to confirm the `system.util.getLogger` entry and `logQuery includeNonPrimary: true` to confirm the bare `print` entry. Do not use this fixture as a general arbitrary event-script writer.

### `udtTagEventScriptProbe`

Constrained fixture for testing UDT tag event scripts reading instance parameters. It requires existing `_types_` and normal provider folders, allowed prefixes, dry-run, and exact confirmation.

On runner `0.3.94+`, this action uses the same bounded synchronous wait contract as `tagEventScriptProbe`. The response `pollAttempts` is effective/capped, `requestedPollAttempts` preserves the normalized caller request, and `pollAttemptsCapped` plus `probeSyncWaitMaxMs` show whether the request was reduced to stay within `maxProbeSyncWaitMs`.

On runner `0.3.95+`, dry-run and apply responses include `failureCleanupPaths` containing the planned instance A path, instance B path, and UDT type path. If an apply fails after fixture creation has started, the runner attempts best-effort cleanup of those fresh UDT probe paths and returns `failureCleanup` while preserving the original error.

On runner `0.3.139+`, failed apply responses that include `failureCleanup` also promote cleanup status to top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired` fields. Use those top-level fields for caller control flow, and keep `failureCleanup` for per-path details.

On runner `0.3.114+`, confirmed UDT probe applies share the Gateway-wide mutation lock and can return retryable `MUTATION_LOCK_BUSY` while another runner mutation is active. `udtTagEventScriptProbe` dry-runs remain non-blocking.

## `scriptEval`

Gateway-scope Jython diagnostic harness.

```json
{
  "action": "scriptEval",
  "requestId": "example-request-001",
  "dryRun": true,
  "script": "return {'ok': True}",
  "args": {}
}
```

Execution requires:

```json
{
  "dryRun": false,
  "confirmScriptEval": "RUN_JYTHON_EVAL"
}
```

Use `scriptEval` only for diagnostics and small behavior probes. It is trusted administrative code execution. Do not claim a timeout exists. Results are JSON-safe and capped; Java `Throwable` failures are returned as JSON.

When a diagnostic eval calls a packaged Project Library module, explicitly import the module in the eval script before calling it. Perspective event scripts may resolve the same module path in page context, but Gateway diagnostic eval should not rely on implicit module globals.

When diagnosing alarm journal pages on runner `0.3.60+`, use `alarmJournalQuery` instead of `scriptEval` for readback whenever possible. On runner `0.3.97+`, match the component's discovered `props.name` as explicit `journalName`; omitted-profile journal queries are not supported by the runner because they can hide mismatches between the script query and component profile. Use `scriptEval` only when the API action is unavailable or a workflow needs a narrow custom diagnostic.

For Perspective button-logging workflows on runner `0.3.59+`, use `auditQuery` for audit readback instead of diagnostic `scriptEval` whenever possible. Keep `scriptEval` for bounded custom SQL/read probes or controlled audit-marker writes when a test specifically needs one. If you must call `system.util.queryAuditLog` manually, use keyword arguments and remember Ignition 8.1 `contextFilter` is an integer bitmask, not a string wildcard.

## `runnerSelfUpdate`

Updates the Web Dev `doPost.py` runner body through the runner itself.

Dry-run first:

```json
{
  "action": "runnerSelfUpdate",
  "requestId": "RSU-001",
  "targetProject": "samplequickstart",
  "webDevResource": "llmImport",
  "expectedRunnerVersion": "<active runnerVersion from health>",
  "scriptBase64": "<base64 simple_webdev_do_post_body.py>",
  "scriptSha256": "<sha256>",
  "dryRun": true
}
```

Apply:

```json
{
  "action": "runnerSelfUpdate",
  "requestId": "RSU-002",
  "targetProject": "samplequickstart",
  "webDevResource": "llmImport",
  "expectedRunnerVersion": "<active runnerVersion from health>",
  "scriptBase64": "<base64 simple_webdev_do_post_body.py>",
  "scriptSha256": "<sha256>",
  "dryRun": false,
  "scanTimeoutSeconds": 10,
  "confirmSelfUpdate": "UPDATE_RUNNER"
}
```

`0.3.49` through `0.3.103` historical self-update backup behavior:

- The backup copy redacts static `TOKEN` or `STATIC_TOKEN` assignments.
- Responses report `backupTokenRedacted: true`.
- Backups remain useful for code recovery but are not token escrow.

`0.3.84+` self-update backup behavior:

- Dry-run responses include `backupDir`, `backupName`, and `backupFormat: "fileChanges-v1"`; apply responses also include file-change counts.
- The manifest records the Web Dev `doPost.py` target file so rollback can restore the recorded code backup if needed.
- For `0.3.84` through `0.3.103`, static token assignments remain redacted in the backup; for `0.3.104+`, the `doPost.py` backup is exact source.

`0.3.85+` self-update locking behavior:

- Self-update apply requests use the Gateway-wide mutation lock and return `MUTATION_LOCK_BUSY` if another runner mutation is active.
- Self-update dry-runs remain syntax/hash/backup-planning requests and do not acquire the mutation lock.

`0.3.86+` self-update file-write behavior:

- The Web Dev `doPost.py` target is staged to a sibling temporary file before the final Java NIO atomic move.
- The backup manifest remains `fileChanges-v1` and rollback-compatible.

`0.3.87+` self-update resource metadata behavior:

- The sibling Web Dev `resource.json` keeps existing `attributes` keys while the runner updates `lastModification` and `lastModificationSignature`.

`0.3.103+` self-update resource metadata rollback behavior:

- The `fileChanges-v1` manifest includes a rollback snapshot for the sibling Web Dev `resource.json`.
- Responses include `targetResourceFile` and `backupIncludesResourceJson: true`.
- Rollback of a current self-update backup restores the recorded `resource.json` metadata state.

`0.3.104+` self-update exact-backup behavior:

- The `fileChanges-v1` manifest stores the exact pre-update Web Dev `doPost.py` source.
- Responses include `backupExactSource: true` and `backupTokenRedacted: false`.
- If the running source contains literal static token assignments, the backup contains them too; protect backup folders like runner source.

`0.3.105+` self-update scan behavior:

- Confirmed self-update accepts `scanTimeoutSeconds` for the post-write project scan. The value must be an integer from `1` through `30`; default `10`.

`0.3.136+` self-update post-write second-wait behavior:

- Confirmed self-update attempts two bounded `system.project.requestScan(scanTimeoutSeconds)` waits when files changed and reports `scanWaitsAttempted`, `scanWaitsCompleted`, and `defensiveSecondScanWait`.

`0.3.135+` self-update scan-completion message behavior:

- Successful confirmed self-update responses use `Runner self-update completed and the project scan returned successfully. Call health to verify the active runner version.` after `system.project.requestScan(scanTimeoutSeconds)` returns and `scanCompleted:true` has been set.
- Dry-run responses still use `Self-update dry run passed. No files were changed.`

`0.3.115+` self-update mid-write failure behavior:

- An exception after self-update backup planning or after the `doPost.py` write returns `MID_WRITE_FAILURE` with `writeFailure`, `backupName`, `failedStage`, `writesStarted`, `writtenPaths`, `recoveryRequired`, and `rollbackAvailable` metadata.

## Operational Notes

- `apply`, `projectResourceImportZip`, confirmed `projectResourceDelete`, `rollback`, and `runnerSelfUpdate` run bounded `system.project.requestScan(scanTimeoutSeconds)` waits after confirmed writes. Runner `0.3.105+` accepts `scanTimeoutSeconds` as `1..30`, default `10`; runner `0.3.136+` attempts two waits when `filesChanged:true` and reports `scanWaitsAttempted`, `scanWaitsCompleted`, and `defensiveSecondScanWait`. Scan responses also report `scanCompleted`, legacy `scanRequested`, `scanTimeoutSeconds`, `filesChanged`, `recoveryRequired`, and optional `scanError`.
- Runner `0.3.85+` serializes package `dryRun`, `apply`, `projectResourceImportZip`, `rollback`, and `runnerSelfUpdate` with the Gateway-wide mutation lock. Runner `0.3.114+` also serializes confirmed `tagConfigure`, `tagEventScriptProbe`, `udtTagEventScriptProbe`, and `udtScaffold` calls with that lock. Runner `0.3.200+` adds confirmed `projectResourceDelete`; its dry-run remains non-blocking.
- Runner `0.3.86+` stages final project-resource file writes/copies to sibling temporary paths before Java NIO atomic moves.
- Runner `0.3.87+` preserves existing `resource.json` `attributes` keys when stamping runner-managed project resources, replacing only Ignition's automatic last-modification fields.
- Runner `0.3.88+` treats scan failure after files changed as non-successful and returns `PROJECT_SCAN_FAILED` with `recoveryRequired: true`.
- Runner `0.3.89+` honors all six documented `IGNITION_LLM_*` path environment overrides in both runner variants and reports their configured state in `gatewayInfo.environment`.
- Runner `0.3.90+` cleans package `dryRun` and `apply` temporary work directories by default. Use `keepWorkDir: true` only for target-local diagnostics and inspect `workDirCleanupStatus` before relying on cleanup evidence.
- Runner `0.3.91+` appends a short UUID suffix to runner-generated fallback request IDs and generated work/backup names. Echoed caller `requestId` values are unchanged.
- Runner `0.3.92+` adds `perspectiveSessionsQuery.matchedCount`; `truncated` now means matching sessions were omitted by `maxResults`, not merely that filtered-out project sessions were scanned.
- Runner `0.3.103+` includes sibling Web Dev `resource.json` in current `runnerSelfUpdate` `fileChanges-v1` backup manifests and reports `backupIncludesResourceJson: true`.
- Runner `0.3.105+` advertises `projectScanTimeoutControl` and bounds every writeful project scan timeout to at most 30 seconds.
- Runner `0.3.135+` advertises `runnerSelfUpdateScanCompletionMessage`; successful confirmed `runnerSelfUpdate` responses say the project scan returned successfully instead of telling callers to wait for a completed scan.
- Runner `0.3.136+` advertises `postWriteProjectScanSecondWait`; changed-file `apply`, `projectResourceImportZip`, `rollback`, and `runnerSelfUpdate` responses include `scanWaitsAttempted`, `scanWaitsCompleted`, and `defensiveSecondScanWait`.
- Runner `0.3.140+` advertises `projectResourceImportZipFinalManifestValidation`; final merged import resource manifests are validated before writes and fail with `RESOURCE_MANIFEST_INVALID` plus `manifestValidationPhase:"finalMergedResourceState"` when package/current state would leave missing listed files or unlisted managed files.
- Runner `0.3.141+` advertises `rollbackWriteFailureEnvelope`; rollback write/restore exceptions return `ROLLBACK_WRITE_FAILED` with backup, pre-rollback backup, failed-stage, changed-file, completed-step, and nested `rollbackFailure` metadata.
- Runner `0.3.142+` advertises `applyPackageStaleViewFilePruning`; package apply overwrites prune stale optional view-managed files such as `thumbnail.png` when the final manifest omits them, report `prunedStaleViewFiles` / `prunedStaleViewFileCount`, and use `validateCopiedViews` for post-copy manifest validation failures.
- Runner `0.3.143+` advertises `udtScaffoldUnknownFailureRecovery`; failed confirmed non-dry-run scaffold steps with missing, null, or empty `qualityCodes` are treated as unknown-mutated and recovery marks all step recovery paths by preflight. Dry-runs remain unchanged.
- Runner `0.3.144+` advertises `unfinishedFileChangeBackupRollbackRecovery`; unfinished `fileChanges-v1` backups are explicitly marked `afterStateKnown:false`, rollback reports `driftCheckSkipped:true`, and strict `afterSha256` drift checks remain reserved for completed backups.
- Runner `0.3.145+` advertises `applyNonViewFinalStateValidation`; package apply validates final copied Project Library script, Named Query, and Perspective page-config destination state after mutation and returns `MID_WRITE_FAILURE` with validation metadata instead of pruning unknown non-view files.
- Runner `0.3.200+` advertises `visionWindowStructuralInspection`; `visionWindowInspect` returns bounded XML component-layout diagnostics or binary-v2 format/token evidence and always reports `runtimeRenderVerified:false`.
- Runner `0.3.200+` advertises `projectResourceDeleteDryRun`, `projectResourceDeleteStateGuard`, and `projectResourceDeleteRollbackBackup`; confirmed deletion requires a current state hash plus exact confirmation, writes a `fileChanges-v1` backup, verifies absence after scan, and restores through normal rollback.
- Runner `0.3.111+` advertises `tagConfigureQualityFailureOkFalse`; bad or mismatched `tagConfigure` QualityCodes return top-level `ok:false`.
- Runner `0.3.112+` advertises `udtScaffoldStepAllGoodFailureOkFalse`; `udtScaffold` fails top-level when a nested configure step fails.
- Runner `0.3.113+` advertises `udtScaffoldPartialFailureRecovery`; failed confirmed scaffolds report recovery metadata and `recoveryRequired`.
- Runner `0.3.138+` advertises `udtScaffoldOverrideRecoveryMismatch`; failed member-override steps with mismatched recovery-path and QualityCode counts mark all step recovery paths when any returned QualityCode is Good.
- Runner `0.3.139+` advertises `tagProbeCleanupRecoveryFields`; failed tag-event probe responses promote cleanup status to top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired` fields.
- Runner `0.3.114+` advertises `tagMutationLocking`; confirmed tag mutation actions return retryable `MUTATION_LOCK_BUSY` instead of running concurrently with another mutation.
- Runner `0.3.115+` advertises `midWriteFailureRecoveryMetadata`; mid-write exceptions in `apply`, confirmed `projectResourceImportZip`, and confirmed `runnerSelfUpdate` return `MID_WRITE_FAILURE` with backup, written-path, failed-stage, and rollback-availability metadata.
- Use `pageValidate`, `viewRead`, focused `logQuery`, and browser validation after applying a page.
- Do not add broad arbitrary Gateway writes to this runner. Keep new API actions narrow, allowlisted, capped, dry-run-first, and page-building driven.


## Runner 0.3.200 Vision Capability Addendum

Runner 0.3.200 adds live-tested Vision resource-name validation, structural and spatial window inspection, dependency preflight, native client session inventory, screenshots, text-fit evidence, focused client logs, and fixed chart/table probes with explicit state restoration. Use `health` as the source of truth for exact supported action and feature names on the installed runner.
