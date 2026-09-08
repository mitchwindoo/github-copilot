# UDT inheritance and layered overrides

Use this chapter when a base UDT, derived UDT, or concrete instance changes parameters, member values, event scripts, alarms, documentation, or members below a Folder.

## The three layers

1. A base definition is a complete `UdtType` imported below `_types_`.
2. A derived definition is a `UdtType` whose provider-relative `typeId` points to the base. Send only intentional overrides and derived-only members.
3. A concrete instance is a `UdtInstance` whose `typeId` points to the base or derived definition. Instance parameter values are normally scalars; member overrides are path stubs.

Import definitions before dependents: base, then derived, then instances. Do not include `_types_` or a provider prefix in `typeId`.

## Override an inherited member

Identify an inherited member by repeating its `name` and `tagType`, then include only the properties intentionally overridden. Omission means inherit.

```json
{
  "name": "DerivedPump",
  "tagType": "UdtType",
  "typeId": "Equipment/BasePump",
  "parameters": {
    "Flavor": {"dataType": "String", "value": "DERIVED"},
    "Factor": {"dataType": "Int4", "value": 3}
  },
  "tags": [
    {"name": "Input", "tagType": "AtomicTag", "value": 1, "documentation": "derived-doc"},
    {
      "name": "Area",
      "tagType": "Folder",
      "tags": [
        {"name": "FolderValue", "tagType": "AtomicTag", "value": 6}
      ]
    },
    {
      "name": "DerivedOnly",
      "tagType": "AtomicTag",
      "valueSource": "memory",
      "dataType": "Int4",
      "value": 99
    }
  ]
}
```

To reach a member below a Folder, reproduce every containing Folder as a nested stub. Do not flatten `Area/FolderValue` into a single name. A Folder does not introduce a new UDT parameter scope.

On the verified Gateway, inherited expression definitions continued to use the effective layer's parameters and overridden source values. A base expression `{[.]Input} * {Factor}` evaluated as 10, 15, and 20 for base, derived, and instance layers after all `Input` values were written to 5 and the effective factors were 2, 3, and 4. A base Folder expression `{[.]FolderValue} + {Factor}` similarly evaluated as 7, 9, and 12 with Folder values 5, 6, and 8.

## Override an event script

Repeat the inherited member stub and supply the complete intended `eventScripts` entry. An omitted `eventScripts` property inherits the prior layer; a supplied array replaces that member's effective event-script configuration for the supplied event ID.

```json
{
  "name": "Input",
  "tagType": "AtomicTag",
  "eventScripts": [
    {
      "eventid": "valueChanged",
      "script": "\tif not initialChange:\n\t\tparent = str(tagPath).rsplit('/', 1)[0]\n\t\tmarker = 'DERIVED|' + unicode(tag['parameters']['Flavor']) + '|' + unicode(currentValue.value)\n\t\tsystem.tag.writeBlocking([parent + '/ScriptMarker'], [marker])\n"
    }
  ]
}
```

The script body must be indented because Ignition places it inside a generated handler. Use `str(tagPath).rsplit('/', 1)[0]` for the containing path on this Jython/Gateway combination; do not assume `tagPath.getParentPath()` exists. Read the owning UDT parameter dictionary with `tag['parameters']['Name']`.

Two clean API-only repetitions proved three distinct scripts on the same inherited `Input` member: the base instance emitted `BASE|BASE|2|5`, the derived instance emitted `DERIVED|DERIVED|3|5`, and the concrete override emitted `INSTANCE|INSTANCE|4|5`. Each marker appeared exactly once and the runs contained zero Gateway ERROR logs.

For scripts attached to members in actual Folder subtrees, follow `project-library-scripts.md`. Folder depth changes how many path segments must be removed to reach the UDT root; it does not change `tag['parameters']`. Use explicit relative/cross-folder paths and verify every read.

## Override an inherited alarm

Repeat the member, the alarm `name`, and its `mode`, then supply the intended alarm properties:

```json
{
  "name": "AlarmPV",
  "tagType": "AtomicTag",
  "alarms": [
    {"name": "High", "mode": "AboveValue", "setpointA": 30, "label": "Instance alarm"}
  ]
}
```

The verified base/derived/instance thresholds of 10/20/30 produced active-source counts of 1, 2, and 3 as controlled values crossed 15, 25, and 35. Verify alarm status by exact source, not count alone, and clear every test alarm during cleanup.

