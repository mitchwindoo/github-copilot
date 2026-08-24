---
name: ignition-ai-log-assistant
description: Diagnose Ignition 8.1 Gateway, wrapper, Perspective, Vision, module, runner, IDB, bundle, and thread-dump evidence. Use for error triage, root-cause analysis, sanitization, and log filtering.
---

# Ignition AI Log Assistant

Skill version: `1.0.78`
Stack version: `starter-2026.07.06.04`
Runner API version: `0.3.148`
Ignition target: `8.1`

## Scope

Use this skill for read-first Ignition log diagnostics. Prefer evidence over guesses, preserve exact timestamps/logger names/messages, and clearly separate:

- first visible error
- earliest suspicious event
- most frequent repeated error
- likely root cause
- follow-on noise
- missing evidence needed to confirm

Do not delete resources, change Gateway configuration, broaden logger levels, run arbitrary scripts, or expose secrets unless the user explicitly authorizes the specific action. If Gateway/API calls return HTTP 402, check/reset Ignition Trial Mode before debugging code.

## Reference Loading

- Load `references/runner-api-diagnostics.md` when using the Web Dev runner beyond a basic `health`/`gatewayInfo`/focused `logQuery`, including rotated logs, non-primary wrapper output, tag-event probes, audit rows, alarm journal rows, runner evidence persistence, or script-output routing.
- Load `references/host-vm-log-files.md` when the user has host VM file access and you need to locate Gateway wrapper logs, rotated logs, copied `system_logs*.idb`, diagnostics folders, or evidence paths outside the runner.
- Load `references/log-source-routing.md` when selecting among Gateway Diagnostic Logs, wrapper logs, browser/Perspective evidence, Designer logs, thread dumps, audit rows, alarm journals, copied IDB files, or diagnostic bundles.
- Load `references/log-technical-source-map.md` when a logger/category/source is unfamiliar or official technical docs are needed to interpret where evidence should appear or what a subsystem term means.
- Load `references/vendor-release-routing.md` when version/module bugs may matter, including IA release notes, Cirrus Link/Chariot modules, Sepasoft/MES modules, unknown third-party modules, or exact-version compatibility claims.
- Load `references/script-catalog.md` before selecting or running a bundled helper, especially when evidence may contain secrets or an output file will be written.

## Start With Evidence

Collect or derive these fields before deep diagnosis:

- exact Ignition version/build, timezone, OS/Java, and runner version, supported actions, and feature flags when using the Web Dev runner
- installed modules, module states, and module versions when available
- log source: Gateway Diagnostic Logs export/paste, wrapper log, Perspective/browser console, Designer/client log, Web Dev runner response, thread dump, audit row, alarm journal row, or support bundle
- issue window with timezone and at least one concrete timestamp
- issue status: ongoing, intermittent, after restart, during startup, after deploy, after module upgrade, or after project/tag/database change
- production impact and what changed recently
- sanitized log excerpt or export covering before, during, and after the first symptom

Ask for only the missing fields that affect the next diagnostic step. If a runner is reachable, gather the safe snapshot yourself.

When Python is available and you have incident metadata but not the evidence yet, use `scripts/build_evidence_request.py <incident.json>` to generate a smallest-useful, source-specific, sanitized evidence request. Treat the output as a collection checklist, not a diagnosis.

## Runner Snapshot

When the approved Web Dev runner is available, use `ignition-perspective-host-builder` for request mechanics when it is installed. Otherwise, use the standalone transport and authentication procedure in `references/runner-api-diagnostics.md`. Save raw request/response evidence to an agreed folder when the user needs a durable diagnostic record.

