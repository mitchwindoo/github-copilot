---
name: ignition-8-3-expression-language
description: Write, review, migrate, troubleshoot, and validate Ignition 8.3 expressions across tags, bindings, UDTs, quality, datasets, Event Streams, Perspective, Vision, and SFC surfaces.
---

# Ignition 8.3 Expression Language

Skill version: `1.47.0`

Primary verified target: Ignition `8.3.8 (b2026071409)`. Confirm the actual Gateway version, build, modules, timezone, and expression surface before making version-specific claims.

## Scope

Use this skill to:

- Design, explain, review, or debug Ignition expression-language text.
- Work with Expression Tags, Vision or Perspective expression bindings and transforms, UDT expression members, tag-property expressions, and dynamic tag paths.
- Handle nulls, type conversion, quality, dates, strings, JSON, DataSets, and collections.
- Migrate expression behavior from 8.1 to 8.3, especially legacy quality handling.
- Reason about 8.3 expression surfaces in Perspective Named Query bindings, Event Streams, and SFCs.
- Build a bounded, reversible live validation when Gateway API access is available.

Do not treat an expression as Jython, SQL, or a general-purpose program. Expressions normally return one value. They do not provide imports, assignments, loops, transactions, or arbitrary side effects. Route project-library scripts, event scripts, database authoring, and project-resource construction to the matching Ignition skill while retaining responsibility for the expression fragments.

## Load References Deliberately

- Read `references/core-expression-recipes.md` for syntax, types, null/error guards, dates, strings, JSON, DataSets, collections, and dynamic paths.
- Read `references/quality-and-migration.md` for quality propagation and `forceQuality()` to `qualifiedValue()` migration.
- Read `references/surfaces-and-architecture.md` for 8.3 host surfaces, OpenAPI, file-backed configuration, resource collections, and deployment modes.
- Read `references/validation-workflow.md` before any live Gateway validation or mutation.

## Start With the Surface

Identify the exact host before proposing an expression:

1. Expression Tag or UDT expression member.
2. Perspective Expression binding or Expression transform.
3. Perspective Tag binding in Expression path mode.
4. Perspective Named Query binding in Expression path mode.
5. Vision Expression binding.
6. Event Stream expression field.
7. SFC transition or Parallel cancel condition.
8. Another module-specific expression field.

Then obtain the concrete provider, tag/property path, configured output type, expected value and quality, timezone/locale, and update trigger. Do not invent provider names, tag paths, component paths, project names, Named Queries, database connections, or event fields.

Surface differences matter:

- An Expression Tag expression returns a value that Ignition coerces to the configured tag data type.
- A Perspective Tag binding in Expression mode returns a tag path string, not the tag value.
- A Perspective Named Query binding path expression returns a Named Query path; parameters remain separate binding configuration.
- Event Stream handler expressions can access the event object through documented event data and metadata references.
- SFC conditions must be boolean in the host context even though the expression language itself can return other types.

## Apply Core Syntax

Use Ignition expression syntax, not Python or JavaScript syntax:

- Equality: `=`
- Inequality: `!=`
- Boolean operators: `&&`, `||`, `!`
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `^`
- Bitwise operators: `~`, `&`, `|`, `xor`, `<<`, `>>`
- Null literals: `null` or `None`
- Bound value: `{[.]PV}` or `{view.params.asset}`
- Function call: `if(condition, trueValue, falseValue)`
- Line comment: `// comment`

Parenthesize mixed or safety-sensitive expressions. Prefer readable native functions such as `if()`, `case()`, `switch()`, `coalesce()`, `try()`, `toInt()`, `toFloat()`, `dateFormat()`, `lookup()`, and `tag()`.

Examples:

```text
5 + 3 * 2
(5 + 3) * 2
5 = 5 && 2 != 3
if({[.]Running}, "Running", "Stopped")
case({[.]State}, 0, "Off", 1, "Running", 2, "Fault", "Unknown")
coalesce({[.]OperatorName}, "N/A")
```

## Design Expression Tags Safely

- Use `{[.]Sibling}` for a sibling tag in the same folder.
- Use `{[<provider>]Folder/Tag}` only when the provider and path are known.
- Use `[~]` when a path should resolve from the current provider root.
- Select `Float8` when fractional precision matters, `String` for formatted text, `Boolean` for predicates, and integer types only when coercion behavior is intentional.
- Read value, runtime type, quality code/level/subcode/diagnostic, and timestamp together during validation.
- Treat a null value with Error quality differently from a Good null.

Guard unsafe arithmetic before it executes:

```text
if({[.]Den} = 0, -1.0, {[.]Num} / {[.]Den})
```

Use `try()` for evaluation exceptions:

```text
try(toInt("boom"), -1)
try({[.]Table}[99, "Status"], "NO_ROW")
```

Do not assume `try()` fixes non-Good quality or every final tag-type coercion failure. Use an explicit quality guard when quality is the decision:

```text
if(isGood({[.]PV}), {[.]PV}, -1.0)
```

## Handle Null, Error, and Quality Separately

Use the mechanism that matches the failure:

