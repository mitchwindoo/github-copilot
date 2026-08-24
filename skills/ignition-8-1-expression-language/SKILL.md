---
name: ignition-8-1-expression-language
description: Write, review, debug, and test Ignition 8.1 expressions for tags, Perspective, Vision, UDTs, dynamic paths, quality, dates, strings, datasets, alarms, and runScript; validate with the Gateway API.
---

# Ignition 8.1 Expression Language

Skill version: `1.0.39`
Stack version: `starter-2026.07.06.04`
Primary target: Ignition `8.1.53`. Always confirm the actual Gateway version and build before making version-specific claims.

## Scope

Use this skill for Ignition expression-language work in Expression Tags, Perspective expression bindings, Perspective expression transforms, Vision expression bindings, UDT expression members, dynamic tag-path recipes, type conversion, quality checks, string/date/math logic, and small expression-to-script boundary decisions.

Do not treat expressions as Jython scripts or SQL. Expressions return a value. They do not contain imports, assignments, loops, multi-line statements, transactions, SQL clauses, or arbitrary side effects. If the user needs event scripts, project library code, database work, or Perspective package/page generation, route to the matching Ignition skill and keep this skill focused on the expression pieces.

## Reference Loading

- Read `references/expression-test-matrix.md` when building reusable fixtures, testing edge cases or cross-surface behavior, or using the bounded request templates.
- Read `references/expression-api-validation.md` before live Gateway/API validation or mutation. It defines transport, authentication, capability discovery, version gates, dry-run/apply/readback/cleanup rules, and the no-API fallback.

## First Checks

- Identify the exact expression surface: Expression Tag, Perspective expression binding, Perspective expression transform, Perspective tag binding Expression mode, Vision expression binding, UDT expression tag/member, or Tag property expression.
- Confirm target context from the Gateway when API access exists: start with `health`, `gatewayInfo`, and provider discovery. Record the actual Ignition version/build, timezone, runner version, and tag provider in validation notes outside `SKILL.md`.
- Discover or request the concrete provider, tag path, property path, UDT parameter names, tag data type, and expected output type. Do not invent target paths, provider names, database connections, project names, or component paths.
- Keep reusable examples generic. Use placeholders such as `[<provider>]Area/Device/Tag`, `{[.]PV}`, `{view.params.asset}`, and `<projectScript.function>`.
- If the actual Gateway is not Ignition 8.1.53, label any live result with the actual version. Do not silently present it as 8.1.53 behavior.

## Core Syntax

- Expressions normally return exactly one value.
- Equality is `=`, not `==`.
- Common boolean operators are `&&`, `||`, and `!`.
- Arithmetic includes `+`, `-`, `*`, `/`, `%`, and `^` for exponentiation. Parenthesize negative or chained exponent expressions when precedence matters.
- Bitwise integer operations include `&`, `|`, `xor`, `<<`, and `>>`.
- String literals can use double quotes or single quotes.
- Use `null` for null values.
- Numeric literals can use decimal, hexadecimal integer, or scientific notation forms such as `12`, `0xFF`, and `1.3e5`.
- The `like` operator can match wildcard patterns such as `"Pump 101" like "Pump*"`. Validate case behavior on the target before relying on case-sensitive or case-insensitive matching.
- Tag and property references use brace syntax when the surface supports bound values, such as `{[.]Speed}` or `{view.params.asset}`.
- Function calls use expression functions such as `if(...)`, `case(...)`, `switch(...)`, `coalesce(...)`, `try(...)`, `toInt(...)`, `dateFormat(...)`, `split(...)`, and `tag(...)`.
- In Ignition 8.1.53 Expression Tags, boolean `&&` and `||` short-circuit the unneeded side for returned-value evaluation. For example, `false && (1/0 > 0)` returns false Good, and `true || (1/0 > 0)` returns true Good. The same Expression Tag surface kept `false && {[.]Missing}` and `true || {[.]Missing}` Good after the unneeded source tag was deleted. Still use explicit `if()`/`case()` guards for value safety and verify other surfaces before making subscription or performance claims.

Useful baseline examples:

```text
5 + 3 * 2
(5 + 3) * 2
0xFF
1.3e5
5 = 5 && 2 != 3
!(1 = 2)
5 | 3
1 << 4
"Pump 101" like "Pump*"
if({[.]Running}, "Running", "Stopped")
case({[.]State}, 0, "Off", 1, "Running", 2, "Fault", "Unknown")
switch({[.]State}, 0, 1, 2, "Off", "Running", "Fault", "Unknown")
coalesce({[.]OperatorName}, "N/A")
```

## Expression Tags

- Use relative sibling tag references such as `{[.]A}` inside tags in the same folder.
- Use absolute paths such as `{[default]Folder/Tag}` only when the provider/path is known for the target.
- `[~]` means the current provider root in tag paths. It is useful when a reusable expression should stay within the current provider.
- The Expression Tag data type matters. Ignition coerces the expression result into the tag's configured data type. Use `Float8` for fractional numeric calculations, `String` for formatted text, `Boolean` for booleans, and an integer type only when rounding/truncation behavior is intentional and verified.
- Read value and quality together. A tag can have a null value with an Error quality when the expression itself or the tag's result coercion fails.
- Prefer guarded expressions that produce a normal value over expressions that rely on a later coercion failure.

Guard divide-by-zero before the division:

```text
if({[.]Denominator} = 0, -1.0, {[.]Numerator} / {[.]Denominator})
```

Do not rely on `try()` to catch divide-by-zero in Expression Tags:

```text
try({[.]Numerator} / {[.]Denominator}, -1.0)
```

Division by zero can produce Infinity or NaN, then fail when the Expression Tag coerces that value into its configured data type. In that case `try()` may not return the failover value. Use `if(den = 0, fallback, numerator / den)` for divide guards.

## Expression Tag Execution Timing

Expression Tag execution settings affect when the tag reevaluates; they do not change the expression syntax.

- In Ignition 8.1.53 Expression Tags, `executionMode: "EventDriven"`, `executionMode: "FixedRate"` with `executionRate: 1000`, and `executionMode: "TagGroupRate"` with either the default tag group or explicit `tagGroup: "Default"` configured successfully and returned Good values for `if({[.]SelectA}, {[.]A}, {[.]B})`.
- In the same surface, `if(...)` and `case(...)` returned the selected branch with Good quality as selected source values and selector tags changed.
- Changing an unselected branch source while the selector chose the other branch did not change the returned value or quality. On Event Driven Expression Tags, the expression tag timestamp still moved after the unselected source write, so do not describe this as proof that Ignition skipped reevaluation or subscription work.
- Deleting an unselected branch source while the selector chose the other branch kept the selected branch value Good. Recreate and re-read deleted sources before treating the dependency graph as healthy again.
- For `coalesce({[.]A}, {[.]B})`, a non-null first argument stayed selected after the fallback source was deleted. When the first argument became null while the fallback source was missing, the expression returned null Good; after the fallback source was recreated, it returned the fallback value Good.
- `runScript("system.date.now().getTime()", 250)` and `now(250)` in Event Driven Expression Tags changed between repeated reads. A Fixed Rate Expression Tag using `now()` with `executionRate: 1000` changed on a later fixed evaluation. Validate timing on the target tag group or binding surface when refresh cadence matters.
- A pass-through Expression Tag reading a memory source with `deadbandMode: "Off"` updated on both a small and large source write. A pass-through Expression Tag reading a memory source with `deadbandMode: "Absolute"` and `deadband: 5.0` ignored a 0.5 write and updated on a 10.0 write. Validate deadband behavior on the real source type before relying on small-change suppression.

