# Tag, Alarm, Historian, And UDT Patterns

Use this reference with `ignition-perspective-host-builder` when Perspective pages depend on tags, UDTs, historian data, alarm status, alarm journals, `tagConfigure`, `udtScaffold`, or tag-event fixture actions.

## Contents

- Tag Discovery
- Historian Evidence
- Alarm Queries
- UDT Scaffold
- Guarded Tag Configuration
- UDT Rules

## Tag Discovery

Tag discovery is read-only.

List providers:

```json
{"action":"tagProviders","maxResults":100}
```

Browse tags:

```json
{
  "action": "tagBrowse",
  "path": "[<tagProvider>]<folderPath>",
  "recursive": true,
  "maxResults": 1000,
  "includeValues": false
}
```

For scalable Perspective pages, use `tagBrowse` to validate the root folder/provider and discover UDT instances, then inspect `truncated` and `totalAvailable`; do not treat a capped result as complete until the response proves all needed rows were returned. Author the page so a parent view/script builds a row or repeater model from that root. Do not copy-paste one hard-coded full tag path per asset when a folder root plus `view.params`/`view.custom` model can drive the page.

Read explicit tag values:

```json
{"action":"tagRead","paths":["[<tagProvider>]<tagPath>"],"maxResults":100}
```

Use fully qualified `[provider]path` values. Treat the returned `value` as usable only when `quality` is good; preserve `timestamp` in diagnostics when freshness matters.

## Historian Evidence

Probe historian-backed data:

```json
{"action":"historyProbe","paths":["[<tagProvider>]<tagPath>"],"rangeMinutes":60,"returnSize":5}
```

Do not treat a good current value as confirmation of tag history. For trend/history components on runner `0.3.137+`, require `queryOk: true`, `sampleCountQueryOk: true`, `goodSampleHistoryAvailable: true`, and a positive `goodStoredSampleCount` or per-tag `tagStats[].goodStoredSampleCount`; if false, use a current-value display or state the good-quality historian dependency. Treat `historyAvailable`, `storedSampleCount`, and `sampleBackedHistoryAvailable` as aliases, and treat `valueQueryHistoryAvailable`, `nonNullCount`, `hasData`, and `lastValue` as diagnostics, not good-sample proof. On runner `0.3.108+`, parse non-2xx JSON too: primary `historyProbe`, alarm-query, and all-failed `auditQuery` backend failures return top-level `ok: false` while preserving fields such as `queryOk`, `sampleCountQueryOk`, `queryError`, and `attempts[]`.
Keep Alarm Status Table and Alarm Journal Table validation separate: `alarmStatusQuery` verifies current alarm state for `ia.display.alarmstatustable`, while `ia.display.alarmjournaltable` depends on a configured Alarm Journal/profile and uses singular `props.filter` plus a date range. For journal tables on runner `0.3.60+`, use `alarmJournalQuery` with the component's discovered `props.name` as explicit `journalName`; runner `0.3.97+` rejects default/omitted journal profile requests because it cannot verify Ignition's exactly-one-journal omission condition. Do not guess profile names such as `Journal`. On runner `0.3.96+`, both `alarmStatusQuery` and `alarmJournalQuery` must include a narrow source/path/displayPath filter before execution. On route-param detail pages, bind Alarm Status Table `props.filters.active.conditions.displayPath` and Alarm Journal Table `props.filter.conditions.displayPath` from `view.params.<assetId>` or a derived display-path pattern, then verify the same concrete filter with `alarmStatusQuery` and `alarmJournalQuery`.

## Alarm Queries

Query current alarms only with explicit filters:

```json
{
  "action": "alarmStatusQuery",
  "displayPath": "<displayPathPattern>",
  "states": ["ActiveUnacked", "ActiveAcked"],
  "priorities": ["Critical", "High", "Medium", "Low"],
  "maxResults": 25
}
```

Require at least one narrow `source`, `path`, or `displayPath` filter on runner `0.3.96+`; provider-only filters do not bound backend work. Use this to verify Alarm Status Table pages; do not use broad Gateway-wide alarm scans.

## UDT Scaffold

Create complete UDT fixtures with `udtScaffold` when available:

```json
{
  "action": "udtScaffold",
  "provider": "<tagProvider>",
  "typePath": "<relativeTypeFolder>/<TypeName>",
  "instanceFolder": "<normalTagFolder>",
  "allowedTypePathPrefix": "[<tagProvider>]_types_/<relativeTypeFolder>",
  "allowedInstancePathPrefix": "[<tagProvider>]<normalTagFolder>",
  "requiredOverrideMembers": ["PV", "Status"],
  "members": [
    {"name": "PV", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float4", "value": 0.0},
    {"name": "Status", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "String", "value": "Unknown"}
  ],
  "instances": [
    {"name": "Asset001", "memberOverrides": {"PV": 12.3, "Status": "Ready"}}
  ],
  "dryRun": true
}
```

