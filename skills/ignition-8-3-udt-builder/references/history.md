# Tag history in UDT members

Use this reference to author and verify historian configuration. Configuration shapes below were imported and exported on Ignition 8.3.8. Stored-sample behavior still requires a target-specific runtime query; configuration persistence alone is not historian proof.

## Discover the provider

Discover an enabled provider from the authenticated live OpenAPI rather than copying a lab name. On the verified contract, the resource-name route was:

```text
GET /data/api/v1/resources/names/com.inductiveautomation.historian/historian-provider
```

Confirm the exact route exists in the target contract and require one enabled match.

## On-change member

```json
{
  "name": "PV",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "Float8",
  "value": 0.0,
  "historyEnabled": true,
  "historyProvider": "YourHistorian",
  "historicalDeadbandStyle": "Discrete",
  "historicalDeadbandMode": "Off",
  "historicalDeadband": 0.0,
  "sampleMode": "OnChange"
}
```

History deadband styles are `Auto`, `Analog_Compressed`, and `Discrete`. Deadband modes are `Absolute`, `Percent`, and `Off`. Sample modes are `OnChange`, `Periodic`, and `TagGroup`.

## Periodic and tag-group members

Periodic:

```json
{
  "historyEnabled": true,
  "historyProvider": "YourHistorian",
  "sampleMode": "Periodic",
  "historySampleRate": 250,
  "historySampleRateUnits": "MS"
}
```

Tag group:

```json
{
  "historyEnabled": true,
  "historyProvider": "YourHistorian",
  "sampleMode": "TagGroup",
  "historyTagGroup": "Default"
}
```

Time-unit JSON names are `MS`, `SEC`, `MIN`, `HOUR`, `DAY`, `WEEK`, `MONTH`, and `YEAR`.

## UDT parameter bindings

Use property-binding objects for a parameterized provider or numeric rate:

```json
"historyProvider": {
  "bindType": "parameter",
  "binding": "{HistoryProvider}"
}
```

```json
"historySampleRate": {
  "bindType": "parameter",
  "binding": "{SampleRate}"
}
```

Both binding objects survived normalization. Plain `"historyProvider": "{HistoryProvider}"` persisted literally; do not mistake persistence for resolution. Plain `"historySampleRate": "{SampleRate}"` was removed. Read both runtime properties per instance and query stored history before claiming either binding works.

## Normalization and counting traps

- Invalid history style, deadband mode, sample mode, and time-unit strings imported without a semantic failure but were omitted from export.
- `historyEnabled: false` did not sanitize an invalid provider string; disabled configuration still needs validation.
- A UDT type root with ten member definitions returned `successCount: 1`. Its member definitions were not counted separately.
- A Folder root containing two UDT instances returned `successCount: 3`: folder plus two descendants. Do not apply Folder counting rules to a UDT type.

## Prove runtime history

After export confirms configuration:

1. Read `HistoryEnabled`, `HistoryProvider`, `SampleMode`, and mode-specific properties on concrete instances.
2. Record a bounded start time, then perform controlled value changes with exact write/readback verification.
3. Wait through the configured collection interval and store-and-forward delay using a bounded deadline.
4. Query only exact qualified paths and a short time window through a live official route or a fixed-shape read-only extension.
5. Preserve returned path, value, quality, timestamp, bounds/interpolation settings, completeness, and truncation.
6. Distinguish observed samples from interpolated or seeded rows. A positive `returnSize` can change the result shape.
7. If the query is empty, inspect the historian provider and store-and-forward diagnostics through authenticated APIs. Treat connection, license, queue, and database-lock failures as fixture failures; do not rewrite a valid UDT merely to make an unhealthy historian return rows.
8. Restore current tag values. Historical test rows intentionally remain in the disposable historian unless an explicitly authorized retention cleanup exists.

Do not infer historian storage from a Good realtime tag, a successful import, an exported `historyEnabled`, or an empty query alone. A verified 8.3.8 run resolved all concrete and binding-object runtime properties and verified three controlled write sequences, but returned zero stored rows because the SQLite historian sink reported `SQLITE_BUSY`/database locked. Preserve that distinction in every result.
