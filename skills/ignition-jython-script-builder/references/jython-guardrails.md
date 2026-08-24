# Jython Guardrails

## Contents

- Runtime
- Scope-Specific UI APIs
- Dates
- Datasets
- JSON
- Document Tag Values
- Loggers
- Shared Globals
- Tag History
- Alarms
- Tag Path Construction
- Project Library Calls
- Tags
- Tag Configuration
- Tag Event Scripts
- Browsing
- Perspective Context
- Named Queries
- Raw SQL Reads
- Database Writes
- Project Message Requests
- HTTP Client
- Third-Party Python And CPython Boundaries
- Async And Polling
- CSV And XML Parsing

## Runtime

Ignition 8.1 scripting commonly runs Jython/Python 2.7. Write for Python 2 compatibility unless the user provides a different runtime.

Avoid:

- f-strings
- type hints
- `pathlib`
- async/await
- match/case
- walrus operator
- Python 3-only standard library behavior

Use `%` formatting for maximum compatibility.

For broad Jython 2.7 compatibility, prefer Python 2 exception syntax:

```python
try:
    do_work()
except Exception, ex:
    print str(ex)
```

Jython console output such as `u'NO_CONN'` and `11L` is normal Python 2 representation for Unicode strings and long integers.

Project Library `code.py` files should be UTF-8 without BOM. A BOM at the start of `code.py` produced a Jython parse/load error (`no viable alternative at character ...`) when the module was loaded through the project script manager, even though the project resource existed.

### Project Library Lifecycle

Keep Project Library module top level boring: imports, constants, function/class definitions, and idempotent lightweight cache setup only. Put tag writes, database work, HTTP calls, file I/O, and operational side effects inside functions that the caller invokes explicitly.

Package/update validation notes:

- A Project Library module's top-level code ran when the module was first loaded by the project script manager.
- Calling the module function repeatedly did not rerun top-level code.
- Applying an updated `code.py` at the same script path and scanning the project caused the top-level code to run again before the next call used the updated marker.

This supports the production rule: do not rely on top-level side effects, and do not assume top-level code runs exactly once over Gateway lifetime. Treat top-level cache initialization as reloadable and idempotent.

```python
# OK at module top level
LOGGER_NAME = "project.area.script"

def run(payload):
    logger = system.util.getLogger(LOGGER_NAME)
    logger.info("doing work for %s" % payload.get("asset"))
    return {"ok": True}
```

Avoid:

```python
# Bad at module top level
system.tag.writeBlocking(["[default]Path"], [1])
rows = system.db.runPrepQuery("select ...", [], "db")
client = system.net.httpClient()
response = client.get("https://example.com")
```

Gateway-verified Jython 2.7 semantics (do not assume Python 3 behavior):

- `7 / 2 == 3` and `7 // 2 == 3`; use `7.0 / 2` or `float()` for real division (`3.5`).
- `2 ** 40` silently promotes to `long`.
- `str` and `unicode` are distinct types; `str + unicode` concatenation yields `unicode`.
- `%` formatting and `.format` both work; `print` as a statement compiles.
- `except Exception as exc` and the legacy `except Exception, exc` form both compile.
- `dict.has_key(...)` works, but prefer `key in dict`; dict comprehensions and `sorted(key=...)` work; `xrange` exists.
- f-strings and the walrus operator `:=` fail at compile time.
- `exec` is a statement. Inside a nested function with free variables, the call form `exec(code, namespace)` raises `SyntaxError: unqualified exec is not allowed`; use the qualified statement form `exec code in namespace`.

### File Path String Escapes

Jython string literals use Python escape rules. Windows paths pasted with single backslashes can compile while silently changing characters:

- `C:\new\tag\file.txt` turned `\n` into newline, `\t` into tab, and `\f` into form feed.
- `C:\Users\test\file.txt` preserved `\U` locally but still turned `\t` and `\f` into tab/form feed.
- `C:\Recipe In\WG10-CSV.csv` happened to preserve `\R` and `\W`, but do not rely on which backslash pairs are harmless.
- A raw string ending with one trailing backslash failed to compile.

Safe patterns:

```python
path1 = "C:/Users/test/file.txt"
path2 = r"C:\Users\test\file.txt"       # not ending in a lone backslash
path3 = "C:\\Users\\test\\file.txt"

from java.io import File
path4 = File(File("C:\\Recipe In"), "WG10-CSV.csv").getPath()
```

For type logging, never call `value.getClass().getName()` directly. It raises `getName(): expected 1 args; got 0` when the Java class defines its own `getName` (verified on `LoggerEx`), and pure Jython objects such as the `stringmap` returned by `system.util.getGlobals()` have no `getClass` at all. Use:

```python
def type_name(value):
    try:
        return str(value.getClass().getName())
    except:
        pass
    try:
        return str(value.__class__.__name__)
    except:
        return str(type(value))
```

### Gateway File I/O And Encoding

In Gateway, Web Dev, Gateway Event, and Perspective scripts, file paths refer to the Gateway host filesystem. Do not assume a path on the Designer or browser user's PC exists on the Gateway.

Keep file paths configurable and validate before writes. Use `system.file.getTempFile()` or an approved configured folder for temporary files. Avoid hard-coded absolute paths in reusable scripts.

For text with any non-ASCII character, pass an explicit encoding on both write and read:

```python
path = system.file.getTempFile("txt")
text = u"alpha\nDegree \u00b0C\nCheck \u2713\n"

system.file.writeFile(path, text, False, "UTF-8")
read_back = system.file.readFileAsString(path, "UTF-8")
if read_back != text:
    raise Exception("UTF-8 file round trip failed")
```

Java UTF-8 streams can preserve `\u00b0` and `\u2713`, while default `system.file` round trips may not preserve every character. The reusable rule is simple: do not rely on default encoding round trips; specify `"UTF-8"` or use Java streams.

When returning file-read values through an API or console, compare `ord()` values if the visible glyphs look corrupted. A clean Gateway-side unicode value can still display as mojibake after client transport.

### Java-Backed Exceptions

Do not assume Python `except Exception` catches failures from Ignition Java-backed system functions. Java exceptions from `system.db.runPrepUpdate()` and `system.util.sendRequest()` can escape `except Exception`, but can be caught by `except java.lang.Exception` and by a bare diagnostic `except:`.

Prefer explicit Java exception handling around expected Ignition API failures:

```python
import java

try:
    rows = system.db.runPrepUpdate(sql, params, databaseName)
except java.lang.Exception, exc:
    fail("database write failed: %s" % exc)
```

For broad diagnostic/probe wrappers that may hit Java runtime/indexing errors, catch `java.lang.Throwable` explicitly. Indexing a zero-row `PyDataSet` through `getValueAt(0, 0)` can raise `java.lang.ArrayIndexOutOfBoundsException`; a wrapper without a Java catch can let the error escape, while `except java.lang.Throwable, exc:` captures it.

Use a final bare `except:` only for narrow diagnostic wrappers that must record unexpected errors, and re-raise when the calling context should fail.

## Scope-Specific UI APIs

Do not use Vision/client UI functions in Gateway, Web Dev, tag event, or Perspective scripts. Gateway/Web Dev validation has found these lookups fail:

- `system.gui` -> `AttributeError`
- `system.vision` -> `AttributeError`
- `system.util.invokeLater` -> `AttributeError`