## Instance overrides

Use scalar instance parameters and nested member stubs:

```json
{
  "name": "PMP-001",
  "tagType": "UdtInstance",
  "typeId": "Equipment/DerivedPump",
  "parameters": {"Flavor": "INSTANCE", "Factor": 4},
  "tags": [
    {"name": "Input", "tagType": "AtomicTag", "value": 2},
    {
      "name": "Area",
      "tagType": "Folder",
      "tags": [
        {"name": "FolderValue", "tagType": "AtomicTag", "value": 8}
      ]
    }
  ]
}
```

Memory-tag runtime writes can appear in an instance export as current values. Restore controlled values before taking a baseline-style export, or compare configuration with an explicit list of runtime-mutable properties excluded from the semantic diff.

## Extend an inherited regular Folder in a derived type

To add evidence beside inherited Folder members, submit a derived `UdtType` with the base `typeId`, then include a named Folder override. Restate inherited atomic members only when replacing their properties, and include derived-only members beside them:

```json
{
  "name": "DerivedType",
  "tagType": "UdtType",
  "typeId": "BaseType",
  "tags": [{
    "name": "RequestEvidence",
    "tagType": "Folder",
    "tags": [
      {"name": "RequestTrigger", "tagType": "AtomicTag", "eventScripts": [/* complete replacement */]},
      {"name": "ReplayDeniedCount", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Int4", "value": 0}
    ]
  }]
}
```

On the verified Gateway, export resolved the effective Folder to seven inherited members plus two additions and retained the replacement request/reset scripts. This permission applies to an ordinary Folder owned by the UDT. It does not authorize adding a new member below an inherited nested `UdtInstance`; that separate shape was rejected with `Bad_Unsupported`.

Export and count every effective Folder member after import. Verify complete event arrays, instantiate both test and Control instances, exercise the new behavior, and reset derived evidence with inherited state.

The same verified mechanism extended that inherited Folder again from nine to twelve effective members, replacing both trigger scripts and adding three typed generation/reset tags. Export all twelve members and both exact events; compile the scripts before import; then verify no-generation denial, stale-generation preservation, matching-generation reset, cross-Folder calls, bounded dedicated logs, ERROR-or-higher logs, alarms, Control isolation, and restoration.

### Restate a complete nested atomic member

Treat a named atomic member beneath an inherited ordinary Folder as a replacement boundary. An alarms-only override of a warning member exported with the new alarm but without the inherited expression or `eventScripts`. The omitted properties did not merge from the base.

When changing one property such as `timeOnDelaySeconds`, restate the member's complete `valueSource`, `dataType`, expression/reference, complete `alarms` array, and complete `eventScripts` array. Compile every restated script before import. Export the derived type and compare the complete effective member—not merely the changed delay—before creating instances.

## Export and verification lessons

- A derived export may contain empty inherited member stubs such as `{"name":"Calc","tagType":"AtomicTag"}`. These are not independent full definitions. Resolve effective behavior through the inheritance chain and runtime checks.
- Member order may change. Compare by hierarchical member path and alarm/event identity, not array position.
- Verify base, derived, and concrete branches independently: effective parameters, script marker/log, expressions, nested Folder values, alarms, derived-only members, and exact runtime quality.
- Run a second clean repetition and restore all written source values and active alarms.

At greater inheritance depth, export may fully materialize a newly added sibling Folder while reducing a twice-inherited Folder to name/type stubs. Do not interpret those stubs as proof that inherited configuration disappeared. Verify the complete alarms/scripts on the direct base export, verify hierarchical member names and counts on the deeper derived export, then instantiate and prove the effective runtime behavior with bounded dedicated and ERROR-or-higher Gateway logs.

For a further-derived ordinary Folder, verify each definition at the depth where it is complete: the direct parent export for the inherited Folder member set, the earlier direct alarm-owning base for complete alarm callbacks, and the newest derived export for the replacement event plus added members. Runtime evidence remains the final proof that the layered effective configuration executes together.

Repeat this depth-specific method at every additional layer. A verified third layer retained nine complete parent gate members, exported ten effective members after adding one String tag and replacing one event body, and still required the earlier alarm-owning base export to inspect the complete callbacks.

