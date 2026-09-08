# Bounded Gateway Validation

Use this workflow for runtime-sensitive expression claims. Keep raw evidence, tokens, private hosts, project names, provider names, and logs outside the reusable skill package.

## Safety Boundary

Start read-only. Mutation requires:

- Exact target and version.
- An explicit test-only namespace.
- Backup or export.
- Authentication.
- Dry-run.
- Bounded allowlists and request sizes.
- Idempotency.
- Readback.
- Exact cleanup.
- Diagnostic review.

Do not use arbitrary script execution, unrestricted tag paths, or broad cleanup.

## Discover the Target

Capture:

- Ignition version and build.
- Operating system, Java, and Jython versions when relevant.
- Gateway timezone and locale.
- Active modules and versions.
- Active deployment mode and resource collection.
- Tag providers and chosen test provider.
- Project used by any Web Dev adapter.
- Live `/openapi.json` and its SHA-256.
- Current test-adapter capability response and its SHA-256.

The target-local OpenAPI is authoritative for available documented routes. A route shown in public documentation, another Gateway, or an older skill is only a discovery lead.

## Preflight

1. Verify Gateway health and module health.
2. Capture a baseline WARN-or-higher log window.
3. Take a Gateway backup or the smallest sufficient project/config export.
4. Verify the intended test root does not exist.
5. Record the cleanup plan before creating anything.
6. Reject a run if the target is production or the chosen scope is ambiguous.

Use a unique run identifier such as:

```text
expr83_<UTC timestamp>_<random lowercase hex>
```

Keep all tag fixtures below one explicit parent such as:

```text
[<provider>]_expression_skill_tests/<runId>
```

Delete only the exact `<runId>` root created by the run. Preserve the shared parent.

## Preferred Test Path

Use the highest-preference method that can prove the claim:

1. Official OpenAPI read-only route.
2. Official OpenAPI bounded mutation route.
3. Supported Gateway-scope scripting or `system.config`.
4. Existing bounded local adapter.
5. A new fixed-fixture adapter only when a material test is otherwise blocked.
6. Manual Designer/runtime work only when the host surface cannot be exercised safely through supported APIs.

Never add a general Jython-evaluation POST endpoint.

## Optional Local Expression Adapter

Some customer Gateways may advertise these non-official, bounded actions through an existing Web Dev test adapter:

- `expression-tag-batch-v1`
- `expression-tag-fixture-suite-v1`
- `expression-tag-cleanup-v1`
- `event-stream-expression-fixture-v1`
- `perspective-named-query-expression-fixture-v1`

Use them only if the live capability response advertises them and its contract matches the request.

### `expression-tag-batch-v1`

Purpose: create and read a batch of caller-supplied, side-effect-free Expression Tags.

Required safety properties:

- Verified API token.
- Provider and parent root fixed by the server.
- Run ID format and exact run root enforced.
- Case count, expression length, output type, and settle time bounded.
- Caller expressions reject bound references, `tag()`, `runScript()`, alarm-state functions, and arbitrary Jython.
- Dry-run is the default.
- Apply is explicit.
- Idempotency key plus request hash.
- Configuration, value, type, full quality, and timestamp readback.

Illustrative request:

```json
{
  "action": "expression-tag-batch-v1",
  "runId": "expr83_<UTC timestamp>_<hex>",
  "idempotencyKey": "<unique printable key>",
  "dryRun": true,
  "apply": false,
  "settleMillis": 1000,
  "cases": [
    {
      "id": "CORE-001",
      "expression": "5 + 3 * 2",
      "dataType": "Int4"
    }
  ]
}
```

Dry-run first. Change to `"dryRun": false, "apply": true` only after inspecting the plan.

For a legacy-to-modern numeric-quality comparison, put the legacy and modern
forms in the same batch with the same literal value and declared type. Require
both values to match, then compare Good state, quality level/name, full code,
diagnostic, and timestamp. On the verified 8.3.8 Expression Tag target,
`forceQuality(123, 0)` produced Bad with full code `-2147483136`, while
`qualifiedValue(123, 0)` produced Good/`192`. Treat this as proof only for
numeric `0` on that host; it is not a mapping table for other legacy codes.

### `expression-tag-fixture-suite-v1`

