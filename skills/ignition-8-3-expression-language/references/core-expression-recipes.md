# Core Expression Recipes

Use these patterns after identifying the exact expression host and configured output type.

## Syntax and Precedence

```text
5 + 3 * 2                         // 11
(5 + 3) * 2                       // 16
5 = 5 && 2 != 3                   // true
!(1 = 2)                          // true
5 | 3                             // 7
1 << 4                            // 16
"Pump 101" like "Pump*"           // wildcard match
```

Ignition uses `=` for equality. Function arguments are expressions and can be nested. Whitespace is largely ignored. `//` begins a line comment.

On the verified 8.3.8 Expression Tag target, `if(true, 1, 1/0)` returned `1` with Good quality. Treat that as selected-branch value behavior, not proof about subscriptions or every expression host.

## Conditionals and Guards

```text
if({[.]Enabled}, {[.]PV}, 0)
if({[.]Den} = 0, -1.0, {[.]Num} / {[.]Den})
case({[.]Mode}, 1, "Auto", 2, "Manual", "Unknown")
switch({[.]State}, 0, 1, 2, "Off", "Running", "Fault", "Unknown")
try(toInt("boom"), -1)
coalesce({[.]OperatorName}, "N/A")
```

Choose the guard by failure class:

| Situation | Preferred pattern |
|---|---|
| Avoidable unsafe branch | `if()` or `case()` |
| Evaluation exception | `try()` |
| Null-like value | `coalesce()` |
| Invalid conversion | `toFloat(value, fallback)` or matching cast |
| Non-Good quality | `if(isGood(value), value, fallback)` |

No one fallback handles every failure.

## Expression Tag Types

The configured tag data type participates in the result:

- `Boolean`: predicates and flags.
- `Int1`, `Int2`, `Int4`, `Int8`: integer output with width-specific range and coercion.
- `Float4`: single-precision floating output.
- `Float8`: double-precision floating output.
- `String`: text and formatted values.
- `Date`: date/time result.
- `DataSet`: tabular values.
- `Document`: JSON-like structured values.

Use `Float8` for calculations where a fractional or high-precision result must survive. A mathematically exact decimal can read back with binary floating-point rounding, especially as `Float4`; compare numerics with a type-appropriate tolerance.

Useful diagnostics:

```text
typeOf({[.]A})
qualityOf({[.]A})
timestampOf({[.]A})
```

On the verified 8.3.8 Expression Tag fixture, a `Float8` sibling read through `typeOf({[.]A})` returned `Double`.

## Nulls

```text
isNull({[.]MaybeNull})
{[.]MaybeNull} = null
coalesce({[.]MaybeNull}, 7.5)
```

An empty string is not null. On the verified 8.3.8 target, a Good null fixture:

- Returned `true` from `isNull(...)`.
- Compared equal to `null`.
- Returned `7.5` through `coalesce(..., 7.5)`.
- Produced a null value with `Error_ExpressionEval` when used in `{[.]MaybeNull} + 5`.

Use a typed fallback before arithmetic when null means a default number.

## Static and Dynamic Tag Paths

Static references:

```text
{[.]A}
{[~]Area/Line1/PV}
{[<provider>]Area/Line1/PV}
```

Dynamic reads:

```text
toFloat(tag("[~]Area/" + {[.]SelectedDevice} + "/PV"), -1.0)
toInt(tag("[<provider>]Area/" + {[.]Asset} + "/State"), -1)
```

The verified 8.3.8 Expression Tag fixture resolved:

- `{[.]A} + {[.]B}` from sibling tags.
- An explicit provider path passed to `tag()`.
- A `[~]` current-provider path passed to `tag()`.
- A missing dynamic tag through `toFloat(tag(path), -999.0)` to the fallback.

That last pattern can hide a missing tag behind a Good result. Expose or independently verify the resolved path when absence matters.

## Numbers and Formatting

```text
numberFormat(0.348, "#.00%")       // 34.80%
numberFormat(1234.567, "#,##0.00")
numberFormat(12.3, "000.00")
floor(2.9)
ceil(2.1)
round(2.5)
sqrt(81)
```