`system.util.invokeLater` is documented for Vision Client scope and runs on the GUI/event-dispatch thread. Perspective scripts execute on the Gateway side of a Perspective session, not in the browser DOM. Use Perspective component events, component/root custom methods, message handlers, params, bindings, or returned data instead of Vision GUI APIs.

`system.perspective` may be visible as a package outside a Perspective session; visibility alone is not confirmation that a function has a valid page/session context. Validate Perspective behavior in the actual Perspective event/transform/message context.

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

## Tag History

`system.tag.queryTagHistory` rows are not confirmation of stored history. With an interpolated `returnSize`, the query returned a dataset with 10 rows (`t_stamp` plus the tag column) where every value cell was null, because the memory tag had no history provider. On runner `0.3.137+`, the equivalent `historyProbe` response names this as good-sample evidence. When good-quality availability matters in direct Jython, use a strict Count query and require a positive good-sample count:

```python
end = system.date.now()
start = system.date.addMinutes(end, -60)
ds = system.tag.queryTagHistory(
    paths=[tagPath],
    startDate=start,
    endDate=end,
    returnSize=1,
    aggregationMode="Count",
    returnFormat="Wide",
    includeBoundingValues=False,
    noInterpolation=True,
    ignoreBadQuality=True
)
goodStoredSamples = 0
for row in range(ds.getRowCount()):
    for col in range(1, ds.getColumnCount()):
        value = ds.getValueAt(row, col)
        try:
            if float(value) > 0:
                goodStoredSamples += float(value)
        except:
            pass
if goodStoredSamples <= 0:
    fail("No good-quality counted historian samples for %s; verify history is enabled and inspect bad-quality rows separately if needed" % tagPath)
```

Use caller-selected value queries for diagnostics only: non-null cells, `LastValue`, and displayed chart-like values can be interpolated, bounded, aggregated, or quality-filtered depending on query settings. Query tag instance paths only. A `_types_` UDT definition path returns no usable history even when the query itself succeeds.

## Alarms

Use `system.alarm.queryStatus(...)` for current alarm state only. It is not alarm history; use `system.alarm.queryJournal(...)` only when a journal/profile exists and the task requires historical transitions.

Always constrain current-alarm queries with at least one explicit filter such as `provider`, `displaypath`, or `source`, and usually a `state` list:

```python
results = system.alarm.queryStatus(
    provider=[tagProvider],
    displaypath=[displayRoot + "/*"],
    state=["ActiveUnacked", "ActiveAcked"]
)
ds = results.getDataset()
```

`AlarmQueryResult` is list-like and also provides `getDataset()`. For realtime `queryStatus` calls, the Ignition 8.1 object reference and target validation may show dataset columns `EventId`, `Source`, `DisplayPath`, `EventTime`, `State`, and `Priority`.

Use PyAlarmEvent methods/keys instead of assuming plain dictionaries:

```python
for alarm in results:
    name = alarm.getName()
    state = str(alarm.getState())
    source = str(alarm.getSource())
    display = str(alarm.getDisplayPathOrSource())
    event_id = str(alarm["EventId"])
```

Alarm status validation:

- A memory tag alarm activated and was found with `provider=[...]` plus `displaypath=["LLM Tests/.../*"]`.
- `queryStatus(..., state=["ActiveUnacked", "ActiveAcked"], priority=["High"])` returned the active event.
- Custom alarm properties such as `assetName` were available through `alarm.get("assetName")`, `alarm.contains("assetName")`, `defined=["assetName"]`, and `all_properties=[("assetName", "=", "...")]`.
- `alarm.getName()`, `getLabel()`, `getDisplayPath()`, `getSource()`, `getPriority()`, `getState()`, `getLastEventState()`, `getId()`, `isAcked()`, `isCleared()`, `isShelved()`, and `getNotes()` all returned usable values.
- After writing the source value below the setpoint, the runtime `.IsActive` tag became false, but `queryStatus` still returned one event as `Cleared, Unacknowledged`. The active-state query returned zero rows. Do not equate "one queryStatus event exists" with "alarm is active."
- `getActiveData()` returned an event-data object containing the active transition details; `getClearedData()` and `getAckData()` were `None` before those transitions existed.

For historical alarm rows, use a bounded date range and `includeData=True` when the script needs event values or associated data:

```python
end = system.date.now()
start = system.date.addHours(end, -1)
results = system.alarm.queryJournal(
    startDate=start,
    endDate=end,
    provider=[tagProvider],
    displaypath=[displayRoot + "/*"],
    includeData=True,
    includeSystem=False
)
```

`queryJournal` returns separate transition rows. In a one-alarm validation, it returned two rows with the same `EventId`: active (`EventState == 0`) and clear (`EventState == 1`). This differs from `queryStatus`, which groups current alarm state.

For `PyAlarmEvent`, simple key/string access is preferred:

```python
for event in results:
    event_value = event.get("eventValue")
    asset_name = event.get("assetName")
    state = event.get("EventState")
```

For the lower-level EventData objects returned by `getActiveData()` and `getClearedData()`, string-key `.get(...)` is not the same API:

```python
from com.inductiveautomation.ignition.common.alarming.config import CommonAlarmProperties
from com.inductiveautomation.ignition.common.alarming.evaluation import EventProperty

active_data = event.getActiveData()
event_value = active_data.get(CommonAlarmProperties.EventValue)
event_value2 = active_data.get(EventProperty.createStatic(CommonAlarmProperties.EventValue, False))
```

For unknown/custom associated data, iterate the EventData property values:

```python
active_data = event.getActiveData()
associated = {}
for property_value in active_data:
    associated[property_value.getProperty().getName()] = property_value.getValue()
```

Alarm journal data validation:

- `event.get("eventValue")` returned `15.5` for the active journal event and `0.0` for the clear event when `includeData=True`.
- `event.get("assetName")` returned the configured associated data.
- `event.getActiveData().get("eventValue")` failed with `1st arg can't be coerced to com.inductiveautomation.ignition.common.config.Property`.
- `activeData.get(CommonAlarmProperties.EventValue)`, `activeData.get(EventProperty.createStatic(CommonAlarmProperties.EventValue, False))`, and iterating property values all returned `15.5`.

## Tag Path Construction

For Gateway, Web Dev, and Project Library helper scripts, prefer fully qualified tag paths assembled from configurable parts:

```python
def clean_segment(name, value):
    text = str(value).strip("/")
    if text == "" or "[" in text or "]" in text or "//" in text:
        fail("bad %s: %s" % (name, value))
    return text

def make_tag_path(provider, root, instance, member):
    return "[%s]%s/%s/%s" % (
        clean_segment("provider", provider),
        clean_segment("root", root),
        clean_segment("instance", instance),
        clean_segment("member", member)
    )
```

Path validation:

- Fully qualified generated paths such as `[Sample_Tags]LLM Tests/<run>/Tank_A/Level` read Good values and supported write/readback.
- A path without provider brackets (`LLM Tests/<run>/Tank_A/Level`) read Good in this Web Dev project because a project default provider resolved it locally. Treat this as non-portable; Gateway/tag contexts may not have a project default provider.
- `[~]LLM Tests/<run>/...` failed from Web Dev/Gateway script scope as `Tag provider '~' not found`.
- `[.]Level` failed from Web Dev/Gateway script scope as `Tag provider '.' not found`.
- `system.tag.browse(...)` returned dict items whose `fullPath` values should be converted with `str(...)` before appending members, logging, or JSON output.

