# Perspective Column Container

Use this reference for the live-tested Ignition 8.3.8 Perspective Column Container. The qualified component type is `ia.container.column`. It lays out children in a responsive 12-column grid using named container breakpoints and per-child breakpoint configurations.

## Contents

- [Tested resource shape](#tested-resource-shape)
- [Breakpoint selection](#breakpoint-selection)
- [Rows, columns, spans, order, and gutters](#rows-columns-spans-order-and-gutters)
- [Child lifecycle](#child-lifecycle)
- [Geometry and topology proof](#geometry-and-topology-proof)
- [API authoring and validation](#api-authoring-and-validation)
- [Focus and accessibility boundary](#focus-and-accessibility-boundary)
- [Runtime validation checklist](#runtime-validation-checklist)
- [Qualification boundary](#qualification-boundary)

## Tested resource shape

Declare the container breakpoints, gutters, and every child's layout at every breakpoint explicitly:

```json
{
  "type": "ia.container.column",
  "meta": { "name": "ColumnContainer" },
  "props": {
    "breakpoints": [
      { "name": "sm", "minWidth": 0 },
      { "name": "md", "minWidth": 700 },
      { "name": "lg", "minWidth": 1000 }
    ],
    "currentBreakpoint": "",
    "gutters": {
      "horizontal": 12,
      "vertical": 16
    }
  },
  "children": [
    {
      "type": "ia.display.view",
      "meta": { "name": "CardA" },
      "position": {
        "height": 150,
        "breakpoints": [
          { "name": "sm", "rowIndex": 0, "colIndex": 0, "span": 12, "order": 1 },
          { "name": "md", "rowIndex": 0, "colIndex": 6, "span": 6, "order": 2 },
          { "name": "lg", "rowIndex": 0, "colIndex": 9, "span": 3, "order": 4 }
        ]
      },
      "props": {
        "path": "Folder/Card View",
        "params": { "label": "A" },
        "style": { "height": "100%", "width": "100%" }
      }
    }
  ]
}
```

Repeat the `position.breakpoints` member for every child. The qualified fixture used four Embedded Views and provided `sm`, `md`, and `lg` configurations for each one. It did not rely on missing-configuration fallback behavior.

`props.currentBreakpoint` was runtime output and settled to the selected lowercase name. Validate it together with painted geometry; do not use its authored empty value as runtime evidence.

## Breakpoint selection

Breakpoint selection used the rendered Column Container width, not the browser viewport width. Parent padding and borders made those values different in the qualified page.

With explicit `sm:0`, `md:700`, and `lg:1000` settings, two independent strict runs reproduced these exact outer-rectangle results:

- width 1001 selected `lg`;
- width 1000 selected `lg`;
- width 999 selected `md`;
- width 701 selected `md`;
- width 700 selected `md`;
- width 699 selected `sm`.

Treat these as exact rendered-boundary observations for the tested integer fixture. The installed client implementation receives a resize-observer measurement that is not exposed directly, so do not infer subpixel boundary behavior from integer `getBoundingClientRect()` output or from minified client source alone. Measure both sides of every required boundary on the target build.

## Rows, columns, spans, order, and gutters

The tested grid contained 12 tracks. `rowIndex` selected the zero-based row, `colIndex` selected the zero-based starting track, and `span` selected the number of tracks occupied.

`order` determined placement order within the selected layout. The four-card fixture intentionally painted different sequences:

- `lg`: one row, `D C B A`, each span 3 at columns 0, 3, 6, and 9;
- `md`: row 0 `B A` and row 1 `D C`, each span 6 at columns 0 and 6;
- `sm`: four rows `A`, `B`, `C`, `D`, each span 12 at column 0.

Keep configured column positions consistent with the sorted order. Overlap, gaps before the first child, and automatic wrapping from incompatible `order`, `colIndex`, or `span` values were not qualified.

The gutter names are counterintuitive in the tested runtime:

- `props.gutters.vertical` produced the horizontal column gap;
- `props.gutters.horizontal` produced the vertical row gap and non-final-row bottom margin.

With vertical 16 and horizontal 12, every row reported a 16-pixel column gap and a 12-pixel row gap. Every non-final row had a 12-pixel bottom margin; the final row had zero.

Each child retained its authored `position.height`. A row's height equaled the tallest child in that row. The qualified heights were A 150, B 170, C 190, and D 210 pixels: the lg row was 210; the md rows were 170 and 210; and the four sm rows were 150, 170, 190, and 210.

For the qualified equal-span layouts, require the painted widths to satisfy:

- four lg cards: `(inner width - 3 × column gap) / 4`;
- two md cards: `(inner width - column gap) / 2`;
- one sm card: `inner width`.

## Child lifecycle

Changing the selected Column breakpoint remounted every Embedded View in the qualified fixture, even though the same four resources remained represented in official topology. Each transition produced new instance identifiers, ran each child startup once, and reset unbound child-local counters:

- `lg` to `md`;
- `md` to `sm`;
- `sm` to `md`;
- `md` to `lg`.

Resizing without changing the selected breakpoint retained all four instances and local state. This included wide to 1001 to 1000 within lg, 999 to 701 to 700 within md, and 1000 back to wide within lg.

Do not keep durable UI state only inside Column children when it must survive responsive layout changes. Store such state above the Column Container or in another explicitly qualified persistent source.

A simultaneous second browser session remained wide in lg with separate child instances and unchanged local counters while session A exercised every boundary.

## Geometry and topology proof

At every responsive edge, record:

- viewport and document dimensions;
- exact Column outer and inner rectangles;
- every row rectangle, grid template, gaps, and bottom margin;
- every child rectangle, selected row, grid start/end, height, and painted order;
- `currentBreakpoint`;
- child startup, instance, and local-state evidence;
- browser diagnostics;
- official sessions and mounted-view topology;
- bounded official Gateway WARN-or-higher logs.

The tested page's official topology contained one shared dock, one Column parent, and four mounted card views per browser page. Filter by exact resource and mount paths. Topology proves the resources remained registered; instance/startup evidence is required to detect responsive remounts.

## API authoring and validation

Use the authenticated official project export/import and scan-lock operations exposed by the live OpenAPI document when whole-project import is the selected workflow. Require a declared delta, tokenless rejection, authenticated success, exact export readback, route activation, protected-resource parity, stable project inventory, and bounded logs.

`llmImport` is optional and project-scoped. Read its health response and require an action in `availableActions` before calling its POST route. Do not add a Column-specific action when official project import or an existing general folder-resource action is sufficient. If `llmImport` is absent, continue with the official OpenAPI capabilities.

Use browser automation only after API authoring, for rendering, screenshots, exact geometry, bounded interactions, diagnostics, and correlation with official topology and logs.

## Focus and accessibility boundary

The tested Column root exposed `tabIndex` -1 and no native interactive semantics. The container itself did not establish keyboard reordering, grid navigation, or an accessible layout-control contract. Accessibility of interactive child content remains the responsibility of those child views.

Focus behavior during responsive remount, screen-reader announcements, tab-order changes, and accessibility conformance remain unqualified.

## Runtime validation checklist

1. Export the approved project, declare the exact page/view delta, and author through an authenticated API operation.
2. Verify exact `breakpoints`, `gutters`, `currentBreakpoint`, and every child's `height` and named row/column/span/order configuration in export readback.
3. Open two independent sessions and save original-resolution screenshots, exact URLs, outer/inner/row/card geometry, current breakpoint, browser diagnostics, official topology, and bounded Gateway logs at every edge.
4. Mutate local state in lg; test 1001, 1000, and 999. Mutate local state in md; test 701, 700, and 699. Mutate local state in sm; return through md and lg, then restore wide.
5. Require expected row count/order/span geometry, gutter axes, row heights, same-breakpoint instance retention, breakpoint-transition remount/startup/reset, and session-B isolation.
6. Query and classify official Gateway WARN-or-higher logs after every edge and after delayed zero-browser-page cleanup, even when the page looks correct.
7. Re-export the project and protected resources after each strict run and require exact hash parity with the accepted baseline.

## Qualification boundary

This reference does not qualify installed default breakpoint values, omitted or missing child configurations, fallback inheritance, duplicate breakpoint names, duplicate/overlapping cells, invalid or fractional row/column/span/order values, empty rows, more than 12 columns, runtime breakpoint mutation, nested Column Containers, non-Embedded-View children, focus restoration, rapid resize storms, touch/mobile behavior, output parameters, tag bindings, asynchronous scripts, security policies, accessibility conformance, subpixel boundary behavior, or other Ignition builds. Test each separately before relying on it.
