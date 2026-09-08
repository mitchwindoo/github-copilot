# Validated Navigation Background Close

This is a fixed Ignition Vision 8.3.8 Client component-event pattern. It validates one retained navigation fixture, not a general scheduler or remote-control bridge.

## Proven source boundary

Import and capture the installed Java sleep primitive before the first UI side effect:

```python
from java.lang import Thread

fixed_sleep = Thread.sleep
```

After that boundary succeeds, the fixed handler may open only the fixed Target A Window. Its bounded worker runs through `system.util.invokeAsynchronous` and calls the captured `fixed_sleep`. Its fixed close callback runs through `system.util.invokeLater` and closes Target A on the EDT. The visible success state is written by the fixed event path and transported through the fixed observation contract.

Do not use `system.util.sleep` in this tested Client event context. It was absent at runtime and stopped execution after Target A opened. Capturing the supported primitive before opening the Window prevents that exact partial-state failure.

## Evidence boundary

The credited Client proved:

- exact fixed event dispatch and one Good/192 result write;
- Target A opened, then was absent from the final open-Window inventory;
- only `P14 Navigation Host Review` remained open;
- exact status `BACKGROUND CLOSE SCHEDULED: TARGET A`;
- final observation thread `AWT-EventQueue-0`;
- six original-resolution screenshots with clean geometry and no error dialog;
- complete phase-by-phase Client and Gateway diagnostics with no unexplained WARN or ERROR.

The evidence does not validate caller-selected paths or callbacks, arbitrary sleep durations, user-driven races, cancellation, exception propagation across background threads, shutdown behavior, Designer scripts, or other Jython contexts. Keep names, inputs, timing, side effects, result schema, and cleanup server-owned and bounded.
