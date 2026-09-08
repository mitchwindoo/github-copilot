# Nested UDT composition

Use this chapter when a UDT definition contains a child `UdtInstance` and the child must receive values dynamically from the owning parent UDT. This is different from placing ordinary tags inside a `Folder`: a nested `UdtInstance` has its own parameter dictionary, while a Folder does not.

## Build in dependency order

1. Import the leaf `UdtType`.
2. Import the parent `UdtType` containing a child `UdtInstance` whose relative `typeId` points to the leaf.
3. For deeper composition, import the next parent only after its child type exists.
4. Import concrete instances last.

Do not include a provider name or `_types_` in a nested child's `typeId`.

## Bind a parent parameter into a child

Use a typed instance-parameter wrapper. The outer object declares the child parameter type; its `value` contains the lowercase property-binding object:

```json
{
  "name": "ParentType",
  "tagType": "UdtType",
  "parameters": {
    "ParentName": {"dataType": "String", "value": "PARENT"},
    "ParentLimit": {"dataType": "Int4", "value": 20},
    "ParentOffset": {"dataType": "Int4", "value": 3}
  },
  "tags": [
    {
      "name": "BoundChild",
      "tagType": "UdtInstance",
      "typeId": "Equipment/LeafType",
      "parameters": {
        "Name": {
          "dataType": "String",
          "value": {"bindType": "parameter", "binding": "{ParentName}"}
        },
        "Limit": {
          "dataType": "Int4",
          "value": {"bindType": "parameter", "binding": "{ParentLimit}"}
        },
        "Offset": {
          "dataType": "Int4",
          "value": {"bindType": "parameter", "binding": "{ParentOffset}"}
        }
      }
    }
  ]
}
```

The tested Gateway normalized numeric parameter metadata from `Int4` to `Integer` on export and retained `String` for the explicitly typed name binding. Compare parameter types semantically across import/export rather than requiring the authored alias byte-for-byte.

## Why the outer type matters

This shorter form executed at runtime but is not the portable authored form:

```json
"Name": {"bindType": "parameter", "binding": "{ParentName}"}
```

The Gateway inferred `dataType: Integer` for that String child parameter on export even though its runtime value was a Unicode string. Always provide the outer `dataType`/`value` wrapper so exported metadata matches the intended parameter type.

This form is not a binding at all:

```json
"Limit": "{ParentLimit}"
```

It remained the literal Unicode value `{ParentLimit}`. An expression using that numeric parameter then read `Error_TypeConversion`. The validator rejects both the raw binding object and the plain-brace form.

## Multi-level propagation

Repeat the same typed wrapper at every nested `UdtInstance` boundary. A two-level Root → Parent → Leaf matrix propagated String and integer parameters through both boundaries. Changing only the concrete Root instance parameters updated:

- the nested Parent parameters;
- the nested Leaf parameters;
- an inherited Leaf expression using those parameters; and
- a Leaf tag-event script reading `tag['parameters']`.

The clean repeats produced these exact transitions:

- direct Parent → Leaf: `DIRECT|20|3|5` then `DIRECT-2|25|5|6`;
- Root → Parent → Leaf: `ROOT-I|30|4|5` then `ROOT-2|40|6|6`;
- Leaf calculation: 23 to 30 for the direct branch and 34 to 46 for the two-level branch.

## Script scope inside nested UDTs

A script on a Leaf member sees the Leaf's effective parameters through `tag['parameters']`, not the Root or intermediate Parent dictionary. Pass required context through typed bindings at each boundary. Folder path depth and nested UDT scope are separate concerns; read `project-library-scripts.md` when the event also calls Project Library code or navigates across member paths.

## Override a deeply inherited child

For a concrete Root instance, identify inherited nested instances by name. Omit `typeId` from these override stubs because they are not new child definitions:

```json
{
  "name": "Asset",
  "tagType": "UdtInstance",
  "typeId": "Equipment/RootType",
  "tags": [{
    "name": "Parent",
    "tagType": "UdtInstance",
    "tags": [{
      "name": "Leaf",
      "tagType": "UdtInstance",
      "parameters": {"Name": "INSTANCE-NAME", "Limit": 77},
      "tags": [{
        "name": "Probe",
        "tagType": "AtomicTag",
        "value": 5,
        "documentation": "Instance-specific probe",
        "eventScripts": [{
          "eventid": "valueChanged",
          "script": "\tif not initialChange:\n\t\tparent = str(tagPath).rsplit('/', 1)[0]\n\t\tsystem.tag.writeBlocking([parent + '/Marker'], [unicode(currentValue.value)])\n"
        }]
      }]
    }]
  }]
}
```

This omission is context-sensitive. A child `UdtInstance` declared inside a `UdtType` is a real nested definition and still requires its relative `typeId`.

Deep instance overrides take precedence over parent-to-child bindings. In the verified Root → Parent → Leaf matrix, overriding Leaf `Name` and `Limit` kept them fixed while the non-overridden `Offset` continued to propagate from Root. A later `MergeOverwrite` changed the same deep parameter, value, documentation, and event-script overrides without recreating the instance.

## Reset overrides deliberately

Do not treat `Overwrite` of the Root instance as a recursive reset. On the verified build, a minimal Root `Overwrite` reset Root parameters and their non-overridden propagation but retained deep Leaf parameter, documentation, and script overrides—even when the Root was wrapped in an overwritten Folder.

To guarantee a full reset, snapshot the exact instance, dry-run an exact guarded delete when that optional action is available, delete only that instance, then recreate a minimal instance through the official tag-import route. Verify inherited parameters, member configuration, script behavior, and Good quality after recreation.

Configuration updates are not an atomic script handoff. When one import changed both a member value and its `valueChanged` script, the old script ran once with the new value and new parameters before the new script became active. If that transition is unacceptable, stage the script/configuration change and the value change as separate operations, wait for export/readback between them, and trigger the value only after the new script is proven active.

## Override a nested member alarm

An inherited Leaf member alarm can use a propagated Leaf parameter through the alarm-property expression shape:

```json
"setpointA": {"bindType": "Expression", "value": "{AlarmLimit}"}
```

A concrete Root instance can override that alarm and the member's alarm-event scripts through the same named Parent → Leaf → member stubs:

```json
{
  "name": "Probe",
  "tagType": "AtomicTag",
  "alarms": [{
    "name": "High",
    "mode": "AboveValue",
    "setpointA": 50,
    "label": "Instance threshold"
  }],
  "eventScripts": [{
    "eventid": "alarmActive",
    "script": "\tparent = str(tagPath).rsplit('/', 1)[0]\n\tsystem.tag.writeBlocking([parent + '/ActiveMarker'], [unicode(alarmName)])\n"
  }]
}
```

The deep concrete alarm threshold takes precedence over the inherited parameter-driven threshold, while the Leaf's `AlarmLimit` parameter itself continues propagating. Verify both separately through `Parameters.AlarmLimit` and `Probe/Alarms/High.SetpointA` runtime-property reads.

On the verified build, raising a live deep threshold from 40 to 50 while Probe stayed at 45 cleared the alarm and invoked the newly imported `alarmCleared` handler. This does not generalize to simultaneous value-plus-`valueChanged` script changes, which showed an old-handler transition. Stage alarm configuration and process-value changes, export/read the new alarm and scripts, and query exact alarm sources before the next value transition.

Root `Overwrite` retained the deep threshold, label, and alarm-event scripts. Exact deletion plus minimal official recreation restored the parameter-driven threshold, base label, and inherited handlers.

## Coordinate sibling nested UDTs

A parent UDT can contain multiple instances of the same child type with distinct typed bindings. A parent expression can address child members relative to the parent:

```json
{
  "name": "Ready",
  "tagType": "AtomicTag",
  "valueSource": "expr",
  "dataType": "Boolean",
  "expression": "{[.]Motor/Status} && {[.]Valve/Status}"
}
```

The verified `CellType` used sibling `Motor` and `Valve` UdtInstances. Their names and peer names remained distinct per concrete Cell, and each Cell's Ready expression responded only to its own two children.

A script inside one child sees that child's effective parameters. To reach its sibling, compute the owning parent path explicitly from the event member path:

```python
	if not initialChange:
		device_root = str(tagPath).rsplit('/', 1)[0]
		cell_root = device_root.rsplit('/', 1)[0]
		peer_name = unicode(tag['parameters']['ExpectedPeer'])
		peer_path = cell_root + '/' + peer_name + '/Status'
		peer = system.tag.readBlocking([peer_path])[0]
		marker = unicode(tag['parameters']['DeviceName']) + '|' + peer_name + '|' + unicode(peer.value) + '|' + unicode(peer.quality)
		system.tag.writeBlocking([device_root + '/ScriptMarker', cell_root + '/CoordinationMarker'], [marker, marker])
```

Count path segments from the actual event member. For `Cell/Motor/Command`, remove `Command` to obtain the Motor root, then remove `Motor` to obtain the Cell root. Do not use `tagPath.getParentPath()`; `tagPath` was Unicode text in the verified 8.3 runtime. Include peer value and quality in an observable marker, and still verify the parent expression independently.

A concrete Motor Command-script override remained in effect after Root parameter propagation changed Motor and Cell names and after a minimal Root `Overwrite`. The Control Cell retained the inherited script, proving per-instance isolation.

## Fan a parent command out to child UDTs

A parent member script can address several fixed nested children in one `system.tag.writeBlocking` call:

```python
	if not initialChange:
		cell_root = str(tagPath).rsplit('/', 1)[0]
		paths = [cell_root + '/Feed/Command', cell_root + '/Process/Command', cell_root + '/Discharge/Command']
		qualities = system.tag.writeBlocking(paths, [currentValue.value, currentValue.value, currentValue.value])
		marker = 'FANOUT|' + unicode(tag['parameters']['CellName']) + '|' + unicode(currentValue.value) + '|' + ','.join([unicode(q) for q in qualities])
		system.tag.writeBlocking([cell_root + '/FanoutMarker'], [marker])
```

The event is on the parent, so `tag['parameters']` is the parent parameter dictionary. Each child's Command event separately sees that child's parameters. In the verified three-child fixture, child markers preserved distinct names and literal Sequence values 1, 2, and 3.

Aggregate child expressions can provide count and all-ready state:

```json
{
  "name": "AcknowledgedCount",
  "tagType": "AtomicTag",
  "valueSource": "expr",
  "dataType": "Int4",
  "expression": "if({[.]Feed/Acknowledged}, 1, 0) + if({[.]Process/Acknowledged}, 1, 0) + if({[.]Discharge/Acknowledged}, 1, 0)"
}
```

One parent fan-out reached count 3 and returned three Good write qualities. Do not call that transactional or atomic. Three sequential controlled child writes exposed count 1, then 2, then 3. Readers can observe intermediate aggregate state unless the application adds an explicit coordination protocol.

A concrete Process child-script override remained local to Process and survived parent-name propagation plus minimal Root `Overwrite`; Feed, Discharge, and the Control Cell retained inherited handlers.

## Add child command/feedback mismatch alarms

Keep mismatch state local to each child, and let the parent aggregate those child states. A Boolean child expression and its `OnCondition` alarm can use the same condition:

```json
{
  "name": "Mismatch",
  "tagType": "AtomicTag",
  "valueSource": "expr",
  "dataType": "Boolean",
  "expression": "{[.]Command} != {[.]Feedback}",
  "alarms": [{
    "name": "CommandFeedbackMismatch",
    "mode": "OnCondition",
    "activeCondition": {
      "bindType": "Expression",
      "value": "{[.]Command} != {[.]Feedback}"
    },
    "priority": "Medium"
  }]
}
```

Alarm-property expressions use `bindType: "Expression"` with a `value` field. Do not substitute the ordinary tag-binding `binding` field. Test both mismatch directions: Command true/Feedback false and Command false/Feedback true both satisfy inequality.

The verified three-child cell aggregated state with `MismatchCount` and `AnyMismatch`. Feedback changes removed exact child alarm sources in a 3 to 2 to 1 to 0 sequence, and reintroducing one mismatch restored only that child's source. Query the exact source paths; the aggregate count cannot identify the affected child.

Alarm-active and alarm-cleared scripts on the child's Mismatch member saw that child's effective `CellName`, `ActuatorName`, and `Sequence` parameters. Ignition also invoked inherited `alarmCleared` handlers during initial alarm evaluation, so reset marker tags after initialization and distinguish initialization callbacks from controlled transitions in bounded logs.

A concrete Process alarm/script override remained local, reported High priority, observed propagated Process names, and survived a minimal parent `Overwrite`. Feed, Discharge, and the Control instance retained inherited behavior. This proves current Boolean state, current alarm source/priority, and handler selection; it does not prove response time, alarm history, notification delivery, or physical feedback.

## Propagate an alarm inhibit separately from mismatch state

Give the child a Boolean `MismatchAlarmEnabled` parameter and bind the alarm's `enabled` property with the alarm-expression shape:

```json
"enabled": {
  "bindType": "Expression",
  "value": "{MismatchAlarmEnabled}"
}
```

Pass a parent `EnableMismatchAlarms` parameter into each child through the typed nested-parameter wrapper:

```json
"MismatchAlarmEnabled": {
  "dataType": "Boolean",
  "value": {
    "bindType": "parameter",
    "binding": "{EnableMismatchAlarms}"
  }
}
```

These are two different binding shapes. Alarm properties use `Expression` plus `value`; nested UDT parameters use lowercase `parameter` plus `binding` inside an explicit `dataType`/`value` wrapper.

In the verified three-child model, setting the parent enable parameter false changed all child enable parameters to false and removed all active alarm sources while every child Mismatch stayed true, MismatchCount stayed 3, and AnyMismatch stayed true. Alarm inhibition suppresses alarm evaluation; it does not repair or acknowledge the process mismatch.