Purpose: run a server-side allowlisted fixture suite. Profiles may cover sibling references, dynamic paths constrained to the exact run root, null/quality behavior, or fixed `runScript()` return and exception controls.

The caller does not supply expression text. A current adapter may advertise:

```text
references-quality-v1
runscript-exceptions-v1
runscript-missing-gsp-v1
runscript-scalar-returns-v1
runscript-structured-returns-v1
```

`references-quality-v1` covers fixed sibling, dynamic-path, null, and quality cases. `runscript-exceptions-v1` covers only server-owned return, null, and deterministic exception expressions. `runscript-missing-gsp-v1` covers one fixed project-library call and matching `try()` fallback while the Gateway Scripting Project is proven absent. `runscript-scalar-returns-v1` covers five fixed integer, long, float, Unicode-string, and boolean controls. `runscript-structured-returns-v1` covers fixed DateTime, DataSet, list-to-Document, dict-to-Document, and explicit-Document controls. The tested adapter serializes Dates as epoch milliseconds and DataSets as a bounded column-name, column-type, and row structure; inspect `valueKind`, `valueType`, `valueTruncated`, and quality as well as value. These profiles do not accept caller-supplied scripts or project-library paths.

Illustrative request:

```json
{
  "action": "expression-tag-fixture-suite-v1",
  "runId": "expr83_<UTC timestamp>_<hex>",
  "idempotencyKey": "<unique printable key>",
  "fixtureProfile": "references-quality-v1",
  "caseIds": ["REF-001", "NULL-002", "QLT-008"],
  "dryRun": true,
  "apply": false,
  "settleMillis": 1500
}
```

Omit `caseIds` only when the live contract says omission selects the complete fixed profile.

### `expression-tag-cleanup-v1`

Purpose: delete and verify absence of the exact run root.

Illustrative apply request:

```json
{
  "action": "expression-tag-cleanup-v1",
  "runId": "expr83_<UTC timestamp>_<hex>",
  "idempotencyKey": "<same key used to create the run>",
  "dryRun": false,
  "apply": true,
  "confirm": "DELETE_EXPRESSION_RUN"
}
```

Use the same idempotency key. Reject cleanup if metadata does not match. Treat an already-absent exact run root as an idempotent cleanup result.

If these actions are absent, do not assume their payloads work. Re-discover the current adapter or use another bounded supported method.

### `event-stream-expression-fixture-v1`

Purpose: manage a server-owned Tag Event expression fixture when official APIs expose Event Stream status but not Event Stream authoring or the required disposable Memory Tags.

Use it only when the live capability response advertises the action and confirms all of these boundaries:

- Fixed project, stream, provider, run root, tag names, source values, target paths, and expressions.
- No caller-supplied path, expression, project, or Jython.
- Only `setup`, `trigger`, `inspect`, and `cleanup` operations.
- Verified API token for mutations.
- Dry-run by default and explicit apply.
- Exact ownership metadata and cleanup confirmation.
- Full value, runtime type, quality, timestamp, Event Stream list, and stage-diagnostic readback.

Do not copy project names, run IDs, paths, source values, or confirmation text from another Gateway. Read them from the live capability contract. A typical safe sequence is:

1. Reject an unknown field, traversal-like run ID, and caller path with `writesAttempted: false`.
2. Dry-run and apply `setup`; replay it idempotently.
3. Create/import only the fixed disposable Event Stream project through the target-local official project API.
4. Wait for the stream to report running with source/handler stages free of errors.
5. Dry-run and apply the fixed triggers; verify selected and unselected targets, path echo, full quality, and canary state.
6. Export/read back the disposable project resource.
7. Delete the exact project.
8. Poll project names, official Event Stream status/details, and `system.eventstream.listEventStreams()` until all report the stream absent.
9. Dry-run and apply exact tag-root cleanup; replay cleanup and verify the shared parent has no children.
10. Review action and teardown WARN-or-higher log windows.

The runtime lifecycle can lag project deletion. Refuse tag cleanup while the fixed stream still appears active. If teardown does not verify complete, keep the bounded recovery capability available instead of removing it prematurely.

### `perspective-named-query-expression-fixture-v1`

Purpose: exercise a server-owned Perspective Query Binding whose Named Query
path is selected by an expression when official APIs expose session
inspection, project import/export, and Named Query execution but not the
complete authoring/mount lifecycle.

