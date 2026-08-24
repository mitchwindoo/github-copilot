# Project Discovery Patterns

Use this reference with `ignition-perspective-host-builder` when a task needs live project/resource discovery, Designer-created component seeds, style/theme/image discovery, Named Query discovery or preview, or allowlisted `viewRead` before authoring or overwriting Perspective resources.

## Contents

- Gateway diagnostics, routes, and views
- Style and reusable resource discovery
- Component seed discovery
- Named Query discovery
- Allowlisted view reads and drift guards

## Gateway Diagnostics, Routes, And Views

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

On runner `0.3.98+`, `routePrefix`, `viewPrefix`, seed view prefixes, reusable view prefixes, style prefixes, Named Query prefixes, dependency prefixes, and project-resource prefixes use exact-or-child matching. Prefix `LLM Tests/A` allows `LLM Tests/A` and `LLM Tests/A/Child`, not sibling `LLM Tests/ABC`; `/llm-...` remains the documented default route namespace.

On runner `0.3.132+`, `health.features` includes `filesystemDiscoverySortBeforeCap`. Capped filesystem-backed discovery such as `styleResourcesList`, `seedViewsList`, `namedQueriesList`, `projectsList`, and `projectResourcesList` sorts eligible candidates by the public response path/name before applying `maxResults`. On older runners, do not rely on truncated subset ordering; narrow prefixes or increase caps before choosing from capped discovery results.

## Style And Reusable Resource Discovery

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

## Component Seed Discovery

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
For View Canvas pages, prefer exact seeds for `ia.display.viewcanvas`; after apply, use `viewRead` to confirm `props.instances[].viewPath` and `viewParams` point at packaged child views and child input params, use `pageValidate` with all dependency views, and browser-click at least one instance to confirm `onInstanceClicked` selection updates parent/detail state.
For View Canvas command popups, require the package to include dependency child views, popup views, and command scripts; after apply, confirm one blocked interlock and one accepted writeback in-browser, then verify the final command/readback tags with `tagRead`.
For UDT-parameter-backed symbol pages, read and write copied instance parameter paths such as `[<tagProvider>]<folder>/<Instance>/Parameters.SymbolVariant`; verify the copied parameter path and dependent member/expression paths with `tagRead`. Normalize `"0"`/`"1"` and numeric strings before using those parameter values as symbol Boolean/numeric props.
For chart components such as Time Series Chart, prefer exact `componentSeedRead` shapes or minimal seed-style `props.series[].data`. For custom Time Series plots, verify `props.plots[].trends[].columns` is an object array with `key` values matching series data fields. Treat browser console property errors after a passing `pageValidate` as real component-schema failures; visual confirmation should confirm rendered SVG/canvas marks. Ignore only unrelated static asset noise such as Ignition favicon 404s.

## Named Query Discovery

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

Use returned `columns` and `rows` as a capped sample for Perspective table/KPI design. Do not execute update/action queries through preview. Do not pass QueryString/Database parameters unless a separate user-approved workflow validates them. For runner `0.3.54+`, QueryString previews require `allowQueryStringParameters: true` plus `queryStringParameterAllowlist`; Database previews require `allowDatabaseParameters: true` plus `databaseParameterAllowlist`. Exact rejected/bad values should fail before execution, and Java-backed execution failures should return a JSON error envelope instead of HTTP 500. If preview rejects an unbounded or over-broad query, add a small numeric top-level DB-side `LIMIT`/`TOP`/`FETCH` within the preview cap or enable a safe max return size before using it as a dashboard source. On runner `0.3.96+`, inspect `previewSafety.backendBounded`, `previewSafety.backendBoundSource`, `previewSafety.backendRowLimit`, and `previewSafety.responseMaxRows`; the backend row limit must be no larger than request `maxRows`. On runner `0.3.99+`, nested subquery or CTE row limiters do not count as the final Named Query row bound.
For Perspective query bindings, keep each component property value wrapped as `{"binding": {...}}` under `propConfig`; include query params under `binding.config.parameters`; validate missing params with `namedQueryPreview`; then confirm the live page in-browser because `pageValidate` does not execute bindings.

## Allowlisted View Reads And Drift Guards

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

Use the returned `viewSha256` before overwriting an existing view. For overwrite dry-run/apply, set `allowOverwrite: true`, set `requireViewSha256ForOverwrite: true`, and pass the current hash in `expectedViewSha256ByViewPath`. A missing, wrong, or stale hash is a stop condition and should fail during dry-run before writing. After a successful apply, immediately `viewRead` again; future overwrites must use the new hash, not the pre-apply hash. Do not request views outside the approved exact-or-child prefix.
