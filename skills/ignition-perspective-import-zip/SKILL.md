---
name: ignition-perspective-import-zip
description: Create portable Ignition 8.1 Perspective project import zip packages. Use when Codex must author a correct Perspective view/page and deliver an importable project .zip/.proj package, install checklist, or dependency bundle for another Ignition instance. Do not use for direct same-PC Gateway/Web Dev/API/filesystem deployment; use ignition-perspective-host-builder for that.
---

# Ignition Perspective Import Zip

Skill version: `1.0.111`
Stack version: `starter-2026.07.06.04`

## Primary Output

Produce a portable Ignition 8.1 project import package, not a live Gateway change.
Keep package mechanics secondary to correct Perspective view/page authoring.

Required output:

- Project import `.zip` or `.proj` built from a valid Ignition 8.1 seed/export structure.
- `INSTALL.md` with import steps, dependencies, conflict policy, and placeholders.
- `VALIDATION.md` with smoke checks for import, route/view rendering, bindings, scripts, and logs.

Never require Gateway credentials, API access, Web Dev access, or filesystem write access for this skill.

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
9. Validate offline before delivery.

If only `view.json` is available and no trusted `resource.json`/seed exists, do not claim the result is importable. Provide Designer Copy JSON/Paste JSON steps or require a seed export.

## Perspective JSON Rules

Load `references/perspective-view-json-guardrails.md` before nontrivial `view.json` edits, bindings, scripts, transforms, embedded views, repeaters, or charts.

Core rules:

- Preserve Ignition 8.1 Perspective JSON shape: `custom`, `params`, `props`, `root`, `propConfig`, `events`, `permissions`.
- Keep dynamic bindings under `propConfig`, not under `props`.
- Put component bindings in that component's own `propConfig` with keys like `props.text`; do not use top-level `propConfig` keys like `root.children[0].props.text`.
- Use `view.params` for external inputs and `view.custom` for internal state.
- Prefer parameterized/reusable views over hard-coded per-device tag paths. Pass a base tag path, device id, provider, or folder root through `view.params`; build derived member paths in bindings/scripts.
- For multi-asset pages, browse/query a validated root folder at startup or in a Project Library script, filter to expected UDT instances/members, write rows/instances into `view.custom`, and bind tables/repeaters to that model.
- Use only component props supported by the Ignition 8.1 component schema or a Designer-created seed.
- Prefer Designer-created component seeds for fragile Perspective JSON. Copy the smallest proven component shape, then parameterize tag roots, params, bindings, styles, images, and labels for the target project.
- Do not treat seed JSON as a full schema or substitute near-match component types; if no exact seed exists, use Ignition 8.1 docs or request/export a better seed.
- For built-in Perspective Symbols, start from an exact `ia.symbol.*` seed and bind only props present on that symbol. Use symbol-specific prop names: Pump variant is `props.variant`; Pump, Motor, and Sensor orientation use `props.orientation`; Valve orientation uses `props.valve` and flow direction uses `props.reverseFlow`; Vessel level/fill uses `props.value.value`, `props.value.capacity`, `props.value.displayValueAsPercent`, `props.displayFillLevel`, `props.liquidColor`, `props.liquidOpacity`, and `props.liquidWarningColor`. Bind nested label/value locations as `props.label.location` and `props.value.location`. Do not assume one symbol's prop exists on another.
- When binding UDT `Parameters.*` paths into Boolean/numeric symbol props such as Valve `props.reverseFlow`, Vessel `props.value.displayValueAsPercent`, or `props.value.capacity`, add script transforms that coerce `"0"`/`"1"` and numeric strings to real Booleans/numbers before the symbol consumes them.
- For reusable symbol faceplates that support multiple symbol types, do not try to dynamically swap the component `type`. Include exact fixed `ia.symbol.*` seed components and bind each symbol's `meta.visible` from `view.params.assetType` plus any live visible/enabled tag; drive state/orientation/value/color through normal bindings.
- When an embedded faceplate changes `baseTagPath` params, avoid using one indirectly bound `view.custom` tag value inside other tag-binding transforms for critical display. Bind each displayed field directly from the current `{base}/Member` path or pass stable values through params.
- For Perspective Pipes, author pipe definitions on the Coordinate Container `props.pipes` array and bind nested pipe `fill`, `stroke`, and `visible` properties. Pipes are not ordinary child components.
- Do not invent Perspective props from CSS/React/web examples. For Flex Container, do not use `props.gap`; use documented margins, padding, child basis, or child spacing instead.
- Do not create accidental scroll regions in fixed headers, nameplates, status banners, KPI tiles, or static labels. For Flex layouts, make child `position.basis`, padding, font size, and line-height fit within the parent height/width; reserve `overflow: auto` or `scroll` for intentionally scrollable tables, logs, lists, and detail panels.
- Use discovered target style classes, reusable views, themes, and project images exactly; do not invent class names, image URLs, or reusable view paths.
- Treat target-only styles, reusable views, and images as prerequisites unless the package includes those resources. Do not use Perspective view thumbnails as general app images. When later applying through the host runner, list only packaged child/dependency views in `dependencyViewPaths`; already-existing target reusable views should be discovered and documented as prerequisites unless the package ships them.
- For enum-like string props such as Flex `props.direction`, bind valid option strings or transform numeric tag codes to strings before binding.
- Keep Jython scripts/transforms Python 2.7-compatible; use transform `code`, preserve Ignition's stored indentation, and avoid Python 3 syntax such as f-strings.
- Use arrays of objects for mixed Perspective table data unless a component requires a dataset.
- For database-backed tables/KPIs, prefer Perspective Named Query bindings over inline SQL. Put the binding under the table/component `propConfig`, for example `propConfig["props.data"].binding.type = "query"` with `config.queryPath`.
- Keep the outer `binding` wrapper for every bound property. A KPI label must use `propConfig["props.text"] = {"binding": {...}}`, not a bare query binding object at `propConfig["props.text"]`.
- Put static or property-derived Named Query parameters in `binding.config.parameters`, and design explicit empty/zero-row text instead of indexing row 0.
- Build table columns/KPI fields from discovered Named Query metadata or a capped preview result. Do not guess result field names from SQL table names.
- Treat preview rows as seed/sample data only; the live Perspective binding owns runtime data. Keep the query DB-side bounded for design previews.
- Avoid QueryString and Database Named Query params in portable packages unless the target workflow explicitly supplies allowlists. QueryString is for vetted SQL identifiers/fragments only; Database params require target-approved connection names and live validation. Do not assume a package-copied `<Parameter>` database setting will execute dynamically without target validation.
- Put view startup scripts under top-level `events.system.onStartup`; do not use `scripts.extensionFunctions` for view startup.
- Keep startup/event scripts as valid Jython function bodies; preserve indentation and compile/lint them before apply when tooling exists.
- Give every Perspective script action object an explicit `scope`, usually `"G"` for gateway execution; a missing/null scope can pass structural checks but break Perspective project serialization.
- When a Perspective event script updates another component with `self.getSibling("<Name>")`, the target must share the same immediate parent as the scripted component. Put status/readback labels in the same container, deliberately navigate the parent/root hierarchy, or bind labels from `view.custom`; browser-test visible text after clicks.
- Treat Flex Repeater `props.instances` as the parent-to-child API; each instance passes child view params as top-level keys matching child `view.params`. Use `instanceStyle` and `instancePosition` only as reserved styling/layout siblings; do not put child params under `viewParams` for Flex Repeater, or the child can render defaults/nulls.
- For dynamic Flex Repeater lists, let one parent view/script build JSON-simple instance objects in `view.custom.<instances>` and bind the repeater's `props.instances` to that property. Declare the child params with top-level `params` defaults and `propConfig["params.<name>"].paramDirection = "input"`, then browser-verify that no default-param text leaks.
- For View Canvas reusable templates, start from an exact `ia.display.viewcanvas` seed. Each `props.instances[]` item should set a child `viewPath` plus `viewParams` keys matching the child `view.params`; include every faceplate/detail child view in the package and dependency list.
- For View Canvas instance-to-detail selection, keep parent selection in `view.custom`; use `onInstanceClicked` to copy the selected instance's `viewParams`, then bind an embedded detail view's `props.params.*` from parent state.
- For View Canvas command popups opened from embedded detail views, pass selected context into the child through `props.params`; scripts inside that child read `self.view.params.*`, not parent `view.custom`.
- For table/list-to-detail selection, keep selected item state on the parent/root view and update it through one page-scoped message handler; list/card actions and table selection can send the same row payload with `system.perspective.sendMessage(..., scope="page")`.
- For Perspective component message handlers, put handlers under the component/root `scripts.messageHandlers` array with `messageType`, `pageScope`, `viewScope`, and `sessionScope` booleans. The `system.perspective.sendMessage(..., scope="page"|"view"|"session")` scope must match a listening flag; wrong-scope sends can be silent, so prove behavior with visible state or durable tags. Component handler `sessionScope` is separate from Perspective Session Event Scripts, which are reached through `system.util.sendMessage`/`sendRequest`.
- Do not claim a portable package creates Project Gateway Event Script handlers or Perspective Session Event handlers unless it starts from a trusted Designer export and clean import validation confirms them. Prefer component message handlers for API-built views and document any Gateway/Session handler as a target prerequisite.
- For Perspective custom methods, put methods under component/root `scripts.customMethods` with `name`, `params`, and indented function-body `script`. Keep calls within the same exact component hierarchy, such as same-component `self.methodName(...)`, same-parent sibling `self.getSibling("<Component Name>").methodName(...)`, or child-to-parent `self.parent.methodName(...)`. Do not use custom methods across embedded/different views; pass params or send messages instead. Catch and surface missing-method errors during validation because they can appear only at runtime.
- For table-to-detail selection, bind table rows as arrays of objects, set explicit row selection, and read `self.props.selection.data[0]` from `events.component.onSelectionChange` into parent selection state. Declare every helper field needed by detail/action logic as a visible or hidden table column; undeclared row keys can be absent from the selection payload.
- For page-to-page detail navigation, mount routes with dynamic segments such as `/detail/:deviceId`, declare `params.deviceId` as an input on the primary view, and navigate with the concrete page URL such as `system.perspective.navigate('/detail/Pump001')`; the `params` dictionary is for `view=` navigation, not `page` navigation.
- For route-param command/detail pages, compute the selected base tag path from `view.params`, pass it into embedded faceplate and popup params, and show live readback/result state on the detail page after the popup returns.
- For route-param alarm/history detail pages, bind Alarm Status Table `props.filters.active.conditions.displayPath` and Alarm Journal Table `props.filter.conditions.displayPath` from the route param; keep current status, journal history, and history/fallback panels visibly separate.
- For shared docked navigation/status shells, put common dock definitions under top-level Perspective page-config `sharedDocks`, not inside a routed view. Each shared dock edge should reference a packaged dock view with `viewPath`, stable `id`, sizing/display settings, and `viewParams` for shared context. Page-specific route `docks` are different and should be used only for one page.
- For runtime-controlled shared docks, give every dock a stable `id`. Use `show: "onDemand"` plus `handle: "show"` for handle-opened panels, `modal: true` only when overlay blocking is intended, and `show: "auto"` plus `autoBreakpoint` for responsive collapse. Browser-test real handle clicks, `openDock`/`closeDock`/`toggleDock`, modal blocking, and wide/narrow breakpoint behavior.
- For operator summary tables, include visible fields plus hidden stable fields such as base tag path, next action, and severity rank in each row object; hide helper columns and use them for selection/detail logic.
- For filtered operator overviews, drive attention cue, filters, KPI counts, rows, selected detail, and chart state from one model; sort abnormal/high-severity assets first and default selection to the highest-priority row.
- For table/list command popups, parent owns selected path/state, passes selected path and expected prefix into popup params, popup calls a packaged Project Library script, then returns a page-scoped result to the parent.
- Tables populated into `view.custom` from startup browse/read are snapshots; after writeback, refresh affected rows or reload table data so tables do not contradict live-bound detail/faceplate readbacks.
- For Tag Browse Tree pages, start from an exact `ia.display.tag-browse-tree` seed, set `props.root.path` to a validated root, keep `props.selection.mode` explicit, and bind sibling detail labels from `../Tag Browse Tree.props.selection.values`. Use `onNodeClick` `event.path`/`event.name` when the page needs clicked-node side effects or tag reads; handle folder reads as bad/unsupported.
- Use `ia.display.alarmstatustable` for real Ignition tag alarms, not custom alarm-like row data; scope it with provider/source/displayPath filters so unrelated site alarms do not appear.
- For UDT-backed alarm rollups, build area counts from runtime alarm reads and filtered current alarm rows, then pass selected area/count/assets/filter values into a reusable alarm detail view through `props.params`.
- Use `ia.display.alarmjournaltable` for historical alarm transition rows only when an Alarm Journal/profile is configured; its props use singular `filter.conditions` plus `dateRange`, unlike Alarm Status Table `filters.active.conditions`. Preserve/discover the exact component `props.name` journal profile from a seed or target Gateway; do not guess `"Journal"`. Keep current status, journal history, and sampled/current-value fallbacks visually separate.
- For status styling, bind specific style subproperties through `propConfig` and map states to restrained semantic colors.
- Format numeric tag readbacks with explicit precision and units before display; do not expose raw Float4 precision artifacts.
- Give long tag-path/readback labels enough width, wrapping, or a dedicated detail panel so bound text does not clip.
- For SCADA/operator pages, make the decision or next action the dominant first region; put KPI cards with units, targets, status, and quality/source context below it.
- For simple progress/fill bars, use a row Flex container with a fill child whose `position.basis` is bound through `propConfig` to a tag/property value transformed to a clamped percent string. Pair it with visible percent/quality text and a growable remainder child; bad, null, or non-numeric values should render an explicit fallback such as `0%`.
- For reusable visual badges/cards, pass state through `view.params`; keep display mapping inside the child view.
- For popup/embedded views, declare child inputs as plain top-level `params` values plus `propConfig["params.<name>"].paramDirection = "input"` before binding visible components to `view.params.<name>`; do not use typed `{"type","value"}` param objects unless an exact Designer seed proves that shape.
- For tree/table-driven reusable UDT faceplates, pass the selected instance path into `ia.display.view.props.params.<basePathParam>` and include the child view in `dependencyViewPaths`.
- For UDT-backed pages, bind to UDT instance/member paths. Do not bind to UDT definition paths under `[<tagProvider>]_types_`.
- For UDT-backed Perspective rows/bindings, preserve the difference between `None`, empty string, and literal `"null"` parameter values; omit an override to inherit defaults, guard numeric null before math, and avoid quoted `{ParamName}` placeholders that can remain literal.
- For shell/tab patterns, bind `ia.display.view.props.path` from `view.custom.<activeViewPath>`, bind shared context through `props.params.<name>` into child `view.params`, and include every possible child view in `dependencyViewPaths`; dynamic Embedded View paths are not inferred just because child views are present in the package.
- For indirect tag bindings, use string references such as `"base": "{view.params.baseTagPath}"`; do not use object-shaped references.
- For indirect tag bindings, set `config.mode: "indirect"` and prefer a small `fallbackDelay`; references without indirect mode can resolve as bad/null while the page shell still renders.
- When an indirect tag path combines a fixed root with a route/page param segment, keep the fixed root literal in `tagPath` and reference only the dynamic segment, for example `"<root>/{device}/PV"` with `"device": "{view.params.deviceId}"`. Declare the route param as an input `view.params` entry and browser-test at least two concrete URLs.
- Relative property binding paths are scoped from the component that owns the `propConfig`; after wrapping/nesting components, adjust `../` depth or centralize selection in `view.custom`.
- Use `{value}` only inside binding transforms; plain expression bindings must reference explicit properties/tags.
- For writeback controls, prefer a Project Library script for real work; keep Perspective event scripts thin, call the exact project script path, check every write quality in the project script, and show live readback/status.
- For audited/operator button workflows, put the event under `events.component.onActionPerformed`, give the component a stable key such as `custom.auditKey`, call one packaged Project Library logging helper, and validate with browser clicks plus audit/log/SQL/tag readback instead of relying on `pageValidate`.
- For audited action logging beyond standard Button, use exact seeds where possible for Button, One-Shot Button, Multi-State Button, Checkbox, and Dropdown `onActionPerformed` workflows. Pass component-specific values from `self.props` or explicit wrapper hints; do not assume the event object carries the selected/control value.
- In Project Library writeback scripts, validate allowed tag prefix, missing/bad dependencies, interlock/enable state, write quality, and verification reads before returning success.
- For dependency-gated commands, calculate dependency rows/summary into `view.custom`, show missing/bad required tags before enabling controls, and bind `props.enabled` from the validated boolean. Treat disabled UI state as operator feedback only; re-read dependencies/interlocks in the Project Library script before every write and return a clear blocked outcome.
- If custom-styling a disabled button, put disabled opacity/background on an inspectable button or wrapper element, or leave the default disabled styling visible.
- For embedded/reusable views, pass inputs through `props.params` into child `view.params`; include every referenced view in the package.
- Verify historian/trend behavior separately from tag browse/value existence; if no non-null history rows are available, label sampled/current-value chart data as a fallback.
- For Time Series Chart, prefer an exact seed or minimal seed-style `props.series[].data` shape. For custom plots, use `props.plots[].trends[].columns` as objects such as `{ "key": "PV" }`, with each `key` matching a field in `props.series[].data`; do not use plain strings. Browser-test for rendered chart SVG/canvas marks and chart runtime errors.

