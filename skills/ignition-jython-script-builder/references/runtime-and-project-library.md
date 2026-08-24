# Runtime And Project Library

Read this before choosing Jython syntax, imports, Project Library boundaries, UI-scope APIs, external runtimes, or asynchronous execution.

## Contents

- [Runtime](#runtime)
- [Scope-Specific UI APIs](#scope-specific-ui-apis)
- [Project Library Calls](#project-library-calls)
- [Third-Party Python And CPython Boundaries](#third-party-python-and-cpython-boundaries)
- [Async And Polling](#async-and-polling)
- [Additional Customer Runtime Rules](#additional-customer-runtime-rules)

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

## Additional Customer Runtime Rules

Use these details for intake, instance portability, Project Library behavior, operational script design, and output expectations.

### Intake

Before writing code, identify:

- Ignition version and execution context: Designer Script Console, Gateway timer, Gateway message handler, Perspective action, Perspective transform, tag event, project script, or named query.
- Exact Project Library path. Do not guess `diagnostics.opcDevices`; use the user's actual tree or ask for it when the script call path matters.
- Tag providers, root paths, database connection names, named queries, modules, and whether the script may write to PLC-facing, MQTT-facing, or MES-facing paths.
- Whether this is staging or production. For production writes, require backups, dry-run mode, and a validation plan.

### Instance portability

Write every script as reusable across different Ignition instances unless the user explicitly provides a site-specific value.

- Do not hard-code project names, tag providers, root paths, database connection names, usernames, passwords, tokens, hostnames, or filesystem paths.
- Put instance-specific values at the top as configuration constants, function parameters, tag parameters, or view/session/project properties.
- Use placeholders such as `<tagProvider>`, `<rootPath>`, `<databaseConnection>`, `<projectName>`, `<gatewayUrl>`, and `<scriptPath>` in instructions.
- If a script must use a site-specific path, state that it must be replaced for the target Gateway and include a validation read before any write.
- Never print secrets. Never include credentials in generated scripts.
- Keep instance identifiers in a separate profile or install note, not in this reusable `SKILL.md`. Lessons learned that apply across Ignition instances should stay in the skill; site/customer identifiers should not.

### Jython, Project Library, and execution behavior

- Write Python 2.7-compatible Jython unless the user proves a newer runtime.
- Do not use f-strings, type hints, `pathlib`, async/await, match/case, walrus, or Python 3-only assumptions.
- Do not import CPython native-extension packages or Python 3 package-manager assumptions inside Ignition Jython. Packages such as `pandas`, `numpy`, `scipy`, `scikit-learn`, `requests`, `pip`, and current Python-3-only libraries are not default Gateway Jython dependencies; native-extension wheels (`.pyd`, `.so`, `.dll`) cannot be loaded by Jython. Use Ignition `system.*` APIs, Python 2.7-compatible pure-Python modules deliberately installed for the Gateway, Java libraries, or an explicitly managed external CPython service/process.
- For expression tags or expression bindings that must call Python, prefer `runScript("library.module.function", pollRate, arg1, arg2, ...)` with a string first argument. In expression tags, Project Library targets must be visible from the configured Gateway Scripting Project; otherwise the expression can return `Error_ExpressionEval` even when the function exists in a project.
- Do not generate eager/non-string `runScript` forms such as `runScript(functionCall(), pollRate)`; they can evaluate surprisingly and do not prove the intended Python function path was called.
- Do not use expression-tag `runScript` poll rates as a scheduler. Expression tag evaluation, tag group cadence, and changing expression arguments can refresh faster than a long `runScript` poll value; use tag groups or Gateway timer/tag-change events for scheduling.
- In tag event scripts, Project Library calls only see the configured Gateway Scripting Project. From tag scope, verify with `system.util.getProjectName()` or `system.project.getProjectName()`; if empty, direct calls like `library.module.func(...)` will fail. Do not prepend the project name or use `import`; configure the Gateway Scripting Project or move the logic to a project Gateway Event script.
- Store Project Library `code.py` as UTF-8 without BOM; a BOM can make Jython module load/compile fail.
- Keep Project Library top-level code limited to definitions, constants, imports, and idempotent lightweight cache setup. Put tag writes, database work, HTTP calls, file I/O, and other side effects inside functions; module top-level code can run on first load and again after a project resource update/reload.
- In Designer Script Console polling, use `java.lang.Thread.sleep()` through a small helper instead of assuming `system.util.sleep()` exists.
- Jython 2.7 `/` between integers truncates (`7 / 2 == 3`). Use a float operand (`7.0 / 2`) or `float()` when real division is required; large integers silently promote to `long`.
- `str` and `unicode` are distinct types in Jython 2.7; mixed concatenation yields `unicode`. When validating unicode through an HTTP API or console, compare `ord()` code points instead of raw glyphs, since transport/display encoding can corrupt glyphs without any Jython bug.
- Never rely on `value.getClass().getName()` for type logging. It fails when the Java class defines its own `getName` (for example `LoggerEx`) and when the value is a pure Jython object (for example the `stringmap` from `getGlobals`). Use a defensive `type_name` helper with a `__class__.__name__` fallback.
- `system.util.invokeAsynchronous` returns a Java `Thread` immediately. Pass all state into the async function explicitly (default arguments or call arguments) instead of relying on closure capture, and prove completion by polling result tags or other observable writes.
- Do not assume CPython packages are available inside Ignition Jython. Common Python 3/CPython packages such as `requests`, `pandas`, `numpy`, `pathlib`, `pip`, and `importlib.util` are not portable Gateway assumptions; use Ignition APIs/Jython stdlib, Gateway-installed pure-Python or Java libraries, or an explicitly managed external CPython service/process.
- Use `system.util.execute`, `subprocess`, or Java `ProcessBuilder` only after explicit site approval. In Gateway/Perspective/Web Dev scope, external processes run on the Gateway host under the Gateway service account/current working directory, not the Designer/client PC. `system.util.execute()` returns `None`; use side-effect/readback proof or `subprocess`/`ProcessBuilder` when stdout, stderr, or return code are required, and catch Java exceptions.

### Operational script design

For operational scripts, include:

1. Configuration constants at the top.
2. A `dryRun` option when writing or configuring tags.
3. Helpers for logging, failing loudly, sleeping, reading, writing, and browse result access.
4. Provider existence checks before browsing provider roots.
5. Batched reads/writes where possible.
6. Specific exception messages that identify missing tags, bad quality, null values, datatype mismatch, configure failure, write failure, or verification failure.
7. A validation section the user can run after install.

### Output expectations

When producing a script, include:

- Where it goes: Project Library path, Gateway timer, message handler, Perspective event, tag event, or Script Console.
- Exact code block using Jython-safe syntax.
- Required parameters and tag/database prerequisites.
- Dry-run or staging instructions for writes.
- Validation steps and expected success signs.
- Runtime proof for packaged Project Library scripts: what called it, what changed, and how the result was read back.
- Known risks, especially PLC-facing writes, provider-not-found risks, bad quality behavior, null behavior, and missed event behavior.
