# Database, Messaging, And HTTP

Read this before using named queries, raw SQL, database writes or transactions, project messages, or outbound HTTP.

## Contents

- [Named Queries](#named-queries)
- [Raw SQL Reads](#raw-sql-reads)
- [Database Writes](#database-writes)
- [Project Message Requests](#project-message-requests)
- [HTTP Client](#http-client)
- [Additional Customer Runtime Rules](#additional-customer-runtime-rules)

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

## Additional Customer Runtime Rules

Use these detailed Named Query, SQL, transaction, project-message, Java-exception, and HTTP rules.

- For Named Query scripts, keep `projectName`, `queryPath`, and `params` configurable; in Gateway/Perspective contexts prefer `system.db.runNamedQuery(projectName, queryPath, params)`, validate expected columns/row count, and convert the returned Dataset/PyDataSet before Perspective use. For Update Named Query action logs, validate all required param names immediately before the call and verify the affected-row/readback result.
- For Database `<Parameter>` Named Queries, do not assume passing `{"database": databaseName}` will work for package-copied resources; they can still look for a literal `<Parameter>` connection. Use target-specific validation or avoid dynamic database selection.
- Named Query missing params, wrong-case params, and `None` values may return an empty dataset instead of throwing. Extra params may be ignored. Validate required param names before calling and validate row count after.
- For Update Named Queries that need a generated key, use keyword arguments such as `system.db.runNamedQuery(projectName, queryPath, params, getKey=1)` or all-keyword calls. Do not leave empty positional argument slots, do not omit `projectName` in Gateway/tag/Web Dev scope, and pass one params dictionary, not a list of dictionaries.
- For Named Query transactions in Gateway/Perspective, call `system.db.beginNamedQueryTransaction(projectName, databaseName, ...)` and `system.db.runNamedQuery(projectName, queryPath, params, tx)`. Do not omit `projectName`; wrong call shapes can coerce `tx` into `params` or return a non-usable transaction id such as `None`.
- Prefer Named Queries over raw SQL. If `system.db.runPrepQuery()` is required, keep `databaseName`, SQL filters, and params configurable; use `?` placeholders only for values, bound read-only SQL, validate result shape/row count, and convert rows before UI use. Pass raw `runPrep*` params as ordered lists/tuples, never scalars or dicts; validate placeholder counts before calling because drivers may bind missing values as `NULL` while rejecting extras.
- Do not bind table names, column names, `ORDER BY` fields, sort directions, SQL operators, or syntax fragments with `?` placeholders. Select those identifiers from strict allowlists, string-format only the allowlisted fragment, and reject everything else before SQL execution.
- For dynamic `IN` filters, do not pass a list, tuple, or CSV string into one placeholder. Generate a bounded comma-separated list of `?` placeholders from the validated value count, bind each value separately, and handle empty lists without emitting invalid SQL.
- For scalar reads, `system.db.runScalarPrepQuery()` returns only the first row/first column and returns `None` for no rows. Pass an explicit database name in Gateway/tag contexts, validate parameter counts before calling, validate the returned value after calling, and catch Java exceptions for SQL failures.
- Generate `system.db.runPrepUpdate()` or mutating SQL only after explicit user authorization. Keep database/table identifiers configurable, validate identifiers that cannot use placeholders, use `?` params for values, check affected-row counts, and verify with a follow-up read. `getKey=1` can return a generated key, but support and value shape depend on the database/driver/query; verify the row by key.
- For multi-statement database writes, use an explicit transaction: `tx = system.db.beginTransaction(databaseName, system.db.READ_COMMITTED, timeoutMs)`, pass `databaseName` and `tx` to each `runPrep*` call, commit or rollback, then always `closeTransaction(tx)` in `finally`. Check `tx` is usable before use; closed transaction ids are invalid.
- In Gateway/tag-scope database scripts, pass the database connection name explicitly to `system.db.runPrepQuery()` / `system.db.runPrepUpdate()`; tag events may not have a project default database and can fail with "database connection - name cannot be null".
- Ignition Java-backed failures may not be caught by Python `except Exception`. For `system.db`, `system.util.sendRequest`, and similar Java APIs, catch `java.lang.Exception` or use a narrow final `except:` only to record/re-raise diagnostic errors. For diagnostic probes that must catch Java runtime/indexing failures, catch `java.lang.Throwable`.
- For project message-handler calls, use `system.util.sendRequest(project="<projectName>", messageHandler="<handlerName>", payload=<dict>, timeoutSec=<seconds>)`; the handler must be a project Gateway Event Script message handler, not a Perspective component handler, and there is no Perspective `scope` selector.
- For Gateway/tag-to-Perspective messaging, use `system.util.sendMessage(project="<projectName>", messageHandler="<sessionHandler>", payload=<dict>, scope="S")` to target project Session Event message handlers; those handlers may then call `system.perspective.sendMessage` to component handlers. Verify with a side effect because send status is not proof of handler execution.
- `system.util.sendRequestAsync` returns a request handle immediately; use `onSuccess`/`onError` callbacks for results/errors and verify observable side effects. Missing handlers can surface only in the async error callback.
- For outbound HTTP APIs, create/reuse `system.net.httpClient(...)`, pass JSON bodies as dictionaries, then check `response.statusCode` and `response.good`; HTTP 4xx/5xx responses can return normal Response objects instead of throwing.
