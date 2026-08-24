# Perspective Scripting

Read this before writing Perspective event, transform, message, navigation, popup, table, or component-context scripts.

## Contents

- [Perspective Context](#perspective-context)
- [Additional Customer Runtime Rules](#additional-customer-runtime-rules)

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

## Additional Customer Runtime Rules

Use these detailed Perspective component, binding, message, popup, dock, session, and custom-method rules.

- Do not use Vision/client UI APIs (`system.gui`, `system.vision`, `system.util.invokeLater`) in Gateway, Web Dev, tag event, or Perspective scripts. `invokeLater` is Vision-client scope only; Perspective UI changes need Perspective events, component methods, messages, params, bindings, or returned data.
- Keep Perspective button/event scripts thin; call a project script for real work. For tested action-oriented components such as Button, One-Shot Button, Multi-State Button, Checkbox, and Dropdown, `onActionPerformed` can call the same helper, but pass selected/control values from component-specific `self.props` hints. The event object may be a dict-like `PyJsonObjectAdapter`; do not assume it contains the component value.
- In Perspective component scripts, `self.getSibling("<Name>")` resolves same-parent siblings only. A button nested in a controls row cannot update a root-level label through `getSibling`; use the correct parent/root path or bind the label from `view.custom`, then prove the visible state in-browser.
- For dependency-gated Perspective commands, do not trust `props.enabled` as the write guard. The Project Library helper must re-read required dependency/interlock tags, treat bad/missing/false dependencies as blocked outcomes, skip the target write, and return/log a clear reason for the UI.
- For Tag Browse Tree `onNodeClick` handlers, use the documented `event.path` and `event.name`; normalize unqualified paths before `system.tag.readBlocking`, write only JSON-simple values into `view.custom`, and handle folder paths as bad/unsupported reads. Use `props.selection.values` for bound readback labels and the event fields for side effects.
- In Perspective binding script transforms, use the documented `value`, `quality`, and `timestamp` inputs. Check `quality.isGood()` when available before numeric conversion, and return explicit fallbacks for bad, null, or non-numeric tag values; disabled or bad-quality tags can arrive with `value is None`.
- In Perspective query binding script transforms, treat `value` as Dataset/PyDataSet-like or list-like depending on the binding/runtime path. Check `getRowCount()` or `len(value)` before indexing, use `getValueAt(row, column)` or row-dict access only after the row exists, and return explicit zero/empty text for no rows.
- For Perspective operator/button logging, separate audit records from debug logs: use `system.util.audit(...)` for audit-trail entries and `system.util.getLogger(...)` for troubleshooting. Use `java.util.UUID.randomUUID().toString()` for correlation IDs unless the Gateway provides a validated helper; do not assume `system.util.getUUID()` exists. For audit readback, call `system.util.queryAuditLog` with keyword arguments or omit `contextFilter`; Ignition 8.1's positional `contextFilter` is an integer bitmask, not a string wildcard.
- For Perspective table `props.data`, return a list of dictionaries keyed by field names; convert Ignition datasets explicitly with `getColumnName()`/`getValueAt()` or `toPyDataSet()` row name access before assigning rows.
- For Perspective component messages, put handlers under component/root `scripts.messageHandlers` with `messageType` plus `pageScope`, `viewScope`, and `sessionScope` booleans. Match `system.perspective.sendMessage(..., scope="<scope>")` to a listening flag, keep message types case-sensitive, read `payload` defensively with `.get(...)`, and verify with visible state or durable tags because sends are asynchronous and wrong-scope sends can be silent.
- For Perspective Table `onSelectionChange`, read selected rows from `self.props.selection.data` first and fall back to `event.data` defensively. For shared table/list detail workflows, have table and list actions send the same page-scoped payload to a root/parent handler that owns `view.custom.selected`; do not assume table selection includes row keys that were not declared as visible or hidden columns.
- For View Canvas `onInstanceClicked` scripts, use `event.index` to select `inst = self.props.instances[int(event.index)]`, read `inst.viewParams` or `inst["viewParams"]` defensively, and update parent `view.custom` state. Do not rely on `event.params` alone when the source instance can be read from `props.instances`.
- In embedded view event scripts, read context passed to that child from `self.view.params.*`. Do not expect parent `view.custom` to be reachable through the child view's `self.view`; pass needed selected values into the child `props.params`.
- For Perspective command popups, call the Project Library guard/write function, send a page-scoped result payload, then close the popup by `str(self.view.params.popupId)` in the same script; validate with a blocked case and an accepted readback.
- Treat `system.perspective.sendMessage` as context-sensitive: default/page/view sends need an attached Perspective page/view thread; Gateway/Web Dev calls can fail with no session/view attached unless a real target session/page is supplied and open.
- In Perspective session/page event scripts, use `system.perspective.openDock("<dockId>", params={...})`, `system.perspective.closeDock("<dockId>")`, and `system.perspective.toggleDock("<dockId>", params={...})` only for docks configured in page config with stable `id` values. Modal docks can block main-page clicks. Do not treat Perspective session/page dock behavior as evidence for Gateway-scope dock control.
- Use `system.perspective.getSessionInfo()` for Perspective sessions and `system.util.getSessionInfo()` for Designer/Vision sessions; they return different shapes.
- For Perspective custom methods, put methods under component/root `scripts.customMethods` with `name`, `params`, and indented function-body `script`; do not include `self` in `params`. Same-view call paths include same-component `self.methodName(...)`, same-parent sibling `self.getSibling("<Component Name>").methodName(...)`, and child-to-parent `self.parent.methodName(...)`. These rely on the exact component hierarchy, do not cross embedded/different views, and should be validated in-browser with visible state/tag readback; missing methods can raise runtime attribute errors such as no attribute `methodName`.
- For nullable Perspective component values such as dropdown selection, use Python `None`, not `null` or `"null"`. Guard `len(value)` and avoid bare truthiness when `0` or `False` can be valid selections.
