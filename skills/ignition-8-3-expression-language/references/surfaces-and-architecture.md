# Ignition 8.3 Surfaces and Architecture

## Keep the Language Separate From Its Hosts

The same expression text can behave differently because the host supplies different bound values, output coercion, quality handling, update triggers, security context, and timezone/locale.

| Host | Expression result represents | Important context |
|---|---|---|
| Expression Tag | Tag value | Configured tag type, provider, execution mode, quality |
| UDT expression member | Member value | Parameters, sibling members, instance provider |
| Perspective Expression binding | Property value | View/session properties, transforms, security, locale |
| Perspective Tag binding Expression mode | Tag path string | Path must resolve for the binding |
| Perspective Named Query path Expression mode | Named Query path | Parameters are configured separately |
| Vision Expression binding | Component property value | Window/component path, client timezone, retargeting |
| Event Stream handler expression | Handler field value | Event data/metadata supplied by source type |
| SFC condition | Boolean decision | SFC context, default provider, lifecycle timing |

Never promote a result from one row to another without either official host documentation or a host-specific runtime test.

## Perspective Named Query Path Expressions

Perspective Query Bindings support Direct and Expression path modes. Expression path mode is documented as new in Ignition 8.3.7.

Use Direct mode when:

- The Named Query is fixed.
- Automatic parameter discovery is useful.
- Design-time traceability is a priority.

Use Expression mode when:

- The Named Query path must vary by site, asset, tenant, recipe, user selection, or environment.
- The project deliberately accepts less automatic schema assistance.

In Expression mode:

- Return a valid Named Query path string.
- Define the parameter rows explicitly.
- Remember that parameter value fields are expressions; quote string literals.
- Test every possible path with the parameter set it expects.
- Test malformed expressions plus missing, unauthorized, and wrong-return-shape paths.
- Consider whether dynamic path selection makes dependencies too difficult to audit.

### Verified 8.3.8 Runtime Subset

A bounded Perspective Query Binding fixture on Ignition `8.3.8
(b2026071409)` verified:

- One API-authored Direct-mode binding used exact fixed path
  `LLM Tests/Expression Validation/NQP Golden 03b932b7/QueryA` and a
  configured integer Value parameter `id = "101"`. In one mounted Designer
  session it published scalar `"1101"` at Good/192, sequence `1`, with
  positive binding/observation timestamps and nonempty session/page identity.
  Polling and value cache were disabled. Designer editor acceptance,
  automatic parameter discovery, and parameter persistence after editor
  changes were not tested.
- One API-authored constant path expression had exact text
  `"LLM Tests/Expression Validation/NQP Golden 03b932b7/QueryA"`. With one
  manually configured `id = "102"` Value parameter, it resolved that fixed
  QueryA path and published `"1102"` at Good/192 in one fresh fixed
  session/page. Polling and value cache were disabled. Designer editor
  acceptance and other constant-expression shapes were not tested.
- One path expression directly referenced the String view custom property
  `{view.custom.querySelector}`. The property was fixed-bound to the Selector
  tag, while the result-change observation recorded the property value itself
  rather than rereading that tag. In one unchanged session/page, property
  values `A` -> `B` -> `A` published `QueryA/"1101"` ->
  `QueryB/"2101"` -> `QueryA/"1101"`, all Good/192 with sequences
  `1` -> `2` -> `3` and strictly advancing binding/observation timestamps.
  The binding used one manual integer `id = "101"` Value parameter with
  polling and value cache disabled.
- A tag-driven expression path switched `QueryA` to `QueryB`, back to
  `QueryA`, and again to `QueryB` without a session restart.
- Both queries reused one manually configured `id` Value parameter. Scalar
  results changed from `1101` to `2101` with Good quality, while the resolved
  path, observation sequence, and binding timestamp advanced.
- With `QueryA` held constant, one manually configured `id` Value parameter
  used the exact expression
  `tag("[default]_expression_skill_tests/perspective_nqp_03b932b7/ParameterId")`.
  Changing that fixed Int4 source `101` -> `202` -> `101` published
  `"1101"` -> `"1202"` -> `"1101"`, all Good/192. Observation sequences
  advanced `2` -> `3` -> `4`; source, binding, and observation timestamps
  strictly advanced; and the session/page identity remained unchanged.
  Polling and value cache were disabled.
- With explicit `id`, `site`, and `equipment` rows, the same binding switched
  `QueryA` -> `QueryDifferentParams` -> `QueryA` and published String-compatible
  results `"1101"` -> `"alpha:pump-7"` -> `"1101"`, all Good/192 with fresh
  resolved paths, timestamps, and sequences. String parameter sources were
  quoted expression literals.