- `coalesce(value, fallback)` for null-like values.
- `try(expression, fallback)` for expression evaluation errors it can catch.
- Conversion fallbacks such as `toFloat(value, fallback)` for invalid or missing numeric input.
- `isGood()`, `isUncertain()`, `isBad()`, `isError()`, or `isBadOrError()` for quality.
- `qualityOf()` for a readable quality result.
- `isNull()` for null detection.

Bad quality can propagate through successful arithmetic. `try({[.]BadPV} + 1.0, -1.0)` can still return the calculated value with Bad quality because no evaluation exception occurred. `coalesce()` does not turn a non-null Bad value into a Good fallback.

Prefer:

```text
if(isGood({[.]BadPV}), {[.]BadPV}, -1.0)
```

## Use Modern Quality Construction

Prefer `qualifiedValue()` for new 8.3 work:

```text
qualifiedValue(123, "Good")
qualifiedValue(123, "Uncertain")
qualifiedValue(123, "Bad")
qualifiedValue(123, "Error")
qualifiedValue(123, "Bad", 515, "Disabled by test")
```

Treat `forceQuality()` as a legacy-quality compatibility function. It uses legacy quality integers. Never migrate by copying the integer into `qualifiedValue()`:

```text
forceQuality(value, 0)       // legacy Bad
qualifiedValue(value, 0)     // modern Good level
```

On the verified 8.3.8 Expression Tag target, a fixed side-by-side comparison
preserved the same integer value `123` while `forceQuality(123, 0)` returned
Bad with full code `-2147483136` and `qualifiedValue(123, 0)` returned
Good/`192`. This proves the semantic reversal for numeric `0` on that target;
it does not map other legacy integers.

On the same target, adding integer `1` to a fixed Bad_Disabled qualified value
changed `41` to `42` while preserving full code `-2147483133` and its
diagnostic text. The matching Good control also changed `41` to `42` and
remained Good/`192`. Scope this to the tested one-addition Expression Tag
case; validate other operators, qualities, or hosts separately.

On a fixed Perspective view on the same 8.3.8 target, a Label with a direct
tag binding to a four-argument Bad_Disabled qualified value and
`overlayOptOut=false` displayed the numeric value under the red Perspective
Error overlay. Opening the overlay showed the exact `Bad_Disabled` subcode,
bound property path, and diagnostic. An unbound Good control had no overlay.
This proves only that direct-binding case; test opt-out behavior, other
qualities, indirect bindings, alarms, Vision, and other components separately.

Decode the legacy meaning, then select the modern level, subcode, and diagnostic. Read `references/quality-and-migration.md` before changing production quality expressions.

## Build Dynamic Paths Intentionally

Use direct brace references when the dependency is static:

```text
{[.]Speed}
{[<provider>]Area/Line1/Speed}
```

Use `tag()` only when the path itself is dynamic:

```text
toFloat(tag("[~]Area/" + {[.]SelectedDevice} + "/Speed"), 0.0)
```

A conversion fallback can hide a missing dynamic tag by returning a Good fallback. When absence matters, expose the resolved path, validate existence/readback separately, or avoid masking the missing target.

For UDTs:

- Use `{ParamName}` for parameters.
- Use `{[.]MemberName}` for sibling members.
- Use `tag({FullPathParam})` when a parameter holds a full tag path.
- Do not quote the parameter reference as `tag("{FullPathParam}")`.

## Respect Date, Locale, and Type Context

- Treat pattern letters as case-sensitive: `yyyy` is calendar year, while `YYYY` is week-year; `dd` is day of month, while `DD` is day of year.
- Label date results with the Gateway, client, or Perspective session timezone used.
- Test DST gaps and overlaps when date logic affects alarms, schedules, reports, or shifts.
- Confirm locale-sensitive formatting and translation in the real client/session context.
- Use a BCP-47 locale tag such as `"zh-CN"` when supplying the locale to `translate()`. On the verified 8.3.8 Gateway Expression Tag host, `translate("<term>", "zh-CN")` returned the matching global Simplified Chinese translation with Good quality; no underscore workaround was required.
- Treat an internal `zh_CN` configuration/readback key as Java locale serialization, not as a reason to rewrite a working BCP-47 expression.
- Keep explicit-locale Gateway evidence separate from current-locale behavior in Perspective or Vision.
- On the verified 8.3.8 Perspective Expression binding surface, `translate("Close")` reevaluated without a reload in one active Designer session as its locale changed `en-US` -> `de-DE` -> `fr-FR` -> `en-US`. The exact values were `Close` -> `Schliessen` -> `Fermer` -> `Close`, each with Good quality code `192`, a fresh observation, and no stale prior-language value.
- For a locale-reactive binding, observe locale, translated value, full quality, timestamp or sequence, and session/page identity together. Test browser sessions, Vision clients, unknown-locale fallback, migration, and restart separately.
- Use `typeOf()` and explicit casts when a DataSet, JSON, Document, array, or property value has an uncertain runtime type.

## Apply 8.3 Surface Guidance

Perspective Named Query path expressions:

