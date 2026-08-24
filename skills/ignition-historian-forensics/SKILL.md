---
name: ignition-historian-forensics
description: Diagnose Ignition 8.1 Tag Historian gaps, sparse or delayed data, deadband, queries, charts, retention, identity, SQL partitions, and store-and-forward anomalies.
---

# Ignition Historian Forensics

Skill version: `1.0.20`  
Stack version: `starter-2026.07.06.04`  
Target Ignition: `8.1.x`  
Runner API: `0.3.148+` recommended for the current read-only historian diagnostics surface; `0.3.137+` remains recommended for good-sample `historyProbe` terminology, `0.3.108+` remains recommended for standardized `historyProbe` backend failure envelopes, and `0.3.79+` remains the minimum for read-only Gateway discovery and the basic `historyProbe` action.

## Scope

Use this skill to explain why Ignition Tag Historian data is missing, sparse, compressed, delayed, backfilled, interpolated, poor-quality, or different from an operator trend or script result.

Full diagnostic coverage: Diagnose Ignition Tag Historian missing, sparse, delayed, compressed, interpolated, filled, backfilled, pruned, retention-limited, bad-quality, or quarantined data. Use for analog deadband, boolean/discrete event gaps, aggregate mode surprises, Average versus SimpleAverage, MinMax, LastValue, CountOn, DurationOn, PctGood, PctBad, scan-class validation, stale data detection, historical tag paths, renamed or deleted/recreated tags, virtual/backfilled paths, queryTagHistory fill/interpolation, Power Chart, Easy Chart, chart cache, x-trace, range brush, pre-processed partitions, store-and-forward delays or quarantine, SQL partitions, datasource pruning, internal or Edge historian limits, archive/active-store mismatches, and compliance questions about whether data was stored, retained, retrieved, rendered, calculated, or inferred.

Default posture is read-only. Do not change tag history settings, write historian rows, alter historian tables, retry quarantine records, clear cache, import resources, or modify Gateway configuration unless the user explicitly asks for remediation and the change path is separately planned, approved, and reversible.

Use adjacent skills when the task shifts:

- Use `ignition-sql-query-builder` for production-ready SQL, Named Queries, and database-specific query syntax.
- Use `ignition-jython-script-builder` for Jython scripts, Project Library code, or custom `system.tag.queryTagHistory` diagnostics.
- Use a UDT-focused workflow when the main question is UDT definition or instance configuration risk.
- Use Perspective host/import/performance skills when the main problem is a screen, binding, or chart implementation rather than historian evidence.

## Required Workflow

1. Define the incident.
   Record exact tag paths, provider names, observed time window, timezone, UTC offset or epoch boundaries when available, target Ignition version/build when available, expected behavior, observed surface, query or chart settings, and whether the concern is operational display, compliance, reporting, or root cause. If the time window is relative, near a daylight-saving transition, or compared across script, chart, database, or log evidence, read `references/time-window-forensics.md`. If the symptom involves storage qualification, History Enabled, Sample Mode, Historical Tag Group, Sample Rate, Min Time Between Samples, Max Time Between Samples, Deadband Style, Deadband Mode, Historical Deadband, analog compression, or a short pulse, read `references/storage-qualification-forensics.md`. If the symptom involves store-and-forward delivery, Memory Buffer, Local Cache, Disk Cache, Write Time, Write Size, Quarantined Items, Total Dropped, arrival time, database connection recovery, or retry/delete/export questions, read `references/store-forward-quarantine-forensics.md`. If the symptom involves a rename, move, deleted/recreated tag, provider or history-provider change, historical tag path, virtual/backfilled path, UDT instance mismatch, or multiple SQL tag identities, read `references/tag-identity-forensics.md`. If the missing data is older than the expected retention period, near a pruning boundary, from an internal or Edge historian, or possibly moved to an archive, read `references/retention-pruning-forensics.md`. If the symptom involves aggregate mode, aggregate calculations, report calculations, Average versus SimpleAverage, MinMax, LastValue, CountOn, DurationOn, PctGood, PctBad, scan-class validation, or stale data detection, read `references/aggregate-validation-forensics.md`. If the symptom is a Power Chart, Easy Chart, x-trace, range-brush value, chart export, chart cache, point count, resolution mode, or pre-processed partition mismatch, read `references/visualization-cache-forensics.md`.

2. Route every matching evidence surface.
   Multi-surface routing matters when one incident includes storage configuration, store-and-forward delivery, query semantics, chart rendering, aggregate calculations, tag identity, retention, SQL rows, logs, or timebase evidence. Read every matching reference before deciding the dominant cause, and record which evidence surfaces remain unverified. Do not let the loudest symptom, such as a chart gap or quarantine count, suppress required routing for identity, retention, storage qualification, aggregate validation, or visualization behavior.

3. Separate storage from retrieval.
   Treat these as different questions:
   - Was the tag configured to store history?
   - Did a sample qualify for storage?
   - Did store-and-forward deliver it to the database?
   - Does raw historian storage contain a row?
   - Did the query, chart, binding, cache, aggregation, or interpolation transform the result?

   For the first two questions, read `references/storage-qualification-forensics.md` before concluding that missing rows are a storage failure. For delivery questions, read `references/store-forward-quarantine-forensics.md` before calling delayed, queued, quarantined, or dropped records lost. A current tag value can be real while its changes did not qualify for historian storage.

4. Discover available evidence.
   If the Web Dev runner is available, read `references/runner-api-forensics.md` and start with `health`. Prefer read-only actions such as `gatewayInfo`, `databaseConnectionsList`, `tagProviders`, `tagBrowse`, `tagRead`, `historyProbe`, and focused `logQuery`. If live runner access is unavailable or the user prefers evidence-only analysis, read `references/offline-evidence-intake.md`.