Disabling the three active alarms did not invoke their `alarmCleared` scripts. Re-enabling them while the mismatches remained true invoked `alarmActive`. Do not infer callback semantics from source disappearance alone; reset markers, query exact sources, and observe both handlers.

A concrete Process `MismatchAlarmEnabled: false` override won over later parent false/true toggles, so only Feed and Discharge alarmed. A minimal parent `Overwrite` then removed this direct nested-child parameter override and restored Process to the inherited true binding. That reset is narrower than the separately proven retention of deeply nested alarm, script, and member overrides. Treat `Overwrite` behavior as override-shape-specific and export/read every effective descendant after it.

When a tag-event script applies `unicode()` to an effective Boolean UDT parameter in Jython 2.7.4, the verified marker text was `1` or `0`. The runtime tag-read API still returned native Boolean values. Use native reads for Boolean assertions and treat textual markers as Jython representations.

## Fan out only to participating children

For selective fan-out, read every child's effective participation parameter first, retain its quality, and build write paths only for Good/true children:

```python
	if not initialChange:
		root = str(tagPath).rsplit('/', 1)[0]
		names = ['Feed', 'Process', 'Discharge']
		read_paths = [root + '/' + name + '/Parameters.Participating' for name in names]
		states = system.tag.readBlocking(read_paths)
		selected = []
		for name, state in zip(names, states):
			if state.quality.isGood() and bool(state.value):
				selected.append(name)
		write_paths = [root + '/' + name + '/Command' for name in selected]
		if write_paths:
			qualities = system.tag.writeBlocking(write_paths, [currentValue.value] * len(write_paths))
		else:
			qualities = []
```

Branch explicitly for zero selection; do not call `system.tag.writeBlocking([], [])`. Include every participation value/quality, selected child name, and returned write quality in an observable marker.

The verified all/2/1/0 masks wrote exactly the selected children. A skipped child retained its existing Command; selection did not force excluded children false. A direct write to an excluded child still ran that child's Command script, but parent participating aggregates ignored its acknowledgement while its participation remained false.

Author zero-participant aggregate semantics explicitly. The verified expression treated acknowledgement as an implication for each child:

```text
(!Participating || Acknowledged) && ...
```

Therefore `AllParticipatingAcknowledged` was true with zero participants, while both counts were zero. This is a chosen vacuous-truth rule, not an Ignition default.

A direct Process `Participating: true` override won over the parent false binding and survived parent-name propagation. Minimal parent `Overwrite` removed that direct child parameter override and restored the inherited false mask, matching the direct alarm-enable parameter result. Continue to distinguish direct child parameter overrides from deeper alarm/script/member overrides that were retained in other tested shapes.

Controlled tag-write readback does not prove the associated tag-event script has completed. One discovery sequence wrote BroadcastCommand false and immediately imported new participation parameters; the still-running event read the new Process flag and selected a different child. Wait for an exact FanoutMarker or other completion marker before applying configuration that the event reads.

## Add a child permissive to selective fan-out

Participation answers whether a child belongs in the operation. A separate child `Permissive` member answers whether a participating child may receive the current command. Batch-read both full paths, keep their qualities, and classify every child as selected, blocked participating, or excluded:

```python
	if not initialChange:
		root = str(tagPath).rsplit('/', 1)[0]
		names = ['Feed', 'Process', 'Discharge']
		paths = []
		for name in names:
			paths.extend([root + '/' + name + '/Parameters.Participating', root + '/' + name + '/Permissive'])
		values = system.tag.readBlocking(paths)
		selected, blocked, excluded = [], [], []
		for index, name in enumerate(names):
			participating = values[index * 2]
			permissive = values[index * 2 + 1]
			if not participating.quality.isGood() or not bool(participating.value):
				excluded.append(name)
			elif not permissive.quality.isGood() or not bool(permissive.value):
				blocked.append(name)
			else:
				selected.append(name)
		write_paths = [root + '/' + name + '/Command' for name in selected]
		if write_paths:
			qualities = system.tag.writeBlocking(write_paths, [currentValue.value] * len(write_paths))
		else:
			qualities = []
```

This event is on the parent, so it uses full child-relative paths. Each child's Command event separately derives its child root with `str(tagPath).rsplit('/', 1)[0]`, reads its own `Permissive`, and sees its own effective child parameters through `tag['parameters']`. Verify both levels with exact parent route and child markers plus bounded logs.

The tested zero-eligible branch skipped child writes and retained every child state. `AllEligibleAcknowledged` was deliberately authored as an implication and therefore returned true when no child was eligible. That is application policy, not built-in Ignition behavior.

Changing a child's Permissive false to true while BroadcastCommand remained true did not replay the parent tag event. Eligibility aggregates changed, but the child Command, acknowledgement, child marker, and parent route marker stayed unchanged until an explicit Broadcast false/true transition. If permissive recovery must issue a command, author and test a separate trigger; do not assume replay.

Jython marker text distinguished the two Boolean sources: effective Boolean UDT parameters rendered as `1`/`0`, while Boolean memory-tag values rendered as `True`/`False`. Native API reads returned Booleans for both. Assert behavior with native values and treat marker strings as representation evidence.

In the tested concrete instance, parent `Overwrite` removed a direct Process participation parameter override but retained Process's concrete Permissive memory value. This contrasts two property shapes inside the same child. Export and read every effective descendant after collision-policy operations; do not claim that Overwrite uniformly clears nested state or overrides.

## Correlate deliberate dispatch attempts

When command state can remain true or false across several attempts, separate the desired Boolean from an increasing dispatch sequence. Put the event on `DispatchSequence`, read `RequestedCommand`, and compare the new sequence to a parent `LastAcceptedSequence` before routing:

```python
	if not initialChange:
		root = str(tagPath).rsplit('/', 1)[0]
		control = system.tag.readBlocking([root + '/LastAcceptedSequence', root + '/RequestedCommand'])
		last = control[0]
		requested = control[1]
		if not last.quality.isGood() or not requested.quality.isGood():
			# Record a control-quality rejection; write no child.
			pass
		elif int(currentValue.value) <= int(last.value):
			# Record a stale rejection; write no child.
			pass
		else:
			# Classify participation/permissive state as in the prior section.
			# For every selected child, write RequestedCommand first and AttemptSequence second.
			pass
```

On each child, put the event on `AttemptSequence`. Read that child's `RequestedCommand`, apply it to `Command`, and write `AcknowledgedSequence`, `AcknowledgedCommand`, and an exact child marker. The parent can count eligible children whose acknowledgement sequence equals `LastAcceptedSequence`.

This pattern made retry explicit. A blocked Process retained Command true and acknowledgement sequence 1 while the parent accepted sequence 2 for Feed and Discharge. Changing Process Permissive true did not replay anything and made the latest-ack aggregate false. Dispatch sequence 3 deliberately retried Process and brought every eligible child to sequence 3.

Writing sequence 3 again did not invoke `valueChanged`, produce a marker, or add a log because the tag value did not change. Changing it to stale sequence 2 did invoke the event; application logic rejected it, kept LastAcceptedSequence 3, and wrote no child. Do not use same-value writes as a retry mechanism.

The zero-eligible sequence was accepted as a new attempt, advanced LastAcceptedSequence, skipped child writes, and retained child state. Its all-eligible-acknowledged expression returned true because that rule was authored as an implication. Decide whether a zero-recipient attempt should be accepted or rejected in your application and test that policy explicitly.

Treat this as bounded application correlation, not a durable queue, transaction, exactly-once protocol, or safety mechanism. Sequence wraparound, restart persistence, redundancy, and concurrent writers need separate designs and evidence.

Finally, distinguish two completion barriers. Exact acknowledgement/route marker reads prove the scripted tag outputs are visible. They do not prove that a `getLogger().info(...)` call placed later in the same event has reached the log query. Before asserting that a later action produced no new log, first wait for the earlier exact log messages and a stable dedicated-log count.

## Keep bypass visible and reason-bearing

Model bypass separately from permissive. A participating child is effectively eligible when its permissive is true or bypass is active with a valid reason. In the tested child, reason presence was an expression member:

```json
{
  "name": "BypassReasonValid",
  "tagType": "AtomicTag",
  "valueSource": "expr",
  "dataType": "Boolean",
  "expression": "!{[.]Bypass} || len(trim({[.]BypassReason})) > 0"
}
```

The expression produced Good quality for empty and nonempty String memory values. With Process nonpermissive, active bypass plus an empty reason asserted attention and invalid counts but did not make Process eligible. Setting reason `WO-42` made it eligible; this is only presence validation, not proof of identity, approval, expiry, audit, or work-order validity.

Keep a separate parent `BypassAttentionCount` based on participating children with active Bypass. Do not derive attention only from `!Permissive && Bypass`. In the verified model, Process became permissive again while bypass stayed active; effective operation was healthy, but bypass attention correctly remained one. The next dispatch marker still listed Process as bypassed, making an unnecessary active bypass visible.

Classify routing explicitly:

- Excluded: participation is not Good/true.
- Selected normally: participation and permissive are Good/true.
- Selected through bypass: participation is true, permissive is false, and Bypass plus BypassReasonValid are Good/true.
- Invalid bypass: bypass is true but its reason-valid value is not Good/true; list the child as both blocked and invalid.

Include selected, bypassed, invalid, blocked, and excluded lists in the parent marker. Include Permissive, Bypass, BypassReason, RequestedCommand, and their qualities in the child acknowledgement marker.

Changing Bypass, BypassReason, or Permissive did not replay the sequence-driven command. Adding `WO-42` changed eligibility and made the parent latest-ack aggregate false because Process still held an older sequence. A later explicit DispatchSequence routed Process. Clearing bypass likewise removed attention without replay; the next sequence used normal permissive routing.

This is application-level routing and visibility, not a safety-rated bypass or authorization system. A blocked or excluded child retained its prior command/sequence state. If the application requires forced-safe action, approvals, expiry, or durable audit, design and test those separately.

## Record bypass evidence in a child Folder

Keep two counters when their meanings matter:

- `ActiveDispatchCount`: increment whenever a selected dispatch occurs while Bypass is active.
- `RequiredDispatchCount`: increment only when Permissive is false and a valid bypass is what makes the child eligible.

An active bypass is not necessarily required. In the verified model, a nonpermissive Process dispatch produced active 1/required 1. After permissive recovered while bypass remained active, the next dispatch produced active 2/required 1. `EverRequired` stayed true and `LastRequiredSequence` stayed on the actual required-bypass attempt.

Store these members under a child Folder such as `BypassEvidence` when grouping improves paths and maintenance. A child root AttemptSequence script can read and write Folder members explicitly:

```python
	root = str(tagPath).rsplit('/', 1)[0]
	active_path = root + '/BypassEvidence/ActiveDispatchCount'
	required_path = root + '/BypassEvidence/RequiredDispatchCount'
```

Do not reset evidence implicitly when bypass clears or a normal command arrives. The tested normal dispatch retained all evidence until an explicit reset.

A reset event located inside the Folder still sees the owning child UDT parameters. Resolve both scopes from the actual event path:

```python
	if not initialChange:
		folder_root = str(tagPath).rsplit('/', 1)[0]
		child_root = folder_root.rsplit('/', 1)[0]
		marker = 'RESET|' + unicode(tag['parameters']['CellName']) + '|' + unicode(tag['parameters']['ActuatorName'])
		system.tag.writeBlocking([
			folder_root + '/ActiveDispatchCount',
			folder_root + '/RequiredDispatchCount',
			folder_root + '/EverRequired',
			folder_root + '/LastRequiredSequence',
			child_root + '/EvidenceResetMarker'
		], [0, 0, False, 0, marker])
```

For `Child/BypassEvidence/ResetSequence`, remove `ResetSequence` to get the Folder root, then remove `BypassEvidence` to get the child root. Treat `tagPath` as text; do not call `tagPath.getParentPath()`.

A parent reset event can invoke fixed nested Folder scripts in one call:

```python
	root = str(tagPath).rsplit('/', 1)[0]
	paths = [root + '/' + name + '/BypassEvidence/ResetSequence' for name in ['Feed', 'Process', 'Discharge']]
	qualities = system.tag.writeBlocking(paths, [currentValue.value] * len(paths))
```

Verify the parent write qualities, every child Folder reset marker, the parent aggregates, and a separate Control instance. In the tested model, direct Process reset affected only Process evidence; the later parent reset invoked Feed, Process, and Discharge Folder scripts and reduced all parent totals to zero.

These memory counters are application diagnostics, not durable audit or historian records. Their read-modify-write behavior is not proven safe with concurrent dispatch writers. Use a durable, concurrency-aware design when evidence must survive restart or support compliance.

## Capture ordered interlock diagnostics and first-out

For a child with several permissives, keep the current active reasons separate from retained first-out evidence. The tested child evaluated `SafetyOK`, `ProcessOK`, then `MaintenanceOK` in that authored order. Its sequenced event read every QualifiedValue, treated bad quality as a named diagnostic reason, and produced an ordered comma-separated String such as `SafetyOK,ProcessOK`.

Use explicit decision states instead of one combined Boolean:

- `ACCEPT`: no active reasons and bypass inactive.
- `ACCEPT-BYPASS-ACTIVE`: no active reasons but bypass still active; retain this visibility.
- `BLOCK`: one or more reasons and no bypass.
- `BLOCK-INVALID-BYPASS`: reasons exist, bypass is active, but its reason is empty or bad quality.
- `BYPASS`: reasons exist and a Good/true bypass has a nonempty Good-quality reason.

On BLOCK or BLOCK-INVALID-BYPASS, increment BlockedDecisionCount and set FirstOutReason only when it is empty. On BYPASS, increment RequiredBypassDecisionCount, keep the current reasons visible, and do not overwrite FirstOutReason. On healthy recovery, set ActiveReasons to `<none>` but retain the historical counters and first-out until explicit reset.

The child event can preserve deterministic cause order with ordinary Jython 2.7 code:

```python
	values = system.tag.readBlocking([
		root + '/SafetyOK', root + '/ProcessOK', root + '/MaintenanceOK'
	])
	reasons = []
	for label, value in [('SafetyOK', values[0]), ('ProcessOK', values[1]), ('MaintenanceOK', values[2])]:
		if not value.quality.isGood():
			reasons.append(label + ':BadQuality')
		elif not bool(value.value):
			reasons.append(label)
	active_text = ','.join(reasons) if reasons else '<none>'
```

This order is an application diagnostic convention, not an Ignition scheduling guarantee or a safety-system first-out record. Test the chosen order explicitly.

Place LastDecision, ActiveReasons, BlockedDecisionCount, RequiredBypassDecisionCount, FirstOutReason, and ResetSequence under a child `DecisionEvidence` Folder. Use the two-segment string path pattern from the preceding section in the Folder reset event. A parent can fan an increasing evaluation sequence to each child, aggregate command and evidence counts with expressions, and fan a reset sequence to every child's Folder member.

The verified matrix covered one and two simultaneous failures, invalid and valid bypass, healthy recovery with bypass still active, direct child reset, mixed child outcomes, and parent reset-all. It also proved that changing only the bypass reason did not replay the sequence event. Require an explicit later sequence change.

Memory values remain application diagnostics: they are not restart-persistent audit, safety logic, authorization, or concurrency-safe counters. If command-off behavior should ignore run permissives, author and test that policy separately; the verified matrix deliberately evaluated a requested true command.

## Gate acknowledgement and reset by live trip state

Do not model acknowledge and reset as interchangeable writes. Keep separate child Folder event members such as `AcknowledgeSequence` and `ResetSequence`, and expose an explicit lifecycle state:

- `NORMAL`: no active reason and no first-out latch.
- `ACTIVE-UNACK`: an interlock is active and its first-out is not acknowledged.
- `ACTIVE-ACK`: an active trip has been acknowledged.
- `CLEARED-UNACK`: inputs recovered but retained evidence is not acknowledged.
- `CLEARED-ACK`: inputs recovered and retained evidence is acknowledged, so reset may clear it.

On each acknowledge or reset event, read the live interlock QualifiedValues again. Do not trust a prior ActiveReasons marker as the reset gate. In the tested reset policy:

- Return `DENIED-ACTIVE` and increment ResetDeniedCount when any live interlock is false or bad quality.
- Return `DENIED-UNACK` and increment ResetDeniedCount when inputs are clear but FirstOutReason is not acknowledged.
- Return `CLEARED`, increment ResetSuccessCount, and clear FirstOutReason/Acknowledged only when inputs are clear and the latch is acknowledged.
- Return `NO-EVIDENCE` without changing counters when no first-out is latched.

Acknowledgement may occur while active or after the inputs clear. It changes ACTIVE-UNACK to ACTIVE-ACK or CLEARED-UNACK to CLEARED-ACK. It does not clear the first-out by itself.

The Folder event still needs both the Folder and child roots:

```python
	if not initialChange:
		folder_root = str(tagPath).rsplit('/', 1)[0]
		child_root = folder_root.rsplit('/', 1)[0]
		values = system.tag.readBlocking([
			child_root + '/SafetyOK',
			child_root + '/ProcessOK',
			child_root + '/MaintenanceOK',
			folder_root + '/FirstOutReason',
			folder_root + '/Acknowledged'
		])
```

A parent can fan acknowledgement or reset sequences to each fixed child Folder member, but returned Good write qualities prove only that those event tags accepted the writes. They do not prove every business action succeeded. In the verified mixed reset, the parent received three Good qualities while Feed returned DENIED-ACTIVE, Process returned CLEARED, and Discharge returned NO-EVIDENCE. Read every child result marker/state and then verify aggregates.

After Feed cleared, a parent acknowledge-all produced one ACKNOWLEDGED and two NO-EVIDENCE outcomes. A later reset-all cleared Feed. The retained denial/success counters provided useful application diagnostics, but remain memory values: they are not durable audit, user identity, authorization, restart persistence, concurrency safety, or safety-rated trip records.

## Expire a bypass without another write

Use a scalar DateTime member and a polling expression when effective bypass must become false after a deadline even if no tag is written at that moment. Author the DateTime as an epoch-millisecond integer; see `complex-values.md` for the verified import/export and generic-read representations.

The tested child expression was:

```json
{
  "name": "BypassEffective",
  "tagType": "AtomicTag",
  "valueSource": "expr",
  "dataType": "Boolean",
  "expression": "{[.]Bypass} && len(trim({[.]BypassReason})) > 0 && now(250) < {[.]BypassExpiresAt}"
}
```

Attach a `valueChanged` script to BypassEffective and ignore `initialChange`. On each real transition, reread Bypass, BypassReason, and BypassExpiresAt with quality checks. Convert the Java Date explicitly:

```python
	expires_millis = system.date.toMillis(expires.value)
	now_millis = system.date.toMillis(system.date.now())
```

Classify false transitions in priority order:

- `CLEARED` when Bypass itself is false.
- `INVALID-REASON` when Bypass is active but the reason is empty or bad quality.
- `EXPIRED` when the reason is valid and current time is at or beyond ExpiresAt.
- A separately visible fallback such as `INACTIVE-OTHER` for any remaining condition.

Classify true transitions as `ACTIVE`. Keep separate activation, expiration, manual-clear, and invalid-reason counters under an `ExpiryEvidence` Folder. Record ObservedExpiryMillis and an exact marker so the typed deadline can be verified through the generic API.

In three verified runs, setting a future expiry while bypass was false emitted no transition. Bypass true with an empty reason also stayed false without a valueChanged event because the expression value did not change. Adding a reason made it ACTIVE. With no subsequent write, it became EXPIRED 193 ms, 201 ms, and 187 ms after the configured epoch. Treat those as observations compatible with `now(250)`, not a deterministic scheduling guarantee.

Importing a later expiry while Bypass and its reason remained set reactivated the expression. Clearing Bypass before that later deadline produced CLEARED without increasing the expiration count. Removing only the reason produced INVALID-REASON; restoring it reactivated the bypass while the deadline remained future.

Use official `MergeOverwrite` for the tested nested DateTime override shape and re-export the concrete instance. The current guarded scalar writer accepts JSON primitives but cannot exactly verify a Java Date against the submitted integer, so do not call that write path proven for DateTime. No API change was needed for the tested workflow.

This is Gateway application timing, not safety-rated bypass enforcement, authorization, durable audit, or exact real-time scheduling. Test clock changes, restart/redundancy, expiry renewal permissions, concurrent writers, and display time zones separately when required.

## Issue a bounded bypass lease from a child event

Prefer a sequenced request event when callers should supply a reason and duration rather than write BypassEnabled or ExpiresAt directly. The tested child exposed LeaseRequested, LeaseReason, RequestedDurationSeconds, and RequestSequence. It read a typed MaxDurationSeconds child parameter inside the event:

```python
	max_duration = int(tag['parameters']['MaxDurationSeconds'])
```

Author numeric parameter values as JSON numbers, not numeric strings. The customer validator now checks String, Boolean, integer, and finite-float UDT parameter literals in both definitions and typed instance wrappers.

Use explicit decisions:

- `DENIED-REASON`: requested true but trimmed reason is empty or bad quality.
- `DENIED-DURATION`: requested duration is zero, negative, or bad quality.
- `DENIED-MAX`: duration exceeds the effective MaxDurationSeconds parameter.
- `GRANTED`: validation passes and no lease is currently effective.
- `RENEWED`: validation passes while a lease is already effective.
- `CANCELED`: LeaseRequested is false; clear BypassEnabled.

For GRANTED or RENEWED, create the typed Date in Gateway scope and retain the exact epoch separately:

```python
	expires = system.date.addSeconds(system.date.now(), duration_value)
	expires_millis = system.date.toMillis(expires)
	system.tag.writeBlocking(
		[root + '/BypassEnabled', root + '/BypassExpiresAt', root + '/LeaseEvidence/LeaseExpiryMillis'],
		[True, expires, expires_millis]
	)
```

Keep request evidence separate from BypassEffective transition evidence. A renewal changes ExpiresAt while the Boolean remains true, so it does not invoke the effective member's `valueChanged` event. Verify RENEWED through the sequenced request marker, a later epoch, official export, and continued effectiveness across the original deadline.

In three runs, renewal extended the original deadline by 2.338–2.374 seconds. After waiting 500 ms beyond the original deadline, the lease was still effective with activation count 1, expiration count 0, and no new transition log. It later expired 105–156 ms after the renewed deadline and the transition handler cleared BypassEnabled.

After expiration, another valid request was GRANTED rather than RENEWED and produced a second ACTIVE transition. A later LeaseRequested false request produced CANCELED plus one CLEARED transition. Final verified Process counts were granted 3, denied 3, canceled 1, activation 2, expiration 1, and manual clear 1; sibling and Control counts stayed zero.

These short durations and observed delays are laboratory evidence, not production recommendations or deadlines. Nonempty reason and maximum duration are application validation—not user identity, permission, approval, safety enforcement, or durable audit. Test cumulative-duration limits, ownership, revoke permissions, concurrency, restart/redundancy, and clock changes separately.

## Fan a lease request from the parent and correlate child completion

A parent event may fan LeaseRequested, LeaseReason, RequestedDurationSeconds, and a shared RequestAllSequence into fixed members such as Feed, Process, and Discharge. Keep each child's validation in the child UDT. The parent coordinates; it does not replace child policy.

Bind each child's typed maximum through a parent parameter at the UdtInstance boundary:

```json
"MaxDurationSeconds": {
  "dataType": "Int4",
  "value": {"bindType": "parameter", "binding": "{ProcessMaxDuration}"}
}
```

In the parent event, build nonempty paths/values arrays, call one writeBlocking, retain every returned quality, and record the parent sequence. Then wait for every child's LastProcessedSequence to equal the parent sequence. Read each LastDecision separately; Good write qualities prove delivery to the child input tags, not GRANTED business outcomes.

The verified first fanout returned twelve Good qualities while Feed and Discharge returned GRANTED and Process returned DENIED-MAX. After ProcessMaxDuration propagated from 3 to 30, its existing denial did not replay or change: the sequence, child marker, completion aggregate, lease state, and dedicated log count stayed fixed. A later RequestAllSequence was required. That explicit retry returned Feed/Discharge RENEWED and Process GRANTED.

For current-sequence aggregates, combine sequence equality with one-hot Boolean evidence retained by each child, for example LastGranted, LastRenewed, LastDenied, and LastCanceled. This avoids treating cumulative counters as the result of the current request. A processed count of three plus outcome counts totaling three is an application-level completion barrier; it is not an atomic transaction, queue, durable workflow, or exactly-once guarantee.

Renewing an already effective child updates its expiry but does not call the BypassEffective valueChanged handler when the Boolean remains true. Verify the child request marker and later epoch independently from activation-transition evidence.

Always start a bounded Gateway log window before importing or changing the UDT, settle the exact parent and child markers, and query both the dedicated logger and ERROR-or-higher rows over the same bounds. The verified matrix produced three parent FANOUT rows, nine child REQUEST rows, six child LEASE transition rows, and zero ERROR-or-higher rows in each of three runs. Restore parameter changes and controlled memory state only after a cleanup sequence has completed; keep guarded write batches within the API's advertised limit.

The maximum duration, reason, sequence, and counters remain application policy/evidence. They do not establish caller identity, authorization, approval, restart persistence, concurrency safety, durable audit, or safety enforcement.

## Correlate a lease holder with an expected generation

Add a caller-supplied RequestedHolder and ExpectedGeneration when cooperating application writers need stale-update detection. Keep the current Holder and Generation under the child LeaseEvidence Folder. Trigger ACQUIRE, RENEW, or RELEASE through a separate RequestSequence and wait for LastProcessedSequence before issuing another request.

Use an explicit decision order:

1. Reject an empty holder.
2. Reject ExpectedGeneration unequal to the current Generation as DENIED-STALE.
3. For ACQUIRE, reject an effective lease as DENIED-HELD; otherwise validate duration and acquire.
4. For RENEW or RELEASE, reject an inactive lease as DENIED-INACTIVE and a nonmatching holder as DENIED-NOT-HOLDER.
5. Increment Generation on every accepted acquire, renewal, release, and automatic expiry.

For a grant or renewal, create BypassExpiresAt as a Java Date and retain its epoch separately. For automatic expiry, the BypassEffective expression event should clear Holder, disable the lease, and increment Generation. That increment makes a pre-expiry expected generation stale even though no API write caused the expiry.

The verified sequence covered blank holder, Alice acquire, Bob conflicting acquire, Alice renewal, Bob release denial, Alice stale release denial, Alice release, Bob acquire/automatic expiry, Bob stale and inactive renewals, and Alice reacquire/release. Renewal advanced generation without another ACTIVE transition. Expiry advanced generation and cleared the holder without an external write.

Keep exact request and transition markers because transport success does not establish the state-machine decision. In three runs the matrix produced 12 REQUEST and six LEASE rows, with zero ERROR-or-higher rows over each exact bounded interval. Feed, Discharge, and a separate Control instance stayed untouched.

This pattern is cooperative application correlation only. RequestedHolder is not authenticated identity, and a tag-event read/compare/write sequence is not an atomic server-side compare-and-set. It does not prove mutual exclusion under simultaneous writers, restart persistence, redundancy behavior, permission enforcement, or durable audit. Test those separately before using lock language.

## Fence a separate child-folder command with live lease state

Keep a protected action separate from the lease request event. In the tested child, CommandEvidence was a sibling Folder to LeaseEvidence and contained RequestedHolder, ExpectedGeneration, DesiredCommand, ExecuteSequence, exact decision flags/counters, and LastProcessedSequence. The ExecuteSequence script removed the event member and Folder segments to reach the child root:

```python
	folder_root = str(tagPath).rsplit('/', 1)[0]
	child_root = folder_root.rsplit('/', 1)[0]
```

Reread BypassEffective, LeaseEvidence/Holder, and LeaseEvidence/Generation during every command event. Do not authorize from a prior marker. Check expected generation before active state so an expired generation is visibly DENIED-STALE; with the current generation, the same inactive child becomes DENIED-INACTIVE. Then check holder equality and return DENIED-NOT-HOLDER or EXECUTED. Write CommandOutput only for EXECUTED.

A parent may fan RequestedHolder, DesiredCommand, a per-child expected generation, and one ExecuteAllSequence into fixed child CommandEvidence folders. Record all returned qualities, then wait for every child LastProcessedSequence and read every decision. In the verified first call, twelve Good writes produced Feed EXECUTED, Process DENIED-NOT-HOLDER, and Discharge DENIED-INACTIVE.

After Process transferred from Bob generation 1 to Alice generation 3, a later explicit parent sequence executed Feed and Process. Feed then expired without another write, advanced generation 1 to 2, cleared Holder and CommandOutput, and made the parent's expected generation 1 stale. Changing only FeedExpectedGeneration to 2 did not replay anything; sequence, markers, output, aggregates, and the settled logger count stayed unchanged until another ExecuteAllSequence.

Clear CommandOutput when the lease is released or expires if that is the selected application policy, and verify the output independently from the lease and command markers. The three-run matrix produced five lease-request rows, six lease-state rows, four parent fanout rows, twelve child command rows, and zero ERROR-or-higher rows over each exact bounded interval.

This is a cooperative fence pattern, not authenticated authorization, atomic CAS, a safety permissive, or deterministic real-time shutdown. A writer that bypasses the event can still write a memory output unless separate security/enforcement prevents it. Restart, redundancy, simultaneous writers, and client-principal enforcement remain separate tests.

## Separate command acceptance from feedback completion

Do not treat EXECUTED as physical completion. For an accepted command, write CommandOutput and separately open Pending with a typed DeadlineAt, exact DeadlineMillis, and LastExecutionSequence. Put the desired value in retained command evidence so completion compares feedback against the request that actually executed.

A root polling expression can classify completion without another write:

```json
"expression": "if({[.]CommandEvidence/Pending},if({[.]Feedback} = {[.]CommandEvidence/DesiredCommand},1,if(now(250) >= {[.]CommandEvidence/DeadlineAt},2,0)),0)"
```

Attach a valueChanged handler and ignore initialChange plus state zero. Interpret 1 as SUCCESS and 2 as TIMEOUT. In either case clear Pending; on TIMEOUT also clear CommandOutput if that is the chosen application policy. Clearing Pending returns the expression to zero, so explicitly ignore that follow-up transition rather than recording a second completion.

Retain LastCompletionSequence, state, exact observed epoch, success/timeout counters, and an exact marker. Wait for command acceptance before waiting for completion because the command event, expression evaluation, and completion event are separate asynchronous barriers. Feedback may already match when Pending opens; test that immediate-success path instead of assuming every command remains pending first.

The verified matrix covered pre-deadline Feed success, Process timeout with no write, late feedback that did not reopen the closed request, immediate success on a new sequence when feedback already matched, and false-direction completion after feedback changed false. Process timeout was observed 23-26 ms after its two-second deadline in three runs. Treat that as laboratory polling evidence, not a scheduling guarantee.

At the parent, keep command-decision aggregates separate from Pending, current completion-success, cumulative success, and cumulative timeout. In the tested three-child fanout, command totals were executed 6 and denied-inactive 3, while completion totals were success 5 and timeout 1; Discharge never accepted a command.

Feedback was a memory tag in this test. SUCCESS does not prove field-device actuation, and TIMEOUT is not a safety response. Test OPC quality, stale timestamps, chatter, contradictory feedback, restart/redundancy, alarm policy, and authenticated enforcement separately.

## Latch command timeouts, alarm them, and gate reset

A completion expression returns to zero after Pending clears, so retain timeout evidence separately when operators or downstream automation must see it. In the tested child, TIMEOUT wrote TimedOutDesired and LastTimeoutSequence before setting a root TimeoutLatched Boolean. That Boolean carried a High `CommandTimeout` alarm. The alarmActive and alarmCleared handlers used an AlarmWasActive memory bit so an initialization clear callback could not be mistaken for a real lifecycle transition.

Do not arm Pending in the same unordered batch that initializes its deadline. A discovery run proved that a dependent expression can observe `Pending=true` while `DeadlineAt` still holds its default epoch, even though `writeBlocking` later returns Good qualities for the whole call. Publish DeadlineAt, DeadlineMillis, sequence, and retained request evidence first; only after that write completes should a second write set CommandOutput and Pending. Good qualities are per-write transport results, not an atomic multi-tag snapshot.

Put reset behind a separate sequence member, such as `CompletionEvidence/ResetSequence`. Its valueChanged handler should remove both the member and Folder path segments, then re-read live TimeoutLatched, Pending, Feedback, and TimedOutDesired. Record distinct decisions: NO-EVIDENCE when no latch exists, DENIED-PENDING while completion is open, DENIED-MISMATCH while feedback still disagrees with the timed-out request, and CLEARED only when retained and live evidence agree. Write the reset decision marker before clearing the latch so the alarm-cleared callback can correlate the completed reset.

Late matching feedback must not replay a closed completion or automatically clear the alarm. The verified two-cycle matrix left Process latched after late feedback, denied mismatch resets, and required a later explicit reset after feedback matched. Two parent reset fanouts returned Good writes while producing mixed child decisions. Across each of three clean runs, exact evidence comprised two parent-command rows, six command rows, six completion rows, two parent-reset rows, eight child-reset rows, two alarm-active rows, two alarm-cleared rows, and zero ERROR-or-higher rows in the same bounded window.

This is application evidence and alarm policy, not a safety reset, authenticated approval, durable audit, or atomic workflow. Test tag permissions, acknowledgement policy, restart/redundancy, simultaneous writers, OPC quality/timestamps, and required safety-system behavior separately.

## Add an inherited single-flight request layer

Extend a proven command-completion UDT when the new behavior is a policy layer rather than a replacement. Give the derived UdtType the base's relative `typeId`, import the base before the derived type, and verify both definitions exist on the destination Gateway. A derived payload is not portable by itself when its base type is absent.

Keep the caller's Int8 RequestedSequence separate from an Int4 ExecuteTrigger. A valueChanged event on RequestedSequence alone cannot observe an explicit duplicate because writing the same value does not create a value transition. The separate trigger lets a caller ask the UDT to classify the same request identity again.

During each trigger, re-read LastAcceptedSequence, Pending, TimeoutLatched, DesiredCommand, and relevant counters. The verified decision order was STALE for a lower sequence, DUPLICATE for the accepted sequence, BUSY for a newer request while another command was pending, BLOCKED-LATCH for a newer request while retained timeout evidence existed, and ACCEPTED otherwise. Classification order is policy: the test intentionally reported an old request as STALE even while the child was latched.

Do not advance LastAcceptedSequence on BUSY when retrying the same identity after completion is desired. Only ACCEPTED published inherited completion evidence, using the already-proven deadline-first/Pending-second ordering. DUPLICATE, STALE, BUSY, and BLOCKED-LATCH changed decision evidence only.

The parent can fan DesiredCommand, RequestedSequence, and ExecuteTrigger to fixed child instances, but every Good write still needs a per-child decision barrier. In the verified matrix, request 11 was BUSY on all children while request 10 was pending; the same request 11 later executed on two completed children while the timed-out Process returned BLOCKED-LATCH. After an evidence-gated reset, request 11 executed on Process while the other two returned DUPLICATE.

Across three clean runs, cumulative child totals were accepted 6, duplicate 8, busy 3, stale 3, blocked-latch 1, success 5, and timeout 1. Each bounded window contained seven parent rows, 21 child-decision rows, six inherited completion rows, two reset rows, one alarm-active row, one alarm-cleared row, and zero ERROR-or-higher rows. Control remained isolated.

This protocol supplies cooperative deduplication and single-flight policy inside one Gateway execution context. It is not an atomic distributed queue, durable message ledger, authenticated caller identity, exactly-once delivery, or concurrency proof. Restart, redundancy, simultaneous writers, sequence rollover, persistence, and external producer reconciliation require separate tests.

## Add a one-slot deferred command queue

Add a bounded queue as another derived policy layer instead of weakening the single-flight child. Keep one retained sequence/desired pair plus an explicit Queued Boolean. Classify submissions independently from inherited execution: DISPATCHED means the queue layer forwarded the request, not that the inherited command accepted it. In the verified matrix, a later request 21 was DISPATCHED by the queue layer while the inherited layer correctly returned DUPLICATE.

When a command is pending, retain the first different incoming request as QUEUED. Return QUEUE-DUPLICATE for the same retained sequence and desired value, and QUEUE-FULL for a different request. When no command is pending but TimeoutLatched is true, return BLOCKED-LATCH and preserve the existing slot. Never overwrite the queued request silently.

For automatic release, require all of the following: Queued, not Pending, not TimeoutLatched, and retained LastCompletionState exactly SUCCESS. Testing only `!Pending && !TimeoutLatched` is unsafe because timeout processing clears Pending before it writes the latch; a dependent expression may observe that intermediate state and dispatch queued work. Clear Queued before invoking the inherited trigger so the readiness expression returns false and cannot re-enter.

Do not auto-dispatch merely because a timeout reset clears the latch. Keep a separate child-Folder ReleaseQueueTrigger that re-reads Queued, Pending, and TimeoutLatched. In three verified runs, Process retained request 21 through TIMEOUT, denied reset, late matching feedback, and successful alarm reset. Queue depth stayed one, Pending stayed zero, and no output was re-energized until the explicit release trigger.

The parent may fan queue submissions, but settle both layers: each child queue decision and each inherited single-flight decision. The verified six parent submissions produced 19 child submit decisions, including one direct BLOCKED-LATCH test; two sibling auto-dispatches; one explicit Process release; 12 inherited decisions; nine completions; two resets; and the exact alarm lifecycle. Each run settled 53 dedicated rows and zero ERROR-or-higher rows.

A memory-backed one-slot queue is not durable messaging. It does not establish persistence across restart, redundancy coordination, atomic producer acknowledgement, fairness, ordering across multiple producers, exactly-once execution, or safety approval. Use a durable external queue or transactionally supported store when those properties are required.

## Guard queue cancellation and replacement with retained identity

Put queue mutation behind a separate child `QueueControl` Folder. Supply Action, ExpectedQueuedSequence, replacement sequence/desired fields, and a changing ControlTrigger. The event must remove the member and Folder path segments and re-read live QueueEvidence; parent input values and an earlier marker are not current queue state.

Classify NO-QUEUE first, then DENIED-EXPECTED when the caller's expected identity differs from the retained slot. Only then apply CANCEL or REPLACE. CANCEL clears Queued. REPLACE changes the retained sequence/desired pair but does not dispatch it. Write the exact decision evidence before mutating QueueEvidence so the marker describes the before/after identity.

Keep queue control separate from command and alarm lifecycle. Canceling deferred work must not change the active command's Pending, output, completion state, TimeoutLatched, alarm acknowledgement, or reset evidence. In the verified Process path, replacement request 32 remained queued behind a timeout; an expected-31 cancel was denied, expected-32 cancel succeeded, and the High timeout alarm remained active until a separate evidence-gated reset.

A parent can fan different control policies to fixed children. One verified 15-write fanout returned all Good qualities while Feed CANCELED request 31, Process REPLACED 31 with 32/true, and Discharge DENIED-EXPECTED against expected 999. Wait for every child ControlTrigger/decision and read the retained queue independently. Changing only a parent replacement input produced no child marker, queue, trigger, or log replay.

Across three clean runs, queue-control totals were canceled 2, replaced 1, denied-expected 2, and no-queue 3. Underlying queue totals remained dispatched 3, queued 3, auto-dispatch 1; inherited totals were accepted 4, success 3, timeout 1. Each bounded window contained 31 dedicated rows and zero ERROR-or-higher rows.

ExpectedQueuedSequence is cooperative stale-update detection, not an atomic compare-and-set across simultaneous writers. Queue cancellation/replacement is not authenticated authorization, alarm acknowledgement, a safety action, durable audit, or transactionally isolated messaging.

## Expire retained queue entries independently

Add a typed QueueRetentionSeconds parameter and deep-override inherited `QueueEvidence/Queued` when the derived type must timestamp enqueue/dequeue transitions. On enqueue, create a Java Date deadline with `system.date.addSeconds` and retain its exact epoch with `system.date.toMillis`. Keep the DateTime and Int8 members separate because generic reads stringify Java Date values.

Do not let a polling expiry expression depend on Queued alone. A discovery run proved the expression can observe `Queued=true` before the Queued value-change handler publishes QueueExpiresAt, compare against the epoch default, and expire every slot immediately. After writing QueueExpiresAt and QueueExpiryMillis, set a separate QueueExpiryArmed Boolean in a second write. Require Queued, QueueExpiryArmed, and the deadline comparison in QueueExpiryState; clear the arm bit on every dequeue.

Expiration should clear only deferred state. Record the queued sequence, desired value, deadline, observed epoch, and count; latch a separate QueueExpiryLatched alarm; then clear Queued. Do not change the active command's Pending, output, feedback, or completion evidence. Use a separate QueueExpiryEvidence reset member and guarded alarm callbacks.

The verified parent used Feed/Process/Discharge retention values 1/5/5 seconds and a five-second active-command timeout. Feed's queued request expired and raised the exact Medium source while request 40 was still pending. Process was canceled before expiry. Discharge completed request 40 and auto-dispatched its queue before expiry. All four accepted commands succeeded; no command timeout occurred.