- Available in Perspective Query Bindings beginning with 8.3.7.
- Choose Direct mode when automatic parameter discovery is more valuable.
- Choose Expression path mode when the query path must vary.
- Define and validate parameters explicitly in Expression mode.
- Test valid, missing, malformed, unauthorized, and type-incompatible query selections.
- Observe the resolved query path, value, full quality, and timestamp together. Do not infer the selected path from the last displayed value.

On the verified 8.3.8 Perspective Query Binding surface:

- One API-authored Direct-mode binding used fixed `QueryA` with a configured integer Value parameter `id = "101"` and published scalar `"1101"` at Good/192, sequence `1`, with positive binding/observation timestamps and a nonempty fixed session/page identity. Polling and value cache were disabled. This verifies one Direct-mode runtime configuration; it does not verify Designer editor acceptance, automatic parameter discovery, parameter persistence after editor changes, other queries or parameter shapes, multiple sessions, Cache & Share, restart, save/reopen, load, migration, permissions, or performance.
- A constant path expression whose exact text was `"LLM Tests/Expression Validation/NQP Golden 03b932b7/QueryA"` resolved that fixed query with one manually defined `id = "102"` Value parameter and published `"1102"` at Good/192. The observation came from one fresh fixed session/page with polling and value cache disabled. This verifies one API-authored quoted path expression at runtime; Designer editor acceptance, other constant expressions, parameter types or counts, sessions, Cache & Share, restart, and load remain separate tests.
- One Query Binding path expression referenced a String view custom property rather than the backing tag directly. As that property changed `A` -> `B` -> `A`, the same session/page published `QueryA/"1101"` -> `QueryB/"2101"` -> `QueryA/"1101"`, all Good/192 with sequences `1` -> `2` -> `3` and strictly newer binding and observation timestamps. This verifies one fixed custom-property dependency with one manual integer `id`, polling/cache disabled, and no session restart; view parameters, bidirectional bindings, other property types or transforms, Cache & Share, multiple sessions, restart, save/reopen, load, migration, permissions, and Designer editor behavior remain separate tests.
- A tag-driven path expression switched between two Named Queries without restarting the session. Both queries reused the binding's explicit `id` parameter; the selected path, scalar result, sequence, and timestamp all updated.
- With the path fixed at `QueryA`, one manually defined `id` parameter used the expression `tag("[default]_expression_skill_tests/perspective_nqp_03b932b7/ParameterId")`. Changing that fixed Int4 source `101` -> `202` -> `101` published `"1101"` -> `"1202"` -> `"1101"`, all Good/192 with observation sequences `2` -> `3` -> `4`, strictly newer source/binding/observation timestamps, and the same session/page. This verifies one tag-driven parameter expression with polling and value cache disabled; other parameter names, expressions, source types, multiple dynamic parameters, sessions, Cache & Share, restart, and load remain separate tests.
- A binding with explicit `id`, `site`, and `equipment` parameter rows switched from `QueryA` to a query with the alternate `site`/`equipment` schema and back. It published `"1101"` -> `"alpha:pump-7"` -> `"1101"`, all Good/192 with fresh path, timestamp, and sequence observations. Because parameter value fields are expressions, string literal sources such as `"alpha"` and `"pump-7"` must include their expression quotes.
- A fixed server-owned rapid cycle wrote selectors `A` -> `B` -> `DIFF` ten times without a caller-controlled sequence or delay. All 30 writes were Good; the latest `DIFF` selector published a fresh `QueryDifferentParams` path and `"alpha:pump-7"` at Good/192, then a normal `A` selection recovered a still-newer Good/192 `"1101"`. This proves only that fixed sequence in one mounted test view, not arbitrary timing, simultaneous clients, polling, Cache & Share, restart, or mixed result schemas.
- One fixed polling binding held selector `POLL`, the resolved Named Query path, and all inputs constant while using polling rate expression string `"1"`. After its baseline, it published six unique database-clock results in 6,522 ms, all Good/192. Consecutive database intervals were 1,000, 1,001, 1,002, 1,000, and 1,003 ms; observed intervals were 1,000, 1,001, 1,002, 1,000, and 1,002 ms. This proves repeated one-second execution only for the fixed binding in one mounted test view, not an exact scheduler guarantee, other rates or rate expressions, pause/resume behavior, simultaneous sessions, Cache & Share, restart, or load behavior.
- On the installed 8.3.8 Perspective runtime, direct `PollingConfig.fromJson` inspection normalized numeric JSON rate `1` to default rate expression `30`, while string JSON rate `"1"` remained expression `1`. The numeric fixture consequently evaluated once but did not poll again during 6.5 seconds. Prefer Designer- or supported API-authored binding configuration. If generating resource JSON, preserve a polling rate expression as a string and verify installed-runtime readback and live cadence instead of relying on the permissive number-or-string schema alone.
- Selecting a nonexistent Named Query path published a fresh null with non-Good `Error_Exception` quality whose diagnostic named the missing path. It did not retain the prior Good scalar, and returning to the valid path produced a still-newer Good result. Validate permission failures, deletion races, and other missing-path shapes separately.
- An empty-string path and an expression-null path produced distinct fresh failures. Empty string published null/`NoneType` with `Error_Exception("Named query \"\" not found.")`, full signed code `-1073741048`; expression null published null/`NoneType` with `Error_Configuration`, full signed code `-1073741055`. Each replaced the prior Good scalar, and each was followed by a newer Good `1101` recovery. This API-imported fixture did not test whether the Designer editor accepts either expression.
- One API-authored path expression with malformed text `if(` published a fresh null/`NoneType` with `Error_Configuration("RuntimeException: Syntax Error on Token: 'End of Expression' (Line 0 , Char 0)")`, full signed code `-1073741055`. It did not silently execute any fixed test query. This verifies saved-resource runtime behavior for that exact text only; Designer editor prevention/flagging and other malformed expressions remain untested.
- An integer path result of `123` was converted to path text `"123"`, then published null/`NoneType` with `Error_Exception("Named query \"123\" not found.")`, full signed code `-1073741048`. Returning to the valid string path produced a newer Good/192 `1101`. Return an actual valid Named Query path string; do not rely on numeric coercion to identify a query.
- Missing Value parameters did not necessarily fail. When an alternate query expected Value parameters that the binding did not define, the binding supplied nulls and published a fresh Good null on this target.
- Missing QueryString parameters failed with `Error_Exception` and named the missing parameter. QueryString parameters remain unsanitized and injection-sensitive; do not use them merely to force validation.
- Prefer Designer- or API-authored Named Query resources over hand-authored resource JSON. If inspecting 8.3 resource JSON, numeric `sqlType` is an Ignition `DataType` ordinal, not a `java.sql.Types` code: String is `7`, while `12` is `Int4Array`. Using `12` for a string QueryString parameter caused a String-to-Long-array coercion failure on the verified target.
- Treat path/parameter compatibility as an application invariant. Prefer prepared Value parameters, validate every selectable query, and explicitly reject an unexpected Good null when null is not a valid result.
- The successful alternate-parameter fixture deliberately kept all selected query results String-compatible. Treat mixed result schemas as unverified.

