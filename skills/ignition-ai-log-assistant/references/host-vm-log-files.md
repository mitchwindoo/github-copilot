# Host VM Log Files

Use this reference when the user has host VM access to Gateway files.

## Discovery Order

- Get environment facts from the runner first when available: `health` and `gatewayInfo` are faster and avoid guessing version/module state.
- Locate the install directory from the customer profile, `IGNITION_HOME`, service configuration, or the platform default. On Windows, check likely install roots such as `<ProgramFiles>\Inductive Automation\Ignition`, but do not scan whole drives.
- Check both `<installDir>\logs` and `<installDir>\data\logs` for wrapper evidence. The active wrapper log, rotated `wrapper.log.N` files, and `system_logs.idb` may be under the install-level `logs` folder.
- Treat `<installDir>\data\db\config.idb` as configuration evidence, not Gateway Diagnostic Logs. Do not feed it to the diagnostic-log parser.

## Wrapper Logs

- Use `scripts/query_wrapper_logs.py <logsDir>` with byte caps before copying large files.
- Include `--include-rotated`, `--max-log-files`, `--max-bytes-per-file`, `--max-total-bytes`, and `--hash-files` when older rotation context may matter.
- Preserve `sourceFiles[]`, `rotationIndex`, per-file hashes, `readBytes`, `sourceBytes`, `tailWindowTruncated`, `matchedCountBeforeCap`, and `truncated`.
- If the result is capped or tail-truncated, narrow the query by time, logger suffix, distinctive message text, source file, or known noise exclusions before reading returned rows as representative.

## Gateway Diagnostic Logs IDB

- Copy `system_logs*.idb` to an evidence folder before querying. Do not point `scripts/query_gateway_idb.py` at the live file.
- Preserve source size/hash, copy size/hash, schema tables, row counts, bounds, `matchedCount`, `returnedCount`, `capped`, selected properties, and exception previews.
- Use IDB property/MDC filters only when `logging_event_property` exists and the copied evidence contains relevant keys. Otherwise mark MDC unavailable.
- Expect IDB history and wrapper tails to have different coverage. The IDB may hold much older diagnostic history than a capped wrapper tail; the wrapper may include service/JVM lines or non-primary output that is not in the diagnostic log tables.

## Large Evidence Indexing

- Before reading large row samples, build a source inventory and aggregate profile from copied evidence: time bounds, level counts, top logger/level pairs, hot time buckets, normalized message signatures, exception first lines, and available property keys.
- Use the aggregate profile to choose the next focused query: earliest occurrence for cause hunting, hottest bucket for repeated-noise sizing, exception first line for stack-preview selection, or property key for MDC filtering.
- When comparing wrapper and IDB evidence, match compatible logger suffixes or wrapper abbreviations before labeling a logger as source-only.
- Treat aggregate hotspots as navigation signals only. A loud repeated error can be a root cause, background noise, or a follow-on symptom until selected rows are inspected against the reported issue window.
- Do not compare capped wrapper samples and full copied-IDB aggregate counts as equivalent counts. Use them to decide which source has the useful coverage for the next question.

## Focus Query Planning

- Turn a hotspot into at least two copied-IDB follow-ups before reading pages of rows: a first-occurrence window and a latest-occurrence window around the same logger, level, and distinctive message or exception token.
- Use a hot-bucket query separately to size repetition. Expect it may cap; do not use the returned sample alone to claim the whole bucket has been reviewed.
- When translating a copied-IDB focus plan to runner `logQuery`, treat the runner payload as a dry-run plan until a live test is registered. Preserve the same source, time, level, logger suffix, message token, cap, and request ID choices.
- Inventory property values only after confirming the key exists, and review values for sensitivity before putting them into shared artifacts or live MDC/property filters.

## Timeline Handoff

- After focused queries, produce a compact source-labeled timeline before diagnosis. Include environment, first/latest rows, loud buckets, cap state, wrapper/API/IDB coverage hints, and missing evidence.
- Keep first/latest inspected windows separate from hot-bucket repetition samples. An uncapped first/latest sample supports inspection; a capped hot bucket only sizes noise until narrowed.
- Carry missing symptom window, impact, recent-change context, module inventory, and current release/vendor lookup as explicit confidence limits when they are absent.
- If a logger is IDB-only, or only appears through wrapper-abbreviated names, state that as source coverage rather than absence or equivalence.

## Next Evidence Request

- When the timeline still has confidence gaps, request the smallest next evidence by lane: human incident metadata, registered API/runner collection, host VM copied artifacts, and current release/vendor lookup.
- Human context should confirm symptom window, timezone, impact, status, affected scope, and recent changes. Do not substitute a log evidence range for the reported symptom window.
- Treat saved runner `logQuery` payloads as dry-run shapes until live coordination is complete. Refresh `health` and `gatewayInfo` first, then run only focused live queries with unique request IDs.
- If `gatewayInfo` lacks module inventory, request module states/versions from a Gateway status view, support bundle, or other approved source before making module-specific license, bug, or compatibility claims.
- For host VM evidence, work from copied `system_logs*.idb` files and bounded wrapper rotations. Preserve source path class, file metadata, hashes, filters, matched/returned counts, and cap state.
- For IDB-only loggers, ask for copied/exported Gateway Diagnostic Logs rather than treating wrapper/API silence as absence. For capped hot buckets, narrow the copied-IDB query before claiming complete row review.
- Keep secrets and configuration databases out of diagnostic evidence requests unless the user separately authorizes a sanitized configuration review.

## Efficient Combined Workflow

1. Use API `health` and `gatewayInfo` for version, module, runner, project, and current system context.
2. Use runner `logQuery` for fast recent wrapper-tail checks.
3. Use host wrapper files when runner `logQuery` is capped, tail-truncated, missing rotations, unavailable, or needs source-file hashing.
4. Use a copied `system_logs*.idb` when Gateway Diagnostic Logs history, aggregate hotspots, exception previews, or MDC/property context is needed.
5. Normalize and group API, wrapper, and copied-IDB rows only after preserving source labels, timezones, and whether each count came from a cap-limited sample or aggregate profile.
