# Historian Query Semantics

Use this reference when the symptom involves `system.tag.queryTagHistory`, chart or binding results, interpolation, fill behavior, deadband, analog compression, boolean events, aggregate modes, scan-class validation, stale data detection, or quality.

If the question is whether a value qualified to store because of History Enabled, Sample Mode, Historical Tag Group, Sample Rate, min/max timers, deadband style, deadband mode, historical deadband, analog compression, discrete deadband, or short pulse timing, read `storage-qualification-forensics.md` before interpreting query absence. If the question involves delayed delivery, store-and-forward queues, quarantine, dropped records, database connection recovery, or late-arriving rows, read `store-forward-quarantine-forensics.md`. If the query path is a historical tag path, a renamed/moved tag, a UDT instance, a virtual/backfilled path, or a provider mismatch, read `tag-identity-forensics.md` before comparing returned rows with current tag reads or SQL evidence. If the window is older than expected active retention or may be pruned/archived, read `retention-pruning-forensics.md` before calling no rows a never-stored finding. If the question depends on Average, SimpleAverage, MinMax, LastValue, CountOn, DurationOn, PctGood, PctBad, `queryTagCalculations`, scan-class validation, stale data detection, bad-quality filtering, or aggregate compliance evidence, read `aggregate-validation-forensics.md`. If the question depends on Power Chart, Easy Chart, chart cache, x-trace, range brush, visible datapoints, export, point count, resolution, or pre-processed partitions, read `visualization-cache-forensics.md`.

Official references:

- Configuring Tag History: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/configuring-tag-history
- How the Tag Historian System Works: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/how-the-tag-historian-system-works
- `system.tag.queryTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-queryTagHistory
- `system.tag.storeTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-storeTagHistory
- Store and Forward: https://www.docs.inductiveautomation.com/docs/8.1/platform/database-connections/store-and-forward
- Controlling Quarantine Data: https://www.docs.inductiveautomation.com/docs/8.1/platform/database-connections/store-and-forward/controlling-quarantine-data
- Perspective Power Chart: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/perspective-components/perspective-chart-palette/perspective-power-chart
- Vision Easy Chart: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/vision-components/charts/easy-chart

This reference targets Ignition 8.1. When an exact parameter, default, or changed behavior matters, confirm the Gateway version/build and use the matching official documentation version before making the final claim.

## Contents

- Storage Evaluation
- Retrieval Evaluation
- Analog Deadband And Compression
- Discrete And Boolean Events
- Backfill And Manual Store
- Store-And-Forward Quarantine Actions
- Quality And Downtime

## Storage Evaluation

Ignition evaluates whether to store history through sample mode, min/max timing, deadband, and store-and-forward delivery.

Key checks:

- `History Enabled`
- Storage provider / historical provider
- Sample mode: `On Change`, `Periodic`, or `Tag Group`
- Historical tag group and execution rate
- Minimum and maximum time between samples
- Deadband and deadband style or mode
- Data type and interpolation mode
- Current tag quality and timestamp during the affected window
- Store-and-forward database health and quarantine evidence; use `store-forward-quarantine-forensics.md` for Memory Buffer, Local Cache, Disk Cache, dropped records, and late-arrival analysis

Normal historian storage is sparse. A static value may not create new rows until a maximum-time setting requires a row. Sparse rows are not automatically a failure.

## Retrieval Evaluation

`system.tag.queryTagHistory` can aggregate and interpolate data. A successful query can return rows that are calculated rather than raw stored rows, or rows with timestamps and no usable value.

The function can accept realtime tag paths and historical tag paths. Preserve the exact supplied path format. A `histprov:` path, a `[Provider]Folder/Tag` path, and a SQL `sqlth_te.id` are not interchangeable until identity evidence ties them together.

For compliance or audit questions, record the exact start and end timestamps, timezone, and whether the result came from a script query, binding, chart, runner probe, or database query. Relative windows such as "last hour" are useful for triage but weak evidence unless translated into absolute boundaries. If endpoint, DST, or cross-system timebase differences could change the conclusion, read `time-window-forensics.md`.

Important parameters:

- `returnSize=-1`: on-change style results.
- `returnSize=0`: natural number of rows based on logging rates.
- positive `returnSize`: fixed number of time slices.
- `aggregationMode` or per-tag `aggregationModes`: controls how multiple samples collapse into a slice.
- `returnFormat`: wide or tall.
- `includeBoundingValues`: includes values near query bounds when supported by the mode.
- `validateSCExec`: marks scan-class downtime differently.
- `noInterpolation`: prevents purely interpolated rows.
- `ignoreBadQuality`: excludes bad-quality values from calculations and result sets.