Event Streams:

- Treat handler expressions as expression-language fields with event-specific bound values.
- Use only fields documented for the configured source type.
- Confirm the providing module is installed and active.
- Validate compile status, test-mode output, handler behavior, and malformed/missing event fields.
- Treat a dynamic Tag Handler path as a write destination, not as a security boundary. Keep every possible result provider-qualified and below one explicit test or application root. Do not concatenate untrusted event input directly into a tag path.
- Do not generalize Event Stream event references to Expression Tags or component bindings.

On the verified 8.3.8 Tag Event to Tag Handler surface:

- `{event.data.value}` preserved changed `Int4` values `42` and `43` in static target readback.
- A server-owned `if()` expression choosing between two complete, provider-qualified paths selected the expected even/odd target, while an independent path-echo target recorded the same resolved path.
- A Tag Handler quality expression returning integer `192` produced `Good` target quality with full code `192`.
- A fixed-fixture adapter rejected traversal-like run IDs and caller-supplied target paths before writes; an in-root canary remained unchanged.
- Project deletion completed before the runtime Event Stream list cleared. Poll both project absence and Event Stream status/diagnostics until the stream is gone before deleting subscribed source tags.

These observations are limited to the tested Tag Event source, JSON-object encoder, Tag Handlers, and fixed payloads. Validate other source types, missing/null members, string or invalid quality values, timestamps, filters, transforms, batching, restart, migration, and Designer test controls separately.

SFC:

