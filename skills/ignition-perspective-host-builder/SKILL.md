---
name: ignition-perspective-host-builder
description: Apply, inspect, update, and validate Ignition 8.1 Perspective resources through an approved host runner. Use for live Gateway changes, not portable import ZIP authoring.
---

# Ignition Perspective Host Builder

Skill version: `1.0.133`
Stack version: `starter-2026.07.06.05`
Runner contract version: `0.3.148`

## Scope

Use the approved Ignition host runner to inspect or apply resources on a reachable Ignition 8.1 Gateway. Use `ignition-perspective-import-zip` first when the task is to author a portable Perspective package; return here to dry-run, apply, read back, and validate it on the live host.

Prioritize completing the requested visualization or page change. Apply relevant design guidance during the build and use the normal readback/browser pass to check the changed behavior.

Treat the runner as controlled support tooling. Do not use guessed connection details, default credentials, direct project-filesystem writes, native file chooser automation, or undocumented Gateway import methods.

## Non-Deletion Rule

Do not delete, remove, prune, or clean up live Gateway, project, Perspective, tag, database, backup, or temporary resources unless the user explicitly commands that deletion in the current task. Default to create, update, merge, read back, and validate. If deletion seems necessary, stop and ask.

The runner's normal automatic cleanup of its own package work directory is part of an authorized dry-run/apply operation. This exception does not authorize deleting user/project resources, retained backups, or unrelated temporary files.

## Runtime Inputs

Obtain these from the user, approved connection profile, environment, or live discovery:

- Gateway and runner connection profile
- target project
- validated package path or package bytes
- target view and page paths
- allowed view, route, script, and Named Query prefixes as applicable
- expected live hashes for intentional overwrites
- exact Ignition patch and affected client/module environment when a version-specific behavior or failure matters; keep these distinct from the runner version

Keep tokens, passwords, cookies, private hosts, local install paths, and customer identifiers out of reusable skill files and generated documentation.

## Read References Selectively

- Read [references/runner-capabilities.md](references/runner-capabilities.md) before calling the runner, selecting an action, or checking compatibility.
- Read [references/apply-and-rollback.md](references/apply-and-rollback.md) before package dry-run, apply, overwrite, backup inspection, or rollback.
- Read [references/project-discovery-patterns.md](references/project-discovery-patterns.md) when discovering routes, views, styles, reusable resources, component seeds, Named Queries, or existing view hashes.
- Read [references/tag-alarm-udt-patterns.md](references/tag-alarm-udt-patterns.md) only when the page depends on tags, history, alarms, UDTs, or guarded tag fixtures.
- Read [references/runner-maintenance.md](references/runner-maintenance.md) only when the user explicitly asks to inspect or update the approved runner resource.
- Read [references/ignition-doc-links.md](references/ignition-doc-links.md) when official Ignition 8.1 source documentation is needed.
- Read [references/complete-runtime-details.md](references/complete-runtime-details.md) when an edge case requires exhaustive pre-restructure runner/workflow detail or a topical reference omits a tested compatibility boundary.
- Read matching sections of [references/page-behavior-and-validation.md](references/page-behavior-and-validation.md) when building or changing reusable/embedded views, repeated content, tables/charts, operator controls, refresh logic, pipes, or custom styles.
- Read matching entries in [references/ignition-8.1-known-issues.md](references/ignition-8.1-known-issues.md) only for an observed failure or an explicit version-compatibility question.

Locate the relevant heading or symptom and read that section, expanding only for actual dependencies. Do not load both new references or the complete runtime archive by default. Open source links only when a decision needs verification beyond the reference.

## Core Workflow

