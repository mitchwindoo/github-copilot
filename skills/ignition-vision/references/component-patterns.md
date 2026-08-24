# Vision Component And Screen Patterns

## Contents

- [Layout and coordinate rules](#layout-and-coordinate-rules)
- [Text, numeric displays, and headers](#text-numeric-displays-and-headers)
- [Process connections and equipment](#process-connections-and-equipment)
- [Gauges, states, and indicators](#gauges-states-and-indicators)
- [Charts, schedules, and tables](#charts-schedules-and-tables)
- [Bindings, scripts, and navigation](#bindings-scripts-and-navigation)
- [Templates and repeated equipment](#templates-and-repeated-equipment)
- [Complex engineering screen composition](#complex-engineering-screen-composition)
- [Review checklist](#review-checklist)

## Layout And Coordinate Rules

- Store child bounds relative to the immediate parent, not the screen.
- Preserve the root design size, each component's bounds, preferred bounds, layout constraints, anchor flags, and font-scaling configuration through the target-version round trip.
- Keep containers purposeful. Use one root composition, a header/status band, a main process/content area, and optional detail panels rather than many overlapping top-level windows.
- Put gallery examples in separate nonstartup windows and persist `resource.json` attribute `open-on-start=false`. Do not stack several startup windows to simulate pages.
- Keep accepted, error-free examples in the project's designated gallery path after validation. Do not delete them as test cleanup; retain their modules, handlers, tags, queries, and other required dependencies.
- Require positive dimensions and containment inside the immediate parent and root.
- Treat sibling overlap findings as review candidates. Pipes, joints, dial layers, ticks, and overlays may intersect intentionally; text occlusion, full containment, and unexplained large overlaps require correction.
- Reserve separate rows or regions for dynamic chart annotations, titles, legends, and scale notes. Runtime marker labels must not paint over a static plot title even when their data position moves across the full axis.
- Validate at the actual client aspect ratio. Preferred-size mismatch alone is not clipping proof.

## Text, Numeric Displays, And Headers

- Set horizontal and vertical alignment explicitly. Vision numeric labels often default to right alignment; use centered alignment when the design calls for a centered readout.
- Allocate width for the longest realistic title, value, unit, and alarm/state text. Do not rely on ellipsis for primary labels.
- Generate and test the longest reachable runtime string for every data-derived label. A representative preview such as `8 NORMAL / 2 WATCH` does not prove that a reachable value such as `10 NORMAL / 0 WATCH / 0 EXCURSION` fits.
- Use a stable hierarchy: page title, short context/subtitle, section labels, values, and units.
- Keep values and engineering units in distinct fields when that improves readability and binding quality visibility.
- Use consistent padding and line height. Avoid text touching the bounds of a label or header.
- Verify actual rendered text fit through the client font metrics and inspect the screenshot for occlusion, z-order, and custom painting.
- Evaluate clipping on visible text separately from hidden technical markers. A deliberately hidden identity label may be tiny or off-canvas; it must not conceal a visible-label failure, and it must not make an otherwise clean visible-text audit fail. Require zero clipped visible labels plus a native screenshot review.
- A blank bordered rectangle often indicates an uninitialized state dataset, a foreground/background issue, or a component with no selected state—not a decorative element.

## Process Connections And Equipment

- Use one continuous pipe component for one continuous physical header whenever possible.
- Add a coupling, reducer, valve, flange, or joint only when it represents a real fitting, state, direction change, or maintenance boundary.
- Avoid two large pipe rectangles joined by an unexplained thin rectangle; it reads as a break or mismatch. Prefer one pipe or an intentional reducer/joint symbol.
- Make flow direction visible through arrows, pump orientation, or process context.
- Build a flow arrow as one stable component or one target-proven native shape. Do not assemble a direction marker from separately positioned strokes that can drift apart after serialization or layout.
- For generated label-based arrows, prefer a target-proven plain-text marker such as `>` unless the exact Unicode glyph has passed native serialization, font, screenshot, and text-fit checks. Keep its caption outside dynamic readouts and inspect the pixels; font metrics alone do not reveal every overlap or malformed glyph.
- Distinguish process level from engineering inventory. If a tank level is fractional, format it explicitly as percent; show volume or mass separately with units.
- Use color to encode state only when the legend and non-color cue are clear. Do not make normal/abnormal meaning depend on color alone.

## Gauges, States, And Indicators

- Prefer a native meter when its range, angles, tick interval, label format, colors, and value presentation meet the requirement.
- Set the real process range. Do not clamp a value to 100 merely because the default meter range is 0–100; configure the instrument for the declared maximum when the process can exceed 100.
- Keep major ticks readable and avoid dense labels. Use a custom dial only when the native component cannot communicate the needed scale or semantics.
- Do not assume a native meter's tick interval limits how many numeric labels the Vision Client paints. When a compact meter crowds the scale, disable its automatic tick labels and add a few deliberate anchors such as minimum, midpoint, and maximum. Put those anchors above the meter in the component order, use unambiguous contrast, and verify them in a fresh native client.
- Keep equipment names and status text outside pump, motor, valve, and rotor glyphs. Use a separate high-contrast badge or caption region when text would otherwise compete with the symbol.
- For a custom dial, separate the directly bound numeric value from the drawing primitives. Clamp and map the value through a short filtered property-change script that updates only known primitives.
- Initialize multi-state datasets explicitly and include every expected state, selected text, colors, and animation fields. Center the selected label when appropriate.
- Preserve ordinary `java.awt.Color` values in generated native resources; avoid look-and-feel resource subclasses.

## Charts, Schedules, And Tables

Choose the component by the engineering question:

| Question | Suitable native component |
|---|---|
| How has a signal changed over time? | Easy Chart with qualified historian-backed pens. |
| How are distributions, median, quartiles, and outliers different across groups? | Box-and-Whisker Chart with a typed dataset. |
| What state occupied each time interval? | Status Chart with complete series/state/color mapping. |
| What work is planned across a time range? | Gantt Chart or Equipment Schedule with ordered dates and unique IDs. |
| What records require sorting, selection, or drill-down? | Power Table with a bounded read-only query and explicit schema. |
| What alarms are active under a fixed filter? | Alarm Status Table with deliberate filter/control settings. |

- Preserve declared dataset column names and Java types. A visually plausible table with wrong types is not valid.
- Validate row/column caps, IDs, date ordering, ranges, and correlations before import.
- For a native Gantt Chart, use the exact typed task columns `Task Name: java.lang.String`, `Start Date: java.util.Date`, `End Date: java.util.Date`, and `Percentage Done: java.lang.Integer`. Keep task names unambiguous, require end time to be at or after start time, and constrain completion to `0..100`.
- For a Status Chart using data format `0`, keep the state dataset as `Timestamp: java.util.Date` plus one `java.lang.Integer` column per series. Supply a complete properties dataset of `SeriesName: String`, `Value: Integer`, and `Color: java.awt.Color`, with exactly one mapping for every reachable series/state pair, plus a legend dataset of `Color` and `Description: String`. Verify the runtime row/column counts and state range, then inspect native pixels; a complete mapping alone does not prove that the live chart refreshed.
- When phase or equipment states are inferred from analog history, state the derivation and threshold model on the page. Labels such as `CHARGE` or `TRANSFER` describe derived signal roles unless an actual recipe or state tag proves the executed phase; do not present adaptive relative bands as authoritative batch execution.
- When Gantt intervals are inferred from historian bands or state transitions, label them as observed signal windows. Do not present them as CMMS work orders, planned maintenance, or executed work unless those records are the actual source.
- Treat a native schedule and a read-only ledger as separate presentation contracts even when they describe the same intervals. Keep `java.util.Date` columns for a component such as Equipment Schedule. When a table must display an exact fixed-width time such as `HH:mm:ss`, give that table explicitly formatted String columns or a separately proven renderer; do not rely on default Date rendering. Validate the longest reachable value in fresh-client pixels.
- For a Classic Chart category dataset whose first column is the category/domain and whose remaining columns are value series, use extract order `By Column`. Then inspect the runtime `CategoryPlot`: each rendered dataset should expose the intended series across the intended category keys. Do not assume runtime dataset order matches descriptor declaration order.
- Treat source datasets, descriptor/axis configuration, rendered plot shape, and native pixels as separate checks. A valid source schema can still render transposed categories, duplicate legend entries, or disconnected series.
- Long native chart titles can collide with a vertical-axis label or plot insets even when every text component passes a font-metric audit. When the layout is tight, leave the chart's native title blank and place a separate label above the chart; confirm the label and the chart are both inside the observed client root.
- Separate static demonstration datasets from live historian or SPC claims. A static distribution chart must say that it is static and must not imply control limits, capability, or live sampling.
- On a transient history/query failure, do not flatten histogram bars or replace statistics with plausible zeros; zero is meaningful process data. Preserve the last known-good or explicitly labelled design snapshot, display a stale/failure state, and replace it only after a successful bounded refresh.
- Treat live-value and moving-tag panels as optional context, not a default demo scaffold. Include them only when they help answer the page's engineering question or validate a data path that matters to the primary visual.
- Do not repeat unrelated moving sample cards beside a static chart. Omit the panel or use the space for relevant source, schema, scope, interpretation, alarm, or quality context. If the primary visual uses no live tags, say so plainly.
- When moving context values are relevant, bind directly to known Good simulated or real tags and label their source. Do not claim those values populate a chart unless the chart dataset actually derives from them.
- Disable editing, dragging, resizing, refresh, or writeback unless the use case explicitly requires and validates it.
- For a sorted Power Table, distinguish the selected visible row from the underlying dataset row. Use the component's view-to-data mapping before updating a linked detail panel, and handle `selectedRow == -1` as an explicit empty state.
- Use one fixed client query for a component-specific runtime contract; do not expose arbitrary dataset accessors.
- Do not treat a component-specific Easy Chart query as a generic chart inspector. For an arbitrary Easy Chart, combine structural pen inspection, bounded history probes for every qualified source, client-side binding/value checks, and a native screenshot that visibly shows the expected traces.

## Bindings, Scripts, And Navigation

- Prefer direct tag, expression, property, query, or history bindings over component event scripts for continuous data flow.
- Use fully qualified tag paths for portable resources.
- For expression bindings, preserve parsed expression structure, value class, and bound tag listeners—not only expression text.
- Keep event scripts short, filtered, and side-effect explicit.
- Use logical Vision paths for `openWindow`, `swapWindow`, and `openWindowInstance`; verify every target exists in the same project.
- Avoid circular startup navigation and duplicate startup windows.
- Inspect the serialized binding/action metadata and then validate values and quality in a fresh client.

## Templates And Repeated Equipment

- Put reusable equipment presentation in a Vision template with explicit public parameters.
- Keep parameters JSON-primitive or typed according to the component contract.
- In Template Repeater dataset mode, match every column name to a public parameter exactly, including case.
- Match each repeater dataset column's Java type to the public parameter, serialized binding value class, and target component property. Do not send `Double` values such as `0.0` to integer-only Swing properties without an explicit, target-proven conversion.
- If the presentation does not require an integer-only control, prefer a type-stable display contract such as a formatted string (`78 / 100`) or a `Double` numeric label over a coercion-prone progress-bar binding.
- A nested container's preferred bounds belong to its parent coordinate system. After placing it, do not reset those bounds to `(0, 0, width, height)`; that can move opaque siblings over titles and values.
- In Template Canvas mode, validate the instance dataset/parameters, absolute instance bounds, loaded template path, and indirect binding resolution.
- Set the Template Canvas background and opacity deliberately. Unused canvas area can otherwise render as a default white rectangle that resembles an unexplained panel or generic box; match the intended parent surface unless the canvas is intentionally transparent.
- Distinguish the component's presentation state from the underlying tag state.
- Validate one native screenshot for z-order and opaque coverage, then inspect focused client logs after template instantiation. Text-fit checks cannot detect a correctly sized label hidden behind another component.
- Retain the template, consuming windows, manifests, thumbnails/binaries, handlers, mailboxes, tag types/instances, query resources, and other dependencies needed by a working example.

## Complex Engineering Screen Composition

Build complex pages around decisions, not component variety:

1. State the operator or engineer's task.
2. Select a primary visual: process overview, trend, distribution, schedule, state timeline, alarm table, or diagnostic matrix.
3. Add only the KPIs and context needed to interpret that visual.
4. Add live values only when they are decision-relevant; otherwise use the space for context that explains the primary visual or leave it open.
5. Keep navigation and detail actions predictable.
6. Use restrained color, consistent typography, and explicit empty/error states.
7. Validate structure, dependencies, runtime state, motion where applicable, focused logs, and pixels separately.

## Review Checklist

- Exactly the intended startup windows open.
- No primary title or value is ellipsized or clipped.
- Numeric values align as intended.
- Bounds are positive and contained.
- Overlaps are intentional and explained.
- Pipes and fittings represent real process semantics.
- Dataset schemas and Java types match the component.
- All tags/queries/templates/navigation targets resolve with Good readiness.
- Live and static data are labeled truthfully.
- Every panel supports the page's primary engineering task; there is no generic demo filler.
- Screenshots, runtime state, and log evidence support only the claims being made.
