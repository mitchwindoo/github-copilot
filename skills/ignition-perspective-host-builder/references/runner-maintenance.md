# Runner Maintenance

Use this reference only when the user explicitly asks to inspect or update the approved Web Dev runner resource. Normal Perspective page-building, validation, and troubleshooting work should not use `runnerSelfUpdate`.

## Self-Update Contract

Only use `runnerSelfUpdate` for the approved Web Dev runner resource. Send the method body as UTF-8 base64, not as raw multiline JSON text. Runner `0.3.103+` self-update backups include both Web Dev `doPost.py` and sibling `resource.json` in the `fileChanges-v1` rollback plan. Runner `0.3.104+` stores exact pre-update `doPost.py` source and reports `backupExactSource: true` plus `backupTokenRedacted: false`.

Start with a dry-run request:

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

After self-update, call `health` until the new runner version/features are visible.
For runner `0.3.103+`, require `runnerSelfUpdateResourceJsonRollback` in `health.features` before relying on self-update rollback to restore the sibling Web Dev `resource.json`.
For runner `0.3.104+`, require `runnerSelfUpdateExactBackup` in `health.features` before relying on exact `doPost.py` source restore; protect backup folders like runner source if static token assignments are present.
For runner `0.3.141+`, require `rollbackWriteFailureEnvelope` before relying on structured rollback write-failure recovery context. If rollback returns `ROLLBACK_WRITE_FAILED`, stop and preserve `backupName`, `backupFormat`, `preRollbackBackupDir`, `failedStage`, completed work lists, nested `rollbackFailure`, and `recoveryRequired` before attempting any follow-up recovery.
For runner `0.3.142+`, require `applyPackageStaleViewFilePruning` before relying on package `apply` to prune stale optional Perspective view-managed files such as `thumbnail.png`; inspect `prunedStaleViewFiles` / `prunedStaleViewFileCount` and read back the resource after intentional overwrites.
For runner `0.3.144+`, require `unfinishedFileChangeBackupRollbackRecovery` before relying on normal rollback for an unfinished `fileChanges-v1` backup. Preserve `afterStateKnown`, `backupManifestComplete`, `rollbackDriftCheckMode`, and `driftCheckSkipped`; completed backups still enforce `ROLLBACK_DRIFT_DETECTED`, and legacy manifests missing `afterStateKnown` default to strict drift checks.

## Safety Rules

- Do not use `runnerSelfUpdate` to update arbitrary Web Dev resources.
- Require the current runner version and expected current hash when available.
- Preserve dry-run output before any write.
- Treat missing health readback after the write as an incomplete update, not success.