- In 8.3.8, Parallel cancel conditions support the full Ignition expression language and editor helpers.
- In 8.3.8, a fix applies the configured default provider to providerless relative `tag()` paths in SFC transition expressions.
- On the verified 8.3.8 callable-transition surface, project readback confirmed the configured default provider before a providerless `tag("Area/TransitionGate")` expression was started. A Good false Memory Tag kept the chart `Running`; a Good true write moved the same instance to `Stopped` on the first official state read, with no WARN-or-higher Gateway log.
- On that same callable-transition surface, `tag("[~]<test-root>/TildeTransitionGate")` resolved from the configured default provider root. Good false plus an explicit false rewrite kept the instance `Running`; Good true moved it to `Stopped` on the first official detail read.
- In the fixed `[.]` transition test, `tag("[.]DotSiblingGate")` did not resolve from the chart resource's folder. A chart-folder candidate left the instance `Running`; a mutually exclusive tag at the configured default provider root moved it to `Stopped`. Treat this as an 8.3.8 SFC Transition result, not the general host-tag rule or proof for other expression surfaces.
- On the same callable-transition surface, `tag({TargetPath})` accepted a chart-scope string supplied by `system.sfc.startChart()`. With `TargetPath` selecting a Good false, provider-qualified target A, setting non-target B true left the same instance `Running` through a 1.53-second observation and readback still showed A. Changing only that stored instance's chart-scope `TargetPath` to the already-true target B with `system.sfc.setVariable()` moved the exact instance to `Stopped` 15 ms after the request began. This proves retargeting and reevaluation for that fixed A-to-B Boolean case; validate other path forms, qualities, types, update sources, and rapid retarget sequences separately.
- A fifth callable Transition used `tag()` with one fixed, explicit-provider path that was deliberately absent. Direct reads before start, after start, after a 2.119-second observation, and after terminal handling all returned null/`NoneType` with non-Good `Bad_NotFound`; the exact chart instance stayed `Running` at its waiting action and emitted no missing-tag WARN-or-higher log. Canceling that stored instance through the official SFC endpoint produced `Canceled`, then retained detail cleared. This proves fail-closed waiting for that exact missing Boolean target on 8.3.8; do not infer Uncertain, stale-value, timeout, other disabled-provider shapes, or other host behavior.
- A seventh fixed callable Transition used a providerless `tag()` path while its project selected one disposable standard provider as the default. Good false started and held the exact instance `Running`. Disabling that provider made the gate read null with non-Good `Bad_NotFound("Tag provider '<provider>' not found")`, full code `-2147483129`, while the same instance remained `Running` for 1.655 seconds. Re-enabling the provider restored Good false and the same Running instance; Good true then produced `Stopped`. Immediate and post-runtime exports preserved the exact providerless expression. This covers one disable/re-enable cycle only, not remote providers, rename/deletion, restart, other quality states, or arbitrary expressions.
- Do not compare a Java full quality integer directly with a documented subcode. In that missing-tag test, `Bad_NotFound` had documented subcode `519`, while Gateway-scope Jython serialized the signed composite full code as `-2147483129` (`0x80000207` unsigned). Preserve the readable quality name and distinguish full code from subcode.
- On the verified 8.3.8 callable-Parallel surface, an explicit-provider `tag("[<provider>]<test-root>/Cancel")` condition kept two blocked branches `Running` while the Good Boolean tag was false. Rewriting false preserved the same instance; writing true produced `Stopped` on the first official detail read 17 ms after the request began.
- Fixed literal baselines distinguished Parallel-element cancellation from chart cancellation. With cancel condition `false`, two true branch transitions completed normally and the chart reached `Stopped` after 25 ms. With cancel condition `true`, two otherwise blocked branches were cancelled and the chart continued to its End step, reaching `Stopped` after 16 ms. Each instance emitted exactly one chart-level `onStop`, with no `onCancel`, `onAbort`, or duplicate terminal event.
- An explicit-provider arithmetic/comparison condition using two `tag()` calls stayed `Running` with input `4` and threshold `10`, then reached `Stopped` 20 ms after input changed to `6`: `(tag("<input>") * 2) > tag("<threshold>")`.
- A native `if(tag("<flag>"), true, false)` condition stayed `Running` with a Good false Boolean and reached `Stopped` 16 ms after true.
- A guarded `try(toInt(tag("<text>")) > 0, false)` condition stayed `Running` with the Good string `"not-a-number"` and reached `Stopped` 22 ms after `"1"`. This verifies the fallback in this fixed SFC host; it does not prove every conversion, quality, or final-coercion failure.
- A literal Good `null` cancel condition behaved as false on the verified host: both branches remained blocked and the chart stayed `Running` until exact-instance cancellation. In the 8.3.8 implementation, Good results are coerced to Boolean, while non-Good results are treated as false before coercion.
- A fixed `tag()` result whose value was true but quality was Bad did not cancel the Parallel block. Changing only that input's quality to Good while preserving true moved the chart to `Stopped` after 19 ms.
- In 20 fixed race trials, one server-owned batch changed a branch-release tag and the Parallel cancel tag to true. Every instance reached `Stopped` in 13–22 ms and emitted exactly one `onStop` event; no trial emitted `onCancel`, `onAbort`, or a duplicate terminal event. Treat this as a result for that synchronized two-tag fixture, not every possible branch/cancel interleaving.
- A callable chart can run multiple instances with private chart scopes. In one fixed two-instance test, `system.sfc.startChart()` supplied `CancelRequested=false` and distinct `InstanceSlot` values. The Parallel condition `{CancelRequested}` stayed false in both. `system.sfc.setVariable(<stored-A-id>, "CancelRequested", true)` stopped A after 21 ms while B retained the same ID, stayed `Running`, and kept `CancelRequested=false` through 37 status/readback samples until A disappeared. Setting the stored B instance true then stopped B after 14 ms. Each ID emitted exactly one slot-correlated `onStop`; neither emitted `onCancel` or `onAbort`.
- On the verified 8.3.8 Enclosing-step surface, a fixed parent started a blocked child and requested cancellation immediately after `system.sfc.startChart()` returned. The measured start-return-to-cancel-call interval was 0 ms; the call returned without an exception, and parent plus child cleared from the active set.
- A stopped SFC instance can remain visible briefly before the running count and detail list clear. Capture the terminal state, then poll detail/status to absence before deleting the project or subscribed tags.
- Prefer explicit provider intent in reusable logic and validate transition/cancel behavior in a disposable SFC. The verified Transition subset includes providerless, `[~]`, `[.]`, one chart-scope dynamic `tag()` retarget, one explicit-provider missing target, one disabled/re-enabled disposable standard provider used as the project default, and one project-resource migration case loaded by Ignition 8.1.53 before import into 8.3.8. In that migration case, export readback preserved the exact providerless `tag()` expression before and after runtime; Good false kept the same instance `Running` for 1.648 seconds and Good true moved it to `Stopped`. This is project-content portability evidence, not proof of full Gateway-upgrade transformations. The verified Parallel subset covers literal false/true lifecycle baselines, direct Boolean `tag()`, arithmetic/comparison, native `if()`, `try()` around `toInt()`, literal `null`, one fixed Bad-to-Good quality transition, one synchronized branch/cancel race, and one two-instance chart-scope variable test. Its cancel conditions do not cover providerless or `[~]`/`[.]` paths. Across the Transition and Parallel tests, arbitrary functions, Uncertain quality, remote providers, provider rename/deletion, more than two instances, arbitrary parameter/value types, arbitrary path-update sources, repeated or rapid retargeting, arbitrary race timing, faults, hot edits, persistence, restart, redundancy, other migrated project shapes, and full Gateway-upgrade transforms remain unverified.

