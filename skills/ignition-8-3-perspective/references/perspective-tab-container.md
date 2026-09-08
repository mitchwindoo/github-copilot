# Perspective Tab Container

Use this reference for the live-tested Ignition 8.3.8 Perspective Tab Container. The qualified component type is `ia.container.tab`. This component owns ordinary Perspective child components; assign each child to a tab with `position.tabIndex`.

## Contents

- [Tested resource shape](#tested-resource-shape)
- [Tab headers and child assignment](#tab-headers-and-child-assignment)
- [Selection and disabled behavior](#selection-and-disabled-behavior)
- [Mounted lifecycle and runWhileHidden](#mounted-lifecycle-and-runwhilehidden)
- [Embedded header parameters](#embedded-header-parameters)
- [Focus and accessibility boundary](#focus-and-accessibility-boundary)
- [Geometry validation](#geometry-validation)
- [Runtime validation checklist](#runtime-validation-checklist)
- [Qualification boundary](#qualification-boundary)

## Tested resource shape

Place the Tab Container in a Perspective view's component tree. This is the tested classic-menu shape, with caller-selected resource paths and parameter values:

```json
{
  "type": "ia.container.tab",
  "meta": { "name": "TabContainer" },
  "props": {
    "currentTabIndex": 0,
    "menuType": "classic",
    "tabSize": {
      "width": 220,
      "height": 58
    },
    "tabs": [
      {
        "disabled": false,
        "text": "TEXT TAB A",
        "runWhileHidden": false
      },
      {
        "disabled": false,
        "viewPath": "Folder/Header View",
        "viewParams": {
          "label": "B",
          "selected": false
        },
        "width": 320,
        "runWhileHidden": true
      },
      {
        "disabled": true,
        "text": "LOCKED TAB C",
        "runWhileHidden": false
      }
    ],
    "menuStyle": {
      "backgroundColor": "#e2e8f0",
      "borderBottom": "2px solid #334155"
    },
    "contentStyle": {
      "backgroundColor": "#f8fafc",
      "border": "3px solid #334155"
    },
    "tabStyle": {
      "active": {
        "backgroundColor": "#dbeafe",
        "fontWeight": "700"
      },
      "inactive": {
        "backgroundColor": "#ffffff"
      },
      "disabled": {
        "backgroundColor": "#fee2e2"
      }
    }
  },
  "children": [
    {
      "type": "ia.display.view",
      "meta": { "name": "TabChildA" },
      "position": { "tabIndex": 0 },
      "props": {
        "path": "Folder/Child A",
        "params": {
          "label": "A",
          "message": "UNMOUNT WHEN HIDDEN"
        }
      }
    },
    {
      "type": "ia.display.view",
      "meta": { "name": "TabChildB" },
      "position": { "tabIndex": 1 },
      "props": {
        "path": "Folder/Child B",
        "params": {
          "label": "B",
          "message": "RUN WHILE HIDDEN"
        }
      }
    },
    {
      "type": "ia.display.view",
      "meta": { "name": "TabChildC" },
      "position": { "tabIndex": 2 },
      "props": {
        "path": "Folder/Child C",
        "params": {
          "label": "C",
          "message": "PROGRAMMATIC LOCKED TAB"
        }
      }
    }
  ]
}
```

## Tab headers and child assignment

`props.tabs` defines the ordered menu headers. `children` defines the content components. A child's zero-based `position.tabIndex` selects the matching header item.

The tested text header used `text`. The tested embedded-view header used `viewPath`, `viewParams`, and a numeric `width`. The tested child content used `ia.display.view`, `props.path`, and `props.params`; those parameters reached matching input parameters on each child view.

Do not put the content view path in the text header item or assume that a header descriptor embeds the content. Header and content are separate surfaces. Keep tab indices contiguous and verify every child assignment by export readback and paint.

## Selection and disabled behavior

A real pointer click on an enabled header changed `props.currentTabIndex`. With no external binding, that selection was session-local. A second simultaneous session retained its original selection and child state.

A pointer click on the tested `disabled: true` text header was a no-op. A component script could still select that same tab:

```python
tabs = self.parent.getSibling("TabContainer")
tabs.props.currentTabIndex = 2
```

That traversal is valid only for the tested hierarchy, where the Button's parent container is the Tab Container's sibling. Inspect the actual component hierarchy before copying it.

On the tested three-item list, assigning 99 settled to index 2, and assigning -1 settled to index 0. The installed client performs this correction after a component update. Do not treat an immediate same-script read as settled clamp evidence; wait for propagation and verify the painted menu plus `currentTabIndex`.

The programmatically selected disabled tab retained its disabled styling while also becoming the active tab. Disabled means that the menu item rejects its pointer handler; it does not make the index unreachable from a script.

The test observed selection through `currentTabIndex`, active CSS state, painted content, and official mounted-view topology. It did not qualify a Tab Container component event.

## Mounted lifecycle and runWhileHidden

The tested default `runWhileHidden: false` behavior was lazy and destructive:

- an unvisited inactive content child was not mounted;
- the active child mounted when first selected;
- switching away unmounted that child;
- returning created a new child instance, reran its view startup action, and reset unbound child-local state.

The tested `runWhileHidden: true` behavior was lazy and retaining:

- the content child was not pre-mounted before its first selection;
- after its first selection, switching away retained it in the DOM with `display: none` and a zero-sized rectangle;
- it remained present in the official mounted-views endpoint;
- returning restored the same instance timestamp and child-local value without rerunning startup.

This differs from the tested Accordion collapse behavior. For a Tab Container, use `runWhileHidden` only when the application actually needs the inactive component to stay mounted. A hidden-running view can keep its local state and runtime work alive.

The embedded header view was mounted in both selected and unselected states. Its lifecycle is separate from the matching content child.

## Embedded header parameters

The tested embedded header view declared input parameters `label` and Boolean `selected`. The Tab Container supplied the authored label and injected the current selection state:

- false while another tab was active;
- true while its own tab was active;
- false again when a different tab became active.

Treat `selected` as a Tab Container-owned header input in this shape. The test did not qualify header-view output propagation.

## Focus and accessibility boundary

The tested classic menu wrappers, including the embedded-view header wrapper, exposed `tabIndex` -1 and no native `role`, `aria-selected`, or `aria-disabled` attributes. The Tab Container root also exposed `tabIndex` -1.

In the exact fixture, pressing Tab from the preceding Reset Button skipped the three menu wrappers but entered the embedded header view's root Flex Container as its own focus stop. Pressing Shift+Tab returned to Reset. This does not establish tab semantics or accessible selection behavior. A text-only menu without an embedded view may have a different focus sequence.

Do not send keys to a non-focusable container after calling `focus()` and assume the container received them. In an invalid discovery attempt, focus remained on the prior Button, so Enter would have activated that Button instead of testing the tabs. Always read the actual active element before interpreting keyboard results.

Arrow-key selection, Enter/Space activation of headers, screen-reader semantics, and accessibility conformance remain unqualified.

## Geometry validation

The tested `tabSize.height` was 58 while the painted header rectangles were 56 pixels high because the menu carried a two-pixel bottom border. The text headers painted at the configured 220-pixel width, and the embedded-view header painted at its item-specific 320-pixel width.

Validate both authored values and browser rectangles. Do not fail solely because the painted content box is smaller than the authored outer menu height, and do not treat positive geometry as proof that long header or Button text is readable. Save and inspect original-resolution screenshots.

## Runtime validation checklist

1. Export the project, declare the exact page/view delta, and author it through an authenticated API operation.
2. Confirm tokenless rejection, authenticated success, activation, exact export readback, route HTTP 200, scan-lock availability, and no unrelated project/protected-resource drift.
3. Verify every `props.tabs` entry and every child `position.tabIndex` before interaction.
4. Open two browser sessions and save a screenshot, geometry, exact URL, browser diagnostics, official session data, and detailed mounted-view topology at every edge.
5. Exercise initial state, local child mutation, ordinary unmount/remount, hidden-running retention, embedded-header selection input, disabled pointer no-op, programmatic disabled selection, high/negative index clamping, and the exact focus sequence.
6. Prove ordinary versus hidden-running lifecycle from instance identity, local state, DOM display/geometry, startup evidence, and official mounted-view presence. Do not infer it from paint alone.
7. Confirm session B did not inherit session A's selection, instance, or child-local state.
8. Query and classify bounded official Gateway WARN-or-higher logs after every edge and after delayed zero-page cleanup, even when all browser diagnostics are empty.
9. Re-export the project and protected resources after runtime testing and require exact hash parity with the accepted baseline.

## Qualification boundary

This reference does not qualify modern menu mode, primitive string/number tab descriptors, dynamic tab add/remove/reorder, duplicate or sparse child indices, multiple children assigned to one index, child or header output propagation, external property/tag bindings, responsive/mobile layouts, overflow and scrolling, localization, icons, animation, security policies, touch input, Arrow/Enter/Space header activation, screen readers, full accessibility semantics, asynchronous scripts, invalid child/header paths, rapid index writes, other component children, or other Ignition builds. Test each separately before relying on it.
