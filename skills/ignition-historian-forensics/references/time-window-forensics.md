# Time Window Forensics

Use this reference when a historian incident depends on "last hour", "yesterday", shift windows, daylight-saving transitions, adjoining query windows, chart/script/SQL comparisons, or disagreement between timestamps from tags, logs, databases, store-and-forward evidence, and UI exports. If delayed delivery, queue recovery, quarantine, dropped records, or late-arriving rows are central to the incident, also read `store-forward-quarantine-forensics.md`.

Official references:

- `system.tag.queryTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-queryTagHistory
- Ignition Database Table Reference: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/ignition-database-table-reference

This reference targets Ignition 8.1. Confirm the target Gateway version/build and use the matching official documentation version when exact endpoint behavior matters.

## Normalize The Window First

Before deciding that history is missing, turn the requested window into explicit boundaries:

- Original user phrase, such as "last hour", "night shift", or "10 to 11".
- Absolute start and end timestamps.
- Timezone name and UTC offset for each boundary.
- Whether the end timestamp is intended to be included or excluded.
- The clock used to resolve relative terms: Gateway, client/session/browser, report server, database server, PLC/device, or analyst workstation.
- The time the query was executed when a dynamic range such as `rangeMinutes` or `now()` was used.

For audit or compliance statements, prefer a frozen interval such as `2026-06-22T08:00:00-05:00` to `2026-06-22T09:00:00-05:00`, not "the last hour".

## Endpoint Semantics

`system.tag.queryTagHistory` can create an interval at the requested `endDate`. The official 8.1 documentation warns that historical query intervals are inclusive of `endDate`, which can produce one extra interval and duplicate boundary data when adjoining windows are stitched together.

When comparing query surfaces:

- Record whether the evidence came from `queryTagHistory`, Perspective/Vision charting, a report query, `historyProbe`, or direct SQL.
- For fixed buckets, check whether the final bucket is a real value, an interpolated/fill value, an all-null bucket, or a duplicate boundary bucket.
- For adjacent script/chart windows, avoid double-counting the shared boundary.
- For SQL evidence, use half-open windows (`>= start_ms` and `< end_ms`) unless intentionally reproducing an inclusive historian query boundary.
- Do not compare a fixed-bucket chart directly to raw SQL rows without noting the endpoint and aggregation differences.

## Daylight-Saving And Ambiguous Local Time

Local wall-clock times can be ambiguous or nonexistent around daylight-saving transitions. A label such as `01:30` may refer to different instants during a fall-back hour, and a spring-forward hour may skip local labels.

When DST could matter:

- Require timezone name plus UTC offset, or epoch milliseconds.
- Preserve the original local timestamp and the normalized instant.
- Avoid using a naive local timestamp as proof that a row is missing.
- State whether the query engine, database conversion, chart display, and report output used the same timezone.
- Prefer epoch milliseconds or ISO-8601 timestamps with offset when handing evidence to SQL or scripts.

## Separate Timebases

Do not collapse these into one timestamp:

- Event/sample timestamp: when the tag value is considered to have occurred.
- Current read timestamp: when the current tag value was last updated.
- Query execution time: when a relative query was run.
- Database row timestamp: the historian `t_stamp` value, usually Unix epoch milliseconds in external historian data tables.
- Store-and-forward arrival or recovery time: when delayed data reached the database.
- Gateway log time: when a message was logged.
- UI display time: the timezone/format used by a chart, report, browser, or export.

If data appears delayed or missing, compare sample time to arrival/log time before concluding storage failed. If a UI shows a different hour than SQL, check display timezone and conversion before claiming the historian shifted the data.

## Report Wording

In the final forensic report, include:

- The normalized start and end instants with timezone and offset.
- Any inclusive-end, half-open SQL, or fixed-bucket behavior that affects counts.
- Whether the window crosses a DST transition or uses an ambiguous local time.
- The timebase for each evidence source.
- Any remaining uncertainty caused by missing timezone, offset, query-execution time, or clock-skew evidence.
