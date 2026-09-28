# Empirical Harness Configuration Calibration

Use this procedure to improve an agent or harness by changing its configuration, not its model. Apply it when runs can be evaluated against a stable task suite or environment with independently checkable outcomes.

## Calibration Procedure

1. **Declare the objective before tuning.** Record a verifiable pass condition, failure signals, ordered metrics and their direction, failure grouping fields (the locus), evidence locations, and a finite run/change budget. Keep the objective and task set fixed across compared versions.
2. **Establish a baseline.** Run the target harness and model on the same representative tasks. Record outcomes, metrics, relevant traces, and resource use. Serialize runs on a shared machine to avoid interference; never compare a scripted substitute as if it were the target model.
3. **Diagnose before editing.** Group failures by the declared locus, inspect evidence for the largest recurring group, then probe until the suspected mechanism is measurable or reproducible. Do not change configuration without evidence and a stated hypothesis.
4. **Change one configuration item per version.** Choose a change in a relevant channel, keep it attributable and reversible, and record the version, change, channel, evidence, run references, before/after metrics, and keep-or-revert verdict. Use the project's existing version control or tracking mechanism; do not introduce a new ledger format unless the workflow needs one.
5. **Validate with the real target.** Repeat the baseline runs with the same target harness/model and comparable conditions. Compare the declared metrics in order; keep a change only when it improves the objective, otherwise revert it. Record the evidence and decision.
6. **Stop transparently.** Stop when the target is reached, the declared budget is exhausted, or three consecutive versions are reverted. State which stopping condition applied and report remaining failures rather than implying success.

## Boundaries

- Keep task verifiers and the environment's truth independent of the configuration being tuned. If evidence points to a faulty environment or verifier, reproduce it and propose a separate code fix with a regression case for human review.
- Do not improve scores by adding hidden scripted behavior that chooses or performs the target model's decisions, weakening safety checks, or broadening authorization, approval, or credential scope.
- Preserve useful run evidence without copying secrets or unnecessary personal data into reports or tracking files.
- Use deterministic tests and scripted probes to diagnose mechanisms, but validate claimed improvements with the target model and harness.

For the source design and examples, see [SystemOneHarness's dual-loop calibration method](https://github.com/HarnessRouter/SystemOneHarness/blob/ab8e8f08b4a6268c0633a474423d556599ee06a4/docs/dual-loop.md) and [design of record](https://github.com/HarnessRouter/SystemOneHarness/blob/ab8e8f08b4a6268c0633a474423d556599ee06a4/docs/design.md).
