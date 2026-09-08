---
name: ignition-vision-83
description: Build, inspect, change, validate, and troubleshoot Ignition Vision 8.3.8 projects through discovered Gateway interfaces. Use for Vision resource lifecycle, OpenAPI or approved custom-API work, client launch, runtime evidence, diagnostics, import/export, or guarded project changes.
---

# Ignition Vision 8.3

Skill version: `0.2.34`

Use this skill only for an exact Ignition `8.3.8` target. Verify the live Gateway build and Vision module before performing version-sensitive work. Stop before mutation when the version, project, resource, capability, or current state is ambiguous.

This skill owns external Gateway and project discovery, supported API selection, Vision resource lifecycle, client launch, runtime observation, diagnostics, and end-to-end validation. Hand code that executes inside Vision to the separately installed `ignition-vision-jython-83` skill through an explicit contract; do not duplicate its implementation here.

## Standard Workflow

1. Discover the live Gateway, exact build, installed Vision module, target project, project inheritance, resource encoding, and available API contract.
2. Define the requested outcome, exact resource identities, dependencies, side effects, rollback path, and evidence needed for each claim.
3. Inventory and use both complementary control planes in one evidence plan: the documented live OpenAPI contract for supported operations and the validated `llmImport` API for demonstrated OpenAPI gaps. Record which plane proves each state or performs each action; using one plane never silently substitutes for checking the other.
4. When neither plane supports the operation, stop and validate the exact gap before proposing the smallest focused `llmImport` capability. Test that capability offline and live, including the mandatory error-log gate, before relying on it.
5. Capture a bounded pre-action state and diagnostic baseline.
6. For a change, use the supported dry-run or preview path when available, protect the write with current-state evidence, and apply only the reviewed operation.
7. Read the resulting state back through a supported interface. Compare logical resource paths and content, not archive-container bytes. Inspect the relevant post-action diagnostics and distinguish new faults from pre-existing noise.
8. Use a fresh Vision Client for runtime or visual claims. Capture and review every available Client error dialog/log and the correlated Gateway WARN+ window before crediting behavior. Keep structure, dependencies, runtime values, pixels, and process-specific logs as separate evidence planes.
9. Preserve user-requested review windows as durable project resources. Restore only temporary test infrastructure unless the user explicitly requests removal, and verify both the retained and removed sets. Reconcile authoritative state before retrying a timed-out or lost-response mutation.
10. Do not qualify a reusable fact from one long-lived Designer, launcher profile, Gateway generation, or Client. For restart/cache claims, compare authoritative resource hashes, fixed runtime values, screenshots, complete correlated logs, boot generation, and two independently launched Client manifests. Explain every difference; matching pixels alone are insufficient.

Load [references/environment-gate.md](references/environment-gate.md) before version-sensitive work.

Load [references/window-build-verify-loop.md](references/window-build-verify-loop.md) before creating, surgically editing, replacing, adapting, or benchmarking Vision window work.

Load [references/failure-recovery.md](references/failure-recovery.md) before injecting a fault, recovering from an interrupted operation, or deciding whether an ambiguous write may be retried.

## Mandatory Error-Log Gate

Apply this gate to every Vision discovery, build, import, save, launch, dispatch, script execution, binding evaluation, tag lifecycle, validation, cleanup, and rollback, not only to failed tests:

1. Capture a bounded pre-action diagnostic baseline on every available relevant plane.
2. Record exact action start/end times, resource identities, owned process/session IDs, and request or correlation IDs.
3. Preserve the complete action window from the owned Vision Client, launcher/controller, Designer when it is explicitly in scope, and Gateway.
4. Inspect every new WARN, ERROR, exception, stack trace, modal error dialog, rejected write, serialization problem, and resource-load/save fault.
5. Correlate and disposition every signal as expected, pre-existing, explained, or unresolved. Preserve the supporting evidence; never discard a fault because the screen or API response looked correct.
6. Withhold correctness and runtime credit when any required log plane is unavailable, incomplete, uncorrelated, or contains an unexplained related signal.
7. After a correction, use a fresh bounded run and prove the old error signature is absent. Do not infer a fix from source changes, serialization, import success, a screenshot, or HTTP success alone.

