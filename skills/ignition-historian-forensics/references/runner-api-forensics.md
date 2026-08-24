# Runner API Forensics

Use this reference when an Ignition Web Dev runner is available. Start read-only and call `health` before any other action.

## Contents

- Read-Only Discovery Order
- Example Requests
- Current API Boundaries

## Read-Only Discovery Order

1. `health`
   - Record `runnerVersion`, `stackVersion`, `features`, and authentication state.
   - Confirm the actions you plan to use are present. Do not invent unsupported action names.

2. `gatewayInfo`
   - Use for Ignition version, Gateway context, module inventory, and whether the Tag Historian module appears present and running when module details are available.

3. `databaseConnectionsList`
   - Use for database type, status counts, and problem flags before blaming historian query behavior.
   - Keep connection names and problem text in target-local evidence when sensitive.
   - This does not expose history provider pruning, prune age, partition length, internal historian limits, or archive settings. Use `retention-pruning-forensics.md` when old data may be outside active retention.

4. `tagProviders`, `tagBrowse`, and `tagRead`
   - Use to prove provider/path existence and current value quality.
   - Use fully qualified paths for reads: `[Provider]Folder/Tag`.
   - Record the current value timestamp. A Good value with a stale timestamp is not proof that the tag was updating during the incident window.
   - Treat these as current realtime provider checks. They do not prove historical tag path identity, historical provider identity, or which `sqlth_te.id` stored rows during an earlier window. If path/provider identity matters, read `tag-identity-forensics.md`.
   - They do not prove History Enabled, Sample Mode, Historical Tag Group, Sample Rate, min/max timers, deadband style, deadband mode, or historical deadband. If storage qualification matters, read `storage-qualification-forensics.md`.

5. `historyProbe`
   - Use to check bounded historian availability for explicit tag paths.
   - Use it as an availability probe, not as a substitute for a full `system.tag.queryTagHistory` diagnostic.
   - It does not reproduce Power Chart or Easy Chart cache, visible datapoint, x-trace, range brush, point-count, resolution, or pre-processed partition behavior. Use `visualization-cache-forensics.md` when chart output differs from direct query evidence.
   - Treat `queryOk: true` as query execution evidence only.
   - On runner `0.3.137+`, check `goodSampleHistoryAvailable`, `sampleCountQueryOk`, top-level `goodStoredSampleCount`, and each `tagStats[].goodStoredSampleCount`. Treat `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` as aliases.
   - On runner `0.3.108+`, parse non-2xx JSON too: primary `historyProbe` backend failures return top-level `ok: false`, `statusCode: 500`, `errorCode`, and `error` while preserving `queryOk`, `sampleCountQueryOk`, `queryError`, and `sampleCountQueryError`.
   - Use `rowCount`, `sampleRows`, `valueQueryHistoryAvailable`, `tagStats[].nonNullCount`, `hasData`, and `lastValue` as diagnostic value-query context, not stored-sample proof.
   - For multiple paths, read every `tagStats[]` entry. A global row count or one populated tag must not be used as proof for all requested tags.
   - Require positive good-sample counts before claiming good-quality stored history exists. False/zero good-sample fields do not prove bad-quality rows are absent. If the live runner is older than `0.3.137`, treat non-null value cells and older availability names as weaker evidence and use an approved direct diagnostic or database proof for stored-history claims.
   - Use `aggregationMode` only from the runner-supported list. `LastValue` is a useful first probe because it exposes timestamp buckets that may still have null values.
   - If aggregate mode, `queryTagCalculations`, scan-class validation, stale data detection, bad-quality filtering, or compliance-grade raw-event proof is decisive, read `aggregate-validation-forensics.md`; `historyProbe` is not a full aggregate validation surface.
   - For audit-sensitive windows, prefer an exact start/end diagnostic path when relative `rangeMinutes` cannot prove the requested boundaries.

6. `logQuery`
   - Use focused filters for historian, history manager, store-and-forward, database connection, and quarantine symptoms.
   - A zero-entry log query means no matching line was found in the selected log scope, not that the event never happened.
   - If logs point to queue delay, quarantine, dropped records, database recovery, or late arrival, read `store-forward-quarantine-forensics.md` before naming the delivery state.

