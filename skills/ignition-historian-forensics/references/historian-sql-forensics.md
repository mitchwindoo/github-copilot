# Historian SQL Forensics

Use this reference when direct database evidence is needed. Keep database work read-only unless the user explicitly requests a separate remediation plan. Use `storage-qualification-forensics.md` when no-row SQL evidence may be explained by history enablement, sample mode, tag group timing, min/max timers, deadband, analog compression, discrete deadband, or short pulse capture. Use `store-forward-quarantine-forensics.md` when rows may have qualified but were delayed, quarantined, dropped, or delivered after the first query. Use `tag-identity-forensics.md` first when a rename, provider, historical path, virtual path, or multiple `sqlth_te` candidate problem could decide which tag identity to query. Use `retention-pruning-forensics.md` when an old-window no-row result may be caused by provider pruning, partition deletion, internal/Edge limits, archival movement, or active-replica mismatch. Use `aggregate-validation-forensics.md` when aggregate calculations, scan-class validation, stale data detection, or bad-quality windows must be reconciled with raw SQL rows. Use `ignition-sql-query-builder` for production-ready SQL or database-specific syntax.

Official reference:

- Ignition Database Table Reference: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/ignition-database-table-reference

This reference targets Ignition 8.1 external historian schema concepts. Confirm the Gateway version/build and provider type before applying table names or partition assumptions to a customer system.

## Contents

- Read-Only Boundary
- External Historian Tables
- Diagnostic Order
- PostgreSQL Sketches
- Empty Result Checklist
- Internal Historian

## Read-Only Boundary

Do not repair historian evidence with direct `INSERT`, `UPDATE`, `DELETE`, or metadata edits against `sqlth_*`, `sqlt_data_*`, `sqlth_1_data`, or internal historian tables. Direct table edits can corrupt tag identity, cache assumptions, partition consistency, quality evidence, and auditability. Use SQL here to diagnose, quantify, and preserve evidence. If the user explicitly requests table-level repair, stop the forensic path and require a separate database remediation plan with backups, source-of-truth rows, rollback, and post-write readback.

## External Historian Tables

Ignition Tag Historian is metadata plus partitioned data, not one table per tag.

- `sqlth_te`: tag metadata. Resolve `tagpath` to `id`; includes `scid`, datatype, query mode, created, and retired timing.
- `sqlth_scinfo`: tag group or scan-class metadata; links to a driver ID.
- `sqlth_sce`: tag group execution periods.
- `sqlth_drv`: driver or Gateway/provider identity.
- `sqlth_partitions`: time ranges mapped to concrete `sqlt_data_*` tables.
- `sqlt_data_*`: raw sample rows with `tagid`, datatype-specific value columns, quality, timestamp, and flags.
- `sqlth_1_data`: single-table storage when partitioning is disabled.
- `sqlth_annotations`: historian annotations.

The data tables store values in datatype-specific columns such as `intvalue`, `floatvalue`, `stringvalue`, and date/time columns. Include raw columns when the tag type is uncertain.

## Diagnostic Order

1. Convert the investigation window to epoch milliseconds.
2. Resolve the tag in `sqlth_te`; account for provider prefixes being absent and paths being normalized.
3. Join `sqlth_te.scid` to `sqlth_scinfo.id`.
4. Join `sqlth_scinfo.drvid` to `sqlth_drv.id`.
5. Discover overlapping `sqlth_partitions` rows for the driver and time window.
6. Dedupe `pname`.
7. Query only discovered data tables.
8. Include raw value columns, `dataintegrity`, `t_stamp`, and any previous-value/gap columns needed for the symptom.
9. Check retired rows, renamed tags, data type changes, and driver/partition mismatch before declaring data absent.

When the incident may predate a rename, move, delete/recreate, datatype change, provider change, or manual backfill, list all plausible `sqlth_te` rows and filter them by overlap with the incident window. Do not query only the current or unretired row unless it is the only candidate whose `created`/`retired` range overlaps the window. Preserve `sqlth_te.id`, `created`, `retired`, datatype, `scid`, `drvid`, and `sqlth_drv` provider details in the evidence.

Use half-open time windows (`>= start_ms` and `< end_ms`) consistently when comparing database evidence with script or chart results. Record the timezone used to convert human-readable incident times into epoch milliseconds. If the window is relative, crosses a daylight-saving transition, or is being compared against a script/chart inclusive endpoint, read `time-window-forensics.md` before deciding rows are absent.