## Performance And Complexity Boundaries

Expression performance is target-specific. Do not turn one Gateway benchmark into a universal maximum for tag fan-in, dynamic `tag()` calls, DataSet or JSON size, nested condition depth, `runScript()` duration, or UDT instance count.

In Ignition 8.1.53 Expression Tags, these complexity shapes returned Good values: 10, 100, and 1,000 static sibling references; 10, 100, and 1,000 dynamic `tag()` calls; DataSet `sum(...)` and `sortDataset(...)` rows up to 10,000; `jsonGet(...)` against JSON strings up to 5,000 items; nested `if(...)` depth up to 100; `runScript()` calls with 0, 25, and 100 ms sleeps; and UDT expression members across 10 and 100 identical instances. Treat those sizes only as target-local validity evidence, not throughput guarantees or design limits.

When an expression may become large or high-frequency:

- Benchmark on the target Gateway and surface with the real tag group or binding refresh rate.
- Include update-path writes and value/quality reads, not only initial configuration.
- Separate static references, dynamic `tag()` calls, DataSet aggregates/sorts, JSON parsing, nested conditionals, and `runScript()` calls because they stress different parts of the expression path.
- Move logic to a project-library script, Gateway event, precomputed tag, Named Query, or upstream model when the expression becomes hard to inspect, needs loops/state/side effects, blocks on I/O or sleeps, or cannot meet the target update budget.
- Record target version, surface, provider/path, refresh rate, sizes, value/quality results, timing method, and cleanup notes outside `SKILL.md`.

## Derived Tags

Use Derived Tags when a tag should read from one source value through a read expression and write back through a separate write expression.

- Configure the tag with `valueSource: "derived"`, a `sourceTagPath`, a read expression, and a write expression.
- In the read expression, `{source}` is the current source value.
- In the write expression, `{value}` is the value being written to the Derived Tag.
- For a Fahrenheit source and Celsius Derived Tag, the read expression can be `({source} - 32) * (5.0 / 9.0)` and the write expression can be `{value} * (9.0 / 5.0) + 32`.
- A source tag change can update the Derived Tag value.
- Writing to the Derived Tag can write the transformed value back to the source when the source supports writes.
- If the source is read-only, such as an Expression Tag, a Derived Tag write can fail with `Bad_ReadOnly` and leave the source and Derived Tag values unchanged.
- The `SourceTagPath` property can be changed to retarget a Derived Tag. After retargeting, reads and writes use the new source path.
- Derived Tags can read from and write back to JSON string sources with `jsonGet()` and `jsonSet()`. For example, read `toFloat(jsonGet({source}, "settings.setpoint"), -999.0)` and write `jsonSet({source}, "settings.setpoint", {value})`.
- If the source is missing, null, or the wrong type for the read expression, read the Derived Tag value and quality together; a null value with an expression or conversion error quality is possible. Recreating a missing source can restore a Good value.
- Do not assume a UDT parameter substituted into a Derived Tag `sourceTagPath` will resolve on every target. Use direct source paths or validate each UDT instance's Derived Tag value and quality before relying on parameterized Derived Tag source paths.

## Tag-Side Surface Differences

In Ignition 8.1.53 tag-side surfaces, Expression Tags, UDT expression members, and Derived Tag read expressions returned the same Good float values for a simple `source + 7` calculation and for `jsonGet(...)` against a JSON string source. The same three surfaces also propagated Bad quality when a Bad-quality numeric source was used in `source + 1`; the numeric value was visible, but the quality remained Bad.

Source changes refreshed the checked outputs on all three tag-side surfaces. In the tested shape, changing the numeric source from `5.0` to `8.5` changed the calculated outputs from `12.0` to `15.5`, and changing a JSON string setpoint from `42.5` to `77.25` changed all three JSON-read outputs to `77.25`.

Writeback is surface-specific. A Derived Tag with a write expression accepted writes and updated its writable source; direct writes to the matching Expression Tag and UDT expression member returned `Bad_ReadOnly("Tag value source does not support writing.")`. For this shape, writing `20.0` to the Derived Tag updated the source so the Expression Tag and Derived Tag both read `20.0`, while the UDT expression member stayed at its source-driven value after its direct write was rejected.

Do not apply these tag-side results to Perspective expression bindings, Perspective expression transforms, Perspective Tag Binding Expression mode, or Vision expression bindings without testing those surfaces separately.

## `try()` And Conditional Guards

Use `try()` for actual evaluation exceptions, especially bad conversions or invalid indexing:

```text
try(toInt("boom"), -1)
try(substring("abc", 9), "N/A")
```

Use `if()` or `case()` when a bad expression is avoidable by selecting a branch:

```text
if({[.]Enabled}, {[.]PV}, 0)
if({[.]Denominator} = 0, "No rate", numberFormat({[.]Flow} / {[.]Denominator}, "#,##0.00"))
case({[.]Mode}, 1, "Auto", 2, "Manual", "Unknown")
```

Selected output from `if()` and `case()` can protect the returned value from an unselected bad arithmetic branch, but do not turn that into a performance or subscription claim unless the target surface has been separately verified.

No single fallback mechanism covers every failure class:

- `try()` can return a Good fallback for bad conversions such as `toInt("boom")`, invalid DataSet row/column access, missing `runScript()` project-library functions, and an Error-quality value from `qualifiedValue(...)`.
- `try()` does not mask parse/configuration errors, missing static or dynamic tag references that read as `Bad_NotFound`, Infinity/NaN final tag coercion, Good null values, Bad/Uncertain quality alone, or a String result being coerced into a Boolean tag.
- `coalesce()` handles null-like values, including a Good null memory tag and simple missing static/dynamic tag reads that resolve to a null value. It does not handle invalid DataSet indexing, missing project-library functions, Infinity/NaN coercion, output-type coercion, or non-null values with Bad/Uncertain/Error quality.
- Conversion fallbacks such as `toFloat(value, fallback)` can return a Good fallback for null values, missing tag reads, and conversion failures such as `"not-boolean"`, but they do not handle every expression error or final Infinity/NaN coercion.
- `if(isGood(value), value, fallback)` is useful for non-Good quality values and simple missing tag reads, but it can still fail if the expression inside the guard throws before it can produce a quality.
- `isNull(...)` and `qualityOf(...)` are diagnostics, not complete error guards. They can return their own Good result even when the final Expression Tag value later fails data-type coercion.
- A malformed expression reads as `Error_Configuration`; fix the expression instead of wrapping it.

## Type Conversion

