# Validated Button Event and Client Bridge

This source is validated only for Ignition 8.3.8, Jython 2.7.4, and the fixed fixture identities below.

## Native component event

Location: `PMIButton` `IncrementButton`, event set `action`, listener `actionPerformed`, `ActionAdapter.MODE_SCRIPT`, `invokeLater == false`.

```python
result = event.source.parent.getComponent("ResultLabel")
next_count = int(result.clickCount) + 1
result.clickCount = next_count
result.text = "CLICK COUNT: %d" % next_count
system.util.getLogger("VisionSkill.P03T03").info(
    "clickCount=%d" % next_count
)
```

The `ResultLabel.clickCount` custom property is primitive Int4 with initial value `0`. The event script performs exactly one state increment, one text update, and one bounded log call. It performs no tag, database, navigation, file, network, project, message, or asynchronous operation.

## Fixed Client Event Script message handler

Resource: `com.inductiveautomation.vision/message/vision-p03-t03-click`, client scope, enabled, thread type `EDT`.

The handler must accept only this exact payload:

```python
{
    "command": "increment",
    "contractVersion": "vision-button-event-bridge-1.0.0",
    "requestId": "<non-empty text, at most 128 characters>"
}
```

Its validated behavior is:

1. reject non-dictionaries, extra/missing keys, the wrong command/contract, and invalid request IDs before UI lookup;
2. compare the request ID with the fixed `VisionSkill.P03T03.lastBridgeRequestId` entry in `system.util.getGlobals()`;
3. ignore an identical request ID;
4. resolve `system.vision.getWindow("00 Blank Startup")`;
5. resolve `IncrementButton` and `ResultLabel` from the root container;
6. record the request ID before the side effect;
7. call `button.doClick()` on the EDT;
8. emit one bounded informational result.

Recording before `doClick()` is an at-most-once guard. If the component call throws after producing an effect, the outcome is ambiguous and the same request ID remains suppressed; inspect the visible client state before choosing a new ID.

## Evidence and limits

Native round-trip preserved the adapter, event set, listener method, target, script hash, builder mode, and Int4 property type/value. One fresh client visually passed `0 → 1 → 1 → 5` for one unique request, one duplicate, and four additional unique requests. The same process remained responsive and closed cleanly.

The detached launcher did not expose a supported client-log readback plane, so log statements were source-verified but their emitted records were not captured. Designer close/reopen, Gateway restart, concurrent delivery, multiple clients, other components, and other event families remain untested.
