# Vision Jython Runtime, Scope, And Patterns

## Contents

- [Scope matrix](#scope-matrix)
- [Designer Design Mode and runtime previews](#designer-design-mode-and-runtime-previews)
- [Component lookup](#component-lookup)
- [Background work and the EDT](#background-work-and-the-edt)
- [Dynamic Vision layout geometry](#dynamic-vision-layout-geometry)
- [Tag reads and writes](#tag-reads-and-writes)
- [Datasets](#datasets)
- [Chart mutations and notification readback](#chart-mutations-and-notification-readback)
- [Java booleans, numbers, and dates](#java-booleans-numbers-and-dates)
- [Exceptions and bounded failures](#exceptions-and-bounded-failures)
- [Component events and extension functions](#component-events-and-extension-functions)
- [Logging](#logging)
- [Review checklist](#review-checklist)

## Scope Matrix

| Script location | Runtime | Common supplied values | Swing access | Side-effect warning |
|---|---|---|---|---|
| Component/window event | Vision Client or Designer preview | `event` | Yes, normally on EDT | Keep short; one action can fire repeatedly. |
| Component extension function | Vision Client | `self` plus function arguments | Yes, normally on EDT | Respect the extension function's return contract. |
| Client Event Script | One copy per client | Event-specific values | Yes through EDT | Writes/navigation multiply across clients. |
| Client message handler | Vision Client | `payload` | Only through bounded EDT work | Validate addressing, expiry, and exact operation. |
| Project Library function | Caller-dependent | Explicit parameters | Caller-dependent | State the allowed caller scopes. |
| Tag Event Script | Gateway | `tagPath`, `previousValue`, `currentValue`, `initialChange`, `missedEvents` | No Vision components | It can run once per tag/event and must be bounded. |
| Gateway Event Script | Gateway | Event-specific values | No Vision components | Never assume a project default tag provider. |

Do not use `event.source` where no `event` exists. Do not call Vision GUI functions from Gateway scope.

## Designer Design Mode And Runtime Previews

Designer Design Mode can evaluate a direct binding without executing a component event or PMITimer action script. This creates a distinctive partial state: a live tag value changes, while history-derived statistics, dynamic bars, markers, or datasets remain at their serialized defaults. Do not diagnose the Jython path from that view alone.

- Ask `ignition-vision` to launch a fresh Vision Client and validate the event path through its external lifecycle.
- Wait for at least two refreshes and assert both the derived values and runtime geometry.
- Keep the slow history/query work off the EDT and apply the bounded component update on the EDT.
- If Design Mode must be useful for gallery review, serialize a clearly marked representative preview such as `DESIGN PREVIEW / CLIENT POPULATES LIVE HISTORY`.
- Runtime success must overwrite every preview statistic, status, marker, and bar. Preview data is explanatory UI, not live evidence.

If a refresh is intentionally Client-only, branch on the documented system flags instead of letting Designer Preview execute a path it cannot satisfy:

```jython
flags = int(system.util.getSystemFlags())
in_designer = bool(flags & 1)
in_designer_preview = bool(flags & 2)
in_client = bool(flags & 4)

if in_designer:
    # Leave the explicitly labelled serialized snapshot intact.
    skip_refresh = True
else:
    skip_refresh = False

if not skip_refresh:
    schedule_client_refresh()
```

The Designer flag remains set in Designer Preview, so this guard covers both Designer modes. Replace `schedule_client_refresh()` with the fixed bounded entry point for the component. Do not use this guard when Preview Mode is a required and supported execution target. In a deployed Client, a transient history/query failure should preserve the last known-good bars and statistics, mark them stale, and expose a bounded failure status; collapsing bars to zero invents a valid-looking distribution.

## Component Lookup

From a component event:

```jython
source = event.source
window = system.gui.getParentWindow(event)
root = window.rootContainer
status = root.getComponent('StatusLabel')
```

Pass the event object itself to `system.gui.getParentWindow`. Use `event.source` for component traversal, but do not substitute it for the event in this call; installed Vision overload resolution can reject the component because it expects a `java.util.EventObject`.

From an extension function:

```jython
source = self
root = source.rootContainer
```

From a client script, require the exact window to be open:

```jython
window_path = 'Operations/Main'
open_paths = list(system.gui.getOpenedWindowNames())
if window_path not in open_paths:
    raise ValueError('Required window is not open: ' + window_path)
window = system.gui.getWindow(window_path)
component = window.rootContainer.getComponent('ProcessArea').getComponent('ValueLabel')
```

For fixed automation, validate the component class as well as the name/path. Component-local bounds must be accumulated through ancestors before comparing screen/root positions.

## Background Work And The EDT

Run slow work in the background and return only the UI mutation to the EDT:

```jython
def load_data():
    try:
        rows = system.db.runNamedQuery('Operations/RecentEvents', {'limit': 100})

        def apply_rows():
            event.source.parent.getComponent('Results').data = rows

        system.util.invokeLater(apply_rows)
    except Exception as exc:
        system.util.getLogger('vision.operations').error('RecentEvents failed', exc)

system.util.invokeAsynchronous(load_data)
```

For a fixed message handler that may be called off the EDT:

```jython
from java.lang import Runnable
from javax.swing import SwingUtilities

class UiCall(Runnable):
    def __init__(self, function):
        self.function = function

    def run(self):
        self.function()

def on_edt(function):
    if SwingUtilities.isEventDispatchThread():
        function()
    else:
        SwingUtilities.invokeAndWait(UiCall(function))
```

Keep the `on_edt` function body bounded. Never perform a database query, network call, sleep, unbounded loop, or large serialization inside it.

## Dynamic Vision Layout Geometry

Run geometry mutations on the EDT. In an `FPMILayout` container, ordinary Swing `component.setBounds(...)` can appear to succeed and then be reset by the Vision layout pass. When runtime behavior truly requires changing component geometry, update Vision's preferred and actual bounds together, then revalidate and repaint the parent once after the batch:

```jython
from java.awt import Dimension
from java.awt.geom import Rectangle2D
from com.inductiveautomation.factorypmi.application.components.util import FPMILayout

def set_vision_bounds(component, x, y, width, height):
    x, y = int(x), int(y)
    width, height = int(width), int(height)
    bounds = Rectangle2D.Double(float(x), float(y), float(width), float(height))
    component.setPreferredSize(Dimension(width, height))
    FPMILayout.setPreferredBounds(component, bounds)
    FPMILayout.setBounds(component, bounds)

# Apply all bounded component changes first.
plot.revalidate()
plot.repaint()
```

`FPMILayout` is an IA implementation class, so confirm the exact class and overloads against the installed target version before relying on this pattern. Prefer static serialized geometry when the screen does not need runtime movement. Validate the rendered result after at least two refreshes; a direct tag value moving does not prove that timer-driven bars, markers, or history-derived fields changed.

## Tag Reads And Writes

Read fully qualified paths and check quality:

```jython
paths = ['[Provider]Area/Line/Speed', '[Provider]Area/Line/State']
values = system.tag.readBlocking(paths)
if len(values) != len(paths):
    raise ValueError('Unexpected tag result count')

for index in range(len(paths)):
    qualified = values[index]
    if not qualified.quality.isGood():
        raise ValueError('Bad quality for ' + paths[index] + ': ' + str(qualified.quality))
```

When the set is finite and known, keep every fully qualified path as an explicit string literal. This lets the external `visionWindowDependencyPreflight` scanner enumerate the same paths the client will read:

```jython
paths = [
    '[Provider]Area/Pump 1/State',
    '[Provider]Area/Pump 1/RPM',
    '[Provider]Area/Pump 2/State',
    '[Provider]Area/Pump 2/RPM',
]
system.tag.readAsync(paths, apply_read)
```

Do not replace that fixed list with a loop such as `'[Provider]Area/Pump %d/' % pump_number` when release evidence depends on static dependency discovery. A scanner can conservatively report the formatted fragment as a literal invalid path even though runtime interpolation succeeds. For genuinely dynamic paths, validate every generated path against a bounded allowlist, have the external workflow read the resolved paths directly, and report static dependency evidence as incomplete rather than manufacturing a pass.

Check every write result:

```jython
paths = ['[Provider]Area/Line/Command']
qualities = system.tag.writeBlocking(paths, [1])
if len(qualities) != len(paths):
    raise ValueError('Unexpected write result count')
for quality in qualities:
    if not quality.isGood():
        raise ValueError('Tag write failed: ' + str(quality))
```

Do not write from a property-change script unless that side effect is explicitly required and protected against feedback loops. A Client Event Script can run in many clients; do not use it for a singleton write without a coordination contract.

## Datasets

Ignition datasets are immutable. Build or transform a new dataset:

```jython
headers = ['Timestamp', 'Value', 'Quality']
rows = []
for item in bounded_items:
    rows.append([item['timestamp'], float(item['value']), str(item['quality'])])
result = system.dataset.toDataSet(headers, rows)
```

Validate before indexing:

```jython
required = ['Name', 'State']
columns = list(dataset.getColumnNames())
for name in required:
    if name not in columns:
        raise ValueError('Missing dataset column: ' + name)
if dataset.getRowCount() > 500:
    raise ValueError('Dataset exceeds the supported row limit')
```

For a Template Repeater in dataset mode, match column names exactly to public template parameters. Treat each column as a four-part contract: dataset cell Java type, public template property type, binding adapter value class, and destination JavaBean setter type. Verify all four. An integer-looking Jython value may arrive at a binding as `java.lang.Double` (for example, `0.0`) and fail an integer-only Swing setter. When a numeric control is not required, a formatted string bound to a label is often the safer presentation contract:

```jython
from java.lang import String

stability = int(round(max(0.0, min(100.0, score))))
row.append(String('%d / 100' % stability))
```

After opening a repeated template in a fresh client, inspect focused client logs for property-setting errors; dataset schema inspection and text-fit alone are insufficient. For Java-backed chart/schedule datasets, preserve the intended Java column types instead of relying on Python inference.

For a native Status Chart with data format `0`, build all three typed datasets explicitly. The primary data uses a `java.util.Date` timestamp followed by one `java.lang.Integer` state column per series. The properties dataset uses `String`, `Integer`, and `java.awt.Color` columns named `SeriesName`, `Value`, and `Color`, and it must map every reachable series/state pair exactly once. The legend uses `Color` and `String` columns. Apply the bounded datasets on the EDT, repaint once, and have `ignition-vision` verify runtime row/column counts, the allowed state range, two distinct refresh signatures, and native pixels. Do not infer a completed refresh from the properties or legend alone.

For a native Gantt Chart, construct the exact typed task schema `Task Name: java.lang.String`, `Start Date: java.util.Date`, `End Date: java.util.Date`, and `Percentage Done: java.lang.Integer`. Build bounded historian- or query-derived intervals off the EDT, reject reversed dates and completion values outside `0..100`, then assign the completed dataset on the EDT. If the intervals come from analog thresholds rather than a work-order source, expose them as observed signal windows instead of implying planned or executed maintenance.

Do not force one dataset to satisfy two incompatible presentation contracts. Keep `java.util.Date` values in a native Equipment Schedule dataset so its renderer and interval logic receive the expected types. If a separate read-only table must display exact fixed-width times, construct a display dataset with explicit String columns:

```jython
from java.lang import String

ledger_rows = []
for job_name, start_date, end_date in bounded_intervals:
    ledger_rows.append([
        String(job_name),
        String(system.date.format(start_date, 'HH:mm:ss')),
        String(system.date.format(end_date, 'HH:mm:ss')),
    ])
ledger = system.dataset.toDataSet(['Job', 'Start', 'End'], ledger_rows)
```

Keep the original Date-backed schedule dataset separate. Validate both schemas and then inspect the longest reachable ledger value in a fresh Vision Client; a correct Java type does not prove that the rendered cell is wide enough.

When Jython formats a data-derived label, enumerate the bounded output states and test the longest reachable string in the target client. A preview row that fits is not evidence that every runtime state count, alarm label, unit, or negative/decimal value fits.

For a Power Table, `selectedRow` and `getSelectedRows()` describe rows in the current visible view. Sorting can change which underlying dataset record occupies a visible row. Guard `selectedRow == -1`, validate the view index, translate it through `getRowsInViewOrder()`, and only then read the backing dataset. Keep view indices and underlying dataset indices as separate variables.

## Chart Mutations And Notification Readback

Treat a multi-dataset Java-backed chart update as a transaction on the Swing EDT:

1. Validate the fixed component path/class, chart type, dataset descriptors, axes, renderers, dataset count, series keys, and an immutable identity marker before mutation.
2. Snapshot the exact previous typed datasets and marker text.
3. Call the underlying chart's `setNotify(False)`, apply the bounded dataset and label changes, and always restore `setNotify(True)` in `finally`.
4. After notification resumes, re-read both component properties and runtime plot datasets. Verify schemas, Java types, row counts, exact X/Y values, descriptors, dataset-to-axis mapping, renderers, labels, and the unchanged marker.
5. On failure, restore the snapshots with notification disabled, clear any transient live-point dataset, apply unambiguous failure text, and perform the same complete readback both before and after the rollback's final `setNotify(True)`.

`setNotify(True)` can synchronously rebuild or alter runtime chart state. A verification performed only before that call is not a completion check. Never report a completed rollback, coherent chart, or retained-curve policy when any post-notification readback differs. Do not rewrite the immutable marker to manufacture a passing result; report marker drift and fail closed.

## Java Booleans, Numbers, And Dates

Normalize strict booleans without accepting arbitrary truthy values:

```jython
from java.lang import Boolean

def strict_boolean(value, field_name):
    if isinstance(value, bool):
        return value
    if isinstance(value, Boolean):
        return value.booleanValue()
    raise ValueError(field_name + ' must be a boolean')
```

Remember:

- `long` exists in Jython 2.7.
- Java numeric wrappers may require explicit `int`, `long`, or `float` conversion.
- Use `java.util.Date`/Ignition date functions where a component expects a Java date.
- Do not coerce request text with `bool(text)`.
- Preserve declared Java dataset types when serializing a native component.

## Exceptions And Bounded Failures

Java calls can raise `java.lang.Throwable` outside ordinary Python exception expectations. Convert failures only at a narrow boundary:

```jython
from java.lang import Throwable

try:
    result = perform_fixed_operation()
except Throwable as exc:
    result = {'ok': False, 'error': str(exc)[:300]}
except Exception as exc:
    result = {'ok': False, 'error': str(exc)[:300]}
```

Do not return unrestricted stack traces, payloads, dataset cells, credentials, or component objects through a diagnostic mailbox.

## Component Events And Extension Functions

Filter property-change scripts:

```jython
if event.propertyName == 'value':
    value = event.newValue
    event.source.toolTipText = 'Value: ' + str(value)
```

Avoid recursive writes to the same property. Prefer bindings for continuous data movement and use events for bounded interaction or derived presentation that cannot be expressed safely as a binding.

Serialized Vision component event scripts may run with distinct global and local mappings. Do not rely on a nested helper function closing over names assigned at the event script's top level; that name may be resolved as a missing global when the helper runs. Pass required components/values as explicit arguments, or keep a short event handler straight-line. This caution is specific to event-script execution and is not a claim that Jython closures generally fail.

Treat editor-injected `event` and `system` the same way. Resolve them in the top-level event body and pass them into the helper; nested asynchronous callbacks can then close over ordinary function parameters:

```jython
def request_refresh(source, system_api):
    canvas = source.parent.getComponent('PumpCanvas')
    paths = ['[Provider]Area/Pump/RPM']

    def apply_read(qualified_values):
        if len(qualified_values) != 1 or not qualified_values[0].quality.isGood():
            return

        def apply_ui():
            canvas.toolTipText = 'RPM %.1f' % float(qualified_values[0].value)

        system_api.util.invokeLater(apply_ui)

    system_api.tag.readAsync(paths, apply_read)

request_refresh(event.source, system)
```

Compiling the snippet proves syntax only. Run the exact event in a fresh Vision Client and fail on relevant client-log or captured launcher-output exceptions; a serialized default or first screenshot can exist even when the timer/event handler fails every refresh.

Extension functions must honor the component contract: expected arguments, return type, and threading. Keep renderer/configure extensions deterministic and avoid I/O.

## Logging

```jython
logger = system.util.getLogger('vision.operations.transfer')
logger.info('Transfer view opened')
```

Use stable hierarchical logger names and bounded request/resource identifiers. Redact passwords, tokens, cookies, authorization values, identity tokens, and secrets. Do not use logs as a dataset export channel.

Vision Client logging and Gateway logging are separate. Ask the external API workflow to collect from the correct JVM.

## Review Checklist

- Exact target version and scope identified.
- Python 2.7-compatible syntax only.
- Editor-supplied variables match the script location.
- Swing access is on the EDT; slow work is not.
- Tag paths are qualified and quality is checked.
- Dataset schemas, sizes, and Java types are validated.
- Longest reachable script-generated label values are exercised in the target client.
- Strict booleans and Java exceptions are handled deliberately.
- Side effects, bounds, timeouts, and restore behavior are explicit.
- Logs are bounded and redacted.
- Code compiles in the installed target IA Jython runtime.
