---
name: ignition-vision-jython-83
description: Write, review, and troubleshoot Jython that executes in Ignition Vision 8.3.8 project contexts. Use for component or window events, extension functions, Client or Gateway Event Scripts, message handlers, project-library code, runtime scope, component access, data types, callbacks, or script diagnostics.
---

# Ignition Vision 8.3 Jython

Skill version: `0.2.9`

Use this skill only for code that will execute in an exact Ignition `8.3.8` environment. Verify the installed runtime and the exact script context before selecting syntax, namespaces, injected variables, Java types, component APIs, or threading behavior.

Use the separately installed `ignition-vision-83` skill for Gateway discovery, project-resource reads and writes, API calls, client launch, screenshots, external diagnostics, and end-to-end lifecycle validation.

## Establish The Contract

Before writing code, identify:

1. The exact script location and runtime scope.
2. The variables and callback arguments actually supplied by that location.
3. The target component or resource identity and expected types.
4. Every tag, query, historian, alarm, file, navigation, message, or UI side effect.
5. The execution-time, result-size, retry, and restoration bounds.
6. The compile, runtime, visual, and diagnostic evidence needed.

Do not move code between contexts merely because it compiles. Do not assume an 8.1 namespace, resource location, private class, serializer, callback signature, or component property remains valid.

## Implement Conservatively

- Prefer the current public 8.3.8 scripting surface discovered from the installed system and version-specific documentation.
- Keep handlers small, explicit, and deterministic.
- Validate inputs before component lookup or side effects.
- Keep UI access and slow work on the execution paths proven for the exact target context.
- Treat values, Java types, quality, timestamps, and dataset schemas as separate contracts.
- Bound waits, loops, result sizes, messages, logging, and retries.
- Redact credentials, tokens, cookies, identity material, and customer data.
- Avoid arbitrary evaluation, reflection targets, caller-selected methods, unrestricted component traversal, or general remote-control handlers.

## Validate

1. Compile the exact source with the installed target runtime.
2. Exercise the exact target context with normal, empty, boundary, malformed, bad-quality, exception, timeout, and restoration cases that apply.
3. Run in a fresh Vision Client when the behavior is client-scoped.
4. Verify the intended state or side effect independently.
5. Inspect diagnostics from the process where the code executed.
6. Restore temporary state and prove restoration.
7. Hand the implementation, source hash, contract, and validation requirements to `ignition-vision-83` for guarded lifecycle work.

Do not promote a reusable pattern until the relevant 8.3.8 test passes. Keep unsupported or partially validated behavior out of customer-facing examples.

The diagnostic step is mandatory for every execution, including executions that return the expected value or render the expected screen. Preserve the complete correlated Client, launcher/controller, Designer when explicitly in scope, and Gateway log windows. Inspect and disposition every new WARN, ERROR, exception, traceback, modal dialog, rejected write, and resource fault. If a required log plane is missing, incomplete, uncorrelated, or contains an unexplained related signal, do not call the script correct. Never assume a successful dispatch, return value, screenshot, or tag write means the Jython ran cleanly.

## Validated Java Class-Name Interop

In installed Jython 2.7.4 on the tested 8.3.8 build,
`component.getClass().getName()` raised `TypeError: getName(): expected 1 args;
got 0`. When an exact class name is genuinely required, use the validated
bound form:

```python
from java.lang import Class

class_name = Class.getName(component.getClass())
```

Keep the target component fixed or otherwise strictly bounded. Do not turn
this interop rule into caller-selected reflection, arbitrary traversal, or a
general remote inspection surface.

## Diagnose A Silent Client Handler

When a fixed Client message handler is selected and dispatch is reported but no result arrives, do not treat another sleep or another application request as evidence. Use a temporary diagnostic copy of the handler and advance a server-owned checkpoint ladder one payload-independent operation at a time:

1. Write an exact bounded marker as the first executable instruction.
2. On a new run, retain that marker and add only the next import or fixed runtime call.
3. Write a second exact marker immediately after that operation.
4. Stop before component lookup, payload parsing, tag-dependent values, application side effects, or the normal success path.
5. Require a fixed marker schema and allowlisted stage value, preserve the raw response and relevant process diagnostics, then remove the diagnostic resource and result transport.

