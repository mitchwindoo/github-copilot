# Simplest Ignition 8.1 LLM Runner

Stack version: `starter-2026.07.14.01`
Runner API version: `0.3.200`

For the fastest setup, open `00_START_HERE_API_SETUP.md` first. It contains the two-minute Designer install and a copy-ready read-only verification prompt.

Use this reference when you want the setup to remain as close as possible to:

```text
Paste one script, publish, then give the AI agent the endpoint and token.
```

For AI-platform installation, read `PLATFORM_SKILL_INSTALL_GUIDE.md` first. Use this document only for installing the Ignition Web Dev runner after the skill is installed in Codex, ChatGPT, Claude, Cowork, or Claude Code.

For action payloads, confirmations, response shapes, and per-action behavior, read `WEBDEV_RUNNER_API_REFERENCE.md`.

Runner `0.3.200+` adds bounded Vision window structural inspection and guarded project-resource deletion with dry-run, state hash, exact confirmation, rollback backup, and post-scan absence verification.

This creates one Web Dev POST endpoint. The LLM sends the generated Perspective project zip as base64 JSON. The endpoint applies only allowed Perspective views/routes, backs up existing resources, and runs bounded `system.project.requestScan(scanTimeoutSeconds)` waits.

Runner `0.3.109+` keeps the same direct-paste API surface and aligns package metadata with the Project Library `projectsList` helper fix; no new feature flag is required.

Runner `0.3.110+` keeps the same direct-paste behavior and aligns package metadata with the Project Library `allowOverwrite` string-boolean fix; no new feature flag is required.

Runner `0.3.111+` advertises `tagConfigureQualityFailureOkFalse`; confirmed `tagConfigure` applies now fail with `statusCode: 400` when Ignition returns a bad `QualityCode` or an unexpected returned-code count.

Runner `0.3.112+` advertises `udtScaffoldStepAllGoodFailureOkFalse`; `udtScaffold` now fails fast when a nested `tagConfigure` step returns `ok: false` or `allGood: false`.

Runner `0.3.113+` advertises `udtScaffoldPartialFailureRecovery`; failed confirmed scaffolds attempt to clean up created roots, restore modified existing roots from preflight snapshots, and report `recoveryRequired: true` if cleanup or restore fails.

Runner `0.3.114+` advertises `tagMutationLocking`; confirmed tag mutation actions share the Gateway-wide mutation lock and return retryable `MUTATION_LOCK_BUSY` responses while another mutation is active. Tag dry-runs remain non-blocking.

Runner `0.3.115+` advertises `midWriteFailureRecoveryMetadata`; mid-write exceptions in `apply`, confirmed `projectResourceImportZip`, and confirmed `runnerSelfUpdate` return `MID_WRITE_FAILURE` with backup, failed-stage, written-path, recovery-required, and rollback-availability metadata.

Runner `0.3.116+` advertises `rollbackRemovalFailureReporting`; confirmed `fileChanges-v1` rollback reports verified actual removals and returns `ROLLBACK_REMOVAL_FAILED` with `failedRemovals` when target-file or empty-directory deletes fail postcondition checks.

Runner `0.3.118+` advertises `rollbackAfterSha256DriftGuard`; `fileChanges-v1` rollback rejects stale `afterSha256` assumptions before mutation unless the caller intentionally uses `forceDriftedRollback: "FORCE_ROLLBACK_DRIFT"` with the normal rollback confirmation.

Runner `0.3.119+` advertises `projectTargetValidation`; project-scoped actions reject `targetProject` values that are not canonical direct child project directories with a regular-file JSON-object `project.json`.

Runner `0.3.120+` advertises `applyPackageSingleProjectRoot`; package `dryRun` and `apply` reject ZIPs containing multiple `project.json` roots with `MULTIPLE_PACKAGE_PROJECT_ROOTS` and `packageProjectRootCandidates` before validation, backup planning, writes, or scan.

Runner `0.3.121+` advertises `projectResourceManifestValidation`; runner-managed Perspective view, Project Library script, Named Query, and page-config `resource.json.files` manifests are validated before writes, backup planning, or scan.

