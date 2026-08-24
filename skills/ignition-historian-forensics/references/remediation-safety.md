# Historian Remediation Safety

Use this reference whenever an investigation could lead to a historian write, configuration change, quarantine action, cache change, chart concealment, or direct database repair.

## Remediation Safety

Treat proof and repair as separate deliverables. A forensic report may recommend a repair path, but do not execute or present repair as evidence unless the user explicitly requested remediation and the plan is approval-required remediation.

- Recognize that `system.tag.storeTagHistory` is a historian write, not a diagnostic query. Before recommending a backfill, require source-of-truth values, qualities, timestamps, tag paths, realtime provider, history provider, timezone, duplicate handling, dry-run, readback, rollback or correction plan, and audit trail.
- Treat quarantine retry, delete, import, export, archive, and load actions as remediation or operational recovery. Verify the root cause first, preserve/export data before destructive actions, and never describe retry or delete as read-only proof.
- Treat tag history enablement, sample mode, deadband, tag group, storage provider, and cache changes as Gateway configuration changes. Record old/new values and expected future-row validation before recommending them.
- Do not repair historian evidence with direct `INSERT`, `UPDATE`, `DELETE`, or metadata edits against historian tables. Use SQL for read-only evidence unless the user asks for a separate database remediation plan.
- Do not make a chart or report "look right" by hiding null, bad-quality, or interpolated data. Explain what the visualization setting changes and whether it weakens forensic evidence.