A verified fourth layer added a typed parameter plus three members to that inherited Folder, yielding thirteen effective gate members and two local event bodies. Expect submitted parameter `Int4` metadata to canonicalize to `Integer` in export. Expect a DataSet default to export as a JSON string on this Gateway; parse it and verify exact columns, Java types, and rows. These representation changes are not permission to loosen runtime checks: compile every local body, verify the parent at its complete depth, and exercise the derived behavior with bounded logs.

A later layer can restate the same complete Folder and change only the typed capacity default. Verify the direct parent and new export independently, require the new integer value, and compile the restated scripts again. Runtime must prove the parameter matters—for example, capacity two retains two rows before the first FIFO eviction—rather than treating an exported parameter value as sufficient behavioral evidence.

Another layer may add maintenance members and replace one inherited reset script. Verify the complete effective member set, the untouched inherited request script, the replacement reset script, and the new maintenance script independently. A verified compaction layer grew the gate from thirteen to seventeen members and compiled all local scripts before import; runtime then proved that compaction changed only retention evidence, not authorization state.

In a minimal deeper override, exported parameter ownership remains local: the derived export may contain only the newly declared parameter, while inherited capacities remain on the direct parent export. Likewise, unchanged inherited Folder members can appear as name/type stubs even though the effective member list is complete. Validate each property at the export depth that owns it; do not require inherited DataSet defaults or event arrays from a deeper stub.

A further layer may restate one inherited Folder trigger and add local evidence members plus an expression alarm. Keep the portable fixture minimal: include the complete restated trigger and only the newly owned members, alarm, callbacks, and parameter. At runtime, separately prove the inherited denial history/summary on the direct parent, the new effective member count on the derived export, and the combined behavior through two alarm occurrences. Do not copy inherited export stubs into the authored override.

A still-deeper ordinary-Folder override may replace only one complete alarm member and add sibling evidence tags. In that derived export, unchanged inherited siblings can appear as exact identity stubs containing only `name` and `tagType`, while the replaced alarm member remains complete. Assert the stubs as stubs, inspect the inherited executable script on the direct parent export, and inspect the replacement alarm and all callbacks on the newest export. Do not require a script from a stub and do not copy the stubs into the authored payload.

When the next layer changes both an inherited request decision tree and the already-replaced alarm callbacks, include both members as complete local overrides. Keep unchanged inherited siblings out of the portable payload even when the effective export lists them as identity stubs. A verified cooldown layer used a complete `RequestTrigger`, complete `DenialBurstActive`, and only twelve new cooldown members; the direct parent remained authoritative for inherited acknowledgement evidence referenced by those callbacks.

A deeper derived type may add a new ordinary Folder inside an inherited ordinary Folder without restating the inherited siblings. One verified layer added only `AcknowledgedCoordinatorReset/CooldownControl` with twelve locally owned command/evidence members. The deepest export fully materialized that new child Folder while continuing to show unchanged gate members as identity stubs. Keep the authored payload minimal, but validate all three planes: the complete inherited gate on its direct parent export, the effective gate names/count on the derived export, and the complete new child Folder plus exact local script on the derived export.

For a script on `AcknowledgedCoordinatorReset/CooldownControl/CancelTrigger`, treat `tagPath` as text and remove segments deliberately:

```python
	control_root = str(tagPath).rsplit('/', 1)[0]
	gate_root = control_root.rsplit('/', 1)[0]
```

Use `control_root` for sibling command evidence and `gate_root` for the parent's cooldown state. Do not call `tagPath.getParentPath()`. Check every read/write quality, and compile the exact indented event body under Ignition Jython before import.

The same nested ordinary Folder can be extended at the next inheritance layer without restating its inherited children. One verified layer added sixteen locally owned cooldown-extension members to the inherited twelve-member `CooldownControl`, producing 28 effective child members. At this depth, the twelve inherited children exported as `name`/`tagType` identity stubs while the sixteen new children exported complete configuration. Validate the inherited cancel script on the direct parent that owns it, validate the new extension script and members on the newest derived export, and assert the complete 28-name effective set at the deepest layer. Do not mistake identity stubs for lost behavior or copy them into the authored override.

