# Historian And MES Patterns

## Historian SQL Shape

Ignition Tag Historian in PostgreSQL is not one table per tag. Resolve tag identity and partition coverage before querying data.

Reliable order:

1. Build a time window in epoch milliseconds.
2. Resolve tag IDs through `sqlth_te`.
3. Join `sqlth_scinfo` for `drvid`.
4. Use `sqlth_partitions` to find overlapping `sqlt_data_*` tables.
5. Dedupe partition table names by `pname`.
6. Query `public.sqlt_data_*` tables.
7. Include raw columns when datatype is uncertain: `intvalue`, `floatvalue`, `stringvalue`.
8. Include `dataintegrity` or `is_good` when analyzing jitter.

Tag paths in `sqlth_te` may omit the provider and may be lowercase. Use suffix or case-insensitive matching before assuming an exact Designer path.

## Partition Edge Cases

Do not assume partitions are daily. A time window can span multiple partitions, and `sqlth_partitions` may return multiple rows for the same `pname`. Collapse to unique table names before building `UNION ALL`.

If a tag resolves to a `drvid` with no partitions, check for the driver/partition mismatch edge case before declaring no data.

## Count Signal Guidance

Do not rely on boolean pulse counts unless the poll rate can reliably catch both the on and off duration. Prefer non-resetting odometer-style PLC counters.

For MES count history:

- Store deltas, not absolute counter values.
- Treat reset-to-zero and rollover explicitly.
- Do not update the "last count" baseline until the database insert succeeds.
- Use synchronous database writes for count deltas unless the project has a verified store-and-forward/retry design.
- Fail loudly and preserve baseline on insert failure so the next change can retry.

## OEE And MES Concepts

OEE is availability x quality x performance. Use it to expose where the constraint is rather than guessing. Be careful defining line-level downtime when a line is an abstraction over many cells with buffers, surge protection, starved/blocked states, and changeover states.

Useful model concepts from the IIOT University notes:

- Work orders belong to runs; one work order can have multiple runs.
- Schedule can exist before a run starts; run IDs may not exist at schedule time.
- Actual start may include changeover; run start may begin after changeover when production is actually running.
- Counts should be whole-number deltas where possible.
- Reason codes should be ordered by operator usage after live data confirms the frequent reasons.
- Use explicit "No Active Run" placeholder records instead of nullable foreign keys in hot transaction tables when the design can support it.

## State History

For machine state history:

- Close the previous open state row before inserting the new state row.
- Keep event timestamps and edited/corrected timestamps conceptually separate.
- Capture state reason ID, reason name/code, line ID, start time, and end time.
- Machine builders should expose a stable status register when possible, with clear ranges for stopped/running/e-stop/blocked/starved/changeover/planned/unplanned/user-defined states.

## UNS And Dashboard Namespace

Do not force every Perspective dashboard to recompute expensive logic locally. When calculations are reused by multiple apps, publish processed dashboard/OEE values back into a namespace so they can be consumed and historized consistently.

The UNS discipline from the notes:

- Agree on one authoritative publisher.
- Use a common payload schema; Sparkplug B helps with this.
- Version or extend topics deliberately so future consumers do not break.
- Do not make assumptions about how data will be consumed later.