Runner `0.3.122+` advertises `atomicCopyTreeDestinationPreservation`; runner directory backup/rollback copies preserve the existing destination through a three-path swap and attempt to restore it if final promotion fails.

Runner `0.3.124+` advertises `applyPackageInvalidDataErrors`; malformed `packageBase64` and decoded Base64 bytes without a ZIP signature return structured HTTP/status `400` errors before work-directory creation, writes, backups, or scans.

Runner `0.3.125+` advertises `jythonScriptSyntaxLintLiteralAware`; Perspective script lint ignores Python 3-only marker examples inside comments and string literals while still rejecting executable Python 3-only syntax for Jython 2.7 compatibility.

Runner `0.3.126+` advertises `auditQueryGlobalMaxResults`; `auditQuery.maxResults` caps aggregate returned rows across all requested audit profiles and successful responses include `maxResultsScope: "global"`.

Runner `0.3.127+` advertises `backendScopeRowBoundMetadata`; alarm/audit query responses report `backendScopeRestricted`, `backendRowBounded: false`, `responseRowsBounded: true`, and `minimumFilterLiteralChars: 2` instead of claiming Ignition backend rows are row-limited.

Runner `0.3.128+` advertises `strictQueryInputValidation`; invalid `logQuery`, `alarmStatusQuery`, `alarmJournalQuery`, and `auditQuery` filter strings/lists return structured HTTP/status `400` errors before log scanning or Ignition backend calls instead of being silently modified.

Runner `0.3.129+` advertises `metricsSnapshotJvmGlobalSequence`; `metricsSnapshot.sequence` is stored in `system.util.getGlobals()` and increments for the Gateway JVM lifetime, including repeated direct-paste Web Dev requests.

Runner `0.3.131+` advertises `metricsSnapshotIntegralNumberPrecision`; large metric counts, gauge values, JVM byte/nanosecond counters, Java integral values, and histogram `min` / `max` values preserve exact integral precision before floating conversion.

Runner `0.3.132+` advertises `filesystemDiscoverySortBeforeCap`; truncated filesystem discovery responses sort all eligible candidates before applying `maxResults`.
Runner `0.3.134+` advertises `sourceVariantDispatchParity`; direct-paste and Project Library deployments return the same structured unknown-action and missing-apply-confirmation errors, expose matching health directory-exists aliases, use the same default `packageName`, and include `mode` plus `inboxDir` on package dry-run/apply success.

Runner `0.3.135+` advertises `runnerSelfUpdateScanCompletionMessage`; successful confirmed `runnerSelfUpdate` responses say the project scan returned successfully because `system.project.requestScan(scanTimeoutSeconds)` has already returned.

Runner `0.3.136+` advertises `postWriteProjectScanSecondWait`; after `filesChanged:true`, confirmed `apply`, `projectResourceImportZip`, `rollback`, and `runnerSelfUpdate` attempt two bounded project-scan waits and report `scanWaitsAttempted`, `scanWaitsCompleted`, and `defensiveSecondScanWait`. These fields report the wait sequence only; they are not overlap detection or loaded-resource proof.

Runner `0.3.137+` advertises `historyProbeGoodSampleTerminology`; `historyProbe` now exposes `goodSampleHistoryAvailable`, `goodStoredSampleCount`, and per-tag `tagStats[].goodStoredSampleCount` for Count-query availability. Compatibility `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` remain aliases. A false/zero good-sample result does not rule out bad-quality historical rows.

Runner `0.3.133+` advertises `zipDuplicateEntryRejection`; package `dryRun`/`apply` and `projectResourceImportZip` reject duplicate normalized ZIP entries with `PACKAGE_ZIP_INVALID` before validation, writes, backups, or scans.

