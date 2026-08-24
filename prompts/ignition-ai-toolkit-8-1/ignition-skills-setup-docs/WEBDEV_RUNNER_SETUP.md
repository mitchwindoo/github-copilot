# Ignition 8.1 Web Dev Runner Setup

Stack version: `starter-2026.07.14.01`
Runner API version: `0.3.200`

Start with `00_START_HERE_API_SETUP.md` for the two-minute direct-paste install and copy-ready read-only verification prompt. Return here for the advanced Project Library deployment and operating details.

This runner gives an AI agent a controlled way to apply generated Perspective views and page routes on a Gateway without using the Gateway browser file picker.

For AI-platform skill installation, read `PLATFORM_SKILL_INSTALL_GUIDE.md` first. Use this document only for installing and operating the Ignition Web Dev runner.

For action payloads, confirmations, response shapes, and per-action behavior, read `WEBDEV_RUNNER_API_REFERENCE.md`.

Runner `0.3.200+` adds read-only `visionWindowInspect` and guarded `projectResourceDelete`. The delete path defaults to dry-run, requires a current resource-state hash plus exact confirmation for apply, creates a `fileChanges-v1` backup, and restores through normal rollback. Treat Vision inspection as structural evidence; it does not prove client rendering.

It is intentionally narrow:

- It reads a zip from `packageBase64` or a fixed runner inbox folder.
- It copies only selected Perspective view resources under an allowed view prefix.
- It merges only requested page routes under an allowed route prefix.
- It backs up affected resources before applying.
- Runner `0.3.86+` stages final project-resource file writes and file copies to sibling temporary paths before Java NIO atomic moves.
- Runner `0.3.87+` preserves existing `resource.json` `attributes` keys when stamping runner-managed project resources, replacing only Ignition's automatic last-modification fields.
- Runner `0.3.88+` reports post-write project scan completion explicitly and treats scan failure after changed files as a recovery-required mutation failure.
- Runner `0.3.89+` honors all documented runner path environment overrides in both runner variants.
- Runner `0.3.90+` cleans temporary package apply work directories by default unless `keepWorkDir: true` is supplied for diagnostics.
- Runner `0.3.91+` appends a short UUID suffix to runner-generated fallback request IDs and generated work/backup names.
- Runner `0.3.92+` reports `perspectiveSessionsQuery.matchedCount`; filtered session responses are truncated only when matching sessions exceed `maxResults`.
- Runner `0.3.137+` reports precise good-sample history fields: `historyProbe.goodSampleHistoryAvailable`, `goodStoredSampleCount`, and per-tag `tagStats[].goodStoredSampleCount`. Compatibility `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` remain aliases. A false/zero good-sample result does not rule out bad-quality historical rows.
- Runner `0.3.94+` caps effective synchronous waits for `tagEventScriptProbe` and `udtTagEventScriptProbe`; inspect `tagEventProbeSynchronousWaitCap`, `pollAttemptsCapped`, and `probeSyncWaitMaxMs`.
- Runner `0.3.95+` attempts best-effort cleanup of freshly planned tag-event probe fixture paths after post-create apply failures; inspect `tagEventProbeFailureCleanup`, `failureCleanupPaths`, and failed-apply `failureCleanup`.
- Runner `0.3.96+` restricts alarm/audit query scope and DB-bounds Named Query preview work before execution; inspect `backendQueryWorkBounds` before relying on the narrower alarm/audit filters or preview row-cap contract.
- Runner `0.3.97+` requires explicit Alarm Journal profile names for `alarmJournalQuery`; inspect `alarmJournalExplicitProfileRequired` before relying on rejection of default/omitted journal flags.
- Runner `0.3.98+` uses exact-or-child prefix matching for logical path allowlists; inspect `pathPrefixBoundaryMatching` before relying on `LLM Tests/A` rejecting siblings such as `LLM Tests/ABC`.
- Runner `0.3.99+` classifies Named Query SQL row bounds at the top-level outer query only; inspect `namedQueryTopLevelRowLimitScanner` before relying on nested SQL limiter rejections.
- Runner `0.3.100+` streams thread dump text into SHA-256; inspect `threadDumpStreamingSha256` before relying on bounded `threadDumpQuery.unredactedDumpSha256` evidence without full raw dump retention.
- Runner `0.3.101+` explicitly uses UTF-8 for runner-managed text file reads/writes; inspect `explicitUtf8TextFileIo` before relying on exact non-ASCII JSON, script, Named Query SQL, or runner self-update text round-trips.
- Runner `0.3.102+` advertises `projectResourceImportZipLegacyRollback`; damaged `fileChanges-v1` rollback manifests with missing backup files are rejected before mutation, and legacy `projectResourceImportZip` backups can restore backed-up overwritten files.
- Runner `0.3.103+` advertises `runnerSelfUpdateResourceJsonRollback`; current self-update backups include both Web Dev `doPost.py` and sibling `resource.json` in their `fileChanges-v1` rollback plan.
- Runner `0.3.104+` advertises `runnerSelfUpdateExactBackup`; current self-update backups restore exact pre-update `doPost.py` source and responses report `backupExactSource: true` and `backupTokenRedacted: false`.
- Runner `0.3.105+` advertises `projectScanTimeoutControl`; writeful project scans accept bounded `scanTimeoutSeconds` values from `1` through `30`, default `10`.
- Runner `0.3.108+` advertises `primaryQueryFailureOkFalse`; primary backend failures in `historyProbe`, `alarmStatusQuery`, `alarmJournalQuery`, and all-failed `auditQuery` return top-level `ok: false` JSON errors while preserving action diagnostics.
- Runner `0.3.109+` fixes Project Library `projectsList` helper drift without adding a new feature flag, action, request field, response field, or confirmation string.
- Runner `0.3.110+` fixes Project Library `apply` boolean parsing for `allowOverwrite`; string values such as `"false"`, `"0"`, and `"no"` no longer enable overwrites. Direct-paste already used the correct parser, and no new feature flag is required.
- Runner `0.3.111+` advertises `tagConfigureQualityFailureOkFalse`; confirmed `tagConfigure` applies return `ok: false` with `statusCode: 400` when Ignition returns a bad `QualityCode` or a returned-code count mismatch.
- Runner `0.3.112+` advertises `udtScaffoldStepAllGoodFailureOkFalse`; `udtScaffold` stops with top-level `ok: false` when any nested `tagConfigure` step returns `ok: false` or `allGood: false`.
- Runner `0.3.113+` advertises `udtScaffoldPartialFailureRecovery`; failed confirmed scaffolds attempt to delete roots created by the same scaffold, restore existing roots from preflight snapshots, and set `recoveryRequired: true` if cleanup or restore fails.
- Runner `0.3.114+` advertises `tagMutationLocking`; confirmed `tagConfigure`, `tagEventScriptProbe`, `udtTagEventScriptProbe`, and `udtScaffold` calls share the Gateway-wide mutation lock and return retryable `MUTATION_LOCK_BUSY` responses while another mutation is active.
- Runner `0.3.115+` advertises `midWriteFailureRecoveryMetadata`; mid-write exceptions in `apply`, confirmed `projectResourceImportZip`, and confirmed `runnerSelfUpdate` return `MID_WRITE_FAILURE` with backup, failed-stage, written-path, recovery-required, and rollback-availability metadata.
- Runner `0.3.116+` advertises `rollbackRemovalFailureReporting`; confirmed `fileChanges-v1` rollback reports verified actual removals and returns `ROLLBACK_REMOVAL_FAILED` with `failedRemovals` when target-file or empty-directory deletes fail postcondition checks.
- Runner `0.3.118+` advertises `rollbackAfterSha256DriftGuard`; `fileChanges-v1` rollback rejects stale `afterSha256` assumptions before mutation unless the caller intentionally uses `forceDriftedRollback: "FORCE_ROLLBACK_DRIFT"` with the normal rollback confirmation.
- Runner `0.3.119+` advertises `projectTargetValidation`; project-scoped actions reject `targetProject` values that are not canonical direct child project directories with a regular-file JSON-object `project.json`.
- Runner `0.3.120+` advertises `applyPackageSingleProjectRoot`; package `dryRun` and `apply` reject ZIPs containing multiple `project.json` roots with `MULTIPLE_PACKAGE_PROJECT_ROOTS` and `packageProjectRootCandidates` before validation, backup planning, writes, or scan.
- Runner `0.3.121+` advertises `projectResourceManifestValidation`; runner-managed Perspective view, Project Library script, Named Query, and page-config `resource.json.files` manifests are validated before writes, backup planning, or scan.
- Runner `0.3.122+` advertises `atomicCopyTreeDestinationPreservation`; runner directory backup/rollback copies preserve the existing destination through a three-path swap and attempt to restore it if final promotion fails.
- Runner `0.3.124+` advertises `applyPackageInvalidDataErrors`; malformed `packageBase64` and decoded Base64 bytes without a ZIP signature return structured HTTP/status `400` errors before work-directory creation, writes, backups, or scans.
- Runner `0.3.125+` advertises `jythonScriptSyntaxLintLiteralAware`; Perspective script lint ignores Python 3-only marker examples inside comments and string literals while still rejecting executable Python 3-only syntax for Jython 2.7 compatibility.
- Runner `0.3.126+` advertises `auditQueryGlobalMaxResults`; `auditQuery.maxResults` caps aggregate returned rows across all requested audit profiles and successful responses include `maxResultsScope: "global"`.
- Runner `0.3.127+` advertises `backendScopeRowBoundMetadata`; alarm/audit query responses report `backendScopeRestricted`, `backendRowBounded: false`, `responseRowsBounded: true`, and `minimumFilterLiteralChars: 2` instead of claiming Ignition backend rows are row-limited.
- Runner `0.3.128+` advertises `strictQueryInputValidation`; invalid `logQuery`, `alarmStatusQuery`, `alarmJournalQuery`, and `auditQuery` filter strings/lists return structured HTTP/status `400` errors before log scanning or Ignition backend calls instead of being silently modified.
- Runner `0.3.129+` advertises `metricsSnapshotJvmGlobalSequence`; `metricsSnapshot.sequence` is stored in `system.util.getGlobals()` and increments for the Gateway JVM lifetime, including repeated direct-paste Web Dev requests.
- Runner `0.3.131+` advertises `metricsSnapshotIntegralNumberPrecision`; large metric counts, gauge values, JVM byte/nanosecond counters, Java integral values, and histogram `min` / `max` values preserve exact integral precision before floating conversion.
- Runner `0.3.132+` advertises `filesystemDiscoverySortBeforeCap`; truncated filesystem discovery responses sort all eligible candidates before applying `maxResults`.
- Runner `0.3.134+` advertises `sourceVariantDispatchParity`; direct-paste and Project Library deployments return the same structured unknown-action and missing-apply-confirmation errors, expose matching health directory-exists aliases, use the same default `packageName`, and include `mode` plus `inboxDir` on package dry-run/apply success.
- Runner `0.3.135+` advertises `runnerSelfUpdateScanCompletionMessage`; successful confirmed `runnerSelfUpdate` responses say the project scan returned successfully because `system.project.requestScan(scanTimeoutSeconds)` has already returned.
- Runner `0.3.136+` advertises `postWriteProjectScanSecondWait`; after `filesChanged:true`, confirmed `apply`, `projectResourceImportZip`, `rollback`, and `runnerSelfUpdate` attempt two bounded project-scan waits and report `scanWaitsAttempted`, `scanWaitsCompleted`, and `defensiveSecondScanWait`.
- Runner `0.3.137+` advertises `historyProbeGoodSampleTerminology`; use the good-sample history fields for Count-query availability, and treat the older fields as aliases only.
- Runner `0.3.133+` advertises `zipDuplicateEntryRejection`; package `dryRun`/`apply` and `projectResourceImportZip` reject duplicate normalized ZIP entries with `PACKAGE_ZIP_INVALID` before validation, writes, backups, or scans.
- Runner `0.3.139+` advertises `tagProbeCleanupRecoveryFields`; failed tag-event probe cleanup status is promoted to top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired`.
- Runner `0.3.140+` advertises `projectResourceImportZipFinalManifestValidation`; final merged import resource manifests are checked before writes and fail with `RESOURCE_MANIFEST_INVALID` plus `manifestValidationPhase:"finalMergedResourceState"` when listed/missing file state would be inconsistent.
- Runner `0.3.141+` advertises `rollbackWriteFailureEnvelope`; rollback write/restore exceptions return `ROLLBACK_WRITE_FAILED` with selected backup, pre-rollback backup, failed-stage, changed-file, completed-step, and nested `rollbackFailure` metadata.
- Runner `0.3.142+` advertises `applyPackageStaleViewFilePruning`; package apply overwrites of Perspective views prune stale optional managed files such as `thumbnail.png` when the final manifest omits them, and responses report `prunedStaleViewFiles` / `prunedStaleViewFileCount`.
- Runner `0.3.143+` advertises `udtScaffoldUnknownFailureRecovery`; failed confirmed non-dry-run `udtScaffold` nested `tagConfigure` steps with missing, null, or empty `qualityCodes` mark all step recovery paths as unknown-mutated by preflight so recovery can delete or restore them. Dry-runs remain unchanged.
- Runner `0.3.144+` advertises `unfinishedFileChangeBackupRollbackRecovery`; unfinished `fileChanges-v1` backups from failed mid-write `apply`, `projectResourceImportZip`, or `runnerSelfUpdate` writes carry `afterStateKnown:false`, `backupManifestComplete:false`, `rollbackDriftCheckMode:"unknown-after-state"`, and rollback responses report `driftCheckSkipped:true`. Completed backups still enforce `ROLLBACK_DRIFT_DETECTED`.
- Runner `0.3.145+` advertises `applyNonViewFinalStateValidation`; confirmed apply validates final Project Library script, Named Query, and Perspective page-config destination state after mutation and fails before scan/success with `MID_WRITE_FAILURE` validation metadata instead of pruning unknown non-view files.
- Runner `0.3.146+` adds live Perspective runtime actions for session pages, live page views, and dry-run/confirmed Perspective session termination. Treat these as runtime/session diagnostics and control, not project page authoring.
- Runner `0.3.147+` adds Gateway-level Perspective asset actions for themes, fonts, icon libraries, and branding metadata. Writes default to dry-run, require exact upsert confirmations, and report restart/refresh caveats.
- Runner `0.3.148+` verifies Perspective session termination with follow-up discovery, enforces strict session/page matching for live view discovery, and lists Perspective module asset backups with `_gateway` metadata in `backupList`.
- It runs bounded `system.project.requestScan(scanTimeoutSeconds)` waits after confirmed writes.
- It does not create tags, database connections, OPC devices, users, roles, certificates, or modules.

Use this first in a development or staging Gateway.

## Files

| File | Purpose |
|---|---|
| `webdev-runner/project_library_llm_runner.py` | Main Jython 2.7.3 Project Library script. |
| `webdev-runner/webdev_do_get.py` | One-line Web Dev `doGet` body. |
| `webdev-runner/webdev_do_post.py` | One-line Web Dev `doPost` body. |
| `webdev-runner/example-request.json` | Example dry-run request body. |

## Quick Path

The normal setup is now:

1. Set `IGNITION_LLM_RUNNER_TOKEN`.
2. Paste one Project Library script at `llm.runner`.
3. Paste two one-line Web Dev method bodies.
4. Call the health check.
5. Send the generated zip as `packageBase64`, or use the returned inbox path when the package-building account can write there.

The runner tries to auto-discover the Gateway data folder. If discovery works, it defaults to:

```text
projects_root: <gatewayDataDir>/projects
runner_root: <gatewayDataDir>/llm-runner
runner_inbox: <gatewayDataDir>/llm-runner/inbox
runner_work: <gatewayDataDir>/llm-runner/work
runner_backups: <gatewayDataDir>/llm-runner/backups
```

## Step 1: Pick Instance Values

Choose these values for your Gateway and store them in the instance profile, not in reusable skills:

```text
gateway_url: <gatewayUrl>
automation_project: <automationProject>
target_project: <projectName>
webdev_folder: llmRunner
webdev_resource: perspectiveImport
allowed_view_prefix: LLM Tests/
allowed_route_prefix: /llm-
token_source: Gateway environment variable IGNITION_LLM_RUNNER_TOKEN
```

Optional environment overrides:

```text
IGNITION_LLM_GATEWAY_DATA_DIR
IGNITION_LLM_PROJECTS_ROOT
IGNITION_LLM_RUNNER_ROOT
IGNITION_LLM_RUNNER_INBOX
IGNITION_LLM_RUNNER_WORK
IGNITION_LLM_RUNNER_BACKUPS
```

The runner auto-creates `inbox`, `work`, and `backups` when the health check or apply endpoint runs. The Ignition Gateway service account must have read/write access to those folders. The AI/package-building account needs write access to the inbox only when not using `packageBase64`.

Runner `0.3.89+` resolves those overrides before falling back to Gateway data-folder defaults and reports `_configured` booleans for all six path variables in `gatewayInfo.environment`. Restart the Gateway service after changing service environment variables so the Gateway JVM can read them.

## Step 2: Configure the Token

Preferred: set a Gateway service environment variable named:

```text
IGNITION_LLM_RUNNER_TOKEN
```

Use a long random value. Restart the Ignition Gateway service after setting the environment variable so the Gateway process can read it.

Development-only fallback: set `STATIC_TOKEN` inside `project_library_llm_runner.py`. Do not use that for production.

## Step 3: Add the Project Library Script

In Designer:

1. Open the project that will host the Web Dev endpoint.
2. Go to `Project Browser > Scripting > Project Library`.
3. Create a package named `llm`.
4. Create a script named `runner`.
5. Paste the contents of `webdev-runner/project_library_llm_runner.py`.

Keep the Project Library call path exactly:

```python
llm.runner
```

## Step 4: Add the Web Dev Resource

In the same Designer project:

1. Go to `Project Browser > Web Dev`.
2. Create a folder named `llmRunner`.
3. Create a Python Resource named `perspectiveImport`.
4. Enable `doGet`.
5. Paste the contents of `webdev-runner/webdev_do_get.py` into the `doGet` script body.
6. Enable `doPost`.
7. Paste the contents of `webdev-runner/webdev_do_post.py` into the `doPost` script body.

Do not paste `project_library_llm_runner.py` directly into the Web Dev `doPost` body. That file belongs in the Project Library at `llm.runner`. The Web Dev method bodies are only the one-line wrappers.

The endpoint will be:

```text
<gatewayUrl>/system/webdev/<automationProject>/llmRunner/perspectiveImport
```

## Step 5: Secure the Web Dev Resource

For development, at minimum use the runner token header.

For a safer setup:

1. Enable `Require Authentication` on the Web Dev Python Resource.
2. Select the correct User Source.
3. Restrict to a role such as `<automationRole>`.
4. Enable `Require HTTPS` if SSL is configured.
5. Keep the token header requirement enabled in the script.
6. Limit network access to the Gateway or endpoint if possible.

The request must include either:

```text
X-LLM-Runner-Token: <token>
```

or:

```text
Authorization: Bearer <token>
```

## Step 6: Health Check

Call `doGet` with the token:

```powershell
$headers = @{
  "X-LLM-Runner-Token" = "<token>"
}