Vision and Perspective:

- Keep property references scoped to the actual component/view/window.
- Validate Designer preview and runtime behavior separately when locale, security, session state, or indirect paths are involved.
- Do not transfer observed Expression Tag quality/timestamp behavior to UI bindings without a host-specific test.
- On one verified 8.3.8 Vision client, a same-Gateway project retarget preserved a direct tag binding, a tag expression, and a property expression. Project A returned `17`, `171`, and `1171`; project B returned `23`, `232`, and `1232`, then reevaluated to `29`, `292`, and `1292` after only B's source changed. Every source and binding read Good with full quality code `192`.
- Treat runtime identity and active-project readback as separate from a Vision client ID. The test kept one JVM across retarget and the target-project client ID stayed stable through its source update, but the client ID changed from project A to project B.
- A second fixed run gave projects A and B different default standard providers. The Vision Client `DefaultTagProvider` system tag changed from A's provider to B's provider at retarget. Direct bindings with the provider omitted or written as `[]`, matching `tag()` expressions, and a component property expression all followed the target project: A produced `17/17/174/1705/1879`, B produced `23/23/234/2305/2539`, and changing only B produced `29/29/294/2905/3199`, all Good/192.
- Do not treat `[~]` as a Vision project-default alias. In that same run, fixed `tag("[~]...")` bindings were non-Good `Error_ExpressionEval` with full code `-1073741054` in A, B, and updated B. Use an omitted/empty provider for the project default or name the provider explicitly; validate `[~]` independently on any other host.
- `hasRole("<role>")` in a Vision client expression follows the current authenticated user. Pair it with an independent current-user surface such as `tag("[System]Client/User/Username")`, and compare both against `system.vision.getUsername()` and `system.vision.getRoles()` after an identity change.
- In one fixed classic-authentication run, a single client changed alpha -> beta -> alpha with `system.vision.switchUser()`. The username expression and two disjoint `hasRole()` expressions reevaluated coherently in every phase, all at Good/192, with no stale prior-user value. Both switches returned true; the client ID and JVM stayed constant while the window instance changed after each switch.
- In one fixed restart run, the same Vision client JVM remained alive across an official Gateway restart. After reconnect, project B's source/binding values changed from `23/232/1232` to `29/292/1292`; omitted/empty-provider controls changed from `23/23/234/2305/2539` to `29/29/294/2905/3199`. Every required source and binding was Good/192.
- A reconnect can issue a new Vision client ID without replacing the client JVM. In that run, project B changed client ID while its JVM identity stayed constant; the post-restart ID matched the Gateway's active client record. Use JVM/process identity, active project, fresh telemetry, and the current Gateway client record together rather than demanding pre/post client-ID equality.
- Treat Vision teardown as a separately verified oracle. After the fixed retarget, default-provider, login/logout, and restart campaigns, one read-only audit found zero run-prefixed projects, providers, users, roles, clients, local client processes, shared test-tag children, or run-identity warnings. Inventory exact prefixes and the shared parent; do not infer cleanup from a successful delete response.
- Scope the verified Vision results to one Windows launcher client, one independent Gateway, classic authentication, two fixed local users and roles, two local standard providers, fixed numeric values, one project retarget, one target update, two successful user switches, and one Gateway restart/reconnect. Validate other Gateways, remote providers, failed or anonymous login, live role mutation, other security expressions, provider lifecycle changes, other binding/value/quality shapes, repeated retargets, switches, or restarts, restart of the security fixture, redundancy, migration, and Alarm Status Table null-priority behavior separately.

## Keep `runScript()` at the Boundary

Use `runScript()` only when native expressions cannot express the required pure calculation and a project-library function already provides the behavior:

```text
runScript("<projectScript.function>", 1000, arg1, arg2)
```

Before recommending it:

- Confirm the project and Gateway Scripting Project context.
- Confirm Jython compatibility; Ignition 8.3.8 uses Jython 2.7.4.
- Avoid writes, long I/O, sleeps, hidden state, and broad exception suppression.
- Define the polling/update behavior.
- Validate return type, exceptions, quality, latency, and log output.
- After saving or deploying a project-library change, treat the update as a
  lifecycle transition. Wait for the intended value at Good quality and
  inspect its timestamp and Gateway logs before declaring recovery.
- Use `try()` during that transition only when the fallback is explicitly
  safe. A Good fallback can mask a project-resolution or availability
  problem, so do not treat the fallback alone as proof of recovery.

