# Apply And Rollback

Use this reference for package transfer, dependency declaration, dry-run, apply, overwrite protection, backup inspection, and rollback.

## Contents

- Package payload
- Dependencies and routes
- Dry-run acceptance
- Apply acceptance
- Readback
- Backup and rollback
- Failure handling

## Package Payload

Prefer base64 package transfer unless the approved runner profile and user explicitly select a fixed host inbox.

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
  "allowedRoutePrefix": "<allowedRoutePrefix>",
  "dependencyViewPaths": ["<childOrReusableViewPath>"],
  "dependencyScriptPaths": ["<projectLibraryScriptPath>"],
  "allowedScriptPrefix": "<scriptPathPrefix>",
  "dependencyNamedQueryPaths": ["<namedQueryPath>"],
  "allowedNamedQueryPrefix": "<namedQueryPrefix>",
  "sharedDockKeys": ["top", "left"],
  "routes": [
    {
      "pagePath": "<pagePath>",
      "viewPath": "<viewPath>",
      "title": "<pageTitle>"
    }
  ],
  "scanTimeoutSeconds": 10
}
```

For apply, change `action` to `apply` and add:

```json
{"confirmApply":"APPLY"}
```

Send explicit `routes` for small generated packages. Do not depend on package route discovery unless `page-config/config.json` contains only intended routes.

## Dependencies And Routes

List every packaged child, popup, reusable, dynamic Embedded View candidate, and View Canvas child in `dependencyViewPaths`. The runner cannot infer every runtime `props.path` value.

List every packaged Project Library resource in `dependencyScriptPaths` and keep it under `allowedScriptPrefix`. List every packaged Named Query in `dependencyNamedQueryPaths` and keep it under `allowedNamedQueryPrefix`.

Do not list target-existing resources as package dependencies unless the package actually contains them. Discover and read them first, then document them as target prerequisites.

Use `sharedDockKeys` only for top-level `sharedDocks` keys: `top`, `bottom`, `left`, `right`, and `cornerPriority`. Treat returned dock view paths as dependencies. Do not use this field for route-specific page docks.

Use exact-or-child prefix semantics. A prefix such as `LLM Tests/A` permits that path and its children, not a sibling such as `LLM Tests/ABC`.

Package QueryString or Database Named Query parameters only with the runner's explicit unsafe-parameter allowlists and confirmation. Otherwise stop. Runtime Database-parameter behavior remains target-specific and requires execution proof.

## Dry-Run Acceptance

Require:

- `ok: true` and the same `requestId`
- expected target project
- expected validated primary and dependency views
- expected routes and shared dock views
- expected validated scripts and Named Queries
- overwrite hash checks for every existing managed view
- no unexpected files, resources, routes, or target roots
- no prefix violation, unsafe parameter, manifest error, or recovery requirement
- cleaned temporary work directory when the cleanup feature is advertised

Require `routeConflictCount: 0` unless overwrite is intentional. For a conflict, inspect the package and target route, `willOverwrite`, and resolution choices. A non-overwrite dry-run must fail without writing; an intentional overwrite must show the exact replacement before apply.

## Apply Acceptance

Require:

- `ok: true` and the same `requestId`
- expected copied primary/dependency views
- expected copied scripts and Named Queries
- expected merged routes and shared dock keys
- runner-created backup evidence
- `scanCompleted: true` for project mutations
- cleaned work directory when advertised
- no `validationStage` failure
- `recoveryRequired` absent or false

When an overwrite intentionally removes a previously managed optional view file such as `thumbnail.png`, require the stale-file pruning report and verify the final `resource.json.files` state through readback.

When scripts, Named Queries, or page config are included, preserve the complete response and stop if final-state validation reports a mid-write failure.

## Readback

After apply:

1. Read every intentionally changed view and record its new hash.
2. Validate the route and all declared view/script/Named Query dependencies with `pageValidate` when available.
3. Confirm shared dock structure through bounded page-config/resource readback.
4. Query a narrow recent log window for apply/reload errors.
5. Open the concrete Perspective route and prove runtime rendering and interactions in the browser.

Structural validation does not execute bindings or prove component behavior. Browser proof does not replace resource readback or hash validation.

## Backup And Rollback

List runner-created backups:

```json
{"action":"backupList","targetProject":"<projectName>","maxResults":50}
```

Use only a returned backup name. Dry-run rollback first:

```json
{"action":"rollback","targetProject":"<projectName>","backupName":"<backupName>","dryRun":true}
```

For rollback apply, set `dryRun` false and add:

```json
{"confirmRollback":"ROLLBACK"}
```

Before applying rollback, require the expected restore/remove counts, backup format, backed-up files, drift checks, and recovery posture. After rollback, require scan evidence for project resources and repeat route/view/resource/browser validation.

Gateway-level Perspective theme, font, and icon-library backups use `targetProject: "_gateway"`, skip project scans, and require matching asset list/read verification plus any required refresh.

If rollback reports write failure, unfinished backup state, unknown after-state, missing backup files, or drift, stop and preserve the full response including completed work, failed stage/path, pre-rollback backup, nested failure, and recovery instructions.

## Failure Handling

- Hash drift: rediscover and decide whether to stop or intentionally replace; never reuse the stale hash.
- Mutation lock: wait for the active mutation, rediscover, and repeat dry-run.
- Scan failure: stop; do not describe the write as successful.
- Partial or unknown mutation: preserve evidence and follow reported recovery before any new write.
- Package manifest failure: correct the authored package; do not bypass with direct file writes.
- Browser/runtime failure after structural success: treat it as a real failure and diagnose component JSON, bindings, scripts, project serialization, and logs.

