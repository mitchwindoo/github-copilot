---
name: perspective-views
description: "Ignition Perspective view.json development skill. USE FOR: creating or editing Perspective view JSON files, component trees, property bindings, expression bindings, script transforms, flex container layout, view custom properties, event handlers, step-based views. DO NOT USE FOR: gateway Python scripts (use ignition-coding), Vision clients, named queries, OPC tags."
---

# Ignition Perspective View Development

## When to Use

- Creating new Perspective `view.json` files
- Editing component trees, bindings, or event handlers in existing views
- Building step-based or state-machine views with conditional visibility
- Adding dropdown bindings, button scripts, or property transforms
- Reviewing view JSON for schema compliance

## View File Structure

Every Perspective view is a directory containing `view.json` + `resource.json`:

```
views/<Category>/<ViewName>/
├── view.json       # Component tree, props, bindings, events
└── resource.json   # Ignition resource metadata
```

### resource.json Template

```json
{
  "scope": "G",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": ["view.json"],
  "attributes": {
    "lastModificationSignature": ""
  }
}
```

### view.json Top-Level Shape

```json
{
  "custom": {},
  "params": {},
  "propConfig": {},
  "props": {
    "defaultSize": { "height": 700, "width": 600 }
  },
  "root": {
    "children": [],
    "meta": { "name": "root" },
    "props": { "direction": "column", "style": { "gap": "1rem", "padding": "1rem" } },
    "type": "ia.container.flex"
  }
}
```

## Critical Rules

### 1. Visibility — Use `position.display`, NOT `props.visible`

`props.visible` is **not in the Perspective component schema** and produces a validation error. All visibility control inside flex containers uses `position.display` (boolean).

**Static default (hidden):**
```json
{
  "position": {
    "basis": "auto",
    "display": false,
    "grow": 1
  }
}
```

**Binding (dynamic show/hide):**
```json
{
  "position": {
    "basis": "auto",
    "display": false,
    "grow": 1
  },
  "propConfig": {
    "position.display": {
      "binding": {
        "config": {
          "expression": "{view.custom.step} = 'myStep'"
        },
        "type": "expr"
      }
    }
  }
}
```

This applies to ALL component types when children of `ia.container.flex` — labels, buttons, nested containers, dropdowns, etc.

### 2. Verified Component Types

Only use component types that exist on this gateway. The following are verified:

**Containers:**
`ia.container.flex` | `ia.container.coord` | `ia.container.column` | `ia.container.breakpt` | `ia.container.tab`

**Display:**
`ia.display.label` | `ia.display.view` | `ia.display.table` | `ia.display.image` | `ia.display.icon` | `ia.display.markdown` | `ia.display.iframe` | `ia.display.progress` | `ia.display.flex-repeater` | `ia.display.viewcanvas` | `ia.display.accordion` | `ia.display.carousel`

**Input:**
`ia.input.button` | `ia.input.dropdown` | `ia.input.text-field` | `ia.input.numeric-entry-field` | `ia.input.checkbox` | `ia.input.toggle-switch` | `ia.input.radio-group` | `ia.input.slider` | `ia.input.date-time-input` | `ia.input.text-area` | `ia.input.fileupload` | `ia.input.password-field` | `ia.input.multi-state-button` | `ia.input.form`

**Other:**
`ia.navigation.horizontalmenu` | `ia.shapes.svg` | `ia.chart.timeseries`

> **The inline frame component is `ia.display.iframe`** (NOT `ia.display.inline-frame`). Its prop is `props.src`.

### 3. Flex Container Children — Position Properties

Every child of `ia.container.flex` has a `position` object controlling its flex behavior:

```json
{
  "position": {
    "basis": "40px",
    "grow": 0,
    "shrink": 0,
    "display": true
  }
}
```