At the next layer, a single payload can replace one atomic member in the outer inherited Folder and another atomic member inside its nested inherited Folder. A verified extension-limit layer completely replaced outer `LastCooldownSourceEventId` to add a reset handler, completely replaced inner `CooldownControl/ExtendTrigger` to add the limit decision, and added three inner evidence tags plus one typed parameter. The effective export retained 44 outer members and grew the nested Folder from 28 to 31 members. Require both replacements to export their complete value configuration and exact event arrays; require unchanged members to remain identity stubs at this depth; inspect their executable configuration at the owning parent depth.

A subsequent layer can replace only the nested trigger while retaining the outer reset override through inheritance. One verified attempt-history layer replaced complete `CooldownControl/ExtendTrigger` and added a typed DataSet, eviction counter, and reset trigger. The outer Folder remained at 44 effective members while `CooldownControl` grew from 31 to 34. In the newest export, require all four locally owned inner members to be complete, including both exact event arrays and the ten-column DataSet definition; validate the inherited outer reset script on its owning parent rather than demanding it from a deeper identity stub.

The next layer may replace two existing nested triggers and add only one Document. A verified attempt-summary layer kept the outer Folder at 44 members and grew `CooldownControl` from 34 to 35. Its portable payload contained the complete history-writing trigger, complete correlated reset trigger, new Document, and one local schema parameter; the inherited DataSet definition was validated on the direct parent because it exported as a deeper stub. This is the correct minimal override shape even though both local scripts read and write that inherited DataSet.

An alarm layer can observe inherited command outcomes without replacing the command trigger again. A verified extension-limit-pressure layer replaced the complete outer `LastCooldownSourceEventId` member, then added two expression observers and eight local state/alarm members inside inherited `CooldownControl`. The outer Folder remained at 44 effective members while the nested Folder grew from 35 to 45. Keep the portable payload to the complete outer replacement, the complete ten-member nested override, and the local typed threshold. Inspect the inherited extension trigger and attempt evidence at their owning parent depths; verify the newest export for both observer scripts, the complete expression alarm, both alarm callbacks, associated-data bindings, and all ten local members.

To change that nested alarm from Auto to Manual acknowledgement, replace the complete alarm-owning atomic member at the next layer. Restate its expression, data type, complete alarm object, associated-data bindings, delay, and complete callback array; add only locally owned acknowledgement evidence beside it. A verified layer left the outer Folder at 44, grew `CooldownControl` from 45 to 50, and exported `alarmActive`, `alarmCleared`, and `alarmAcked` exactly. Keep the inherited streak observers out of this portable payload and inspect them on their owning parent.

The same rule applies when a deep sibling analytics alarm changes from Auto to Manual. Replace only the complete `ValidationMismatchActive` member, including its relative expression, alarm and associated-data bindings, and all three callbacks; add the five acknowledgement evidence siblings without restating the inherited validation producer. The verified export retained 45 gate members and grew `ReviewAnalytics` from 20 to 25. An activation callback must reset occurrence-scoped UUID, actor, and timestamp fields but preserve the cumulative acknowledgement count.

To add bounded acknowledgement history at the next depth, replace the same complete alarm member only because `alarmAcked` gains the DataSet append. Add the typed DataSet, eviction counter, reset trigger, and capacity parameter; leave inherited scalar acknowledgement evidence as inherited siblings. The verified export retained 45 gate members and grew `ReviewAnalytics` from 25 to 28. Inspect the five inherited scalar tags on the direct parent and validate the complete local alarm, DataSet schema, reset event, and typed parameter on the newest layer.

To project the newest acknowledgement into a versioned Document, replace the complete alarm member and complete history-reset trigger, then add only the Document and typed schema-version parameter. Build the row and Document from one callback snapshot and write both together. The verified export retained 45 gate members and grew `ReviewAnalytics` from 28 to 29; the inherited DataSet and capacity remain owned by the direct parent.

A later layer can replace that same complete alarm member to make `alarmAcked` write a local DataSet while leaving its inherited scalar acknowledgement tags untouched. One verified payload added only the replacement member, a five-column DataSet, eviction counter, reset trigger, and typed capacity. The outer Folder remained at 44 and `CooldownControl` grew from 50 to 53. Validate inherited scalar tags at the parent depth and the complete alarm, DataSet schema, reset event, and local parameter at the newest depth.

The next layer can project the newest inherited acknowledgement row into one local Document without restating the DataSet. Replace the complete alarm-owning member because `alarmAcked` now writes both representations, replace the complete history reset trigger because it now clears both, and add only the Document plus its typed schema-version parameter. The verified export kept 44 outer members and grew `CooldownControl` from 53 to 54. Inspect the inherited five-column DataSet on the direct parent when the deeper export supplies only a stub; require the two complete local event arrays and complete RESET Document at the newest depth.