Use `[.]` and `[~]` only where Ignition supplies tag-relative context, such as tag bindings, UDT definitions, and tested tag event scripts. Library functions should accept the base path/provider as an argument instead of assuming a relative tag context.

## Project Library Calls

Ignition Project Library paths follow the Designer tree.

If the tree is:

```text
Project Library
  diagnostics
    opcDevices
```

call:

```python
diagnostics.opcDevices.refresh(force=True, reason="manual")
```

If the script is at the root:

```text
Project Library
  opcDevices
```

call:

```python
opcDevices.refresh(force=True, reason="manual")
```

Do not recommend:

```python
import diagnostics.opcDevices
reload(diagnostics.opcDevices)
```

Do not rely on `import <rootProjectScript>` or `reload(<rootProjectScript>)` for Project Library refresh workflow. The Project Library object is not a normal Python module.

After creating, moving, or renaming project scripts, save the project and reset/reopen the Designer Script Console before running the script.

### Tag Event Scope

Tag event scripts are Gateway-scoped but not project-scoped unless the Gateway Scripting Project is configured. In tag scope, these functions return the Gateway Scripting Project name, or an empty string when it is not configured:

```python
system.util.getProjectName()
system.project.getProjectName()
```

When the Gateway Scripting Project is configured to the project that owns the library, call the library path only:

```python
myFuncs.thankYou(user=ackedBy)
```

Do not prepend the project name:

```python
projectName.myFuncs.thankYou(user=ackedBy)  # wrong
```

Do not try to import the Project Library from a tag event:

```python
import myFuncs  # wrong workflow
```

Validation notes for a Gateway with no Gateway Scripting Project configured:

- `system.util.getProjectName()` and `system.project.getProjectName()` both returned `""` from a tag event.
- Direct `llm.jy029scope_...record(...)` failed with `global name 'llm' is not defined`.
- `<projectName>.llm...` failed with a project-name global not defined.
- `import llm...` failed with `No module named llm`.
- An internal Java `ProjectScriptManager` workaround could call the project module after the file was rewritten without BOM, but that is not the production pattern to teach in the skill. Prefer configuring the Gateway Scripting Project, or move the trigger logic into a project Gateway Event script that already has project context.

Project Gateway Event scripts are different from tag event scripts: they run on the Gateway but are project resources. Use them for project-owned timer/message/tag-change logic that needs the project library. Keep event bodies thin and pass event context into library functions explicitly; do not assume UI objects such as `event.source` exist in Gateway/tag scope.

### Expression Tags And `runScript`

For expression tags or expression bindings, prefer the documented argument form:

```text
runScript("library.module.function", 1000, arg1, arg2)
```

The first argument should be a string. The expression function passes any remaining arguments positionally; keyword invocation is not supported.

Expression-tag validation notes:

- `runScript("len", 1000, "abc")` returned `3` with Good quality.
- Legacy `runScript("len('abc')", 1000)` also returned `3`.
- `runScript("system.date.toMillis", 1000, now())` returned a Good millisecond value.
- A project library function path in an expression tag returned `Error_ExpressionEval(...)` when no Gateway Scripting Project was configured, even though the function existed in the project.
- A non-string/eager form like `runScript(len("abc"), 1000)` returned a Good value in one narrow case, which is still a trap: it does not confirm a Project Library function path was called. Do not generate it.
- Expression tags using `runScript("system.date.toMillis", 5000, now())` changed on each read interval around 1.6 seconds apart on the default tag group, while `now(5000)` did not change during the same short window. This shows that a long `runScript` poll value is not a reliable scheduler when the expression/tag group/dependencies are still evaluating.

Expression tags that call Project Library scripts have the same Gateway Scripting Project dependency as tag event scripts. If a reusable design needs periodic script work, prefer a Gateway timer/tag-change event that writes result tags, a tag group configured for the desired cadence, or a short `runScript` expression that calls a fast function in the configured Gateway Scripting Project. Keep heavy work out of expression tags.

## Tags

`system.tag.readBlocking()` returns QualifiedValue objects:

- `.value`
- `.quality`
- `.timestamp`

Good quality does not guarantee non-null value. Check both quality and nullness for critical reads.

`system.tag.readBlocking(path)` with a single string path still returned a list. Missing paths returned a bad QualifiedValue (`Bad_NotFound`) with `value == None`, not an exception. Always iterate the returned list and inspect each QualityCode.

`system.tag.writeBlocking()` returns quality results. Check all of them. Missing paths, expression/read-only tags, and datatype mismatches returned `Bad_NotFound`, `Bad_ReadOnly`, or `Error_TypeConversion` QualityCodes instead of throwing in local tests.

Never use truthiness to decide whether a read/write succeeded. Validation notes:

- `bool(qv)` was `True` for both good and bad QualifiedValues.
- `bool(qv.quality)` was `True` even when quality was `Bad_NotFound`.
- `bool(qc)` was `True` even when a write returned `Bad_NotFound`.
- Valid values such as `0`, `False`, and `""` were falsey even with Good quality.

Use explicit checks:

```python
qv = system.tag.readBlocking([tagPath])[0]
if not qv.quality.isGood():
    fail("bad read quality: %s" % qv.quality)
value = qv.value

qc = system.tag.writeBlocking([tagPath], [value])[0]
if not qc.isGood():
    fail("bad write quality: %s" % qc)
```

Scalar write forms such as `system.tag.writeBlocking(path, value)` may be accepted by some Gateway/script contexts, but reusable scripts should still use path/value lists:

```python
results = system.tag.writeBlocking([tagPath], [newValue])
for qc in results:
    if not qc.isGood():
        fail("write failed: %s" % qc)
```

When copying values from one tag to another, prefer explicit `.value` extraction unless you intentionally want to pass the full QualifiedValue:

```python
qv = system.tag.readBlocking([sourcePath])[0]
if not qv.quality.isGood():
    fail("bad source quality: %s" % qv.quality)
system.tag.writeBlocking([destPath], [qv.value])
```

Validation notes:

- `system.tag.writeBlocking([dest], [qv.value])` wrote the value.
- `system.tag.writeBlocking([dest], readBlocking([source]))` also wrote the value because the source read list exactly paralleled the destination path list.
- `system.tag.writeBlocking([dest], qv)` scalar form also worked locally.
- `system.tag.writeBlocking([dest], [readBlocking([source])])` failed with `Error_TypeConversion` because it wrapped the list as one nested value.

Use the explicit `.value` form as the default skill pattern. Passing QualifiedValues can be valid when quality/timestamp propagation is intentional, but it should be a deliberate choice and still requires returned QualityCode checks.

`system.tag.exists()` does not confirm a tag value is usable.

### Async Tag Reads/Writes

`system.tag.readAsync()` and `system.tag.writeAsync()` return `None`; the callback is where continuation logic belongs. Do not write code that expects an async call to return values to the next line.

Validation notes:

- `readAsync([path], callback)` returned `None`.
- The read callback received a list of QualifiedValues and wrote a result tag.
- `writeAsync([path], [value], callback)` returned `None`.
- The write callback received a list of QualityCodes and wrote a result tag.

Use blocking calls when the current script needs the value/result immediately:

```python
qv = system.tag.readBlocking([tagPath])[0]  # use now
```

Use async calls only when the callback can own the next step:

```python
def read_done(qvs, resultPath=resultPath):
    import system
    qv = qvs[0]
    if qv.quality.isGood():
        system.tag.writeBlocking([resultPath], ["value=%s" % qv.value])

system.tag.readAsync([tagPath], read_done)
```

Pass state into callbacks explicitly through default args, callable objects, or other stable storage. Import `system` inside callbacks for Gateway-event portability; a Web Dev callback may work without it, but Gateway timer/tag callback scope is known to be less forgiving.

When comparing source tags to MQTT/reference/output tags, normalize types when appropriate:

```python
def same_value(actual, expected):
    return str(actual) == str(expected)
```

Do not create siblings whose names differ only by case. A local `system.tag.configure(..., "a")` test treated `ObjDataType` and `ObjDatatype` as the same path: the second configure returned a collision and reading the case-variant path resolved to the first tag.

## Tag Configuration

Use `system.tag.getConfiguration()` for inspection. Do not mutate the returned object and pass it back into `system.tag.configure()`.

Build a fresh minimal payload:

```python
cfg = {
    "name": "<instanceName>",
    "tagType": "UdtInstance",
    "typeId": "<udtTypeId>"
}
system.tag.configure("[<tagProvider>]<parentFolder>", [cfg], "m")
```

The configure path is the parent folder. The child name is inside the config.

Do not treat `getConfiguration()` output as portable JSON. Validation notes:

- `path` was a `BasicTagPath`.
- `tagType`, `dataType`, and alarm `mode` were Java/Ignition-backed objects.
- `system.util.jsonEncode(original_cfg)` failed with recursion depth / Java `StackOverflowError`.
- A deep-copied config whose `name` was changed but whose `path` was retained returned `Error_Configuration(...)` because the copied path object was not coercible back into a `TagPath`.

Do not deep-copy/rename a returned config and write it as a clone. Build a fresh minimal config. If you are intentionally salvaging a copied config in a controlled migration, remove `path` and internal/generated fields first and verify every QualityCode; fresh minimal config is still preferred.

Do not overwrite `tagType` on a returned config object. Those objects can contain Ignition-backed internal types; structural mutation can cause `TagObjectType` cast errors or null path errors.

For targeted edits, use collision policy `"m"` and check every returned quality code:

```python
results = system.tag.configure(parentPath, [cfg], "m")
for qc in results:
    if not qc.isGood():
        raise Exception("Configure failed: %s" % qc)
```

Collision-policy validation:

- `"m"` with a partial config preserved unspecified properties (`dataType`, `valueSource`, `documentation`, `enabled`, `engUnit`) and applied the specified value change.
- `"o"` with a partial config replaced the tag configuration and removed unspecified properties, even though the write QualityCode was Good.
- `"i"` returned Good with an ignored/collision message and left the tag unchanged.
- `"a"` returned a bad QualityCode instead of throwing in this run and left the tag unchanged.

Reusable rule: do not use partial `"o"` for small edits. Use fresh complete configs for intentional replacement, `"m"` for targeted edits, and always inspect returned QualityCodes plus readback/config shape.

For UDT instance parameter overrides, pass either the scalar value or a full typed object:

```python
system.tag.configure("[<provider>]<folder>", [{
    "name": "Pump001",
    "tagType": "UdtInstance",
    "typeId": "<relative/type/path>",
    "parameters": {"AssetName": "MOTOR_A"}
}], "m")

system.tag.configure("[<provider>]<folder>", [{
    "name": "Pump002",
    "tagType": "UdtInstance",
    "typeId": "<relative/type/path>",
    "parameters": {"AssetName": {"dataType": "String", "value": "MOTOR_B"}}
}], "m")
```

Do not use a value-only object:

```python
"parameters": {"AssetName": {"value": "MOTOR_A"}}  # wrong
```

Validation notes: the value-only object configured with Good quality but `getConfiguration()` reported `{datatype=Integer, value=null}`. Direct scalar and full `dataType` object produced `{datatype=String, value=...}`.

## Tag Event Scripts

For Ignition 8.1 tag event JSON, use `eventScripts` with lowercase `eventid` values such as `valueChanged`.

Store script text as the indented body of the event function:

```python
cfg = {
    "name": "<tagName>",
    "tagType": "AtomicTag",
    "valueSource": "memory",
    "dataType": "Int4",
    "eventScripts": [{
        "eventid": "valueChanged",
        "script": "\tif initialChange:\n\t\treturn\n\t# script body..."
    }]
}
```

For `valueChanged`, guard `initialChange`, check `missedEvents`, and treat `currentValue` and `previousValue` as QualifiedValues. Use `.value` for the value and `.quality.isGood()` before critical logic. `currentValue == 10` can be false while `currentValue.value == 10` is true.

Ignition 8.1.32+ `valueChanged` behavior is value-change focused. On the local 8.1.53 Gateway, a write from `10` to `10` returned Good quality but did not increment the event counter; a later write from `10` to `11` did. Do not use same-value writes as a trigger mechanism.

Treat `tagPath` as a full string path unless the context confirms it is a richer object. For same-folder tag event reads/writes, prefer Ignition relative paths such as `[.]Sibling` when the target context validates that scope:

```python
countQv = system.tag.readBlocking(["[.]EventCount"])[0]
system.tag.writeBlocking(["[.]EventCount", "[.]Status"], [int(countQv.value) + 1, "updated"])
```

Use string operations on `str(tagPath)` when you need to derive paths outside the same folder or need explicit path evidence.

Keep tag event scripts short. Move heavy logic to a Project Library or Gateway script and call it from the event.

### UDT Parameters And Curly Braces

In UDT tag event scripts, prefer the modern parameter dictionary:

```python
asset_name = tag["parameters"]["AssetName"]
```

Validation notes: a UDT tag event using `tag["parameters"]["AssetName"]` read `MOTOR_A`, then after a parameter merge update read `MOTOR_B` on the next event without restarting the UDT.

Avoid legacy curly-brace parameter expansion inside UDT tag event bodies:

```python
asset_name = {AssetName}  # wrong for string parameters
```

Validation notes: with `AssetName = "MOTOR_A"`, the legacy line failed as `global name 'MOTOR_A' is not defined`, because the expanded string was not quoted Python.

Also avoid Python `.format(...)` placeholders in UDT tag event bodies:

```python
text = "{0}_ACK".format(currentValue.value)  # unsafe in UDT tag events
```

Validation notes: on plain memory tag event scripts, `{0}` `.format`, `%` formatting, dict literals, and concatenation all ran. On UDT tag event scripts, `%` formatting, concatenation, and a simple dict literal ran, but the `{0}` `.format` case never updated result tags (`EventCount=0`, `Status="Waiting"`). Use `%` formatting or concatenation in UDT tag events, or delegate formatting to a Project Library function after project scope is verified.

## Browsing

Use `results.getResults()` and treat each browse item as a dictionary. Browse items may be dictionaries, and attribute access such as `item.fullPath` can fail.

```python
results = system.tag.browse(root, {"recursive": True})
for item in results.getResults():
    name = str(item["name"])
    full_path = str(item["fullPath"])  # BasicTagPath -> string
```

Do not JSON-encode browse result dictionaries directly. Validation notes:

- `item["fullPath"]` was a `BasicTagPath`.
- `system.util.jsonEncode(item)` failed with recursion / Java `StackOverflowError`.
- `system.util.jsonEncode({"fullPath": item["fullPath"]})` also failed in the fixture browse.
- `results.getContinuationPoint()` existed and returned `""` for this completed browse; `results.hasMoreResults()` did not exist in the local wrapper.