Use it only when the live capability response advertises the action and
confirms:

- Fixed project, database, route, view, Named Queries, tag root, expressions,
  selector values, and cleanup confirmation.
- No caller-supplied SQL, expression, Jython, resource path, project, session,
  page, route, or mount path.
- Only bounded setup, mount/navigation, selector, optional fixed rapid-cycle,
  fixed parameter-phase, fixed polling, or fixed invalid-syntax observation,
  inspection, unmount, and cleanup operations.
- Verified API token for mutations, dry-run by default, explicit apply,
  idempotency, exact resource hashes, and exact cleanup ownership.
- Official Perspective session/page/view readback plus result value, runtime
  type, full quality, resolved query path, sequence, and timestamps.

A safe sequence is:

1. Capture project export, page configuration hash, Perspective
   sessions/pages/views, and WARN-or-higher baseline.
2. Reject caller SQL, paths, and session identifiers before writes.
3. Dry-run and apply setup; replay setup idempotently.
4. Mount only the fixed disposable view and confirm it through the official
   Perspective view endpoint.
5. Exercise each fixed selector and require a fresh sequence/timestamp rather
   than accepting a stale value.
6. If a fixed Direct-mode capability is present, reject caller-supplied
   paths, parameter names or values, expressions, projects, sessions, timing,
   and Jython. Require readback of exact Direct mode, fixed query path,
   configured parameter map, disabled polling/cache, scalar result, full
   quality, sequence/timestamp, and session/page identity. Record Designer
   editor acceptance and automatic parameter discovery as untested unless
   separate direct evidence proves them.
7. If a fixed constant-expression capability is present, reject
   caller-supplied paths, parameter names or values, expressions, projects,
   sessions, timing, and Jython. Require readback of the exact quoted path
   expression and manual parameter map, then require the fixed resolved path,
   scalar result, full quality, sequence/timestamp, and session/page identity.
   Treat API-authored runtime acceptance as distinct from Designer editor
   acceptance.
8. If a fixed property-driven capability is present, reject caller-supplied
   property names or values, paths, parameter names or values, expressions,
   projects, sessions, timing, and Jython. Read back the exact property
   binding and Query Binding path expression. Record the runtime property
   value from the view, not merely its backing source, then require each fixed
   property/path/result transition, full quality, strict freshness, and one
   unchanged session/page identity.
9. If a fixed rapid-cycle capability is present, reject caller-supplied paths,
   parameters, sequences, and delays. Dry-run the server-owned sequence, then
   require every write quality, final selector, resolved path, value, full
   quality, and freshness oracle before a normal-selector recovery.
10. If a fixed parameter-expression capability is present, reject
   caller-supplied parameter values/names, paths, expressions, projects,
   sessions, timing, and Jython. Dry-run the immutable phase plan, then require
   a fixed baseline -> changed -> recovered-baseline sequence. Record the
   parameter source value/quality/timestamp, resolved path, result, full
   quality, sequence, binding/observation timestamps, and session/page identity
   together. Require every source, binding, and observation timestamp to
   advance and require the same session/page throughout.
11. If a fixed polling capability is present, reject caller-supplied paths,
   rates, windows, parameters, projects, and sessions. Dry-run the immutable
   plan, hold the selector/path/inputs constant, and distinguish executions
   with query-generated data such as a database clock. Require unique results,
   full Good quality, binding and observation timestamps, session/page
   identity, measured intervals, and zero observer writes. On the verified
   8.3.8 runtime, numeric JSON rate `1` normalized to default expression `30`,
   while string `"1"` remained expression `1`; verify installed-runtime
   readback and live cadence when generating resource JSON.
12. If a fixed invalid-syntax capability is present, reject caller-supplied
    expressions, paths, parameter names/values, projects, sessions, timing,
    and Jython. Read back the exact fixed malformed text, mount only the owned
    disposable view, and require a fresh non-Good value/type/full-quality
    observation with sequence, timestamps, and session/page identity. Explicitly
    reject every known valid-query result as a silent fallback. Preserve the
    exact runtime diagnostic, and state that API-authored saved-resource
    behavior does not prove Designer editor prevention or flagging.
