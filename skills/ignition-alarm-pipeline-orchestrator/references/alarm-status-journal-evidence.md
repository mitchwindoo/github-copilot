# Alarm Status, Journal, And Evidence

Use this reference when the question depends on what happened to an alarm event, whether history is missing, or which source proves a claim.

## Evidence Classes

Keep these sources separate until the timeline is aligned:

- Current status: current active, clear, acknowledged, unacknowledged, or shelved state.
- Journal: lifecycle history that the selected journal profile actually stored.
- Audit: actor and action attribution only when the target audit profile stores the action.
- Pipeline status: pipeline and block path participation.
- Notification sink or provider: channel delivery evidence tied to the EventId or source path.
- Gateway logs: focused error or module context, not a replacement for status or journal proof.
- Client/UI evidence: Alarm Status Table visibility, selection, and operator controls.
- Cleanup checks: before/after proof for every temporary resource class touched.

## Status Versus Journal

- Use current status to answer what the event is doing now.
- Use the journal to answer which transitions were recorded over time.
- Carry provider, source path, display path, EventId, state, priority, and timestamps together.
- Query shelved inclusion explicitly when an active alarm appears to be missing.
- Preserve raw numeric state and priority values before writing operator-facing labels.

## Journal Gaps

Separate storage from query filters:

- Confirm the selected journal profile and its storage settings before treating an empty result as proof that no event happened.
- Check minimum priority, Store Shelved Events, Query Only behavior, source filters, and display-path filters.
- If associated data matters, prove it through the event object or property filters; fixed datasets may omit custom fields.

## Audit And Logs

- Treat audit availability as plumbing until action-specific rows prove attribution.
- Query audit by the same time window, action class, target/source, actor, and EventId when available.
- Use focused logs for explanations such as module errors, script exceptions, failed delivery attempts, or resource load issues.
- Do not infer operator identity from status or journal fields unless the field explicitly supplies it.

## Report Notes

Label each fact as observed, inferred, missing, or contradicted. When evidence is missing, name the smallest next proof step instead of filling the gap with a plausible story.
