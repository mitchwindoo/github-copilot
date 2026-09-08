# Perspective generic Tree

This reference covers the generic `ia.display.tree` behavior reproduced twice on Ignition 8.3.8 with Perspective 3.3.8. Test other builds and unlisted interactions independently.

## Contents

- [Component shape](#component-shape)
- [Items and appearance](#items-and-appearance)
- [Selection behavior](#selection-behavior)
- [External selection boundary](#external-selection-boundary)
- [Expansion and dynamic items](#expansion-and-dynamic-items)
- [Read-only Document-tag model](#read-only-document-tag-model)
- [Guarded Document-object mutation](#guarded-document-object-mutation)
- [Interaction flags and events](#interaction-flags-and-events)
- [Script serialization](#script-serialization)
- [Runtime validation](#runtime-validation)
- [Boundaries](#boundaries)

## Component shape

Use this tested top-level shape:

```json
{
  "type": "ia.display.tree",
  "meta": {"name": "Tree"},
  "props": {
    "interactable": true,
    "branchNodeSelectable": true,
    "items": [],
    "selection": [],
    "appearance": {
      "textOverflow": "truncate",
      "rowHeight": 40,
      "selectedStyle": {"backgroundColor": "#2563eb", "color": "#ffffff"},
      "unselectedStyle": {"backgroundColor": "#ffffff", "color": "#0f172a"}
    },
    "style": {}
  }
}
```

The installed wrapper uses multiple-selection mode. It exposes `selection` and `selectionData` as separate arrays and writes both only when its internal selection-change callback runs.

## Items and appearance

Each node requires `label`, `expanded`, and `items`. `data` and `icon` are optional:

```json
{
  "label": "Pump A",
  "expanded": false,
  "icon": {"path": "material/settings", "style": {"color": "#2563eb"}},
  "data": {"id": "P-A", "running": true},
  "items": []
}
```

Nested children form the visible hierarchy. `appearance.rowHeight` controls each row. `appearance.textOverflow: "truncate"` truncates long node labels. Constrain long diagnostic labels separately with `overflow: "hidden"`, `whiteSpace: "nowrap"`, and `textOverflow: "ellipsis"`; screenshots are required to detect vertical overlap.

## Selection behavior

`selection` contains String item-index paths such as `0/1`. Property or expression traces can display those strings wrapped with quality and timestamp metadata; do not mistake the rendered wrapper for the underlying path type.

For the tested expanded hierarchy:

- A plain pointer click replaced the prior selection.
- Ctrl-click appended or removed one path while retaining action order in `selection`.
- A settled Shift-click selected the inclusive visible range between its anchor and endpoint, including a visible branch node between terminal nodes.
- DOM paint order followed tree order, which can differ from ordered `selection` output.

`selectionData` contains objects shaped like `{itemPath, value}`. Internal pointer selection updated it with the selected node's authored `data`. Tested object, numeric, and String values remained distinguishable.

## External selection boundary

Binding `props.selection` bidirectionally to view state allowed external assignment to control selection paint:

```json
"propConfig": {
  "props.selection": {
    "binding": {
      "type": "property",
      "config": {"path": "view.custom.selectionPaths", "bidirectional": true}
    }
  }
}
```

External assignment changed `selection` and painted the node at that path. It did not recompute `selectionData`. External `[]` cleared paths and paint while retaining the prior `selectionData` snapshot through a delayed check and later item/expansion changes.

Treat these as separate state:

1. selected path strings;
2. painted occupants at those paths;
3. the last internally generated `selectionData` snapshot.

Do not read `selectionData` as authoritative after external selection writes unless an independently tested workflow refreshes it.

## Expansion and dynamic items

When `props.items` was bidirectionally bound to a view-custom array, pointer expansion wrote the exact nested `expanded` Boolean back through the binding.

Do not carry that result over to a direct Document-tag binding. On the tested build, setting `bidirectional:true` on a direct tag binding from Tree `props.items` to a Document tag was destructive: expanding one nested branch wrote the scalar Boolean `true` over the entire Document value and both concurrent Trees immediately lost all items. The same fresh-fixture sequence reproduced twice, with independent typed tag readback proving the scalar replacement each time.

Use a read-only direct Document-tag binding for `props.items` unless a separately tested, explicit whole-document write workflow is required:

```json
"props.items": {
  "binding": {
    "type": "tag",
    "config": {
      "mode": "direct",
      "tagPath": "[provider]path/to/items",
      "fallbackDelay": 2.5
    }
  }
}
```

Do not add `bidirectional:true` to this direct structured binding. If branch expansion or other nested edits must be persisted, implement and test an explicit read-copy-mutate-write boundary with exact type, quality, value, concurrency, and Gateway-log checks; the generic Tree binding alone is not a safe structured write contract.

## Read-only Document-tag model

A direct read-only binding from `props.items` to a Document memory tag accepted a complete array of Tree nodes. Authenticated whole-Document imports through the official tag-import endpoint propagated reordered, removed, and restored item arrays to two concurrent sessions without project mutation or navigation.

The same index-path boundaries described above still apply across shared tag updates:

- Reordering children retained a selected path and its prior `selectionData`; paint followed the new visible occupant at that index.
- Collapsing a branch through the imported model hid a selected descendant without clearing its path or data snapshot.
- Removing the selected index left its path and old data intact while no node was painted.
- Restoring the original hierarchy did not repaint a stale path automatically.
- Assigning `[]` through the tested local selection binding cleared paths and paint but retained the prior `selectionData` snapshot.

In the tested two-session sequence, reloading one browser page retained the same official session and page identifiers. With selection bound to a persistent view-custom property, the path and `selectionData` survived while selected paint cleared. The other session remained unchanged. Treat reload identity, retained property state, and component paint as separate observations.

For API verification, compare parsed Document values recursively; object-member order can change in official exports. A semantically changed official import advanced the tag timestamp, while importing an already-identical Document could leave the timestamp unchanged. Require advancement only when the value actually changes.

The official API supplied tag import/export but no runtime typed Document read on the tested Gateway. When a compatible optional agent API advertises `tag-read-complex-v1`, it can provide bounded value/type/quality/timestamp evidence for nested Documents. If that optional API is absent, omit the call and use only available official endpoints; do not assume generic scalar-read actions preserve arbitrary nesting.

## Guarded Document-object mutation

For an explicit runtime-write workflow, use an object-root Document and bind Tree `props.items` read-only to its nested array:

```json
"props.items": {
  "binding": {
    "type": "tag",
    "config": {
      "mode": "direct",
      "tagPath": "[<provider>]<approved-folder>/<document-tag>['items']",
      "fallbackDelay": 2.5
    }
  }
}
```

A compatible optional `llmImport` 0.61.0 action, `tag-document-cas-v1`, was reproduced twice with two concurrent read-only Trees. A no-precondition dry run returned opaque server-issued timestamp/hash tokens; apply required the exact pair, an object-root replacement, `dryRun:false`, and `apply:true`. Three changed writes per run propagated to both sessions. Stale timestamp, stale hash, outside-prefix, scalar-root, oversized-value, and missing-precondition controls all reported no write; an already-identical apply also performed no write.

The action is optimistic, not atomic: it checks the timestamp/hash immediately before one blocking write, but another writer can race between those operations. See [Guarded Document tag writes](perspective-document-tag-writes.md) for the full contract and evidence gates.

Do not generalize this to a root-array runtime write. A Python-list write to a root-array Document read back semantically yet changed runtime representation and did not update either open Tree, with no browser or Gateway warning. Official whole-Document import remains qualified for the root-array workflow described above; the guarded runtime writer is qualified only for an object root containing the `items` array.

Selection remained index-path based during whole-list mutation. Reordering two children retained path `0/0`; paint moved to the new occupant while `selectionData` retained the previous occupant's data. Removing the originally selected node compacted another node into `0/0`, painted that node, and again left the old data snapshot. Restoring the original list moved paint back without refreshing the snapshot.

Clear or deliberately reconcile selection before reordering/removing items when identity, not position, matters. Do not assume Tree performs key-based reconciliation.

## Interaction flags and events

Place `onItemClicked` under `events.component`:

```json
"events": {
  "component": {
    "onItemClicked": {
      "type": "script",
      "scope": "G",
      "config": {"script": "\tself.view.custom.lastPath = str(event.itemPath)"}
    }
  }
}
```

After `branchNodeSelectable:false` had settled, a normal branch-label click emitted `onItemClicked` but did not change selection. After `interactable:false` had settled, a normal terminal-label click also emitted the event without changing selection. Therefore neither flag is an event-suppression boundary on the tested build.

`event.itemPath` arrived in Gateway Jython as an array. Tested `event.data` types were `PyJsonObjectAdapter` for an object, `long` for a JSON integer, and `str` for a String. Test arrays, nulls, floating-point values, and other nested shapes independently.

## Script serialization

Perspective stores only the indented function body in `config.script`. Do not store the outer `def runAction(self, event):` line, and do not strip the body's leading indentation.

Validate the exact stored form by compiling `"def runAction(self, event):\n" + storedBody` with the target Jython runtime. Compiling the unindented body alone can pass locally while Ignition later rejects the generated action with an expected-indent error. Runtime execution plus bounded Gateway-log inspection remains mandatory.

## Runtime validation

For every accepted state:

1. Capture visible row labels, `data-item-path`, selected paint, and exact trace values.
2. Capture a screenshot and verify row/card geometry, clipping, and long-text containment.
3. Inspect normal pointer, Ctrl, and settled Shift behavior in one browser process.
4. Correlate the exact session, page, view, component, and binding counts through official APIs.
5. Query and classify the bounded official Gateway WARN-or-higher window, including failed actions and post-close cleanup.
6. Terminate only the exact test session through the official session API and prove no matching session remains.
7. Export twice and prove the target and protected projects remained unchanged during runtime testing.

## Boundaries

The evidence does not establish keyboard-only navigation, focus behavior, touch/mobile interaction, drag/drop, lazy or recursive loading, very large trees, concurrent item writers, null/malformed paths, duplicate labels, custom CSS beyond the tested styles, reload/reconnect persistence, Designer behavior, redundancy, or other Ignition/Perspective builds. Test each independently.