Invoke-RestMethod `
  -Method Get `
  -Uri "<gatewayUrl>/system/webdev/<automationProject>/llmRunner/perspectiveImport" `
  -Headers $headers
```

Expected result:

```json
{
  "ok": true,
  "gatewayDataDir": "<gatewayDataDir>",
  "inboxDir": "<gatewayDataDir>/llm-runner/inbox",
  "workDir": "<gatewayDataDir>/llm-runner/work",
  "backupDir": "<gatewayDataDir>/llm-runner/backups",
  "projectsRootConfigured": true,
  "inboxConfigured": true,
  "workConfigured": true,
  "backupConfigured": true,
  "projectsRootExists": true,
  "inboxExists": true,
  "workExists": true,
  "backupExists": true,
  "inboxDirExists": true,
  "workDirExists": true,
  "backupDirExists": true
}
```

If the endpoint returns HTTP 200 with an empty body, the Web Dev method is reachable but not calling the runner. Check that `doGet` is `return llm.runner.handle_get(request, session)` and `doPost` is `return llm.runner.handle_post(request, session)`.

For runner `0.3.86+`, `features` should include `atomicProjectResourceFileWrites` when relying on runner-managed final project-resource file writes. For runner `0.3.87+`, `features` should include `projectResourceAttributePreservation` when relying on runner-managed resource metadata stamping to preserve existing `resource.json` `attributes`. For runner `0.3.88+`, `features` should include `projectScanFailureIsFailure` when relying on `scanCompleted` and recovery-required scan failure reporting after writes. For runner `0.3.89+`, `features` should include `environmentPathOverrides` when relying on any `IGNITION_LLM_*` runner path override. For runner `0.3.90+`, `features` should include `applyPackageWorkDirCleanup` when relying on default cleanup of package apply work directories. For runner `0.3.91+`, `features` should include `uniqueIdStamps` before relying on generated request/work/backup names being collision-resistant within the same millisecond. For runner `0.3.92+`, `features` should include `perspectiveSessionsQueryMatchedCount` before relying on filtered `perspectiveSessionsQuery.truncated` semantics. For runner `0.3.93+`, `features` should include `historyProbeSampleBackedAvailability` before relying on sample-count-backed `historyProbe` availability. For runner `0.3.137+`, `features` should include `historyProbeGoodSampleTerminology` before relying on `goodSampleHistoryAvailable` / `goodStoredSampleCount` names; false/zero means no good-quality Count samples were returned, not that no bad-quality rows exist. For runner `0.3.94+`, `features` should include `tagEventProbeSynchronousWaitCap` before relying on bounded effective probe polling metadata. For runner `0.3.95+`, `features` should include `tagEventProbeFailureCleanup` before relying on best-effort cleanup metadata for failed tag-event probe applies. For runner `0.3.96+`, `features` should include `backendQueryWorkBounds` before relying on scope-restricted alarm/audit or DB-bounded Named Query preview work. For runner `0.3.97+`, `features` should include `alarmJournalExplicitProfileRequired` before relying on rejection of default/omitted alarm journal profile requests. For runner `0.3.98+`, `features` should include `pathPrefixBoundaryMatching` before relying on exact-or-child prefix matching for views, routes, scripts, Named Queries, dependencies, shared docks, and project resources. For runner `0.3.99+`, `features` should include `namedQueryTopLevelRowLimitScanner` before relying on top-level-only Named Query SQL row-limit classification. For runner `0.3.100+`, `features` should include `threadDumpStreamingSha256` before relying on `threadDumpQuery` integrity hashes without retaining a full raw dump list. For runner `0.3.101+`, `features` should include `explicitUtf8TextFileIo` before relying on exact non-ASCII project-resource, script, query, backup manifest, or runner self-update text round-trips. For runner `0.3.102+`, `features` should include `projectResourceImportZipLegacyRollback` before relying on legacy import backup restore or fatal missing-backup-file rollback validation. For runner `0.3.103+`, `features` should include `runnerSelfUpdateResourceJsonRollback` before relying on self-update rollback to restore the sibling Web Dev `resource.json`. For runner `0.3.104+`, `features` should include `runnerSelfUpdateExactBackup` before relying on current self-update rollback to restore exact `doPost.py` source, including any literal static token assignments present in the source. For runner `0.3.108+`, `features` should include `primaryQueryFailureOkFalse` before relying on top-level `ok: false` envelopes for primary backend failures in `historyProbe`, `alarmStatusQuery`, `alarmJournalQuery`, and all-failed `auditQuery`. For runner `0.3.111+`, `features` should include `tagConfigureQualityFailureOkFalse` before relying on top-level tag configure failure envelopes for bad QualityCodes. For runner `0.3.112+`, `features` should include `udtScaffoldStepAllGoodFailureOkFalse` before relying on scaffold fail-fast behavior for nested configure failures. For runner `0.3.113+`, `features` should include `udtScaffoldPartialFailureRecovery` before relying on scaffold recovery metadata. For runner `0.3.114+`, `features` should include `tagMutationLocking` before relying on mutation-lock serialization for confirmed tag mutation actions. For runner `0.3.115+`, `features` should include `midWriteFailureRecoveryMetadata` before relying on `MID_WRITE_FAILURE` recovery metadata for mid-write exceptions in `apply`, confirmed `projectResourceImportZip`, or confirmed `runnerSelfUpdate`. For runner `0.3.116+`, `features` should include `rollbackRemovalFailureReporting` before relying on verified actual rollback removals or `ROLLBACK_REMOVAL_FAILED` failed-removal metadata. For runner `0.3.118+`, `features` should include `rollbackAfterSha256DriftGuard` before relying on rollback `afterSha256` drift rejection or `backupAfterScanRefreshed` metadata. For runner `0.3.119+`, `features` should include `projectTargetValidation` before relying on strict `targetProject` project-directory validation.

