---
name: ignition-perspective-host-builder
description: Apply, inspect, update, and validate Ignition 8.1 Perspective resources through an approved host runner. Use for live Gateway changes, not portable import ZIP authoring.
---

# Ignition Perspective Host Builder

Skill version: `1.0.131`
Stack version: `starter-2026.07.06.04`
Runner contract version: `0.3.148`

## Scope

Use the approved Ignition host runner to inspect or apply resources on a reachable Ignition 8.1 Gateway. Use `ignition-perspective-import-zip` first when the task is to author a portable Perspective package; return here to dry-run, apply, read back, and validate it on the live host.

Treat the runner as controlled support tooling. Do not use guessed connection details, default credentials, direct project-filesystem writes, native file chooser automation, or undocumented Gateway import methods.

## Non-Deletion Rule

Do not delete, remove, prune, or clean up live Gateway, project, Perspective, tag, database, backup, or temporary resources unless the user explicitly commands that deletion in the current task. Default to create, update, merge, read back, and validate. If deletion seems necessary, stop and ask.

## Runtime Inputs

Obtain these from the user, approved connection profile, environment, or live discovery:

- Gateway and runner connection profile
- target project
- validated package path or package bytes
- target view and page paths
- allowed view, route, script, and Named Query prefixes as applicable
- expected live hashes for intentional overwrites

Keep tokens, passwords, cookies, private hosts, local install paths, and customer identifiers out of reusable skill files and generated documentation.

## Read References Selectively

- Read [references/runner-capabilities.md](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-host-builder/references/runner-capabilities.md) before calling the runner, selecting an action, or checking compatibility.
- Read [references/apply-and-rollback.md](apply-and-rollback.md) before package dry-run, apply, overwrite, backup inspection, or rollback.
- Read [references/project-discovery-patterns.md](project-discovery-patterns.md) when discovering routes, views, styles, reusable resources, component seeds, Named Queries, or existing view hashes.
- Read [references/tag-alarm-udt-patterns.md](tag-alarm-udt-patterns.md) only when the page depends on tags, history, alarms, UDTs, or guarded tag fixtures.
- Read [references/runner-maintenance.md](runner-maintenance.md) only when the user explicitly asks to inspect or update the approved runner resource.
- Read [references/ignition-doc-links.md](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-host-builder/references/ignition-doc-links.md) when official Ignition 8.1 source documentation is needed.
- Read [references/complete-runtime-details.md](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-host-builder/references/complete-runtime-details.md) when an edge case requires exhaustive pre-restructure runner/workflow detail or a topical reference omits a tested compatibility boundary.

## Core Workflow

1. Call runner health through the approved connection profile. Require JSON with `ok: true`; stop on empty or non-JSON success responses.
2. Confirm the target project, runner contract, callable actions, and only the feature flags required for the requested workflow. Never invent an unavailable action.
3. Call `gatewayInfo` when Ignition version, module state, trial/license state, target project existence, or runner-path diagnostics matter.
4. Discover existing routes and views before choosing new paths. Read an existing view and capture its current SHA-256 before any intentional overwrite.
5. Discover styles, reusable views, project images, component seeds, Named Queries, tags, alarms, and history only when the page requires them. Use returned names and paths exactly; do not guess project resources.
6. Obtain a validated package from the authoring/import-zip workflow. Declare every packaged dependency explicitly.
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
- Use `seedViewsList` followed by an exact `seedViewRead` or `componentSeedRead` before hand-authoring fragile component JSON. Select a concrete seed view first; a component type alone is insufficient.
- Copy only the minimal component shape and parameterize project-specific paths, bindings, styles, images, and values.
- Treat dynamic Embedded View paths, View Canvas children, popup views, Project Library scripts, Named Queries, and shared docks as explicit dependencies.
- Design database-backed pages from discovered Named Query metadata and bounded preview rows, then prove the runtime binding in the browser.
- Design tag-driven pages from a verified provider/root and reusable model. Avoid one hard-coded full path per asset when a root plus parameters can drive the page.

## Mutation Guardrails

- Dry-run every write and use the exact action-specific confirmation string.
- Allowlist project names, resource prefixes, dependency paths, file types, and package sources.
- Require current view hashes for existing view overwrites. Treat stale or missing hashes as stop conditions.
- Treat mutation-lock conflicts as retryable state changes: rediscover, repeat dry-run, and apply only if the plan remains identical.
- Treat scan failures, partial writes, final-state validation failures, unknown mutation state, and recovery-required responses as stop conditions.
- Preserve the complete JSON error body on non-2xx responses when the runner returns structured diagnostics.
- Never expose or reconstruct runner work paths and backup names; treat returned values as opaque.

## Validation Standard

After apply:

- Confirm the live target project and completed scan/reload evidence.
- Confirm route, view, script, Named Query, shared dock, and hash checks relevant to the package.
- Confirm structural readback matches the package's final managed state.
- Verify the concrete browser route, not only HTTP 200.
- Treat browser component/property errors as failures even when structural validation passes.
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