1. Call `health` first and inspect `runnerVersion`, `supportedActions`, `features`, `mutationLockedActions`, `tokenConfigured`, and `stackVersion` when present. Treat `supportedActions` as the callable action catalog and `features` as capability flags.
2. Call `gatewayInfo` to capture Ignition version/build, time/timezone, modules/states/versions, target project existence, system properties, and runner action/feature context.
3. Use `logQuery` with a caller-generated `requestId`, numeric `sinceMinutes` or captured `sinceEpochMillis`, capped results, and at least one narrow logger/message/text filter unless the user explicitly authorizes a broad diagnostic query.
4. Inspect returned `sinceEpochMillis`, `sourceFiles`, `lineScanCount`, `matchedCountBeforeCap`, `truncated`, and `tailWindowTruncated` before interpreting entries.
5. If `matchedCountBeforeCap` exceeds returned entries, or truncation is true, narrow again by logger suffix, distinctive message text, and a shorter time window before treating the sample as representative.
6. Treat current-only `logQuery` as wrapper-log evidence, not a complete replacement for exported Gateway Diagnostic Logs.
7. Load `references/runner-api-diagnostics.md` before using rotated wrapper logs, non-primary lines, tag-event probes, audit queries, alarm-journal queries, saved evidence metadata, script-output routing, or runner maintenance/update workflows.

Focused log query shape:

```json
{
  "action": "logQuery",
  "requestId": "<runId>-log-focused",
  "sinceMinutes": 15,
  "levels": ["ERROR", "WARN"],
  "loggerContains": "<stableLoggerSuffix>",
  "messageContains": "<runIdOrErrorText>",
  "maxResults": 50,
  "tailBytes": 524288
}
```

Broad scans are noisy and should remain exceptional. If a broad query is unavoidable, use the runner's explicit broad-query confirmation and explain why the narrower filters were insufficient.

Use `scriptEval` only for bounded diagnostics with explicit confirmation. A dry-run compile is not execution confirmation. Do not use `scriptEval` as the general write or repair path.

## Host VM Files

When host VM access is available, use it to extend or cross-check API evidence without mutating Gateway files.

1. Discover the install/data/log locations from the instance profile, environment, service config, or shallow platform-default checks; do not scan whole drives.
2. Check both install-level `logs` and `data/logs` locations. Wrapper logs and `system_logs*.idb` can live beside each other outside `data/logs`.
3. Parse wrapper logs with byte caps, rotation limits, and source-file hashes before widening the query.
4. Copy `system_logs*.idb` to an evidence folder before querying it; do not point the IDB helper at a live file.
5. Do not treat `data/db/config.idb` as Gateway Diagnostic Logs evidence.

Use API `health`/`gatewayInfo` for environment facts, runner `logQuery` for fast recent wrapper-tail checks, host wrapper files for older rotations/source hashes, and copied IDBs for diagnostic-log history, exception previews, and MDC/property context.

## Source Routing

Choose the source that can actually contain the symptom:

- Gateway Diagnostic Logs: database, OPC/device, auth, alarm, Gateway-scoped project resource errors, and `system.util.getLogger` output.
- Wrapper logs: startup/restart, service/JVM wrapper events, Gateway-scoped print output, and many Gateway script/logger messages.
- Perspective/browser evidence: client-side component/runtime errors, failed project resource fetches, binding failures visible only in the session, and user interaction failures.
- Designer/client logs: Designer/runtime-only client symptoms.
- Thread dumps: hangs, high CPU, deadlocks, and blocked execution.
- Audit rows: who changed a Gateway/project/tag/security/datasource item and when.
- Alarm journal rows: historical alarm source, event timestamp, state, priority, associated data, and property snapshots.

Preserve source labels. Do not merge Gateway, wrapper, browser, Designer, audit, alarm-journal, or thread-dump evidence as if they were one log stream unless timestamps/timezones are aligned and the output still retains each evidence class.

Use the bundled helpers when their input is available:

- `scripts/query_gateway_idb.py <copied-system_logs.idb>` for copied/exported Gateway Diagnostic Logs `.idb` files; inspect schema/bounds, matched vs returned counts, cap state, selected properties, and exception previews.
- `scripts/query_wrapper_logs.py <wrapper-file-or-dir>` for local/exported wrapper logs and rotated siblings.
- `scripts/inspect_diagnostic_bundle.py <zip-or-dir>` to classify support archives before selecting source-specific parsers; treat filename matches as routing hints only.
- `scripts/compare_thread_dumps.py <dump1> <dump2> [...]` for two or more copied/exported thread dumps.
- `scripts/normalize_log_rows.py <input...>` before grouping mixed parser/helper outputs.
- `scripts/group_log_findings.py <rows.json>` as a triage aid before writing the report.
- `scripts/route_log_technical_sources.py <rows-or-grouped-findings.json>` to map log categories/logger clues to official Ignition technical reading sources.