- In Ignition 8.1.53 Expression Tags, `toInt()` and `toLong()` rounded the checked positive half values up and the checked negative half values toward zero: `toInt(2.49)` returned `2`, `toInt(2.5)` returned `3`, `toInt(-2.5)` returned `-2`, `toInt(-2.51)` returned `-3`, `toLong(2.5)` returned `3`, and `toLong(-2.5)` returned `-2`.
- Fractional Expression Tag result coercion depends on the configured integer width. `Int1` and `Int2` coerced `2.49`, `2.5`, and `2.51` to `2`, and `-2.49`, `-2.5`, and `-2.51` to `-2`. `Int4` and `Int8` matched the checked `toInt()`/`toLong()` results for those values. Choose a floating data type when fractional precision matters.
- `Int1`, `Int2`, and `Int4` overflow or underflow beyond their checked min/max values returned `Error_TypeConversion(...)`. `Int8` values produced by `toLong()` clamped out-of-range string input to `-9223372036854775808` or `9223372036854775807` instead of returning the supplied fallback.
- Conversion functions did not trim whitespace in the checked numeric strings: `toInt(" 33 ", -1)`, `toFloat(" 12.5 ", -1.0)`, and `toLong(" 9223372036854775807 ", -1)` returned the fallback. Without whitespace, `toInt("33.5", -1)` returned `34` and `toFloat("12.5", -1.0)` returned `12.5`.
- Hex and scientific numeric literals worked in Expression Tags. `0xFF` read as `255` for `Int2`, `Int4`, and `Int8`, but overflowed `Int1`; `1.3e5` coerced to `130000` as `Int4`.
- `Float4` and `Float8` differ in precision and range. `1.234567890123` read with less precision as `Float4` than as `Float8`; `3.5e38` as `Float4` and `1.0e309` as `Float8` returned `Error_TypeConversion("Invalid value: Tag value is Infinity or NaN.")`.
- Floating `-0.0` retained negative-zero text in checked `Float4` and `Float8` reads. Around `2^53`, `9007199254740993` read back as `9007199254740992.0` in a `Float8` tag, while `toLong("9007199254740993", -1)` preserved the integer in an `Int8` tag.
- `+` with any string operand concatenated before final tag coercion. `"2" + 3` read as `"23"` in a `String` tag and `23.0` in a `Float8` tag; `3 + "2"` read as `"32"` in a `String` tag and `32.0` in a `Float8` tag.
- `toBoolean("yes", false)` returns `true`.
- `isNull(null)` is true; `isNull("")` is false.
- Empty strings are not null. `coalesce("", "fallback")` and `coalesce(null, "", "fallback")` return the empty string, not the fallback.
- A tag can hold a Good null value. `isNull({[.]MaybeNull})` and `{[.]MaybeNull} = null` can be true, but arithmetic such as `{[.]MaybeNull} + 5` can fail with an expression error. Use `coalesce({[.]MaybeNull}, 0)` before arithmetic when null should mean a default number.
- `typeOf({[.]A})` is useful when diagnosing what type Ignition sees after tag/property resolution.

## Dates And Times

Use Java date/time pattern case carefully:

```text
dateFormat(toDate("2020-12-31 12:00:00"), "yyyy-MM-dd")
dateFormat(toDate("2020-02-01 12:00:00"), "dd")
```

- Lowercase `yyyy` is calendar year.
- Uppercase `YYYY` is week-year and can format late-December dates as the next year.
- Lowercase `dd` is day of month.
- Uppercase `DD` is day of year.
- `dateExtract(<date>, "month")` returns a zero-indexed month. Add 1 when the output needs a human month number.
- `dateDiff(start, end, "minute")` can return fractional values such as `15.5`.
- `dateDiff(toDate("2020-01-01 00:00:00"), toDate("2020-01-02 12:00:00"), "hour")` returns `36.0`.
- `dateArithmetic(toDate("2020-01-31 00:00:00"), 1, "month")` lands on `2020-02-29` when formatted as `yyyy-MM-dd`.
- In Ignition 8.1.53 Expression Tags on a Gateway whose default timezone is `America/Chicago`, `dateFormat(..., "yyyy-MM-dd HH:mm:ss.SSS Z z")` formatted January dates as `-0600 CST` and July dates as `-0500 CDT`. Label date recipes with the Gateway or session timezone used to validate them.
- In that Gateway-scope surface, `toDate("2024-03-10 02:30:00")` normalized the spring-forward gap to `2024-03-10 03:30:00.000 -0500 CDT`; `dateArithmetic(toDate("2024-03-10 01:30:00"), 1, "hour")` landed on the same `03:30` CDT value.
- Across the same spring-forward boundary, `dateDiff(toDate("2024-03-10 01:30:00"), toDate("2024-03-10 03:30:00"), "hour")` returned `1.0`, and midnight-to-midnight on `2024-03-10` returned `23.0` hours.
- Across the fall-back boundary, `toDate("2024-11-03 01:30:00")` formatted as `2024-11-03 01:30:00.000 -0600 CST`. Adding one hour to `2024-11-03 00:30:00` produced `01:30` CDT; adding two hours produced `01:30` CST.
- In that fall-back test, `dateDiff(toDate("2024-11-03 00:30:00"), toDate("2024-11-03 02:30:00"), "hour")` returned `3.0`, and midnight-to-midnight on `2024-11-03` returned `25.0` hours.
- Around DST changes, `dateArithmetic(..., 24, "hour")` and `dateArithmetic(..., 1, "day")` can land on different clock times. From `2024-03-09 12:00:00`, `24` hours landed at `2024-03-10 13:00:00.000 -0500 CDT` while `1` day landed at `2024-03-10 12:00:00.000 -0500 CDT`; from `2024-11-02 12:00:00`, `24` hours landed at `2024-11-03 11:00:00.000 -0600 CST` while `1` day landed at `2024-11-03 12:00:00.000 -0600 CST`.
- Leap-day and end-of-period behavior is calendar-aware in the tested surface: `2024-02-28 + 1 day` formatted as `2024-02-29`, `2024-02-29 + 1 year` formatted as `2025-02-28`, `2021-01-31 + 1 month` formatted as `2021-02-28`, `2024-01-31 + 1 month` formatted as `2024-02-29`, and `2024-12-31 + 1 day` formatted as `2025-01-01`.
- `toDate()` preserved `.SSS` milliseconds in the tested rows, and `toMillis(toDate(...))` plus `fromMillis(...)` round-tripped `2024-03-10 01:59:59.123` exactly when formatted back to `yyyy-MM-dd HH:mm:ss.SSS Z z`.
- In the same surface, `dateDiff(..., "millisecond")` and `dateArithmetic(..., 1, "millisecond")` did not return Good values. Use `toMillis()`/`fromMillis()` when exact millisecond deltas or round trips matter.
- `now()` and `now(<millis>)` can refresh Expression Tag values over time. Validate the exact refresh timing for the target tag group or binding surface when timing matters.
- These DST and timezone rows were Gateway-scope Expression Tags. Validate Perspective session timezone behavior separately before applying them to session-local display or browser workflows.
- For stale-data checks in Expression Tags, use `timestampOf(...)` with a refresh source such as `now(1000)`, and check quality separately:

```text
if(isGood({[.]PV}), dateDiff(timestampOf({[.]PV}), now(1000), "second") > 10, true)
```

- In Ignition 8.1.53 Expression Tags, `timestampOf({[.]PV})`, `timestampOf(tag({[.]PVPath}))`, and `{[.]PV.timestamp}` matched the source tag timestamp while the referenced source existed and read Good.
- In Ignition 8.1.53 Expression Tags, a different-value write to a memory source updated its timestamp; a same-value write to that memory source did not move the timestamp.
- A dynamic `tag({[.]PVPath})` timestamp retargeted to the newly selected source path and updated when that selected source value changed.
- Do not use `dateDiff(timestampOf(...), now(...), ...)` as the only missing-source detector. When a static or dynamic source was deleted in Ignition 8.1.53 Expression Tags, `timestampOf({[.]PV})` and `timestampOf(tag({[.]PVPath}))` returned a fresh Good timestamp for the failed/missing evaluation, while the source itself read `Bad_NotFound`. Pair age checks with `isGood(...)`, a resolved-path echo, or a separate read/existence check when missing paths matter.
- Direct `.timestamp` access such as `{[.]PV.timestamp}` can expose missing static paths differently: in the same missing-source test it read null with `Bad_NotFound` instead of returning a Good timestamp. Validate this form on the exact surface before using it as a fault indicator.
- Timestamp behavior can change on quality-only transitions. In Ignition 8.1.53 Expression Tags, a qualified-value Expression Tag changed timestamp when its quality changed between Good and Bad while the numeric value stayed the same.

