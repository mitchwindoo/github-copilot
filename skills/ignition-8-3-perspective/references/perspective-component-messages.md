# Perspective component messages

Use this workflow only after inspecting live Ignition 8.3 component resources on the target build. Treat each message scope combination as a separate behavioral contract.

## Contents

- Tested receiver serialization
- Tested sender
- Validation gates
- Embedded parent and child scope matrix
- Session scope across active pages
- Closed browser page retention
- Browser reload lifecycle
- Route replacement lifecycle
- Execution-queue boundary
- Boundaries

## Tested receiver serialization

The tested handler is stored on the receiving component under `scripts.messageHandlers`:

```json
{
  "scripts": {
    "customMethods": [],
    "extensionFunctions": null,
    "messageHandlers": [
      {
        "messageType": "example-message",
        "pageScope": true,
        "script": "\tmessage = payload.get(\"text\")\n\tself.view.custom.status = message",
        "sessionScope": false,
        "viewScope": false
      }
    ]
  }
}
```

Keep the message type and all three Boolean scope flags explicit. The tested script received a dictionary-like `payload`, accessed it with `payload.get`, and synchronously updated visible view custom state.

## Tested sender

The tested Button used an ordinary Gateway-scoped script action:

```python
system.perspective.sendMessage(
    "example-message",
    {"text": "PAGE_PASS"},
    scope="page"
)
```

The sender scope must match a scope enabled on the receiver. In the tested negative, the same message type sent with `scope="view"` did not reach a handler whose `viewScope` was false and `pageScope` was true.

## Validation gates

1. Export and verify the exact receiver `scripts` object, handler fields, sender event, message type, payload, and scope.
2. Start from deterministic visible state and establish that the target resource is not already mounted.
3. Open a fresh page and record initial screenshot, geometry, console, and official session script metrics.
4. Invoke a unique mismatched-scope control. Require exact unchanged visible state, no received payload marker, and one sender-only script-metric increment.
5. Invoke a unique matching page-scope control. Require exact payload-derived visible state and a count-1 receipt marker. Require script metrics consistent with one sender plus one handler.
6. Correlate the exact mounted resource and component/binding counts. Require unchanged project content, stable supporting APIs, a clear scan lock, bounded clean or causally reconciled logs, screenshots for all states, and session cleanup.

Visible state alone does not prove which script ran. Combine the negative and positive states with the session script-metric deltas and exact stored resource.

## Embedded parent and child scope matrix

One tested page mounted a parent view and one embedded child. Both root containers declared separate handlers for the same two message types:

- the `view` handler set only `viewScope: true`;
- the `page` handler set only `pageScope: true`.

The parent and child each stored independent view/page counters and last-origin markers. The exact sequence reproduced in two fresh sessions:

| Sender and scope | Parent view count | Child view count | Parent page count | Child page count |
|---|---:|---:|---:|---:|
| Initial | 0 | 0 | 0 | 0 |
| Parent sends `view` | 1 | 0 | 0 | 0 |
| Child sends `view` | 1 | 1 | 0 | 0 |
| Parent sends `page` | 1 | 1 | 1 | 1 |
| Parent repeats `page` | 1 | 1 | 2 | 2 |

This proves that the tested `view` send stayed within its originating view while the tested `page` send reached one matching parent handler and one matching embedded-child handler exactly once. The exact cumulative script sequence was `0, 2, 4, 7, 10`: each view send ran one sender and one handler; each page send ran one sender and two handlers.

Require exact painted counters and origins in both views, one registered parent and child mount, stable session/page identity, zero reconnects, and exact script counts. Treat expression metrics only as nondecreasing execution correlation. Across discovery and confirmation runs, expression counts varied despite identical paint and scripts.

Do not assume the official page Views API contains only the primary and embedded resources. The tested page also registered a configured shared dock resource, so aggregate view/component/binding counts included that resource. Identify the parent and child by exact `resourcePath`.