Across three clean runs, enqueue/dequeue totals were 3/3, expired 1, queue-control canceled 1, auto-dispatch 1, accepted/success 4/4, and expiry alarm active/cleared 1/1. Each bounded window settled 28 dedicated rows and zero ERROR-or-higher rows. Feed's expiry latch remained active through successful command completion until its own reset.

Queue retention is application policy, not durable message expiry, real-time scheduling, safety enforcement, or a guarantee of execution timing. Test restart, redundancy, clock changes, scan delays, simultaneous writers, and durable storage separately.

## Coordinate child completion with a current-sequence quorum

Treat a parent quorum as a second state machine over child completion evidence. Count a child only when its `LastExecutionSequence` equals the parent's current operation sequence, `Pending` is false, and its terminal state is the expected value. Keep cumulative totals separate from current-operation counts.

Do not arm the quorum merely by changing the parent sequence. A discovery run showed that child sequence members can update before their new Pending flags, allowing retained SUCCESS states from the prior operation to satisfy a new 2-of-3 quorum falsely. Clear a parent `OperationArmed` bit before fanout. Set it only after all children report the current sequence and Pending true, and record an exact armed marker.

Even after that barrier, do not treat an expression event's `currentValue` as a committed snapshot. Simultaneous child completion writes can queue a transient expression result while the settled success/timeout counts already imply a different outcome. Use the expression event as a wake-up, re-read the settled current-sequence counts in the event script, derive success or failure again, and ignore the callback when neither terminal threshold is actually met.

Make the commit sequence-idempotent. Before changing counters, decision state, or logs, compare `LastDecisionSequence` with the current sequence. Once a decision is recorded, later child success, timeout, alarm, or reset transitions must not overwrite it. A 2-of-3 success can therefore close while one child remains Pending; the later timeout is evidence about that child, not a replacement parent decision.

The verified two-operation matrix first produced Feed and Discharge success, recorded QUORUM-SUCCESS, then allowed Process to time out without overwriting it. The second operation produced one success plus two timeouts and recorded QUORUM-FAILED. Across three corrected runs, each bounded window contained two parent fanouts, two arm markers, six child commands, six completions, two quorum decisions, three resets, three alarm-active rows, three alarm-cleared rows, and zero ERROR-or-higher rows. A separate Control instance remained unchanged.

This is an application-level completion policy, not atomic distributed consensus, a safety vote, or a transactional snapshot. Restart, redundancy, simultaneous callback execution, unreliable feedback, OPC quality/timestamps, and safety-system requirements need separate designs and tests.

## Latch and review a degraded quorum success

Keep the terminal quorum decision immutable, and add a separate policy layer when a 2-of-3 success must remain visible after the final child times out. A derived UDT can add a root polling expression plus a nested `DegradedEvidence` Folder without changing the proven base coordinator.

Require all of these before latching degraded success: the parent's terminal sequence equals the current operation, the terminal decision is `QUORUM-SUCCESS`, every child is complete, at least one current-sequence timeout exists, and the degraded sequence has not already been recorded. Treat the expression event as a wake-up and re-read those conditions in the script. Publish sequence, count, and marker before setting the latch so its alarm callback receives complete correlation metadata.

Put ReviewTrigger and ClearTrigger inside the evidence Folder. Remove the member and Folder segments with `str(tagPath).rsplit('/', 2)[0]`, then read sibling parent and inherited child paths. Review records the degraded sequence. Clear should distinguish no evidence, unreviewed evidence, pending children, uncleared child timeout latches, and successful clear. Do not clear the degraded alarm merely because the child High alarm clears.

The verified lifecycle latched a Medium parent `QuorumDegraded` alarm after Process timed out following a successful Feed/Discharge quorum. Clear was denied before review and again while the child timeout latch remained. Resetting the child cleared only its High alarm; the Medium alarm remained until a later reviewed clear. A second operation with one success and two timeouts produced `QUORUM-FAILED` and did not create another degraded-success event.

Across three clean runs, each bounded window contained the inherited 27 rows plus one degraded transition, one review, three clear decisions, and one active/cleared degraded-alarm pair: 34 rows total with zero ERROR-or-higher rows. Control remained isolated and final state was restored.

This is application review evidence, not alarm acknowledgement, authenticated approval, a safety reset, durable audit, or transactional incident management. Test those properties separately.

## Escalate overdue degraded review

Add review timing as another derived layer instead of deep-overriding the proven degraded-review Folder. Use a typed timeout parameter and a separate `ReviewSlaEvidence` Folder for deadline, escalation, alarm, and cleanup evidence.

When a new degraded sequence latches, create the review deadline with `system.date.addSeconds`, retain its exact epoch with `system.date.toMillis`, and publish DateTime, epoch, sequence, counter, and marker before setting `DeadlineArmed`. Require the arm bit in the polling expression so it cannot compare against default epoch metadata.

Use `now(250)` only as a polling wake-up. Before latching overdue review, re-read degraded latch, armed state, degraded/reviewed/escalated sequences, deadline epoch, and current epoch. Require the same unreviewed sequence and `observedMillis >= dueMillis`. Publish escalation correlation before setting the High alarm latch.

Late review should not erase an already-observed overdue condition. In the verified policy, inherited degraded clear remained the lifecycle boundary. A separate root expression detected `ReviewEscalated && !DegradedLatched`, cleared the deadline arm and escalation latch, and allowed guarded overdue-alarm callbacks to record the High clear without replacing the inherited Folder script.

The verified alarm progression was child High plus parent Medium, then child High plus parent Medium plus overdue High without another API write, then both parent alarms after child reset, then zero after reviewed clear. A later failed quorum produced two child High alarms but no new review deadline or escalation.

Across three corrected runs, typed deadline and observed epochs proved escalation never preceded its deadline. Each bounded window contained the inherited 34 rows plus one deadline, one escalation, one escalation cleanup, and one overdue-alarm active/cleared pair: 39 exact rows and zero ERROR-or-higher rows.

Set test deadlines longer than any exact-log stability interval used to prove the pre-expiry state. A one-second discovery deadline expired during the two-second stability check, so the lab interval was increased to four seconds. This was a harness observability conflict, not an escalation defect.

Application review deadlines are not deterministic real-time timers, native alarm acknowledgement deadlines, notification guarantees, durable scheduling, or safety escalation. Test clock changes, restart, redundancy, notification pipelines, and required safety behavior separately.

## Compose multiple quorum Cells under an Area

Once one Cell type is proven, compose fixed Cell UDT instances under an Area type instead of copying their members. Bind each nested Cell's identity and review timeout with typed parameter wrappers. Import and verify the full base-type chain before the Area definition.

Give the Area its own operation sequence and trigger. Fan desired command, sequence, and the child trigger to each fixed Cell, record every returned quality, then settle each Cell's `LastDecisionSequence` and terminal decision. Guard current-operation completion aggregates against sequence zero; otherwise untouched default child sequence values can appear complete.

Keep Area maintenance calls in a nested Folder. An Area review/clear script can remove its member and Folder segments, then call each Cell's `DegradedEvidence` trigger. A reset-all script can build fixed paths through Cell and actuator levels to each `CompletionEvidence/ResetSequence`. Good parent writes still require every deep child decision to settle.

The verified Area contained two Cells and six actuators. Both Cells reached QUORUM-SUCCESS, but CellA later degraded and escalated while CellB completed three-for-three. Area aggregates settled decision complete 2, success 2, failure 0, degraded 1, and overdue 1. ReviewAll affected only CellA. ClearAll produced DENIED-CHILD-LATCH for CellA and NO-EVIDENCE for CellB behind two Good writes.

After late matching CellA Process feedback, ResetAll called all six actuator evidence folders: Process returned CLEARED and the other five returned NO-EVIDENCE. Only the child High alarm cleared. A second Area ClearAll produced CellA CLEARED and CellB NO-EVIDENCE, then the parent Medium and overdue High cleared through their independent inherited lifecycles.

Across three corrected runs, exact alarm sources existed only under CellA. Each bounded window contained 39 inherited rows plus one Area command, one review, two clears, and one reset: 44 exact rows and zero ERROR-or-higher rows. A separate ControlArea stayed at sequence zero and all operational aggregates zero.

This is fixed-shape hierarchical orchestration, not an atomic transaction, distributed workflow engine, authenticated maintenance approval, safety reset, or durable fleet coordinator. Test simultaneous Area writers, partial delivery recovery, restart, redundancy, permissions, and field-device behavior separately.

## Build a quorum of Cell quorums

An Area can apply a second quorum over terminal decisions from fixed child Cells. Keep the child actuator quorum unchanged and derive a new Area type with its own `RequiredCellSuccesses`, arm bit, current-sequence Cell counts, and terminal Area decision evidence.

Use a separate hierarchy start trigger. Clear `AreaOperationArmed` before calling the inherited Area start trigger. Arm only after both Cells report the Area's current sequence and every actuator in each Cell is Pending. This prevents retained child decisions from an earlier operation from satisfying the Area policy during fanout.

Count a Cell only when its `LastDecisionSequence` equals the current Area sequence. Treat the Area quorum expression callback as a wake-up: re-read both raw Cell sequence/decision pairs, derive the outcome again, and commit only when a terminal threshold is settled. Guard the commit with `LastAreaDecisionSequence`, so an early 1-of-2 Area success remains terminal even if the other Cell later fails.

Expression-backed `valueChanged` callbacks can be invoked with `initialChange` false while `currentValue.value` is `None`. Before `int(currentValue.value)`, `long(...)`, or `float(...)`, either enter through an explicit `currentValue.value is not None` check or return early from an `if ... currentValue.value is None:` guard. A bounded ERROR query caught the missing guard on an untouched ControlArea even though the exercised Area's functional reads and exact dedicated-log count were correct.

The verified lifecycle armed after six Pending actuators, let CellA's 2-of-3 success produce `AREA-QUORUM-SUCCESS` while CellB still had two Pending actuators, then retained that Area decision after CellB reached one success/two timeouts and `QUORUM-FAILED`. Two exact High alarms appeared under CellB. Late matching feedback caused no replay; the inherited deep reset reached all six evidence Folders and cleared both alarms.

Across three corrected runs, each bounded window contained one hierarchy start, one Area command, two Cell fanouts, six commands, two Cell arm rows, one Area arm row, six completions, two Cell decisions, one Area decision, two alarm-active rows, one Area reset, six reset decisions, and two alarm-cleared rows: 33 exact dedicated rows and zero ERROR-or-higher rows. A separate ControlArea remained at sequence zero.

This remains application-level hierarchical completion policy, not distributed consensus, a safety vote, atomic snapshot, or durable workflow. Test restart, redundancy, concurrent writers, partial delivery, device quality/timestamps, and safety requirements separately.

## Review degraded success across Cell quorums

Preserve the terminal Area quorum decision and add a separate derived evidence layer when an early Area success is later accompanied by a current-sequence Cell failure. Do not reinterpret or overwrite `AREA-QUORUM-SUCCESS`.

Latch only after the Area decision sequence equals the current operation, the decision is success, both Cells have terminal current-sequence decisions, at least one Cell failed, and the degraded sequence has not already been recorded. Use the expression event only as a wake-up, re-read those conditions, publish sequence/count/marker first, and set the Area degraded latch last.

Place review and clear controls in a nested `AreaDegradedEvidence` Folder. Remove the member and Folder segments with `str(tagPath).rsplit('/', 2)[0]`. Review must correlate to the same degraded sequence. Clear must re-read both Cell completion states and all six actuator timeout latches; deny unreviewed, incomplete, or still-latched evidence. A Good clear-trigger write is not proof that evidence cleared.

Keep the Area Medium alarm independent from child High alarms. In the verified lifecycle, CellB's two High timeout alarms and the Area Medium degraded alarm were active together. The inherited six-actuator reset cleared the High alarms but deliberately left the Medium alarm active. Only the later reviewed Area clear removed it.

Across three clean runs, each bounded window contained the 33 inherited hierarchy rows plus one Area-degraded transition, one review, three clear decisions, and one active/cleared Area-degraded alarm pair: 40 exact rows and zero ERROR-or-higher rows. The immutable Area decision remained success and ControlArea produced no degraded evidence.

This is application review evidence, not native alarm acknowledgement, authenticated approval, durable audit, transactional recovery, or a safety reset. Test those requirements separately.

## Escalate repeated Area degradation

Keep per-incident Area degraded evidence separate from a cumulative recurrence policy. Derive again, add a typed repeat threshold, and use the inherited degraded count as the recurrence input. A first incident can remain Medium while a later threshold crossing latches a separate High alarm.

Fence a cumulative threshold with a consumed count. Require `DegradedCount >= RepeatDegradedThreshold`, `DegradedCount > ThresholdObservedCount`, and recurrence not already latched. A discovery expression that only required `count >= threshold && !latched` re-latched immediately after reset because clearing the latch did not reduce the cumulative count. It produced a second High activation and 87 rows instead of the expected 85.

Treat the expression callback as a wake-up. Re-read count, threshold, sequence, and latch; publish `ThresholdObservedCount` and correlation before setting the latch. After reset, the unchanged count no longer exceeds the consumed count. A future degraded operation advances the count and may deliberately create a new recurrence event.

Give recurrence its own nested Folder and reset lifecycle. Deny recurrence reset while the current Area degraded incident remains active. Clear the Medium incident first, then clear the retained High recurrence evidence. Do not make an incident clear erase cumulative history or silently reset recurrence policy.

The verified two-operation matrix kept recurrence inactive at degraded count 1, then latched it exactly once when count reached threshold 2. The second incident produced two child High alarms, one Area Medium alarm, and one recurrence High alarm. Deep actuator reset left the two Area alarms; incident clear left recurrence High alone; recurrence reset cleared the final source.

Across corrected discovery and two repeats, each bounded window contained two complete 40-row degraded-review lifecycles plus one recurrence transition, two reset decisions, and one recurrence active/cleared alarm pair: 85 exact rows and zero ERROR-or-higher rows. ControlArea remained untouched and cleanup restored state.

