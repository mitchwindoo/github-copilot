# Data, Serialization, And Files

Read this before handling dates, datasets, JSON, Document values, logging, globals, CSV, XML, or Gateway filesystem data.

## Contents

- [Dates](#dates)
- [Datasets](#datasets)
- [JSON](#json)
- [Document Tag Values](#document-tag-values)
- [Loggers](#loggers)
- [Shared Globals](#shared-globals)
- [CSV And XML Parsing](#csv-and-xml-parsing)
- [Additional Customer Runtime Rules](#additional-customer-runtime-rules)

## Dates

`system.date` functions return real `java.util.Date` objects, and `format`/`parse` patterns follow Java `SimpleDateFormat`. Prefer them over Python `datetime` when dates flow into other Ignition APIs (history queries, tag writes, bindings).

Gateway-verified behavior:

```python
now = system.date.now()                                # java.util.Date
text = system.date.format(now, "yyyy-MM-dd HH:mm:ss")
iso = system.date.format(now, "yyyy-MM-dd'T'HH:mm:ss'Z'")
parsed = system.date.parse("2026-01-15 10:30:00")      # java.util.Date back
parsed2 = system.date.parse("2026-01-15 10:30", "yyyy-MM-dd HH:mm")
later = system.date.addMinutes(now, 90)
mins = system.date.minutesBetween(now, later)          # 90
days = system.date.daysBetween(now, system.date.addDays(now, 3))  # 3
inside = system.date.isBetween(now, system.date.addDays(now, -1), later)
millis = system.date.toMillis(now)                     # long
same = system.date.fromMillis(millis)
floor = system.date.midnight(now)                      # 00:00:00 same day
```

When a date offset comes from a tag, unpack and validate the tag value before calling `system.date.add*`:

```python
qv = system.tag.readBlocking([secondsTagPath])[0]
if not qv.quality.isGood() or qv.value is None:
    fail("bad seconds tag: %s" % qv.quality)
end = system.date.addSeconds(start, int(qv.value))
```

Validation notes:

- `system.date.addSeconds(start, qv)` failed: second arg could not be coerced to int.
- `system.date.addSeconds(start, qv.value)` worked for Int4 and Int8 values.
- A raw string tag value such as `"150"` failed; `int(qv.value)` worked.
- Missing tag `None` failed. Check quality/null before date math.

Watch for these date-parsing traps:

- Python `datetime.datetime` is not a `java.util.Date` for Ignition APIs. `system.date.format(py_dt, ...)`, `system.date.toMillis(py_dt)`, and `system.date.addDays(py_dt, 1)` all failed with `TypeError`.
- Java `SimpleDateFormat` tokens are case-sensitive. `yyyy-mm-dd HH:mm:ss` parsed the month position as minutes and silently produced a different date than `yyyy-MM-dd HH:mm:ss`.
- ISO strings ending in `Z` need a timezone-aware pattern such as `yyyy-MM-dd'T'HH:mm:ss.SSSX`. Quoting `'Z'` treats the character as a literal; the local test parsed the same text five hours apart from the `X` pattern.

Practical ISO parse pattern:

```python
text = "2025-09-02T13:05:07.832Z"
dt = system.date.parse(text, "yyyy-MM-dd'T'HH:mm:ss.SSSX")
```

### SQL Date/Time Parameters

Date/time behavior is partly database/driver-specific. Treat a single Gateway result as target-specific evidence, not universal SQL truth.

SQLite-backed Gateway validation notes:

- Inserting a `java.util.Date` into a `TIMESTAMP` column read back as `java.sql.Timestamp`; the SQLite storage type reported `integer`.
- Filtering a text timestamp column with `yyyy-MM-dd HH:mm:ss` strings worked for the test window.
- Filtering an epoch-millis integer column with `system.date.toMillis(...)` values worked for the test window.
- Filtering the local timestamp column with Java Date params also worked locally, but this must be revalidated on the target database/driver.
- Passing a string timestamp from the database into `system.date.minutesBetween(...)` failed; `system.date.parse(text, "yyyy-MM-dd HH:mm:ss")` produced a `java.util.Date` and the date math passed.
- Format patterns are case-sensitive: `yyyy-MM-dd HH:mm:ss` and `yyyy-mm-dd HH:MM:ss` produced different values.

Practical pattern:

```python
start = system.date.parse(str(startText), "yyyy-MM-dd HH:mm:ss")
end = system.date.parse(str(endText), "yyyy-MM-dd HH:mm:ss")

# Choose one target-validated storage/query strategy:
params_for_datetime_column = [start, end]  # only after target DB confirmation
params_for_text_column = [
    system.date.format(start, "yyyy-MM-dd HH:mm:ss"),
    system.date.format(end, "yyyy-MM-dd HH:mm:ss")
]
params_for_epoch_column = [
    system.date.toMillis(start),
    system.date.toMillis(end)
]
```

Do not infer time zone or instant correctness from `str(date)`. For Perspective displays, return Date objects, epoch millis, or explicitly formatted strings with a known zone/display policy.


## Datasets

Every `system.dataset` manipulation function returns a NEW dataset; the input is never mutated. Always reassign:

```python
headers = ["asset", "value"]
ds = system.dataset.toDataSet(headers, [["PUMP", 10], ["TANK", 42]])
ds2 = system.dataset.addRow(ds, ["MIX", 97])    # ds still has 2 rows
ds3 = system.dataset.setValue(ds2, 0, "value", 99)  # ds2 still has 10
ds4 = system.dataset.sort(ds3, "asset")
ds5 = system.dataset.deleteRow(ds4, 0)          # ds4 unchanged
narrow = system.dataset.filterColumns(ds3, ["value"])
```

`toPyDataSet` rows support index and column-name access:

```python
py = system.dataset.toPyDataSet(ds3)
total = 0
for row in py:
    total += row["value"]
```

Access validation notes:

- `ds.getValueAt(0, 1)` and `ds.getValueAt(0, "Count")` both worked.
- `py[0][1]`, `py[0]["Count"]`, `py.getValueAt(1, 0)`, and `py.getValueAt(1, "Name")` worked.
- `len(py)`, `ds.rowCount`, and `ds.columnCount` worked locally, but method calls (`getRowCount()`, `getColumnCount()`) remain the clearest portable style.
- `row["Missing"]` raised `ValueError: getColumnIndex(): Column 'Missing' not found in dataset`.

Dataset memory tags read back as `BasicDataset` values:

```python
qv = system.tag.readBlocking([datasetTagPath])[0]
if not qv.quality.isGood() or qv.value is None:
    fail("bad dataset tag")

ds = qv.value
color = ds.getValueAt(0, "Color")       # one cell
py = system.dataset.toPyDataSet(ds)
color2 = py[0]["Color"]                 # row/name access after conversion
```

Do not paste expression dataset syntax into Jython. Expression-style dataset access such as `read_ds[0, "Color"]` and `read_ds[0]` can fail because a `BasicDataset` is not subscriptable in Jython. Use `getValueAt(...)`, `toPyDataSet(...)`, or explicit loops.

`getValueAt(...)` returns one cell, not a column. For a whole column, use `system.dataset.filterColumns(ds, ["Color"])` or loop over row indexes and build a list.

Column-name lookup was case-insensitive on one tested Gateway for both `BasicDataset.getValueAt(row, name)` and PyDataset row-name access: `"Color"`, `"color"`, `"COLOR"`, and `"CoLoR"` all returned the same column. Missing columns still failed (`ArrayIndexOutOfBoundsException` for `getValueAt`, `ValueError` for PyDataset row access). A duplicate-column dataset with `["Color", "color"]` was allowed, but name lookup for both names returned the first column while index lookup could reach both. Avoid dataset columns that differ only by case, and validate expected canonical column names before lookup.

When configuring a Dataset memory tag through `system.tag.configure(...)`, use `dataType: "DataSet"`. `dataType: "Dataset"` can fail with an enum/configuration error.

When writing a Dataset memory tag, write a real Dataset/PyDataSet value and then read it back:

```python
headers = ["Asset", "Value", "Enabled"]
rows = [["Mixer_A", 10, True]]
ds = system.dataset.toDataSet(headers, rows)
qc = system.tag.writeBlocking([datasetTagPath], [ds])[0]
if not qc.isGood():
    fail("dataset write failed: %s" % qc)
qv = system.tag.readBlocking([datasetTagPath])[0]
if not qv.quality.isGood() or qv.value is None:
    fail("dataset readback failed: %s" % qv.quality)
```

Dataset tag write/readback validation:

- `BasicDataset` from `system.dataset.toDataSet(...)` wrote Good and read back Good.
- A `PyDataSet` wrote Good and read back as a Good `BasicDataset`.
- Perspective-style `list[dict]` and list-of-lists returned Good write QualityCodes locally, but the Dataset tag readback became bad `Error_TypeConversion("class org.python.core.PyList: Invalid DataType for Dataset.")` with `value == None`.
- JSON text returned an `Error_TypeConversion` write QualityCode.
- Converting the list-of-dicts into a Dataset first restored Good readback.

Dataset memory tag validation:

- Correct `system.tag.writeBlocking([datasetTagPath], [dataset])` returned Good and read back a two-row `BasicDataset`.
- One-item scalar forms such as `system.tag.writeBlocking(path, dataset)`, `system.tag.writeBlocking(path, [dataset])`, and `system.tag.writeBlocking([path], dataset)` may be accepted by some Gateway/script contexts, but they are not the reusable style.
- `system.tag.writeBlocking([path], [[dataset]])` returned Good but readback became bad `Error_TypeConversion("class org.python.core.PyList: Invalid DataType for Dataset.")` because the nested list became the value.
- Path/value count mismatches threw `Length of values does not match length of paths.`

Do not trust the write QualityCode alone for Dataset tags. Verify readback quality and row/column shape after writes, especially when the value originated from Perspective table rows.

SQL query results can be valid and empty. A zero-row `runPrepQuery` can return a `DatasetUtilities$PyDataSet` with `getRowCount() == 0`, `len(result) == 0`, and `bool(result) == False`. `result[0]` can raise `IndexError`; `result.getValueAt(0, 0)` can raise a Java `ArrayIndexOutOfBoundsException`.

Use a count guard before first-row access:

```python
def first_row_or_none(dataset):
    if dataset is None or dataset.getRowCount() <= 0:
        return None
    columns = [dataset.getColumnName(i) for i in range(dataset.getColumnCount())]
    row = dataset[0]
    return dict((col, row[col]) for col in columns)
```

For Perspective tables or JSON APIs, convert at the boundary:

```python
headers = [ds.getColumnName(i) for i in range(ds.getColumnCount())]
rows = []
py = system.dataset.toPyDataSet(ds)
for row in py:
    item = {}
    for header in headers:
        item[header] = row[header]
    rows.append(item)
```

For large scans where performance matters, prefer native `dataset.getValueAt(row, column)` loops and convert only the final bounded result.

`system.dataset.toDataSet(headers, rows)` requires every row to be a sequence with the same width as `headers`. Validation notes:

- Good: list rows and tuple rows with matching width.
- Bad: too-short and too-long rows raised `IndexError: Row 0 doesn't have the same number of columns as header list.`
- Bad: dictionary rows raised a Java `ClassCastException` because rows must be sequences, not mapping objects.

Normalize row shape before constructing the dataset:

```python
def normalize_rows(headers, rows):
    width = len(headers)
    out = []
    for idx, row in enumerate(rows):
        if len(row) != width:
            raise Exception("row %s has %s values; expected %s" % (idx, len(row), width))
        out.append(list(row))
    return out

ds = system.dataset.toDataSet(headers, normalize_rows(headers, rows))
```

### Dataset CSV Round Trips

Use `system.dataset.toCSV(..., forExport=True, ...)` when the result will be read by `system.dataset.fromCSV(...)`.

CSV round-trip validation:

- Plain CSV from `system.dataset.toCSV(ds, True, False, False)` was rejected by `fromCSV` with `CSV invalid format: expected #NAMES on line 1`.
- Hand-written plain CSV such as `ID,Name\n1,Alpha\n` was rejected for the same reason.
- Export CSV from `system.dataset.toCSV(ds, True, True, False)` included `#NAMES`, `#TYPES`, and `#ROWS` metadata and round-tripped Integer, String, Boolean, Date, comma-containing strings, and quoted strings.
- `forExport=True` overrode the `showHeaders` argument enough to include dataset metadata.
- A deliberately wrong `#ROWS` count still parsed locally and returned the actual two rows. Verify row/column counts after `fromCSV`; do not trust metadata alone.

```python
csv_text = system.dataset.toCSV(ds, True, True, False)
round_trip = system.dataset.fromCSV(csv_text)
if round_trip.getRowCount() != ds.getRowCount():
    fail("CSV dataset row count mismatch")
```

For arbitrary external CSV, parse with Python 2-compatible `csv`/Java libraries and build a dataset explicitly. Do not feed plain CSV directly to `fromCSV`.


## JSON

`system.util.jsonEncode(obj)` returns a `unicode` string. `system.util.jsonDecode(text)` returns dict-like/list-like objects; read fields defensively with `.get(...)`. Nested dict/list/number/unicode round trips were verified clean in Gateway scope.

Prefer explicit JSON/API output shapes for Ignition objects. Direct encoding can be lossy, locale-dependent, or unstable:

- `QualifiedValue` encoded as `{"value":..., "quality":{"code":...}, "timestamp":"Jun 10, 2026, ..."}`. This loses the readable quality string and uses a locale-style timestamp.
- `QualityCode` encoded only as `{"code":...}`. Include `qc.isGood()` and `str(qc)` yourself.
- `Date` encoded as a locale-style string. Use `system.date.format(...)` or `system.date.toMillis(...)` for machine-stable output.
- `Dataset` and `PyDataSet` encoded as `{columns:[...], rows:[[...]]}`. Convert to bounded list-of-dicts when Perspective tables or external APIs expect field-keyed rows.
- `BasicTagPath` direct encoding sometimes produced `{"pathParts":[...], "source":"..."}`, but browse dictionaries and dictionaries containing browse `fullPath` values hit recursion / Java `StackOverflowError` in local tests. Cast tag paths to `str(...)` before JSON/logging.

Safe conversion pattern:

```python
def qv_to_dict(qv):
    return {
        "value": qv.value,
        "quality": str(qv.quality),
        "qualityGood": qv.quality.isGood(),
        "timestampMillis": system.date.toMillis(qv.timestamp)
    }
```

When validating unicode through an HTTP API or console, return code points instead of glyphs; transport or console encoding can corrupt the display (verified mojibake on a clean Gateway-side value):

```python
decoded = system.util.jsonDecode(system.util.jsonEncode({"name": u"Mixer\u00b0C"}))
ords = [ord(ch) for ch in decoded.get("name")]  # [77,105,120,101,114,176,67]
```


## Document Tag Values

Document memory tags read back as `PyDocumentObjectAdapter`, not plain Python dictionaries. Write plain dictionaries to Document tags, but convert read values before returning them from helper scripts or JSON APIs.

Verified access rules:

```python
qv = system.tag.readBlocking([documentTagPath])[0]
doc = qv.value

asset = doc["asset"]                 # bracket access works
asset2 = doc.get("asset", None)      # get requires a default arg in this adapter
mode = doc["state"]["mode"]          # nested document bracket access works
first_alarm = doc["alarms"][0]["name"]
plain = doc.toDict()                 # dict/list nested shape
json_text = system.util.jsonEncode(plain)
```

Avoid:

```python
doc.get("asset")                     # TypeError: expected 2 args; got 1
system.util.jsonEncode(doc)          # encoded only the root keys in local test
dict(doc)                            # converted nested values inconsistently
```

If `toDict()` is unavailable in a target version/context, use a small recursive converter over `.keys()` and indexed arrays. Validate output types before feeding Perspective tables or external JSON APIs.

For Document tag edits, convert to a plain dict, change that dict, write the full document back, and verify readback:

```python
qv = system.tag.readBlocking([documentTagPath])[0]
if not qv.quality.isGood() or qv.value is None:
    fail("bad document tag: %s" % qv.quality)

plain = qv.value.toDict()
plain["state"]["mode"] = "Manual"
qc = system.tag.writeBlocking([documentTagPath], [plain])[0]
if not qc.isGood():
    fail("document write failed: %s" % qc)
```

Document write validation:

- Nested assignment into the adapter failed: `PyDocumentObjectAdapter object does not support item assignment`.
- Mutating a plain dict returned from `toDict()` did not change the tag until the full dict was written back.
- Writing a full plain dict and writing an edited `toDict()` dict both returned Good and changed readback.
- JSON text was accepted locally as a full Document write, but the reusable pattern should still prefer plain dictionaries because it preserves type intent and avoids assuming string parsing behavior across projects.


## Loggers

`system.util.getLogger(name)` returns an Ignition `LoggerEx` (its own `getName(String)` shadows `Class.getName()`; see the `type_name` helper). INFO/WARN/ERROR all reached wrapper.log at default Gateway logging levels.

Verification rules verified against wrapper.log:

- Flush latency is real: queries fired ~5 s after a successful write returned nothing; the same entries appeared minutes later, and a 30 s wait was sufficient. An empty immediate query is not confirmation the write failed.
- wrapper.log abbreviates leading logger segments logback-style: `LLM.JY024Probe` is recorded as `L.JY024Probe`. Filter by the leaf segment (`JY024Probe`) or by message text, never by the full dotted prefix.
- Use unique marker text in test log messages so message-text filtering is reliable.

Gateway/Web Dev code should use `system.util.getLogger(...)` for diagnostics. `system.perspective.print(...)` can resolve from Gateway/Web Dev scope, but the local 8.1.53 test raised `java.lang.IllegalArgumentException: No perspective session attached to this thread.` Use `system.perspective.print(...)` only when the code is actually executing on an attached Perspective session/page/view thread.

For logger exception arguments, distinguish Java `Throwable` from Jython/Python exceptions:

```python
from java.lang import Throwable

try:
    java_call()
except Throwable, t:
    logger.error("Java-backed failure", t)  # OK: second arg is a Java Throwable
```

Do not pass a Python/Jython exception object as the second logger argument:

```python
try:
    1 / 0
except Exception, e:
    logger.error("Python failure", e)  # TypeError: 2nd arg cannot be coerced to Throwable
```

Validation notes:

- `logger.warn(message, javaThrowable)` and `logger.error(message, javaThrowable)` succeeded and produced WARN/ERROR log entries.
- `logger.warn(message, pythonException)` and `logger.error(message, pythonException)` failed with `TypeError: 2nd arg can't be coerced to java.lang.Throwable`.
- `logger.warnf("... %s", pythonException)`, `logger.error(traceback.format_exc())`, and `logger.info(str(sys.exc_info()))` succeeded as text logging.

For Python exceptions, use `traceback.format_exc()` or string formatting unless the site already has a verified wrapper that converts Python exceptions to Java `Throwable`.


## Shared Globals

`system.util.getGlobals()` returns a Jython `stringmap` (no `getClass`) that persists across separate script executions within the same Gateway interpreter lifetime - a value stored by one HTTP-triggered execution was read back by a later, separate execution.

```python
g = system.util.getGlobals()
g["myFeature:state"] = {"marker": "run42", "storedAt": str(system.date.now())}
# ... later, separate execution ...
state = system.util.getGlobals().get("myFeature:state")
```

Treat it as in-memory cache, not durable storage: contents do not survive Gateway/interpreter restarts. Store JSON-simple values under unique, prefixed keys.

For Gateway queues shared between tag events, message handlers, and timer workers, store Java concurrent collections under unique keys:

```python
from java.util.concurrent import LinkedBlockingDeque, TimeUnit

key = "myFeature:queue"
queue = system.util.globals.setdefault(key, LinkedBlockingDeque(1000))

if not queue.offer({"path": str(tagPath), "value": currentValue.value}):
    system.util.getLogger("myFeature.Queue").warn("Queue full; dropping newest item")

item = queue.poll(50, TimeUnit.MILLISECONDS)
if item is not None:
    process_item(item)
```

Validation notes:

- `system.util.globals` and `system.util.getGlobals()` read/write the same backing dictionary.
- `.setdefault(key, LinkedBlockingDeque(2))` returned the existing queue on later calls and did not replace its capacity.
- `offer(...)` returned `False` when the bounded queue was full.
- `poll(timeout, TimeUnit.MILLISECONDS)` returned items in order, then `None` when empty.
- Plain dict payloads round-tripped through the Java queue.

Do not use `getGlobals()` as durable storage. Avoid storing user-defined Jython class instances there unless the project has a deliberate reload/replacement strategy; prefer primitives, plain dict/list data, or Java concurrent collections.


## CSV And XML Parsing

For small CSV payloads in Jython 2.7, use the Python 2-compatible stdlib:

```python
import csv
from StringIO import StringIO

reader = csv.DictReader(StringIO("asset,value\nPump_A,12.5\n"))
rows = []
for row in reader:
    rows.append({"asset": row.get("asset"), "value": float(row.get("value"))})
```

For UTF-8 CSV files in Jython 2, `csv` works on byte strings. Decode byte fields to unicode before returning rows to Perspective or APIs:

```python
import csv
from StringIO import StringIO

def decode_utf8(value):
    if value is None:
        return None
    if isinstance(value, unicode):
        return value
    return value.decode("utf-8")

csv_bytes = system.file.readFileAsString(path, "UTF-8").encode("utf-8")
reader = csv.DictReader(StringIO(csv_bytes))
rows = []
for row in reader:
    rows.append({
        "name": decode_utf8(row.get("name")),
        "unit": decode_utf8(row.get("unit")),
        "value": float(row.get("value"))
    })
```

When validating non-ASCII CSV data through an HTTP/API path, compare `ord()` values on decoded unicode strings; rendered glyphs can be corrupted by client display while the Gateway value is correct.

For XML, prefer Java XML APIs when portability matters:

```python
from java.io import StringReader
from org.xml.sax import InputSource
from javax.xml.parsers import DocumentBuilderFactory

factory = DocumentBuilderFactory.newInstance()
builder = factory.newDocumentBuilder()
doc = builder.parse(InputSource(StringReader(xml_text)))
items = doc.getElementsByTagName("asset")
```

Validation notes: `csv.DictReader(StringIO(...))` and `DocumentBuilderFactory` parsed the same two-row payload into identical row dictionaries in Gateway scope. Avoid Python 3-only parser examples and be explicit about string/float conversion.

## Additional Customer Runtime Rules

Use these detailed dataset, date, JSON, Document, logging, file, global-state, CSV, and XML rules.

- For `system.dataset.toDataSet(headers, rows)`, every row must be a sequence with exactly the same length as `headers`; do not pass dictionaries as rows. Normalize row shape before constructing the dataset.
- `PyDataSet` rows support both index and column-name access (`row[0]`, `row["Column"]`); missing column names raise `ValueError`. Use `dataset.getValueAt(row, "Column")` for large scans and convert rows to dictionaries at UI/API boundaries. SQL queries can return a valid zero-row `PyDataSet`; check `getRowCount()` or `len(result)` before `result[0]` / `getValueAt(0, ...)`.
- Dataset memory tags read back as `BasicDataset` values. Use `qv.value.getValueAt(row, column)` or convert with `system.dataset.toPyDataSet(qv.value)` before `row["Column"]`; expression-style dataset subscripts such as `dataset[0, "Column"]` are not Jython. `getValueAt()` returns one cell; use `filterColumns()` or a loop for whole-column output. Avoid dataset columns that differ only by case; name lookup can be case-insensitive and duplicate case-only names can resolve ambiguously.
- Write Dataset tags with real Dataset/PyDataSet objects, preferably from `system.dataset.toDataSet(...)` or `system.dataset` transforms. When configuring a Dataset memory tag, use `dataType: "DataSet"`. Do not write Perspective table `list[dict]`, list-of-lists, nested Dataset lists, or JSON text directly to a Dataset tag; invalid values can appear accepted until readback fails with `Error_TypeConversion`. Always verify Dataset tag readback quality and shape after writes.
- Prefer `system.date` over Python `datetime` for Gateway scripts. Python `datetime` is not a `java.util.Date` for `system.date.format`/`toMillis`/`add*`. `format`/`parse` patterns are case-sensitive Java `SimpleDateFormat` patterns; use `MM` for month and `mm` for minutes, and parse ISO `Z` timezone strings with `X`, not quoted `'Z'`. For `addSeconds`/`addMinutes`/similar calls using tag values, pass a checked numeric `.value` and cast strings with `int(...)`; do not pass the QualifiedValue, raw string, or `None`.
- For SQL date/time filters, inspect the target DB column and returned value type. Parse string timestamps with `system.date.parse(...)` before date math, and use target-validated DateTime parameters, formatted text, or epoch millis consistently; do not treat date stringification or SQLite-specific behavior as portable behavior.
- Every `system.dataset` manipulation function (`addRow`, `setValue`, `sort`, `deleteRow`, `filterColumns`, ...) returns a NEW dataset and leaves the input unchanged. Always reassign: `ds = system.dataset.addRow(ds, ...)`.
- `system.util.jsonEncode` returns a `unicode` string; `system.util.jsonDecode` returns dict-like/list-like objects. Read decoded fields defensively with `.get(...)`.
- Before JSON/API output, convert Ignition/Java objects to explicit primitives: QualifiedValue to `{value, quality, qualityGood, timestampMillis}`, QualityCode to `{good, text, code}`, Date to formatted text or millis, Dataset/PyDataset to bounded rows, and TagPath/BasicTagPath to `str(path)`.
- Document tag values read as `PyDocumentObjectAdapter`; use bracket access (`doc["key"]`) or `doc.get("key", default)`, and call `doc.toDict()` before JSON encoding or returning plain data. To edit a Document tag, mutate a plain dict from `toDict()`, write the full document back with `writeBlocking`, and verify readback; adapter/plain in-memory mutations do not persist without a write.
- `system.util.getLogger` writes land in wrapper.log with flush latency: an empty immediate log query is not proof the write failed. Wait and re-query before concluding absence, and filter by the logger leaf segment or message text, never the full dotted prefix, because wrapper.log abbreviates leading logger segments (`LLM.X` is recorded as `L.X`).
- For logger stack traces, pass a Java `Throwable` as the second logger argument. Do not pass a Jython/Python exception object as the second argument; log Python exceptions as formatted text/`traceback.format_exc()` unless a site-validated wrapper converts them to a Java `Throwable`.
- In Gateway, Web Dev, tag event, and Gateway Event scripts, use `system.util.getLogger(...)` for diagnostics. Do not use `system.perspective.print(...)` unless the code is running on an attached Perspective session/page/view thread; it can resolve in Gateway scope but fail with "No perspective session attached to this thread."
- For Windows file paths in Jython strings, use forward slashes, raw strings that do not end with a lone backslash, doubled backslashes, or `java.io.File`. Do not paste unescaped paths such as `C:\new\tag\file.txt`; escapes like `\n`, `\t`, and `\f` can silently corrupt the string.
- Gateway, Perspective, Web Dev, and Gateway Event file I/O use the Gateway filesystem. Keep paths configurable, validate before writes, and use `system.file.getTempFile()` or an approved configured folder for temporary files. For non-ASCII text, pass `"UTF-8"` explicitly on both reads and writes or use Java UTF-8 streams; do not trust default encoding round trips.
- `system.util.getGlobals()` persists values across separate executions in the same Gateway interpreter lifetime. Treat it as in-memory cache, not durable storage; store JSON-simple values under unique keys.
- For shared Gateway queues, store Java concurrent collections in `system.util.globals` / `system.util.getGlobals()` under unique keys. Use `.setdefault(key, LinkedBlockingDeque(capacity))`, check `offer(...)` for `False` when full, and use `poll(timeout, TimeUnit.MILLISECONDS)` so event/timer scripts never block indefinitely.
- For `system.dataset` CSV round trips, `fromCSV` expects Ignition dataset-export format with `#NAMES`/`#TYPES`/`#ROWS`; generate it with `toCSV(dataset, showHeaders, forExport=True, localized)`. Do not use `fromCSV` for arbitrary plain CSV; parse plain CSV and build a dataset explicitly. Verify row/column counts after `fromCSV`.
- For small CSV/XML parsing in Gateway Jython, use Python 2-compatible `csv` with `StringIO`, or Java XML APIs such as `DocumentBuilderFactory`; do not assume Python 3 parsing libraries or byte/string behavior. When parsing UTF-8 CSV through Python 2 byte strings, decode fields to `unicode` before returning them to Perspective or APIs.
