# Validated Navigation And Background Close

Use this pattern only for the credited fixed Ignition Vision 8.3.8 navigation fixture. It is not a general remote-navigation or arbitrary event-execution interface.

## Retained resources

The accepted `V83_SKILL_LAB` baseline retains these four native Windows:

- `P14 Navigation Host Review`
- `P14 Navigation Target A`
- `P14 Navigation Target B`
- `P14 Parameter Popup Review`

The fixed Host exposes only named, server-owned actions. The validated sequence covered Host readiness, Target A open, duplicate suppression, Target A close, typed popup open, visible wrong-parameter rejection, swap to Target B, return to Host, visible missing-target rejection, and close-during-background. Do not accept caller-selected project, Window, component, handler, script, payload, timing, or expected result.

## Background-close threading boundary

In the fixed Client component event, import `Thread` and capture its sleep function before the first UI mutation:

```python
from java.lang import Thread

fixed_sleep = Thread.sleep
```

Only after those lines pass may the fixed script open Target A and schedule its two bounded callbacks. The worker uses the captured sleep off the EDT. The close callback runs through `system.util.invokeLater` and closes the fixed Target A path on the EDT. The credited final observation contained only `P14 Navigation Host Review`, exact status `BACKGROUND CLOSE SCHEDULED: TARGET A`, thread `AWT-EventQueue-0`, and one Good/192 result write.

Do not replace this with `system.util.sleep`. In the installed Client event context, that call stopped the script after Target A opened and before either callback or visible status update. Import and capture before opening the Window so an unavailable runtime primitive cannot leave a partial UI state.

This evidence does not prove arbitrary sleep durations, caller-selected Window paths, general cancellation, concurrent user actions, shutdown races, Designer behavior, or other event contexts.

## Acceptance evidence

Require all of the following for a changed fixture:

1. Native project readback and exact logical-resource parity for every retained resource.
2. Installed-Jython execution of the exact event source and fixed callbacks.
3. One fresh owned non-Designer Client and an exact new session selected by inventory set difference.
4. All fixed phase results, including visible expected failures and the Host-only background-close result.
5. Original-resolution screenshots for every credited visual phase. Inspect complete images for geometry, clipping, overlap, scrollbars, error dialogs, identity, and state text.
6. Complete correlated Client and Gateway diagnostics after every phase and over the full cycle. A clean screen never clears an unexplained Client exception.
7. Clean Client close, temporary handler/result cleanup, exact durable project retention, tag/session/process/listener reconciliation, and untouched user-owned Designers.

Keep the four review Windows in the project after successful acceptance. Remove only temporary handlers, result transport, and owned launch artifacts.