- A fixed server-owned cycle wrote `A` -> `B` -> `DIFF` ten times in immediate
  succession. All 30 tag writes were Good. The final selector won with a fresh
  `QueryDifferentParams` observation, value `"alpha:pump-7"`, and Good/192
  quality; a normal `A` selection then produced a newer Good/192 `"1101"`.
  The fixed parameter union was `id="101"`, `site="alpha"`, and
  `equipment="pump-7"`, and callers could not supply paths, parameters,
  sequences, or delays.
- A fixed polling binding held selector `POLL`, resolved path `QueryPolling`,
  and all binding parameters constant. Its rate was serialized as string
  expression `"1"`. After the baseline, six unique SQLite-clock values were
  observed in 6,522 ms, all Good/192. Consecutive database intervals were
  1,000, 1,001, 1,002, 1,000, and 1,003 ms; observation intervals were 1,000,
  1,001, 1,002, 1,000, and 1,002 ms.
- Direct reflection of the installed 8.3.8 `PollingConfig.fromJson` showed a
  resource-serialization discrepancy: numeric JSON rate `1` normalized to
  default expression `30`, while string JSON rate `"1"` remained expression
  `1`. The numeric diagnostic evaluated once and produced no additional poll
  in 6.5 seconds. Prefer Designer- or supported API-authored binding resources.
  If resource JSON must be generated, preserve the rate expression as a string
  and verify both installed-runtime readback and live cadence.
- Switching to a query with different Value parameters while only `id` was
  configured produced a fresh Good null on this target. The old successful
  value was replaced, but the parameter mismatch did not become a non-Good
  quality.
- In a separate negative fixture, missing QueryString parameters produced
  `Error_Exception` with null value and diagnostic text naming the missing
  `{site}` parameter.
- Empty string and expression null were distinguishable in an API-imported
  runtime fixture. Empty string published null/`NoneType` with
  `Error_Exception("Named query \"\" not found.")`, full signed code
  `-1073741048`; expression null published null/`NoneType` with
  `Error_Configuration`, full signed code `-1073741055`. Both observations
  were fresh, replaced the prior Good scalar, and recovered to a newer Good
  `1101`. Designer editor acceptance was not tested.
- One API-authored saved resource used the exact malformed path expression
  `if(`. In one mounted Designer session/page it published a fresh
  null/`NoneType` with
  `Error_Configuration("RuntimeException: Syntax Error on Token: 'End of Expression' (Line 0 , Char 0)")`,
  full signed code `-1073741055`, sequence `1`, and positive
  binding/observation timestamps. No QueryA, QueryB, or
  QueryDifferent result was published. This proves runtime behavior for that
  fixed imported resource, not whether the Designer editor prevents or flags
  it before save.
- An integer path result of `123` was converted to path text `"123"` and
  treated as that exact Named Query path. Because no such query existed, the
  binding published null/`NoneType` with
  `Error_Exception("Named query \"123\" not found.")`, full signed code
  `-1073741048`, then recovered to a newer Good/192 `1101` after the expression
  returned the valid string path again. Return a valid path string; do not rely
  on numeric coercion to identify a query.

This distinction matters: a dynamic path with an incompatible parameter schema
does not have one universal failure shape. Check the selected path, value,
quality, and timestamp together. If null is invalid, reject a Good null
explicitly instead of waiting for a quality error.

Use prepared Value parameters for ordinary data values. QueryString parameters
are substituted into SQL text without sanitization and are susceptible to SQL
injection; the negative result above is evidence about missing-value behavior,
not a recommendation to replace Value parameters with QueryStrings.

Prefer Designer- or API-authored Named Query resources. In inspected 8.3
resource JSON, numeric `sqlType` is an Ignition `DataType` ordinal, not a
`java.sql.Types` code: String is `7`, while `12` is `Int4Array`. Using `12` for
a string QueryString parameter caused a String-to-Long-array coercion failure
on the verified target.

The runtime subset does not cover Designer acceptance or automatic parameter
discovery for Direct mode, parameter persistence after Direct-mode editor
changes, other Direct queries or parameter shapes, Designer acceptance of the
API-authored constant or property-driven path expressions, other constant
expressions, view parameters, bidirectional property bindings, other property
types or transforms, other parameter-expression sources or types, multiple
  dynamic parameters, Designer acceptance of empty/null, malformed, or
  non-string path expressions, other malformed expression shapes, document
  and other non-string path types, mixed result schemas,
permissions, deletion races, other missing-path shapes, polling rates or
expressions beyond the fixed one-second string, polling pause/resume or
failure behavior, Cache & Share, restart, save/reopen, arbitrary rapid
sequences or delays, simultaneous clients, other concurrency, load, or
migration. Validate those separately.

Official documentation:

- https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/query-bindings-in-perspective
- https://www.docs.inductiveautomation.com/docs/8.3/platform/sql-in-ignition/named-queries/named-query-parameters

## Event Streams

