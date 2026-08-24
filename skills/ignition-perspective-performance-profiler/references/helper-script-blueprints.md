# Helper Script Recreation Blueprints

## Availability Boundary

The customer package now ships the approved helpers. Apply the following original fallback rule only when a shipped helper is unavailable or cannot run in the customer's restricted environment:

The helper script names in this guide are implementation labels, not required shipped files. When those files are unavailable, recreate the equivalent behavior from `references/helper-script-blueprints.md`: preserve the same Ignition runner actions, Perspective resource/readback details, evidence fields, rollback gates, and verifier decisions before relying on the result.

## Contents

- [Common Helper Contract](#common-helper-contract)
- [Core Read-Only Helpers](#core-read-only-helpers)
- [Lifecycle And Baseline Helpers](#lifecycle-and-baseline-helpers)
- [Incident Mechanics Helpers](#incident-mechanics-helpers)
- [Comparison And Claim Gates](#comparison-and-claim-gates)
- [Disposable Fixture Helpers](#disposable-fixture-helpers)

Use this reference when the skill names a helper script but the helper code is not available in the customer's environment. Recreate the behavior, not the filename. A recreated helper can be Python, Jython, JavaScript, shell plus API calls, or an LLM tool sequence as long as it preserves the Ignition-specific gates, evidence shape, and rollback semantics below.

Do not invent unsupported runner actions or Perspective resource names. Discover capabilities from `health.supportedActions` and `health.features`, then read live project, route, view, metric, session, tag, Named Query, and database objects before using them.

When recreating a helper in a different runtime, especially translating local Python helper behavior into Gateway-side Jython or browser-side JavaScript, call out each Ignition-specific dependency in the new helper: the runner action or `system.*` call it depends on, the project/resource path it reads or writes, the Perspective property shape it expects, the readback or browser proof that validates it, and the rollback or no-write gate that limits risk.

When a helper step depends on a named Ignition feature, call out that feature individually rather than relying on a broad "Python helper" description. Examples include Named Query parameter definitions, Perspective `propConfig` binding config, Gateway `system.*` function signatures, tag provider paths, historian providers, page routes, session metrics, and rollback/readback actions.

If the recreated helper includes an Ignition-specific operation, document that operation next to the code or tool step that performs it. Do not summarize all dependencies in one vague note. Name the exact dependency category:

- Runner or Gateway API action, such as `viewRead`, `pageValidate`, `namedQueryPreview`, `metricsSnapshot`, `perspectiveSessionsQuery`, `tagRead`, or `historyProbe`.
- Gateway-side Jython or `system.*` call, including the expected argument shape, project scope, and whether it is read-only or writes resources.
- Project resource path, such as Perspective view paths, page routes, named-query paths, tag paths, database connections, script paths, or history providers.
- Perspective JSON schema detail, such as `propConfig`, binding `type`, binding `config`, `cacheAndShare`, `props.params`, `props.instances[]`, `props.tabs[]`, `meta.visible`, or event-script locations.
- Runtime proof, such as readback equality, route-to-view validation, browser-visible ready/result text, returned query/tag values, metric tokens, session tokens, logs, or thread evidence.
- Cleanup guard, such as dry-run/apply confirmation, backup name, rollback command, route/view/query/tag cleanup readback, or an explicit bounded-persistence note when the current API cannot delete a fixture resource.

## Common Helper Contract

Every recreated helper should:

- Accept a stable `runId`, output directory, project, route or view identifiers, browser alias, and sample settings.
- Call `health` first; record `runnerVersion`, `stackVersion`, `supportedActions`, and `features`.
- Treat runner actions and feature flags separately. For example, clean-baseline helpers that need `perspectiveSessionsQuery` should check it in `health.supportedActions`, while feature flags such as `perspectiveSessionsQueryMatchedCount` describe response behavior. Use the union only as a legacy fallback after recording both sets.
- Use request IDs that include the run ID and step name.
- Use redacted Gateway/browser aliases in reusable reports; keep raw URLs, tokens, headers, hostnames, usernames, user agents, and session identifiers out of portable notes.
- Discover routes and views with `routesList`, `viewsList`, `viewRead`, and `pageValidate`; do not guess route-to-view mapping.
- Store raw request/response JSON, browser summaries, metrics/session samples, logs, comparison outputs, and a short report.
- Preserve parseable JSON/NDJSON, SHA-256 hashes for important view/package/profile files, and explicit missing-evidence records.
- Keep static findings, observed runtime deltas, correlated signals, causal proof, and unproven hypotheses separate.

For any helper that writes a disposable fixture or remediation variant:

- Require explicit approval for non-read-only work, especially production targets.
- Use an allowlisted test route prefix and view prefix; avoid customer production route/view paths unless the user approved that exact target.
- Dry-run the package before apply.
- Apply with an explicit confirmation, current-resource drift guard when overwriting, and captured backup or rollback reference.
- Read back the exact view/resource after apply; verify `pageValidate` route-to-view mapping.
- Browser-prove a visible ready marker that is unique to the run and route. `document.title` alone is shell evidence, not view readiness.
- Profile the scenario with synchronized Gateway, Perspective session, and browser evidence.
- Roll back or remove the disposable route/view/query resources, then verify the route/view/query cleanup with discovery/readback.
- Treat failed readback, missing ready text, stale sessions, browser console/render errors, non-JSON runner envelopes, or partial rollback as stop conditions unless the report explicitly labels the artifact as failed-boundary evidence.

## Core Read-Only Helpers

### Gateway Contract Tests

Equivalent to `run_gateway_contract_tests.py`.

Recreate it as a read-only contract suite:

- G-01: `health` succeeds and shows the expected runner version floor, supported actions, feature flags, token/auth state, and stack version.
- G-02: `gatewayInfo` returns Ignition/Gateway/Perspective context without exposing secrets.
- G-03: invalid or missing request bodies return structured runner errors, not unhandled Gateway pages.
- G-04: `projectsList`, `routesList`, `viewsList`, `viewRead`, and `pageValidate` work for the intended project/route/view and preserve route-to-view mapping.
- G-05: `metricsList`, `metricsSnapshot`, and `gatewayPerformanceSnapshot` are bounded, parseable, and do not require writes.
- G-06: `perspectiveSessionsQuery` is bounded, redacted, and exposes matched/truncated counts when the runner supports them.
- G-07: optional browser/session correlation opens the exact Perspective route, waits for body-visible readiness, and correlates a browser-observed page/session with runner session samples.
- G-08: `logQuery` and optional `threadDumpQuery` are bounded, filtered, redacted, and do not run unless the scenario justifies them.
- G-09: unsupported or unavailable actions are reported as missing capability, not treated as evidence.
- G-10: request/response sizes, max-results fields, and timeouts are enforced.
- G-11: no-write proof is preserved: no fixture resources, backups, audit writes, tag writes, or project-resource changes occur during the contract suite.
- G-12: the report contains pass/fail/skip status, raw responses, runner version, stack version, and next blocked capability.

### Static View Profile

Equivalent to `view_lint.py` or `profile_view_json.py`.

Given a `viewRead` response or exported `view.json`, parse JSON structurally. Count components, nesting depth, bindings, polling candidates, query/tag/history bindings, Cache & Share settings, scripts, transform scripts, event scripts, table/chart/gauge payload sizes, Embedded View/Flex Repeater/View Canvas carriers, tabs, Carousel usage, hidden `meta.visible: false` subtrees, parameter payload bytes, and custom-property data size. Record component paths so runtime browser evidence can be matched back to view content. Treat all findings as candidates until runtime evidence supports them.

Ignition-specific details to preserve:

- Perspective component JSON has nested child containers; do not rely on string searches when a JSON traversal is possible.
- Query bindings, tag bindings, expression bindings, script transforms, and event scripts have different runtime meanings. Keep them separate.
- Cache & Share is only a configuration hypothesis until runtime query, historian, or equivalent activity counters prove consolidation.
- A reference tag can appear as a direct Perspective tag binding because provider indirection lives in tag configuration; report UI binding shape and provider/tag model separately.

### Route Ranking

Equivalent to `rank_routes.py`.

Read all project routes and candidate views, compute static triage scores, and rank routes by evidence-backed risk signals: view JSON size, component count, nested children, Embedded View/Flex Repeater/View Canvas count, table/chart payload indicators, binding counts, polling settings, script count/size, hidden retained content, parameter payload size, and route dependency fan-out. Output a ranked list with the route, mapped primary view, static signals, missing data, and the top route to profile. Do not call the ranked route the cause without runtime evidence.

### Browser Route Probe

Equivalent to `browser_route_probe.mjs`.

Open the Perspective route in a controlled browser context and write:

- `browser-summary.json`: ready marker timing, navigation timing, LCP when available, DOM node count, used JS heap, long task count/total, result/click timing, screenshot path if captured, and final status.
- `browser-console.json`: console errors/warnings with redaction.
- `network-summary.json`: request count, transfer sizes, content lengths when known, WebSocket frame and byte counts, and throttling settings if applied.

Ignition-specific details to preserve:

- Use the Perspective client URL shape for the target Gateway/project/route.
- Require a body-visible ready marker, stable selector, or approved shell-only readiness rule.
- For click evidence, require the post-click result marker to be absent before the click and visible after the click.
- For repeated clicks, preserve cadence and mode (`playwright`, mouse, or DOM dispatch) and record whether visible fixture counters matched.
- For network/backpressure tests, apply throttling after ready and record whether the throttle applied to all variants or only the backlog/target variant.

### Synchronized Profile Bundle

Equivalent to `collect_profile.py`.

Recreate it as a read-only bundle:

1. Discover route/view with runner actions.
2. Save `viewRead` and static profile.
3. Start browser probing when browser evidence is requested.
4. Use `metricsList` with Perspective-focused filters and keep the returned metric tokens.
5. Sample `metricsSnapshot`, `gatewayPerformanceSnapshot`, and `perspectiveSessionsQuery` at the declared cadence and duration.
6. Query focused recent logs for Perspective, route, view, run ID, binding, script, query, tag, and data-source context.
7. Finish browser probing and write a manifest/report.

Preserve these evidence files when possible:

```text
manifest.json
summary.json
view-read.json
static-profile.json
metrics-list.json
gateway-samples.ndjson
perspective-session-samples.ndjson
browser-summary.json
browser-console.json
network-summary.json
logs.json
thread-excerpts.json
comparison.json
report.md
raw/
```

For I-02 queue evidence, make sure `metricsList` includes `perspective.session-<uuid>.queue-length` and `perspective.session-<uuid>.queue-tasks` when available. Sampling too many metric tokens too frequently can make collection exceed the parent timeout; reduce token count only if the queue-length and queue-task tokens remain in scope.

### Evidence Bundle Verifier

Equivalent to `verify_evidence_bundle.py`.

Validate that JSON files parse, NDJSON files parse line by line, expected files are present or explicitly listed as missing, SHA-256 fields match saved files when present, raw evidence exists for claimed metrics/browser/log/session data, report boundaries label observed/correlated/causal/unproven statements, and integrity output is separate from the source bundle. Do not let a verifier output replace raw evidence.

## Lifecycle And Baseline Helpers

### Minimal Control Route Profile

Equivalent to `run_minimal_control_route_profile.py`.

Build or use a stable minimal/control route, measure cold and warm route load, run timeout-aware tab close/session lifecycle checks, wait for clean baselines when configured, and write one composite bundle. Ignition-specific gates: `pageValidate` must map the route to the intended view; post-close sampling must cover the configured Perspective session timeout plus grace before classifying retained pages/sessions.

### Cold/Warm Load Profiles

Equivalent to `run_cold_warm_load_profiles.py`.

Run fresh-profile cold observations, then one uncounted shared-profile warm prime, then counted warm observations in the same browser profile. Report cold and warm separately. Do not mix reload, URL re-entry, back navigation, and fresh browser context in one metric.

### Interaction Profiles

Equivalent to `run_interaction_profiles.py`.

Repeat the same click or operator action with stable pre-ready and post-click result markers. Record per-repetition browser click elapsed time, result elapsed time, console/network evidence, Gateway/session metric deltas, and failures. Use enough repetitions for a distribution before claiming latency behavior.

### Navigation Lifecycle

Equivalent to `run_navigation_lifecycle.py`.

Repeat control -> target -> control navigation cycles. Preserve separate control and target route/view mappings, browser readiness for each route, cycle timings, session/page counts, and Gateway/browser deltas. Use clean-baseline waits when retained sessions from previous cycles could contaminate samples.

### Browser Tab Close / Session Lifecycle

Equivalent to `run_lifecycle_profile.py`.

Open a target route, capture during-open evidence, close the tab or browser context, then sample until the expected Perspective timeout plus grace is covered. Report raw page/session counts, fixture-new retained tokens, JVM heap, browser heap, and logs separately. Do not call retention a leak unless retained fixture-new sessions/pages remain after the timeout window or stronger customer proof exists.

### Idle Dwell

Equivalent to `run_idle_dwell_profile.py`.

Hold one browser session open without interaction for the declared duration. Sample Gateway performance, Perspective sessions/pages, Perspective metric counters, browser heap, DOM nodes, long tasks, network/WebSocket bytes, and logs. Treat positive heap slope or idle counter movement as a follow-up signal, not leak proof.

### Multi-Session Scaling

Equivalent to `run_multisession_profile.py`.

Open session-count groups such as 1, 5, and 10 against the same route and readiness rule. Use clean-baseline waits between groups when necessary. Compare per-session metrics, browser timings, Gateway CPU/heap/thread counts, WebSocket bytes, and page/session counts. Mark timed-out or non-zero-baseline groups as contaminated unless the scenario intentionally includes existing sessions.

## Incident Mechanics Helpers

### Long Script / Active Freeze Fixture

Equivalent to `run_long_script_incident.py`.

Only use on dev/staging or an approved target. Import a disposable Perspective route/view with a button event that runs a bounded Gateway-side script for a configured duration and emits unique start/done markers. Browser-click the button, capture visible active-window timing and screenshot, open a second same-route browser context during the active window, immediately sample Gateway/session metrics, capture one bounded filtered thread dump, query logs for the run markers, then roll back route/view resources. Keep script duration small and bounded. Treat this as mechanics evidence unless captured on a real customer symptom.

Ignition-specific details to preserve:

- The event script must be bounded by max milliseconds and must not run arbitrary customer code.
- Visible ready/result markers must be unique to the run.
- Thread evidence must use narrow filters and redaction.
- Route/view cleanup must be verified after rollback.

### Queue Backlog Fixture

Equivalent to `run_queue_backlog_incident.py`.

Only use on dev/staging or an approved target. Import two or more disposable button-action variants with different bounded task counts and per-task sleep/work limits. The browser must prove expected/started/accepted/completed/last counters before and after repeated clicks. Profile click-to-done timing with `perspective.session-<uuid>.queue-length`, queue-task, script, property-change, message, Gateway, browser, and network evidence. Compare the larger/backlog variant to the smaller baseline.

Ignition-specific details to preserve:

- Perspective resource shape: create one disposable page route and one disposable view per task-count variant. The view should include a unique ready marker, one button, a result label bound to `view.custom.doneText`, counter labels bound to `view.custom.expectedTasks`, `handledTasks`, `startedActions`, `acceptedActions`, `completedActions`, and `lastHandledIndex`, plus a combined counter label whose text can be parsed as `expected=N started=N accepted=N completed=N last=N`.
- Ignition package shape: the import package must include the target project root, `project.json`, `com.inductiveautomation.perspective/views/<viewPath>/view.json`, the view `resource.json`, and `com.inductiveautomation.perspective/page-config/config.json` mapping the generated page path to the generated view path. Keep all generated view paths under the allowed test view prefix and all page paths under the allowed test route prefix.
- Generated view details: use Perspective component types such as `ia.container.flex`, `ia.display.label`, and `ia.input.button`; give the ready label a stable marker such as `meta.domId: "perf-ready"` and the combined counter label a stable marker such as `meta.domId: "perf-counters"`. Initialize view custom properties to `runId`, `variant`, `taskCount`, `maxTasks`, `workMillis`, `maxWorkMillis`, `expectedTasks`, `handledTasks: 0`, `startedActions: 0`, `acceptedActions: 0`, `completedActions: 0`, `lastHandledIndex: 0`, `lastError: ""`, and `doneText: "I-02 PENDING"`.
- Binding details: bind the done label's `props.text` to `view.custom.doneText` with a Perspective property binding. Bind individual status labels to their matching `view.custom` values, and bind the combined counter label with an expression equivalent to `'Fixture Counters: expected=' + toStr({view.custom.expectedTasks}) + ' started=' + toStr({view.custom.startedActions}) + ' accepted=' + toStr({view.custom.acceptedActions}) + ' completed=' + toStr({view.custom.completedActions}) + ' last=' + toStr({view.custom.lastHandledIndex})`.
- Event-script contract: attach a bounded Gateway-scope Perspective button action script (`events.component.onActionPerformed`, script `scope: "G"`). The script must clamp `expectedTasks`, `workMillis`, and `maxWorkMillis`; increment started/accepted/completed/last counters on the view custom properties; sleep only for the configured bounded work interval; and set `view.custom.doneText` to `I-02 DONE <expected>` only after the expected count completes.
- Event-script control flow: read values from `self.view.custom`, coerce invalid values to safe defaults, clamp negative counts/times to `0` or `1` as appropriate, cap `workMillis` to `maxWorkMillis`, set `doneText` to `I-02 RUNNING 0` when the first click starts, call `time.sleep(float(workMillis) / 1000.0)` only when bounded work is positive, then increment `handledTasks`, `completedActions`, and `lastHandledIndex`. The script must not import project libraries, run arbitrary customer code, create threads, call external systems, or write outside the generated view custom properties.
- Browser proof: wait for the route-specific ready marker, prove the counter label is at `started=0 accepted=0 completed=0 last=0` before clicking, repeat clicks with an explicit cadence and mode, then require both the post-click result marker and the final counter label to match the expected count. If the post-click counters are missing or mismatched, treat the run as fixture calibration only even when profile sampling and cleanup succeed.
- Selector/readiness details: use route-specific ready text or a stable component selector such as the ready marker component path. Treat `document.title` as shell evidence only. If component-path selectors are used for counters, verify the selector points to the combined counter label for the current generated view shape; the local helper used a data-component-path watch target for the combined counter label and parsed it with `expected=(\d+).*started=(\d+).*accepted=(\d+).*completed=(\d+).*last=(\d+)`.
- Readback gates: after import, require `pageValidate` to confirm the generated route resolves to the expected view, and require `viewRead` with `includeViewJson`/`includeResourceJson` to show the correct task count, max task count, work bounds, zeroed counters, ready marker, button text, combined counter label, and done marker.
- Profile proof: keep `metricsList` filters broad enough to retain per-session `queue-length`, `queue-tasks`, script, property-change, and message tokens. Sample `metricsSnapshot`, `gatewayPerformanceSnapshot`, and `perspectiveSessionsQuery` throughout the click/result window, and record whether the target session's queue-length metric is present.
- Cadence calibration: preserve the configured `clickRepeatCount`, `clickRepeatIntervalMs`, and click mode. Burst clicks with interval `0` can be useful calibration, but do not use them as accepted I-02 evidence unless the final fixture counters match and the browser result marker appears.
- Network/backpressure details: when applying browser network throttle, record whether it is applied before navigation or after the ready marker, and whether scope is all variants or only the backlog variant. A throttled target that fails final counter proof is boundary evidence, not accepted negative evidence.
- Cleanup proof: roll back generated route/view resources with dry-run/apply rollback, then verify route absence through `routesList` and view absence through `viewRead`. Keep failed or partial rollback as a stop condition unless the report is explicitly failed-boundary evidence.

I-02 proof requires all of these:

- fixture mechanics pass for at least baseline and backlog variants;
- the target/backlog variant has the queue-length metric present;
- target queue length rises above baseline and above the declared minimum;
- queue length is sustained for the declared sample count;
- queue length recovers before the final sample;
- click/result latency increases by the declared threshold;
- cleanup passes.

Queue-task, script, property-change, executor pool, or backing queue counters are supporting activity only. They are not queue-backlog proof without sustained queue-length rise/recovery. If mechanics pass but queue length stays flat, record accepted negative fixture evidence and run the strict verifier as an expected failure.

### Data-Source Delay Fixture

Equivalent to `run_datasource_delay_incident.py`.

Only use against an approved test database or read-only data source. Create fast and delayed read-only Named Query variants and same-shape polling-disabled Perspective views. Browser-prove a button-triggered `refreshBinding("props.text")` changes the query-backed label. Compare direct `namedQueryPreview` timing and browser click-to-result timing, while checking browser DOM/long tasks/heap and Gateway CPU stability. Roll back route/view/query resources. Treat as I-06 mechanics unless it uses the customer's actual approved data-source symptom.

### Memory-Growth Suspicion Fixture

Equivalent to `run_memory_growth_suspicion.py`.

Import a disposable static route/view, repeat deterministic fresh browser open/close cycles, and sample pre/during/post API evidence plus browser evidence. Subtract baseline Perspective session/page tokens introduced by the fixture. Separate JVM heap, browser JS heap, raw Perspective session/page counts, and fixture-new retained tokens. Verify route/view rollback. A short post-close window is retention timing evidence only.

## Comparison And Claim Gates

### Compare Profiles

Equivalent to `compare_profiles.py`.

Given a control bundle and a target bundle, compute deltas for ready timing, click/result timing, DOM, long tasks, browser heap, transfer/WebSocket bytes, Gateway CPU/heap/thread counts, Perspective metric family deltas/rates, session/page counts, log errors, and missing evidence. Do not infer causality from one comparison.

### Paired Profiles

Equivalent to `run_paired_profiles.py`.

Run repeated control/target or before/after pairs under the same scenario. Preserve pair order, pauses, clean-baseline checks, primary metric, safety metrics, and pairwise comparison output. Default causal policy is seven pairs, at least six improved pairs, at least 15% median primary improvement, and no material safety regression.

### Recommendation Link Verifier

Equivalent to `verify_recommendation_links.py`.

Require every recommendation to reference observed finding IDs and expected metrics. Findings that mention metric names must link to raw metric evidence. Reject generic recommendations that are not traceable to observed evidence.

### Safety Coverage Verifier

Equivalent to `verify_safety_coverage.py`.

Require declared limits and observed values for Gateway CPU, heap, browser errors, log errors, WebSocket/message volume or duplicate-message checks, duplicate writes when writes are part of the scenario, operator latency, and functional correctness. Partial safety means no acceptance wording.

### Repetition Policy Verifier

Equivalent to `verify_repetition_policy.py`.

Check repetitions, warm-up discard policy, improved-pair count, median improvement threshold, safety regression threshold, and whether the report explicitly labels local/suggestive/rejected evidence. Use local rejection only when the report refuses causal/release wording.

### Target Equivalence Verifier

Equivalent to `verify_target_equivalence.py`.

Require structured fields that show the evidence target matches the customer question: project/route/view aliases, readiness rule, browser/device/cache/session class, data shape, query/historian/tag/provider details, queue symptom window when relevant, safety and rollback scope, and customer-approved boundaries. Local fixture evidence can pass only as local/partial rejection, not customer-specific proof.

### Acceptance Case Verifier

Equivalent to `verify_acceptance_case_claims.py`.

Require an acceptance-case report with scope, primary metric, safety metrics, functional equivalence, changed resources, rollback result, repetition status, target equivalence, evidence paths, and explicit release-ready or partial status. Reject release-ready wording when any required evidence is missing or local-only.

### Queue Backlog Claim Verifier

Equivalent to `verify_queue_backlog_claims.py`.

Read one or more queue fixture summaries. Positive proof requires strict I-02 conditions. Accepted negative evidence requires `mechanicsOk`, queue-length metric presence, cleanup, supporting activity, flat zero or non-rising queue length, and explicit rejection of local queue-backlog proof. Emit the exact failed strict checks so the report cannot confuse negative evidence with proof.

### Cache & Share Claim Verifier

Equivalent to `verify_cache_share_claims.py`.

For query or tag-history Cache & Share evidence, require static config readback plus runtime sensitive metric evidence. Positive consolidation needs database, historian, or equivalent query-activity counters to fall by the declared meaningful threshold across the tested shape and repetitions. If the selected metric is insensitive or deltas are flat/noisy, reject the local claim instead of recommending Cache & Share.

### Tag Binding Claim Verifier

Equivalent to `verify_tag_binding_claims.py`.

Separate local binding-shape mechanics from target-provider behavior. Local direct/indirect/reference tag binding evidence can prove browser-visible tag flow and static binding shape. Claims about remote/reference provider latency need target-specific provider quality/timestamp/update-latency or fetch/message proof.

### Runner API Workflow Verifier

Equivalent to `verify_runner_api_workflow.py`.

When a claim depends on a new or changed runner action, require design notes, implementation evidence, live self-update evidence, runner version/stack version, health after update, contract tests, docs/capability updates, and evidence that downstream skill/runbook names use the shipped action. Design-only notes cannot support proof.

## Disposable Fixture Helpers

All disposable fixture helpers follow the write-helper contract. The Ignition-specific details below are the details a recreated helper must preserve.

### Table Virtualization A/B

Equivalent to `run_table_ab_remediation.py` and `run_table_ab_repeated.py`.

Create a same-data Perspective Table before/after pair that changes only `props.virtualized`. Preserve row/column data hashes, column config hashes, visible ready markers, browser/Gateway evidence, comparison output, and rollback. Repeated wrapper runs fresh disposable pairs and enforces the causal comparison rule.

Ignition-specific details to preserve:

- Build a disposable Ignition project resource package, not an ad hoc JSON blob. Include `project.json`, a Perspective view resource under `com.inductiveautomation.perspective/views/<view path>/view.json`, the matching `resource.json`, and page config under `com.inductiveautomation.perspective/page-config/config.json` mapping the generated route to the generated view path.
- The view should use standard Perspective component resource JSON: a root `ia.container.flex`, visible `ia.display.label` ready and functional-equivalence markers, and one `ia.display.table`. Keep generated table `props.data`, `props.columns`, `selection`, style, row count, column count, data hash, and column hash identical between the before and after variants. Change only `props.virtualized`.
- Import the before package with the runner's project import action using an allowlisted route prefix and view prefix. Capture the returned backup name, read the generated view with `viewRead`, record the returned `viewSha256`, and validate the route with `pageValidate` against the expected route, view path, and current hash.
- Profile the before route through the Perspective client URL for the target project and generated route. Browser readiness must wait for the variant-specific ready marker rendered by the view, not only the Perspective shell.
- Import the after package with a current-hash drift guard based on the before `viewSha256`, then repeat `viewRead`, `pageValidate`, and route profiling. If the drift guard fails, stop before interpreting performance evidence.
- Compare the before/after bundles with the same browser class, viewport, wait-after-ready time, profile duration, metric filters, and sample cadence. Report browser metrics, Gateway metrics, Perspective session bytes, focused logs, and console/network evidence separately.
- Prove functional equivalence by checking the before and after data hashes and column hashes. The helper may show the first and last generated row in the view, but the hash readback is the durable proof.
- Roll back in two stages when the target changed: first restore the after backup to return to the before hash, then restore/remove the before backup to clean up the generated route and view. Verify rollback through `viewRead`, `routesList`, and route/view absence or expected failure before marking cleanup passed.
- For repeated runs, create fresh route/view names for each repetition, preserve each child run's summary and comparison output, wait for a clean browser-session baseline when configured, and evaluate causal wording only after repetitions, functional equivalence, drift guards, rollback, and safety coverage all pass.

### Table Row/Column Scaling

Equivalent to `run_table_scaling.py`.

Create a matrix of table row and column counts. Keep generated data deterministic and comparable. Measure static JSON bytes, browser ready time, DOM, heap, long tasks, transfer/WebSocket bytes, Gateway/session metrics, and compare each size to the smallest baseline.

Ignition-specific details to preserve:

- For each row/column size, create a separate disposable Perspective view and route from an Ignition project resource package. Use the same project export shape as the table A/B helper: Perspective `views/<view path>/view.json`, `resource.json`, and `page-config/config.json`.
- Generate deterministic table rows and columns at the requested size, store row count, column count, cell count, `props.virtualized`, data hash, column hash, and static view JSON byte counts in the artifact for that variant.
- Keep the view shape fixed across variants: the same flex root, ready marker label, scenario-summary label, and one `ia.display.table`. Change only row count, column count, generated data, generated columns, and the optional table `props.virtualized` setting.
- Import each variant with the runner project import action under allowlisted route/view prefixes. Capture backup names, then verify with `viewRead` and `pageValidate` that the generated route points to the expected view and the readback view hash matches the generated package.
- Browser readiness must use a variant-specific marker containing the run id and size label, so a stale route or wrong size cannot pass.
- Profile each variant with identical browser class, viewport, wait-after-ready time, profile duration, sample cadence, metric filters, and clean-baseline policy. Preserve browser summary, network/WebSocket summary, Gateway metric samples, Perspective session samples, and focused logs.
- Compare each larger size to the smallest baseline and report static payload, DOM, long-task, LCP/ready-time, heap, transfer, WebSocket, and Gateway/session deltas independently. Treat the run as scaling characterization; do not turn one synthetic size matrix into a universal table limit.
- Roll back every generated route and view by backup name, then verify route absence with `routesList` and view absence or expected `viewRead` failure. A size variant is not complete unless cleanup passed or the retained artifact is explicitly marked intentional.

### Table Filter Results Writeback

Equivalent to `run_table_filter_writeback_ab.py`.

Compare identical filtered tables with `props.filter.results.enabled` false versus true. Measure static payload, property-change counters, browser/network/WebSocket evidence, and Gateway/session metrics. Do not recommend disabling writeback if downstream bindings/scripts require `props.filter.results.data` unless an equivalent design is proven.

### Embedded View Breadth

Equivalent to `run_embedded_breadth_scaling.py`.

Create a parent view with 1/10/50/100 child Embedded View instances and a deterministic child ready marker. Validate parent and child dependencies, profile each count, compare to the one-instance baseline, and roll back.

### Embedded View Depth

Equivalent to `run_embedded_depth_scaling.py`.

Create static nested chains of Embedded Views. Require a leaf ready marker so evidence proves every level rendered. Compare each depth to a one-level baseline. Do not turn one synthetic depth into a platform-wide limit.

### Embedded Loading Mode

Equivalent to `run_embedded_loading_mode.py`.

Compare `props.loading.order` values while recording both parent-first-ready and child-total-ready markers. Report perceived first render separately from child completion.

### Hidden Content

Equivalent to `run_hidden_content_ab.py`.

Compare a subtree hidden with Perspective `meta.visible: false` against the same view with that subtree removed. Record static component/binding reduction separately from browser and Gateway deltas. Repeat before causal wording.

### Expression Poll Rate

Equivalent to `run_poll_rate_scaling.py`.

Keep visible shape and binding count constant while changing only expression `now(rate)` values. Compare faster rates against the slowest baseline. Report cost against the screen's required freshness.

### Query Polling Versus Event Refresh

Equivalent to `run_refresh_binding_ab.py`.

Create a read-only Named Query and same-shape query-bound labels. Compare continuous query polling with polling disabled plus a button event that calls `refreshBinding("props.text")` on watched labels. Browser-prove the manual click changes the first watched label value. Roll back route, view, and Named Query resources.

### Query Cache & Share

Equivalent to `run_query_cache_share_ab.py`.

Create same-shape query-bound labels across concurrent sessions with Cache & Share off versus on. Verify exact Named Query and view readback. Sample database query timers or equivalent query-activity counters plus Perspective metrics. Treat static Cache & Share as a hypothesis until runtime activity drops by threshold.

Ignition-specific details to preserve:

- Discover a valid database connection first, then create two disposable read-only Query-type Named Queries under the allowed test prefix. Keep SQL text identical across cache-off and cache-on variants and record a SQL hash or exact SQL readback.
- Create two disposable Perspective views and page routes with identical visible shape, label count, polling rate, session count, viewport, launch stagger, ready marker, and sampling cadence. Change only the query binding `cacheAndShare` setting between variants.
- In each label's Perspective `propConfig`, use a query binding pointed at the generated Named Query path. Preserve the binding `type`, query path, polling settings, `cacheAndShare` boolean, and any transform/readiness text needed for the browser probe.
- Before profiling, read back the Named Query with `namedQueryRead`, preview it with `namedQueryPreview`, read back the view with `viewRead`, and validate the route/view with `pageValidate`.
- Make browser readiness route-specific and tied to the generated view, not only the Perspective shell. The local fixture used variant-specific ready text plus a query-backed secondary marker so an empty or stale binding could not silently pass.
- Collect synchronized evidence from concurrent browser sessions and Gateway metrics. Prefer database query counters such as `databases.queries` or `databases.<token>.queries`, but preserve the selected metric name and prove it is an activity counter before interpreting it.
- Compute off/on deltas from pre/during/post samples and require a declared meaningful reduction threshold. A smaller cache-on delta is not enough if it does not meet the threshold.
- Roll back generated route, view, and Named Query resources, then verify route/view/query absence by discovery or readback before treating cleanup as passed.

### Query Multiplicity Sensitivity

Equivalent to `run_query_multiplicity_sensitivity.py`.

With Cache & Share disabled, compare one query-bound property, many properties sharing one Named Query path, and many properties using distinct Named Query paths. Use this before interpreting Cache & Share if the database metric may not respond to same-path or distinct-path multiplicity.

Ignition-specific details to preserve:

- Keep `cacheAndShare: false` for every variant so the run measures metric sensitivity, not a remediation.
- Build three same-shape Perspective variants: one active query-bound label, many labels sharing one Named Query path, and many labels each pointing at a distinct generated Named Query path. Keep visible label count, route shape, polling cadence, browser sessions, and sampling cadence constant.
- For the same-path variant, read back that every tested label's `propConfig` points to the same Named Query resource. For the distinct-path variant, read back that each tested label points to a unique generated Named Query resource with the same SQL shape.
- Use `namedQueryPreview` or equivalent query execution proof before browser profiling so a missing Named Query does not masquerade as low query activity.
- Report one-bound, same-path many-binding, and distinct-path database-query deltas separately. Do not infer that same-path extra bindings are visible unless the one-bound to same-path increase exceeds the declared sensitivity threshold.
- Treat distinct-path sensitivity as a path-shape observation. It can prove the counter sees more query paths, but it does not prove same-path Cache & Share consolidation by itself.
- Roll back all generated routes, views, and Named Queries for every variant and verify cleanup.

### Query Parameter Sensitivity

Equivalent to `run_query_parameter_sensitivity.py`.

Compare identical versus distinct Value parameter values on the same Named Query path with Cache & Share off/on. Browser-prove returned parameter values. Report parameter shape separately from Cache & Share behavior.

Ignition-specific details to preserve:

- Create a read-only Query-type Named Query with a required Value parameter and read back the parameter definition before runtime profiling.
- In Perspective query binding config, serialize Value parameter literals as expression strings, not bare JSON values, when matching the tested resource shape.
- Keep the same Named Query path, label count, polling rate, session count, and browser readiness rule across same-parameter and distinct-parameter variants.
- Make browser readiness depend on a query-returned parameter value so an empty label, transform fallback, or static prefix cannot pass the test.
- Record whether the selected database query metric is sensitive to parameter shape before interpreting Cache & Share deltas.
- Roll back route, view, and Named Query resources and verify absence through discovery or readback.

### Tag-History Cache & Share

Equivalent to `run_tag_history_cache_share_ab.py`.

Create bounded history-enabled expression tags under a controlled test prefix. Prove current values with `tagRead` and historian rows with `historyProbe` good-sample evidence when available. Compare same-shape tag-history labels across sessions with Cache & Share off/on. Roll back route/view resources and do not claim automatic tag cleanup unless the target API exposes tag deletion and it was verified.

Ignition-specific details to preserve:

- Discovery: call `health` first and require the needed actions, then discover a writable tag provider, the selected history provider or database connection, and the target Perspective project. Record runner version, stack version, supported actions, selected project, selected tag provider, and selected history provider without exposing raw endpoint or token values.
- Tag fixture setup: create expression tags under an allowlisted provider path with `tagConfigure` dry-run and confirmed apply. Enable history on each generated tag using the selected history provider, deterministic names, bounded scan/update behavior, and run-specific expression values. Use `tagRead` after apply and require Good quality, current timestamps, and expected values before using the tags in a Perspective view.
- History proof: wait for historian samples with `historyProbe` before profiling. Preserve `aggregationMode`, range minutes, return size, return format, query status, row count, good stored sample count, per-tag `tagStats`, first/last timestamps, and sample-backed availability. Treat missing or bad history rows as fixture calibration only, even when current `tagRead` values are Good.
- Perspective binding JSON: create one disposable view and route per variant. Bind visible labels through component-level `propConfig` tag-history bindings that use the exact generated tag paths, the same history range, aggregation, return size, polling rate, and only one changed field: `binding.config.cacheAndShare` false versus true. Read back the generated view with `viewRead` and fail if the `cacheAndShare` value, tag paths, history settings, binding count, or variant identity do not match.
- Route/view proof: validate the route with `pageValidate`, then require browser readiness tied to route-specific tag-history label text, such as a rows/count marker returned from the history binding. Static shell readiness or `document.title` alone is not enough because it does not prove historian rows rendered.
- Profile proof: open the same number of browser sessions for each variant, with identical viewport, launch stagger, polling rate, sample cadence, clean-baseline policy, and metric filters. Capture browser summaries, console/network evidence, Gateway performance, Perspective session samples, and selected database/historian activity counters.
- Metric interpretation: prefer database or historian query-activity counters such as `databases.queries` when the target exposes them, but preserve the selected metric token and prove it changes for the tested workload before interpreting Cache & Share. Compute off/on deltas from pre/during/post samples and require a declared meaningful reduction threshold; below-threshold reductions are rejected local evidence, not recommendations.
- Cleanup boundary: roll back generated route/view resources and verify absence through `routesList`, `viewsList`, `viewRead`, or `pageValidate` failure/readback. If no tag deletion action exists, leave the generated tags only under the bounded test prefix and record `tagCleanupAvailable: false` plus the persisted tag path.
- Translation boundary: if recreating this helper in Gateway-side Jython, name the `system.tag.configure`, `system.tag.readBlocking`, `system.tag.queryTagHistory`, Perspective resource/package, and route/page-config calls next to the code that uses them. Preserve the same dry-run/apply/readback, browser-proof, metric, and cleanup gates; do not hide these Ignition dependencies behind a generic "create tags" or "profile route" comment.

### Tag Binding Mode

Equivalent to `run_tag_binding_mode_ab.py`.

Create bounded source tags, indirect-binding parameters, and reference tags. Compare direct local tag bindings, indirect tag paths through view parameters, and direct bindings to reference tags backed by source tags. Browser-prove initial and updated values, profile sessions, and roll back route/view resources. Keep provider behavior separate from UI binding shape.

Ignition-specific details to preserve:

- Tag fixture setup: use `tagConfigure` dry-run and apply under an allowlisted provider path for source memory tags with `tagType: AtomicTag`, `valueSource: memory`, `dataType: String`, and run-specific string values. Verify configured values with `tagRead` and require Good quality before using the fixture.
- Reference-tag setup: for the reference variant, configure source memory tags first, then configure display tags with `valueSource: reference` and `sourceTagPath` pointing at the source tags. Read back both source and reference/display tag values; do not treat a reference tag's Perspective binding shape as provider-latency proof.
- Perspective binding JSON: create one label per tag and bind `props.text` through component-level `propConfig`. Direct and reference variants use `binding.type: tag` with `binding.config.tagPath` set to the explicit display tag path. Indirect variants use `binding.config.mode: indirect`, `binding.config.tagPath: "{base}/ValueNNN"`, and `binding.config.references.base: "{view.params.baseTagPath}"`.
- View parameter contract: for indirect variants, set view `params.baseTagPath` to the source tag folder and mark `propConfig["params.baseTagPath"].paramDirection` as `input`. Read back the view and fail if the indirect mode, reference token, or parameter declaration is missing.
- Route/view proof: import one disposable view and page route per variant, then require `pageValidate.routeMatchesExpectedView`, `viewRead` static binding counts, and a browser-visible run-specific ready marker before profiling.
- Update proof: after initial browser readiness, update the first source memory tag with `tagConfigure`; require `tagRead` to show the updated value and require the browser to show the updated text. For reference tags, read both the source tag and the reference/display tag after the update.
- Profile proof: profile each variant with the same session count, browser ready text, sampling cadence, Perspective/tag metric filters, and clean-baseline policy. Record per-variant browser ready counts, update-visible timing, session samples, metric tokens, console errors, network/WebSocket summary, and route/view hashes.
- Cleanup boundary: roll back the generated route/view resources and verify them absent through discovery/readback. If the active API lacks tag deletion, leave the bounded tag fixture under the allowed test prefix and record `tagCleanupAvailable: false` or equivalent bounded-persistence language.
- Claim boundary: local direct, indirect, and reference mechanics prove UI binding shape and browser-visible tag flow only. Remote/reference-provider recommendations require target-specific provider quality, timestamps, update-latency, or fetch/message evidence.

### Tab Container Run While Hidden

Equivalent to `run_tab_runwhilehidden_ab.py`.

Compare `runWhileHidden: false` versus `true` while activating a work tab, returning to a control tab, and sampling during the background hold. For tabs whose content comes from child views, use `props.tabs[].viewPath`; do not serialize both `text` and `viewPath` on the same tab object because the label text can mask the child view path behavior.

### Carousel Rotation

Equivalent to `run_carousel_rotation.py`.

Compare `props.lazyLoad: false` versus `true` for the same child views. Advance `props.activePane` through a bounded button event, browser-prove pane/slide-label changes, and fail on console errors or component-registry render warnings. Confirm Carousel resource shape from official docs, Designer seeds, or source-view readback before generating fixtures.

### Parameter Payload

Equivalent to `run_parameter_payload_ab.py`.

Compare same-visible-shape scalar child-view parameters against deep object/array parameters. Preserve carrier type: Embedded View `props.params`, Flex Repeater `props.instances[]`, or View Canvas `props.instances[].viewParams`. Report static parameter bytes, transfer/WebSocket bytes, browser heap, and readiness separately.

### Chart Scaling

Equivalent to `run_chart_scaling.py`.

For Time Series Chart, XY Chart, or Gauge fixtures, vary count, series/axis/range count, and static point rows while keeping other shape elements constant. For XY Chart, measure `props.dataSources` rows when using static data. Do not infer historian/query/provider cost unless bindings or data-source calls are present and measured.

Ignition-specific details to preserve:

- Build one disposable Perspective view and page route per chart-size variant from an Ignition project resource package. The package must include the target project root, `project.json`, `com.inductiveautomation.perspective/views/<viewPath>/view.json`, the view `resource.json`, and `com.inductiveautomation.perspective/page-config/config.json` mapping the generated page path to the generated view path.
- Keep generated route paths and view paths under explicit allowlisted test prefixes. Use `dryRun` before `apply`; on apply, capture the returned backup name so the same helper can roll back the route and view even if profiling fails.
- Use the expected Perspective component family explicitly: Time Series Chart uses `ia.chart.timeseries` with static `props.series`, XY Chart uses `ia.chart.xy` with static `props.dataSources`, `props.series`, `props.xAxes`, and `props.yAxes`, and Gauge uses `ia.chart.gauge` with static axis and range props. Do not substitute a Designer-only component or Power Chart shape unless it is read from a seed view and profiled as a clone.
- Keep the surrounding view shape fixed across variants: the same flex root, run-specific ready label, scenario summary label, and chart grid container. Change only chart count, series or axis count, point or range count, and the static chart payload for the selected chart family.
- Record variant metadata in the view and artifacts: `chartKind`, chart count, series/axis count, points/ranges per series, total plotted points or ranges, static payload hash, view JSON hash, package ZIP hash, route, view path, and run-specific ready text.
- After import, call `viewRead` and verify the readback contains the expected component type, `chartKind`, payload hash, and ready text. Then call `pageValidate` and require the generated route to match the generated view path before opening the browser.
- Browser readiness must use the route-specific ready text for that variant, not only the Perspective shell or `document.title`. Preserve browser summary, console, network/WebSocket, DOM node count, JS heap, long-task, and transfer evidence for each variant.
- Profile each variant with the same browser class, viewport, wait-after-ready time, profile duration, sample cadence, metric filters, and clean-baseline policy. Compare each larger variant to the smallest baseline, but report static payload, DOM, long-task, ready-time, heap, transfer, WebSocket, Gateway, and session deltas as separate signals.
- Roll back every generated route and view by backup name, then verify route absence with `routesList` and view absence or expected `viewRead` failure. A chart variant is not complete unless cleanup passed or the retained resource is explicitly labeled intentional.
- Treat this helper as chart rendering and static payload characterization only. It does not prove historian, query, tag, or provider cost unless the profiled chart/view actually includes those bindings or data-source calls and the helper captures the matching runtime counters.

### Seed View Clone Profile

Equivalent to `run_seed_view_clone_profile.py`.

Read an existing allowed source view, clone it under a disposable target prefix, inject a run-specific ready marker, add a temporary route, profile the clone, then roll back. Use this when Designer-created components such as Power Chart or trends are hard to serialize safely. Do not infer historian/query/provider cost unless the cloned source view actually exercises those bindings.

### Property-Change Storm

Equivalent to `run_property_change_chain.py`.

Create a bounded button-triggered custom-property write storm. Profile Perspective property-change, script, queue-task, message, browser, network, and Gateway/session evidence. This proves controlled storm mechanics only; a real component `propertyChange` loop needs a proven Designer/runtime event shape.

### Transform Cost

Equivalent to `run_transform_cost_ab.py`.

Compare same-visible-shape Document/custom-property, expression-only, and property-binding script-transform variants. Measure static script count, Perspective expression/script/property/queue metrics, browser timing, DOM, heap, network/WebSocket evidence, and visible output equivalence before recommending a transform move, removal, or rewrite.
