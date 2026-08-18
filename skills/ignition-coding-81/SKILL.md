---
name: ignition-coding-81
description: "Ignition 8.1 SCADA Jython 2.7 coding skill. USE FOR: writing Ignition 8.1.x gateway scripts, Perspective/Vision scripting, tag operations, named queries via system.db.runNamedQuery, system.* function usage, expression bindings, Transaction Groups, SFCs, alarm pipelines, UDTs, OPC-UA. DO NOT USE FOR: Ignition 8.3+ projects (use ignition-coding-83), non-SCADA tasks, Python 3 code, general web development."
---

# Ignition 8.1 SCADA Coding

## Guiding Principles

- **Clarity and Documentation**: Every script must be fully documented with in-line comments explaining logic, parameters, and key steps.
- **Correctness and Compatibility**: All code must be valid Jython 2.7 and compatible with Ignition 8.1.x. Avoid any Python 3+ features.
- **Maintainability**: Favor reusable functions and modular design. Avoid duplicating logic.
- **Best Practices**: Use Ignition's Expression Language when more efficient than scripting; fall back to Jython for complex logic.
- **Beginner-Friendly**: Communicate in a technical yet approachable tone. Focus on explaining both the "what" and the "why."

## Stack Defaults

| Layer | Default |
|-------|---------|
| Framework | Ignition 8.1.x |
| Scripting Language | Jython 2.7 |
| Client Types | Perspective and Vision |
| Database Queries | Named Query syntax via `system.db.runNamedQuery` |
| Tag Access | `system.*` functions (globally available, no imports) |
| Logging | `system.util.getLogger()` for debug and audit trails |

## Syntax and Style Rules

- **Naming**: Use `camelCase` for variables and functions
- **String Formatting**: Use `.format()` with keyword arguments — never f-strings
- **SQL**: Format for Ignition Named Query compatibility
- **Tag Paths**: Always pass as strings; avoid hardcoding where possible
- **Perspective view scripts**: In `view.json` `"script"` and `"code"` strings, encode Jython with one base tab for top-level lines (`\t`), two tabs inside blocks (`\t\t`), and three tabs inside nested blocks (`\t\t\t`)
- **Forbidden**: `import system.*` and `import com.inductiveautomation.ignition.*` — these are implicit

## Response Structure

When generating Ignition code, follow this structure:

1. **Plan**: Restate the request, outline logic steps, note assumptions or constraints.
2. **Draft**: Provide fully documented Jython 2.7 code block with in-line comments and best practices.
3. **Finalize**: Explain code line-by-line, highlight design choices, suggest improvements.

## Common Patterns

### Logger Setup
```python
logger = system.util.getLogger("MyScript")
logger.info("Starting process for tag: {tagPath}".format(tagPath=tagPath))
```

### Tag Read/Write
```python
value = system.tag.readBlocking([tagPath])[0].value
system.tag.writeBlocking([tagPath], [newValue])
```

### Named Query (Ignition 8.1)
```python
# SELECT queries — returns a dataset
params = {"stationId": stationId, "startDate": startDate}
results = system.db.runNamedQuery("MyProject/QueryName", params)

# INSERT / UPDATE / DELETE queries — also uses runNamedQuery
rowsAffected = system.db.runNamedQuery("MyProject/UpdateName", params)
```

> In Ignition 8.1, `system.db.runNamedQuery` handles both SELECT and write operations. Named queries in inheritable parent projects resolve automatically from any child project context.

> **Migration note**: Ignition 8.3 deprecates `runNamedQuery` in favor of `system.db.execQuery` (SELECT) and `system.db.execUpdate` (INSERT/UPDATE/DELETE). If migrating to 8.3, update all `runNamedQuery` calls.

## Platform Constraints

### Gateway Tag-Change Scripts

Gateway tag-change scripts compile as a **single named function**. Only `def onTagChange(initialChange, newValue, previousValue, event, executionCount):` may appear at the top level of `onTagChange.py`. Any sibling `def helper(...)` above or below it causes `SyntaxError: ... expecting INDENT` because Ignition wraps the file as the function body. Inline helpers inside `onTagChange` or move them into `script-python` modules.

### Inheritable Project Constraints

- Projects with `inheritable: true` **cannot execute message handler scripts**
- `system.util.sendRequest(project=...)` must target a **non-inheritable child project** for the handler to run
- Script libraries defined in the parent project ARE available in child project handlers (inherited)
- Place Gateway Message Handlers in child projects, not in inheritable parents

### Named Query Parameter Pitfalls

- Ignition's named query parameter parser scans the **entire SQL text** for `:identifier` patterns — it does **NOT** skip string literals
- A literal colon inside `N'...'` (e.g. `CONCAT(N'Lock:', @Id)`) will be misinterpreted as a parameter placeholder
- Use `_`, `-`, or `CHAR(58)` instead of `:` in SQL string constants within named queries

### MSSQL Stored Procedure EXEC

`EXEC @r = sp_getapplock @Resource = CONCAT(...)` fails with syntax error. Declare a variable first, then pass it:
```sql
DECLARE @LockResource NVARCHAR(255) = CONCAT(N'Lock_', @Id)
EXEC @r = sp_getapplock @Resource = @LockResource
```

### Perspective PropertyTree Serialization

- Reading `self.view.custom.someDict` returns a `PyPropertyTreeJsonElement` wrapper, **not** a true Python dict
- `.get()` and `.keys()` work, but `isinstance(x, dict)` is `False`
- Before passing to a project script that does `isinstance(x, dict)` validation, round-trip via `system.util.jsonDecode(system.util.jsonEncode(x))` to produce a true dict
- `system.util.jsonEncode` accepts the wrapper directly

## Scope Restrictions

- Treat "Python" as Jython 2.7 in all Ignition contexts
- Do not generate non-SCADA-related content
