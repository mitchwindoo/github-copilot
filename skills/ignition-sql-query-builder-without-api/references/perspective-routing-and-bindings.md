# Perspective Routing and Query Bindings

## Contents

- Perspective URL And Route Filters
- Perspective Binding Pattern

## Perspective URL And Route Filters

- For route-parameter query pages, declare the route input as a plain top-level view param such as `"params": {"matchText": ""}` with `propConfig["params.matchText"].paramDirection = "input"`, then bind the Named Query param to `"{view.params.matchText}"`.
- Keep path segment values route-safe: asset IDs, slugs, or exact text filters are safer than SQL wildcard strings. Encode spaces as `%20` and literal plus signs as `%2B`; do not assume raw `+` means space in a path segment.
- Treat raw `?` as a path/query-string delimiter, not a value character. Encode literal question marks as `%3F` and literal equals signs as `%3D` inside path segment values.
- Treat raw `#` as a browser fragment delimiter, not part of a path segment value. Encode literal hash signs as `%23`, and ask the user to verify the visible `view.params.<name>` echo, row-count/table result, and `window.location.hash` when hashes may appear.
- Treat raw `/` as a path separator. Encode a literal slash as `%2F` only when it must remain inside one route parameter segment, and ask the user to verify target behavior because route handling or reverse proxies can normalize encoded slashes differently.
- Do not depend on an encoded `%` wildcard such as `%25` inside a Perspective path segment; it can fail route decoding before the query binding runs. For wildcard search, prefer a TextField/form input or another target-verified transformation outside the URL path segment.
- Do not assume a URL query string on a static Perspective page route populates top-level `view.params` or automatically drives a Named Query binding. For query-string-driven filters, use the read-only Perspective page property `page.props.urlParams`, add a visible echo, and bind the Named Query parameter from `"{page.props.urlParams.<name>}"` or a bridge such as `view.custom.<name>`.
- Test omitted and empty query-string values separately when a URL filter has an all/default state. Keep the Named Query parameter present and branch intentionally, for example `:matchText IS NULL OR :matchText = '' OR displaypath LIKE :matchText`.
- Do not use repeated same-name query-string keys such as `?matchText=A&matchText=B` as a multi-select or dynamic `IN` shortcut; use distinct slots or a target-verified bridge/normalizer.
- Do not use bracket-style query-string keys such as `?matchText[0]=A` or `?matchText[]=A` as array shortcuts unless the user's target proves that exact shape. Expect Perspective to expose those as literal `page.props.urlParams` keys (`matchText[0]`, `matchText[]`) rather than populating `page.props.urlParams.matchText`; if both plain and bracketed forms are present, ask the user to verify which scalar drives the query.
- Encode query-string values deliberately: use `%20` for spaces when generating URLs, `%2B` for literal plus signs, `%26` for `&`, `%3D` for `=`, `%23` for `#`, and `%25` for `%` when those characters are part of the value.
- URL encoding is not SQL `LIKE` escaping. If a decoded query-string value containing `%` or `_` is passed to `displaypath LIKE :matchText`, those characters remain SQL wildcards. Use `%2525` only when the intended URL value contains the characters `%25`, and use equality or explicit `LIKE` escaping/normalization when the SQL match must treat `%` or `_` literally. If using `LIKE ... ESCAPE '!'`, pre-escape the parameter value itself, for example `!` -> `!!`, `%` -> `!%`, and `_` -> `!_`; adding an `ESCAPE` clause alone does not stop an unescaped wildcard from acting as a wildcard. Ask the user to verify both wildcard and literal-match cases on the target.
- Do not assume `LIKE` or `=` case behavior is portable. Case sensitivity depends on the database, collation, connection/session settings, and operator (`LIKE`, `=`, `ILIKE`, `COLLATE`, etc.). When case matters, ask the user to verify exact, lower, and upper case values on the target. For required case-insensitive matching, use a target-verified normalizer or collation such as `LOWER(column) = LOWER(:param)`, `ILIKE`, or `COLLATE`, and call out index/performance effects for the user to check.
- URL-delivered SQL-looking strings are safe only when they remain data bound through Named Query `Value` parameters or prepared calls. Do not concatenate decoded URL values into SQL, do not switch to QueryString parameters for user text, and do not treat URL encoding as SQL escaping.


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
            "literalText": "\"<literalValue>\"",
            "propertyValue": "{view.params.asset}",
            "routeFilter": "{view.params.matchText}",
            "dropdownFilter": "{../FilterDropdown.props.value}",
            "checkboxFilter": "{../FilterCheckbox.props.selected}",
            "toggleSwitchFilter": "{../FilterToggle.props.selected}",
            "minValue": "{../MinValue.props.value}",
            "startDateValue": "{../StartDate.props.value}",
            "queryUrlFilter": "{page.props.urlParams.matchText}"
          },
          "polling": {"enabled": true, "rate": "5"}
        }
      }
    }
  }
}
```

Use known or exported result columns for table `field` values only after confirming the returned names are exact, unique, and simple enough for Perspective bindings and transforms.

For a Perspective Button or script that should navigate to a query-string filter URL, build a full client URL and pass it by keyword:

```python
system.perspective.navigate(
    url="http://<gatewayHost>:<port>/data/perspective/client/<projectName>/<pagePath>?matchText=<encodedValue>"
)
```

If that URL should open in a new browser tab, add the documented optional `newTab` argument and ask the user to verify distinct-tab behavior, not just the rendered target route. Have them capture the browser tab/page list before and after the click, confirm the source tab remains on the source route, confirm a separate target tab opens with the expected target URL/search, and verify the target tab's visible URL-param echo, row count, and table state:

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

For a Perspective Button that should manually refresh a query-bound component, call `refreshBinding` on the component and property that owns the query binding. For example, when a sibling Label owns the query binding on `props.text`:

```python
self.getSibling("<LabelName>").refreshBinding("props.text")
```

For an IA Table with the query binding on `props.data`:

```python
self.getSibling("<TableName>").refreshBinding("props.data")
```

Ask the user to verify the exact component name and bound property path in Designer. Do not refresh the parent container, table columns, or an unrelated status label when the query binding lives on the Table's `props.data`. If proving manual-only refresh, disable polling and ask the user to confirm a visible query tick/status value stays stable before the click and changes after the click, with a separate click/status echo. For tables, ask for a row-count/tick/status label derived from the Table's `props.data` or actual changing row values, because paging and virtualization can make DOM-only table-cell checks ambiguous.

Set table columns from known query output:

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

For KPI labels or counters bound to a Named Query, keep the same outer `{"binding": {...}}` wrapper under `propConfig["props.text"]` and use a script transform that checks row count before indexing Dataset/PyDataSet or list-like results. Treat missing required params and zero rows as separate cases: a valid zero-row result is a proven query outcome, while a missing required param is a binding defect that may leave default/fallback text visible. Browser-visible fallback text can look identical for a valid empty result and a missing-param binding, and the missing-param case may produce no relevant console/page errors. Do not let a defensive transform that returns `0`, `"No rows"`, or another benign fallback for `None` or errors stand in for parameter-map proof; ask the user to verify every required parameter in the Named Query Designer preview and inspect the Perspective binding JSON.

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


