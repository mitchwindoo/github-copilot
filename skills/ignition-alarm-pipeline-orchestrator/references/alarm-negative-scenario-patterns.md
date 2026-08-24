# Alarm Negative Scenario Patterns

Use this reference when alarm pipeline evidence looks like a failure, but the first risk is a bad reference, wrong event, outside action, restart, missing property, or scripted side effect rather than normal branch or recipient logic.

## Named Resources

Check exact names before explaining behavior: alarm journal profile, notification profile, pipeline, roster, user source, schedule, audit profile, project, tag provider, and source/display path. Treat a missing or misspelled resource as a configuration lookup failure until the target Gateway proves otherwise.

Report named-resource problems separately from alarm-event behavior:

- Resource name checked.
- Surface that used the name.
- Error, empty response, or fallback observed.
- Smallest correction or readback step.
- Whether any alarm event actually reached the intended pipeline or profile.

## Contact Eligibility Versus Delivery

A roster can contain active users and still have no eligible recipients for the selected notification profile. Resolve profile type, user source, user contact records, schedule state, and roster membership as separate facts before calling the delivery layer failed.

For each expected recipient, preserve the contact type being requested and the contact type actually present. A missing email, SMS, phone, or voice contact is a routing eligibility problem, not proof that a send attempt failed.

## Wrong Event Or Time-Adjacent Proof

Do not accept a sink capture, provider log, or pipeline status row as proof unless EventId and source path match the alarm under review. Time-adjacent notifications can be real sends for a different alarm.

When proof points at a different event, mark the result as contradicted and include:

- Expected EventId and source/display path.
- Observed EventId and source/display path.
- Shared or misleading fields, such as pipeline, profile, recipient, or timestamp.
- Next bounded check for the correct event.

## Outside Operator Actions

Manual acknowledgement, shelving, unshelving, clear, or channel acknowledgement can change escalation timing outside the route being tested. If an outside action occurs during the window, stop treating the timeline as a pure pipeline timing test.

Record the actor when available, the action surface, the source path, the EventId, and the timestamp. Use audit only when the target profile captures that action; otherwise report the action as observed by status, journal, sink, or log evidence without overclaiming attribution.

## Restarts And Project Saves

Gateway restarts, Alarm Notification module restarts, project saves, and Gateway scripting restarts are operational interruptions for in-flight delay, loop, consolidation, script, and notification behavior. Capture the interruption time before deciding whether a pipeline delayed, retried, skipped, continued, or restarted.

For interruption cases, include:

- What was in flight: delay, loop, consolidation, notification, script, or dropout.
- Interruption type and timestamp.
- Current status and journal rows before and after the interruption when available.
- Gateway log lines or module state changes in the same window.
- Whether the observed behavior is proved for the target or still needs a controlled sandbox run.

## Missing Event Properties

Branch expressions, notification messages, and script blocks can reference properties that are absent from the event. Confirm the exact event property name, spelling, case, spacing, value, and type before deciding a branch or template is wrong.

If a property is absent, report what the surface did with the missing value: blank substitution, expression false path, script exception, notification error, dropout, or continued pipeline execution. Keep missing-property behavior separate from recipient and delivery behavior.

## Scripted External Side Effects

Script blocks that post webhooks, write databases, call APIs, or run automation are side effects in the pipeline path. Treat them differently from built-in notification profiles.

For webhook-style script blocks, capture endpoint, timeout, returned status or exception, retry behavior if any, and whether the pipeline continued, dropped, looped, or produced a log entry. An endpoint-down result proves script-side behavior only; it does not prove email, SMS, voice, roster, or notification-profile behavior.