Cumulative memory counters and recurrence alarms are not restart-persistent statistics, durable audit, rate-based analytics, authenticated escalation, or safety functions. Use a historian/database and separately validated workflows when those properties matter.

## Fence recurring evidence by generation

When recurrence may clear and later re-arm, add a generation to distinguish the new evidence from an old reset request. Deep-override the recurrence event to increment Generation and publish it before setting the inherited latch. Add a reset input for the expected generation and deep-override the nested ResetTrigger script.

Evaluate reset in this order: no recurrence evidence, mismatched expected generation, current degraded incident still active, then clear. A request carrying generation 1 must not clear recurrence generation 2. Keep the consumed degraded-count fence as well; generation identifies the recurrence episode while `ThresholdObservedCount` prevents same-count replay.

This reset check is cooperative application correlation. The Gateway event's read/compare/write sequence is not atomic compare-and-set, a lock, authentication, authorization, or protection from another direct writer. If concurrent writers matter, expose a guarded server-side operation and test contention separately.

Give short command deadlines a deliberate test margin. A provisional three-operation discovery happened to pass with inherited two-second actuator deadlines, but its first repeat timed out before the separate feedback API request arrived: both Cells legitimately failed and the Area decision failed. The run captured 68 bounded rows, zero ERROR-or-higher rows, and restored state.

The corrected test deep-overrode all six actuator `CommandTimeoutSeconds` values to five seconds on both Area instances, read all twelve effective parameter paths before starting, and retained deliberate no-write timeout coverage. Choose a deadline longer than the start request, Pending barrier, feedback request, and expected scheduling jitter; do not merely add sleeps.

Across corrected discovery and two clean repeats, operation 1 produced no recurrence, operation 2 latched generation 1, and operation 3 advanced the consumed count and latched generation 2. Each recurrence rejected a stale generation and the current generation while its Medium incident remained active, then cleared with the matching generation after incident clear. Each bounded window contained 132 exact rows and zero ERROR-or-higher rows.

Generation counters in memory are not durable identities across restart or redundancy. Persist and reconcile them when resets must survive Gateway lifecycle changes.

## Keep alarm acknowledgement separate from application reset

Native alarm acknowledgement and a UDT's review/reset workflow are different state planes. For a retained recurrence alarm, set `ackMode: "Manual"` and, when operator context is required, `ackNotesReqd: true`. Acknowledging the current event changes `ActiveUnacked` to `ActiveAcked`; it must not clear `DegradedLatched`, `RecurrenceLatched`, or bypass the generation-fenced reset rules.

When a derived UDT adds `alarmAcked` to a deeply inherited alarm tag, override the complete `alarms` array and the complete `eventScripts` array. Restate `alarmActive` and `alarmCleared`; list properties replace inherited lists rather than append to them. Export the derived definition and verify the exact alarm plus all three event IDs before runtime testing.

Use the guarded acknowledgement API in `llm-tools`: query the exact active source, capture its current event UUID, dry-run with a nonempty note and username, require `code: dry_run_ok` and `writesAttempted: false`, then apply and require `allAcknowledged: true`, no failed event IDs, and `ActiveAcked`. Treat acknowledgement as irreversible for that event.

Test reactivation, not only one acknowledgement. After the application workflow clears the first recurrence, a later degradation count must create a distinct event UUID in `ActiveUnacked`; acknowledgement must not carry forward. An `alarmAcked` script can record generation/count/marker evidence using the enclosing Folder path, but this is in-memory operational evidence, not durable or authenticated audit.

The focused verified fixture drove the already-proven Area evidence tags directly. Across discovery and two repeats, each run proved two manual acknowledgements over generations 1 and 2, stale/current reset denial behavior, a distinct unacknowledged event on reactivation, untouched ControlArea state, 17 exact dedicated rows, zero ERROR-or-higher rows over the same bounds, and zero active sources after cleanup. Direct evidence driving narrows the claim to alarm lifecycle; it does not re-prove the six-child hierarchy.

### Capture supported acknowledgement callback metadata

An `alarmAcked` tag event receives `alarmEvent`, `alarmPath`, `ackedBy`, and `missedEvents`. In the verified 8.3.8 runtime, use `alarmEvent.getId()` for the UUID—not `getEventId()`—plus `getSource()`, `getState()`, `getLastEventState()`, `isAcked()`, `isCleared()`, and `getNotes()`.

Exact observed string forms matter. A username supplied as `codex.actor.active` arrived as qualified `ackedBy` value `usr:codex.actor.active`. `alarmPath` and `unicode(alarmEvent.getSource())` both equaled the fully qualified source. The overall states were `Active, Acknowledged` and `Cleared, Acknowledged`; `unicode(alarmEvent.getLastEventState())` was `Ack` in both callbacks.

Do not confuse alarm configuration Notes with the acknowledgement call's note. With alarm `notes: "CONFIGURED-RECURRENCE-NOTE"` and API notes `ACK-NOTE-ACTIVE`/`ACK-NOTE-CLEARED`, `alarmEvent.getNotes()` returned the configured alarm Notes value in both callbacks. Retain the acknowledgement note in the Alarm Journal or another separately verified audit path when it is required; this callback accessor did not expose it.

Test acknowledgement timing. The active branch reported acknowledged true/cleared false. A later event was cleared first, remained `ClearUnacked`, then its callback reported acknowledged true/cleared true after acknowledgement. Across corrected discovery and two repeats, each focused run produced 14 exact dedicated rows, zero ERROR-or-higher rows, exact UUID/source/path/actor metadata, untouched ControlArea state, and zero active sources after cleanup. A failed discovery that expected last transition text `Acknowledged` instead of live `Ack` preserved four dedicated rows, zero errors, and restored state.

## Consume a sibling Document through a child UDT

Prefer a small child UDT when a complex consumer has its own triggers, correlation state, counters, and reset lifecycle. Nest the child beside the producing Folder and bind only the parent parameters it needs. A child member script can remove its member and child segments from `str(tagPath)`, append the sibling Folder path, read the Document, and index nested object/array fields after requiring Good quality.

Use a monotonically changing envelope identity. The verified acknowledger used `eventTimeMillis` plus optional expected decision, retained `LastAcknowledgedEventTimeMillis`, and classified no-envelope, stale, mismatched, duplicate, and accepted requests. It did not infer execution from trigger readback. Exact result tags and logger rows proved each branch.

Precompile the exact event bodies with Jython before creating the child type. Four stopped runs persisted malformed scripts with Good trigger writes and zero ERROR+; an offline Jython compile exposed an extra `)`. After correction, discovery and two repeats each produced ten exact rows, zero ERROR+, two accepted identities, three denials, one duplicate, Control isolation, independent reset, zero alarms, and restoration.

This is cooperative in-memory correlation. Test persistence, restart, redundancy, authentication, concurrent consumers, and durable delivery separately.

## Verification checklist