Before browsing a provider root, verify the provider exists. A missing-provider browse may not throw in every context; it can return no useful nodes and lead the script to make a false "no tags exist" conclusion.

For UDT auto-discovery, browse a bounded root with recursive UDT instance filters and then read member paths from discovered instances:

```python
root = "[<provider>]<folder>"
type_id = "<relative/typeId>"
results = system.tag.browse(root, {
    "recursive": True,
    "tagType": "UdtInstance",
    "typeId": type_id
})

instances = []
for item in results.getResults():
    instances.append(str(item["fullPath"]))

member_paths = []
for base in instances:
    member_paths.append(base + "/Speed")
    member_paths.append(base + "/Nested/State")
qvs = system.tag.readBlocking(member_paths)
```

Validation notes: `{"recursive": True, "typeId": type_id}` by itself returned UDT instances plus child folders/member tags. Pair `typeId` with `tagType: "UdtInstance"` when the goal is an instance list. Cast `fullPath` to string before concatenating child paths. Use `maxResults`/caps for broad recursive browses and check continuation metadata when present.

Browse filters are simple key/value filters, not SQL-like predicates:

- `name` supports `*` wildcards.
- A Python expression such as `{"tagType": "Folder"} or {"tagType": "UdtInstance"}` evaluates to the first non-empty dict, so it browsed only folders locally.
- Duplicate keys in one dict keep only one effective value. A local duplicate `tagType` dict behaved like the last `tagType` value.
- Browse does not filter UDT instances by the value of a child member tag. Browse the instances first, then read member paths and filter in script.

Example:

```python
instances = []
for item in system.tag.browse(root, {
    "recursive": True,
    "tagType": "UdtInstance",
    "typeId": type_id
}).getResults():
    instances.append(str(item["fullPath"]))

status_paths = [path + "/Status" for path in instances]
qvs = system.tag.readBlocking(status_paths)
active = []
for path, qv in zip(instances, qvs):
    if qv.quality.isGood() and qv.value is True:
        active.append(path)
```

## Perspective Context

Perspective scripts run on the Gateway, not in the browser. Any helper path or filesystem path must be valid on the Gateway.

Keep Perspective button actions thin:

```python
project.someModule.runForView(self, someArg)
```

Bind an output or status text area to a view custom property when troubleshooting so failures are visible immediately.

Perspective message handlers belong under a component/root `scripts.messageHandlers` array, not under component `events`. Match the send scope to the handler scope flags:

```python
# Button/event script
payload = {"kind": "select", "baseTagPath": baseTagPath}
system.perspective.sendMessage("select-device", payload=payload, scope="page")
```

```json
{
  "messageType": "select-device",
  "pageScope": true,
  "sessionScope": false,
  "viewScope": false,
  "script": "\tkind = str(payload.get('kind', ''))\n\tself.view.custom.lastKind = kind"
}
```

A page-scoped handler did not receive a session-scoped send in the tested Gateway context. Treat `payload` as dict-like and read fields defensively.

For table/list detail workflows, keep selected state on the parent/root handler. A tested Table `onSelectionChange` script used `self.props.selection.data` as the selected-row source and fell back to `event.data` defensively before sending the same page-scoped payload shape used by list/card buttons. If the handler needs helper row fields, declare them as visible or hidden table columns; table selection did not reliably carry undeclared row keys.

`system.perspective.sendMessage` is context-sensitive. From Gateway/Web Dev scope in local tests:

- Default/page-scope send failed with `No perspective session attached to this thread`.
- Session-scope send without a target also failed with `No perspective session attached to this thread`.
- View-scope send failed with `No perspective view attached to this thread`.
- A fake `sessionId` failed with `Perspective session ... not found`.
- Some invalid or uppercase scope strings returned `None` without verifying delivery.

Do not use a successful return value from `system.perspective.sendMessage` as confirmation that a component handler ran. Validate handler behavior with a visible property update, result tag, log marker, or browser interaction. For Gateway/tag-to-Perspective messaging, a project Session Event message handler can be the bridge only when it already exists or has target confirmation: Gateway/tag script calls `system.util.sendMessage(..., scope="S")`; the Session Event handler calls `system.perspective.sendMessage(...)` into open component handlers. Do not package Project Gateway Event or Perspective Session Event handlers from guessed `data.bin` shapes through the Web Dev runner.

Use `system.perspective.getSessionInfo()` for Perspective sessions. It returned a list of session dictionaries in Gateway/Web Dev scope, including a Designer Perspective session with fields like `id`, `project`, `sessionScope`, `activePages`, and `pageIds`. `system.util.getSessionInfo()` returned a PyDataSet for Designer/Vision sessions (`username`, `project`, `address`, `isDesigner`, `clientId`, `creationTime`). Do not treat these two functions as interchangeable.

Perspective custom methods live under component/root `scripts.customMethods`. Use `name`, `params`, and an indented function-body `script`:

```json
{
  "name": "formatResult",
  "params": ["marker", "value"],
  "script": "\tresult = '%s:%s' % (marker, value)\n\treturn result"
}
```

A custom method attached to the same component was successfully called from that component's binding transform as:

```python
return self.formatResult(value["marker"], value["value"])
```

Cross-component custom method calls were not verified in this test set; prefer same-component calls or Project Library functions until the target call path is verified.

For nullable Perspective component values such as Dropdown `props.value`, use Python `None`, not `null` or the string `"null"`. A reusable no-selection check should guard `len(...)` and avoid bare truthiness because `0` and `False` can be valid selected values:

```python
def is_no_selection(value):
    if value is None:
        return True
    try:
        return len(value) == 0
    except:
        return False
```

For Perspective table data, prefer a list of dictionaries keyed by the table `columns[].field` names. Convert Ignition datasets explicitly before assigning to table props:

```python
def dataset_to_rows(dataset):
    columns = []
    for col in range(dataset.getColumnCount()):
        columns.append(str(dataset.getColumnName(col)))
    rows = []
    for row_index in range(dataset.getRowCount()):
        row = {}
        for col_index in range(len(columns)):
            row[columns[col_index]] = dataset.getValueAt(row_index, col_index)
        rows.append(row)
    return rows
```

`system.dataset.toPyDataSet(dataset)[0]["ColumnName"]` worked for column-name lookup in the tested Gateway context, but still return plain row dictionaries to Perspective when table rows need to be portable and inspectable.

## Named Queries

In Gateway/Perspective contexts, pass the project name, Named Query path, and parameters as configuration instead of hard-coding them inside helper logic:

```python
def fail(reason):
    raise Exception("NAMED QUERY SCRIPT FAILURE: " + str(reason))

def dataset_to_rows(dataset):
    columns = []
    for col in range(dataset.getColumnCount()):
        columns.append(str(dataset.getColumnName(col)))
    rows = []
    for row_index in range(dataset.getRowCount()):
        row = {}
        for col_index in range(len(columns)):
            row[columns[col_index]] = dataset.getValueAt(row_index, col_index)
        rows.append(row)
    return columns, rows

def run_named_query(projectName, queryPath, params):
    if projectName is None or str(projectName).strip() == "":
        fail("projectName is required")
    if queryPath is None or str(queryPath).strip() == "":
        fail("queryPath is required")
    if params is None:
        params = {}
    dataset = system.db.runNamedQuery(str(projectName), str(queryPath), params)
    columns, rows = dataset_to_rows(dataset)
    if len(rows) < 1:
        fail("Named Query returned no rows: %s" % queryPath)
    return columns, rows
```

