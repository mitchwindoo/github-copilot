---
name: ignition-alarm-pipeline-orchestrator
description: Diagnose and design Ignition 8.1 alarm notification pipelines, escalation, rosters, schedules, acknowledgement, shelving, nuisance routing, delivery, and status/journal correlation.
---

# Ignition Alarm Pipeline Orchestrator

Skill version: `1.0.33`
Stack version: `starter-2026.07.06.04`
Runner compatibility: call `health` at runtime and load `references/webdev-runner-alarm-api.md` for validated current and minimum versions, feature boundaries, and fallbacks.
Primary target: Ignition `8.1.53`. Always confirm the actual Gateway version and build before making version-specific claims.

## Scope

Use this skill for alarm notification orchestration: pipeline topology, rosters, schedules, notification profiles, channels, escalation loops, dropout behavior, nuisance flooding, ack/clear/shelve effects, and distributed alarm permissions.

Do not use this skill as a general tag-modeling, SQL reporting, Perspective page-building, Jython-authoring, historian, or generic log-triage skill. Route those parts to the neighboring Ignition skills and keep this skill focused on alarm lifecycle and notification orchestration.

## Boundary Routing

Remain accountable when the user's final decision depends on alarm event lifecycle, notification route, recipient/channel behavior, escalation/dropout behavior, ack/clear/shelve state, or remote alarm permissions. Supporting evidence may come from logs, SQL, UI components, scripts, or UDT exports, but the alarm-event question still belongs here.

Hand off when the final deliverable is the adjacent implementation surface:

- UDT/tag model or inherited alarm properties: UDT skills.
- Expression syntax or expression-surface behavior: expression-language skill.
- Jython body for a script block, webhook, or automation: Jython script-builder skill.
- Alarm journal SQL, Named Queries, or reports: SQL query-builder skill.
- Perspective screens, Alarm Status Table layout, deployment, or performance: Perspective skills.
- Historian storage, retention, interpolation, or chart retrieval: historian skill.
- Generic log parsing or vendor bug lookup: log assistant.

## Reference Loading

- Load `references/alarm-pipeline-runbook.md` for end-to-end pipeline triage, report shape, state interpretation, and safety checks.
- Load `references/alarm-status-journal-evidence.md` when the work turns on status versus journal versus audit versus logs or sink evidence.
- Load `references/alarm-pipeline-topologies.md` when designing or reviewing branch, delay, loop, splitter, jump, consolidation, dropout, or escalation behavior.
- Load `references/rosters-and-calculated-rosters.md` when recipients, contacts, schedules, holidays, rosters, or calculated rosters are central.
- Load `references/ack-shelve-service-security.md` when acknowledgement, notes, shelving, client permission, Gateway script authority, or remote Gateway service permissions matter.
- Load `references/synthetic-alarm-test-playbooks.md` when planning a lab, staging, acceptance, rollback, or cleanup run.
- Load `references/alarm-negative-scenario-patterns.md` when a case involves missing named resources, recipient/contact mismatches, wrong-event notification proof, outside operator actions, Gateway or project restarts, missing event properties, or scripted external side effects.
- Load `references/webdev-runner-alarm-api.md` before using the Web Dev runner for alarm status, journal, audit, log, Gateway Network preflight, or bounded diagnostic calls.
- Load `references/script-catalog.md` before running `scripts/notification_safety_gate.py` or when Python is unavailable and a manual safety review is required.

## Non-Negotiables

