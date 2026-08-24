# Historian, Alarms, And MES

Read this before querying tag history or alarm journals, or implementing historian-backed MES/OEE workflows.

## Contents

- [Tag History](#tag-history)
- [Alarms](#alarms)
- [Historian And MES Patterns](#historian-and-mes-patterns)
- [Additional Customer Runtime Rules](#additional-customer-runtime-rules)

## Tag History

`system.tag.queryTagHistory` rows are not confirmation of stored history. With an interpolated `returnSize`, the query returned a dataset with 10 rows (`t_stamp` plus the tag column) where every value cell was null, because the memory tag had no history provider. On runner `0.3.137+`, the equivalent `historyProbe` response names this as good-sample evidence. When good-quality availability matters in direct Jython, use a strict Count query and require a positive good-sample count:

```python
end = system.date.now()
start = system.date.addMinutes(end, -60)
ds = system.tag.queryTagHistory(
    paths=[tagPath],
    startDate=start,
    endDate=end,
    returnSize=1,
    aggregationMode="Count",
    returnFormat="Wide",
    includeBoundingValues=False,
    noInterpolation=True,
    ignoreBadQuality=True
)
goodStoredSamples = 0
for row in range(ds.getRowCount()):
    for col in range(1, ds.getColumnCount()):
        value = ds.getValueAt(row, col)
        try:
            if float(value) > 0:
                goodStoredSamples += float(value)
        except:
            pass
if goodStoredSamples <= 0:
    fail("No good-quality counted historian samples for %s; verify history is enabled and inspect bad-quality rows separately if needed" % tagPath)
```

Use caller-selected value queries for diagnostics only: non-null cells, `LastValue`, and displayed chart-like values can be interpolated, bounded, aggregated, or quality-filtered depending on query settings. Query tag instance paths only. A `_types_` UDT definition path returns no usable history even when the query itself succeeds.


## Alarms

Use `system.alarm.queryStatus(...)` for current alarm state only. It is not alarm history; use `system.alarm.queryJournal(...)` only when a journal/profile exists and the task requires historical transitions.

Always constrain current-alarm queries with at least one explicit filter such as `provider`, `displaypath`, or `source`, and usually a `state` list:

```python
results = system.alarm.queryStatus(
    provider=[tagProvider],
    displaypath=[displayRoot + "/*"],
    state=["ActiveUnacked", "ActiveAcked"]
)
ds = results.getDataset()
```

`AlarmQueryResult` is list-like and also provides `getDataset()`. For realtime `queryStatus` calls, the Ignition 8.1 object reference and target validation may show dataset columns `EventId`, `Source`, `DisplayPath`, `EventTime`, `State`, and `Priority`.

Use PyAlarmEvent methods/keys instead of assuming plain dictionaries:

```python
for alarm in results:
    name = alarm.getName()
    state = str(alarm.getState())
    source = str(alarm.getSource())
    display = str(alarm.getDisplayPathOrSource())
    event_id = str(alarm["EventId"])
```

Alarm status validation:

- A memory tag alarm activated and was found with `provider=[...]` plus `displaypath=["LLM Tests/.../*"]`.
- `queryStatus(..., state=["ActiveUnacked", "ActiveAcked"], priority=["High"])` returned the active event.
- Custom alarm properties such as `assetName` were available through `alarm.get("assetName")`, `alarm.contains("assetName")`, `defined=["assetName"]`, and `all_properties=[("assetName", "=", "...")]`.
- `alarm.getName()`, `getLabel()`, `getDisplayPath()`, `getSource()`, `getPriority()`, `getState()`, `getLastEventState()`, `getId()`, `isAcked()`, `isCleared()`, `isShelved()`, and `getNotes()` all returned usable values.
- After writing the source value below the setpoint, the runtime `.IsActive` tag became false, but `queryStatus` still returned one event as `Cleared, Unacknowledged`. The active-state query returned zero rows. Do not equate "one queryStatus event exists" with "alarm is active."
- `getActiveData()` returned an event-data object containing the active transition details; `getClearedData()` and `getAckData()` were `None` before those transitions existed.

For historical alarm rows, use a bounded date range and `includeData=True` when the script needs event values or associated data:

```python
end = system.date.now()
start = system.date.addHours(end, -1)
results = system.alarm.queryJournal(
    startDate=start,
    endDate=end,
    provider=[tagProvider],
    displaypath=[displayRoot + "/*"],
    includeData=True,
    includeSystem=False
)
```

`queryJournal` returns separate transition rows. In a one-alarm validation, it returned two rows with the same `EventId`: active (`EventState == 0`) and clear (`EventState == 1`). This differs from `queryStatus`, which groups current alarm state.

For `PyAlarmEvent`, simple key/string access is preferred:

```python
for event in results:
    event_value = event.get("eventValue")
    asset_name = event.get("assetName")
    state = event.get("EventState")
```

For the lower-level EventData objects returned by `getActiveData()` and `getClearedData()`, string-key `.get(...)` is not the same API:

```python
from com.inductiveautomation.ignition.common.alarming.config import CommonAlarmProperties
from com.inductiveautomation.ignition.common.alarming.evaluation import EventProperty

active_data = event.getActiveData()
event_value = active_data.get(CommonAlarmProperties.EventValue)
event_value2 = active_data.get(EventProperty.createStatic(CommonAlarmProperties.EventValue, False))
```

For unknown/custom associated data, iterate the EventData property values:

```python
active_data = event.getActiveData()
associated = {}
for property_value in active_data:
    associated[property_value.getProperty().getName()] = property_value.getValue()
```

Alarm journal data validation:

- `event.get("eventValue")` returned `15.5` for the active journal event and `0.0` for the clear event when `includeData=True`.
- `event.get("assetName")` returned the configured associated data.
- `event.getActiveData().get("eventValue")` failed with `1st arg can't be coerced to com.inductiveautomation.ignition.common.config.Property`.
- `activeData.get(CommonAlarmProperties.EventValue)`, `activeData.get(EventProperty.createStatic(CommonAlarmProperties.EventValue, False))`, and iterating property values all returned `15.5`.


## Historian And MES Patterns

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

## Additional Customer Runtime Rules

Use these detailed alarm state, alarm history, and stored-history availability rules.

- For current alarm state, use `system.alarm.queryStatus(...)` with explicit `provider`, `displaypath` or `source`, and `state` filters. It returns current combined alarm events, not alarm history; after a clear, the event can remain as `Cleared, Unacknowledged`. Use `getDataset()` or PyAlarmEvent methods/keys and verify active state separately.
- For alarm history, use `system.alarm.queryJournal(startDate=..., endDate=..., provider=[...], displaypath=[...], includeData=True, includeSystem=False)`. It depends on an alarm journal and returns separate transition rows. If a Perspective Alarm Journal Table uses `props.name`, pass that same value as `journalName`; Ignition can omit `journalName` only when exactly one alarm journal exists, and the Web Dev runner requires an explicit profile because it cannot verify that condition. For `PyAlarmEvent`, prefer `event.get("eventValue")` / `event.get("assetName")`; for `getActiveData()` / `getClearedData()` EventData, use `CommonAlarmProperties`/`EventProperty` or iterate property values, not `data.get("eventValue")`.
- `system.tag.queryTagHistory` returning rows is not proof of stored history: interpolated or bounded return modes can emit timestamp/value rows that are not stored samples in the requested window. For good-quality availability checks, use a bounded Count query such as `aggregationMode="Count"`, `returnSize=1`, `includeBoundingValues=False`, `noInterpolation=True`, and `ignoreBadQuality=True`, then require a positive count per tag. Treat false/zero as "no good samples counted," not proof that bad-quality rows are absent. Treat non-null value cells as diagnostic context, and query tag instance paths, never `_types_` UDT definition paths.
