# Gateway And Vision Diagnostics

## Contents

- [Evidence planes](#evidence-planes)
- [API access and health](#api-access-and-health)
- [Project and resource triage](#project-and-resource-triage)
- [Window structure and dependencies](#window-structure-and-dependencies)
- [Designer-only expression binding failures](#designer-only-expression-binding-failures)
- [Client sessions, startup, and exits](#client-sessions-startup-and-exits)
- [Gateway and client logs](#gateway-and-client-logs)
- [Unresolved built-in menu terms](#unresolved-built-in-menu-terms)
- [Runtime state and screenshots](#runtime-state-and-screenshots)
- [Designer Design Mode versus runtime](#designer-design-mode-versus-runtime)
- [Open Designer boundary](#open-designer-boundary)
- [Layout and text problems](#layout-and-text-problems)
- [A screen that does not move](#a-screen-that-does-not-move)
- [Runner update or activation problems](#runner-update-or-activation-problems)
- [Recovery and completion](#recovery-and-completion)

## Evidence Planes

Keep each claim on the evidence plane that can actually prove it:

| Plane | Can prove | Cannot prove alone |
|---|---|---|
| Gateway health/project API | versions, modules, projects, providers, connections, resources, logs | client pixels or client-only logs |
| Serialized Vision inspection | component hierarchy, bounds, bindings, actions, resource identity | live evaluation, pixels, clicks |
| Dependency preflight | bounded tag/query/template/navigation readiness | visual correctness or future availability |
| Fixed client query | allowlisted runtime state/action in one correlated client | arbitrary client control or unrelated components |
| Native client screenshot | pixels at one moment | binding quality, event execution, persistence |
| Focused logs | reported errors/events in one JVM | absence of all possible failures |

Do not collapse these into a single “screen works” claim.

## API Access And Health

1. Call `health` and require the expected token/capabilities.
2. Call `gatewayInfo` and `gatewayPerformanceSnapshot`.
3. Reject mutation when heap use is unbounded, blocked threads are nonzero, the runner is unhealthy, or an expected module/project is absent.
4. Record `runnerVersion`, `supportedActions`, and `features` from the live response.
5. Use read-only diagnostics before opening a client or changing a resource.

If authentication fails, verify the endpoint and process environment without printing the token. If the action is unsupported, use the documented fallback or upgrade; do not force the operation through script evaluation.

Treat the Gateway shell and the runner route as separate health planes. The Gateway root, `StatusPing`, and `system/gwinfo` can all return HTTP 200 while a licensed Web Dev route rejects `health` before action dispatch. If the runner route returns HTTP 402:

1. Stop runner updates and project mutations through that route.
2. Verify the Gateway shell endpoints independently and record the runner route's exact status.
3. Inspect bounded Gateway logs for trial or license reset/expiration messages.
4. Treat the result as a license/trial gate, not as proof that runner code failed or that its version changed.
5. For the authorized direct shell workflow, require expired status from `GET /data/status/trial`, an authenticated same-origin IdP session with `config:true`, a separate exact reset confirmation, `PUT /data/status/trial`, and positive active status on readback. Keep credentials, cookies, and identity tokens in memory only.
6. Re-run runner `health`, capability, and performance checks before resuming.

Do not use runner self-update as a workaround for HTTP 402; the request was rejected before the runner could execute. This customer package intentionally ships no reset/recovery executable or desktop fallback; use the documented bounded workflow or stop.

## Project And Resource Triage

- Use `projectsList` to select the exact project.
- Use `projectInfoRead` for live default provider/database information.
- Use `projectResourcesList` under the narrowest module/resource prefix.
- Read the exact resource with hashes and `resource.json` metadata.
- Validate the path with `projectResourceNameValidate` before any create, import, rename, or relocation.
- Compare filesystem/resource hashes to the intended package. A Designer tree can be stale even when the Gateway resource is correct.
- Export the current resource before a risky change and record the backup returned by the runner.

Common causes of a resource visible on disk but missing in Designer include an invalid resource name, invalid `resource.json`, undeclared/missing payload files, wrong module root, scan failure, or a stale Designer project tree.

## Window Structure And Dependencies

Use `visionWindowInspect` or `visionTemplateInspect` and require:

- exact project/resource/logical path identity;
- valid manifest and declared payload file;
- expected serialization format and version;
- complete, non-truncated hierarchy and interaction results;
- positive local bounds and valid accumulated bounds;
- expected binding types and script/action metadata;
- no unexplained warnings.

Then use dependency preflight and verify concrete:

- tag providers, paths, values, and quality;
- Named Queries, database connection health, parameters, and bounded preview eligibility;
- template resources and payloads;
- navigation targets;
- indirect bindings and parameters when reusable templates are involved.

For a finite tag set used by component-event or timer Jython, require the returned script tag dependencies to equal the intended fully qualified paths exactly. If preflight returns a path containing a formatting placeholder or a partially assembled fragment, do not waive the failure because the client happens to move. Route the handler to `ignition-vision-jython`, replace the fixed path construction with explicit string literals, and rerun preflight. When paths are truly runtime-dynamic, record that static dependency evidence is incomplete and use a bounded allowlist, direct `tagRead` quality checks, fresh-client behavior, and focused client logs as separate evidence.

Inspecting serialized metadata does not execute scripts or prove a live binding.

## Designer-Only Expression Binding Failures

An expression can fail while Designer attaches the binding even when every source tag currently reads Good. One important failure shape is a nested bound-tag listener whose serialized initial `QualifiedValue` is missing or null: the expression may dereference that raw value before the first subscription update arrives.

Diagnose this API-first:

1. Call live `health`; require `visionWindowInspect` and `visionExpressionBindingInitialValueInspection`.
2. Inspect the exact window with complete component/interaction limits and a pinned resource-state hash.
3. Require target-runtime transcode for binary-v2 and complete aggregate evidence for every expression binding.
4. Review both the expression adapter initial value and every nested bound-tag listener initial value. A Good live tag read does not initialize a missing serialized listener value.
5. Fail closed on unknown/truncated evidence, missing/null/unresolved listener values, initialization-risk flags, or unexplained warnings/advisories.
6. After repair, repeat deterministic inspection, then use one newly launched Vision Client for runtime confirmation and focused client logs.

This is an API visibility boundary: Gateway logs cannot show a Designer-JVM dialog, the fixed Vision Client log query excludes Designer, and Designer session inventory proves presence rather than reading its logs. Serialized initialization inspection is the programmatic prevention gate. If the remaining claim depends on Designer-only runtime evidence, stop without substituting desktop control.

## Client Sessions, Startup, And Exits

- Query sessions before resource changes and before dispatching a fixed client action.
- Exclude Designer sessions. Select one exact project/client ID or require zero clients.
- Classify the Inductive Automation Designer Launcher utility separately from an active Designer and a Vision Client. A launcher Java process can have a visible window but no Designer startup hook and no Gateway client session; require its verified launcher main class/title and keep an explicit list of unexplained process candidates. Do not count the launcher as runtime evidence or block a zero-client guard merely because it is open.
- Keep one intended startup window unless the project explicitly requires more.
- Separate gallery pages into nonstartup windows; multiple startup windows can appear stacked.
- Install required Client Event Scripts and mailboxes before launching a fresh client.
- Distinguish an intentional owned-client shutdown from a crash. Record the process/session identity, launch time, exit code, client logs, Gateway logs, and whether the runner deliberately stopped it.
- After validation, stop only clients the workflow owns and require the final session inventory expected by the operator.

A window that opens and immediately exits can result from authentication failure, project/resource download failure, deserialization errors, startup script exceptions, missing modules, trial state, launcher/classpath mismatch, or an intentional cleanup path. Use logs from both JVMs.

## Gateway And Client Logs

For Gateway logs, use a small time window and focused logger/message/text filters. Query broad logs only with the explicit broad-query confirmation and a strict result cap.

For Vision Client logs, require the fixed client-log action, handler, and mailbox-restoration features. If they are unavailable, stop the client-log claim. Do not infer client status from Gateway logs.

When the API workflow owns the native client process and captures its stdout/stderr, scan those streams as a separate failure plane. Early component-event and `ActionAdapter` Jython exceptions can appear there before the fixed client-log bridge returns them. Require clean focused client logs and clean relevant process output when both are available; a connected session or successful screenshot is not a substitute.

A registered client session can appear before the Vision application and Project Client Event Script bridges are ready. Track at least these states separately:

- process started;
- Gateway session registered;
- Vision application/window ready;
- exact fixed bridge returned a correlated typed response;
- requested runtime/log/screenshot evidence collected.

Use a bounded bridge-readiness deadline after a fresh launch. On timeout, collect evidence before cleanup: session inventory, client ID, project and resource identity, resource hash, action/error code, Gateway logs, client-log result or its timeout, owned launcher stdout/stderr, and timestamps. Give every evidence plane an explicit collection status. Do not turn an unavailable client-log bridge into a false `clean` result.

Good diagnostic practice:

- capture a timestamp immediately before the action;
- filter for the project/resource/handler/component logger or a bounded request ID;
- include WARN and ERROR, plus INFO/DEBUG only when needed;
- preserve short structured entries, not unrestricted log tails;
- redact credentials, tokens, cookies, and usernames unless identity is necessary and approved.

## Unresolved Built-In Menu Terms

Text such as `¿fpmi.RootMenu.Command.Name?` is an unresolved built-in localization key, not an intentional menu label or window style.

1. Correlate the visible Java process with exactly one registered non-Designer Vision session. Treat a responsive process with no Gateway connection or session as orphaned or stale; do not use it as runtime proof.
2. Record the launch time and arguments. Check for unexpected locale, language, or bundle overrides.
3. Verify that the cached Vision client artifacts match the Gateway patch and contain the expected localization bundle entries. Do not modify jars or delete the cache during diagnosis.
4. Inspect project/global locale settings and Client Event startup, update, timer, and message-handler code for localization calls.
5. After the runner starts a fresh client, immediately query its logs through the fixed client-log action for `Localization.ClientLocalizationManager`, bundle, and translation messages.
6. Reproduce the failure on two fresh launches before considering cache repair. Preserve the original cache and logs first, and do not substitute Gateway logs for client startup logs.

## Runtime State And Screenshots

Use the fixed runtime query for one exact client and allowlisted component paths. Validate:

- one selected non-Designer session;
- exact open/current window state;
- expected component class and structural path;
- bounded value, quality, geometry, state, or dataset shape;
- exact resource hash and marker identity;
- zero unexpected side effects;
- mailbox restoration.

For visual claims, request one bounded PNG of the exact open root and a complete text-fit audit. Verify the decoded dimensions and hash, then inspect:

- titles and primary labels;
- ellipsis/clipping;
- numeric alignment;
- z-order and occlusion;
- runtime intersections between titles, legends, scale notes, and moving annotations;
- chart legends/axes/series;
- state text and colors;
- custom painting and process connections.

Text-fit success does not prove custom-painted content, overlap, or interaction. A screenshot does not prove tag quality or persistence.

A fixed Easy Chart query may support only one allowlisted window, component path, and serialized fixture contract. Read the live action contract before using it. If the target chart is outside that contract, do not broaden the action or claim generic chart introspection. Use the safe fallback as a combined proof:

1. Inspect the window and dependency preflight to identify each chart, pen, and fully qualified historian source.
2. Run a bounded history probe for every source and require Good results with the expected time range and row shape.
3. Query allowlisted client components to prove the related bound values are Good and moving where motion is claimed.
4. Capture the exact client root and complete text-fit report, then inspect the PNG for visible traces, axes, legends, title collisions, and content outside the observed root.

History rows prove available source data, not that the chart rendered it. The screenshot proves rendered pixels at one moment, not binding quality. Require both evidence planes for a live-chart claim.

For timer- or history-driven visuals, capture runtime properties after at least two completed refreshes. Assert the derived fields as well as the directly bound value: for example, sample count and statistics are populated, bar heights are non-placeholder and varied, marker coordinates are in range, and the live value changes. Query Vision's runtime geometry properties such as `boundsHeight` or `boundsX` when the client bridge exposes them; serialized design bounds alone do not prove the layout manager retained a runtime change.

## Designer Design Mode Versus Runtime

Designer Design Mode can evaluate direct tag bindings while leaving component-event or PMITimer-driven Jython at its serialized defaults. A screen can therefore show a changing live value beside blank statistics or flat bars even though the same window populates correctly in Preview Mode or a Vision Client.

Diagnose this split explicitly:

1. Identify which fields are direct bindings and which are produced by event/timer code.
2. Treat changing direct-bound values in Design Mode as tag/binding evidence only.
3. Use a newly launched Vision Client, wait for at least two completed refreshes, and query the derived fields and runtime geometry.
4. Require focused client logs and a native screenshot before declaring the scripted visual working.
5. If Design Mode is part of a review-gallery workflow, serialize an obviously labelled representative preview rather than blank or misleading values. The preview must say that the client supplies live data, and runtime code must replace every preview-derived field.

Do not label serialized preview statistics as current live results. An already-open Designer can retain old local bytes after a Gateway import, so exclude that Designer state from API proof. Judge the imported resource by Gateway readback and a newly launched Vision Client.

## Open Designer Boundary

An externally imported or relocated resource can be correct on the Gateway while an already-open Designer tab still holds the previous payload and manifest. Saving that stale tab can overwrite the repaired bytes and can restore old `open-on-start` values across several windows.

1. Before mutation, record the exact resource-state hash, payload hashes, complete startup set, and open Designer identity.
2. Treat the open Designer as a mutation guard, not a controllable API target. `visionDesignerSessionsQuery` can inventory the session, but the runner cannot refresh its project, receive a project message in it, or resolve its local conflicts.
3. Do not use or save affected Designer tabs during the API-managed change. If completion depends on unsaved Designer-local work, stop without attempting a desktop or internal-SDK workaround.
4. Re-read the Gateway resource-state hash, payload hashes, dependency readiness, and complete startup set after the mutation and again at handoff. Then use one newly launched Vision Client, focused client/Gateway logs, and a native screenshot for runtime confirmation.
5. If Gateway drift occurred, restore the intended sole-startup baseline, rebuild or re-import the replacement under a separate candidate path, prove it in a fresh client, and use state-pinned delete/relocation with rollback backups. Do not patch the drifted canonical payload in place.

Attribute a property-setting error to the resource identity named in the error before changing the current window. Compare that qualified template/window name with the current dependency preflight. If the current window points only to a different, state-pinned replacement and its fresh-client log is clean, inspect the named stale or orphaned resource separately. Remove an obsolete resource only after a complete project dependency audit and an exact-state, rollback-backed delete; do not modify the working replacement merely because an open Designer tab reports an older resource's error.

Treat a changed hash or unexpected startup window as a failed final gate even when the prior client screenshot and logs were clean.

## Layout And Text Problems

When values or titles are clipped:

1. Inspect local and accumulated bounds.
2. Confirm the component is inside its immediate parent and root.
3. Check preferred bounds, layout constraints, anchor flags, and font scaling.
4. Confirm the actual text, font, insets, icon gap, and alignment.
5. Exercise the longest reachable data-derived string, not only the serialized preview value.
6. Capture the root at the failing client size.
7. Correct the smallest responsible bound/layout/text choice and repeat the native round trip.

When windows appear stacked, first inspect startup flags and startup navigation. Designer selection/z-order is not runtime navigation. Keep examples nonstartup and open them intentionally.

When an empty bordered box appears, inspect the component class, state/dataset initialization, foreground/background, selected state, and serialized properties. Do not assume it is decorative.

## A Screen That Does Not Move

Diagnose in this order:

1. Confirm the intended source is genuinely dynamic.
2. Read the exact tag at least three times over a useful interval and require Good quality plus changed values.
3. Inspect the serialized binding target and fully qualified tag path.
4. Verify the active project's default provider only if the binding is unqualified.
5. Query the component's runtime value and binding quality in the same client.
6. If a chart is involved, distinguish configured pens from loaded datapoints and historian retrieval.
7. Check client and Gateway logs for binding, expression, history, query, or deserialization errors.
8. Label static demonstration datasets as static. Do not expect motion from a fixed dataset.

Use existing moving simulated tags when appropriate. Create new tags or UDTs only when the screen needs a missing semantic/data contract, and preserve the evidence for that separate skill change.

## Runner Update Or Activation Problems

If a guarded runner update reports a successful file write/scan but live `health` remains on the old version:

1. Stop further mutations.
2. Read back the exact Web Dev resource and compare the stored wrapper hash to the candidate.
3. Query focused and bounded Gateway logs around the update timestamp for the resource, project manager, Web Dev, compiler, traceback, and method-size failures.
4. Compile the readable source, direct Web Dev wrapper, and every lazy/generated payload with the installed target Jython runtime.
5. Check Gateway performance and blocked threads to rule out overload.
6. Reconcile resource metadata, project scan completion, active endpoint version, and backups before deciding whether a same-version rescan or rollback is safe.
7. Do not restart the Gateway unless the operator explicitly authorizes it and API/readback alternatives are exhausted.

A clean focused log query does not prove activation. The live health response is the final capability authority.

## Recovery And Completion

- On a failed or lost write response, reconcile before retrying.
- Use the runner-created backup and normal rollback contract; do not manually replace project files while the Gateway is active.
- Treat mailbox restore failure, partial scan, stale hash, ambiguous client, bad quality, or truncated required evidence as incomplete recovery.
- Recheck health/performance, startup windows, retained dependencies, sessions, and focused logs after recovery.
- Preserve diagnostics and screenshots internally; ship only approved operational references, reusable helpers, and explicitly required assets.
