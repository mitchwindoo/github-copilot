# Runner Validation

Read this reference only when the customer has an approved Ignition API or runner. The skill remains usable without one through offline review, Designer execution, or manual Gateway validation.

## Capability Discovery

1. Call the runner health or capability-discovery operation before choosing an action.
2. Treat the returned `supportedActions` and response schema as authoritative for that live runner.
3. Do not infer support from a historical runner version alone.
4. Record the runner version and the discovered actions with the validation evidence.

If capability discovery is unavailable, do not guess endpoint or action names. Use the runner's current customer documentation or fall back to Designer/manual validation.

## Safe Execution Sequence

For runner-supported Project Library validation:

1. Submit the package or resource change in dry-run mode.
2. Inspect the exact proposed resource list and validation result.
3. Apply only after the user authorizes the mutation.
4. Treat `pageValidate` or equivalent structural validation as necessary but insufficient.
5. Execute a bounded diagnostic with `scriptEval` only when that action is advertised.
6. Import the exact packaged Project Library module inside that diagnostic before calling it.
7. Use `confirmScriptEval` only for a real diagnostic when the runner requires explicit confirmation.
8. After package apply, allow a short bounded retry because the Gateway project scan can settle after structural validation succeeds.
9. Verify the result through return values, tags, database rows, files, UI state, or focused logs.

Do not package or claim Project Gateway Event Script handlers or Perspective Session Event handlers unless the runner advertises explicit resource actions or a Designer-created fixture exists and has been validated.

## Historian And Alarm Probes

Use specialized probes only when capability discovery advertises them. `historyProbe` was validated with runner `0.3.137` and later in the original test lineage, but live capability discovery still takes precedence over that historical minimum.

Keep history and alarm queries bounded by time, path, provider, journal, and result count. A successful request does not prove that the returned dataset is semantically correct; inspect quality, timestamps, row counts, and representative values.

## Mutation Controls

- Default to read-only or dry-run.
- Require explicit user approval before apply, tag writes, configuration changes, database writes, file writes, or external-process execution.
- Validate the exact target identifiers before mutation.
- Capture the pre-change state when rollback matters.
- Read back the changed state and report partial failures.
- Never treat HTTP success alone as operational proof.

## Fallbacks

When a runner action is unavailable:

- author the script offline and perform a Jython 2.7 compatibility review
- provide exact Designer or Gateway installation steps
- provide a bounded manual test procedure
- identify the expected return value, tag quality, row, file, UI state, or log record
- state that live execution remains unverified

Do not make the customer skill depend on a private runner, a local development path, or an internal evidence store.

## Additional Customer Runtime Rules

Use these rules when validating packaged Project Library code or runner-supported event resources.

- Do not use normal Python `import` / `reload()` assumptions for Ignition Project Library scripts. Call the saved project script by its exact Project Library path. The Web Dev runner `scriptEval` diagnostic harness is an exception: explicitly `import <moduleName>` inside the eval script before calling a packaged Project Library module, then dry-run before execution and use `confirmScriptEval` only for the real diagnostic. Immediately after package apply, retry bounded import diagnostics briefly because the Gateway project scan can settle after `pageValidate` already sees the script file.
- Do not treat package dry-run, apply, or structural validation as proof that Project Library code parses or runs. Execute the script in its target context and verify result tags, return values, UI state, or focused logs.
- Do not ship or leave known-bad Project Library script resources in shared projects/packages. Treat `ScriptIndexer -- Failed to parse` as a validation failure to repair or isolate in a copied test project.
- When using the approved Web Dev runner, do not package or claim Project Gateway Event Script handlers or Perspective Session Event handlers unless `health.supportedActions` exposes explicit resource actions or a Designer-created fixture/target setup is available and validated. Keep these handlers as target-specific prerequisites or one-line delegates to Project Library code until directly tested.
