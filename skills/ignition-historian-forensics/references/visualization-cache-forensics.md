# Visualization Cache And Chart Query Forensics

Use this reference when a Power Chart, Easy Chart, chart export, x-trace, range brush, point count, resolution, cache, or pre-processed partition behavior is part of the historian question. If the decisive issue is aggregate semantics, report calculations, Average versus SimpleAverage, CountOn, DurationOn, PctGood, PctBad, scan-class validation, stale data detection, or bad-quality filtering, also read `aggregate-validation-forensics.md`.

Official references:

- How the Tag Historian System Works: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/how-the-tag-historian-system-works
- Perspective Power Chart: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-chart-palette/perspective-power-chart
- Vision Easy Chart: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/vision-components/charts/easy-chart
- `system.tag.queryTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-queryTagHistory

This reference targets Ignition 8.1. Confirm the Gateway version/build and component version notes before making a final claim about exact chart properties.

## Contents

- Core Rule
- Evidence To Capture
- Power Chart
- Easy Chart
- Pre-Processed Partitions
- Comparison Workflow
- Report Language

## Core Rule

A chart point is rendered query evidence, not raw historian storage proof. A direct query that uses the same tag identity, time window, aggregation, interpolation, quality filter, and return format is stronger evidence than a screenshot, x-trace, range brush, or export.

When chart output differs from script or SQL evidence, keep these causes separate:

- cache or component-query mismatch
- point count or resolution mismatch
- aggregate mode mismatch
- interpolation or fill mismatch
- bad-quality filtering mismatch
- scan-class validation mismatch
- pre-processed partition versus raw data table mismatch
- historical path conversion or identity mismatch
- active-store, archive, retention, or replica mismatch

## Evidence To Capture

Record the exact component, surface, and settings:

- Component: Power Chart, Easy Chart, Time Series Chart, XY Chart, report, script, or binding.
- Mode: realtime, historical, manual, or explicit script query.
- Exact start/end timestamps, timezone, visible range, zoomed range, and exported range.
- Pen source path, including whether the path is a historical path such as `histprov:...`.
- Point count, resolution, resolution mode, aggregate mode, return format, and row/point count.
- Interpolation, fill, bad-quality filtering, scan-class validation, and bounding behavior.
- Cache setting, including Easy Chart `Bypass Tag History Cache` when applicable.
- Provider pre-processed partition setting and Pre-processed Window Size when available.
- Whether the evidence is an x-trace value, range brush aggregate, visible datapoints export, chart table, direct `queryTagHistory` result, or SQL row evidence.

## Power Chart

Power Chart data is a chart query surface. Treat it as rendered evidence until backed by a direct query or raw/on-change rows.

Power Chart details that commonly change the result:

- `config.mode`: realtime or historical.
- `config.pointCount`: number of data points returned for the selected range.
- `pointCount=-1`: retrieves pen data points as stored; this is equivalent to a Tag History binding Query Mode of AsStored.
- Pen `data.source`: non-historical tag paths can be converted to a historical path format for tags that have history enabled. If identity matters, preserve the converted historical path and read `tag-identity-forensics.md`.
- Pen `data.aggregateMode`: values such as Average, MinMax, LastValue, Count, DurationOn, DurationOff, PctGood, and PctBad are calculated query outputs.
- X-trace values are displayed/interpolated values at the selected trace timestamp, not necessarily stored samples.
- Range brush values are aggregate summaries over the selected range.
- Exports contain the datapoints visible on the chart plots; treat them as visible datapoints, not a complete raw-history dump.

## Easy Chart

Easy Chart has chart-specific properties that can make it disagree with a script query.

Review these properties before making a historian claim:

- `Bypass Tag History Cache`: when true, tag history queries do not use the client history cache.
- `Allow Tag History Interpolation`: if enabled and the query mode is not raw, the chart may interpolate gaps.
- `Ignore Bad Quality Data`: can hide stored bad-quality rows from the chart result.
- `Validate Scan Class Executions`: can mark scan-class downtime differently.
- `Tag History Resolution` and `Tag History Resolution Mode`: choose how many points are requested and whether the result is fixed, natural, chart-width-based, or raw.
- `Tag History Resolution=-1`: equivalent to Raw Resolution Mode.
- `Tag History Resolution=0`: equivalent to Natural Resolution Mode.
- Historical mode does not poll; realtime and manual modes can poll.

If an Easy Chart is stale but a direct query now returns rows, classify it as a chart cache or component-query mismatch until a cache-bypassed chart comparison proves otherwise. Do not clear or globally change cache as a forensic proof step unless the user asks for remediation or operational recovery.

## Pre-Processed Partitions

The historian retrieval path discovers database partitions for the query window. If pre-processed partitions are enabled, Ignition may use processed tables for chart or aggregate queries instead of raw data tables.

For Easy Chart, fixed resolution interacts with pre-processed partitions:

- If chart range divided by requested resolution produces a bucket window greater than or equal to the provider Pre-processed Window Size, the chart can use pre-processed partitions.
- If the bucket window is smaller than the Pre-processed Window Size, the raw data table is used.
- Raw/AsStored comparisons should use raw/on-change query settings, not the same fixed-resolution chart output.

Do not say raw history is missing only because a pre-processed or aggregate chart point differs from a raw query. Report the mismatch as resolution/pre-processed-partition evidence until raw rows are checked.

## Comparison Workflow

1. Freeze the incident to exact start/end timestamps with timezone.
2. Preserve the exact chart component, mode, pen path, point count or resolution, aggregate, interpolation, quality, scan-class, and cache settings.
3. Export or capture the chart evidence if it is user-visible, but label it as rendered query evidence.
4. Run or request a direct query with equivalent settings.
5. If storage proof is required, run or request a raw/on-change query and, if needed, read-only SQL against the correct tag identity.
6. Compare per tag or per value column. A chart with one populated pen does not prove every pen has backing rows.
7. Classify the mismatch with the narrowest supported label: cache/component-query, resolution/pre-processed-partition, aggregate, interpolation/fill, quality filter, scan-class validation, identity/path conversion, active-store/retention, or unverified.

## Report Language

Use precise labels:

- "Observed chart output" for screenshots, trend points, x-trace values, range brush summaries, and exports.
- "Observed direct query output" for `queryTagHistory` or binding output with known parameters.
- "Observed raw/on-change rows" only when the query mode or SQL evidence actually supports that claim.
- "Inferred rendered/interpolated value" for x-trace or non-raw chart values that do not correspond to a stored sample.
- "Unverified storage state" when the chart differs from raw evidence but the path, cache, quality, resolution, or retention evidence is incomplete.
