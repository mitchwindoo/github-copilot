# Quality and Migration

## Read the Whole Qualified Value

During validation, capture:

- Serialized value.
- Runtime value class or Ignition data type.
- Full integer quality code.
- Quality level.
- Subcode or readable quality name.
- Diagnostic message.
- Timestamp.

Do not reduce every outcome to value-only or Good/Bad-only checks.

## Distinguish Full Code From Subcode

The quality integer exposed by a Java or Jython object may be a signed composite
full code, while the manual lists the low quality subcode. Do not compare those
numbers as though they were the same field.

On the verified 8.3.8 Gateway, a direct read of one deliberately missing tag
returned null/`NoneType` and the readable quality
`Bad_NotFound("<path> not found.")`. The documented subcode is `519`, but
Gateway-scope Jython serialized the signed composite full code as
`-2147483129`; interpreted as unsigned it is `2147484167` or `0x80000207`.

Capture the readable name, full code, and subcode separately. Prefer the
readable quality API or an explicitly decoded subcode over a hard-coded signed
integer when writing portable validation.

## Quality Helpers

```text
isGood({[.]PV})
isUncertain({[.]PV})
isBad({[.]PV})
isError({[.]PV})
isBadOrError({[.]PV})
qualityOf({[.]PV})
```

The helper expression normally returns its own Good boolean or string result when it evaluates successfully, even if the inspected value has non-Good quality.

## Construct Modern Quality

`qualifiedValue()` is the preferred construction function for new 8.3 expressions:

```text
qualifiedValue(value, level)
qualifiedValue(value, level, subcode)
qualifiedValue(value, level, subcode, diagnosticMessage)
```

Supported documented levels:

| Name | Numeric level |
|---|---:|
| Good | 0 |
| Uncertain | 1 |
| Bad | 2 |
| Error | 3 |

Examples:

```text
qualifiedValue(123, "Good")
qualifiedValue(123, "Uncertain")
qualifiedValue(123, "Bad")
qualifiedValue(123, "Error")
qualifiedValue(123, "Bad", 515, "Disabled by test")
```

On the verified 8.3.8 Expression Tag target, these forms preserved the numeric value while producing the requested Good, Uncertain, Bad, Error, or `Bad_Disabled` quality. A diagnostic supplied to the four-argument form was preserved.

## Treat `forceQuality()` as Legacy

`forceQuality(value[, qualityCode])` uses legacy 7.9-era integer quality codes. The official 8.3 documentation directs new code toward `qualifiedValue()` for the modern quality model.

Verified examples:

```text
forceQuality(123, 0)       // value 123 with Bad quality
forceQuality(123, 192)     // value 123 with Good quality
```

Do not convert this:

```text
forceQuality(value, 0)
```

to this:

```text
qualifiedValue(value, 0)
```

The first uses legacy code `0` for Bad. The second uses modern level `0` for
Good. In one fixed, side-by-side 8.3.8 Expression Tag batch, both expressions
preserved integer value `123`; the legacy form returned Bad with full code
`-2147483136`, while the naive modern form returned Good with full code `192`.
The comparison was independently read back and replayed idempotently. A
numeric search-and-replace therefore reverses the intended semantics for
numeric `0`. This result does not map other legacy integers or cover component
overlays, alarms, or other expression hosts.

## Migrate Semantically

For every `forceQuality()` call:

1. Capture the expression, surface, output type, and the legacy integer.
2. Determine the legacy quality name and operational meaning.
3. Decide whether the modern result should be Good, Uncertain, Bad, or Error.
4. Select a modern subcode that preserves the intended condition.
5. Preserve or improve the diagnostic message.
6. Build a `qualifiedValue()` candidate.
7. Compare value, level, subcode/name, diagnostic, and timestamp on the exact 8.3 target.
8. Test downstream overlays, alarms, bindings, and guards that consume the quality.

Example shape:

```text
qualifiedValue({[.]PV}, "Bad", 515, "Disabled by interlock")
```

Choose the actual subcode from the target's current quality-code documentation; do not copy `515` merely because it appears in an example.

### Supported Gateway-Backup Persistence Boundary

One fixed Gateway backup from exact Ignition 8.1.53 was restored into exact
8.3.8 after a source restart. Four Expression Tags retained their exact
expression text and values:

- legacy `forceQuality()` with quality integers `0` and `192`
- modern `qualifiedValue()` with explicit Bad and Good levels

The legacy-zero and modern-Bad tags remained Bad, the legacy-192 and
modern-Good tags remained Good, and the supplied modern-Bad diagnostic was
preserved exactly. This proves persistence for those fixed tags through that
supported backup route. It does not prove automatic rewriting, semantic
conversion, equivalence between legacy integers and modern levels, other
versions, or other expression hosts.

## Quality Propagation

On the verified 8.3.8 Expression Tag fixture, a numeric value carrying `Bad_Disabled` behaved as follows:

| Expression shape | Value behavior | Final quality |
|---|---|---|
| `{[.]BadPV} + 1.0` | Arithmetic result returned | Bad_Disabled; diagnostic preserved |
| `try({[.]BadPV} + 1.0, -1.0)` | Arithmetic result returned; fallback not used | Bad |
| `coalesce({[.]BadPV}, -1.0)` | Non-null value returned | Bad |
| `if(isGood({[.]BadPV}), {[.]BadPV}, -1.0)` | Fallback returned | Good |
| `if(true, {[.]BadPV}, -1.0)` | Bad selected value returned | Bad |
| `if(false, {[.]BadPV}, 5.0)` | Good selected value returned | Good |
| `if(true, 5.0, {[.]BadPV})` | Good selected value returned | Good |

A dedicated direct-arithmetic control on the same target started from integer
`41`. Adding `1` produced `42` while preserving Bad_Disabled full code
`-2147483133` and the exact diagnostic text. The matching Good qualified-value
control also produced `42` and remained Good/`192`. This proves one integer
addition only; test other operators, multiple qualified operands, quality
levels, and hosts separately.

### Perspective Direct-Binding Overlay

On a fixed Perspective view on the verified 8.3.8 target, a Label used a
direct tag binding to an Expression Tag returning:

```text
qualifiedValue(
  42,
  "Bad",
  515,
  "FQ-008: maintenance interlock active"
)
```

With `overlayOptOut=false`, Perspective retained the displayed value `42` and
rendered its red Error overlay. Opening the overlay reported:

- Subcode: `Bad_Disabled`
- Property: `root/QualifiedBad.text`
- Description: `FQ-008: maintenance interlock active`

An unbound static Good control on the same view had no overlay. This confirms
that one Bad_Disabled direct-binding path from an Expression Tag to a
Perspective Label. It does not prove opt-out behavior, indirect bindings,
other quality levels or components, alarms, Vision, or migration parity.

The practical rules are:

- Bad quality is not the same as an exception.
- `try()` catches an evaluation error; it is not a general quality scrubber.
- `coalesce()` checks null-like values; it is not a quality guard.
- A selected Bad branch can propagate Bad quality.
- An unselected Bad branch need not contaminate the returned branch's quality on the verified Expression Tag surface.

Do not generalize the last point into a subscription, performance, or cross-surface claim without a separate test.

## Error-Quality Fallback

On the verified 8.3.8 Expression Tag target:

```text
try(qualifiedValue(123.0, "Error"), -1.0)
```

returned the Good fallback. By contrast, Bad or Uncertain quality can remain a successfully evaluated, non-Good result. Test the exact quality level you intend to handle.

## Quality Review Checklist

- Does the expression intentionally preserve source quality?
- Can a usable numeric value still be Bad or Uncertain?
- Does the caller inspect value only and accidentally ignore quality?
- Is an overlay opt-out hiding a non-Good result?
- Is `try()` being used for a quality condition it cannot handle?
- Is `coalesce()` being used for a non-null Bad value?
- Was a legacy `forceQuality()` integer copied into `qualifiedValue()`?
- Are the level, subcode, and diagnostic meaningful to operators?
- Was the behavior verified on the actual host surface?

## Official References

- `forceQuality()`: https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/advanced/forceQuality
- `qualifiedValue()`: https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/advanced/qualifiedValue
- 8.1-to-8.3 upgrade guide: https://www.docs.inductiveautomation.com/docs/8.3/getting-started/installing-and-upgrading/ignition-8-upgrade-guide/81to83-upgrade-guide
