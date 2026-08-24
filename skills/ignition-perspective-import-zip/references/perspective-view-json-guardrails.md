# Perspective View JSON Guardrails

## Contents

- Scope
- Structure
- Bindings
- Scripts And Transforms
- Perspective Design Patterns
- Common Failure Patterns
- Smoke Test

## Scope

These rules target Ignition 8.1.x Perspective `view.json`, especially 8.1.48 style exports. Treat `view.json` as a private serialization format with no complete public schema.

## Structure

- Preserve existing top-level keys such as `custom`, `params`, `props`, `root`, `propConfig`, `events`, and `permissions`.
- The component tree starts at `root`; children are usually under `root.children`.
- Components commonly contain `type`, `meta`, `props`, `position`, `custom`, `propConfig`, `events`, and `children`.
- Do not rewrite the whole file for small changes. Patch the smallest relevant object.

## Bindings

- Dynamic values belong in `propConfig`, not directly in `props`.
- Do not place binding objects inside component property values such as `props.text`; Perspective may render the binding JSON as text instead of evaluating it.
- `propConfig` keys are property paths such as `props.text`, `props.options`, `custom.summary`, or `position.basis`.
- `propConfig` is scoped to the object that owns it. For a child component, put `propConfig` inside that component and use keys like `props.text`; do not put `root.children[...]` paths in top-level view `propConfig`.
- Binding objects keep `binding.type`, `binding.config`, and optional `binding.transforms`.
- Direct tag bindings use `binding.config.tagPath`, not `binding.config.path`.
- `{value}` exists inside transforms, not in arbitrary expression bindings. A plain expression binding that uses `{value}` can render blank/incomplete text instead of failing loudly.
- For indirect tag bindings in 8.1, keep reference values as simple strings. Object-shaped references can render plausible wrong values such as `0.0` instead of failing loudly. Example:

```json
"references": {
  "basePath": "{view.custom.diagnosticsBasePath}"
}
```

## Scripts And Transforms

- Perspective scripts run as Jython/Python 2.7 in Ignition 8.1.
- Do not use f-strings, type hints, async/await, match/case, walrus, or Python 3-only libraries.
- Script actions normally store code under `config.script`; script transforms normally store code under `code`.
- Script action objects should include an explicit `scope`, usually `"G"`; a missing/null scope can break Perspective project serialization even when route wiring validates.
- Preserve stored indentation exactly. Many exported scripts include leading tabs because Ignition wraps code inside generated functions.
- If editing script text, mentally validate it as a function body. Top-level `return` is normal in transform context but invalid in a bare Python file.
- Use Jython 2.7-compatible formatting such as `%` or `str.format`; f-strings can render `null` in Perspective script transforms instead of failing loudly.
- Compile/lint generated startup, event, and transform script bodies when tooling exists; malformed indentation can leave the page shell rendered while `view.custom` data never loads.

## Perspective Design Patterns