For runner `0.3.120+`, `features` should include `applyPackageSingleProjectRoot` before relying on package `dryRun` or `apply` to reject ZIPs with multiple `project.json` roots.

For runner `0.3.121+`, `features` should include `projectResourceManifestValidation` before relying on malformed managed `resource.json.files` manifests being rejected with `RESOURCE_MANIFEST_INVALID` before writes, backup planning, or scan.

For runner `0.3.122+`, `features` should include `atomicCopyTreeDestinationPreservation` before relying on rollback/backup directory copies to preserve the existing destination when final tree promotion fails.
For runner `0.3.124+`, `features` should include `applyPackageInvalidDataErrors` before relying on `PACKAGE_BASE64_INVALID` or `PACKAGE_ZIP_INVALID` validation envelopes from package `dryRun` and `apply`.
For runner `0.3.125+`, `features` should include `jythonScriptSyntaxLintLiteralAware` before relying on Perspective script lint to ignore Python 3-only marker examples inside comments or string literals.
For runner `0.3.126+`, `features` should include `auditQueryGlobalMaxResults` before relying on `auditQuery.maxResults` as a global response row cap across multiple profiles. For runner `0.3.127+`, `features` should include `backendScopeRowBoundMetadata` before relying on alarm/audit `backendScopeRestricted`, `backendRowBounded`, `responseRowsBounded`, `minimumFilterLiteralChars`, or `BACKEND_SCOPE_FILTER_TOO_BROAD` metadata. For runner `0.3.128+`, `features` should include `strictQueryInputValidation` before relying on query filter validation errors such as `FILTER_LIMIT_EXCEEDED`, `FILTER_VALUE_TOO_LONG`, or `FILTER_CONTROL_CHARACTERS`. For runner `0.3.129+`, `features` should include `metricsSnapshotJvmGlobalSequence` before relying on `metricsSnapshot.sequence` to increment across repeated direct-paste Web Dev requests for the Gateway JVM lifetime. For runner `0.3.131+`, `features` should include `metricsSnapshotIntegralNumberPrecision` before relying on exact precision for large metric counts, gauge values, JVM byte/nanosecond counters, Java integral values, gauge values, or histogram `min` / `max` fields. For runner `0.3.132+`, `features` should include `filesystemDiscoverySortBeforeCap` before relying on stable sorted-first truncated subsets from filesystem discovery actions. For runner `0.3.133+`, `features` should include `zipDuplicateEntryRejection` before relying on duplicate normalized ZIP entries being rejected before package/import validation or writes. For runner `0.3.134+`, `features` should include `sourceVariantDispatchParity` before relying on direct-paste and Project Library parity for unknown-action errors, missing apply-confirmation errors, health aliases, package-name defaults, and package dry-run/apply response shape. For runner `0.3.135+`, `features` should include `runnerSelfUpdateScanCompletionMessage` before relying on the corrected confirmed `runnerSelfUpdate` success message that says the project scan returned successfully. For runner `0.3.136+`, `features` should include `postWriteProjectScanSecondWait` before relying on the two-wait post-write scan sequence and `scanWaitsAttempted` / `scanWaitsCompleted` response fields. For runner `0.3.137+`, `features` should include `historyProbeGoodSampleTerminology` before relying on the precise good-sample historyProbe field names.

