# Data Bindings And Refresh

Read the matching section while authoring the requested page. Preserve exact seed/schema rules and apply the relevant design defaults. Runtime/browser checks in these rules belong in `VALIDATION.md` when no authorized target is available; they do not block delivery after offline checks pass.

## Contents

- Named Queries And Runtime Data
- Tag Discovery And UDT Context
- Tables Paging And Refresh
- Alarms And Journal Data
- History And Chart Shapes

## Named Queries And Runtime Data

- Use arrays of objects for mixed Perspective table data unless a component requires a dataset.
- For database-backed tables/KPIs, prefer Perspective Named Query bindings over inline SQL. Put the binding under the table/component `propConfig`, for example `propConfig["props.data"].binding.type = "query"` with `config.queryPath`.
- Keep the outer `binding` wrapper for every bound property. A KPI label must use `propConfig["props.text"] = {"binding": {...}}`, not a bare query binding object at `propConfig["props.text"]`.
- Put static or property-derived Named Query parameters in `binding.config.parameters`, and design explicit empty/zero-row text instead of indexing row 0.
- Build table columns/KPI fields from discovered Named Query metadata or a capped preview result. Do not guess result field names from SQL table names.
- Treat preview rows as seed/sample data only; the live Perspective binding owns runtime data. Keep the query DB-side bounded for design previews.
- Avoid QueryString and Database Named Query params in portable packages unless the target workflow explicitly supplies allowlists. QueryString is for vetted SQL identifiers/fragments only; Database params require target-approved connection names and live validation. Do not assume a package-copied `<Parameter>` database setting will execute dynamically without target validation.


A design preview is a sample, not a runtime performance guarantee. Bound/filter the actual query for the operator's task and let the live binding own the data. Do not infer that a component pager imposes a database row limit. Choose the intended data shape before multiplying bindings across a page.

## Tag Discovery And UDT Context

- For Tag Browse Tree pages, start from an exact `ia.display.tag-browse-tree` seed, set `props.root.path` to a validated root, keep `props.selection.mode` explicit, and bind sibling detail labels from `../Tag Browse Tree.props.selection.values`. Use `onNodeClick` `event.path`/`event.name` when the page needs clicked-node side effects or tag reads; handle folder reads as bad/unsupported.
- For UDT-backed pages, bind to UDT instance/member paths. Do not bind to UDT definition paths under `[<tagProvider>]_types_`.
- For UDT-backed Perspective rows/bindings, preserve the difference between `None`, empty string, and literal `"null"` parameter values; omit an override to inherit defaults, guard numeric null before math, and avoid quoted `{ParamName}` placeholders that can remain literal.
- For UDT-backed rows/bindings, preserve null, empty string, and literal `"null"` parameter values distinctly; omit overrides for defaults, guard numeric null, and avoid quoted `{ParamName}` placeholders that can stay literal.
- For Tag Browse Tree pages, start from an exact `ia.display.tag-browse-tree` seed, set `props.root.path` to a validated provider/root, keep `props.selection.mode` explicit, and bind sibling detail/readback components from `../Tag Browse Tree.props.selection.values`. Use `onNodeClick` `event.path`/`event.name` for clicked-node side effects or tag reads; folder paths can read as bad/unsupported.
- Heavy discovery, browse, and merge logic belongs in one parent/list view or project script, not inside every repeated card.

## Tables Paging And Refresh

- For operator summary tables, include visible fields plus hidden stable fields such as base tag path, next action, and severity rank in each row object; hide helper columns and use them for selection/detail logic.
- For filtered operator overviews, drive attention cue, filters, KPI counts, rows, selected detail, and chart state from one model; sort abnormal/high-severity assets first and default selection to the highest-priority row.
- Tables populated into `view.custom` from startup browse/read are snapshots; after writeback, refresh affected rows or reload table data so tables do not contradict live-bound detail/faceplate readbacks.
- For operator summary tables, keep visible columns and hidden helper fields in the same row object. Hide helper columns such as base tag path, next action, and severity rank, then use them to drive detail panels and action context.
- For filtered operator overview screens, calculate attention cue, filter counts, table rows, selected detail, and chart input from one shared model. Sort abnormal/high-severity assets first and set default selection from that sorted list.
- Startup-built table rows in `view.custom` are snapshots. If a popup/script writes tags, refresh the affected row or reload table data after the result so the table does not contradict live-bound detail components.
- For heterogeneous table data, prefer Perspective arrays of objects. If a dataset is required, keep each column one datatype.