For table/KPI pages, validate expected column names before using the rows. The tested `runNamedQuery(projectName, queryPath, {})` call returned a `DatasetUtilities$PyDataSet`-style object that supported `getColumnCount()`, `getColumnName()`, `getRowCount()`, and `getValueAt()`. Do not require `dataset.getClass().getName()` for confirmation; it failed in one Gateway/Perspective test context. If type logging is useful, use a defensive helper:

```python
def type_name(value):
    try:
        return value.getClass().getName()
    except:
        pass
    try:
        return value.__class__.__name__
    except:
        return str(type(value))
```

Prefer existing Named Queries over inline SQL for reusable Perspective pages. Keep database connections, query paths, and parameter values instance-specific.

Parameter behavior verified against a read-only `Tank Details` Named Query:

- Correct `{"tankNo": "100"}` returned one row.
- Wrong-case `{"TankNo": "100"}`, missing `{}`, and `{"tankNo": None}` returned zero rows, not errors.
- Numeric-looking string `"100"` matched the numeric SQL parameter in this SQLite-backed sample.
- Extra params were ignored by the query execution path.
- Two-argument `system.db.runNamedQuery(queryPath, params)` worked from this Gateway-scope runner, but reusable Gateway/Perspective helpers should still prefer the explicit project-name form to avoid scope ambiguity.

Do not assume a bad parameter will throw. Validate required parameter names before calling and validate row count/columns after calling.

### Update Named Query `getKey`

For Update Query Named Queries that should return a generated key, prefer keyword arguments:

```python
new_id = system.db.runNamedQuery(
    str(projectName),
    str(queryPath),
    params,
    getKey=1
)
```

All-keyword form also worked in the Gateway/Web Dev test:

```python
new_id = system.db.runNamedQuery(
    project=str(projectName),
    path=str(queryPath),
    parameters=params,
    getKey=1
)
```

Gateway validation against a sample `INSERT` Named Query:

- `runNamedQuery(projectName, queryPath, params)` returned affected-row count `1`.
- `runNamedQuery(projectName, queryPath, params, getKey=1)` returned a generated key as a `long`.
- `runNamedQuery(project=..., path=..., parameters=..., getKey=1)` also returned a generated key.
- `runNamedQuery(projectName, queryPath, params, None, 1)` and `runNamedQuery(projectName, queryPath, params, "", 1)` worked locally, but keyword `getKey=1` is clearer and avoids placeholder-slot mistakes.
- `runNamedQuery(queryPath, params, getKey=1)` from Gateway/Web Dev scope failed with `ProjectNotFoundException` because the first argument was treated as the project name.
- `runNamedQuery(projectName, queryPath, [params], getKey=1)` failed because parameters must be one dictionary/Map, not a list of dictionaries.
- `system.db.runNamedQuery("x", {}, , 1)` is invalid Python/Jython syntax; empty positional argument slots cannot be used.

Generated scripts should not rely on `getKey` unless the target database/driver and Named Query type support generated-key retrieval. Always verify the inserted row or returned id before using it downstream.

### Named Query Transactions

In Gateway/Perspective scope, use the project-aware transaction form:

```python
import java

tx = None
try:
    tx = system.db.beginNamedQueryTransaction(
        str(projectName),
        str(databaseName),
        system.db.READ_COMMITTED,
        10000
    )
    if tx in [None, ""]:
        fail("beginNamedQueryTransaction returned no transaction id")

    ds = system.db.runNamedQuery(str(projectName), str(queryPath), params, tx)
    rows = dataset_to_rows(ds)[1]
    system.db.commitTransaction(tx)
except java.lang.Exception, exc:
    if tx not in [None, ""]:
        try:
            system.db.rollbackTransaction(tx)
        except:
            pass
    fail("named query transaction failed: %s" % exc)
finally:
    if tx not in [None, ""]:
        system.db.closeTransaction(tx)
```

Gateway validation notes:

- `beginNamedQueryTransaction(projectName, databaseName, ...)` plus `runNamedQuery(projectName, queryPath, {}, tx)` returned five read-only sample rows.
- `runNamedQuery(queryPath, {}, tx)` from Gateway scope failed with a `ClassCastException` because the transaction id was coerced into the params slot.
- `beginNamedQueryTransaction(databaseName, isolationLevel, timeout)` returned `None` on this Gateway instead of throwing. Check the returned transaction id before using it.
- Committing an empty Named Query transaction succeeded on this Gateway, but treat that as version/context behavior, not a useful workflow.

## Raw SQL Reads

Prefer Named Queries for reusable Perspective pages. When a raw read-only SQL helper is truly required, use `system.db.runPrepQuery()` with a configured database name and parameter list:

```python
def run_alarm_preview(databaseName, filterLike):
    if databaseName is None or str(databaseName).strip() == "":
        fail("databaseName is required")
    if filterLike is None or str(filterLike).strip() == "":
        fail("filterLike is required")

    sql = (
        "SELECT displaypath, "
        "datetime(eventtime / 1000, 'unixepoch') as eventtime "
        "FROM alarm_events "
        "WHERE displaypath LIKE ? "
        "ORDER BY eventtime DESC "
        "LIMIT 5"
    )
    dataset = system.db.runPrepQuery(sql, [str(filterLike)], str(databaseName))
    columns, rows = dataset_to_rows(dataset)
    if "displaypath" not in columns or "eventtime" not in columns:
        fail("Unexpected columns: %s" % ",".join(columns))
    return rows
```

Do not concatenate user/operator values into SQL. Keep database connection names and filters as view/project config or function parameters. Bound read-only queries with a DB-side limit and validate columns/row count before assigning rows to Perspective.

For `runPrepQuery`, no matching rows is a normal result, not a failure. Validate expected columns and row count separately; build UI empty states or return `None`/`[]` deliberately instead of indexing row 0.

### Raw Prepared Parameter Shapes

For `system.db.runPrepQuery(...)` and `system.db.runPrepUpdate(...)`, use ordered list/tuple parameter containers. Do not pass a scalar or dict for raw JDBC placeholders.

Validation against `Sample_SQLite_Database`:

- `["list-ok"]` and `("tuple-ok",)` both worked for `select ? as value`.
- `[None]` bound SQL `NULL` and read back as `None`.
- Scalar string params failed with `ClassCastException`.
- Scalar integer params failed with a surprising coerced object-array error; this is another reason to avoid scalar params.
- Dict params failed with `ClassCastException`; dicts are for Named Query params, not positional raw prepared placeholders.
- Extra params failed.
- One missing param in `select ? as a, ? as b` may not fail on every JDBC driver; a SQLite-backed query returned the first value and `NULL` for the second column. Validate placeholder counts yourself before calling.
- Java `Date` and Python `datetime` params both returned epoch-like `long` values in this SQLite probe. Treat date binding as database/driver-specific; this does not make Python `datetime` safe for `system.date` APIs.

```python
def require_param_count(sql, params, expected):
    if params is None:
        params = []
    if len(params) != expected:
        fail("expected %s SQL params, got %s" % (expected, len(params)))
    return list(params)

rows = system.db.runPrepQuery(sql, require_param_count(sql, params, 2), databaseName)
```

