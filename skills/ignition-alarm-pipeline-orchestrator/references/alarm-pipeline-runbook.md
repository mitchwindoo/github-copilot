# Alarm Pipeline Runbook

Use this reference runbook when the task is about alarm notification orchestration in Ignition 8.1: why an alarm did or did not notify, why escalation repeated or stopped, how ack/clear/shelve state affected routing, or how to design a safer pipeline.

## Contents

- Scope And Trigger Detail
- Safety Boundary
- Evidence Classes
- Status And Journal Interpretation
- Triage Workflow
- Common Failure Patterns
- Report Template
- Report Contracts
- Adjacent Skill Routing

## Scope And Trigger Detail

Plan, troubleshoot, and explain Ignition 8.1 alarm notification pipelines, escalation paths, shelving, acknowledgement behavior, nuisance alarm routing, rosters, notification profiles, and current-status versus journal/audit correlation. Use when protecting plant trust in alarming while diagnosing who was notified, why an alarm did or did not route, why escalation looped or stopped, or how ack/shelve/clear state affects pipeline behavior.

## Safety Boundary

Before changing anything, classify the target:

- Production: read-only first; require approval before changing tags, pipelines, rosters, notification profiles, users, schedules, logger levels, or remote Gateway permissions.
- Staging or lab: still use unique names and cleanup steps.
- Notification channels: prefer Test Mode, capture servers, fake recipients, sandbox SMS/voice, or local simulation before live recipients.
- User/contact fixtures: use unique disposable users when a lab user source is manageable, and verify removal after the readback.
- Roster fixtures: use unique disposable static rosters in a lab when possible, read back membership order and empty roster behavior, and verify removal after the readback.
- Schedule fixtures: use unique disposable schedules/users in a lab when possible, check exact Gateway-time timestamps, and verify removal after the readback. For holiday checks, compare holiday-observing and holiday-ignoring users before, during, and after the holiday change.
- Remote Gateways: identify the owning Gateway and service permissions before any ack, shelve, or pipeline action.
- External sends: before email, SMS, voice, webhook, or remote Gateway notification work, run `scripts/notification_safety_gate.py <plan.json>` and resolve any blockers before continuing.
- Pipeline/profile fixtures: use Designer/Gateway configuration, a vetted export, or a proven runner action. Do not invent alarm notification project-resource JSON from names or assumptions.
- Cleanup proof: after lab mutations, record before/after checks for each resource class touched, including normal and include-shelved alarm status, shelved-path inventory, tag existence, and roster, user, schedule, profile, or pipeline presence as applicable.

Never infer notification success from pipeline entry alone. Delivery needs recipient/channel evidence, notification profile state, and sink or module logs. Treat local sink acceptance, Ignition Notification Block execution, and external provider or carrier delivery as separate proof layers. For sink evidence, preserve the channel, profile or endpoint, EventId, source/display path, event or send time, capture time, headers or envelope, and sanitized payload.

## Evidence Classes

Keep these separate until the timeline is aligned:

- Current status: the current lifecycle state of active, clear, acked, unacked, or shelved alarm events.
- Journal: historical transition rows for alarm lifecycle events.
- Audit: actor/action attribution only when the queried audit profile captures the relevant operation.
- Pipeline status: which event entered which pipeline and block path.
- Notification sink: email/SMS/voice/test-mode/capture-server output.
- Roster records: roster existence, static membership order, empty roster state, and the user source those members belong to.
- User/contact records: the user source, contact type, and contact value shape available to the notification profile.
- Schedule records: schedule model name, user assignment, checked timestamp, scheduled-user membership, schedule adjustment, and before/during/after holiday effect.
- Gateway logs: explanation for errors, dropouts, module failures, or pipeline script exceptions.
- Client/UI evidence: Alarm Status Table state, button availability, or client permission symptoms.
- Cleanup state: resource-class-specific before/after checks for any temporary alarms, shelves, tags, rosters, users, schedules, profiles, or pipelines.