13. For incompatible parameters, record the selected path, value, quality code
    and diagnostic. Account for both Good null and non-Good outcomes unless the
    exact parameter type and target behavior were already proved.
14. Unmount, verify zero matching views, and apply exact cleanup.
15. Poll official project export until owned resources disappear and the page
    configuration returns to its exact prior bytes; a successful scan response
    can precede export-cache convergence.
16. Replay cleanup, verify the shared tag parent has no children, and review all
    action/teardown log windows.

Keep this adapter optional. A customer skill must remain useful when the local
fixture action is absent.

### `sfc-transition-expression-fixture-v1`

Use the official project and SFC web APIs for project create/import/readback,
project export/delete, chart status/totals/detail, and emergency cancel. If the
target has no official chart-start web route, a bounded Gateway-scope adapter
may call the documented
`system.sfc.startChart(projectName, chartPath, parameters)` signature.

A safe transition-path adapter should expose:

- Fixed disposable projects, seven callable charts, one primary provider/run
  root, one fixed disposable secondary standard provider/run root, one
  provider-root canary, seven fixed case IDs, and cleanup confirmation. If one
  project is a migration source, bind it to a separately validated, immutable
  archive rather than accepting a caller-supplied project or path.
- Server-owned providerless, `[~]`, and `[.]` transition expressions. For `[.]`,
  keep the chart-folder and provider-root candidates fixed and mutually
  exclusive so the observed base is unambiguous.
- One server-owned `tag({TargetPath})` expression, two provider-qualified
  Boolean targets, a fixed chart-scope start parameter selecting target A, and
  a fixed retarget from A to B on only the stored instance.
- One server-owned, provider-qualified `tag()` path that must remain absent.
  Serialize its direct value/type/quality/timestamp at every phase, forbid the
  Boolean gate-write operation for that case, and never create or delete the
  missing target.
- For a project-resource migration case, require exact source version and load
  provenance, an allowlisted archive, exact Transition XML/expression hash,
  immediate 8.3 export readback, false/true runtime proof on the same instance,
  and a second exact export after runtime. State explicitly that direct project
  import does not validate full Gateway-upgrade transformations.
- No caller-supplied project, chart path, instance ID, variable name/value, tag
  path, expression, or Jython; reject unknown case IDs and candidates before
  writes.
- Only fixed setup, case start, Boolean gate write, chart-scope retarget,
  inspect, and cleanup operations.
- Dry-run by default, verified API-token mutation, ownership metadata,
  per-case instance tracking, idempotent replay, serialized
  value/type/quality/timestamp readback, and cleanup refusal while any fixed
  chart is active.

A typical safe sequence is:

1. Confirm SFC totals/status are clean and capture baseline logs.
2. Dry-run and apply every fixed false gate; replay setup.
3. Create/import the disposable project through the official project API.
4. Read back the configured default provider and export all chart XML. Require
   byte-exact expressions; allow only understood metadata rewrites in
   `resource.json`.
5. Wait for the official SFC status route to report all seven definitions.
6. For providerless and `[~]`, start once, prove Good false plus a false rewrite
   preserves the exact `Running` instance, then write true and capture the first
   official terminal state.
7. For `[.]`, start with both candidates false, try the chart-folder candidate,
   reset it, then try the provider-root candidate. Keep candidates mutually
   exclusive and cancel the exact stored instance if neither resolves.
8. For the dynamic path, start with both targets false and chart-scope
   `TargetPath` selecting A. Make only non-target B true and prove the same
   instance remains `Running` with readback still A. Then change only the
   stored instance's `TargetPath` to B; require that exact instance to reach
   `Stopped` without another tag write.
9. For the missing target, require `exists=false` and a direct non-Good read,
   start once, and observe the exact instance for a bounded interval. Fail any
   `Stopped` result. Record `Running` or `Aborted` exactly; if still `Running`,
   cancel only the stored ID through the official API and require `Canceled`.
   Verify the target remained absent/non-Good before start, after start, after
   observation, and after terminal handling.
10. For disabled-provider recovery, use only a fixed disposable standard
    provider selected as the disposable project's default. Start at Good
    false, disable only that provider through supported Gateway configuration,
    require a non-Good gate and the same `Running` instance for a bounded
    interval, then re-enable it. Require Good false and the same instance
    before writing Good true and capturing `Stopped`. Never disable a
    pre-existing or production provider for this test.
