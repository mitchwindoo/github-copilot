---
name: ignition-perspective-button-logging
description: Build, review, and verify Ignition 8.1 Perspective button-press logging workflows for HMI troubleshooting and auditability. Use when Codex needs to instrument Perspective buttons, commands, UI-only actions, operator acknowledgements, audit records, logger records, custom SQL action logs, or browser/API verification that a button press was captured.
---

# Ignition Perspective Button Logging

Skill version: `1.0.73`
Stack version: `starter-2026.07.06.04`
Ignition target: `8.1`

## Boundaries

Use the Project Library helper pattern for button/action logging. Direct SQL inserts, Named Query inserts, native audit checks, non-Button controls, and disabled/gated command controls are target-sensitive; verify the relevant Gateway settings and readbacks on each target.

Do not assume native audit captures UI-only Perspective actions. Add explicit action logging for popups, navigation, custom prop changes, blocked commands, and other operationally important UI actions.

Use Gateway/session message-handler logging only when the target has a verified handler path. Otherwise use component event wrappers, Project Library helpers, and packaged Named Queries.

## Core Pattern

Use a hybrid logging design for important Perspective buttons:

1. Keep native project auditing enabled for built-in auditable actions, but verify Gateway/project audit settings on each target.
2. Put important button scripts on `events.component.onActionPerformed`.
3. Keep the Perspective event script thin; call a Project Library helper with explicit context.
4. Log intent, execute the command, then log result.
5. Write a manual `system.util.audit(...)` record for audit-trail visibility.
6. Write `system.util.getLogger(...)` messages for troubleshooting.
7. Insert an append-only SQL/Named Query action row when page/session/button fields, previous values, new values, outcomes, or correlation IDs matter.
8. Verify with browser clicks plus API/readback evidence; `pageValidate` alone does not confirm that button logging works.

Do not assume native auditing captures every UI-only button press. Buttons that only open popups, navigate, change custom props, or run custom logic need explicit logging if they matter operationally.

## Button Event Rules

- Prefer `onActionPerformed` for Button actions. One-Shot Button, Multi-State Button, Checkbox, and Dropdown can use the same event wrapper pattern when their values are captured explicitly. Use pointer/click events only when pointer behavior is the actual requirement.
- Add a stable key such as `custom.auditKey` or a view param. Do not rely on labels, component names, or changing page layout as the permanent identity.
- For non-Button controls, pass the selected/control value from component props, not from guessed event fields: Button `props.text`, One-Shot Button `props.value`, Multi-State Button `props.controlValue`, Checkbox `props.selected`, and Dropdown `props.value`. Treat Multi-State `props.indicatorValue` as feedback unless it is explicitly bound as the command value.
- Pass `session.props.id`, `page.props.pageId`, `page.props.path`, actor/user, button key, target path, requested value, and correlation IDs into the Project Library helper.
- Read previous values before writes when troubleshooting or forensics require before/after records.
- Use `system.tag.writeBlocking([path], [value])` when the next log line must include the actual write `QualityCode`. Check each QualityCode and verify readback for critical commands.
- For UI-only or unavailable actions, record an explicit outcome such as `UI_ONLY`, `NAVIGATED`, `POPUP_OPENED`, `BLOCKED_INTERLOCK`, or `BLOCKED_MISSING_DEPENDENCY` so the log does not look like a failed tag write.
- Do not rely on `props.enabled` as the only guard for important commands. The Project Library helper should re-read dependencies/interlocks, return/log the blocked reason, and verify that blocked target tags did not change.

## Jython/Audit Rules

- Use `system.util.audit(...)`, not `system.audit.write`.
- Use `java.util.UUID.randomUUID().toString()` for correlation IDs unless the target Gateway has a verified helper. Do not assume `system.util.getUUID()` exists in Ignition 8.1.
- Keep `originatingSystem` as an even-length list such as `["page", pagePath, "pageId", pageId, "sessionId", sessionId, "correlationId", correlationId]` so Ignition can retain/generated context plus your details.
- For audit readback diagnostics, call `system.util.queryAuditLog` with keyword arguments or omit `contextFilter`; the positional `contextFilter` argument is an integer bitmask in Ignition 8.1, not a string wildcard.
- Use `system.util.getLogger` for debug/troubleshooting evidence separately from audit records. When validating through wrapper logs, filter by a stable suffix, message text, or correlation ID because dotted logger prefixes may be abbreviated.
- Catch Java-backed failures from SQL, tags, audit, and log probes with `java.lang.Exception` or `java.lang.Throwable` in diagnostic code, then return a bounded status object.

## SQL Log Table Rules

Prefer a Named Query for production inserts when the action log should be packaged and API-verified. Use a Gateway/Session message handler only when that handler already exists as a target prerequisite or has been created through a verified runner/resource path. If using direct SQL from a Perspective/session script, use prepared parameters, an explicit database connection, and `skipAudit=True` for the logging insert when duplicate query audit records would create noise.

For Named Query action logs, package the Update Named Query as a dependency when possible, preserve its `resource.json` metadata, call `system.db.runNamedQuery(projectName, queryPath, params)`, validate every required param name before the call, and verify the returned affected-row status plus a bounded readback.

Use an append-only action table with fields like:

- `event_ts`, `project_name`, `session_id`, `page_id`, `page_path`
- `actor`, `actor_host`, `button_key`, `event_name`
- `target_path`, `previous_value`, `new_value`
- `outcome`, `write_quality`, `audit_status`, `correlation_id`, `action_json`

Validate identifier fragments from strict allowlists; bind values with parameters. Index by timestamp, session, page, actor, button key, and correlation ID when forensic lookup matters.

## Host/API Validation

When API access exists, verify the workflow through the approved Web Dev runner:

1. Call `health` first and inspect `supportedActions` for callable actions plus `features` for capability flags.
2. Discover routes/views/tags/named queries/logs before writes.
3. Create any temporary validation tags with `tagConfigure` dry-run/apply under approved prefixes.
4. Apply the Perspective package with dry-run first, then `confirmApply: "APPLY"`.
5. Run `pageValidate`, `viewRead`, and focused `logQuery`.
6. Browser-open the route and click at least one tag-writing button and one UI-only or blocked button when the workflow supports them. For disabled controls, verify the normal click is blocked and use a deliberate guard-probe/bypass path to confirm the helper still returns a blocked outcome.
7. Verify tag results with `tagRead`.
8. Verify SQL action rows with a bounded diagnostic query or Named Query preview.
9. Verify audit rows with a bounded `queryAuditLog` diagnostic.
10. Verify logger rows with `logQuery` filtered by stable suffix/run ID/message.

When the user needs a durable diagnostic record, save sanitized requests/responses, browser screenshots, DOM/text observations, and negative findings in an agreed artifact folder. Preserve negative findings when they explain a reusable target boundary.
