# Evidence And Reporting

Use this reference for every historian forensic conclusion. Apply the evidence rules before assigning a cause, and use the complete output contract when preparing the report.

## Contents

- Evidence Rules
- Output Contract

## Evidence Rules

- Evidence bundle handling: preserve an artifact inventory when the request includes multiple evidence files or snippets. Do not merge logs, chart exports, SQL rows, screenshots, and user assertions into one undifferentiated evidence pool.
- Material finding discipline: every finding that changes the likely cause, incident scope, compliance posture, or next action must include an evidence grade, the supporting evidence surface or artifact, the claim boundary, and the next proof or approval-required remediation status. Treat root-cause claim language as unverified unless the cited evidence directly supports it.
- Multi-surface routing: when evidence spans more than one surface, read all matching references and preserve the unverified surface list. A chart symptom can coexist with tag identity, retention, query, aggregate, storage qualification, or store-and-forward evidence gaps.
- Query fully qualified tag paths like `[Provider]Folder/Tag` for live API checks.
- Query tag instance paths, not `_types_` UDT definition paths.
- Treat realtime tag paths, historical tag paths, and SQL historian identities as separate evidence surfaces. Same leaf name or a Good current value at the current path is not enough; preserve realtime provider, history provider, historical path, `sqlth_te.id`, `created`, `retired`, datatype, `scid`, `drvid`, and driver/provider identity when identity is in question.
- Treat `system.tag.storeTagHistory` virtual paths and typo paths as possible valid historical identities even when no current realtime tag exists at that path.
- Treat active historian no-row evidence for old windows as active-store evidence only. Check history provider type, data pruning, prune age and units, partition length, internal historian time/point limits, Edge local-history limits, archive/backup/replica availability, and missing `sqlth_partitions` metadata before concluding rows were never stored.
- Treat timestamp rows with all-null value cells as no usable value evidence.
- When using runner `0.3.137+` `historyProbe`, prefer good-quality Count evidence fields `goodSampleHistoryAvailable`, top-level `goodStoredSampleCount`, and per-tag `tagStats[].goodStoredSampleCount` over `rowCount` or `nonNullCount`. Treat `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` as compatibility aliases, not different evidence. False/zero good-sample fields do not prove bad-quality rows are absent. On runner `0.3.108+`, parse non-2xx JSON too because primary `historyProbe` backend failures return top-level `ok: false` while preserving `queryOk`, `sampleCountQueryOk`, `queryError`, and `sampleCountQueryError`. On older runners, treat `historyAvailable`/`nonNullCount` as weaker value-query evidence and escalate to approved Jython or database proof before making stored-history claims.
- For multi-tag queries, evaluate each tag or value column separately. One tag with non-null history does not prove another tag has history.
- Do not treat `historyProbe` as a full raw-history query surface. If raw/on-change rows, `noInterpolation`, bounding values, scan-class execution validation, or bad-quality filtering are decisive, use the Jython/script diagnostic route or database evidence.
- Use `references/jython-history-diagnostics.md` before drafting a Gateway-scope diagnostic script. Keep the script read-only, bounded by exact paths and absolute start/end timestamps, and approved before execution.
- Keep null values, absent rows, bad-quality rows, and rows filtered out by query settings as different states.
- Preserve contradictory evidence as a finding. Do not smooth over conflicts such as Good current value with stale timestamp, successful query with all-null rows, or chart output without backing rows.
- Treat screenshots, trend lines, chart points, and UI exports as symptom evidence until the underlying query settings, binding settings, returned rows, or raw storage evidence are reviewed.
- Treat a trend line or chart point as rendered query output, not raw historian storage proof.
- Treat Power Chart and Easy Chart x-trace values, range-brush aggregates, visible datapoints, and exports as rendered query evidence. Record chart cache/bypass settings, mode, point count or resolution, aggregate mode, interpolation, bad-quality filtering, scan-class validation, and pre-processed partition settings before comparing them with direct query or SQL evidence.
- Treat aggregate outputs as calculations over a query window, not as proof that every underlying raw event was stored. Record `returnSize`, interval, aggregate mode, per-tag aggregate overrides, `includeBoundingValues`, `noInterpolation`, `ignoreBadQuality`, scan-class validation, and return format before comparing aggregates with raw/on-change evidence.
- Treat Average versus SimpleAverage, MinMax, LastValue, CountOn, CountOff, DurationOn, DurationOff, PctGood, and PctBad as different evidence types. A calculated aggregate can answer an operations question while still being too weak for raw-event or compliance proof.
- Treat scan-class validation and stale data detection as quality/downtime evidence surfaces. A bad-quality validation gap is not the same as absent storage, and a flat-looking unvalidated value is not proof that the equipment was good through downtime.
- Treat History Enabled, Storage Provider, Sample Mode, Historical Tag Group or Sample Rate, Min Time Between Samples, Max Time Between Samples, Deadband Style, Deadband Mode, and Historical Deadband as storage qualification evidence. Do not infer those properties from a current value, a chart line, or a sparse query result.
- Treat analog compression and discrete deadband as different storage rules. Small analog movement, missing intermediate points, or a flat trend may be expected compression, but only configuration plus raw/on-change row evidence can support that finding.
- Treat short pulse capture as a sampling problem until raw/on-change edges, counters, explicit event rows, or matching tag group execution evidence prove both edges were captured.
- Treat store-and-forward status as delivery evidence, not storage qualification evidence. Separate Memory Buffer, Local Cache, Disk Cache, Quarantined Items, Total Dropped, database status, schedule holds, event timestamp, and arrival time before claiming data was lost.
- Treat a global quarantine count as weak context until the quarantine item ID, count, description, reason, provider, tag identity, and incident window match the data under investigation.
- Preserve timezone, range boundaries, and query settings in every conclusion.
- For audit or compliance questions, convert relative ranges such as "last hour" into absolute start/end timestamps with timezone before making the final evidence statement.
- Treat wall-clock timestamps without timezone, UTC offset, or epoch milliseconds as incomplete evidence when DST, client/Gateway/database timezone differences, or cross-system comparisons could matter.
- Keep event/sample timestamp, query execution time, database row timestamp, log/arrival time, and UI display time separate.
- For exact function parameters, historian table schemas, or version-sensitive behavior, verify against the official 8.1 documentation linked from the relevant reference and report the target Gateway version/build when available.
- Keep raw current values, history rows, database rows, and Gateway logs conceptually separate.
- Do not call deadband, interpolation, cache, or quarantine the cause without matching configuration, query, log, or database evidence.
- Do not rely on broad Gateway-wide scans when a narrow tag, provider, database, logger, or time window can answer the question.