For writes, set `dryRun` false and add `{ "confirmUdtScaffold": "SCAFFOLD_UDT" }`. Keep `typePath` and `typeId` relative to `[provider]_types_`; keep `instanceFolder` under normal `[provider]` tags. Runner `0.3.112+` advertises `udtScaffoldStepAllGoodFailureOkFalse` and returns top-level `ok:false` with `failedStepResult` plus partial `stepResults` when any nested step returns `ok:false` or `allGood:false`; on every runner, inspect `stepResults[]`, nested `allGood`, and nested `qualityCodes` before trusting the scaffold. Runner `0.3.143+` advertises `udtScaffoldUnknownFailureRecovery`; failed confirmed non-dry-run nested `tagConfigure` steps with missing, null, or empty `qualityCodes` are treated as unknown-mutated and mark every step recovery path from the preflight snapshot. Preserve `writesStarted`, `completedSteps`, `preflightExistingPaths`, `preflightNewPaths`, `recoveryAttempted`, `recoveryAllGood`, `recoveryRequired`, and nested `recovery` details such as `deletePaths` and `restorePaths` before continuing. After apply, read the returned `memberReadPaths` with `tagRead` and bind Perspective to instance/member paths, not UDT definition paths.
If a scaffold includes many members, instances, or per-instance overrides, estimate `plannedTagCount = 1 + member count + instance count + override tag count` and set `maxItems` high enough on both dry-run and apply while keeping the same allowed prefixes. A dry-run rejection for `planned tag count exceeds maxItems` is a guardrail, not a Gateway failure.

## Guarded Tag Configuration

Create scaffold tags/UDTs through `tagConfigure` only under approved prefixes:

```json
{
  "action": "tagConfigure",
  "basePath": "[<tagProvider>]<approvedFolder>",
  "allowedTagPathPrefixes": ["[<tagProvider>]<approvedFolder>"],
  "collisionPolicy": "a",
  "dryRun": true,
  "tags": [
    {"name": "DemoValue", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float4", "value": 1.23}
  ]
}
```

For writes, set `dryRun` false and add `{ "confirmTagConfigure": "CONFIGURE_TAGS" }`. On runner `0.3.111+`, bad returned QualityCodes or returned-code count mismatches should come back as top-level `ok: false` with `TAG_CONFIGURE_BAD_QUALITY` or `TAG_CONFIGURE_QUALITY_CODE_COUNT_MISMATCH`; still inspect `allGood`, `qualityCodes`, and readback. On older runners, treat `ok: true` plus `allGood: false` or any `qualityCodes[].good: false` as a failed write. Put UDT definitions under `[<tagProvider>]_types_/...`; create UDT instances under normal tag paths and bind Perspective to instances, not definitions. Reference tags require `valueSource: "reference"` and a non-empty `sourceTagPath`; do not use Reference-tag `sourceTagPath` parameters as confirmation of dynamic UDT path behavior without member readback.

## UDT Rules

For UDT scaffolds:

- Create `UdtType` definitions under `[<tagProvider>]_types_/...`.
- Create `UdtInstance` tags under normal `[<tagProvider>]...` folders with `typeId` relative to `_types_`.
- To initialize different member values per UDT instance, create the instance first, then call `tagConfigure` with `basePath` set to the instance path, `collisionPolicy: "m"`, and `tags` containing member names/values.
- Use `tagConfigure` directly rather than `udtScaffold` when a test must confirm explicit UDT instance `parameters` overrides; `udtScaffold` is for complete fixture scaffolds, not fine-grained copied-parameter write tests.
- For alarm component fixtures, `AtomicTag` configs may include `alarms` arrays; use numeric setpoints and verify runtime paths such as `[<tagProvider>]<tagPath>/Alarms/<alarmName>.IsActive` with `tagRead`. For per-instance UDT alarm overrides, merge alarm config before changing the value that activates the alarm so current alarm status captures the final display path.
- Verify instance member paths with `tagRead` before binding Perspective components.
- Use scaffold tags/UDTs for demos and tests; keep real process writeback in Project Library scripts.
- Prefer this existing scaffold path over adding broader tag-write endpoints unless a page-building test confirms a specific gap.

Do not add tag imports, provider creation, database edits, or Gateway configuration changes to the low-touch runner.