## Package Rules

Load `references/package-contract.md` only when building the zip structure, dependency bundle, install order, or validation checklist.

- Project export zips can include project resources such as Perspective views/properties, project scripts, named queries, reports, SFCs, Transaction Groups, Gateway Event Scripts, and Vision resources.
- Named Query resources live under `ignition/named-query/<queryPath>/` with `resource.json` and usually `query.sql`; include those files when the package must be portable. Preserve Named Query `resource.json` attributes because they hold query type, database, enabled state, file list, and parameter metadata.
- Project export zips do not include Gateway-level configuration or tag providers/tags.
- Project root must include `project.json`; missing it means the package is not a valid project import zip.
- Perspective page-config routes must map pages with a non-empty string `viewPath`, never `view`; reject missing/null/empty `viewPath` and confirm the target view is packaged.
- Perspective shared docked views live in top-level page-config `sharedDocks` keys such as `top`, `bottom`, `left`, `right`, and `cornerPriority`; include every referenced dock view in the package and tell host/API validation which keys should be merged.
- Project Library scripts live under `ignition/script-python/<scriptPath>/code.py` with a sibling `resource.json`; include only `code.py` and `resource.json` in that resource folder.
- Each managed resource's `resource.json.files` list must match the final sibling data files in that resource folder. When the host runner `0.3.140+` imports with `projectResourceImportZip`, it overlays package entries onto the current target state and rejects missing listed files or unlisted managed files with `RESOURCE_MANIFEST_INVALID` and `manifestValidationPhase:"finalMergedResourceState"` before writes. When runner `0.3.142+` performs normal package `apply`, overwriting a Perspective view whose final manifest omits optional files such as `thumbnail.png` prunes those stale target files and reports `prunedStaleViewFiles` / `prunedStaleViewFileCount`.
- If a routed view embeds child views or calls Project Library scripts, include those dependency resources in the package and list them in validation notes.
- If a routed view references already-existing target reusable views, style classes, themes, or images that are not in the package, list them as prerequisites and verify their exact names during host discovery; do not make the zip appear self-contained.
- If a routed view references existing style classes, images, themes, or reusable views from the target project, include those resources in the package or list them as prerequisites with placeholders.
- If a routed view references existing Named Queries, include the Named Query resources or list `<namedQueryPath>` and `<databaseConnection>` as prerequisites. For host/API validation, list packaged queries in `dependencyNamedQueryPaths` so the runner can validate, copy, back up, and page-validate them.
- QueryString/Database Named Query dependencies are unsafe by default in host validation. If a package intentionally includes them, document the exact QueryString fragment allowlist or Database connection allowlist. Treat Database `<Parameter>` execution as target-specific until live validation confirms the intended connection is selected; do not rely on package metadata alone.
- Put tag exports under a dependency folder and instruct import through Designer Tag Browser. Import UDT definitions before UDT instances.
- Keep UDT definitions and UDT instances as tag dependencies outside the project export zip; document provider placeholders and import definitions before instances.
- Document required modules, database connections, tag providers, OPC/MQTT providers, certificates, and security roles as prerequisites.
- Write generated JSON files as UTF-8 without BOM.
- For package scope, omit unrelated resources from the new package instead of deleting them from a source project.

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

