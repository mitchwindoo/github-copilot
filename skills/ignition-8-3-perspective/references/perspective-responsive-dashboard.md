# Perspective responsive dashboard integration

Use this reference for the live-tested integration of session-local selection and Table data, shared tag-bound KPI state, a responsive Column Container, and dynamic navigation on Ignition 8.3.8 / Perspective 3.3.8.

## Contents

- [Composition](#composition)
- [Responsive Column sizing](#responsive-column-sizing)
- [Numeric indirect-tag transform](#numeric-indirect-tag-transform)
- [Guarded external shared-state update](#guarded-external-shared-state-update)
- [Session-local Table data](#session-local-table-data)
- [Navigation and state boundary](#navigation-and-state-boundary)
- [Visual and log gate](#visual-and-log-gate)
- [Boundary](#boundary)

## Composition

The original qualified dashboard used:

- one persistent view-custom String as session-local selected-asset state;
- one searchable single-select Dropdown bidirectionally property-bound to that state;
- one Table whose `props.data` binding read the selected asset and used a script transform to return one of two fixed three-record arrays;
- four Embedded View KPI cards with indirect tag bindings in one Column Container;
- one Checkbox bidirectionally bound to a caller-approved shared Boolean memory tag; and
- one Button navigating to a separate dynamic `:asset` route.

Keep local selection separate from shared tag state. In two sessions, changing the asset updated only the initiating session's Dropdown, marker, and Table. Changing the Boolean tag through the Checkbox propagated to both sessions and an independent live tag read.

The five-card extension added a second Embedded View shape whose numeric value used an indirect Speed tag binding plus an expression transform. An external guarded Speed write repainted both the direct Speed card and derived `TARGET - SPEED` card in both sessions while each session retained its own Dropdown, Table dataset, and selected row.

## Responsive Column sizing

The tested Column declared complete `sm:0`, `md:700`, and `lg:1000` child layouts. As a direct child of a vertical Flex root, this position followed its responsive row content:

```json
{
  "position": {
    "basis": "auto",
    "grow": 0,
    "shrink": 0
  }
}
```

At `lg`, the original four 150-pixel cards painted in one row. At `sm`, they painted as four full-width rows. A fixed 330-pixel basis was rejected: DOM and topology still reported every row/view, but screenshots showed the lower two cards clipped.

Require each card rectangle to stay inside the Column rectangle. This `basis: "auto"` result is limited to the exact direct-Flex-child, four-Embedded-View fixture.

The five-card extension independently qualified the same `basis: "auto"` position with exact measured Column widths and complete child layouts:

| Measured Column width | Runtime breakpoint | Tested card rows |
|---:|---|---|
| 1001 | `lg` | 3/2 |
| 1000 | `lg` | 3/2 |
| 999 | `md` | 2/2/1 |
| 701 | `md` | 2/2/1 |
| 700 | `md` | 2/2/1 |
| 699 | `sm` | 1/1/1/1/1 |

Adjust the viewport until the live Column rectangle reaches the target width; viewport width alone does not prove a container breakpoint. At every boundary, require the runtime breakpoint marker, row distribution, five mounted cards, card containment, screenshots, local Table selection, official topology, and a fresh Gateway WARN-or-higher query. This extends the sizing result only to the exact direct-Flex-child five-card fixture and tested layouts.

## Numeric indirect-tag transform

The extension's variance value used the exact single-reference indirect tag shape plus one numeric expression transform:

```json
{
  "binding": {
    "type": "tag",
    "config": {
      "mode": "indirect",
      "references": {
        "tagPath": "{view.params.tagPath}"
      },
      "tagPath": "{tagPath}"
    },
    "transforms": [
      {
        "type": "expression",
        "expression": "75 - {value}"
      }
    ]
  }
}
```

With independently read Good Speed 62.5, the card painted 12.5. After a guarded external write changed Speed to 68.75, both sessions painted direct Speed 68.75 and derived variance 6.25. A guarded restore returned Speed to 62.5 and variance to 12.5. Do not generalize this to bad quality, nulls, other numeric types, multiple references, bidirectional mode, or other expression operators.

## Guarded external shared-state update

When official OpenAPI does not expose a general live tag-value write and compatible `llmImport` advertises `tag-write-v1`, qualify an external update through four separate edges:

1. Dry-run the exact in-scope path and value; require `ok:true`, `accepted:true`, `dryRun:true`, and `writesAttempted:false`, then independently require unchanged value and source timestamp.
2. Attempt one out-of-prefix path; on the tested helper this returned HTTP 200 with `ok:false`, `accepted:false`, and `writesAttempted:false`. Treat the structured body as the rejection, not HTTP status alone, and require zero in-scope drift.
3. Apply the in-scope write with `dryRun:false` and `apply:true`; require `writesAttempted:true`, `allVerified:true`, independent value/timestamp advancement, and correct repaint in both sessions.
4. Dry-run and apply the original baseline, then independently require exact restoration in the tag and both sessions.

Preserve all request/response evidence without credentials. If `llmImport` is absent or does not advertise the action, these POST calls are unavailable; use only the official operations available from `/openapi.json` and do not claim this runtime-write proof.

## Session-local Table data

The Table binding used the selected-asset property as source and a synchronous script transform:

```json
{
  "binding": {
    "type": "property",
    "config": {"path": "view.custom.selectedAsset"},
    "transforms": [
      {
        "type": "script",
        "code": "\tif value == \"LINE_B\":\n\t\treturn [{\"time\":\"08:11\",\"event\":\"Inspection complete\",\"severity\":\"INFO\"}]\n\treturn [{\"time\":\"08:03\",\"event\":\"Shift started\",\"severity\":\"INFO\"}]"
      }
    ]
  }
}
```

The qualified resource returned three complete objects per branch with the same String keys. Selection changed rows without remounting the dashboard or affecting the second session. One real row click painted single-row selection.

Do not generalize to dynamic lengths, mixed schemas/types, asynchronous transforms, query/tag sources, arbitrary objects, selection reconciliation, or large datasets.

## Navigation and state boundary

The Button built a dynamic destination from the current selected asset:

```python
system.perspective.navigate(
    page="/approved/dashboard/detail/" + str(self.view.custom.selectedAsset)
)
```

The route used `:asset` and a matching persistent String input. The detail view painted the exact route value. Browser Back returned through route replacement and reset the dashboard's local selected asset to its authored default. The shared Boolean tag remained external to that lifecycle.

## Visual and log gate

1. Save paired screenshots, component rectangles, exact URLs, selected breakpoint, Table state, Checkbox paint, browser diagnostics, official topology, independent tag values/qualities/timestamps, and official WARN-or-higher logs at every state.
2. Treat Dropdown open as a no-write edge. Require unchanged shared value and source timestamp; an option visible in the menu is not selected state.
3. At narrow width, require every card inside the Column bounds.
4. A Perspective root can own a nested scroll viewport. Locate the nearest ancestor whose scroll height exceeds its client height, scroll it, and save a separate bottom screenshot proving lower controls are reachable.
5. Restore shared test tags and verify them independently.
6. Close both sessions, wait for official topology cleanup, and query logs again. Delayed warnings invalidate an otherwise clean run unless explicitly expected and classified.
7. If unrelated Gateway work contaminates an accepted edge with WARN-or-higher output, preserve and invalidate the run, correlate surrounding official logs and exported resources, wait for a clean window, and repeat the entire strict sequence. Do not silently filter the warning.

The qualified cleanup window exposed an unnecessary integer-tag conversion warning. Reauthoring that display-only count as a tested floating-point memory tag removed it. This proves the need for post-close logs; it is not a general rule to replace integer tags.

## Boundary

This qualifies only the exact two-option String selection, two fixed three-record Table branches, the original four-card Boolean-writeback fixture, the five-card external-Speed fixture, exact 1000/700 Column breakpoints, one numeric indirect expression transform, one dynamic detail navigation, one Browser Back edge, two simultaneous sessions, and the tested build. It does not establish arbitrary filtering, write conflicts, security, bad quality, reconnect/reload persistence, rapid interaction, keyboard/touch behavior, other expressions or numeric types, other component combinations, or other builds.