Prepared `?` placeholders are for values only. They do not parameterize SQL identifiers or syntax. Validation against the sample `tank` table showed:

- `SELECT ? AS selected_value, tankName ...` returned the literal `"tankName"`, not the `tankName` column value.
- `SELECT tankNo FROM ? ...` failed; a table name cannot be a bound value.
- `ORDER BY ?` sorted by a constant, not by the requested column.

For dynamic sort/table/partition cases, map trusted UI keys to allowlisted SQL fragments:

```python
ORDER_COLUMNS = {"number": "tankNo", "name": "tankName"}
DIRECTIONS = {"asc": "ASC", "desc": "DESC"}

def safe_sort_clause(sortKey, direction):
    if sortKey not in ORDER_COLUMNS:
        fail("invalid sort key")
    if direction not in DIRECTIONS:
        fail("invalid sort direction")
    return "%s %s" % (ORDER_COLUMNS[sortKey], DIRECTIONS[direction])

sql = "SELECT tankNo, tankName FROM tank ORDER BY %s" % safe_sort_clause(sortKey, direction)
rows = system.db.runPrepQuery(sql, [], databaseName)
```

For `IN` filters, one placeholder is one value. A list argument and a CSV string argument in `IN (?)` can both return zero matching fixture rows. Generate a bounded placeholder list and keep values bound:

```python
def run_in_query(databaseName, values):
    if values is None:
        fail("values required")
    if len(values) == 0:
        return []
    if len(values) > 25:
        fail("too many values")

    clean = [int(value) for value in values]
    placeholders = ",".join(["?"] * len(clean))
    sql = "SELECT tankNo, tankName FROM tank WHERE tankNo IN (%s)" % placeholders
    return system.db.runPrepQuery(sql, clean, databaseName)
```

If the filter list comes from an operator or URL param, validate/cast every value before building SQL.

### Scalar Prep Queries

Use `system.db.runScalarPrepQuery()` only when the script truly needs one scalar value. It returns the first row/first column only, not a dataset:

```python
import java

def scalar_required(databaseName, sql, params):
    if databaseName is None or str(databaseName).strip() == "":
        fail("databaseName is required")
    try:
        value = system.db.runScalarPrepQuery(sql, params, str(databaseName))
    except java.lang.Exception, exc:
        fail("scalar query failed: %s" % exc)
    if value is None:
        fail("scalar query returned no rows")
    return value
```

Validation notes:

- `SELECT COUNT(*) ...` returned a Java/Jython `long`.
- A no-row scalar query returned `None`.
- `SELECT marker, numeric_value ...` returned only the first row's first column.
- Too few prep parameters on a SQLite-backed query can return `0` rows instead of throwing; too many parameters and invalid SQL threw Java exceptions.
- Omitting the database worked from the Web Dev project context in this local project, but reusable Gateway/tag scripts should pass the database name explicitly to avoid scope-dependent defaults.

Validate required params before calling and validate the returned value afterward; do not assume bad params will throw.

## Database Writes

Do not generate `runPrepUpdate()` or mutating SQL unless the user explicitly authorizes database writes and provides a safe target/validation plan. For targeted writes, validate identifiers that cannot be parameterized, use placeholders for values, check affected-row counts, then verify with a read:

```python
def validate_identifier(name):
    value = str(name)
    if value == "":
        fail("identifier is required")
    for ch in value:
        if not (ch.isalnum() or ch == "_"):
            fail("unsafe identifier: %s" % value)
    return value

def upsert_fixture_row(databaseName, tableName, runId):
    db = str(databaseName)
    table = validate_identifier(tableName)
    run_id = str(runId)

    create_sql = (
        "CREATE TABLE IF NOT EXISTS %s ("
        "run_id TEXT PRIMARY KEY, "
        "status TEXT NOT NULL, "
        "numeric_value INTEGER NOT NULL, "
        "notes TEXT, "
        "updated_at TEXT NOT NULL)"
    ) % table
    system.db.runPrepUpdate(create_sql, [], db)

    insert_sql = (
        "INSERT INTO %s "
        "(run_id, status, numeric_value, notes, updated_at) "
        "VALUES (?, ?, ?, ?, datetime('now'))"
    ) % table
    insert_count = system.db.runPrepUpdate(insert_sql, [run_id, "inserted", 1, "created"], db)
    if int(insert_count) != 1:
        fail("insert affected %s rows" % insert_count)

    update_sql = (
        "UPDATE %s "
        "SET status = ?, numeric_value = ?, notes = ?, updated_at = datetime('now') "
        "WHERE run_id = ?"
    ) % table
    update_count = system.db.runPrepUpdate(update_sql, ["updated", 2, "updated", run_id], db)
    if int(update_count) != 1:
        fail("update affected %s rows" % update_count)

    verify_sql = "SELECT run_id, status, numeric_value, notes, updated_at FROM %s WHERE run_id = ?" % table
    dataset = system.db.runPrepQuery(verify_sql, [run_id], db)
    columns, rows = dataset_to_rows(dataset)
    if len(rows) != 1:
        fail("verification returned %s rows" % len(rows))
    return rows[0]
```

Only table/column identifiers should be string-formatted after strict validation; values belong in `?` parameters. Do not delete verification rows, temp rows, or fixture tables unless the user explicitly asks for cleanup.

`runPrepUpdate()` returns affected-row count by default. Validation against the sample SQLite DB returned `1` for a normal insert; `getKey=1` returned generated integer keys for keyword, empty-transaction positional, and `None`-transaction positional forms, and each key was verified with a follow-up `SELECT`. Reusable guidance remains database/driver cautious: generated-key retrieval can fail or return surprising values on some targets, so prefer keyword `getKey=1` when the call shape supports it and always verify the returned key/row.

Gateway/tag-scope database calls should pass the database connection name explicitly. In a tag `valueChanged` script with no Gateway Scripting Project context, `system.db.runPrepUpdate(sql, params)` failed with `Cannot find database connection - name cannot be null`; the same tag event succeeded when called as `system.db.runPrepUpdate(sql, params, databaseName)`. The Ignition 8.1 Gateway syntax for `runPrepUpdate` also lists `database` as required.

### Explicit Transactions

Use explicit transactions only when the script must make several database changes as one unit. Keep identifiers validated, values parameterized, and transaction lifetime short:

```python
import java

tx = None
committed = False
try:
    tx = system.db.beginTransaction(str(databaseName), system.db.READ_COMMITTED, 10000)
    if tx in [None, ""]:
        fail("beginTransaction returned no transaction id")

    count1 = system.db.runPrepUpdate(sql1, params1, str(databaseName), tx)
    count2 = system.db.runPrepUpdate(sql2, params2, str(databaseName), tx)
    if int(count1) != 1 or int(count2) != 1:
        fail("unexpected affected rows: %s/%s" % (count1, count2))

    system.db.commitTransaction(tx)
    committed = True
except java.lang.Exception, exc:
    if tx not in [None, ""] and not committed:
        try:
            system.db.rollbackTransaction(tx)
        except:
            pass
    fail("transaction failed: %s" % exc)
finally:
    if tx not in [None, ""]:
        system.db.closeTransaction(tx)
```

Transaction behavior to validate: uncommitted rows can be visible inside the transaction and not visible outside before commit; committed rows should persist; rollback should remove inserted rows; using a closed transaction id can fail with `Transaction datasource unknown`. Always close the transaction id and never reuse it after close.