The Table's built-in pager operates on supplied data. Virtualization reduces browser row rendering; neither automatically implements SQL paging. Use filtered/bounded queries and suitable virtualization first. Add custom database paging only when the requested result volume warrants it, with correct full-result sorting/filtering semantics. [Table documentation](https://docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-display-palette/perspective-table), [8.1.45 paging discussion](https://forum.inductiveautomation.com/t/ignition-perspective-table-virtualized-and-pager-explanations/101605)

Refresh a snapshot or its owning data binding after a successful commit. Between embedded views, send a suitably scoped message to the owner instead of brittle cross-view component traversal. `refreshBinding` refreshes a polling binding; it does not promise a third-party chart formatter/configuration will redraw. Include the affected post-write display check in the normal handoff. [Component methods](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/perspective-component-methods)

## Alarms And Journal Data

- For route-param alarm/history detail pages, bind Alarm Status Table `props.filters.active.conditions.displayPath` and Alarm Journal Table `props.filter.conditions.displayPath` from the route param; keep current status, journal history, and history/fallback panels visibly separate.
- Use `ia.display.alarmstatustable` for real Ignition tag alarms, not custom alarm-like row data; scope it with provider/source/displayPath filters so unrelated site alarms do not appear.
- For UDT-backed alarm rollups, build area counts from runtime alarm reads and filtered current alarm rows, then pass selected area/count/assets/filter values into a reusable alarm detail view through `props.params`.
- Use `ia.display.alarmjournaltable` for historical alarm transition rows only when an Alarm Journal/profile is configured; its props use singular `filter.conditions` plus `dateRange`, unlike Alarm Status Table `filters.active.conditions`. Preserve/discover the exact component `props.name` journal profile from a seed or target Gateway; do not guess `"Journal"`. Keep current status, journal history, and sampled/current-value fallbacks visually separate.
- Built-in `ia.display.alarmstatustable` reads Gateway alarm events. Back it with configured tag alarms and set `props.filters.active.conditions` such as `displayPath`, `source`, or `provider`; otherwise unrelated active alarms can appear.
- For UDT-backed alarm rollup pages, verify the row model against runtime alarm reads and filtered `alarmStatusQuery` counts, then pass selected area/count/assets/filter values into reusable detail views through `props.params`.

## History And Chart Shapes

- Verify historian/trend behavior separately from tag browse/value existence; if no non-null history rows are available, label sampled/current-value chart data as a fallback.
- For Time Series Chart, prefer an exact seed or minimal seed-style `props.series[].data` shape. For custom plots, use `props.plots[].trends[].columns` as objects such as `{ "key": "PV" }`, with each `key` matching a field in `props.series[].data`; do not use plain strings. Browser-test for rendered chart SVG/canvas marks and chart runtime errors.
- For trend panels, confirm historian availability separately from current tag reads. If history queries return only null/no rows, label the chart as sampled/current-value fallback data.
- For Time Series Chart custom plots, `props.plots[].trends[].columns` should be an array of objects such as `{ "key": "PV" }`; each key must match a field in `props.series[].data`. Plain string columns are a known bad shape. Browser confirmation should show rendered SVG/canvas marks and no relevant chart runtime errors.
- Give every operator-facing Tag History entry a unique `alias`; keep provider paths and simulator leaf names internal. With Wide return format, use that alias as the dataset field and update every explicit `props.plots[].trends[].columns[].key` to match. In the browser, require intended aliases, no raw path/provider/simulator keys, rendered marks, and no chart errors.

Missing chart points can come from data/quality filtering as well as rendering. Preserve source and fallback labels. If an actual backfill symptom occurs on 8.1.50, use the issue reference; do not lower quality requirements or claim a PowerChart fix from an unconfirmed workaround. Carousel/browser memory complaints also require a matching reproduction; no standard new-chart package needs a soak test.