On the verified 8.3.8 Expression Tag target, a fixed fixture observed:

- `runScript("len", 0, "abcd")` and legacy `runScript("len('abcd')", 0)` both returned `4` with Good quality.
- `runScript("None", 0)` returned a Good null.
- `runScript("1/0", 0)` returned null with `Error_ExpressionEval` and a deterministic diagnostic.
- `try(runScript("1/0", 0), -1)` returned the Good fallback `-1`.
- With no Gateway Scripting Project configured, `runScript("LLMRunScriptIdentity.runtimeIdentity", 0)` returned null with full code `-1073741054`, `Error_ExpressionEval`, and diagnostic `Error executing script for runScript() expression:LLMRunScriptIdentity.runtimeIdentity`. Wrapping that call in `try(..., "SCRIPT_FAIL")` returned the Good fallback `SCRIPT_FAIL`.
- Five fixed one-line scalar returns were Good/192: integer `42` into `Int4` arrived as `int`; long `2147483648` into `Int8` as `long`; float `2.5` into `Float8` as `float`; Unicode `alpha` into `String` as `unicode`; and boolean `true` into `Boolean` as `bool`.
- Five fixed structured returns were Good/192 with their shapes preserved: epoch-zero `java.util.Date` into `DateTime`; a two-column, two-row Ignition DataSet into `DataSet`; a Python list into a `Document` array; and both a Python dict and explicit Ignition Document into `Document` objects. On the tested Gateway read surface, the list reported type `array`, while the dict-backed values reported `PyDocumentObjectAdapter`.
- Two fixed Java standard-library method chains were Good/192: multiplying `BigDecimal("12.50")` by `BigDecimal("2")` into `Float8` returned `25.0` as `float`, and appending then reversing `StringBuilder("alpha")` into `String` returned `ateb-ahpla` as `unicode`.
- In one fixed Event-Driven Gateway Expression Tag, `runScript(..., 0)` internally read an absolute source path without an Ignition expression tag reference. After the source changed from `10` to `20`, the target stayed `10` with its exact original timestamp through 14 Good/192 observations spanning 3.629 seconds. Replacing only the target's expression with a server-owned equivalent caused it to reevaluate to `20` with a newer Good/192 timestamp. Treat zero as non-polling in this exact scenario, not as proof that the expression can never reevaluate.
- In one fixed Event-Driven Gateway Expression Tag with no Ignition expression tag reference, `runScript("system.date.now().getTime()", 250)` produced 23 distinct Good/192 updates across 40 reads over 5.490 seconds. The distinct update timestamps spanned 5.512 seconds, and the observed inter-update intervals were 250–251 milliseconds with a 251-millisecond median. Treat this as an observed fixed scenario, not an exact scheduler guarantee. Validate effective cadence on the target Tag Group and expression surface.
- In one fixed Event-Driven Gateway Expression Tag, a numeric bound input was embedded in a fixed `runScript(..., 2000)` script string whose result also exposed execution time. The first unchanged-input poll occurred 2,000 milliseconds after initial execution. Changing the input from `10` to `20` produced a separate Good/192 execution 116 milliseconds after that poll; the next poll occurred 1,884 milliseconds later, exactly 2,000 milliseconds after the preceding poll. In this run, the input trigger was inserted between polls without shifting the observed poll phase. Treat this as a measured interaction, not a scheduling guarantee. Prefer positional arguments, and never interpolate untrusted text into a script string.
- In one fixed Event-Driven blocking-latency campaign, 0-, 25-, and 100-millisecond sleeps were triggered in cohorts of one and four Expression Tags. The one-target internal elapsed times were 0, 25, and 101 milliseconds. The corresponding four-target per-expression times were 0 each, 25–28, and 100–103 milliseconds; their cohort script windows were 1, 54, and 202 milliseconds. This demonstrates visible per-expression and aggregate delay in the fixed fixture, not a scheduler, concurrency, throughput, or capacity guarantee. Keep `runScript()` work short and measure it with the intended Tag Group and representative load.
- With the intended Gateway Scripting Project configured, one fixed polling
  Gateway Expression Tag returned the intended project-library value at
  Good/192.
  After a supported project update changed only that function, the same tag
  reached the intended updated value and remained Good/192 for eight
  consecutive observations. No transient expression error was observed and
  the full Gateway was not restarted. Treat this as one lifecycle
  observation, not a timing or no-transient guarantee.
- In one supported Gateway-backup migration, an exact Ignition 8.1.53
  Gateway was backed up and restored into an exact Ignition 8.3.8 Gateway.
  Two project-library source files and all five Expression Tag texts were
  byte-for-byte unchanged after restore. Imported integer and string returns
  stayed Good, a deterministic exception stayed `Error_ExpressionEval`,
  `try()` returned its Good fallback, and a 500-millisecond polled function
  produced 11 distinct Good updates in 20 observations on both versions.
  Treat this as one fixed migration route, not a guarantee for other versions,
  scripts, return shapes, poll rates, Tag Groups, hosts, or deployment modes.

