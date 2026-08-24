---
name: ignition-vision
description: Build, edit, inspect, validate, launch, and troubleshoot Ignition Vision 8.1 windows, templates, project resources, clients, and diagnostics through an approved runner API.
---

# Ignition Vision

Skill version: `1.0.54`

Use the runner API as the primary control and diagnostic plane for Ignition Vision. Discover the live Gateway before planning or changing a project. Do not assume project names, providers, tag paths, databases, resources, roles, sessions, or capabilities.

This skill owns Gateway/project operations, the runner API, resource lifecycle, client launch, screenshots, imports/exports, and external validation. Hand code that executes inside Ignition Vision to the separately installed `ignition-vision-jython` skill. Exchange explicit contracts such as the exact handler name, payload schema, component path, mailbox path, side-effect budget, and response schema; do not copy the Jython implementation into this skill.

## Contents

- [Compatibility](#compatibility)
- [Standard workflow](#standard-workflow)
- [Evidence boundaries](#evidence-boundaries)
- [Resource and change safety](#resource-and-change-safety)
- [Fixed client handoff](#fixed-client-handoff)
- [Shipped helpers](#shipped-helpers)
- [Completion gate](#completion-gate)
- [References](#references)

## Compatibility

- Minimum supported runner/API version: `0.3.187`.
- Recommended runner/API version: `0.3.221`.
- Target platform: Ignition Vision `8.1.x`.

Always call `health` first and trust its live `runnerVersion`, `supportedActions`, and `features` over copied documentation. Require the action and feature flag needed for the operation. If either is unavailable, use the safe fallback in the table below or stop and request a runner upgrade; never imitate a missing fixed action with arbitrary script execution.

| Operation | Required live capability | Safe fallback |
|---|---|---|
| Validate a resource name | `projectResourceNameValidate` and `projectResourceNameValidation` | Do not import, rename, or relocate until the installed Gateway can validate every segment. |
| Inspect a window | `visionWindowInspect`, `visionWindowStructuralInspection`, `visionWindowHierarchyInspection` | Use bounded resource read/export and make no hierarchy or render claim. |
| Check expression-binding initialization | `visionWindowInspect` and `visionExpressionBindingInitialValueInspection` | Export the exact resource and inspect adapter plus nested listener initial `QualifiedValue` state with the matching Ignition runtime; do not claim Designer-safe initialization from tags, logs, or XML tokens alone. |
| Audit layout geometry | `visionWindowSpatialAudit` | Review serialized bounds plus a native client screenshot; label the result as partial. |
| Preflight dependencies | `visionWindowDependencyPreflight` and `visionWindowDependencyPreflightDiagnostics` | Resolve tags, queries, templates, and navigation targets individually; do not mutate while readiness is unknown. |
| Query client sessions | `visionClientSessionsQuery` and `visionClientSessionInventory` | Stop unless the selected client is exact or the required inventory is zero. |
| Prove a fresh client bridge is ready | One exact client session plus a successful response from the exact fixed bridge required by the workflow | Treat session presence as connection evidence only. Use a bounded readiness deadline; if the bridge does not respond, capture the timeout evidence described in `api-contract.md` and stop. |
| Capture pixels and text fit | `visionClientRuntimeQuery`, `visionClientRuntimeRootScreenshot`, `visionClientRuntimeTextFitAudit` | Do not make a pixel or text-fit claim; upgrade the runner or add and validate the missing fixed capability. |
| Read client logs | `visionClientLogQuery`, `visionClientLogClientMessageTransport`, `visionClientLogMailboxRestore` | Stop the client-log claim; a Gateway log query is not a substitute. Upgrade the runner or add and validate the fixed bridge. |
| Recover from a runner HTTP 402 trial gate | Readable Gateway trial-status shell plus an authorized IdP account with Gateway config permission | Use only the bounded shell workflow in `api-contract.md`; otherwise stop. Do not self-update the runner, retry project mutations, or treat shell HTTP 200 as runner health. |
| Probe Power Table selection and sorting | `visionClientPowerTableSelectionProbe`, `visionClientPowerTableSelectionFixedSequence`, `visionClientPowerTableSelectionViewDataMapping`, `visionClientPowerTableSelectionStructuralPreflight`, and `visionClientPowerTableSelectionDualRestoration` | Build and validate a new fixed action or stop; do not substitute arbitrary setters, reflection, or desktop control. |
| Run a fixed client query | The exact action and all action-specific structural-preflight and mailbox-restoration features | Do not use a generic script, method, property, or tag tunnel. Build and validate a new fixed action first. |

## Standard Workflow

1. Call `health` with an explicit action and stable `requestId`. Confirm token configuration, version, supported actions, and features.
2. Call `gatewayInfo`, `projectsList`, and `projectInfoRead`. Record the exact project and its live connection defaults.
3. Discover dependencies before mutation:
   - tags with `tagProviders`, bounded `tagBrowse`, and `tagRead` on fully qualified paths;
   - data with `databaseConnectionsList`, `namedQueriesList`, `namedQueryRead`, and eligible bounded `namedQueryPreview`;
   - Vision resources with `projectResourcesList`, `projectResourceRead`, `visionWindowInspect`, `visionTemplateInspect`, dependency preflight, and `projectResourceExport`;
   - clients with `visionClientSessionsQuery`.
4. Validate every proposed slash-delimited resource path through `projectResourceNameValidate`. Require `allPathsLegal:true`; an HTTP 200 with an illegal segment is a failed gate.
5. Establish a zero-write baseline: health, project/provider records, resource-state hashes, dependency quality, session count, and relevant logs.
6. Build from a Designer export, customer resource, or a target-version serializer round trip. Do not patch opaque Vision binary bytes.
7. For a write, dry-run first, review the exact file and dependency impact, apply with the documented confirmation and current-state hash, then re-read after the project scan. Reconcile a lost response before retrying.
8. Validate each claim on the correct evidence plane. Stop owned clients and restore expressly temporary mailboxes or state.

Load [api-contract.md](references/api-contract.md) for request envelopes, confirmation tokens, resource lifecycle, fixed client actions, and failure handling.

## Evidence Boundaries

- Project-resource reads and inspectors prove serialized structure, not pixels.
- Dependency preflight proves only the bounded dependencies it reports.
- When a fixed client script reads a finite tag set, require dependency preflight to return the exact fully qualified paths with Good reads. A constructed placeholder or format token reported as a tag path is not acceptable evidence; have `ignition-vision-jython` express the fixed paths as explicit literals, then repeat preflight. Treat a genuinely dynamic path set as an explicit evidence limitation and add bounded `tagRead`, fresh-client, and client-log proof without claiming complete static discovery.
- A fixed client action proves only its allowlisted observation or action in the selected client.
- Gateway logs and Vision Client logs come from different JVMs.
- A registered Vision Client session proves a connection, not that the Vision application, Project Client Event Scripts, or a particular fixed diagnostic bridge has finished starting. Record session readiness and bridge readiness separately.
- For an API-owned native-client launch, inspect focused client logs and captured process stdout/stderr when available. A rendered screenshot or connected session does not cancel an `ActionAdapter`/Jython exception reported during startup or refresh.
- A native client screenshot proves pixels at one moment, not tag quality, event execution, persistence, or future responsiveness.
- Import success does not prove a working screen. Require structure, dependencies, runtime state, focused logs, and pixels when the claim is visual.
- For a Template Repeater, prove that every dataset column type agrees with the public template parameter, binding adapter value, and destination JavaBean setter. A valid dataset schema and clean screenshot do not rule out an instance-creation binding error; inspect the Vision Client log after opening the repeated template.
- Designer Design Mode is not runtime proof. Direct bindings can display changing tag values there while PMITimer/component-event Jython and its derived bars, markers, or statistics remain at serialized defaults. Use a fresh Vision Client for runtime claims.
- A transient history/query failure must not be rendered as a valid zero distribution. Preserve the last known-good or explicitly labelled design snapshot, expose a stale/failure status, and prove recovery in a fresh client.

Load [gateway-and-vision-diagnostics.md](references/gateway-and-vision-diagnostics.md) when diagnosing startup, stale resources, client exits, layout, logs, or a screen that does not move.

## Resource And Change Safety

- Preserve `resource.json`, module scope, declared file lists, and opaque payload bytes unless a target-version serializer owns the change.
- Treat window, template, client-tag, and client-event resources as different serialization domains.
- Keep one intended startup window unless the project explicitly requires more. Do not use startup stacking as a gallery mechanism.
- Keep each accepted, error-free review example as a separate window in the project's designated gallery path with `resource.json` attribute `open-on-start=false`. Do not delete accepted examples after testing merely to clean up the project.
- The runner cannot refresh or reconcile an already-open Designer's local project state. Treat affected Designer tabs as outside the API proof plane: do not use or save them during API-managed mutations. Re-read the Gateway resource-state hash and complete startup set, then validate the changed resource in a newly launched Vision Client. Stop if completion depends on reconciling unsaved Designer-local work.
- Keep every dependency required by a retained working screen.
- Reject stale state hashes, conflicting destinations, ambiguous clients, truncated evidence, bad quality, partial restore, and project-scan failures.
- Never persist credentials, authorization headers, cookies, identity tokens, or package/script payloads in logs or evidence.
- Prefer fully qualified tag paths in portable resources. Treat project default providers as live configuration.
- Use `scriptEval` only for a bounded read-only diagnostic when no first-class action exists. Do not use it as a general automation or write surface.

Load [vision-resource-model.md](references/vision-resource-model.md#small-in-place-window-changes) before changing an existing Vision component property or binding in place.

Load [vision-resource-model.md](references/vision-resource-model.md) before assembling or moving resources, and [component-patterns.md](references/component-patterns.md) before reviewing layout, bindings, navigation, templates, or complex engineering screens.

## Fixed Client Handoff

When an operation requires Vision-only code:

1. Define one exact project, handler, client-selection rule, resource identity, window/component path, request kind, response tag, expiry, and bounded response schema.
2. Define the permitted UI call and explicit zero-or-bounded side effects.
3. Have `ignition-vision-jython` implement and validate the fixed handler for Jython 2.7 and Swing threading.
4. Install the handler through the guarded project-resource lifecycle.
5. Start a fresh authenticated client only after the resource is present.
6. Dispatch through the matching first-class runner action and require a correlated typed response plus mailbox restoration.
7. Verify state independently and keep the handler/mailbox only when they are declared dependencies of a retained customer resource.

Do not create a relative filesystem dependency between the two skills.

## Shipped Helpers

- `scripts/runner_client.py`: Python 3 HTTP client library for authenticated runner calls with request/response evidence and secret redaction. Set `IGNITION_RUNNER_URL`, `IGNITION_RUNNER_TOKEN`, and optionally `IGNITION_TARGET_PROJECT` and `IGNITION_RUNNER_OUTPUT_DIR`.
- `scripts/export-validation.py`: Python 3 read-only Vision resource inventory and export-readiness manifest. It depends only on the shipped `runner_client.py`; it does not import or change project resources.
- `scripts/vision-client-runtime-launch.py`: Jython launcher bridge for classic-auth Vision Clients. Run it with the target Ignition Java/Jython/client classpath. Supply `IGNITION_VISION_USERNAME` and `IGNITION_VISION_PASSWORD` only in the process environment; optionally set `IGNITION_VISION_DIAGNOSTIC_FILE`. Never place credentials on the command line or in saved configuration.

Use the launch helper only when the installed target runtime is available and its external Ignition jars match the Gateway version. The skill does not bundle proprietary Ignition runtime files.

This customer package intentionally does not ship trial-reset or recovery executables. For an authorized HTTP 402 trial gate, follow the bounded Gateway-shell workflow in [api-contract.md](references/api-contract.md); if its exact preconditions are unavailable, stop. Re-establish runner health before resuming.

## Completion Gate

Before calling work complete, require:

- live health and capability gates;
- legal resource names and exact project/resource identities;
- deterministic local artifacts where generation is involved;
- dry-run, state-guarded apply, scan completion, and readback for every write;
- complete non-truncated structural and dependency evidence;
- runtime/client evidence for runtime claims;
- a native screenshot and text-fit review for visual claims;
- focused Gateway and client log checks;
- separate connected-session and fixed-bridge readiness evidence for every fresh-client workflow;
- verified restoration of temporary state and zero unintended clients;
- a dependency list for every retained screen.

## References

- [api-contract.md](references/api-contract.md): runner requests, capability gates, confirmations, and failure handling.
- [component-patterns.md](references/component-patterns.md): Vision layout, bindings, navigation, reusable templates, and screen composition.
- [gateway-and-vision-diagnostics.md](references/gateway-and-vision-diagnostics.md): API-first Gateway, project, client, log, runtime, and visual diagnostics.
- [version-8.1.53.md](references/version-8.1.53.md): actionable Ignition 8.1.53 compatibility cautions.
- [vision-resource-model.md](references/vision-resource-model.md): resource shapes, metadata, serialization boundaries, startup semantics, and safe lifecycle.
