# Complex UDT member values

Use explicit JSON shapes for array, `Document`, `DataSet`, and `Text` memory members. Validate the authored root before import, then verify both export and direct runtime members. HTTP 200, semantic import success, Good quality, and a root snapshot can all coexist with a silently null or coerced value.

For ordinary scalar memory members, also preserve the declared JSON type: signed in-range JSON integers for `Int1`/`Int2`/`Int4`/`Int8`, finite JSON numbers for `Float4`/`Float8`, JSON Booleans for `Boolean`, and JSON strings for `String`. Do not encode generations, counters, limits, or other numeric state as strings. The validator accepts a property-binding object where scalar member bindings are valid and otherwise checks these literal types before import.

## Arrays

Use JSON arrays for these verified types:

```json
{
  "name": "Samples",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "Float8Array",
  "value": [1.25, -2.5, 3.0]
}
```

The verified array types are `Int1Array`, `Int2Array`, `Int4Array`, `Int8Array`, `Float4Array`, `Float8Array`, `BooleanArray`, `StringArray`, `DateTimeArray`, and `ByteArray`. Empty arrays are valid. Use exact element types:

- Integer arrays: JSON integers within the signed width. `ByteArray` uses signed `-128..127` values in the tested JSON representation.
- Float arrays: finite JSON numbers, not Boolean or string values.
- `BooleanArray`: JSON Booleans.
- `StringArray`: JSON strings.
- `DateTimeArray`: epoch-millisecond JSON integers. Runtime structured reads return `{"dateTimeMillis": ...}` per element.

Do not rely on coercion. A scalar or mixed string/integer `Int4Array` imported with success and later read null/Good; the mixed array also emitted a delayed conversion ERROR. `Int1Array` values `128` and `-129` wrapped to `-128` and `127`. An ISO date string became a null date element with Good quality.

## Documents

Objects and arrays are both valid `Document` values:

```json
{
  "name": "Metadata",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "Document",
  "value": {
    "asset": {"id": "P-001", "enabled": true},
    "limits": [1, 2.5],
    "optional": null
  }
}
```

A scalar JSON string was also accepted as a Document and read as a scalar. If the consumer requires an object or array, verify that exact runtime kind and fields; `dataType: "Document"` alone does not establish the root shape.

## DataSets

In a UDT definition, use an object with `columns` and `rows`. Preserve row nesting even for one row:

```json
{
  "name": "Table",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "DataSet",
  "value": {
    "columns": [
      {"name": "Name", "type": "java.lang.String"},
      {"name": "Reading", "type": "java.lang.Double"},
      {"name": "Enabled", "type": "java.lang.Boolean"}
    ],
    "rows": [
      ["A", 1.5, true],
      ["B", null, false]
    ]
  }
}
```

Verified column classes are `java.lang.String`, `java.lang.Byte`, `java.lang.Short`, `java.lang.Integer`, `java.lang.Long`, `java.lang.Float`, `java.lang.Double`, `java.lang.Boolean`, and `java.util.Date`. Date cells use epoch-millisecond integers. Null cells are valid. Empty `columns` and `rows` produce a valid empty dataset.

Definition export encodes the dataset object as a JSON string. For an instance member override, supply that encoded string and include `dataType: "DataSet"` so local validation can parse it:

```json
{
  "name": "Table",
  "tagType": "AtomicTag",
  "dataType": "DataSet",
  "value": "{\"columns\":[{\"name\":\"Name\",\"type\":\"java.lang.String\"}],\"rows\":[[\"OVR\"]]}"
}
```

Passing the structured object directly as an instance override was interpreted as a Document and produced `Error_TypeConversion`. Dataset column strings, unknown column classes, and row-width mismatches imported successfully but normalized to null/Good. Always require exact column names/classes, dimensions, and cell values at runtime.

When generating dataset JSON in PowerShell, `@(@("A", 1.5))` can unwrap a single row. Create an explicit inner object array and wrap it with the unary comma or an equivalent JSON-safe method, then inspect the serialized request bytes.

### Script-managed bounded DataSets

A memory `DataSet` can hold a small, typed audit window inside a UDT. Define the complete empty schema in the UDT JSON, including `java.util.Date` for event time. In the tag event script, read the Dataset as a QualifiedValue and require Good quality before using it. Datasets are immutable: assign the return from `system.dataset.addRow`, then repeatedly assign the return from `system.dataset.deleteRow(dataset, 0)` until the configured capacity is met. Use `system.dataset.clearDataset` for reset so the empty result retains the schema.

Keep `AuditRowCount` and `AuditEvictionCount` as separate typed evidence tags. Clamp capacity to at least one in the script, but also validate the UDT parameter as an `Int4` JSON integer before import. Write the Dataset and its counters in one `writeBlocking` call and require every returned quality to be Good.

