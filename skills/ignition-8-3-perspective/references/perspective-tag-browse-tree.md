# Perspective Tag Browse Tree

Use `ia.display.tag-browse-tree` only after inspecting the installed component descriptor and client implementation on the target build. The behavior below was reproduced twice on Ignition 8.3.8 with Perspective 3.3.8.

## Contents

- [Component shape](#component-shape)
- [Filtering extension](#filtering-extension)
- [Selection behavior](#selection-behavior)
- [Filter and refresh reset](#filter-and-refresh-reset)
- [Node events](#node-events)
- [Runtime validation](#runtime-validation)
- [Boundary](#boundary)

## Component shape

Use a caller-approved tag root and retain the refresh icon while qualifying the component:

```json
{
  "meta": {"name": "TagBrowseTree"},
  "props": {
    "root": {"path": "[ApprovedProvider]Approved Folder"},
    "filter": {"enabled": true, "text": ""},
    "selection": {"mode": "single", "values": []},
    "display": {
      "refreshIcon": {
        "visible": true,
        "path": "material/refresh",
        "style": {}
      }
    },
    "style": {}
  },
  "type": "ia.display.tag-browse-tree"
}
```

The installed descriptor accepts `single` and `multiple` for `props.selection.mode`. It describes `props.selection.values` as selected tag paths in selection order. Runtime and installed-client evidence confirmed ordered path strings.

Treat `props.selection.values` as an output trace on this build. The Tag Browse Tree writes it when its internal Tree selection changes, but does not feed it back into that internal Tree. Assigning `[]` externally empties the property while the old row remains painted as selected, including after a delayed stability check. Do not create an external Clear button by assigning this property and claim that the visible selection cleared.

## Filtering extension

Serialize `filterBrowseNode` under `scripts.extensionFunctions`, using an indented function body rather than the outer `def` wrapper:

```json
{
  "scripts": {
    "customMethods": [],
    "extensionFunctions": [
      {
        "enabled": true,
        "name": "filterBrowseNode",
        "script": "\tname = unicode(node.name)\n\tif name == \"ExcludedName\":\n\t\treturn False\n\treturn str(node.objectType) in (\"AtomicTag\", \"Folder\")"
      }
    ],
    "messageHandlers": []
  }
}
```

The tested extension received `self` and `node`, excluded one named node, and admitted `AtomicTag` and `Folder` object types. Independent tag reads remained necessary to prove that filtering affected paint rather than deleting or corrupting source tags.

## Selection behavior

In the tested `single` mode, clicking a different node replaced the selected path.

In the tested `multiple` mode:

- A plain click replaced the current selection; it did not accumulate.
- Ctrl-click added an unselected node and removed an already selected node.
- Shift-click selected the flattened inclusive range from the settled anchor. The tested range included a folder because this Tag Browse Tree made branches selectable.
- Selection output preserved interaction/range order even when DOM queries naturally returned painted nodes in tree order.

Keep modifier down, perform the pointer click, and release the modifier in one browser process. Cross-command automation can lose modifier state. Allow the anchor click to settle before Shift-click; an immediate second command can race the component's React state update and collapse the result to the second node.

Expression rendering may show quality and timestamp wrappers around the path values. That display is not evidence that the component property changed from ordered strings. Validate order from the installed handler, painted selection, event paths, and the sequence in the output trace.

## Filter and refresh reset

Native typing into the filter is debounced. While typing, the input can display text before `props.filter.text` updates because the tested component wrote that property on blur.

The tested native Ctrl+A followed by Backspace while filtering invoked reset-browse, restored collapsed roots, and cleared both internal selection paint and `selection.values`. Programmatic empty-fill was not equivalent to this native keyboard path.

Clicking the visible refresh icon while browsing also invoked reset-browse, rebuilt the collapsed roots, and cleared both paint and the output trace. Use a native filter reset or refresh reset when visible clearing is required; do not substitute an external write to `selection.values`.

## Node events

The tested component accepted `onNodeClick`, `onNodeDoubleClick`, and `onNodeContextMenu` under `events.component`. Each handler received `event.name` and the full `event.path`.

A native automated double-click produced two click events plus one double-click event in both strict runs. Treat that count as gesture/browser evidence, not a universal event-count guarantee. The tested context-menu event reported the right-clicked node without changing the existing selection.

## Runtime validation

For each accepted interaction state:

1. Capture a full-page screenshot, visible rows, selected paint, input value, trace text, viewport geometry, console errors, page errors, and failed requests.
2. Query official session, page, and mounted-view topology; require one connection and zero reconnects for the stable single-page test.
3. Read every source tag independently and require expected value/type/quality without writes.
4. Query and classify the bounded official Gateway WARN-or-higher window even when paint and browser diagnostics are clean.
5. Close the browser, terminate the exact test session through the official API when needed, and inspect the post-close log window.

Include single replacement, mode transition, Ctrl add/remove, plain replacement in multiple mode, settled Shift range, filter persistence, native filter clear, double-click, context-menu, external property-clear divergence, native refresh reset, and delayed stability. Inspect representative screenshots at original resolution for clipping and stale paint.

## Boundary

This qualifies one nested memory-tag tree, one name/type filter extension, pointer selection, native filter clearing, refresh reset, and three node events on the tested build. It does not qualify UDT browsing, tag security denial, remote providers, alarms, history, dynamic root replacement, touch/mobile gestures, keyboard tree navigation, macOS Meta behavior, Ctrl+Shift union, disabled filtering, Designer behavior, other browsers, or other Ignition/Perspective builds. Test each separately.
