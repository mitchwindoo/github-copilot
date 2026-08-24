# Safety and Scope

## Use This Skill For

- Slow Perspective page or route opens.
- Sluggish repeated navigation, tab switches, or click-to-visible interactions.
- High Gateway CPU, heap growth, session queue symptoms, or excessive Perspective messages.
- Large tables, trends, charts, embedded views, Flex Repeaters, View Canvas usage, or complex overview screens.
- Suspected query/tag/history polling, Cache & Share, binding transform, script, or data-source cost.
- Before/after remediation proof where the answer must be evidence-backed.

Do not use this skill as a generic page builder, SQL authoring skill, Jython authoring skill, or log-triage-only workflow. Use the Perspective host/import skills for guarded package writes and rollback when a fixture or remediation variant is required.

## Non-Negotiables

- Static findings are candidates only. Never call a static lint finding the cause without synchronized runtime or A/B evidence.
- Start read-only: `health`, `gatewayInfo`, project/route/view discovery, `viewRead`, `pageValidate`, logs, metrics, sessions, and browser evidence.
- On production, do not create fixtures, open many sessions, run load tests, capture thread dumps, or apply remediation variants without explicit user approval.
- Every profile run needs a unique `runId`; include it in request IDs, visible fixture markers, browser evidence, logs, and report filenames where possible.
- Keep secrets, hostnames, tokens, usernames, client addresses, full user agents, raw thread dumps, and customer-specific metric/session identifiers out of reusable notes.
- Prefer one small measurable change per remediation cycle, then rerun the exact same scenario and rollback or retain intentionally.