For aggregate mode, aggregate calculations, report calculations, custom aggregates, scan-class validation, stale data detection, or compliance use of calculated history, read `aggregate-validation-forensics.md` before treating the returned rows as raw storage proof. Average versus SimpleAverage, MinMax row shape, LastValue interpolation, CountOn/CountOff/DurationOn/DurationOff, and PctGood/PctBad all answer different questions.

When testing whether raw history exists, prefer on-change/raw evidence and count non-null value cells per tag. In `Wide` output, inspect each tag column separately. In `Tall` output, group rows by path or series identifier before drawing a conclusion. A fixed return size can make empty intervals look like valid time buckets.

Bad-quality rows, null values, and absent rows are different evidence states. If `ignoreBadQuality` or component settings filter bad quality, query output can look empty even when stored rows exist.

Screenshots, rendered trend points, x-trace values, range-brush aggregates, visible datapoints, and chart exports may reflect component settings, cache, point count, resolution, pre-processed partitions, aggregation, or fill/interpolation behavior. Treat them as symptoms until the underlying query settings or returned rows are reviewed. For Power Chart and Easy Chart specifics, read `visualization-cache-forensics.md`.

For old-window queries, a valid empty result from `queryTagHistory`, a chart, or a report query is active-query evidence. It does not prove the value was never stored unless retention/pruning, archive, provider-limit, and identity evidence have also been reviewed.

## Analog Deadband And Compression

Analog history is not a promise to store every small movement. The deadband acts like a compression threshold. To diagnose sparse analog rows:

1. Compare actual process movement with the configured deadband and engineering units.
2. Check sample mode and historical tag group rate.
3. Check min/max time between samples.
4. Compare raw/on-change historian rows with chart output.
5. Avoid blaming deadband when database delivery, tag quality, query window, or interpolation evidence is missing.

## Discrete And Boolean Events

Boolean or discrete history should be treated as change/event evidence, not periodic evidence, unless configuration forces periodic storage.

For missed boolean events:

1. Determine whether the PLC signal is a durable state or a short pulse.
2. Compare pulse width against tag execution and historian sample timing.
3. Check whether the query range includes both edges of the event.
4. Use `CountOn`, `CountOff`, `DurationOn`, `DurationOff`, or raw rows only after checking query settings.
5. Prefer counters or explicit event rows for short pulses that must be auditable.

## Backfill And Manual Store

`system.tag.storeTagHistory` is a write. It can insert historian rows by script, associate rows with historical and realtime providers, and store rows for virtual paths that do not exist in the realtime provider. Paths must be typed precisely because a typo can store valid history under the wrong path. The history system also caches tag data, so deleting metadata rows manually is not a safe repair strategy.

When backfill is suspected:

- Check whether rows have historical timestamps but appeared only after a later store-and-forward recovery or manual write.
- Compare `t_stamp` with log evidence, audit evidence, or script evidence.
- Verify the exact provider and path used for the stored rows.

Before recommending a manual backfill:

- Require a source-of-truth for every value, quality, timestamp, tag path, realtime provider, and history provider.
- Convert timestamps to exact timezone-aware values and document how duplicates or overlapping existing rows will be handled.
- Plan a dry-run, narrow sample, readback query, rollback or correction plan, audit trail, and explicit approval before any write.

## Store-And-Forward Quarantine Actions

Read `store-forward-quarantine-forensics.md` when quarantine, queue delay, dropped records, disk cache, or late-arrival evidence may explain a query result.

Quarantine retry, delete, import, export, archive, and load actions are remediation actions, not read-only diagnostics. Use quarantine counts, logs, Gateway UI evidence, or exported details as evidence first. Fix the root error before retrying quarantined records, and preserve/export records before destructive actions. Do not infer that deleted or retried quarantine records explain an incident unless the affected provider, timestamps, and row identities match the incident window.

## Quality And Downtime

Historian rows carry quality or data integrity. A chart can hide quality details. Database evidence should include quality columns, and script evidence should preserve qualified values when possible.

Use `validateSCExec` thoughtfully. Without scan-class execution validation, values may appear flat and good through downtime. With validation, downtime can appear as bad quality.
