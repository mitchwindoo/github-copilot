# Ignition Expression Test Matrix

Use this reference when building a small, disposable live validation fixture for Ignition 8.1 expression-language behavior. Keep target-specific connection details outside this file.

## Contents

- [Fixture Shape](#fixture-shape)
- [Core Matrix](#core-matrix)
- [Tag Reference Matrix](#tag-reference-matrix)
- [Edge Case Matrix](#edge-case-matrix)
- [Numeric Bounds And Coercion Matrix](#numeric-bounds-and-coercion-matrix)
- [DST And Timezone Matrix](#dst-and-timezone-matrix)
- [Advanced Behavior Matrix](#advanced-behavior-matrix)
- [Null Tag Matrix](#null-tag-matrix)
- [Dynamic Retarget Matrix](#dynamic-retarget-matrix)
- [Circular Reference Recovery Matrix](#circular-reference-recovery-matrix)
- [Tag-Side Cross-Surface Differential Matrix](#tag-side-cross-surface-differential-matrix)
- [Timestamp And Stale-Data Matrix](#timestamp-and-stale-data-matrix)
- [JSON And Quality Matrix](#json-and-quality-matrix)
- [Quality Propagation Matrix](#quality-propagation-matrix)
- [DataSet Lookup Matrix](#dataset-lookup-matrix)
- [DataSet Transform And Aggregate Matrix](#dataset-transform-and-aggregate-matrix)
- [Structured Value Representation Matrix](#structured-value-representation-matrix)
- [Alarm Rollup Matrix](#alarm-rollup-matrix)
- [Expression Tag Execution Timing Matrix](#expression-tag-execution-timing-matrix)
- [Performance Boundary Matrix](#performance-boundary-matrix)
- [UDT Expression Member Matrix](#udt-expression-member-matrix)
- [UDT DataSet/Table Member Matrix](#udt-datasettable-member-matrix)
- [`runScript()` Matrix](#runscript-matrix)
- [`hasChanged()` Matrix](#haschanged-matrix)
- [API Request Templates](#api-request-templates)

## Fixture Shape

Create a unique disposable folder under a discovered provider:

```text
[<provider>]_expression_skill_tests/<uniqueId>
```

Recommended memory tags:

| Name | Type | Initial value | Purpose |
|---|---:|---:|---|
| `A` | `Float8` | `5.0` | Arithmetic, relative references, dynamic tag reads |
| `B` | `Float8` | `3.0` | Arithmetic |
| `Num` | `Float8` | `10.0` | Division |
| `Den` | `Float8` | `0.0` | Divide-by-zero guard |

Recommended expression tag configuration fields:

```json
{
  "tagType": "AtomicTag",
  "valueSource": "expr",
  "executionMode": "EventDriven",
  "dataType": "<String|Float8|Int4|Boolean>",
  "expression": "<expression>"
}
```

## Core Matrix

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| Arithmetic precedence | `5 + 3 * 2` | `Int4` | `11` | `Good` |
| Parentheses | `(5 + 3) * 2` | `Int4` | `16` | `Good` |
| Exponent and modulo | `2 ^ 3 + 10 % 4` | `Int4` | `10` | `Good` |
| Equality and AND | `5 = 5 && 2 != 3` | `Boolean` | `true` | `Good` |
| NOT | `!(1 = 2)` | `Boolean` | `true` | `Good` |
| Bitwise AND | `5 & 3` | `Int4` | `1` | `Good` |
| Bitwise XOR | `5 xor 3` | `Int4` | `6` | `Good` |
| `if()` | `if(true, "Yes", "No")` | `String` | `Yes` | `Good` |
| `case()` | `case(1, 0, "Off", 1, "Running", 2, "Fault", "Unknown")` | `String` | `Running` | `Good` |
| `switch()` | `switch(1, 0, 1, 2, "Off", "Running", "Fault", "Unknown")` | `String` | `Running` | `Good` |
| `coalesce()` | `coalesce(null, null, "N/A")` | `String` | `N/A` | `Good` |
| Conversion failover | `try(toInt("boom"), -1)` | `Int4` | `-1` | `Good` |
| String to int rounding | `toInt("33.9", -1)` | `Int4` | `34` | `Good` |
| String to float | `toFloat("38.772", 0.0)` | `Float8` | `38.772` | `Good` |
| Boolean conversion | `toBoolean("yes", false)` | `Boolean` | `true` | `Good` |
| Percent formatting | `numberFormat(0.348, "#.00%")` | `String` | `34.80%` | `Good` |
| String cleanup | `upper(trim(" pump 1 "))` | `String` | `PUMP 1` | `Good` |
| Substring | `substring("hamburger", 4, 8)` | `String` | `urge` | `Good` |
| Bad substring failover | `try(substring("abc", 9), "N/A")` | `String` | `N/A` | `Good` |
| Date formatting | `dateFormat(toDate("2003-9-14 8:00:00"), "yyyy-MM-dd HH:mm:ss")` | `String` | `2003-09-14 08:00:00` | `Good` |
| Date arithmetic | `dateFormat(dateArithmetic(toDate("2010-01-04 8:00:00"), 5, "hour"), "yyyy-MM-dd HH:mm:ss")` | `String` | `2010-01-04 13:00:00` | `Good` |
| Date diff | `dateDiff(toDate("2010-01-04 8:00:00"), toDate("2010-01-04 8:15:30"), "minute")` | `Float8` | `15.5` | `Good` |
| Month extraction | `dateExtract(toDate("2009-1-15 8:00:00"), "month") + 1` | `Int4` | `1` | `Good` |
| Split dataset value | `split("a,b,c", ",")[1, "parts"]` | `String` | `b` | `Good` |
| Split length | `len(split("a,b,c", ","))` | `Int4` | `3` | `Good` |
| JSON path | `jsonGet("{\"item\":{\"firstThing\":1,\"secondThing\":2}}", "item.secondThing")` | `Int4` | `2` | `Good` |
| Bit read | `getBit(8, 3)` | `Int4` | `1` | `Good` |
| Binary encode | `binEnc(true, false, true)` | `Int4` | `5` | `Good` |

For `toFloat("38.772", 0.0)`, validate with tolerance rather than exact string equality.

## Tag Reference Matrix

| Focus | Expression | Data type | Initial expected | After write expected |
|---|---|---:|---:|---:|
| Relative sibling refs | `{[.]A} + {[.]B}` | `Float8` | `8.0` | `27.0` after `A=20`, `B=7` |
| Guarded divide | `if({[.]Den} = 0, -1.0, {[.]Num}/{[.]Den})` | `Float8` | `-1.0` | `2.5` after `Den=4` |
| Dynamic absolute tag | `toFloat(tag("[<provider>]_expression_skill_tests/<uniqueId>/A"), 0.0)` | `Float8` | `5.0` | `20.0` after `A=20` |
| Dynamic current provider root | `toFloat(tag("[~]_expression_skill_tests/<uniqueId>/A"), 0.0)` | `Float8` | `5.0` | `20.0` after `A=20` |
| Missing dynamic tag fallback | `toFloat(tag("[<provider>]_expression_skill_tests/<uniqueId>/NoSuchTag"), -999.0)` | `Float8` | `-999.0` | Same |
| Quality good | `isGood({[.]A})` | `Boolean` | `true` | `true` if `A` stays Good |
| Quality bad/error | `isBadOrError({[.]A})` | `Boolean` | `false` | `false` if `A` stays Good |
| Type check | `typeOf({[.]A})` | `String` | `Double` | `Double` |

The missing dynamic tag fallback can return a Good fallback. Use an additional existence/read check when missing tags must be treated as faults.

## Edge Case Matrix

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| `if()` skips bad false branch | `if(true, 1, 1/0)` | `Int4` | `1` | `Good` |
| `if()` skips bad true branch | `if(false, 1/0, 2)` | `Int4` | `2` | `Good` |
| `case()` selected branch before bad branch | `case(1, 1, 100, 2, 1/0, 0)` | `Int4` | `100` | `Good` |
| `try()` divide by zero | `try(1/0, -1.0)` | `Float8` | `null` | `Error_TypeConversion` |
| Null check | `isNull(null)` | `Boolean` | `true` | `Good` |
| Empty string check | `isNull("")` | `Boolean` | `false` | `Good` |
| Calendar year | `dateFormat(toDate("2020-12-31 12:00:00"), "yyyy-MM-dd")` | `String` | `2020-12-31` | `Good` |
| Week year | `dateFormat(toDate("2020-12-31 12:00:00"), "YYYY-MM-dd")` | `String` | `2021-12-31` | `Good` |
| Day of month | `dateFormat(toDate("2020-02-01 12:00:00"), "dd")` | `String` | `01` | `Good` |
| Day of year | `dateFormat(toDate("2020-02-01 12:00:00"), "DD")` | `String` | `32` | `Good` |
| Regex delimiter trap | `len(split("a.b.c", "."))` | `Int4` | `0` | `Good` |
| Escaped literal dot | `split("a.b.c", "\\.")[1, "parts"]` | `String` | `b` | `Good` |
| Empty split length | `len(split("", ","))` | `Int4` | `1` | `Good` |
| `toInt()` below half | `toInt(2.49, -1)` | `Int4` | `2` | `Good` |
| `toInt()` half up | `toInt(2.5, -1)` | `Int4` | `3` | `Good` |
| Float expression in Int tag | `10.0 / 4.0` | `Int4` | `3` | `Good` |

## Numeric Bounds And Coercion Matrix

Use Expression Tags and read value, quality, and value class when numeric boundaries matter.

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| `toInt()` positive below half | `toInt(2.49)` | `Int4` | `2` | `Good` |
| `toInt()` positive half | `toInt(2.5)` | `Int4` | `3` | `Good` |
| `toInt()` positive above half | `toInt(2.51)` | `Int4` | `3` | `Good` |
| `toInt()` negative below half | `toInt(-2.49)` | `Int4` | `-2` | `Good` |
| `toInt()` negative half | `toInt(-2.5)` | `Int4` | `-2` | `Good` |
| `toInt()` negative above half | `toInt(-2.51)` | `Int4` | `-3` | `Good` |
| `toLong()` positive half | `toLong(2.5)` | `Int8` | `3` | `Good` |
| `toLong()` negative half | `toLong(-2.5)` | `Int8` | `-2` | `Good` |
| Whitespace int string | `toInt(" 33 ", -1)` | `Int4` | `-1` | `Good` |
| Whitespace float string | `toFloat(" 12.5 ", -1.0)` | `Float8` | `-1.0` | `Good` |
| Non-whitespace int string | `toInt("33.5", -1)` | `Int4` | `34` | `Good` |
| Non-whitespace float string | `toFloat("12.5", -1.0)` | `Float8` | `12.5` | `Good` |
| `toInt()` below min string | `toInt("-2147483649", 0)` | `Int4` | `0` | `Good` |
| `toInt()` above max string | `toInt("2147483648", 0)` | `Int4` | `0` | `Good` |
| `toLong()` below min string | `toLong("-9223372036854775809", 0)` | `Int8` | `-9223372036854775808` | `Good` |
| `toLong()` above max string | `toLong("9223372036854775808", 0)` | `Int8` | `9223372036854775807` | `Good` |
| `Int1` min | `-128` | `Int1` | `-128` | `Good` |
| `Int1` below min | `-129` | `Int1` | null | `Error_TypeConversion` |
| `Int2` max | `32767` | `Int2` | `32767` | `Good` |
| `Int2` above max | `32768` | `Int2` | null | `Error_TypeConversion` |
| `Int4` max | `2147483647` | `Int4` | `2147483647` | `Good` |
| `Int4` above max | `2147483648` | `Int4` | null | `Error_TypeConversion` |
| `Int1` fractional half | `2.5` | `Int1` | `2` | `Good` |
| `Int2` fractional above half | `2.51` | `Int2` | `2` | `Good` |
| `Int4` fractional half | `2.5` | `Int4` | `3` | `Good` |
| `Int8` fractional negative above half | `-2.51` | `Int8` | `-3` | `Good` |
| Hex literal as `Int1` | `0xFF` | `Int1` | null | `Error_TypeConversion` |
| Hex literal as `Int4` | `0xFF` | `Int4` | `255` | `Good` |
| Scientific literal as int | `1.3e5` | `Int4` | `130000` | `Good` |
| Negative zero text | `-0.0` | `Float8` | `-0.0` text | `Good` |
| Positive infinity into float | `1.0 / 0.0` | `Float8` | null | `Error_TypeConversion` |
| NaN into float | `0.0 / 0.0` | `Float8` | null | `Error_TypeConversion` |
| NaN into int | `0.0 / 0.0` | `Int4` | `0` | `Good` |
| `Float4` precision | `1.234567890123` | `Float4` | about `1.2345678806304932` | `Good` |
| `Float8` precision | `1.234567890123` | `Float8` | about `1.234567890123` | `Good` |
| `Float4` overflow candidate | `3.5e38` | `Float4` | null | `Error_TypeConversion` |
| `Float8` overflow candidate | `1.0e309` | `Float8` | null | `Error_TypeConversion` |
| `Float8` around `2^53 + 1` | `9007199254740993` | `Float8` | `9007199254740992.0` | `Good` |
| `Int8` around `2^53 + 1` | `toLong("9007199254740993", -1)` | `Int8` | `9007199254740993` | `Good` |
| String plus number | `"2" + 3` | `String` | `23` | `Good` |
| Number plus string coerced to float | `3 + "2"` | `Float8` | `32.0` | `Good` |

## DST And Timezone Matrix

Use Gateway-scope Expression Tags and record the actual Gateway timezone before relying on these rows. These rows were validated with a Gateway default timezone of `America/Chicago`; validate Perspective session timezone behavior separately.

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| Winter offset | `dateFormat(toDate("2024-01-15 12:00:00"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-01-15 12:00:00.000 -0600 CST` | `Good` |
| Summer offset | `dateFormat(toDate("2024-07-15 12:00:00"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-07-15 12:00:00.000 -0500 CDT` | `Good` |
| Spring gap parse | `dateFormat(toDate("2024-03-10 02:30:00"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-03-10 03:30:00.000 -0500 CDT` | `Good` |
| Spring add one hour | `dateFormat(dateArithmetic(toDate("2024-03-10 01:30:00"), 1, "hour"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-03-10 03:30:00.000 -0500 CDT` | `Good` |
| Spring elapsed gap hours | `dateDiff(toDate("2024-03-10 01:30:00"), toDate("2024-03-10 03:30:00"), "hour")` | `Float8` | `1.0` | `Good` |
| Spring day elapsed hours | `dateDiff(toDate("2024-03-10 00:00:00"), toDate("2024-03-11 00:00:00"), "hour")` | `Float8` | `23.0` | `Good` |
| Spring add 24 hours | `dateFormat(dateArithmetic(toDate("2024-03-09 12:00:00"), 24, "hour"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-03-10 13:00:00.000 -0500 CDT` | `Good` |
| Spring add one day | `dateFormat(dateArithmetic(toDate("2024-03-09 12:00:00"), 1, "day"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-03-10 12:00:00.000 -0500 CDT` | `Good` |
| Fall ambiguous parse | `dateFormat(toDate("2024-11-03 01:30:00"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-11-03 01:30:00.000 -0600 CST` | `Good` |
| Fall add one hour | `dateFormat(dateArithmetic(toDate("2024-11-03 00:30:00"), 1, "hour"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-11-03 01:30:00.000 -0500 CDT` | `Good` |
| Fall add two hours | `dateFormat(dateArithmetic(toDate("2024-11-03 00:30:00"), 2, "hour"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-11-03 01:30:00.000 -0600 CST` | `Good` |
| Fall repeated elapsed hours | `dateDiff(toDate("2024-11-03 00:30:00"), toDate("2024-11-03 02:30:00"), "hour")` | `Float8` | `3.0` | `Good` |
| Fall day elapsed hours | `dateDiff(toDate("2024-11-03 00:00:00"), toDate("2024-11-04 00:00:00"), "hour")` | `Float8` | `25.0` | `Good` |
| Fall add 24 hours | `dateFormat(dateArithmetic(toDate("2024-11-02 12:00:00"), 24, "hour"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-11-03 11:00:00.000 -0600 CST` | `Good` |
| Fall add one day | `dateFormat(dateArithmetic(toDate("2024-11-02 12:00:00"), 1, "day"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-11-03 12:00:00.000 -0600 CST` | `Good` |
| Leap plus one day | `dateFormat(dateArithmetic(toDate("2024-02-28 00:00:00"), 1, "day"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-02-29 00:00:00.000 -0600 CST` | `Good` |
| Leap plus one year | `dateFormat(dateArithmetic(toDate("2024-02-29 00:00:00"), 1, "year"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2025-02-28 00:00:00.000 -0600 CST` | `Good` |
| Non-leap month end | `dateFormat(dateArithmetic(toDate("2021-01-31 00:00:00"), 1, "month"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2021-02-28 00:00:00.000 -0600 CST` | `Good` |
| Leap-year month end | `dateFormat(dateArithmetic(toDate("2024-01-31 00:00:00"), 1, "month"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-02-29 00:00:00.000 -0600 CST` | `Good` |
| Year end | `dateFormat(dateArithmetic(toDate("2024-12-31 00:00:00"), 1, "day"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2025-01-01 00:00:00.000 -0600 CST` | `Good` |
| Millisecond parse | `dateFormat(toDate("2024-03-10 01:59:59.123"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-03-10 01:59:59.123 -0600 CST` | `Good` |
| Millisecond round trip | `dateFormat(fromMillis(toMillis(toDate("2024-03-10 01:59:59.123"))), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | `2024-03-10 01:59:59.123 -0600 CST` | `Good` |
| Millisecond diff unit | `dateDiff(toDate("2024-03-10 01:59:59.123"), toDate("2024-03-10 01:59:59.456"), "millisecond")` | `Float8` | null | `Error_ExpressionEval` |
| Millisecond arithmetic unit | `dateFormat(dateArithmetic(toDate("2024-03-10 01:59:59.999"), 1, "millisecond"), "yyyy-MM-dd HH:mm:ss.SSS Z z")` | `String` | null | `Error_ExpressionEval` |

## Advanced Behavior Matrix

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| Boolean AND short-circuit | `false && (1/0 > 0)` | `Boolean` | `false` | `Good` |
| Boolean OR short-circuit | `true || (1/0 > 0)` | `Boolean` | `true` | `Good` |
| Empty string coalesce | `coalesce("", "fallback")` | `String` | empty string | `Good` |
| Null then empty string coalesce | `coalesce(null, "", "fallback")` | `String` | empty string | `Good` |
| String length | `len("pump")` | `Int4` | `4` | `Good` |
| First substring index | `indexOf("banana", "na")` | `Int4` | `2` | `Good` |
| Last substring index | `lastIndexOf("banana", "na")` | `Int4` | `4` | `Good` |
| Replace occurrences | `replace("banana", "na", "NA")` | `String` | `baNANA` | `Good` |
| Floor and ceil | `floor(2.9) + ceil(2.1)` | `Int4` | `5` | `Good` |
| Square root | `sqrt(81)` | `Int4` | `9` | `Good` |
| Min and max | `min(5, 3) + max(5, 3)` | `Int4` | `8` | `Good` |
| Round half | `round(2.5)` | `Int4` | `3` | `Good` |
| Thousands number format | `numberFormat(1234.567, "#,##0.00")` | `String` | `1,234.57` | `Good` |
| Zero-pad number format | `numberFormat(12.3, "000.00")` | `String` | `012.30` | `Good` |
| Month-end date arithmetic | `dateFormat(dateArithmetic(toDate("2020-01-31 00:00:00"), 1, "month"), "yyyy-MM-dd")` | `String` | `2020-02-29` | `Good` |
| Date diff hours | `dateDiff(toDate("2020-01-01 00:00:00"), toDate("2020-01-02 12:00:00"), "hour")` | `Float8` | `36.0` | `Good` |

## Null Tag Matrix

Add a nullable memory tag named `MaybeNull` with a null value.

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| Null literal coerced to tag | `null` | `Float8` | `null` | `Good` |
| Sibling null check | `isNull({[.]MaybeNull})` | `Boolean` | `true` | `Good` |
| Sibling null equality | `{[.]MaybeNull} = null` | `Boolean` | `true` | `Good` |
| Null fallback | `coalesce({[.]MaybeNull}, 7.5)` | `Float8` | `7.5` | `Good` |
| Null arithmetic fault | `{[.]MaybeNull} + 5` | `Float8` | `null` | expression error |

## Dynamic Retarget Matrix

Add memory tags named `A`, `B`, and `SelectedName`, then configure these expression tags:

| Focus | Expression | Data type | Initial expected | After change expected |
|---|---|---:|---:|---:|
| Dynamic selected tag | `toFloat(tag("[~]_expression_skill_tests/<uniqueId>/" + {[.]SelectedName}), -1.0)` | `Float8` | `A` value when `SelectedName` is `A` | `B` value after `SelectedName` changes to `B` |
| Dynamic selected tag absolute | `toFloat(tag("[<provider>]_expression_skill_tests/<uniqueId>/" + {[.]SelectedName}), -1.0)` | `Float8` | `A` value when `SelectedName` is `A` | Updated selected tag value after selector or target value changes |
| Resolved path echo | `"[<provider>]_expression_skill_tests/<uniqueId>/" + {[.]SelectedName}` | `String` | Path ending in `/A` | Path ending in the changed selector |
| Nested status | `case({[.]State}, 0, "Stopped", 1, "Running " + numberFormat({[.]A}, "0.0"), 2, if({[.]A} > 50, "High", "Normal"), "Unknown")` | `String` | Depends on `State` and `A` | `High` when `State=2` and `A>50` |
| Missing selected tag fallback | `toFloat(tag("[~]_expression_skill_tests/<uniqueId>/" + {[.]SelectedName}), -1.0)` | `Float8` | selected tag value | `-1.0` Good if the selected path does not exist |

The missing selected tag fallback should be paired with a path echo, existence check, or readback check if a missing target must be treated as a fault.

## Circular Reference Recovery Matrix

Use this matrix when reviewing or repairing expression cycles. Read value and quality together at every phase. Keep the fixture small and use a known Good memory source named `Base`.

Suggested setup:

| Name | Type | Initial value or expression | Purpose |
|---|---:|---|---|
| `Base` | `Float8` memory | `10.0` | Known Good recovery source |
| `Path` | `String` memory | Full path to `DynamicCycle` | Dynamic path loop selector |
| `SelfCycle` | `Float8` Expression Tag | `{[.]SelfCycle} + 1` | Direct self-reference |
| `A` | `Float8` Expression Tag | `{[.]B} + 1` | Mutual-reference member |
| `B` | `Float8` Expression Tag | `{[.]A} + 1` | Mutual-reference dependent |
| `DynamicCycle` | `Float8` Expression Tag | `tag({[.]Path})` | Dynamic path loop |
| `DerivedSelf` | `Float8` Derived Tag | source is `DerivedSelf`, read `{source} + 1` | Derived self-reference |
| `DerivedA` | `Float8` Derived Tag | source is `DerivedB`, read `{source} + 1` | Derived mutual-reference member |
| `DerivedB` | `Float8` Derived Tag | source is `DerivedA`, read `{source} + 1` | Derived mutual-reference dependent |

Expected review phases:

| Phase | Action | Expected review |
|---|---|---|
| Initial cycle read | Read all cycle tags | Direct self, mutual Expression Tags, and Derived cycles can read null with expression error quality; the dynamic path loop can read an uncertain initial value rather than a Good calculated value |
| Break Expression Tag cycles | Change `SelfCycle` and `A` to `{[.]Base} + 1` | `SelfCycle` and `A` read `11.0` Good; `B` reads `12.0` Good |
| Retarget dynamic path | Change `Path` to the full path of `Base` | `DynamicCycle` reads `10.0` Good |
| Retarget Derived Tags | Change `DerivedSelf` and `DerivedA` source paths to `Base`, and `DerivedB` source path to `DerivedA` | `DerivedSelf` and `DerivedA` read `11.0` Good; `DerivedB` reads `12.0` Good |
| Source value change | Write `20.0` to `Base` | Repaired plus-one tags read `21.0` Good; repaired second-chain tags read `22.0` Good |
| Delete one repaired member | Delete `A` | `A` reads `Bad_NotFound`; dependent `B` reads null with expression error quality |
| Recreate repaired member | Recreate `A` as `{[.]Base} + 1` | `A` and `B` recover to Good values |

For UDTs, repeat with an actual UDT instance before relying on type-level inspection. A UDT instance with self-reference, mutual-reference, and dynamic path parameter loop shapes can be repaired by changing the type expressions and retargeting the path parameter to a known Good source; verify the instance member values and qualities after the repair.

Validate Gateway restart recovery, nested UDT cycles, Transaction Group Expression Items, Perspective bindings, and Vision bindings separately before relying on this matrix for those surfaces.

## Tag-Side Cross-Surface Differential Matrix

Use this matrix only for tag-side surface comparisons: Expression Tags, UDT expression members, and Derived Tag read expressions. Validate Perspective and Vision surfaces separately.

Suggested setup:

| Surface | Fixture | Expression shape |
|---|---|---|
| Expression Tag | sibling memory source `Source` | `{[.]Source} + 7` |
| Derived Tag read expression | `sourceTagPath` points to `Source` | `{source} + 7` |
| UDT expression member | UDT memory member `UdtSource` | `{[.]UdtSource} + 7` |
| Expression Tag JSON read | sibling JSON string tag `Json` | `toFloat(jsonGet({[.]Json}, "settings.setpoint"), -999.0)` |
| Derived Tag JSON read | `sourceTagPath` points to `Json` | `toFloat(jsonGet({source}, "settings.setpoint"), -999.0)` |
| UDT JSON member | UDT JSON string member `UdtJson` | `toFloat(jsonGet({[.]UdtJson}, "settings.setpoint"), -999.0)` |
| Bad-quality propagation | Bad-quality numeric source | source-plus-one expression per surface |

Expected review phases:

| Phase | Action | Expected review |
|---|---|---|
| Initial read | Read value, Java class, quality, and timestamp for all three tag-side surfaces | Numeric plus-seven rows read `12.0` Good; JSON setpoint rows read `42.5` Good; Bad-quality rows show the numeric value with Bad quality |
| Source change | Change numeric sources from `5.0` to `8.5` and JSON setpoints from `42.5` to `77.25` | Numeric rows update to `15.5` Good; JSON rows update to `77.25` Good on all three tag-side surfaces |
| Writeback contrast | Write a new value to matching Derived, Expression Tag, and UDT expression member outputs | Derived Tags with write expressions can write back to writable sources; direct writes to Expression Tags and UDT expression members should be reviewed for read-only rejection |

Do not treat this matrix as Perspective or Vision coverage. Perspective expression binding, expression transform, Tag Binding Expression mode, Vision expression binding, project-library scope, and client/session scope each need their own surface validation.

## Timestamp And Stale-Data Matrix

Add memory tags named `PV`, `PVAlt`, `PVPath`, and `QMode`. Initialize `PVPath` to the full path of `PV`, then retarget it to `PVAlt` during the dynamic-path phase.

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| Direct source timestamp | `timestampOf({[.]PV})` | `DateTime` | Matches the source tag timestamp while `PV` exists |
| Dynamic source timestamp | `timestampOf(tag({[.]PVPath}))` | `DateTime` | Matches the selected source timestamp while the selected path exists |
| Direct timestamp property | `{[.]PV.timestamp}` | `DateTime` | Matches the source tag timestamp while `PV` exists |
| Direct age | `dateDiff(timestampOf({[.]PV}), now(1000), "second")` | `Float8` | Increases while the source timestamp does not change |
| Dynamic age | `dateDiff(timestampOf(tag({[.]PVPath})), now(1000), "second")` | `Float8` | Tracks the selected source path and increases while that source does not change |
| Guarded stale flag | `if(isGood({[.]PV}), dateDiff(timestampOf({[.]PV}), now(1000), "second") > 10, true)` | `Boolean` | Treats non-Good source quality as stale/faulted instead of relying on age alone |
| Quality-only timestamp fixture | `timestampOf(if({[.]QMode} = "Bad", qualifiedValue({[.]PV}, "Bad"), qualifiedValue({[.]PV}, "Good")))` | `DateTime` | Can update when quality changes even if the numeric value is unchanged |

Test phases:

| Phase | Action | Expected review |
|---|---|---|
| Initial | Read source, direct timestamp, dynamic timestamp, and `.timestamp` property | Timestamp values match source timestamps while sources are Good |
| Different-value write | Write a new value to `PV` | Source timestamp and timestamp expressions update |
| Same-value write | Write the same value to `PV` | On the memory-tag shape covered by this matrix, timestamp did not move; verify the target before relying on this |
| Quality-only change | Toggle a qualified-value fixture between Good and Bad | Timestamp can change when quality changes |
| Disable/re-enable | Disable and re-enable `PV` if safe | Read value and quality together; disabled source quality matters |
| Delete/recreate | Delete and recreate `PV` inside the disposable folder | `timestampOf(...)` can return a fresh Good timestamp for missing static/dynamic sources, so age alone is not a not-found detector |
| Dynamic retarget | Change `PVPath` from `PV` to `PVAlt` | Dynamic timestamp follows the newly selected source |
| Dynamic outage/recovery | Delete and recreate the selected dynamic source | Missing-source quality must be checked separately from age |
| Fixed-rate/no source change | Read fixed-rate and `now(1000)` expressions before and after a delay | `now(...)`/age can advance while source timestamps stay unchanged |

## JSON And Quality Matrix

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| JSON array root index | `jsonGet("[10,20,30]", "[1]")` | `Int4` | `20` | `Good` |
| JSON object array scalar | `jsonGet("{\"items\":[10,20]}", "items[1]")` | `Int4` | `20` | `Good` |
| JSON object array field | `jsonGet("{\"items\":[{\"v\":5},{\"v\":7}]}", "items[1].v")` | `Int4` | `7` | `Good` |
| Malformed dot-number JSON path | `jsonGet("{\"items\":[{\"v\":5},{\"v\":7}]}", "items.1.v")` | `Int4` | `null` | expression error |
| Malformed path fallback | `try(jsonGet("{\"items\":[{\"v\":5},{\"v\":7}]}", "items.1.v"), -1)` | `Int4` | `-1` | `Good` |
| Missing JSON path fallback | `try(jsonGet("{\"a\":1}", "b"), -1)` | `Int4` | `-1` | `Good` |
| Qualified Good | `qualifiedValue(123, "Good")` | `Float8` | `123.0` | `Good` |
| Qualified Uncertain | `qualifiedValue(123, "Uncertain")` | `Float8` | `123.0` | `Uncertain` |
| Qualified Bad | `qualifiedValue(123, "Bad")` | `Float8` | `123.0` | `Bad` |
| Qualified Error | `qualifiedValue(123, "Error")` | `Float8` | `123.0` | `Error` |
| Qualified Bad diagnostic | `qualifiedValue(123, "Bad", 515, "Disabled by test")` | `Float8` | `123.0` | `Bad_Disabled` |
| Check qualified Uncertain | `isUncertain(qualifiedValue(123, "Uncertain"))` | `Boolean` | `true` | `Good` |
| Quality label qualified Bad | `qualityOf(qualifiedValue(123, "Bad"))` | `String` | Bad quality label | `Good` |
| Legacy force bad quality | `forceQuality(123, 0)` | `Int4` | `123` | `Bad` |
| Legacy force good quality | `forceQuality(123, 192)` | `Int4` | `123` | `Good` |

## Quality Propagation Matrix

Assume `BadPV` is an Expression Tag with `qualifiedValue(123.0, "Bad")` or `forceQuality(123.0, 0)`, and `GoodPV` is a Good-quality numeric tag with value `10.0`.

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| Forced bad source | `forceQuality(123.0, 0)` | `Float8` | `123.0` | `Bad` |
| Forced good source | `forceQuality(123.0, 192)` | `Float8` | `123.0` | `Good` |
| `isGood` bad source | `isGood({[.]BadPV})` | `Boolean` | `false` | `Good` |
| `isBadOrError` bad source | `isBadOrError({[.]BadPV})` | `Boolean` | `true` | `Good` |
| `isBad` bad source | `isBad({[.]BadPV})` | `Boolean` | `true` | `Good` |
| `isError` plain bad source | `isError({[.]BadPV})` | `Boolean` | `false` | `Good` |
| `qualityOf` bad source | `qualityOf({[.]BadPV})` | `String` | `Bad` | `Good` |
| Arithmetic preserves bad quality | `{[.]BadPV} + 1.0` | `Float8` | `124.0` | `Bad` |
| `try()` does not fail over on bad quality alone | `try({[.]BadPV} + 1.0, -1.0)` | `Float8` | `124.0` | `Bad` |
| `coalesce()` does not fail over on bad quality alone | `coalesce({[.]BadPV}, -1.0)` | `Float8` | `123.0` | `Bad` |
| Guarded fallback | `if(isGood({[.]BadPV}), {[.]BadPV}, -1.0)` | `Float8` | `-1.0` | `Good` |
| Error-quality fallback | `try(qualifiedValue(123.0, "Error"), -1.0)` | `Float8` | `-1.0` | `Good` |
| Selected bad branch | `if(true, {[.]BadPV}, -1.0)` | `Float8` | `123.0` | `Bad` |
| Unselected bad true branch | `if(false, {[.]BadPV}, 5.0)` | `Float8` | `5.0` | `Good` |
| Unselected bad false branch | `if(true, 5.0, {[.]BadPV})` | `Float8` | `5.0` | `Good` |
| Force bad wrapper | `forceQuality({[.]GoodPV} + 1.0, 0)` | `Float8` | `11.0` | `Bad` |
| Quality label wrapper | `qualityOf({[.]ForcedBadWrapper})` | `String` | `Bad` | `Good` |

## DataSet Lookup Matrix

Assume `LookupTable` is a DataSet tag with columns `Name`, `PV`, `Status`, `Enabled`, and `Priority`, including rows for `PumpA`, `PumpB`, and `PumpC`. Include a duplicate `PumpB` row when validating duplicate-key behavior.

| Focus | Expression | Data type | Expected value | Expected quality |
|---|---|---:|---:|---|
| Lookup by column names | `lookup({[.]LookupTable}, "PumpC", "NO_MATCH", "Name", "Status")` | `String` | `ALARM` | `Good` |
| Lookup numeric result | `lookup({[.]LookupTable}, "PumpC", -1.0, "Name", "PV")` | `Float8` | `101.25` | `Good` |
| Lookup by column indexes | `lookup({[.]LookupTable}, "PumpC", "NO_MATCH", 0, 2)` | `String` | `ALARM` | `Good` |
| Default lookup/result columns | `lookup({[.]LookupTable}, "PumpC", "NO_MATCH")` | `String` | `101.25` | `Good` |
| Missing lookup key | `lookup({[.]LookupTable}, "NoSuchPump", "NO_MATCH", "Name", "Status")` | `String` | `NO_MATCH` | `Good` |
| String-key case sensitivity | `lookup({[.]LookupTable}, "pumpc", "NO_MATCH", "Name", "Status")` | `String` | `NO_MATCH` | `Good` |
| Boolean result | `lookup({[.]LookupTable}, "PumpC", false, "Name", "Enabled")` | `Boolean` | `true` | `Good` |
| Integer result | `lookup({[.]LookupTable}, "PumpC", -1, "Name", "Priority")` | `Int4` | `3` | `Good` |
| Duplicate key ordering | `lookup({[.]LookupTable}, "PumpB", "NO_MATCH", "Name", "Status")` | `String` | first matching row's status | `Good` |
| Numeric result coerced to string fallback type | `lookup({[.]LookupTable}, "PumpC", "NO_MATCH", "Name", "PV")` | `String` | `101.25` | `Good` |
| Dynamic DataSet path string | `lookup(tag({[.]TablePath}), "PumpC", "NO_MATCH", "Name", "Status")` | `String` | selected table's status | `Good` |
| Dynamic DataSet numeric | `lookup(tag({[.]TablePath}), "PumpC", -1.0, "Name", "PV")` | `Float8` | selected table's PV | `Good` |
| Missing dynamic DataSet path | `lookup(tag({[.]MissingTablePath}), "PumpC", "NO_TABLE", "Name", "Status")` | `String` | `null` | `Uncertain` |
| Missing dynamic lookup wrapped in `try()` | `try(lookup(tag({[.]MissingTablePath}), "PumpC", "NO_TABLE", "Name", "Status"), "TRY_FAIL")` | `String` | `null` | `Uncertain` |
| Bad result column wrapped in `try()` | `try(lookup({[.]LookupTable}, "PumpC", "BAD_COL", "Name", "NoSuchColumn"), "TRY_FAIL")` | `String` | `TRY_FAIL` | `Good` |
| Dynamic path retarget | same dynamic lookup after `TablePath` changes to another DataSet tag | mixed | values from the new table | `Good` |
| Dynamic target rewrite | same dynamic lookup after the selected DataSet tag is rewritten | mixed | updated values from the selected table | `Good` |

## DataSet Transform And Aggregate Matrix

Assume `TransformTable` is a DataSet tag with columns `Name`, `PV`, `Status`, `Priority`, and `Batch`, in this row order: `PumpB`/`5.5`/`WARN`/`2`/`B`, `PumpA`/`10.0`/`OK`/`1`/`A`, `PumpC`/`null`/`ALARM`/`2`/`C`, and `PumpD`/`2.25`/`OK`/`3`/`D`. Also include `EmptyTable`, `SingleTable`, `NullTable`, `AltTable`, and a writable string tag `TablePath` that can point at either `TransformTable` or `AltTable`.

| Focus | Expression | Data type | Expected value or behavior | Expected quality |
|---|---|---:|---|---|
| Sort by priority ascending | `sortDataset({[.]TransformTable}, "Priority", true)[0, "Name"]` | `String` | `PumpA` | `Good` |
| Sort ascending duplicate-key order | `sortDataset({[.]TransformTable}, "Priority", true)[1, "Name"]` and row `2` | `String` | Duplicate priority rows read `PumpB`, then `PumpC` | `Good` |
| Sort by priority descending | `sortDataset({[.]TransformTable}, "Priority", false)[0, "Name"]` | `String` | `PumpD` | `Good` |
| Sort descending duplicate-key order | `sortDataset({[.]TransformTable}, "Priority", false)[1, "Name"]` and row `2` | `String` | Duplicate priority rows read `PumpB`, then `PumpC` | `Good` |
| Numeric ascending null position | `sortDataset({[.]TransformTable}, "PV", true)[3, "Name"]` | `String` | `PumpC` | `Good` |
| Numeric descending null position | `sortDataset({[.]TransformTable}, "PV", false)[0, "Name"]` | `String` | `PumpC` | `Good` |
| Rename columns | `columnRename({[.]TransformTable}, "Asset", "Value", "State", "Priority", "Batch")[0, "Value"]` | `Float8` | `5.5` | `Good` |
| Old name after rename | `try(columnRename({[.]TransformTable}, "Asset", "Value", "State", "Priority", "Batch")[0, "PV"], "__OLD_MISSING__")` | `String` | `__OLD_MISSING__` | `Good` |
| Rearrange selected columns | `columnRearrange({[.]TransformTable}, "Status", "Name", "PV")[0, "Status"]` | `String` | `WARN` | `Good` |
| Rearranged row count | `len(columnRearrange({[.]TransformTable}, "Status", "Name", "PV"))` | `Int4` | `4` | `Good` |
| Sum numeric column | `sum({[.]TransformTable}, "PV")` | `Float8` | `17.75` | `Good` |
| Mean numeric column | `mean({[.]TransformTable}, "PV")` | `Float8` | `5.916666666666667` | `Good` |
| Median numeric column | `median({[.]TransformTable}, "PV")` | `Float8` | `5.5` | `Good` |
| Population std dev | `stdDev({[.]TransformTable}, "PV")` | `Float8` | about `3.1776126608` | `Good` |
| Min and max | `min({[.]TransformTable}, "PV")` / `max({[.]TransformTable}, "PV")` | `Float8` | `2.25` / `10.0` | `Good` |
| Concatenate names | `groupConcat({[.]TransformTable}, "Name", "|")` | `String` | `PumpB|PumpA|PumpC|PumpD` | `Good` |
| Empty table sort length | `len(sortDataset({[.]EmptyTable}, "Priority", true))` | `Int4` | `0` | `Good` |
| Empty table numeric aggregate | `isNull(sum({[.]EmptyTable}, "PV"))` and `isNull(mean({[.]EmptyTable}, "PV"))` | `Boolean` | `true` | `Good` |
| Empty table concat | `groupConcat({[.]EmptyTable}, "Name", "|")` | `String` | empty string | `Good` |
| Single-row std dev | `stdDev({[.]SingleTable}, "PV")` | `Float8` | `0.0` | `Good` |
| All-null numeric aggregate | `isNull(sum({[.]NullTable}, "PV"))` and `isNull(mean({[.]NullTable}, "PV"))` | `Boolean` | `true` | `Good` |
| Missing sort column fallback | `try(sortDataset({[.]TransformTable}, "NoSuchColumn", true)[0, "Name"], "__MISSING_COL__")` | `String` | `__MISSING_COL__` | `Good` |
| Aggregate after rename | `sum(columnRename({[.]TransformTable}, "Asset", "Value", "State", "Priority", "Batch"), "Value")` | `Float8` | `17.75` | `Good` |
| Transform-to-aggregate formatting | `numberFormat(sum(sortDataset({[.]TransformTable}, "Priority", true), "PV"), "0.00")` | `String` | `17.75` | `Good` |
| Bad-quality sorted value | `sortDataset(qualifiedValue({[.]TransformTable}, "Bad"), "Priority", true)[0, "Name"]` | `String` | `PumpA` with Bad quality | `Bad` |
| Bad-quality aggregate value | `sum(qualifiedValue({[.]TransformTable}, "Bad"), "PV")` | `Float8` | `17.75` with Bad quality | `Bad` |
| Dynamic sorted table | `sortDataset(tag({[.]TablePath}), "Priority", true)[0, "Name"]` | `String` | Follows the selected table path | `Good` |
| Dynamic aggregate | `sum(tag({[.]TablePath}), "PV")` | `Float8` | Follows the selected table path and table rewrites | `Good` |
| Dynamic formatted aggregate | `numberFormat(sum(sortDataset(tag({[.]TablePath}), "Priority", true), "PV"), "0.00")` | `String` | Recalculates after retargeting or rewriting the selected table | `Good` |

## Structured Value Representation Matrix

Use this matrix when an expression must read structured values rather than simple scalar tags. Configure separate source tags for a JSON string, a Document memory tag, numeric and string arrays, and a DataSet memory tag. Read both value and quality for every expression.

Suggested source tags:

| Name | Type | Example value | Purpose |
|---|---:|---|---|
| `JsonText` | `String` | `{"items":[{"name":"alpha","pv":12.5,"enabled":true,"note":null},{"name":"beta","pv":7.25,"enabled":false,"note":"ok"}],"settings":{"setpoint":42,"mode":"auto","emptyArray":[],"emptyObject":{}}}` | JSON string path access |
| `Doc` | `Document` | Same logical object as `JsonText` | Direct Document indexing |
| `FloatArray` | `Float8Array` | `[1.25, 2.5, 3.75]` | Numeric array indexing |
| `StringArray` | `StringArray` | `["alpha", "beta", ""]` | String array indexing and empty string |
| `FloatArrayFromJson` | `Float8Array` | Write `"[3.14, 2.72]"` when validating JSON-array-string coercion | Array write coercion |
| `Table` | `DataSet` | Columns `Name`, `PV`, `Enabled`, `Note` | Row/column access |
| `Index` | `Int4` | `1` | Dynamic index |
| `IndexText` | `String` | `"1"` | Dynamic JSON path index |
| `RowIndex` | `Int4` | `1` | Dynamic DataSet row |
| `ColName` | `String` | `PV` | Dynamic DataSet column |
| `TablePath` | `String` | Full path to `Table` | Dynamic DataSet path |
| `MissingPath` | `String` | Full path to a missing tag | Missing dynamic source behavior |

JSON string expressions:

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| Object array field | `jsonGet({[.]JsonText}, "items[0].name")` | `String` | Reads the field value Good |
| Numeric JSON value | `jsonGet({[.]JsonText}, "items[1].pv")` | `Float8` | Reads the numeric value Good |
| Boolean JSON value | `jsonGet({[.]JsonText}, "items[0].enabled")` | `Boolean` | Reads the boolean value Good |
| JSON null to string | `jsonGet({[.]JsonText}, "items[0].note")` | `String` | Can read as text `null`; validate other output types before assuming null propagation |
| Missing JSON fallback | `try(jsonGet({[.]JsonText}, "items[99].name"), "__MISSING__")` | `String` | Returns the fallback Good |
| Dynamic JSON path | `jsonGet({[.]JsonText}, "items[" + {[.]IndexText} + "].name")` | `String` | Follows the index text when it changes |
| Returned JSON copy | `jsonSet({[.]JsonText}, "settings.setpoint", 55)` | `String` | Returns a modified JSON string; does not write the source tag by itself |
| JSON numeric type | `typeOf(jsonGet({[.]JsonText}, "items[1].pv"))` | `String` | Returns the observed numeric type label, such as `Double` |

Document expressions:

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| Document object array field | `{[.]Doc}["items"][0]["name"]` | `String` | Reads the field value Good |
| Document numeric field | `{[.]Doc}["items"][1]["pv"]` | `Float8` | Reads the numeric value Good |
| Document nested object field | `{[.]Doc}["settings"]["setpoint"]` | `Float8` | Reads the nested value Good |
| Present null check | `isNull({[.]Doc}["items"][0]["note"])` | `Boolean` | Returns true for a present null |
| Missing Document fallback | `try({[.]Doc}["items"][99]["name"], "__MISSING__")` | `String` | Returns the fallback Good |
| Dynamic Document index | `{[.]Doc}["items"][{[.]Index}]["name"]` | `String` | Follows the numeric index when it changes |
| Document type label | `typeOf({[.]Doc})` | `String` | Returns the target's Document type label |
| Document list length | `len({[.]Doc}["items"])` | `Int4` | Returns the list length |

Array expressions:

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| Float array length | `len({[.]FloatArray})` | `Int4` | Returns the array length |
| Float array fixed index | `{[.]FloatArray}[1]` | `Float8` | Reads the selected element Good |
| Float array dynamic index | `{[.]FloatArray}[{[.]Index}]` | `Float8` | Follows the numeric index when it changes |
| Float array missing index | `try({[.]FloatArray}[99], -999.0)` | `Float8` | Returns the fallback Good |
| String array index | `{[.]StringArray}[1]` | `String` | Reads the selected string element Good |
| Empty string array element | `{[.]StringArray}[2]` | `String` | Reads an empty string Good when the element is empty |
| JSON-array-string write length | `len({[.]FloatArrayFromJson})` | `Int4` | Returns `2` after the JSON-array-string write is accepted |
| JSON-array-string write value | `{[.]FloatArrayFromJson}[1]` | `Float8` | Reads `2.72` after the JSON-array-string write is accepted |

DataSet and quality expressions:

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| DataSet row count | `len({[.]Table})` | `Int4` | Returns the DataSet row count |
| Fixed DataSet string cell | `{[.]Table}[1, "Name"]` | `String` | Reads the selected string cell Good |
| Dynamic DataSet cell | `{[.]Table}[{[.]RowIndex}, {[.]ColName}]` | `Float8` | Reads the selected numeric cell Good when the output type matches the selected value |
| Dynamic DataSet type mismatch | same expression after `ColName` selects a text column into a numeric tag | `Float8` | Can read null with type-conversion error quality |
| Missing DataSet row fallback | `try({[.]Table}[99, "Name"], "__MISSING__")` | `String` | Returns the fallback Good |
| Missing DataSet column fallback | `try({[.]Table}[0, "Missing"], "__MISSING__")` | `String` | Returns the fallback Good |
| Dynamic DataSet path | `tag({[.]TablePath})[{[.]RowIndex}, {[.]ColName}]` | `Float8` | Reads the selected table while the path exists |
| Missing dynamic DataSet path | `try(tag({[.]MissingPath})[0, "PV"], -999.0)` | `Float8` | Can read null with `Bad_NotFound` instead of returning the fallback |
| Missing dynamic quality diagnostic | `qualityOf(tag({[.]MissingPath}))` | `String` | Can return the missing-path quality label as a Good diagnostic string |
| Bad Document indexing | `try(qualifiedValue({[.]Doc}, "Bad")["items"][0]["name"], "__BAD__")` | `String` | Can return the selected value while preserving Bad quality |
| Bad DataSet indexing | `try(qualifiedValue({[.]Table}, "Bad")[0, "PV"], -999.0)` | `Float8` | Can return the selected value while preserving Bad quality |

## Alarm Rollup Matrix

Create a disposable folder with at least two areas and three memory tags that have real alarms: one Low, one High, and one Critical. Use explicit display paths and read value plus quality for every expression. Keep acknowledgement and shelving actions outside expressions and use only target-approved tooling to drive those states.

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| Wildcard active state | `isAlarmActive("[<provider>]AreaA/*")` | `Boolean` | False Good when matching alarms are clear; true Good when at least one matching alarm is active |
| Exact alarm | `isAlarmActive("[<provider>]AreaA/CriticalPV", "CriticalAlarm")` | `Boolean` | Follows that alarm's active state; returned false Good while that alarm was shelved in the Expression Tag shape |
| Wildcard alarm name | `isAlarmActive("[<provider>]AreaA/*", "*Alarm")` | `Boolean` | Matches active alarms by wildcard alarm name |
| Critical priority filter | `isAlarmActiveFiltered("[<provider>]AreaA/*", "*", "*", 4, 4, false, true, false)` | `Boolean` | True Good for an active, unshelved Critical alarm; false Good when the retained event is clear |
| Ack blocked | `isAlarmActiveFiltered("[<provider>]AreaA/*", "*", "*", 4, 4, false, false, false)` | `Boolean` | After acknowledgement, false Good for the acknowledged Critical alarm |
| Ack allowed | `isAlarmActiveFiltered("[<provider>]AreaA/*", "*", "*", 4, 4, false, true, false)` | `Boolean` | After acknowledgement, true Good while the Critical alarm remains active and unshelved |
| Shelved blocked | `isAlarmActiveFiltered("[<provider>]AreaA/*", "*", "*", 4, 4, false, true, false)` | `Boolean` | After shelving that Critical alarm, false with `Bad_NotFound` can occur when shelved events are excluded |
| Shelved allowed | `isAlarmActiveFiltered("[<provider>]AreaA/*", "*", "*", 4, 4, false, true, true)` | `Boolean` | After shelving that Critical alarm, true Good when shelved events are allowed |
| Cleared allowed | `isAlarmActiveFiltered("[<provider>]AreaA/CriticalPV", "CriticalAlarm", "*", 4, 4, true, true, true)` | `Boolean` | Can remain true Good for a retained cleared event |
| Cleared blocked | `isAlarmActiveFiltered("[<provider>]AreaA/CriticalPV", "CriticalAlarm", "*", 4, 4, false, true, true)` | `Boolean` | False Good for the same cleared event |
| Dynamic area path | `isAlarmActive({[.]AreaPath})` | `Boolean` | Retargets as the path string changes |
| Dynamic priority filter | `isAlarmActiveFiltered({[.]AreaPath}, "*", "*", 4, 4, false, true, false)` | `Boolean` | Retargets as the path string changes; no-match priority filters can read false with `Bad_NotFound` |
| Provider omitted comparison | `isAlarmActive("_expression_skill_tests/<uniqueId>/AreaA/*")` | `Boolean` | Verify on the target; Ignition 8.1.53 Expression Tags followed current-provider state, but reusable examples should prefer `[<provider>]` or `[~]` |

## Expression Tag Execution Timing Matrix

Create one disposable folder with memory sources `A`, `B`, `SelectA`, `Mode`, `CoalesceA`, `CoalesceB`, `BadOrMissing`, `EventSrc`, `FixedSrc`, `DeadbandOffSrc`, and `DeadbandAbsSrc`. Record value, quality, and timestamp for each read. Do not infer Gateway subscription counts from these observations alone.

| Focus | Fixture expression/config | Data type | Expected behavior |
|---|---|---:|---|
| Event Driven branch | `if({[.]SelectA}, {[.]A}, {[.]B})` with `executionMode: "EventDriven"` | `Float8` | Returns the selected branch Good as source and selector values change |
| Fixed Rate branch | same expression with `executionMode: "FixedRate"`, `executionRate: 1000` | `Float8` | Returns the selected branch Good after the fixed evaluation catches the source or selector change |
| Tag Group Rate branch | same expression with `executionMode: "TagGroupRate"` | `Float8` | Configures and returns selected branch Good using the tag group's evaluation cadence |
| Explicit tag group | same expression with `executionMode: "TagGroupRate"`, `tagGroup: "Default"` | `Float8` | Configures and returns selected branch Good when the named tag group exists |
| `case()` branch | `case({[.]Mode}, 1, {[.]A}, 2, {[.]B}, 0)` | `Float8` | Returns the selected branch Good as `Mode`, `A`, and `B` change |
| Unselected branch write | write `B` while `SelectA=true` and `Mode=1` | mixed | Returned value remains the selected `A` value Good; Event Driven tag timestamps can still move |
| Unselected branch delete | delete `A` while `SelectA=false` and `Mode=2` | mixed | Returned value remains the selected `B` value Good |
| Boolean short-circuit missing right side | `false && {[.]BadOrMissing}` after deleting `BadOrMissing` | `Boolean` | Returns `false` Good |
| Boolean short-circuit missing right side | `true || {[.]BadOrMissing}` after deleting `BadOrMissing` | `Boolean` | Returns `true` Good |
| `coalesce()` fallback present | `coalesce({[.]CoalesceA}, {[.]CoalesceB})` | `String` | Returns the first non-null value Good |
| `coalesce()` fallback missing | same expression after deleting `CoalesceB` while `CoalesceA` is non-null | `String` | Keeps the first value Good |
| `coalesce()` all unavailable/null | same expression after setting `CoalesceA` null while `CoalesceB` is missing | `String` | Returns null Good |
| `coalesce()` fallback recreated | same expression after recreating `CoalesceB` while `CoalesceA` is null | `String` | Returns fallback value Good |
| Event timer | `now(250)` | `DateTime` | Updates between repeated reads on the Event Driven Expression Tag surface |
| Event script poll | `runScript("system.date.now().getTime()", 250)` | `Int8` | Updates between repeated reads on the Event Driven Expression Tag surface |
| Fixed timer | `now()` with `executionMode: "FixedRate"`, `executionRate: 1000` | `DateTime` | Updates on a later fixed evaluation |
| Event `hasChanged()` | `hasChanged({[.]EventSrc})` | `Boolean` | Returns Good; timing of true/false visibility depends on evaluation cadence |
| Fixed `hasChanged()` | `hasChanged({[.]FixedSrc})` with `executionMode: "FixedRate"`, `executionRate: 1000` | `Boolean` | Can show `true` near the fixed evaluation after a source write and return `false` later |
| Deadband off source | pass through `{[.]DeadbandOffSrc}` where source has `deadbandMode: "Off"` | `Float8` | Updates on small and large writes |
| Absolute deadband source | pass through `{[.]DeadbandAbsSrc}` where source has `deadbandMode: "Absolute"`, `deadband: 5.0` | `Float8` | Does not move on a 0.5 write from 0.0; updates on a 10.0 write |

## Performance Boundary Matrix

Use this matrix when an expression is large, repeated across many tags or UDT instances, or tied to a tight update budget. Record value, quality, write duration, read/poll wait, tag group or binding cadence, and target Gateway version. Do not reuse one target's numbers as general limits.

| Focus | Suggested sizes | Fixture shape | Result to record |
|---|---:|---|---|
| Static sibling references | 10, 100, 1,000 | Expression Tag sums many `{[.]RefNNN}` sibling memory tags | Write duration, returned sum, quality, and read wait |
| Dynamic `tag()` calls | 10, 100, 1,000 | Expression Tag sums `tag("<absolute path>")` calls | Write duration, returned sum, quality, and read wait |
| DataSet aggregate and sort | 10, 100, 1,000, 10,000 rows | DataSet memory tag plus `sum({[.]Table}, "PV")` and `sortDataset({[.]Table}, "PV", false)[0, "PV"]` | Returned aggregate/top value, quality, and read wait |
| JSON document read | increasing item counts | String memory tag containing JSON plus `jsonGet({[.]JsonText}, "items[n].pv")` | JSON length, returned value, quality, and read wait |
| Nested conditional depth | 10, 50, 100 | Nested `if(...)` or `case(...)` Expression Tag selected by a source value | Returned selected branch, quality, and read wait |
| `runScript()` duration | 0, 25, 100 ms | Pure `runScript()` call with an explicit source-value echo so each update is observable | Returned value, quality, read wait, and scheduler/tag-group context |
| Identical UDT instances | 10, 100 | Disposable UDT type with a memory source and expression member | Checked instance count, returned member values, quality, and read wait |

Gate or separately document tag-group overrun counters, JVM/memory readings, restart behavior, Perspective/Vision client behavior, and Designer behavior unless the active target exposes them safely.

## UDT Expression Member Matrix

Create a disposable UDT type under a unique `_types_` path and a disposable instance folder under the provider. Use scalar parameter overrides and member tags like these:

Parameters:

| Name | Suggested type | Example value | Purpose |
|---|---|---:|---|
| `AssetName` | `String` | `Unit-1` | Formatting and parameter readback |
| `Scale` | `Float` | `2.5` | Numeric math |
| `Offset` | `Float` | `1.0` | Numeric math and `+` behavior |
| `HighLimit` | `Float` | `10.0` | Comparison |
| `Enabled` | `Boolean` | `true` | Boolean parameter logic |
| `FlowPath` | `String` | `[<provider>]Area/SourcePV` | Dynamic `tag()` path |

Member matrix:

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| Parameter plus sibling math | `({[.]Raw} * {Scale}) + {Offset}` | `Float8` | With `Raw=4`, `Scale=2.5`, `Offset=1`, returns `11.0` Good |
| Threshold compare | `{[.]ScaledPV} > {HighLimit}` | `Boolean` | With `ScaledPV=11` and `HighLimit=10`, returns true Good |
| Boolean parameter and sibling | `{Enabled} && {[.]High}` | `Boolean` | Returns true Good when both are true |
| String parameter formatting | `{AssetName} + ": " + numberFormat({[.]ScaledPV}, "0.0")` | `String` | Returns text such as `Unit-1: 11.0` Good |
| Dynamic path parameter | `toFloat(tag({FlowPath}), -1.0)` | `Float8` | Reads the tag named by `FlowPath`; updates when the source value changes |
| Quoted dynamic path trap | `toFloat(tag("{FlowPath}"), -1.0)` | `Float8` | Treats `{FlowPath}` as a literal path and can return null with an expression error |
| Numeric-looking string multiply | `{Scale} * 2` with `Scale="2.5"` | `Float8` | Can coerce and return `5.0` Good |
| Numeric-looking string plus | `{Scale} + 1` with `Scale="2.5"` | `String` | Can concatenate and return `2.51` Good |
| Bad numeric string | `{Scale} * 2` with `Scale="abc"` | `Float8` | Returns null with an expression/conversion error |
| Parameter update recalculation | `({[.]Raw} * {Scale}) + {Offset}` after override/write | `Float8` | Re-read member values after parameter or source changes; do not rely only on parameter readback |

## UDT DataSet/Table Member Matrix

For table-shaped UDT coverage, create a disposable UDT type with a DataSet member and at least one external DataSet source tag. Populate real DataSet values during validation with `system.dataset.toDataSet(headers, rows)` or another platform-native DataSet source, then read both value and quality from the expression members.

Suggested UDT parameters:

| Name | Suggested type | Example value | Purpose |
|---|---|---:|---|
| `AssetName` | `String` | `Table-1` | Label formatting |
| `RowIndex` | numeric or integer-like | `1` | Zero-based DataSet row selection |
| `StatusColumn` | `String` | `Status` | Parameterized column selection |
| `TablePath` | `String` | `[<provider>]Area/SourceTable` | Dynamic external DataSet path |
| `PVScale` | `Float` | `1.0` | Numeric cell scaling |
| `MissingTablePath` | `String` | `[<provider>]Area/MissingTable` | Missing dynamic DataSet behavior |

Suggested table columns:

```text
Name, PV, Status, Enabled, Priority
```

Member matrix:

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| Sibling row count | `len({[.]LocalTable})` | `Int4` | Returns the DataSet row count |
| Sibling string cell | `{[.]LocalTable}[{RowIndex}, "Status"]` | `String` | Reads the selected row's status |
| Sibling parameterized column | `{[.]LocalTable}[{RowIndex}, {StatusColumn}]` | `String` | Uses the string parameter as the column name |
| Sibling numeric cell | `toFloat({[.]LocalTable}[{RowIndex}, "PV"], -1.0)` | `Float8` | Reads the selected numeric cell; validate with float tolerance |
| Sibling scaled numeric cell | `toFloat({[.]LocalTable}[{RowIndex}, "PV"], -1.0) * {PVScale}` | `Float8` | Applies a UDT parameter after cell extraction |
| Sibling boolean cell | `toBoolean({[.]LocalTable}[{RowIndex}, "Enabled"], false)` | `Boolean` | Converts the selected cell to a boolean |
| Sibling label | `{AssetName} + ":" + {[.]LocalTable}[{RowIndex}, "Status"] + ":" + numberFormat({[.]LocalTable}[{RowIndex}, "PV"], "0.0")` | `String` | Combines parameter text and table cells |
| Missing sibling column fallback | `try({[.]LocalTable}[{RowIndex}, "NoSuchColumn"], "MISSING")` | `String` | Returns a Good fallback for an invalid column |
| Missing sibling row fallback | `try({[.]LocalTable}[99, "Status"], "NO_ROW")` | `String` | Returns a Good fallback for an out-of-range row |
| Dynamic row count | `len(tag({TablePath}))` | `Int4` | Counts rows from the external DataSet tag |
| Dynamic string cell | `tag({TablePath})[{RowIndex}, "Status"]` | `String` | Reads a cell from the parameter-supplied table path |
| Dynamic parameterized column | `tag({TablePath})[{RowIndex}, {StatusColumn}]` | `String` | Uses both dynamic table path and dynamic column name |
| Dynamic numeric cell | `toFloat(tag({TablePath})[{RowIndex}, "PV"], -1.0)` | `Float8` | Reads and casts a numeric cell from the external table |
| Dynamic label | `tag({TablePath})[{RowIndex}, "Name"] + ":" + numberFormat(tag({TablePath})[{RowIndex}, "PV"], "0.0")` | `String` | Formats external table cells for display |
| Quoted dynamic table trap | `try(tag("{TablePath}")[0, "Status"], "BAD_TABLE")` | `String` | Treats `{TablePath}` as a literal path; fallback may return Good, but the pattern is still wrong for production |
| Missing dynamic table path | `try(tag({MissingTablePath})[0, "Status"], "NO_TABLE")` | `String` | Can read null with Bad_NotFound instead of returning the fallback; verify quality when a missing table is possible |
| Parameter row update | same members after `RowIndex` changes | mixed | Re-read member values after parameter updates |
| DataSet rewrite update | same members after the DataSet tag is rewritten | mixed | Re-read member values after table contents change |
| Instance isolation | same UDT type with a second instance and different parameters | mixed | Each instance should use its own `RowIndex`, `TablePath`, and scaling parameter |

## `runScript()` Matrix

Use this matrix only when a target needs expression-to-script behavior. Keep script calls small and verify the evaluating scope before using project-library paths.

| Focus | Expression | Data type | Expected behavior |
|---|---|---:|---|
| Inline arithmetic | `runScript("1 + 2", 0)` | `Int4` | Returns `3` Good |
| Preferred builtin path | `runScript("len", 0, "abcd")` | `Int4` | Returns `4` Good |
| Legacy call string | `runScript("len('abcd')", 0)` | `Int4` | Returns `4` Good |
| Preferred system function path | `runScript("system.date.now", 0)` | `DateTime` | Returns a date value Good |
| Legacy system call string | `runScript("system.date.now()", 0)` | `DateTime` | Returns a date value Good |
| Script exception fallback | `try(runScript("1/0", 0), -1)` | `Int4` | Returns `-1` Good |
| Polling value | `runScript("system.date.now().getTime()", 250)` | `Int8` | Can update between reads when the tag group or binding refresh permits |
| Non-polling value | `runScript("system.date.now().getTime()", 0)` | `Int8` | Does not create its own polling timer |
| Project library call | `runScript("textScript.statusText", 0, {[.]State})` | `String` | Requires the Gateway Scripting Project to expose `textScript` to Expression Tag/Gateway scope |
| Project library unavailable | `runScript("textScript.statusText", 0, {[.]State})` without the needed Gateway scripting scope | `String` | Can return null with expression-evaluation error quality |
| Project library fallback | `try(runScript("textScript.statusText", 0, {[.]State}), "SCRIPT_FAIL")` | `String` | Can return a Good fallback for script/evaluation errors |

## `hasChanged()` Matrix

Use separate fixture sources for each scenario so one change does not pollute another tag's state. Record both value and quality for every `hasChanged(...)` tag.

| Focus | Fixture expression | Data type | Observation to capture |
|---|---|---:|---|
| First evaluation after configuration | `hasChanged({[.]ChangeSrc})` | `Boolean` | Whether the first stable read is `true` or `false`; do not assume a false baseline |
| Same-value write | `hasChanged({[.]SameSrc})` | `Boolean` | Value after writing the same value back to the source |
| Event Driven, no poll | `hasChanged({[.]EventSrc})` | `Boolean` | How long `true` remains visible after a value change |
| Event Driven with pollRate | `hasChanged({[.]PollSrc}, false, 1000)` | `Boolean` | Whether the result resets after the poll-rate evaluation |
| Fixed Rate Expression Tag | `hasChanged({[.]FixedSrc})` with `executionMode: "FixedRate"` and `executionRate: 1000` | `Boolean` | Whether the true result appears on the next fixed evaluation and then resets |
| Quality-only, value mode | `hasChanged({[.]QualifiedPV}, false)` | `Boolean` | Whether a quality-only transition changes the result |
| Quality-only, value+quality mode | `hasChanged({[.]QualifiedPV}, true)` | `Boolean` | Whether a quality-only transition changes the result |
| Good null to Good value | `hasChanged({[.]NullToValueSrc})` | `Boolean` | Whether Good null-to-value reads as changed |
| Good value to Good null | `hasChanged({[.]ValueToNullSrc})` | `Boolean` | Whether value-to-Good-null reads as changed |
| Disable/re-enable | `hasChanged({[.]DisableSrc}, true)` and `hasChanged({[.]DisableSrc}, false)` | `Boolean` | Values during Bad_Disabled and after re-enable |
| Dynamic retarget | `hasChanged(tag({[.]PVPath}))` | `Boolean` | Values after path retargeting and after selected-source value changes |
| Two separate tags | Two tags with `hasChanged({[.]TwoSrc})` | `Boolean` | Whether separate tags agree after the source changes |
| Two calls in one expression | `if(hasChanged({[.]TwoSrc}), 10, 0) + if(hasChanged({[.]TwoSrc}), 1, 0)` | `Int4` | `0`, `1`, `10`, or `11`, showing which calls read true |

## API Request Templates

Health and context:

```json
{"action": "health", "requestId": "expr-health"}
{"action": "gatewayInfo", "requestId": "expr-gateway", "includeModules": false}
{"action": "tagProviders", "requestId": "expr-providers", "maxResults": 100}
```

Configure disposable tags with dry-run first:

```json
{
  "action": "tagConfigure",
  "requestId": "expr-tags-dryrun",
  "basePath": "[<provider>]_expression_skill_tests/<uniqueId>",
  "tags": [],
  "allowedTagPathPrefixes": ["[<provider>]_expression_skill_tests/<uniqueId>"],
  "collisionPolicy": "a",
  "dryRun": true,
  "maxItems": 100
}
```

Apply only after the dry-run is clean:

```json
{
  "action": "tagConfigure",
  "requestId": "expr-tags-apply",
  "basePath": "[<provider>]_expression_skill_tests/<uniqueId>",
  "tags": [],
  "allowedTagPathPrefixes": ["[<provider>]_expression_skill_tests/<uniqueId>"],
  "collisionPolicy": "a",
  "dryRun": false,
  "confirmTagConfigure": "CONFIGURE_TAGS",
  "maxItems": 100
}
```

Read values and quality:

```json
{
  "action": "tagRead",
  "requestId": "expr-read",
  "paths": [
    "[<provider>]_expression_skill_tests/<uniqueId>/SomeExpression"
  ],
  "maxResults": 100
}
```

Use any available narrow tag-write/delete action in preference to general script execution. If the active runner has no such action, confirmed `scriptEval` may be used only for bounded writes and cleanup under the unique disposable folder.

Bounded write shape:

```json
{
  "action": "scriptEval",
  "requestId": "expr-write-dryrun",
  "dryRun": true,
  "script": "paths = args['paths']\nvalues = args['values']\nqualities = system.tag.writeBlocking(paths, values)\nreturn [str(q) for q in qualities]",
  "args": {
    "paths": ["[<provider>]_expression_skill_tests/<uniqueId>/A"],
    "values": [20.0]
  }
}
```

Cleanup shape:

```json
{
  "action": "scriptEval",
  "requestId": "expr-cleanup-dryrun",
  "dryRun": true,
  "script": "path = args['path']\nreturn {'existsBefore': system.tag.exists(path)}",
  "args": {
    "path": "[<provider>]_expression_skill_tests/<uniqueId>"
  }
}
```

The actual cleanup script should delete only the exact unique folder path and then verify it no longer exists.
