# Expression API Validation

Use this reference before validating or mutating expression fixtures through the Ignition Web Dev runner. Keep credentials, private hosts, project names, providers, and run-specific evidence outside the reusable skill.

## Contents

- [Original Trigger Coverage](#original-trigger-coverage)
- [Runtime Requirements](#runtime-requirements)
- [Transport And Authentication](#transport-and-authentication)
- [Capability Discovery](#capability-discovery)
- [Relevant Version Gates](#relevant-version-gates)
- [Safe Validation Sequence](#safe-validation-sequence)
- [Mutation And Cleanup Guardrails](#mutation-and-cleanup-guardrails)
- [No-API Fallback](#no-api-fallback)

## Original Trigger Coverage

The shorter cross-platform frontmatter description preserves this original trigger statement here verbatim:

> Write, review, debug, and test Ignition 8.1 expression language for Expression Tags, Perspective and Vision expression bindings, expression transforms, UDT expression members, dynamic tag paths, quality checks, date/string/math logic, and runScript usage. Use when the work involves converting Python/Jython/SQL assumptions into Ignition expressions, diagnosing expression tag value or quality behavior, or validating expressions against a Gateway API.

## Runtime Requirements

- A reachable Ignition 8.1 Gateway with the supported Web Dev runner installed.
- The automation project and Web Dev resource names supplied through runtime configuration.
- A valid runner token supplied through a protected runtime setting, never embedded in the skill or evidence.
- A discovered writable tag provider and a unique disposable test path when a live fixture is required.
- Explicit authorization before any write, apply, delete, or trusted `scriptEval` operation.

The current verified product contract is runner API `0.3.193`, stack `starter-2026.07.12.17`. Do not assume the installed target matches it. Discover the live runner version and capability surface before choosing actions.

## Transport And Authentication

Send JSON requests to the configured resource:

```text
POST <gatewayUrl>/system/webdev/<automationProject>/<webDevFolder>/<webDevResource>
Content-Type: application/json
X-LLM-Runner-Token: <token>
```

Some installations use a resource directly below the project and therefore omit `<webDevFolder>`. Use the installed endpoint supplied by the operator; do not guess project, folder, resource, host, or token values.

Every request must contain an explicit `action`. Add a unique `requestId` so responses and evidence can be correlated. Treat an HTTP response as transport evidence only; inspect the JSON `ok`, error code, action, request ID, and action-specific result fields.

## Capability Discovery

Start every target session with read-only discovery:

1. Call `health` and record `runnerVersion`, `stackVersion`, `supportedActions`, and feature flags.
2. Call `gatewayInfo` and record the actual Ignition version/build, timezone, and relevant module state.
3. Call `tagProviders` and select an explicit provider from the returned inventory.
4. Stop or choose the documented fallback if a required action or feature is absent. Never infer support from the skill's current version.

The live `supportedActions` and features are authoritative. A newer version number alone does not authorize an action, and an older runner may require a narrower workflow.

## Relevant Version Gates

- Runner `0.3.77+` supports the Derived Tag `tagConfigure` behavior used by derived-tag fixtures.
- Runner `0.3.111+` returns failed `tagConfigure` QualityCodes as a failed envelope instead of reporting a successful mutation.
- Runner `0.3.114+` serializes confirmed tag mutations under the Gateway-wide mutation lock. Treat `MUTATION_LOCK_BUSY` as retryable, not as write evidence.
- Runner `0.3.156+` adds guarded `tagDelete` for one nested `AtomicTag` leaf.
- Runner `0.3.157+` adds the bounded deterministic configuration snapshot used by `tagDelete` drift guards.

Use capability discovery in addition to these gates. Do not copy unrelated newer runner capabilities into an expression test.

## Safe Validation Sequence

1. Define one unique disposable base path below an explicit provider and allowed prefix.
2. Build the smallest fixture that proves the expression behavior.
3. Submit `tagConfigure` with `dryRun: true`, the exact `basePath`, narrow `allowedTagPathPrefixes`, a bounded `maxItems`, and an intentional `collisionPolicy`.
4. Review the dry-run response and stop on any unexpected path, collision, warning, or validation failure.
5. Apply only with the action's exact current confirmation fields and only after user authorization.
6. Read every tested tag with `tagRead`; validate both value and quality and correlate the response with `requestId`.
7. Change only the bounded input values needed for the test. Prefer a dedicated narrow write action when the live runner exposes one.
8. Re-read after each mutation and preserve raw request/response evidence outside the customer package.
9. Clean up only resources created under the exact unique base path, then verify absence.

Dry-run is planning evidence, not proof that a write occurred. An apply response is not enough by itself; use readback or verified absence.

## Mutation And Cleanup Guardrails

- Never use broad arbitrary `scriptEval` for routine expression work. It is trusted administrative code execution.
- Use confirmed `scriptEval` only when the required narrow write or cleanup action is unavailable, the script is bounded to the unique test path, and the operator explicitly authorizes it.
- Do not place secrets, private endpoint details, or target-specific names in reusable requests.
- Do not reuse a disposable path from an earlier run.
- Do not delete a provider root, top-level tag, folder, UDT, or node with children through `tagDelete`.
- `tagDelete` is a leaf cleanup action only: it accepts one fully qualified nested `AtomicTag` below an allowed prefix. Apply requires the dry-run configuration hash, `confirmTagDelete: "DELETE_TAG"`, and verified absence.
- Runner `0.3.157+` reports the bounded snapshot algorithm and node count. Treat configuration drift or snapshot failure as a stop condition.
- Because `tagDelete` cannot remove a populated fixture folder as a unit, plan cleanup during fixture design: delete eligible leaves individually or use a separately authorized bounded cleanup method.
- Record recovery status whenever a mutation partially succeeds or cleanup cannot be verified.

## No-API Fallback

When the runner is unreachable, unauthorized, or missing required capabilities:

1. Perform static review with `SKILL.md` and `references/expression-test-matrix.md`.
2. Give the operator a bounded Designer/Gateway test procedure using a unique disposable path.
3. Require value and quality readback on the actual expression surface.
4. Label the behavior as unverified until target-local evidence exists.
5. Do not invent API results, runner capabilities, provider names, or cleanup status.