11. Poll detail and totals until every completed or cancelled instance leaves
    the active set.
12. Run unrelated existing-action regressions and classify the exact action log
    window; do not suppress project or SFC warnings broadly.
13. Delete every disposable project, then poll project names, SFC status,
    totals, and every chart detail until all definitions and instances are
    absent. Do not require a global zero-definition total while another
    disposable project is intentionally still loaded.
14. Dry-run and apply exact cleanup for both owned run roots and the
    provider-root canary,
    replay it, verify both locations plus the unowned missing target are absent,
    delete the disposable provider only while it is re-enabled, and review
    teardown logs.

Keep this adapter optional. Manual or project-local validation can use the same
official project/SFC readbacks and documented scripting function.

### Vision retarget expression fixture

Use two fixed disposable projects, two fixed standard providers, and one fixed
internal test user. Each project should contain the same small Vision window
with a direct tag binding, a tag expression, and a property expression, while
the provider-qualified source path and fixed source value differ by project.
For classic login, include the project's all-scope `ignition/global-props`
resource with the intended authentication profile; project-local auto-login
settings do not replace that resource.

A bounded API-first sequence is:

1. Capture adapter health, fixed-resource inventory, launcher protocol/app
   state, and baseline WARN-or-higher logs.
2. Generate both project archives locally, parse every generated Jython source
   with the target Jython runtime, then create the providers, tags, user, and
   projects through bounded authenticated APIs.
3. Launch one test-owned client from a known Gateway entry and an
   evidence-local launcher home. Record the launcher process and identify the
   exact child Vision JVM; never stop unrelated Java processes.
4. In project A, serialize project/client/JVM identity, source path and
   qualified value, plus each binding's value, full quality, and timestamp.
5. Retarget to project B with fixed parameters. Require the same test-owned JVM
   and an active Gateway client record for B. Record any client-ID transition
   rather than prescribing equality across projects.
6. Capture B's initial telemetry, change only B's fixed source, then require
   fresh B telemetry. B's client ID should remain stable through that update,
   and all expected binding values and qualities must update coherently.
7. Stop the exact child JVM, uninstall only the test-owned launcher entry, and
   remove any test-owned protocol/app-home state. Apply exact cleanup for both
   projects, providers, tag roots, and user; replay cleanup and prove absence.
8. Roll back any temporary adapter extension, require its prior health/version,
   run unrelated regressions, review action and teardown log windows, and
   preserve protected-reference hashes.

For a default-provider retarget variant:

1. Give A and B different fixed local standard providers and store each
   provider in that project's all-scope global properties.
2. Use identical binding text in both projects: direct bindings with no
   provider and `[]`, `tag()` with no provider and `[]`, plus a property
   expression derived from those results. Retain explicit-provider bindings as
   controls.
3. Record `[System]Client/System/DefaultTagProvider` with value, full quality,
   and timestamp in every client snapshot. Require A's provider before retarget
   and B's provider before and after the target update.
4. Use distinct A/B source values, then change only B. Require every
   omitted/empty-provider binding to select A, switch to B, and publish the
   fresh B update with Good/192 quality.
5. Test `[~]` separately. Accept only a coherent Good result that follows the
   target project's provider or a coherent non-Good result with full quality.
   Fail mixed, stale, opposite-provider, or unexplained values. Do not assume
   `[~]` means project default on a component-expression host.

Keep project names, providers, user, operations, parameters, expressions,
source paths, and cleanup confirmation fixed or narrowly allowlisted. Do not
accept caller-supplied Jython or arbitrary project/tag/process targets. Keep
this adapter optional; a project-local test can use the same telemetry and
cleanup oracle.

### Vision Gateway-restart recovery variant

Use the fixed retarget fixture when validating restart recovery; do not add a
custom restart action when the target's official 8.3 OpenAPI exposes one.

1. Require explicit authorization for a disruptive restart. Read the exact
   Gateway name, host, port, build, redundancy role, module health, and
   current adapter version/action count before the call.
2. Launch one test-owned Vision client, retarget to the fixed project B, and
   persist a stable Good/192 pre-restart snapshot.