There is no "assume clean" path. A test is clean only when readback and every required diagnostic plane independently support that conclusion.

## Vision Window Boundary

Treat Vision windows as native versioned project resources. Do not invent or hand-edit opaque binary payloads. Preserve an existing native encoding or use a version-matched serializer/build capability that has already passed its own fixture, import, readback, client, and diagnostic tests.

Before live import, use a tested version-matched installed-class renderer when one is available. Render the exact candidate window at its intended design dimensions and review the complete image for clipped or ellipsized text, overlaps, containment, readable state labels, and unambiguous project/window identity. Preserve renderer stdout, stderr, and operational log output; any unexpected exception or WARN/ERROR blocks the candidate. If the window changes, rebuild and revalidate every downstream project, runtime, and API archive that embeds it. This preflight can reject a bad candidate, but it never proves live bindings, quality, Client layout, or runtime behavior; those still require a fresh Client, screenshots, readback, and the complete diagnostic gate.

When a window is created for user review, retain that exact window in the Gateway project as a named durable addition. Capture a new approved project baseline that proves all pre-existing logical entries are unchanged and identifies only the intended additions. Remove temporary message handlers, observation/result tags, and launch artifacts separately. For owned source tags, use the provider-default tag group unless the reviewed design requires an override; omit a serialized tag-group override and prove the effective values, types, qualities, and exact retained paths after cleanup.

The validated primitive covers a project with global properties, Vision login properties, and one open-on-start window. The tested component subset covers fixed-window labels plus native rectangular panels with explicit bounds and size constraints. For one native `PMILabel`, class, name, bounds, text, bold font, foreground/background colors, opacity/fill, horizontal alignment, tooltip text, and Boolean/Int4/String dynamic custom properties survived native serialization, project import/export readback, and a fresh-client lifecycle. A baseline and changed fixture differed semantically only in `text`, and fresh clients rendered the expected `PROPERTY ORACLE A` then `PROPERTY ORACLE B`. Treat tooltip persistence as structural readback evidence because hover pixels were not validated. Do not infer Designer close/reopen persistence or cross-process byte-deterministic serialization; compare decoded semantics and the retained resource's own hash.

A partially validated direct-binding increment covers one one-way numeric binding to the fully qualified read-only system tag `[System]Gateway/UptimeSeconds`, including fresh-client initial display and a later visual update matched to adjacent Good tag reads. A second comparison proves that one missing numeric source with overlays enabled renders a patterned overlay, diagonal corner, and red-X marker while retaining its sentinel value. A third test proves that one Float8 source can disappear and return while the same client remains open: the overlay appears on `Bad_NotFound` and clears after Good readback without reopening.

One bounded component-event increment validates a native `PMIButton` `actionPerformed` script stored through an 8.3.8 `ActionAdapter` in script mode. The exact script found a sibling `PMILabel`, incremented one primitive Int4 dynamic property, updated the label text, and emitted one bounded client logger call. Native serializer/deserializer readback preserved the event set, listener method, target, script, builder mode, and `invokeLater == false`. In one fresh client, a fixed EDT client message handler called `doClick()` on the fixed button: screenshots proved `CLICK COUNT: 0` to `1`, an identical request ID remained at `1`, and four additional unique request IDs reached `5`. This proves that exact adapter and handler path only. The logger call was source-verified but the detached launcher exposed no supported client-log readback plane. Designer close/reopen, Gateway restart, arbitrary components, concurrent dispatch, and other event families remain untested.

One 8.3.8 typed-matrix fixture additionally validates five one-way direct bindings with overlays enabled and fixed native component sizes:

- Boolean to `PMICheckBox.selected` with primitive `boolean`;
- Int4 to `PMISpinner.intValue` with primitive `int` and spinner mode `0`;
- Float8 to `PMISpinner.doubleValue` with primitive `double` and spinner mode `1`;
- String to `PMITextField.text` with `java.lang.String`;
- DateTime to `PMIDateTimePopupSelector.date` with `java.util.Date`.