Treat helper outputs as intermediate evidence. They do not fetch missing logs, browse current sources, or make the final diagnosis. Parse recognized bundle entries with source-specific helpers and manually review unknown entries before root-cause claims. Before grouping mixed helper outputs, normalize them and inspect row counts, source labels, source filenames/rotation indexes when present, and redaction status.

## Filtering Workflow

Filter in this order:

1. Source: choose the log stream that can actually contain the symptom.
2. Time: narrow to the issue window plus a short before/after buffer.
3. Level: start with ERROR/WARN, then include INFO/DEBUG only when needed.
4. Logger/message: use exact logger suffixes, stable run IDs, route paths, tag paths, query names, project names, or exception text.
5. MDC/context: use project, route path, method, thread/session, or other returned keys when present.
6. Frequency: group repeated stack traces by normalized exception class, logger, first stack frame, and message shape.

For large copied IDBs or capped wrapper outputs, build an aggregate navigation pass before row-by-row reading: source bounds, level/logger counts, time buckets, normalized message signatures, exception first lines, and available property keys. Treat hotspots as focus targets, not proof of cause.

Convert hotspots into bounded follow-ups: use first-occurrence and latest-occurrence windows for inspectable row samples, hot-bucket windows only to size repetition, and live runner payloads only after separate live-test registration.

After focused samples, build a source-labeled timeline before diagnosis: first/latest evidence, repeated-noise buckets, cap state, cross-source coverage, and missing symptom/change context.

If the timeline still leaves confidence gaps, return the smallest next-evidence request split by human incident context, registered API/runner collection, host VM copied artifacts, and current release/vendor lookup. Mark live actions separately from offline copied-evidence steps.

Before treating zero or sparse matches as negative evidence, check source coverage, first/last timestamps, timezone alignment, rotation/tail truncation, result caps, embedded vs wrapper level fields, and primary vs non-primary wrapper status. If a focused query misses, relax one dimension at a time while keeping source and time bounded.

For live runner queries, a zero count with `sourceAvailable` and `sourceFiles` still means only "no matches inside this source, time window, filter set, and tail window." Check `tailWindowTruncated`, rotated-file coverage, and whether exported Gateway Diagnostic Logs are needed before saying an event is absent.

For copied Gateway log IDBs, use MDC/property filters only when the copied evidence includes a property table and relevant keys. If that table or key is absent, mark MDC context unavailable instead of claiming the context did not exist.

Classify by source/log stream and logger before exception text. If a Perspective/browser or script entry repeats an upstream SQL/database exception after the first database or Named Query failure, keep it as a linked follow-on group instead of merging it into the database root-cause group. Treat audit, alarm-journal, and thread-dump rows as context unless they directly confirm the diagnostic event.

Wrapper logs can abbreviate dotted logger names. Filter with a stable suffix plus a unique message/run marker when available instead of relying only on the fully dotted display name.

## Root-Cause Triage

For each error group, record:

- first timestamp and last timestamp
- count or "seen once"
- level and logger
- source log
- exact first-line message
- associated project/tag/device/database/module/path
- likely category: startup/module, project resource load, Perspective client/session, script/Jython, tag/OPC/device, alarm, database/Named Query, auth/security, network, license/trial, or runner/tooling
- confidence: high only when evidence directly ties the error to the symptom

Prefer the earliest causal event over the loudest repeated follow-on error. Call out "not enough evidence" rather than filling gaps.

When using grouped findings, inspect `followOnOf`/`linkedFollowOns` and verify the source/logger against timestamps. Treat helper categories as triage labels until the evidence explains whether a row is root cause, caller context, or follow-on noise.

When subsystem meaning is unclear, route the evidence to official technical sources and read the relevant docs before interpreting terms such as wrapper log, Named Query, tag quality, OPC/device status, alarm journal, audit row, or thread dump. Treat technical-source hints as reading aids; they are not root-cause proof.

## Bug And Release Lookup

When version/module bugs might matter, search current sources and cite links in the answer. Do not rely on memory for "latest" release notes or open bugs.

Do not use general technical docs as bug evidence. Use them to understand the subsystem, then use current release/vendor sources for fixed-in-version, compatibility, latest-version, or known-bug claims.