Runner `0.3.139+` advertises `tagProbeCleanupRecoveryFields`; failed tag-event probe cleanup status is promoted to top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired`.

Runner `0.3.140+` advertises `projectResourceImportZipFinalManifestValidation`; final merged import resource manifests are checked before writes and fail with `RESOURCE_MANIFEST_INVALID` plus `manifestValidationPhase:"finalMergedResourceState"` when listed/missing file state would be inconsistent.

Runner `0.3.141+` advertises `rollbackWriteFailureEnvelope`; rollback write/restore exceptions return `ROLLBACK_WRITE_FAILED` with selected backup, pre-rollback backup, failed-stage, changed-file, completed-step, and nested `rollbackFailure` metadata.

Runner `0.3.142+` advertises `applyPackageStaleViewFilePruning`; package apply overwrites of Perspective views prune stale optional managed files such as `thumbnail.png` when the final manifest omits them, and responses report `prunedStaleViewFiles` / `prunedStaleViewFileCount`.

Runner `0.3.143+` advertises `udtScaffoldUnknownFailureRecovery`; failed confirmed non-dry-run `udtScaffold` nested `tagConfigure` steps with missing, null, or empty `qualityCodes` mark all step recovery paths as unknown-mutated by preflight so recovery can delete or restore them. Dry-runs remain unchanged.

Runner `0.3.144+` advertises `unfinishedFileChangeBackupRollbackRecovery`; unfinished `fileChanges-v1` backups from failed mid-write `apply`, `projectResourceImportZip`, or `runnerSelfUpdate` writes carry `afterStateKnown:false`, `backupManifestComplete:false`, `rollbackDriftCheckMode:"unknown-after-state"`, and rollback responses report `driftCheckSkipped:true`. Completed backups still enforce `ROLLBACK_DRIFT_DETECTED`.

Runner `0.3.145+` advertises `applyNonViewFinalStateValidation`; confirmed apply validates final Project Library script, Named Query, and Perspective page-config destination state after mutation and fails before scan/success with `MID_WRITE_FAILURE` validation metadata instead of pruning unknown non-view files.

Runner `0.3.146+` adds live Perspective runtime actions for session pages, live page views, and dry-run/confirmed Perspective session termination. Treat these as runtime/session diagnostics and control, not project page authoring.

Runner `0.3.147+` adds Gateway-level Perspective asset actions for themes, fonts, icon libraries, and branding metadata. Writes default to dry-run, require exact upsert confirmations, and report restart/refresh caveats.

Runner `0.3.148+` verifies Perspective session termination with follow-up discovery, enforces strict session/page matching for live view discovery, and lists Perspective module asset backups with `_gateway` metadata in `backupList`.

## One-Time Designer Setup

1. Open Designer.
2. Open the project that will host the API endpoint.
3. In Project Browser, right-click `Web Dev`.
4. Create a new Python Resource, for example `llmImport`.
5. Select `doPost`.
6. Check `Enabled`.
7. Paste the whole script from:

```text
webdev-runner/simple_webdev_do_post_body.py
```

8. Set `TOKEN` near the top of the pasted script to a unique long random value before publishing. For an environment-managed production token, leave `TOKEN = ""` and configure the Gateway service environment variable:

```text
IGNITION_LLM_RUNNER_TOKEN
```

Runner `0.3.89+` also honors optional Gateway service environment variables for runner paths:

```text
IGNITION_LLM_GATEWAY_DATA_DIR
IGNITION_LLM_PROJECTS_ROOT
IGNITION_LLM_RUNNER_ROOT
IGNITION_LLM_RUNNER_INBOX
IGNITION_LLM_RUNNER_WORK
IGNITION_LLM_RUNNER_BACKUPS
```

Restart the Gateway service after changing service environment variables so the Gateway JVM can read them.

9. Save/publish the project.

Your endpoint is:

```text
<gatewayUrl>/system/webdev/<projectName>/llmImport
```

If you put the resource inside a Web Dev folder, include the folder in the URL:

```text
<gatewayUrl>/system/webdev/<projectName>/<folderName>/llmImport
```

## Give The LLM

Give the LLM only:

```text
endpoint: <gatewayUrl>/system/webdev/<projectName>/llmImport
token: <token>
targetProject: <projectName>
allowedViewPrefix: LLM Tests/
allowedRoutePrefix: /llm-
```

## Health Check

```json
{
  "token": "<token>",
  "action": "health"
}
```

Expected response includes:

```json
{
  "ok": true,
  "projectsRootExists": true,
  "tokenConfigured": true
}
```

If the endpoint returns HTTP 200 with an empty body, the Web Dev method is reachable but the runner is not executing. Reopen the Web Dev resource and confirm `doPost` contains the full `simple_webdev_do_post_body.py` script, including the final `return main()` line.

For runner `0.3.107+`, `supportedActions` is the callable action catalog. Use `features` only for non-action capability flags such as the versioned checks below.

For runner `0.3.86+`, `features` should include `atomicProjectResourceFileWrites` when relying on runner-managed final project-resource file writes. For runner `0.3.87+`, `features` should include `projectResourceAttributePreservation` when relying on runner-managed resource metadata stamping to preserve existing `resource.json` `attributes`. For runner `0.3.88+`, `features` should include `projectScanFailureIsFailure` when relying on `scanCompleted` and recovery-required scan failure reporting after writes. For runner `0.3.89+`, `features` should include `environmentPathOverrides` when relying on runner path environment variables. For runner `0.3.90+`, `features` should include `applyPackageWorkDirCleanup` when relying on default cleanup of package apply work directories. For runner `0.3.91+`, `features` should include `uniqueIdStamps` before relying on generated request/work/backup names being collision-resistant within the same millisecond. For runner `0.3.92+`, `features` should include `perspectiveSessionsQueryMatchedCount` before relying on filtered `perspectiveSessionsQuery.truncated` semantics. For runner `0.3.93+`, `features` should include `historyProbeSampleBackedAvailability` before relying on sample-count-backed `historyProbe` availability. For runner `0.3.137+`, `features` should include `historyProbeGoodSampleTerminology` before relying on `goodSampleHistoryAvailable` / `goodStoredSampleCount` names; false/zero means no good-quality Count samples were returned, not that no bad-quality rows exist. For runner `0.3.94+`, `features` should include `tagEventProbeSynchronousWaitCap` before relying on bounded effective `tagEventScriptProbe` or `udtTagEventScriptProbe` polling metadata. For runner `0.3.95+`, `features` should include `tagEventProbeFailureCleanup` before relying on best-effort cleanup metadata for failed tag-event probe applies. For runner `0.3.96+`, `features` should include `backendQueryWorkBounds` before relying on scope-restricted alarm/audit or DB-bounded Named Query preview work. For runner `0.3.97+`, `features` should include `alarmJournalExplicitProfileRequired` before relying on rejection of default/omitted alarm journal profile requests. For runner `0.3.98+`, `features` should include `pathPrefixBoundaryMatching` before relying on exact-or-child prefix matching for views, routes, scripts, Named Queries, dependencies, shared docks, and project resources. For runner `0.3.99+`, `features` should include `namedQueryTopLevelRowLimitScanner` before relying on top-level-only Named Query SQL row-limit classification. For runner `0.3.100+`, `features` should include `threadDumpStreamingSha256` before relying on `threadDumpQuery` integrity hashes without retaining a full raw dump list. For runner `0.3.101+`, `features` should include `explicitUtf8TextFileIo` before relying on exact non-ASCII project-resource, script, query, backup manifest, or runner self-update text round-trips. For runner `0.3.102+`, `features` should include `projectResourceImportZipLegacyRollback` before relying on legacy import backup restore or fatal missing-backup-file rollback validation. For runner `0.3.103+`, `features` should include `runnerSelfUpdateResourceJsonRollback` before relying on self-update rollback to restore the sibling Web Dev `resource.json`. For runner `0.3.104+`, `features` should include `runnerSelfUpdateExactBackup` before relying on current self-update rollback to restore exact `doPost.py` source, including any literal static token assignments present in the source. For runner `0.3.105+`, `features` should include `projectScanTimeoutControl` before relying on `scanTimeoutSeconds` defaults/range for writeful project scans. For runner `0.3.108+`, `features` should include `primaryQueryFailureOkFalse` before relying on top-level `ok: false` envelopes for primary backend failures in `historyProbe`, `alarmStatusQuery`, `alarmJournalQuery`, and all-failed `auditQuery`. For runner `0.3.111+`, `features` should include `tagConfigureQualityFailureOkFalse` before relying on top-level tag configure failure envelopes for bad QualityCodes. For runner `0.3.112+`, `features` should include `udtScaffoldStepAllGoodFailureOkFalse` before relying on scaffold fail-fast behavior for nested configure failures. For runner `0.3.113+`, `features` should include `udtScaffoldPartialFailureRecovery` before relying on scaffold recovery metadata. For runner `0.3.114+`, `features` should include `tagMutationLocking` before relying on mutation-lock serialization for confirmed tag mutation actions. For runner `0.3.115+`, `features` should include `midWriteFailureRecoveryMetadata` before relying on `MID_WRITE_FAILURE` recovery metadata for mid-write exceptions in `apply`, confirmed `projectResourceImportZip`, or confirmed `runnerSelfUpdate`. For runner `0.3.116+`, `features` should include `rollbackRemovalFailureReporting` before relying on verified actual rollback removals or `ROLLBACK_REMOVAL_FAILED` failed-removal metadata. For runner `0.3.118+`, `features` should include `rollbackAfterSha256DriftGuard` before relying on rollback `afterSha256` drift rejection or `backupAfterScanRefreshed` metadata. For runner `0.3.119+`, `features` should include `projectTargetValidation` before relying on strict `targetProject` project-directory validation.

For runner `0.3.120+`, `features` should include `applyPackageSingleProjectRoot` before relying on package `dryRun` or `apply` to reject ZIPs with multiple `project.json` roots.

For runner `0.3.121+`, `features` should include `projectResourceManifestValidation` before relying on malformed managed `resource.json.files` manifests being rejected with `RESOURCE_MANIFEST_INVALID` before writes, backup planning, or scan.

For runner `0.3.122+`, `features` should include `atomicCopyTreeDestinationPreservation` before relying on rollback/backup directory copies to preserve the existing destination when final tree promotion fails.
For runner `0.3.124+`, `features` should include `applyPackageInvalidDataErrors` before relying on `PACKAGE_BASE64_INVALID` or `PACKAGE_ZIP_INVALID` validation envelopes from package `dryRun` and `apply`.
For runner `0.3.125+`, `features` should include `jythonScriptSyntaxLintLiteralAware` before relying on Perspective script lint to ignore Python 3-only marker examples inside comments or string literals.
For runner `0.3.126+`, `features` should include `auditQueryGlobalMaxResults` before relying on `auditQuery.maxResults` as a global response row cap across multiple profiles. For runner `0.3.127+`, `features` should include `backendScopeRowBoundMetadata` before relying on alarm/audit `backendScopeRestricted`, `backendRowBounded`, `responseRowsBounded`, `minimumFilterLiteralChars`, or `BACKEND_SCOPE_FILTER_TOO_BROAD` metadata. For runner `0.3.128+`, `features` should include `strictQueryInputValidation` before relying on query filter validation errors such as `FILTER_LIMIT_EXCEEDED`, `FILTER_VALUE_TOO_LONG`, or `FILTER_CONTROL_CHARACTERS`. For runner `0.3.129+`, `features` should include `metricsSnapshotJvmGlobalSequence` before relying on `metricsSnapshot.sequence` to increment across repeated direct-paste Web Dev requests for the Gateway JVM lifetime. For runner `0.3.131+`, `features` should include `metricsSnapshotIntegralNumberPrecision` before relying on exact precision for large metric counts, gauge values, JVM byte/nanosecond counters, Java integral values, gauge values, or histogram `min` / `max` fields. For runner `0.3.132+`, `features` should include `filesystemDiscoverySortBeforeCap` before relying on stable sorted-first truncated subsets from filesystem discovery actions. For runner `0.3.133+`, `features` should include `zipDuplicateEntryRejection` before relying on duplicate normalized ZIP entries being rejected before package/import validation or writes. For runner `0.3.134+`, `features` should include `sourceVariantDispatchParity` before relying on direct-paste and Project Library parity for unknown-action errors, missing apply-confirmation errors, health aliases, package-name defaults, and package dry-run/apply response shape. For runner `0.3.135+`, `features` should include `runnerSelfUpdateScanCompletionMessage` before relying on the corrected confirmed `runnerSelfUpdate` success message that says the project scan returned successfully. For runner `0.3.136+`, `features` should include `postWriteProjectScanSecondWait` before relying on the two-wait post-write scan sequence and `scanWaitsAttempted` / `scanWaitsCompleted` response fields. For runner `0.3.137+`, `features` should include `historyProbeGoodSampleTerminology` before relying on the precise good-sample historyProbe field names.

## Tag Discovery

The runner supports read-only tag discovery so an LLM can inspect providers and tag paths before building Perspective bindings.

List tag providers:

```json
{
  "token": "<token>",
  "action": "tagProviders",
  "maxResults": 100
}
```

Browse tags under a provider or folder:

```json
{
  "token": "<token>",
  "action": "tagBrowse",
  "provider": "<tagProvider>",
  "path": "",
  "recursive": false,
  "maxResults": 500
}
```

Browse recursively under a known folder:

```json
{
  "token": "<token>",
  "action": "tagBrowse",
  "path": "[<tagProvider>]<folderPath>",
  "recursive": true,
  "maxResults": 1000
}
```

`includeValues` defaults to `false`. Only set it to `true` for small, intentional reads because tag values can be noisy or sensitive.

Always send a `maxResults` cap. Runner `0.3.83+` reports `returnedCount`, `returnedSize`, `totalAvailable`, and `truncated`; if `truncated` is true or `totalAvailable > returnedCount`, narrow the path/filter or increase the cap before treating the browse as complete.

## Dry Run

The LLM should base64-encode the generated zip and send:

```json
{
  "token": "<token>",
  "action": "dryRun",
  "targetProject": "<projectName>",
  "packageName": "llm-perspective-package.zip",
  "packageBase64": "<base64-zip>",
  "allowOverwrite": false,
  "allowedViewPrefix": "LLM Tests/",
  "allowedRoutePrefix": "/llm-",
  "routes": [
    {
      "pagePath": "/llm-example",
      "viewPath": "LLM Tests/Example",
      "title": "Example"
    }
  ]
}
```

Prefer the explicit `routes` list. Auto-discovery is only safe when the package page config contains exactly the intended `/llm-...` routes and every referenced `LLM Tests/...` view is included in the zip.

## Apply

After dry-run passes:

```json
{
  "token": "<token>",
  "action": "apply",
  "confirmApply": "APPLY",
  "targetProject": "<projectName>",
  "packageName": "llm-perspective-package.zip",
  "packageBase64": "<base64-zip>",
  "allowOverwrite": false,
  "allowedViewPrefix": "LLM Tests/",
  "allowedRoutePrefix": "/llm-",
  "routes": [
    {
      "pagePath": "/llm-example",
      "viewPath": "LLM Tests/Example",
      "title": "Example"
    }
  ]
}
```

The response should include:

```json
{
  "ok": true,
  "copiedViews": ["LLM Tests/Example"],
  "mergedRoutes": ["/llm-example"],
  "backupDir": "<gatewayDataDir>/llm-runner/backups/<projectName>-<timestamp>",
  "filesChanged": true,
  "scanCompleted": true,
  "scanRequested": true,
  "scanWaitsAttempted": 2,
  "scanWaitsCompleted": 2,
  "defensiveSecondScanWait": true,
  "recoveryRequired": false,
  "keepWorkDir": false,
  "workDirKept": false,
  "workDirCleaned": true,
  "workDirCleanupStatus": "cleaned"
}
```

Runner `0.3.86+` stages final project-resource file writes and file copies to sibling temporary paths before Java NIO atomic moves. Runner `0.3.87+` preserves existing `resource.json` `attributes` keys when stamping runner-managed project resources, replacing only Ignition's automatic last-modification fields. Runner `0.3.88+` uses `scanCompleted` as the authoritative post-write project scan field; if files changed and the scan fails, it returns `PROJECT_SCAN_FAILED` with `recoveryRequired: true`. Runner `0.3.90+` removes package apply work directories by default and reports `workDirCleanupStatus`. Runner `0.3.91+` appends a short UUID suffix to generated fallback request IDs and generated work/backup names. Runner `0.3.92+` adds `perspectiveSessionsQuery.matchedCount` and reports `truncated` only when matching sessions exceed `maxResults`. Runner `0.3.93+` makes `historyProbe` availability sample-count backed; runner `0.3.137+` exposes precise good-sample fields and keeps older history fields as aliases. Runner `0.3.94+` caps effective tag-event probe polling and returns `requestedPollAttempts`, effective `pollAttempts`, `pollAttemptsCapped`, and probe wait metadata. Runner `0.3.95+` adds best-effort cleanup metadata for failed tag-event probe applies and attempts to delete only the fresh planned probe fixture paths. Runner `0.3.96+` adds backend query work bounds for alarm, audit, and Named Query preview diagnostics. Runner `0.3.97+` requires explicit Alarm Journal profile names for `alarmJournalQuery` and rejects default/omitted journal flags before calling Ignition. Runner `0.3.98+` adds exact-or-child prefix matching; `LLM Tests/A` does not allow `LLM Tests/ABC`, while `/llm-` remains the route namespace for `/llm-...` pages and default `llm` still allows root-level `llm...` Project Library script modules. Runner `0.3.99+` classifies Named Query SQL row-limit proof at the top-level outer query only; nested-only limiters, `TOP PERCENT`, `TOP/FETCH WITH TIES`, dynamic limits, and nonliteral limits reject unless a safe Named Query max return size is enabled. Runner `0.3.100+` streams thread dump text into SHA-256 for `unredactedDumpSha256` without retaining a full raw dump list. Runner `0.3.101+` explicitly uses UTF-8 for runner-managed text file reads/writes while keeping ZIP, log-tail, backup-copy, and hash byte paths binary. Runner `0.3.102+` rejects damaged `fileChanges-v1` rollback manifests with missing backup files before mutation and can restore backed-up overwritten files from legacy `projectResourceImportZip` backup folders. Runner `0.3.103+` includes both Web Dev `doPost.py` and sibling `resource.json` in current `runnerSelfUpdate` `fileChanges-v1` rollback manifests. Runner `0.3.104+` stores exact pre-update `doPost.py` source in current self-update backups and reports `backupExactSource: true` plus `backupTokenRedacted: false`. Runner `0.3.105+` accepts bounded `scanTimeoutSeconds` for writeful project scans; allowed values are `1..30`, default `10`. Runner `0.3.136+` attempts two bounded waits after `filesChanged:true` and returns `scanWaitsAttempted`, `scanWaitsCompleted`, and `defensiveSecondScanWait`.

## What It Allows

- Perspective views under exact-or-child `allowedViewPrefix`.
- Perspective page routes under exact-or-child `allowedRoutePrefix`, including the documented `/llm-...` route namespace.
- Package route discovery from the package page config.
- Explicit route list if needed.
- Read-only tag provider/path discovery through `system.tag.browse`.
- Backups before apply.

## What It Rejects

- Tags, tag providers, database connections, OPC devices, users, roles, modules, certificates.
- Zip entries with absolute paths, drive letters, or `..`.
- Views outside exact-or-child `allowedViewPrefix`.
- Routes outside exact-or-child `allowedRoutePrefix`, except the documented `/llm-...` route namespace.
- Existing routes/views unless `allowOverwrite` is true.

## Notes

This is the easiest bootstrap, not the most enterprise-perfect version. Use HTTPS and Web Dev authentication/roles when moving beyond local development.






