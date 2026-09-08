# Perspective Breakpoint Container

Use this reference for the live-tested Ignition 8.3.8 Perspective Breakpoint Container. The qualified component type is `ia.container.breakpt`. The tested determinant is `width`, with one explicitly assigned `small` child and one explicitly assigned `large` child.

## Contents

- [Tested resource shape](#tested-resource-shape)
- [Selection rule and currentBreakpoint](#selection-rule-and-currentbreakpoint)
- [Child lifecycle and local state](#child-lifecycle-and-local-state)
- [Geometry and topology proof](#geometry-and-topology-proof)
- [API authoring and validation](#api-authoring-and-validation)
- [Focus and accessibility boundary](#focus-and-accessibility-boundary)
- [Runtime validation checklist](#runtime-validation-checklist)
- [Qualification boundary](#qualification-boundary)

## Tested resource shape

Declare the determinant, breakpoint, and both child sizes explicitly:

```json
{
  "type": "ia.container.breakpt",
  "meta": { "name": "BreakpointContainer" },
  "position": { "basis": "0px", "grow": 1 },
  "props": {
    "breakpoint": 900,
    "determinant": "width",
    "currentBreakpoint": ""
  },
  "children": [
    {
      "type": "ia.display.view",
      "meta": { "name": "SmallChild" },
      "position": { "size": "small" },
      "props": {
        "path": "Folder/Small Child",
        "params": {},
        "style": { "height": "100%", "width": "100%" }
      }
    },
    {
      "type": "ia.display.view",
      "meta": { "name": "LargeChild" },
      "position": { "size": "large" },
      "props": {
        "path": "Folder/Large Child",
        "params": {},
        "style": { "height": "100%", "width": "100%" }
      }
    }
  ]
}
```

The installed defaults observed on the tested build were a breakpoint of 640 and a width determinant. Do not rely on those defaults when the behavior matters. The installed component descriptor accepts `small` and `large` as child `position.size` values and `width` or `height` as determinant values; only the explicit width configuration above was runtime-qualified.

## Selection rule and currentBreakpoint

For the tested width determinant, Perspective compares the Breakpoint Container's measured rendered width with `props.breakpoint`:

- measured width strictly less than the breakpoint selects `small`;
- measured width equal to the breakpoint selects `large`;
- measured width greater than the breakpoint selects `large`.

This boundary was reproduced with an exact 900-pixel component width selecting `large` and an exact 899-pixel component width selecting `small`. Use the component rectangle, not the browser viewport width, when proving the boundary. Parent padding, borders, docks, and other layout can make those values different.

The runtime wrote `props.currentBreakpoint` as the lowercase String `small` or `large`, matching the selected child. Treat it as runtime output. Validate both the property and the painted child instead of relying on either alone.

## Child lifecycle and local state

Only the selected child is mounted. Crossing the boundary removes the outgoing Embedded View and mounts the incoming one. Returning to a previously selected size creates a new child instance; it does not restore the prior child instance.

In the qualified sequence:

1. the initial large child started once and retained its local counter while width stayed above the boundary and at exactly 900;
2. changing from 900 to 899 removed that large child and mounted a fresh small child with startup count 1 and local counter 0;
3. changing from 899 to 900 removed the small child and mounted a fresh large child with a different instance identifier and reset local counter;
4. every later cross-boundary return again produced a new instance and reset unbound local state.

Do not use this container to preserve inactive-child UI state. Put durable state above the Breakpoint Container, in an appropriate binding, or in another explicitly qualified store when state must survive responsive replacement.

Two simultaneous browser sessions selected independently. Resizing session A did not change session B's width, selected size, child instance, or unbound local counter.

## Geometry and topology proof

Record the Breakpoint Container's exact `getBoundingClientRect()` result at every responsive edge. In the qualified fixture, changing the viewport by one pixel changed the measured component width from exactly 900 to 899 while its x position, y position, height, and document overflow state stayed stable.

At each edge, require all of these to agree:

- the measured component width;
- `props.currentBreakpoint` as painted by an independent status binding;
- the visible small or large child marker;
- exactly one embedded child beneath the Breakpoint Container;
- official mounted-view topology showing the parent and only the selected child;
- the expected child startup count, instance identifier, and local state;
- clean browser diagnostics and classified official Gateway logs.

The tested page also had a shared dock, so official page topology contained the dock view plus the Breakpoint parent and selected child. Filter topology by exact resource path and mount path; do not mistake unrelated dock views for Breakpoint children.

## API authoring and validation

Use the official authenticated project export/import operations exposed by the live OpenAPI document when whole-project import is the selected workflow. Coordinate with the official project scan-lock operation, require tokenless rejection, and prove exact export readback after activation. Prefer a bounded folder-resource write when a compatible caller-approved agent API provides it.

`llmImport` is optional and project-scoped. Before using any of its POST actions, read its health response and require the intended action in `availableActions`. If `llmImport` is absent or incompatible, its POST route cannot be used; continue with the official Ignition OpenAPI capabilities. Do not add a Breakpoint-specific Web Dev action merely to author this component when the existing project import or general folder-resource workflow is sufficient.

Browser automation is validation-only. Author the view and page route through an API, then use a caller-approved headless client to render, measure, screenshot, and interact with the retained resource.

## Focus and accessibility boundary

The tested Breakpoint root exposed `tabIndex` -1 and no native interactive semantics. This test established responsive child selection, not keyboard interaction or an accessible control contract. Accessibility of the child content remains the responsibility of those child views.

Screen-reader behavior, focus restoration when a focused child is replaced, reduced-motion behavior, and accessibility conformance remain unqualified.

## Runtime validation checklist

1. Export the approved project, declare the exact page/view delta, and author it through an authenticated API operation.
2. Confirm tokenless rejection, authenticated success, activation, exact export readback, route HTTP 200, scan-lock availability, and no unrelated project or protected-resource drift.
3. Verify `ia.container.breakpt`, explicit numeric `props.breakpoint`, explicit `props.determinant`, and one child for each explicit `position.size` value.
4. Open two independent sessions and save exact URLs, screenshots, root geometry, status text, child state, browser diagnostics, official sessions, detailed mounted-view topology, and bounded Gateway WARN-or-higher logs at every edge.
5. Increment unbound local state in the selected large child, measure exactly the breakpoint, then one pixel below it; increment the small child; return to equality; and repeat the cross-boundary replacement.
6. Require equality to select `large`, one pixel below to select `small`, same-side instance retention, cross-boundary instance replacement, startup count 1 for every new instance, local-state reset after remount, and session-B isolation.
7. Query and classify official Gateway WARN-or-higher logs after every edge and again after delayed zero-browser-page cleanup, even when the page looks correct.
8. Re-export the project and protected resources and require exact hash parity with the accepted post-authoring baseline.

## Qualification boundary

This reference does not qualify the height determinant, omitted child `position.size`, duplicate small or large children, missing children, more than two children, dynamic breakpoint mutation, invalid determinant coercion, external property or tag bindings, nested Breakpoint Containers, focus restoration across replacement, rapid resize storms, CSS media queries, touch or mobile-browser behavior, output parameters, asynchronous scripts, security policies, accessibility conformance, or other Ignition builds. Test each separately before relying on it.