3. Keep the exact client JVM alive. Invoke only the official restart
   operation with its explicit confirmation parameter, then observe the
   outage and poll until the same Gateway identity, expected adapter, and
   healthy Vision module return with a new startup time.
4. Give the client observer a bounded deadline longer than the expected
   outage. Change only the fixed source after health returns; require a fresh
   Good/192 source, direct binding, `tag()` expression, property expression,
   and default-provider controls.
5. Require pre/post JVM equality. Do not require client-ID equality across
   restart: require the post-restart ID to match the Gateway's one active
   client record, and record whether re-registration rotated the ID.
6. Capture and classify restart WARN-or-higher entries by exact
   logger/message patterns. Fail any current-run identity or unclassified
   entry; do not delete unrelated pre-existing resources to make the log
   window clean.
7. Terminate only the owned client/JVM, replay exact fixture cleanup, remove
   fixed projects/providers, restore the prior adapter, and wait for a clean
   post-teardown/final audit.

This variant proves one independent-Gateway restart only. Test redundancy,
multiple clients, repeated restarts, longer outages, migration, and other
Vision expression shapes separately.

### Vision login/logout security-expression fixture

Use one fixed disposable Vision project, one protected existing tag provider,
two fixed internal users, and two fixed disjoint roles. Keep passwords
server-owned and out of capabilities, responses, logs, and saved telemetry.
Bind fixed Label properties to the current-user system tag and one
`hasRole()` expression per role.

A bounded API-first sequence is:

1. Require the project, users, roles, run subtree, client, and exact client JVM
   to be absent. Verify the protected provider is enabled.
2. Generate and Jython-parse the project archive locally. Use a client-aware
   expression function factory when parsing `hasRole()` for serialized Vision
   bindings.
3. Through a fixed authenticated setup operation, create ownership metadata,
   one telemetry tag, both roles, and both users. Give each user only its
   matching role; replay setup and verify exact readback.
4. Import the project, auto-login as alpha, launch one test-owned client, and
   identify the exact project JVM. Wrap process/client query results as arrays
   before applying count assertions in Windows PowerShell.
5. Capture a stable alpha snapshot. Require Good/192 username and role
   bindings to agree with `system.vision.getUsername()` and
   `system.vision.getRoles()`.
6. Switch alpha -> beta -> alpha. If an asynchronous harness initiates the
   switch, marshal it to Swing's event-dispatch thread. Reacquire the window
   and components after each switch because Vision closes and reopens them.
7. Persist raw telemetry before asserting it. Require both switches true,
   exact alpha/beta/alpha values, disjoint roles, one client ID, one JVM,
   changed window identities, ordered timestamps, and no stale identity.
8. Stop only the exact client/JVM, delete users before roles, delete the owned
   run subtree and project, replay cleanup, preserve the provider, roll back
   any temporary API extension, and require clean action/post logs plus the
   final Gateway audit.

Keep the project, provider, user source, users, roles, expressions, tag path,
operations, and cleanup confirmation fixed. Do not accept caller-supplied
credentials, Jython, expressions, users, roles, projects, providers, tag
paths, or process targets. Failed login, anonymous state, other
authentication strategies, live role edits, and multiple-client behavior
need separate cases.

### Cross-fixture Vision cleanup audit

After stopping the exact owned client and replaying each fixture's cleanup,
run a read-only cross-fixture audit rather than trusting deletion responses:

1. List official project names, Tag Provider resources, default user-source
   users and roles, and active Vision clients.
2. Require zero project names matching the fixed test prefix and zero
   providers, users, or roles matching their fixed prefixes.
3. Recursively browse the bounded shared test-tag root and require a complete,
   non-truncated zero-item result.
4. On the local launcher host, require zero Java processes whose command line
   contains the fixed project prefix. Do not stop or classify unrelated
   Designer or client processes.
5. Review a bounded WARN-or-higher window and require zero entries containing
   the fixed Vision run prefixes.
6. Recheck the adapter version/action count and protected-reference hashes.

One verified 8.3.8 audit after the retarget, default-provider, login/logout,
and restart campaigns found zero matches in every category and no warnings in
the five-minute window. It added no POST action and made no Gateway mutation.
Remote-provider cleanup was not exercised because no remote topology was
available; require the same exact-prefix absence check when that case becomes
eligible.

### `sfc-parallel-expression-fixture-v1`