Start bug/release routing from the live module inventory when available. Route only installed module IDs/names from `gatewayInfo.modules.modules[]`; note when no Cirrus or third-party modules are present instead of implying those vendor sources apply to the current Gateway.

When Python is available and you have a saved `gatewayInfo` response or module-list JSON, use `scripts/route_module_sources.py <gatewayInfo-or-modules.json>` to build a deterministic IA/Cirrus/Sepasoft/unknown-vendor source-routing plan. Treat the output as a routing plan only. Load `references/vendor-release-routing.md` before making vendor/module compatibility or bug/fix claims.

## Logger Levels

Changing logger levels can increase load and expose sensitive data. Require human approval before recommending or applying any logger-level change. Always capture the current level, proposed temporary level and duration, exact logger name or parent logger, reason, and rollback/restoration step.

Use documented `system.util.setLoggingLevel` only as a bounded, reversible diagnostic. Choose the narrowest logger, capture baseline behavior or the current setting when available, set the temporary level, reproduce, collect focused logs, restore the previous or approved level, and verify DEBUG/TRACE noise is suppressed again.

## Sanitization

Do not ask for or print passwords, tokens, cookies, license keys, private keys, JDBC URLs with credentials, user PII, customer hostnames, VPN details, or full production tag paths when a redacted path is enough. Preserve enough structure to diagnose: timestamps, levels, logger names, exception classes, first stack frames, module/project/resource names when relevant, and redacted path shapes.

When Python is available, prefer `scripts/sanitize_log_evidence.py <evidence-file>` before outside review or support escalation. Treat it as a first-pass sanitizer, not a substitute for human review.

## Output Contract

Return a concise diagnostic report with:

- environment snapshot: Ignition version/build, timezone, OS/Java, modules/states and module versions if available, and runner version, supported actions, and feature flags if used
- evidence window: source logs, time range, filters used, and saved diagnostic artifact location when applicable
- top findings: grouped by likely root cause first, then follow-on noise
- bug/release check: sources searched, matching fixes or "no matching public evidence found"
- next steps: one to three concrete checks or fixes, each tied to evidence
- missing evidence: only what is needed to raise confidence, split by human context, API/runner, host VM files, and current source lookup when more collection is the next step
- provenance: include only customer-relevant diagnostic artifacts; leave testing, release, and packaging provenance out of the diagnostic report unless the user specifically asks how the skill was validated

Use confidence labels. If the best answer is "the logs show the symptom but not the cause," say that plainly.

When Python is available and you already have grouped findings from `scripts/group_log_findings.py`, use `scripts/build_diagnostic_brief.py <grouped-findings.json>` to format a source-labeled diagnostic brief. Supply environment and source-check inputs when available. Treat the brief as a formatting scaffold; it does not fetch logs, browse current sources, or make the final diagnosis by itself.

## Safety Limits

Use this skill as a conservative diagnostic aid, not as an automatic repair agent.

- Treat runner `logQuery` as wrapper-log evidence unless exported Gateway Diagnostic Logs or copied IDB evidence is also provided.
- Treat copied/exported IDB parsing, wrapper-log rotation, audit profile access, alarm journal access, and source paths as target/version-specific.
- Keep Gateway logs, wrapper logs, browser/client evidence, audit rows, alarm-journal rows, and thread dumps source-labeled in the final analysis.
- Treat audit, alarm-journal, and thread-dump rows as context unless they directly confirm the diagnostic event.
- Treat helper scripts as collection, normalization, grouping, sanitization, or formatting aids. They do not fetch missing evidence, browse current sources, or make the final diagnosis.
- Browse current official/vendor sources before making version-specific bug, fix, latest-version, or compatibility claims.
- Require explicit authorization for broad scans, logger-level changes, `scriptEval`, resource changes, and any action that could expose secrets.
- If a needed runner action is absent from `health.supportedActions`, or a needed capability flag is absent from `health.features`, do not invent unsupported calls. Treat runner updates as a separate coordinated maintenance task with dry-run/update safeguards and a regression check before relying on the new capability.
- For Designer/Vision console capture, Tag Event Script output routing, Gateway UI diagnostic exports, and third-party module diagnostics, inspect the target environment before relying on source layout or behavior.
- If evidence only confirms the symptom, say so and ask for the smallest missing artifact needed to raise confidence.