In one retained client process, all five Good expression sources changed on the next one-second evaluation and every listed native target visibly changed without a quality overlay. Require source Good quality, exact project-resource readback, a responsive fresh client, and before/after native screenshots before relying on these mappings. The validated expression-tag data type name is `DateTime`, not `Date`. Do not infer quality from the displayed value alone. Do not generalize these results to other standard tag types, other quality codes, provider/network disconnects, bidirectional writes, restart persistence, or programmatic component QualifiedValues. Event scripts, navigation, templates, maximized/responsive layout, visually verified tooltip behavior, and advanced components remain separate increments and require their own retained tests before promotion.

For a binding whose target is a Vision `DynamicPropertyDescriptor`, the property adapter must be marked as targeting a dynamic property. In the installed 8.3.8 runtime this is the adapter's `targetPropertyDynamic` flag. Leaving it false selected the JavaBean setter path and produced a Client-side descriptor-cast failure even though native serialization/readback had preserved both the descriptor and adapter. Treat adapter serialization as structural evidence only: exercise the installed setter path offline, then require a fresh Client with no related error dialog/log before crediting subscription or value propagation.

One credited navigation fixture retains four native Vision Windows and validates ten fixed phases in one fresh non-Designer Client: single-instance open, duplicate suppression, close, typed popup parameters, visible wrong-type rejection, swap and return, visible missing-target rejection, window inventory, and close-during-background. Six original-resolution screenshots passed geometry, clipping, overlap, scrollbar, and error-dialog review only after the matching Client and Gateway log gates were clean. The background-close phase imported and captured `java.lang.Thread.sleep` before opening Target A, scheduled bounded background work, closed Target A on the EDT, and observed only the Host Window with exact visible completion state. An earlier use of `system.util.sleep` stopped after Target A opened, so do not substitute it in this installed Client event context. Load [references/validated-navigation-background-close.md](references/validated-navigation-background-close.md) for the exact resource, threading, evidence, and claim boundaries.

## Custom API Boundary

Before expanding a custom API:

1. Prove the live OpenAPI and existing custom routes cannot safely perform the required operation.
2. Define one small reusable operation with explicit inputs, outputs, authorization, side effects, limits, and structured errors.
3. Test successful behavior, invalid input, authorization failure, readback accuracy, diagnostics, and absence of unintended changes.
4. Do not use the new operation as skill evidence until its own validation passes.

Never expose arbitrary script execution, reflection, filesystem access, query text, component methods, tag writes, or caller-selected project mutations as a convenience endpoint.

The validated read-only `vision-client-sessions-v1` custom action is an authenticated fallback for current Vision session inventory when the official 8.3.8 Vision client-list route is unavailable. Supply one exact expected project and optionally a Boolean `includeDesigners`; require `ok`, `sourceAvailable`, and `writesAttempted == false`, then inspect every returned row. A session row proves current Gateway registration only. It does not prove client bridge readiness, open windows, component values, binding quality, pixels, or later liveness, and it does not repair or validate the separate official route.

For a Client message bridge, model process start, Gateway session registration, Client startup observation, handler readiness, and application eligibility as separate states. Select a fresh owned session by exact inventory set difference. Do not use a fixed sleep, session presence, or `SENT` status as proof that a handler can receive and finish work. Require one fixed bounded readiness request and an independently transported exact result before any application message. Cross Vision RPC boundaries with primitive bounded values; encode millisecond timestamps as decimal text because a Jython `long` was observed crossing as `java.math.BigInteger` and failed deserialization. Convert the text to an integer only after exact schema and digit checks. Load [references/fixed-client-bridge.md](references/fixed-client-bridge.md) for the validated readiness sequence, observed local distribution, and limits.

If a selected handler remains silent after readiness and one bounded dispatch, stop application retries. Diagnose it with the fixed, payload-independent checkpoint ladder in [references/fixed-client-bridge.md](references/fixed-client-bridge.md), preserving each evidence boundary and restoring the temporary diagnostic resources afterward.

