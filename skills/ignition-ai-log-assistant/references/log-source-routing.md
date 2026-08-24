# Log Source Routing

Use this reference when selecting diagnostic sources or parser helpers.

## Scope And Trigger Detail

Original comprehensive trigger detail retained from the pre-restructure skill:

> Diagnose Ignition 8.1 Gateway, wrapper, Perspective, Vision, module, and runner logs with evidence-first triage. Use when Codex needs to inspect or summarize Ignition errors, filter logs by time/level/logger/message/MDC/source, snapshot Gateway health/version/modules/environment, check current Ignition or vendor release/bug sources, or produce likely root-cause and next-step diagnostics from pasted/exported logs, host VM Gateway files, or the approved Web Dev runner API.

## Source Selection

- Gateway Diagnostic Logs: database, OPC/device, auth, alarm, Gateway-scoped project resource errors, and `system.util.getLogger` output. Prefer pasted/exported evidence when the runner only has wrapper-log access.
- Wrapper logs: startup/restart, service/JVM wrapper events, Gateway-scoped print output, and many Gateway script/logger messages.
- Perspective/browser evidence: client-side component/runtime errors, failed project resource fetches, binding failures visible only in the session, and user interaction failures.
- Designer/client logs: Designer/runtime-only client symptoms.
- Thread dumps: point-in-time thread-state evidence for hangs, high CPU, deadlocks, and blocked execution. Collect multiple dumps during the observed issue, compare repeated thread name/state/top-frame signatures, and correlate persistent stacks with logs or metrics before calling root cause.
- Audit logs: change-attribution context, such as who changed a Gateway/project/tag/security/datasource item and when. Do not classify audit rows as diagnostic logs.
- Alarm journals: historical process/alarm context, such as alarm source, event timestamp, state, priority, associated data, and property snapshots. Do not classify alarm-journal rows as diagnostic logs or current alarm status.

Preserve source labels in the analysis. Do not merge Gateway, wrapper, browser, Designer, audit, alarm-journal, or thread-dump evidence as if they were one log stream unless timestamps/timezones are aligned and the output still retains each evidence class.

## Wrapper Logs

- For local/exported rotated wrapper logs, find the configured path before assuming OS defaults.
- When local filesystem access is available, parse `ignition.conf` for `wrapper.logfile`, resolve a relative value against the Ignition install root, and collect the configured file plus numeric siblings from that directory.
- Record `wrapper.logfile.maxsize` and `wrapper.logfile.maxfiles` as rotation context.
- Record file hashes/sizes/modified times, and cap per-file reads and returned rows.
- Prefer `scripts/query_wrapper_logs.py <wrapper-file-or-dir>` for local/exported wrapper files.
- On runner `0.3.61+`, use `logQuery includeRotated: true` and `maxLogFiles` to scan the target Gateway's current wrapper log plus discovered numeric siblings through the API.
- Parse the wrapper prefix separately from any embedded Ignition severity/logger, and use the embedded Ignition event for grouping when present.
- Treat observed paths, rotation names, and wrapper formats as target-specific.

## Gateway Diagnostic Logs IDB

- Work from an exported/copied `.idb` file opened read-only.
- Prefer `scripts/query_gateway_idb.py <copied-system_logs.idb>` over ad hoc SQLite queries.
- Discover schema before querying.
- Use time/level/logger/thread/message/MDC filters and cap returned rows.
- Join exception/MDC tables only for selected event IDs.
- Use MDC filters only when copied/exported evidence actually contains keys.
- Treat table names, context keys, official export filenames, and schema details as target/version-specific.
- Do not read live active IDB files unless the target explicitly supports it and the user authorizes it.

## Diagnostic Bundles

- Enumerate the archive first.
- Classify recognized files by evidence source.
- Open copied IDBs read-only with schema discovery.
- Prefer `scripts/inspect_diagnostic_bundle.py <zip-or-dir>` to classify a bundle or extracted directory without extraction before choosing a source-specific parser.
- Route copied `system_logs*.idb` files to `query_gateway_idb.py`, wrapper logs to `query_wrapper_logs.py`, Gateway info snapshots to module/version source routing, and browser/audit/alarm/thread evidence to separate source-labeled review.
- Build the diagnostic report from source-labeled outputs, not from the inspector's filename classification alone.
- Match Gateway log exports by `system_logs` plus `.idb` instead of hard-coding an exact timestamp format.
- Treat bundle members such as Gateway information, thread dumps, wrapper logs, system-log IDBs, metrics IDBs, and optional dumps as absent unless the archive actually contains them; treat unknown files as manual-review candidates.

## Helper Routing

- Use `scripts/compare_thread_dumps.py <dump1> <dump2> [...]` when two or more copied/exported thread dump files are available. Treat persistent signatures as thread-state evidence that still requires log or metric correlation before root-cause claims.
- Use `scripts/normalize_log_rows.py <input...>` when parser/helper JSON outputs or source-labeled row lists need normalization before grouping. Treat it as a normalization bridge only.
- Use `scripts/group_log_findings.py <rows.json>` as a triage aid before writing the report. It normalizes repeated findings, preserves source labels, keeps audit/alarm/thread rows as context, and links likely Perspective/script follow-ons back to earlier database/Named Query roots for human review.

Classify by source/log stream and logger before exception text. If a Perspective/browser or alarm entry repeats an upstream SQL/database exception after the first database or Named Query failure, keep it as a linked follow-on group instead of merging it into the database root-cause group.
