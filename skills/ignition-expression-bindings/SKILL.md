---
name: ignition-expression-bindings
description: "Ignition Expression Language skill for binding syntax. USE WHEN: writing or debugging Perspective/Vision expression bindings, Expression tags, binding transforms that use the expression engine, if/switch/case logic in bindings, string concatenation in bindings, dateArithmetic/dateFormat in bindings, bound property `{path}` references, len/indexOf/isNull in expression bindings, Error_ExpressionEval troubleshooting. DO NOT USE FOR: Jython scripts (use ignition-coding), Named Queries, Perspective view structure (use perspective-views), tag configuration."
---

# Ignition Expression Language — Binding Syntax

Expression Language is used by Perspective/Vision **Expression Bindings**, **Expression Tags**, and **Expression transforms** on bindings. It is NOT a scripting language — every expression **returns a single value**. It is distinct from Jython.

> Canonical references:
> - [Expression Language and Syntax](https://docs.inductiveautomation.com/docs/8.3/platform/expression-language-and-syntax)
> - [Expression Functions index](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions)
> - [Logic functions](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic) (`if`, `case`, `switch`, `coalesce`, `isNull`, `len`, `try`, …)

## When to Use

- Writing a new Perspective expression binding (`"type": "expr"`)
- Fixing `Error_ExpressionEval` errors in the binding preview
- Debugging type-mismatch issues (e.g. `if` rejects a string)
- Concatenating strings, formatting dates, or doing conditional logic inside a binding
- Referencing other view/session/page/custom properties via `{path}` notation

## Core Rules

### 1. Every expression returns exactly one value

Expressions are not statements. No `return` keyword, no semicolons, no assignment. The whole expression IS the returned value.

### 2. Comparison uses `=`, NOT `==`

Operators straight from the docs:

| Operator | Meaning |
|----------|---------|
| `=` | Equal (single equals) |
| `!=` | Not equal |
| `>` `<` `>=` `<=` | Comparisons |
| `&&` | Logical AND |
| `\|\|` | Logical OR |
| `!` | Logical NOT |
| `+` | Add (numbers) **OR** string concatenation |
| `-` `*` `/` `%` `^` | Arithmetic |
| `&` `\|` `xor` `~` `<<` `>>` | Bitwise |
| `like` | Fuzzy string match with `%`, `*`, `?` wildcards |

### 3. `if(condition, trueVal, falseVal)` requires a **boolean or numeric** condition

The `if()` function **does NOT coerce strings**. Passing a string throws:

```
Error_ExpressionEval: "if" function expected a boolean or numeric first argument, but got a class java.lang.String
```

**WRONG:**
```
if({view.custom.name}, {view.custom.name}, 'Unknown')
```

**RIGHT — explicit boolean condition:**
```
if(len({view.custom.name}) > 0, {view.custom.name}, 'Unknown')
```

**Other common patterns:**
```
if(isNull({view.custom.value}), 'N/A', {view.custom.value})
if({view.custom.count} > 0, 'Has items', 'Empty')
if({view.custom.active} = true, 'On', 'Off')
```

> For null-or-empty coalescing across many values, prefer [`coalesce(v1, v2, v3, ...)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/coalesce). It returns the first non-null argument.

### 4. Bound values use curly-brace `{path}` notation

```
{view.custom.docUrl}                      // view custom property
{view.params.recordId}                    // view param
{view.props.defaultSize.width}            // view own prop
{session.custom.user}                     // session prop
{page.props.id}                           // page prop
{[default]Folder/Path/TagName}            // tag path
```

Paths are resolved by the binding engine. **Inside bindings, do not use `self.` — that is Jython syntax, not expression syntax.**

### 5. String literals use single OR double quotes

```
'hello'
"hello"
"She said \"hi\""   // escape double-quotes with backslash
'Line1\nLine2'      // \n, \t, \r escape sequences
```

### 6. String concatenation with `+`

```
'Tool ID: ' + {view.custom.toolId}
{view.custom.first} + ' ' + {view.custom.last}
'Count: ' + 2                             // returns 'Count: 2' (auto-coerces to string)
```

> Prefer `+` for simple concat. Use [`concat(s1, s2, ...)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/advanced) when you have many pieces.

### 7. Number → string conversion in concat happens automatically, but be careful with types

- `'x=' + 5` → `'x=5'` ✓
- `2 + 3` → `5` (both numeric, adds)
- `'2' + 3` → `'23'` (left is string, concats)

When you want forced string, wrap in `toStr()`: `toStr({view.custom.count}) + ' items'`.

### 8. Boolean literals

`True`, `true`, `TRUE`, `tRuE` — all equivalent (case-insensitive). Ditto `False`. Prefer `True` / `False` for Python-style consistency.

### 9. Null literal

`null`, `None`, `none` — all equivalent. Test with `isNull({path})`, not `{path} = null`.

### 10. Comments use `//`

```
// This is a comment, rest of line ignored
if(
  {view.custom.enabled},   // turn on when user checks the box
  'Active',
  'Inactive'
)
```

Whitespace (spaces, tabs, newlines) is ignored — break long expressions across lines.

### 11. Dataset / collection access uses square brackets

```
{myDataset}['ColumnName']              // first row, by column name
{myDataset}[3]                         // row 3, first column  (by index)
{myDataset}[3, 'ColumnName']           // specific cell
{myDataset}[3, 2]                      // by row index and column index
{myArray}[0]                           // array element
{myMap}['myKey']                       // map / JSON object lookup
```

For dataset columns of known type, wrap with casting: `toInt({ds}[0, 'Count'])`.

## Cheat-Sheet of Essential Functions

| Function | Purpose | Example |
|----------|---------|---------|
| [`if(c, t, f)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/if) | Conditional (condition MUST be bool/numeric) | `if(len({x}) > 0, {x}, 'empty')` |
| [`switch(v, c1, c2, ..., r1, r2, ..., default)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/switch) | Multi-branch by matching value | `switch({state}, 0, 1, 2, 'Off','Run','Fault', '?')` |
| [`case(v, t1,r1, t2,r2, ..., default)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/case) | Like `switch` but pairs | |
| [`coalesce(a, b, c, ...)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/coalesce) | First non-null | `coalesce({x}, {fallback}, 'N/A')` |
| [`isNull(v)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/isNull) | Null test | `isNull({x})` |
| [`len(v)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/len) | String length or dataset row count | `len({view.custom.name}) > 0` |
| [`indexOf(s, sub)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/indexOf) | Substring position (-1 if not found) | `indexOf({msg}, 'error') >= 0` |
| [`try(expr, fallback)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/try) | Swallow errors from an expression | `try({ds}[0, 'x'], 0)` |
| [`isGood(v)` / `isBad(v)` / `isError(v)`](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic) | Quality tests | `isGood({[default]tag})` |
| `dateFormat(d, 'pattern')` | Format a Date | `dateFormat(now(), 'yyyy-MM-dd HH:mm:ss')` |
| `dateArithmetic(d, n, 'unit')` | Add/subtract time | `dateArithmetic(now(), -15, 'minute')` |
| `dateExtract(d, 'year')` | Extract part | `dateExtract({d}, 'year')` |
| `now(pollRate)` | Current time, optionally refreshing at rate-ms | `now(1000)` |
| `concat(s1, s2, ...)` | Explicit string concat | `concat('ID=', {x}, ' Name=', {y})` |
| `toStr(v)` / `toInt(v)` / `toFloat(v)` | Type casting | `toInt({ds}[0, 'Count'])` |
| `forceQuality(v, q)` | Override quality of a value | `forceQuality('!BAD!', 0)` |

Full function catalog by category (JSON, Advanced, Aggregates, Alarming, Colors, Date and Time, Logic, Math, Strings, etc.) lives under the [Expression Functions appendix](https://docs.inductiveautomation.com/docs/8.3/appendix/expression-functions).

## Expression Binding — JSON Shape (Perspective)

In a Perspective `view.json`, expression bindings live under `propConfig`:

```json
"propConfig": {
  "props.text": {
    "binding": {
      "config": {
        "expression": "if(len({view.custom.name}) > 0, {view.custom.name}, 'Unknown')"
      },
      "type": "expr"
    }
  }
}
```

- `"type": "expr"` (not `"property"` — property bindings are for direct path binding)
- Expression string goes inside `config.expression`
- Braces `{}` inside the expression string are the bound-value syntax
- Escape any inner quotes: inside JSON the expression needs `\"` for any `"` character
- Prefer single quotes `'...'` inside expressions so the JSON encoding stays clean

## Reviewing an Expression Binding (Checklist)

Before saving any expression binding:

1. **Comparison uses `=` not `==`** — `==` is a silent syntax error in some contexts
2. **`if()` first arg is boolean/numeric** — wrap strings with `len(...) > 0` or `isNull()` or `= 'value'`
3. **Null check with `isNull(x)`** — never `x = null`
4. **Every `{path}` resolves** — check property exists; watch for case sensitivity
5. **Escape quotes inside JSON** — prefer `'single quotes'` in the expression to avoid JSON escaping
6. **No Jython syntax** — no `self.`, no `.get()`, no `import`, no `def`, no list comprehensions
7. **Dataset access has a valid index/column** — wrap risky lookups in `try(expr, fallback)`
8. **Number vs string intent** — `'2' + 3` returns `'23'`, not `5`. Use `toInt`/`toFloat` when needed
9. **Use `coalesce` for null-fallback chains** — cleaner than nested `if(isNull(...))`
10. **Test in the Binding Preview panel** — the bottom of the editor shows live result or error

## Common Error → Fix Reference

| Error / symptom | Cause | Fix |
|-----------------|-------|-----|
| `Error_ExpressionEval: 'if' function expected a boolean or numeric first argument, but got a class java.lang.String` | Passed a string to `if()` | Wrap with `len(x) > 0`, `isNull(x)`, or `x = 'value'` |
| Binding shows `null` unexpectedly | Referenced path doesn't exist or is null | Add `coalesce(...)` fallback or check property path |
| `Error_TypeConversion` in dataset access | Column not the expected type | Wrap with `toInt`, `toFloat`, `toStr` |
| Concatenation produces wrong number | `+` treating numbers as strings | Use `toInt`/`toFloat` on each operand before `+` |
| `=` treated as assignment | You used `==` thinking like Python | Change to single `=` |
| Expression silently fails in tag | Bad quality propagating | Use `try(expr, fallback)` or `forceQuality(...)` |
| Can't reference `self.props.X` | Expression syntax, not script | Use `{this.props.X}` or bound path instead |

## Writing Expressions Safely (Defensive Patterns)

```
// Defensive string render
coalesce({view.custom.title}, 'Untitled')

// Defensive number cast + fallback
try(toInt({view.custom.count}), 0)

// Guard nullable concatenation
coalesce({view.custom.prefix}, '') + ' - ' + coalesce({view.custom.suffix}, '')

// Boolean from possibly-null flag
isNull({view.custom.flag}) = false && {view.custom.flag} = true

// Conditional style class binding
if({view.custom.state} = 'error', 'nxedge/components/alert/error_msg', 'nxedge/components/alert/info_msg')

// Dataset lookup with guard
try({myDataset}[0, 'Name'], 'N/A')
```

## Do NOT

- Do not mix Jython into expression strings (`self.`, `.get()`, `import`, list comps) — use a **script transform** on the binding if you need Jython logic
- Do not use `==`, `is`, `is not`, `in`, `not in` — these are Python, not expression language
- Do not use `null`-equality; use `isNull()`
- Do not assume `if()` does truthy coercion on strings/lists — it does NOT