Use absolute timestamps and the Gateway timezone. When timing order matters, record clock source, timezone, sample window or round-trip uncertainty, and estimated skew for each Gateway, sink, provider, client, or remote node before comparing events. Carry EventId, source path, display path, priority, state, pipeline, profile, roster, channel, and actor whenever available.

## Status And Journal Interpretation

Current status and journal rows answer different questions:

- Current status answers: "What is the alarm event doing now?"
- Journal answers: "What lifecycle transitions were recorded?"
- A single alarm event can appear as one current status row while the journal contains multiple transition rows.
- Journal profile storage settings decide which events exist in history before query filters run. Check minimum priority, Store Shelved Events, Query Only, and source/display-path profile filters before interpreting an empty journal result.
- Source path is the mutation and correlation anchor. Display path is often what operators recognize.
- Shelved alarms can be absent from normal current-status views. Query shelved inclusion explicitly when investigating a missing active alarm.
- Audit rows are useful only when the profile captures the relevant operation. A successful audit query, synthetic marker row, status result, or journal result does not prove ack, shelve, notification, or channel-ack attribution exists.

Do not rely on state or priority names without confirming the returned fields on the target. Some API results expose numeric values; map them in the local report rather than assuming every surface uses the same display strings. Under standard Ignition priority semantics, Diagnostic, Low, Medium, High, and Critical map to 0, 1, 2, 3, and 4; preserve the raw value beside any interpreted label before using it in branch logic or a report.

Associated data is event property data. Confirm it by reading the event object or by using `defined`, `all_properties`, or `any_properties` filters. Fixed status and journal datasets can omit custom fields even when the event object contains them, so keep the raw property name, value, and type in the investigation notes.

## Triage Workflow

1. Confirm context.
   Capture Gateway version/build, module state, timezone, project, tag provider, journal profile, audit profile, runner version/features, and safe work boundary.

2. Find the alarm event.
   Collect source path, display path, priority, current state, EventId, event time, associated data, ack mode, shelving policy, and active/clear/ack pipeline assignments.

3. Establish the lifecycle.
   Query current status and journal for the provider/source/display path. Compare active, clear, ack, shelve, and unshelve observations by EventId. Use a narrow time window around the issue.
   If journal rows are missing, determine whether the profile would have stored that priority, source/display path, and shelved/enabled/disabled event class before changing the query.

4. Determine whether the event entered a pipeline.
   Check pipeline assignment, pipeline enabled state, Alarm Notification module state, priority filters, branch expressions, and pipeline status. If the event never entered, inspect assignment and intake gates before delivery.
   For priority gates, check both the raw value and the display label before interpreting the branch.
   For associated-data gates, check the exact event key and value before interpreting the branch.

5. Trace the pipeline path.
   For each block, record whether the event passed, dropped, delayed, jumped, looped, consolidated, or failed. For expression or script blocks, capture the input data and the branch/result.

6. Trace recipients and channels.
   Resolve roster, schedule, calculated roster, user contacts, profile type, channel selection, and whether recipients are active for the event time. Distinguish empty roster, no matching contact method, disabled profile, failed delivery, and successful delivery to the wrong recipient.
   Confirm contact records on the same user source the roster/profile resolves. Treat `email`, `sms`, `phone`, all-contact, and no-contact users as separate cases; a non-empty roster is not enough to prove channel eligibility.
   For static rosters, read back the exact roster name, member list order, and empty roster state. Treat schedule filtering, calculated roster output, and delivery status as separate checks.
   For schedules, evaluate the exact event timestamp in the Gateway timezone. Use the assigned schedule model plus scheduled-user membership checks to distinguish "user not in roster" from "user in roster but off shift." For holidays, compare a holiday-observing user with a non-observing control at the same timestamp before, during, and after the holiday change.