Event Streams are an Ignition 8.3 host surface. Handler expressions use the expression language and can access source-specific event data and metadata.

Examples of documented tag-event references include:

```text
{event.data.value}
{event.data.quality}
{event.data.timestamp}
{event.metadata.tagPath}
{event.metadata.isInitial}
{event.metadata.previousValue}
```

Only use fields documented for the selected source. Kafka, HTTP, alarm, tag, timer, Gateway, and listener events do not expose identical objects. Some sources or handlers require additional installed modules.

Validate:

1. Expression compile status.
2. The providing module and handler availability.
3. Test-panel output for representative payloads.
4. Missing or malformed data/metadata.
5. Quality-code and timestamp serialization.
6. Handler side effects and failure behavior.
7. Saved/running/faulted status after project save.

Do not reuse `{event...}` references in Expression Tags or component bindings.

### Verified 8.3.8 Tag Event Subset

A bounded runtime fixture on Ignition `8.3.8 (b2026071409)` verified one Tag Event source with four Tag Handlers:

- `{event.data.value}` delivered changed `Int4` values `42` and `43`.
- A static Tag Handler path received both values.
- A dynamic path expression chose between two complete, provider-qualified paths below one run root:

  ```text
  if({event.data.value} = 42,
     "[<provider>]<test-root>/DynamicEven",
     "[<provider>]<test-root>/DynamicOdd")
  ```

- A separate fixed target echoed the same selected path.
- A quality expression of `192` wrote `Good` quality with full code `192`.
- The unselected dynamic target and an in-root canary remained unchanged.
- The stream reported `RUNNING`; its Tag Event source and four Tag Handlers reported `GOOD` with no diagnostic errors after the controlled triggers.

The path expression above is safe only because every possible return is a server-owned, provider-qualified literal below the same root. An Event Stream expression does not enforce authorization. Do not build write targets by appending untrusted payload text. Enumerate allowable destinations with `if()`, `case()`, or `switch()`, echo the resolved path, and verify a canary or outside-root readback.

During cleanup, deleting the project removed it from the project list before the runtime Event Stream list cleared. Poll project absence plus `system.eventstream.listEventStreams()` or the official status/details routes until the stream is absent, then remove subscribed tags. Do not treat project-delete HTTP success as proof that subscriptions have already shut down.

This runtime evidence does not cover other source types, missing/null event members, string or invalid quality, timestamp expressions, filters, transforms, batching, disabled/faulted streams, restart, migration, or Designer test controls.

Official documentation:

- https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/event-streams
- https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/event-streams/types-of-sources/source-data-and-metadata

## SFC Expressions

Ignition 8.3.8 adds full expression-language support and expression editor helpers to an SFC Parallel Element's cancel condition.

Ignition 8.3.8 also fixes SFC transition expressions so `tag()` applies the configured default provider when a relative path omits a provider.

### Verified 8.3.8 Callable-Transition and Relative-Path Subset

A bounded callable SFC on Ignition `8.3.8 (b2026071409)` used a providerless transition expression shaped like:

```text
tag("Area/TransitionGate")
```

The disposable project's official configuration readback confirmed its default tag provider before start. With the referenced Memory Tag at Good false, the same chart instance remained `Running`. A Good true write moved it to `Stopped` on the first official detail read; the action and teardown WARN-or-higher log windows were empty.

Two additional fixed charts tested the relative bases directly:

```text
tag("[~]<test-root>/TildeTransitionGate")
tag("[.]DotSiblingGate")
```

For `[~]`, the tag below the configured default provider root controlled the transition: Good false and an explicit false rewrite preserved `Running`, then Good true produced `Stopped` on the first official detail read.

For `[.]`, two mutually exclusive server-owned candidates distinguished possible bases. A tag beside the chart's logical resource folder did not fire the transition and the same instance remained `Running`. After that candidate was reset false, a tag named `DotSiblingGate` at the configured default provider root moved the instance to `Stopped`. Thus, on this tested 8.3.8 callable SFC Transition host, `[.]` resolved from the default provider root rather than the SFC chart resource folder.

The general Tag Paths documentation describes `[.]` relative to the host tag's folder. An SFC Transition is not a host tag. Keep the observed SFC base scoped to this host and build; do not transfer it to Expression Tags, UDT members, bindings, Parallel cancel conditions, or other surfaces without their own test.

One additional chart used a chart-scope target path:

```text
tag({TargetPath})
```

The chart started with target A selected and false. Making only target B true
left the same instance `Running` for 1.53 seconds while scope readback remained
A. Changing only that instance's `TargetPath` to the already-true B target
produced `Stopped` after 15 ms, without another tag write.

A fifth chart referenced one deliberately absent, provider-qualified target:

```text
tag("[<provider>]<test-root>/MissingTransitionTarget")
```

