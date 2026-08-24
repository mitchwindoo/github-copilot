---
name: ignition-vision-jython
description: Write, review, and troubleshoot Jython 2.7 inside Ignition Vision 8.1, including component events, client handlers, Swing threading, datasets, Java types, and fixed bridges.
---

# Ignition Vision Jython

Skill version: `0.2.19`

Use this skill for code that executes inside Ignition Vision. Use the separately installed `ignition-vision` skill for runner API calls, Gateway/project discovery, resource imports and exports, client launch, screenshots, external diagnostics, and end-to-end lifecycle work.

Do not create a relative filesystem dependency between the two skills. When both are needed, exchange an explicit handler contract rather than duplicating implementation or operational instructions.

## Contents

- [Compatibility](#compatibility)
- [Establish scope first](#establish-scope-first)
- [Keep the client responsive](#keep-the-client-responsive)
- [Resolve components deliberately](#resolve-components-deliberately)
- [Treat values, types, and quality separately](#treat-values-types-and-quality-separately)
- [Author native Vision data safely](#author-native-vision-data-safely)
- [Build fixed client bridges](#build-fixed-client-bridges)
- [Logging and diagnostics](#logging-and-diagnostics)
- [Verification gate](#verification-gate)
- [Shipped helper](#shipped-helper)
- [References](#references)

## Compatibility

- Target Ignition family: Vision `8.1.x`.
- Runtime language: Inductive Automation Jython `2.7`.
- Confirm the exact Ignition and IA Jython versions before using private classes, serializers, bean properties, or overloaded Java methods.

Write Python 2.7-compatible code. Do not use f-strings, annotations, `async`/`await`, dataclasses, structural pattern matching, `pathlib`, or Python-3-only standard-library behavior. Treat Java `Boolean`, numeric wrappers, `Date`, `Throwable`, collections, Ignition datasets, `QualifiedValue`, and `QualityCode` as Java-backed values.

## Establish Scope First

Before writing code, identify:

1. The exact script location: component event, extension function, window event, Client Event Script, message handler, Project Library, Tag Event Script, or Gateway Event Script.
2. The runtime scope: Vision Client, Designer, or Gateway.
3. The variables supplied by that editor, such as `event`, `self`, `payload`, `initialChange`, or `missedEvents`.
4. Whether the code touches Swing components and therefore must run on the event-dispatch thread (EDT).
5. Every tag, database, alarm, navigation, project-update, file, or messaging side effect.

Do not move code between scopes merely because it compiles. A Gateway-scoped Tag Event Script cannot reach a Vision component. A Client Event Script runs once per client and can multiply side effects.

Designer Design Mode is not the runtime scope for component-event or PMITimer Jython. It may still show changing direct bindings while scripted derived values remain at serialized defaults. Validate runtime behavior in a fresh Vision Client through the external lifecycle owned by the `ignition-vision` skill. For client-only refresh code, inspect `system.util.getSystemFlags()` and skip the Designer flags deliberately; retain an explicitly labelled snapshot there and replace it on the first successful Client refresh. On refresh failure, preserve the last good visualization and expose a bounded stale/failure status instead of manufacturing zero data.

Load [runtime-scope-and-patterns.md](references/runtime-scope-and-patterns.md) for the scope matrix, component lookup, threading, tag, dataset, quality, and Java-type patterns.

## Keep The Client Responsive

- Keep component events and EDT work short and deterministic.
- Use `system.util.invokeAsynchronous` for slow I/O or computation.
- Return Swing mutations through `system.util.invokeLater`.
- In a fixed message handler, use `SwingUtilities.isEventDispatchThread()` and `invokeAndWait` only for one bounded UI snapshot or action.
- Never sleep, poll without a hard bound, run a long query, or process a large dataset on the EDT.
- Do not access Swing components from an arbitrary background thread.

## Resolve Components Deliberately

- From a component event, start with `event.source`.
- From an extension function, start with `self`.
- Use `system.gui.getParentWindow(event)` when an event is available.
- From client code, use `system.gui.getWindow(path)` only after proving the exact window is open.
- For automation, require one exact window, one component path beginning with `Root Container`, and the expected concrete class.

Component bounds are local to their immediate parent. A successful lookup does not prove Good binding quality, visible pixels, correct z-order, or interaction behavior.

In serialized component event scripts, avoid nested helpers that resolve editor-injected names such as `event` or `system` as globals. Ignition may execute the script with distinct global and local mappings. Pass the required source and system object explicitly, or keep a short handler straight-line when that is clearer. See the routed runtime reference for the fixed pattern.

## Treat Values, Types, And Quality Separately

- Check the count and `quality.isGood()` of every `system.tag.readBlocking` result before using `.value`.
- Check every `QualityCode` returned by `system.tag.writeBlocking`.
- Prefer fully qualified tag paths. Use an unqualified path only after the active project default provider is known and available.
- For a finite fixed read set, spell out each fully qualified tag path as a literal in the handler. Avoid constructing those paths with `%` formatting, loops, or concatenated fragments when the external dependency preflight must enumerate and read them. If the path set is genuinely dynamic, define a bounded allowlist and tell `ignition-vision` that static dependency discovery cannot be claimed complete.
- Validate dataset column names, declared Java types, row/column counts, and bounds before indexing.
- For Template Repeater datasets, align the runtime cell type with the public template property, binding adapter value class, and destination JavaBean setter. Jython numeric inference can surface as a Java `Double` such as `0.0`; do not assume an integer-looking value will satisfy an integer-only setter.
- Keep Java `Date` values in a native schedule dataset. If a separate read-only table must show exact fixed-width times, build String display columns with an explicit format such as `HH:mm:ss`; do not coerce the schedule's Date columns to text.
- Treat Ignition datasets as immutable; construct a new dataset and assign it.
- In a sorted Power Table, translate the selected visible row through the component's view-to-underlying-row mapping before reading the backing dataset; treat `-1` as no selection.
- Accept only Python `bool` or `java.lang.Boolean` when a strict boolean is required. Do not call `bool(value)` on request text.
- Catch `java.lang.Throwable` as well as Python `Exception` when a Java failure must be converted to a bounded diagnostic result.
- Validate exact type, length, allowed characters, range, identity, and expiry before any side effect.

## Author Native Vision Data Safely

- Build expression bindings with the target expression parser and fully qualified `TagListener` paths; do not serialize expression text without a parsed expression.
- Match every expression branch and `setValueClass` to the real source and target types.
- Prefer an end-to-end type-stable presentation field when coercion is unnecessary. For example, publish `String('%d / 100' % score)` to a label instead of binding a possibly floating numeric value to `JProgressBar.value`.
- Use executable Jython bean calls for primitive setters; do not invent primitive class signatures in hand-authored serialized XML.
- Use target-version serializer/deserializer defaults and deserialize the final bytes again.
- Preserve preferred bounds, layout constraints, nested local coordinates, module scope, and declared resource files.
- Do not byte-patch opaque native Vision payloads.

Load [native-vision-serialization-and-transcode.md](references/native-vision-serialization-and-transcode.md) before working with native serialized windows/templates, parsed expression adapters, or binary transcode evidence.

## Build Fixed Client Bridges

When the runner API needs an in-client observation or action, implement a fixed message handler. The handler must:

- bind exact project, client, handler, request kind/schema, resource identity, component path, mailbox, and expiry;
- silently ignore messages not addressed to it;
- allowlist every component, property, method, and operation;
- perform at most one bounded UI operation or snapshot on the EDT;
- return a small typed and correlated response;
- verify mailbox write quality and report bounded failures;
- report actual side-effect counts;
- expose no arbitrary command, expression, script, reflection target, method, property, component, tag path, or tag value.

When generating a handler from templates or substitutions, assert the exact final Java import symbols before packaging. Avoid chained broad replacements that can manufacture a plausible but nonexistent class name. Python/Jython syntax compilation alone does not prove that the Vision client classloader can resolve an imported class; load the final handler in the matching client runtime before promotion.

Snapshot temporary configuration before changing it, restore in `finally`, re-read the restored state, and withhold success unless restoration is verified. A delivery receipt proves transport only; the outer workflow must require the correlated response and independently verify state.

Load [fixed-client-bridge.md](references/fixed-client-bridge.md) before designing or reviewing a bridge. Hand the resulting fixed handler contract to `ignition-vision` for guarded installation, fresh-client launch, API dispatch, mailbox lifecycle, screenshots, logs, and external validation.

## Logging And Diagnostics

Use `system.util.getLogger` with a stable hierarchical name. Log bounded identifiers and summaries, not unrestricted payloads or dataset rows. Redact passwords, tokens, authorization values, cookies, identity tokens, and secrets.

Vision logs belong to the client JVM. Gateway logs cannot substitute for client-local logs. Ask `ignition-vision` to collect focused client logs through an approved fixed bridge when programmatic evidence is required.

## Verification Gate

Before returning reusable Jython:

1. Compile every snippet with the target IA Jython runtime.
2. Assert exact generated imports and load them through the target scope's real classloader; do not treat syntax-only compilation as class-availability proof.
3. Exercise normal, empty, boundary, malformed, Java-type, bad-quality, exception, timeout, and restoration cases where applicable.
4. Run the code in the exact target scope in a fresh Vision client.
5. Verify component state, tag quality, side effects, and focused logs independently.
6. For every script-generated label, exercise the longest reachable formatted value or state combination; do not validate text fit only with representative data.
7. For visual behavior, hand off to `ignition-vision` for a bounded native screenshot and text-fit review.
8. Restore temporary handlers, mailboxes, component settings, and test data.

Large generated modules may exceed Jython/JVM method limits. Keep public entry points small, split ordinary code into modules, and compile the outer source plus every generated or lazy-loaded group with the installed target runtime.

## Shipped Helper

Use `scripts/validate-markdown-jython.py FILE.md [FILE.md ...]` to extract `jython` fenced blocks and compile them without executing Ignition calls. The script is Python-2.7-compatible, uses no Ignition imports, writes no files, and returns nonzero when no Jython blocks exist or any block fails compilation.

## References

- [runtime-scope-and-patterns.md](references/runtime-scope-and-patterns.md): runtime scope, components, EDT patterns, tags, datasets, Java types, and logging.
- [fixed-client-bridge.md](references/fixed-client-bridge.md): fixed message-handler contract, mailbox response, restoration, and rejection rules.
- [native-vision-serialization-and-transcode.md](references/native-vision-serialization-and-transcode.md): native serialization, layout, expression adapters, binary transcode limits, and validation.