Examples:

```text
dateFormat(toDate("2003-9-14 8:00:00"), "yyyy-MM-dd HH:mm:ss")
dateFormat(dateArithmetic(toDate("2010-01-04 8:00:00"), 5, "hour"), "yyyy-MM-dd HH:mm:ss")
dateExtract(toDate("2009-1-15 8:00:00"), "month") + 1
dateFormat(toDate("2024-03-10 02:30:00"), "yyyy-MM-dd HH:mm:ss.SSS Z z")
dateDiff(toDate("2024-11-03 00:30:00"), toDate("2024-11-03 02:30:00"), "hour")
dateFormat(fromMillis(toMillis(toDate("2024-03-10 01:59:59.123"))), "yyyy-MM-dd HH:mm:ss.SSS Z z")
if(isGood({[.]PV}), dateDiff(timestampOf({[.]PV}), now(1000), "second") > 10, true)
```

## Strings, Datasets, And JSON

- `trim()`, `upper()`, `lower()`, and `substring()` are useful for status text and label cleanup.
- `len("pump")` returns `4`.
- `indexOf("banana", "na")` returns `2`; string indexes are zero-based.
- `lastIndexOf("banana", "na")` returns `4`.
- `replace("banana", "na", "NA")` returns `baNANA`.
- `substring("hamburger", 4, 8)` returns `urge`.
- `split()` returns a dataset with a column named `parts`. Access a row with `[row, "parts"]`.
- `len(split("a,b,c", ","))` returns `3`.
- `split()` delimiters are regular expressions. Escape a literal dot as `"\\."`.
- `split("", ",")` can produce a one-row result. Check `len(...)` instead of assuming empty input means zero rows.
- Table-shaped DataSet values use the same row/column indexing pattern. Use zero-based row indexes and column names such as `{[.]LocalTable}[1, "Status"]`.
- `len(<dataset>)` returns the DataSet row count.
- A column name can come from a string parameter or property, such as `{[.]LocalTable}[{RowIndex}, {StatusColumn}]`.
- Cast or format table cells before using them in numeric, boolean, or display expressions: `toFloat(...)`, `toBoolean(...)`, and `numberFormat(...)` are safer than relying on implicit coercion.
- In Ignition 8.1.53 Expression Tags, a DataSet memory tag populated with platform-native DataSet values can be read with `len({[.]Table})`, fixed cell access such as `{[.]Table}[1, "Name"]`, and dynamic row/column access such as `{[.]Table}[{[.]RowIndex}, {[.]ColName}]` when the selected cell can coerce to the Expression Tag's output type.
- Dynamic row/column DataSet access still has output-type risk. Selecting a text cell into a `Float8` Expression Tag produced a null value with type-conversion error quality.
- Missing DataSet rows and columns can be wrapped with `try(...)` for a Good fallback when the DataSet itself is available, such as `try({[.]Table}[99, "Name"], "NO_ROW")` and `try({[.]Table}[0, "Missing"], "NO_COLUMN")`.
- Use `lookup(dataset, lookupValue, noMatchValue, [lookupColumn], [resultColumn])` when you need a keyed row lookup instead of a fixed row index.
- `lookup()` can use column names or column indexes. If `lookupColumn` and `resultColumn` are omitted, Ignition uses column `0` for lookup and column `1` for the returned value.
- The `lookup()` return is coerced to the type of `noMatchValue`. Use `-1.0` for a floating result, `-1` for an integer result, `false` for a boolean result, or a string fallback for display text.
- In Ignition 8.1.53 Expression Tags, string lookup keys were case-sensitive and duplicate keys returned the first matching row.
- For dynamic table paths, use the DataSet value returned by `tag()`: `lookup(tag({[.]TablePath}), "PumpC", "NO_MATCH", "Name", "Status")`. This can retarget when the path string changes and can update again when the selected table value changes.
- A missing lookup key returns `noMatchValue` with Good quality. A missing dynamic DataSet tag is different: `lookup(tag({[.]MissingTablePath}), ...)` can return null with Uncertain quality, and wrapping that shape in `try()` may still leave the value null/Uncertain rather than using the failover.
- Direct dynamic DataSet indexing has the same missing-path caution. In Ignition 8.1.53 Expression Tags, `tag({[.]TablePath})[{[.]RowIndex}, {[.]ColName}]` read the selected table while the path existed; after the path was changed to a missing tag, the expression read null with `Bad_NotFound`. Wrapping `try(tag({[.]MissingPath})[0, "PV"], -999.0)` did not replace that missing dynamic source with the fallback.
- `sortDataset(dataset, columnName, ascending)` can return a DataSet sorted by a column name. In Ignition 8.1.53 Expression Tags, sorting by a `Priority` column preserved duplicate-key row order in both ascending and descending examples.
- Numeric sort null placement can depend on direction. In Ignition 8.1.53 Expression Tags, ascending `sortDataset({[.]Table}, "PV", true)` placed the null `PV` row last, while descending `sortDataset({[.]Table}, "PV", false)` placed the null `PV` row first.
- `columnRename(dataset, newName...)` can return a DataSet with all columns renamed when you provide one new name per existing column. After renaming, index or aggregate by the new column name.
- `columnRearrange(dataset, columnName...)` can select and reorder columns. `len(columnRearrange(...))` still returns the row count.
- Aggregate functions such as `sum`, `mean`, `median`, `stdDev`, `min`, `max`, and `groupConcat` can read a DataSet column by name. In Ignition 8.1.53 Expression Tags, numeric aggregates over a mixed numeric/null `PV` column ignored null cells; empty and all-null numeric columns returned null for `sum` and `mean`; and a single-row `stdDev` returned `0.0`.
- `groupConcat(dataset, columnName, separator)` concatenates the selected column in the supplied DataSet row order. If text order matters, validate the row order of the DataSet value that feeds `groupConcat(...)`.
- Wrap missing transform or indexing column access with `try(...)` when a Good fallback is acceptable, but still read quality if the source DataSet may itself be non-Good.
- Bad-quality DataSet inputs can carry Bad quality through a transform or aggregate even when a selected value is visible. In Ignition 8.1.53 Expression Tags, `sortDataset(qualifiedValue({[.]Table}, "Bad"), "Priority", true)[0, "Name"]` returned the selected value with Bad quality, and `sum(qualifiedValue({[.]Table}, "Bad"), "PV")` returned the numeric sum with Bad quality.
- Dynamic DataSet transform and aggregate expressions can use `tag({[.]TablePath})`. In Ignition 8.1.53 Expression Tags, sorting, summing, and formatting retargeted when the path string changed and recalculated after the selected DataSet tag was rewritten.
- `jsonGet()` can read nested JSON properties from a JSON string.
- `jsonGet()` array indexes use bracket path syntax. Use `[1]`, `items[1]`, or `items[1].v`; dot-number paths such as `"1"` or `"items.1.v"` are malformed.
- Wrap optional or uncertain `jsonGet()` paths in `try(...)` when a fallback value is acceptable.
- In Ignition 8.1.53 Expression Tags, `jsonGet({[.]JsonText}, "items[0].name")`, `jsonGet({[.]JsonText}, "items[1].pv")`, and `jsonGet({[.]JsonText}, "items[0].enabled")` read string, numeric, and boolean values from a JSON string source with Good quality.
- A JSON path can be built from expression text, such as `jsonGet({[.]JsonText}, "items[" + {[.]IndexText} + "].name")`.
- A missing JSON path wrapped in `try(jsonGet(...), fallback)` returned the fallback with Good quality. When `jsonGet(...)` extracted a JSON null into a `String` Expression Tag, the result was the text `null`; use a typed fixture before assuming null propagation for a different output type.
- `jsonSet(jsonText, path, value)` returns a modified JSON string. In an Expression Tag, that returned string does not write back to the source tag by itself; use a write-capable surface such as a Derived Tag write expression when the source value must be updated.
- In Ignition 8.1.53 Expression Tags, a `Document` memory tag with nested object/list content could be indexed directly with expressions such as `{[.]Doc}["items"][0]["name"]`, `{[.]Doc}["items"][1]["pv"]`, and `{[.]Doc}["settings"]["setpoint"]`.
- For the same `Document` source, `len({[.]Doc}["items"])` returned the item count, `typeOf({[.]Doc})` returned `ExtendedDocument`, `isNull({[.]Doc}["items"][0]["note"])` detected a present null, a dynamic index such as `{[.]Doc}["items"][{[.]Index}]["name"]` followed the index tag, and an out-of-range list access wrapped in `try(...)` returned a Good fallback.
- In Ignition 8.1.53 Expression Tags, `Float8Array` and `StringArray` memory tags accepted list writes and supported `len(...)`, direct index access, and dynamic index access. An out-of-range `Float8Array` index wrapped in `try(...)` returned a Good fallback, and an empty `StringArray` element read as an empty string.
- On the same target, writing the JSON array string `"[3.14, 2.72]"` to a `Float8Array` memory tag produced a two-element array readable by `len({[.]FloatArrayFromJson})` and `{[.]FloatArrayFromJson}[1]`.
- Bad quality can propagate through structured indexing. In Ignition 8.1.53 Expression Tags, indexing `qualifiedValue({[.]Doc}, "Bad")` and `qualifiedValue({[.]Table}, "Bad")` returned the selected value with Bad quality; wrapping the indexing expression in `try(...)` did not make the final quality Good.

