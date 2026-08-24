# Complete Runtime Details

Use this reference when an edge case depends on exhaustive runner compatibility, payload, discovery, component, validation, or recovery detail that the topical references summarize. Live `health`, the current `SKILL.md`, and the current topical references remain authoritative when older wording conflicts.

This file retains the complete two source candidates used for the `1.0.131` restructure so no customer-runtime information was removed from the installed skill.

## Canonical Pre-Restructure Source — Skill 1.0.129
---
name: ignition-perspective-host-builder
description: Apply, update, inspect, or validate Ignition 8.1 Perspective resources on a reachable Gateway through the approved Web Dev runner API. Use when Codex has same-PC/host access and the desired result is an applied running-Gateway change, not a portable import zip. For authoring the Perspective view/package itself, use ignition-perspective-import-zip first.
---

# Ignition Perspective Host Builder

Skill version: `1.0.129`
Stack version: `starter-2026.07.06.03`
Runner API version: `0.3.148`

## Scope

Use the existing Ignition Web Dev runner API as the host-side access path.

This skill applies or inspects resources on a running Ignition 8.1 Gateway. It is not the place to teach Perspective JSON design. If a page/view/package must be authored, create the artifact with `ignition-perspective-import-zip`, then return here to dry-run, apply, and validate it.
Keep runner request details to the minimum needed; the main goal is reliable Perspective page creation and validation.
Treat the runner contract as support tooling. Add or use runner actions only when they help build, apply, or verify a real Perspective page.

Do not use default credentials, guessed endpoints, direct filesystem writes, native file chooser automation, or ad hoc Gateway import APIs unless the user explicitly changes the access model.

## Non-Deletion Rule

Do not delete, remove, prune, or clean up live Gateway/project/tag resources unless the user explicitly commands that deletion in the current task. This includes files, Perspective views/routes/styles/images, scripts, named queries, tags, UDTs, alarms, database rows, backups, and temp resources. Default to create/update/merge/validate; if deletion seems required, stop and ask.

## Runtime Values

Get these from the user, environment, instance profile, or active host discovery:

- `<gatewayUrl>`
- `<projectName>`
- `<webDevResource>`
- `<token>`
- `<packagePath>` or package bytes
- `<viewPath>`
- `<pagePath>`
- `<allowedViewPrefix>`
- `<allowedRoutePrefix>`

Never write real tokens, usernames, passwords, cookies, local install paths, or customer identifiers into this skill or generated reusable docs.

## Runner Endpoint

Expected endpoint shape:

```text
POST <gatewayUrl>/system/webdev/<projectName>/<webDevResource>
Content-Type: application/json
X-LLM-Runner-Token: <token>
```

Supported actions:

- `health`: verify runner availability, supported callable actions, and feature flags.
- `gatewayInfo`: read-only Gateway/version/module/path diagnostics. Runner `0.3.55+` reports module versions from the documented Gateway-scope `system.util.getModules` dataset when `health.features` includes `gatewayInfoModuleVersions`.
- `dryRun`: validate package, routes, prefixes, and target project without writing files.
- `apply`: copy allowlisted resources, merge routes, back up affected resources, and request a project scan.
- `tagProviders`: read-only list of tag providers.
- `tagBrowse`: read-only tag browsing through `system.tag.browse`; runner `0.3.83+` returns `returnedCount`, `returnedSize`, `totalAvailable`, and `truncated` so callers can detect incomplete capped browses.
- `tagRead`: read-only current value, quality, and timestamp for explicit tag paths.
- `tagConfigure`: guarded tag/UDT scaffold creation through `system.tag.configure`; use dry-run, allowed tag prefixes, explicit confirmation, then require a successful apply response plus `allGood`/good `qualityCodes` and `tagRead` verification before binding pages. Runner `0.3.47+` permits Reference tags when `health.features` includes `referenceTagConfigure`. Runner `0.3.111+` advertises `tagConfigureQualityFailureOkFalse` and returns top-level `ok: false` for bad returned QualityCodes or returned-code count mismatches; older runners still require manual `allGood`/`qualityCodes` inspection because `ok: true` did not prove every `system.tag.configure` QualityCode was good.
- `udtScaffold`: guarded higher-level UDT fixture helper; creates UDT type, instances, and member overrides through `tagConfigure`. Runner `0.3.112+` advertises `udtScaffoldStepAllGoodFailureOkFalse` and returns top-level `ok: false` when any nested scaffold step returns `ok: false` or `allGood: false`; runner `0.3.113+` advertises `udtScaffoldPartialFailureRecovery` and reports `recoveryRequired` plus recovery detail when a later scaffold step fails after earlier writes. Runner `0.3.143+` advertises `udtScaffoldUnknownFailureRecovery`; when a confirmed non-dry-run nested `tagConfigure` step fails with missing, null, or empty `qualityCodes`, treat every step recovery path as unknown-mutated by preflight and inspect recovery fields before continuing. Still inspect `stepResults`, nested `qualityCodes`, and `tagRead` member readback before binding pages.
- `udtTagEventScriptProbe`: constrained UDT tag-event fixture for proving `valueChanged` scripts can read instance parameters; requires existing type/instance base paths, `allowedTagPathPrefixes`, dry-run, and `confirmUdtTagEventScriptProbe: "CREATE_UDT_TAG_EVENT_PROBE"` for apply. It is not a general arbitrary `eventScripts` writer. Runner `0.3.94+` caps effective synchronous polling and returns probe wait metadata; runner `0.3.95+` returns `failureCleanupPaths` and attempts best-effort cleanup of fresh planned probe fixture paths after post-create apply failures; runner `0.3.139+` promotes cleanup status to top-level recovery fields.
- Project Gateway Event Script resources and Perspective Session Event Script resources are not runner-supported write/read surfaces unless `health.supportedActions` exposes explicit actions for them; `tagEventScriptProbe`/`udtTagEventScriptProbe` are constrained tag fixtures, not Project Gateway Event handlers. Do not invent `sessionScripts*` or `gatewayEventScripts*` API calls without supported-action proof plus dry-run/apply/readback validation.
- `historyProbe`: read-only tag history check for explicit tag paths. Runner `0.3.137+` exposes good-quality Count evidence as `goodSampleHistoryAvailable`, `goodStoredSampleCount`, and per-tag `tagStats[].goodStoredSampleCount`; treat older `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` fields as aliases and `nonNullCount` as value-query diagnostic context only. False/zero good-sample fields do not rule out bad-quality historical rows.
- `alarmStatusQuery`: read-only current alarm status query; runner `0.3.96+` requires a narrow source, path, or displayPath filter before execution. Provider/state/priority filters are supplemental and capped results are response caps.
- `alarmJournalQuery`: read-only historical alarm journal query; require explicit `journalName`, `journal`, or `alarmJournal`, a time window, capped results, and on runner `0.3.96+` a narrow source/path/displayPath filter. Runner `0.3.97+` rejects default/omitted journal flags because it cannot verify Ignition's exactly-one-journal omission condition. Provider/state/priority/isSystem filters are supplemental, the maximum window is `1440` minutes, and broad confirmation bypasses are not available.
- `auditQuery`: read-only audit/change-attribution query; require explicit audit profile names, a bounded time window, caps, and narrow actor/action/target/value/system filters. WebDev/Gateway scope rejects `useDefaultProfile`; runner `0.3.96+` caps the window at `1440` minutes and rejects broad audit scans before execution. `contextFilter` must be an integer bitmask and is not a backend bound by itself.
- `logQuery`: read-only recent Gateway/Perspective log query; require time window, filters, and caps.
- `routesList`: read-only list of Perspective page routes in a target project.
- `viewsList`: read-only list of Perspective views in a target project.
- `viewRead`: read-only parsed `view.json` for one allowlisted Perspective view.
- `pageValidate`: read-only structural route/view/dependency/script/hash validation after apply.
- `sharedDockKeys`: package request field for allowlisted top-level Perspective page-config `sharedDocks` merges.
- `styleResourcesList`: read-only Perspective style class, theme, image, and reusable-view metadata discovery. Responses can be envelopes; consume returned `items` and exact fields such as `stylePath`, `viewPath`, and `themeName`.
- `perspectiveSessionsQuery`, `perspectiveSessionPagesList`, `perspectivePageViewsList`: read-only live Perspective runtime discovery. Use tokens by default; raw IDs require `includeIdentifiers:true`. Live page-view discovery requires strict session/page matching and does not infer results from static routes or views.
- `perspectiveSessionTerminate`: guarded live-session close. Dry-run first; apply requires `expectedSessionToken` and `confirmTerminateSession: "TERMINATE_PERSPECTIVE_SESSION"`. Treat `closeSessionCalled` as the attempted close call and `terminated`/`terminationVerified` as follow-up discovery proof that the token is gone.
- `perspectiveThemesList`/`perspectiveThemeRead`/`perspectiveThemeUpsert`, `perspectiveFontsList`/`perspectiveFontRead`/`perspectiveFontUpsert`, `perspectiveIconLibrariesList`/`perspectiveIconLibraryRead`/`perspectiveIconLibraryUpsert`, and `perspectiveBrandingRead`: Gateway-level Perspective module assets and branding metadata. List/read before writes. Upserts default to dry-run, reject built-in theme/icon names, require exact confirmations, write `_gateway` backups, skip project scans, and may require browser/client/Gateway/Designer refresh.
- `seedViewsList`: read-only metadata discovery for allowlisted Designer-created Perspective seed views/components.
- `seedViewRead`: read-only capped JSON/metadata read for one allowlisted seed view.
- `componentSeedRead`: read-only extraction of one exact component seed from an allowlisted seed view.
- `namedQueriesList`: read-only Named Query path/metadata discovery.
- `namedQueryRead`: read-only metadata and optional small SQL body/hash for one allowlisted Named Query.
- `namedQueryPreview`: read-only capped preview for an allowlisted, DB-side bounded Named Query. Runner `0.3.54+` rejects QueryString/Database params by default, supports exact preview allowlists for controlled diagnostics, and wraps preview execution failures as JSON errors. Runner `0.3.96+` requires the SQL `LIMIT`/`TOP`/`FETCH` or Named Query max return size to be no larger than request `maxRows`; runner `0.3.99+` only treats top-level outer-query `LIMIT`/`TOP`/`FETCH` numeric literals as SQL row bounds.
- `dependencyNamedQueryPaths`: package request field for allowlisted Named Query resources under `ignition/named-query`; runner `0.3.52+` preserves query `resource.json` attributes and validates/copies only explicitly listed dependencies. Runner `0.3.54+` rejects packaged QueryString/Database params unless `allowUnsafeNamedQueryParameters`, `unsafeNamedQueryParameterPaths`, and `confirmUnsafeNamedQueryParameters: "ALLOW_UNSAFE_NAMED_QUERY_PARAMETERS"` are all supplied.
- `viewDriftGuard`: optional overwrite guard using `viewRead` SHA-256 hashes.
- `backupList`: list runner-created project/resource, runner-code, and runner-created Perspective module asset backups, including `fileChanges-v1` metadata when available. Runner `0.3.148+` reports Perspective asset backups as `type:"perspectiveModuleAsset"` with `restoreTargetProject:"_gateway"`, `assetAction`, `targetRootKind:"perspectiveModule"`, and `scanMode:"none"`.
- `rollback`: restore a runner-created backup after dry-run and explicit confirmation. Runner `0.3.84+` restores existing files and removes files that the backup recorded as newly created. Runner `0.3.141+` returns `ROLLBACK_WRITE_FAILED` with recovery context if rollback write/restore work fails.
- `runnerSelfUpdate`: runner maintenance only; use `scriptBase64`, `scriptSha256`, expected version/hash, explicit confirmation, rollback-compatible exact-source backup for both Web Dev `doPost.py` and sibling `resource.json`, scan, and health verification.
- Runner `0.3.85+` advertises `mutationLocking` and `mutationLockedActions`; package `dryRun`/`apply`, `projectResourceImportZip`, `rollback`, `runnerSelfUpdate`, confirmed tag/probe/UDT writes, and confirmed Perspective session/theme/font/icon mutations can return `MUTATION_LOCK_BUSY` / HTTP 409 when another runner mutation is active. Treat that as retryable, re-run discovery if state may have changed, and repeat dry-run before applying later.
- Runner `0.3.86+` advertises `atomicProjectResourceFileWrites`; final project-resource file writes and file copies stage to sibling temporary paths before the final Java NIO atomic move. Treat atomic-move failures as mutation failures, not as permission to write resource files directly.
- Runner `0.3.87+` advertises `projectResourceAttributePreservation`; runner-managed resource stamping preserves existing `resource.json` `attributes` keys and replaces only Ignition's automatic `lastModification` and `lastModificationSignature` fields. `projectResourceImportZip` and rollback remain exact-file paths.
- Runner `0.3.88+` advertises `projectScanFailureIsFailure`; after files change, scan exceptions from `apply`, confirmed `projectResourceImportZip`, confirmed rollback, or confirmed `runnerSelfUpdate` return `PROJECT_SCAN_FAILED` with `scanCompleted: false` and `recoveryRequired: true`. Treat recovery-required scan failure as a stop condition, not as a successful apply.
- Runner `0.3.89+` advertises `environmentPathOverrides`; both runner variants honor all documented `IGNITION_LLM_*` path overrides and `gatewayInfo.environment` reports their configured booleans without exposing raw path values.
- Runner `0.3.90+` advertises `applyPackageWorkDirCleanup`; package `dryRun` and `apply` clean temporary work directories by default and report `keepWorkDir`, `workDirKept`, `workDirCleaned`, and `workDirCleanupStatus`. Use `keepWorkDir: true` only for target-local diagnostics when extracted package files must be inspected.
- Runner `0.3.91+` advertises `uniqueIdStamps`; runner-generated fallback `requestId` values and generated work/backup names include a short Java UUID suffix after the timestamp. Treat returned `backupName`, `backupDir`, and work paths as opaque values instead of reconstructing timestamp-only names.
- Runner `0.3.92+` advertises `perspectiveSessionsQueryMatchedCount`; filtered `perspectiveSessionsQuery` responses include `matchedCount`, and `truncated` is true only when matching sessions exceed `maxResults`.
- Runner `0.3.137+` advertises `historyProbeGoodSampleTerminology`; use `historyProbe.goodSampleHistoryAvailable`, `goodStoredSampleCount`, and `tagStats[].goodStoredSampleCount` as good-quality Count evidence. Treat `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` as compatibility aliases, and treat `valueQueryHistoryAvailable`, `tagStats[].nonNullCount`, `hasData`, and `lastValue` as diagnostics from the displayed value query.
- Runner `0.3.94+` advertises `tagEventProbeSynchronousWaitCap`; `tagEventScriptProbe` and `udtTagEventScriptProbe` return `requestedPollAttempts`, effective `pollAttempts`, `pollAttemptsCapped`, and `probeSyncWaitMaxMs`/`maxProbeSyncWaitMs` so dry-runs can prove the bounded wait before applying a live tag fixture.
- Runner `0.3.95+` advertises `tagEventProbeFailureCleanup`; `tagEventScriptProbe` and `udtTagEventScriptProbe` return `failureCleanupPaths`, and failed applies that reach post-create fixture work may return `failureCleanup` with best-effort cleanup results for fresh planned probe paths only.
- Runner `0.3.139+` advertises `tagProbeCleanupRecoveryFields`; failed `tagEventScriptProbe` and `udtTagEventScriptProbe` responses with `failureCleanup` also return top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired`.
- Runner `0.3.140+` advertises `projectResourceImportZipFinalManifestValidation`; import dry-run/apply validates the final overlaid `resource.json.files` state before writes and rejects missing listed files or unlisted managed files with `RESOURCE_MANIFEST_INVALID` and `manifestValidationPhase:"finalMergedResourceState"`.
- Runner `0.3.141+` advertises `rollbackWriteFailureEnvelope`; rollback write/restore failures return `ROLLBACK_WRITE_FAILED` with `backupName`, `backupFormat`, `preRollbackBackupDir`, `failedStage`, completed work lists, nested `rollbackFailure`, and `recoveryRequired:true`.
- Runner `0.3.142+` advertises `applyPackageStaleViewFilePruning`; package apply overwrites of runner-managed Perspective views prune stale optional managed files such as `thumbnail.png` when the package and final `resource.json.files` omit them. Inspect `prunedStaleViewFiles` and `prunedStaleViewFileCount` when a view overwrite intentionally removes a thumbnail.
- Runner `0.3.143+` advertises `udtScaffoldUnknownFailureRecovery`; failed confirmed non-dry-run `udtScaffold` nested `tagConfigure` steps with missing, null, or empty `qualityCodes` are treated as unknown-mutated and recovery marks every step recovery path from the preflight snapshot. Dry-runs do not mark mutations.
- Runner `0.3.144+` advertises `unfinishedFileChangeBackupRollbackRecovery`; unfinished `fileChanges-v1` backups created during failed `apply`, `projectResourceImportZip`, or `runnerSelfUpdate` writes expose `afterStateKnown:false`, `backupManifestComplete:false`, `rollbackDriftCheckMode:"unknown-after-state"`, and rollback `driftCheckSkipped:true`. Completed backups still enforce `ROLLBACK_DRIFT_DETECTED`.
- Runner `0.3.145+` advertises `applyNonViewFinalStateValidation`; apply validates final Project Library script, Named Query, and page-config destination state after copy/merge. Treat `validateCopiedScripts`, `validateCopiedNamedQueries`, or `validateMergedPageConfig` `MID_WRITE_FAILURE` responses as stop-and-rollback/inspect evidence; do not expect the runner to prune unknown non-view files.
- Runner `0.3.146+` advertises Perspective live-page runtime actions. Use `perspectiveSessionsQuery` to get a session token, `perspectiveSessionPagesList` to get page tokens, and `perspectivePageViewsList` to inspect live view instances on a page.
- Runner `0.3.148+` advertises Perspective theme/font/icon-library management and branding metadata readback. The callable branding action is `perspectiveBrandingRead`; `perspectiveBrandingMetadataRead` is only a feature flag.
- Runner `0.3.148+` advertises verified Perspective session termination, strict live view session/page matching, and Perspective asset backup metadata. Do not treat `perspectiveSessionTerminate.closeSessionCalled` as proof; require `terminated:true` or inspect `terminationVerified`, `postCloseMatchedCount`, and `verificationAttempts`.
- Runner `0.3.96+` advertises `backendQueryWorkBounds`; alarm status/journal diagnostics require narrow source/path/displayPath filters before execution, audit diagnostics require narrow actor/action/target/value/system filters, and Named Query previews require DB-side row bounds no larger than request `maxRows`.
- Runner `0.3.97+` advertises `alarmJournalExplicitProfileRequired`; `alarmJournalQuery` requires explicit `journalName`, `journal`, or `alarmJournal`, rejects default/omitted journal flags before calling Ignition, and returns `journalNameRequired: true` on successful queries.
- Runner `0.3.98+` advertises `pathPrefixBoundaryMatching`; view, route, seed, style, script, Named Query, dependency, shared dock, and project-resource allowlists use exact-or-child prefix matching. `LLM Tests/A` does not allow `LLM Tests/ABC`; `/llm-...` remains the default route namespace and root-level `llm...` Project Library script modules remain allowed by the default script prefix.
- Runner `0.3.99+` advertises `namedQueryTopLevelRowLimitScanner`; `namedQueryPreview` ignores nested-only row limiters as proof of bounded backend work and rejects `TOP PERCENT`, `TOP/FETCH WITH TIES`, dynamic limits, and nonliteral limits unless a safe Named Query max return size is enabled.
- Runner `0.3.100+` advertises `threadDumpStreamingSha256`; `threadDumpQuery` keeps `unredactedDumpSha256` evidence while streaming canonical unredacted dump text into SHA-256 instead of retaining a full raw dump list.
- Runner `0.3.101+` advertises `explicitUtf8TextFileIo`; runner-managed text file reads/writes use explicit UTF-8 for project resources, scripts, Named Query SQL, backups/manifests, and self-update source. Binary ZIP, log-tail, backup-copy, and hash paths remain byte-oriented.
- Runner `0.3.102+` advertises `projectResourceImportZipLegacyRollback`; damaged `fileChanges-v1` rollback manifests with missing backup files reject before dry-run/apply can succeed, and legacy `projectResourceImportZip` backups can restore backed-up overwritten files while reporting `createdFilesNotRemoved: true`.
- Runner `0.3.103+` advertises `runnerSelfUpdateResourceJsonRollback`; current `runnerSelfUpdate` backups include both Web Dev `doPost.py` and sibling `resource.json` in their `fileChanges-v1` rollback plan, with `targetResourceFile` and `backupIncludesResourceJson` in self-update responses.
- Runner `0.3.104+` advertises `runnerSelfUpdateExactBackup`; current `runnerSelfUpdate` backups store exact pre-update `doPost.py` source and responses include `backupExactSource: true` plus `backupTokenRedacted: false`. Treat backup folders as sensitive if static token assignments exist in runner source.
- Runner `0.3.105+` advertises `projectScanTimeoutControl`; writeful `apply`, confirmed `projectResourceImportZip`, confirmed rollback, and confirmed `runnerSelfUpdate` accept optional `scanTimeoutSeconds` from `1` through `30`, defaulting to `10`. Use this field only as bounded scan-wait control, not as proof the project resources are valid.
- Runner `0.3.108+` advertises `primaryQueryFailureOkFalse`; primary backend failures in `historyProbe`, `alarmStatusQuery`, `alarmJournalQuery`, and all-failed `auditQuery` return top-level `ok: false`, `statusCode: 500`, `errorCode`, and `error` while preserving action-specific diagnostics such as `queryOk`, `sampleCountQueryOk`, `queryError`, `sampleCountQueryError`, `errorType`, and `attempts[]`. Parse the JSON body on non-2xx responses before diagnosing.

Include a caller-generated `requestId` on every request when possible. Require the same `requestId` in success, validation-error, auth-error, and write responses. Valid caller-supplied IDs are echoed unchanged; the `0.3.91+` UUID suffix applies only to runner-generated fallback IDs.

## Apply Payload

Use base64 package transfer unless the runner and user explicitly choose a fixed host inbox.

```json
{
  "action": "dryRun",
  "requestId": "<stableRequestId>",
  "targetProject": "<projectName>",
  "packageName": "<packageName>.zip",
  "packageBase64": "<base64Zip>",
  "allowOverwrite": true,
  "requireViewSha256ForOverwrite": true,
  "expectedViewSha256ByViewPath": {
    "<viewPath>": "<viewSha256FromViewRead>"
  },
  "allowedViewPrefix": "<allowedViewPrefix>",
  "scanTimeoutSeconds": 10,
  "allowedRoutePrefix": "<allowedRoutePrefix>",
  "dependencyViewPaths": [
    "<embeddedOrReusableViewPath>"
  ],
  "dependencyScriptPaths": [
    "<projectLibraryScriptPath>"
  ],
  "sharedDockKeys": [
    "top",
    "left"
  ],
  "allowedScriptPrefix": "<scriptPathPrefix>",
  "routes": [
    {
      "pagePath": "<pagePath>",
      "viewPath": "<viewPath>",
      "title": "<pageTitle>"
    }
  ]
}
```

For apply, change `action` to `apply` and add:

```json
{ "confirmApply": "APPLY" }
```

Send explicit `routes` for small generated packages. Do not rely on package route auto-discovery unless `page-config/config.json` contains only intended routes.

If a routed view embeds or depends on other project views that are included in the package, include those packaged child/dependency views in `dependencyViewPaths`; dry-run/apply validates and copies only explicitly listed packaged dependencies. If the view intentionally references an already-existing target reusable view, first discover it with `viewsList`/`styleResourcesList` and `viewRead`, document it as a target prerequisite, and do not list it in `dependencyViewPaths` unless the package also contains that view. A missing listed packaged dependency should fail dry-run before apply. For dynamic Embedded View shells, do not rely on the runner to infer every possible `props.path` value from parent state or from extra packaged views.

If a routed view calls Project Library scripts, include those scripts in `dependencyScriptPaths` and keep them under `allowedScriptPrefix`. The runner copies only `code.py` and `resource.json` for explicitly listed script resources.

If a routed view or Project Library helper needs packaged Named Queries, include those queries in `dependencyNamedQueryPaths` and keep them under `allowedNamedQueryPrefix`. After apply, require `validatedNamedQueries`, `copiedNamedQueries`, `namedQueryRead` metadata, and `pageValidate.namedQueryChecks` before relying on the query at runtime. Do not package QueryString or Database params unless the workflow has an explicit unsafe-param allowlist; keep Database `<Parameter>` execution target-specific and require runtime execution proof on the target connection.

For runner `0.3.98+`, treat all runner path prefixes as exact-or-child allowlists unless this skill explicitly calls out a documented namespace. A prefix such as `LLM Tests/A` allows `LLM Tests/A` and children, not siblings such as `LLM Tests/ABC`.

For shared docked navigation/status shells, package each dock view and pass explicit `sharedDockKeys` for the top-level page-config `sharedDocks` keys to merge. Allowed keys are `top`, `bottom`, `left`, `right`, and `cornerPriority`. Treat dry-run/apply `sharedDockViewPaths` as dependency views and require apply `mergedSharedDockKeys` to match the intended keys. Do not use `sharedDockKeys` for route-specific page `docks`.

For shared dock runtime behavior, use API proof for structure and browser proof for behavior. `pageValidate`/`viewRead` can prove the dock views exist; bounded page-config readback can prove `id`, `show`, `handle`, `modal`, `autoBreakpoint`, and `viewPath`; only browser tests prove real handle clicks, `openDock`/`closeDock`/`toggleDock` actions, modal overlay blocking, and wide/narrow breakpoint collapse.

## Workflow

1. Call `health`; require JSON with `ok: true`. Stop on empty/non-JSON HTTP 200 because the Web Dev body is not invoking the runner. If `supportedActions` exists, use it to confirm callable actions such as `pageValidate`, `logQuery`, `auditQuery`, `alarmJournalQuery`, and `udtTagEventScriptProbe`. If `features` exists, use it to confirm `packageBase64`, `logQueryRotatedFiles`, lint, route-conflict detail, top-level event script lint, `gatewayInfoModuleVersions` when module versions matter, `sharedDockKeys` when merging shared docks, `referenceTagConfigure` support when Reference tags are needed, `tagConfigureQualityFailureOkFalse` when relying on top-level `ok: false` for bad `tagConfigure` QualityCodes, `udtScaffoldStepAllGoodFailureOkFalse` when relying on top-level `ok: false` for a failed `udtScaffold` nested step, `udtScaffoldPartialFailureRecovery` when relying on recovery metadata from partially completed scaffold writes, `udtScaffoldUnknownFailureRecovery` when relying on conservative recovery after a failed confirmed scaffold step has missing, null, or empty `qualityCodes`, `unfinishedFileChangeBackupRollbackRecovery` when relying on normal rollback after an unfinished file-change backup, `tagEventProbeSynchronousWaitCap` when relying on bounded tag-event probe waits and timing metadata, `tagEventProbeFailureCleanup` when relying on failed tag-event probe cleanup metadata, `tagProbeCleanupRecoveryFields` when relying on top-level failed-probe cleanup recovery fields, `projectResourceImportZipFinalManifestValidation` when relying on final merged import-manifest validation, `rollbackWriteFailureEnvelope` when relying on structured rollback write-failure recovery context, `applyPackageStaleViewFilePruning` when relying on package apply to remove stale optional view-managed files during overwrites, `applyNonViewFinalStateValidation` when relying on final post-apply validation for scripts, Named Queries, or page config, `perspectiveSessionTerminateVerification` when relying on termination proof, `perspectiveLiveViewStrictSessionMatch` when relying on live page-view discovery, `perspectiveThemeAssetManagement`, `perspectiveFontAssetManagement`, `perspectiveIconLibraryManagement`, `perspectiveBrandingMetadataRead`, `perspectiveAssetBackupListMetadata`, and `perspectiveAssetRollbackNoProjectScan` when using Perspective module assets, `backendQueryWorkBounds` when relying on bounded backend alarm/audit/Named Query preview work, `alarmJournalExplicitProfileRequired` when relying on rejection of default/omitted alarm journal profile requests, `primaryQueryFailureOkFalse` when relying on top-level error envelopes for failed backend read queries, `pathPrefixBoundaryMatching` when relying on exact-or-child prefix allowlists, `namedQueryTopLevelRowLimitScanner` when relying on top-level-only Named Query SQL row-limit classification, `threadDumpStreamingSha256` when relying on `threadDumpQuery` integrity hashes without full raw dump retention, `explicitUtf8TextFileIo` when relying on exact non-ASCII text file read/write round-trips, `projectResourceImportZipLegacyRollback` when relying on legacy import rollback or fatal missing-backup-file validation, `runnerSelfUpdateResourceJsonRollback` when relying on self-update rollback to restore the sibling Web Dev `resource.json`, `projectScanTimeoutControl` when relying on bounded `scanTimeoutSeconds` for writeful project scans, `atomicProjectResourceFileWrites` when relying on runner-managed final project-resource file writes, `projectResourceAttributePreservation` when relying on runner-managed resource metadata stamping to preserve existing `resource.json` `attributes`, `projectScanFailureIsFailure` when relying on `scanCompleted` and recovery-required scan failure reporting after writes, `applyPackageWorkDirCleanup` when relying on default cleanup of package apply work directories, `uniqueIdStamps` when relying on generated request/work/backup names being collision-resistant within the same millisecond, and `perspectiveSessionsQueryMatchedCount` when relying on filtered Perspective session truncation semantics.
2. If version/module/path/trial state matters, call `gatewayInfo` before deeper debugging.
3. For existing project context, call `routesList` and `viewsList` before choosing new route/view paths. Use `viewRead` before editing an existing allowlisted view. If page design must match existing project styling, call `styleResourcesList` and use discovered style/view/image names exactly. Treat `viewThumbnail` image entries as metadata for views, not general app images. For Perspective module themes, fonts, icon libraries, or branding, call the matching list/read action first; dry-run every upsert, apply only with the exact confirmation string, verify readback, then check `backupList` with `targetProject:"_gateway"` because those backups are Gateway-level assets, not project resources.
4. Before hand-authoring fragile component JSON, call `seedViewsList`; use `seedViewRead` or `componentSeedRead` for a matching Designer-created seed. `componentSeedRead` requires a concrete `viewPath` returned by `seedViewsList`; do not call it with only `componentType`. Copy only the minimal exact component shape, then parameterize project/tag/binding/style values. For Tag Browse Tree pages, extract an exact `ia.display.tag-browse-tree` seed, verify `props.root.path`, explicit `props.selection.mode`, sibling `../Tag Browse Tree.props.selection.values` bindings, and `onNodeClick` `event.path`/`event.name` only when side effects/tag reads are needed; browser-expand folders through disclosure controls and click at least two leaf tags with final `tagRead` proof. For built-in symbol pages, extract exact `ia.symbol.*` seeds and bind only props present on that symbol; later verify with `viewRead` plus browser clicks that chosen props such as Pump `props.variant`, Valve `props.valve`/`props.reverseFlow`, Vessel `props.value.value`/fill props, state, value, orientation, or pipe visibility actually change. For Flex Repeater pages, extract or inspect an exact `ia.display.flex-repeater` seed, bind `props.instances` from parent `view.custom`, pass child params as top-level instance keys matching the packaged child view's `view.params`, and verify in-browser that distinct cards render without default-param leakage. For dynamic Embedded View shell/tab pages, use `viewRead` to confirm `ia.display.view.props.path` is bound from parent state, child inputs are declared in `view.params`, and every possible child path is supplied to `dependencyViewPaths`/`pageValidate`; browser-click each tab because dry-run can pass when an unlisted child is still present in the package. For View Canvas pages, extract an exact `ia.display.viewcanvas` seed, use `props.instances[].viewPath` plus `viewParams`, include child views in `dependencyViewPaths`, then verify `onInstanceClicked` parent/detail updates in-browser. For View Canvas command popups, verify selected state flows from parent `view.custom` into embedded child `props.params`, child scripts use `self.view.params.*`, popup views/scripts are listed as dependencies, and browser evidence proves both blocked and accepted commands with final `tagRead`. For route-param equipment detail pages, validate the dynamic route key such as `/equipment/:assetId` with `pageValidate`, then browser-open a concrete URL; bind component filters from `view.params` rather than hard-coded asset ids. For Alarm Journal Table pages, extract an exact `ia.display.alarmjournaltable` seed and preserve/discover its `props.name` profile before authoring filters; do not substitute a guessed profile name. For reusable multi-symbol faceplates, `viewRead` should show fixed `ia.symbol.*` components with `meta.visible` bindings, and browser evidence should select at least one visible asset and one hidden/disabled asset.
5. If page design needs database-backed tables/KPIs, call `namedQueriesList`, `namedQueryRead`, then `namedQueryPreview`; design from returned columns/rows, not guessed SQL/table names. For runtime query-bound pages, `viewRead` should show query bindings under each component `propConfig`, `pageValidate` should include any packaged `dependencyNamedQueryPaths`, and browser evidence should prove rendered table rows, KPI labels, and zero/empty states. Do not treat preview rows alone as runtime proof. On runner `0.3.96+`, make the SQL `LIMIT`/`TOP`/`FETCH` or Named Query max return size no larger than the request `maxRows`; a larger DB-side cap can be rejected even if the response would be locally truncated. On runner `0.3.99+`, put the SQL row limiter on the outer/top-level query; nested subquery or CTE limits do not prove the final Named Query result is backend-bounded. For QueryString or Database params, prove both rejected and allowlisted values through runner allowlists before execution; do not generalize Database `<Parameter>` runtime behavior from package metadata alone, even when `namedQueryRead` synthesizes the `database` parameter.
6. If page design needs real tags, call `tagProviders` and `tagBrowse` read-only. Prefer validating a provider/root folder and UDT shape over hard-coding every device path. On runner `0.3.83+`, treat `truncated: true` or `totalAvailable > returnedCount` as an incomplete browse; narrow the path/filter or increase `maxResults` before building a row model. Use `tagRead` for explicit current values and require good quality before trusting values. UDT instance parameters are read as `Parameters.ParamName` paths; normalize Boolean/numeric string readbacks before binding to Boolean/numeric Perspective props, preserve `None`/empty/literal `"null"` distinctions in row models, and omit overrides when defaults should apply. Use `historyProbe` before building trend/history charts; on runner `0.3.137+`, require `goodSampleHistoryAvailable: true` plus positive `goodStoredSampleCount` or per-tag `tagStats[].goodStoredSampleCount` before claiming good-quality stored historian samples. Do not treat false/zero good-sample fields as proof that no bad-quality rows exist. On runner `0.3.108+`, parse non-2xx JSON from `historyProbe`, `alarmStatusQuery`, `alarmJournalQuery`, and `auditQuery` because primary backend failures now return top-level `ok: false` with preserved diagnostic fields. For alarm components, use `alarmStatusQuery` for current state and `alarmJournalQuery` for historical journal rows with the same narrow source/path/displayPath or displayPath-derived filters the component will use; provider-only or state-only probes do not bound backend work on runner `0.3.96+`. Use the exact Alarm Journal profile from the component's `props.name`, target docs, or operator-provided Gateway configuration as `journalName`; runner `0.3.97+` rejects default/omitted journal profile requests. Use `udtScaffold` for complete fixture UDT types/instances when available, but require each returned scaffold `stepResults[]` item to be successful with `allGood: true` and good nested `qualityCodes`; runner `0.3.112+` converts failed nested steps to top-level `ok: false`, while older runners still need manual nested-step inspection. On runner `0.3.113+`, preserve `recoveryRequired` and related recovery metadata when a partially completed scaffold must be restored or manually reconciled. On runner `0.3.143+`, a failed confirmed scaffold step with missing, null, or empty `qualityCodes` is treated as unknown-mutated, so preserve the full recovery response and verify cleanup/restore before issuing more tag writes. Use `udtTagEventScriptProbe` only for the fixed UDT parameter/tag-event probe; otherwise use `tagConfigure` only under explicit allowed prefixes. For tag-event probe dry-runs on runner `0.3.94+`, inspect `pollAttemptsCapped` and `probeSyncWaitMaxMs` before apply and treat response `pollAttempts` as the effective capped count. On runner `0.3.95+`, inspect `failureCleanupPaths` before apply and, if a probe apply fails after creation begins, preserve `failureCleanup` evidence while treating cleanup as best-effort rather than proof of a successful probe. On runner `0.3.139+`, use top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired` to decide whether cleanup follow-up is needed. Dry-run tag writes first, require the action confirmation string for writes, then require `ok: true`, `allGood: true`, good `qualityCodes`, and `tagRead` verification before binding the page; on runners before `0.3.111`, manually treat `ok: true` plus bad QualityCodes as a failed write.
7. Obtain a validated package artifact from the import-zip/page-authoring flow.
8. Call `dryRun`.
9. Require `ok: true`, expected `validatedViews` including dependency and shared dock views, expected `validatedRoutes`, expected `checkedViewHashes` when overwriting, and no unexpected target project. Require `routeConflictCount: 0` unless overwriting an existing route is intentional; when conflicts exist, inspect `routeConflicts[].packageRoute`, `routeConflicts[].targetRoute`, `willOverwrite`, and `resolutionOptions` before choosing rename, overwrite, or stop. A route conflict dry-run with `allowOverwrite: false` should fail without writing; an intentional overwrite dry-run should show `willOverwrite: true` before any apply. When `health.features` includes `applyPackageWorkDirCleanup`, require default dry-run cleanup fields: `keepWorkDir: false`, `workDirKept: false`, `workDirCleaned: true`, and `workDirCleanupStatus: "cleaned"`.
10. Call `apply` only after dry-run passes.
11. Require `ok: true`, expected `copiedViews` including dependency/shared dock views, expected `copiedScripts`, expected `copiedNamedQueries` when using Named Query dependencies, expected `mergedRoutes`, expected `mergedSharedDockKeys` when using `sharedDockKeys`, backup evidence, `scanCompleted: true`, and no `recoveryRequired`. When `health.features` includes `applyPackageWorkDirCleanup`, require default apply cleanup fields: `keepWorkDir: false`, `workDirKept: false`, `workDirCleaned: true`, and `workDirCleanupStatus: "cleaned"`. When `health.features` includes `applyPackageStaleViewFilePruning` and an intentional overwrite omits a previously present view `thumbnail.png`, inspect `prunedStaleViewFiles` / `prunedStaleViewFileCount`, then use `projectResourceRead`, `viewRead`, or `pageValidate` to prove the final resource matches `resource.json.files`. When `health.features` includes `applyNonViewFinalStateValidation` and the package includes scripts, Named Queries, or page config, require no `validationStage` failure; preserve the full response if `validateCopiedScripts`, `validateCopiedNamedQueries`, or `validateMergedPageConfig` appears.
12. If `pageValidate` is available, require `ok: true`, `routeMatchesExpectedView: true`, empty `issues`, expected view/script/Named Query existence, and hash matches when expected hashes are supplied. For dynamic Embedded View shells, pass the full set of possible child view paths as `dependencyViewPaths`; missing listed child views should fail, but unlisted dynamic children are a caller mistake that validation cannot infer. For shared docks, pass returned dock view paths as `dependencyViewPaths` or verify them with `viewRead`; use bounded page-config readback only when proving dock ids/display properties and browser proof for runtime behavior.
13. If `logQuery` is available, query only the recent apply/render window with severity plus logger/message filters; use results as diagnostics, not render proof.
14. For operator action logging workflows, browser-click the tested buttons/components and verify all intended records through `tagRead`, SQL/Named Query readback, `auditQuery`, and focused `logQuery`. For `auditQuery`, provide explicit audit profile names through `profile`, `auditProfileName`, or `profiles`; runner `0.3.82+` rejects `useDefaultProfile` in WebDev/Gateway scope. Include a time window, caps, and narrow actor/action/target/value/system filters; on runner `0.3.96+`, broad audit scans are rejected before execution and `contextFilter` alone does not bound backend work. Poll briefly after controlled audit writes because readback can lag. Use bounded `scriptEval` for audit readback only when `auditQuery` is unavailable or insufficient. Use a stable logger suffix/run ID/message filter because wrapper logs may abbreviate dotted logger names. If a bounded `scriptEval` diagnostic imports a Project Library module immediately after apply, retry briefly after project scan evidence before declaring the module missing. For non-Button action logging, require one clicked/readback row per component type and record which component-specific `self.props` value was passed to the helper.
15. For disabled/gated command pages, browser-prove visible dependency reasons, disabled-click failure for unavailable controls, and any custom disabled opacity/background on an inspectable element. Then use a deliberate guard-probe/bypass path and final `tagRead` to prove the Project Library helper blocks unsafe writes and leaves blocked target tags unchanged.
16. For table/list-to-detail pages, use `viewRead` to confirm explicit table row selection, hidden helper columns for fields used by detail/action logic, `onSelectionChange`, one root/parent `scripts.messageHandlers` entry with `pageScope: true`, and the expected `sendMessage` type. Browser-click both table and list/card selectors, then verify visible detail state plus durable result tags/logs; `pageValidate` alone does not prove the interaction.
17. For Flex fill/progress visualizations, use `viewRead` to confirm fill-child `position.basis` bindings, then browser-verify visible readout text and actual flex style/width for 0, mid, 100, clamped over-range, and bad-quality/null fallback cases. Use `tagRead` to prove the source quality behind fallback rows.
18. For route-param indirect tag binding pages, require `health.features` to include `indirectTagReferenceLint`, dry-run one bad object-reference package when practical, use `viewRead` to confirm `config.mode: "indirect"`, string `references`, literal fixed-root `tagPath`, and small `fallbackDelay`, then browser-open at least two concrete route URLs to prove the same view switches values.
19. Validate the running Perspective route in a browser and report exact applied resources.
20. For project-resource/page-config writes, require the Gateway to reload the changed project resource through scan/reload/restart evidence before declaring success. If the Perspective project resource endpoint returns HTTP 500 while `pageValidate` passes, inspect focused logs and `viewRead` for generated view JSON problems such as script actions with missing/null `scope`; repair by overwrite through dry-run/apply, not deletion.