Always inspect and save the complete bounded Gateway log result. In the tested final window, one unrelated warning from another resource occurred while T95 had zero claim-relevant warnings; report that distinction instead of calling the complete window clean.

## Session scope across active pages

For a session receiver, set only `sessionScope` true:

```json
{
  "messageType": "example-session-message",
  "pageScope": false,
  "script": "\torigin = payload.get(\"origin\")\n\tself.view.custom.lastOrigin = origin",
  "sessionScope": true,
  "viewScope": false
}
```

Send with the matching scope:

```python
system.perspective.sendMessage(
    "example-session-message",
    {"origin": "SOURCE"},
    scope="session"
)
```

The tested topology used two active pages, A and B, in one browser context and page C in a separate context. Official Perspective APIs—not cookie assumptions—proved that A/B shared one session with distinct page IDs and C belonged to another session. Every page mounted one parent and one embedded child receiver.

| Send | A parent/child | B parent/child | C parent/child | Script delta |
|---|---|---|---|---:|
| A parent sends | receipt | receipt | unchanged | shared session +5 |
| B child sends | receipt | receipt | unchanged | shared session +5 |
| C parent sends | unchanged | unchanged | receipt | C session +3 |
| A child sends | receipt | receipt | unchanged | shared session +5 |

The +5 consists of one sender plus four matching handlers across two pages. The +3 consists of one sender plus the parent and child handlers on C. Exact counters and payload origins proved one receipt per matching mounted view in discovery and two fresh confirmations.

For this test, correlate each page through official session, page, and view endpoints. Do not assume two browser tabs are separate Perspective sessions. Treat a painted `session.props.id` or `page.props.pageId` as a cross-check only; diagnostic identity paint was delayed during failed harness attempts even though the main view state rendered.

Bring each background page to the foreground before browser screenshots. Save every page at every state, inspect geometry and browser diagnostics, and query a complete bounded Gateway WARN-or-higher window even when all paint is correct.

## Closed browser page retention

Do not assume that closing a browser page immediately removes its server-side Perspective page or message handlers. In the exact tested headless `page.close()` lifecycle, pages A and B initially shared one officially identified Perspective session and each mounted one parent plus one embedded-child session receiver. Fifteen seconds after closing B, the official session/page/view APIs still returned A and B and both T97 views on each page.

A send from visible page A after that close advanced the shared session script metric by five: one sender plus A's two visible handlers and B's two retained hidden handlers. A newly opened page D then joined the same session with fresh counters and no replay. Its child send advanced scripts by seven: one sender plus six handlers across A, retained B, and D. A separate-session control page remained isolated and advanced by three for its sender plus two local handlers. Discovery and two fresh confirmations reproduced these exact deltas with zero reconnects, browser errors, or claim-relevant Gateway warnings.

After any client close, query the official Perspective session, page, and view endpoints before reasoning about membership or handler cleanup. A closed browser object and an absent visible tab are not sufficient evidence that the server-side page is gone. Keep any action that can be triggered by a retained handler safe under delayed cleanup.

The qualified duration is only at least 15 seconds. This does not establish indefinite retention, eventual cleanup timing, human tab-close or other browser behavior, Designer behavior, navigation, reload, reconnect, logout, session expiration, crash behavior, delivery ordering, exceptions, or security. Test each lifecycle separately.

## Browser reload lifecycle

Treat ordinary browser reload as distinct from page close. In the exact tested Playwright/Chromium `page.reload()` sequence, pages A and B shared one official Perspective session and each mounted one parent plus one embedded-child session receiver. Page C was an isolated control session. Before reload, one A send established message count 1 and origin `A-PARENT` in all four A/B receivers.

Reloading B preserved all of the following in discovery and two fresh confirmations:

- official Perspective session ID;
- official Perspective page ID;
- parent and child mount tokens written by their startup scripts;
- parent and child startup counts of one;
- parent and child message count/origin state;
- exactly two official pages in the shared session; and
- one parent and one embedded-child receiver on each page.

