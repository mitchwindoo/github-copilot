# Web Dev Runner Alarm API

Use this reference when the approved Ignition Web Dev runner is available for bounded alarm diagnostics. Call `health` first and treat `health.supportedActions` as the live action contract and `health.features` as the live capability-flag contract for the session. Prefer runner `0.3.98+` so alarm diagnostics also inherit exact-or-child path prefix guards from `pathPrefixBoundaryMatching`.

## Contents

- Compatibility
- Startup Snapshot
- Current Alarm Status
- Shelving Probes
- Acknowledgement Probes
- Alarm Journal
- Audit
- Focused Logs
- Guardrails
- Minimal Interpretation Checklist

## Compatibility

Runner API version: `0.3.148` current; `0.3.98+` remains the minimum for direct `alarmStatusQuery.includeShelved`, `gatewayNetworkPreflight`, explicit-profile `auditQuery`, `backendQueryWorkBounds`, `alarmJournalExplicitProfileRequired`, and `pathPrefixBoundaryMatching` support.

Treat that version statement as the validated package baseline, not a substitute for live discovery. Always call `health` and prefer the returned `runnerVersion`, `stackVersion`, `supportedActions`, and `features` when deciding what the connected runner can actually do.

## Startup Snapshot

```json
{
  "action": "health",
  "requestId": "<runId>-health"
}
```

Confirm:

- `runnerVersion`
- `stackVersion`
- `features`
- `tokenConfigured`

Then capture Gateway and provider context:

```json
{
  "action": "gatewayInfo",
  "requestId": "<runId>-gateway-info"
}
```

```json
{
  "action": "tagProviders",
  "requestId": "<runId>-tag-providers"
}
```

## Current Alarm Status

Use `alarmStatusQuery` for current state. On runner `0.3.96+`, always include at least one narrow source, path, or display-path filter; provider-only filters are supplemental and do not bound backend work.

```json
{
  "action": "alarmStatusQuery",
  "requestId": "<runId>-status",
  "sources": ["prov:<provider>:/tag:<path-or-pattern>"],
  "displayPath": ["<display/path/or/pattern>"],
  "includeShelved": false,
  "maxResults": 50
}
```

For missing-active-alarm or shelving questions, run the same query with `includeShelved: true` when `health.features` includes `alarmStatusQueryIncludeShelved`.

```json
{
  "action": "alarmStatusQuery",
  "requestId": "<runId>-status-include-shelved",
  "sources": ["prov:<provider>:/tag:<path-or-pattern>"],
  "displayPath": ["<display/path/or/pattern>"],
  "includeShelved": true,
  "maxResults": 50
}
```

To narrow by priority through the runner, pass canonical priority names:

```json
{
  "action": "alarmStatusQuery",
  "requestId": "<runId>-status-priority",
  "sources": ["prov:<provider>:/tag:<path-or-pattern>"],
  "displayPath": ["<display/path/or/pattern>"],
  "priorities": ["High", "Critical"],
  "maxResults": 50
}
```

Record the returned `EventId`, `Source`, `DisplayPath`, `EventTime`, `State`, and `Priority` fields when present. Use source paths for mutation or correlation work; use display paths for operator-facing explanations. If `State` or `Priority` is numeric, preserve the raw value and map it only after confirming the target's meaning.

For associated data, do not rely on the status dataset alone. Use a bounded diagnostic script or native alarm query with `defined`, `all_properties`, or `any_properties` to confirm the exact event property name and value. Preserve the raw value and type, especially for numeric-looking custom fields.

## Shelving Probes

When troubleshooting NoShelve or missing active alarms, capture both the configured alarm property and the execution scope used for the operation. Do not treat `shelvingAllowed: false` as proof that every shelving path is blocked. For script-driven shelving checks, compare normal status, `includeShelved: true`, and `system.alarm.getShelvedPaths`, and record the actor if the target exposes one. Client Alarm Status Table button state and remote service permission behavior need separate evidence on the target.

## Acknowledgement Probes

When a bounded diagnostic uses Gateway-scope scripting to acknowledge an event, record the exact argument mode, returned error or failed-ID list, and the status query after the attempt. For notes-required alarms, do not collapse an omitted notes argument, an explicit null note value, an empty string, and a non-empty note into the same case; different scopes can treat those paths differently. Only retry after confirming whether the first attempt left the event unacknowledged or already moved it to the acknowledged state.

For ack-mode comparisons, capture the configured `ackMode` along with active status, post-ack status, post-clear status, and journal `EventState` sequence. Auto, Manual, and Unused alarms can produce different current-status and journal shapes; preserve those rows before reasoning about acknowledged dropout or pipeline admission.

## Alarm Journal