## Backup And Rollback

List backups before risky changes or when recovery is needed:

```json
{"action":"backupList","targetProject":"<projectName>","maxResults":50}
```

Rollback uses runner-created backup folder names only. Dry-run first:

```json
{"action":"rollback","targetProject":"<projectName>","backupName":"<backupName>","dryRun":true}
```

For the write call, set `dryRun` false and add:

```json
{ "confirmRollback": "ROLLBACK" }
```

Require expected restore/remove counts, pre-rollback backup evidence, scan evidence, and route/view/resource validation after rollback. For runner `0.3.84+`, inspect `backupFormat: "fileChanges-v1"`, `restoredFiles`, and `removedFiles` in rollback dry-run before applying.
For runner `0.3.85+`, rollback apply can return `MUTATION_LOCK_BUSY`; wait for the active mutation to finish, rerun backup discovery and rollback dry-run, then apply with the exact confirmation only if the plan still matches.
For runner `0.3.86+`, rollback restores individual files through staged sibling temporary files and Java NIO atomic moves; legacy directory rollback is staged before replacement but is not a full multi-file transaction.
For runner `0.3.87+`, rollback still restores/removes the exact files recorded in the selected backup manifest; it does not restamp `resource.json` attributes during restore.
For runner `0.3.88+`, rollback apply must return `scanCompleted: true` after changed files. If it returns `PROJECT_SCAN_FAILED` with `recoveryRequired: true`, stop and inspect the scan error plus backup state before making more changes.
For runner `0.3.102+`, damaged `fileChanges-v1` rollback manifests with missing required backup files are rejected before mutation. Legacy `projectResourceImportZip` backups can restore backed-up overwritten files, but they report `createdFilesNotRemoved: true` because files created by the original legacy import cannot be inferred or removed.
For runner `0.3.103+`, current `runnerSelfUpdate` rollback manifests include both Web Dev `doPost.py` and sibling `resource.json`, so rollback dry-run should list the resource metadata file before a self-update rollback is applied.
For runner `0.3.104+`, current `runnerSelfUpdate` rollback manifests restore exact pre-update `doPost.py` source. Confirm `backupExactSource: true` and `backupTokenRedacted: false` before relying on exact source restore.
For runner `0.3.141+`, if rollback apply returns `ROLLBACK_WRITE_FAILED`, stop and preserve the full response. Inspect `backupName`, `backupFormat`, `preRollbackBackupDir`, `failedStage`, `failedPath`, completed work lists, nested `rollbackFailure`, and `recoveryRequired` before attempting any follow-up recovery.
For runner `0.3.148+`, Perspective theme/font/icon asset backups list under `targetProject:"_gateway"` with `type:"perspectiveModuleAsset"` and must be rolled back with `targetProject:"_gateway"`. Expect `scanSkipped:true` and `restartOrRefreshMayBeRequired:true`; verify with the matching asset read/list action rather than `pageValidate`.