For multi-tag investigations, keep counts grouped by `tagid` and resolved tag path. A populated partition or data table for one `tagid` is not evidence that neighboring tags have rows. Preserve `dataintegrity` or quality values so bad-quality rows are not mistaken for missing rows.

For scan-class validation or stale data detection questions, keep `sqlth_sce` separate from data-table evidence. `sqlth_sce` records tag group execution periods, while `sqlt_data_*` or `sqlth_1_data` records value rows. A gap in scan-class execution can support a validation-generated bad-quality finding, but it is not by itself proof that a value row was deleted or never existed. If the user is comparing this evidence with Average, LastValue, CountOn, DurationOn, PctGood, PctBad, or report calculations, read `aggregate-validation-forensics.md`.

For old windows, partition absence is not automatically tag absence. Check history provider data pruning, prune age/units, partition length, duplicate history providers, internal historian limits, Edge limits, and external archive or database maintenance evidence before saying data was never stored. If `sqlth_partitions` has no overlapping partition for the correct `drvid`, report active-store absence unless retention or archive evidence closes the loop.

## PostgreSQL Sketches

Resolve candidate tag metadata:

```sql
SELECT
  te.id AS tagid,
  te.tagpath,
  te.scid,
  te.datatype,
  te.querymode,
  te.created,
  te.retired,
  sc.scname,
  sc.drvid,
  drv.name AS driver_name,
  drv.provider AS driver_provider
FROM sqlth_te te
LEFT JOIN sqlth_scinfo sc ON sc.id = te.scid
LEFT JOIN sqlth_drv drv ON drv.id = sc.drvid
WHERE lower(te.tagpath) = lower(:tag_path_without_provider)
   OR lower(te.tagpath) LIKE lower(:tag_path_suffix)
ORDER BY te.retired NULLS FIRST, te.created DESC;
```

Find overlapping partitions:

```sql
SELECT
  p.pname,
  min(p.start_time) AS start_time_ms,
  max(p.end_time) AS end_time_ms,
  p.blocksize,
  p.flags
FROM sqlth_partitions p
WHERE p.drvid = :driver_id
  AND p.start_time < :end_ms
  AND p.end_time > :start_ms
GROUP BY p.pname, p.blocksize, p.flags
ORDER BY min(p.start_time);
```

Inspect one discovered data table:

```sql
SELECT
  d.tagid,
  d.t_stamp AS t_stamp_ms,
  to_timestamp(d.t_stamp / 1000.0) AS ts_utc,
  d.intvalue,
  d.floatvalue,
  d.stringvalue,
  d.dataintegrity,
  d.vtype
FROM public.sqlt_data_1_2026_06 d
WHERE d.tagid = :tagid
  AND d.t_stamp >= :start_ms
  AND d.t_stamp < :end_ms
ORDER BY d.t_stamp;
```

Treat table names as identifiers, not bind parameters. Discover them from `sqlth_partitions`, validate that each matches the expected historian table shape, and build any `UNION ALL` in trusted code. Never accept a partition table name directly from user input.

## Empty Result Checklist

When raw SQL returns no rows:

- Did `sqlth_te` resolve the tag path?
- Is the matching row retired, renamed, or a different datatype version?
- Does the row's `scid` point to the expected driver?
- Does the matching `drvid` and `sqlth_drv.provider` match the realtime provider/history provider being investigated?
- Are there partitions for that driver and window?
- If no partition overlaps an old window, is provider data pruning, partition deletion, archive movement, or a replica/backup boundary plausible?
- Is partitioning disabled, requiring `sqlth_1_data` instead of `sqlt_data_*`?
- Do rows exist in a nearby partition but outside the requested time boundary?
- Is the value stored in a different datatype column?
- Is quality poor or filtered out by a higher-level query?
- Is there a driver/partition mismatch edge case?

## Internal Historian

Internal history providers use local Ignition storage rather than the external `sqlth_*` table scheme. The database table reference documents internal tables such as `tagdata`, `tagdetails`, `tagproperties`, and `tags`. Do not apply PostgreSQL partition assumptions to internal historian evidence. For internal or Edge retention questions, use `retention-pruning-forensics.md`.
