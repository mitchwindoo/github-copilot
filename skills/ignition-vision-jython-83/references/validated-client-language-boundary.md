# Validated Vision Language Boundary

Use this reference only for exact Ignition 8.3.8 Vision project contexts using Jython 2.7.4. The evidence comes from four fixed contexts: one non-Designer Client message handler containing the corpus, one scope-`C` Project Library module called through a corpus-free Client forwarder, one native `PMIButton.actionPerformed` component event, and one scope-`G` Shared Gateway message handler. Each used exact request identity, a bounded String-tag result, Good configure/write/delete qualities, and verified cleanup. The Client runtime baseline independently reported Java 17.0.19.

## Compile Matrix

The fixed corpus compiled these eight forms in all four contexts:

- Python 2 `print 'text'` statement;
- comma exception syntax, `except ValueError, error`;
- Unicode and long literals, including `u'caf\u00e9'` and `2147483648L`;
- list comprehension;
- `with` statement;
- `from java.lang import String`;
- generator expression;
- a function containing `yield`.

It rejected each of these five forms with `SyntaxError`:

- f-string;
- variable annotation;
- assignment expression (`:=`);
- `async def`;
- keyword-only argument syntax.

Use Python 2.7 syntax in Client scripts. Do not generate Python 3-only syntax and rely on a later runtime branch to hide it; the resource must parse before that branch can run.

This matrix proves compilation of the exact snippets only. In particular, the `with open(...)` case was compiled but not executed, so it does not validate Client filesystem access. A compiled Java import does not validate arbitrary packages or classes.

## Executed Runtime Values

The same fixed corpus executed and returned:

- Unicode value `café` with Python type name `unicode`;
- long value `2147483648` with Python type name `long`;
- list comprehension result `[1, 4, 9]`;
- context-manager events `["enter", "body", "exit"]`;
- raised `ValueError` with text `fixed-error`;
- generator result `[0, 1, 4]`;
- imported class name `java.lang.String`;
- Client scope flags `12` in the three Client contexts.

These are exact bounded observations, not a general standard-library, Java-interoperability, or performance guarantee.

## Generation Rules

When producing Client code:

1. Use Python 2.7 grammar and explicit Unicode handling.
2. Prefer `except Exception, error` only where the exact target requires Python 2 syntax; keep the caught type narrow when possible.
3. Use `unicode(...)` deliberately at Java, JSON, tag, logging, and byte boundaries.
4. Treat Java values returned through Ignition JSON helpers as potentially Java-backed scalar wrappers. Normalize a fixed Boolean with a bounded Boolean helper and a fixed integer with `int(...)` before identity-sensitive validation.
5. Keep imports explicit and version-specific. A successful `java.lang.String` import does not authorize reflection or caller-selected imports.
6. Compile the exact final source with installed Jython 2.7.4, then exercise it in the exact callback or handler context.

## Project Library in a Vision Client

The credited Project Library fixture stored `VisionLanguageP06T01` under `ignition/script-python` with resource scope `C`. Its fixed Vision message handler contained no corpus, compile call, or runtime-value construction. It explicitly executed:

```python
import VisionLanguageP06T01
observation = VisionLanguageP06T01.observe(request_id)
```

That module produced the same exact compile matrix and runtime values as the handler-local baseline. The direct top-level module import matters: a prior bounded diagnostic proved that this message-handler context did not inject a `project` global and returned `NameError` for `project.VisionLanguageP06T01`.

For 8.3.8 Vision Client project-library calls:

1. Use resource scope `C` for Client-only modules.
2. Use the top-level module name documented by the 8.3 Project Library model.
3. Explicitly import the fixed module when the callback does not supply it.
4. Do not copy an 8.1-style `project.<module>` assumption without an exact target-context test.
5. Keep the forwarding callback small; validate payloads before import/call and preserve bounded diagnostics.

## Native Component Events

The credited component-event fixture stored the corpus in one native script-mode `ActionAdapter` for `PMIButton.actionPerformed`. A fixed scope-`C`, EDT Client message handler validated one exact payload, resolved one exact open window and button, and called `doClick()`. The handler contained no corpus, compile call, runtime-value construction, or result write; the component event produced the full observation.

