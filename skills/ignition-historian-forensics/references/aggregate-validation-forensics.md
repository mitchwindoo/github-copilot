# Aggregate And Scan-Class Validation Forensics

Use this reference when historian evidence depends on aggregate mode, aggregate calculations, report calculations, Perspective Tag History binding calculations, Power Chart or Easy Chart aggregate settings, scan-class validation, stale data detection, bad-quality filtering, or whether an aggregate result is strong enough for compliance evidence.

Official references:

- `system.tag.queryTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-queryTagHistory
- `system.tag.queryTagCalculations`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-queryTagCalculations
- Perspective Tag History Bindings: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/tag-history-bindings-in-perspective
- Custom Tag History Aggregates: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/custom-tag-history-aggregates
- Ignition Database Table Reference: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/ignition-database-table-reference
- Vision Easy Chart: https://www.docs.inductiveautomation.com/docs/8.1/appendix/components/vision-components/charts/easy-chart

This reference targets Ignition 8.1. Confirm the target Gateway version/build and use matching official documentation before final claims about exact parameter names, defaults, chart properties, or aggregate behavior.

## Contents

- Core Rule
- Capture These Settings
- Aggregate Modes
- Raw, Natural, Fixed, And Calculation Queries
- Bad Quality And Interpolation
- Scan-Class Validation And Stale Data Detection
- Boolean Event Aggregates
- Compliance And Report Output

## Core Rule

An aggregate result is calculated query evidence. It can be correct and useful without proving that each underlying raw event was stored. When the question is compliance, event reconstruction, or why a value is missing, preserve the query settings and compare aggregate output with raw/on-change rows or read-only database evidence before making a storage conclusion.

Use these labels:

- "Observed aggregate output" for Average, MinMax, LastValue, CountOn, DurationOn, PctGood, PctBad, report calculations, or chart summaries returned with known settings.
- "Observed raw/on-change rows" only when the query mode or SQL evidence supports the claim.
- "Observed scan-class validation gap" when validation produced bad-quality downtime evidence.
- "Inferred aggregate mismatch" when the output differs from expectations but raw rows, quality, time bounds, or tag identity are incomplete.
- "Unverified compliance proof" when aggregate output has not been tied back to raw/on-change storage, quality, and exact time boundaries.

## Capture These Settings

Record the query surface and every setting that can change the result:

- Surface: `system.tag.queryTagHistory`, `system.tag.queryTagCalculations`, Perspective Tag History binding, Power Chart, Easy Chart, report query, export, or direct SQL.
- Exact start/end timestamps and timezone.
- Tag path or historical path, return format, aliases, and per-tag aggregate overrides.
- `returnSize=-1` for on-change style evidence; `returnSize=0` for natural rows; fixed positive `returnSize` or interval settings for aggregate windows.
- `aggregationMode` or per-tag `aggregationModes`.
- `includeBoundingValues`, `noInterpolation`, `ignoreBadQuality`, and scan-class validation.
- `validateSCExec` for `queryTagHistory`; `validatesSCExec` for `queryTagCalculations`.
- Component settings such as Perspective Prevent Interpolation, Easy Chart interpolation, bad-quality filtering, and Validate Scan Class Executions.
- SQL identity fields and `sqlth_sce` evidence when downtime or stale data detection is part of the question.

## Aggregate Modes

Interpret aggregate modes as different evidence types:

- Average: time-weighted average. It can differ from the arithmetic average when values last for different durations.
- SimpleAverage: arithmetic mean of values in the window.
- MinMax: returns the minimum and maximum for a time slice; when min and max differ, this can produce two rows or points for one slice.
- LastValue: the value closest to the end of the time slice; with interpolation, it can hide whether a new raw row existed inside the slice.
- Sum, Minimum, Maximum, Range, Variance, and StdDev: window calculations, not raw-event proof by themselves.
- DurationOn and DurationOff: total seconds spent non-zero or zero in the window.
- CountOn and CountOff: transition counts. They summarize transitions but do not show exact edge timestamps unless raw/on-change rows are also reviewed.
- Count: count of qualifying values in the window.
- PctGood and PctBad: percentage-of-time quality summaries. They are quality evidence, not missing-row proof.

For Average versus SimpleAverage disputes, test whether long-held values are weighting the result. Do not call either answer wrong until the aggregate mode and raw samples are known.

## Raw, Natural, Fixed, And Calculation Queries

`returnSize=-1` is the first scripting route for raw/on-change-style evidence, especially with `noInterpolation=True` and `includeBoundingValues=False`. It still proves returned query evidence, not necessarily all database storage, and should be paired with quality and identity evidence when those are decisive.

`returnSize=0` follows natural row behavior based on logging rates. A natural result is not the same as as-stored raw rows.

Fixed positive `returnSize` and interval queries divide the range into windows. Aggregates then collapse multiple stored or interpolated values into each window. A row per window can be a generated calculation bucket, not a stored row.

For custom aggregate functions, `returnSize greater than 0` is required for the custom aggregate to apply. Custom aggregates receive raw and interpolated values inside each window according to query settings, then return calculated output. Treat custom aggregate output as calculated evidence unless the function and returned input evidence are reviewed.

Use `queryTagCalculations` when the goal is a single calculation per tag over a range. Use `queryTagHistory` when the goal is time-sliced or row-by-row history. Neither replaces raw/on-change evidence when the question is whether a specific pulse, sample, or quality transition was stored.

## Bad Quality And Interpolation

Bad-quality rows, absent rows, null cells, and filtered rows are different states.

- If `ignoreBadQuality=True`, bad-quality values may be excluded from the calculation. Empty or reduced output may mean quality filtering, not missing storage.
- If `noInterpolation=False`, returned values may include interpolated values. Interpolated values can be useful for charts but weaker for raw-event proof.
- If `includeBoundingValues=True`, values just outside the requested window may influence interpolation or aggregate output.
- PctGood and PctBad can show whether quality, not storage, is the stronger explanation.

When compliance is involved, report whether bad-quality data was included, excluded, or only summarized. Do not hide quality loss behind a clean aggregate.

## Scan-Class Validation And Stale Data Detection

Scan-class execution validation compares the query against tag group execution records. In the external historian schema, `sqlth_sce` tracks scan-class execution periods for tag groups. Use it to separate "the tag group was not executing" from "no value changed" when SQL evidence is available and appropriate.

When validation is enabled, downtime can appear as bad-quality data for periods where the scan class did not execute. This is not the same as never-stored evidence.

When validation is disabled or stale data detection is turned off, a value can appear flat or good-looking through a period that may not have fresh execution evidence. Treat that as an unvalidated downtime risk until logs, `sqlth_sce`, component settings, or script settings clarify it.

For Easy Chart, record the Validate Scan Class Executions setting before comparing chart output to a direct query. For scripting, record whether `validateSCExec` or `validatesSCExec` was used.

## Boolean Event Aggregates

For boolean and discrete evidence:

1. Use CountOn, CountOff, DurationOn, and DurationOff to summarize activity over a window.
2. Use raw/on-change rows when the question is whether both edges were stored or exactly when a pulse occurred.
3. Compare pulse duration with tag group execution and historian sample timing.
4. Keep aggregate count, duration, raw edge rows, and quality evidence separate in the report.

If a report says CountOn is one and DurationOn is two seconds, that is useful summary evidence. It does not by itself show both stored edge timestamps or prove the chart exported all raw event rows.

## Compliance And Report Output

For compliance, audit, or regulatory questions:

- Convert relative ranges to absolute timestamps with timezone.
- Preserve the exact aggregate mode and all query settings.
- State whether the result is raw/on-change, natural, fixed-window aggregate, report calculation, custom aggregate, or rendered chart output.
- Verify tag identity and history provider identity if a rename, move, historical path, virtual path, or SQL candidate ambiguity exists.
- Verify quality handling, scan-class validation, and interpolation settings.
- Use read-only SQL or an approved Jython diagnostic when raw storage, exact edge timing, or downtime quality evidence is decisive.

Report aggregate output as a summary unless raw/on-change rows and quality evidence support the stronger conclusion.
