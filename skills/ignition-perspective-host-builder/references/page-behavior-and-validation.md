# Page Behavior And Validation

Use the relevant section while building or reviewing a Perspective page, then incorporate its checks into the skill's normal browser/readback pass. These are design defaults and conditional checks, not an additional test suite. Keep the requested visualization moving toward a working result. An unchanged feature does not need a new investigation merely because it appears here.

## Contents

- Reusable View Context — embedded views, repeaters, startup, provider/equipment switching
- Page Composition And Data Volume — repeated content, nesting, large diagrams, scripting
- Tables And Refresh — virtualization, paging, query data, chart updates
- Operator Controls — action events, disabled state, touch input
- Pipes And Styles — pipe edits, binding assignments, stylesheet syntax
- Failure Triage — browser versus Gateway, version-specific symptoms

## Reusable View Context

**Build:** Give reusable views a small, explicit input contract, such as provider/base tag path and equipment identity. Keep external inputs in `view.params` and internal selection/state in `view.custom`. Reuse the existing discovery patterns to obtain real paths and component shapes. Use one parent-owned row/instance model where repeated children need the same context; avoid duplicating discovery work for each child.

A child can evaluate before its final bound context arrives. Use inert saved context where practical and gate commands on valid selected equipment/provider context. Keep required command authorization and interlock checks in the existing command path; a disabled display alone is not that authorization.

**Avoid:** active design-time equipment paths leaking into a reusable child; assuming a correct settled display proves the first read/write target was correct; changing every view to `inputBehavior: merge` or `props.loading.order: after-parent` as a blanket optimization.

`merge` retains default object keys omitted from incoming parameters; `replace` removes those absent defaults. Choose the intended semantics. `after-parent` changes loading order and may improve the perceived first layer while increasing total loading work. Use either deliberately, not as a universal race fix.

**Check when affected:** during the normal page pass, open the page from a fresh route and switch the selected equipment/provider. Confirm child labels/readbacks follow the selected context and a command cannot use an uninitialized target. Exercise partial/missing parameter cases only when the view accepts them or initialization is failing.

Sources: [View object and input behavior](https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-view-object), [Embedded View loading](https://docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-embedded-view).

## Page Composition And Data Volume

**Build:** Keep the active page understandable and responsive. Reuse parameterized components, but keep extra wrapper views and nested dependencies purposeful. Keep shared data near the view/container that owns it and avoid repeating expensive browse/query work across identical children. Use direct bindings or expressions for straightforward values; use scripts for transformations or behavior that actually need them.

Preserve the skill's existing equipment geometry, named connection anchors, legible labels, state-driven animation, and live readback requirements. Performance advice should support those visualization goals. It does not justify removing requested operator information without a design reason.

**Avoid:** creating an entire hierarchy of views for simple repeated decoration; regenerating broad tag inventories per tile; replacing all scripts/transforms merely because one technique is claimed to be faster; treating a community component/session count as a capacity limit.

**Check when affected:** inspect the actual page at the target viewport with representative content. If opening or interaction is visibly slow, first narrow the expensive view, binding, or query. Ordinary builds do not need a capacity benchmark. Designer opening time and browser rendering time are separate symptoms.

Sources: [Embedded View composition guidance](https://docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-embedding-palette/perspective-embedded-view), [Community performance discussion; no controlled universal benchmark](https://forum.inductiveautomation.com/t/perspective-performance-strategies-for-diagnosing-slow-load-times/100034).

## Tables And Refresh

**Build:** Continue using discovered Named Query metadata, bounded previews, explicit empty states, and real runtime bindings. Preview rows are design samples, not the runtime data source. Limit/filter the actual query appropriately for the operator's task.

A Table's built-in pager operates on supplied data. Virtualization reduces rendered rows in the browser; neither automatically turns the SQL query into database paging. If the requested result volume warrants database paging, provide matching controls and correct full-result sorting/filtering semantics. Do not implement custom paging solely because a table exists.

After a successful command/database commit, update the affected snapshot or refresh the owning data binding so summary rows and detail values agree. For separate embedded views, use a suitably scoped message to the owning view rather than brittle cross-view component traversal. `refreshBinding` can refresh a polling binding; it does not guarantee a third-party chart's formatter or configuration will redraw.

**Avoid:** fetching all history just to show one page of rows; assuming virtualization fixes database work; refreshing before the write commits; treating a successful query preview as proof that the runtime table/chart works.

**Check when affected:** verify visible rows, empty state, and a relevant sort/selection or post-command refresh during normal interaction testing. Investigate query time/payload and browser rendering separately only if a performance symptom remains.

Sources: [Table properties](https://docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-display-palette/perspective-table), [Paging versus virtualization discussion](https://forum.inductiveautomation.com/t/ignition-perspective-table-virtualized-and-pager-explanations/101605), [Component methods and binding refresh](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/perspective-component-methods).

## Operator Controls

**Build:** Use `onActionPerformed` for a component action where supported. If `onClick` is required, explicitly account for enabled state: the event may still fire on a disabled component. Keep one command path per intended interaction. `onSelect` describes text selection, not a generic touch action.

For touch numeric entry, prefer the target's existing working control or a suitable proven component. Carry equipment context, units, validation, cancel/commit behavior, and visible readback through the popup. Choose a custom keypad only when the requested device/workflow needs it.

**Avoid:** duplicating a write across click and touch handlers; assuming a visual disabled state enforces backend permissions; adopting a new keypad module for an ordinary desktop button.

**Check when affected:** use the actual target input method, verify disabled/blocked behavior and one accepted action, and confirm final readback under the existing command-validation rules. Test additional mouse/touch/keyboard paths when those devices are part of the requested deployment.

Source: [Perspective event types](https://docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/perspective-event-types-reference). Keypad choice is a deployment-specific design recommendation, not a demonstrated patch fix.

## Pipes And Styles

**Build:** Keep pipes derived from the existing named equipment anchors. Establish pipe structure/order before attaching many bindings when practical. After reordering, adding, or deleting pipes in an authorized edit, reopen the view and check that state/color bindings still address the intended equipment.

Reuse discovered styles and preserve the skill's typed-style rules. When editing `stylesheet.css`, keep syntax valid and inspect the intended applied rule if the visual result is wrong.

**Avoid:** assuming a visually correct pipe retained its tag binding after a structural edit; keeping disposable first style classes to conceal a stylesheet parsing problem.

**Check when affected:** combine the binding check with the existing pipe geometry/browser pass. For a style edit, inspect its rendered result; investigate stylesheet parsing when that result fails. A simple color change does not require replaying all version incidents.

Sources: [Pipe-binding reports on 8.1.43–8.1.45; no verified in-range fix](https://forum.inductiveautomation.com/t/bug-pipe-bindings-does-not-follow-the-pipe-if-the-z-order-of-pipes-is-changed/101896), [8.1.47 style report resolved by correcting CSS](https://forum.inductiveautomation.com/t/first-style-does-not-work/115377).

## Failure Triage

If the normal build check exposes a failure, retain the concrete symptom and affected resource. A healthy Gateway does not establish browser health; a fresh working session does not explain a frozen existing session. Start with the affected browser and a narrow corresponding Gateway log window, using available approved tools.

Consult the matching known-issue entry only when a symptom or explicit compatibility question warrants it. Reports are diagnostic candidates, not permission to change Gateway versions, install modules, redesign unrelated pages, or start load/soak tests. When evidence is unavailable, describe the unproven behavior without claiming a fix.