7. Explain ack, clear, and shelve effects.
   Ack requires the current event identity, not just a friendly display path. Clear and ack state can stop or continue escalation depending on dropout conditions. Shelving can hide active alarms from default status and may prevent or alter routing depending on when the event was shelved.
   Treat the alarm's shelving policy, actor, permission path, and execution scope as separate facts. A client UI may make shelving unavailable while a Gateway-scope script or remote service path still needs its own proof.
   Check `ackMode` before interpreting acknowledged dropout or pipeline entry. Auto, Manual, and Unused alarms can produce different current-status and journal shapes, so preserve the active, acknowledgement, and clear rows before reasoning about pipeline admission or dropout.
   When acknowledgement notes are required, distinguish an omitted notes argument from an explicit empty or null note value, and record both the returned error or failed-ID list and the follow-up state before retrying. Treat client UI enforcement, Gateway-scope scripting, and notification-channel acknowledgement as separate surfaces until the target proves otherwise.
   When actor attribution matters, query the specific audit profile for the same action, source, EventId, target, actor, and time window. Treat profile access or unrelated audit rows as proof of audit plumbing only.

8. Check distributed permissions when relevant.
   For Gateway Network alarming, identify the owning Gateway, remote service visibility, alarm status service permission, detailed ack/shelve permissions, security zones, and module placement. Do not assume a Gateway that can display an alarm can mutate it.

9. Close with a bounded recommendation.
   State what was observed, what is inferred, what remains unproven, and the smallest safe validation or remediation step.

## Common Failure Patterns

- Pipeline disabled or not assigned to the event transition.
- Active pipeline configured, but the issue happened on clear or ack.
- Branch expression filters by display text when the event uses numeric priority or associated data.
- Priority reports or route checks relabel 1, 2, 3, or 4 without carrying the raw event value.
- Associated-data fields are visible through the event object but absent from a dataset-style table, causing route or report logic to treat them as missing.
- Journal query filters are adjusted repeatedly while the profile's storage filters are ignored, so events filtered out at storage time are mistaken for nonexistent alarms.
- Delay, consolidation, or loop makes notification timing look like a delivery failure.
- Dropout condition stops escalation after clear, ack, or shelving.
- Roster is non-empty, but schedule leaves no active members at the event time.
- Roster exists, but static membership or member order differs from the expected escalation order.
- Roster exists and is empty, which is different from a non-empty roster filtered down by schedules.
- User is in the roster, but the checked event timestamp falls outside the assigned schedule.
- "Active now" is used to explain a past or future event without checking the event timestamp.
- Holiday suppression is assumed without before/during/after timestamp checks, or rotating on-call behavior is assumed from the schedule name instead of proven for that date.
- Recipient has a user profile but no contact method matching the notification profile.
- Recipient exists in a different user source than the roster/profile path being evaluated.
- Notification module/profile is present but unlicensed, disabled, or misconfigured.
- Alarm Status Table hides shelved events while the underlying event is still present.
- Shelving-disabled alarm configuration is treated as proof for one surface when another surface, such as Gateway-scope scripting or remote service access, has not been checked.
- Audit profile is queryable but does not capture the exact ack/shelve/notification/channel action, so actor attribution is unavailable.
- Remote Gateway service permissions allow visibility but not ack or shelving.

## Report Template

```text
Scope:
- Gateway/project/provider:
- Alarm source/display path:
- Pipeline/profile/roster/channel:
- Time window/timezone:

Timeline:
- Current status observations:
- Journal transitions:
- Pipeline path:
- Notification sink/profile observations:
- Audit/log observations:
- Missing sources:

Route:
- Diagram or block list:
- Branch/dropout/delay/loop/consolidation points:

Recipients:
- Roster/profile/channel matrix:
- Eligible recipients:
- Observed delivery or non-delivery:
- Expected recipient/channel/time:
- Observed recipient/channel/time:

Timing:
- Expected timing:
- Observed timing:
- Difference or dropout point:
- Clock source/skew:

Diagnosis:
- Directly observed:
- Inferred:
- Missing:
- Contradicted:
- Unproven:

Risk:
- Missed notification:
- Duplicate or looped notification:
- Nuisance/flood behavior:
- Permission/audit gap:

Next action:
- Read-only check:
- Safe change or sandbox validation:
- Smallest next proof step:
- Rollback/cleanup:
- Adjacent skill handoff:
```

