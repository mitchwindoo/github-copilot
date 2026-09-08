# Component Layout And Visuals

Read the matching section while authoring the requested page. Preserve exact seed/schema rules and apply the relevant design defaults. Runtime/browser checks in these rules belong in `VALIDATION.md` when no authorized target is available; they do not block delivery after offline checks pass.

## Contents

- Process Symbols And Pipes
- Flex Layout And Readability
- State Styles And Animation

## Process Symbols And Pipes

- For built-in Perspective Symbols, start from an exact `ia.symbol.*` seed and bind only props present on that symbol. Use symbol-specific prop names: Pump variant is `props.variant`; Pump, Motor, and Sensor orientation use `props.orientation`; Valve orientation uses `props.valve` and flow direction uses `props.reverseFlow`; Vessel level/fill uses `props.value.value`, `props.value.capacity`, `props.value.displayValueAsPercent`, `props.displayFillLevel`, `props.liquidColor`, `props.liquidOpacity`, and `props.liquidWarningColor`. Bind nested label/value locations as `props.label.location` and `props.value.location`. Do not assume one symbol's prop exists on another.
- When binding UDT `Parameters.*` paths into Boolean/numeric symbol props such as Valve `props.reverseFlow`, Vessel `props.value.displayValueAsPercent`, or `props.value.capacity`, add script transforms that coerce `"0"`/`"1"` and numeric strings to real Booleans/numbers before the symbol consumes them.
- For reusable symbol faceplates that support multiple symbol types, do not try to dynamically swap the component `type`. Include exact fixed `ia.symbol.*` seed components and bind each symbol's `meta.visible` from `view.params.assetType` plus any live visible/enabled tag; drive state/orientation/value/color through normal bindings.
- For Perspective Pipes, author pipe definitions on the Coordinate Container `props.pipes` array and bind nested pipe `fill`, `stroke`, and `visible` properties. Pipes are not ordinary child components.
- Treat built-in symbol artwork as anatomy, not process topology. Set anatomy props such as `orientation`, `displayStand`, and `displayAgitator` explicitly from the exact seed or documentation, do not infer nozzles from stands or artwork, and define named overlay anchors for real process connections.
- In a process Coordinate Container, define equipment bounds and named connection anchors before authoring pipes. Derive every segment from those anchors, render pipes before equipment, and use only a small documented overlap under the symbol edge; do not run a process line through a symbol interior.