Use official project/SFC APIs for disposable project lifecycle, definition and
instance readback, export verification, totals, status, detail, and emergency
cancel. If no official chart-start route exists, a fixed Gateway adapter may
use documented `system.sfc.startChart()` and `system.sfc.cancelChart()` calls.

Require one fixed project, three fixed callable charts, one fixed tag root,
one explicit-provider cancel expression, and no caller project, chart,
instance, tag path, expression, or Jython. Safe operations are fixed setup,
tag-driven start, Boolean cancel write, immediate start/cancel, inspect, and
confirmed cleanup. Dry-run, API-token authentication, ownership metadata,
idempotent replay, full tag readback, exact cleanup, and rollback are required.

A safe sequence is:

1. Prove clean SFC totals/status, absent project/tag root, and baseline logs.
2. Reject caller-controlled fields; dry-run/apply setup and replay it.
3. Import/export the fixed project and verify all chart XML byte-for-byte.
4. Start the Parallel chart with the Good cancel tag false; prove the exact
   instance remains running, rewrite false, then write true.
5. Capture the first official terminal state and measured cancellation latency,
   then poll detail/totals until the retained instance clears.
6. Start the Enclosing parent and request fixed-instance cancellation in the
   same bounded operation; require no exception and no active parent or child
   after retention clears.
7. Run existing-action regressions and review the exact action log window.
8. Delete the project and poll all three definitions absent; dry-run/apply and
   replay exact tag cleanup; verify zero shared-parent children and teardown
   warnings.

### `sfc-parallel-expression-suite-v1`

Use this optional fixed-fixture pattern when validating more than a direct
Boolean `tag()` condition in an 8.3.8 Parallel Element. Keep project lifecycle,
chart definition/status/detail, export, totals, emergency cancel, and deletion
on the official project/SFC APIs. Use the adapter only for the missing bounded
start and fixed-trigger operations.

A safe contract should expose:

- One fixed disposable project, nine fixed callable Parallel charts, nine
  allowlisted case IDs, one fixed provider/tag root, and exact cleanup.
- Server-owned literal false/true baselines; arithmetic/comparison, native
  `if()`, and `try()` plus `toInt()` expressions with explicit-provider paths;
  literal null; fixed quality and race cases; and one chart-scope
  `{CancelRequested}` case.
- Only setup, start-case, Boolean set-trigger, inspect, and cleanup operations.
- No caller project, chart, instance, tag path, expression, raw value, or
  Jython.
- For the instance case, accept only fixed slot A or B. Start with
  server-owned parameters, store each returned instance ID, and map the slot to
  that ID plus the fixed `CancelRequested` variable. Never accept an instance
  ID or variable name from the caller.
- Dry-run by default, verified API-token mutation, ownership metadata,
  one-chart-at-a-time isolation except for the exact two-slot instance case,
  idempotent replay, full tag and chart-scope readback, and two-phase
  cancellation-before-tag-deletion cleanup.

A safe sequence is:

1. Prove clean SFC totals/status, absent project/tag root, and baseline logs.
2. Reject every caller-controlled field, invalid case ID, invalid/missing
   instance slot, and non-Boolean trigger selector before writes.
3. Dry-run/apply setup, replay it, then create/import/export the fixed project.
4. Verify all nine callable definitions and exact exported chart XML.
5. Start each literal case once, require `Stopped`, correlate exactly one
   chart-level `onStop`, require no `onCancel` or `onAbort`, reject trigger
   attempts before writes, and refuse replay.
6. For each triggerable single-instance case, start once and prove the inactive input leaves the same
   instance `Running` through an observation interval and explicit false
   rewrite.
7. Select active, capture the first official terminal state and latency, then
   poll retained detail and totals to absence. Refuse a second start.
8. For the two-instance case, start A and B with fixed false scope values,
   require distinct IDs and matching scope readback, rewrite A false, then set
   A true by its stored ID. Prove B retains its ID, remains `Running`, and
   preserves false through A's terminal-to-removal interval. Then set B true
   and correlate exactly one `onStop` per ID and slot.
9. Run existing-action regressions and require an empty WARN-or-higher action
   window.
10. Delete the project and poll all definitions absent. Dry-run/apply and replay
    exact tag cleanup; verify zero shared-parent children, zero running charts,
    and an empty teardown warning window.