Ignition executes an action script through a function-like wrapper. That affects Python 2 name resolution. A nested class method in the first fixture tried to access an enclosing action-script local named `events` and produced `NameError`. The corrected context manager owned its list on the instance:

```python
class FixedContext(object):
    def __init__(self):
        self.events = []

    def __enter__(self):
        self.events.append("enter")
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.events.append("exit")
        return False

fixed_context = FixedContext()
with fixed_context:
    fixed_context.events.append("body")
```

For native Vision component-event scripts:

1. Validate the exact callback variable and component identity.
2. Assume the action script is function-wrapped for local-name resolution.
3. Do not make nested class methods depend on enclosing action-script locals.
4. Put mutable callback state on the instance or pass it explicitly.
5. Exercise the final serialized event in a fresh Client; a top-level Jython `exec` test does not reproduce wrapper scoping.
6. Keep cross-thread triggers on an exact tested path; this fixture used a native scope-`C` EDT handler and one fixed `doClick()`.

## Gateway Shared Message Handler

The credited Gateway fixture stored one fixed Shared message handler with resource scope `G`. After project import and semantic readback, the live test allowed a fixed five-second lifecycle-settle interval before one server-owned dispatch. The handler compiled and executed the same 13-case corpus and returned the same bounded runtime values.

Gateway scope required a different observation contract. `system.util.getSystemFlags()` is not available in this 8.3.8 Gateway handler context, so the validated result used:

```python
scope_evidence = {
    "handlerScope": "G",
    "systemFlagsAvailable": False,
}
```

Values crossing Ignition JSON and Java boundaries were normalized before exact validation: fixed text values through `unicode(...)` and the Java Boolean through a bounded Boolean conversion followed by `bool(...)`. This avoids Python identity checks against Java-backed scalar wrappers.

For a Gateway Shared handler:

1. Store the handler with resource scope `G` and `threadType` `Shared`.
2. Validate one fixed command, contract, and request identity before work.
3. Do not call Client/Designer-only `system.util.getSystemFlags`.
4. Keep the corpus and any result tag server-owned; reject caller-supplied code, source, project, handler, payload, tag, timing, scope, or expected result.
5. After import, verify semantic resource readback and allow bounded lifecycle readiness before dispatch.
6. Normalize fixed Java-backed scalar wrappers before exact comparison.
7. Treat send status as dispatch evidence only; require the independent result, Good tag qualities, diagnostics, cleanup, and rollback.

## Mandatory Per-Execution Diagnostics

For every fixed Jython execution, capture the complete correlated diagnostics from the process where the code ran and from the Gateway for the same action window. Inventory every WARN, ERROR, exception, traceback, modal error dialog, rejected write, and resource fault before applying focused filters. Disposition every related signal with evidence. Expected output does not override a log fault. Missing, incomplete, or uncorrelated logs are an observability gap and prevent a clean or correct claim. After changing code, use a fresh bounded execution and prove the previous error signature is absent; never infer correction from compilation or source inspection alone.

## Evidence Boundary

Validated:

- fixed non-Designer Client handler, fixed scope-`C` Project Library module/forwarder, fixed native `PMIButton.actionPerformed` event, and fixed scope-`G` Shared Gateway message handler;
- exact 13-case compile matrix;
- exact runtime values above;
- one fixed message delivery and result-tag lifecycle per tested context;
- negative rejection of caller-supplied code, corpus, source, project, handler, tag path, timing, and scope.

Not validated:

- Designer script context or Gateway contexts other than the fixed scope-`G` Shared handler;
- arbitrary user code or general Python compatibility;
- arbitrary imports, Java classes, files, network, database, or reflection;
- component-event callback variables beyond the fixed `event`, UI threading beyond the fixed EDT trigger, concurrency, restart persistence, or performance;
- other Ignition, Java, or Jython builds.

Re-run a bounded target-context test when any of those dimensions matter.