- Start read-only whenever possible: confirm Gateway version, module state, runner supported actions and feature flags, tag providers, current alarm status, journal availability, audit availability, and focused logs before proposing changes.
- Do not send real email, SMS, voice, webhook, or remote-Gateway notifications unless the user has named the sandbox or approved the exact live recipient path.
- For planned notification sends or profile changes, run `scripts/notification_safety_gate.py` against a JSON plan before any external channel is used. Treat blockers as a stop condition until the plan names a sandbox target or carries explicit live approval.
- Do not infer delivery success from pipeline status or a send attempt alone. Delivery proof needs controlled sink or provider evidence with channel, profile or endpoint, EventId, source/display path, event/send time, capture time, headers or envelope, and a sanitized payload.
- For recipient or channel claims, verify the user source and each user's contact records for the intended profile type. Treat email, SMS, phone/voice, multi-contact, and no-contact users as different routing cases.
- For roster claims, verify the roster name, static membership order, empty roster behavior, user-source/contact alignment, and schedule filtering as separate facts. Treat calculated rosters as pipeline-block evidence until proven on the target.
- For multi-contact users, preserve the full contact-method readback and do not assume which same-channel contact a Notification Block will select until delivery evidence proves it.
- For dynamic or merged rosters, quote and escape roster names with spaces or punctuation for the target expression surface and dedupe overlapping recipient candidates deliberately.
- For schedule claims, use Gateway-time and date-specific evidence. Separate the assigned schedule model, user schedule assignment, scheduled-user membership, schedule adjustments, holiday behavior, roster membership, contact records, and delivery result. For holiday behavior, compare holiday-observing and holiday-ignoring users at the same checked timestamp before, during, and after the holiday change.
- Do not fabricate alarm notification pipeline or notification profile resources from guessed project-resource JSON. Use documented Gateway/Designer configuration, a vetted export, or a proven runner action, then validate in a sandbox before enabling live recipients.
- For lab or staging mutations, prove cleanup by resource class before closing: alarm status with and without shelved inclusion, shelved-path inventory, tag existence, and exact roster, user, schedule, pipeline, and profile presence for resources touched. Do not treat tag deletion alone as proof that alarm state or notification resources were cleaned up.
- Treat current status, journal rows, audit rows, pipeline status, notification sink output, and Gateway logs as separate sources. Do not merge them into one timeline until timestamps and timezones are aligned.
- For escalation timing or disputed order of events, record each source clock, timezone, sample window or round-trip uncertainty, and estimated skew before comparing Gateway, sink, provider, client, or remote-Gateway timestamps.
- Carry event-level identifiers through the work: provider, source path, display path, EventId, priority, state, timestamps, pipeline name, profile, roster, recipient/channel, and actor when available.
- Make shelved-alarm intent explicit. For missing-active-alarm investigations, query both normal status and status with shelved alarms included when the runner or Ignition API supports it.
- Verify shelving with multiple facts: normal status visibility, status with shelved alarms included, shelved-path inventory, timeout or expiration, and the actor/scope that performed the shelf. Short shelves can return an alarm to normal status while the condition is still active, re-shelving can shorten expiration, and timeout-zero behavior can remove a shelf on Gateway-scope paths; re-query before calling shelving a durable suppression.
- Treat shelving path strings as evidence, not assumptions. A display path may be accepted on some targets, but the qualified source path from current status or journal evidence is the clearest disambiguator; wildcard-style source strings can affect multiple alarms and need blast-radius proof before use.
- Do not assume a disabled shelving policy blocks every shelving path. Confirm the actor and execution scope; client UI availability, Gateway-scope scripting, and remote service permissions can differ.
- When status or journal rows expose numeric state fields, map or show the numeric values before writing operator-facing state labels.
- Treat journal profile storage rules and `queryJournal` filters as separate layers. Confirm the target profile's minimum priority, Store Shelved Events, Query Only setting, and source/display-path filters before treating missing journal rows as missing alarm events.
- When routing or reporting depends on priority, preserve the raw priority value and mapped label; verify whether the target surface expects numeric comparison values or canonical names before editing branch logic.
- When routing or reporting depends on associated data, verify the exact event property name and value through the event object or property filters; do not assume fixed status or journal datasets include custom fields.
- For nuisance behavior, separate source-side alarm lifecycle controls from pipeline controls before changing notification logic. Check alarm on-delay, off-delay, deadband, Any Change, Bad Quality, enabled state, and whether the current EventId is carrying active-time snapshots of priority or associated data.
- Confirm each alarm's ack mode before reasoning about acknowledged dropout or pipeline entry; Auto and Unused alarms can produce different status/journal shapes from Manual alarms.
- For acknowledgement retries, treat EventId as the mutation boundary. A cleared-unacknowledged event, a duplicate retry, a stale EventId, and a later event from the same source can all behave differently; inspect failed-ID lists and re-query each intended event before declaring success or no-op behavior.
- For notes-required acknowledgements, preserve returned errors or failed-ID lists and confirm the post-ack state before retrying; do not assume every client, script, or Gateway scope enforces notes the same way.
- Treat audit profile access as plumbing, not attribution. Do not promise actor identity for ack, shelve, unshelve, notification, or channel acknowledgement until action-specific rows from the target audit profile prove those operations are captured.
- Keep reusable examples generic. Use placeholders such as `[<provider>]Area/Device/PV`, `<AlarmName>`, `<PipelineName>`, `<RosterName>`, and `<NotificationProfile>`.

## Required Workflow

1. Define the alarm question.
   Identify whether the user needs routing design, missing notification triage, repeated escalation, nuisance suppression, acknowledgement/shelving behavior, remote Gateway behavior, or an operator-facing incident summary. Record production impact and the safe work boundary.

2. Establish Gateway and alarm context.
   Confirm Ignition version/build, Alarm Notification module state, relevant notification modules, timezone, project, tag provider, journal profile, audit profile, runner version, supported actions, feature flags, and whether the work is production, staging, or a disposable lab.

3. Identify the event surface.
   Find the alarm's source path and display path. Current status answers what the alarm event is doing now; the journal answers how the event moved through lifecycle transitions. Use both when diagnosing notification behavior.
   For journal gaps, separate events that were never stored by the journal profile from events filtered out by the query.

