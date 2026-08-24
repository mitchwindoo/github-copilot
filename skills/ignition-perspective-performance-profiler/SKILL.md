---
name: ignition-perspective-performance-profiler
description: Profile Ignition 8.1 Perspective performance using static analysis, synchronized Gateway/browser evidence, controlled A/B tests, and evidence-backed remediation.
---

# Ignition Perspective Performance Profiler

Skill version: `1.0.182`

## Purpose

Profile and triage slow Ignition 8.1 Perspective views, routes, sessions, projects, interactions, and Designer workflows. Separate Gateway, browser, network/payload, data-source, and lifecycle causes using synchronized evidence. Produce an evidence-backed remediation plan and prove or reject changes with bounded before/after measurements.

Do not use this skill as a generic page builder, SQL authoring skill, Jython authoring skill, or log-triage-only workflow.

## Core Safety Rules

- Begin read-only. Discover the live runner capabilities, project, route, view, session conditions, and current resource hashes before considering changes.
- Treat static findings as hypotheses. Do not name a root cause without synchronized runtime evidence or repeated controlled A/B evidence.
- Require explicit approval before production thread dumps, multi-session/load tests, prolonged sampling, fixtures, or any Gateway write.
- Use one bounded change per remediation cycle. Require dry-run, drift guards, exact readback, functional-equivalence checks, and verified rollback.
- Keep credentials, endpoints, hostnames, customer identifiers, raw session identifiers, unredacted thread data, and full browser/user-agent details out of reusable output.
- Record missing evidence explicitly. Never replace unavailable browser, Gateway, metric, session, log, or thread evidence with assumptions.

Read [Safety and Scope](safety-and-scope.md) before live work, load testing, incident capture, or any controlled fixture.

## Workflow

1. Define one measurable symptom and scenario: project, route/view, user/session class, browser/device class, cache state, readiness condition, cadence, repetitions, and success metric.
2. Call runner `health`. Inspect `runnerVersion`, `stackVersion`, `supportedActions`, `features`, and token state. Read [Runner Capabilities](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-performance-profiler/references/runner-capabilities.md) before relying on live diagnostic actions.
3. Discover the actual project, route, view, and dependencies. Do not guess aliases or deployment-specific resource names.
4. Run static analysis and route ranking when appropriate. Treat the results as candidates to verify.
5. Collect one synchronized read-only profile before creating fixtures or remediation variants.
6. Correlate Gateway, Perspective session, browser, network, query/provider, log, and bounded thread evidence according to the active symptom window.
7. Use a controlled dev/staging fixture only when read-only evidence cannot answer the question and the user approved the write and load boundary.
8. Verify evidence integrity and claim gates. Report observed, correlated, causal, and unproven findings separately.
9. For remediation, compare the exact same scenario with repeated paired observations, safety metrics, functional-equivalence proof, and rollback status.

Read [Runtime Workflow](runtime-workflow.md) before executing a complete profile, incident workflow, controlled A/B test, or remediation validation.

## Bundled Scripts

The customer package includes the approved helpers used by this skill. Do not recreate a shipped helper from memory.

Before execution, read [Customer Script Catalog](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-performance-profiler/references/script-catalog.md) for each helper's purpose, dependencies, output, safety class, approval boundary, and fallback. Write generated evidence to a user-selected directory outside the installed skill folder.

Key entry points:

- `scripts/view_lint.py`: offline static view analysis.
- `scripts/rank_routes.py`: static route prioritization.
- `scripts/collect_profile.py`: first synchronized read-only evidence bundle.
- `scripts/verify_evidence_bundle.py`: bundle integrity gate.
- `scripts/compare_profiles.py` and `scripts/run_paired_profiles.py`: before/after comparison.
- `scripts/run_gateway_contract_tests.py`: read-only runner contract validation.

Browser helpers require Node.js, Playwright, and a compatible Chromium browser. Python helpers require Python 3. If a runtime is unavailable, use [Helper Script Recreation Blueprints](helper-script-blueprints.md) to preserve the same action, evidence, redaction, rollback, and decision contract; otherwise continue with the available evidence and mark the missing surface.

## References

- Read [Safety and Scope](safety-and-scope.md) for supported scenarios, production restrictions, privacy rules, and approval requirements.
- Read [Runner Capabilities](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-performance-profiler/references/runner-capabilities.md) for API versions, action semantics, fallbacks, metric/session/thread boundaries, and runner health discovery.
- Read [Runtime Workflow](runtime-workflow.md) for detailed read-only profiling, incident classification, remediation gates, and controlled fixture procedures.
- Read [Perspective Performance Profile Workflow](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-performance-profiler/references/profile-workflow.md) for scenario schemas, sampling cadence, classification rules, evidence bundle design, and report checklist.
- Read [Evidence and Reporting](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-performance-profiler/references/evidence-and-reporting.md) for bundle shape, evidence grades, causal comparison rules, static candidates, and report output.
- Read [Customer Script Catalog](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-performance-profiler/references/script-catalog.md) before executing any bundled helper.
- Read [Helper Script Recreation Blueprints](helper-script-blueprints.md) only when a shipped helper cannot run or must be adapted to a restricted environment.
- Read [Official Ignition 8.1 Documentation](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-perspective-performance-profiler/references/official-ignition-8.1-docs.md) when verifying official metrics, sessions, thread, binding, component, parameter, or SDK behavior.

## Output

Return:

- The symptom, scope, scenario, and evidence grade.
- Baseline static and synchronized runtime evidence.
- Findings grouped by likely Gateway, browser, network/payload, data-source, or lifecycle cause.
- A clear separation of observed facts, correlations, causal proof, and unproven hypotheses.
- Recommendations ordered by expected impact, reversibility, and operator risk.
- Exact changed resources, before/after primary and safety metrics, functional-equivalence checks, and rollback status when a remediation was approved.