Build pipe geometry/order before attaching many state bindings when practical. If an authorized edit reorders/adds/removes pipes, retain a resource export and add a focused post-import check that bindings still target the intended equipment after reopening. Reports on 8.1.43–8.1.45 describe shifted assignments; no in-range fix was verified. This supplements the existing geometry check, not a reason to redesign unrelated piping. [Community pipe-binding reports](https://forum.inductiveautomation.com/t/bug-pipe-bindings-does-not-follow-the-pipe-if-the-z-order-of-pipes-is-changed/101896)

## Flex Layout And Readability

- Do not invent Perspective props from CSS/React/web examples. For Flex Container, do not use `props.gap`; use documented margins, padding, child basis, or child spacing instead.
- Do not create accidental scroll regions in fixed headers, nameplates, status banners, KPI tiles, or static labels. For Flex layouts, make child `position.basis`, padding, font size, and line-height fit within the parent height/width; reserve `overflow: auto` or `scroll` for intentionally scrollable tables, logs, lists, and detail panels.
- Format numeric tag readbacks with explicit precision and units before display; do not expose raw Float4 precision artifacts.
- Give long tag-path/readback labels enough width, wrapping, or a dedicated detail panel so bound text does not clip.
- For SCADA/operator pages, make the decision or next action the dominant first region; put KPI cards with units, targets, status, and quality/source context below it.
- For simple progress/fill bars, use a row Flex container with a fill child whose `position.basis` is bound through `propConfig` to a tag/property value transformed to a clamped percent string. Pair it with visible percent/quality text and a growable remainder child; bad, null, or non-numeric values should render an explicit fallback such as `0%`.
- Format numeric readbacks with explicit precision and units in transforms/scripts before display; raw Float4 values can expose binary precision artifacts.
- Long selected tag paths need stable width, wrapping, or a dedicated detail panel. Do not place bound long-path labels in narrow row siblings where text will clip.
- For operator decision screens, put the decision/next action in the first major region; show primary indicators with units, targets, status, and source/quality context before supporting detail.
- In a Flex Container, interpret `position.basis` on the parent's main axis: width in a row and height in a column. Give row action buttons an explicit horizontal basis and verify unwrapped text at the target viewport.
- For a growing row child that contains a Time Series Chart, set `grow: 1`, choose `shrink` deliberately, and prefer `basis: "0px"`; apply the same zero basis to intermediate growing wrappers. Browser-check bounding rectangles because package and structural validation cannot detect intrinsic flex overflow.
- For simple percent bars in Flex, use a row Flex container with a fill child and remainder child. Bind the fill child's `position.basis` to a clamped percent string such as `82%`; let the remainder child grow.

Keep nested views and layout wrappers purposeful. Use parameterized reuse without turning simple decoration into a hierarchy of live views. Large Designer opening time and browser render time are separate symptoms; no community object/session count is a universal limit. Build the requested operator information and put relevant viewport checks in the handoff. Do not start a capacity benchmark for an ordinary page. [Embedded View composition guidance](https://docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-embedded-view)

## State Styles And Animation

- Use discovered target style classes, reusable views, themes, and project images exactly; do not invent class names, image URLs, or reusable view paths.
- For enum-like string props such as Flex `props.direction`, bind valid option strings or transform numeric tag codes to strings before binding.
- For status styling, bind specific style subproperties through `propConfig` and map states to restrained semantic colors.
- If custom-styling a disabled button, put disabled opacity/background on an inspectable button or wrapper element, or leave the default disabled styling visible.
- For status-to-style bindings, bind concrete subproperties such as `props.style.backgroundColor` or `props.style.color` under `propConfig`; use map transforms from state values to semantic colors.
- For enum-like component props, bind valid option strings. If the source tag is numeric, add a transform that returns the documented string option before binding the prop.
- Treat enum-backed style properties as Perspective schema values, not merely browser-valid CSS. Serialize `style.fontWeight` as a supported string such as `"700"`, `"800"`, `"bold"`, or `"normal"`; recursively reject non-string or unsupported weights across every nested style object, and confirm serialized/live view types after repair.
- For reusable visual badges/cards, pass state through `view.params` and bind child text/style from params; the parent should pass simple instance objects, not duplicate style maps.
- Derive each route marker from the same named start/end anchors as its route segment. Across the full animation range, require its rendered bounds to stay in that corridor and outside equipment, nameplate, and label exclusions. If telemetry proves activity but not transit or direction, use a fixed directional cue with changing opacity; label medium and direction locally and browser-sample at least two frames to prove the intended visual change, corridor intersection, zero equipment overlap, and no duplicate marker.
- Reserve an obstacle-free lane for every animated overlay across its full travel envelope. Compare its swept bounding box against bars, labels, and reference lines at two or more frames. For text inside bars, set explicit `alignItems`, `justifyContent`, `textAlign`, and zero padding, then verify the rendered text center against the bar center at the target viewport.

When authoring stylesheet changes, keep CSS syntax valid and reuse the target's documented classes. If the first class appears ineffective, inspect syntax/applied rules before adding a disposable class: an 8.1.47 reporter resolved that symptom by removing an extra closing brace. Existing typed-style checks still apply; valid CSS is not proof of valid Perspective serialization. [User-confirmed stylesheet correction](https://forum.inductiveautomation.com/t/first-style-does-not-work/115377)
