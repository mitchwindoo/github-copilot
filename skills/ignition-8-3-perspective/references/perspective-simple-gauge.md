# Perspective Simple Gauge

Use this reference only after confirming Ignition 8.3.8 or reproducing the behavior on the installed build. It qualifies the complete tested installed four-component `ia.chart.simple-gauge` family. Do not infer this schema or its runtime behavior from standard Gauge, another chart, Ignition 8.1, or documentation alone.

## Installed shapes

The tested family contained:

| Variant | Angles | Maximum | Arc distinction | Label |
| --- | --- | ---: | --- | --- |
| Default/180 degree | omitted | 10 | default width | zero decimals, `lb/in²` |
| Filled/360 degree | omitted start, end 540 | 360 | width 88 | two decimals, `°` |
| Thin/240 degree | 150–390 | 130 | width 2 | two decimals, `RPM` |
| Hollow/360 degree | 90–450 | omitted | corner radius 10 | two decimals, `psi` |

An illustrative subset is:

```json
{
  "type": "ia.chart.simple-gauge",
  "props": {
    "arc": {"color": "#FF4747CC", "width": 2},
    "arcBackground": {"color": "#FF4747CC"},
    "startAngle": 150,
    "endAngle": 390,
    "maxValue": 130,
    "label": {"maxDecimal": 2, "units": "RPM"}
  }
}
```

This is not a minimal schema. Preserve the full live-discovered object, including omitted members, until separate equivalence tests qualify normalization.

## Direct live binding

Each tested component bound `props.value` directly to one existing numeric tag:

```json
{
  "propConfig": {
    "props.value": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[provider]path/to/numeric-tag"
        },
        "type": "tag"
      }
    }
  }
}
```

Discover the approved provider and tag path at runtime. This test does not qualify writeback, bad quality, missing paths, or nonnumeric values.

## Paint and live value behavior

At a 1400-by-950 viewport, all four components measured 300 by 250 pixels, painted one SVG and zero canvas elements, and contained 13 paths. The foreground value arc changed its SVG `d` geometry as the direct tag value changed. Unlike the tested standard Gauge, Simple Gauge did not use a moving needle.

The displayed label used `label.maxDecimal` and appended `label.units`. A zero-decimal label can remain textually unchanged for several observations while its foreground arc already moves. Use bounded polling for displayed-label transitions and compare foreground geometry independently.

Reload preserved graphic counts and unit signatures while new live values continued to paint.

## Unicode and screenshot gate

Treat project JSON as UTF-8 explicitly. A rejected run decoded no-BOM UTF-8 through an implicit Windows PowerShell code page and rendered `lb/inÂ²` and `Â°`. Candidate and comparison objects were both corrupted, so semantic self-comparison passed.

For non-ASCII content:

1. read and write with an explicit UTF-8 encoding;
2. assert exact strings or code points independently;
3. inspect the rendered screenshot and DOM/accessibility text;
4. reject mojibake even when import status, project delta, readback, and logs pass;
5. repair only the affected resource through the approved API, then repeat every runtime and cleanup gate.

## Accessibility

Each tested Simple Gauge appeared as a group containing a `Chart` region. The region's accessible name included the live numeric value and units. No pointer-cursor hit region was found. Do not infer keyboard, touch, focus, event, or editable semantics from the accessible value.

## Validation workflow

1. Extract and preserve the exact installed view and all Simple Gauge objects.
2. Decode every JSON resource explicitly as UTF-8 and assert any non-ASCII fixture text independently.
3. Author through the approved API with tokenless rejection, authenticated success, exact delta, semantic readback, route activation, and protected/inventory/helper/log gates.
4. Capture full-page and per-component screenshots; record geometry, SVG/canvas/path counts, label text, clipping, quality, browser diagnostics, accessibility, and official topology.
5. Capture foreground path geometry and labels repeatedly. Require every foreground arc to change; use bounded polling for rounded label changes.
6. Reload and require stable static graphic/unit signatures plus continued live paint.
7. Query Gateway WARN-or-higher logs for authoring, open, observation, reload, exact-session termination, and post-close edges.
8. Terminate only the exact discovered test session and bracket final accepted runs with project/protected no-drift exports.

## Qualification boundary

This reference qualifies only the exact tested four installed shapes, four direct numeric bindings, observed 13-path SVG paint, foreground-arc path changes, rounded labels and units, same-session reload, accessible live Chart names, explicit-UTF-8 repair workflow, exact-session cleanup, and no-drift evidence on the tested build. It does not qualify arbitrary angles, minimums, maxima, widths, radii, colors, missing/null/nonnumeric values, bad quality, writeback, events, alarms, animations beyond observed arc changes, keyboard/touch behavior, reconnect, Designer behavior, performance limits, other configurations, or other builds.

