# Alarms and tag event scripts

## Contents

- [Alarms](#alarms)
- [Alarm modes](#alarm-modes)
- [Alarm deadband, delay, and evaluation](#alarm-deadband-delay-and-evaluation)
- [Property-specific parameterization](#property-specific-parameterization)
- [Acknowledgement and shelving lifecycle](#acknowledgement-and-shelving-lifecycle)
- [Instance alarm overrides](#instance-alarm-overrides)
- [Tag event scripts](#tag-event-scripts)

## Alarms

Alarms are an `alarms` array on the member tag:

```json
{
  "name": "PV",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "Float8",
  "value": 0.0,
  "alarms": [
    {
      "name": "HighPV",
      "mode": "AboveValue",
      "setpointA": 10.0,
      "priority": "High",
      "label": "High process value",
      "displayPath": "Area/Asset"
    }
  ]
}
```

On the verified target, these runtime paths read Good and agreed with configuration:

```text
<member>/Alarms/<alarm>.Enabled
<member>/Alarms/<alarm>.IsActive
<member>/Alarms/<alarm>.SetpointA
<member>/Alarms/<alarm>.Priority
<member>/Alarms/<alarm>.Label
<member>/Alarms/<alarm>.DisplayPath
```

A runtime write from PV 0 to 20 activated an `AboveValue` 10 alarm, and a write back to 0 cleared it. Separately verify history, notification pipelines, rollups, and restart persistence when the task depends on them. Use the guarded lifecycle actions in `api-contract.md` for acknowledgement and shelving when the target advertises them.

Use numeric JSON values or the proven alarm-expression object for setpoints. Do not use a numeric string. Keep alarm names free of `/` to avoid ambiguous display behavior. Establish label/display path/priority sources before activation and compare current event rows with runtime properties.

### Alarm modes

Use these exact JSON names:

| Behavior | `mode` | Required fields |
|---|---|---|
| equal / not equal | `Equality` / `Inequality` | numeric `setpointA` |
| above / below | `AboveValue` / `BelowValue` | numeric `setpointA`; optional Boolean `inclusiveA` |
| between / outside | `BetweenValues` / `OutsideValues` | numeric `setpointA`, `setpointB`; optional Boolean `inclusiveA`, `inclusiveB` |
| engineering range | `OutOfEngRange` | member `engLow` and `engHigh` |
| Boolean state | `WhenTrue` / `WhenFalse` | Boolean or numeric member |
| bit state | `Bit` | nonnegative integer `bitPosition`; optional Boolean `bitOnZero` |
| bad input quality | `BadQuality` | no setpoint |
| every value change | `AnyChange` | no setpoint; use `ackMode: "Manual"` when cleared events must remain queryable |
| free-form condition | `OnCondition` | Boolean or alarm-expression `activeCondition` |

On the verified 8.3.8 target, all modes above survived export and passed two clean runtime runs. Numeric modes matched values 0, 10, 15, 20, and 25 around 10/20 boundaries. Inclusive `BetweenValues` was active at both boundaries; non-inclusive `OutsideValues` was clear there. `Bit` at position 2 changed state between values 0 and 4, and `bitOnZero: true` inverted it. `OutOfEngRange` was clear at 50 and active at -1 and 101 for engineering limits 0..100. A missing Reference member read `Bad_NotFound` while its `BadQuality` alarm property read Good/true.

`AnyChange` never stayed active. Two controlled writes produced two distinct `ClearUnacked` status rows with unique event IDs. Verify this mode through bounded status results, not only `.IsActive`.

For `OnCondition`, use the alarm-property expression shape, which is distinct from UDT member parameter bindings:

```json
{
  "name": "Conditional",
  "mode": "OnCondition",
  "activeCondition": {
    "bindType": "Expression",
    "value": "{[.]Condition}"
  }
}
```

Capitalization and field names matter: use exact `bindType: "Expression"` and `value`. In two clean runs, changing the sibling Boolean changed both `.ActiveCondition` and `.IsActive` with Good quality. A plain string `"{[.]Condition}"` normalized to static `false`. Replacing `value` with `binding` normalized to an empty expression; both malformed forms remained Good/inactive and therefore require export comparison, not only quality checks.

The same exact binding rule applies to an alarm attached to a relative expression tag: lowercase `bindType: "expression"` is invalid even when the expression text is otherwise correct. Validate `activeCondition.bindType`, its `value`, the tag's own relative expression, associated-data bindings, and both callback bodies independently.

### Alarm deadband, delay, and evaluation

For deterministic hysteresis, use a concrete Absolute deadband:

```json
{
  "name": "High",
  "mode": "AboveValue",
  "setpointA": 10.0,
  "deadbandMode": "Absolute",
  "deadband": 2.0,
  "timeOnDelaySeconds": 0.6,
  "timeOffDelaySeconds": 0.6
}
```

In two clean 8.3.8 runs, the alarm activated at 11, remained active at 10, and cleared at exactly 8.0. A configured 0.6-second active or clear delay preserved the prior state immediately after the write and transitioned after about 1.03–1.05 seconds on the tested tag group. Treat delay values as minimum configuration, not an exact client sleep: poll the runtime state to a bounded deadline and preserve the observed elapsed time.

Do not generalize alarm `deadbandMode: "Percent"` on this build. Both `deadband: 10.0` and `0.1` persisted in export and read back Good/Percent, but once active neither alarm cleared at expected thresholds; the 10.0 case remained active even at -950.1 on a 0..100 engineering span. Prefer Absolute or require a clean target-specific activation/clear matrix before accepting Percent.

Use alarm-level `"enabled": false` to disable one alarm. Use member-level `"alarmEvalEnabled": false` to stop evaluation for all alarms on that member. In the verified run, both forms left `.IsActive` false at a value above the setpoint, while the second alarm's own `.Enabled` remained true. Read both properties when diagnosing an apparently inert alarm.

### Property-specific parameterization

Do not reuse the member-parameter binding object for alarm properties. Alarm expressions use:

```json
{
  "bindType": "Expression",
  "value": "{[.]SiblingTag}"
}
```

The verified 8.3.8 matrix produced these results:

| Alarm property shape | Runtime result |
|---|---|
| concrete numeric `setpointA` | supported |
| plain string `"{HighSP}"` for `setpointA` | silently coerced to `0.0`; parameter changes did not update it |
| `Expression`/`value` object for `setpointA` | supported; sibling setpoint changes updated `.SetpointA` and alarm state |
| `Expression`/`value` object for `enabled` | supported; sibling Boolean changes updated `.Enabled` and alarm state |
| `Expression`/`value` object for `activeCondition` | supported; drove `OnCondition` activation and clear |
| `Expression`/`value` object for `priority` and `label` | supported as event metadata; values were captured from source state when each new alarm event was created |
| literal-string expression object for `displayPath` | supported; returned the evaluated string with Good quality |
| member-style `bindType: "parameter"` / `binding` object on alarm properties | wrong schema; earlier imports could remove the alarm |
| `bindType: "Expression"` with `binding` instead of `value` | normalized to an empty expression and remained inactive |
| plain `"{AlarmPriority}"` | priority became null with Good property quality |
| plain `"{AlarmEnabled}"` | became `false`, regardless of the Boolean parameter |
| plain `"{Area}"` display path and `"{AlarmLabel}"` label | resolved correctly when the instance was created |

Setpoint, enabled, and active-condition bindings are continuously evaluated in the proven matrix. Priority and label are event attributes: establish their source values before triggering a new event, then verify the active event/runtime properties. Do not expect changing their source while no new event is created to rewrite an existing event. A label expression on the same Boolean that drove `activeCondition` captured the pre-transition value in both directions, so avoid coupling event metadata to the exact trigger edge unless that behavior is explicitly desired and tested.

Plain label/display-path parameter placeholders remained construction-time values in the earlier fixture: later parameter changes did not rewrite existing runtime metadata, while a newly created instance used the new values. Use concrete values or the exact `Expression`/`value` form according to the required lifecycle, and always export after import.

### Acknowledgement and shelving lifecycle

Use these exact alarm properties in UDT JSON:

```json
{
  "name": "High",
  "mode": "AboveValue",
  "setpointA": 10,
  "ackMode": "Manual",
  "ackNotesReqd": true,
  "shelvingAllowed": true
}
```

Valid acknowledgement modes are `Manual`, `Auto`, and `Unused`:

- `Manual` creates an unacknowledged event. A verified acknowledgement changed the event from ActiveUnacked to ActiveAcked.
- `Auto` was ActiveUnacked while the condition was active and became ClearAcked when the condition cleared.
- `Unused` was ActiveAcked while active; do not design a manual-ack workflow around it.

Set `ackNotesReqd: true` when the acknowledgement must carry a note. The guarded acknowledgement action requires a username and accepts a bounded note, but it does not read alarm configuration to reject an omitted or empty required note during planning. Supply a non-empty note proactively, dry-run first, and acknowledge the exact current event UUID, not an alarm name or tag path.

Do not confuse three different acknowledgement values:

- the `alarmAcked` callback argument `ackedBy` is the qualified actor, such as `usr:codex.actor.active`;
- `alarmEvent.getNotes()` returned the UDT alarm's configured `notes` value in the tested callback;
- Alarm Journal `ackNotes` retained the per-call note supplied to `system.alarm.acknowledge`, and only on the journal's `Ack` transition row.

Use `alarmEvent.getId()`, not nonexistent `getEventId()`, to correlate the callback with current status and Alarm Journal. On the verified 8.3.8 build, `unicode(alarmEvent.getLastEventState())` was `Ack`; overall callback state was `Active, Acknowledged` or `Cleared, Acknowledged`. A clear-before-ack event journaled `Active`, `Clear`, then `Ack`, with the final Ack row reporting both acknowledged and cleared true. Query `alarm-query-journal-v1` with the exact UUID, qualified prefix, named journal, and bounded lifecycle interval when this audit correlation is required.

### Alarm associated data

Custom associated-data properties are direct keys on the alarm object. Use a string for static data or the normal alarm Expression/value binding object for dynamic data:

```json
{
  "name": "RepeatedAreaDegradation",
  "mode": "OnCondition",
  "activeCondition": {
    "bindType": "Expression",
    "value": "{[.]RecurrenceLatched}"
  },
  "AreaCode": {
    "bindType": "Expression",
    "value": "{[.]AssociatedAreaCode}"
  },
  "Group": "Production"
}
```

For portable API querying, use identifier names of 1-64 characters (`AreaCode`, not a name containing spaces or punctuation). Read associated data inside `alarmActive`, `alarmCleared`, or `alarmAcked` with `alarmEvent.getOrElse('AreaCode', '')`; use the same exact property names in the journal query's `propertyNames` array. Although the manual describes associated data as strings, a direct Int4 Expression binding remained a JSON integer in the verified journal. Use `toStr(...)` in the alarm expression or `unicode(...)` in the callback when downstream consumers require a string contract.

The 8.3 manual describes a snapshot when the alarm becomes active. Live 8.3.8 build 2026071409 produced a narrower, version-specific result for dynamic bindings: the Active callback/journal row contained the value at activation, while later Ack and Clear callbacks/rows contained the binding value at those transitions under the same event UUID. Three two-instance runs reproduced this with no cross-instance leakage. Do not assume one activation-time value is immutable through later transitions on this build; test the intended lifecycle after upgrades and use a static property or an explicitly latched evidence tag when immutable context is required.

For immutable dynamic context, separate request values from alarm-bound values:

1. Put `RequestedAreaCode` and `LatchedAreaCode` under a nested evidence Folder.
2. Add a sequenced `ArmTrigger` memory tag whose indented `valueChanged` script reads the requested values, copies them into the latched tags, increments a `LatchedGeneration`, and writes an observable marker.
3. Wait for the marker, Good latched-value readback, and expected generation before allowing the alarm condition to become active.
4. Bind the alarm property to `{[.]ContextEvidence/LatchedAreaCode}`, never to the mutable requested tag.
5. Do not write the latched tags again while that alarm UUID remains current. Change request tags freely for the next occurrence.
6. Verify the exact value on Active, Ack, and Clear callbacks and journal rows, plus the bounded Gateway logs.

Three two-instance runs proved this pattern with both acknowledgement orders. Request values changed after Active, but all nine callback result tags and all three journal rows per UUID retained the armed values. Each run also proved the two instance generations and sources were independent. The ordering is part of the safety contract: arming after activation is too late for the Active event.

Guard the arm script as well. Before copying requested values, read the application alarm latch (for example `AreaRecurrenceEvidence/RecurrenceLatched`) plus `LatchedGeneration` and `ArmDeniedCount`. If the latch is true, increment the denial count, write `LastArmDecision = "DENIED-ACTIVE"`, emit an exact marker, and do not write any latched value. Only the false branch may copy request values and advance the context generation. This is a cooperative write fence, not an atomic compare-and-swap; keep one authoritative arm writer per instance.

After the generation-fenced alarm reset clears the latch, a later trigger may publish generation 2 for the next occurrence. Verify four things independently: the denied trigger did not change latched values, the allowed trigger incremented exactly once, the next alarm has a new UUID, and every journal row for each UUID contains its own generation's context. Three runs exercised two instances and two alarm occurrences each: four allowed arms, four active denials, four distinct UUIDs, twelve exact journal rows, and no context leakage per run.

Expose the context generation itself as associated data when consumers must correlate an alarm with the arm decision. A direct binding such as `{[.]ContextEvidence/LatchedGeneration}` preserved its Int4 type in Alarm Journal JSON on the tested build. A computed token can make the correlation human-readable:

```json
"ContextGeneration": {
  "bindType": "Expression",
  "value": "{[.]ContextEvidence/LatchedGeneration}"
},
"ContextToken": {
  "bindType": "Expression",
  "value": "concat({[.]ContextEvidence/LatchedAreaCode}, ':', toStr({[.]ContextEvidence/LatchedGeneration}))"
}
```

In callbacks, convert explicitly before writing String result tags: `unicode(alarmEvent.getOrElse('ContextGeneration', ''))`. Three runs proved generation 1 and 2 across separate UUIDs: journal generation was numeric, the computed token and callback result tags were strings, both acknowledgement orders correlated correctly, and an untouched ControlArea retained empty result tags.

Read the same context from the current alarm before acting on it by calling `alarm-query-status-v1` with exact qualified prefixes and `propertyNames`. Match the exact `EventId` and `Source`; do not select an alarm merely by label or array position. The returned item places requested properties under `data`, preserves numeric versus string JSON types, and returns absent requested properties as null. On the verified build, the same latched generation/token and UUID survived ActiveUnacked to ActiveAcked and ActiveUnacked to ClearUnacked to ClearAcked. A denied re-arm changed requested tags but not the current event's status context. Status is current-state evidence, so correlate the exact UUID with bounded `alarm-query-journal-v1` rows for transition history.

### Sequence-fenced branch scripts and partial writes

When an external operation may update several deep UDT branches, give each branch its own `ApplySequence`, `LastAppliedSequence`, `AppliedCount`, and `LastDecision`. Its `valueChanged` script should ignore initialization/null/zero, apply only when `sequence > LastAppliedSequence`, and explicitly record `REJECTED-STALE` otherwise. Derive the containing Folder with `str(tagPath).rsplit('/', 1)[0]`; read and write only explicit sibling paths.

This fence turns ambiguous transport recovery into state reconciliation: read each branch, identify which sequence actually committed, and send only the missing branch. It is not an atomic transaction or compare-and-swap. Keep one authoritative writer per branch or add a stronger ownership fence. Do not expect rewriting the same trigger value to execute the script, and do not expect sibling callbacks from one batch to run in request order. Require per-branch result tags and bounded exact-marker logs.

Alarm lifecycle callbacks may run during initial tag/instance creation. Do not assume every `alarmCleared` callback represents a prior application alarm. Check a retained generation, command sequence, or other context key for a meaningful nonzero value before emitting audit markers or changing business evidence. Treat `None` as possible during initialization even when the final tag reads Good.

For a DateTime memory tag, JSON configuration can use epoch milliseconds such as `0`. Runtime Jython should write a native Date, for example `system.date.fromMillis(0)`. A guarded HTTP write of numeric `0` can return Good and change the tag, yet strict API readback verification can still fail because the runtime serializes the native Date as a date string rather than the submitted JSON number. Verify the resulting instant semantically, or let the UDT callback perform the native Date reset and keep the external cleanup batch away from that representation boundary.

Set `shelvingAllowed: true` only where operators or automation may suppress the alarm temporarily. Shelving is addressed by exact alarm source, for example:

```text
prov:Provider:/tag:Approved Root/Pump-001/PV:/alm:High
```

In two clean runs, a shelved active alarm disappeared from status results with `includeShelved: false`, remained queryable with `includeShelved: true`, and appeared in the shelved-path query. The status dataset did not expose a portable `IsShelved` column; prove shelving by exact-source visibility plus `alarm-query-shelved-v1`. Explicit unshelve removed it. An alarm with `shelvingAllowed: false` rejected verification after the native shelve call, so require readback rather than trusting request acceptance.

Always unshelve sacrificial alarms in cleanup and restore their source values. Acknowledgement changes event state and is not reversible; use a newly created lab event for testing.

### Instance alarm overrides

An alarm object nested under an instance member can override setpoint, priority, enabled, label, and display path. Include `name` and `mode` explicitly when creating the override. In the verified fixture, an instance created with a partial override that omitted `mode` defaulted to `Equal`, so PV 20 did not activate its intended high alarm. A targeted `MergeOverwrite` repair adding `mode: "AboveValue"` restored activation.

A late `MergeOverwrite` changed setpoint 10 to 25 while PV was 20, updated runtime metadata immediately, and cleared the active alarm. Writing PV 30 then created a new active event with the new Diagnostic priority and display path. Query current status after overrides; do not infer event snapshots from configuration alone.

## Tag event scripts

The documented configuration shape is:

```json
"eventScripts": [
  {
    "eventid": "valueChanged",
    "script": "\tif not initialChange:\n\t\tparent = str(tagPath).rsplit('/', 1)[0]\n\t\tvalue = tag['parameters']['AssetName']\n"
  }
]
```

The `script` value is inserted inside a generated event function. Start every nonblank body line with indentation; a leading tab is the live-proven export/import form. An unindented body persisted and exported but never executed and emitted no bounded error, so local indentation validation is mandatory.

Compile the exact generated function body with the target Ignition Jython generation before import. Run `scripts/validate_jython_event_scripts.py` with an explicit Jython jar path after the structural payload validator. In live tests, an extra `)` in a list assignment persisted and exported exactly, every trigger write returned Good, the trigger tag stayed Good, and the bounded Gateway ERROR count was zero, but the handler never ran. The embedded Jython 2.7.4 compiler reported the precise mismatched-parenthesis line. Import success, export equality, Good source quality, and an empty ERROR query therefore cannot substitute for syntax compilation plus an observable execution marker.

Use these event IDs:

| Event | `eventid` | Additional fields |
|---|---|---|
| Value Changed | `valueChanged` | none |
| Quality Changed | `qualityChanged` | none |
| Qualified Value | `qualifiedValueChanged` | required nonempty `changeTypes` array |
| Alarm Active | `alarmActive` | none |
| Alarm Cleared | `alarmCleared` | none |
| Alarm Acknowledged | `alarmAcked` | none |

The Qualified Value event was added in Ignition 8.3.3. Its portable JSON form is:

```json
"eventScripts": [
  {
    "eventid": "qualifiedValueChanged",
    "changeTypes": ["VALUE", "QUALITY", "TIMESTAMP"],
    "script": "\tif not initialChange:\n\t\tparent = str(tagPath).rsplit('/', 1)[0]\n\t\tsystem.tag.writeBlocking([parent + '/LastChanged'], [unicode(changed)])\n"
  }
]
```

Choose one or more uppercase triggers: `VALUE`, `QUALITY`, or `TIMESTAMP`. The event object must contain a nonempty `changeTypes` array. On the verified 8.3.8 build, `qualifiedValueChanged` without triggers persisted and exported but never executed; the incorrect ID `qualifiedValue` behaved the same way. Do not infer validity from persistence.

Use the canonical array exactly. Lowercase and duplicate values normalized on import, an unknown enum caused the event to disappear on export, and a scalar string became a triggerless inert event despite a successful import envelope. The shipped validator rejects all of these forms before import.

`changed` is the set of aspects that actually changed, not merely the configured trigger subset. A value write reported `[VALUE, TIMESTAMP]`; a fixed-rate expression evaluation with an unchanged value reported `[TIMESTAMP]`; a reference transition through disabled quality reported `[VALUE, QUALITY, TIMESTAMP]`. Filter on membership if the script needs one specific cause. `previousValue` and `currentValue` remain qualified values with `.value`, `.quality`, and `.timestamp`; `initialChange` and `missedEvents` are also available.

For `qualityChanged`, controlled reference transitions proved `Good > Bad_Disabled > Good`. Quality-only scripts receive `tagPath`, `previousValue`, `currentValue`, `initialChange`, and `missedEvents`, but not `changed`.

Set optional `"enabled": false` on any event object to retain the script while preventing execution. `true` is the default and may be omitted from exports. Require a Boolean; do not use string values.

Treat `tagPath` as a Python string/unicode path. Do not call `tagPath.getParentPath()`; that produced `AttributeError: 'unicode' object has no attribute 'getParentPath'`, and the shipped validator rejects the call. To address a sibling from a member script, use `str(tagPath).rsplit('/', 1)[0]`, then append `'/Sibling'`. Read UDT parameters directly with `tag['parameters']['Name']` and explicit casts; do not invent a `.Parameters.Name` tag path when the event already supplies the parameter dictionary. Guard `initialChange` on value/quality events.

For calls from tag events into Project Library modules, including modules below package folders and calls made from nested UDT instances, follow `project-library-scripts.md`. A Gateway-scoped tag event needs a configured Gateway Scripting Project; successful project import alone does not provide that context.

Two clean 8.3.8 runs proved inherited UDT scripts after correcting those two details:

- `valueChanged` copied 7 into a sibling result tag;
- parameter access multiplied 7 by an instance parameter of 3 and wrote 21;
- `alarmActive`, `alarmAcked`, and `alarmCleared` each wrote the exact alarm name;
- the correlated logger recorded all five controlled paths;
- the wrong-path control produced the exact dispatcher `AttributeError` while its result remained unchanged;
- the unindented control remained Good at the source tag but never changed its result.

Two additional clean runs proved `qualityChanged`, all three Qualified Value trigger selections, event-level disable, and the following negatives:

- a `VALUE`-only event did not fire on an unchanged same-value memory write;
- a `TIMESTAMP`-only event fired from a fixed-rate expression update;
- an empty/missing `changeTypes` array remained inert;
- the wrong `qualifiedValue` ID remained inert;
- `enabled: false` remained inert;
- every controlled transition restored its source state and produced no Gateway error log.

An `alarmCleared` script also fired during instance initialization. Before a controlled alarm-event matrix, wait for initialization, reset every observable result marker, then activate, acknowledge, and clear in order. Match event IDs and bounded timestamps where available; do not count an initialization transition as the requested event.

Make success and failure externally observable through result/status/error tags plus a narrow correlated logger; never rely on a manual Script Console. Therefore:

- do not claim script runtime success from import/export;
- require a controlled source write and result-tag/timestamp evidence;
- capture a narrow Gateway log window;
- treat unchanged result tags as failure, even when the source write and source quality are Good;
- include at least one malformed control so logger/error behavior is characterized;
- revalidate after Gateway upgrades because tag scripts execute in a shared bounded thread pool.

When an event script dynamically fans out to child UDT triggers, never call `system.tag.writeBlocking([], [])`; branch around an empty selection. Inspect every returned quality for a nonempty dispatch, but treat those qualities only as write acceptance. Prove asynchronous child completion from correlated result tags or aggregate expressions after the handlers settle, and keep the bounded dedicated plus ERROR log checks around the full mutation/test/cleanup interval.

Do not reuse a trigger value for a `valueChanged` event. Writing the same value can return Good while producing no value transition and therefore no handler execution. Prefer a changing or monotonic request sequence, retain the last processed sequence in the consumer, and prove execution from the consumer's correlated result plus an exact logger marker.

Do not assume `qualifiedValueChanged` with `TIMESTAMP` rescues redundant memory writes. On the verified 8.3.8 memory provider, a same-value write returned Good/all-verified but retained the exact earlier QualifiedValue timestamp; the TIMESTAMP-qualified event did not run, its state remained unchanged, and the bounded ERROR query stayed empty. A TIMESTAMP trigger is appropriate only when the source actually produces new timestamps, such as a separately verified evaluation cycle. For command semantics, require a changing request identity and prove the exact request timestamp, handler marker, generated downstream sequence, and consumer result.

For a configurable consecutive-failure alarm, keep the counter and the expression alarm separate. Increment the counter only on denied branches, reset it only on the accepted branch, and bind the alarm to an expression such as `{[.]ConsecutiveDeniedRequestCount}>={DenialBurstThreshold}`. Publish the latest decision, request, and observed milliseconds as associated data. Retain the active UUID in a sibling tag and clear its latch only from the matching clear callback; this distinguishes a new burst occurrence from a continuing one.

`alarm-query-status-v1` returns the configured symbolic priority as a numeric runtime code on the verified 8.3.8 API (`Medium` exported from the UDT, `Priority: 2` in status). Prove the symbolic value from export and the numeric value from current status as separate contracts. Requested associated-data fields appear under `data`, retain their JSON types, and unrelated requested fields may be null.

When the burst requires manual acknowledgement, keep acknowledgement evidence occurrence-local. In `alarmActive`, latch the new event UUID and atomically reset `WasAcked`, `AckEventId`, and `AckedBy`; in `alarmAcked`, write the acknowledged UUID and qualified `ackedBy` actor. This prevents a prior occurrence's acknowledgement from making a new burst appear acknowledged.

Exercise both legal orderings. For clear-then-ack, require `ActiveUnacked` (2) to become `ClearUnacked` (0), acknowledge the retained UUID, and require `ClearAcked` (1). For ack-then-clear, require `ActiveUnacked` (2) to become `ActiveAcked` (3), then clear to `ClearAcked` (1) without changing the UUID or acknowledgement evidence. Acknowledge dry-runs must leave alarm state, evidence tags, callback count, and logs unchanged.

To impose a cooldown only after the same burst is both cleared and acknowledged, start it from whichever callback completes that pair. Increment a cooldown generation, publish the native DateTime deadline, matching Int8 epoch, and source event UUID first, then write `CooldownActive=true` separately as the final arm operation. Writing the arm in the same batch before the deadline can let a polling expression briefly observe the old epoch and dispatch an `EARLY` generation; that consumed request identity can prevent the real deadline from firing later.

Use a generation-valued due expression such as `if({[.]CooldownActive}&&now(250)>={[.]CooldownDeadlineAt},{[.]CooldownGeneration},0)`. Re-read active, generation, and epoch in the expiry handler. Reject an old requested generation as `STALE` without clearing the newer cooldown; expire only the exact current generation after its retained epoch. Keep cooldown denials in a separate counter/evidence plane so they do not rewrite authorization counters, denial streak, accepted/denied DataSets, or the denial summary.

### Manually triggered sibling validation probes

Use a small sibling probe when one Folder consumes a committed Document from another Folder and operators need an on-demand integrity check. Give the request an `Int4` trigger and retain `LastValidatedTrigger`; accept only positive values greater than the retained value. A repeated same value is a `valueChanged` no-op. A lower or re-armed duplicate must publish `DENIED-STALE` without changing the retained accepted trigger, snapshot, counts, or validation timestamp.

On an accepted request, read the committed Document, every consumer scalar, the last trigger, and both counters in one `system.tag.readBlocking` call and check every quality. Derive the expected consumer snapshot only from the committed Document, but retain the observed consumer values in the validation snapshot. This makes a deliberate perturbation visible instead of overwriting the evidence with expected values. Publish the accepted trigger, `MATCH` or `MISMATCH`, observed snapshot, counters, and one observed-at millisecond in a single checked write batch.

Test initial RESET match, same-value no-op, stale denial, deliberate one-scalar mismatch, repair through the real producer, post-repair match, reset match, and reconstruction where retained values are zero but cumulative values remain. Explicitly repair any deliberate perturbation during cleanup when the producer Document stayed RESET and therefore emitted no new event.

Do not call a broad inherited harness helper unless every global it closes over is declared in the focused scenario. The verified probe initially stopped because a review helper also inspected incident paths that the narrow harness had not defined. Drive the intended command tags directly or provide a self-contained helper, then assert producer result and consumer repair independently.

### Alarming a manual validation result

Drive the alarm from the committed validation decision, not directly from the producer or consumer values. A Boolean expression such as `{[.]ValidationState}="MISMATCH"` creates one occurrence after an accepted mismatching validation. A stale denial must not alarm, and repairing the underlying consumer must not clear the occurrence while the committed decision remains MISMATCH. Require a new accepted validation to publish MATCH and clear the same UUID.

Attach the accepted trigger, validation state, observed snapshot values, validation count, and mismatch count as alarm associated data. Verify the configured symbolic priority from UDT export and the runtime numeric priority from status separately. Query the exact alarm source and retain its UUID in an `alarmActive` callback. In `alarmCleared`, update lifecycle evidence only when an occurrence-local WasActive latch is true; alarm clear callbacks can occur during initialization.

Prove four independent surfaces: expression-tag state, current alarm status/UUID, callback evidence tags, and bounded logger markers. For auto-acknowledged alarms, the verified mismatch occurrence was ActiveUnacked while active and ClearAcked after MATCH. Do not infer callback success from alarm status alone.

For manual acknowledgement, test both legal orderings on distinct occurrences. Clear-then-ack must move `ActiveUnacked (2) -> ClearUnacked (0) -> ClearAcked (1)`. Ack-then-clear must move `ActiveUnacked (2) -> ActiveAcked (3) -> ClearAcked (1)`. Retain the same UUID within each ordering and require different UUIDs between occurrences.

Reset occurrence-local acknowledgement evidence in `alarmActive`: WasAcked false, empty acknowledgement UUID/actor, and zero acknowledgement time. Preserve only the cumulative acknowledgement count. This prevents a prior occurrence from satisfying the new one. An acknowledgement dry-run must leave status, evidence, timestamp, count, and alarm logs unchanged.

Submit a bare username such as `codex.udt.validation.operator` to `alarm-acknowledge-v1`; the verified API rejected an input already prefixed with `usr:` as `username_invalid`. Require the `alarmAcked` callback to publish the qualified actor `usr:codex.udt.validation.operator`.

Use a discriminating convergence barrier when two asynchronous Document versions share the same state and headline counter. In the verified history reconstruction, both old and new Documents were RECORDED with cumulative total one. Waiting on only those fields accepted the old retained values. Wait first on a consumer field that must change, then validate every source field and timestamp.

### Bounded acknowledgement history for a manual validation alarm

Append acknowledgement history only from `alarmAcked`; activation and clearing do not own the history. A compact verified schema is `AcknowledgementSequence` (Long), `EventId`, `AcknowledgedBy`, `AlarmPhase`, `WasCleared`, `ValidationTrigger` (Integer), `ValidationCount` (Long), `ValidationMismatchCount` (Long), and `AcknowledgedAt` (Date). Use the existing cumulative acknowledgement count as the row sequence when it already has identical ownership; do not create a redundant sequence tag.

Read the acknowledgement count, DataSet, and eviction counter together. Derive the qualified actor from `ackedBy`, phase from `alarmEvent.isCleared()`, and context from `alarmEvent.getOrElse(...)`. Create one native Date, use its milliseconds for the latest scalar evidence, append the Date itself to the row, delete index zero until `rowCount <= capacity`, and write scalar evidence, count, DataSet, and evictions in one checked batch.

Associated data reflects the event snapshot at acknowledgement time. For clear-then-ack, the verified row contained the clear transition's trigger and validation count, not the earlier activation values. For ack-then-clear, it contained the active mismatch context. Keep `AlarmPhase` plus `WasCleared` so consumers do not need to parse Ignition's display state text.

Make history reset independently owned: clear only the DataSet and eviction counter. Preserve the cumulative acknowledgement count, latest acknowledgement UUID/actor/time, alarm lifecycle counters, validation evidence, and producer state. After reset, the next acknowledgement must continue the old sequence. Test at least three acknowledgements at capacity two to prove oldest-first eviction, then reset and append a fourth row to prove sequence continuity.

Do not use a same-content producer RESET as a repair barrier. A committed Document that stays semantically RESET may not produce the consumer transition needed to overwrite a deliberate perturbation. Use a real producer command that changes authoritative evidence, wait for discriminating consumer fields, then issue a new monotonic validation trigger. Likewise, a distribution reset does not necessarily erase the producer subsystem's lifetime counters; assert retained and cumulative fields separately.

### Latest acknowledgement summary Document

Add a latest-summary Document only as a projection of the acknowledgement callback's committed row. Build the row and Document from the same local sequence, UUID, actor, phase, validation context, eviction count, and native Date. Write scalar acknowledgement evidence, bounded DataSet, eviction counter, and Document in one checked `system.tag.writeBlocking` batch. Do not re-read the DataSet afterward to reconstruct the Document; that introduces a second snapshot and avoidable race.

Use explicit `state` values such as `RESET` and `RECORDED`, a typed schema-version parameter, `retainedRows`, `evictions`, and every newest-row field. Store the native Date in the DataSet and its Int8 milliseconds in the Document. Verify field-for-field equality, newest-row Date equality, and identical DataSet/Document QualifiedValue timestamps after each owner write.

Replace the history reset callback so it clears the DataSet, zeroes evictions, and publishes a complete RESET Document in one batch. Preserve the cumulative acknowledgement count and latest scalar acknowledgement evidence; those are occurrence/lifetime planes, not bounded-projection state. A later acknowledgement must continue the old sequence while the new bounded window starts at one row.

Prove ownership with value and timestamp checks. Activation, alarm clearing, producer repair, accepted validation, and acknowledgement dry-run must not rewrite either complex tag. Only `alarmAcked` may publish RECORDED, and only the paired history reset may publish RESET. Test a quiet control instance independently.

### Read-only integrity for a DataSet/Document pair

Add a separate integrity Document when downstream agents must verify that a bounded DataSet and its latest-summary Document still represent one commit. Let the observer write only that integrity Document. Read the DataSet, summary, eviction scalar, and previous integrity value in one `system.tag.readBlocking` call; reject any bad quality before deriving a result.

Publish exactly three semantic states:

- `EMPTY`: zero DataSet rows plus a complete RESET summary with zero retained rows, evictions, identity, context, and time fields;
- `CONSISTENT`: a nonempty DataSet whose newest row matches every summary field, whose native Date equals the summary milliseconds, whose eviction values agree, and whose DataSet/summary QualifiedValue timestamps match;
- `MISMATCH`: any failed invariant, with deterministic reason codes and a cumulative mismatch count.

Do not require independently initialized empty memory tags to share a QualifiedValue timestamp. They can be semantically consistent without having been written in one batch. Require timestamp equality after RECORDED commits, and verify RESET timestamps separately when the paired reset is known to write both values together.

Attach the automatic observer to the summary `valueChanged` event so it runs only after the pair owner publishes the summary. Also provide a positive monotonic Int4 manual trigger for on-demand verification. Both paths may update the integrity Document, but neither may write the source DataSet, summary, eviction count, alarm evidence, or acknowledgement evidence. Prove this with before/after source values and timestamps.

To test MISMATCH without exposing a generic Document-write endpoint, derive a lab-only subtype that overrides the summary's initial value with a structurally valid but semantically impossible RECORDED projection while inheriting an empty history. Instantiate it under the same isolated run folder, fire the manual probe through the guarded scalar-write API, require MISMATCH and the expected reason codes, and confirm both malformed sources retained their exact timestamps. Keep a clean control instance and audit the dedicated observer loggers plus the bounded all-Gateway ERROR+ window.

### First-transition incidents from pair integrity

Add a separate incident plane when repeated integrity probes should not create duplicate operational records. Attach its consumer to the committed integrity Document, not directly to the DataSet/summary sources. Keep a Boolean latch, cumulative Int8 incident sequence, bounded DataSet, eviction counter, and guarded reset trigger.

When state first becomes `MISMATCH` while unlatched, build one row entirely from that committed integrity Document. A useful schema includes incident sequence, integrity check/mismatch counts, reason, history rows/evictions, summary state, latest/summary sequences, and a native `DetectedAt` derived from `checkedAtMillis`. Write history, evictions, latch, and cumulative sequence in one checked batch. While latched, log repeated MISMATCH checks as suppressed and do not rewrite the DataSet or its timestamp.

Clear only the latch when a later committed integrity state is `CONSISTENT` or `EMPTY`; do not clear incident history during re-arm. Reject unknown integrity states. Permit incident-history reset only while unlatched, clear only the DataSet and eviction counter, and preserve cumulative sequence so identity cannot be reused after reset.

A guarded scalar perturbation can safely test this complex flow when one scalar participates in the pair oracle. With a valid RECORDED pair, temporarily change the history-eviction scalar so it differs from the summary, fire a new manual integrity probe, and require one incident with `RECORDED_EVICTIONS`. Fire another probe without repair and require suppression plus an unchanged incident-history timestamp. Restore the scalar, fire another monotonic probe, require `CONSISTENT` and latch re-arm, then repeat across enough incidents to prove FIFO eviction. Finish by resetting incident history, creating one more incident, and proving cumulative sequence continuation. Keep a separate Control instance and include incident, integrity, source, and Gateway-wide ERROR+ logs in the bounded audit.

### Latest summary for pair-integrity incidents

Add a versioned latest-summary Document only as a projection of a newly recorded integrity-incident row. Build both from the same committed integrity Document fields and one native Date. Include `state`, schema version, retained rows, evictions, incident sequence, integrity check/mismatch counts, reason, source history rows/evictions, source summary state, latest/summary sequences, and detection milliseconds.

Write the bounded incident DataSet, eviction counter, latch, cumulative incident count, and latest summary in one checked batch. Require the newest row's Date to equal the summary milliseconds and require the DataSet/Document QualifiedValue timestamps to match. Do not reconstruct the summary by re-reading the DataSet after the owner write.

Repeated MISMATCH suppression must not rewrite the DataSet or Document. Healthy re-arm owns only the latch, so it must preserve both complex values and timestamps. A source acknowledgement-pair reset can update the integrity state to EMPTY but must not rewrite incident projections when the incident latch is already clear.

Replace the incident reset callback so it clears the DataSet, zeroes incident evictions, and publishes a complete RESET summary in one batch. Preserve the cumulative incident sequence. After reset, record another incident and require the next sequence rather than identity reuse. Test enough pre-reset incidents to exercise capacity eviction, verify the summary always follows the newest retained row, and keep a quiet Control instance plus bounded focused and Gateway-wide ERROR+ logs.
