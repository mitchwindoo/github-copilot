# Tag Historian PostgreSQL Guardrails

Use this reference for Ignition 8.1 Tag Historian queries stored in PostgreSQL.

## Contents

- Storage Shape
- Tag Path Resolution
- Partition Selection
- Driver/Partition Mismatch
- Time And Display
- Values And Quality
- Empty Result Debug Order
- Dynamic SQL Safety
- SQL Comments

## Storage Shape

Ignition Tag Historian is metadata plus time-partitioned data, not one table per tag:

- `sqlth_te`: tag metadata; resolve `tagpath` to `tagid`.
- `sqlth_scinfo`: links `sqlth_te.scid` to `drvid`.
- `sqlth_partitions`: maps time windows and driver IDs to data table names.
- `sqlt_data_*`: actual samples, partitioned by time.

Do not jump straight to a guessed `sqlt_data_*` table. First resolve the tag, then find overlapping partitions.

## Tag Path Resolution

`sqlth_te.tagpath` often omits the `[Provider]` prefix and may be lowercase. Prefer case-insensitive suffix or folder matches:

```sql
WHERE te.retired IS NULL
  AND te.tagpath ILIKE '%<area>/<line>/<machine>/<folder>/<tagname>'
```

Avoid exact matches that include provider prefixes unless verified from `sqlth_te`.

"All historized tags under a folder" means tag IDs under that path that exist in `sqlth_te` and have rows in historian data tables for the target window. A UDT instance JSON member list is not the same as historian coverage.

## Partition Selection

Build explicit epoch-millisecond windows because historian `t_stamp` uses milliseconds:

```sql
WITH ms AS (
  SELECT
    (extract(epoch FROM (now() - interval '12 hours')) * 1000)::bigint AS start_ms,
    (extract(epoch FROM now()) * 1000)::bigint AS end_ms
)
SELECT
  p.pname,
  min(p.start_time) AS start_time_ms,
  max(p.end_time) AS end_time_ms
FROM sqlth_partitions p
CROSS JOIN ms
WHERE p.drvid = 1
  AND p.blocksize = 0
  AND p.start_time < ms.end_ms
  AND p.end_time > ms.start_ms
GROUP BY p.pname
ORDER BY min(p.start_time);
```

Do not assume partitions are daily. A window can span multiple tables, and `sqlth_partitions` can return multiple rows for the same `pname`. Collapse to unique `pname` values before generating a `UNION ALL`.

Always schema-qualify data tables:

```sql
FROM public.sqlt_data_1_20260107
```

## Driver/Partition Mismatch

If a tag resolves but partition coverage is empty:

1. Resolve `tagid`, `drvid`, and `scname` from `sqlth_te` plus `sqlth_scinfo`.
2. Count partitions for that `drvid`.
3. If no partitions exist for the driver, sanity-check whether rows exist for that `tagid` in known `public.sqlt_data_1_*` tables.

The `_exempt_`/`drvid` mismatch edge case can make `drvid -> sqlth_partitions -> pname` report no coverage even when rows exist under `sqlt_data_1_*`.

## Time And Display

Use `timestamptz` for specific local windows:

```sql
timestamptz '<yyyy-mm-dd hh:mm:ss-offset>'
```

For display, convert from epoch milliseconds and make the timezone explicit:

```sql
timezone('<localTimezone>', to_timestamp(t_stamp / 1000.0)) AS ts_local
```

## Values And Quality

Ignition stores datatypes in separate columns. Include raw columns when debugging:

- `intvalue`
- `floatvalue`
- `stringvalue`
- `datevalue` when present

Numeric helper:

```sql
COALESCE(floatvalue, intvalue::double precision) AS value_num
```

`value_num` is expected to be `NULL` for string tags.

For jitter/counter analysis, show or filter quality:

```sql
(d.dataintegrity & 192) = 192 AS is_good
```

Useful jitter columns:

- `prev_value_num`
- `delta_num`
- `gap_s`
- `is_good`
- raw value columns
- `prev_ts_*` and `t_stamp_ms`

## Empty Result Debug Order

When a historian query returns no rows:

1. Confirm `sqlth_te` resolves a `tagid`.
2. Confirm `sqlth_scinfo.drvid` and overlapping `sqlth_partitions`.
3. Query the newest sample for that `tagid` from an expected partition.
4. If the tag's `drvid` has no partitions, check for driver/partition mismatch before declaring no data.

## Dynamic SQL Safety

Partition table names are identifiers, not value parameters. If code must build a historian `UNION ALL`, discover table names from `sqlth_partitions`, dedupe them, validate they match the expected `sqlt_data_*` shape, and never use a user-supplied table name directly.

## SQL Comments

Avoid block comments when writing SQL with tag paths or wildcard examples. Text like `MES/COUNTS/*` contains `/*` and can create an unterminated block comment.

Prefer:

```sql
-- Includes all tags under MES/COUNTS
-- Includes ING/prodCount
```
