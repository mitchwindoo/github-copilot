# Perspective component script events

Use this workflow only after inspecting a live Ignition 8.3 component-event seed on the target build. Keep the event thin and put reusable, independently testable behavior in a top-level Project Library helper.

## Tested Button action shape

The tested Button action script is stored on the component beneath `events.component.onActionPerformed`:

```json
{
  "events": {
    "component": {
      "onActionPerformed": {
        "config": {
          "script": "\tself.view.custom.count = ProjectHelper.next_value(self.view.custom.count)"
        },
        "scope": "G",
        "type": "script"
      }
    }
  },
  "type": "ia.input.button"
}
```

The tested client resolved the top-level `ProjectHelper` module, called its synchronous function, and assigned the returned integer to view custom state. A separately tested expression binding reflected each update in a Label.

Do not embed large or environment-specific logic in the event. Validate helper input types and bounds, return deterministic values, and prove the helper independently in live Gateway scope before relying on the client event.

## Do not assume `system.util.invokeLater` exists

On the tested Ignition 8.3.8 / Perspective 3.3.8 browser session, a Button action called `system.util.invokeLater(callback, delay)` after painting a pre-call marker. The first call raised an `AttributeError` stating that the session-scope `system.util` object had no `invokeLater` member. No callback was scheduled.

Two fresh sessions reproduced the same warning. The source Table, selected BRAVO record, copied selection payload, and event trace remained unchanged through five seconds; the exact script sequence was `0,1,2,2,2`, with one selection script followed by the failed Button script and no later callback scripts.

Do not copy a Vision `system.util.invokeLater` pattern into a Perspective component event. This proves only absence in the exact tested Perspective Button session scope/build. It does not identify a supported asynchronous replacement or qualify other scopes, versions, schedulers, callbacks, Designer behavior, or redundancy. Test the intended alternative independently before documenting it.

## Narrow non-preferred `system.util.invokeAsynchronous` observation

On the tested Ignition 8.3.8 / Perspective 3.3.8 browser session, this Button-event pattern returned immediately while one worker completed later:

```python
from java.lang import Thread

view = self.view

def worker(target_view=view):
    Thread.sleep(1500L)
    target_view.custom.phase = "COMPLETED"

view.custom.phase = "LAUNCHED"
handle = system.util.invokeAsynchronous(
    worker,
    [],
    {},
    "perspective-worker"
)
```

The exact retained experiment captured the intended live view reference in the event before launching the worker and bound it as a default argument. It demonstrated one narrow runtime observation, not a recommended reusable pattern. Set immediate state synchronously before launch. The returned object reported Java type `Thread` and was alive immediately; the worker changed three captured root-view custom properties after about 1.5 seconds, and property-bound Labels painted the completed values.

Two fresh sessions reproduced the result in 1504 ms. Each stayed stable for another five seconds, with one script execution per click, no reconnect, no browser/page error, and no claim-relevant Gateway warning. The worker reported the thread name `script-invoke-async`; the supplied description did not become the observed thread name, so do not depend on that argument for naming or identity.

This is a narrow runtime observation, not a general thread-safety guarantee. It proves only one worker, one captured live root view, three view-custom property writes, and no navigation, close, reload, reconnect, or resource revision while the worker ran. Do not carry a live Perspective component, view, page, session, property-tree object, event, or other owner-scoped object into a reusable asynchronous worker. It does not qualify component-tree access, tags, queries, messages, popups, navigation, cancellation, exception propagation, multiple workers, session closure, redundancy, or other APIs/scopes/builds. Prefer off-thread work that captures only immutable primitive data and returns through a separately tested coordination mechanism. For the qualified page-message mechanism, read [perspective-asynchronous-handoff.md](perspective-asynchronous-handoff.md).

The optional project dispatch API was used only for fixed capability probes and was not an authoring dependency. When that project resource is absent, omit those probes; the official Ignition OpenAPI remains the authoring surface.

## Validation gates

1. Export the project and verify the exact event path, `type`, `scope`, script text, initial view state, helper source, and route.
2. Invoke a bounded fixed API contract that calls the exact helper with positive and negative inputs.
3. Render the route only with caller-approved programmatic browser validation.
4. Require the exact initial visible state and a unique visible enabled in-viewport Button before every click.
5. Click once per declared transition and require the exact painted result after each click. Save screenshots, DOM, geometry, URL, viewport, and console diagnostics.
6. Correlate the exact mounted view and component/binding counts through official session reads. Do not infer custom-state values from those counts.
7. Re-export and require the declared project delta, stable agent/helper contracts, clear scan lock, clean claim-relevant Gateway logs, and settled session cleanup.

Browser validation must remain read/interaction-only; author the event, helper, view, and route through approved APIs.

## Boundary

This contract does not establish other event names, event-object fields, asynchronous behavior beyond the exact `invokeAsynchronous` case, general thread safety, session/page APIs, tag writes, navigation, message handlers, security behavior, error presentation beyond the exact `invokeLater` negative, or Designer-scope execution. Test each behavior independently before adding it to a reusable skill.