Remember that percent patterns multiply by 100. Avoid assuming a language-level rounding rule is identical to final tag-type coercion; test both the function and configured type when boundary values matter.

## Dates and Times

```text
dateFormat(now(1000), "yyyy-MM-dd HH:mm:ss")
dateArithmetic(now(), -15, "minute")
dateDiff(startDate, endDate, "hour")
dateExtract(someDate, "month")
toDate("2024-03-10 01:30:00")
```

Pattern case matters:

- `yyyy`: calendar year.
- `YYYY`: week-year.
- `dd`: day of month.
- `DD`: day of year.

Record the evaluation timezone. Test DST spring gaps and fall overlaps when the result affects operations. Gateway-scope, Vision-client, and Perspective-session timezones can differ.

## Strings

```text
upper(trim(" pump 1 "))
concat("Asset: ", {[.]AssetName})
try(substring({[.]Code}, 9), "N/A")
split("a,b,c", ",")[1, "parts"]
replace({[.]Text}, "old", "new")
```

`+` can concatenate when a string operand is involved. Cast explicitly when `"2" + 3` must not become text before final output coercion.

## JSON, Documents, Arrays, and Collections

JSON-string functions:

```text
jsonGet("{\"item\":{\"v\":2}}", "item.v")
jsonGet("{\"items\":[{\"v\":5},{\"v\":7}]}", "items[1].v")
try(jsonGet({[.]JsonText}, "items[9].v"), -1)
jsonSet({[.]JsonText}, "settings.setpoint", 55)
```

Use bracket notation for array indexes inside `jsonGet()` paths, such as `items[1].v`. A dotted numeric segment such as `items.1.v` is malformed on the verified 8.3.8 target.

Document or mapping access:

```text
{[.]Doc}["settings"]["setpoint"]
{[.]Doc}["items"][0]["name"]
len({[.]Doc}["items"])
```

Collection access uses zero-based indexes. Wrap optional or out-of-range access when a fallback is acceptable, and validate the value type plus quality.

## DataSets

```text
{[.]Table}[0, "Status"]
toFloat({[.]Table}[{[.]RowIndex}, "PV"], -1.0)
lookup({[.]Table}, "PumpC", "NO_MATCH", "Name", "Status")
sortDataset({[.]Table}, "Priority", true)
sum({[.]Table}, "PV")
mean({[.]Table}, "PV")
groupConcat({[.]Table}, "Name", ", ")
columnRename({[.]Table}, "Asset", "Value", "State", "Priority", "Batch")
columnRearrange({[.]Table}, "Status", "Name", "PV")
```

Dataset indexing may require a type cast because the expression engine cannot always infer a column's type. Validate missing rows, missing columns, empty datasets, null cells, heterogeneous columns, and non-Good source quality.

## UDTs

```text
{[.]PV} * {Scale}
if({EnableAlarm}, {[.]PV} > {HighLimit}, false)
toFloat(tag({FullPathParam}), 0.0)
{AssetName} + ": " + numberFormat({[.]ScaledPV}, "0.0")
```

Use `{ParamName}` for a UDT parameter and `{[.]Member}` for a sibling member. When a parameter contains a full tag path, call `tag({FullPathParam})`; quoting the brace reference passes literal text instead of the parameter value.

After changing UDT parameters, read the dependent member's value and quality. Parameter readback alone does not prove the expression recalculated correctly.

## `runScript()` Return And Error Boundaries

Prefer a project-library function path and positional arguments:

```text
runScript("textScript.statusText", 0, {[.]State})
try(runScript("textScript.statusText", 0, {[.]State}), "SCRIPT_FAIL")
```

On the verified 8.3.8 Expression Tag target, fixed built-in controls produced:

| Expression | Value | Quality |
|---|---:|---|
| `runScript("1 + 2", 0)` | `3` | Good |
| `runScript("len", 0, "abcd")` | `4` | Good |
| `runScript("len('abcd')", 0)` | `4` | Good |
| `runScript("None", 0)` | null | Good |
| `runScript("1/0", 0)` | null | `Error_ExpressionEval` |
| `try(runScript("1/0", 0), -1)` | `-1` | Good |
| `runScript("LLMRunScriptIdentity.runtimeIdentity", 0)` with no Gateway Scripting Project | null | `Error_ExpressionEval`, full code `-1073741054` |
| `try(runScript("LLMRunScriptIdentity.runtimeIdentity", 0), "SCRIPT_FAIL")` in that same state | `SCRIPT_FAIL` | Good |

A Good null return is not the same as a script exception. Inspect both value and quality. Use `try()` when a fallback is appropriate for evaluation failures, but do not let it hide a configuration or availability problem that operators need to see.

For the fixed missing-Gateway-Scripting-Project case, the direct diagnostic was `Error executing script for runScript() expression:LLMRunScriptIdentity.runtimeIdentity`. Treat that result as a configuration-state symptom, not a universal classifier for every missing project, module, function, or permission. Inspect the Gateway Scripting Project before rewriting the expression.

A separate fixed scalar-return profile recorded the receiving tag type and Jython/Python value type:

| Fixed script result | Tag data type | Value | Receiving type | Quality |
|---|---|---:|---|---|
| integer | `Int4` | `42` | `int` | Good/192 |
| long | `Int8` | `2147483648` | `long` | Good/192 |
| float | `Float8` | `2.5` | `float` | Good/192 |
| Unicode string | `String` | `alpha` | `unicode` | Good/192 |
| boolean | `Boolean` | `true` | `bool` | Good/192 |

A separate fixed structured-return profile recorded typed Expression Tag
conversion and the Gateway read surface:

| Fixed script result | Tag data type | Serialized value | Receiving type | Quality |
|---|---|---|---|---|
| `java.util.Date(0)` | `DateTime` | epoch milliseconds `0` | `java.util.Date` | Good/192 |
| DataSet with `Label`, `Amount` and rows `A/1`, `B/2` | `DataSet` | column names, Java column types, and rows preserved | `BasicDataset` | Good/192 |
| `[1, u"two", True]` | `Document` | `[1, "two", true]` | `array` | Good/192 |
| `{u"alpha": 1, u"nested": {u"beta": 2}}` | `Document` | matching object | `PyDocumentObjectAdapter` | Good/192 |
| explicit Ignition Document `{"gamma":3,"delta":[4,5]}` | `Document` | matching object | `PyDocumentObjectAdapter` | Good/192 |

Treat other structured shapes and sizes, configured project-library lookup, tag-group scheduling, runtime load, and non-tag host behavior as separate validation dimensions. Do not infer arbitrary object coercion, polling, or performance from these fixed return-value tests.

A separate fixed Java-interop profile used only Java standard-library
constructors and methods:

| Fixed script result | Tag data type | Value | Receiving type | Quality |
|---|---|---:|---|---|
| `BigDecimal("12.50").multiply(BigDecimal("2"))` | `Float8` | `25.0` | `float` | Good/192 |
| `StringBuilder(u"alpha").append(u"-beta").reverse().toString()` | `String` | `ateb-ahpla` | `unicode` | Good/192 |

These controls prove only the fixed constructors, method chains, and receiving
tag conversions on the tested Gateway. Validate other Java classes,
constructors, overloads, third-party libraries, return objects, and expression
hosts separately.

### Poll rate zero in one Event-Driven Expression Tag

A fixed Event-Driven Gateway Expression Tag used `runScript(..., 0)` to call
`system.tag.readBlocking` on one absolute source path from inside the script.
The expression contained no Ignition expression tag reference. After the source
changed from `10` to `20`, the target remained `10` with its exact original
timestamp through 14 Good/192 observations spanning 3.629 seconds. A
server-owned configuration change replaced the expression with a semantically
equivalent form; the target then became `20` with a newer Good/192 timestamp.

For this exact scenario, poll rate zero did not create a periodic timer.
Configuration change still triggered reevaluation, so do not describe zero as
"evaluate once forever." Validate registered tag references, other execution
modes, Tag Groups, project-library functions, longer intervals, bindings, and
other expression hosts separately.