## Ignition 8.1 Docs

Use Ignition 8.1 docs unless the user requests another version:

- Project export/import: https://www.docs.inductiveautomation.com/docs/8.1/platform/projects/project-export-and-import
- `resource.json`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/resource-json-file
- Tag export/import: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/exporting-and-importing-tags
- Perspective module: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective
- Perspective Docked Views: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/views-in-perspective/docked-views
- Perspective View Canvas: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-view-canvas
- Perspective Embedded View: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-embedded-view
- Perspective Popup Views: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/views-in-perspective/popup-views
- Perspective Component Message Handlers: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/component-message-handlers
- Perspective Component Methods: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/perspective-component-methods
- Perspective Session Event Scripts: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/perspective-session-events-scripts
- Perspective Pipes: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/perspective-pipes
- Perspective Alarm Status Table: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-display-palette/perspective-alarm-status-table
- Perspective Alarm Journal Table: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-display-palette/perspective-alarm-journal-table
- Perspective Time Series Chart: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-chart-palette/perspective-time-series-chart
- Perspective Pump Symbol: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-symbols-palette/perspective-pump
- Perspective Valve Symbol: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-symbols-palette/perspective-valve
- Perspective Vessel Symbol: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-symbols-palette/perspective-vessel
- Perspective Motor Symbol: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-symbols-palette/perspective-motor
- Perspective Sensor Symbol: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-symbols-palette/perspective-sensor
- Perspective event types: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/perspective-event-types-reference
- `system.perspective.navigate`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-navigate
- `system.perspective.openDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-openDock
- `system.perspective.closeDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-closeDock
- `system.perspective.toggleDock`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-toggleDock
- `system.perspective.openPopup`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-openPopup
- `system.perspective.closePopup`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-closePopup
- `system.perspective.sendMessage`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-sendMessage
- Perspective pages and URL params: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/pages-in-perspective
- Flex Container: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-container-palette/perspective-flex-container
- Style Reference: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/style-reference
- Named Queries: https://www.docs.inductiveautomation.com/docs/8.1/platform/sql-in-ignition/named-queries