5. Inventory user-provided evidence bundles.
   When the user provides screenshots, CSVs, JSON exports, chart exports, logs, SQL rows, tag configuration fragments, or quarantine details, create an artifact inventory before diagnosing. Record each artifact name, source surface, timebase, tag/path/provider scope, query or component settings, and whether it is raw evidence, rendered evidence, calculated evidence, configuration evidence, log evidence, or user assertion. Do not infer an artifact's source or meaning from its filename alone; map each artifact to the relevant evidence question, and mark any missing artifact that prevents a stronger conclusion.

6. Verify current tag context separately from history.
   A Good current value only proves the current tag path returned a qualified value at the read timestamp. If that timestamp is stale or outside the incident window, treat it as separate availability evidence. It does not prove history is enabled, that values qualified for storage, or that historical rows exist.

7. Verify historian query behavior.
   For scripting, historical bindings, report queries, and chart data, read `references/query-semantics.md`. For aggregate mode, aggregate calculations, `queryTagCalculations`, bad-quality filtering, scan-class validation, stale data detection, or compliance questions that depend on calculated values, also read `references/aggregate-validation-forensics.md`. For Power Chart, Easy Chart, chart cache, visible datapoints, x-trace, range-brush, export, resolution, point-count, or pre-processed partition questions, also read `references/visualization-cache-forensics.md`. For an approved Gateway-scope read-only `system.tag.queryTagHistory` diagnostic, read `references/jython-history-diagnostics.md`. Use sample-backed Count evidence when proving stored-sample availability; keep non-null value cells as diagnostic context and distinguish raw/on-change rows from aggregated, calculated, interpolated, quality-filtered, or rendered rows.

8. Use database evidence only when needed.
   For partition, datatype, driver, retired-tag, pruning, or raw-row investigations, read `references/historian-sql-forensics.md`. For path/provider identity questions, read `references/tag-identity-forensics.md` first so SQL rows are tied to the correct realtime provider, history provider, driver, and time-overlapping historian identity. For old-window no-row cases, read `references/retention-pruning-forensics.md` before deciding rows were never stored. Query historian tables read-only, resolve metadata before data tables, and never use user-supplied partition table names directly.

9. Classify the most likely failure mode.
   Choose the narrowest classification supported by evidence:
   - not configured to store
   - did not qualify for storage because of sample mode, min/max timer, deadband, or compression
   - current tag unavailable or poor quality during the window
   - store-and-forward delayed, failed, or quarantined writes
   - rows exist but query settings hid, aggregated, interpolated, or filled them
   - rows exist but aggregate mode, aggregate calculations, scan-class validation, bad-quality filtering, or stale data detection changed the returned evidence
   - rows exist under a different tag identity, data type, retired entry, provider, or partition
   - rows once existed but are outside active retention, pruned by provider limits, moved to an archive, or absent from the active replica being queried
   - visualization cache or component binding differs from a direct query
   - chart point count, resolution, pre-processed partition, x-trace, range-brush, export, or cache settings explain a chart/direct-query mismatch
   - evidence unavailable or inconclusive

   For a symptom-specific sequence, read `references/symptom-playbooks.md`.

10. Report with evidence boundaries.
    State what was observed, what is inferred, what remains unverified, and the next least-invasive proof step. Before reporting, read `references/evidence-and-reporting.md`. If any repair, write, configuration change, quarantine action, or cache change is proposed, also read `references/remediation-safety.md`.

## Reference Routes

- Read [Evidence And Reporting](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/evidence-and-reporting.md) before every final finding or report.
- Read [Remediation Safety](remediation-safety.md) before proposing or performing any repair or mutable operation.
- Read [Symptom Playbooks](symptom-playbooks.md) for the matching incident sequence.
- Read [Offline Evidence Intake](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/offline-evidence-intake.md) when runner access is unavailable or evidence-only analysis is preferred.
- Read [Runner API Forensics](runner-api-forensics.md) when the read-only Web Dev runner is available.
- Read [Query Semantics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/query-semantics.md) for `queryTagHistory`, fill, interpolation, return-size, and retrieval behavior.
- Read [Jython History Diagnostics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/jython-history-diagnostics.md) for an approved bounded Gateway-scope diagnostic.
- Read [Historian SQL Forensics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/historian-sql-forensics.md) for external historian metadata, partitions, and raw-row evidence.
- Read [Time Window Forensics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/time-window-forensics.md) for range boundaries, timezones, DST, and cross-system timebases.
- Read [Storage Qualification Forensics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/storage-qualification-forensics.md) for history configuration, sample modes, timers, deadband, compression, and pulse capture.
- Read [Store-And-Forward And Quarantine Forensics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/store-forward-quarantine-forensics.md) for delivery queues, quarantine, drops, and late arrival.
- Read [Tag Identity Forensics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/tag-identity-forensics.md) for renamed, recreated, virtual, historical, provider, UDT, and SQL identities.
- Read [Retention And Pruning Forensics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/retention-pruning-forensics.md) for old-window absence, pruning, provider limits, archives, backups, and replicas.
- Read [Aggregate And Scan-Class Validation Forensics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/aggregate-validation-forensics.md) for aggregate modes, calculation queries, quality filtering, and validation behavior.
- Read [Visualization Cache And Chart Query Forensics](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-historian-forensics/references/visualization-cache-forensics.md) for Power Chart, Easy Chart, cache, x-trace, range brush, export, resolution, and pre-processed partitions.