1. Call runner health through the approved connection profile. Require JSON with `ok: true`; stop on empty or non-JSON success responses.
2. Confirm the target project, runner contract, callable actions, and only the feature flags required for the requested workflow. Never invent an unavailable action.
3. Call `gatewayInfo` when Ignition version, module state, trial/license state, target project existence, or runner-path diagnostics matter.
4. Discover existing routes and views before choosing new paths. Read an existing view and capture its current SHA-256 before any intentional overwrite.
5. Discover styles, reusable views, project images, component seeds, Named Queries, tags, alarms, and history only when the page requires them. Use returned names and paths exactly; do not guess project resources.
6. Obtain a validated package from the authoring/import-zip workflow. Declare every packaged dependency explicitly.
   Apply the relevant page-behavior guidance while building or reviewing that package; choose only the checks needed for its changed features.
7. Submit package `dryRun` with a stable caller-generated `requestId`, approved prefixes, dependencies, routes, overwrite policy, and expected hashes. Require the same request ID in the response.
8. Stop on unexpected project, route conflicts, missing dependencies, hash drift, prefix violations, unsafe query parameters, incomplete validation, or any recovery-required response.
9. Call `apply` only after dry-run proves the exact intended change. Require expected copied resources, merged routes/docks, backup evidence, completed scan, final-state validation, and `recoveryRequired` not true.
10. Read back changed resources. Use `pageValidate` as a structural gate, not render proof.
11. Query only a narrow recent log window when diagnostics are needed. Logs explain failures; they do not prove the page rendered correctly.
12. Open the concrete Perspective route in a browser. Verify components, bindings, empty/fallback states, interactions, and browser-console cleanliness appropriate to the workflow.
13. For command or writeback pages, prove both a blocked unsafe case and an accepted safe case, then verify final state through the relevant readback action.
14. Report exact changed resources, target route, validation evidence, backup name/location, rollback posture, and any remaining dependency.

## Discovery And Authoring Rules

- Use `routesList`, `viewsList`, and `viewRead` before overwriting or selecting paths.
- Use `styleResourcesList` before claiming alignment with an existing project style, theme, reusable view, or image.
- Use `seedViewsList` followed by an exact `seedViewRead` or `componentSeedRead` before hand-authoring fragile component JSON. Select a concrete seed view first; a component type alone is insufficient. Inspect the exact symbol seed/documentation for anatomical artwork; do not infer process nozzles from stands, shafts, agitators, or decoration. Set anatomy props such as Vessel `orientation`, `displayStand`, and `displayAgitator` explicitly, and model real process connections with named overlay anchors.
- Copy only the minimal component shape and parameterize project-specific paths, bindings, styles, images, and values.
- For Coordinate Container process graphics, define equipment bounds, named nozzle/connection anchors, header centerlines, and elbows before pipes. Derive every pipe segment from those anchors, render pipes behind equipment, and allow only a small documented endpoint overlap beneath a symbol edge; never route a process line through a symbol interior.
- Treat dynamic Embedded View paths, View Canvas children, popup views, Project Library scripts, Named Queries, and shared docks as explicit dependencies.
- Design database-backed pages from discovered Named Query metadata and bounded preview rows, then prove the runtime binding in the browser.
- Design tag-driven pages from a verified provider/root and reusable model. Avoid one hard-coded full path per asset when a root plus parameters can drive the page.
- Give every operator-facing Tag History entry an explicit unique `alias`; do not expose provider paths or simulator leaf names. With Wide return format, treat the alias as the dataset field name and update explicit `props.plots[].trends[].columns[].key` values to match.
- Give every industrial animation explicit semantics: what changes, where, in which direction, and under which live state. Gate it from that state, add a nearby text or shape cue, and sample the source tag before normalizing and clamping its documented range.
- Derive each moving route marker from the same named start/end anchors as its route segment. If telemetry proves activity but not transit or direction, use a fixed directional cue with a pulsing visual property and label the local medium and direction.

## Mutation Guardrails