- Use `view.params` for external inputs to a view or embedded view.
- Use `view.custom` for internal runtime state owned by the view.
- View startup scripts belong under top-level `events.system.onStartup` with `type`, `scope`, and `config.script`; `scripts.extensionFunctions` is not the view startup event shape.
- Use `ia.display.view` for embedded views. Set `props.path` to the child view path and `props.params` to values passed into the child.
- Declare popup/child view inputs as plain top-level `params` values; mark `propConfig["params.<name>"]` with `paramDirection: "input"` when those params are passed in or bound to visible properties. Avoid typed `{"type","value"}` view-param objects unless an exact Designer seed confirms that shape.
- Bind parent values into embedded-view params through `propConfig["props.params.<name>"].binding` when the value comes from parent `view.params` or another dynamic source.
- For reusable UDT faceplates, pass one base tag path param and use indirect tag bindings such as `tagPath: "{base}/PV"` with `mode: "indirect"`, `fallbackDelay`, and `references.base: "{view.params.<baseParam>}"`. References without `mode: "indirect"` can render bad/null values while the page shell still opens.
- For UDT-backed rows/bindings, preserve null, empty string, and literal `"null"` parameter values distinctly; omit overrides for defaults, guard numeric null, and avoid quoted `{ParamName}` placeholders that can stay literal.
- If only one segment of an indirect tag path is dynamic, keep the fixed root literal in `tagPath` and reference only the dynamic segment, such as `tagPath: "[provider]Area/Equipment/{device}/PV"` with `references.device: "{view.params.deviceId}"`. Do not move a static root into `references`; it can resolve to `None`.
- For tree/table-driven reusable UDT faceplates, bind the selected instance path into `ia.display.view.props.params.<basePathParam>` and package the child view as a dependency.
- Relative property binding paths are evaluated from the component that owns the `propConfig`. If a bound label moves into a wrapper panel, update `../` depth or bind through `view.custom` instead.
- Treat Flex Repeater as an API: `props.path` points to the child view, `props.instances` is an array of objects, and each instance key should match a child view param. Unknown instance keys are not passed to the child and can leave default/null child param values visible.
- For dynamic repeaters, put browse/query/merge logic in one parent view startup script or project script; write the resulting array to `view.custom.<instances>` and bind `propConfig["props.instances"]` to that custom property.
- For child-to-parent list/table selection, put a `scripts.messageHandlers` entry on the parent/root component with `pageScope: true`; child buttons and table selection scripts can call `system.perspective.sendMessage("<messageType>", payload=payload, scope="page")` with the same row payload.
- Perspective component message handlers live under component/root `scripts.messageHandlers` with `messageType` plus `pageScope`, `viewScope`, and `sessionScope` booleans. The send scope must match a listening flag; wrong-scope sends may be silent, so validate with visible state or tags. Component `sessionScope` is not a Project Session Event Script handler.
- Do not author Project Gateway Event Script handlers or Perspective Session Event handlers from guessed `data.bin` shapes. Treat them as target prerequisites unless a Designer-exported fixture and clean import/API confirmation exist.
- Perspective component custom methods live under `scripts.customMethods` with `name`, `params`, and an indented function-body `script`. Verified same-view calls are `self.methodName(...)`, same-parent `self.getSibling("<Component Name>").methodName(...)`, and child-to-parent `self.parent.methodName(...)`; do not use this pattern across embedded/different views.
- For selected-detail layouts, bind the embedded detail view's `props.params.<name>` from parent `view.custom` selection state.
- For table-to-detail layouts, bind `props.data` to an array of objects and use `events.component.onSelectionChange` to read `self.props.selection.data[0]` into parent `view.custom` state. If detail/action logic needs helper fields such as asset type, base tag path, next action, or severity rank, declare those fields as hidden non-editable table columns; undeclared row keys can be missing from the table selection payload.
- For page-to-page detail layouts, mount the detail page with dynamic URL segments such as `/detail/:deviceId`; declare `params.deviceId` as an input on the primary view, then navigate with the concrete page path. `system.perspective.navigate(page)` does not pass the `params` dictionary into page params.
- For route-param command/detail pages, compute the selected base tag path from the route param in the detail view, pass that path into the embedded faceplate and popup params, and let a page-scoped popup result update result/status state while live tag bindings verify readback.
- For operator summary tables, keep visible columns and hidden helper fields in the same row object. Hide helper columns such as base tag path, next action, and severity rank, then use them to drive detail panels and action context.
- For filtered operator overview screens, calculate attention cue, filter counts, table rows, selected detail, and chart input from one shared model. Sort abnormal/high-severity assets first and set default selection from that sorted list.
- For table/list command popups, parent owns selected path/state, passes selected path and expected prefix through popup params, popup calls a packaged Project Library script, then sends a page-scoped result back to the parent.
- Startup-built table rows in `view.custom` are snapshots. If a popup/script writes tags, refresh the affected row or reload table data after the result so the table does not contradict live-bound detail components.
- For Tag Browse Tree pages, start from an exact `ia.display.tag-browse-tree` seed, set `props.root.path` to a validated provider/root, keep `props.selection.mode` explicit, and bind sibling detail/readback components from `../Tag Browse Tree.props.selection.values`. Use `onNodeClick` `event.path`/`event.name` for clicked-node side effects or tag reads; folder paths can read as bad/unsupported.
- Built-in `ia.display.alarmstatustable` reads Gateway alarm events. Back it with configured tag alarms and set `props.filters.active.conditions` such as `displayPath`, `source`, or `provider`; otherwise unrelated active alarms can appear.
- For UDT-backed alarm rollup pages, verify the row model against runtime alarm reads and filtered `alarmStatusQuery` counts, then pass selected area/count/assets/filter values into reusable detail views through `props.params`.
- For status-to-style bindings, bind concrete subproperties such as `props.style.backgroundColor` or `props.style.color` under `propConfig`; use map transforms from state values to semantic colors.
- For enum-like component props, bind valid option strings. If the source tag is numeric, add a transform that returns the documented string option before binding the prop.
- Format numeric readbacks with explicit precision and units in transforms/scripts before display; raw Float4 values can expose binary precision artifacts.
- Long selected tag paths need stable width, wrapping, or a dedicated detail panel. Do not place bound long-path labels in narrow row siblings where text will clip.
- For operator decision screens, put the decision/next action in the first major region; show primary indicators with units, targets, status, and source/quality context before supporting detail.
- For simple percent bars in Flex, use a row Flex container with a fill child and remainder child. Bind the fill child's `position.basis` to a clamped percent string such as `82%`; let the remainder child grow.
- For reusable visual badges/cards, pass state through `view.params` and bind child text/style from params; the parent should pass simple instance objects, not duplicate style maps.
- For shell/tab patterns, one `ia.display.view` can bind `props.path` from parent `view.custom.<activeViewPath>`. Store the active child view path in parent state, bind shared context through `props.params.<name>` into declared child `view.params`, and package/list every possible child view because dynamic paths are not discoverable from a static route alone.
- For command/writeback buttons, prefer a thin Project Library script call such as `<scriptPath>.<function>(...)`; keep the project script packaged under `ignition/script-python/<scriptPath>/code.py`, validate allowed prefix/interlock state, use `system.tag.writeBlocking(paths, values)`, loop every returned quality with `.isGood()`, verify readback before returning success, and update visible readback/status.
- For dependency-gated commands, build dependency rows/summary in `view.custom`, display bad/missing required tags in a wide detail area, bind button `props.enabled` from the same validated boolean, and re-check dependencies inside the Project Library script before writes. If custom button colors are used, bind disabled color/opacity too.
- For trend panels, confirm historian availability separately from current tag reads. If history queries return only null/no rows, label the chart as sampled/current-value fallback data.
- For Time Series Chart custom plots, `props.plots[].trends[].columns` should be an array of objects such as `{ "key": "PV" }`; each key must match a field in `props.series[].data`. Plain string columns are a known bad shape. Browser confirmation should show rendered SVG/canvas marks and no relevant chart runtime errors.
- Heavy discovery, browse, and merge logic belongs in one parent/list view or project script, not inside every repeated card.
- For heterogeneous table data, prefer Perspective arrays of objects. If a dataset is required, keep each column one datatype.

