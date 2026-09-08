# Perspective Split Container

Use this reference for the live-tested Ignition 8.3.8 Perspective Split Container. The qualified component type is `ia.container.split`. Assign its two children with `position.position`.

## Contents

- [Tested resource shape](#tested-resource-shape)
- [Position, orientation, and geometry](#position-orientation-and-geometry)
- [Dragging and bound events](#dragging-and-bound-events)
- [Child lifecycle and session isolation](#child-lifecycle-and-session-isolation)
- [Headless pointer-release safeguard](#headless-pointer-release-safeguard)
- [Focus and accessibility boundary](#focus-and-accessibility-boundary)
- [Runtime validation checklist](#runtime-validation-checklist)
- [Qualification boundary](#qualification-boundary)

## Tested resource shape

Use a String percentage for the qualified position path:

```json
{
  "type": "ia.container.split",
  "meta": { "name": "SplitContainer" },
  "props": {
    "orientation": "horizontal",
    "split": {
      "position": "40%",
      "size": 20,
      "visible": true,
      "draggable": true
    }
  },
  "events": {
    "component": {
      "onMinBoundReached": {
        "type": "script",
        "scope": "G",
        "config": { "script": "\t# Handle the minimum bound.\n" }
      },
      "onMaxBoundReached": {
        "type": "script",
        "scope": "G",
        "config": { "script": "\t# Handle the maximum bound.\n" }
      }
    }
  },
  "children": [
    {
      "type": "ia.display.view",
      "meta": { "name": "PrimaryChild" },
      "position": { "position": "left" },
      "props": {
        "path": "Folder/Primary Child",
        "params": {},
        "style": { "height": "100%", "width": "100%" }
      }
    },
    {
      "type": "ia.display.view",
      "meta": { "name": "GrowChild" },
      "position": { "position": "right" },
      "props": {
        "path": "Folder/Grow Child",
        "params": {},
        "style": { "height": "100%", "width": "100%" }
      }
    }
  ]
}
```

The installed defaults observed on this build were horizontal orientation, `"50%"`, size 16, visible true, and draggable true. Declare the values that matter instead of relying on defaults.

## Position, orientation, and geometry

For horizontal orientation, use `left` and `right`. For vertical orientation, use `top` and `bottom`. In the tested runtime, changing `props.orientation` from `horizontal` to `vertical` remapped the existing left/right children to top/bottom; changing it back restored left/right without restarting the children.

The visible handle consumes `props.split.size`. Percentage position divides the remaining pane space, not the outer component rectangle. In the tested 1246-by-698 inner Split rectangle with a 20-pixel handle:

- horizontal 40% painted panes of 490.390625 and 735.609375 pixels;
- horizontal 53% painted panes of 649.765625 and 576.234375 pixels;
- vertical 40% painted panes of 271.1875 and 406.8125 pixels;
- vertical 57% painted panes of 386.453125 and 291.546875 pixels.

For either orientation, require `primary pane + handle + grow pane` to equal the Split rectangle on the active axis. Keep the authored outer component rectangle distinct from the inner Split rectangle and save original-resolution screenshots.

Setting `props.split.position` from a component script worked in the tested hierarchy:

```python
container = self.parent.getSibling("SplitContainer")
container.props.split.position = "40%"
```

Inspect the actual component hierarchy before copying that traversal.

## Dragging and bound events

A real pointer drag changed `props.split.position` and settled to a rounded percentage String. The tested positive horizontal gesture moved 40% to 53%; the tested vertical gesture moved 40% to 57%.

At the tested minimum, position settled to `"0%"`, the primary pane painted at zero pixels, and `onMinBoundReached` fired once. At the tested maximum, position settled to `"100%"`, the grow pane painted at zero pixels, and `onMaxBoundReached` fired once. Both event payloads exposed no keys in the tested scripts.

Reset to a non-bound position between independent minimum and maximum probes. At a zero-width pane, overflowing child content can cover the handle and invalidate a second pointer start from that extreme.

With `props.split.draggable = false`, the handle remained visible, gained the tested undraggable class and `not-allowed` cursor, and the same pointer gesture changed neither position, geometry, nor event counts. Re-enable it with `props.split.draggable = true`.

Do not accept the property value alone as drag proof. Require all of these to agree after release:

- the reported `split.position`;
- both pane rectangles and the handle rectangle;
- the expected event identity and count at a bound;
- an inactive handle;
- unchanged child instance/state evidence;
- clean browser diagnostics and classified Gateway logs.

## Child lifecycle and session isolation

Both embedded children remained mounted throughout every tested drag, bound, reset, disabled, and orientation edge. Their startup counts, instance identifiers, and unbound local counters remained unchanged after the initial local mutations. Official mounted-view topology continued to report the parent plus both children in each page.

The Split state was session-local in the unbound fixture. A simultaneous second browser session retained horizontal 40%, draggable true, zero event counts, zero local counters, and different child-instance identifiers while session A exercised every edge.

## Headless pointer-release safeguard

In the retained API-authored fixture, a drag that wrote `split.position` could trigger a server echo and component update before Playwright's native mouse release cleared the Split's body-level drag state. The visible symptom was an `isActive` handle with a new property value but stale pane geometry. A later pointer move could then create a false bound event.

For the qualified headless verifier, keep the real Playwright mouse down, move, and up. Immediately dispatch a matching bubbling `mouseup` on `document.body` as a release safeguard, because the installed Split client registers its release handler there. Do not replace the real pointer movement with a property write. Afterward, require the handle to lack `isActive` and require geometry to match the reported percentage.

Treat this as a validation-harness safeguard for the exact tested build and bound fixture, not as an application script or a general browser requirement. Preserve invalid race traces instead of silently retrying them.

## Focus and accessibility boundary

The tested Split root and handle exposed `tabIndex` -1. The handle exposed no native `role` or `aria-orientation`. Its cursor changed between `col-resize`, `row-resize`, and `not-allowed`, but that does not establish keyboard resizing or accessible separator semantics.

Keyboard resize, screen-reader behavior, and accessibility conformance remain unqualified.

## Runtime validation checklist

1. Export the project, declare the exact page/view delta, and author it through an authenticated API operation.
2. Confirm tokenless rejection, authenticated success, activation, exact export readback, route HTTP 200, scan-lock availability, and no unrelated project/protected-resource drift.
3. Verify `ia.container.split`, the nested `props.split` members, both event names, and each child `position.position` in export readback.
4. Open two sessions and record exact URL, screenshots, Split/pane/handle geometry, handle classes, child state, browser diagnostics, official session data, and detailed mounted-view topology at every edge.
5. Exercise initial 40%, bounded horizontal drag, independent minimum and maximum probes, reset, disabled-drag no-op, re-enable, vertical orientation, vertical drag, reset, and final horizontal restoration.
6. Correlate position, geometry, event identity/count, empty payload keys, retained child instances/state, and session-B isolation.
7. Query and classify bounded official Gateway WARN-or-higher logs after every edge and after delayed zero-page cleanup.
8. Re-export the project and protected resources after runtime testing and require exact hash parity with the accepted baseline.

## Qualification boundary

This reference does not qualify numeric/pixel position, hidden handles, touch drag, keyboard resize, more or fewer than two children, duplicate positions, dynamic child replacement, rapid alternating orientation, external property or tag bindings, responsive/mobile resizing, output parameters, asynchronous scripts, accessibility conformance, security policies, overflow behavior beyond the observed zero-width test warning, other child component types, or other Ignition builds. Test each separately before relying on it.
