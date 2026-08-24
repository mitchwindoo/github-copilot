# Symptom Playbooks

Use the playbook matching the reported symptom after completing the core incident-definition and evidence-routing steps in `SKILL.md`. Read every additional reference named by the selected playbook.

## Contents

- Good Current Value, Empty History
- Sparse Analog Data Or Flat Trend
- Missing Boolean Or Discrete Events
- Aggregate, Calculation, Or Scan-Class Validation Mismatch
- Delayed Or Backfilled Rows
- Partition Or SQL No-Row Mystery
- Path, Provider, Or Rename Identity Mismatch
- Old History, Retention, Or Archive Gap
- Chart Cache, Resolution, Or Export Mismatch

## Symptom Playbooks

### Good Current Value, Empty History

1. Confirm the exact tag path and current quality with `tagRead`.
2. Compare the current value timestamp with the incident window; a stale Good value is not proof of live sampling during the affected period.
3. Confirm history configuration from tag export, tag browse/config evidence, Designer screenshot, or approved diagnostics.
4. Use `historyProbe` on runner `0.3.137+` or a direct `queryTagHistory` Count diagnostic over a bounded window; interpret the Count result as good-quality sample evidence when `ignoreBadQuality=True`.
5. If timestamp rows exist but value cells are null, treat the query as structurally successful but not proof of stored values.
6. Check storage provider/database status and focused historian/store-and-forward logs before concluding the data was never stored.

### Sparse Analog Data Or Flat Trend

1. Read `references/storage-qualification-forensics.md`.
2. Inspect History Enabled, Storage Provider, Sample Mode, Historical Tag Group or Sample Rate, Min Time Between Samples, Max Time Between Samples, Deadband Style, Deadband Mode, Historical Deadband, interpolation mode, and data type.
3. Compare expected process movement with the configured deadband and sample cadence.
4. Prefer on-change or raw-row evidence before judging compression.
5. Use aggregated trend output only as a symptom; raw rows or on-change results are stronger evidence.

### Missing Boolean Or Discrete Events

1. Read `references/storage-qualification-forensics.md`.
2. Determine whether the signal is a state, pulse, counter, or event.
3. Compare pulse duration with tag execution and historian sample timing.
4. For discrete values, expect rows around changes, not periodic repeats unless max time settings force them.
5. Use `CountOn`, `CountOff`, `DurationOn`, or raw/on-change rows only after checking query settings and range boundaries.
6. For short pulses, recommend non-resetting counters or explicit event rows when the historian sample path cannot reliably capture both edges.

### Aggregate, Calculation, Or Scan-Class Validation Mismatch

1. Capture the exact query surface: `system.tag.queryTagHistory`, `system.tag.queryTagCalculations`, Perspective Tag History binding, Power Chart, Easy Chart, report query, or export.
2. Record aggregate mode per tag: Average, SimpleAverage, MinMax, LastValue, Sum, Minimum, Maximum, DurationOn, DurationOff, CountOn, CountOff, Count, Range, Variance, StdDev, PctGood, or PctBad.
3. Record `returnSize`, interval settings, `includeBoundingValues`, `noInterpolation`, `ignoreBadQuality`, return format, and whether scan-class validation or stale data detection was enabled.
4. For Average versus SimpleAverage mismatches, compare time-weighted versus arithmetic sample evidence before blaming storage.
5. For CountOn, CountOff, DurationOn, or DurationOff mismatches, use raw/on-change rows when the question is whether both boolean edges were stored.
6. For PctGood, PctBad, or ignored bad-quality data, report whether output was filtered or calculated from quality evidence rather than absent rows.
7. For compliance or audit questions, use aggregate/report output as a summary only until raw/on-change rows, quality, exact time bounds, and storage identity are reviewed.

### Delayed Or Backfilled Rows

1. Read `references/store-forward-quarantine-forensics.md`.
2. Check database connection status and store-and-forward evidence.
3. Look for focused logs around the time window using historian, store-and-forward, database, quarantine, or connection terms.
4. Compare row timestamp (`t_stamp`) with query time and any visible late arrival evidence.
5. Separate delayed delivery from interpolation; a later query may show rows that an earlier query did not.
6. Treat quarantine retry/delete/export/import, disk-cache archive/load, and queue recovery as remediation or preservation actions unless the user explicitly asks for recovery.

### Partition Or SQL No-Row Mystery

1. Resolve the tag in `sqlth_te` first.
2. Join through `sqlth_scinfo` and `sqlth_drv` to understand tag group and driver identity.
3. Discover overlapping `sqlth_partitions` rows for the target window.
4. Dedupe partition names before querying data tables.
5. Include datatype-specific value columns and quality in any diagnostic query.
6. Check retired rows, renamed tags, data type changes, and driver/partition mismatch before declaring data absent.
7. For old windows, check retention and pruning evidence before using active-table absence as never-stored evidence.

### Path, Provider, Or Rename Identity Mismatch

1. Capture the exact displayed path, fully qualified realtime path, historical tag path if present, realtime tag provider, history provider, and database connection or historian provider.
2. Confirm whether the evidence is from a current tag read, a historical path such as `histprov:...`, `queryTagHistory`, `browseHistoricalTags`, direct SQL, or a manual/backfill path.
3. For UDTs, verify the instance path and provider; do not diagnose `_types_` definition paths as stored tag identities.
4. When SQL evidence is needed, list every matching `sqlth_te` candidate and compare `id`, `tagpath`, `created`, `retired`, datatype, `scid`, and `drvid` against the incident window before choosing the row to query.
5. If the current tag was renamed, moved, deleted/recreated, or changed type, expect historical evidence to be split across old and new identities.
6. If a realtime tag is missing but historical rows exist or `storeTagHistory` was used, classify the path as virtual, stale, or separately stored until provider/path evidence proves otherwise.

### Old History, Retention, Or Archive Gap

1. Identify whether the provider is datasource, internal, remote, third-party, or Edge, and whether the query is against the active historian, a replica, or an archive.
2. Capture configured data pruning, prune age and units, partition length, internal historian time limit, internal historian point limit, and any external database archival or maintenance jobs when available.
3. For datasource historians, compare the incident window with `sqlth_partitions` coverage before querying data tables. Missing partition metadata is retention evidence, not proof the tag never stored.
4. For internal or Edge historians, do not apply external `sqlth_*` table assumptions. Use provider settings, historical browsing/query evidence, sync evidence, or product edition limits instead.
5. If pruning or archival movement is plausible, grade the finding as active-store absence until archive, backup, replica, export, or audit evidence is checked.

### Chart Cache, Resolution, Or Export Mismatch

1. Identify the component and mode: Power Chart or Easy Chart, realtime, historical, or manual, plus the exact time range, visible range, zoom, and pen source path.
2. Capture chart query settings: point count, resolution or resolution mode, aggregate mode, interpolation, bad-quality filtering, scan-class validation, cache or bypass-cache setting, and any pre-processed partition/provider settings known.
3. Treat x-trace values, range-brush summaries, chart aggregates, and exported visible datapoints as rendered query evidence, not raw stored rows.
4. Compare the chart to a direct `queryTagHistory` diagnostic using the same tags, absolute time window, aggregation mode, interpolation, quality filter, and return format before blaming storage.
5. If the chart differs from direct query evidence, classify the mismatch as cache/component-query, resolution/pre-processed-partition, rendered-interpolation, aggregate/export, or identity/path conversion until raw/on-change rows prove the storage state.