Use `alarmJournalQuery` for lifecycle history. Keep the time window and source/path/display-path filters narrow. On runner `0.3.97+`, pass explicit `journalName`, `journal`, or `alarmJournal`; default/omitted journal flags are rejected because the runner cannot verify Ignition's exactly-one-journal omission condition. On runner `0.3.96+`, provider/state/priority/system filters are supplemental, broad confirmation bypasses are removed, and the maximum window is `1440` minutes.

```json
{
  "action": "alarmJournalQuery",
  "requestId": "<runId>-journal",
  "journalName": "<AlarmJournalProfileName>",
  "sources": ["prov:<provider>:/tag:<path-or-pattern>"],
  "displayPath": ["<display/path/or/pattern>"],
  "sinceMinutes": 60,
  "includeData": true,
  "includeSystem": true,
  "includeShelved": true,
  "maxResults": 100
}
```

Status and journal row counts do not have to match. Journal rows are lifecycle transitions, while status rows are the current event state.

If `EventState` or `Priority` is numeric, preserve the raw value and map it from the target before using a display label.

Separate journal profile storage from query-time filtering. `alarmJournalQuery` can test the rows available to scripting for the exact requested profile, but it does not prove that the profile stored lower-priority, shelved, enabled/disabled, or source-filtered events. Confirm profile settings such as Minimum Priority, Store Shelved Events, Query Only, and source/display-path filters when missing history matters.

When journal history must include associated data, check the target journal profile and query shape. A journal row count proves lifecycle storage, but custom event properties still need explicit event-object or property-filter confirmation.

## Audit

Use `auditQuery` only when the exact audit profile name is confirmed. WebDev/Gateway scope requires `profile`, `auditProfileName`, or `profiles`; do not send `useDefaultProfile`. Keep actor, action, target, system, or value filters narrow. On runner `0.3.96+`, broad confirmation bypasses are removed, `contextFilter` alone is not a backend bound, and the maximum window is `1440` minutes.

```json
{
  "action": "auditQuery",
  "requestId": "<runId>-audit",
  "profile": "<AuditProfileName>",
  "sinceMinutes": 60,
  "actionFilter": "%Alarm%",
  "maxResults": 100
}
```

If the query returns 0 rows, report audit attribution as unavailable for that profile/window. Do not fill in operator identity from status or journal fields unless those fields explicitly provide it.

A queryable profile, a synthetic marker, or an unrelated audit row proves audit storage/query plumbing only. For alarm attribution, run action-specific queries against the target profile for the same action class, source path, EventId or target, actor, and time window. If ack, shelve, notification, or channel-ack rows are absent, report attribution as unproven even when status and journal prove the alarm operation happened.

## Focused Logs

Use `logQuery` for focused supporting context, not as a substitute for alarm status, journal, audit, or sink evidence.

```json
{
  "action": "logQuery",
  "requestId": "<runId>-logs",
  "sinceMinutes": 30,
  "levels": ["ERROR", "WARN"],
  "loggerContains": "<alarm-or-module-logger-suffix>",
  "messageContains": "<EventId-or-source-or-pipeline-name>",
  "maxResults": 50
}
```

If focused logs miss, relax only one filter at a time while keeping the time window bounded.

`logQuery` returns log entries, not alarm rows. Preserve `timestamp`, `epochMillis`, `level`, `logger`, `message`, and `sourceFileName` when present. Wrapper-log parsing can normalize or omit logger names, especially for Gateway-scope script output; when a logger-filtered query misses a known marker, retry with `textContains` on the run marker, EventId, or source path. Set `includeNonPrimary: true` when the expected evidence may be a bare script print or another timestamped wrapper line without an Ignition logger prefix.

## Guardrails

- Narrow status by source, path, or display path.
- Narrow journal by source, path, or display path plus a short time window.
- Narrow audit by actor, action, target, value, system, or short time window.
- Narrow logs by time, level, logger, message, or run marker.
- Use broad-query confirmations only with explicit user approval and a clear reason.
- Keep notification sends, tag writes, pipeline edits, roster edits, and remote Gateway mutations out of runner diagnostics unless the user has approved the exact safe target.

## Minimal Interpretation Checklist

For every alarm incident, answer:

- Did the alarm exist in current status?
- Was it hidden by shelving?
- What EventId and source path identify it?
- Which journal transitions exist for the same event/source?
- Which associated data fields are present on the event object or property-filter query?
- Did the event enter the expected pipeline?
- Which roster/profile/channel should have received it?
- Does the roster exist, and does readback show the expected static member order or an empty roster?
- At the event timestamp in the Gateway timezone, are the selected users scheduled?
- Do the selected users come from the expected user source and expose the contact type required by that profile?
- Is there notification sink or module evidence?
- Is audit attribution available, unavailable, or unconfigured?
- Are logs explanatory, or only follow-on noise?