Scope these observations to the tested Expression Tag and fixed one-line scripts. The Java controls prove only those two standard-library constructors and method chains, not arbitrary Java class availability, overload resolution, third-party libraries, or object coercion. The missing-Gateway-Scripting-Project result proves only that fixed configuration state and function path; it does not distinguish every missing project, module, function, or permission cause. The poll-zero result covers one Event-Driven tag, one internal `readBlocking` path, one 3.629-second window, and one configuration-change trigger. The explicit-poll result covers only the fixed 250-millisecond expression. The input-plus-poll result covers one numeric reference, one fixed 2,000-millisecond legacy script-string expression, and one trigger between two observed polls. The blocking-latency result covers only fixed sleeps of 0, 25, and 100 milliseconds, cohort sizes of one and four, and one trigger pass. The project-update result covers one configured Gateway Scripting Project, one function, one String tag, and one project update. It does not establish exact restart timing, transient quality, or cache behavior for other script structures. The Gateway-backup result covers only the stated 8.1.53-to-8.3.8 fixture. These results do not establish an exact scheduling guarantee or cover other inputs, preferred-argument functions, poll rates, Tag Groups, execution modes, other project-library functions, bindings, loads, performance conditions, migration routes, or other hosts. Check the Gateway Scripting Project before changing the expression, and validate other structured shapes and sizes, project-library resolution, lifecycle recovery, latency, and migration separately.

One additional fixed 100-millisecond fan-out campaign used Event-Driven cohorts of 1, 10, and 25 Expression Tags. Their script windows were 101, 413, and 919 milliseconds, and their maximum observed interval overlaps were 1, 3, and 3. All 36 targets remained Good/192 with no expression errors. This covers one local Gateway, one Tag Group, fixed work, fixed counts, and one credited trigger pass per cohort; it did not execute sessions. Treat the results as local measurements, not an SLA, capacity, throughput, scheduler, maximum-concurrency, session-load, or production-sizing guarantee. Measure the intended Tag Group and representative fan-out while recording latency, CPU, memory, thread states, quality, and Gateway logs.

Prefer native expressions for small reactive calculations. Move complex, stateful, looping, side-effecting, or I/O-heavy work to an explicit scripting/event boundary.

## Migrate From 8.1 Deliberately

1. Inventory expressions containing `forceQuality(`, `qualifiedValue(`, `translate(`, `runScript(`, `tag(`, `now(`, `dateFormat(`, and timezone helpers.
2. Capture the 8.1 value, type, quality details, timestamp, locale/timezone, and surface.
3. Upgrade through the supported installer or Gateway-backup path when validating migration transforms; direct project/tag import is a different test.
   One fixed Gateway backup from Ignition 8.1.53 restored into 8.3.8 with two project-library files and five script-backed Expression Tags unchanged; their fixed imports, returns, exception/fallback behavior, and 500-millisecond polling passed on both sides. Separately, one fixed SFC project loaded and started by 8.1.53 was imported as a project resource without rewriting its providerless Transition expression, but that direct-import result covers only project-content portability.
   A second fixed 8.1.53-to-8.3.8 Gateway-backup fixture retained exact legacy `forceQuality()` and modern `qualifiedValue()` expression text across source restart and target restore. Its legacy-zero and modern-Bad tags remained Bad, its legacy-192 and modern-Good tags remained Good, and the supplied modern-Bad diagnostic remained exact. This verifies persistence for those four tags; it does not prove automatic quality conversion, expression rewriting, or a complete legacy-to-modern mapping.
4. Re-run each high-risk expression on the exact 8.3 build.
5. Test Perspective dynamic Named Query paths, Event Streams, and SFC surfaces as new host contexts rather than assuming tag-side equivalence.
6. Classify differences as documentation change, harness/fixture issue, intended 8.3 change, fixed defect, or regression.
7. Update the expression only after the semantic difference is understood.

## Validate Through Bounded APIs

Read `references/validation-workflow.md` before using a live Gateway.

At minimum:

1. Capture `gatewayInfo`, module health, timezone, tag providers, and the live `/openapi.json`.
2. Inspect the current API or test-adapter capability contract; never assume routes from another Gateway or an older skill.
3. Take a backup or export before mutation.
4. Use a unique run root under an explicit test-only namespace.
5. Dry-run first.
6. Apply only a bounded, allowlisted request.
7. Read back configuration plus value, type, full quality, and timestamp.
8. Exercise idempotent replay and conflict behavior when supported.
9. Clean up the exact run root and verify absence.
10. Review the pre/action/post Gateway WARN-or-higher log windows.

If no suitable route exists, prefer a narrowly scoped fixed-fixture adapter over arbitrary code execution. Require authentication, an allowlist, item/size bounds, dry-run, explicit apply, idempotency, exact-prefix enforcement, readback, exact cleanup, and diagnostics. Do not add a general script-evaluation endpoint.

## Answer With Useful Boundaries

When delivering an expression:

- Name the target surface and configured output type.
- Provide the expression in a `text` code block.
- Explain the path, null, type, and quality assumptions.
- Call out 8.3/build/module requirements.
- Include a bounded validation recipe when behavior is runtime-sensitive.
- State what remains unverified instead of presenting a cross-surface inference as fact.
