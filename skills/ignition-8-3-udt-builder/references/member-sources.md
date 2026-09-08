# Scaling, derived, and database-query members

Use this reference when a UDT member scales a value, derives from another tag, or executes a database query. These shapes were imported, exported, and read on Ignition 8.3.8.

## Scaling and engineering limits

Linear scaling:

```json
{
  "name": "ScaledPV",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "Float8",
  "value": 50.0,
  "scaleMode": "Linear",
  "rawLow": 0.0,
  "rawHigh": 100.0,
  "scaledLow": 0.0,
  "scaledHigh": 10.0,
  "clampMode": "Clamp_Both"
}
```

Verified `scaleMode` JSON names are `Off`, `Linear`, `SquareRoot`, `ExponentialFilter`, and `BitInversion`. Verified `clampMode` names are `No_Clamp`, `Clamp_Low`, `Clamp_High`, and `Clamp_Both`.

Observed results:

- Linear 50 from raw 0–100 to scaled 0–10 returned 5.
- Linear 150 with `Clamp_Both` returned 10; `No_Clamp` returned 15.
- Square-root 25 over the same ranges returned 5.
- `BitInversion` changed Boolean true to false.

Use a binding object for a parameterized numeric property:

```json
"rawHigh": {
  "bindType": "parameter",
  "binding": "{RawHigh}"
}
```

Plain `"rawHigh": "{RawHigh}"` was silently omitted from the normalized export and did not respond to an instance override. Read the property and verify different instance parameters produce different scaled values.

Engineering limits are quality limits, not value clamps. With `engLow: 0`, `engHigh: 100`, and `engLimitMode: "Clamp_Both"`, a value of 150 remained 150 and quality became `Bad_OutOfRange`.

## Derived members

```json
{
  "name": "EngineeringValue",
  "tagType": "AtomicTag",
  "valueSource": "derived",
  "dataType": "Float8",
  "sourceTagPath": "[.]Source",
  "deriveExpressionGetter": "{source} * 2",
  "deriveExpressionSetter": "{value} / 2",
  "preserveSourceTimestamp": true
}
```

Writing 50 to this member wrote 25 to `Source`, and the getter read back 50. Verify both source and derived values after every write.

For an instance-selectable source, use a property binding object:

```json
"sourceTagPath": {
  "bindType": "parameter",
  "binding": "{SourcePath}"
}
```

Plain `"sourceTagPath": "{SourcePath}"` remained literal and the member stayed `Uncertain_InitialValue`.

Do not assume that omitting `deriveExpressionSetter` makes the member read-only. On the verified build it used identity write-through: writing 100 changed the source to 100, while a getter of `{source} + 1` read back 101. The guarded write therefore returned good write quality but failed exact readback verification. Define a setter deliberately or prohibit writes at a higher layer.

## Database-query members

Scalar query:

```json
{
  "name": "QueryValue",
  "tagType": "AtomicTag",
  "valueSource": "db",
  "dataType": "Int4",
  "datasource": "YourDatabase",
  "query": "SELECT 42",
  "queryType": "Select",
  "executionMode": "FixedRate",
  "executionRate": 500
}
```

Use `DataSet` for multirow results. A two-row select returned Good `BasicDataset`; the guarded generic read API stringified that dataset, so use a dataset-aware verifier when cell-level proof matters.

Both of these query forms resolved a UDT parameter per instance in the verified fixture:

```json
"query": "SELECT {QueryNumber}"
```

```json
"query": {
  "bindType": "parameter",
  "binding": "SELECT {QueryNumber}"
}
```

This plain-text substitution behavior is specific to query text. Do not generalize it to numeric properties or tag-path properties.

An unknown datasource and malformed SQL both imported but produced `Error_ExpressionEval` at runtime. Discover an enabled datasource first and prove value, type, quality, and update timing after import.