## Runner Maintenance

Only use `runnerSelfUpdate` for the approved Web Dev runner resource. Send the method body as UTF-8 base64, not as raw multiline JSON text. Runner `0.3.84+` stores the code backup in a rollback-compatible `fileChanges-v1` backup folder; runner `0.3.104+` stores exact pre-update source, so protect backup folders like runner source if static token assignments are present.
For runner `0.3.85+`, self-update apply can return `MUTATION_LOCK_BUSY`; retry from `health` and self-update dry-run after the active mutation completes.
For runner `0.3.86+`, the Web Dev `doPost.py` target is staged to a sibling temporary file before the final Java NIO atomic move.
For runner `0.3.87+`, the sibling Web Dev `resource.json` keeps existing `attributes` keys while the runner updates `lastModification` and `lastModificationSignature`.
For runner `0.3.103+`, current self-update backups include both Web Dev `doPost.py` and sibling `resource.json`; dry-run/apply responses include `targetResourceFile` and `backupIncludesResourceJson: true`.
For runner `0.3.104+`, current self-update backups include exact pre-update `doPost.py`; dry-run/apply responses include `backupExactSource: true` and `backupTokenRedacted: false`.
For runner `0.3.88+`, self-update apply must return `scanCompleted: true` before trusting the updated Web Dev resource. If the scan fails after writing, treat `recoveryRequired: true` as a recovery stop and verify live `health` before any further mutation.

```json
{
  "action": "runnerSelfUpdate",
  "targetProject": "<projectName>",
  "webDevResource": "<webDevResource>",
  "expectedRunnerVersion": "<currentRunnerVersion>",
  "expectedCurrentSha256": "<optionalCurrentDoPostSha256>",
  "scriptBase64": "<utf8Base64MethodBody>",
  "scriptSha256": "<sha256OfDecodedMethodBody>",
  "dryRun": true
}
```

For the write call, set `dryRun` false and add:

```json
{ "confirmSelfUpdate": "UPDATE_RUNNER" }
```

After self-update, call `health` until the new runner version, supported actions, and feature flags are visible.

## Project Discovery

Read Gateway diagnostics:

```json
{
  "action": "gatewayInfo",
  "targetProject": "<projectName>",
  "includeModules": true,
  "maxModules": 80
}
```

Use `gatewayInfo` to confirm Ignition version, module presence/name/version/state/license status, runner path existence, and target project existence. Treat it as best-effort diagnostics; do not copy local paths, hostnames, or licensing details into reusable skills.

List existing routes:

```json
{"action":"routesList","targetProject":"<projectName>","routePrefix":"<optionalPrefix>","maxResults":1000}
```

List existing views:

```json
{"action":"viewsList","targetProject":"<projectName>","viewPrefix":"<optionalPrefix>","maxResults":1000}
```

Discover styling/resources before authoring styled pages:

```json
{
  "action": "styleResourcesList",
  "targetProject": "<projectName>",
  "stylePrefixes": ["<optionalStylePrefix>"],
  "reusableViewPrefixes": ["<optionalViewPrefix>"],
  "includeStylePreview": true,
  "includeViewStyleRefs": true,
  "includeViewThumbnails": false,
  "maxResults": 200
}
```

Use returned `stylePath`, `viewPath`, `themeName`, and project-image metadata exactly, unwrapping `items` arrays when the response is envelope-shaped. Do not invent style classes, reusable views, themes, or image URLs. Treat `viewThumbnail` entries as view metadata, not app images. Do not request arbitrary `resourceRoot`, binary/image bytes, or broad uncapped discovery.

Discover Designer-created component seeds before authoring fragile component JSON:

```json
{
  "action": "seedViewsList",
  "targetProject": "<projectName>",
  "seedViewPrefix": "<seedViewFolderPrefix>",
  "componentType": "ia.<component.family>",
  "maxResults": 50
}
```

Read one seed view only when needed:

```json
{
  "action": "seedViewRead",
  "targetProject": "<projectName>",
  "seedViewPrefix": "<seedViewFolderPrefix>",
  "viewPath": "<seedViewPath>",
  "includeViewJson": false,
  "includeResourceJson": true
}
```

Extract one exact component seed:

```json
{
  "action": "componentSeedRead",
  "targetProject": "<projectName>",
  "seedViewPrefix": "<seedViewFolderPrefix>",
  "viewPath": "<seedViewPath>",
  "componentType": "ia.<component.family>",
  "componentIndex": 0
}
```

Keep `seedViewsList` metadata-only. Use exact returned `viewPath`, `componentType`, `componentName`, and hashes. Do not call `componentSeedRead` with only `componentType`; first choose the concrete seed `viewPath` from `seedViewsList`. Do not treat seed JSON as a full schema, do not substitute near-match component types, and do not copy project-specific tag paths, params, styles, images, or bindings without parameterizing them.
For built-in Perspective symbol pages, prefer exact seeds for `ia.symbol.pump`, `ia.symbol.valve`, `ia.symbol.vessel`, `ia.symbol.motor`, and `ia.symbol.sensor`; after apply, use `viewRead` to confirm the live view contains the expected `ia.symbol.*` component types and any Coordinate Container `props.pipes` definitions, then use browser evidence and follow-up `tagRead` to verify operator controls manipulate exact symbol props such as Valve `props.valve`, Valve `props.reverseFlow`, Vessel `props.value.value`, Pump `props.variant`, and pipe `visible`/`fill`/`stroke`.
For Flex Repeater pages, prefer exact seeds for `ia.display.flex-repeater`; after apply, use `viewRead` to confirm `props.path`, the `props.instances` property binding, and child `params.*` inputs. Use `pageValidate` with the child view in `dependencyViewPaths`, then browser-open the page and verify each repeated card receives distinct top-level instance params with no child default text.
For View Canvas pages, prefer exact seeds for `ia.display.viewcanvas`; after apply, use `viewRead` to confirm `props.instances[].viewPath` and `viewParams` point at packaged child views and child input params, use `pageValidate` with all dependency views, and browser-click at least one instance to prove `onInstanceClicked` selection updates parent/detail state.
For View Canvas command popups, require the package to include dependency child views, popup views, and command scripts; after apply, prove one blocked interlock and one accepted writeback in-browser, then verify the final command/readback tags with `tagRead`.
For UDT-parameter-backed symbol pages, read and write copied instance parameter paths such as `[<tagProvider>]<folder>/<Instance>/Parameters.SymbolVariant`; verify the copied parameter path and dependent member/expression paths with `tagRead`. Normalize `"0"`/`"1"` and numeric strings before using those parameter values as symbol Boolean/numeric props.
For chart components such as Time Series Chart, prefer exact `componentSeedRead` shapes or minimal seed-style `props.series[].data`. For custom Time Series plots, verify `props.plots[].trends[].columns` is an object array with `key` values matching series data fields. Treat browser console property errors after a passing `pageValidate` as real component-schema failures; visual proof should confirm rendered SVG/canvas marks. Ignore only unrelated static asset noise such as Ignition favicon 404s.

Discover Named Queries before authoring database-backed pages:

```json
{
  "action": "namedQueriesList",
  "targetProject": "<projectName>",
  "namedQueryPrefix": "<optionalQueryFolderPrefix>",
  "maxResults": 200
}
```

Read one candidate:

```json
{
  "action": "namedQueryRead",
  "targetProject": "<projectName>",
  "queryPath": "<namedQueryPath>",
  "namedQueryPrefix": "<allowedQueryPrefix>",
  "includeSql": true
}
```

Preview only allowlisted read-only bounded queries:

```json
{
  "action": "namedQueryPreview",
  "targetProject": "<projectName>",
  "queryPath": "<namedQueryPath>",
  "namedQueryPrefix": "<allowedQueryPrefix>",
  "parameters": {"<paramName>": "<value>"},
  "maxRows": 25
}
```

Use returned `columns` and `rows` as a capped sample for Perspective table/KPI design. Do not execute update/action queries through preview. Do not pass QueryString/Database parameters unless a separate user-approved workflow validates them. For runner `0.3.54+`, QueryString previews require `allowQueryStringParameters: true` plus `queryStringParameterAllowlist`; Database previews require `allowDatabaseParameters: true` plus `databaseParameterAllowlist`. Exact rejected/bad values should fail before execution, and Java-backed execution failures should return a JSON error envelope instead of HTTP 500. If preview rejects an unbounded or over-broad query, add a small numeric top-level DB-side `LIMIT`/`TOP`/`FETCH` within the preview cap or enable a safe max return size before using it as a dashboard source.
For Perspective query bindings, keep each component property value wrapped as `{"binding": {...}}` under `propConfig`; include query params under `binding.config.parameters`; validate missing params with `namedQueryPreview`; then prove the live page in-browser because `pageValidate` does not execute bindings.

Read one allowlisted view:

```json
{
  "action": "viewRead",
  "targetProject": "<projectName>",
  "viewPath": "<allowedViewPath>",
  "allowedViewPrefix": "<allowedViewPrefix>",
  "includeViewJson": true,
  "includeResourceJson": false
}
```

Use the returned `viewSha256` before overwriting an existing view. For overwrite dry-run/apply, set `allowOverwrite: true`, set `requireViewSha256ForOverwrite: true`, and pass the current hash in `expectedViewSha256ByViewPath`. A missing, wrong, or stale hash is a stop condition and should fail during dry-run before writing. After a successful apply, immediately `viewRead` again; future overwrites must use the new hash, not the pre-apply hash. Do not request views outside the approved prefix.

## Page Validation

Use `pageValidate` after apply as a structural gate, not as render proof:

```json
{
  "action": "pageValidate",
  "targetProject": "<projectName>",
  "pagePath": "<pagePath>",
  "expectedViewPath": "<viewPath>",
  "allowedViewPrefix": "<allowedViewPrefix>",
  "allowedRoutePrefix": "<allowedRoutePrefix>",
  "dependencyViewPaths": ["<embeddedOrReusableViewPath>"],
  "dependencyScriptPaths": ["<projectLibraryScriptPath>"],
  "allowedScriptPrefix": "<scriptPathPrefix>",
  "expectedViewSha256ByViewPath": {
    "<viewPath>": "<expectedLiveViewSha256>"
  },
  "expectedScriptSha256ByScriptPath": {
    "<projectLibraryScriptPath>": "<expectedLiveCodeSha256>"
  }
}
```