Before start, after start, after a 2.119-second observation, and after terminal
handling, direct reads returned null/`NoneType` with non-Good
`Bad_NotFound("<path> not found.")`. The same instance remained `Running` at
`WaitForDeliberatelyMissingTag` and did not reach End. The exact action window
contained no missing-tag warning. Official exact-instance cancellation produced
`Canceled`, and retained detail then cleared.

The official quality table lists `Bad_NotFound` subcode `519`. The verified
Gateway-scope Jython read exposed the signed composite full code
`-2147483129` (`0x80000207` unsigned). Keep full code, subcode, readable name,
diagnostic, and Good flag as separate evidence fields.

Another fixed chart selected one disposable standard provider as the project's
default and used this providerless Transition:

```text
tag("_expression_skill_tests/<fixed-run>/TransitionGate")
```

Good false started and held the exact instance `Running`. While that provider
was disabled, its official configuration readback reported disabled/Faulted,
the gate read null with non-Good
`Bad_NotFound("Tag provider '<provider>' not found")` and full code
`-2147483129`, and the same instance stayed `Running` for 1.655 seconds.
Re-enabling the provider restored Good false on the first recovery inspection
without changing the instance. Good true then moved that instance to
`Stopped`. Immediate and post-runtime project exports retained the exact
providerless expression.

This is evidence for one standard provider, one project-default lookup, and
one disable/re-enable cycle. It does not cover remote providers, rename or
deletion, multiple disabled providers, restart, Uncertain/stale values, other
Bad subcodes, arbitrary expressions, or other SFC hosts.

A separate chart tested project-resource migration rather than a full Gateway
upgrade. A fixed project was loaded, externally scanned, and started by an
isolated Ignition 8.1.53 Gateway with this Transition:

```text
tag("_expression_skill_tests/<fixed-run>/Legacy81RelativeGate")
```

The settled three-file project archive was imported into 8.3.8. Immediate
export and post-runtime export preserved `sfc.xml` byte-for-byte and preserved
the exact providerless expression. With the configured `default` provider,
Good false kept the same instance `Running` for 1.648 seconds; rewriting false
still kept it `Running`; Good true moved that exact instance to `Stopped`.
Gateway-owned `lastModification` metadata was the only accepted 8.1 settling
change. This demonstrates the fixed project's content portability and 8.3.8
runtime resolution, not Designer authorship or the transformations performed
by an installer or Gateway-backup upgrade.

The stopped instance remained in SFC detail for the platform's short completed-instance retention period before the detail list and running count cleared. Treat terminal-state observation and later instance removal as separate lifecycle checkpoints. Before cleanup, require the chart to be non-running, delete the project, and poll project names, SFC status, totals, and chart detail until the definition and instance are absent.

This proves only the seven fixed callable transitions across two disposable projects, configured default providers, providerless/`[~]`/`[.]` paths, one dynamic A-to-B path retarget, one explicit-provider missing target, one disabled/re-enabled disposable standard provider, one 8.1.53-loaded project-resource import, Good Boolean Memory Tag sequences, the two fixed `[.]` candidate locations, normal completion, and exact-instance cancellation. It does not prove Parallel cancellation, other relative or dynamic path shapes, remote providers, provider rename/deletion, Uncertain/stale values, timeouts, faults, hot edits, persistence, restart, redundancy, other migrated content, or full Gateway-upgrade transformations.

Even with that fix:

- Prefer explicit provider intent in reusable logic.
- Confirm what the SFC project uses as its default provider.
- Test transition false/true changes, immediate cancellation, normal completion, faults, and restart/recovery behavior.
- Review Gateway logs around the SFC test.
- Do not infer the SFC base path from Expression Tag behavior.

### Verified 8.3.8 Parallel-Cancellation Subset

A second bounded callable fixture used a Parallel Element with two branches held by false transitions and this fixed cancel condition:

```text
tag("[<provider>]<test-root>/Cancel")
```

Project export readback preserved the enabled cancel condition, explicit provider, and exact expression. A Good false Boolean tag kept the same chart instance `Running` for the observation interval; an explicit false rewrite also preserved it. A Good true write produced `Stopped` on the first official detail read, 17 ms after the request began. The completed instance then remained visible during normal SFC retention before status/detail cleared.

The same fixture started an Enclosing-step parent whose child was blocked, then called `system.sfc.cancelChart()` immediately after `system.sfc.startChart()` returned. The measured start-return-to-cancel-call interval was 0 ms. The call returned without an exception, and both parent and child left the active set. The exact action and teardown WARN-or-higher log windows were empty.

This proves only the fixed callable charts, one explicit-provider `tag()` cancel expression, Good Boolean false/true input, two blocked Parallel branches, and one immediate Enclosing-child cancellation. It does not prove the full expression-function catalog in cancel conditions, providerless or relative paths there, non-Good quality, branch-completion races, every cancellation timing, faults, hot edits, persistence, restart, redundancy, or migration.