Examples:

```text
upper(trim(" pump 1 "))
try(substring({[.]Code}, 9), "N/A")
split("a,b,c", ",")[1, "parts"]
split("a.b.c", "\\.")[1, "parts"]
{[.]LocalTable}[{RowIndex}, "Status"]
toFloat({[.]LocalTable}[{RowIndex}, "PV"], -1.0)
lookup({[.]LookupTable}, "PumpC", "NO_MATCH", "Name", "Status")
lookup({[.]LookupTable}, "PumpC", -1.0, "Name", "PV")
lookup(tag({[.]TablePath}), "PumpC", "NO_MATCH", "Name", "Status")
sortDataset({[.]LocalTable}, "Priority", true)[0, "Name"]
columnRename({[.]LocalTable}, "Asset", "Value", "State", "Priority", "Batch")
columnRearrange({[.]LocalTable}, "Status", "Name", "PV")
sum({[.]LocalTable}, "PV")
mean({[.]LocalTable}, "PV")
groupConcat({[.]LocalTable}, "Name", ", ")
numberFormat(sum(sortDataset(tag({[.]TablePath}), "Priority", true), "PV"), "0.00")
try(sortDataset({[.]LocalTable}, "NoSuchColumn", true)[0, "Name"], "MISSING_COLUMN")
jsonGet("{\"item\":{\"firstThing\":1,\"secondThing\":2}}", "item.secondThing")
jsonGet("{\"items\":[{\"v\":5},{\"v\":7}]}", "items[1].v")
jsonGet({[.]JsonText}, "items[" + {[.]IndexText} + "].name")
jsonSet({[.]JsonText}, "settings.setpoint", 55)
{[.]Doc}["items"][{[.]Index}]["name"]
len({[.]FloatArray})
try({[.]FloatArray}[99], -999.0)
tag({[.]TablePath})[{[.]RowIndex}, {[.]ColName}]
```

## Alarm Rollup Expressions

Use alarm expression functions as boolean rollups. Drive acknowledgement, shelving, and alarm-state operations outside the expression itself, then read both value and quality from the rollup expression.

- In Ignition 8.1.53 Expression Tags, `isAlarmActive(...)` returned Good booleans for active and clear states with exact paths, wildcard paths, and wildcard alarm names.
- `isAlarmActiveFiltered(...)` includes priority, cleared, acknowledged, and shelved filters. Read value and quality together; no-match filtered cases can return `false` with `Bad_NotFound`, not only `false` Good.
- On Ignition 8.1.53 Expression Tags, Low, High, and Critical priority filters used numeric values `1`, `3`, and `4`.
- After a manually acknowledged Critical alarm, `allowAcked=false` returned `false` Good while `allowAcked=true` kept that Critical rollup `true` Good.
- After shelving the Critical alarm, exact `isAlarmActive(path, alarmName)` returned `false` Good for that alarm. `isAlarmActiveFiltered(..., allowShelved=false)` returned `false` with `Bad_NotFound` for the shelved Critical filter, while `allowShelved=true` returned `true` Good.
- With `allowCleared=true`, a retained cleared Critical event returned `true` Good; with `allowCleared=false`, the same expression shape returned `false` Good. Set this flag intentionally.
- Dynamic path string tags can feed alarm functions, such as `isAlarmActive({[.]AreaPath})` and `isAlarmActiveFiltered({[.]AreaPath}, "*", "*", 4, 4, false, true, false)`. Validate the path string and quality after retargeting.
- In Ignition 8.1.53 Expression Tags, a provider-omitted path under the current provider followed active and clear state. Prefer explicit `[<provider>]` or `[~]` paths for reusable expressions until the target surface proves providerless behavior.

Examples:

```text
isAlarmActive("[<provider>]AreaA/*")
isAlarmActive("[<provider>]AreaA/CriticalPV", "CriticalAlarm")
isAlarmActive("[<provider>]AreaA/*", "*Alarm")
isAlarmActiveFiltered("[<provider>]AreaA/*", "*", "*", 4, 4, false, true, false)
isAlarmActiveFiltered("[<provider>]AreaA/*", "*", "*", 4, 4, false, false, false)
isAlarmActiveFiltered("[<provider>]AreaA/*", "*", "*", 4, 4, true, true, true)
isAlarmActive({[.]AreaPath})
isAlarmActiveFiltered({[.]AreaPath}, "*", "*", 1, 1, false, true, false)
```

## Number Formatting

`numberFormat()` follows Java-style numeric patterns. Percent patterns multiply by 100:

```text
numberFormat(0.348, "#.00%")
numberFormat(1234.567, "#,##0.00")
numberFormat(12.3, "000.00")
```

- `numberFormat(0.348, "#.00%")` returns `34.80%`.
- `numberFormat(1234.567, "#,##0.00")` returns `1,234.57`.
- `numberFormat(12.3, "000.00")` returns `012.30`.

Common math helpers include `floor()`, `ceil()`, `sqrt()`, `min()`, `max()`, and `round()`. In Ignition 8.1.53 Expression Tags, `round(2.5)` returns `3`.

## Dynamic Tag Paths

Prefer the platform's direct or indirect tag binding features when the UI surface supports them. Use expression `tag()` when the path itself must be built by an expression.

For expression `tag()`:

- Build a full tag path string.
- Include a provider such as `[default]` or use `[~]` when current-provider-root behavior is intended.
- Cast the result to the expected type with a safe fallback.
- Treat missing dynamic paths carefully. A conversion fallback can return a Good fallback value and hide the fact that the dynamic tag did not exist.
- Dynamic `tag()` expressions can retarget when the path-building tag/property changes, and they can update when the newly selected target value changes. If a missing dynamic target must be visible to the operator or caller, expose the resolved path, do an existence/readback check, or avoid hiding the missing path behind a Good conversion fallback.