Tag events are a poor place for heavy database work. If a tag event must record a small bounded row, keep the event body short: guard `initialChange`, validate/cast `currentValue.value`, call a project/Gateway helper where possible, use explicit `databaseName`, catch Java exceptions, write a result/status tag, and verify with a readback.

```python
import java

def write_event_row(databaseName, tableName, tagPath, value):
    table = validate_identifier(tableName)
    sql = (
        "INSERT INTO %s "
        "(event_path, event_value, created_at) "
        "VALUES (?, ?, datetime('now'))"
    ) % table
    try:
        count = system.db.runPrepUpdate(sql, [str(tagPath), int(value)], str(databaseName))
    except java.lang.Exception, exc:
        fail("insert failed: %s" % exc)
    if int(count) != 1:
        fail("insert affected %s rows" % count)
    return count
```

## Project Message Requests

Use `system.util.sendRequest()` only for project Gateway Event Script message handlers, not Perspective component message handlers. The required call shape is:

```python
import java

try:
    result = system.util.sendRequest(
        project="<projectName>",
        messageHandler="<handlerName>",
        payload={"asset": assetName},
        timeoutSec=3
    )
except java.lang.Exception, exc:
    fail("message request failed: %s" % exc)
```

Rules verified locally:

- `project` is required; omitting it raised `ValueError: Missing required argument project`.
- A missing handler raised `com.inductiveautomation.ignition.common.script.message.MessageHandlerException`.
- `except Exception` did not catch the missing-handler Java exception; `except java.lang.Exception` and a narrow bare `except:` did.
- Passing a Perspective-style `scope` keyword did not select a handler scope; `sendRequest` still attempted the project Gateway message handler. Do not use `scope` with `sendRequest`.

### Fire-And-Forget Messages

`system.util.sendMessage()` is fire-and-forget. It returns routing status objects or an empty list, not the handler result.

Gateway/Web Dev validation notes:

- No explicit scope returned an ArrayList with a `sendStatus=SENT` Gateway entry, even for a missing handler.
- `scope="G"` also returned `sendStatus=SENT` for the missing Gateway handler.
- `scope="S"`, `scope="C"`, lowercase `scope="s"`, an invalid scope string, and a missing project returned empty lists rather than throwing.
- Omitting the required `project` argument raised `ValueError`.

Treat `sendStatus=SENT` as "message was routed/queued", not "handler executed successfully". Always verify an observable side effect when a script depends on the handler running.

### Async Requests

`system.util.sendRequestAsync()` returns a request handle immediately. Use callbacks for results and errors:

```python
def on_success(result):
    import system
    system.util.getLogger("my.feature").info("handler returned %s" % repr(result))

def on_error(error):
    import system
    system.util.getLogger("my.feature").error("handler failed: %s" % error)

handle = system.util.sendRequestAsync(
    project="<projectName>",
    messageHandler="<handlerName>",
    payload={},
    timeoutSec=3,
    onSuccess=on_success,
    onError=on_error
)
```

Validation notes: a missing handler returned a `SystemUtilities$RequestImpl` handle immediately; after a short wait, `onError` ran with `MessageHandlerException` and wrote a result tag. Do not expect the return handle to contain the handler result.

## HTTP Client

Use `system.net.httpClient()` for outbound HTTP/API calls. Create clients sparingly and reuse them from Project Library state when appropriate; Ignition 8.1 docs describe the client as heavyweight.

Gateway-verified JSON POST pattern:

```python
client = system.net.httpClient(timeout=5000)
response = client.post(
    url="<apiUrl>",
    data={"action": "health", "requestId": requestId},
    headers={"Content-Type": "application/json"},
    timeout=5000
)

if not response.good:
    fail("HTTP %s: %s" % (response.statusCode, response.text[:500]))

data = response.json
```

Validation notes:

- `data` as a dictionary was JSON-encoded and accepted by the target API.
- `response.statusCode`, `response.getStatusCode()`, `response.good`, `response.isGood()`, `response.text`, `response.json`, and `response.getJson()` worked.
- `response.text` was `unicode`.
- A bad-token 401 returned a normal Response object with `good == False` and `clientError == True`; it did not throw.

## Third-Party Python And CPython Boundaries

Ignition 8.1 Jython is not CPython. Do not assume packages installed for a desktop/server Python interpreter are importable inside Ignition.

Gateway import validation notes:

- Missing: `requests`, `pandas`, `numpy`, `pathlib`, `pip`, `importlib.util`.
- Present in this Gateway's Jython library path: `importlib`, `urllib2`, `json`, `csv`, `subprocess`.
- Java packages such as `java.net` are visible through Jython's Java integration.
- `system.net.httpClient(timeout=...)` is available and is the preferred Ignition-native HTTP client.

Treat `subprocess`/external process use as a site-specific integration, not a default scripting pattern. It depends on Gateway OS paths, service account permissions, process lifetime, and security review. When a task truly requires CPython packages such as pandas/numpy/scikit-learn, use an explicitly managed external CPython service/process and call it with `system.net.httpClient` or another approved boundary.

### External Process Boundary

Use external processes only after explicit site/user approval. In Gateway, Web Dev, Perspective, and Gateway Event scopes, the process launches on the Gateway host, under the Gateway service account and its working directory. It does not run on the Designer/client PC.

`system.util.execute(commands)` launches the OS command and returns `None`; it does not capture stdout, stderr, or exit code. Confirm success with an observable side effect or use a subprocess/Java process wrapper when output matters.

```python
import java

try:
    result = system.util.execute(["<program>", "<arg1>", "<arg2>"])
except java.lang.Throwable, exc:
    raise Exception("external command failed to launch: %s" % exc)

# result is None. Verify by reading the file/tag/DB row/log the command was expected to create.
```

For stdout/stderr/exit code, prefer an explicitly approved wrapper:

```python
from java.lang import ProcessBuilder
from java.io import BufferedReader, InputStreamReader

pb = ProcessBuilder(["<program>", "<arg1>"])
process = pb.start()
reader = BufferedReader(InputStreamReader(process.getInputStream()))
lines = []
line = reader.readLine()
while line is not None:
    lines.append(line)
    line = reader.readLine()
exit_code = process.waitFor()
```

The default process working directory may be the Ignition install folder, and Java launch failures can surface as `java.io.IOException`. Never hard-code those local paths or account names into reusable scripts.

## Async And Polling

Use Java sleep in Script Console or Gateway helper code:

```python
from java.lang import Thread

def sleep_ms(milliseconds):
    Thread.sleep(long(milliseconds))
```

Do not assume `system.util.sleep()` exists in the Designer Script Console.

`system.util.invokeAsynchronous(func)` works from Gateway scope and returns a `java.lang.Thread` immediately while the function runs in the background. Two Gateway-verified rules:

- Pass all state into the async function explicitly. A worker that referenced enclosing-scope locals failed in a Gateway exec context; binding state through default arguments fixed it:

```python
def launch_async(paths, values):
    def worker(paths=paths, values=values):
        try:
            results = system.tag.writeBlocking(paths, values)
        except Exception as exc:
            system.util.getLogger("MyFeature").error("async worker failed: %s" % exc)
    return system.util.invokeAsynchronous(worker)
```

- Confirm completion by polling an observable result (tags, database row, log marker); the immediate return only confirms the launch.

Async monitors need an explicit stop flag. Do not create orphaned loops.

Polling measurements are approximate; report the poll interval and timing resolution.

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