| Property | Type | Purpose |
|----------|------|---------|
| `basis` | string | Flex basis — `"auto"`, `"40px"`, `"200px"` |
| `grow` | number | Flex grow factor (0 = don't grow, 1 = fill) |
| `shrink` | number | Flex shrink factor (0 = don't shrink) |
| `display` | boolean | Show/hide the component. **This is the visibility toggle.** |

### 4. Perspective Property Bindings

Bindings go in the `propConfig` object. The key is the dot-path to the property being bound:

```json
"propConfig": {
  "props.text": {
    "binding": {
      "config": { "path": "view.custom.myValue" },
      "type": "property"
    }
  },
  "props.options": {
    "binding": {
      "config": { "path": "view.custom.myList" },
      "type": "property"
    }
  },
  "position.display": {
    "binding": {
      "config": { "expression": "{view.custom.step} = 'active'" },
      "type": "expr"
    }
  }
}
```

**Binding types:**
- `"type": "property"` — Direct property path binding (`config.path`)
- `"type": "expr"` — Expression binding (`config.expression`)
- `"type": "tag"` — Tag binding (`config.path`)

### 5. Script Transforms on Bindings

Perspective stores Jython in `view.json` script strings with a base tab level. Every non-empty top-level line in a `"script"` or `"code"` string starts with `\t`; each block adds one more tab:

- `\t` + top-level code
- `\t\t` + code inside blocks (`if`, `for`, `try`, `def`, etc.)
- `\t\t\t` + nested block code

Use tab characters encoded as `\t`, not spaces. Do not strip the first leading tab from generated Perspective view scripts.

A binding can have a `transforms` array. Script transforms receive the bound `value` and return the result:

```json
"propConfig": {
  "custom.templates": {
    "binding": {
      "config": { "expression": "1" },
      "transforms": [
        {
          "code": "\tresult = someModule.getData(self.session)\n\treturn result",
          "type": "script"
        }
      ],
      "type": "expr"
    }
  }
}
```

- Use `self.session` for the Perspective session object
- Use `self.view.custom.X` to write to view custom properties
- Use `self.custom.X` for component-level custom properties
- Use `value` to read the incoming bound value
- Return the transformed value

### 6. Event Handlers (Component Scripts)

Button clicks, dropdown changes, etc. are in the `events` object:

```json
{
  "events": {
    "component": {
      "onActionPerformed": {
        "config": {
          "script": "\tself.view.custom.myProp = self.props.value"
        },
        "scope": "G",
        "type": "script"
      }
    }
  }
}
```

- `scope: "G"` = gateway scope (required for API calls via project scripts)
- `scope: "C"` = session/client scope
- Script strings use `\t` for the required base tab indentation and `\n` for newlines (JSON-encoded)

### 6a. View `onStartup` Script

The view-level startup script lives in the **top-level** `events` object (sibling of `custom`, `params`, `root`), NOT inside any component. It fires once when the view loads.

```json
{
  "custom": { "step": "selectTemplate", "error": "" },
  "events": {
    "system": {
      "onStartup": {
        "config": {
          "script": "\t# Reset custom properties to initial state\n\tself.custom.step = \"selectTemplate\"\n\tself.custom.error = \"\"\n\n\t# Trigger data refresh\n\tsystem.perspective.sendMessage(\"refresh-data\")"
        },
        "scope": "G",
        "type": "script"
      }
    }
  },
  "params": {},
  "root": { ... }
}
```

**Rules:**
- Key path is `events.system.onStartup` — not `events.component`
- Use `self.custom.X` (NOT `self.view.custom.X`) — at the view level, `self` IS the view
- Reset ALL stateful custom properties to their initial values so re-opening the view starts clean
- If the view needs initial data, call `system.perspective.sendMessage()` to trigger a message handler, or set properties directly
- Always include `"scope": "G"` if the script calls gateway-scoped project library functions

### 6b. Message Handlers

Message handlers live on the **root component** in `root.scripts.messageHandlers`. They respond to `system.perspective.sendMessage()` calls.

```json
{
  "root": {
    "scripts": {
      "customMethods": [],
      "extensionFunctions": null,
      "messageHandlers": [
        {
          "messageType": "refresh-data",
          "pageScope": true,
          "script": "\tresult = myModule.getData(self.session)\n\tif result['success']:\n\t\tself.view.custom.items = result['items']",
          "sessionScope": false,
          "viewScope": false
        }
      ]
    },
    "type": "ia.container.flex"
  }
}
```

**Rules:**
- Message handlers are an **array** inside `root.scripts.messageHandlers`
- Each handler has: `messageType` (string), `script` (string), and three scope booleans
- **Scope booleans** control which messages the handler receives:
  - `pageScope: true` — receives messages sent with `system.perspective.sendMessage(type, payload, 'page')`
  - `sessionScope: true` — receives messages sent with scope `'session'`
  - `viewScope: true` — receives messages sent with scope `'view'` (rare, only same view instance)
  - Set exactly **one** to `true` for clarity; `pageScope: true` is the most common pattern
- **Inside message handler scripts, `self` is the ROOT CONTAINER, not the view** — use `self.view.custom.X` to access view custom properties (NOT `self.custom.X`, which refers to the root container's custom props, which don't exist by default)
- The `payload` dict from `sendMessage` is available as `payload` in the handler script
- `customMethods` and `extensionFunctions` must be present (empty array / null) even if unused

### 7. Expression Binding Syntax

Perspective expressions use `{path}` for property references:

```
{view.custom.step} = 'selectTemplate'
len({view.custom.error}) > 0
!{view.custom.loading}
'Text: ' + {view.custom.toolId}
if({view.custom.flag}, 'classA', 'classB')
```

- Equality is `=` (single equals), not `==`
- Negation is `!` prefix
- String concat uses `+`
- Conditional: `if(condition, trueVal, falseVal)` — **condition MUST be boolean or numeric, never a string**
- To check if a string is non-empty: `if(len({view.custom.myStr}) > 0, ..., ...)`
- **WRONG:** `if({view.custom.myStr}, ..., ...)` — throws `Error_ExpressionEval` because `if()` rejects `java.lang.String`

### 8. Perspective PropertyTree Serialization

When storing data in `view.custom` properties, be aware of Perspective's JSON serialization:

- **Integer dict keys become strings** — `{1: "a"}` stored in custom becomes `{"1": "a"}` on read-back
- **`view.custom` dicts are not real Python dicts** — reading `self.view.custom.someDict` returns a `PyPropertyTreeJsonElement` wrapper. `.get()` and `.keys()` work, but `isinstance(x, dict)` is `False`. Before passing to a project script that validates with `isinstance(x, dict)`, round-trip via `system.util.jsonDecode(system.util.jsonEncode(x))` to produce a true dict.
- **Java objects don't serialize** — HTTP response objects, Java Date, etc. will be lost or corrupted
- **Large payloads bloat the property tree** — Don't cache full API responses; extract only the values you need
- **Safe types:** strings, numbers, booleans, lists of primitives, simple dicts with string keys

### 9. External URLs — Embed with `ia.display.iframe`, Never Navigate

`system.perspective.navigate()` resolves paths **within the Perspective page config**. Navigating to an external URL (e.g., a Unipoint doc link, a PDF, any non-Perspective URL) produces **"View Not Found"** because Perspective tries to match it as a view path.

**WRONG — causes "View Not Found":**
```python
system.perspective.navigate(url, {'target': '_blank'})
```

**CORRECT — embed the URL inline:**
```json
{
  "meta": { "name": "DocIframe" },
  "position": { "grow": 1, "shrink": 0 },
  "propConfig": {
    "props.src": {
      "binding": {
        "config": { "path": "view.custom.docUrl" },
        "type": "property"
      }
    }
  },
  "props": {
    "src": "",
    "style": {
      "borderColor": "#b0b7c3",
      "borderRadius": "4px",
      "borderStyle": "solid",
      "borderWidth": "1px",
      "minHeight": "400px"
    }
  },
  "type": "ia.display.iframe"
}
```

- Use `ia.display.iframe` with `props.src` bound to the URL
- Give it `grow: 1` and a `minHeight` so it fills available space
- `system.perspective.navigate()` is **only** for navigating between Perspective pages/views

### 10. Toast Notifications

Use `system.perspective.sendMessage` to the topNav docked view:

```python
payload = {
    'toastType': 'success',       # success | error | warning | info
    'toastContent': 'Operation complete.',
    'toastAutoClose': 5000,
    'toastPosition': 'top-right',
    'sessionTheme': 'light'
}
system.perspective.sendMessage('showToast', payload, 'page')
```

### 10a. Toast Confirm Callback Scope

When using `showToastView` with a confirm/cancel toast, the callback message must match the **scope of the target handler**:

- If the target handler has `pageScope: true`, the callback payload must include `messageHandler.scope = 'page'`
- If the target handler has `sessionScope: true`, use `messageHandler.scope = 'session'`
- **Mismatched scope = silent failure** — Confirm button does nothing, no gateway log entry
- When debugging a toast confirm that does nothing, compare the callback scope to the target handler's scope booleans **first**

## Step-Based View Pattern

For multi-step wizard views, use a `custom.step` string property with `position.display` bindings:

```json
{
  "custom": {
    "step": "step1"
  },
  "root": {
    "children": [
      {
        "meta": { "name": "Step_One" },
        "position": { "basis": "auto", "grow": 1 },
        "propConfig": {
          "position.display": {
            "binding": {
              "config": { "expression": "{view.custom.step} = 'step1'" },
              "type": "expr"
            }
          }
        },
        "props": { "direction": "column" },
        "type": "ia.container.flex"
      },
      {
        "meta": { "name": "Step_Two" },
        "position": { "basis": "auto", "display": false, "grow": 1 },
        "propConfig": {
          "position.display": {
            "binding": {
              "config": { "expression": "{view.custom.step} = 'step2'" },
              "type": "expr"
            }
          }
        },
        "props": { "direction": "column" },
        "type": "ia.container.flex"
      }
    ]
  }
}
```

- Step 1 has no static `display` default (shows in designer)
- Steps 2+ have `"display": false` (hidden until binding evaluates)
- Transition via `self.view.custom.step = 'step2'` in button scripts

## Validation Checklist

Before finalizing any view.json:

1. **JSON valid** — Parse with `json.load()`, no trailing commas
2. **No `props.visible`** — Search for `props.visible` and `"visible"` in props; must be zero
3. **No `ia.display.inline-frame`** — Use `ia.display.iframe` instead
4. **All component types verified** — Cross-check against the verified list above
5. **`position.display`** used for all show/hide logic with `false` defaults on initially-hidden components
6. **Bindings in `propConfig`** — Not stray keys like `propConfig2`, `propConfig3`
7. **Script strings JSON-encoded with base tabs** — Non-empty top-level lines start with `\t`; block contents use `\t\t`, nested blocks use `\t\t\t`; newlines as `\n`, quotes escaped
8. **No large objects in `view.custom`** — Only serializable primitives and small dicts
9. **Event handlers have `scope`** — `"G"` for gateway script calls, `"C"` for client-only
10. **Dropdown `onActionPerformed`** — Captures `self.props.value` into custom prop
11. **No `system.perspective.navigate()` for external URLs** — Use `ia.display.iframe` to embed; navigate is only for Perspective page paths
12. **`onStartup` uses `self.custom`** — At view level, `self` is the view; do NOT use `self.view.custom`
13. **`onStartup` resets all state** — Every stateful custom prop must be re-initialized so re-opening the view starts clean
14. **Message handlers on root** — `root.scripts.messageHandlers` array, not on child components; include `customMethods: []` and `extensionFunctions: null`
15. **Message handler scope booleans** — Set exactly one of `pageScope`/`sessionScope`/`viewScope` to `true`; use `pageScope: true` with `sendMessage(type, payload, 'page')`
16. **Message handler `self` is root container** — In `root.scripts.messageHandlers`, `self` is the root container, NOT the view. Use `self.view.custom.X` to read/write view custom props
17. **Toast confirm scope must match handler** — Confirm callback payloads must set `messageHandler.scope` to match the target handler's scope boolean (`'page'` for `pageScope: true`)
18. **Flex repeater paths must match view resource paths** — If `props.instances` has rows but nothing renders, verify `props.path` against the actual `views/.../view.json` location before debugging the query
19. **Named query API is version-dependent** — Ignition 8.1 uses `system.db.runNamedQuery`; Ignition 8.3+ uses `system.db.execQuery` (SELECT) or `system.db.execUpdate` (INSERT/UPDATE/DELETE). Match the project's gateway version.