## Output Contract

Return a concise forensic report with:

- Symptom and scope.
- Evidence inventory and unavailable evidence.
- Reference routes used and evidence surfaces intentionally left unverified.
- Evidence bundle or artifact inventory when user-provided files, screenshots, exports, logs, SQL rows, or configuration snippets were reviewed.
- Contradictions or mixed evidence that could change the conclusion.
- Findings grouped by likely storage, forwarding, retrieval, query, visualization, or database cause.
- Exact tags, providers, time windows, and query settings reviewed.
- Storage qualification evidence reviewed when missing rows may depend on history enablement, sample mode, tag group rate, sample rate, min/max timers, deadband style/mode, historical deadband, analog compression, discrete deadband, or short pulse capture.
- Store-and-forward evidence reviewed when delayed, failed, quarantined, dropped, or late-arriving rows are part of the incident, including Memory Buffer, Local Cache, Disk Cache, Quarantined Items, Total Dropped, Write Time, Write Size, schedule, database status, event timestamp, arrival time, and whether any retry/delete/export/import action would be remediation.
- Identity evidence reviewed when a rename, provider, UDT, virtual path, historical path, or SQL tag-candidate mismatch is plausible.
- Retention, pruning, provider-limit, archive, backup, or active-replica evidence reviewed when old data is missing or compliance retention is part of the question.
- Per-tag or per-value-column status when more than one tag is involved.
- Target Ignition version/build and official documentation basis for any version-sensitive claims, if reviewed.
- Any relative time ranges translated to absolute start/end timestamps with timezone.
- Whether screenshots, charts, or UI exports were used only as symptoms or backed by returned rows/query settings.
- Visualization evidence reviewed when Power Chart, Easy Chart, x-trace, range brush, export, cache, point count, resolution, or pre-processed partition behavior is part of the incident.
- Aggregate and scan-class validation evidence reviewed when aggregate mode, report calculations, `queryTagCalculations`, Average versus SimpleAverage, MinMax, LastValue, CountOn, DurationOn, PctGood, PctBad, bad-quality filtering, stale data detection, or compliance calculations are part of the incident.
- Evidence grade for each finding:
  - **Observed:** direct API, script, database, log, or user-provided evidence.
  - **Correlated:** two or more independent signals point to the same explanation.
  - **Inferred:** likely from configuration or known historian behavior, but not directly proven.
  - **Unverified:** plausible but missing required evidence.
- For each material finding, cite the supporting evidence, state the claim boundary, and name the next proof step or approval-required remediation status.
- Recommended next proof step or approval-required remediation, ordered from least-invasive read-only proof to more invasive diagnostics and finally explicit remediation.
