# Perspective View Canvas

Use this reference only after confirming Ignition 8.3.8 or reproducing the behavior on the installed build. It qualifies one responsive two-canvas, five-child ordering fixture. Do not infer View Canvas behavior from Coordinate Container, Embedded View, Flex Repeater, Ignition 8.1, or documentation alone.

## Instance shape

The tested component used `type: "ia.display.viewcanvas"` and five ordered instance objects:

```json
{
  "viewPath": "path/to/child",
  "viewParams": {"instance": 3},
  "position": "absolute",
  "left": 0,
  "top": 30,
  "right": "auto",
  "bottom": "auto",
  "width": "250px",
  "height": "110px",
  "zIndex": 0,
  "style": {"overflow": "visible"}
}
```

The canvas set `useDefaultViewWidth: false`, `useDefaultViewHeight: false`, and a linear `0.1s` transition. Preserve the complete live-discovered objects; this is not a minimal schema.

The tested child declared one input parameter and expression-bound its label from that parameter. Discover and retain every child dependency before authoring.

## Resource and visual dependencies

A resource manifest's `files` array must match its included data files exactly. Do not copy an installed `thumbnail.png` declaration unless the thumbnail is intentionally included. Ignition can return HTTP 200, remove the missing declaration, and emit a `ProjectFileUtil` warning; reject that run.

Style Class names are project-scoped dependencies. Inventory referenced classes before copying a view across projects. If an approved class resource is unavailable, replace it with independently qualified inline styling or another approved dependency, then repeat screenshots and runtime tests. Floating text with correct DOM geometry is not adequate card-layout proof.

## Responsive fixture

The tested 802-pixel Breakpoint Container held one large and one small View Canvas:

- large: five 250-by-110 cards at left 0, 137.5, 275, 412.5, and 550, with a fan-shaped top/z pattern;
- small: five cards sharing left 275, with top values 0 through 60 in 15-pixel increments and z-indices 0 through 4.

Only one canvas painted at a time. Breakpoint transitions replaced all five mounted child views and changed their mount-path prefix while retaining the same parent session/page identity.

## In-place ordering scripts

The tested Forward and Backward handlers obtained both canvases through `getChild(...)`, iterated each `props.instances` collection, and assigned `left`, `top`, and `zIndex` members in place. They did not reorder the arrays.

Forward moved the large front card from `View 1` to `View 2`. Resizing immediately afterward showed `View 2` already front in the small canvas, proving the same script updated the inactive breakpoint canvas. Backward restored both exact authored signatures.

Identify front state from z-index, geometry, and child text. Array order is not visual order.

## Reload and fresh-session boundary

Same-session reload preserved the exact tested Forward state in both canvases. A fresh session opened after exact prior-session termination began at the authored baseline. Do not infer project persistence from same-session reload persistence.

## Targeting and accessibility

Use a locator scoped to the intended page-local component path and verify icon, visibility, and geometry. A global Button index selected an invisible shared-dock Button after reload and also made an earlier alleged Forward action execute Backward.

The tested icon-only Buttons had no accessible names in the captured tree. Do not claim keyboard, focus, or screen-reader usability without adding and separately validating an accessible label.

## Validation workflow

1. Extract the exact parent, child, breakpoint, instance, parameter, binding, script, and resource-manifest shapes using explicit UTF-8.
2. Inventory child paths, Style Classes, icons, thumbnails, and every other project-scoped dependency.
3. Author through the approved API with tokenless rejection, exact source delta, semantic readback, route, protected/inventory/helper, and bounded log gates.
4. Capture large and small screenshots; measure canvas/card geometry, z-index, clipping, styles, buttons, quality, diagnostics, accessibility, and official mounted-view topology.
5. Scope each Button to the page-local path. Assert the exact Forward/Backward coordinate and front-card signatures.
6. Resize after one action to prove or reject hidden-canvas mutation. Reconcile all child mount replacements with stable session/page identity.
7. Test same-session reload while mutated and a fresh session only after exact cleanup.
8. Keep primary errors separate from cleanup failures. Query logs at every click, resize, reload, termination, and post-close edge.
9. Run two fresh strict reproductions and bracket final work with project/protected no-drift exports.

## Qualification boundary

This reference qualifies only the exact tested two-canvas/five-child fixture, absolute pixel positions, one input parameter, one child expression, two in-place coordinate/z-index scripts, inactive-canvas mutation, large/small breakpoint remounts, same-session reload retention, fresh-session reset, visual dependency correction, scoped page-local targeting, exact-session cleanup, and no-drift evidence on the tested build. It does not qualify arbitrary instance counts, runtime add/remove/reorder, dynamic paths, other CSS units or position modes, drag/drop, other transitions, nested canvases, external child projects, writeback, events beyond the two scripts, accessible icon controls, keyboard/touch interaction, reconnect, Designer behavior, performance limits, other configurations, or other builds.