- Treat enum-backed Perspective styles as typed schema values, not generic CSS. Before apply, recursively inspect every packaged view, component, and nested style object; require `fontWeight` to be a Designer-supported string such as `"700"`, `"800"`, `"bold"`, or `"normal"`, and fail numeric or unsupported values.
- Dry-run every write and use the exact action-specific confirmation string.
- Allowlist project names, resource prefixes, dependency paths, file types, and package sources.
- Require current view hashes for existing view overwrites. Treat stale or missing hashes as stop conditions.
- Treat mutation-lock conflicts as retryable state changes: rediscover, repeat dry-run, and apply only if the plan remains identical.
- Treat scan failures, partial writes, final-state validation failures, unknown mutation state, and recovery-required responses as stop conditions.
- Preserve the complete JSON error body on non-2xx responses when the runner returns structured diagnostics.
- Do not reconstruct runner work paths or invent backup names. Treat returned backup identifiers as opaque values for reporting and rollback; report a backup location only if the runner explicitly returns it for the current user's operation. Keep private paths out of reusable output.

## Validation Standard

Integrate feature checks into the existing readback/browser pass. After required checks pass, deliver the build. Do not add benchmarks, soak tests, load tests, broad audits, new fixtures, or a diagnostics project merely because a reference mentions them; pursue extra investigation only when requested or needed to resolve an observed failure within the authorized scope.

After apply:

- Confirm the live target project and completed scan/reload evidence.
- Confirm route, view, script, Named Query, shared dock, and hash checks relevant to the package.
- Confirm structural readback matches the package's final managed state.
- Verify the concrete browser route, not only HTTP 200.
- For a Time Series Chart in a row-layout branch, confirm with `viewRead` that the growing chart column and every intermediate growing wrapper use the intended `grow`/`shrink` values and `basis: "0px"`; browser-measure bounding rectangles at the target viewport and fail intrinsic-width overflow or displaced sibling workflows.
- For every process Coordinate Container, perform a focused crop or DOM/SVG geometry pass after the whole-page screenshot. Confirm every pipe endpoint meets a named anchor, no segment crosses equipment unexpectedly, no orphan pipe remains, symbol fills look intentional, and animation is state-gated and locally labeled. At the named target viewport, require asset nameplates to remain outside equipment bounds, pipe corridors, instrument cards, and action regions with a deliberate 8-16 px gap unless intentionally overlaid; reapply that viewport after login or trial navigation before saving evidence.
- Treat browser component/property errors as failures even when structural validation passes.
- Render every built-in symbol state and orientation the page can use at its final size and background. For valves, inspect open, closed, partially closed, reverse-flow, and orientation variants as applicable; reject accidental or asymmetric neutral styling and pair visual state with redundant text. A schema-valid enum is not visual acceptance proof.
- For Tag History charts, require every intended alias in the browser, no raw provider/path/simulator key, rendered marks, and no console errors.
- Sample animated DOM properties at two or more times and require a measurable change. Prove no duplicate or legacy route marker exists, its full travel range stays in the named corridor, and its bounds never intersect equipment, nameplates, or label exclusions. Reserve an obstacle-free lane for every animated overlay and compare its swept bounds against bars, labels, and reference lines; for text inside bars, require explicit `alignItems`, `justifyContent`, `textAlign`, zero padding, and measured center alignment.
- After apply, recursively inspect live `viewRead` output for the entire changed view set and confirm every `fontWeight` remains a supported string; do not stop after repairing the first visible component.
- Verify tag quality, query rows, alarm filters, historian availability, command readback, and fallback behavior when used.
- Smoke-test Designer startup when page-config or project-resource changes could serialize correctly at runtime but fail in Designer.
- Do not stop Gateway service processes while cleaning up a Designer launch test.

## Output

Report:

- target Gateway/project and applied page/view paths
- dry-run and apply request IDs
- copied and merged resources
- overwrite hashes and readback hashes
- backup evidence and rollback note
- structural, log, browser, and Designer validation performed
- any unavailable capability, unresolved dependency, recovery requirement, or unproven runtime behavior