- Export each definition and confirm relative `typeId`, typed wrappers, exact lowercase `bindType: parameter`, and binding text.
- Read the concrete parent and every nested child's `Parameters.<name>` paths.
- Read at least one dependent expression in the leaf and require exact Good quality.
- Change only the root or parent instance parameters through a controlled `MergeOverwrite` patch; require every bound descendant to update without recreating the instance.
- Trigger an observable leaf script when scripts depend on child parameters; verify exact marker and bounded logger output.
- Export the concrete instance and confirm deep inherited-member stubs omit `typeId` while nested definitions retain it.
- Verify overridden child parameters stay fixed and non-overridden parameters continue to propagate.
- Never claim `Overwrite` recursively clears overrides; use exact delete/recreate when a full reset is required.
- Stage event-script and value changes when transitional execution of the old handler is unsafe.
- Read the Leaf parameter and effective alarm setpoint separately; a deep alarm override can leave parameter propagation intact.
- Query exact alarm sources and marker outputs after every threshold transition; tag value and Good quality do not prove alarm state or handler selection.
- For sibling coordination, verify each child's parameters, the peer read value and quality, the parent expression, and a separate Control instance.
- For fan-out, verify every child write quality and readback, each child marker, aggregate count/all state, and a separate instance; never infer transactionality from one `writeBlocking` call.
- For command/feedback alarms, test both inequality directions, exact per-child sources, aggregate counts, alarm priority, initialization callbacks, override isolation, and zero-active-alarm cleanup.
- For alarm inhibition, prove mismatch state and alarm sources independently, observe enable/disable callbacks, verify native child Boolean parameters, and export/read direct child overrides again after parent `Overwrite`.
- For selective fan-out, verify every participation value/quality, selected path, returned write quality, skipped-child state, zero-selection branch, aggregate rule, and an event-completion marker before the next configuration change.
- For permissive fan-out, record selected, blocked, and excluded children separately; verify both read qualities, no automatic replay, zero-eligible policy, nested child markers, and parameter-versus-memory Overwrite behavior.
- For sequenced dispatch, verify increasing acceptance, stale rejection, same-value non-triggering, exact child acknowledgement sequences, explicit retry after permissive recovery, zero-eligible policy, and separate tag-marker versus logger-settle barriers.
- For bypass routing, verify empty/nonempty reason behavior, invalid/blocked classification, always-visible bypass attention, healthy-but-active bypass state, explicit retry, child input qualities, and the authorization/safety claim boundary.
- For bypass evidence, distinguish active from required counts, test latching and explicit reset, verify child-Folder parameter scope/path traversal, prove parent-to-child-Folder reset calls, and avoid durable-audit or concurrency claims.
- For multi-interlock diagnostics, verify ordered current reasons, first-out latching, invalid versus required bypass, healthy-but-active bypass visibility, direct and parent resets, mixed child decisions, no state-change replay, and a separate Control instance.
- For trip acknowledgement/reset, exercise active denial, active and cleared acknowledgement, cleared-unacknowledged denial, successful reset, NO-EVIDENCE, mixed parent fanout outcomes, retry, live interlock re-read, retained counters, and Control isolation. Never infer child business success from parent write qualities.
- For expiring bypass, verify epoch import/export, generic Date stringification limits, reason validation, no-write expiration, transition classification/counters, exact toMillis evidence, observed latency, re-arm, manual clear, reason invalidation, nested aggregates, Control isolation, and bounded logs.
- For a bounded bypass lease, verify typed maximum duration, every denial, grant versus renewal, a later epoch, no effective transition on renewal, survival across the old deadline, expiration, post-expiry grant, explicit cancel, request/transition counters, sibling and Control isolation, and bounded logs.
- For parent lease fanout, verify every returned write quality and every child decision, current-sequence completion/outcome aggregates, parameter propagation without replay, explicit retry, renewal-versus-activation behavior, cancel-all, Control isolation, exact dedicated-log cardinality, and the bounded ERROR-or-higher query.
- For holder/generation lease correlation, test blank/conflicting/stale/non-holder/inactive decisions, generation increments on every accepted transition and expiry, renewal without another ACTIVE event, post-expiry invalidation, exact request/transition markers, sibling/Control isolation, and bounded dedicated plus ERROR-or-higher logs. Do not call it atomic CAS or authenticated ownership.
- For lease-fenced child-folder commands, reread live sibling lease state, test mixed parent outcomes behind Good writes, per-child generations, transfer plus explicit replay, expiry-driven stale then inactive decisions, no replay from generation-input changes, output clearing on lease loss, exact root/Folder paths, current/cumulative aggregates, Control isolation, and the bounded log contract.
- For command completion, distinguish EXECUTED from SUCCESS/TIMEOUT; verify typed deadline/epoch, Pending, pre-deadline feedback, no-write timeout, late-feedback non-replay, immediate already-matching feedback, both Boolean directions, zero-state suppression, completion sequence/counters, parent completion aggregates, release cleanup, Control isolation, and bounded logs.
- For timeout alarm/reset, publish deadline evidence before arming Pending; verify retained timeout evidence, exact High alarm source, guarded active/cleared callbacks, no automatic late-feedback clear or replay, NO-EVIDENCE/PENDING/MISMATCH/CLEARED reset decisions behind Good writes, mixed parent reset outcomes, final zero-active sources, Control isolation, and exact bounded dedicated plus ERROR-or-higher logs.
- For inherited single-flight commands, import and verify the base before the derived UDT; separate request identity from trigger; exercise ACCEPTED/DUPLICATE/BUSY/STALE/BLOCKED-LATCH, same-identity retry after BUSY, per-child mixed outcomes, latch/reset interaction, exact inherited completion/alarm behavior, Control isolation, and bounded logs. Do not claim a distributed queue or exactly-once delivery.
- For a one-slot deferred queue, verify DISPATCHED versus inherited acceptance, QUEUED/QUEUE-DUPLICATE/QUEUE-FULL/BLOCKED-LATCH, success-only automatic release, timeout intermediate-state protection, queue retention through alarm reset, explicit post-timeout release, exact queue/inherited markers, Control isolation, and bounded logs. Do not claim durability or exactly-once execution.
- For queue cancel/replace, use a child Folder trigger and re-read live retained identity; test NO-QUEUE/DENIED-EXPECTED/CANCELED/REPLACED, mixed parent outcomes behind Good writes, input-change non-replay, before/after markers, separation from active command/alarm/reset state, Control isolation, and bounded logs. Do not call the expected-sequence check atomic CAS.
- For queue expiry, publish typed DateTime/epoch before setting a separate expiry arm bit; require Queued+armed+deadline in the polling expression; test expire/cancel/auto-dispatch branches, exact Medium alarm source, independent command completion and expiry reset, retained timing evidence, Control isolation, and bounded logs.
- For completion quorum, correlate every child to the current sequence; clear and re-arm only after all children are Pending; use expression events as wake-ups; re-read settled counts before committing; guard with LastDecisionSequence; prove early 2-of-3 success, later-child non-overwrite, one-success/two-timeout failure, Control isolation, exact alarm sources, and bounded logs. Do not call it distributed consensus or a safety vote.
- For degraded quorum success, preserve the terminal decision; latch only after all children complete and a successful quorum has a timeout; publish correlation before the latch; require review plus cleared child latches; prove High/Medium alarm independence, failed-quorum exclusion, nested Folder path traversal, Control isolation, and bounded logs. Do not call application review an alarm acknowledgement or safety reset.
- For overdue review escalation, publish typed DateTime/epoch before an arm bit; revalidate unreviewed sequence and exact epoch in the timer callback; retain late-review escalation until the degraded lifecycle clears; prove three-level alarm transitions, failed-quorum exclusion, deadline-versus-observed ordering, Control isolation, and bounded logs. Make the test deadline longer than the pre-expiry log-stability window.
- For an Area of quorum Cells, use typed nested parameter bindings; guard sequence-zero aggregates; settle every Cell decision after command fanout; test mixed Cell outcomes, deep Area-to-Cell-to-actuator maintenance calls, per-child business decisions behind Good writes, exact nested alarm sources, ControlArea isolation, and bounded logs. Do not infer atomicity from a hierarchical write batch.
- For a quorum of Cell quorums, clear the Area arm before inherited fanout; arm only after every Cell is current and fully Pending; count only current-sequence Cell decisions; re-read raw child decisions in the expression callback; null-guard numeric `currentValue.value` conversions; make the Area commit sequence-idempotent; prove early Area success, late Cell failure non-overwrite, deep reset, exact alarms, ControlArea isolation, and bounded logs.
- For Area degraded-success review, preserve the Area terminal decision; latch only after every Cell is terminal and a successful Area quorum has a failed Cell; publish correlation before the latch; review the same sequence; require all six actuator timeout latches clear; prove High/Medium alarm independence, Good-write versus business-decision separation, ControlArea isolation, and bounded logs.
- For repeated Area degradation, use a typed threshold plus a consumed-count fence; prove no recurrence at count one, one threshold event at count two, denial while the current incident is active, incident-versus-recurrence alarm independence, no immediate post-reset relatch, a future-count re-arm policy, ControlArea isolation, and bounded logs.
- For generation-fenced recurrence, publish generation before latching; reject stale and active-incident resets; prove later-count re-arm increments generation; clear only with the matching current generation; label the check non-atomic; read back any deep timeout overrides; choose test deadlines longer than the full API request/settle path; and retain bounded failure and clean-run logs.
- For manual acknowledgement of retained recurrence, deep-override the complete alarm and event-script lists; export all three event IDs; query the exact event UUID; dry-run before apply; require ActiveUnacked→ActiveAcked without clearing application latches; prove a later occurrence has a distinct unacknowledged event; keep generation-fenced reset tests; isolate ControlArea; and retain bounded dedicated plus ERROR-or-higher logs.
- For acknowledgement callback metadata, use `getId()` and the documented AlarmEvent methods; require qualified `usr:` actor, exact UUID/source/path, `Ack` transition, configured Notes semantics, active-versus-cleared flags, missed-event false, a cleared-unacknowledged branch, ControlArea isolation, and bounded logs. Do not treat `getNotes()` as the acknowledgement note.
- For a Document acknowledger child, precompile exact event bodies with target Jython; verify typed parent bindings, Good Document quality, nested field casts, schema/no-envelope/stale/mismatch/duplicate/accepted branches, last-accepted identity, producer/consumer reset separation, Control isolation, exact focused rows, and the same-window ERROR-or-higher query. Do not call it durable or exactly-once messaging.
- Do not add a brand-new child below an inherited nested UDT instance through a derived override. The verified Gateway rejected that shape with `Bad_Unsupported` subcode 528. Add the member to the nested UDT type itself, or compose the new Folder/UDT instance as a sibling on the derived parent.
- For a correlated acknowledgement receipt, let a sibling receipt Folder read the producer Document plus acknowledger evidence, publish a versioned receipt Document, and let a second sibling Folder verify it. Fence receipt sequence, producer epoch/decision/trigger, acknowledgement identity, duplicate reads, and a newer producer epoch. Wait on a monotonic producer counter before reading a later Document when decision text may repeat.
- For a generation-fenced sequencer reset, increment generation only for newly observed higher requests according to the documented consumption policy, preserve it on replay, require a positive exact expected-generation match before reset, and prove denied resets preserve sibling dispatcher, child journal, and completion state. Treat the check as an in-memory fence rather than atomic CAS or durable deduplication.
- For a prepared reset coordinator, snapshot generation plus request identity, re-read both on commit, retain stale preparation for diagnosis/cancel, stage the expected generation before the reset trigger, and wait for the target Folder's own reset evidence. Caller `COMMITTED` is accepted dispatch, not callee completion.
- For a leased preparation, publish native DateTime and epoch deadline before an arm bit; let a guarded `now(250)` expression wake an expiry script; re-read all inputs before clearing; retain expired identity/time; and prove cancel/commit suppression by waiting beyond each captured old deadline with stable logs.
- For lease renewal, require expected generation/request, preserve deadline on mismatch, disarm before replacing DateTime/epoch evidence, extend from the retained deadline, rearm, and prove survival beyond every superseded deadline before the single final expiry.
- For a renewal budget, evaluate live/expiry/identity guards before the limit, accept only while the retained accepted count is below a typed maximum, and deny beyond the boundary without changing the final deadline or prepared/armed state. Retain a limit-specific counter, reset it only at the coordinator lifecycle boundary, and verify the effective inherited Folder plus canonical exported parameter type.
- For renewal-budget alarm telemetry, add remaining/exhausted expressions beneath the inherited ordinary Folder, bind active identity/count/deadline as alarm associated data, and keep alarm state separate from command behavior. Prove configuration through export and active data through status. Latch the active event UUID locally because clear-time bindings may already reflect reset values; use the latch to suppress initialization clears and correlate the exact active/clear occurrence.
- For warning-to-exhaustion alarm tiers, derive both from one remaining-budget state, keep independent correlation evidence per tier, and require mutually exclusive Low-at-one/Medium-at-zero source sets. A single renewal may asynchronously clear one alarm and activate another; verify eventual callbacks, UUIDs, expressions, and exact cardinality without encoding callback order.
- For a delayed inherited warning, restate the complete nested atomic member because a derived member override replaces omitted source/expression/event properties instead of merging them. Prove a measured sub-delay true pulse produces no alarm evidence, then prove a sustained true state activates and clears one correlated event.
- For an off-delayed tier handoff, distinguish mutually exclusive expression values from temporarily overlapping active alarm sources. Observe both tier UUIDs before the delay, then require the outgoing clear no earlier than configured while the incoming UUID remains unchanged.
- For a Manual delayed warning, keep active-source and all-state queries separate. Require ActiveUnacked→ClearUnacked→ClearAcked with one UUID, dry-run acknowledgement inertness, applied `alarmAcked` sibling evidence, and independent state/UUID verification for the incoming alarm tier.
- A small composed child UDT can act as an observer of several sibling subtrees. Bind only shared identity/logger/schema parameters into the child, derive sibling paths from text `tagPath`, require every QualifiedValue to be Good, and correlate the receipt Document, current producer Document, and verifier decision before publishing a confirmation Document. Keep the observer read-only with respect to those sibling business tags.
- Treat verifier state and observer state as separate planes. A retained prior `VERIFIED` value is not sufficient after the producer epoch changes; reject until receipt and verification are current again. Fence repeated observation by receipt sequence, retain observable counters, and reset the observer independently.
- A second composed child can journal the observer's confirmation without modifying the observer. Read the confirmation Document, current producer Document, local DataSet, and local fence/counters together; require Good quality; reject missing, stale, and duplicate observation identities; then append only an admitted confirmation. Bind journal capacity as a typed parameter and verify the concrete child typeId after export.
- Reuse one child UDT type for multiple consumers when their behavior is identical but policy differs. Give each instance a distinct name and typed capacity binding while sharing typed identity/logger bindings. Export both concrete instances and verify the same child typeId plus the correct binding target for each policy parameter.
- Compute multi-consumer completion against the current correlation identity. Count a journal only when its `LastJournaledReceiptSequence` equals the observer's current `LastConfirmedReceiptSequence`; require the current identity to be positive. A new confirmation must move the aggregate back to zero even when every child retains older nonzero history, then progress through partial to complete as consumers catch up.
- Include a literal-brace negative control and verify its dependent numeric expression is not Good.
- Restore patched parameters and controlled member values, scan for Gateway errors, and run a clean repeat.

## Selective parent-to-child dispatch

Use a parent Folder script to fan out only to stale child UDT consumers. Derive the parent and fleet roots from text `tagPath`, read the current correlation identity and all child last-consumed identities in one `readBlocking` call, and reject any bad quality. Build parallel `target_paths` and `target_names` lists only for mismatches.

Guard the empty branch: return `ALREADY-CURRENT` without calling `writeBlocking([], [])`. For a nonempty list, check every returned child-write quality and publish selected target names/count plus the correlation identity. Then wait separately for child identities and parent aggregates to converge. A Good trigger write is accepted dispatch, not proof that asynchronous child handlers completed.

The verified matrix covered no-confirmation denial, both-child dispatch, an already-current no-op, and one-child recovery after only Operations had caught up. Run-specific bounded logs, zero ERROR+, Good runtime values, zero alarms, a control instance, reset, and restoration remain mandatory for every creation attempt.

Keep dispatch completion in a separate sibling Folder when selected children execute asynchronously. Correlate the dispatch receipt and target list with the current producer identity and each selected child's last-consumed identity. Publish exact pending target names, and fence completed identities against duplicate observation and producer advance.

`valueChanged` is edge-driven: a Good same-value trigger write does not execute the handler. Use a new trigger value for every requested execution. A live controlled matrix pre-seeded one child at the parent's next trigger value, proved that only the other child executed, observed the named pending child, then advanced it with a distinct value and proved completion. Do not replace this state evidence with a sleep or an empty ERROR query.

Keep caller request identity separate from generated child-dispatch identity. Require a changed request value, then compute the downstream sequence above the retained parent and child trigger values. This prevents the parent from accidentally issuing the same child trigger even when request numbering and child numbering differ.

A TIMESTAMP-qualified event does not guarantee that a redundant memory write executes. The verified memory provider returned Good/all-verified without replacing the QualifiedValue timestamp, so no qualified event occurred. Prove this boundary from the request tag's exact timestamp, unchanged sequencer state, and stable dedicated-log count. Use changing request identities for commands; reserve TIMESTAMP triggers for sources that demonstrably produce new timestamps.

## Extend an inherited ordinary Folder

A derived `UdtType` can submit the inherited Folder name with `tagType: "Folder"`, restate an inherited atomic member to replace its complete `eventScripts` array, and add new atomic members beside it. A verified replay-fence derivation replaced request/reset handlers and added two Int4 evidence tags. Export contained all seven inherited members plus both additions and exactly one effective event per overridden trigger.

This supported shape does not change the nested-UDT boundary. An ordinary Folder is part of the owning UDT definition; an inherited child `UdtInstance` is a separate typed definition boundary. The Gateway separately rejected adding a brand-new descendant beneath the latter. Extend the child UDT type itself or compose a sibling when the target is an inherited `UdtInstance`.

After a Folder override, export the complete effective Folder, verify all inherited and new member names, verify complete event arrays and qualified `changeTypes`, instantiate a Control, run behavior, reset new and inherited evidence together, and inspect the bounded logs.

## Gate a reset on an acknowledged alarm occurrence

Put the authorization logic in a new sibling ordinary Folder when it must read one inherited Folder and call another. Derive the gate, UDT, and target roots from the event's text path, for example `str(tagPath).rsplit('/', 1)[0]`; do not call object methods such as `tagPath.getParentPath()` on the verified Unicode-text event argument.

Fence the request with all of these conditions before forwarding:

- a nonblank caller-supplied expected alarm UUID;
- an exact match to the warning occurrence UUID retained by the alarm callback;
- an exact match to the callback-latched acknowledged UUID;
- a true acknowledged-evidence Boolean.

Retain separate expected-identity, unacknowledged, and accepted counters plus the last forwarded trigger. Acknowledgement authorizes a later reset; it must not perform the reset by itself. After the gate writes the target trigger, wait independently for the gate's `FORWARDED` evidence and the target Folder's own `RESET` state/marker. Good write quality proves dispatch only.

Export can become less detailed at another inheritance depth: a newly added sibling Folder may be fully materialized while a twice-inherited Folder appears only as name/type stubs. In that case, verify the complete inherited scripts and alarms on the direct base export, verify exact member identity/count on the deeper derived export, and prove effective behavior at runtime. Keep the bounded Gateway-log interval for both stopped discoveries and clean runs.

When one acknowledged occurrence may authorize only one reset, further derive the gate Folder, replace the complete `RequestTrigger` event script, and add a String `LastConsumedWarningEventId` plus Int4 `DeniedReplayCount`. Evaluate expected identity and acknowledgement first, then deny when the current warning UUID equals the consumed UUID. On the accepted branch, retain the UUID as consumed; on replay, leave the downstream reset trigger unchanged and increment only replay evidence. This is an in-memory application fence, not an atomic compare-and-swap or durable exactly-once guarantee.

Re-arm that fence by correlation identity rather than by clearing it. A later alarm activation must provide a distinct UUID; accept that fresh UUID while moving the former current UUID to `PreviousConsumedWarningEventId`. Preserve previous/current values on replay denial. This gives operators a two-occurrence diagnostic trail without making the older occurrence eligible again.

## Add bounded DataSet history to an inherited Folder

Further derive the ordinary gate Folder to add a typed capacity parameter, a memory DataSet, an eviction counter, and a separate reset trigger. Use explicit columns such as event UUID, previous UUID, request identity, and Date. Append only after the command is accepted; delete row zero until the configured capacity is met and increment eviction evidence for every deletion. Do not rewrite the DataSet on denial branches.

