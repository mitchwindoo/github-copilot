---
name: ignition-perspective-import-zip
description: Create portable Ignition 8.1 Perspective project import zip packages. Use when Codex must author a correct Perspective view/page and deliver an importable project .zip/.proj package, install checklist, or dependency bundle for another Ignition instance. Do not use for direct same-PC Gateway/Web Dev/API/filesystem deployment; use ignition-perspective-host-builder for that.
---

# Ignition Perspective Import Zip

Skill version: `1.0.113`
Stack version: `starter-2026.07.06.05`

## Primary Output

Produce a portable Ignition 8.1 project import package, not a live Gateway change.
Keep package mechanics secondary to correct Perspective view/page authoring.

Build the requested visualization using relevant guidelines and anti-patterns. Apply those rules during authoring, then complete the package and required offline checks. Do not add benchmarks, load/soak tests, broad audits, new fixtures, or a diagnostics project by default. Extra investigation is for a requested analysis or an observed failure within scope.

Required output:

- Project import `.zip` or `.proj` built from a valid Ignition 8.1 seed/export structure.
- `INSTALL.md` with import steps, dependencies, conflict policy, and placeholders.
- `VALIDATION.md` with smoke checks for import, route/view rendering, bindings, scripts, and logs.

Never require Gateway credentials, API access, Web Dev access, or target Gateway filesystem access for this skill. Local output-file creation is part of producing the requested package.

## Non-Deletion Rule

Do not delete, remove, prune, or clean up existing user/project resources unless the user explicitly commands that deletion in the current task. This includes files, Perspective views/routes/styles/images, scripts, named queries, tags, UDTs, alarms, database rows, backups, and temp resources. Default to create/update/merge/validate; if deletion seems required, stop and ask.

## Portability

- Do not hard-code local paths, Gateway URLs, project names, tag providers, tag paths, database names, usernames, passwords, tokens, cookies, or workstation usernames.
- Use placeholders: `<gatewayUrl>`, `<projectName>`, `<viewPath>`, `<pagePath>`, `<tagProvider>`, `<tagPath>`, `<databaseConnection>`, `<gatewayUser>`.
- Treat tags, tag providers, database connections, OPC devices, MQTT providers, certificates, users, roles, and security zones as per-instance prerequisites.
- Put instance values in install/config notes, not reusable skills or generated project resources, unless the user explicitly provides final target values.

## Build Flow

1. Identify Ignition version, target project/package name, view path, route path, title, required tags/scripts/queries/modules, and import method.
2. Start from a matching Ignition 8.1 seed export whenever possible.
3. Preserve `project.json`, `resource.json`, resource folder names, and expected file lists.
4. Add or replace only intended project resources.
5. When adding or removing files inside a runner-managed resource folder, update that resource's `resource.json.files` list so it matches the final sibling data files.
6. Structurally parse and write `com.inductiveautomation.perspective/page-config/config.json`; include only intended routes and every referenced view.
7. Package Gateway-level dependencies separately; do not pretend the project zip creates them.
8. Record the intended `pagePath`, primary `viewPath`, dependency view paths, and Project Library script paths for later host/API validation.
9. Validate offline before delivery. Put relevant target acceptance checks in `VALIDATION.md`; mark checks not performed as pending instead of claiming live proof or delaying a usable package for unavailable access.

If only `view.json` is available and no trusted `resource.json`/seed exists, do not claim the result is importable. Provide Designer Copy JSON/Paste JSON steps or require a seed export.


## Read References Selectively

Read the matching heading/section, expanding only for real dependencies. Do not load every reference or open every source link for an ordinary build. Use sources when a concrete decision needs verification beyond the guidance.

- Read [references/perspective-view-json-guardrails.md](references/perspective-view-json-guardrails.md) for view structure; read its Bindings or Scripts sections when authoring those features.
- Read [references/component-layout-and-visuals.md](references/component-layout-and-visuals.md) for exact symbols/pipes, Flex sizing/readability, semantic styling, or animation.
- Read [references/reusable-views-and-interactions.md](references/reusable-views-and-interactions.md) for embedded params, repeaters/View Canvas, selection/navigation/docks, messages/custom methods, or command controls.
- Read [references/data-bindings-and-refresh.md](references/data-bindings-and-refresh.md) for Named Queries, UDT/tag models, tables/paging/refresh, alarms, history, or chart data shapes.
- Read [references/package-contract.md](references/package-contract.md) when constructing the project ZIP, manifests, dependency bundle, install order, or handoff checklist.
- Read [references/ignition-8.1-known-issues.md](references/ignition-8.1-known-issues.md) only for an observed failure or an explicit patch-compatibility question. Unknown patch details do not block an otherwise valid offline package; record assumptions when relevant.
- Read [references/ignition-doc-links.md](references/ignition-doc-links.md) when official source documentation is needed.

## Core Perspective JSON Rules

- Preserve Ignition 8.1 Perspective JSON shape: `custom`, `params`, `props`, `root`, `propConfig`, `events`, `permissions`.
- Keep dynamic bindings under `propConfig`, not under `props`.
- Put component bindings in that component's own `propConfig` with keys like `props.text`; do not use top-level `propConfig` keys like `root.children[0].props.text`.
- Use `view.params` for external inputs and `view.custom` for internal state.
- Prefer parameterized/reusable views over hard-coded per-device tag paths. Pass a base tag path, device id, provider, or folder root through `view.params`; build derived member paths in bindings/scripts.
- For multi-asset pages, browse/query a validated root folder at startup or in a Project Library script, filter to expected UDT instances/members, write rows/instances into `view.custom`, and bind tables/repeaters to that model.
- Use only component props supported by the Ignition 8.1 component schema or a Designer-created seed.
- Prefer Designer-created component seeds for fragile Perspective JSON. Copy the smallest proven component shape, then parameterize tag roots, params, bindings, styles, images, and labels for the target project.
- Do not treat seed JSON as a full schema or substitute near-match component types; if no exact seed exists, use Ignition 8.1 docs or request/export a better seed.

## Package Rules

Read the package contract when assembling the artifact. Preserve the trusted export metadata, package the declared resources, and separate Gateway prerequisites from project resources. Keep scope changes and install conflicts explicit.

## Validation

Offline validation must confirm:

- Zip root and resource folders match Ignition project export shape.
- JSON parses structurally before and after writes; never patch page-config JSON with blind string replacement.
- `resource.json` files are preserved from trusted seeds or exports.
- Every packaged managed `resource.json.files` list matches the actual final managed files in that resource folder.
- Page config routes use `viewPath`, not `view`, and point only to packaged views.
- Every embedded/dynamic child view and Project Library script needed by the routed view is packaged or explicitly listed as an external dependency.
- Bindings/scripts/transforms use valid 8.1 structures.
- No instance-specific secrets or local identifiers leak.

Do not treat HTTP 200 from the Perspective client shell as render validation. A live acceptance test must confirm the route maps to the intended view and visible page markers/components render. When a package changes project-level Perspective page config, Designer startup/open is also validation; a malformed route can leave browser runtime alive while Designer fails.

For offline work, runtime/browser/Designer instructions throughout the references define the relevant handoff checks. Execute them only with an available, authorized target; otherwise record them as pending in `VALIDATION.md` and deliver the package. Existing structural, dependency, portability, and honest-evidence requirements still apply. Once necessary offline checks pass, finish the requested deliverable.
