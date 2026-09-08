# Perspective Accordion

Use this reference for the live-tested Ignition 8.3.8 Perspective Accordion component. The qualified component type is `ia.display.accordion`. Runtime behavior in this reference is limited to `expansionMode: "single"`.

## Contents

- [Tested resource shape](#tested-resource-shape)
- [Component events](#component-events)
- [Runtime behavior](#runtime-behavior)
- [Script and hierarchy cautions](#script-and-hierarchy-cautions)
- [Runtime validation checklist](#runtime-validation-checklist)
- [Qualification boundary](#qualification-boundary)

## Tested resource shape

Place the component in a Perspective view's component tree. This is the tested shape, with caller-selected view paths and parameters:

```json
{
  "type": "ia.display.accordion",
  "meta": { "name": "Accordion" },
  "props": {
    "expansionMode": "single",
    "items": [
      {
        "expanded": true,
        "header": {
          "content": {
            "type": "text",
            "text": "Section A",
            "viewPath": "",
            "viewParams": {},
            "useDefaultViewHeight": false,
            "useDefaultViewWidth": false,
            "style": {}
          },
          "height": "56px",
          "reverse": false,
          "style": {},
          "toggle": {
            "enabled": true,
            "collapsedIcon": {
              "path": "material/expand_more",
              "color": "#334155",
              "style": {}
            },
            "expandedIcon": {
              "path": "material/expand_less",
              "color": "#334155",
              "style": {}
            }
          }
        },
        "body": {
          "height": "170px",
          "viewPath": "Folder/Body View",
          "viewParams": {
            "label": "A",
            "message": "ALPHA"
          },
          "useDefaultViewHeight": false,
          "useDefaultViewWidth": false,
          "style": { "margin": "8px" }
        }
      }
    ],
    "style": {},
    "unusedSpaceStyle": {}
  }
}
```

For an embedded view header, replace `header.content` with the following tested shape:

```json
{
  "type": "view",
  "text": "",
  "viewPath": "Folder/Header View",
  "viewParams": {
    "label": "B",
    "message": "REVERSED VIEW HEADER"
  },
  "useDefaultViewHeight": false,
  "useDefaultViewWidth": false,
  "style": {}
}
```

Set `header.reverse` to `true` to place the tested chevron on the right. Set `header.toggle.enabled` to `false` to block pointer toggling while retaining programmatic control of the item's `expanded` member. Header and body `viewParams` reached matching input parameters in the embedded views.

## Component events

The installed component exposes `onItemExpanded` and `onItemCollapsed`. Put both under `events.component`:

```json
{
  "events": {
    "component": {
      "onItemExpanded": {
        "type": "script",
        "scope": "G",
        "config": {
          "script": "\tindex = int(event.index)\n"
        }
      },
      "onItemCollapsed": {
        "type": "script",
        "scope": "G",
        "config": {
          "script": "\tindex = int(event.index)\n"
        }
      }
    }
  }
}
```

On this build, `event.index` was a Jython `long`, and `event.keys()` contained only `index`. No event fired merely because the view mounted with an initially expanded item. In single mode, opening one item can collapse the previously open item and therefore fire both event types. Do not depend on their relative order; preserve separate evidence for each event when order matters.

## Runtime behavior

- Opening an item in tested single mode collapsed the previously open item. An open item could also be collapsed so that no item remained open.
- Collapsing a body did not unmount its embedded view. The body remained in the DOM with a collapsed class and near-zero height, and child-local state was retained when the item reopened.
- Because collapsed child controls remain mounted, a page-wide role locator can still find them. Scope browser automation to the intended Accordion body index before locating a child control.
- A pointer click on a header with `toggle.enabled: false` was a no-op. Assigning that item's `expanded` member from a component script still opened it.
- A reversed embedded-view header rendered its chevron on the opposite side and received the tested input parameters.
- Two simultaneous browser sessions retained independent expansion, event-count, and child-local state when no external binding was used.
- Tested headers had `tabIndex` 1, but pressing Enter on a focused header was a no-op. Do not claim keyboard activation or accessibility conformance from this fixture.

## Script and hierarchy cautions

Mutate only the intended item member, for example:

```python
accordion = self.parent.getSibling("Accordion")
accordion.props.items[2].expanded = True
```

That traversal is valid only when the triggering component is inside a container that is an immediate sibling of the Accordion. A nested Button calling `self.getSibling("Accordion")` returned `None` in the tested hierarchy and produced a `perspective.actions.script` WARN. Inspect the actual component hierarchy and qualify each traversal; do not copy this expression blindly.

In Flex layouts, give adjacent long-label controls enough width and visually inspect the rendered text. Equal controls were qualified with `basis: "0px"`, `grow: 1`, and `shrink: 1`; positive rectangles alone did not detect the original text clipping.

## Runtime validation checklist

1. Export the project, declare the exact view/page delta, and apply it through an authenticated API operation.
2. Read the view and page configuration back exactly and confirm the route returns HTTP 200.
3. Open two independent browser sessions and save a screenshot plus geometry at every edge.
4. Verify initial state, child-local mutation, single-mode replacement, collapse-to-none, reopen with retained child state, disabled pointer no-op, programmatic open, and reset.
5. Record `onItemExpanded` and `onItemCollapsed` independently, including `event.index` and its runtime type.
6. Confirm collapsed bodies remain mounted and scope locators by body index.
7. Query and classify bounded official Gateway WARN-or-higher logs after every edge and after delayed page cleanup, even when browser diagnostics are empty.
8. Confirm the second session did not inherit the first session's local state and that runtime testing caused no project or protected-resource drift.

## Qualification boundary

This reference does not qualify multiple-expansion runtime behavior, child output-parameter propagation, dynamic item add/remove/reorder, content types other than tested text and embedded-view headers, touch/mobile interaction, keyboard behavior beyond the Enter no-op, ARIA or screen-reader behavior, animation, embedded-view output writeback, child lifecycle event counts, invalid or missing view paths, asynchronous mutation, or other Ignition builds. Test each separately before relying on it.