Examples:

```text
toFloat(tag("[default]Area/Line1/Speed"), 0.0)
toFloat(tag("[~]Area/Line1/Speed"), 0.0)
toInt(tag("[default]Area/" + {[.]SelectedDevice} + "/State"), -1)
```

For Perspective Tag Binding Expression mode, the expression returns the tag path string for the binding. That is different from an Expression Binding that calls `tag()` and returns the tag value. Verify the specific binding mode before writing the expression.

## Circular References And Recovery

Avoid expression cycles in production logic. A cycle can leave a tag value null, uncertain, or carrying an expression error, and the most useful diagnostic is the value and quality together.

In Ignition 8.1.53 Expression Tags:

- A direct self-reference such as `{[.]SelfCycle} + 1` read null with `Error_ExpressionEval("Expression left operand is null.")` in the initial cycle state.
- A mutual pair such as `A = {[.]B} + 1` and `B = {[.]A} + 1` read null with the same expression error in the initial cycle state.
- A dynamic path loop such as `tag({[.]Path})`, where `Path` pointed back to the same Expression Tag, read an uncertain initial value instead of a Good calculated value.
- Derived Tags whose `SourceTagPath` pointed to themselves or to each other read null with the same expression error when the read expression used `{source} + 1`.
- After the cycle was broken by changing the expression, `Path`, or Derived Tag `SourceTagPath` to a Good source, the same tags recovered without a Gateway restart. A base source value of `10.0` produced `11.0` for direct/source-plus-one tags and `12.0` for the second tag in a repaired two-tag chain; after the base source changed to `20.0`, those values updated to `21.0` and `22.0`.
- After one repaired member in a two-tag Expression Tag chain was deleted, the deleted member read `Bad_NotFound` and the dependent member read null with an expression error. Recreating the deleted member restored both members to Good values.

In a UDT instance on the same target, expression members with self-reference, mutual-reference, and dynamic-parameter loop shapes showed the same null/error or uncertain initial behavior. After changing the UDT type expressions and retargeting the dynamic path parameter to a Good source, the instance members read Good recovered values without a Gateway restart.

Use this recovery pattern when repairing a cycle:

1. Read every involved tag value and quality.
2. Break the cycle at the source: change one expression, dynamic path tag, UDT parameter, or Derived Tag `SourceTagPath` to a known Good source.
3. Read the repaired tags again and verify value and quality.
4. Change the source value once and confirm the repaired dependency graph recalculates.
5. If a referenced member was deleted or recreated, read the dependent members again before treating the repair as complete.

Validate Gateway restart behavior, nested UDT cycles, Transaction Group Expression Items, Perspective bindings, and Vision bindings separately before relying on the same recovery behavior in those surfaces.

## Change Detection With `hasChanged()`

In Ignition 8.1.53 Expression Tags, `hasChanged(...)` keeps evaluation state. These forms configured and returned Good-quality values:

```text
hasChanged({[.]PV})
hasChanged({[.]QualifiedPV}, true)
hasChanged({[.]PV}, false, 1000)
```

Do not treat the first value after configuring an Expression Tag as a clean `false` baseline. In Ignition 8.1.53 Expression Tags, first reads after configuration were mixed: some `hasChanged(...)` expressions read `true`, while event-driven `hasChanged(..., false, 1000)` and a fixed-rate `hasChanged(...)` expression read `false`.

Timing depends on the expression's evaluation mode:

- An Event Driven Expression Tag without a `pollRate` argument read `true` after a value change and was still `true` about 3 seconds later.
- An Event Driven Expression Tag using `hasChanged({[.]PV}, false, 1000)` read `true` shortly after a value change and read `false` by about 1.5 seconds later.
- A Fixed Rate Expression Tag with `executionRate` 1000 ms read `false` shortly after the source write, then `true` near the next fixed evaluation, then `false` again by about 3.2 seconds.

Use the optional `includeQuality` argument deliberately. In Ignition 8.1.53 Expression Tags, a `qualifiedValue(...)` fixture that changed from Good to Bad while keeping the same numeric value made `hasChanged({[.]QualifiedPV}, false)` read `false`, while `hasChanged({[.]QualifiedPV}, true)` read `true`. The `true` value remained visible in the event-driven no-poll expression until another evaluation reset it.

Value changes involving Good nulls also count as changes in Expression Tags. A Good null-to-string write and a string-to-Good-null write both made `hasChanged(...)` read `true`.

Dynamic paths need the same timing caution as direct paths. In Ignition 8.1.53 Expression Tags, `hasChanged(tag({[.]PVPath}))` read `true` after retargeting the path to a different source and after writing a different value to the selected dynamic source.

When two separate Expression Tags watched the same source, both read `true` after the source changed. In Ignition 8.1.53 Expression Tags, a single expression containing two calls to `hasChanged({[.]PV})` also saw both calls return `true` after the source changed. Do not use multiple calls as a substitute for an event log; if the UI needs a resettable pulse or history, design that state explicitly.

## Quality Checks

Use quality-aware functions when a value may be stale, bad, uncertain, or unavailable:

```text
if(isGood({[.]PV}), {[.]PV}, -1)
isBadOrError({[.]PV})
qualityOf({[.]PV})
```

Quality checks should be validated against the target condition that matters. A Good memory tag proves only the good-path logic; bad/uncertain quality behavior needs a separate fixture or real target condition.

For deliberate quality fixtures, prefer `qualifiedValue()` when available:

```text
qualifiedValue(123, "Good")
qualifiedValue(123, "Uncertain")
qualifiedValue(123, "Bad")
qualifiedValue(123, "Error")
qualifiedValue(123, "Bad", 515, "Disabled by test")
isUncertain(qualifiedValue(123, "Uncertain"))
```

In Ignition 8.1.53 Expression Tags, those `qualifiedValue(...)` shapes preserved the value `123` while setting Good, Uncertain, Bad, Error, or a custom Bad diagnostic quality. `isGood(...)`, `isUncertain(...)`, `isBad(...)`, `isError(...)`, `isBadOrError(...)`, and `qualityOf(...)` returned Good-quality helper results for those qualified values.

For legacy forced-quality fixtures or deliberate low-level quality-code tests, use numeric quality codes rather than strings:

```text
forceQuality(123, 0)
forceQuality(123, 192)
isGood(forceQuality(123, 0))
isBadOrError(forceQuality(123, 0))
qualityOf(forceQuality(123, 0))
```

In Ignition 8.1.53 Expression Tags, `forceQuality(123, 0)` returns the value with Bad quality, while `forceQuality(123, 192)` returns the value with Good quality. Passing `"Bad"` as a string quality argument can fail coercion.

Bad quality can propagate even when the value itself is usable:

- `{[.]BadPV} + 1.0` can return the numeric result while keeping Bad quality.
- `try({[.]BadPV} + 1.0, -1.0)` does not use the failover when the expression evaluates successfully but carries Bad quality.
- `coalesce({[.]BadPV}, -1.0)` checks for null-like values; it does not turn a Bad-quality non-null value into a Good fallback.
- `if(isGood({[.]BadPV}), {[.]BadPV}, -1.0)` can return a Good fallback when the quality guard is false.
- `try(qualifiedValue(123, "Error"), -1.0)` can return the Good fallback, while Bad and Uncertain qualified values keep their non-Good quality unless explicitly guarded.
- `if(false, {[.]BadPV}, 5.0)` and `if(true, 5.0, {[.]BadPV})` can return the Good selected branch without inheriting the unselected Bad branch's quality, while `if(true, {[.]BadPV}, 5.0)` returns the selected value with Bad quality.
- Quality helper outputs such as `isGood(...)`, `isBad(...)`, `isBadOrError(...)`, `isError(...)`, and `qualityOf(...)` return their own Good-quality boolean/string results when the helper expression itself evaluates.