The reload added zero script executions and exactly one official reconnect. Subsequent sends from A and reloaded B each added five scripts—one sender plus four handlers—so the receiver set remained active without an observable duplicate. The isolated C send added only three scripts in its own session.

Correlate painted page/session IDs, mount tokens, lifecycle counters, message state, official session/page/view topology, script metrics, reconnect metrics, screenshots, browser diagnostics, and the complete Gateway log window. No one signal is sufficient by itself.

This qualifies only one ordinary `page.reload()` after a settled route on the tested build. It does not establish hard reload, cache clearing, browser restart, navigation, tab close, network interruption, reconnect storms, session expiration, Gateway restart, Designer behavior, other browsers, or other view topologies. The reconnect count proves the observed metric change, not transport implementation details.

## Route replacement lifecycle

Navigation and Browser Back/Forward behaved differently from ordinary reload in the tested two-route parent/child topology. Each route change shut down the outgoing route's two views, freshly mounted the incoming two views, reset that route's prior view-local message count/origin, and replaced its mount tokens while preserving the official session/page IDs with zero reconnects.

Each session send advanced scripts by exactly three: one sender plus the currently mounted parent and child handlers. The opposite route's handlers never executed after their views left official topology. Discovery and two fresh confirmations reproduced A-to-B, Back-to-A, and Forward-to-B. Use the full counter, topology, and cleanup procedure in [page navigation](perspective-page-navigation.md); do not generalize this active-only rule to browser-close retention, where a closed page remained server-side and continued receiving in the separately tested boundary.

## Execution-queue boundary

Do not assume that moving a PropertyTree assignment into a component message handler supplies the execution queue requested by an exception. On the tested Ignition 8.3.8 build, a page-scoped handler received the message, incremented a visible handler counter, and wrote a `START` marker, but failed before its `COMPLETE` marker when it attempted to replace an Embedded View child's complete Coordinate `position` object:

```python
target = payload.get("target")
value = system.util.jsonDecode(
    '{"x":40,"y":30,"width":240,"height":80}'
)
self.getChild(target).position = value
```

The sender returned normally. The Gateway emitted one `com.inductiveautomation.perspective.ComponentModel` WARN naming the receiver's `onMessageReceived`; its traceback contained `MessageHandlerCollection$MessageHandlerImpl`, `PropertyTree.merge`, and:

```text
java.lang.IllegalStateException: Must be executed in execution queue.
```

Two strict runs reproduced the failure first against an already-canonical target and then against a deliberately different layout applied through known-good direct member writes. The latter remained exactly unchanged, proving no partial write and excluding an equal-value no-op explanation. Embedded instance identity, startup count, local state, pipe topology, non-target geometry, and a second session remained stable.

Use separate sender-return, handler-start, and handler-complete markers when testing handler failures. A returned `sendMessage` call proves neither receiver completion nor receiver success. Always correlate those markers with exact resource serialization, DOM geometry, official mounted-view topology, browser diagnostics, and per-edge Gateway logs.

This negative qualifies only the tested page-scoped component handler, complete JSON-decoded Coordinate `position` replacement, and Ignition 8.3.8. It does not establish other scopes, other PropertyTree owners, direct position-member writes, deferred/invoked-later work, other assignment types, Designer execution, or another build.

Direct member writes are a separately qualified positive in the same page-scoped handler shape:

```python
child = self.getChild(target)
child.position.x = value["x"]
child.position.y = value["y"]
child.position.width = value["width"]
child.position.height = value["height"]
```

Two strict runs each completed an alternate/canonical/alternate/canonical cycle for one known Coordinate child. Every message returned from the sender, reached handler `START`, advanced the handler count exactly once, and reached `COMPLETE`. Exact property recaptures and DOM rectangles reproduced `(80,50,210,90)` and `(40,30,240,80)` twice. Non-target geometry, pipe topology, Embedded View identity/startup/local state, and a second session remained unchanged; browser diagnostics and claim-relevant Gateway WARN+ were clean.