To add a separate lifecycle timeline, replace the complete alarm-owning member again and add only a six-column lifecycle DataSet, its eviction counter, reset trigger, and typed capacity. The verified layer kept 44 outer members and grew `CooldownControl` from 54 to 57. Its `alarmActive` and `alarmCleared` callbacks write only lifecycle evidence; its `alarmAcked` callback must retain the complete inherited acknowledgement-history/summary behavior while also appending the lifecycle transition. Validate the inherited acknowledgement DataSet, Document, and schema parameters on their owning parents rather than restating them in the portable payload.

The next layer can add one lifecycle-summary Document without restating the inherited lifecycle DataSet. Replace the complete alarm-owning member because all three callbacks now write the projection, replace the complete lifecycle reset trigger because it now resets both representations, and add only the Document plus its typed schema-version parameter. The verified layer retained 44 outer members and grew `CooldownControl` from 57 to 58. Validate the six-column DataSet and capacity at the direct parent, and require three complete callback bodies, the complete reset body, and complete RESET Document at the newest depth.

A deeper layer can change an inherited DataSet schema, but that schema change is a complete member replacement rather than an additive override. One verified payload replaced the lifecycle DataSet with a seven-column version whose leading `Sequence` column is `java.lang.Long`, added an Int8 memory sequence, and replaced the complete alarm-owning member, lifecycle reset trigger, and summary Document. It kept 44 outer members and grew `CooldownControl` from 58 to 59. Keep the inherited capacity and schema-version parameters at their owning parent depth; require all five locally owned members to export complete configuration at the newest depth.

To observe that inherited sequence history without replacing its alarm callbacks, replace only the complete lifecycle DataSet to add a `valueChanged` event, then add a derived integrity Document and its guarded reset trigger. One verified layer retained 44 outer members and grew `CooldownControl` from 59 to 61. The newest export owns the complete seven-column DataSet, observer body, Document, reset body, and typed integrity schema parameter; inspect the inherited alarm and lifecycle-reset callbacks on the direct parent. This keeps diagnostic projection ownership separate from alarm and acknowledgement ownership.

A deeper layer can replace one inherited producer Document solely to attach a consumer event while adding the consumer tags in a sibling Folder. Restate the complete Document default and the exact `valueChanged` body, but do not restate unrelated inherited members or parameters. From a member path ending in `CooldownControl/ExtensionLimitIntegrityReviewDistributionSummary`, derive the shared gate with `str(tagPath).rsplit('/', 2)[0]`, then append `/ReviewAnalytics`. Count path levels from the actual event member, not from the UDT type diagram. Require the sibling Folder's five typed tags by name because Ignition may canonicalize their export order.

When checking whether the direct parent owns an optional property such as `eventScripts`, inspect property existence explicitly. In PowerShell, a missing dynamic property can behave unexpectedly inside `@(...).Count`; use `$null -eq $object.PSObject.Properties['eventScripts']`. After importing the derived type, require the complete local override and exact event body on the new export, then exercise the effective inherited producer at runtime.

The next inheritance layer can extend that inherited sibling Folder without restating its five analytics members. One verified payload added only eight validation members to `ReviewAnalytics`, including one complete trigger with its event body. The effective export retained 45 gate members and 87 `CooldownControl` members while `ReviewAnalytics` grew from five to thirteen. Validate the five inherited analytics members and producer event at the direct parent depth; validate all eight local validation members and the exact trigger body at the newest depth.

Inside `ReviewAnalytics/ValidationTrigger`, derive the local Folder with `str(tagPath).rsplit('/', 1)[0]`, derive the shared gate by removing one more segment, then append the explicit sibling producer path. This reverse direction complements a producer script that writes into `ReviewAnalytics`: each script should own only its own output plane, and neither should rely on event-array write order.

The next layer can add an expression alarm beside that inherited validation plane without replacing the validation trigger. One verified payload added one complete expression/alarm member plus six callback-evidence tags, growing `ReviewAnalytics` from thirteen to twenty effective members while the gate and `CooldownControl` counts stayed 45 and 87. Inspect the inherited validation script on the direct parent; require the new expression, complete alarm binding, associated data, and both exact callbacks only at the newest depth.

