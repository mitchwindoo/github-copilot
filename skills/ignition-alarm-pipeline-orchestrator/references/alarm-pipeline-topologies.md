# Alarm Pipeline Topologies

Use this reference when designing, reviewing, or troubleshooting pipeline paths, branch choices, escalation, dropout, fanout, or nuisance behavior.

## Topology Inventory

For each pipeline involved, capture:

- Pipeline name and enabled state.
- Event transition assignment: active, clear, ack, or another configured path.
- Block order, branch names, and unwired exits.
- Delay, loop, jump, splitter, consolidation, notification, and script blocks.
- Dropout conditions and their intended exit behavior.
- Profile, roster, schedule, and calculated roster references.

## Intake Questions

Before editing blocks, prove whether the event entered the expected pipeline:

- Was the pipeline assigned to the alarm transition that occurred?
- Was the pipeline enabled when the event transitioned?
- Did the Alarm Notification module and relevant notification module report a usable state?
- Did branch filters compare the actual event property, raw priority, state, or associated-data value?
- Did the event drop before reaching delivery, or reach delivery and fail later?

## Branch And Expression Review

- Prefer exact event properties over friendly labels when the target surface exposes raw values.
- For priority routing, carry both the raw value and the mapped label.
- For associated data, verify spelling, case, spacing, value, and type on the event object.
- Treat unwired branches as deliberate filters only when the report says so.
- Keep expression syntax review separate from alarm-routing proof.

## Escalation And Nuisance Risk

Flag these risks before live enablement:

- No bounded exit from a loop.
- Delay or retry windows that outlast the operator response target.
- Splitters that duplicate notifications without recipient dedupe.
- Consolidation that mixes sites, areas, or recipient groups.
- Ack, clear, or shelve dropout assumptions that were not proven on the target.
- Script blocks with external side effects, such as webhooks or database writes.

## Source-Side Nuisance Checks

Before blaming a pipeline delay, loop, consolidation rule, or notification profile, check whether the alarm event itself is being shaped by tag-alarm behavior:

- Compare alarm on-delay and off-delay with pipeline Delay blocks; they act at different layers and need separate status/journal proof.
- Verify deadband with values on both sides of the expected clear threshold before treating repeated notifications as a pipeline-only issue.
- Treat Any Change alarms as event generators that can create more than one live EventId for the same source during rapid value changes.
- Treat Bad Quality alarms as quality-driven lifecycle events; record the tag quality and event value because the event value can be absent or not useful.
- If an alarm is disabled while active, re-query status and journal before assuming the event cleared, dropped out, or reached a pipeline exit.
- If priority or associated data changes while an alarm is already active, verify the current EventId's event object before assuming route expressions or message templates will see the new configuration values.

## Design Output

For design work, return a compact route map, recipient/channel matrix, timing rules, dropout assumptions, acceptance checks, and rollback path. For troubleshooting, show the observed path, where proof stopped, and the next safest check. For nuisance review, call out duplicate paths, unbounded loops, jump paths with no bounded exit, long delay or voice timeout chains, empty rosters, missing contact methods, cross-area consolidation, and script side effects before recommending live enablement.