A first-instruction marker distinguishes registration, handler-name resolution, dispatch delivery, and handler entry from later body failures. A marker after an import or fixed call proves only that the preceding operation completed. It does not validate the remaining handler, component access, bound values, or business result. Keep checkpoint inputs and destinations fixed; never accept caller code, tag paths, handler names, exception text, reflection targets, or arbitrary payload fields. Use a fresh Client for each credited runtime claim and make no automatic retry after an ambiguous mutation.

## Validated Client Runtime Baseline

A fixed fresh Vision Client on the tested 8.3.8 build reported Java `17.0.19`, implementation `Jython`, Jython `[2, 7, 4]`, Python version text beginning with `2.7.4`, and scope flags `12`. The observation used a fixed Client message handler, exact request identity, a bounded primitive JSON envelope, verified Client delivery, Good tag-write quality, and independently verified temporary-tag cleanup.

Treat these as Client-process facts only. Do not infer the Designer or Gateway runtime, arbitrary imports, callback variables, thread safety, or behavior on another build. Compile and execute in the exact target context whenever those details affect the script.

## Validated Client And Gateway Language Boundary

The same server-owned 13-case syntax corpus passed in four fixed contexts: a non-Designer Client message handler, a scope-`C` Project Library module called through a fixed Client forwarder, a native `PMIButton.actionPerformed` component event, and a scope-`G` Shared Gateway message handler. Eight Python 2.7 forms compiled, while f-strings, variable annotations, assignment expressions, `async def`, and keyword-only arguments each raised `SyntaxError`. Every context executed bounded unicode, long-integer, list-comprehension, context-manager, exception, generator, and `java.lang.String` observations. The Client contexts reported scope flags `12`; the Gateway handler instead proved `handlerScope == "G"` and that `system.util.getSystemFlags` was unavailable.

Load [references/validated-client-language-boundary.md](references/validated-client-language-boundary.md) before generating or reviewing syntax-sensitive Vision code. In 8.3.8 Client contexts, store a Project Library module with resource scope `C`, explicitly import its top-level module name where the callback does not inject it, and call the module directly. In native component-event scripts, treat the script as function-wrapped: nested class methods must not depend on enclosing action-script locals; keep their state on the instance or pass it explicitly. In a Gateway Shared handler, do not call Client/Designer-only `system.util.getSystemFlags`; use a context-specific fixed observation contract. Do not assume an 8.1-style `project.<module>` global exists. Treat the matrix as a compatibility guard, not proof that arbitrary scripts, imports, files, side effects, Designer scripts, or general Gateway scripts work.

## Validated Event Pattern

The tested 8.3.8 pattern is one `PMIButton.actionPerformed` native `ActionAdapter` in script mode. Its exact handler mutates only one sibling label's primitive Int4 dynamic property and text, then emits one bounded client log message. A separate fixed Client Event Script message handler runs on the EDT, validates an exact payload shape and contract, suppresses one repeated request ID through client globals, resolves one fixed open window and button, and calls `doClick()` so the native action event fires.

Load [references/validated-button-event-and-client-bridge.md](references/validated-button-event-and-client-bridge.md) for the exact source, threading, input, and evidence boundary. Do not generalize it to arbitrary component methods, windows, payloads, concurrent callers, or remote-control handlers.

## Validated Navigation Background-Close Pattern

One fixed native Client component event in the retained four-Window navigation fixture imports `java.lang.Thread`, captures `Thread.sleep` before opening a target Window, performs bounded background work through `system.util.invokeAsynchronous`, and schedules the fixed Target A close through `system.util.invokeLater` on the EDT. The credited final observation contained only the Host Window, exact visible scheduled status, `AWT-EventQueue-0`, and one Good/192 result write. `system.util.sleep` was not available in this installed Client event context and left Target A open before callbacks ran. Load [references/validated-navigation-background-close.md](references/validated-navigation-background-close.md) before generating or reviewing this pattern. Do not generalize it to arbitrary navigation paths, timing, cancellation, concurrency, Designer scripts, or other runtime scopes.

## Validated EDT Snapshot Pattern

One fixed 8.3.8 client handler also reads a bounded component snapshot on
the EDT. It resolves one exact open window, inventories five direct
children, reads fixed classes/bounds/text and one primitive Int4 dynamic
property, verifies one missing lookup, and sends only a flat bounded
`snapshotJson` string to one fixed Gateway handler.

Load [references/validated-edt-component-snapshot-handler.md](references/validated-edt-component-snapshot-handler.md) before implementing or reviewing this pattern. Do not generalize it to recursive traversal, arbitrary properties, caller-selected components, reflection, concurrent requests, or a general remote-inspection bridge.
