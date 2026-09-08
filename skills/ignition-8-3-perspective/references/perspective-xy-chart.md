# Perspective XY Chart

Use this reference for the live-tested installed `ia.chart.xy` dual-line shape on Ignition 8.3.8 / Perspective 3.3.8.

## Contents

- [Installed-source boundary](#installed-source-boundary)
- [Data, series, and axes](#data-series-and-axes)
- [Painted result](#painted-result)
- [Legend interaction](#legend-interaction)
- [Tooltip, wheel, and drag boundaries](#tooltip-wheel-and-drag-boundaries)
- [Reload and session boundaries](#reload-and-session-boundaries)
- [Validation gate](#validation-gate)
- [Boundary](#boundary)

## Installed-source boundary

Export an installed 8.3 project containing the component and preserve the complete component object. The tested XY Chart used large nested series and axis defaults; the identifying fragments below are not a qualified minimal schema. Clone the full installed object before adapting tested data, names, position, or outer style.

Do not infer XY Chart serialization from Time Series Chart, Power Chart, Ignition 8.1, or documentation alone.

## Data, series, and axes

The tested component stored one named static source with eleven rows:

```json
{
  "dataSources": {
    "example": [
      {
        "output_temp": 38,
        "process_temp": 63,
        "t_stamp": "Tue Aug 07 2018"
      }
    ]
  }
}
```

The complete fixture used `Int32` numeric members and one String date member. Each of two series mapped the same source and x field but a different numeric y field and y-axis name:

```json
{
  "data": {
    "source": "example",
    "x": "t_stamp",
    "y": "process_temp"
  },
  "label": {"text": "Process Temp"},
  "render": "line",
  "xAxis": "time",
  "yAxis": "process temp"
}
```

The second series used `output_temp`, label `Output Temp`, and y-axis `output temp`.

The one x-axis used `name: "time"`, `render: "date"`, visible label `Time`, date format `M/d`, and input format `yyyy-MM-dd kk:mm:ss`. Both y-axes used `render: "value"`; Process Temp painted on the left and Output Temp used `appearance.opposite: true` on the right.

Preserve the remaining installed series, line, tooltip, axis, and appearance members until separately minimized and tested.

## Painted result

At the tested 1400×950 viewport, each vertically stacked chart measured 1380×325 and remained contained without document overflow. Each painted:

- one SVG;
- two long line paths with distinct signatures;
- eleven visible date ticks from `8/7` through `8/17`;
- the `Time`, `Process Temp`, and `Output Temp` axis labels;
- two pointer-enabled legend hit regions.

The tested primary view contained eight components and zero bindings. Treat exact SVG/path/text counts as fixture diagnostics rather than universal internals.

## Legend interaction

Clicking the Process Temp legend entry:

1. removed exactly the Process Temp long line path;
2. retained the Output Temp line;
3. left both axis labels and both legend labels painted;
4. exposed a visible `[bold]Process Temp[/] hidden` status string.

Clicking the same legend entry again restored the exact initial line signature and exposed the corresponding `shown` status. The untouched sibling chart and a simultaneous second session did not change.

Discover the legend hit region from rendered pointer cursor geometry. Do not assume fixed coordinates or use label text alone as proof that a series is painted.

## Tooltip, wheel, and drag boundaries

Although each installed series serialized `tooltip.enabled: true`, both line paths had computed `pointer-events: none` and the installed line bullets were disabled. Sweeping all 22 exact data vertices produced no visible tooltip or new value text.

For this exact installed shape:

- negative wheel input over the plot was an exact no-op;
- horizontal plot drag was an exact no-op;
- both interactions left the primary, sibling, and second-session line signatures unchanged.

Do not generalize `tooltip.enabled` to reachable tooltips. Bullets, cursors, series appearance, or interaction configuration require separate tests. Do not infer XY pan/zoom behavior from Time Series Chart.

## Reload and session boundaries

Hiding one series and reloading the page inside the same Perspective session restored both authored series and cleared the transient hidden/shown status. A genuinely fresh session also painted both authored series.

The sibling chart and a simultaneous second session remained stable through hide, restore, no-op wheel/drag, and reload. Treat legend visibility as component/session-local transient state for this fixture only.

## Validation gate

1. Save installed source, candidate delta, tokenless/authenticated responses, and semantic export readback.
2. Capture full-page and focused original-resolution screenshots; verify both lines, eleven ticks, opposing axes, legends, containment, and exact geometry.
3. Save path signatures and pointer regions before and after legend hide/restore.
4. Probe actual pointer-event layers before claiming tooltips, pan, or zoom.
5. Use an untouched sibling and a simultaneous second session as isolation controls.
6. Test reload while a series is hidden and open a genuinely fresh session after official cleanup.
7. Correlate every edge with exact URL, official view topology, quality overlays, browser console/page/request diagnostics, and unfiltered Gateway WARN-or-higher logs.
8. Wait for zero active browser pages and inspect delayed-close logs at both cleanup boundaries.

Invalidate and repeat the complete run for every unclassified concurrent warning. If Gateway export later reformats resource metadata, require exact hashes for all unaffected entries and canonical JSON equality for the reformatted file.

## Boundary

This reference qualifies only the complete installed eleven-row, one-source, two-line, one-date-x-axis, two-value-y-axis shape and the exact interactions above on the tested build. It does not qualify a minimized schema, other date formats or input types, missing/null/duplicate/unordered values, dynamic bindings, tag history, multiple sources, bullets, reachable tooltips, cursors, pan/zoom configuration, selection, other render modes, heatmaps, candlesticks, columns, stacked series, axis breaks, logarithmic axes, performance limits, keyboard/touch accessibility, Designer behavior, Power Chart, or other builds.
