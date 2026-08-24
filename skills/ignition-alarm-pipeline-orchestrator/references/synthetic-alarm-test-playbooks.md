# Synthetic Alarm Test Playbooks

Use this reference when planning a lab, staging, acceptance, rollback, or cleanup run for alarm notification behavior.

## Lab Rules

- Start read-only and confirm Gateway version, module state, project, tag provider, runner features, and time zone.
- Use unique disposable names for tags, users, schedules, rosters, profiles, and pipelines.
- Keep timings short enough to observe but long enough to capture evidence.
- Prefer Test Mode, local capture servers, fake recipients, or approved sandboxes before any live recipient.
- Use documented configuration, a vetted export, or a proven runner action for pipeline/profile resources.
- Do not fabricate alarm notification project-resource JSON.

## Basic Alarm Fixture

For a disposable alarm event:

1. Create or select a lab memory tag with one alarm.
2. Capture configured alarm properties, including priority, ack mode, shelving policy, display path, and associated data.
3. Trigger active, ack, clear, shelve, or unshelve paths as needed.
4. Capture current status and journal rows for the same source path and EventId.
5. Prove cleanup with status, shelved-path inventory, and tag existence checks.

## Notification Fixture

Before delivery testing:

- Name the profile, roster, user source, contacts, schedule, and sink.
- Run a safety gate for external channels.
- Prove the event entered the intended pipeline before interpreting delivery.
- Capture pipeline status, sink/provider output, focused logs, and audit rows when available.
- Separate local sink acceptance, module send attempt, and provider/carrier delivery.

## Acceptance Checklist

For a proposed pipeline, include:

- Route map and unwired exits.
- Recipient/channel matrix.
- Timing and escalation expectations.
- Dropout behavior for active, clear, ack, and shelve.
- Evidence sources required for sign-off.
- Pass/fail state, tester, approver, date/time, rollback owner, and notes.
- Rollback steps and resource-class cleanup checks.

## Rollback Checklist

After a lab change, prove the target is clean:

- Test pipelines are disabled, removed, or restored to their starting state.
- Test alarm assignments are removed or restored.
- No current or shelved disposable alarms remain.
- Disposable alarms are unshelved before final cleanup when needed.
- Disposable tag paths are gone.
- Disposable users, rosters, schedules, profiles, and pipelines are gone or restored.
- Logger levels, notification profiles, and service-security or Gateway Network settings are returned to the starting state.
- Any remaining evidence gap is named with the next safe proof step.
