# Jython History Diagnostics

Use this reference when `historyProbe` is too limited and the user approves a narrow Gateway-scope read-only Jython diagnostic for `system.tag.queryTagHistory`. If the diagnostic is comparing aggregate mode, `queryTagCalculations`, scan-class validation, stale data detection, or quality-filtered calculations, read `aggregate-validation-forensics.md` first so the script preserves the settings that make the result meaningful.

Official reference:

- `system.tag.queryTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-queryTagHistory

This reference targets Ignition 8.1. Confirm the Gateway version/build and use the matching official documentation version when exact parameters or defaults matter.

## Contents

- Approval Boundary
- Exact Query Pattern
- Interpreting Results

## Approval Boundary

Do not execute Gateway-scope Jython just because it is convenient. Before using `scriptEval`, a Designer script console, or a temporary project script, state that the script executes in Gateway scope, list the exact tag paths and absolute start/end timestamps, and get user approval unless the user has already explicitly accepted that diagnostic path.

Keep diagnostics read-only. Do not include:

- `system.tag.storeTagHistory`
- `system.tag.writeBlocking` or `system.tag.writeAsync`
- `system.tag.configure`, import, delete, move, or rename calls
- `system.db.runUpdateQuery`, `system.db.runPrepUpdate`, or SQL DML such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or `TRUNCATE`
- cache clearing, quarantine retry/delete/import/export, or Gateway configuration changes

## Exact Query Pattern

Use absolute start/end timestamps with timezone. Prefer fully qualified realtime paths unless the user is intentionally querying historical paths. Keep the path list narrow enough that each returned value column can be reviewed.

For raw/on-change-style evidence, start with `returnSize=-1` and `noInterpolation=True`. Change one parameter at a time when comparing rendered chart output with diagnostic rows.

```python
# Read-only queryTagHistory diagnostic. Replace all placeholder values before use.
from java.text import SimpleDateFormat
from java.util import TimeZone

tz = TimeZone.getTimeZone("America/Chicago")
fmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX")
fmt.setTimeZone(tz)

paths = [
    "[Provider]Area/Line/AnalogPV",
    "[Provider]Area/Line/RunState",
]
start_date = fmt.parse("2026-06-22T08:00:00-05:00")
end_date = fmt.parse("2026-06-22T09:00:00-05:00")

ds = system.tag.queryTagHistory(
    paths=paths,
    startDate=start_date,
    endDate=end_date,
    returnSize=-1,
    returnFormat="Wide",
    noInterpolation=True,
    includeBoundingValues=False,
    validateSCExec=True,
    ignoreBadQuality=False,
)

headers = [ds.getColumnName(i) for i in range(ds.getColumnCount())]
rows = []
stats = {}
for header in headers:
    if header != "t_stamp":
        stats[header] = {"nonNullCount": 0, "firstTimestamp": None, "lastTimestamp": None}

for row_index in range(ds.getRowCount()):
    row = {}
    timestamp = ds.getValueAt(row_index, "t_stamp")
    row["t_stamp"] = str(timestamp)
    for header in headers:
        if header == "t_stamp":
            continue
        value = ds.getValueAt(row_index, header)
        row[header] = value
        if value is not None:
            stats[header]["nonNullCount"] += 1
            if stats[header]["firstTimestamp"] is None:
                stats[header]["firstTimestamp"] = str(timestamp)
            stats[header]["lastTimestamp"] = str(timestamp)
    rows.append(row)

result = {
    "paths": paths,
    "start": "2026-06-22T08:00:00-05:00",
    "end": "2026-06-22T09:00:00-05:00",
    "timezone": "America/Chicago",
    "returnSize": -1,
    "returnFormat": "Wide",
    "noInterpolation": True,
    "includeBoundingValues": False,
    "validateSCExec": True,
    "ignoreBadQuality": False,
    "rowCount": ds.getRowCount(),
    "columns": headers,
    "stats": stats,
    "sampleRows": rows[:20],
}
result
```

## Interpreting Results

- Treat `rowCount` as structural query output. Require per-column non-null counts before claiming usable value evidence.
- In `Wide` output, map each non-`t_stamp` value column back to its requested tag or returned alias. One populated column is not evidence for another column.
- In `Tall` output, group rows by path, series, or tag identity before summarizing availability.
- Do not infer raw database storage from this script alone if the query used aggregation, interpolation, or bounding values.
- Do not infer good quality from a non-null value unless quality evidence is explicitly returned or separately checked. Use database evidence or a quality-preserving diagnostic when quality is decisive.
- Keep query settings in the final report so chart, binding, and script outputs can be compared without guessing.
- For aggregate comparisons, preserve aggregate mode, interval or `returnSize`, interpolation, bounding values, quality filtering, and scan-class validation settings. Do not present aggregate output as raw/on-change storage evidence unless the diagnostic actually used raw/on-change settings and returned per-tag value evidence.