## UDT Expression Members

In UDT expression tags:

- Use `{ParamName}` for UDT parameters.
- Use `{[.]MemberName}` for sibling member tags.
- Keep dynamic full paths in parameters as strings and call `tag({FullPathParam})` without quotes around the parameter reference.
- Do not use `tag("{FullPathParam}")`; that passes a literal string instead of the parameter value and can produce an expression evaluation error for the literal brace path instead of returning a conversion fallback.
- Do not build direct brace tag references such as `{[Provider]{Root}/PV}` from parameters. Use `tag()` for dynamic paths.
- Validate both the UDT instance's `Parameters.ParamName` values and the dependent member values/qualities.
- Prefer typed numeric/boolean parameter overrides for numeric/boolean expression work. String values that look numeric can coerce in multiplication, but `+` can concatenate once a string is involved. For example, a `Scale` parameter value of `"2.5"` can make `{Scale} * 2` evaluate numerically while `{Scale} + 1` evaluates as text-like concatenation.
- Bad strings in numeric/boolean UDT parameters can configure successfully but fail at runtime with expression or type-conversion quality errors. Test the runtime value and quality, not just configuration success.
- After changing UDT instance parameter overrides, read the dependent expression members again. Parameter readback representation can vary by configure/update path, so a `Parameters.ParamName` read alone is not enough proof that dependent math, comparison, formatting, or dynamic `tag()` members are correct.

Patterns:

```text
{[.]PV} * {Scale}
if({EnableAlarm}, {[.]PV} > {HighLimit}, false)
toFloat(tag({FullPathParam}), 0.0)
{AssetName} + ": " + numberFormat({[.]ScaledPV}, "0.0")
```

### UDT DataSet/Table Members

For UDT members that read table-shaped DataSet tags:

- Configure the table member as a memory tag with `dataType: "DataSet"` when the value is a DataSet.
- Use `{[.]LocalTable}[{RowIndex}, "Status"]` for sibling DataSet members.
- Use `{[.]LocalTable}[{RowIndex}, {StatusColumn}]` when the column name is a UDT string parameter.
- Use `tag({TablePath})[{RowIndex}, "Status"]` when a UDT string parameter contains the full path to an external DataSet tag.
- Use `len({[.]LocalTable})` or `len(tag({TablePath}))` for row count checks.
- Use `toFloat({[.]LocalTable}[{RowIndex}, "PV"], -1.0)` and `toBoolean({[.]LocalTable}[{RowIndex}, "Enabled"], false)` for typed cells.
- Re-read dependent expression members after a row-index parameter change or after the DataSet tag is rewritten. Both parameter changes and table-value changes can recalculate member values.
- Keep separate validation for each UDT instance. The same UDT type can have different `RowIndex`, `TablePath`, and scale parameters per instance.
- `try({[.]LocalTable}[{RowIndex}, "NoSuchColumn"], "MISSING")` can provide a Good fallback for an invalid DataSet column, and `try({[.]LocalTable}[99, "Status"], "NO_ROW")` can provide a Good fallback for an out-of-range DataSet row.
- Do not assume `try(tag({MissingTablePath})[0, "Status"], "NO_TABLE")` will mask a missing dynamic DataSet tag. A missing dynamic tag path can leave the expression value null with Bad_NotFound quality instead of returning the fallback. If missing tables must be operator-visible, expose the resolved path or add an existence/readback check.
- For keyed table lookup, `lookup(tag({TablePath}), "PumpC", "NO_MATCH", "Name", "Status")` can read from a dynamic DataSet path. If `TablePath` changes to a different DataSet tag, the expression can retarget; if the selected DataSet is rewritten, the lookup can recalculate. Still validate missing-path quality separately because `lookup(tag({MissingTablePath}), ...)` can return null with Uncertain quality instead of `noMatchValue`.
- Floating-point DataSet cells can read back with binary precision tails. Use `numberFormat()` for display and tolerance for validation.

Example table-member expressions:

```text
len({[.]LocalTable})
{[.]LocalTable}[{RowIndex}, "Status"]
{[.]LocalTable}[{RowIndex}, {StatusColumn}]
toFloat({[.]LocalTable}[{RowIndex}, "PV"], -1.0) * {PVScale}
tag({TablePath})[{RowIndex}, "Status"]
tag({TablePath})[{RowIndex}, {StatusColumn}]
tag({TablePath})[{RowIndex}, "Name"] + ": " + numberFormat(tag({TablePath})[{RowIndex}, "PV"], "0.0")
lookup(tag({TablePath}), "PumpC", "NO_MATCH", "Name", "Status")
try({[.]LocalTable}[{RowIndex}, "NoSuchColumn"], "MISSING")
```

## Perspective And Vision Notes

- Expression bindings and expression transforms use the Ignition expression language, but their reference paths are surface-specific. Perspective property references look like `{view.params.asset}`, `{page.props.urlParams.filter}`, or `{../Input.props.text}`. Vision property references use Vision component paths.
- Perspective tag bindings have multiple modes. Direct and Indirect Tag bindings are not the same as an Expression Binding. In Tag Binding Expression mode, the expression resolves to a tag path string.
- When a Perspective expression drives a visible page, validate in the client when rendering, URL parameters, component property updates, or user interaction matter. API expression-tag tests do not prove browser binding behavior by themselves.
- If the expression uses URL parameters, text fields, dropdowns, or other component state, make the value visible somewhere during testing so the property reference and the final expression output can be checked together.

## `runScript()`

Use `runScript()` sparingly. It evaluates a single line of Python/Jython from an expression and can call a script function by path. Prefer expression functions, tag bindings, Named Queries, Gateway events, or project-library scripts outside the expression when the logic is complex.

Syntax shape:

```text
runScript(scriptFunction, [pollRate], [arg...])
```

In Ignition 8.1.53 Expression Tags, these shapes are valid:

```text
runScript("1 + 2", 0)
runScript("len", 0, "abcd")
runScript("len('abcd')", 0)
runScript("system.date.now", 0)
runScript("system.date.now()", 0)
try(runScript("1/0", 0), -1)
```

For project-library functions in Expression Tags or other Gateway-scope expression surfaces, the Gateway Scripting Project must be configured to the project that contains the script. Once that scope is available, call the function by its library path, such as:

```text
runScript("textScript.myFunc", 0, {[.]State}, "fallback")
```

Do not use `project.` or a project-name prefix as a generic rule for Expression Tags. If the Gateway Scripting Project is not configured or the library path is not visible to the evaluating scope, the expression can fail with an expression-evaluation error. Wrap risky calls only when a normal fallback is acceptable:

```text
try(runScript("textScript.maybeFaulty", 0, {[.]PV}), "SCRIPT_FAIL")
```

Keep the called code:

- Pure, deterministic, and fast.
- Available in the scope that evaluates the expression.
- Explicit about polling rate when polling is intended, and separately validate the tag group or binding refresh behavior.
- Free of writes, long database calls, network calls, sleeps, and user-specific side effects.

In Expression Tags, `pollRate` is not the only timing control. The tag group or scan class can cap when the tag evaluates. A `pollRate` of `0` is not a polling timer; use it for non-polling calls and verify refresh behavior when timing matters.

## Gateway API Validation Workflow

