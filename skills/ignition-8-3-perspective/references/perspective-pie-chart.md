# Perspective Pie Chart

Use this reference only after confirming Ignition 8.3.8 or reproducing the behavior on the installed build. It qualifies the complete tested installed four-chart family. Do not infer Pie serialization or interactions from other chart components, Ignition 8.1, or documentation alone.

## Contents

- [Installed shapes](#installed-shapes)
- [Paint and accessibility](#paint-and-accessibility)
- [Tooltip and slice click](#tooltip-and-slice-click)
- [Legend visibility](#legend-visibility)
- [Reload and fresh-session boundaries](#reload-and-fresh-session-boundaries)
- [Validation workflow](#validation-workflow)
- [Qualification boundary](#qualification-boundary)

## Installed shapes

Every tested component used `type: "ia.chart.pie"`, `enableTransitions: false`, an ordered `colors` array, an ordered `data` array, a title, and title/label styling. Preserve the complete installed object before attempting to minimize it.

The tested family contained:

| Variant | Rows | Qualified distinguishing props |
| --- | ---: | --- |
| Standard | 5 | labels and legend visible; five colors |
| Three-dimensional | 6 | `threeDimensional: true`; `showLabels: false`; legend visible; explicit `valueFormat` |
| No legend | 4 | `showLegend: false`; labels visible |
| Cutout | 3 | `cutoutRadius: 50`; `showLegend: false`; labels visible |

The standard rows used exact objects such as `{"count":36,"flavor":"Pumpkin"}`. The other installed variants used exact objects such as `{"color":"Blue","count":42}`. This proves only the two tested string-member names and numeric `count` values; do not generalize arbitrary key selection without a separate test.

## Paint and accessibility

At a 1400-by-950 viewport, the complete installed page painted four SVG charts and no canvas. Initial path counts were 14, 34, 8, and 7. No chart clipped or overflowed.

Each rendered slice exposed an accessible `menuitem`. The two visible legends exposed 5 and 6 checked `switch` controls. The hidden-legend charts exposed no switches. A switch's computed accessible name came from rendered child text even though the element had no literal `aria-label`; inspect `aria-checked` and text on the actual switch.

Do not assume authored data order equals SVG/DOM order. In the tested three-dimensional chart, the first hittable rendered slice was Yellow even though the first authored row was Blue.

## Tooltip and slice click

Find a real hit point inside a rendered `menuitem` with DOM hit-testing before moving or clicking the mouse. The tested first-rendered-slice tooltips were:

- standard: `Pumpkin : 41.9%`;
- three-dimensional: `Yellow : 5.0%`;
- no legend: `Rainy : 12.5%`;
- cutout: `Desktop : 56.8%`.

Clicking the Pumpkin slice left all five slice paths, five legend swatches, percentages, and switch states unchanged. It changed only transient tooltip/background SVG state while the pointer remained on the slice. Treat data paths/control state separately from tooltip infrastructure. A transient tooltip can exist during immediate DOM inspection and fade before a later screenshot.

## Legend visibility

Clicking the first standard-chart legend switch:

- changed Pumpkin to unchecked `0.0%`;
- reduced the first-chart path count from 14 to 13;
- recalculated Pecan to 34.0%, Apple to 28.0%, Sweet Potato to 20.0%, and Chocolate to 18.0%;
- left the other three charts' data-path and switch signatures unchanged.

Target a legend by role only after asserting the exact switch count and order. Transient slice feedback changed computed accessible lookup behavior without changing the underlying switch data.

## Reload and fresh-session boundaries

Reloading the same session after hiding Pumpkin restored Pumpkin checked at 41.9%, the 14-path first-chart baseline, and all four authored data signatures.

A separate test terminated a session while Pumpkin remained hidden. A genuinely fresh session then opened with the complete authored baseline. Treat legend visibility as session-local transient state for this exact fixture only.

## Validation workflow

1. Extract and preserve the exact installed view and each Pie component.
2. Author through the approved project API and require tokenless rejection, authenticated success, exact three-resource delta, route activation, protected/helper integrity, and clean authoring logs.
3. Capture full-page and per-chart screenshots; record component/SVG geometry, paths, fills, titles, labels, legend switches, clipping, quality overlays, console/page/request diagnostics, and official topology.
4. Discover real slice hit points; verify tooltip text for every distinct variant.
5. Compare identified data-path and switch signatures before/after slice click; classify transient tooltip paths separately.
6. Hide one legend item; verify recalculated values and sibling isolation.
7. Test both same-session reload and a fresh session after terminating a still-mutated session.
8. Query bounded Gateway WARN-or-higher logs at every edge, terminate only the exact qualified test session, inspect cleanup logs, and bracket a final strict run with authenticated project/protected exports.

## Qualification boundary

This reference qualifies only the exact tested four installed shapes, numeric/string rows above, initial paint/path counts, four first-rendered-slice tooltips, transient-only first-slice click, one first-legend hide/recalculation, sibling isolation, reload restoration, fresh-session restoration, and exact no-drift behavior on the tested build. It does not qualify arbitrary schemas, missing/null/negative/zero values, duplicate names, mismatched colors, dynamic bindings, enabled transitions, other 3D/cutout values, other label/value formats, slice events, keyboard/touch activation, multiple hidden slices, resize breakpoints, performance limits, Designer behavior, or other builds.