## Example Requests

Health:

```json
{"action":"health","requestId":"HISTORIAN-HEALTH-001"}
```

Tag providers:

```json
{"action":"tagProviders","requestId":"HISTORIAN-PROVIDERS-001","maxResults":100}
```

Current value:

```json
{
  "action": "tagRead",
  "requestId": "HISTORIAN-TAGREAD-001",
  "paths": ["[Provider]Area/Line/Tag"],
  "maxResults": 20
}
```

History probe:

```json
{
  "action": "historyProbe",
  "requestId": "HISTORIAN-PROBE-001",
  "paths": ["[Provider]Area/Line/Tag"],
  "rangeMinutes": 60,
  "returnSize": 10
}
```

Optional bounded aggregation probe:

```json
{
  "action": "historyProbe",
  "requestId": "HISTORIAN-PROBE-COUNT-001",
  "paths": ["[Provider]Area/Line/BooleanState"],
  "rangeMinutes": 1440,
  "returnSize": 24,
  "sampleRows": 5,
  "aggregationMode": "CountOn"
}
```

Focused logs:

```json
{
  "action": "logQuery",
  "requestId": "HISTORIAN-LOGS-001",
  "sinceMinutes": 240,
  "loggerContains": "History",
  "messageContains": "store",
  "maxResults": 50
}
```

## Current API Boundaries

Current runner builds expose `historyProbe`, not a complete arbitrary Tag Historian query builder. Runner `0.3.137+` uses a strict Count query with `ignoreBadQuality=True` internally for availability and reports that as good-quality Count evidence, but caller-selected value output remains bounded and diagnostic. If the investigation needs exact start/end boundaries, `returnSize=-1`, caller-controlled `noInterpolation`, caller-controlled `ignoreBadQuality`, `returnFormat`, per-tag `aggregationModes`, `queryTagCalculations`, `validateSCExec`, `validatesSCExec`, exact scan-class validation behavior, bad-quality row proof, or exact binding/chart cache comparison, use a user-approved diagnostic path such as a narrow Jython script, a chart/binding export, `aggregate-validation-forensics.md`, `visualization-cache-forensics.md`, or the Jython skill.

Current runner builds do not expose a general store-and-forward queue/quarantine API, historian provider configuration API, raw historian partition API, or direct tag configuration export for every property. Use Gateway UI evidence, exported tag JSON, focused logs, read-only database evidence, and `store-forward-quarantine-forensics.md` where appropriate.

Current runner builds do not expose datasource history provider pruning settings, internal historian time/point limits, Edge local-history limit evidence, or external archive/replica topology. Treat runner no-row evidence for old windows as active-query evidence and route retention questions to Gateway configuration evidence, approved scripts, or read-only SQL.

Current runner builds do not expose a complete tag history configuration export for all history properties. Treat `historyProbe` no-row evidence as query evidence until History Enabled, Storage Provider, Sample Mode, Historical Tag Group or Sample Rate, Min Time Between Samples, Max Time Between Samples, Deadband Style, Deadband Mode, and Historical Deadband are reviewed through configuration evidence or an approved diagnostic. Use `storage-qualification-forensics.md` when a value may not have qualified to store.

Current runner builds do not browse `histprov:` historical tag paths directly. Use user-provided historical paths, component/export evidence, an approved Jython diagnostic such as `system.tag.browseHistoricalTags`, or read-only SQL metadata when identity cannot be resolved from realtime tag discovery.

Use `scriptEval` only for explicit diagnostics and only after the user accepts that it executes Gateway-scope Jython. Keep scripts narrow, read-only when possible, bounded by time window and tag path, and free of credentials.

Do not use runner diagnostics to perform historian writes, quarantine retry/delete/import actions, tag configuration changes, cache changes, or direct SQL repair. Any runner capability that performs those operations is a remediation API, not a forensics API, and needs a separate approved change workflow before use.

Do not change runner behavior for a historian investigation unless a missing capability blocks a reusable, safe, read-only diagnostic. If a runner API action or contract changes, update the runner API reference, capabilities, evidence, and release notes before relying on the new behavior.