4. Build an event timeline.
   Correlate active, clear, ack, shelve, unshelve, notification, dropout, and escalation observations by EventId and source path. Keep state changes, pipeline stages, recipient/channel decisions, and operator actions in timestamp order.
   Use audit only for operations that the target profile actually stores; a queryable audit profile or unrelated marker row does not prove ack, shelve, notification, or channel-ack attribution.

5. Triage routing and escalation.
   Inspect pipeline assignment, enabled state, branch expressions, delays, jumps, loops, dropout conditions, rosters, schedules, profiles, and channel contact data. Distinguish an event that never entered a pipeline from one that entered and then dropped, delayed, looped, or failed at delivery.
   For recipient gaps, prove the user source is the one the roster/profile uses and that the selected users expose the expected contact type before changing pipeline logic.
   For roster gaps, prove the roster exists and read back static member order or empty membership separately from schedule activity, calculated roster output, and notification delivery.
   For schedule gaps, evaluate the exact event timestamp in the Gateway timezone. Prove whether the selected user is scheduled at that timestamp before changing rosters, profiles, or pipeline logic.
   For priority branches, compare the event's raw priority value with the target expression or filter semantics before changing routing.
   For associated-data branches, prove the property exists on the event and check exact spelling, spacing, case, and raw value before changing branch logic.

6. Triage nuisance behavior safely.
   Separate alarm source behavior from pipeline behavior. Check priority, display path, associated data, ack mode, shelving policy, shelving actor/scope, deadband/delay assumptions, repeated state changes, and whether shelving or dropout hides the symptom instead of fixing the root cause.

7. Triage permissions and distributed behavior.
   Separate client UI permission, Gateway script authority, notification-channel acknowledgement, and remote Gateway service permissions. For Gateway Network cases, identify the owning Gateway before reasoning about remote ack, shelve, query, or pipeline access.

8. Report with clear confidence.
   Return the question answered, the observed timeline, likely cause, what remains unproven, safe next actions, rollback or cleanup status for any changes, and the exact source classes used.

## Runner Use

When the approved Web Dev runner is reachable, call `health` first and inspect `runnerVersion`, `stackVersion`, `supportedActions`, `features`, and token state. Treat `supportedActions` as callable actions and `features` as capability flags. Prefer narrow, bounded calls:

- `gatewayInfo` for Ignition version, timezone, module state, and environment context.
- `gatewayNetworkPreflight` for read-only Gateway Network, security-zone, service-security, remote-notification, and alarm-module preflight before remote ack, shelve, query, pipeline, or notification reasoning.
- `tagProviders` before building provider-qualified source paths.
- `alarmStatusQuery` for current event state. Include provider/source/display-path filters, use priority filters deliberately, and use `includeShelved` when investigating shelves.
- `alarmJournalQuery` for historical event transitions. On runner `0.3.97+`, provide explicit `journalName`, `journal`, or `alarmJournal`; default/omitted journal flags are rejected because the runner cannot verify Ignition's exactly-one-journal omission condition. On runner `0.3.96+`, include a narrow source/path/displayPath filter and keep the window at or below `1440` minutes; provider/state/priority filters and a short window are supplemental, not a backend-work bound by themselves.
- `auditQuery` only after confirming the target audit profile and using narrow action/actor/target filters.
- `logQuery` for focused Gateway or wrapper log context tied to the same time window, EventId, source path, run marker, or pipeline/profile name.

Broad status, journal, audit, or log scans are exceptional. Narrow first; runner `0.3.96+` rejects broad alarm journal and audit query bypasses before backend work even when response caps are supplied.

## Output Shape

For pipeline incidents, return:

- Scope: Gateway/project/provider/alarm/pipeline/profile/roster/channel.
- Route view: a compact route diagram or block list when pipeline path, branch, dropout, delay, loop, or escalation behavior matters.
- Recipient matrix: roster, schedule, profile, channel, eligible recipients, observed recipients, and delivery status when notification choice matters.
- Timing line: expected versus observed timing for active, clear, ack, shelve, delay, consolidation, notification, retry, and escalation steps.
- Timeline: current status, journal transitions, pipeline stages, notifications, audit/log context, and missing sources.
- Diagnosis: what is directly observed, inferred, missing, contradicted, and still unproven.
- Risk: nuisance behavior, missed notifications, duplicate notifications, escalation loops, permission gaps, or audit blind spots.
- Action plan: lowest-risk next proof step or change, validation step, rollback/cleanup step, and any adjacent skill handoff.

For design work, return:

- Pipeline intent and branch map.
- Recipient/channel matrix.
- Delay, loop, dropout, and escalation rules.
- Ack/clear/shelve behavior assumptions to validate.
- Safe sandbox validation plan before live recipients are enabled.
