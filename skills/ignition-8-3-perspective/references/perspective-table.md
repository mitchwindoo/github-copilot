# Perspective Table

Use this reference for the live-tested static array-of-object and direct memory-Dataset Table boundaries on Ignition 8.3.8 with Perspective 3.3.8. Inspect the installed component descriptor and a current exported seed before authoring on another build.

## Contents

- [Tested component shape](#tested-component-shape)
- [Tested selection event](#tested-selection-event)
- [Tested String-column sorting](#tested-string-column-sorting)
- [Selection after descending sorting](#selection-after-descending-sorting)
- [Tested bottom pagination](#tested-bottom-pagination)
- [Tested page-size changes](#tested-page-size-changes)
- [Tested selection across pages](#tested-selection-across-pages)
- [Paged selection event payloads](#paged-selection-event-payloads)
- [Same-row second click](#same-row-second-click)
- [Programmatic selected-row clear attempt](#programmatic-selected-row-clear-attempt)
- [Programmatic selection-data clear attempt](#programmatic-selection-data-clear-attempt)
- [Programmatic two-member assignment order](#programmatic-two-member-assignment-order)
- [Bound-data refresh then selected-row clear](#bound-data-refresh-then-selected-row-clear)
- [Bound-data selected-row removal](#bound-data-selected-row-removal)
- [Bound-data selected last-row removal](#bound-data-selected-last-row-removal)
- [Bound-data empty result and restore](#bound-data-empty-result-and-restore)
- [Bound-data same-index record replacement](#bound-data-same-index-record-replacement)
- [Bound-data selected-record reorder](#bound-data-selected-record-reorder)
- [Bound-data list-index object assignment](#bound-data-list-index-object-assignment)
- [Bound-data nested scalar assignment](#bound-data-nested-scalar-assignment)
- [Bound-data sequential nested writes](#bound-data-sequential-nested-writes)
- [Direct memory-Dataset binding](#direct-memory-dataset-binding)
- [Typed Dataset rendering and numeric sorting](#typed-dataset-rendering-and-numeric-sorting)
- [Dataset replacement with two sessions](#dataset-replacement-with-two-sessions)
- [Dataset shrink clear and automatic reselection](#dataset-shrink-clear-and-automatic-reselection)
- [Schema-preserving empty Dataset and restore](#schema-preserving-empty-dataset-and-restore)
- [Reordered Dataset columns and one extra field](#reordered-dataset-columns-and-one-extra-field)
- [Missing configured Dataset field with one extra field](#missing-configured-dataset-field-with-one-extra-field)
- [Missing configured Dataset field with no extra field](#missing-configured-dataset-field-with-no-extra-field)
- [Selection handler access to a removed Dataset member](#selection-handler-access-to-a-removed-dataset-member)
- [Guarded access to a removed Dataset member](#guarded-access-to-a-removed-dataset-member)
- [Record `get` with a default](#record-get-with-a-default)
- [Record membership and default collisions](#record-membership-and-default-collisions)
- [Record key enumeration](#record-key-enumeration)
- [Record item enumeration](#record-item-enumeration)
- [Record values and mapping alignment](#record-values-and-mapping-alignment)
- [Direct record iteration](#direct-record-iteration)
- [Record length](#record-length)
- [Dictionary snapshot conversion](#dictionary-snapshot-conversion)
- [Dictionary snapshot top-level mutation](#dictionary-snapshot-top-level-mutation)
- [Runtime evidence gate](#runtime-evidence-gate)
- [Boundary](#boundary)

## Tested component shape

The tested component type is `ia.display.table`. Its relevant stored properties follow this shape:

```json
{
  "type": "ia.display.table",
  "props": {
    "data": [
      {"name": "ALPHA", "status": "ACTIVE", "value": 11},
      {"name": "BRAVO", "status": "IDLE", "value": 22},
      {"name": "CHARLIE", "status": "ALARM", "value": 33}
    ],
    "virtualized": true,
    "selection": {
      "mode": "single",
      "enableRowSelection": true,
      "enableColumnSelection": false,
      "selectedColumn": null,
      "selectedRow": null,
      "data": [],
      "style": {"backgroundColor": "#dbeafe"}
    },
    "enableHeader": true,
    "enableFooter": false,
    "columns": [
      {
        "field": "name",
        "visible": true,
        "editable": false,
        "render": "string",
        "justify": "left",
        "align": "center",
        "resizable": true,
        "sortable": true,
        "sort": "none",
        "width": "38%",
        "strictWidth": false,
        "header": {"title": "NAME", "justify": "left", "align": "center", "style": {"classes": ""}},
        "style": {}
      }
    ],
    "dragOrderable": false,
    "sortOrder": [],
    "resizeMode": "fill"
  }
}
```

Repeat the column object for each data field and set its `field`, `render`, justification, width, and header title explicitly. Exact export readback proved three complete column objects. Do not infer omitted defaults or rely on percentage widths as exact painted widths when `resizeMode` is `fill`; the tested client distributed the three columns equally despite stored 38/32/30 percent values.

The installed descriptor allowed array or dataset data. Only the displayed three-row array-of-object form above received runtime qualification; dataset behavior remains untested.

## Tested selection event

Store the script beneath `events.component.onSelectionChange`:

```json
{
  "events": {
    "component": {
      "onSelectionChange": {
        "config": {
          "script": "\trow = event.selectedRow\n\tdata = list(event.data)\n\tif row is None:\n\t\tself.view.custom.selectedRow = -1\n\t\treturn\n\tif len(data) != 1:\n\t\traise ValueError(\"selection_count:%s\" % len(data))\n\trecord = data[0]\n\tself.view.custom.selectedRow = int(row)\n\tself.view.custom.selectedName = str(record[\"name\"])\n\tself.view.custom.selectedStatus = str(record[\"status\"])\n\tself.view.custom.selectedValue = int(record[\"value\"])\n\tself.view.custom.eventCount = int(self.view.custom.eventCount) + 1"
        },
        "scope": "G",
        "type": "script"
      }
    }
  }
}
```

Declare the referenced view custom properties and initialize them before import. Compile the stored script with the target Jython 2.7 runtime before authoring. Keep validation guards appropriate to the caller's fixed data contract.

## Tested String-column sorting

For the static three-row object array above, the STATUS column stored `sortable: true` and `sort: "none"`, while the Table stored `sortOrder: []`. A fresh client initially painted source order:

```text
ALPHA/ACTIVE, BRAVO/IDLE, CHARLIE/ALARM
```

One pointer click on the STATUS header painted ascending String order:

```text
ALPHA/ACTIVE, CHARLIE/ALARM, BRAVO/IDLE
```

A second pointer click on the same header painted descending String order:

```text
BRAVO/IDLE, CHARLIE/ALARM, ALPHA/ACTIVE
```

A third pointer click cleared the sort and restored the original source order. All transitions occurred in one unchanged session/page. With no prior selection, selection stayed empty and `onSelectionChange` did not execute. Validate sorting from complete painted row order, not only from the arrow icon or stored `sort`/`sortOrder` defaults.

## Selection after descending sorting

For the exact descending STATUS order `BRAVO, CHARLIE, ALPHA`, `event.selectedRow` remained the original source-array index rather than the current displayed position:

| Selected record | Displayed position | `event.selectedRow` | `event.data[0]` |
| --- | ---: | ---: | --- |
| CHARLIE | 1 | 2 | CHARLIE / ALARM / 33 |
| BRAVO | 0 | 1 | BRAVO / IDLE / 22 |

The selected highlight painted at the displayed position and moved from CHARLIE to BRAVO. The guarded script execution count advanced from 0 to 1 to 2. When a Table can be sorted, do not use `event.selectedRow` as a displayed-row offset; use it as the tested source index and validate the selected record from `event.data`.

When CHARLIE was selected in descending display position 1 and the STATUS header was clicked a third time, the source order returned and the same selection followed CHARLIE to display position 2. `onSelectionChange` did not run again: the visible source index, payload fields, and event count remained CHARLIE / 2 / 1. A later ALPHA click emitted source index 0 and advanced the event count to 2.

Selection paint may move between DOM levels during a reorder. Before reset, the tested row container carried a translucent selection background. After reset, the row container was transparent while three descendant selection cells carried the configured opaque `#dbeafe`. Validate the full painted row and relevant descendants plus screenshot pixels; do not treat the row container's background alone as the selection state.

## Tested bottom pagination

For one static 30-row array-of-object Table, the following stored pager object activated a bottom-only pager with ten visible rows per page:

```json
{
  "pager": {
    "options": [10, 25, 50],
    "activeOption": 10,
    "top": false,
    "bottom": true,
    "activePage": 1,
    "style": {}
  }
}
```

The installed descriptor identified `activeOption` as the current page size and marked `initialOption` deprecated. Inspect the descriptor again on another build rather than copying an older property name.

At 1280 by 720 with DPR 1, the exact bottom controls showed page buttons 1, 2, and 3 and a visible `10 rows` chooser. Pointer clicks in one unchanged session/page produced:

| State | Active page | Painted rows |
| --- | ---: | --- |
| Initial | 1 | `ROW-01` through `ROW-10` |
| Click page 2 | 2 | `ROW-11` through `ROW-20` |
| Click page 3 | 3 | `ROW-21` through `ROW-30` |
| Click page 1 | 1 | `ROW-01` through `ROW-10` |

The exact active-page class moved 1 -> 2 -> 3 -> 1, the top pager remained absent, and official runtime reads stayed at one session/page with zero reconnects. Apply the focused page-size workflow below before making claims about the chooser or changing its value.

## Tested page-size changes

Opening the native page-size `<select>` for the exact stored `[10, 25, 50]` configuration displayed this runtime option sequence on Ignition 8.3.8 / Perspective 3.3.8:

```text
10 rows, 25 rows, 50 rows, 50 rows, 100 rows
```

The first `50 rows` came from the stored options; the runtime also appended its default `50 rows` and `100 rows`, producing a duplicate value 50. This was confirmed from the opened chooser screenshot and the exact `<option>` sequence in both fresh confirmation sessions. Do not assume `pager.options` replaces the runtime defaults, deduplicate values automatically, or limits the chooser to the stored array on this build. Also do not infer that selecting the appended or duplicate options works; only 10 and 25 were selected.

Selecting 25 from the initial ten-row page changed the pager from three pages to two and kept page 1 active. Because the tested Table stored `virtualized: true`, all 25 rows were not mounted or painted simultaneously at the 1280 by 720 viewport:

| 25-row page state | Mounted overscan rows | Fully painted rows |
| --- | --- | --- |
| Page 1, top | `ROW-01` through `ROW-20` | `ROW-01` through `ROW-17` |
| Page 1, scrolled to bottom | `ROW-08` through `ROW-25` | `ROW-09` through `ROW-25` |
| Page 2 | `ROW-26` through `ROW-30` | `ROW-26` through `ROW-30` |

The top/bottom union proved the complete first 25-record page, while page 2 proved the non-multiple five-record remainder. Do not equate mounted React Virtualized overscan rows with pixels inside the clipped Table viewport; save both DOM geometry and screenshots.

While 25 rows and page 2 were active, selecting 10 preserved active page number 2, restored page buttons 1/2/3, and painted `ROW-11` through `ROW-20`. It did not preserve the prior records 26-30 and did not reset to page 1. This exact 10 -> 25/page 1 -> 25/page 2 -> 10/page 2 result reproduced in two fresh sessions with zero reconnects, browser/page errors, or Gateway WARN-or-higher entries.

For a page-size test, open and capture the chooser once, assert the exact runtime `<option>` values/text, use a native select interaction for the intended value, correlate each state with official session/page/view reads, and require a second fresh confirmation before promoting page-number behavior after a size change.

## Tested selection across pages

For the same 30-row Table at size 10, single-row selection stayed attached to the selected source record while that record was outside the visible page. The retained fixture had no `onSelectionChange` handler, so this workflow proves painted client selection state only:

| Step | Active page | Visible selection |
| --- | ---: | --- |
| Initial | 1 | none |
| Click `ROW-05` | 1 | `ROW-05` |
| Page 2 | 2 | none |
| Return page 1 | 1 | `ROW-05` restored |
| Page 2, click `ROW-15` | 2 | `ROW-15` replaces `ROW-05` |
| Page 1 | 1 | none; `ROW-05` is no longer selected |
| Return page 2 | 2 | `ROW-15` restored |

This exact sequence reproduced in two fresh sessions. Each visible selected record had three contiguous descendant cells with class `t-selected`, one cell also had `root-selected`, and all three cells painted the configured `#dbeafe`. Off-page states had no visible selected marker. The row container's background reflected hover immediately after a click and was transparent after page return, so inspect the selected descendant cells and screenshot pixels rather than the row background alone.

The session/page identifiers stayed stable within each run, and official script count remained zero because no handler existed. Do not infer `event.selectedRow`, `event.data`, selection-event count, or stored `props.selection.selectedRow` from this test. Use the earlier event-qualified workflow when a payload is required, and independently test the combination of events and paging before relying on it.

For a paging-selection test, click a unique row container, require exactly three configured selected cells, move to a page where the record is absent, return and require restoration on the same record, select a different record on another page, and revisit both pages to prove replacement. Use fresh page-control locators after each page change and repeat the full sequence in a fresh session.

## Paged selection event payloads

The same 30-row, size-10 setup was independently tested with an `onSelectionChange` script. The handler required exactly one item in `event.data`, treated `event.selectedRow` as the zero-based source-array index, validated all three record fields against that index, copied them to view custom properties, and incremented a view event counter.

Two fresh sessions reproduced this exact sequence:

| Step | Active page | Visible selection | `event.selectedRow` | Payload | Event count | Script count |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| Initial | 1 | none | - | `NONE` | 0 | 0 |
| Click `ROW-05` | 1 | `ROW-05` | 4 | `ROW-05`, `ODD`, `5` | 1 | 1 |
| Page 2 | 2 | none | unchanged | unchanged | 1 | 1 |
| Return page 1 | 1 | `ROW-05` restored | unchanged | unchanged | 1 | 1 |
| Page 2, click `ROW-15` | 2 | `ROW-15` | 14 | `ROW-15`, `ODD`, `15` | 2 | 2 |
| Page 1 | 1 | none | unchanged | unchanged | 2 | 2 |
| Return page 2 | 2 | `ROW-15` restored | unchanged | unchanged | 2 | 2 |

Thus, for this exact static array and page sequence, `event.selectedRow` remained a source index rather than a page-relative index: the fifth row on page 1 produced 4 and the fifth row on page 2 produced 14. Each event delivered one selected record. Page-control clicks and automatic restoration of an off-page selection did not run `onSelectionChange`; official script counts stayed `0,1,1,1,2,2,2`.

The status label used a single expression binding over five custom properties. Official expression counts differed between the two fresh observation windows while the painted status and scripts remained exact, so expression counts are diagnostic only. Do not infer atomic expression reevaluation counts from the sequential property assignments.

For an event-qualified paging test, show the source index, complete record payload, and independent event count in painted state; correlate every page/selection state with official session metrics; require no script increment on pure page transitions or selection restoration; revisit both pages to prove replacement; and repeat in a fresh session.

## Same-row second click

For the exact retained single-select, size-10 Table, a second pointer click at the center of the already-selected `ROW-05` row did not deselect it. Two fresh sessions reproduced:

| State | Painted selection | Painted event state | Official script count |
| --- | --- | --- | ---: |
| Initial | none | `NONE`, events 0 | 0 |
| First `ROW-05` click | three configured selected cells | source row 4, `ROW-05`/`ODD`/`5`, events 1 | 1 |
| Second `ROW-05` click | the same three selected cells | unchanged | 1 |

The second click generated neither a visible state change nor another `onSelectionChange` execution. This establishes a no-op for that exact pointer gesture, not a general statement that single selection can never be cleared. Test programmatic selection changes, data replacement, keyboard/touch input, other selection modes, and any explicit deselection control independently.

When testing this boundary, click the same row geometry twice, capture after each click, require the second status and selected descendant cells to remain exact, and correlate the unchanged official script count in two fresh sessions. Do not infer a deselection payload when no event ran.

## Programmatic selected-row clear attempt

Assigning only the selected-row property did not clear the tested single-select Table:

```python
table = self.getSibling("DataTable")
table.props.selection.selectedRow = None
```

A retained sibling Button recorded `selection.selectedRow` and `len(selection.data)` immediately before and after that assignment. Two fresh sessions reproduced BRAVO selection, the assignment, CHARLIE recovery selection, and a second assignment:

| Operation | Row before | Data count before | Row after | Data count after | Painted selection | Selection events |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Clear selected BRAVO | 1 | 1 | `None` | 1 | BRAVO remains | unchanged at 1 |
| Clear selected CHARLIE | 2 | 1 | `None` | 1 | CHARLIE remains | unchanged at 2 |

Official script counts advanced `0,1,2,3,4`: each real row click ran `onSelectionChange`, and each Button click ran only its own action script. The selected record retained three configured selected cells after both assignments. A subsequent real row click replaced the selection and delivered the expected event, showing that the Table remained interactive.

Treat `props.selection.selectedRow` and `props.selection.data` as distinct runtime members for this boundary. Writing `selectedRow = None` alone is insufficient to clear the selected record because the data member and paint remain. Do not claim a supported programmatic-clear recipe until assigning the data member, assigning both members, ordering, event behavior, and recovery have their own focused test.

## Programmatic selection-data clear attempt

Assigning only the selection-data property also did not clear the tested single-select Table:

```python
table = self.getSibling("DataTable")
table.props.selection.data = []
```

A retained sibling Button recorded both selection members immediately before and after that assignment. Two fresh sessions reproduced BRAVO selection, the assignment, CHARLIE recovery selection, and a second assignment:

| Operation | Row before | Data count before | Row after | Data count after | Painted selection | Selection events |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Empty data for selected BRAVO | 1 | 1 | 1 | 0 | BRAVO remains | unchanged at 1 |
| Empty data for selected CHARLIE | 2 | 1 | 2 | 0 | CHARLIE remains | unchanged at 2 |

Official script counts advanced `0,1,2,3,4`: each real row click ran `onSelectionChange`, and each Button click ran only its action script. After each data-only assignment, the selected record retained three configured selected cells and the painted payload/event state did not change. A subsequent real row click replaced the visible selection, restored data length 1, and delivered the expected event.

Thus, directly emptying `props.selection.data` can create a split runtime state in this fixture: the handler immediately reads an empty data member while `selectedRow`, selection paint, and the last event-qualified payload remain. Do not treat either member as a standalone clear command. Test assignment of both members, both assignment orders, supported component APIs, event behavior, and recovery before publishing a clear-selection recipe.

## Programmatic two-member assignment order

Assigning both members sequentially converged to `selectedRow = None` and an empty data array, but still did not clear the painted selection in the tested fixture. Both direct assignment orders were tested:

```python
# Row, then data.
table.props.selection.selectedRow = None
table.props.selection.data = []

# Data, then row.
table.props.selection.data = []
table.props.selection.selectedRow = None
```

Separate Buttons recorded the selection members before, between, and after each pair. Two fresh sessions reproduced:

| Order and selected record | Before row/data | Intermediate row/data | Final row/data | Painted selection | Selection events |
| --- | --- | --- | --- | --- | ---: |
| Row then data, BRAVO | `1/1` | `None/1` | `None/0` | BRAVO remains | unchanged at 1 |
| Data then row, CHARLIE | `2/1` | `2/0` | `None/0` | CHARLIE remains | unchanged at 2 |

Official script counts advanced `0,1,2,3,4,5`: each real row click ran `onSelectionChange`, and each ordering Button ran only its own action script. Both retained selected records kept three configured selected cells after the pair. Real CHARLIE and ALPHA clicks replaced the painted selection, restored a coherent one-record data member, and delivered the expected events.

The final stored member pair is therefore insufficient evidence of cleared client selection. Validate pixels/selected descendants and events, not just immediate property readback. Neither tested direct assignment order is a supported clear-selection recipe on this boundary. Test documented component methods or other mechanisms independently.

## Bound-data refresh then selected-row clear

An installed sample used `refreshBinding("props.data")` before assigning `selectedRow = None`. That sample shape was treated as a hypothesis and independently reproduced with a controlled property-bound Table:

```json
{
  "propConfig": {
    "props.data": {
      "binding": {
        "config": { "path": "view.custom.rows" },
        "type": "property"
      }
    }
  }
}
```

The tested Button action was:

```python
table = self.getSibling("DataTable")
table.refreshBinding("props.data")
table.props.selection.selectedRow = None
```

The property binding continued to supply the same three-row array. Two fresh sessions reproduced:

| State | Immediate stored row/data | Painted selection | Selection event count | Script count |
| --- | --- | --- | ---: | ---: |
| Initial | no selection | none | 0 | 0 |
| Select BRAVO | `1/1` | BRAVO | 1 | 1 |
| Refresh then assign row | `None/1` | BRAVO remains | 1 | 2 |
| Five seconds later | status unchanged | BRAVO remains | 1 | 2 |
| Select CHARLIE | `2/1` through the event | CHARLIE replaces BRAVO | 2 | 3 |

Thus, refreshing an unchanged property binding before the selected-row assignment did not clear paint, clear selection data, or emit `onSelectionChange`, including through the tested five-second observation. A refresh request is not evidence that a new result set was delivered. Do not generalize this negative result to query/tag bindings or changed binding results; test those separately with independent source/readback evidence.

## Bound-data selected-row removal

The changed-result case was tested separately. The same Table kept `props.data` property-bound to persistent `view.custom.rows`. After selecting BRAVO at source index 1, a sibling Button replaced only the complete source list:

```python
self.view.custom.rows = [
    {"name": "ALPHA", "status": "ACTIVE", "value": 11},
    {"name": "CHARLIE", "status": "ALARM", "value": 33}
]
```

The Button did not call `refreshBinding` and did not write either selection member. Two fresh sessions reproduced:

| State | Bound rows | Stored row/data | Painted selection | Event count | Script count |
| --- | --- | --- | --- | ---: | ---: |
| Initial | ALPHA, BRAVO, CHARLIE | no selection | none | 0 | 0 |
| Select BRAVO | ALPHA, BRAVO, CHARLIE | `1/1` | BRAVO | 1 | 1 |
| Replace source without BRAVO | ALPHA, CHARLIE | `1/1` | CHARLIE | 2 | 3 |
| Five seconds later | ALPHA, CHARLIE | `1/1` | CHARLIE | 2 | 3 |
| Click already-selected CHARLIE | ALPHA, CHARLIE | `1/1` | CHARLIE | 2 | 3 |

The two scripts at the replacement step were the Button action and the automatically emitted `onSelectionChange`. The Table preserved selected index 1, remapped its one-record payload and three selected cells to the new record now occupying index 1, and delivered CHARLIE through the event. A second pointer click on that already-selected row remained a no-op.

Treat selection as index-sensitive when a bound result changes. Removing a selected record does not imply selection clearing when another record occupies the same index. If record identity must remain stable or selection must clear, implement and independently test an explicit identity/selection policy. This exact result does not qualify insertion, reordering, filtering, paging, sorting, empty results, query/tag timing, datasets, multi-select, or other data mutations. The out-of-range last-row case is qualified separately below.

## Bound-data selected last-row removal

The out-of-range case used the same property-bound three-row source but selected CHARLIE at index 2. A sibling Button replaced only `view.custom.rows` with ALPHA and BRAVO; it did not refresh the binding or write selection members.

The Button captured selection members synchronously around the source assignment. Two fresh sessions reproduced:

| State | Bound rows | Button's immediate row/data | Settled handler state | Painted selection | Event count | Script count |
| --- | --- | --- | --- | --- | ---: | ---: |
| Initial | ALPHA, BRAVO, CHARLIE | not run | NONE | none | 0 | 0 |
| Select CHARLIE | ALPHA, BRAVO, CHARLIE | not run | CHARLIE at `2/1` | CHARLIE | 1 | 1 |
| Remove selected last row | ALPHA, BRAVO | `2/1 -> 2/1` | NONE at `None/0` | none | 2 | 3 |
| Five seconds later | ALPHA, BRAVO | unchanged | NONE | none | 2 | 3 |
| Select BRAVO | ALPHA, BRAVO | unchanged | BRAVO at `1/1` | BRAVO | 3 | 4 |

The source assignment therefore did not synchronously mutate the Table selection members inside the action script. After binding propagation settled, the prior index 2 was out of range, the Table emitted `onSelectionChange` with `selectedRow is None` and empty `event.data`, cleared all selected-cell paint, and remained interactive. Do not use an immediate same-script property read as proof of the settled bound result.

For the two tested removal cases, the retained numeric index explains the outcome: replacement at the same index remapped selection, while removal that made the index invalid cleared selection through an event. This does not prove a universal identity model or timing guarantee. Test insertion, reorder, same-length replacement, filtering, sorting, paging, query/tag delivery timing, datasets, multi-select, and other mutations independently. The exact empty/restore lifecycle is qualified separately below.

## Bound-data empty result and restore

The empty-result test selected BRAVO at index 1, assigned `[]` to the same persistent property-bound source, waited five seconds, restored the exact original ALPHA/BRAVO/CHARLIE list, and then clicked BRAVO again. Neither mutation called `refreshBinding` or wrote Table selection members.

Two fresh sessions reproduced:

| State | Rows/headers painted | Action's immediate row/data | Settled handler state | Selected paint | Event count | Script count |
| --- | --- | --- | --- | --- | ---: | ---: |
| Initial | three rows/three headers | not run | NONE | none | 0 | 0 |
| Select BRAVO | three rows/three headers | not run | BRAVO at `1/1` | BRAVO | 1 | 1 |
| Assign empty list | no rows/no headers | `1/1 -> 1/1` | NONE at `None/0` | none | 2 | 3 |
| Five seconds later | no rows/no headers | unchanged | NONE | none | 2 | 3 |
| Restore original list | three rows/three headers | `None/0 -> None/0` | BRAVO at `1/1` | BRAVO | 3 | 5 |
| Click restored BRAVO | three rows/three headers | unchanged | BRAVO at `1/1` | BRAVO | 4 | 6 |

Empty binding propagation emitted a clear event after the action's synchronous read and removed the tested Table’s rows, headers, data, and selected paint. Restoring the identical list emitted another selection event and reinstated the prior index-1 BRAVO payload and paint, even though the restore action synchronously read `None/0`. The next center click on the restored BRAVO emitted another event in this lifecycle, unlike the separately tested ordinary same-row second click.

Therefore, a settled clear during a transient empty result did not prove that the Table forgot its prior client selection lifecycle. If restoration must remain unselected, design and independently test an explicit post-result selection policy. Do not generalize the restored-click difference to every same-row click or infer undocumented identity storage. Test different restored arrays, delays, empty startup, multiple empty/restore cycles, query/tag delivery timing, filtering, sorting, paging, datasets, and multi-select separately.

## Bound-data same-index record replacement

The same-length test selected BRAVO at index 1, replaced the complete three-row bound list with ALPHA, DELTA, CHARLIE, waited five seconds, restored ALPHA, BRAVO, CHARLIE, and clicked BRAVO. DELTA was a distinct exact record: `PAUSED` and `44`. Neither mutation called `refreshBinding` or wrote selection members.

Two fresh sessions reproduced:

| State | Index-1 record | Immediate row/data | Settled payload/paint | Event count | Script count |
| --- | --- | --- | --- | ---: | ---: |
| Initial | BRAVO | not run | none selected | 0 | 0 |
| Select BRAVO | BRAVO | not run | BRAVO at `1/1` | 1 | 1 |
| Replace with DELTA | DELTA | `1/1 -> 1/1` | DELTA at `1/1` | 2 | 3 |
| Five seconds later | DELTA | unchanged | DELTA at `1/1` | 2 | 3 |
| Restore BRAVO | BRAVO | `1/1 -> 1/1` | BRAVO at `1/1` | 3 | 5 |
| Click restored BRAVO | BRAVO | unchanged | BRAVO unchanged | 3 | 5 |

Each bound record replacement preserved selected index/data counts and emitted `onSelectionChange` with the record currently occupying index 1; the three selected cells and copied payload changed from BRAVO to DELTA and back. The final ordinary same-row click was a no-op, consistent with the standalone same-row test and distinct from the transient-empty restoration lifecycle.

For this exact whole-list reassignment, selection behaved by retained index rather than retaining the old record identity. Do not infer a universal keyless identity algorithm. Test in-place item mutation, moving the selected record to another index, duplicates, sorting/filtering/paging, query/tag delivery timing, datasets, and multi-select independently.

## Bound-data selected-record reorder

The reorder test selected BRAVO at source index 1, reassigned the complete bound list from ALPHA, BRAVO, CHARLIE to BRAVO, ALPHA, CHARLIE, waited five seconds, restored the original order, and clicked the painted BRAVO row. All three records remained equivalent apart from their position. Neither mutation refreshed the binding or wrote a selection member.

Two fresh sessions reproduced:

| State | Bound row order | Immediate row/data | Settled payload/paint | Event count | Script count |
| --- | --- | --- | --- | ---: | ---: |
| Initial | ALPHA, BRAVO, CHARLIE | not run | none selected | 0 | 0 |
| Select BRAVO | ALPHA, BRAVO, CHARLIE | not run | BRAVO at `1/1` | 1 | 1 |
| Move BRAVO to index 0 | BRAVO, ALPHA, CHARLIE | `1/1 -> 1/1` | ALPHA at `1/1` | 2 | 3 |
| Five seconds later | BRAVO, ALPHA, CHARLIE | unchanged | ALPHA at `1/1` | 2 | 3 |
| Restore original order | ALPHA, BRAVO, CHARLIE | `1/1 -> 1/1` | BRAVO at `1/1` | 3 | 5 |
| Click restored BRAVO | ALPHA, BRAVO, CHARLIE | unchanged | BRAVO unchanged | 3 | 5 |

The selected index remained 1; selection did not follow BRAVO to index 0. Each whole-list reorder emitted `onSelectionChange` and remapped the one-record payload plus all three selected cells to the record occupying index 1. The final same-row click remained a no-op.

Use a tested explicit record-identity policy when the application requires selection to follow a logical record through source reordering. This exact evidence does not establish in-place reorder behavior, duplicate-row identity, arbitrary permutations, sorting/filtering/paging interaction, query/tag delivery timing, datasets, multi-select, or other selection modes.

## Bound-data list-index object assignment

The list-index test selected BRAVO at index 1 and replaced only that existing persistent-list element:

```python
self.view.custom.rows[1] = {
    "name": "DELTA",
    "status": "PAUSED",
    "value": 44
}
```

It waited five seconds and assigned the complete original BRAVO object back to the same index. The action never reassigned `view.custom.rows`, refreshed the binding, or wrote a Table selection member.

Two fresh sessions reproduced:

| State | Index-1 record | Immediate row/data | Settled payload/paint | Event count | Script count |
| --- | --- | --- | --- | ---: | ---: |
| Initial | BRAVO | not run | none selected | 0 | 0 |
| Select BRAVO | BRAVO | not run | BRAVO at `1/1` | 1 | 1 |
| Assign DELTA object | DELTA | `1/1 -> 1/1` | DELTA at `1/1` | 2 | 3 |
| Five seconds later | DELTA | unchanged | DELTA at `1/1` | 2 | 3 |
| Assign BRAVO object | BRAVO | `1/1 -> 1/1` | BRAVO at `1/1` | 3 | 5 |
| Click restored BRAVO | BRAVO | unchanged | BRAVO unchanged | 3 | 5 |

Complete-object assignment at an existing list index propagated through the property binding without whole-list reassignment. It retained the selected index/data counts and emitted `onSelectionChange` with the new record at that index. The final same-row click remained a no-op.

This is not proof that editing a nested member such as `rows[1]["value"]` has the same notification or event behavior. Test nested-member writes, other indexes, insert/remove operations, duplicates, arbitrary object shapes, query/tag timing, datasets, and other selection modes independently.

## Bound-data nested scalar assignment

The nested-member test selected BRAVO at index 1 and changed only its integer value:

```python
self.view.custom.rows[1]["value"] = 24
```

It waited five seconds and restored only that member to 22. The action did not replace the row object, reassign the list, refresh the binding, or write selection members.

Two fresh sessions reproduced:

| State | BRAVO value | Immediate row/data | Settled payload/Table cell | Event count | Script count |
| --- | ---: | --- | --- | ---: | ---: |
| Initial | 22 | not run | none selected | 0 | 0 |
| Select BRAVO | 22 | not run | BRAVO value 22 at `1/1` | 1 | 1 |
| Assign nested value | 24 | `1/1 -> 1/1` | BRAVO value 24 at `1/1` | 2 | 3 |
| Five seconds later | 24 | unchanged | BRAVO value 24 at `1/1` | 2 | 3 |
| Restore nested value | 22 | `1/1 -> 1/1` | BRAVO value 22 at `1/1` | 3 | 5 |
| Click restored BRAVO | 22 | unchanged | BRAVO unchanged | 3 | 5 |

The nested integer write propagated through the property binding without replacing its parent object or list. It updated the painted Table cell and one-record event payload, retained index/data `1/1` and three selected cells, and emitted one `onSelectionChange` per write. The final same-row click remained a no-op.

Keep this boundary narrow: it proves one integer member at one existing row/index. Test name/status or other types, multiple sequential writes and intermediate events, other indexes, structural changes, query/tag timing, datasets, and other selection modes independently.

## Bound-data sequential nested writes

The sequential-write test changed the selected BRAVO record through three no-delay nested assignments in one synchronous Button action:

```python
self.view.custom.rows[1]["name"] = "DELTA"
self.view.custom.rows[1]["status"] = "PAUSED"
self.view.custom.rows[1]["value"] = 44
```

It restored the same members in reverse order: value 22, status IDLE, then name BRAVO. A persistent painted trace appended every `onSelectionChange` payload. Neither action replaced the row/list, refreshed the binding, wrote selection members, or delayed between writes.

Two fresh sessions reproduced:

| State | Settled record | Complete event trace | Script count |
| --- | --- | --- | ---: |
| Initial | no selection | empty | 0 |
| Select BRAVO | BRAVO/IDLE/22 | `1:BRAVO\|IDLE\|22@1` | 1 |
| Three-write change | DELTA/PAUSED/44 | prior + `2:DELTA\|PAUSED\|44@1` | 3 |
| Five seconds later | DELTA/PAUSED/44 | unchanged | 3 |
| Reverse three-write restore | BRAVO/IDLE/22 | prior + `3:BRAVO\|IDLE\|22@1` | 5 |
| Click restored BRAVO | BRAVO/IDLE/22 | unchanged | 5 |

Each synchronous three-write action yielded one selection callback containing only its fully settled record. No event trace entry contained an intermediate mixed payload such as DELTA/IDLE/22 or DELTA/PAUSED/22.

Describe this as observed callback coalescing for the exact action, not general transaction atomicity. The evidence does not observe internal states that never reached `onSelectionChange` or paint. Test different member orders, explicit delays, asynchronous scripts, other fields/types/indexes, query/tag timing, datasets, and selection modes independently.

## Direct memory-Dataset binding

The tested tag-import representation used the case-sensitive configured type `DataSet`:

```json
{
  "name": "Rows",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "DataSet",
  "value": {
    "columns": [
      {"name": "assetId", "type": "java.lang.String"},
      {"name": "line", "type": "java.lang.String"},
      {"name": "count", "type": "java.lang.Integer"},
      {"name": "temperature", "type": "java.lang.Double"},
      {"name": "enabled", "type": "java.lang.Boolean"}
    ],
    "rows": [
      ["P-3", "Gamma", 3, 33.5, true],
      ["P-1", "Alpha", 10, 21.25, true],
      ["P-2", "Beta", 2, 28.75, false],
      ["P-4", null, 7, 19.0, false]
    ]
  }
}
```

`dataType: "Dataset"` was rejected with a case-sensitive enum error on the tested build; do not normalize the spelling. Official export represented Dataset `value` and `defaultValue` as JSON strings, so parse and compare their semantics instead of assuming an object on export.

The Table stored an empty fallback array and a direct read-only tag binding:

```json
{
  "propConfig": {
    "props.data": {
      "binding": {
        "type": "tag",
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[Provider]Approved Folder/Rows"
        }
      }
    }
  },
  "props": {"data": []}
}
```

Use a caller-approved provider/folder and independently read the live value after import. The qualified readback was Good, untruncated, runtime type `BasicDataset`, four rows by five columns, with exact Java column types and the null String cell preserved. Descriptor allowance for `dataset` is discovery evidence only; rendered rows and typed readback are the runtime gates.

## Typed Dataset rendering and numeric sorting

With explicit Table columns matching the Dataset column names, all four rows rendered. Boolean values painted as checkbox cells. Integer and Double cells rendered their numeric values, and the null String cell painted empty.

A real pointer click on the COUNT header sorted numerically rather than lexically:

```text
source counts:     3, 10, 2, 7
ascending counts:  2, 3, 7, 10
```

The Table's event record exposed values by Dataset column name, such as `record["assetId"]`, `record["count"]`, and `record["enabled"]`. Validate the runtime values and conversions used by the script; the rendered text alone does not prove Java/Python value types.

## Dataset replacement with two sessions

Two fresh sessions selected different rows. One session then sorted COUNT ascending while the other remained in source order. A complete official tag import replaced all four Dataset rows while both sessions stayed open.

The tested selection rule was source-index preservation, not business-key preservation:

| Session | Before replacement | After replacement | Event result |
| --- | --- | --- | --- |
| A | source row 2, P-2 | source row 2, P-1 | payload/paint remapped; count advanced once |
| B | source row 1, P-1 | source row 1, P-4 | payload/paint remapped; count advanced once |

The sorted session retained numeric ascending order and painted its newly remapped row at that record's visible sorted position. The unsorted session retained source order. After a three-second stability check, restoring the original Dataset repeated the source-index remap and emitted one more selection event in each session; each session retained its own sort state.

Do not treat an identifier column as an implicit Table row key. If replacement can reorder or substitute rows, either accept index-based remapping or explicitly clear/reconcile selection using a separately tested application rule. A successful import, Good tag quality, clean browser console, and clean Gateway logs do not prove client reconciliation; keep two rendered observers open, inspect selection-overlay geometry and screenshots, and query logs at every edge and after close.

## Dataset shrink clear and automatic reselection

For one exact four-to-three-to-four complete memory-Dataset sequence, two sessions selected different source indices before the shrink:

| Session | Local state before shrink | Three-row shrink | Four-row restore |
| --- | --- | --- | --- |
| A | source index 2/P-2; COUNT ascending | index 2 remained valid and remapped to P-6; one event; paint followed P-6 to visible position 1 | remapped to index 2/P-2; one event; ascending sort remained |
| B | source index 3/P-4; source order | index 3 became invalid; one clear event; row/data state became none; no selected paint | index 3/P-4 automatically reselected; one event; paint returned |

Both the three-row and restored states remained exact for five seconds. Session/page identity stayed stable, the clients did not reconnect, and their different sort states remained local.

Treat the clear as a runtime invalid-index state, not proof that the Table discarded all selection intent. When the original row count returned, the previously out-of-range source index became valid and the Table automatically selected its new occupant. This is not business-key restoration: the tested occupant happened to be P-4 because index 3 returned.

Instrument both record and clear callbacks when testing shrink behavior. A clear handler can use `event.selectedRow is None` to reset application-facing payload state, but that handler does not prove future Dataset growth will remain unselected. If permanent clearing is required, test an explicit application reconciliation rule independently.

This qualification covers only complete replacement of the exact four-row Dataset by the exact three-row Dataset and restoration. Empty results, other row counts or selected indices, equal-length selected-record removal, duplicate identifiers, explicit selection clearing during the gap, reloads, and other Dataset sources remain separate tests.

## Schema-preserving empty Dataset and restore

For one exact four-to-zero-to-four sequence, the empty memory Dataset kept the same five column definitions and Java types while setting `rows` to an empty array. Independent readback remained Good and reported runtime type `BasicDataset`, column count 5, and row count 0.

Two sessions had selected source indices 2 and 3 before the empty import. One session also held a local COUNT ascending sort. On the zero-row update, both sessions:

- emitted exactly one `onSelectionChange` with `event.selectedRow is None`;
- cleared the instrumented record payload and selected-cell overlays;
- painted zero Table body rows;
- painted zero headers despite explicit Table columns and the retained five-column Dataset schema;
- retained the bottom pager, page 1 indicator, and page-size chooser.

Both empty states remained exact for five seconds. Restoring the original four rows recreated all five headers, automatically reselected source indices 2 and 3, emitted one additional selection event per session, and restored selection paint. The sorted session returned in COUNT ascending order while the other remained in source order. Session/page identity stayed stable throughout.

Do not use schema presence or explicit Table columns as proof that an empty Table will display its headers on this build. If a screen requires persistent empty-state headers, design and test a separate presentation rather than assuming the native Table header remains.

Also do not interpret the clear event as permanent removal of internal index intent. Restoration automatically revalidated both old source indices. Test an explicit application-level clear independently when automatic reselection is undesirable.

This qualification does not cover a Dataset without columns, null or bad quality, other selected indices, explicit clearing during the zero-row interval, other pager configurations, query/historical results, loading transitions, reload/reconnect, or other builds.

## Reordered Dataset columns and one extra field

For one direct read-only memory-Dataset Table with five explicit fields in display order `assetId,line,count,temperature,enabled`, a complete replacement changed the physical source order to `enabled,temperature,count,line,assetId,note`. On Ignition 8.3.8 / Perspective 3.3.8, two fresh two-session reproductions retained exactly five configured headers and rendered every String, Integer, Double, and Boolean value by configured field name. The unconfigured String field `note` did not render.

One client retained local numeric COUNT ascending order while the other retained source order. Each client also retained its prior source index: replacement remapped selection payload and paint to the new record at that index, ran `onSelectionChange` once, and baseline restoration remapped it back. Both replacement and restored states remained exact for five seconds. This establishes field-name resolution for this exact complete replacement; it does not qualify missing, renamed, duplicate, or incompatible typed fields, multiple extras, extra-field event access, partial writes, other Dataset sources, editing, or other builds.

Selection styling requires rendered validation. In this Table, an opaque `selection.style.backgroundColor` produced a selection overlay above the underlying cells and made the selected row's text and checkbox invisible even though DOM text and event payloads were correct. Adding `color` to the selection style did not fix it. The qualified retained style used a translucent overlay:

```json
{
  "selection": {
    "style": {
      "backgroundColor": "rgba(37, 99, 235, 0.18)"
    }
  }
}
```

Do not infer readability from DOM text, event values, or a presumed CSS foreground. Save and inspect screenshots for selected and unselected rows, verify checkbox paint, and correlate the overlay geometry with the intended record.

## Missing configured Dataset field with one extra field

For one five-column Table configured as `assetId,line,count,temperature,enabled`, a complete Good `BasicDataset` replacement supplied `enabled,temperature,count,assetId,note`. The configured String field `line` was absent and one otherwise unconfigured String field `note` remained.

On Ignition 8.3.8 / Perspective 3.3.8, the Table did not retain an empty LINE column. Two fresh two-session reproductions painted headers:

```text
ASSET, note, COUNT, TEMP, ENABLED
```

The second column painted exact `note` values. Its native lowercase header was not sortable and did not inherit LINE's configured title or sortable setting. The other four configured fields retained their configured headers, sortable classes, name-based values, numeric behavior, and Boolean checkbox paint. Baseline restoration returned the configured LINE header, its values, and sortable behavior.

Thus, do not assume that an explicit Table column whose Dataset field disappears will stay present, paint blank cells, or reserve its configured behavior. With this exact equal-count replacement, the remaining unconfigured Dataset field became a runtime-generated column in that slot. Verify the complete header sequence, header classes, cell values, geometry, and screenshots after every schema change.

The test's selection handler intentionally read only fields common to both schemas. Source-index selection remapped to the new records and local COUNT sorting persisted, but direct access to the absent `line` member was not tested. Do not generalize this result to multiple missing/extra fields, missing non-String fields, renamed or duplicate fields, incompatible types, different column counts, event access to the missing member, partial writes, other Dataset sources, or other builds.

## Missing configured Dataset field with no extra field

For the same five configured fields, a separate replacement supplied only four physical Dataset columns: `enabled,temperature,count,assetId`. The runtime did not collapse the Table to four columns and did not retain configured LINE.

Two fresh two-session reproductions painted:

```text
ASSET, column_5, COUNT, TEMP, ENABLED
```

The generated second header used `data-column-id="column_5"`, was non-sortable, and painted an equal-width blank cell in every row. With `resizeMode: "fill"`, all five header/cell widths remained equal in the tested viewport. The common configured fields retained their headers, sortable classes, name-based typed values, numeric behavior, and Boolean checkboxes. Baseline restoration returned configured LINE title, values, and sortability.

Do not assume a missing configured field with no replacement field produces fewer painted columns. On this exact build and schema, Perspective retained the five-column geometry through a generated blank `column_5`. Treat that name as observed runtime behavior, not a stable public naming contract for other positions or counts. Validate complete headers, DOM column IDs, blank-cell geometry, screenshots, and logs after every schema change.

The handler again accessed only common fields. Source-index selection remapping and local COUNT sorting remained functional, but missing-member script access, multiple missing fields, other missing types/positions, different counts, bad quality, and other Dataset sources/builds remain separate tests.

## Selection handler access to a removed Dataset member

Direct mapping access is not safe across the tested schema removal. An `onSelectionChange` handler that evaluated `record["line"]` after automatic source-index remapping raised `KeyError: line` when the replacement Dataset omitted `line`.

Assignment order mattered. The tested handler incremented an attempt counter, assigned selected row/asset, and set stage `BEFORE_LINE` before the failing access. Later LINE/count/temperature/enabled assignments, completion increment, stage `COMPLETE`, and last-event assignment followed it. In two fresh two-session reproductions, replacement produced:

- current remapped Table rows, selection paint, selected row, and asset;
- attempt 2 but completion 1 and stage `BEFORE_LINE`;
- stale LINE/count/temperature/enabled/last-event values from each session's different prior selection;
- one WARN per session from `perspective.actions.script`, action `component.onSelectionChange`, generated wrapper line 24, `KeyError: line`;
- no browser error and no additional WARN+.

This mixed state is important: a visually current Table and some current custom properties do not prove the handler completed. When schema can vary, expose or log completion separately, avoid publishing partial application state before fallible access, and validate required members before committing dependent state. This test does not qualify a particular guard or lookup method; test the chosen guard independently on the target build.

Restoring the original schema automatically invoked the handler again. Both sessions reached attempt 3/completion 2/`COMPLETE`, refreshed every payload field, restored LINE/header/selection, and emitted no recovery or post-close warning. Recovery does not erase the earlier stale-state interval or warning.

Require official bounded logs even when the Table paints normally. For an expected negative, classify the exact logger/action/path/line/exception and multiplicity; reject every additional WARN+. Do not broaden this result to other missing members/types, multiple removals, manual clicks while absent, different assignment ordering, guarded access, async code, other Dataset sources, or other builds.

## Guarded access to a removed Dataset member

On the tested build, a narrow `KeyError` guard around direct mapping access handled the same automatic selection-remap edge without a script warning:

```python
record = list(event.data)[0]

# Read required common members into locals before publishing dependent state.
asset_value = str(record["assetId"])
count_value = int(record["count"])
temperature_value = float(record["temperature"])
enabled_value = bool(record["enabled"])

try:
    line = record["line"]
    line_value = "NULL" if line is None else str(line)
except KeyError:
    line_value = "MISSING"

# Commit the complete payload only after the fallible reads above.
self.view.custom.selectedAsset = asset_value
self.view.custom.selectedLine = line_value
self.view.custom.selectedCount = count_value
self.view.custom.selectedTemperature = temperature_value
self.view.custom.selectedEnabled = enabled_value
```

The test used separate attempt, completion, fallback, and stage properties. In two fresh two-session reproductions, replacement without `line` automatically invoked `onSelectionChange` once per session. Each handler reached attempt 2/completion 2/fallback 1/`COMPLETE`; published the current remapped row, asset, count, temperature, enabled value, and `LINE: MISSING`; retained readable selection paint; and emitted zero WARN+ at the replacement, stable, recovery, and post-close edges. Restoring the original schema invoked the handler again and reached attempt 3/completion 3/fallback 1/`COMPLETE` with the real line value.

This qualifies only `except KeyError` around the single tested `record["line"]` access. Do not use a broad `except`, because it can conceal unrelated conversion, script, or state-publication failures. The tested read-before-commit ordering avoids the partial mixed state observed in the unguarded control, but it is not a transaction: subsequent property assignments can still fail independently. Validate required event cardinality and common members, expose completion separately from attempt count, and query bounded official Gateway logs at every edge even when fallback UI looks correct.

This guarded-access test alone does not qualify `.get`, membership tests, Java Dataset APIs, multiple missing fields, missing non-String members, manual clicks while the field is absent, other Dataset sources, or other builds. The next section records the separate `.get` reproduction.

## Record `get` with a default

On the tested build, the mapping-like record in the one-item `event.data` sequence supported Python-style `get` with a default:

```python
record = list(event.data)[0]
line = record.get("line", "MISSING")
line_value = "NULL" if line is None else str(line)
```

With the five-column Dataset, `get` returned each selected record's actual `line`, including `None` for the tested null member rather than the default. After whole-Dataset replacement removed the `line` column, the same call returned the supplied `"MISSING"` default. It did not raise `KeyError` or require an exception handler.

In two fresh two-session reproductions, automatic source-index remapping invoked `onSelectionChange` once per session. Each replacement handler reached attempt 2/completion 2/default-count 1/`COMPLETE`, published the complete current payload, retained readable selected-row paint, and emitted zero WARN+. Restoration invoked it again, reached 3/3/1/`COMPLETE`, and returned the real line values. Independent local sorting, stable holds, browser diagnostics, official topology, every bounded edge log window, and post-close logs also passed.

Read fallible or schema-sensitive values into locals before publishing dependent state. A default sentinel can collide with legitimate data; if the application must distinguish a missing member from a present member equal to the default, use the separately reproduced membership pattern in the next section instead of inferring absence from equality.

Do not generalize the observed `get` behavior to multiple missing members, missing non-String members, one-argument `get`, keyword arguments, Java map methods, mutation methods, other event objects, other Dataset sources, malformed payloads, asynchronous use, Designer behavior, or other builds without separate reproduction.

## Record membership and default collisions

On the tested build, the mapping-like selection record supported Python membership syntax:

```python
line_present = "line" in record
line = record.get("line", "MISSING")
line_value = "NULL" if line is None else str(line)
```

Use the membership Boolean—not equality with the default—to decide whether the member is absent. The collision-aware fixture proved three distinct cases:

- a present `line` whose legitimate value was the literal String `MISSING`: membership `True`, lookup value `MISSING`;
- a present `line` whose value was null: membership `True`, lookup value `None`;
- a Dataset schema with no physical `line` member: membership `False`, lookup value `MISSING`.

In two fresh two-session reproductions, both baseline controls completed at attempt 1/completion 1/missing-count 0/`COMPLETE`. Whole-Dataset replacement removed `line`, automatically remapped both source-index selections, and completed at 2/2/1/`COMPLETE` with current payloads. Restoration returned to 3/3/1/`COMPLETE`, membership `True`, and the literal-sentinel/null values. Independent local sorting, all stable holds, browser diagnostics, official topology, every bounded edge log window, and post-close logs passed with no WARN+.

Read membership, lookup results, and other fallible values into locals before committing dependent application state. A membership result answers whether the mapping exposes that key; it does not validate the value's type, convertibility, quality, or business meaning.

Do not generalize this result to `has_key`, case-insensitive names, Java map APIs, mutation methods, multiple missing members, other missing types, other event objects, other Dataset sources, malformed records, asynchronous use, Designer behavior, or other builds without separate reproduction. The next section records a separate `keys()` enumeration test.

## Record key enumeration

On the tested build, the mapping-like selection record supported `record.keys()` and conversion to a Jython list:

```python
keys = list(record.keys())
keys_text = "|".join([str(key) for key in keys])
```

For the tested five-column Dataset, both sessions returned:

```text
assetId|line|count|temperature|enabled
```

After whole-Dataset replacement supplied four reordered physical columns, both sessions returned:

```text
enabled|temperature|count|assetId
```

Restoring the baseline restored the original five-key sequence. Thus, in this exact fixture, the enumeration matched physical Dataset column order and changed with that schema; it did not follow the configured Table header order, which remained `ASSET`, generated `column_5`, `COUNT`, `TEMP`, `ENABLED` during replacement.

Corrected discovery and two fresh clean strict reproductions exercised different selected source indices and independent local sort states. Every handler published the exact key count/text with the complete current payload. Replacement and restoration were stable for five seconds, session/page identities remained constant, browser diagnostics were empty, and all accepted bounded edge and post-close log windows contained zero WARN+.

One otherwise visually successful strict attempt was rejected because its post-close window contained an unrelated concurrent `tags.json` warning. Preserve and reject contaminated runs; do not ignore a warning merely because its logger is outside Perspective. Start a fresh observation window and require the full sequence to pass again.

Treat the observed key sequence as runtime evidence for these schemas, not a universal ordering contract. Do not generalize to `values`, direct record iteration, repeated/duplicate names, case variants, Java map APIs, mutation, other event objects, other Dataset sources, asynchronous use, Designer behavior, or other builds without separate reproduction. The next section records a separate `items()` test.

## Record item enumeration

On the tested build, the mapping-like selection record supported `record.items()` and conversion to an ordered Jython list of key/value pairs:

```python
items = list(record.items())
items_text = "|".join([
    "%s=%s" % (str(key), "NULL" if value is None else str(value))
    for key, value in items
])
```

The pair order matched `record.keys()` and the physical Dataset column order in both tested schemas. Representative exact results were:

```text
assetId=P-3|line=MISSING|count=3|temperature=33.5|enabled=True
assetId=P-4|line=NULL|count=7|temperature=19|enabled=False
enabled=True|temperature=29.5|count=12|assetId=P-2
enabled=False|temperature=36|count=15|assetId=P-5
```

The handler deliberately normalized only `None` to `NULL`; the other text came from Jython `str(value)`. In this fixture, Boolean strings were capitalized `True`/`False`, while Double values with no fractional remainder painted without `.0` (`19`, `36`). Do not reuse this debug representation as a typed interchange format or assume it matches Perspective expression `toStr`, which painted lowercase Boolean values and `19.0`/`36.0` in the separate payload labels.

Discovery and two fresh two-session strict reproductions verified exact pair count/text at baseline, after reordered schema removal, during stable holds, and after restore. The literal-sentinel, present-null, missing-member, key-order, payload, independent local-sort, geometry, browser-diagnostic, topology, cleanup, and bounded edge/post-close log assertions all remained active and passed with zero WARN+.

Treat `items()` as a snapshot for immediate synchronous inspection in this tested handler. Do not generalize to direct iteration, mutable views, nested/complex values, serialization round trips, duplicate/case-variant names, Java map APIs, mutation, other event objects, other Dataset sources, asynchronous retention, Designer behavior, or other builds without separate reproduction. The next section records a separate `values()` and alignment test.

## Record values and mapping alignment

On the tested build, the mapping-like selection record supported `record.values()` and conversion to a Jython list. The test also compared all three enumeration surfaces index by index before publishing state:

```python
keys = list(record.keys())
values = list(record.values())
items = list(record.items())

aligned = len(keys) == len(values) and len(values) == len(items)
if aligned:
    for index in range(len(items)):
        if items[index][0] != keys[index] or items[index][1] != values[index]:
            aligned = False
            break
```

Alignment remained true for both sessions at baseline, after reordered schema removal, during stable holds, and after restore. Representative values text, using the same null-only normalization as the items test, was:

```text
P-3|MISSING|3|33.5|True
P-4|NULL|7|19|False
True|29.5|12|P-2
False|36|15|P-5
```

Thus, for these exact records and schemas, `keys()`, `values()`, and `items()` had equal lengths and matching physical-column order. This does not establish a universal mapping-order contract; keep the alignment check when code depends on positional pairing.

Discovery and two clean strict confirmations passed the full seven-state, two-session sequence with all previous key/item/membership/collision/null/payload/sort/restore assertions, 1250-pixel-tall screenshot geometry, browser diagnostics, official topology, bounded logs at every edge, and post-close logs.

One strict attempt remains rejected because the Perspective client trial expired during its stable replacement hold and painted the native Trial Expired screen. Gateway WARN+ and browser error streams were empty, proving that log/console success cannot substitute for screenshot and DOM state. The baseline was restored, official trial status later reported active, and the full run was repeated cleanly.

Do not generalize to mutable collection views, nested/complex values, typed serialization, equality semantics for complex objects, duplicate/case-variant names, other event objects, Java map APIs, asynchronous retention, Designer behavior, or other builds without separate reproduction. The next section records a separate direct-iteration test.

## Direct record iteration

On the tested build, direct iteration over the mapping-like Table selection record produced keys. Convert the result immediately when a concrete snapshot is needed:

```python
iteration = list(record)
keys = list(record.keys())
iteration_matches_keys = iteration == keys
```

For both independent sessions, the selected baseline records produced this exact direct-iteration sequence:

```text
assetId|line|count|temperature|enabled
```

After whole-Dataset replacement removed `line` and reordered the physical schema, both sessions produced:

```text
enabled|temperature|count|assetId
```

Restoring the baseline restored the original five-key sequence. `iteration_matches_keys` was true for every selected record at baseline, after replacement, throughout the five-second replacement hold, immediately after restore, and throughout the five-second restore hold. Before any selection, the view deliberately published an empty iteration and `false`; that sentinel state is not evidence about an actual record.

Discovery and two fresh strict reproductions retained the prior key/item/value alignment, membership, missing-member, null, literal-sentinel, payload, independent local-sort, and automatic remapping assertions. Each run also required two stable session/page identities, original-resolution screenshots at every state, bounded official Gateway WARN+ logs at every edge and after close, empty browser diagnostics, unchanged project/protected resources, and zero remaining test sessions. All accepted windows were clean.

This proves only that `list(record)` yielded the same ordered key snapshot as `list(record.keys())` for these exact Table `onSelectionChange` records, two schemas, synchronous handler, and tested build. It does not establish a universal mapping-order guarantee or prove behavior for values, items, duplicate/case-variant names, nested/complex values, mutation, retained iterators, asynchronous use, other event objects, other Dataset sources, Designer behavior, or other builds. Keep an explicit comparison when application correctness depends on the equivalence.

## Record length

On the tested build, the mapping-like Table selection record supported Python's `len` operation. Compare it with an independently enumerated key snapshot before committing dependent state:

```python
keys = list(record.keys())
record_length = len(record)
length_matches_keys = record_length == len(keys)
```

Both sessions returned length `5` for selected records from the five-column baseline Dataset, length `4` after whole-Dataset replacement supplied four reordered columns, and length `5` after restoration. `length_matches_keys` was true immediately after each schema edge and throughout both five-second stable holds. Local Table sorting in one session did not alter the result.

The view's initial no-selection state deliberately displayed length `0` and match `false`; the handler did not evaluate `len` on a record in that state. Do not cite this sentinel as proof about an empty selection record.

Discovery and two fresh strict reproductions preserved every earlier key/iteration/item/value alignment, membership, null, missing-member, payload, selection-paint, local-sort, and restore assertion. Each accepted run also required two stable session/page identities, fourteen original-resolution screenshots, exact API tag checkpoints, unchanged project/protected resources, empty browser diagnostics, bounded zero-WARN+ Gateway logs at every edge and after close, baseline restoration, and zero remaining test sessions.

This establishes only that `len(record)` equaled the enumerated key count for these exact synchronous Table `onSelectionChange` records, two schemas, and tested build. It does not establish behavior for an empty constructed record, nested/complex values, mutations, other mapping implementations, other event objects, other Dataset sources, asynchronous retention, Designer behavior, or other builds. Retain the explicit comparison when the equality matters to application correctness.

## Dictionary snapshot conversion

On the tested build, `dict(record)` converted the mapping-like Table selection record into a concrete Jython `dict`. Verify content independently; do not assume the resulting dictionary preserves the record's physical-column key order:

```python
keys = list(record.keys())
values = list(record.values())
snapshot = dict(record)
snapshot_keys = list(snapshot.keys())

key_order_matches = snapshot_keys == keys
content_matches = len(snapshot) == len(keys)
if content_matches:
    for index in range(len(keys)):
        key = keys[index]
        if key not in snapshot or snapshot[key] != values[index]:
            content_matches = False
            break
```

For both independent sessions, baseline records had five members and the snapshot reported type `dict`. Every key/value comparison passed, but the observed key sequence was:

```text
line|count|enabled|assetId|temperature
```

The live record's tested physical-column sequence remained:

```text
assetId|line|count|temperature|enabled
```

After whole-Dataset replacement removed `line` and reordered the four physical columns to `enabled|temperature|count|assetId`, snapshot content still matched completely, while the observed dictionary key sequence was:

```text
count|enabled|assetId|temperature
```

Restoration returned the five-member snapshot and its previously observed dictionary order. Thus, in this exact Jython/runtime fixture, `dict(record)` preserved all tested primitive/null content but did not preserve the source record's key order. Use `list(record.keys())`, `list(record.values())`, or `list(record.items())` when positional alignment with physical Dataset columns matters; use dictionary lookup when order does not matter.

Discovery and two fresh strict reproductions passed the seven-state two-session sequence with exact type, count, order-mismatch, content-match, prior mapping/payload, local-sort, selection-paint, geometry, topology, tag checkpoint, project-integrity, browser-diagnostic, restoration, cleanup, and bounded edge/post-close log assertions. All accepted WARN+ windows were empty.

One incomplete strict attempt is excluded: an official project export stalled until the outer command timeout interrupted orchestration, and the Gateway logged a project-export failure. The exact sessions and orphan observer were terminated, a fresh export completed cleanly, and two full strict runs then passed. Never treat a partial run as evidence, and never waive an export warning as unrelated.

This does not establish deep-copy independence, mutation safety, stable dictionary order beyond these exact observations, serialization behavior, nested/complex equality, Java map conversion, other event objects, other Dataset sources, asynchronous retention, Designer behavior, or other builds. Test those separately.

## Dictionary snapshot top-level mutation

On the tested build, a second local `dict(record)` copy accepted ordinary top-level dictionary replacement, insertion, and deletion without changing the live Table event record:

```python
snapshot = dict(record)
original_asset = str(record["assetId"])
original_count = record["count"]

snapshot["assetId"] = "SNAPSHOT_ONLY"
snapshot["snapshot_probe"] = "ADDED"
del snapshot["count"]

snapshot_changed = (
    snapshot["assetId"] == "SNAPSHOT_ONLY"
    and snapshot["snapshot_probe"] == "ADDED"
    and "count" not in snapshot
)
record_unchanged = (
    str(record["assetId"]) == original_asset
    and record["count"] == original_count
    and "count" in record
    and "snapshot_probe" not in record
)
```

For five-member baseline records, the local copy remained size five after one insertion and one deletion. For the four-member reordered replacement records, it remained size four. In every selected state, `snapshot_changed` and `record_unchanged` were both true. Exact evidence also showed the current record's original asset, `count` still present, and the probe absent. Local sorting, both five-second holds, and restoration did not change the result.

Discovery and two fresh strict reproductions passed the full seven-state, two-session sequence with exact mutation, dictionary conversion/order/content, record enumeration/length/membership, payload, selection-paint, geometry, topology, API tag checkpoint, project-integrity, browser-diagnostic, baseline-restoration, cleanup, and bounded edge/post-close log assertions. All accepted WARN+ windows were empty.

This proves top-level independence only for a newly created local dictionary and the tested primitive String/Integer keys and values. It does not prove deep-copy independence for nested lists, dictionaries, documents, datasets, dates, or other mutable/complex objects. It also does not authorize mutation of the event record itself, establish persistence after the handler returns, or prove safe concurrent/asynchronous use. Test those boundaries separately.

## Runtime evidence gate

1. Export and verify the component type, complete data and column objects, selection object, event path, scope, script text, view custom state, and route.
2. Render the exact route in a caller-approved headless client at a declared viewport.
3. Resolve one unique visible Table body-row container from all expected cell values and click within its geometry. Do not target an ambiguous nested text node.
4. Require the exact visible selected source-row index and every expected field from `event.data`, plus one event-count increment.
5. Select a different row and require replacement rather than retained multi-selection, the second exact payload, and a second event-count increment.
6. Save initial and post-click screenshots, row/header geometry, computed selection styling, URL, browser diagnostics, and official session/page/view metrics.
7. Require a stable session/page, zero reconnects, clean bounded Gateway logs, route/readback success, and exact unchanged projects when the test is interaction-only.

On the tested sequence, selecting source row 1 delivered one record with `BRAVO`, `IDLE`, and `22`; selecting source row 2 next delivered one record with `CHARLIE`, `ALARM`, and `33`. The selected highlight moved from row 1 to row 2, and script executions advanced 0 to 1 to 2. Official expression evaluation counts varied by observation timing and are diagnostic only, not a deterministic event assertion.

## Boundary

This evidence does not establish multi-select, deselection through mechanisms other than the tested same-row pointer and exact array/typed-Dataset empty/restore lifecycles, direct selected-row/data assignments, unchanged property-binding refresh no-ops, bound-result mutations other than the five exact whole-list cases and the exact complete memory-Dataset replacement/shrink/empty sequences above, one exact existing-list-index assignment, one exact nested integer-member assignment, and one exact synchronous three-member sequence tested, a working permanent programmatic-clear recipe, supported component clear APIs, query/historical Dataset behavior, bidirectional Dataset writes, partial Dataset writes, Dataset editing, large or bad-quality Datasets, schema-less or null Datasets, Dataset shape/type changes, duplicate identifiers, dates, Dataset shrink/removal beyond the exact source indices and row counts above, explicit clear during an invalid-index or zero-row gap, other empty-state header/pager configurations, refresh timing, delays beyond five seconds, other assigned values/types, column selection, other stored/runtime `props.selection` properties, other page-relative/source-index combinations, other numeric/date/null/duplicate sorting, custom comparators, repeated cycles beyond the exact tested sequences, multi-column sorting, selection semantics for other sort directions/columns, navigation/reload persistence, filtering, programmatic `activePage`/`activeOption` changes, top pagers, selecting 50/100 or either duplicate option, other stored option arrays/order/duplicates, sizes other than 10/25, other starting/ending pages, selection combined with page-size changes, drag ordering, keyboard/touch behavior, virtualized large-data performance, alternate row-object shapes, other event fields, asynchronous scripts, Designer behavior, reconnect semantics, or other builds. Test each independently before relying on it.
