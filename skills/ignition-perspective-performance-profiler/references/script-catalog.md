# Customer Script Catalog

Read this catalog before executing a bundled helper. Run scripts from the installed skill's `scripts/` directory, provide deployment-specific values through arguments or environment variables, and write output to a user-selected directory outside the installed skill.

## Contents

- [Runtime Dependencies](#runtime-dependencies)
- [Safety Classes](#safety-classes)
- [Core Analysis and Profiling](#core-analysis-and-profiling)
- [Claim and Acceptance Gates](#claim-and-acceptance-gates)
- [Controlled Dev/Staging Fixtures](#controlled-devstaging-fixtures)
- [Fallbacks](#fallbacks)

## Runtime Dependencies

- Python 3 is required for `.py` helpers. The shipped Python helpers use the standard library and bundled local modules.
- Node.js and Playwright with a compatible Chromium browser are required for `.mjs` browser probes. Supply an available `node_modules` location through the documented option or `NODE_PATH` when Playwright is not globally resolvable.
- Live Gateway workflows require a reachable supported runner endpoint and token. Begin with `health`; never assume action or feature availability from a version string alone.
- Static analysis and local verification remain available when Gateway or browser access is unavailable. Mark unavailable evidence explicitly instead of inventing it.

## Safety Classes

- **Local read-only:** reads files or completed evidence and writes only local reports.
- **Gateway read-only:** calls discovery, metrics, session, log, or bounded diagnostic actions without changing Gateway resources.
- **Browser session:** opens one or more browser contexts and may create runtime session load; obtain approval for multi-session or prolonged sampling.
- **Controlled write:** creates disposable resources on an explicitly approved dev/staging target, uses dry-run/apply and drift guards, and must verify rollback.

Thread dumps, production load tests, multi-session scaling, controlled fixtures, and every Gateway write require the approval rules in [Safety and Scope](safety-and-scope.md).

## Core Analysis and Profiling

| Script | Purpose | Class and output |
|---|---|---|
| `view_lint.py` | Analyze exported or runner-returned Perspective view JSON for static performance candidates. | Local read-only; JSON/Markdown findings. |
| `profile_view_json.py` | Convenience entry point for the static view analyzer. | Local read-only; delegates to `view_lint.py`. |
| `rank_routes.py` | Rank discovered routes by static triage signals before selecting live targets. | Gateway read-only; ranked route report. |
| `collect_profile.py` | Collect synchronized static, Gateway, session, log, and optional browser evidence. | Gateway read-only plus optional browser session; evidence bundle. |
| `classify_incident_bundle.py` | Classify an existing bundle into repeatable triage hypotheses. | Local read-only; classification report. |
| `compare_profiles.py` | Compare two completed profile bundles. | Local read-only; comparison report. |
| `run_gateway_contract_tests.py` | Validate the live read-only profiler action contract and redaction/bounds behavior. | Gateway read-only; contract evidence bundle. |
| `run_minimal_control_route_profile.py` | Capture an R-01 minimal/control baseline. | Gateway read-only plus browser session; composite bundle. |
| `run_cold_warm_load_profiles.py` | Compare fresh cold observations with correctly primed warm observations. | Browser session and Gateway read-only; aggregate bundle. |
| `run_interaction_profiles.py` | Repeat a click/action scenario and report latency distribution. | Browser session and Gateway read-only; interaction bundle. |
| `run_navigation_lifecycle.py` | Repeat control-target-control navigation cycles. | Browser session and Gateway read-only; lifecycle bundle. |
| `run_lifecycle_profile.py` | Measure browser-close, session-timeout, and return-to-baseline behavior. | Browser session and Gateway read-only; lifecycle bundle. |
| `run_idle_dwell_profile.py` | Measure idle/soak behavior without interaction. | Browser session and Gateway read-only; dwell bundle. |
| `run_multisession_profile.py` | Measure approved concurrent-session scaling. | Browser sessions and Gateway read-only; scaling bundle. |
| `run_paired_profiles.py` | Orchestrate repeated control/target or before/after pairs. | Depends on selected scenario; paired bundle. |
| `verify_evidence_bundle.py` | Validate hashes, parseability, missing-evidence declarations, and report boundaries. | Local read-only unless an output directory is supplied; integrity report. |
| `browser_route_probe.mjs` | Capture route-ready timing, console, network, DOM, heap, long-task, and WebSocket evidence. | Browser session; browser evidence files. |
| `browser_navigation_cycles.mjs` | Drive repeated navigation in one Chromium context. | Browser session; per-cycle browser evidence. |

## Claim and Acceptance Gates

All gate scripts are local read-only. A failed gate is a stop condition for the wording it protects.

| Script | Protected claim |
|---|---|
| `verify_recommendation_links.py` | Recommendations link to observed findings and metric evidence. |
| `verify_safety_coverage.py` | CPU, heap, messages, errors, duplicate work, and operator latency stay within declared limits. |
| `verify_repetition_policy.py` | Repeated evidence supports causal, recommendation, acceptance, or release wording. |
| `verify_target_equivalence.py` | Local/dev mechanics are equivalent enough for customer-specific claims. |
| `verify_acceptance_case_claims.py` | An acceptance case has the required evidence and boundaries. |
| `verify_cache_share_claims.py` | Query or history Cache & Share claims have sensitive activity evidence. |
| `verify_tag_binding_claims.py` | Local binding mechanics are separated from provider-latency claims. |
| `verify_queue_backlog_claims.py` | Queue-backlog proof uses sustained queue length, recovery, and correlated delay. |
| `verify_runner_api_workflow.py` | A new or changed runner action is shipped, versioned, contract-tested, and documented. |

## Controlled Dev/Staging Fixtures

These helpers are customer-usable only on an explicitly approved dev/staging target. They may create routes, views, Named Queries, tags, or other disposable resources. Require allowlisted prefixes, current resource hashes, dry-run before apply, bounded load, readback, and verified rollback. A local fixture proves mechanics for that fixture; it does not establish a customer root cause by itself.

| Scripts | Purpose |
|---|---|
| `run_embedded_breadth_scaling.py`, `run_embedded_depth_scaling.py`, `run_embedded_loading_mode.py` | Embedded View breadth, nesting-depth, and loading-order characterization. |
| `run_hidden_content_ab.py` | Compare hidden retained content with a removed-subtree control. |
| `run_poll_rate_scaling.py`, `run_refresh_binding_ab.py` | Expression polling rate and polling-versus-event refresh comparisons. |
| `run_query_cache_share_ab.py`, `run_query_multiplicity_sensitivity.py`, `run_query_parameter_sensitivity.py` | Query Cache & Share, query-path multiplicity, and parameter-shape sensitivity. |
| `run_tag_history_cache_share_ab.py`, `run_tag_binding_mode_ab.py` | Tag-history Cache & Share and tag-binding shape/provider-boundary mechanics. |
| `run_tab_runwhilehidden_ab.py`, `run_carousel_rotation.py` | Hidden tab work and Carousel lazy-load/rotation behavior. |
| `run_parameter_payload_ab.py` | Scalar versus deep child-view parameter payloads. |
| `run_table_scaling.py`, `run_table_filter_writeback_ab.py` | Table row/column scaling and filter-results writeback cost. |
| `run_table_ab_remediation.py`, `run_table_ab_repeated.py` | Table virtualization before/after and repeated causal-policy checks. |
| `run_chart_scaling.py`, `run_seed_view_clone_profile.py` | Chart/gauge scaling and profiling of cloned Designer-proven component shapes. |
| `run_property_change_chain.py`, `run_transform_cost_ab.py` | Property-write storm mechanics and expression/script-transform alternatives. |
| `run_queue_backlog_incident.py`, `run_long_script_incident.py` | Bounded queue-backlog and long-script/active-freeze mechanics. |
| `run_datasource_delay_incident.py`, `run_memory_growth_suspicion.py` | Approved test-database delay and repeated open/close memory suspicion mechanics. |

The specialized browser dependencies are:

- `browser_carousel_cycle_probe.mjs` for Carousel pane rotation.
- `browser_long_script_probe.mjs` for bounded long-script active-window timing.
- `browser_tab_switch_probe.mjs` for tab switching and background observation.
- `browser_tag_update_probe.mjs` for browser-visible tag update proof.

## Fallbacks

- If Python is unavailable, perform the documented workflow manually and preserve the same request, evidence, redaction, and decision fields. Use [Helper Script Recreation Blueprints](helper-script-blueprints.md) as the contract.
- If Node.js or Playwright is unavailable, continue with static and Gateway evidence and mark browser evidence missing. Do not claim browser rendering causality.
- If the required runner actions or features are absent, fall back to static analysis, browser evidence, `gatewayInfo`, `logQuery`, and available discovery actions. Mark metric/session/thread evidence missing.
- Never recreate a controlled write helper casually on production. Use the guarded package/write workflow from the applicable Perspective host/import skill or stop and request approval.
