# Offline Evidence Intake

Use this reference when live runner access is unavailable or the user prefers an evidence-only investigation. Ask for narrow, exportable evidence before requesting broader screenshots or data pulls.

## Contents

- Evidence Request Order
- Missing Evidence Language
- Request Discipline

## Evidence Request Order

1. Incident scope
   - Exact tag paths, provider names, history provider or database connection name when known.
   - Absolute start and end timestamps with timezone or UTC offset.
   - Expected behavior, observed behavior, and whether the concern is operations, reporting, compliance, or root cause.

2. Gateway and module context
   - Ignition version/build, Tag Historian module status, and relevant module versions from screenshots or copied Gateway pages.
   - Keep site names, connection names, and module details only as needed for the report.

3. Current tag context
   - User-provided tag read/export/screenshot with value, quality, timestamp, and fully qualified path.
   - Treat current value evidence as current-state context only. It does not prove historical storage during the incident window.

4. History configuration
   - Tag export, Designer screenshot, or pasted tag JSON showing History Enabled, Storage Provider, Sample Mode, Historical Tag Group or Sample Rate, Min Time Between Samples, Max Time Between Samples, Deadband Style, Deadband Mode, Historical Deadband, interpolation mode, and datatype.
   - If only a screenshot is available, record visible fields and mark hidden properties as unverified.

5. Historian query results
   - User-provided `system.tag.queryTagHistory` output, chart export, report export, or binding result with exact paths, start/end timestamps, return size, aggregation mode, interpolation, quality filtering, scan-class validation, and return format.
   - Treat row counts, non-null counts, and rendered chart points as different evidence types. For multi-tag results, review each returned value column separately.

6. Database evidence
   - User-provided SQL result sets from `sqlth_te`, `sqlth_scinfo`, `sqlth_drv`, `sqlth_partitions`, and relevant `sqlt_data_*` or `sqlth_1_data` tables.
   - Require the query text or a description of filters used before treating empty results as proof.

7. Delivery and log evidence
   - Gateway logs copied by the user, store-and-forward screenshots, database connection status, Memory Buffer, Local Cache, Disk Cache, Quarantined Items, Total Dropped, Write Time, Write Size, quarantine item details, and any retry/delete/export/import history.
   - Separate event timestamps, arrival timestamps, log timestamps, and query execution time.

8. Visualization evidence
   - Power Chart or Easy Chart screenshots/exports with component mode, visible range, pen path, point count or resolution, aggregate mode, interpolation, bad-quality filtering, scan-class validation, cache/bypass setting, and export settings when visible.
   - Treat x-trace values, range-brush summaries, and chart exports as rendered query evidence until direct query or raw storage evidence is reviewed.

## Missing Evidence Language

When evidence is unavailable, state the missing artifact and the claim it prevents. Use wording such as:

- "Unverified: history configuration was not provided, so storage qualification cannot be confirmed."
- "Observed: chart export shows a gap, but raw query rows or SQL evidence were not provided."
- "Inferred: retention may explain the active-store absence, but provider pruning settings or archive evidence are missing."

## Request Discipline

Prefer the smallest artifact that can answer the next question. Ask for exact tag paths and bounded windows before asking for broad exports. Do not request credentials or broad production data when user-provided, read-only evidence can answer the question.