Read complex values through the bounded complex-read API. Require exact column names and Java types, Good quality, `truncated: false`, and exact rows. Compare `timestampMillis` as well as row content across a denied replay to prove that no write occurred. Reset history through an API-written trigger whose event script uses `system.dataset.clearDataset`; read back zero rows and a zero eviction counter.

Test capacity with more accepted occurrences than retained rows. For capacity two, require progression `[first]`, `[first, second]`, then `[second, third]`; eviction must remain zero until the third append and become one afterward. Preserve each row's previous-event lineage. Replay after every stage, not only after eviction, because a denial can accidentally rewrite an equal-looking DataSet and still change its QualifiedValue timestamp.

Add a separate compaction trigger when retention must react to a reduced runtime parameter without accepting a new event. Read the existing DataSet and counters, delete row zero until within the current capacity, and increment eviction once per removed row. On a zero-removal trigger, update only compaction/no-op counters; omit the DataSet and eviction tag from the write list so their values and timestamps remain stable. Extend the explicit history reset to clear the new counters.

## Keep accepted and denied histories independent

Add a second typed DataSet when rejected requests need their own bounded diagnostic trail. A proven six-column schema is `Decision` String, `RequestTrigger` Integer, `ExpectedEventId` String, `WarningEventId` String, `AckEventId` String, and `ObservedAt` Date. Append on every denied branch, cap by deleting row zero, and maintain a denial-only eviction counter. On `FORWARDED`, omit the denial DataSet and its counter from the write list; likewise, denial writes must omit accepted history.

Test mixed denial categories beyond capacity, not merely repeated copies of one branch. At capacity two, blank-expected, stale-expected, unacknowledged, and three replay denials must finish with only the last two replay rows and four evictions. Compare rows and `timestampMillis` across each accepted request and across accepted-history compaction to prove the denial DataSet was not rewritten. Give denial history its own reset trigger and require that it clears only denial rows/evictions while accepted authorization and history remain unchanged.

Keep cleanup batches within the API's advertised write cap. The verified test stopped when a 33-plus-write cleanup was submitted to a 32-write action, even though all UDT behavior had passed; split cleanup into bounded calls and retain the stopped interval's focused and ERROR+ logs before retrying.

## Correlate denial history with a summary Document

Add a Document when consumers need the latest denial without scanning the bounded DataSet. Build both from one captured Date: append that Date to the row and store `getTime()` in the Document. Include an explicit schema version, state, retained row count, eviction count, latest decision/request, expected/live/acknowledged UUIDs, and observed milliseconds. Write the DataSet, eviction counter, and Document in the same checked `writeBlocking` batch; describe this as correlated evidence, not an atomic transaction.

A minimal further derivation needs to restate only the complete request script, the complete denial-reset script, and the new Document member. Its deeper export can list unchanged inherited members as name/type stubs. Validate the 21-member effective identity set there, but inspect inherited DataSet schemas, capacity parameters, and maintenance scripts on the direct parent export. The new schema parameter belongs only to the derived export.

Cross-read both complex tags after every denial. Require the newest row's decision/identities and Date milliseconds to equal the Document, and require its retained-row/eviction fields to match the DataSet/counter. Across acceptance and unrelated history compaction, compare both Document value and QualifiedValue timestamp for no-write proof. The denial reset must clear the DataSet/counter and replace the Document with a complete RESET value while leaving accepted history and authorization unchanged.

## Record first-transition-only integrity incidents

Further derive a lifecycle-integrity observer when operators need a bounded history of distinct integrity episodes rather than one continuously changing GAP projection. Override only the complete lifecycle DataSet event script. Keep alarm callbacks, acknowledgement evidence, lifecycle history ownership, and the inherited integrity Document/reset separate.

Add a typed positive capacity, an eight-column incident DataSet, Int8 cumulative incident and eviction counters, a Boolean latch, and an independent reset trigger. A useful row contains incident sequence, first/last retained lifecycle sequence, missing and out-of-order counts, retained rows, lifecycle scalar sequence, and one native Date. On every lifecycle callback, continue updating the inherited integrity Document. Append an incident only when the computed state is GAP and the latch was false; set the latch in the same checked write. While GAP persists, omit the incident DataSet and both incident counters from the write list so rows and QualifiedValue timestamps remain unchanged. Clear only the latch after a CONTIGUOUS or EMPTY commit.

Use the cumulative incident count as the row identity; do not reuse it after DataSet reset. Cap oldest-first and increment eviction once per removed row. Permit incident-history reset only while the latch is false, clear rows and evictions, and preserve the cumulative incident count. Give incident commits and resets their own child logger so base callbacks, integrity observations, and incidents have independently testable cardinalities.

Create test gaps with a deterministic lifecycle transition rather than racing a short alarm-active window. The verified fixture advanced the lifecycle scalar, deliberately cleared the occurrence, recorded the first GAP incident on that clear, then acknowledged the cleared occurrence and proved it was a duplicate GAP callback. Resetting lifecycle history re-armed the latch. Three episodes at capacity two retained incidents two and three with one eviction; independent incident reset cleared rows/evictions while count three survived.

Across three unchanged runs, the derived export had 44 outer and 66 nested members. Every run produced 23 base, 20 integrity, and 4 incident INFO records, a quiet Control instance, full restoration, and zero Gateway ERROR-or-higher rows. Two earlier timer-race runs were preserved as stopped evidence; both restored and also had zero errors.

## Correlate integrity incidents with a latest Document

Further derive the incident-history type when consumers need the newest distinct integrity episode without scanning the bounded DataSet. Add only a typed schema-version parameter and `ExtensionLimitIntegrityIncidentSummary` Document, then completely replace the lifecycle observer and incident reset scripts. Construct the incident row and `RECORDED` Document from the same computed values and one captured native Date. Include retained rows, incident evictions, cumulative incident count, incident sequence, first/last lifecycle sequence, gap/out-of-order counts, lifecycle scalar sequence, and detected milliseconds.

Write history, eviction count, cumulative count, and Document in one checked `writeBlocking` batch only for GAP with latch false. On every duplicate GAP callback, omit all four incident-owned values; prove both the DataSet and Document values and QualifiedValue timestamps remain unchanged. Lifecycle reset may re-arm the latch but must also preserve the latest incident Document byte-for-byte and timestamp-for-timestamp.

Reset history, eviction count, and the complete Document together only while unlatched. Preserve the cumulative scalar count and copy its current value into the RESET projection. During final restoration, clear the cumulative scalar first, invoke the owning reset trigger to rebuild a RESET/cumulative-zero Document, then return the trigger to zero; a zero trigger is ignored and must not add a reset record.

At deep inheritance levels, official export returns inherited members as name/type stubs and exposes only locally declared parameters. Validate the local Document, schema parameter, observer override, reset override, and effective 44/67 identity counts on the derived export; validate inherited capacity and values on the instantiated runtime or direct parent. Three clean API-only runs correlated three distinct incidents through capacity-two eviction, fenced three duplicate callbacks, preserved the summary across lifecycle resets, reset with cumulative count three, restored to cumulative zero, isolated Control, produced 23 base/20 integrity/5 incident INFO, and found zero bounded Gateway ERROR+ rows. Preserve the earlier zero-error stopped export-gate attempt as evidence of the stub rule.

## Add a sequence-fenced operator review command

Place review request, result, and counters as sibling memory tags inside the same nested control Folder as the incident summary. A trigger event can reach those siblings portably with `control_root = str(tagPath).rsplit('/', 1)[0]`; do not depend on Designer-only browsing or unsupported TagPath object methods. Read the latest incident Document, expected incident sequence, actor, prior review state, and counters together, require Good quality, and inspect every quality returned by the result write.

Evaluate branches in a deliberate order: deny when there is no current `RECORDED` incident, deny an actor that is blank or lacks the required qualified prefix, deny an expected sequence that differs from the latest incident, and deny a duplicate review of the same sequence. Only the accepted branch may publish `REVIEWED`, reviewed sequence, qualified actor, review milliseconds, and cumulative accepted count. Denials may update their own decision/counter evidence but must not rewrite incident history or its latest-summary Document.

When the lifecycle observer records a genuinely new first-GAP incident, clear prior review identity in that same checked evidence write and publish `UNREVIEWED`; persistent GAP callbacks must omit review fields. Preserve accepted review evidence across duplicate acknowledgement callbacks, lifecycle reset, and incident-history reset. The history reset may make the incident summary `RESET`, so a later review request must return `DENIED-NO-INCIDENT` without erasing the retained review evidence.

Test all four denials, multiple accepts, automatic clear on every new incident, exact actor/time/sequence fields, and both complex-value timestamps around every review action. Keep a separate review logger and a quiet Control review plane. Split final review cleanup from other cleanup if combining the writes would exceed the API action's advertised maximum. Three clean runs exported 44 outer/80 nested identities, produced 23 base/20 integrity/5 incident/11 review INFO, restored all review fields, and found zero bounded Gateway ERROR+ rows.

## Retain a bounded review-decision history

Further derive the review type when operators need the recent command trail, including denials. Add a typed positive capacity, a six-column DataSet, an Int8 eviction counter, and an independent reset trigger. Override only the complete review trigger script. A useful row contains decision, changing trigger, expected incident sequence, current incident sequence, actor, and one native observation Date.

Append exactly one row after every handled review branch, including `DENIED-NO-INCIDENT`, `DENIED-ACTOR`, `DENIED-STALE`, `DENIED-DUPLICATE`, and `REVIEWED`. Capture one Date before branch evaluation; use it for the row and use its milliseconds for accepted review evidence. Add the immutable `addRow` result, delete row zero until within capacity, increment eviction once per deletion, and submit decision evidence, history, and eviction count in one checked write.

Keep review history independent from new-incident review clearing, persistent GAP callbacks, lifecycle reset, and incident-history reset. Those branches must not touch its value or QualifiedValue timestamp. Reset review history with `clearDataset` through its own trigger while preserving review state, review counters, and incident complex evidence. If row count stays at capacity, wait on the exact eviction counter and review log before reading; row count alone can return the prior valid snapshot.

## Correlate review history with a latest-decision Document

Further derive the history type when consumers need one compact latest-decision projection. Add only `ExtensionLimitIntegrityReviewSummary`, a local positive Int4 schema-version parameter, and complete replacements of the review and history-reset triggers. Keep inherited history, eviction, review-state, incident, alarm, and lifecycle members at their owning depths. Deep export should therefore retain 48 root and 44 `AcknowledgedCoordinatorReset` identities, grow nested `CooldownControl` from 83 to 84, and expose only the local schema parameter plus the three complete local member definitions.

Capture one native Date and one branch result. After FIFO trimming, build a complete `RECORDED` Document containing schema/state, retained rows, evictions, decision, trigger, expected/current incident sequence, actor, and observation milliseconds. Write the row, eviction scalar, and Document in the same checked `writeBlocking` call. For accepted reviews, the row Date, Document milliseconds, and reviewed-at scalar must all be identical; denied branches still receive a row and Document time while leaving reviewed-at zero.

Reset history and the Document together. Use `clearDataset`, zero evictions, and a complete `RESET` object with every field present; preserve review state/counters and incident evidence. Prove unrelated GAP, alarm acknowledgement, lifecycle reset, and incident maintenance preserve both complex values and both QualifiedValue timestamps. Compare the Document by named fields plus timestamp rather than dictionary serialization order. At capacity, wait for the command marker and exact eviction scalar before correlating the newest row and Document.

Exercise a mixed eight-command sequence rather than repeating one branch. At capacity four, require retention of triggers 5–8 in exact order with decisions duplicate, reviewed, reviewed, and no-incident, plus four evictions. Verify native Date cells and accepted-row time equality, quiet Control history/logger, separate reset marker, bounded cleanup, and the all-Gateway ERROR+ interval. Three clean API-only runs exported 44 outer/83 nested identities and ended with 23/20/5/11/1 dedicated logs, zero errors, and complete restoration.

## Project retained and cumulative review decisions separately

Further derive the review-summary type when consumers need both the current bounded mix and lifetime decision totals. Add a typed `ExtensionLimitIntegrityReviewDecisionDistribution` DataSet with exactly two rows: `RETAINED` and `CUMULATIVE`. Recompute RETAINED by scanning the post-eviction review history. Build CUMULATIVE from the authoritative accepted/no-incident/actor/stale/duplicate counters after applying the current command. Capture one native Date and use it for both rows and the latest-review Document; write history, eviction count, summary, and distribution in the same checked batch. Describe this as correlated evidence, not an atomic transaction.

Keep maintenance ownership explicit. A distribution-reset trigger clears only the distribution. The next review command reconstructs both rows from retained history and lifetime counters. A review-history reset clears history and its latest-decision Document but rebuilds distribution as retained zeros plus preserved cumulative counters. A later distribution reset must leave RESET history/summary, review scalars, counters, and incident evidence unchanged. Verify the quiet Control distribution and logger independently. Three clean API-only runs retained 48 root/44 gate/86 nested identities, produced 23/20/5/12/1/2 focused INFO, restored, and found zero bounded Gateway ERROR+.

Add a versioned distribution-summary Document when clients need the two-row projection without DataSet parsing. Populate every retained and cumulative category from the exact values used to construct the rows, and reuse the same native Date milliseconds. Write history, latest-review Document, distribution, and distribution summary in one checked batch on commands. Compare the new Document by named fields plus QualifiedValue timestamp rather than dictionary serialization order.

Treat distribution reset as ownership of both distribution representations: clear the DataSet and publish a complete zeroed RESET Document together. Let history reset rebuild both as retained zeros plus preserved cumulative totals and a fresh shared Date. This keeps the summary truthful instead of leaving a stale RECORDED projection after its source DataSet is cleared. Three clean API-only runs retained 48/44/87 identities and the established 23/20/5/12/1/2 focused logs with zero Gateway ERROR+.
