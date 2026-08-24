# Perspective Performance Profile Workflow

## Contents

- [1. Scenario Definition](#1-scenario-definition)
- [2. Read-Only Gateway Discovery](#2-read-only-gateway-discovery)
- [3. Static Analyzer](#3-static-analyzer)
- [4. Browser Probe](#4-browser-probe)
- [5. Runtime Sampling Cadence](#5-runtime-sampling-cadence)
- [6. Classification Rules](#6-classification-rules)
- [7. Remediation Validation](#7-remediation-validation)
- [8. Evidence Bundle](#8-evidence-bundle)
- [9. Report Checklist](#9-report-checklist)

Use this reference when a Perspective performance request needs synchronized static, Gateway, session, and browser evidence.

The script commands in this reference are examples of helper behavior. If those helper files are not present in the target environment, recreate the equivalent behavior from `helper-script-blueprints.md`, preserving the same Ignition runner actions, Perspective resource details, evidence fields, gates, and rollback checks.

## 1. Scenario Definition

Before collecting data, define:

- `runId`
- Target Gateway alias, not a secret URL.
- Project, route, primary view, and known child views.
- Symptom: cold load, warm load, repeated navigation, tab close/lifecycle, idle dwell, click latency, multi-session scaling, or active freeze.
- Browser/device class, viewport, cache state, and the ready marker or selector.
- Sample interval, total duration, repetitions, session count, and explicit stop conditions.
- Primary metric and safety metrics.

Do not mix browser refresh, URL re-entry, back navigation, and fresh browser context in one timing set. They measure different cache and lifecycle behavior.

## 2. Read-Only Gateway Discovery

Start each session with:

1. `health` with `requestId`; inspect `runnerVersion`, `stackVersion`, `features`, and token/config state.
2. `gatewayInfo`; record Ignition version, Perspective module state/version/license, OS, Java, and project roots if provided.
3. `projectsList`, `routesList`, `viewsList`, and `viewRead` for the target.
4. `pageValidate` for the target route/view.
5. `logQuery` for recent WARN/ERROR lines related to the route, view, run ID, Perspective, bindings, or data source.

If runner API `0.3.79+` performance actions are available, add:

1. `metricsList` with bounded Perspective and Gateway-relevant filters.
2. `metricsSnapshot` using explicit metric tokens/names.
3. `gatewayPerformanceSnapshot` at the same cadence.
4. `perspectiveSessionsQuery` for the target project.
5. `threadDumpQuery` only during active freeze/backlog/CPU evidence, with narrow filters and confirmation.

For runner `0.3.92+`, require `perspectiveSessionsQueryMatchedCount` before interpreting filtered session truncation. `matchedCount` is the count after local `sessionIds` matching and before `maxResults`; `truncated` means matched sessions were omitted.

For a first run on a Gateway, after a runner update, or when contract behavior is uncertain, run the read-only contract harness before interpreting profile evidence:

```bash
python scripts/run_gateway_contract_tests.py --project MyProject --route /target-route --view "Folder/Primary View" --out-dir evidence/contracts-001
```

Add `--browser-url` and a non-secret `--browser-url-alias` when G-07 session correlation should be proven with a browser-owned Perspective session.

For a repeatable read-only Gateway bundle, use:

```bash
python scripts/collect_profile.py --project MyProject --route /target-route --duration-sec 30 --interval-sec 2 --out-dir evidence/run-001
```

For synchronized Gateway and browser evidence, add a browser URL and a non-secret alias:

```bash
python scripts/collect_profile.py --project MyProject --route /target-route --duration-sec 30 --interval-sec 2 --out-dir evidence/run-001 --browser-url "https://gateway.example/data/perspective/client/MyProject/target-route" --browser-url-alias customer-gateway --browser-ready-selector "[data-testid='perf-ready']"
```

The collector writes `manifest.json`, `static-profile.json`, `gateway-samples.ndjson`, `perspective-session-samples.ndjson`, `logs.json`, `browser-summary.json`, `browser-console.json`, `network-summary.json`, and `report.md`. If `--browser-url` is omitted, browser files are explicit placeholders with a missing-evidence reason.

After collecting a bundle, verify evidence integrity before using the report:

```bash
python scripts/verify_evidence_bundle.py evidence/run-001 --out-dir evidence/run-001-integrity
```

The verifier checks file hashes, JSON and NDJSON parseability, manifest-listed files, explicit `missingEvidence` reasons, `changedResources`, and report labels for observed evidence, interpretation, and unproven limits. Treat a verifier failure as a stop condition. Use `--require-file relative/path.json` for scenario-specific evidence that must be present or explicitly listed as missing.

## 3. Static Analyzer

Run `scripts/view_lint.py` against the `viewRead` response or exported `view.json`:

```bash
python scripts/view_lint.py path/to/viewread-response.json > static-profile.json
```

The analyzer reports:

- View hash and view JSON byte size.
- Components and component types.
- Static child view dependencies, dynamic/unresolved view paths, and view-instantiation families.
- Bindings, binding types, and tag binding modes.
- Polling/rate candidates.
- Cache/share fields where present.
- Script blocks and cost indicators.
- Tables, chart series/point counts, gauge axis/range counts, media payloads, virtualization/filter-result writeback hints, hidden/persistent content, parameter payloads, and object-depth statistics.
- Risk signals worded as candidates.

Static output must be stable for the same view hash. Do not report static findings as causes without runtime proof.

When the target route is not known, rank routes first:

```bash
python scripts/rank_routes.py --project MyProject --out-dir evidence/route-ranking --gateway-alias customer-gateway
```

`rank_routes.py` lists routes, reads primary views plus bounded static dependencies, runs the static analyzer, and writes `route-static-ranking.json`, `view-static-profiles.ndjson`, and `route-static-ranking.md`. Treat the score as a profiling priority only. Profile one selected route with synchronized Gateway/browser evidence before classifying the bottleneck.

## 4. Browser Probe

Use a deterministic ready marker on fixture views:

```html
data-testid="perf-ready"
```

For production views, use a user-approved stable selector. A HTTP 200, `pageValidate`, or non-error route response is not render proof.

The bundled probe can be used when Playwright is available:

```bash
node scripts/browser_route_probe.mjs --url "https://gateway.example/data/perspective/client/Project/route" --url-alias customer-gateway --ready-selector "[data-testid='perf-ready']" --out-dir evidence/run-001
```

When testing network sensitivity in a controlled environment, add Chromium network throttling to the probe or pass the matching `collect_profile.py` `--browser-network-*` options:

```bash
node scripts/browser_route_probe.mjs --url "https://gateway.example/data/perspective/client/Project/route" --url-alias customer-gateway --ready-selector "[data-testid='perf-ready']" --network-latency-ms 100 --network-download-kbps 512 --network-upload-kbps 512 --out-dir evidence/network-throttle
```

Use `--network-throttle-after-ready` when the throttle should begin after the first ready marker instead of before navigation. Record the throttle values in the scenario notes and do not mix throttled and unthrottled evidence in the same baseline set.

Capture:

- Ready marker elapsed time.
- Optional secondary ready marker elapsed time when the first visible parent state and total child/render-complete state are different.
- DOMContentLoaded/load timing where available.
- Largest Contentful Paint and long-task count/duration where available.
- DOM node count and browser JavaScript heap where available.
- Optional browser timeline samples during post-ready dwell windows when idle/soak trends matter.
- Console errors/warnings and page errors.
- Network response counts, statuses, and known content-length bytes.
- WebSocket frame counts and bytes.

When a deterministic interaction is part of the scenario, separately measure click timestamp to visible state change and preserve console/network evidence for that interaction.

For collector-owned R-04 click/action-latency evidence, pass a click target and a post-click result marker:

```bash
python scripts/collect_profile.py --project MyProject --route /target-route --duration-sec 30 --interval-sec 2 --out-dir evidence/run-001 --browser-url "https://gateway.example/data/perspective/client/MyProject/target-route" --browser-url-alias customer-gateway --browser-ready-selector "[data-testid='perf-ready']" --browser-click-selector "[data-testid='start-cycle']" --browser-click-label start-cycle --browser-click-result-selector "[data-testid='cycle-complete']"
```

Use `--browser-click-text` and `--browser-click-result-text` only for approved stable text. The probe records whether the result already matched before the click; treat that as ambiguous evidence unless the scenario explicitly expects a no-op. A valid R-04 run should show exactly one configured interaction, `interaction.ok: true`, no duplicate process writes, clean console/log evidence, and a latency distribution across repeated runs before any operator-impact claim.

When the post-click proof must show that a displayed value changed, add `--browser-watch-text-selector` and `--browser-watch-text-regex` through `collect_profile.py`. The browser probe records bounded before/after match values and a `changed` boolean; use this for event-driven refresh checks where the visible result is dynamic rather than a fixed success marker.

For repeated interaction evidence, use:

```bash
python scripts/run_interaction_profiles.py --run-id CLICK-001 --out-dir evidence/click-001 --project MyProject --route /target-route --browser-url "https://gateway.example/data/perspective/client/MyProject/target-route" --browser-url-alias customer-gateway --browser-ready-selector "[data-testid='perf-ready']" --browser-click-selector "[data-testid='start-cycle']" --browser-click-label start-cycle --browser-click-result-selector "[data-testid='cycle-complete']" --repetitions 7
```

The repeated runner writes one `collect_profile.py` bundle per repetition plus aggregate click-dispatch and click-to-result latency stats. It redacts raw browser URLs and click/result text in its own command logs. It cannot prove duplicate process writes unless the chosen screen exposes a scenario-specific write/message marker; capture that marker separately when the click writes to process state.

## 5. Runtime Sampling Cadence

For each sample window, write synchronized rows:

- `gateway-samples.ndjson`: `metricsSnapshot` and `gatewayPerformanceSnapshot` results.
- `perspective-session-samples.ndjson`: `perspectiveSessionsQuery` results.
- `logs.json`: focused `logQuery` results.
- `thread-excerpts.json`: redacted `threadDumpQuery` results only when triggered.

Recommended starting cadence:

- Baseline: 30 seconds before route open.
- Load window: route open until ready marker or timeout.
- Post-load: 30 seconds after ready.
- Idle dwell: 15 minutes for development checks, longer only with approval.
- Navigation lifecycle: 20 control-target-control cycles when lifecycle growth is suspected.
- Session scaling: 1, 5, 10, and optionally 20 sessions on staging only.

Lower the sample rate if profiler reads themselves produce material load.

For read-only R-07 idle dwell/soak checks, use:

```bash
python scripts/run_idle_dwell_profile.py --run-id IDLE-DWELL-001 --out-dir evidence/idle-dwell --route /target --view "Folder/Primary View" --browser-url "https://gateway.example/data/perspective/client/Project/target" --browser-url-alias customer-gateway --browser-ready-selector "[data-testid='perf-ready']" --duration-sec 900 --interval-sec 30 --browser-timeline-sample-interval-ms 30000
```

The idle-dwell helper wraps `collect_profile.py`, holds one browser route open without interaction, requires browser timeline evidence when timeline sampling is enabled, and writes JVM heap, non-heap, CPU/thread, Perspective metric, session/page, browser heap, DOM, long-task, and transfer trends. Interpret idle counter movement and positive slopes as follow-up flags. Do not call a leak from JVM heap alone; require retained Perspective sessions/pages, browser heap/DOM growth, or repeated target-specific evidence.

For cold versus warm route-load checks, use:

```bash
python scripts/run_cold_warm_load_profiles.py --run-id LOAD-001 --out-dir evidence/cold-warm --route /target --view "Folder/Primary View" --browser-url "https://gateway.example/data/perspective/client/Project/target" --browser-url-alias customer-gateway --browser-ready-selector "[data-testid='perf-ready']" --cold-repetitions 5 --warm-repetitions 5
```

The cold/warm helper writes one `collect_profile.py` bundle per observation, using a fresh Chromium profile directory for each counted cold load. It then runs one required uncounted warm-prime load and all counted warm loads in a shared persistent Chromium profile. The root summary includes counted-run rows, cold/warm phase medians, and warm-minus-cold median deltas. Use this when browser-cache/profile state is part of the declared scenario; report cold and warm aggregates separately and do not mix refresh, URL re-entry, back navigation, and new browser contexts in one result set.

For repeated navigation lifecycle checks, use:

```bash
python scripts/run_navigation_lifecycle.py --run-id NAV-001 --out-dir evidence/navigation --control-route /control --target-route /target --control-view "Folder/Control View" --target-view "Folder/Target View" --browser-control-url "https://gateway.example/data/perspective/client/Project/control" --browser-target-url "https://gateway.example/data/perspective/client/Project/target" --browser-url-alias customer-gateway --cycles 20 --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420
```

The navigation helper drives one Chromium context through control -> target -> control cycles and writes `browser-navigation-cycles.json`, `navigation-samples.ndjson`, `gateway-samples.ndjson`, `perspective-session-samples.ndjson`, browser console/network files, no-write readback evidence, `summary.json`, and `report.md`. Treat monotonically increasing target ready time, DOM, heap, active page/session, or metric counts as flags for repeat testing; do not call them leaks until the configured timeout/post-settle behavior and retained work are proven.

For browser-tab close or post-settle lifecycle checks, use:

```bash
python scripts/run_lifecycle_profile.py --run-id LIFE-001 --out-dir evidence/lifecycle --route /target --browser-url "https://gateway.example/data/perspective/client/Project/target" --browser-url-alias customer-gateway --post-samples 20 --interval-sec 5 --expected-session-timeout-sec 75 --timeout-grace-sec 15 --require-timeout-coverage
```

The lifecycle helper writes `lifecycle-samples.ndjson` with `pre`, `during`, and `post` phases plus browser evidence. Interpret retained sessions/pages only against the configured Perspective session timeout. A page that remains during a short post-close window is expected retention, not leak proof. Treat heap movement as a signal until a longer post-settle or GC-aware run shows retained pages/sessions/work.
Recent helper versions also report post-close page/session release timing, post-close heap first/min/max/last values, and a `timeoutCoverage` block. Prefer those fields over phase averages when deciding whether a page or browser session returned to zero. When `--require-timeout-coverage` is set, the helper fails unless the post-close observation covers the declared timeout plus grace. Choose `post-samples` and `interval-sec` so `(post-samples - 1) * interval-sec` is at least `expected-session-timeout-sec + timeout-grace-sec`.

For controlled I-04 memory-growth suspicion mechanics on dev/staging or an explicitly approved target, use:

```bash
python scripts/run_memory_growth_suspicion.py --run-id MEMORY-GROWTH-001 --out-dir evidence/memory-growth --project MyProject --cycles 3 --rows 500 --columns 30 --pre-samples 2 --during-samples 4 --post-samples 18 --interval-sec 5 --expected-session-timeout-sec 75 --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The memory-growth helper writes `memory-growth-samples.ndjson`, API raw evidence, `summary.json`, `summary.md`, and per-cycle browser console/network/summary files. It imports one disposable static route/view, repeats browser open/close cycles, baseline-subtracts fixture-new session/page tokens from pre-existing browser sessions, separates JVM heap from browser JavaScript heap, then rolls back and verifies route/view cleanup. Report JVM heap, browser heap, raw Perspective counts, and fixture-new retained sessions/pages separately. Do not call heap peaks or short-window retention a leak; leak language needs retained fixture-new sessions/pages after the declared timeout or stronger target-specific evidence.

For read-only multi-session scaling checks on staging or another approved target, use:

```bash
python scripts/run_multisession_profile.py --run-id SCALE-001 --out-dir evidence/scale --route /target --browser-url "https://gateway.example/data/perspective/client/Project/target" --browser-url-alias customer-gateway --session-counts 1,5,10
```

When sequential groups must start clean, add:

```bash
python scripts/run_multisession_profile.py --run-id SCALE-001 --out-dir evidence/scale --route /target --view "Folder/Primary View" --browser-url "https://gateway.example/data/perspective/client/Project/target" --browser-url-alias customer-gateway --session-counts 1,5,10 --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --baseline-wait-interval-sec 10 --fail-on-baseline-timeout
```

The multi-session helper opens concurrent browser probes for each requested group and writes `multi-session-samples.ndjson`, `baseline-wait-samples.ndjson` when baseline waiting is enabled, per-group browser evidence, `summary.json`, and `report.md`. Interpret during-minus-pre deltas instead of absolute session counts when existing sessions are present. If a previous group leaves retained sessions, either wait through the configured Perspective timeout plus grace period before the next group or label the group baseline-contaminated. Pass the exact `--view` when route inventory cannot resolve the route unambiguously.

## 6. Classification Rules

- Gateway CPU, bindings, scripts, fetches, or queue metrics rise while browser evidence stays modest: likely Gateway, binding, script, or data-source cost.
- Browser long tasks, DOM nodes, browser heap, or ready time rise while Gateway stays modest: likely browser/component rendering cost.
- Network bytes or resource counts rise while CPU stays modest: likely payload, cache, or network behavior.
- Query/fetch timing rises with low Gateway CPU: likely data-source or remote-provider latency.
- Session queue/backlog evidence aligns with freezes: capture one bounded thread snapshot during the active symptom.
- Heap peaks without retained component/session/page/browser evidence are not enough to call a leak.

For repeatable post-processing of an existing live bundle, use:

```bash
python scripts/classify_incident_bundle.py --summary evidence/profile-summary --out-dir evidence/incident-classification --label route-or-fixture-name
```

The classifier reads a `summary.json` file or bundle directory and writes `classification-summary.json` plus `classification-report.md`. It can label browser-rendering pressure, network/payload pressure, database-query activity, and Gateway script/queue pressure when the needed evidence crosses conservative thresholds. Blank metric families remain blank; do not turn a classifier label into a root-cause or remediation claim without the matching raw evidence and, for changes, repeated A/B or before/after proof. Use `--expect-label` in regression tests when a known evidence bundle should trigger a particular label.

For a development-only bounded long-running script incident fixture, use:

```bash
python scripts/run_long_script_incident.py --run-id LONG-SCRIPT-001 --out-dir evidence/long-script-incident --project MyProject --target-millis 5000 --max-millis 7000 --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The helper imports one disposable route/view with a bounded button script, waits for browser click/result proof, records an active-window screenshot/timestamp, starts a same-route second browser context during the first session's active window, samples Gateway/session/metric evidence immediately after the click signal, captures one focused thread dump, verifies focused log markers, then rolls back route/view resources. Run it only on dev/staging or explicitly approved targets, keep duration caps small, and treat it as I-03/I-01 mechanics evidence rather than customer freeze proof by itself.

For a development-only bounded queue-backlog mechanics fixture, use:

```bash
python scripts/run_queue_backlog_incident.py --run-id QUEUE-BACKLOG-001 --out-dir evidence/queue-backlog --project MyProject --task-counts 5,40 --work-millis 25 --max-work-millis 100 --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The helper imports disposable bounded button-action variants, profiles browser click-to-done timing with synchronized Perspective queue-length, queue-task, script, property-change, message, browser, network, and Gateway/session evidence, then rolls back route/view resources. I-02 is proven only when the larger variant shows sustained `queue-length` samples, returns to the recovered threshold by the final sample, and has a correlated interaction-delay increase versus the smaller baseline. Queue-task, script, property-change, and message counters are supporting activity signals; do not use them as a substitute for `queue-length` backlog proof.

When the goal is only to validate fixture mechanics or collect negative/sensitivity evidence, add `--allow-negative-i02` and report the resulting `mechanicsOk`, `strictI02Ok`, and `negativeI02Accepted` fields separately. Do not use that flag for customer root-cause proof. If the runner endpoint returns a non-JSON Gateway/server page during `health`, `dryRun`, apply, or readback, pause write/profile attempts and resume only after a lightweight `health` call returns a normal runner envelope.

For a development/staging data-source-delay mechanics fixture, use:

```bash
python scripts/run_datasource_delay_incident.py --run-id DATASOURCE-DELAY-001 --out-dir evidence/datasource-delay --project MyProject --database MyReadOnlyTestDatabase --delay-size 2500 --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The helper imports matching fast and delayed polling-disabled read-only Named Query route/view variants, proves a real query-backed label value changes after manual `refreshBinding()`, compares direct preview timing and browser click-to-query-label timing, checks browser DOM/heap/long-task and Gateway CPU stability, then rolls back route/view/query resources. Use only an approved test database or equivalent disposable data source. Treat passing evidence as I-06 fixture mechanics; customer data-source root cause still needs customer-route timing, query/provider evidence, and repeated or incident-specific correlation.

Classifications are hypotheses until a controlled A/B or before/after run proves them.

## 7. Remediation Validation

Each candidate should declare:

- Observed evidence.
- Primary metric expected to improve.
- Safety metrics that must not regress.
- Exact route/view/tag/query/project resources to change.
- Dry-run, apply, readback, browser, functional-equivalence, and rollback steps.

Use current `viewSha256` or equivalent drift guard before overwriting. Re-run the same scenario with the same browser/cache/session/data conditions. If the change is retained, record why rollback was not performed. If the change is rejected, rollback and verify the profile restored.

For control-versus-target or before/after math, compare two evidence bundles:

```bash
python scripts/compare_profiles.py --control-dir evidence/control --target-dir evidence/target
```

The script writes `comparison.json` and `comparison.md` with target-minus-control deltas for static, browser, network, Gateway, session, and global Perspective metrics. A single comparison is observational; repeated paired runs are required before a causal remediation claim.

For repeated pairs, use the orchestrator:

```bash
python scripts/run_paired_profiles.py --run-id RUN-001 --out-dir evidence/repeated --pairs 7 --control-route /control --target-route /target --control-browser-url "https://gateway.example/data/perspective/client/Project/control" --target-browser-url "https://gateway.example/data/perspective/client/Project/target" --browser-url-alias customer-gateway
```

The orchestrator runs `collect_profile.py` for each control/target pair, runs `compare_profiles.py` per pair, and writes `summary.json` plus `summary.md` with median target-minus-control deltas. Use it for route comparison and before/after remediation evidence; do not treat repeated route comparison as remediation proof unless functional-equivalence, safety, and rollback gates also pass.

For a disposable table row/column scaling fixture, use:

```bash
python scripts/run_table_scaling.py --run-id TABLE-SCALE-001 --out-dir evidence/table-scaling --project MyProject --row-counts 100,500,1000 --column-counts 10,30,50 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper imports each table size independently with a fixed surrounding view shape, profiles it, compares each size to the smallest baseline, rolls back, and verifies route/view cleanup. Report rows, columns, cells, view bytes, table bytes, DOM, heap, transfer, WebSocket, and Gateway/session signals separately. Use it before A-11 or A-12 when table size is unknown, and require repeated/customer-specific evidence before recommending row, column, payload, or virtualization limits.

For a disposable Table filter-results writeback A/B fixture, use:

```bash
python scripts/run_table_filter_writeback_ab.py --run-id TABLE-FILTER-WB-001 --out-dir evidence/table-filter-writeback --project MyProject --rows 1000 --columns 30 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper keeps table data, columns, filter text, and visible shape fixed while changing only `props.filter.results.enabled`. It verifies exact view readback, profiles each variant, compares writeback-on minus writeback-off, then rolls back route/view resources and verifies cleanup. Report filtered row count, table bytes, browser heap, DOM, long tasks, transfer/WebSocket bytes, property-change metrics, and Gateway/session signals separately. Preserve the functional requirement first: disabling filtered-result writeback is only safe when no downstream bindings, scripts, or integrations depend on `props.filter.results.data`, or when an equivalent replacement has been proven.

For a disposable chart count and point-count scaling fixture, use:

```bash
python scripts/run_chart_scaling.py --run-id CHART-SCALE-001 --out-dir evidence/chart-scaling --project MyProject --sizes 1x3x100,1x3x1000,4x3x500,8x3x1000 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper imports one Time Series Chart fixture at a time, changes only chart count, series count, and static points per series, profiles browser/Gateway/network evidence, compares each variant to the smallest baseline, then rolls back route/view resources and verifies cleanup. Report chart count, total series, total points, chart payload bytes, DOM, long tasks, browser heap, transfer/WebSocket bytes, and Gateway/session signals separately. Treat the result as client/payload characterization unless the tested chart uses bindings or data-source calls; static points alone do not prove historian, query, or provider cost.

For a disposable XY Chart count, series-count, and static `dataSources` point-count scaling fixture, use:

```bash
python scripts/run_chart_scaling.py --chart-kind xy --run-id XY-CHART-SCALE-001 --out-dir evidence/xy-chart-scaling --project MyProject --sizes 1x2x100,1x2x500,4x2x100,8x2x500 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

For XY fixtures, `--sizes` entries are `CHARTSxSERIESxPOINTS`. The helper generates one documented XY `props.dataSources` dataset per chart, maps each series to fields in that dataset, profiles browser/Gateway/network evidence, compares each variant to the smallest baseline, then rolls back route/view resources and verifies cleanup. Report XY chart count, total series, `dataSources` rows, plotted points, payload bytes, DOM, long tasks, browser heap, transfer/WebSocket bytes, and Gateway/session signals separately. Treat the result as static XY client/payload characterization unless the tested screen uses bindings, historian pens, queries, or provider-backed data.

For a disposable Gauge count, axis-count, and range-count scaling fixture, use:

```bash
python scripts/run_chart_scaling.py --chart-kind gauge --run-id GAUGE-SCALE-001 --out-dir evidence/gauge-scaling --project MyProject --sizes 1x1x2,1x2x4,4x1x4,8x2x8 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

For Gauge fixtures, `--sizes` entries are `GAUGESxAXESxRANGES`. The helper changes only gauge count, axes per gauge, and static ranges per axis, profiles browser/Gateway/network evidence, compares each variant to the smallest baseline, then rolls back route/view resources and verifies cleanup. Report gauge count, axis count, range count, gauge payload bytes, DOM, long tasks, browser heap, transfer/WebSocket bytes, and Gateway/session signals separately. Treat the result as Gauge client/payload characterization unless the tested screen uses bindings or data-source calls.

For seeded or customer chart shapes where synthetic fixture JSON would be a guess, clone and profile an existing source view instead:

```bash
python scripts/run_seed_view_clone_profile.py --run-id SEED-CHART-001 --out-dir evidence/seed-chart --project MyProject --source-view "Folder/Seed Chart View" --source-allowed-view-prefix "Folder/" --expected-component-type ia.chart.powerchart --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The helper reads the source view, writes a disposable clone under the allowed test view prefix, injects a run-specific ready marker, adds a temporary route, profiles the cloned route with synchronized Gateway/browser evidence, then rolls back and verifies route/view cleanup. Use it for Power Chart, trend, or other Designer-created shapes before creating a synthetic fixture. Treat the result as render/profile mechanics and source-shape evidence only; it does not prove historian, query, provider, or pen cost unless the cloned source view actually exercises those bindings or data sources.

For a disposable bounded property-change storm fixture, use:

```bash
python scripts/run_property_change_chain.py --run-id PROP-STORM-001 --out-dir evidence/property-storm --project MyProject --targets 10,100,250 --max-changes 750 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper imports one bounded storm variant at a time, triggers a button event that writes custom properties up to the configured target, profiles Perspective property-change/script/queue/message metrics plus browser/Gateway/network evidence, compares larger write counts to the smallest baseline, then rolls back route/view resources and verifies cleanup. Report the write target, property-change deltas/rates, script deltas/rates, queue-task rates, browser long tasks, DOM, WebSocket bytes, and Gateway CPU/heap separately. This fixture intentionally avoids unproven component `propertyChange` event JSON; use a Designer-seeded event resource before claiming evidence about real handler recursion.

For a disposable transform/script alternative fixture, use:

```bash
python scripts/run_transform_cost_ab.py --run-id TRANSFORM-COST-001 --out-dir evidence/transform-cost --project MyProject --label-count 80 --work-iterations 250 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper imports same-visible-shape Document/custom-property, expression-only, and property-binding script-transform variants, verifies exact readback and page validation, profiles static script count plus Perspective expression/script/property/queue metrics, browser timing, DOM, heap, transfer, and WebSocket evidence, compares expression/script variants to the Document data baseline, then rolls back and verifies cleanup. Use it for A-05-style decisions about transform or script alternatives. Do not assume static script count predicts runtime script counters by itself; report output equivalence, static view size, browser evidence, and Gateway/session metrics together.

For a disposable large-table virtualization A/B fixture, use:

```bash
python scripts/run_table_ab_remediation.py --run-id TABLE-AB-001 --out-dir evidence/table-ab --project MyProject --route /llm-table-ab-001 --view-path "LLM Tests/PerformanceProfiler/TableAB001" --gateway-alias customer-gateway --browser-url-alias customer-gateway --rows 500 --columns 30
```

The helper builds a valid Ignition project-resource ZIP for a disposable route/view, profiles a table with `props.virtualized: false`, overwrites the same view with `props.virtualized: true` using current `viewSha256` drift guard, profiles again, compares the bundles, verifies data/column hashes, rolls back the after variant to before, then removes the disposable route/view. Use it as a controlled A-10/A-11 and V-02 through V-09 mechanics harness; repeat paired runs before making a causal optimization claim.

For repeated table fixture observations, use:

```bash
python scripts/run_table_ab_repeated.py --run-id TABLE-AB-REPEAT-001 --out-dir evidence/table-ab-repeat --project MyProject --repetitions 7 --rows 500 --columns 30 --gateway-alias customer-gateway --browser-url-alias customer-gateway --pause-sec 10
```

The repeated helper runs the guarded single fixture once per repetition with fresh disposable route/view names and aggregates the browser deltas against the declared causal policy. If the primary metric does not improve in enough pairs or by enough median percentage, report that the remediation was rejected or remains unproven. Increase `--pause-sec` to cover the configured Perspective session timeout plus grace period when Gateway/session metrics are part of the claim.

For a disposable Embedded View breadth scaling fixture, use:

```bash
python scripts/run_embedded_breadth_scaling.py --run-id EMBED-BREADTH-001 --out-dir evidence/embedded-breadth --project MyProject --counts 1,10,50,100 --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The helper applies one parent/child fixture at a time, validates the parent route plus child dependency, profiles browser/Gateway evidence, compares each count to the one-instance baseline, rolls back, and verifies both route and view cleanup. Use it to find a tested scaling curve or knee point for the fixture or approved staging screen; do not promote the measured count as a platform-wide limit.

For a disposable Embedded View nesting-depth scaling fixture, use:

```bash
python scripts/run_embedded_depth_scaling.py --run-id EMBED-DEPTH-001 --out-dir evidence/embedded-depth --project MyProject --depths 1,2,4,6 --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The helper applies one static nested chain at a time and waits for a leaf ready marker, so browser-ready evidence proves the top route and every static child level rendered. It compares each depth to the one-level baseline, rolls back, and verifies route plus view cleanup. Use it for a tested nesting-depth curve; do not turn a synthetic fixture depth into a universal Embedded View rule.

For a disposable Embedded View loading-mode fixture, use:

```bash
python scripts/run_embedded_loading_mode.py --run-id EMBED-LOADING-001 --out-dir evidence/embedded-loading --project MyProject --modes with-parent,after-parent --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The helper compares `props.loading.order` values and records the parent marker as primary ready plus the child marker as secondary/total ready. Use it when the question is perceived first render versus child completion. Treat the result as fixture-specific and report both timings separately.

For a disposable hidden-content A/B fixture, use:

```bash
python scripts/run_hidden_content_ab.py --run-id HIDDEN-AB-001 --out-dir evidence/hidden-ab --project MyProject --variants hidden,removed --gateway-alias customer-gateway --browser-url-alias customer-gateway
```

The helper compares a subtree hidden with Perspective `meta.visible: false` against a removed-subtree variant. It validates exact readback, profiles browser/Gateway evidence, compares removed-minus-hidden deltas, rolls back, and verifies route/view cleanup. Use it to test whether hidden content still carries static or runtime cost in the tested design. Report static component/binding reductions separately from browser and Gateway deltas, and require repeated clean-baseline pairs before claiming a causal improvement.

For a disposable Tab Container `runWhileHidden` fixture, use:

```bash
python scripts/run_tab_runwhilehidden_ab.py --run-id TAB-RWH-001 --out-dir evidence/tab-runwhilehidden --project MyProject --work-labels 80 --background-hold-ms 15000 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

For a Tab Container that loads tab content from child views, run the same fixture in view-path mode:

```bash
python scripts/run_tab_runwhilehidden_ab.py --run-id TAB-RWH-VIEWPATH-001 --out-dir evidence/tab-runwhilehidden-viewpath --project MyProject --content-mode viewpath --work-labels 80 --background-hold-ms 15000 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper imports either a direct-child Tab Container fixture or a parent Tab Container plus sibling child views for `props.tabs[].viewPath`, activates the work tab, switches back to a control tab, samples during the background hold, compares `runWhileHidden: false` with `runWhileHidden: true`, then rolls back and verifies route/view cleanup. In view-path mode it declares dependency view paths, verifies child-view readback, and uses index-based browser switching because the tab labels may come from view content. Do not set both `text` and `viewPath` on the same tab object; Ignition uses `text` instead of `viewPath` when both are present. Use the fixture to test whether tab-hidden content is retained in the browser and whether Gateway expression/property work changes for the tested design. Report browser DOM/heap retention separately from Gateway expression, property-change, fetch, queue, and database signals. Repeat clean-baseline pairs before making a remediation rule.

For a disposable Carousel repeated-rotation fixture, use:

```bash
python scripts/run_carousel_rotation.py --run-id CAROUSEL-ROTATION-001 --out-dir evidence/carousel-rotation --project MyProject --slide-count 4 --work-labels 18 --cycles 16 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper imports same-child-view Carousel variants with `props.lazyLoad` off and on, advances `props.activePane` through a bounded button event, captures browser pane/slide-label changes plus DOM, heap, console, network, and WebSocket evidence, samples Gateway/session metrics during rotation, compares lazy-load-on minus lazy-load-off, then rolls back and verifies route/view cleanup. Confirm the Carousel resource shape from official docs, Designer seeds, or runner seed-read evidence before generating fixtures; a route that passes `pageValidate` can still fail at runtime if the component registry does not recognize the serialized component type. Treat lazy loading as a hypothesis about initial retained DOM/payload and rotation-time work, not as a universal recommendation, and repeat clean-baseline pairs on customer-like child views before making a remediation rule.

For a disposable child-view parameter-payload fixture, use:

```bash
python scripts/run_parameter_payload_ab.py --run-id PARAM-PAYLOAD-001 --out-dir evidence/parameter-payload --project MyProject --embedded-count 12 --deep-groups 18 --deep-width 10 --deep-depth 4 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper compares the same visible child count and carrier shape with scalar child-view params versus deep object/array params. The default carrier is Embedded View `props.params`; add `--carrier flex-repeater --instance-count 12` for Flex Repeater `props.instances[]` parameters, or `--carrier view-canvas --instance-count 12 --canvas-columns 4` for View Canvas `props.instances[].viewParams`. It browser-proves child parameter flow, profiles Gateway/browser/network evidence, compares deep-minus-scalar deltas, then rolls back and verifies route/view cleanup. Use static parameter-payload bytes, WebSocket and transfer bytes, browser heap, and readiness evidence together. Repeat clean-baseline pairs, and build a matching fixture before generalizing to dynamic paths or customer-specific parameter conventions.

For a disposable expression poll-rate scaling fixture, use:

```bash
python scripts/run_poll_rate_scaling.py --run-id POLL-RATE-001 --out-dir evidence/poll-rate --project MyProject --rates 250,1000,5000 --label-count 60 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper builds same-shape visible expression workloads and changes only `now(rate)`. It validates exact readback, profiles browser/Gateway evidence for each rate, compares faster rates against the slowest rate, rolls back, and verifies route/view cleanup. Use clean-baseline waiting when rates run sequentially; retained Perspective browser sessions from the previous variant can otherwise distort per-session metric deltas. Report Gateway expression/property-change/queue signals against the screen's required freshness, not as a universal poll-rate recommendation.

For a disposable query polling versus manual `refreshBinding()` fixture, use:

```bash
python scripts/run_refresh_binding_ab.py --run-id REFRESH-BINDING-001 --out-dir evidence/refresh-binding --project MyProject --query-count 8 --polling-rate-sec 1 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper imports a disposable read-only Named Query plus same-shape query-bound label views. The polling variant leaves query polling enabled; the manual variant disables polling and uses a Button event script to call `refreshBinding("props.text")` on each watched label. Browser evidence proves the manual click changes the first watched label value, then the helper compares polling-minus-manual evidence and rolls back route, view, and Named Query resources. Use this for A-03-style decisions about continuous query polling versus bounded event-driven refresh, not as a universal rule to remove polling.

For a disposable query Cache & Share multi-session fixture, use:

```bash
python scripts/run_query_cache_share_ab.py --run-id QUERY-CACHE-001 --out-dir evidence/query-cache-share --project MyProject --query-count 8 --session-count 5 --polling-rate-sec 1 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper imports disposable read-only Named Queries plus same-shape query-bound label views, with Cache & Share disabled for one variant and enabled for the other. It verifies exact view readback, opens concurrent browser sessions, samples database query timers plus Perspective metrics, compares Cache-on versus Cache-off, and rolls back route, view, and Named Query resources. Treat the serialized Cache & Share setting as a hypothesis until runtime database query counts or equivalent query-activity counters fall by the declared meaningful threshold across repeated clean-baseline pairs.

For a disposable tag-history Cache & Share multi-session fixture, use:

```bash
python scripts/run_tag_history_cache_share_ab.py --run-id HISTORY-CACHE-001 --out-dir evidence/history-cache-share --project MyProject --binding-count 8 --history-tag-count 3 --session-count 5 --polling-rate-sec 1 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper creates a bounded history-enabled expression-tag fixture under an allowed tag prefix, verifies current values with `tagRead`, waits for `historyProbe` to show good-sample historian rows on runner `0.3.137+`, then imports same-shape tag-history label views with Cache & Share disabled for one variant and enabled for the other. Browser evidence waits for rendered history-row text, profile evidence samples database/historian/Perspective metrics across concurrent sessions, and rollback verifies generated route/view cleanup. Current runner builds may not expose tag deletion, so treat the bounded tag fixture as retained test setup unless the target API provides an explicit cleanup action. Do not report tag-history Cache & Share as a remediation until runtime query or historian activity falls by the declared meaningful threshold across repeated clean-baseline pairs.

For a disposable direct/indirect/reference tag binding mode fixture, use:

```bash
python scripts/run_tag_binding_mode_ab.py --run-id TAG-BINDING-001 --out-dir evidence/tag-binding-mode --project MyProject --binding-count 12 --tag-count 12 --session-count 5 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The helper creates bounded source tags, indirect-binding parameters, and reference tags, then imports same-shape label views for direct local tags, indirect tag paths, and direct bindings to reference tags. It verifies tag configuration/readback, exact view readback, `pageValidate`, browser-visible initial and updated values, synchronized multi-session profile evidence, and route/view rollback. Current runner builds may not expose tag deletion, so treat generated tags as retained controlled test setup unless the target API provides a cleanup action. Static view JSON can show a reference-tag variant as a direct binding because the provider indirection lives in the tag configuration; record UI binding shape and provider/tag model separately.

When Cache & Share query-count evidence is ambiguous, first prove whether the chosen database metric can see the query shape being tested:

```bash
python scripts/run_query_multiplicity_sensitivity.py --run-id QUERY-SENS-001 --out-dir evidence/query-sensitivity --project MyProject --label-count 8 --session-count 5 --polling-rate-sec 1 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The sensitivity helper imports three disposable variants with Cache & Share disabled: one query-bound property, many query-bound properties sharing one Named Query path, and many query-bound properties using distinct Named Query paths. It verifies exact view and Named Query readback, profiles concurrent browser sessions, compares database query deltas, and rolls back route, view, and Named Query resources. If the metric does not visibly respond to the relevant query shape, treat Cache & Share deltas for that shape as inconclusive and gather a better customer-specific signal before making a recommendation.

When the target view uses one Named Query path with runtime parameters, test parameter shape separately:

```bash
python scripts/run_query_parameter_sensitivity.py --run-id QUERY-PARAM-001 --out-dir evidence/query-parameter-sensitivity --project MyProject --query-count 8 --session-count 5 --polling-rate-sec 1 --gateway-alias customer-gateway --browser-url-alias customer-gateway --wait-for-clean-baseline --baseline-max-browser-sessions 0 --baseline-wait-timeout-sec 420 --fail-on-baseline-timeout
```

The parameter-shape helper imports four disposable variants: identical parameter values with Cache & Share off/on and distinct parameter values with Cache & Share off/on. It verifies Named Query preview/readback, exact query binding readback, browser-ready text containing the returned parameter value, synchronized multi-session profiles, and route/view/Named Query cleanup. Use it before interpreting Cache & Share on parameterized screens; report whether the database metric responds to distinct parameter values separately from whether Cache & Share reduces work for a given parameter shape.

## 8. Evidence Bundle

A complete bundle normally contains:

```text
manifest.json
static-profile.json
gateway-samples.ndjson
perspective-session-samples.ndjson
browser-summary.json
browser-console.json
network-summary.json
logs.json
thread-excerpts.json
comparison.json
report.md
```

`thread-excerpts.json` and `comparison.json` are optional and should be present only when relevant.

Manifest fields:

- Gateway alias.
- Ignition/Perspective/runner versions and runner feature flags.
- Project, route, primary view, dependencies, and view hashes.
- Browser engine/version, viewport, device class, throttling, and cache state.
- Scenario steps, sample cadence, repetitions, session count, and timestamps.
- Evidence grade: Observed, Correlated, Causal, or Unproven.
- Missing evidence and the reason it was unavailable.

Run `scripts/verify_evidence_bundle.py` after bundle creation and before report handoff. Keep verifier output beside the evidence bundle or in a sibling integrity folder. The integrity report is evidence about the bundle; it is not a replacement for the raw Gateway, session, browser, log, or comparison files.

## 9. Report Checklist

The report must answer:

- What was directly observed?
- What is inferred?
- What is causally proven?
- What remains unproven?
- Which resources changed, if any?
- Did primary metrics improve and did safety metrics regress?
- Were functional markers, values, quality, and interactions preserved?
- Was rollback performed or intentionally skipped?