When Gateway API access is available, use live validation for important or uncertain expression behavior.

Read `references/expression-api-validation.md` before using this workflow. Treat the live `health` response and its `supportedActions` and feature flags as authoritative for the installed runner.

1. Call `health`, then `gatewayInfo`, then `tagProviders`.
2. Confirm the runner actions and feature flags before relying on them.
3. Create a unique disposable test folder under a known provider. Use a neutral root such as `[<provider>]_expression_skill_tests/<uniqueId>`.
4. Use `tagConfigure` with `dryRun: true`, `allowedTagPathPrefixes`, `collisionPolicy: "a"`, and a small `maxItems` before any actual fixture write.
5. Configure only memory tags, expression tags, Derived Tags, folders, and UDT fixtures needed for the test.
6. Read results with `tagRead`; inspect both `value` and `quality`.
7. For input changes, prefer a narrow tag-write API if available. If the active runner exposes no tag-write/delete actions, use confirmed `scriptEval` only for bounded `system.tag.writeBlocking` and cleanup against the unique disposable folder.
8. Do not use broad arbitrary `scriptEval` for normal expression work. Treat it as trusted administrative code execution.
9. Clean up only the exact unique test folder created by the run.
10. Do not add target-specific connection details or disposable resource names to reusable guidance.

Minimal expression-tag fixture:

```json
{
  "basePath": "[<provider>]_expression_skill_tests/<uniqueId>",
  "tags": [
    {"name": "A", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float8", "value": 5.0},
    {"name": "B", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float8", "value": 3.0},
    {"name": "Sum", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Float8", "executionMode": "EventDriven", "expression": "{[.]A} + {[.]B}"}
  ]
}
```

Read and validate:

```json
{
  "action": "tagRead",
  "paths": ["[<provider>]_expression_skill_tests/<uniqueId>/Sum"],
  "maxResults": 1
}
```

For a fuller reusable matrix, use `references/expression-test-matrix.md`.

## Static Review Checklist

Check these before handing back an expression:

- The expression surface is named and the reference syntax matches that surface.
- Equality uses `=`.
- Guarded divide-by-zero uses `if(den = 0, fallback, numerator / den)`.
- `try()` is used for actual evaluation exceptions, not as the only divide-by-zero guard.
- The output type matches the tag/property type and expected coercion.
- Derived Tag read and write expressions use `{source}` and `{value}` in the correct direction, and the source supports writes when writeback is expected.
- Derived Tag retargeting validates the `SourceTagPath` property plus read/write behavior after the retarget.
- Parameterized Derived Tag source paths in UDTs are proven on the target before they are trusted.
- Surface-specific behavior is labeled by surface; tag-side Expression Tag, UDT expression member, and Derived Tag results are not reused as Perspective or Vision coverage.
- Integer coercion/rounding is intentional.
- Float expectations allow tolerance.
- Empty string handling is intentional; `coalesce()` does not treat `""` as null.
- Null tag values are guarded before arithmetic if a default number is required.
- Date patterns use lowercase `yyyy` and `dd` unless week-year or day-of-year is intentionally required.
- Date arithmetic, date diff units, and `now()` refresh behavior are verified when timing or month-end behavior matters.
- Stale-data expressions check both age and source quality; `timestampOf(...)` alone is not a missing-source detector.
- `hasChanged(...)` logic does not assume the first configured value is false, and timing-sensitive uses specify Event Driven/no-poll, Event Driven with `pollRate`, or Fixed Rate behavior.
- `split()` delimiters are treated as regex and literal punctuation is escaped.
- Dataset access uses a valid zero-based row and column name, such as `[1, "parts"]` or `{[.]LocalTable}[{RowIndex}, "Status"]`.
- DataSet dynamic row/column expressions verify that the selected cell type matches the output tag or property type.
- Dynamic DataSet paths use `tag({TablePath})[...]` without quotes around the path parameter, and missing dynamic table paths are not hidden unless that behavior has been verified.
- JSON array paths use bracket syntax such as `[0]` and `items[1].v`.
- `jsonSet(...)` results are written back only by an explicit write-capable surface; an Expression Tag result alone is just the returned JSON string.
- Document and array indexing reads value and quality together, especially when the source may be Bad quality or the index may be out of range.
- Dynamic `tag()` paths include a provider or intentionally use `[~]`, and the result is cast.
- Missing dynamic tags are not hidden by Good fallback values unless that is explicitly desired.
- Circular expression dependencies are repaired by changing a real expression/path/source, then re-reading value and quality after the repair and after one source-value change.
- UDT cycle repairs are validated on an actual instance, not only by inspecting the UDT type or parameter values.
- Deliberate quality fixtures use `qualifiedValue(...)` when available, or numeric `forceQuality(...)` codes when low-level quality-code behavior is specifically intended.
- UDT parameters use `{ParamName}` and dynamic parameter paths use `tag({ParamName})` without quotes.
- Quality checks consider value and quality, not value alone.
- Large or high-frequency expressions have target-local timing evidence and a fallback plan for moving logic out of the expression.
- `runScript()` is pure, fast, scope-valid, has an intentional poll rate, and has Gateway Scripting Project availability checked when called from Expression Tags or Gateway scope.
- Alarm rollups read value and quality together, especially no-match `isAlarmActiveFiltered(...)` cases, acknowledgement filters, shelving filters, and dynamic path retargets.
- Alarm-state actions such as acknowledgement and shelving are kept outside the expression; the expression reads the resulting state.

## Response Pattern

When answering an expression-language request, include:

- Target context: Gateway version if known, expression surface, provider/path/property context, and output type.
- Expression: the exact expression or a small set of alternatives.
- Why it fits: only the shortest useful explanation of syntax, data type, or quality behavior.
- Validation: live API result summary when available, or a target-side validation checklist when not.
- Caveats: version mismatch, unverified Perspective/Vision client behavior, possible hidden fallback, or cleanup status.

## Official Ignition 8.1 References

- Expression language and syntax: https://www.docs.inductiveautomation.com/docs/8.1/platform/expression-language-and-syntax
- Expression functions: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions
- `if`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/logic/if
- `case`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/logic/case
- `lookup`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/logic/lookup
- `try`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/logic/try
- `hasChanged`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/logic/hasChanged
- `isAlarmActive`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/alarming/isAlarmActive
- `isAlarmActiveFiltered`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/alarming/isAlarmActiveFiltered
- `tag`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/advanced/tag
- `qualityOf`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/advanced/qualityOf
- `runScript`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/advanced/runScript
- Project Library scripts and Gateway Scripting Project: https://www.docs.inductiveautomation.com/docs/8.1/platform/scripting/scripting-in-ignition/project-library
- Tag paths: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/tag-paths
- Tag properties: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/tag-properties
- Types of tags: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/types-of-tags
- Quality codes and overlays: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/quality-codes-and-overlays
- UDT parameters: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/user-defined-types-udts/udt-parameters
- Perspective expression bindings: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/expression-bindings-in-perspective
- Perspective tag bindings: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/tag-bindings-in-perspective
- Perspective expression transform: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/transforms/expression-transform
- Vision expression binding: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/vision/binding-types-in-vision/expression-binding-in-vision
- Vision indirect tag binding: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/vision/binding-types-in-vision/indirect-tag-bindings-in-vision
- `system.tag.configure`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-configure
- `system.tag.readBlocking`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-readBlocking
- `system.tag.writeBlocking`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-writeBlocking
- `system.tag.deleteTags`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-deleteTags
- `system.tag.getConfiguration`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-getConfiguration
- `system.tag.exists`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-exists