### Fixed 250-millisecond poll in one Event-Driven Expression Tag

A fixed Event-Driven Gateway Expression Tag with no Ignition expression tag
reference used `runScript("system.date.now().getTime()", 250)`. It produced 23
distinct Good/192 updates across 40 reads over 5.490 seconds. The distinct
update timestamps spanned 5.512 seconds. Observed inter-update intervals were
250–251 milliseconds with a 251-millisecond median.

Treat this as an observed fixed scenario, not an exact scheduler guarantee.
Validate effective cadence on the target Tag Group and expression surface.
Other poll rates, Tag Groups, execution modes, project-library functions,
bindings, hosts, loads, performance conditions, and migration paths remain
separate validation cases.

### Input reference plus a fixed poll

One fixed Event-Driven Gateway Expression Tag embedded a numeric bound input
in a server-owned `runScript(..., 2000)` script string and returned both the
input and execution time. With input `10`, the first unchanged-input poll
occurred 2,000 milliseconds after initial execution. Changing the input to
`20` produced a separate Good/192 execution 116 milliseconds after that poll.
The next poll occurred 1,884 milliseconds after the input-triggered execution,
exactly 2,000 milliseconds after the preceding poll.

In this fixed run, the input-triggered execution was inserted between polls
without shifting the observed poll phase. Treat that as a measured interaction,
not a scheduler guarantee. Validate it on the target Tag Group and expression
surface.

Prefer the positional-argument form of `runScript()` for normal authoring.
Never interpolate untrusted text into a script string. The measured control
used one fixed numeric input; validate other input types, preferred-argument
project functions, poll rates, Tag Groups, execution modes, hosts, loads,
performance conditions, restarts, and migration separately.

### Fixed blocking-latency cohorts

One fixed Event-Driven Gateway Expression Tag campaign triggered 0-, 25-, and
100-millisecond sleeps in cohorts of one and four targets:

| Sleep | One-target internal elapsed / script window | Four-target internal elapsed | Four-target script window |
|---:|---:|---:|---:|
| 0 ms | 0 / 0 ms | 0, 0, 0, 0 ms | 1 ms |
| 25 ms | 25 / 25 ms | 28, 28, 28, 25 ms | 54 ms |
| 100 ms | 101 / 101 ms | 103, 103, 100, 100 ms | 202 ms |

The write-start-to-all-target-detection measurements were 28, 70, and 156
milliseconds for the one-target cohorts and 25, 81, and 267 milliseconds for
the four-target cohorts. Detection includes write, read, and observation
overhead; do not treat it as script execution time.

These values demonstrate visible blocking delay only for the fixed scripts,
cohort sizes, Tag Group, host, and test conditions. They do not establish a
scheduler, concurrency, throughput, or capacity guarantee. Keep
`runScript()` work short. If blocking work cannot be removed, validate both
per-expression and aggregate latency with the intended Tag Group and
representative load.

### Fixed concurrent-tag fan-out

One local Event-Driven Gateway Expression Tag campaign triggered fixed
100-millisecond scripts in cohorts of 1, 10, and 25 targets:

| Targets | Per-expression internal elapsed | Script window | Maximum observed interval overlap | Write start to all-target detection |
|---:|---:|---:|---:|---:|
| 1 | 101 ms | 101 ms | 1 | 152 ms |
| 10 | 100-106 ms (median 103.5 ms) | 413 ms | 3 | 472 ms |
| 25 | 100-104 ms (median 101 ms) | 919 ms | 3 | 945 ms |

All 36 targets were Good/192 with zero Bad or expression-error results.
Across 48 bounded performance samples, CPU was 0.638-2.027 percent, the total
reported thread-state count was 209-227, blocked threads remained zero, and
heap use was approximately 1.62-1.76 GB. The action-through-rollback Gateway
log window contained no warning-or-higher entries.

