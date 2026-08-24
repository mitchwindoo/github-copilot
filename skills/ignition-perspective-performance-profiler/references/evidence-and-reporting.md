# Evidence and Reporting

## Evidence Bundle

For a full profile, create an evidence folder with:

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

Use `thread-excerpts.json` only when thread evidence is triggered. Use `comparison.json` only for A/B or before/after runs. In `manifest.json`, record missing evidence explicitly and explain why it was unavailable.

Before sharing a report, run `scripts/verify_evidence_bundle.py <bundle> --out-dir <integrity-output>`. Treat failures as a stop condition until evidence hashes, JSON/NDJSON parseability, explicit missing-evidence entries, and report boundary labels are fixed. Warnings may still be acceptable when they describe legacy metadata, but the final report must keep observed evidence, interpretation, causal proof, and unproven limits visibly separated.

Keep generated evidence paths concise when practical. On Windows, use the bundled verifier outputs rather than manual recursive shell listings to prove completeness for long generated readiness paths.

Before calling the skill release-ready against the gateway test plan, run `scripts/audit_guide_coverage.py --require-release-ready --out-dir <coverage-output>`. Treat a nonzero exit as a stop condition and keep remaining partial, open, or documented-missing items out of release-ready wording.

Evidence grades:

- **Observed:** direct static, Gateway, session, browser, log, or thread evidence.
- **Correlated:** two or more synchronized signals changed during the same symptom window.
- **Causal:** a controlled A/B change altered the primary metric repeatably without material safety regression.
- **Unproven:** plausible finding without repeatable runtime effect.

Default causal comparison rule when practical:

- Run at least seven paired observations per variant.
- Discard one warm-up run for warm behavior.
- Require at least six of seven paired runs to improve.
- Require at least 15% median improvement in the declared primary metric.
- Reject the causal claim if a declared safety metric regresses by more than 10%.
- Label smaller or high-variance improvements as suggestive.
- Use `scripts/verify_repetition_policy.py` to enforce this policy before causal, recommendation, acceptance, or release-ready wording.
- Use `scripts/verify_target_equivalence.py` before customer-specific recommendation, acceptance, remediation, or release-ready wording.


## Static Findings To Look For

- Many components, high nesting depth, repeated containers, or very large view JSON.
- Embedded View, Flex Repeater, View Canvas, tab, carousel, or parameter-driven child view expansion.
- Query, tag, history, expression, property, script, or indirect bindings with polling or duplicated work.
- Query/history bindings that could use Cache & Share, and variants where Cache & Share is already enabled but runtime evidence does not consolidate work.
- Table, chart, gauge, trend, SVG/image, or custom-property payloads with large row/point/axis/range/byte counts.
- Script transforms, property-change scripts, event scripts, loops, blocking calls, repeated tag/DB/network calls, or JSON encode/decode churn.
- Hidden or retained content that may continue work while not visible.

Report these as candidate risks. Pair each candidate with the runtime evidence needed to confirm or reject it.

## Report Shape

Return:

- Symptom, scope, scenario, and evidence grade.
- Baseline static and runtime evidence.
- Findings grouped by likely Gateway, browser, network/payload, data-source, or lifecycle cause.
- What was directly observed, what is inferred, what is causally proven, and what remains unproven.
- Recommendations ordered by expected impact, reversibility, and operator risk.
- Exact resources changed, before/after primary and safety metrics, functional-equivalence checks, and rollback status when a remediation was applied.
- Acceptance-case status only after the structured acceptance gate passes, with local/dev fixture mechanics labeled as partial when customer-equivalent staging evidence is still missing.