### Verified 8.3.8 Native-Expression and Edge Parallel Suite

A separate fixed project exported and ran nine callable Parallel charts. Two literal baselines established the control-flow endpoints: cancel condition `false` with two true branch transitions reached `Stopped` after 25 ms, while cancel condition `true` cancelled two otherwise blocked branches and reached `Stopped` after 16 ms. Each chart emitted exactly one chart-level `onStop`, with no `onCancel`, `onAbort`, or duplicate terminal event. Thus, cancelling a Parallel element did not mean cancelling the chart; the chart continued to its End step.

Three additional charts used provider-qualified tag paths and one allowlisted input change:

```text
(tag("<input>") * 2) > tag("<threshold>")
if(tag("<flag>"), true, false)
try(toInt(tag("<text>")) > 0, false)
```

For the arithmetic/comparison case, Good input `4` with threshold `10` kept the same instance `Running`; input `6` produced `Stopped` 20 ms after the request began. For `if()`, Good false kept the instance `Running`, and true produced `Stopped` after 16 ms. For the `try()` guard, the Good string `"not-a-number"` kept the instance `Running` without a WARN-or-higher entry in the exact action window; `"1"` produced `Stopped` after 22 ms.

The additional edge charts used a literal `null`, a fixed `tag()` result that could preserve Boolean true while switching between Bad and Good quality, and a fixed two-tag branch/cancel race:

```text
null
tag("<bad-quality-condition>")
tag("<race-cancel>")
```

The Good literal `null` stayed `Running` with both branches blocked until the exact instance was cancelled. A true value with Bad quality also stayed `Running`; changing only the quality to Good while preserving true produced `Stopped` after 19 ms. This matches the inspected 8.3.8 implementation: Good results are coerced to Boolean, and a non-Good result is treated as false before coercion.

For the race chart, one fixed server-owned write batch changed both the branch-release and cancel tags from false to true. All 20 unique instances reached `Stopped` after 13–22 ms. Lifecycle instrumentation recorded exactly 20 `onStop` calls correlated to those 20 instance IDs, with no `onCancel`, `onAbort`, or duplicate terminal event. The separately cancelled `null` chart emitted one `onCancel`; the Bad-to-Good chart emitted one `onStop`.

The ninth chart tested instance-private chart scope:

```text
{CancelRequested}
```

Two `system.sfc.startChart()` calls supplied fixed parameters `CancelRequested=false` and `InstanceSlot=A|B`, producing distinct IDs and private scope readbacks. Rewriting A false kept both instances `Running`. Writing true with `system.sfc.setVariable()` against the server-stored A ID produced `Stopped` after 21 ms. B retained its original ID, remained `Running`, and preserved false through 37 consecutive Gateway status/API samples until A left retained detail. Writing the stored B instance true then produced `Stopped` after 14 ms. Both instances emitted exactly one `onStop` correlated to ID and slot, with no `onCancel`, `onAbort`, or duplicate event.

The fixture accepted only case IDs `SFC-001`, `SFC-002`, `SFC-004`, `SFC-005`, `SFC-008`, `SFC-009`, `SFC-010`, `SFC-012`, and `SFC-013`. The literal cases had no trigger and rejected trigger attempts before writes. For `SFC-013`, the caller could select only fixed slot A or B; the adapter looked up the corresponding server-owned instance ID and fixed variable name. It rejected caller-supplied instance IDs as well as project, chart, tag path, expression, raw value, and Jython fields before writes. Project export preserved all nine chart XML files byte-for-byte. Chart completion instrumentation defined the required `onStop(chart)`, `onCancel(chart)`, and `onAbort(chart)` functions. All 26 expected lifecycle events were present exactly once. The exact action and teardown WARN-or-higher windows were empty, and the project, SFC definitions, running instances, and fixed tag root were absent after teardown.

This proves only those nine fixed conditions and the tested lifecycle operations on the callable 8.3.8 SFC Parallel host. The literal results are control-flow baselines, not proof of every branch-completion/cancellation interleaving. The invalid string demonstrates the configured `try()` fallback prevented cancellation in that host. The quality case does not cover Uncertain quality or every Bad subcode, and the race result does not generalize to arbitrary write ordering or timing. The instance result proves isolation only for two instances, two Boolean updates, the fixed chart parameter names, and the stored-ID `setVariable()` sequence. These results also do not cover every conversion function, nested errors, other SFC elements, providerless or relative cancel paths, faults, hot edits, persistence, restart, redundancy, or migration.

Official evidence:

- https://www.docs.inductiveautomation.com/docs/8.3/new-in-this-version
- https://inductiveautomation.com/downloads/releasenotes/8.3.8
- https://www.docs.inductiveautomation.com/docs/8.3/platform/tags/tag-paths
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/advanced/tag
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/if
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/logic/try
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/type-casting/toInt
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/advanced/qualifiedValue
- https://www.docs.inductiveautomation.com/docs/8.3/platform/tags/quality-codes-and-overlays
- https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/sequential-function-charts/SFC-basics/chart-properties
- https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/sequential-function-charts/SFCs-in-action/pause-resume-and-cancel
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-sfc/system-sfc-startChart
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-sfc/system-sfc-getRunningCharts
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-sfc/system-sfc-getVariables
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-sfc/system-sfc-setVariable
- https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/sequential-function-charts/SFC-basics/chart-scope-and-variables

## Vision and Perspective Runtime Context

For UI bindings:

- Resolve property paths in the actual view/window.
- Test Designer preview and runtime client/session separately.
- Include security/user roles when the referenced property or query is protected.
- Include session locale and timezone for translations and dates.
- Confirm retargeted projects and default providers.
- Inspect overlays and returned quality, not only displayed text.

### Verified 8.3.8 Vision Retarget Subset

One bounded live test launched a single authenticated Vision client against
two disposable projects on the same Gateway. Each project used its own
explicit standard provider and the same window shape:

- a direct tag binding;
- a tag expression equal to `source * 10 + 1`; and
- a property expression equal to the tag-expression result plus `1000`.

Project A's source `17` produced `17`, `171`, and `1171`. After
`system.vision.retarget()` loaded project B, its source `23` produced `23`,
`232`, and `1232`. Changing only B's source to `29` reevaluated the bindings
to `29`, `292`, and `1292`. Every source and binding observation was Good
with full quality code `192`.

The JVM identity stayed constant across the retarget. The Gateway's active
client record matched project B, and B's client ID remained stable through
the post-retarget source update. The client ID changed between projects A and
B, so do not use cross-retarget client-ID equality as the continuity oracle.
Track the test-owned JVM/runtime identity, active target project, transferred
parameters, resolved paths, value, quality, timestamp, and fresh updates.

In a second run, the generated project A and B selected different local
standard providers as their project defaults. The Vision Client system tag
`[System]Client/System/DefaultTagProvider` was Good/192 and reported A's
provider before retarget, then B's provider both before and after B's source
update.

The two projects used identical default-path binding text. Direct bindings
with the provider omitted or written as `[]`, `tag()` expressions using those
same two forms, and a property expression combining the expression results
all followed the target project:

| Phase | omitted direct | `[]` direct | omitted `tag()` | `[]` `tag()` | property expression |
|---|---:|---:|---:|---:|---:|
| A initial | 17 | 17 | 174 | 1705 | 1879 |
| B initial | 23 | 23 | 234 | 2305 | 2539 |
| B updated | 29 | 29 | 294 | 2905 | 3199 |

Every value in that table was Good with full code `192`. Changing only B's
fixed source produced the final row, while B's client ID and reported default
provider stayed stable.

The same window also tested `tag("[~]...")`. It remained non-Good
`Error_ExpressionEval`, full code `-1073741054`, in all three phases. This is
consistent with the documented distinction: an omitted provider or `[]`
means the current project's default, while `[~]` is relative to the provider
of a tag hosting the binding. Do not transfer `[~]` behavior from an
Expression Tag or SFC Transition to a Vision component expression.

This proves only one Windows launcher client, classic authentication, one
same-Gateway retarget, explicit and project-default paths, two local standard
providers, fixed numeric values, the listed binding shapes, and one
target-source update. It does not prove a different Gateway, remote providers,
provider rename/deletion/faults, other relative forms, other
binding/value/quality shapes, rapid or repeated retargets, restart, redundancy,
migration, security-context bindings, Designer equivalence, or independent
reproduction on a fresh Gateway.