## Supported Gateway Migration Record

When validating 8.1-to-8.3 Gateway-wide transforms, use the supported installer
or Gateway-backup route. Do not substitute project or tag import.

1. Record exact source and target versions/builds, image or installer identity,
   modules, Gateway Scripting Project, provider, Tag Group, and timezone.
2. On the source, capture project-script hashes, exact expression text, value,
   type, full quality, timestamp, polling cadence, restart persistence, and the
   complete action log window.
3. Produce the Gateway backup through the supported backup utility. Treat it as
   credential-bearing, keep it only as long as needed, and record its hash
   without publishing credentials.
4. Restore into an isolated exact-version target. Wait for both Gateway and
   fixed observation routes to be ready; do not infer readiness from an early
   HTTP response alone.
5. Recheck the Gateway Scripting Project, script hashes, exact expression text,
   scalar/structured returns, direct exceptions, guarded fallbacks, polling,
   restart behavior, and target migration logs.
6. Classify every warning/error independently. Expected non-Good tag quality is
   not automatically a clean log result, and environment warnings are not
   automatically migration failures.
7. Delete the exact test root, stop and remove target-owned resources, delete
   credential-bearing backups/tokens, and prove the installed Gateway and
   protected references were unchanged.

One fixed 8.1.53-to-8.3.8 Gateway-backup route passed this sequence for two
project-library files and five script-backed Expression Tags. Treat that as a
bounded example, not evidence for the installer route, other versions,
projects, functions, return shapes, polling schedules, hosts, load, or
redundancy.

A second fixed route using the same exact versions preserved four quality
expressions across source restart and target restore: legacy `forceQuality()`
Bad/Good cases and modern `qualifiedValue()` Bad/Good cases. Exact expression
text, values, intended Good/Bad semantics, and the supplied modern-Bad
diagnostic persisted. Record that as preservation evidence, not as automatic
rewriting or a complete quality-code mapping.

## Minimum Result Record

For each expression case, record:

```yaml
test_id: CORE-001
surface: ExpressionTag
expression: "5 + 3 * 2"
declared_type: Int4
expected:
  value: 11
  quality: Good
actual:
  value: 11
  value_type: java.lang.Integer
  quality_code: 192
  quality_level: Good
  quality_name: Good
  diagnostic: null
  timestamp_iso: "<captured>"
status: PASS
cleanup_verified: true
```

Preserve request/response bodies, but redact secrets and private identifiers before sharing.

## Test Sequence

For every mutating batch:

1. Fetch current capabilities.
2. Verify expected version/action count or named actions.
3. Submit a missing-token negative test when developing a new adapter.
4. Submit invalid-field/path/profile negative tests.
5. Submit dry-run and confirm `writesAttempted: false`.
6. Apply the exact reviewed request.
7. Read configuration plus value/type/quality/timestamp.
8. Replay the identical request and confirm no write.
9. Change the request under the same run root and confirm a conflict.
10. Run an unrelated existing read action to catch adapter regressions.
11. Dry-run cleanup.
12. Test incorrect key and missing confirmation when developing the adapter.
13. Apply exact cleanup and verify absence.
14. Replay cleanup and confirm the root remains absent.
15. Export/read back the adapter project if it changed.
16. Query the action-window logs for WARN or higher.

## Diagnostics

Use three windows:

- Baseline: before the action.
- Action: mutation and readback.
- Post-action: cleanup and stabilization.

Classify each warning/error:

- Pre-existing and unrelated.
- Expected negative-test diagnostic.
- Fixture/configuration failure.
- Product/runtime failure.
- Cleanup failure.
- Unexplained; block the affected claim.

Do not declare success merely because the HTTP request returned 200.

## Capability-Gap Rule

Add a new POST action only when:

1. A specific claim is blocked.
2. The live OpenAPI lacks a suitable route.
3. Supported scripting/configuration APIs cannot provide the needed proof directly.
4. The action can be fixed or narrowly allowlisted.
5. It can enforce authentication, bounds, dry-run, idempotency, readback, diagnostics, and exact cleanup.
6. Offline parser/guardrail tests and a live deployment/rollback contract will be executed.

Keep the adapter optional. The reusable expression skill must still work for design, review, and manual validation when the adapter is absent.