Prove the final value with `tag-read-complex-v1`, not the generic reader. Require exact column names/classes, retained row order, cell JSON types, structured `dateTimeMillis`, fixed-cap eviction, and `truncated: false`. Also exercise `clearDataset` and prove zero rows after reset. Three live nested-UDT runs appended six release decisions into a capacity-four table, retained triggers 3-6 in order, reported two evictions, reset to the same typed empty table, isolated a Control instance, retained exactly seven run-specific logs, and had zero same-window ERROR rows.

### Correlate a DataSet with a Document snapshot

Pair a bounded audit DataSet with a `Document` when consumers need both history and a convenient latest-decision envelope. On the verified Gateway, a tag event script could write a plain Jython dictionary directly to a Document memory tag. Give the envelope an explicit schema version and stable nested fields rather than exposing incidental script objects.

Capture time once: `now_millis = system.date.toMillis(system.date.now())`. Put `system.date.fromMillis(now_millis)` in the DataSet Date cell and the integer `now_millis` in the Document. Build both values from the same decision inputs, write the DataSet, Document, and evidence counters in one `writeBlocking` call, and require every returned quality to be Good. A multi-item write is not a transaction; read both complex tags back and compare decision, trigger, sequence, generation, mask, counts, row count, eviction count, and exact event milliseconds.

Arrays inside the Document are useful for decoded state. The live roster test derived `selectedSlots` from the frozen mask: mask 7 produced `[0, 1, 2]`, while mask 3 produced `[0, 1]`. Reset the two structures deliberately: `clearDataset` preserves only the DataSet schema, so also write a complete RESET Document and reset its counters. Verify the untouched Control instance and query the bounded dedicated and ERROR-or-higher Gateway logs even when all complex-value qualities are Good.

### Consume a Document from a nested UDT

A nested child UDT event script can read a sibling Folder's Document as a QualifiedValue and index the live `PyDocumentObjectAdapter` with ordinary mapping syntax: `envelope['decision']`, `envelope['roster']['mask']`, and `envelope['roster']['selectedSlots']`. Require Good quality before indexing and cast every field to its application type. Use `len(...)` for a Document array when only its cardinality is needed.

Correlate consumption to a stable identity such as `eventTimeMillis`, not merely a repeated decision string. Acknowledgement tests distinguished RESET/no-envelope, stale identity, expected-decision mismatch, duplicate identity, and accepted identity while retaining the last accepted epoch. Three clean runs consumed two successive envelopes and preserved Good typed evidence, Control isolation, explicit reset, ten focused logs, and zero ERROR+. This is cooperative application correlation, not atomic compare-and-set or durable messaging.

If consecutive Documents can carry the same decision, a poll that checks only `value.decision` may return the earlier Good value immediately. First wait for a monotonic scalar such as `EnvelopeWriteCount`, then read the Document and assert its exact trigger and epoch. Receipt tests caught this race in a stopped attempt and passed three repeats after adding the scalar barrier.

### Journal a correlated Document into a bounded DataSet

A consumer child UDT can translate a sibling confirmation Document into a typed audit row. Require Good quality for the confirmation, current producer Document, existing DataSet, and local fence/counters. Reject RESET/no confirmation, a producer identity mismatch, and a repeated observation sequence before calling `system.dataset.addRow`.

Use native integer/string values and convert confirmation/journal epochs with `system.date.fromMillis` for `java.util.Date` columns. Assign the immutable return from `addRow`; while over capacity, assign the return from `deleteRow(dataset, 0)` and increment eviction evidence. Reset with `clearDataset` so the schema remains intact.

At test capacity one, two valid confirmations deterministically evicted the first. Three clean runs retained the exact second row, two typed Date cells, row count one, eviction one, journaled two, denied two, duplicate one, 21 exact logs, and zero ERROR+.

## Scalar DateTime

Use an epoch-millisecond JSON integer for a scalar `DateTime` memory member:

```json
{
  "name": "ExpiresAt",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "DateTime",
  "value": 1784570855406
}
```

Official import and export preserved this exact integer in the verified 8.3.8 UDT definition and concrete nested-member override. Do not substitute an ISO string without target-specific proof; the customer validator rejects it because it is not the verified scalar import shape.

The consolidated generic `tag-read-v1` serialized the runtime value as `valueType: Date`, `valueKind: stringified`, with a locale/time-zone display string. That string is useful for visibility but not exact epoch comparison. For an exact runtime epoch, use `system.date.toMillis(qualifiedValue.value)` in an observable script and write the result to an `Int8` marker, or use another explicitly Date-aware API surface. Keep transport representation, display time zone, and application comparison semantics separate.

## Text

Use an explicit JSON string for `Text`, including multiline content. A numeric value imported successfully and became string `"42"`; reject implicit coercion when exact type/content matters.

## Verification

Export the type and instance and compare normalized configuration. Then read each direct member. Use advertised `tag-read-complex-v1` for structured values and require:

- exact quality and `isGood`;
- exact `kind`, dimensions/counts, column types, elements/fields/cells, and timestamps;
- `truncated: false`;
- instance overrides plus at least one unchanged inherited sibling.

If the action is unavailable, use an approved dataset/document-aware runner. Generic stringification such as `<PyDataset rows:2 cols:3>` is not cell-level proof.
