# Perspective Time Series Chart

Use this reference for the live-tested static `ia.chart.timeseries` shape on Ignition 8.3.8 / Perspective 3.3.8.

## Contents

- [Installed source discovery](#installed-source-discovery)
- [Static series data](#static-series-data)
- [Line and area trends](#line-and-area-trends)
- [Painted result](#painted-result)
- [Pointer interactions](#pointer-interactions)
- [Validation gate](#validation-gate)
- [Boundary](#boundary)

## Installed source discovery

Begin with a fresh official export of an installed project containing the component. The tested source inventory contained both:

- dedicated chart examples whose `props.series[0].data` used a `tag-history` binding; and
- a separate self-contained chart whose `series[0].data` was an inline array of objects.

Use the static shape to learn component fundamentals without conflating them with tag-history configuration. Do not infer one shape from the other.

## Static series data

The tested component used one named series and ordered objects containing epoch-millisecond `time` plus two numeric members:

```json
{
  "type": "ia.chart.timeseries",
  "props": {
    "series": [
      {
        "name": "Process",
        "data": [
          {"Pressure": 12, "Temperature": 52, "time": 1560469431423},
          {"Pressure": 42, "Temperature": 18, "time": 1560469432423},
          {"Pressure": 81, "Temperature": 26, "time": 1560469433423}
        ]
      }
    ]
  }
}
```

The fully tested fixture used ten rows. With the exact empty trend `columns` shape below, the chart automatically painted both numeric members as independent Pressure and Temperature traces/areas and legend items. Do not generalize to strings, nulls, bad quality, duplicate/missing times, unordered rows, arbitrary member counts, or multiple series.

## Line and area trends

The tested line and area charts differed only by `trends[0].type` and title text. This is the qualified core:

```json
{
  "defaultStyles": {
    "colorScheme": "Paired",
    "normal": {"stroke": {"width": 2}}
  },
  "legend": {"visible": true},
  "plots": [
    {
      "axes": [],
      "markers": [],
      "relativeWeight": 1,
      "trends": [
        {
          "axis": "",
          "baselines": [],
          "breakLine": true,
          "columns": [],
          "interpolation": "curveLinear",
          "radius": 3,
          "series": "Process",
          "stack": true,
          "type": "line",
          "visible": true
        }
      ]
    }
  ],
  "series": [
    {"name": "Process", "data": "<the tested row array>"}
  ],
  "title": {"visible": true, "text": "STATIC PROCESS - LINE"},
  "timeRange": {
    "visible": true,
    "dateFormat": "M-D-YYYY",
    "timeFormat": "h:mm:ss"
  }
}
```

Use `"type":"area"` for the separately reproduced area chart. The tested chart also used a complete x-trace object derived from the installed sample:

```json
{
  "xTrace": {
    "visible": true,
    "line": {
      "visible": true,
      "color": "var(--neutral-90)",
      "dashArray": 0,
      "opacity": 0.5,
      "width": 1,
      "style": {}
    },
    "infoBox": {
      "visible": true,
      "width": 120,
      "showTime": true,
      "dataFormat": "0,0.##",
      "fill": {"color": "var(--neutral-10)", "opacity": 0.9},
      "stroke": {
        "color": "var(--neutral-90)",
        "dashArray": 0,
        "opacity": 0.5,
        "width": 1
      },
      "style": {}
    }
  }
}
```

## Painted result

At the tested 1400x950 viewport, two side-by-side chart roots each measured 666x594. Both painted:

- title;
- numeric y-axis ticks;
- time x-axis ticks;
- two independent Pressure/Temperature plots;
- full-input time-range footer; and
- two legend items.

The line chart contained four nonempty SVG paths and the area chart six. Each chart used three SVG descendants and no circle nodes. These counts are exact-fixture diagnostics, not universal component internals.

Filled-area path bounding boxes can extend outside the visible plot while an SVG clip path constrains paint. Require screenshot inspection and clip-aware geometry; do not reject the chart solely because an unclipped path rectangle extends beyond the component.

## Pointer interactions

For one exact plot coordinate and static ten-row fixture:

1. Hover added two SVG trace lines and a tooltip with exact time and both numeric values. Plot-path hashes did not change.
2. Negative wheel input changed x-axis tick density and plot-path hashes.
3. A real horizontal pointer drag changed ticks and path hashes again and cleared the tooltip.
4. Positive wheel input changed ticks and paths again; moving over the plot produced a different exact data-point tooltip.
5. Reload restored the initial line and area signatures exactly.

The interacted line chart did not alter the sibling area chart or a second simultaneous browser session. Treat zoom/pan state as session/component local for this fixture only.

The visible time-range footer continued to show the full static input extent while the plotted viewport zoomed and panned. Do not use that footer alone to prove the current zoom window.

## Validation gate

1. Save the exact source export, candidate delta, authenticated/tokenless authoring responses, and exact export readback.
2. Capture original-resolution full-page and focused chart screenshots. Require complete title, axes, plot, time range, legends, and page containment.
3. Inventory chart/SVG/path/line/text geometry before interaction.
4. For hover, wheel, and drag, save the changed text/tick/path signatures and paired screenshots. Browser API completion alone does not prove the chart reacted.
5. Use a second session and untouched sibling chart as isolation controls.
6. Correlate every edge with official session/page/view topology and browser console/page/request diagnostics.
7. Query and save official Gateway WARN-or-higher logs at authoring, every client edge, after delayed session cleanup, and final audit.

The tested chart exposed little native accessibility semantics: the title group had `tabindex=-1`, while plot interaction was SVG/pointer based. Do not claim keyboard accessibility without a separate test.

## Boundary

This reference qualifies only the exact static one-series/two-numeric-member shape, explicit line and area trends, tested x-trace object and plot coordinate, tested wheel deltas, tested horizontal drag, reload reset, two-session/sibling isolation, and tested build. It does not qualify tag-history bindings, Chart Range Selector, live updates, multiple series, arbitrary columns or axes, other trend/interpolation/stack settings, legend interaction, events, annotations, export, keyboard/touch input, reconnect persistence, Designer behavior, performance limits, or other builds.