## Common Failure Patterns

- Rebuilding a partial view and accidentally omitting `root.children`.
- Putting binding config under `props`.
- Putting child-component binding keys such as `root.children[0].props.text` in top-level view `propConfig`; this can prevent Gateway from deserializing the view.
- Serializing indirect tag references as objects when 8.1 expects strings.
- Using `{view.custom.path}/Something` directly in an indirect tag binding instead of a placeholder plus reference mapping.
- Using `system.perspective.navigate(page=..., params={...})` and expecting page params to change; page params come from mounted URL segments.
- Putting a fixed tag root in indirect binding `references` instead of leaving it literal in `tagPath`.
- Adding Python 3 syntax to Jython script actions.
- Removing leading tabs from script transforms.
- Adding extra indentation to a top-level view startup script; the page can open but the startup data load can silently fail.
- Concatenating generated script lines so a helper `def` and the next statement land on one physical line.
- Letting local syntax checks create `__pycache__` inside packaged Project Library script resources; package only `code.py` and `resource.json`.
- Hardcoding provider names without checking provider existence, causing Gateway log spam.
- Putting browse-heavy logic on a fast `now(1000)` or repeated-card binding.

## Smoke Test

- JSON parses.
- View opens in Designer.
- Bindings show expected preview values.
- Script actions execute without parse errors.
- All critical rows/components still exist after refactors.
- Page loads in a Perspective session.
- Gateway logs are clean after a full refresh.