Portable `llmImport` API 0.85.0 keeps 72 allowlisted actions and exposes `vision-skill-lab-v1` contract 1.4.0. The fixed `invoke-button` bridge remains available. The fixed `snapshot-button` operation additionally creates one temporary String tag, sends one fixed request to the exact client handler, polls under a fixed deadline, validates one bounded component snapshot, and deletes the tag in `finally`. The client crosses scopes with a flat bounded `snapshotJson` string; a fixed Gateway message handler decodes and re-encodes it before the API validates exact keys, classes, bounds, component names, EDT state, missing lookup, and integer `clickCount` metadata. The caller supplies only an idempotency key and one verified client session ID. It accepts no caller code, project, window, component, handler, payload, tag path, timing, or click count.

Always dry-run first. For snapshot apply, require `code == "component_snapshot_verified"`, `snapshotValidationStage == "verified"`, `sendStatusVerified == true`, `cleanupVerified == true`, Good configure/delete qualities, and independent fresh-client evidence. The fixed redacted validation stage is diagnostic metadata, not returned component content. Load [references/fixed-client-bridge.md](references/fixed-client-bridge.md) before using the button bridge and [references/fixed-edt-component-snapshot.md](references/fixed-edt-component-snapshot.md) before using or extending the snapshot path.

## Jython Handoff

For code that will execute inside Vision, give `ignition-vision-jython-83`:

- the exact script location and runtime scope;
- supplied variables and required inputs;
- the resource, window, and component identities;
- the allowed side effects and limits;
- the expected response or visible result;
- the compile, runtime, diagnostics, and restoration checks.

Receive a bounded implementation and validation contract. Use this skill to install it through the supported project-resource lifecycle and verify it in the target environment.

The Jython skill includes a credited fixed four-context language-boundary matrix for Jython 2.7.4: a Client message handler, a scope-`C` Project Library module called through a fixed forwarder, a native `PMIButton.actionPerformed` event, and a scope-`G` Shared Gateway message handler. For Client project libraries, preserve the proven top-level explicit import pattern; do not assume an injected `project.<module>` namespace. For native action scripts, preserve function-wrapper-safe scoping: nested class methods must use instance-owned or explicitly passed state rather than enclosing script locals. In Gateway scope, do not use the Client/Designer-only `system.util.getSystemFlags`; preserve the fixed Gateway-specific scope contract and normalize Java-backed text and Boolean values before exact comparison. Use the matrix as a syntax-generation guard, but preserve its explicit boundary: Designer scripts, other Gateway contexts, arbitrary code, general imports, and broad Python compatibility still require their own tests.

## Completion Gate

Do not report a task complete until:

- the exact 8.3.8 environment and target identities are recorded;
- every write is bounded, reviewed, read back, and diagnosable;
- required evidence is complete and unambiguous;
- runtime or visual claims use a fresh client;
- project-package comparisons use logical resource entries and hashes rather than expecting byte-identical ZIP containers;
- related Gateway, Designer, launcher, or client diagnostics are checked on the correct process plane;
- every available Vision Client error dialog and complete owned-Client log window is captured and reviewed; a Client exception invalidates the affected behavior even when Gateway logs are clean;
- every new or related WARN/ERROR/exception on every required process plane has an evidence-backed disposition; missing or incomplete logs prevent a clean or correct claim;
- a failed diagnostic or session endpoint is reported as an observability gap, never interpreted as an empty or healthy result;
- temporary state is restored;
- unsupported behavior and remaining validation gaps are explicit.

## References

- [references/environment-gate.md](references/environment-gate.md): exact tested Gateway and Vision module identity gate.
- [references/window-build-verify-loop.md](references/window-build-verify-loop.md): native window package, readback, client, visual, diagnostic, iteration, and rollback contract.
- [references/fixed-client-bridge.md](references/fixed-client-bridge.md): fixed message resource, session selection, dispatch, duplicate suppression, visual proof, and API rollback boundary.
- [references/fixed-edt-component-snapshot.md](references/fixed-edt-component-snapshot.md): fixed primitive-envelope snapshot lifecycle, result checks, cleanup, and claim boundary.
- [references/validated-navigation-background-close.md](references/validated-navigation-background-close.md): retained four-Window navigation fixture, typed popup, fixed background-close threading, screenshot, and complete log gates.
- [references/failure-recovery.md](references/failure-recovery.md): visible failure states, authoritative reconciliation, retry suppression, restoration, and log requirements.
