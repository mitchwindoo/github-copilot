# Perspective Query Bindings

## Contents

- [Perspective Binding Pattern](#perspective-binding-pattern)

## Perspective Binding Pattern

For a table bound to a Named Query:

```json
{
  "propConfig": {
    "props.data": {
      "binding": {
        "type": "query",
        "config": {
          "queryPath": "<namedQueryPath>",
            "parameters": {
                "literalText": "\"<matchPattern>\"",
                "propertyValue": "{view.params.asset}",
                "routeFilter": "{view.params.matchText}",
                "dropdownFilter": "{../FilterDropdown.props.value}",
                "checkboxFilter": "{../FilterCheckbox.props.selected}",
                "toggleSwitchFilter": "{../FilterToggle.props.selected}",
                "minValue": "{../MinValue.props.value}",
                "startDateValue": "{../StartDate.props.value}",
                "queryUrlFilter": "{page.props.urlParams.matchText}",
                "queryUrlSlot0": "{page.props.urlParams.match0}",
                "queryUrlSlot1": "{page.props.urlParams.match1}"
            },
          "polling": {"enabled": true, "rate": "5"}
        }
      }
    }
  }
}
```

For a Perspective Button or script that should navigate to a query-string filter URL, build a full client URL and pass it by keyword:

```python
system.perspective.navigate(
    url="http://<gatewayHost>:<port>/data/perspective/client/<projectName>/<pagePath>?matchText=<encodedValue>"
)
```

If that URL should open in a new browser tab, add the documented optional `newTab` argument and verify a distinct target tab, not just the rendered target route. Capture the browser tab/page list before and after the click, confirm the source tab remains on the source route, and verify the target tab URL/search plus visible URL-param echo, row count, and table state:

```python
system.perspective.navigate(
    url="http://<gatewayHost>:<port>/data/perspective/client/<projectName>/<pagePath>?matchText=<encodedValue>",
    newTab=True
)
```

For a Perspective Button or script that should move between dynamic route values on an existing route-param page, pass the concrete Perspective page path by keyword:

```python
system.perspective.navigate(page="/<routePagePath>/<routeSafeValue>")
```

For a Perspective Button or script that should replace the current view and pass view parameters without changing the browser address, use the `view` argument with `params`:

```python
system.perspective.navigate(view="<viewPath>", params={"matchText": "<value>"})
```

Set table columns from preview/discovery:

```json
{"field": "<returnedColumnName>", "visible": true, "sortable": true, "editable": false}
```

For hidden master-table keys used by detail queries, keep the field in `props.data` and declare it in `props.columns` with visibility disabled:

```json
{"field": "<stableKeyColumn>", "visible": false, "sortable": false, "editable": false}
```

For a detail table or label driven by the master Table selection, bind the detail Named Query parameter from the selected row data and configure row selection on the master Table:

```json
{
  "props": {
    "selection": {
      "mode": "single",
      "enableRowSelection": true,
      "enableColumnSelection": false
    }
  },
  "propConfig": {
    "props.data": {
      "binding": {
        "type": "query",
        "config": {
          "queryPath": "<detailNamedQueryPath>",
          "parameters": {
            "selectedKey": "{../<MasterTableName>.props.selection.data[0].<stableKeyColumn>}"
          }
        }
      }
    }
  }
}
```

When building a package from an existing target Named Query, either package a copied Named Query under an allowed path and bind the table to that packaged path, or bind to the existing target query path without listing it as a packaged dependency. For copied query packages on runner `0.3.62+`, request `namedQueryRead` with `includeResourceJson: true` and write the returned raw resource beside `query.sql`; preserving only summary fields such as type, database, enabled state, params, or hand-authored `sqlType` values is not enough. Use `namedQueryPreview` columns for `props.columns[].field` and check that returned column names are unique and simple before generating `props.columns`; package dry-run validates structure and dependency files, not live runtime refresh. After apply, preview the copied query path to prove runtime execution. If page rendering matters, open the Perspective client route and verify the table actually renders preview-derived rows or, for zero-row results, verify a separate visible column/status label and empty-state label because the IA Table may not expose headers when its data is empty. For zero-row, fallback, blank-table, or no-data claims, prove the exact intended parameter map with `namedQueryPreview` and inspect the binding parameter map; a missing required query-binding parameter can leave fallback/default UI visible and produce no relevant browser console errors. If polling matters, bind a visible status label to the same query with an intentionally changing read-only value and wait in the browser for that value to change while the page stays open; keep a row-count/status label visible so a transform error cannot masquerade as a refresh. For paged table behavior, generate enough bounded rows to force another page, add a query-bound row-count label, check one visible first-page row, confirm a later/off-page row is absent before paging, click a unique pager control, and then verify the later row appears; do not require every row up to the page size to be present in the DOM because IA Table row virtualization can expose only the visible viewport. For route-param filters, declare matching input `view.params`, bind query parameters from those params, add a visible route echo/status label, and browser-open at least one route-safe matching URL plus one no-match URL. Encode route path spaces as `%20`; do not assume raw `+` means space in a path segment, because Perspective dynamic routes can treat raw `+` and `%2B` as literal plus values. Encode literal route path delimiters too: use `%3F` for `?` and `%3D` for `=` when they are part of the segment value, because raw `?` starts the query string before the route param finishes; use `%23` for literal `#`, because raw `#` starts the browser fragment and can truncate the route param before Perspective sees it. Encode literal slash as `%2F` if it must stay inside one route param; raw `/` is a path separator and can miss the route entirely. Browser-check both the `view.params` echo, any `page.props.urlParams` key that could be created by a split, and `window.location.hash` when `#` might appear. If a Button or script navigates between dynamic route values, use `system.perspective.navigate(page=<page path with route-safe concrete segment>)` and browser-test the click through URL path, `view.params` echo, and table state. If a Button or script navigates to a view with params, use `system.perspective.navigate(view=<view path>, params={<name>: <value>})`, then browser-test that the URL remains on the mounted page while `view.params`, row count, and table state update. For static routes with URL query strings, do not treat `?name=value` as equivalent to a dynamic route param; bind the Named Query param directly from `"{page.props.urlParams.<name>}"` when no intermediate transformation is needed, add visible URL-param/direct-value echoes, and browser-open omitted, empty, matching, and no-match query-string URLs when null/empty/default behavior matters. Do not use repeated same-name query-string keys as a multi-value shortcut for a direct `page.props.urlParams.<name>` binding; use distinct slots or a target-verified bridge/normalizer for multi-value URL filters. Encode URL filter values intentionally: `%20` and `+` decoded to spaces in direct `urlParams` bindings, while `%2B` decoded to a literal `+`; encode literal plus signs as `%2B`, literal `&` as `%26`, literal `=` as `%3D`, literal `#` as `%23`, and literal `%` as `%25`, then verify the decoded echo and query result. URL encoding is not SQL `LIKE` escaping: if a decoded query-string value such as `Asset%High%Alarm` or `Asset_High_Alarm` is passed to `displaypath LIKE :matchText`, the percent signs and underscores remain SQL wildcards. Use `%2525` only when the intended URL value contains the characters `%25`, and use equality or explicit `LIKE` escaping/normalization when the SQL match must treat `%` or `_` literally. A raw `&` in the query string starts another parameter, and a raw `#` starts the browser fragment instead of staying in the query value, so add visible echoes for parameters that could be accidentally split and check `window.location.hash` for hash-sensitive values. For SQL-looking URL values, keep the Named Query parameter type as `Value` and bind it as a parameter; never build SQL text from the decoded URL value or use a QueryString parameter for user-entered text. If a Button or script changes the query string, use `system.perspective.navigate(url=<full Perspective client URL with query string>)` and browser-test the click through URL path/search, target page content, URL-param echo, direct or bridged query-param value, row count, and table state; do not rely on positional `page` navigation for query-param passing. This `url=` pattern also applies when the Button lives on a separate source page and the query-backed table lives on a target page. If the workflow requires `newTab=True`, capture browser tab/page state before and after the click, verify the original/source tab remains available on the source URL, verify a distinct target tab opens with the expected target path/search, and verify the target tab's visible URL-param echo, direct or bridged query-param value, row count, and table state; do not count target-page render or current-tab navigation alone as new-tab proof. If you need normalization, defaulting, reuse, or debug visibility, first bind `page.props.urlParams.<name>` into an explicit property such as `view.custom.<name>` and bind the Named Query param from that bridged property; browser-test the bridge separately. For user-entered filters, add a visible echo/status label bound to the same input and browser-test the initial match state plus an edited no-match state. If the TextField uses `props.deferUpdates: true`, also prove the uncommitted state: the input value changes while the echo/table still show the previous committed query parameter, then Enter or blur commits the new value and the table refreshes. If the TextField uses `props.deferUpdates: false`, prove the no-explicit-commit state instead: after filling the input, the input remains focused while the echo/table refresh from the typed query parameter. For Dropdown/select filters, define explicit `props.options[].value` entries or bind `props.options` to an options query that returns/transforms to `label`/`value` objects, bind the downstream query parameter from `"{../FilterDropdown.props.value}"`, add a visible selection echo and options-loaded/status label, and browser-select both a matching option and a no-match or alternate option to prove the option list, selected scalar, query-backed label, and table refresh together. For multi-select Dropdown filters, set `props.multiSelect: true`, bind bounded scalar Named Query params from indexed selected values such as `"{../FilterDropdown.props.value[0]}"` and `"{../FilterDropdown.props.value[1]}"`, add an echo that shows the selected values in order, and browser-test an initial multi-selection plus selected-pill removal. If `props.showClearIcon: true` is enabled on the multi-select, also prove clear-all: selected pills should disappear, the echo should show an empty state, indexed scalar params should resolve through the intended null/empty-slot SQL branch or sentinel mapping, and the query-backed row count/table should update accordingly. For optional all-state Dropdowns, use an allowlisted sentinel option such as `__ALL__`, keep the required param present in every API and Perspective call, branch in SQL for the sentinel, and prove match, no-match, and all-state previews plus browser states. For clearable Dropdowns, use `props.showClearIcon: true`, branch SQL for the resulting null or mapped sentinel value, and prove the clear action changes the visible echo and query-backed table rather than only clearing the control's label. Confirm relevant browser console errors are absent, but do not use that as the only proof that a binding ran. Then rollback with explicit `viewPaths`, `namedQueryPaths`, and deletion controls only for resources the current task created.

For Checkbox-filtered query pages, bind the downstream query parameter from `"{../FilterCheckbox.props.selected}"`, add a visible selected-state echo and query-derived row-count/status label, and browser-test checked, unchecked, and rechecked states. Use API preview to prove the SQL's true, false, null, invalid, missing-param, and unexpected-param branches when those states matter.

For Toggle Switch-filtered query pages, bind the downstream query parameter from the component's `props.selected`, for example `"{../FilterToggle.props.selected}"`, not from a guessed `props.value`. The official Perspective Toggle Switch docs describe `props.selected` as the boolean selected state and the component as a bit-style on/off control similar to Checkbox. Add a visible selected-state echo and query-derived row-count/status label, browser-test selected, unselected, and reselected states, and use API preview to prove true/false, string `true`/`false`, numeric-looking `1`/`0`, null/default, invalid, missing-param, and unexpected-param branches when those states matter. Treat the bound value as target-coerced data, not guaranteed database-native boolean.

For Text Area-filtered query pages, bind the downstream query parameter from `props.text`, for example `"{../FilterTextArea.props.text}"`. Text Area is multiline; expose a visible echo that normalizes line breaks, such as replacing newline with `<LF>`, and add a query-derived row-count/status label so empty tables, no-match states, and binding mistakes cannot hide. If `props.deferUpdates` is true, browser-test a focused uncommitted edit separately from the committed blur/Enter state; for multiline entry, use real keyboard interaction and a Tab/blur commit proof rather than only a synthetic fill. Use API preview to prove multiline text, single-line text, empty/default, null/default, no-match or partial text, SQL-looking text, missing-param rejection, and unexpected-param rejection. Keep the parameter as a Named Query `Value` parameter and branch in SQL intentionally for empty/null/default states.

For Numeric Entry Field-filtered query pages, bind the downstream query parameter from the component's `props.value`, add a visible numeric echo and data-derived row-count/status label, and browser-test at least the initial value, a changed decimal value, and a zero/all-state or low-threshold value. Use API preview to prove numeric number/string, decimal, zero, null/empty/default, invalid, missing-param, and unexpected-param branches when those states matter, because a value that appears numeric in the component can still need target-specific SQL normalization.

For Slider-filtered query pages, bind the downstream query parameter from the component's `props.value` and keep `min`, `max`, and `step` as UI constraints, not the only data-validation boundary. Add a visible slider-value echo and data-derived row-count/status label, browser-test at least the initial value, an actual track/handle change, an off-step/manual or bound value when step matters, a zero/all or low-threshold value, and a max/no-row value if that state matters. Use API preview to prove numeric number/string, off-step decimal, min/max/zero, null/empty/default, invalid, missing-param, and unexpected-param branches because Slider `step` does not guarantee every value reaching SQL is step-aligned or target-normalized.

For Radio Group-filtered query pages, define explicit radio `value` entries and bind the downstream query parameter from the component's `props.value`. Add a visible selected-value echo and data-derived row-count/status label, browser-click the initial option plus at least two alternate options, and use API preview to prove allowlisted values, all-state sentinel or null/default handling, invalid values, missing-param rejection, and unexpected-param rejection.

For DateTime Input-filtered query pages, bind the downstream query parameter from the component's `props.value`. Add a visible DateTime value echo and data-derived row-count/status label, browser-test initial/in-range, alternate in-range, future/no-row, and clear/null states, and use API preview to prove epoch-millis, ISO/date text, null/empty/default, invalid, missing-param, and unexpected-param branches when those states matter.

For Table-selection detail pages, browser-test the unselected initial state and then click at least two different master rows. Verify the selected-key echo, hidden helper key availability, detail row count/status, and detail row values all change together. Use `namedQueryPreview` to prove the detail Named Query with a valid key, a second valid key, explicit null/no-selection, invalid text, SQL-looking text, missing required params, and unexpected params. Inspect `viewRead`/view JSON to confirm the binding path references `props.selection.data[0].<stableKeyColumn>` and that `props.columns` includes the hidden helper field with `visible: false`.

For Button-triggered manual refresh of a query-bound component, refresh the property that owns the query binding, not a parent container or unrelated property:

```python
self.getSibling("<LabelName>").refreshBinding("props.text")
```

For an IA Table with the query binding on `props.data`:

```python
self.getSibling("<TableName>").refreshBinding("props.data")
```

Use a visible changing query value such as a timestamp/tick and a separate click/status echo when proving the workflow. For tables, add a row-count/tick/status label derived from the Table's `props.data` or check actual row values so paging or virtualization cannot hide whether the data refreshed.

For bounded multi-value URL filters on static routes, prefer scalar slot params over repeated same-name or bracket-style query-string keys. Declare one required Named Query `Value` parameter per slot, bind each from a distinct `page.props.urlParams.<slot>` property, keep each slot present in API previews and Perspective binding maps, branch null/empty slots in SQL, and browser-test omitted, empty, slot0-match, slot1-match, and all-slots-no-match states.

For KPI labels or counters bound to a Named Query, keep the same outer `{"binding": {...}}` wrapper under `propConfig["props.text"]` and use a script transform that checks row count before indexing Dataset/PyDataSet or list-like results. Treat missing required params and zero rows as separate cases: a valid zero-row result is a proven query outcome, while a missing required param is a binding defect that may leave default/fallback text visible. Browser-visible fallback text can look identical for a valid empty result and a missing-param binding, and the missing-param case may produce no relevant console/page errors. Do not let a defensive transform that returns `0`, `"No rows"`, or another benign fallback for `None` or errors stand in for parameter-map proof; prove the exact required parameter map with `namedQueryPreview` and inspect the Perspective binding JSON.

Safe label transform body:

```python
try:
    row_count = value.getRowCount()
except Exception:
    try:
        row_count = len(value)
    except Exception:
        row_count = 0

if row_count < 1:
    return "No rows"

try:
    return value.getValueAt(0, "<columnName>")
except Exception:
    try:
        rows = system.dataset.toPyDataSet(value)
        return rows[0]["<columnName>"]
    except Exception:
        return value[0]["<columnName>"]
```