If `projectsRootConfigured` is false, set `IGNITION_LLM_GATEWAY_DATA_DIR` or `IGNITION_LLM_PROJECTS_ROOT`, restart the Gateway, and run the health check again.

## Step 7: Prepare the Zip

Preferred: base64-encode the generated import zip and send it as `packageBase64` in the dry-run/apply request. This avoids OS write permissions on the runner inbox.

Optional: copy the generated import zip into the `inboxDir` returned by the health check when the package-building account can write there.

The request uses only the filename, never a path:

```json
"packageName": "llm-perspective-package.zip"
```

## Step 8: Dry Run

Edit `webdev-runner/example-request.json` for your target project. Prefer listing the intended routes explicitly. Use page-config auto-discovery only when the package config contains exactly the intended routes and all referenced views are included in the zip.

```json
{
  "action": "dryRun",
  "confirmApply": "",
  "packageName": "llm-perspective-package.zip",
  "packageBase64": "<base64-zip>",
  "targetProject": "<projectName>",
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

Call `doPost`:

```powershell
$headers = @{
  "Content-Type" = "application/json"
  "X-LLM-Runner-Token" = "<token>"
}

Invoke-RestMethod `
  -Method Post `
  -Uri "<gatewayUrl>/system/webdev/<automationProject>/llmRunner/perspectiveImport" `
  -Headers $headers `
  -InFile "webdev-runner/example-request.json"