## Report Contracts

### Recipient/Channel Matrix

Include one row per expected recipient path or observed delivery path. Carry these fields when available: pipeline branch, roster, schedule state, profile, channel, eligible recipient, expected send time, observed recipient, observed channel, observed send/capture time, delivery evidence source, and confidence label. Mark rows as missing or contradicted when the expected route has no matching sink/provider/log evidence or when the observed EventId/source path does not match the alarm under review.

### Event Timeline

Use absolute timestamps with timezone and clock source. Include current status, journal transitions, pipeline stage entries/exits, delay or consolidation windows, notification sends or sink captures, ack, clear, shelve, unshelve, dropout, cancellation, audit/log notes, and missing sources. Do not order cross-source events until clock skew or sample uncertainty is stated.

### Evidence Confidence

Label material facts as direct, inferred, missing, or contradicted:

- Direct: the source itself shows the fact, such as current status, journal row, sink capture, profile log, audit row, roster readback, schedule check, or runner response.
- Inferred: the fact follows from multiple direct observations, but no single source states it.
- Missing: the needed source was unavailable, blocked, disabled, not configured, or not yet tested.
- Contradicted: two evidence sources disagree on EventId, source path, timestamp order, recipient, channel, state, or route.

When evidence is missing, name the smallest safe next proof step instead of filling the gap with a likely story.

### Nuisance Risk Checklist

Call out plant-trust risks before deployment or after repeated escalation: duplicate branch paths, splitter fanout without dedupe, infinite or unbounded loops, jump paths with no bounded exit, delay or retry windows that exceed the response target, consolidation across unrelated areas, long voice queues or timeout chains, empty rosters, recipients without matching contact methods, unproven dropout assumptions, script blocks with external side effects, and audit gaps for operator actions.

### Acceptance Checklist

For an operator or owner sign-off package, include acceptance item, expected evidence, actual evidence, pass/fail state, tester, approver, date/time, rollback owner, and notes. Cover route map, recipient/channel matrix, timing and escalation expectations, dropout behavior for active/clear/ack/shelve, notification sink or provider proof, audit/log evidence when required, and cleanup proof for any lab resources.

### Rollback Checklist

For lab or staging changes, name each rollback action and proof: disable or restore test pipeline state, remove or restore alarm assignments, unshelve disposable alarms, clear or reset test tags, delete disposable users/rosters/schedules/profiles/pipelines, restore notification profile settings, restore service-security or Gateway Network changes, restore logger levels, and verify resource-class cleanup after the rollback.

### Next Proof Step

When a channel or module cannot be tested safely, report the evidence gap, why it is blocked, the smallest safe next action, the expected artifact from that action, who must approve it, and the fallback conclusion until that proof exists. Prefer read-only profile/module checks, Test Mode, local capture servers, fake recipients, or approved sandboxes before live sends.

## Adjacent Skill Routing

Stay with the alarm-pipeline workflow when the outcome depends on EventId/source/display-path correlation, route choice, recipient/channel behavior, escalation/dropout timing, ack/clear/shelve state, or remote alarm authority. Hand off only the implementation mechanics and bring the resulting evidence back into the alarm timeline.

- Tag/UDT alarm property inheritance: use the UDT skills.
- Expression syntax inside a branch or alarm property: use the expression-language skill.
- Jython script-block implementation: use the Jython script-builder skill.
- SQL over journal tables: use the SQL query-builder skill.
- Perspective Alarm Status Table UI work: use Perspective host/import or UI skills.
- Generic Gateway log diagnosis: use the log assistant, while this skill keeps the alarm-event semantics.
