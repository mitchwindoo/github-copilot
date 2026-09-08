# Perspective Chart Range Selector

Use this reference for the live-tested static `ia.chart.chartrangeselector` shape on Ignition 8.3.8 / Perspective 3.3.8.

## Contents

- [Installed source discovery](#installed-source-discovery)
- [Static data and selected range](#static-data-and-selected-range)
- [Bound selection feedback](#bound-selection-feedback)
- [Static selector-driven filtering](#static-selector-driven-filtering)
- [Live tag-history selector and guarded query](#live-tag-history-selector-and-guarded-query)
- [Painted result](#painted-result)
- [Pointer interactions](#pointer-interactions)
- [Reload and session boundaries](#reload-and-session-boundaries)
- [Validation gate](#validation-gate)
- [Boundary](#boundary)

## Installed source discovery

Begin with an official export of an installed project containing the component. The tested installed examples used tag-history bindings for `props.data`; one paired the selector with a Time Series Chart whose query consumed `selectedRange.start` and `.end`. A separate installed instance serialized numeric epoch-millisecond start/end values directly.

The Ignition 8.3 component documentation separately permits object, array, and Dataset data. Test the static array form independently before combining the selector with history bindings or scripted queries.

## Static data and selected range

The qualified static shape used ordered objects containing numeric epoch-millisecond `time` and two numeric value members:

```json
{
  "type": "ia.chart.chartrangeselector",
  "meta": {"name": "RangeSelector"},
  "props": {
    "areaStyles": {"colorScheme": "YlGnBu"},
    "brushRange": {"visible": true},
    "data": [
      {"Pressure": 12, "Temperature": 52, "time": 1560469431423},
      {"Pressure": 42, "Temperature": 18, "time": 1560469432423},
      {"Pressure": 81, "Temperature": 26, "time": 1560469433423}
    ],
    "enablePanZoom": true,
    "selectedRange": {
      "start": 1560469433423,
      "end": 1560469438423
    }
  }
}
```

The complete fixture used ten rows. The selector automatically painted both tested numeric members as filled series. Do not generalize to strings, nulls, bad quality, unordered/duplicate/missing times, arbitrary member counts, or alternate object shapes.

## Bound selection feedback

Two sibling Labels used property bindings to expose the tested range members:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "path": "../RangeSelector.props.selectedRange.start"
        },
        "type": "property"
      }
    }
  }
}
```

Use `.end` for the second label. A third sibling Label calculated seconds without a script:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "expression": "({../RangeSelector.props.selectedRange.end} - {../RangeSelector.props.selectedRange.start}) / 1000"
        },
        "type": "expr"
      }
    }
  }
}
```

The authored initial start/end rendered as numeric text. After the first pointer interaction, those direct bindings rendered JSON-quoted ISO date strings while the subtraction expression continued to return numeric seconds. Do not assume stable user-facing display types across initial and interactive states; add a separately tested normalization/formatting transform when presentation matters.

## Static selector-driven filtering

The tested sibling Time Series Chart bound `props.series[0].data` to the whole selected-range object and applied one script transform:

```json
{
  "propConfig": {
    "props.series[0].data": {
      "binding": {
        "config": {
          "path": "../RangeSelector.props.selectedRange"
        },
        "transforms": [
          {
            "code": "<the endpoint-normalizing inclusive filter below>",
            "type": "script"
          }
        ],
        "type": "property"
      }
    }
  },
  "props": {
    "series": [
      {"name": "Filtered", "data": []}
    ]
  }
}
```

The serialized script-transform code used one leading tab on each top-level line and additional tabs for nested blocks. Its tested logic was:

```python
def toMillis(endpoint):
    try:
        return endpoint.getTime()
    except:
        return long(endpoint)

rows = [
    {"Pressure": 12, "Temperature": 52, "time": 1560469431423},
    {"Pressure": 42, "Temperature": 18, "time": 1560469432423},
    {"Pressure": 81, "Temperature": 26, "time": 1560469433423}
]
start = toMillis(value["start"])
end = toMillis(value["end"])
return [row for row in rows if row["time"] >= start and row["time"] <= end]
```

The complete fixture used the same ten rows as the selector. The `getTime()` branch handled interaction-produced date-like endpoints; the `long(...)` fallback handled authored numeric endpoints. The inclusive result list of dictionaries deserialized directly as Time Series Chart data.

A separate visible feedback Label bound to `../FilteredChart.props.series[0].data` and used one script transform whose serialized code was `\treturn len(value)`. Do not accept this count alone: correlate it with the chart's visible time extent, path signatures, clean quality, screenshots, and logs.

At the fixed tested viewport and exact pointer distances, the filter produced six initial rows, then five after brush move, four after left-handle resize, and two after a new brush selection. Each result produced a distinct chart time extent and SVG path signature. Selector wheel zoom left the two-row result unchanged because `selectedRange` did not change. Same-session reload preserved the two-row filtered result; a fresh session restored six rows.

## Live tag-history selector and guarded query

The qualified live-history fixture referenced three existing, history-enabled numeric tags and performed no tag writes. Its selector bound `props.data` directly to one hour of history:

```json
{
  "binding": {
    "config": {
      "aggregate": "MinMax",
      "avoidScanClassValidation": true,
      "dateRange": {
        "endDate": "now(0)",
        "startDate": "dateArithmetic(now(0), -1, 'hour')"
      },
      "ignoreBadQuality": false,
      "preventInterpolation": false,
      "returnFormat": "Wide",
      "returnSize": {"numRows": "100", "type": "FIXED"},
      "tags": [
        {"path": "[provider]folder/tag0"},
        {"path": "[provider]folder/tag1"},
        {"path": "[provider]folder/tag2"}
      ],
      "valueFormat": "DATASET"
    },
    "type": "tag-history"
  }
}
```

Replace the example paths with independently read-back, history-enabled tags in the approved provider. Confirm the history provider is healthy and populated; tag configuration alone does not prove query results.

The selector's `props.selectedRange` used `now(0)` plus one script transform:

```python
return {
    "start": system.date.addMinutes(value, -15),
    "end": system.date.addMinutes(value, -5)
}
```

The sibling Time Series Chart bound `props.series[0].data` through an expression-structure binding with `waitOnAll: true`:

```json
{
  "config": {
    "struct": {
      "endTime": "{../RangeSelector.props.selectedRange.end}",
      "startTime": "{../RangeSelector.props.selectedRange.start}"
    },
    "waitOnAll": true
  },
  "type": "expr-struct"
}
```

Do not call history directly with those values. On the tested build, the exact installed sample transform fired once with placeholder endpoints and logged a page-specific history-query ERROR: the requested timestamp went backward from `0` to `-1`. The page later painted valid history, so screenshots, HTTP 200, and eventual binding recovery did not reveal the failed startup edge.

Guard the transform before querying:

```python
startTime = value["startTime"]
endTime = value["endTime"]
try:
    startMillis = startTime.getTime()
    endMillis = endTime.getTime()
except:
    return []
if startMillis >= endMillis:
    return []
tags = [
    "[provider]folder/tag0",
    "[provider]folder/tag1",
    "[provider]folder/tag2"
]
return system.tag.queryTagHistory(
    paths=tags,
    startDate=startTime,
    endDate=endTime,
    returnFormat="Wide",
    intervalMinutes=1
)
```

Serialize the normal Perspective script-transform indentation used by the target export. This guard was validated twice from fresh browser sessions: both selector and downstream chart painted three historical traces, a real brush move changed both selected endpoints and the downstream chart path signatures, the ten-minute span remained constant, and client diagnostics plus navigation, interaction, and delayed-close Gateway WARN-or-higher windows were empty.

Treat `waitOnAll` as insufficient protection against semantically invalid startup values. Validate endpoint type and ordering inside the script that performs the external query.

## Painted result

At the tested 1400x950 viewport, the selector root measured 1380x250. It painted one SVG, six nonempty paths, two filled data areas, x/y axes, a range footer, one brush move region, and two narrow horizontal resize handles. The exact initial fixture produced a 726.666748x173 move region plus 6- and 7-pixel resize handles.

Treat these counts and dimensions as exact-fixture diagnostics, not universal internals. Require screenshot inspection in addition to DOM/SVG inventory.

## Pointer interactions

Using cursor-discovered hit regions at the fixed viewport:

1. Dragging the brush interior moved both endpoints by the same amount and preserved duration.
2. Dragging the left resize handle changed only the start endpoint and duration.
3. Dragging across an unselected plot region created a new brush and updated both endpoints.
4. Negative-wheel input changed visible axis/path geometry without changing `selectedRange`. The tested zoomed state did not paint the brush because the selection matched the displayed domain.

The interacted selector did not alter a separate static Time Series Chart or a second simultaneous browser session. Treat selection and zoom as session/component local for this fixture only.

## Reload and session boundaries

Reload and a new browser session produced different outcomes:

- Reload restored the full static viewport after wheel zoom but preserved the modified `selectedRange` and brush inside the same Perspective session.
- Closing that session, waiting for official topology cleanup, and opening a fresh session restored the complete authored numeric initial state.

Do not describe reload as a reset for this component. Distinguish page reload/reconnect behavior from a genuinely new server-side Perspective session.

## Validation gate

1. Save installed source evidence, the exact candidate delta, tokenless/authenticated authoring responses, and exact export readback.
2. Capture original-resolution full-page and focused selector screenshots. Require complete containment, plotted data, axes, range footer, brush, and bound feedback.
3. Inventory paths, axes, brush move region, and resize-handle geometry before interaction; discover hit regions from rendered cursor behavior.
4. For every move, resize, new-selection, wheel, reload, and fresh-session edge, save exact start/end/duration values, brush rectangles, path signatures, URL, and paired screenshots.
5. Use an untouched sibling component and a second session as isolation controls.
6. Correlate every edge with official session/page/view topology and browser console/page/request diagnostics.
7. Wait for the modified session to disappear before opening the fresh-session control.
8. Query and save official Gateway WARN-or-higher logs at authoring, every client edge, both delayed cleanup boundaries, and final audit. Reject the complete run for any unclassified or concurrent warning; do not filter it.

The tested selector exposed pointer/SVG interaction rather than qualified native keyboard semantics. Do not claim keyboard accessibility without a separate test.

## Boundary

This reference qualifies the exact static ten-row/two-numeric-member shape, numeric initial selected range, tested sibling property/expression bindings, exact static endpoint-normalizing inclusive filter, and the exact three-tag live-history shape with the guarded selected-range query. It also qualifies the tested fixed-viewport pointer geometry, drag distances, wheel delta, static reload/fresh-session boundaries, and live-history brush-to-chart handoff on the tested build. It does not qualify arbitrary history providers, tag counts or types, aggregates, query intervals, history backfill, live subscription refresh, empty/one-row results, unguarded query transforms, arbitrary schemas or endpoint types, touch/pinch input, keyboard accessibility, performance limits, Designer behavior, or other builds.
