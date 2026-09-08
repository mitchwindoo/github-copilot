# Perspective Gauge

Use this reference only after confirming Ignition 8.3.8 or reproducing the behavior on the installed build. It qualifies the complete tested installed six-Gauge family, including single and double axes, direct live tag bindings, range serialization, SVG paint, and needle motion. Do not infer Gauge schema from another chart component, Ignition 8.1, or documentation alone.

## Installed shape

Each tested component used `type: "ia.chart.gauge"`. The axis objects used `data` to select the component value member:

```json
{
  "type": "ia.chart.gauge",
  "props": {
    "startAngle": 140,
    "endAngle": 400,
    "outerAxis": {
      "data": "value",
      "maxValue": 350,
      "percentRadius": 100,
      "ranges": [
        {"color": "#77B6D8CC", "start": 0, "end": 280, "width": 8}
      ],
      "show": true,
      "width": 1
    },
    "innerAxis": {
      "data": "secondaryValue",
      "show": false
    }
  }
}
```

This is an illustrative subset of one qualified installed component, not a minimal schema. Preserve the complete live-discovered object when authoring.

The six tested variants covered:

| Variant | Angle members | Outer scale | Inner scale | Authored ranges |
| --- | --- | --- | --- | ---: |
| Single | 140–400 | default minimum to 350 | hidden | 3 |
| Double | 140–400 | default minimum to 140 | -5 to 5 | 8 |
| Single | omitted | -60 to 60 | hidden | 5 |
| Double | omitted | default minimum to 5500 | -25 to 25 | 8 |
| Single | 90–450 | empty-string minimum to 139.9 | hidden | 3 |
| Double | 90–450 | default bounds | default minimum to 9.9 | 6 |

The family contained 33 range objects. Some ranges had `width: 0`; one minimum was the empty string; several members were omitted. Do not normalize omitted, empty-string, zero-width, or default-valued members until a separate equivalence test proves that safe.

## Bindings

The installed family used direct tag bindings on `props.value` and, for double Gauges, `props.secondaryValue`:

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

Discover the caller-approved provider and numeric tag paths at runtime. The tested family had nine bindings: six outer values and three inner values. This reference does not qualify writeback or nonnumeric quality behavior.

## Paint and live motion

At a 1400-by-950 viewport, the six Gauges painted as SVG and no canvas. The observed path counts were 17, 35, 23, 35, 17, and 29. Axis labels covered positive, negative-to-positive, large comma-formatted, fractional-bound, 260-degree, 180-degree/default-angle, and 360-degree variants.

Every live binding moved its needle during two observations five seconds apart. A single Gauge changed one nested SVG-group rotation. A double Gauge changed two rotation groups. Compare transforms or measured needle geometry; unchanged path counts and axis text do not prove a live binding is updating.

After reload, all six variants retained their static graphic counts and axis-label signatures while the live inputs continued changing. Treat this as exact tested reload behavior, not proof for reconnect, stale quality, or different binding modes.

## Accessibility and interaction boundary

The tested browser exposed each Gauge as a group containing a generic `Chart` region. It did not expose the live numeric value in the captured accessibility tree. No pointer-cursor hit regions were found. Do not claim interactive, keyboard, touch, focus, event, or screen-reader value behavior without separate tests.

## Validation workflow

1. Extract the installed Gauge view and preserve the exact component and binding objects.
2. Count optional `ranges` only after proving the property exists; do not count a missing property as a one-element null array.
3. Author through the approved API and require tokenless rejection, authenticated success, exact resource delta, semantic readback, route activation, protected/inventory/helper integrity, and clean authoring logs.
4. Capture full-page and per-Gauge screenshots, component geometry, SVG/canvas counts, paths, labels, clipping, quality overlays, browser diagnostics, and official mounted-view topology.
5. Capture every graphic's transform and geometry twice across a real tag-update interval. Require one moving needle per single Gauge and two per double Gauge.
6. Reload in the same session and require stable static signatures plus continued dynamic behavior.
7. Distinguish the primary view's binding count from page-level totals contributed by docks or other mounted views.
8. Query bounded Gateway WARN-or-higher logs at authoring, open, observation, reload, exact-session termination, and post-close edges.
9. Terminate only the exact API-discovered test session, verify `terminated: 1` and absence, then bracket final runtime work with project and protected-project no-drift exports.

## Qualification boundary

This reference qualifies only the exact installed six-Gauge family, 33 authored ranges, nine direct numeric tag bindings, single/double-axis SVG paint, observed label and path signatures, live needle rotation, same-session reload, official topology, and clean exact-session cleanup on the tested build. It does not qualify arbitrary ranges, missing/null/nonnumeric values, bad tag quality, range visibility equivalence for `width: 0`, runtime property writes, bidirectional bindings, events, alarms, animations beyond observed needle motion, accessibility beyond the captured tree, touch/keyboard interaction, reconnect, Designer behavior, performance limits, other configurations, or other builds.