Keep these rules separate: the four member assignments are tested; `child.position = value` is not a shorthand for them on this build. This positive does not qualify other handler scopes, targets, members, PropertyTree owners, deferred work, or builds.

The same page-scoped pattern also completed one valid four-child batch of sixteen sequential member assignments. The retained handler iterated `TopLeaf`, `BottomLeaf`, `OriginEnd`, and `BranchLeaf`, updated a visible `APPLIED <direction> <target> <n>/4` marker after each target, and wrote `COMPLETE <direction> ALL 4` only after the loop. Two strict runs each reproduced alternate/canonical/alternate/canonical layouts with exact property tuples and DOM rectangles for every child, retained all Embedded View instances and local state, kept the recursive pipe unchanged, isolated a second session, and produced no claim-relevant WARN+ or browser diagnostics.

Do not call this sequence atomic. A separate retained test deliberately accessed missing child `MissingChild` before the third real target, after completing direct member writes for `TopLeaf` and `BottomLeaf`. The sender returned, the handler stopped at `APPLIED alternate BottomLeaf 2/4`, and Gateway emitted one `com.inductiveautomation.perspective.ComponentModel` warning:

```text
AttributeError: 'NoneType' object has no attribute 'position'
```

The next explicit capture and DOM geometry showed Top/Bottom at alternate values while Origin/Branch remained canonical. Earlier writes were not rolled back. A following valid canonical batch completed all four targets and restored the canonical layout without remounting children or changing the pipe; a valid alternate batch and second canonical recovery also completed. Two strict runs reproduced this exact failure, mixed state, and recovery.

Validate all targets and values before starting when partial layout is unacceptable. Keep per-target progress, explicit post-failure recapture, and a tested recovery path. This boundary does not establish other exceptions, rollback implementations, intermediate client paint, concurrent messages, or rapid re-entry.

For child existence, one tested safer pattern resolved every requested child before entering the mutation loop:

```python
children = {}
missing = []
for name in requested:
    child = self.getChild(name)
    if child is None:
        missing.append(name)
    else:
        children[name] = child

if missing:
    self.view.custom.handlerResult = "REJECTED %s BEFORE WRITES" % ",".join(missing)
    return
```

Two strict runs rejected `MissingChild` first from a fully canonical layout and then from a fully alternate layout. Both sends returned, handler counts advanced, visible rejection was exact, every property tuple and DOM rectangle remained unchanged, and Gateway WARN+ stayed clean. Valid alternate and canonical batches still completed afterward; instances, local state, pipe topology, and the isolated session remained stable.

This qualifies child-existence prevalidation only. Validate required members, value types/ranges, permissions, and any other failure source separately; a later assignment can still fail after writes begin.

Required-member and numeric-type validation are separately qualified for the four Coordinate position members. The tested handler iterated `x`, `y`, `width`, and `height` for every target before its mutation loop, returned a property-specific `MISSING` rejection when a member was absent, and used this numeric gate:

```python
value = layout[name][member]
if isinstance(value, bool) or not isinstance(value, (int, long, float)):
    self.view.custom.handlerResult = (
        "REJECTED %s.%s NONNUMERIC BEFORE WRITES" % (name, member)
    )
    return
```

Two strict runs changed candidate `OriginEnd.width` to string `wide` and reproduced exact rejection from canonical and alternate current layouts. Both states retained every tuple and DOM rectangle with zero WARN+; later valid alternate/canonical batches completed normally. Explicitly exclude Boolean because Python/Jython Boolean values are integer-like.

This qualifies the tested required-member check and one nonnumeric string rejection. It does not qualify finite/range/unit validation, NaN/infinity, numeric-string coercion, permissions, or later assignment failures.

## Boundaries

The active-page contract does not establish arbitrary fan-out beyond the tested topology, more than one embedded child per page, handler ordering, asynchronous delivery, retries, exceptions, message security, rapid navigation/reconnect interactions, session-property persistence, or other scope combinations. Reload, route replacement, and closed-page retention are distinct tested lifecycle boundaries above. Test each independently before reuse.