HTTP sampling and tag reads add observer overhead, and detection includes the
write/read loop. These values cover one local Gateway, one Tag Group, fixed
work, fixed counts, and one credited trigger pass per cohort. They are not an
SLA, capacity, throughput, scheduler, maximum-concurrency, session-load, or
production-sizing guarantee. Measure representative fan-out on the intended
Tag Group while recording latency, CPU, memory, thread states, quality, and
Gateway logs.

### Project-library save and update lifecycle

For a Gateway-scoped Expression Tag that calls a project-library function,
first configure the intended project as the Gateway Scripting Project. After
saving or deploying a script change, observe the same tag until it returns
the intended new value at Good quality. Record its timestamp and inspect
Gateway logs; a successful project save alone does not prove that the
expression has recovered.

In one fixed 8.3.8 test, a polling String Expression Tag initially returned
the expected value at Good/192. A supported project update changed only the
called function. The intended updated value then remained Good/192 for eight
consecutive observations. No transient expression error was observed, and the
full Gateway was not restarted.

Do not generalize that timing or the absence of a transient. Other functions,
script structures, projects, Tag Groups, bindings, sessions, redundant
Gateways, and migration paths require their own validation. If temporary
unavailability is unacceptable, use `try()` only with an explicitly safe
fallback and continue to expose quality or operational diagnostics; a Good
fallback is not proof that project-library resolution recovered.

### Gateway-backup migration of script-backed expressions

Use an installer upgrade or Gateway-backup restore when the claim concerns
Gateway-wide 8.1-to-8.3 migration. Direct project or tag import tests content
portability, not the same configuration transformation.

One fixed supported route backed up Ignition 8.1.53 and restored it into
Ignition 8.3.8. Two project-library files and five Expression Tag texts were
exact after restore. The set covered imported integer and string functions, a
deterministic exception, the same exception under `try()`, and one
500-millisecond polled function.

The imported integer and string stayed Good, the direct exception stayed
`Error_ExpressionEval`, the guarded expression returned the Good fallback, and
the polled function produced 11 distinct Good timestamps in 20 observations
on both versions. Confirm that the intended Gateway Scripting Project survives
the restore, compare script and expression text, and validate value, type,
full quality, timestamp, polling, restart persistence, and logs on both sides.

This covers only exact 8.1.53 and 8.3.8 builds, two fixed source files, five
fixed Expression Tags, and the Gateway-backup route. It does not cover the
installer route, other imports, return shapes, poll rates, Tag Groups,
bindings, sessions, redundancy, production load, or required rewrites in other
projects.

## Official References

- Syntax, bound values, DataSet access, and collection access: https://www.docs.inductiveautomation.com/docs/8.3/platform/expression-language-and-syntax
- Expression function index: https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions
- DataSet aggregates: https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/aggregates
- Create a DataSet in scripting: https://www.docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-dataset/system-dataset-toDataset
- Tag data types and coercion: https://www.docs.inductiveautomation.com/docs/8.3/platform/tags/tag-data-types
- Dynamic `tag()`: https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/advanced/tag
- UDT parameters in expressions: https://www.docs.inductiveautomation.com/docs/8.3/platform/tags/user-defined-types-udts/udt-parameters
- `runScript()`: https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/advanced/runScript
- Jython and Java-library access: https://www.docs.inductiveautomation.com/docs/8.3/platform/scripting/python-scripting/libraries
- Tag Groups: https://www.docs.inductiveautomation.com/docs/8.3/platform/tags/tag-groups
- Gateway system performance: https://www.docs.inductiveautomation.com/docs/8.3/platform/gateway/web-interface/diagnostics/system-performance
- Gateway Scripting Project setting: https://www.docs.inductiveautomation.com/docs/8.3/platform/gateway/web-interface/platform/gateway-settings
- Saving projects: https://www.docs.inductiveautomation.com/docs/8.3/platform/designer/saving-projects
- Gateway project-script lifecycle: https://www.docs.inductiveautomation.com/docs/8.3/platform/scripting/scripting-in-ignition/gateway-event-scripts
- 8.1-to-8.3 upgrade guide: https://www.docs.inductiveautomation.com/docs/8.3/getting-started/installing-and-upgrading/ignition-8-upgrade-guide/81to83-upgrade-guide