Treat `routeViewMismatch`, `routeMissing`, `viewMissing`, `scriptMissing`, `viewHashMismatch`, and `scriptHashMismatch` as stop conditions until the package or expected inputs are corrected. Route objects must use a non-empty string `viewPath`, never `view`; missing/null/empty `viewPath` or a non-existent target view is a stop condition. A passing `pageValidate` means the route/resource wiring exists; it does not prove startup scripts, bindings, components, session connectivity, interactions, or Designer startup.

## Recent Logs

Capture time before the change, then query only the relevant apply/render window:

```json
{
  "action": "logQuery",
  "sinceEpochMillis": 0,
  "levels": ["ERROR", "WARN"],
  "loggerContains": "<stableLoggerSuffixOrName>",
  "messageContains": "<pageOrRunMarker>",
  "maxResults": 25,
  "tailBytes": 524288
}
```

Require `sinceEpochMillis` or `sinceMinutes`, at least one narrow text/logger filter, and capped results. Check `matchedCountBeforeCap`, `truncated`, and `tailWindowTruncated`; narrow noisy queries before reading entries. Gateway wrapper logs may abbreviate logger names, so prefer a stable logger suffix when filtering. On runner `0.3.61+`, use `includeRotated: true` with `maxLogFiles` only when failures may have rolled out of the current wrapper log; preserve `sourceFiles` and each entry's `sourceFileName`, and reduce `tailBytes`/`maxLogFiles` if the total-tail-byte cap rejects the scan. Logs diagnose failures; browser/render validation proves the page.

## Tag Discovery

Tag discovery is read-only.

List providers:

```json
{"action":"tagProviders","maxResults":100}
```

Browse tags:

```json
{
  "action": "tagBrowse",
  "path": "[<tagProvider>]<folderPath>",
  "recursive": true,
  "maxResults": 1000,
  "includeValues": false
}
```

For scalable Perspective pages, use `tagBrowse` to validate the root folder/provider and discover UDT instances, then inspect `truncated` and `totalAvailable`; do not treat a capped result as complete until the response proves all needed rows were returned. Author the page so a parent view/script builds a row or repeater model from that root. Do not copy-paste one hard-coded full tag path per asset when a folder root plus `view.params`/`view.custom` model can drive the page.

Read explicit tag values:

```json
{"action":"tagRead","paths":["[<tagProvider>]<tagPath>"],"maxResults":100}
```

Use fully qualified `[provider]path` values. Treat the returned `value` as usable only when `quality` is good; preserve `timestamp` in diagnostics when freshness matters.

Probe historian-backed data:

```json
{"action":"historyProbe","paths":["[<tagProvider>]<tagPath>"],"rangeMinutes":60,"returnSize":5}
```

Do not treat a good current value as proof of tag history. For trend/history components on runner `0.3.137+`, require `queryOk: true`, `sampleCountQueryOk: true`, `goodSampleHistoryAvailable: true`, and a positive `goodStoredSampleCount` or per-tag `tagStats[].goodStoredSampleCount`; if false, use a current-value display or state the good-quality historian dependency. Treat `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` as aliases, and treat `valueQueryHistoryAvailable`, `nonNullCount`, `hasData`, and `lastValue` as diagnostics, not good-sample proof.
Keep Alarm Status Table and Alarm Journal Table validation separate: `alarmStatusQuery` verifies current alarm state for `ia.display.alarmstatustable`, while `ia.display.alarmjournaltable` depends on a configured Alarm Journal/profile and uses singular `props.filter` plus a date range. For journal tables on runner `0.3.60+`, use `alarmJournalQuery` with the component's discovered `props.name` as explicit `journalName`; runner `0.3.97+` rejects default/omitted journal profile requests because it cannot verify Ignition's exactly-one-journal omission condition. Do not guess profile names such as `Journal`. On runner `0.3.96+`, both `alarmStatusQuery` and `alarmJournalQuery` must include a narrow source/path/displayPath filter before execution. On route-param detail pages, bind Alarm Status Table `props.filters.active.conditions.displayPath` and Alarm Journal Table `props.filter.conditions.displayPath` from `view.params.<assetId>` or a derived display-path pattern, then verify the same concrete filter with `alarmStatusQuery` and `alarmJournalQuery`.

Query current alarms only with explicit filters:

```json
{
  "action": "alarmStatusQuery",
  "displayPath": "<displayPathPattern>",
  "states": ["ActiveUnacked", "ActiveAcked"],
  "priorities": ["Critical", "High", "Medium", "Low"],
  "maxResults": 25
}
```

Require at least one narrow `source`, `path`, or `displayPath` filter on runner `0.3.96+`; provider-only filters do not bound backend work. Use this to verify Alarm Status Table pages; do not use broad Gateway-wide alarm scans.

Create complete UDT fixtures with `udtScaffold` when available:

```json
{
  "action": "udtScaffold",
  "provider": "<tagProvider>",
  "typePath": "<relativeTypeFolder>/<TypeName>",
  "instanceFolder": "<normalTagFolder>",
  "allowedTypePathPrefix": "[<tagProvider>]_types_/<relativeTypeFolder>",
  "allowedInstancePathPrefix": "[<tagProvider>]<normalTagFolder>",
  "requiredOverrideMembers": ["PV", "Status"],
  "members": [
    {"name": "PV", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float4", "value": 0.0},
    {"name": "Status", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "String", "value": "Unknown"}
  ],
  "instances": [
    {"name": "Asset001", "memberOverrides": {"PV": 12.3, "Status": "Ready"}}
  ],
  "dryRun": true
}
```

For writes, set `dryRun` false and add `{ "confirmUdtScaffold": "SCAFFOLD_UDT" }`. Keep `typePath` and `typeId` relative to `[provider]_types_`; keep `instanceFolder` under normal `[provider]` tags. On runner `0.3.112+`, a nested step with `ok: false` or `allGood: false` returns top-level `ok: false` with `failedStep`, `failedStepResult`, and `stepResults`; on older runners, inspect `stepResults[]`, nested `allGood`, and nested `qualityCodes` yourself before trusting a completed response. On runner `0.3.143+`, failed confirmed scaffold steps with missing, null, or empty `qualityCodes` mark all step recovery paths from preflight and attempt conservative recovery; preserve `writesStarted`, `completedSteps`, `preflightExistingPaths`, `preflightNewPaths`, `recoveryAttempted`, `recoveryAllGood`, `recoveryRequired`, and nested `recovery` details such as `deletePaths` and `restorePaths`. After apply, read the returned `memberReadPaths` with `tagRead` and bind Perspective to instance/member paths, not UDT definition paths.
If a scaffold includes many members, instances, or per-instance overrides, estimate `plannedTagCount = 1 + member count + instance count + override tag count` and set `maxItems` high enough on both dry-run and apply while keeping the same allowed prefixes. A dry-run rejection for `planned tag count exceeds maxItems` is a guardrail, not a Gateway failure.

Create scaffold tags/UDTs through `tagConfigure` only under approved prefixes:

```json
{
  "action": "tagConfigure",
  "basePath": "[<tagProvider>]<approvedFolder>",
  "allowedTagPathPrefixes": ["[<tagProvider>]<approvedFolder>"],
  "collisionPolicy": "a",
  "dryRun": true,
  "tags": [
    {"name": "DemoValue", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float4", "value": 1.23}
  ]
}
```

For writes, set `dryRun` false and add `{ "confirmTagConfigure": "CONFIGURE_TAGS" }`. On runner `0.3.111+`, bad returned QualityCodes or returned-code count mismatches should come back as top-level `ok: false` with `TAG_CONFIGURE_BAD_QUALITY` or `TAG_CONFIGURE_QUALITY_CODE_COUNT_MISMATCH`; still inspect `allGood`, `qualityCodes`, and readback. On older runners, treat `ok: true` plus `allGood: false` or any `qualityCodes[].good: false` as a failed write. Put UDT definitions under `[<tagProvider>]_types_/...`; create UDT instances under normal tag paths and bind Perspective to instances, not definitions. Reference tags require `valueSource: "reference"` and a non-empty `sourceTagPath`; do not use Reference-tag `sourceTagPath` parameters as proof of dynamic UDT path behavior without member readback.

For UDT scaffolds:

- Create `UdtType` definitions under `[<tagProvider>]_types_/...`.
- Create `UdtInstance` tags under normal `[<tagProvider>]...` folders with `typeId` relative to `_types_`.
- To initialize different member values per UDT instance, create the instance first, then call `tagConfigure` with `basePath` set to the instance path, `collisionPolicy: "m"`, and `tags` containing member names/values.
- Use `tagConfigure` directly rather than `udtScaffold` when a test must prove explicit UDT instance `parameters` overrides; `udtScaffold` is for complete fixture scaffolds, not fine-grained copied-parameter write tests.
- For alarm component fixtures, `AtomicTag` configs may include `alarms` arrays; use numeric setpoints and verify runtime paths such as `[<tagProvider>]<tagPath>/Alarms/<alarmName>.IsActive` with `tagRead`. For per-instance UDT alarm overrides, merge alarm config before changing the value that activates the alarm so current alarm status captures the final display path.
- Verify instance member paths with `tagRead` before binding Perspective components.
- Use scaffold tags/UDTs for demos and tests; keep real process writeback in Project Library scripts.
- Prefer this existing scaffold path over adding broader tag-write endpoints unless a page-building test proves a specific gap.

Do not add tag imports, provider creation, database edits, or Gateway configuration changes to the low-touch runner.

## Safety Rules

- Treat the runner as staging/development tooling unless production approval is explicit.
- Use HTTPS, loopback-only access, Web Dev auth/roles, a caller-managed token, or equivalent protection.
- Allowlist project names, view prefixes, route prefixes, resource file types, and package sources.
- Reject arbitrary filesystem paths and unrestricted zip contents.
- Keep secrets in runtime input, environment variables, or the instance profile; never print them.
- Require explicit confirmation strings for every write action.
- Apply the non-deletion rule during cleanup, rollback planning, backups, and temp-file handling.
- Keep backups of every modified project resource and its `resource.json` metadata before writes.
- For existing view overwrites, prefer `viewRead` then `expectedViewSha256ByViewPath`; treat drift as a stop condition.
- If Ignition returns HTTP 402, check trial/module state before debugging the runner.

## Validation

After apply:

- Confirm the target project is the project the user expects.
- Confirm the project scan/import completed; on runner `0.3.88+`, require `scanCompleted: true` after writeful mutations and stop on `recoveryRequired: true`.
- Open `<gatewayUrl>/data/perspective/client/<projectName>/<pagePath>`.
- Verify rendered page markers/components, not only HTTP 200.
- Verify tag bindings resolve or degrade clearly.
- Verify Gateway/Perspective/browser logs have no relevant errors.
- Treat client-side component errors in browser console logs as failures even when `pageValidate`, `viewRead`, and focused Gateway `logQuery` pass.
- For page-config/project-resource writes, smoke-test Designer startup when feasible; browser runtime can work while malformed page config breaks Designer.
- Treat Perspective project-resource fetch failures as validation failures even when route wiring is structurally valid; malformed script-action fields such as missing/null `scope` can break project serialization after apply.
- Scan Designer/Gateway launch logs for `EditablePageConfig`, `Error loading layout`, `NullPointerException`, and `ScriptIndexer -- Failed to parse`.
- If Designer launch testing leaves hidden Designer/Launcher Java processes, stop only child processes matching `BootstrapSwing`, `DesignerStartupHook`, or `DesignerLauncher`; do not kill the Gateway service process.
- If Designer is open, refresh/reopen the project and confirm `Perspective > Views > <viewPath>` appears.
- Report changed view paths, route paths, backup location, and rollback note.

## Ignition 8.1 Docs

Use Ignition 8.1 docs unless the user requests another version:

- Perspective module: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective
- Perspective View Canvas: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-view-canvas
- Perspective Embedded View: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-embedded-view
- Perspective Popup Views: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/views-in-perspective/popup-views
- Perspective Component Message Handlers: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/component-message-handlers
- `system.perspective.openDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-openDock
- `system.perspective.closeDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-closeDock
- `system.perspective.toggleDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-toggleDock
- `system.perspective.openPopup`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-openPopup
- `system.perspective.closePopup`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-closePopup
- `system.perspective.sendMessage`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-sendMessage
- `resource.json`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/resource-json-file
- `system.project.requestScan`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-project/system-project-requestScan
- `system.tag`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag
- `system.tag.configure`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-configure
- Web Dev module: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/web-dev
- Named Queries: https://www.docs.inductiveautomation.com/docs/8.1/platform/sql-in-ignition/named-queries
- `system.db.runNamedQuery`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-db/system-db-runNamedQuery

---

## Latest Staged Source Candidate — Skill 1.0.130
---
name: ignition-perspective-host-builder
description: Apply, update, inspect, or validate Ignition 8.1 Perspective resources on a reachable Gateway through the approved local host-runner workflow. Use when Codex has same-PC/host access and the desired result is an applied running-Gateway change, not a portable import zip. For authoring the Perspective view/package itself, use ignition-perspective-import-zip first.
---

# Ignition Perspective Host Builder

Skill version: `1.0.130`
Stack version: `starter-2026.07.06.04`
Runner contract version: `0.3.148`

## Scope

Use the configured Ignition host runner as the host-side access path. Keep raw connection details in the runner reference, local environment, or task handoff, not in this skill.

This skill applies or inspects resources on a running Ignition 8.1 Gateway. It is not the place to teach Perspective JSON design. If a page/view/package must be authored, create the artifact with `ignition-perspective-import-zip`, then return here to dry-run, apply, and validate it.
Keep runner request details to the minimum needed; the main goal is reliable Perspective page creation and validation.
Treat the runner contract as support tooling. Add or use runner capabilities only when they help build, apply, or verify a real Perspective page.

Do not use default credentials, guessed connection details, direct filesystem writes, native file chooser automation, or ad hoc Gateway import methods unless the user explicitly changes the access model.

## Non-Deletion Rule

Do not delete, remove, prune, or clean up live Gateway/project/tag resources unless the user explicitly commands that deletion in the current task. This includes files, Perspective views/routes/styles/images, scripts, named queries, tags, UDTs, alarms, database rows, backups, and temp resources. Default to create/update/merge/validate; if deletion seems required, stop and ask.

## Runtime Values

Get these from the user, environment, instance profile, or active host discovery:

- `<gatewayUrl>`
- `<projectName>`
- `<packagePath>` or package bytes
- `<viewPath>`
- `<pagePath>`
- `<allowedViewPrefix>`
- `<allowedRoutePrefix>`
- configured host-runner connection profile when applying live

Never write real tokens, usernames, passwords, cookies, local install paths, or customer identifiers into this skill or generated reusable docs.

## Runner Request Rules

Do not copy transport URLs, headers, tokens, or an exhaustive runner capability catalog into this skill. Keep that material in the dedicated runner reference and use the configured runner client/profile from the task context.

Before live work, use runner health/discovery to confirm the runner version, target project, callable capabilities, and feature flags. Include a caller-generated `requestId` on every request when possible, and require the same `requestId` in success, validation-error, auth-error, and write responses.

Use dry-run before every write. Apply only after the dry-run response proves the target project, route/view prefixes, package contents, dependencies, and expected hashes match the intended change. If health does not advertise a capability, do not invent or call it.

For runner `0.3.148+`, the tested Perspective runtime/asset capabilities include live sessions/pages/views, guarded session termination, Perspective theme/font/icon-library management, and branding metadata readback. Keep the exact callable names, confirmations, and transport details in the runner reference; this skill should only carry the page-building rule that discovery/readback/rollback evidence is required before declaring success.

## Apply Payload

Use base64 package transfer unless the runner and user explicitly choose a fixed host inbox.

```json
{
  "action": "dryRun",
  "requestId": "<stableRequestId>",
  "targetProject": "<projectName>",
  "packageName": "<packageName>.zip",
  "packageBase64": "<base64Zip>",
  "allowOverwrite": true,
  "requireViewSha256ForOverwrite": true,
  "expectedViewSha256ByViewPath": {
    "<viewPath>": "<viewSha256FromViewRead>"
  },
  "allowedViewPrefix": "<allowedViewPrefix>",
  "scanTimeoutSeconds": 10,
  "allowedRoutePrefix": "<allowedRoutePrefix>",
  "dependencyViewPaths": [
    "<embeddedOrReusableViewPath>"
  ],
  "dependencyScriptPaths": [
    "<projectLibraryScriptPath>"
  ],
  "sharedDockKeys": [
    "top",
    "left"
  ],
  "allowedScriptPrefix": "<scriptPathPrefix>",
  "routes": [
    {
      "pagePath": "<pagePath>",
      "viewPath": "<viewPath>",
      "title": "<pageTitle>"
    }
  ]
}
```

For apply, change `action` to `apply` and add:

```json
{ "confirmApply": "APPLY" }
```

Send explicit `routes` for small generated packages. Do not rely on package route auto-discovery unless `page-config/config.json` contains only intended routes.

If a routed view embeds or depends on other project views that are included in the package, include those packaged child/dependency views in `dependencyViewPaths`; dry-run/apply validates and copies only explicitly listed packaged dependencies. If the view intentionally references an already-existing target reusable view, first discover it with `viewsList`/`styleResourcesList` and `viewRead`, document it as a target prerequisite, and do not list it in `dependencyViewPaths` unless the package also contains that view. A missing listed packaged dependency should fail dry-run before apply. For dynamic Embedded View shells, do not rely on the runner to infer every possible `props.path` value from parent state or from extra packaged views.

If a routed view calls Project Library scripts, include those scripts in `dependencyScriptPaths` and keep them under `allowedScriptPrefix`. The runner copies only `code.py` and `resource.json` for explicitly listed script resources.

If a routed view or Project Library helper needs packaged Named Queries, include those queries in `dependencyNamedQueryPaths` and keep them under `allowedNamedQueryPrefix`. After apply, require `validatedNamedQueries`, `copiedNamedQueries`, `namedQueryRead` metadata, and `pageValidate.namedQueryChecks` before relying on the query at runtime. Do not package QueryString or Database params unless the workflow has an explicit unsafe-param allowlist; keep Database `<Parameter>` execution target-specific and require runtime execution proof on the target connection.

For runner `0.3.98+`, treat all runner path prefixes as exact-or-child allowlists unless this skill explicitly calls out a documented namespace. A prefix such as `LLM Tests/A` allows `LLM Tests/A` and children, not siblings such as `LLM Tests/ABC`.

For shared docked navigation/status shells, package each dock view and pass explicit `sharedDockKeys` for the top-level page-config `sharedDocks` keys to merge. Allowed keys are `top`, `bottom`, `left`, `right`, and `cornerPriority`. Treat dry-run/apply `sharedDockViewPaths` as dependency views and require apply `mergedSharedDockKeys` to match the intended keys. Do not use `sharedDockKeys` for route-specific page `docks`.

For shared dock runtime behavior, use runner readback for structure and browser proof for behavior. `pageValidate`/`viewRead` can prove the dock views exist; bounded page-config readback can prove `id`, `show`, `handle`, `modal`, `autoBreakpoint`, and `viewPath`; only browser tests prove real handle clicks, `openDock`/`closeDock`/`toggleDock` actions, modal overlay blocking, and wide/narrow breakpoint collapse.

## Workflow

1. Call `health`; require JSON with `ok: true`. Stop on empty/non-JSON HTTP 200 because the Web Dev body is not invoking the runner. Confirm only the callable actions and feature flags needed by the current Perspective workflow, such as package transfer, route/view validation, log diagnostics, tag/query/alarm probes, shared docks, exact-or-child prefix allowlists, bounded backend query work, final-state validation, live Perspective runtime discovery, and Perspective theme/font/icon/branding asset support.
2. If version/module/path/trial state matters, call `gatewayInfo` before deeper debugging.
3. For existing project context, call `routesList` and `viewsList` before choosing new route/view paths. Use `viewRead` before editing an existing allowlisted view. If page design must match existing project styling, call `styleResourcesList` and use discovered style/view/image names exactly. Treat `viewThumbnail` image entries as metadata for views, not general app images. For Perspective module themes, fonts, icon libraries, or branding, call the matching list/read action first; dry-run every upsert, apply only with the exact confirmation string, verify readback, then check `backupList` with `targetProject:"_gateway"` because those backups are Gateway-level assets, not project resources.
4. Before hand-authoring fragile component JSON, call `seedViewsList`; use `seedViewRead` or `componentSeedRead` for a matching Designer-created seed. `componentSeedRead` requires a concrete `viewPath` returned by `seedViewsList`; do not call it with only `componentType`. Copy only the minimal exact component shape, then parameterize project/tag/binding/style values. For Tag Browse Tree pages, extract an exact `ia.display.tag-browse-tree` seed, verify `props.root.path`, explicit `props.selection.mode`, sibling `../Tag Browse Tree.props.selection.values` bindings, and `onNodeClick` `event.path`/`event.name` only when side effects/tag reads are needed; browser-expand folders through disclosure controls and click at least two leaf tags with final `tagRead` proof. For built-in symbol pages, extract exact `ia.symbol.*` seeds and bind only props present on that symbol; later verify with `viewRead` plus browser clicks that chosen props such as Pump `props.variant`, Valve `props.valve`/`props.reverseFlow`, Vessel `props.value.value`/fill props, state, value, orientation, or pipe visibility actually change. For Flex Repeater pages, extract or inspect an exact `ia.display.flex-repeater` seed, bind `props.instances` from parent `view.custom`, pass child params as top-level instance keys matching the packaged child view's `view.params`, and verify in-browser that distinct cards render without default-param leakage. For dynamic Embedded View shell/tab pages, use `viewRead` to confirm `ia.display.view.props.path` is bound from parent state, child inputs are declared in `view.params`, and every possible child path is supplied to `dependencyViewPaths`/`pageValidate`; browser-click each tab because dry-run can pass when an unlisted child is still present in the package. For View Canvas pages, extract an exact `ia.display.viewcanvas` seed, use `props.instances[].viewPath` plus `viewParams`, include child views in `dependencyViewPaths`, then verify `onInstanceClicked` parent/detail updates in-browser. For View Canvas command popups, verify selected state flows from parent `view.custom` into embedded child `props.params`, child scripts use `self.view.params.*`, popup views/scripts are listed as dependencies, and browser evidence proves both blocked and accepted commands with final `tagRead`. For route-param equipment detail pages, validate the dynamic route key such as `/equipment/:assetId` with `pageValidate`, then browser-open a concrete URL; bind component filters from `view.params` rather than hard-coded asset ids. For Alarm Journal Table pages, extract an exact `ia.display.alarmjournaltable` seed and preserve/discover its `props.name` profile before authoring filters; do not substitute a guessed profile name. For reusable multi-symbol faceplates, `viewRead` should show fixed `ia.symbol.*` components with `meta.visible` bindings, and browser evidence should select at least one visible asset and one hidden/disabled asset.
5. If page design needs database-backed tables/KPIs, call `namedQueriesList`, `namedQueryRead`, then `namedQueryPreview`; design from returned columns/rows, not guessed SQL/table names. For runtime query-bound pages, `viewRead` should show query bindings under each component `propConfig`, `pageValidate` should include any packaged `dependencyNamedQueryPaths`, and browser evidence should prove rendered table rows, KPI labels, and zero/empty states. Do not treat preview rows alone as runtime proof. On runner `0.3.96+`, make the SQL `LIMIT`/`TOP`/`FETCH` or Named Query max return size no larger than the request `maxRows`; a larger DB-side cap can be rejected even if the response would be locally truncated. On runner `0.3.99+`, put the SQL row limiter on the outer/top-level query; nested subquery or CTE limits do not prove the final Named Query result is backend-bounded. For QueryString or Database params, prove both rejected and allowlisted values through runner allowlists before execution; do not generalize Database `<Parameter>` runtime behavior from package metadata alone, even when `namedQueryRead` synthesizes the `database` parameter.
6. If page design needs real tags, call `tagProviders` and `tagBrowse` read-only. Prefer validating a provider/root folder and UDT shape over hard-coding every device path. On runner `0.3.83+`, treat `truncated: true` or `totalAvailable > returnedCount` as an incomplete browse; narrow the path/filter or increase `maxResults` before building a row model. Use `tagRead` for explicit current values and require good quality before trusting values. UDT instance parameters are read as `Parameters.ParamName` paths; normalize Boolean/numeric string readbacks before binding to Boolean/numeric Perspective props, preserve `None`/empty/literal `"null"` distinctions in row models, and omit overrides when defaults should apply. Use `historyProbe` before building trend/history charts; on runner `0.3.137+`, require `goodSampleHistoryAvailable: true` plus positive `goodStoredSampleCount` or per-tag `tagStats[].goodStoredSampleCount` before claiming good-quality stored historian samples. Do not treat false/zero good-sample fields as proof that no bad-quality rows exist. On runner `0.3.108+`, parse non-2xx JSON from `historyProbe`, `alarmStatusQuery`, `alarmJournalQuery`, and `auditQuery` because primary backend failures now return top-level `ok: false` with preserved diagnostic fields. For alarm components, use `alarmStatusQuery` for current state and `alarmJournalQuery` for historical journal rows with the same narrow source/path/displayPath or displayPath-derived filters the component will use; provider-only or state-only probes do not bound backend work on runner `0.3.96+`. Use the exact Alarm Journal profile from the component's `props.name`, target docs, or operator-provided Gateway configuration as `journalName`; runner `0.3.97+` rejects default/omitted journal profile requests. Use `udtScaffold` for complete fixture UDT types/instances when available, but require each returned scaffold `stepResults[]` item to be successful with `allGood: true` and good nested `qualityCodes`; runner `0.3.112+` converts failed nested steps to top-level `ok: false`, while older runners still need manual nested-step inspection. On runner `0.3.113+`, preserve `recoveryRequired` and related recovery metadata when a partially completed scaffold must be restored or manually reconciled. On runner `0.3.143+`, a failed confirmed scaffold step with missing, null, or empty `qualityCodes` is treated as unknown-mutated, so preserve the full recovery response and verify cleanup/restore before issuing more tag writes. Use `udtTagEventScriptProbe` only for the fixed UDT parameter/tag-event probe; otherwise use `tagConfigure` only under explicit allowed prefixes. For tag-event probe dry-runs on runner `0.3.94+`, inspect `pollAttemptsCapped` and `probeSyncWaitMaxMs` before apply and treat response `pollAttempts` as the effective capped count. On runner `0.3.95+`, inspect `failureCleanupPaths` before apply and, if a probe apply fails after creation begins, preserve `failureCleanup` evidence while treating cleanup as best-effort rather than proof of a successful probe. On runner `0.3.139+`, use top-level `recoveryAttempted`, `recoveryAllGood`, and `recoveryRequired` to decide whether cleanup follow-up is needed. Dry-run tag writes first, require the action confirmation string for writes, then require `ok: true`, `allGood: true`, good `qualityCodes`, and `tagRead` verification before binding the page; on runners before `0.3.111`, manually treat `ok: true` plus bad QualityCodes as a failed write.
7. Obtain a validated package artifact from the import-zip/page-authoring flow.
8. Call `dryRun`.
9. Require `ok: true`, expected `validatedViews` including dependency and shared dock views, expected `validatedRoutes`, expected `checkedViewHashes` when overwriting, and no unexpected target project. Require `routeConflictCount: 0` unless overwriting an existing route is intentional; when conflicts exist, inspect `routeConflicts[].packageRoute`, `routeConflicts[].targetRoute`, `willOverwrite`, and `resolutionOptions` before choosing rename, overwrite, or stop. A route conflict dry-run with `allowOverwrite: false` should fail without writing; an intentional overwrite dry-run should show `willOverwrite: true` before any apply. When `health.features` includes `applyPackageWorkDirCleanup`, require default dry-run cleanup fields: `keepWorkDir: false`, `workDirKept: false`, `workDirCleaned: true`, and `workDirCleanupStatus: "cleaned"`.
10. Call `apply` only after dry-run passes.
11. Require `ok: true`, expected `copiedViews` including dependency/shared dock views, expected `copiedScripts`, expected `copiedNamedQueries` when using Named Query dependencies, expected `mergedRoutes`, expected `mergedSharedDockKeys` when using `sharedDockKeys`, backup evidence, `scanCompleted: true`, and no `recoveryRequired`. When `health.features` includes `applyPackageWorkDirCleanup`, require default apply cleanup fields: `keepWorkDir: false`, `workDirKept: false`, `workDirCleaned: true`, and `workDirCleanupStatus: "cleaned"`. When `health.features` includes `applyPackageStaleViewFilePruning` and an intentional overwrite omits a previously present view `thumbnail.png`, inspect `prunedStaleViewFiles` / `prunedStaleViewFileCount`, then use `projectResourceRead`, `viewRead`, or `pageValidate` to prove the final resource matches `resource.json.files`. When `health.features` includes `applyNonViewFinalStateValidation` and the package includes scripts, Named Queries, or page config, require no `validationStage` failure; preserve the full response if `validateCopiedScripts`, `validateCopiedNamedQueries`, or `validateMergedPageConfig` appears.
12. If `pageValidate` is available, require `ok: true`, `routeMatchesExpectedView: true`, empty `issues`, expected view/script/Named Query existence, and hash matches when expected hashes are supplied. For dynamic Embedded View shells, pass the full set of possible child view paths as `dependencyViewPaths`; missing listed child views should fail, but unlisted dynamic children are a caller mistake that validation cannot infer. For shared docks, pass returned dock view paths as `dependencyViewPaths` or verify them with `viewRead`; use bounded page-config readback only when proving dock ids/display properties and browser proof for runtime behavior.
13. If `logQuery` is available, query only the recent apply/render window with severity plus logger/message filters; use results as diagnostics, not render proof.
14. For operator action logging workflows, browser-click the tested buttons/components and verify all intended records through `tagRead`, SQL/Named Query readback, `auditQuery`, and focused `logQuery`. For `auditQuery`, provide explicit audit profile names through `profile`, `auditProfileName`, or `profiles`; runner `0.3.82+` rejects `useDefaultProfile` in WebDev/Gateway scope. Include a time window, caps, and narrow actor/action/target/value/system filters; on runner `0.3.96+`, broad audit scans are rejected before execution and `contextFilter` alone does not bound backend work. Poll briefly after controlled audit writes because readback can lag. Use bounded `scriptEval` for audit readback only when `auditQuery` is unavailable or insufficient. Use a stable logger suffix/run ID/message filter because wrapper logs may abbreviate dotted logger names. If a bounded `scriptEval` diagnostic imports a Project Library module immediately after apply, retry briefly after project scan evidence before declaring the module missing. For non-Button action logging, require one clicked/readback row per component type and record which component-specific `self.props` value was passed to the helper.
15. For disabled/gated command pages, browser-prove visible dependency reasons, disabled-click failure for unavailable controls, and any custom disabled opacity/background on an inspectable element. Then use a deliberate guard-probe/bypass path and final `tagRead` to prove the Project Library helper blocks unsafe writes and leaves blocked target tags unchanged.
16. For table/list-to-detail pages, use `viewRead` to confirm explicit table row selection, hidden helper columns for fields used by detail/action logic, `onSelectionChange`, one root/parent `scripts.messageHandlers` entry with `pageScope: true`, and the expected `sendMessage` type. Browser-click both table and list/card selectors, then verify visible detail state plus durable result tags/logs; `pageValidate` alone does not prove the interaction.
17. For Flex fill/progress visualizations, use `viewRead` to confirm fill-child `position.basis` bindings, then browser-verify visible readout text and actual flex style/width for 0, mid, 100, clamped over-range, and bad-quality/null fallback cases. Use `tagRead` to prove the source quality behind fallback rows.
18. For route-param indirect tag binding pages, require `health.features` to include `indirectTagReferenceLint`, dry-run one bad object-reference package when practical, use `viewRead` to confirm `config.mode: "indirect"`, string `references`, literal fixed-root `tagPath`, and small `fallbackDelay`, then browser-open at least two concrete route URLs to prove the same view switches values.
19. Validate the running Perspective route in a browser and report exact applied resources.
20. For project-resource/page-config writes, require the Gateway to reload the changed project resource through scan/reload/restart evidence before declaring success. If the Perspective project resource fetch returns HTTP 500 while `pageValidate` passes, inspect focused logs and `viewRead` for generated view JSON problems such as script actions with missing/null `scope`; repair by overwrite through dry-run/apply, not deletion.

## Backup And Rollback

List backups before risky changes or when recovery is needed:

```json
{"action":"backupList","targetProject":"<projectName>","maxResults":50}
```

Rollback uses runner-created backup folder names only. Dry-run first:

```json
{"action":"rollback","targetProject":"<projectName>","backupName":"<backupName>","dryRun":true}
```

For the write call, set `dryRun` false and add:

```json
{ "confirmRollback": "ROLLBACK" }
```

Require expected restore/remove counts, pre-rollback backup evidence, scan evidence, and route/view/resource validation after rollback. For runner `0.3.84+`, inspect `backupFormat: "fileChanges-v1"`, `restoredFiles`, and `removedFiles` in rollback dry-run before applying.
For runner `0.3.85+`, rollback apply can return `MUTATION_LOCK_BUSY`; wait for the active mutation to finish, rerun backup discovery and rollback dry-run, then apply with the exact confirmation only if the plan still matches.
For runner `0.3.86+`, rollback restores individual files through staged sibling temporary files and Java NIO atomic moves; legacy directory rollback is staged before replacement but is not a full multi-file transaction.
For runner `0.3.87+`, rollback still restores/removes the exact files recorded in the selected backup manifest; it does not restamp `resource.json` attributes during restore.
For runner `0.3.88+`, rollback apply must return `scanCompleted: true` after changed files. If it returns `PROJECT_SCAN_FAILED` with `recoveryRequired: true`, stop and inspect the scan error plus backup state before making more changes.
For runner `0.3.102+`, damaged `fileChanges-v1` rollback manifests with missing required backup files are rejected before mutation. Legacy `projectResourceImportZip` backups can restore backed-up overwritten files, but they report `createdFilesNotRemoved: true` because files created by the original legacy import cannot be inferred or removed.
For runner `0.3.141+`, if rollback apply returns `ROLLBACK_WRITE_FAILED`, stop and preserve the full response. Inspect `backupName`, `backupFormat`, `preRollbackBackupDir`, `failedStage`, `failedPath`, completed work lists, nested `rollbackFailure`, and `recoveryRequired` before attempting any follow-up recovery.
For runner `0.3.148+`, Perspective theme/font/icon asset backups list under `targetProject:"_gateway"` with `type:"perspectiveModuleAsset"` and must be rolled back with `targetProject:"_gateway"`. Expect `scanSkipped:true` and `restartOrRefreshMayBeRequired:true`; verify with the matching asset read/list action rather than `pageValidate`.

Runner maintenance workflows belong in the dedicated runner reference, not in this Perspective host-builder skill.

## Project Discovery

Read Gateway diagnostics:

```json
{
  "action": "gatewayInfo",
  "targetProject": "<projectName>",
  "includeModules": true,
  "maxModules": 80
}
```

Use `gatewayInfo` to confirm Ignition version, module presence/name/version/state/license status, runner path existence, and target project existence. Treat it as best-effort diagnostics; do not copy local paths, hostnames, or licensing details into reusable skills.

List existing routes:

```json
{"action":"routesList","targetProject":"<projectName>","routePrefix":"<optionalPrefix>","maxResults":1000}
```

List existing views:

```json
{"action":"viewsList","targetProject":"<projectName>","viewPrefix":"<optionalPrefix>","maxResults":1000}
```

Discover styling/resources before authoring styled pages:

```json
{
  "action": "styleResourcesList",
  "targetProject": "<projectName>",
  "stylePrefixes": ["<optionalStylePrefix>"],
  "reusableViewPrefixes": ["<optionalViewPrefix>"],
  "includeStylePreview": true,
  "includeViewStyleRefs": true,
  "includeViewThumbnails": false,
  "maxResults": 200
}
```

Use returned `stylePath`, `viewPath`, `themeName`, and project-image metadata exactly, unwrapping `items` arrays when the response is envelope-shaped. Do not invent style classes, reusable views, themes, or image URLs. Treat `viewThumbnail` entries as view metadata, not app images. Do not request arbitrary `resourceRoot`, binary/image bytes, or broad uncapped discovery.

Discover Designer-created component seeds before authoring fragile component JSON:

```json
{
  "action": "seedViewsList",
  "targetProject": "<projectName>",
  "seedViewPrefix": "<seedViewFolderPrefix>",
  "componentType": "ia.<component.family>",
  "maxResults": 50
}
```

Read one seed view only when needed:

```json
{
  "action": "seedViewRead",
  "targetProject": "<projectName>",
  "seedViewPrefix": "<seedViewFolderPrefix>",
  "viewPath": "<seedViewPath>",
  "includeViewJson": false,
  "includeResourceJson": true
}
```

Extract one exact component seed:

```json
{
  "action": "componentSeedRead",
  "targetProject": "<projectName>",
  "seedViewPrefix": "<seedViewFolderPrefix>",
  "viewPath": "<seedViewPath>",
  "componentType": "ia.<component.family>",
  "componentIndex": 0
}
```

Keep `seedViewsList` metadata-only. Use exact returned `viewPath`, `componentType`, `componentName`, and hashes. Do not call `componentSeedRead` with only `componentType`; first choose the concrete seed `viewPath` from `seedViewsList`. Do not treat seed JSON as a full schema, do not substitute near-match component types, and do not copy project-specific tag paths, params, styles, images, or bindings without parameterizing them.
For built-in Perspective symbol pages, prefer exact seeds for `ia.symbol.pump`, `ia.symbol.valve`, `ia.symbol.vessel`, `ia.symbol.motor`, and `ia.symbol.sensor`; after apply, use `viewRead` to confirm the live view contains the expected `ia.symbol.*` component types and any Coordinate Container `props.pipes` definitions, then use browser evidence and follow-up `tagRead` to verify operator controls manipulate exact symbol props such as Valve `props.valve`, Valve `props.reverseFlow`, Vessel `props.value.value`, Pump `props.variant`, and pipe `visible`/`fill`/`stroke`.
For Flex Repeater pages, prefer exact seeds for `ia.display.flex-repeater`; after apply, use `viewRead` to confirm `props.path`, the `props.instances` property binding, and child `params.*` inputs. Use `pageValidate` with the child view in `dependencyViewPaths`, then browser-open the page and verify each repeated card receives distinct top-level instance params with no child default text.
For View Canvas pages, prefer exact seeds for `ia.display.viewcanvas`; after apply, use `viewRead` to confirm `props.instances[].viewPath` and `viewParams` point at packaged child views and child input params, use `pageValidate` with all dependency views, and browser-click at least one instance to prove `onInstanceClicked` selection updates parent/detail state.
For View Canvas command popups, require the package to include dependency child views, popup views, and command scripts; after apply, prove one blocked interlock and one accepted writeback in-browser, then verify the final command/readback tags with `tagRead`.
For UDT-parameter-backed symbol pages, read and write copied instance parameter paths such as `[<tagProvider>]<folder>/<Instance>/Parameters.SymbolVariant`; verify the copied parameter path and dependent member/expression paths with `tagRead`. Normalize `"0"`/`"1"` and numeric strings before using those parameter values as symbol Boolean/numeric props.
For chart components such as Time Series Chart, prefer exact `componentSeedRead` shapes or minimal seed-style `props.series[].data`. For custom Time Series plots, verify `props.plots[].trends[].columns` is an object array with `key` values matching series data fields. Treat browser console property errors after a passing `pageValidate` as real component-schema failures; visual proof should confirm rendered SVG/canvas marks. Ignore only unrelated static asset noise such as Ignition favicon 404s.

Discover Named Queries before authoring database-backed pages:

```json
{
  "action": "namedQueriesList",
  "targetProject": "<projectName>",
  "namedQueryPrefix": "<optionalQueryFolderPrefix>",
  "maxResults": 200
}
```

Read one candidate:

```json
{
  "action": "namedQueryRead",
  "targetProject": "<projectName>",
  "queryPath": "<namedQueryPath>",
  "namedQueryPrefix": "<allowedQueryPrefix>",
  "includeSql": true
}
```

Preview only allowlisted read-only bounded queries:

```json
{
  "action": "namedQueryPreview",
  "targetProject": "<projectName>",
  "queryPath": "<namedQueryPath>",
  "namedQueryPrefix": "<allowedQueryPrefix>",
  "parameters": {"<paramName>": "<value>"},
  "maxRows": 25
}
```

Use returned `columns` and `rows` as a capped sample for Perspective table/KPI design. Do not execute update/action queries through preview. Do not pass QueryString/Database parameters unless a separate user-approved workflow validates them. For runner `0.3.54+`, QueryString previews require `allowQueryStringParameters: true` plus `queryStringParameterAllowlist`; Database previews require `allowDatabaseParameters: true` plus `databaseParameterAllowlist`. Exact rejected/bad values should fail before execution, and Java-backed execution failures should return a JSON error envelope instead of HTTP 500. If preview rejects an unbounded or over-broad query, add a small numeric top-level DB-side `LIMIT`/`TOP`/`FETCH` within the preview cap or enable a safe max return size before using it as a dashboard source.
For Perspective query bindings, keep each component property value wrapped as `{"binding": {...}}` under `propConfig`; include query params under `binding.config.parameters`; validate missing params with `namedQueryPreview`; then prove the live page in-browser because `pageValidate` does not execute bindings.

Read one allowlisted view:

```json
{
  "action": "viewRead",
  "targetProject": "<projectName>",
  "viewPath": "<allowedViewPath>",
  "allowedViewPrefix": "<allowedViewPrefix>",
  "includeViewJson": true,
  "includeResourceJson": false
}
```

Use the returned `viewSha256` before overwriting an existing view. For overwrite dry-run/apply, set `allowOverwrite: true`, set `requireViewSha256ForOverwrite: true`, and pass the current hash in `expectedViewSha256ByViewPath`. A missing, wrong, or stale hash is a stop condition and should fail during dry-run before writing. After a successful apply, immediately `viewRead` again; future overwrites must use the new hash, not the pre-apply hash. Do not request views outside the approved prefix.

## Page Validation

Use `pageValidate` after apply as a structural gate, not as render proof:

```json
{
  "action": "pageValidate",
  "targetProject": "<projectName>",
  "pagePath": "<pagePath>",
  "expectedViewPath": "<viewPath>",
  "allowedViewPrefix": "<allowedViewPrefix>",
  "allowedRoutePrefix": "<allowedRoutePrefix>",
  "dependencyViewPaths": ["<embeddedOrReusableViewPath>"],
  "dependencyScriptPaths": ["<projectLibraryScriptPath>"],
  "allowedScriptPrefix": "<scriptPathPrefix>",
  "expectedViewSha256ByViewPath": {
    "<viewPath>": "<expectedLiveViewSha256>"
  },
  "expectedScriptSha256ByScriptPath": {
    "<projectLibraryScriptPath>": "<expectedLiveCodeSha256>"
  }
}
```

Treat `routeViewMismatch`, `routeMissing`, `viewMissing`, `scriptMissing`, `viewHashMismatch`, and `scriptHashMismatch` as stop conditions until the package or expected inputs are corrected. Route objects must use a non-empty string `viewPath`, never `view`; missing/null/empty `viewPath` or a non-existent target view is a stop condition. A passing `pageValidate` means the route/resource wiring exists; it does not prove startup scripts, bindings, components, session connectivity, interactions, or Designer startup.

## Recent Logs

Capture time before the change, then query only the relevant apply/render window:

```json
{
  "action": "logQuery",
  "sinceEpochMillis": 0,
  "levels": ["ERROR", "WARN"],
  "loggerContains": "<stableLoggerSuffixOrName>",
  "messageContains": "<pageOrRunMarker>",
  "maxResults": 25,
  "tailBytes": 524288
}
```

Require `sinceEpochMillis` or `sinceMinutes`, at least one narrow text/logger filter, and capped results. Check `matchedCountBeforeCap`, `truncated`, and `tailWindowTruncated`; narrow noisy queries before reading entries. Gateway wrapper logs may abbreviate logger names, so prefer a stable logger suffix when filtering. On runner `0.3.61+`, use `includeRotated: true` with `maxLogFiles` only when failures may have rolled out of the current wrapper log; preserve `sourceFiles` and each entry's `sourceFileName`, and reduce `tailBytes`/`maxLogFiles` if the total-tail-byte cap rejects the scan. Logs diagnose failures; browser/render validation proves the page.

## Tag Discovery

Tag discovery is read-only.

List providers:

```json
{"action":"tagProviders","maxResults":100}
```

Browse tags:

```json
{
  "action": "tagBrowse",
  "path": "[<tagProvider>]<folderPath>",
  "recursive": true,
  "maxResults": 1000,
  "includeValues": false
}
```

For scalable Perspective pages, use `tagBrowse` to validate the root folder/provider and discover UDT instances, then inspect `truncated` and `totalAvailable`; do not treat a capped result as complete until the response proves all needed rows were returned. Author the page so a parent view/script builds a row or repeater model from that root. Do not copy-paste one hard-coded full tag path per asset when a folder root plus `view.params`/`view.custom` model can drive the page.

Read explicit tag values:

```json
{"action":"tagRead","paths":["[<tagProvider>]<tagPath>"],"maxResults":100}
```

Use fully qualified `[provider]path` values. Treat the returned `value` as usable only when `quality` is good; preserve `timestamp` in diagnostics when freshness matters.

Probe historian-backed data:

```json
{"action":"historyProbe","paths":["[<tagProvider>]<tagPath>"],"rangeMinutes":60,"returnSize":5}
```

Do not treat a good current value as proof of tag history. For trend/history components on runner `0.3.137+`, require `queryOk: true`, `sampleCountQueryOk: true`, `goodSampleHistoryAvailable: true`, and a positive `goodStoredSampleCount` or per-tag `tagStats[].goodStoredSampleCount`; if false, use a current-value display or state the good-quality historian dependency. Treat `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` as aliases, and treat `valueQueryHistoryAvailable`, `nonNullCount`, `hasData`, and `lastValue` as diagnostics, not good-sample proof.
Keep Alarm Status Table and Alarm Journal Table validation separate: `alarmStatusQuery` verifies current alarm state for `ia.display.alarmstatustable`, while `ia.display.alarmjournaltable` depends on a configured Alarm Journal/profile and uses singular `props.filter` plus a date range. For journal tables on runner `0.3.60+`, use `alarmJournalQuery` with the component's discovered `props.name` as explicit `journalName`; runner `0.3.97+` rejects default/omitted journal profile requests because it cannot verify Ignition's exactly-one-journal omission condition. Do not guess profile names such as `Journal`. On runner `0.3.96+`, both `alarmStatusQuery` and `alarmJournalQuery` must include a narrow source/path/displayPath filter before execution. On route-param detail pages, bind Alarm Status Table `props.filters.active.conditions.displayPath` and Alarm Journal Table `props.filter.conditions.displayPath` from `view.params.<assetId>` or a derived display-path pattern, then verify the same concrete filter with `alarmStatusQuery` and `alarmJournalQuery`.

Query current alarms only with explicit filters:

```json
{
  "action": "alarmStatusQuery",
  "displayPath": "<displayPathPattern>",
  "states": ["ActiveUnacked", "ActiveAcked"],
  "priorities": ["Critical", "High", "Medium", "Low"],
  "maxResults": 25
}
```

Require at least one narrow `source`, `path`, or `displayPath` filter on runner `0.3.96+`; provider-only filters do not bound backend work. Use this to verify Alarm Status Table pages; do not use broad Gateway-wide alarm scans.

Create complete UDT fixtures with `udtScaffold` when available:

```json
{
  "action": "udtScaffold",
  "provider": "<tagProvider>",
  "typePath": "<relativeTypeFolder>/<TypeName>",
  "instanceFolder": "<normalTagFolder>",
  "allowedTypePathPrefix": "[<tagProvider>]_types_/<relativeTypeFolder>",
  "allowedInstancePathPrefix": "[<tagProvider>]<normalTagFolder>",
  "requiredOverrideMembers": ["PV", "Status"],
  "members": [
    {"name": "PV", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float4", "value": 0.0},
    {"name": "Status", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "String", "value": "Unknown"}
  ],
  "instances": [
    {"name": "Asset001", "memberOverrides": {"PV": 12.3, "Status": "Ready"}}
  ],
  "dryRun": true
}
```

For writes, set `dryRun` false and add `{ "confirmUdtScaffold": "SCAFFOLD_UDT" }`. Keep `typePath` and `typeId` relative to `[provider]_types_`; keep `instanceFolder` under normal `[provider]` tags. On runner `0.3.112+`, a nested step with `ok: false` or `allGood: false` returns top-level `ok: false` with `failedStep`, `failedStepResult`, and `stepResults`; on older runners, inspect `stepResults[]`, nested `allGood`, and nested `qualityCodes` yourself before trusting a completed response. On runner `0.3.143+`, failed confirmed scaffold steps with missing, null, or empty `qualityCodes` mark all step recovery paths from preflight and attempt conservative recovery; preserve `writesStarted`, `completedSteps`, `preflightExistingPaths`, `preflightNewPaths`, `recoveryAttempted`, `recoveryAllGood`, `recoveryRequired`, and nested `recovery` details such as `deletePaths` and `restorePaths`. After apply, read the returned `memberReadPaths` with `tagRead` and bind Perspective to instance/member paths, not UDT definition paths.
If a scaffold includes many members, instances, or per-instance overrides, estimate `plannedTagCount = 1 + member count + instance count + override tag count` and set `maxItems` high enough on both dry-run and apply while keeping the same allowed prefixes. A dry-run rejection for `planned tag count exceeds maxItems` is a guardrail, not a Gateway failure.

Create scaffold tags/UDTs through `tagConfigure` only under approved prefixes:

```json
{
  "action": "tagConfigure",
  "basePath": "[<tagProvider>]<approvedFolder>",
  "allowedTagPathPrefixes": ["[<tagProvider>]<approvedFolder>"],
  "collisionPolicy": "a",
  "dryRun": true,
  "tags": [
    {"name": "DemoValue", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float4", "value": 1.23}
  ]
}
```

For writes, set `dryRun` false and add `{ "confirmTagConfigure": "CONFIGURE_TAGS" }`. On runner `0.3.111+`, bad returned QualityCodes or returned-code count mismatches should come back as top-level `ok: false` with `TAG_CONFIGURE_BAD_QUALITY` or `TAG_CONFIGURE_QUALITY_CODE_COUNT_MISMATCH`; still inspect `allGood`, `qualityCodes`, and readback. On older runners, treat `ok: true` plus `allGood: false` or any `qualityCodes[].good: false` as a failed write. Put UDT definitions under `[<tagProvider>]_types_/...`; create UDT instances under normal tag paths and bind Perspective to instances, not definitions. Reference tags require `valueSource: "reference"` and a non-empty `sourceTagPath`; do not use Reference-tag `sourceTagPath` parameters as proof of dynamic UDT path behavior without member readback.

For UDT scaffolds:

- Create `UdtType` definitions under `[<tagProvider>]_types_/...`.
- Create `UdtInstance` tags under normal `[<tagProvider>]...` folders with `typeId` relative to `_types_`.
- To initialize different member values per UDT instance, create the instance first, then call `tagConfigure` with `basePath` set to the instance path, `collisionPolicy: "m"`, and `tags` containing member names/values.
- Use `tagConfigure` directly rather than `udtScaffold` when a test must prove explicit UDT instance `parameters` overrides; `udtScaffold` is for complete fixture scaffolds, not fine-grained copied-parameter write tests.
- For alarm component fixtures, `AtomicTag` configs may include `alarms` arrays; use numeric setpoints and verify runtime paths such as `[<tagProvider>]<tagPath>/Alarms/<alarmName>.IsActive` with `tagRead`. For per-instance UDT alarm overrides, merge alarm config before changing the value that activates the alarm so current alarm status captures the final display path.
- Verify instance member paths with `tagRead` before binding Perspective components.
- Use scaffold tags/UDTs for demos and tests; keep real process writeback in Project Library scripts.
- Prefer this existing scaffold path over adding broader tag-write surfaces unless a page-building test proves a specific gap.

Do not add tag imports, provider creation, database edits, or Gateway configuration changes to the low-touch runner.

## Safety Rules

- Treat the runner as staging/development tooling unless production approval is explicit.
- Use HTTPS, loopback-only access, Web Dev auth/roles, a caller-managed token, or equivalent protection.
- Allowlist project names, view prefixes, route prefixes, resource file types, and package sources.
- Reject arbitrary filesystem paths and unrestricted zip contents.
- Keep secrets in runtime input, environment variables, or the instance profile; never print them.
- Require explicit confirmation strings for every write action.
- Apply the non-deletion rule during cleanup, rollback planning, backups, and temp-file handling.
- Keep backups of every modified project resource and its `resource.json` metadata before writes.
- For existing view overwrites, prefer `viewRead` then `expectedViewSha256ByViewPath`; treat drift as a stop condition.
- If Ignition returns HTTP 402, check trial/module state before debugging the runner.

## Validation

After apply:

- Confirm the target project is the project the user expects.
- Confirm the project scan/import completed; on runner `0.3.88+`, require `scanCompleted: true` after writeful mutations and stop on `recoveryRequired: true`.
- Open `<gatewayUrl>/data/perspective/client/<projectName>/<pagePath>`.
- Verify rendered page markers/components, not only HTTP 200.
- Verify tag bindings resolve or degrade clearly.
- Verify Gateway/Perspective/browser logs have no relevant errors.
- Treat client-side component errors in browser console logs as failures even when `pageValidate`, `viewRead`, and focused Gateway `logQuery` pass.
- For page-config/project-resource writes, smoke-test Designer startup when feasible; browser runtime can work while malformed page config breaks Designer.
- Treat Perspective project-resource fetch failures as validation failures even when route wiring is structurally valid; malformed script-action fields such as missing/null `scope` can break project serialization after apply.
- Scan Designer/Gateway launch logs for `EditablePageConfig`, `Error loading layout`, `NullPointerException`, and `ScriptIndexer -- Failed to parse`.
- If Designer launch testing leaves hidden Designer/Launcher Java processes, stop only child processes matching `BootstrapSwing`, `DesignerStartupHook`, or `DesignerLauncher`; do not kill the Gateway service process.
- If Designer is open, refresh/reopen the project and confirm `Perspective > Views > <viewPath>` appears.
- Report changed view paths, route paths, backup location, and rollback note.

## Ignition 8.1 Docs

Use Ignition 8.1 docs unless the user requests another version:

- Perspective module: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective
- Perspective View Canvas: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-view-canvas
- Perspective Embedded View: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-embedded-view
- Perspective Popup Views: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/views-in-perspective/popup-views
- Perspective Component Message Handlers: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/component-message-handlers
- `system.perspective.openDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-openDock
- `system.perspective.closeDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-closeDock
- `system.perspective.toggleDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-toggleDock
- `system.perspective.openPopup`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-openPopup
- `system.perspective.closePopup`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-closePopup
- `system.perspective.sendMessage`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-sendMessage
- `resource.json`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/resource-json-file
- `system.project.requestScan`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-project/system-project-requestScan
- `system.tag`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag
- `system.tag.configure`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-configure
- Web Dev module: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/web-dev
- Named Queries: https://www.docs.inductiveautomation.com/docs/8.1/platform/sql-in-ignition/named-queries
- `system.db.runNamedQuery`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-db/system-db-runNamedQuery