To add monotonic identity to a bounded acknowledgement DataSet and latest-summary Document, replace the complete alarm member, DataSet, reset trigger, and Document, then add one `Int8` sequence. A DataSet schema change is a complete member replacement: prepend `Sequence` as `java.lang.Long`. One verified export retained 45 gate members and grew `ReviewAnalytics` from 29 to 30. Keep inherited capacity and schema-version parameters at their owning parents. Increment only in `alarmAcked`; clear history without writing the scalar, and publish the retained scalar in the RESET Document.

To observe that acknowledgement sequence without replacing proven alarm callbacks, replace only the complete six-column DataSet to attach `valueChanged`, then add an integrity Document, guarded integrity-reset trigger, and typed schema parameter. One verified export retained 45 gate members and grew `ReviewAnalytics` from 30 to 32. The observer must use `currentValue.value` as its committed DataSet snapshot, read scalar sequence and evictions as siblings, and write only the diagnostic Document. Keep the alarm, acknowledgement summary, and history reset inherited at their owning parent.

To consume that integrity projection without replacing its DataSet observer, replace only the complete integrity Document to attach `valueChanged`, then add a bounded incident DataSet, eviction/count/latch state, reset trigger, and typed capacity. One verified export retained 45 gate members and grew `ReviewAnalytics` from 32 to 37. Use the committed Document as the incident snapshot, correlate its observation milliseconds into a native Date, and keep every acknowledgement producer inherited.

To add a latest-incident projection, replace that complete integrity Document again because its consumer now writes both representations, replace the complete incident-history reset trigger because it now resets both, and add only the versioned incident-summary Document plus typed schema parameter. One verified export retained 45 gate members and grew `ReviewAnalytics` from 37 to 38. Build the appended row and Document from one committed integrity snapshot; validate inherited incident state at its owning parent.

A sequence-fenced review layer can remain small: replace only the complete integrity Document because the new-incident branch must clear review identity, then add thirteen typed review siblings including one trigger script. One verified export retained 45 gate members and grew `ReviewAnalytics` from 38 to 51. Keep incident history, summary, reset, and every alarm/acknowledgement producer inherited; review commands must never rewrite them.

To journal those review decisions, replace only the complete review trigger, then add a typed DataSet, eviction counter, reset trigger, and local capacity parameter. One verified export retained 45 gate members and grew `ReviewAnalytics` from 51 to 54. The replacement must preserve every inherited decision branch while appending accepted and denied outcomes; validate the accepted-review siblings and incident plane at their owning parent.

To add a latest-decision projection, replace the complete review trigger and complete history-reset trigger, then add only one Document and typed schema parameter. One verified export retained 45 gate members and grew `ReviewAnalytics` from 54 to 55. Build the row and Document from one captured command snapshot; keep the inherited DataSet/capacity/eviction definitions at their direct parent.

To add a review-decision distribution at the next inheritance layer, replace those same two complete scripts, add the nine-column DataSet and guarded distribution reset, and add only the typed schema parameter. Compute `RETAINED` from the surviving FIFO rows and `CUMULATIVE` from the five authoritative lifetime counters; never infer lifetime counts from bounded history. A distribution-only reset owns only that DataSet. A history reset must also reconstruct retained-zero/cumulative-preserved distribution rows. Validate locally authored identities/scripts on the derived export and inherited behavior at the owning parent or runtime.

To pair that distribution with a latest-summary Document, replace the complete command, history-reset, and distribution-reset scripts, then add only the Document and its typed schema parameter. Create the rows and summary from the same computed counts and Date. Distribution reset owns the DataSet/summary pair and publishes a complete zeroed RESET Document; history reset instead publishes retained-zero/cumulative-preserved rows plus a matching RECORDED summary. Keep review history, latest decision, scalar counters, and incident evidence inherited and independently owned.

To add a sibling consumer without editing proven producers, override only the committed summary tag to attach its complete `valueChanged` script and add a new sibling folder under their common parent. Resolve the parent with `str(tagPath).rsplit('/', 2)[0]`, then address the sibling folder explicitly. Keep all sibling values memory-backed and typed. Validate the source override and sibling identities locally; validate producer behavior at the inherited parent/runtime. Use the committed Document as the sole cross-folder contract instead of rereading its DataSet and counters independently.