The
[8.3 retarget documentation](https://docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-vision/system-vision-retarget)
defines the project-load and parameter-transfer boundary. The
[8.3.8 release notes](https://inductiveautomation.com/downloads/releasenotes/8.3.8)
identify both the Vision binding fix after project retargeting and an Alarm
Status Table fix for null expression priorities. The retarget binding subset
above is runtime verified; the Alarm Status Table item remains only a
regression-test lead.

Default-provider interpretation is bounded by the
[project-properties documentation](https://docs.inductiveautomation.com/docs/8.3/platform/designer/project-properties),
[Tag Paths documentation](https://www.docs.inductiveautomation.com/docs/8.3/platform/tags/tag-paths),
and
[Vision Client system-tag documentation](https://www.docs.inductiveautomation.com/docs/8.3/platform/tags/types-of-tags/system-tags).

### Verified 8.3.8 Vision Login/Logout Security-Expression Subset

One bounded live test used a single Vision client, the `default` classic user
source, and two fixed internal users with disjoint fixed roles. The project
auto-logged in as alpha, then called `system.vision.switchUser()` for beta and
again for alpha. A successful switch replaces the current identity and
closes/reopens the client's windows.

The window bound three Label `text` properties:

```text
toStr(tag("[System]Client/User/Username"))
toStr(hasRole("expr83_vis005_alpha_03b932b7"))
toStr(hasRole("expr83_vis005_beta_03b932b7"))
```

The client also sampled `system.vision.getUsername()` and
`system.vision.getRoles()` as independent scripting-side identity evidence:

| Phase | username expression | alpha role | beta role | scripting identity |
|---|---|---:|---:|---|
| alpha initial | alpha | `true` | `false` | alpha / alpha role |
| beta | beta | `false` | `true` | beta / beta role |
| alpha restored | alpha | `true` | `false` | alpha / alpha role |

Every bound value had Good quality with full code `192`, both switch calls
returned true, and no phase mixed current-user data with the prior user's
roles. The client ID and JVM identity stayed constant across all three
phases. The window object identity changed after each switch, consistent with
the documented close/reopen behavior.

When a background test worker must invoke `switchUser()`, marshal the call to
the Swing event-dispatch thread. The verified 8.3.8 client did not expose
`system.util.invokeAndWait`; `javax.swing.SwingUtilities.invokeAndWait`
provided the tested handoff. Treat this as a harness detail, not an
expression-language requirement.

This proves reevaluation only for one Windows client, two successful fixed
identity replacements, the default classic user source, two disjoint roles,
one username system tag, and `hasRole()` converted to Label text. It does not
prove failed credentials, anonymous/logout-screen behavior, role edits during
a session, other authentication strategies or user sources, multiple
clients, other security functions, Designer preview, restart, redundancy, or
migration.

The
[hasRole documentation](https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/users/hasRole),
[switchUser documentation](https://docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-vision/system-vision-switchUser),
and
[getUsername documentation](https://www.docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-vision/system-vision-getUsername)
define the tested current-user boundary.

### Verified 8.3.8 Vision Gateway-Restart Subset

One fixed run kept a single Windows Vision client JVM alive while its
independent Gateway restarted through the official 8.3 REST operation with
explicit confirmation. Exact Gateway name, host, port, build, and redundancy
role were checked before the call; the same identity, healthy Vision module,
and a new Vision-module startup time were required afterward.

Project B's source and required bindings were:

| Phase | source | direct | `tag()` expression | property expression | default-provider controls |
|---|---:|---:|---:|---:|---|
| before restart | 23 | 23 | 232 | 1232 | 23 / 23 / 234 / 2305 / 2539 |
| after restart and source update | 29 | 29 | 292 | 1292 | 29 / 29 / 294 / 2905 / 3199 |

All required values had Good quality with full code `192`. The JVM identity
stayed constant. The Vision client ID changed during reconnect, and the new
ID matched the Gateway's active client record. This is successful
same-process recovery with client re-registration, not evidence that client
IDs persist across restart.

The fixture's `[~]` `tag()` expression remained non-Good
`Error_ExpressionEval`, full code `-1073741054`, before and after restart;
the restart did not change the earlier host-specific classification. This
test covers one client, one independent Gateway, one retargeted project, two
local standard providers, one source update, and one restart. It does not
cover redundant Gateways, multiple clients, security-expression restart,
long outages, repeated restarts, migration, or other binding shapes.

### Verified 8.3.8 Vision Cleanup Subset

A separate read-only audit ran after the fixed retarget, default-provider,
login/logout, and restart campaigns. Official project, Tag Provider,
user-source, SCIM user/role, and Vision-client inventories contained zero
fixed Vision test prefixes. A bounded recursive browse of the shared
`[default]_expression_skill_tests` root returned zero children without
truncation. The local process inventory found no Java process containing the
fixed Vision project prefix, and the five-minute WARN-or-higher window
contained zero matching run identities.

The audit observed llmImport 0.78.0 with 70 actions and added no action or
Gateway mutation. It proves exact absence for the fixed local resources used
by those campaigns. Remote-provider cleanup remains untested because the
current Gateway Network has no eligible remote or redundant topology.

## Translation and Locale

Use BCP-47 locale tags at expression and Perspective session boundaries:

```text
translate("START_COMMAND", "zh-CN")
```

A bounded Ignition `8.3.8 (b2026071409)` Gateway Expression Tag test stored a
global Simplified Chinese translation through the official `zh-CN.json`
configuration data-file route. The translation singleton represented that
locale internally as `zh_CN`, while the expression above returned the exact
translated text with Good quality and full code `192`. The hyphenated BCP-47
argument worked without an underscore workaround.

That observation proves the explicit-locale call on the tested Gateway
Expression Tag host. A separate bounded test on the same 8.3.8 Gateway used
this current-locale Perspective Expression binding:

```text
translate("Close")
```

In one active Designer session, changing the session locale from `en-US` to
`de-DE`, then `fr-FR`, then back to `en-US` reevaluated the binding without a
reload. The observed sequence was `Close`, `Schliessen`, `Fermer`, `Close`;
every result had Good quality code `192`, a strictly newer observation
sequence, and the same session/page identity. The final English result was
newer than the French result, so no stale prior-language value remained.

Scope this evidence to one Designer session and the pre-existing global
translations on the tested Gateway. Browser sessions, Vision clients,
unknown-locale fallback, translation migration, restart, and independent
reproduction remain separate tests. For any locale-reactive host, record the
locale, translated value, full quality, timestamp or sequence, and runtime
identity together.

Official documentation:

- https://www.docs.inductiveautomation.com/docs/8.3/appendix/expression-functions/translation/translate
- https://docs.inductiveautomation.com/docs/8.3/platform/localization-and-languages
- https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/expression-bindings-in-perspective

## 8.3 File-Backed Configuration

Ignition 8.3 stores Gateway configuration as file-backed resources. Projects remain under `data/projects`; Gateway resource collections are under `data/config/resources`. Runtime and module state can still exist under `data/var`.

Documented collection roles:

| Collection | Role |
|---|---|
| `system` | Built-in immutable resources |
| `external` | Externally managed, read-only within the Gateway |
| `core` | Normal mutable base configuration |
| custom deployment mode | Overrides/inherits for an environment |
| `local` | Host-specific resources; not inherited like normal mode content |

An inactive collection can contain a resource definition without making it the active runtime definition. Record the active deployment mode and collection whenever configuration identity affects an expression test.

Do not hand-edit resource files as a first choice. Prefer the Gateway UI, documented OpenAPI, or `system.config` in Gateway scope. File-system scans and restart operations can be disruptive.

Official documentation:

- https://www.docs.inductiveautomation.com/docs/8.3/appendix/reference-pages/gateway-folder-structure
- https://www.docs.inductiveautomation.com/docs/8.3/platform/gateway/web-interface/platform/gateway-deployment-modes
- https://www.docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions/system-config

## Live OpenAPI

The Gateway generates `/openapi.json` from the installed modules and current Gateway state. Do not hard-code a route inventory from public examples or another Gateway.

Before using the API:

1. Fetch and hash the target-local specification.
2. Identify authentication and exact request/response schemas.
3. Prefer read-only discovery first.
4. Enable/review auditing for configuration mutations.
5. Treat POST, PUT, and DELETE as potentially destructive.
6. Use preconditions, backups, exact scope, readback, and cleanup.

Official documentation:

- https://www.docs.inductiveautomation.com/docs/8.3/platform/gateway/openapi

## 8.1-to-8.3 Migration Boundary

Use the supported installer or Gateway-backup restore path to validate actual migration transforms. Importing selected projects or tags into a fresh 8.3 Gateway is useful for content testing but is not equivalent to upgrading the Gateway configuration.

Verified narrow content boundary: one three-file SFC project was loaded and
started by Ignition 8.1.53, imported into 8.3.8, exported before and after
runtime, and retained its providerless Transition XML and expression exactly.
Treat that as evidence for the fixed project resource only. Continue to use a
supported installer or Gateway-backup restore when the claim concerns
Gateway-wide upgrade conversion.

Verified narrow Gateway-backup boundary: one exact Ignition 8.1.53 Gateway
with the intended Gateway Scripting Project was backed up through the Gateway
backup utility and restored into exact Ignition 8.3.8. Two project-library
files and five script-backed Expression Tag texts were exact after restore.
Fixed imported integer and string returns stayed Good, a direct deterministic
exception stayed `Error_ExpressionEval`, its `try()` wrapper returned the Good
fallback, and a 500-millisecond polled function produced 11 distinct Good
timestamps in 20 observations on both versions. Source restart persistence,
target cleanup, source/target logs, and absence of test-owned containers,
volumes, and listeners were also checked.

That result does not cover the installer-upgrade route, other source or target
builds, arbitrary project-library imports, other return shapes, poll rates,
Tag Groups, bindings, sessions, redundancy, production load, or automatic
rewrites outside the fixed fixture. For another migration, inventory the
high-risk expressions below; capture exact source behavior; use the intended
supported upgrade route; then compare project scripts, expression text, value,
type, full quality, timestamp, polling, restart behavior, and logs.

High-risk expression inventory:

```text
forceQuality(
qualifiedValue(
translate(
runScript(
tag(
now(
dateFormat(
getTimezone
```

Official upgrade guidance:

- https://www.docs.inductiveautomation.com/docs/8.3/getting-started/installing-and-upgrading/ignition-8-upgrade-guide/81to83-upgrade-guide