```

Expected dry-run result:

```json
{
  "ok": true,
  "action": "dryRun",
  "discoveredRoutes": false,
  "validatedViews": ["LLM Tests/Example"],
  "validatedRoutes": ["/llm-example"],
  "message": "Dry run passed. No files were changed."
}
```

## Optional: Tag Discovery

The runner supports read-only tag discovery through `system.tag.browse`. This lets an LLM inspect provider names and tag paths before it creates Perspective bindings.

List providers:

```json
{
  "action": "tagProviders",
  "maxResults": 100
}
```

Browse one provider/folder:

```json
{
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
  "action": "tagBrowse",
  "path": "[<tagProvider>]<folderPath>",
  "recursive": true,
  "maxResults": 1000
}
```

Keep `includeValues` omitted or `false` by default. Use it only for small, deliberate reads.

Always send a `maxResults` cap. Runner `0.3.83+` reports `returnedCount`, `returnedSize`, `totalAvailable`, and `truncated`; if `truncated` is true or `totalAvailable > returnedCount`, narrow the path/filter or increase the cap before treating the browse as complete.

## Step 9: Apply

Only after dry-run passes, change the request:

```json
"action": "apply",
"confirmApply": "APPLY"
```

If replacing an existing route or view, also set:

```json
"allowOverwrite": true
```

Run the same `doPost` call again.

Expected apply result:

```json
{
  "ok": true,
  "action": "apply",
  "copiedViews": ["LLM Tests/Example"],
  "mergedRoutes": ["/llm-example"],
  "backupDir": "<gatewayDataDir>/llm-runner/backups/<projectName>-<timestamp>",
  "filesChanged": true,
  "scanCompleted": true,
  "scanRequested": true,
  "recoveryRequired": false,
  "keepWorkDir": false,
  "workDirKept": false,
  "workDirCleaned": true,
  "workDirCleanupStatus": "cleaned"
}
```

On runner `0.3.88+`, `scanCompleted` is authoritative. If files changed but the project scan fails, the response is not successful: expect `ok: false`, `errorCode: "PROJECT_SCAN_FAILED"`, `scanCompleted: false`, and `recoveryRequired: true`.

## Step 10: Verify

1. Refresh or reopen Designer.
2. Confirm the view exists under `Perspective > Views > <viewPath>`.
3. Confirm the page route exists in Perspective page configuration.
4. Open:

```text
<gatewayUrl>/data/perspective/client/<projectName>/<pagePath>
```

5. Verify the page renders the expected marker or component.
6. Check Gateway logs for `LLM.WebDevRunner`.

HTTP 200 alone is not enough. Confirm the configured route maps to the expected view and the rendered page content is present.

## Request Contract

Minimal request:

```json
{
  "action": "dryRun | apply",
  "confirmApply": "APPLY only for apply action",
  "packageName": "filename.zip, optional; defaults to llm-perspective-package.zip",
  "packageBase64": "<base64-zip, optional when package is already in inbox>",
  "targetProject": "<projectName>",
  "allowOverwrite": false,
  "allowedViewPrefix": "LLM Tests/",
  "allowedRoutePrefix": "/llm-",
  "keepWorkDir": false
}
```

Optional explicit routes:

```json
{
  "routes": [
    {
      "pagePath": "/llm-example",
      "viewPath": "LLM Tests/Example",
      "title": "Example"
    }
  ]
}
```

If `routes` is omitted or empty, the runner discovers routes from the package's Perspective page config, then applies only routes matching `allowedRoutePrefix` and views matching `allowedViewPrefix`.

Runner `0.3.98+` uses exact-or-child prefix matching for logical paths. Prefix `LLM Tests/A` allows `LLM Tests/A` and `LLM Tests/A/Child`, not sibling `LLM Tests/ABC`; `/llm-` remains the documented route namespace for `/llm-...` pages.

Older project-library runner versions accepted `mode` for dry-run/apply. Prefer `action`; keep `mode` only for compatibility with older installed copies.

The runner rejects:

- Package paths instead of simple filenames.
- Zip entries with absolute paths, drive letters, or `..`.
- View paths outside exact-or-child `allowedViewPrefix`.
- Page routes outside exact-or-child `allowedRoutePrefix`, except the documented `/llm-...` route namespace.
- Unexpected files inside a selected view directory.
- Existing views/routes unless `allowOverwrite` is true.
- Apply action unless `confirmApply` is exactly `APPLY`.
- Tag writes, tag imports, and tag configuration changes.

## Notes

Ignition Web Dev Python Resources receive `request` and `session`, can parse JSON request data, and return `{"json": ...}` responses. The official Web Dev docs also describe resource-level HTTPS/authentication settings. Use those settings plus the runner token for defense in depth.






