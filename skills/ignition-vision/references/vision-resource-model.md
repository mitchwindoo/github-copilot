# Vision Resource Model

## Contents

- [Project and module roots](#project-and-module-roots)
- [Resource directory contract](#resource-directory-contract)
- [Windows, templates, and startup](#windows-templates-and-startup)
- [Client tags and client event scripts](#client-tags-and-client-event-scripts)
- [Bindings and external dependencies](#bindings-and-external-dependencies)
- [Native serialization boundary](#native-serialization-boundary)
- [Small in-place window changes](#small-in-place-window-changes)
- [Import, export, relocation, and rollback](#import-export-relocation-and-rollback)
- [Release and retention boundary](#release-and-retention-boundary)

## Project And Module Roots

An Ignition project is a collection of module-owned resources plus project-level configuration. Select the project through the live Gateway API. Do not infer the project from a local directory name or Designer tab.

Vision resources live below the Vision module root, commonly including logical groups for windows, templates, client tags, and client event scripts. Treat each resource path as a sequence of Ignition resource-name segments and validate every segment through the installed Gateway before writing.

## Resource Directory Contract

A manifest-backed resource directory contains `resource.json` and the exact payload files declared by the manifest. Preserve:

- scope and attributes;
- declared file names and order where significant;
- resource identity and logical path;
- opaque payload bytes unless a target-version serializer owns the change;
- the relationship between payload, manifest, and thumbnail.

Reject missing/extra required files, duplicate normalized ZIP destinations, traversal, prefix escape, invalid names, stale hashes, malformed metadata, and unexpected nested resource roots.

Resource-state hashes should cover the complete current resource. Use them as preconditions for delete, overwrite, relocation, and other guarded changes.

## Windows, Templates, And Startup

Windows and templates are separate resource types with separate payload contracts. A window commonly includes root design bounds, component hierarchy, bindings, action metadata, and startup attributes. A template also includes public parameters and can be consumed by repeaters, canvases, or holders.

- Preserve the exact serialized logical identity.
- Keep nested bounds relative to the immediate parent.
- Keep one intended startup window unless the project explicitly needs more.
- Do not mark gallery/review examples as startup windows.
- When auditing a legacy resource, an omitted `open-on-start` attribute means the resource is not selected for startup; normalize every retained or newly written gallery example to explicit `open-on-start=false` instead of preserving the omission.
- Validate navigation targets and template usage before moving or deleting a resource.
- Retain every template and dependency required by a retained consuming window.

Multiple startup windows may appear stacked in the Vision Client. Startup is not a page-layout mechanism.

## Client Tags And Client Event Scripts

Client tags and Client Event Scripts are singleton-style project resources with native payloads. Editing one handler or tag must preserve unrelated entries and non-handler configuration.

- Use a target-version deserializer/serializer or a dedicated preservation helper.
- Require exact source hashes before transformation.
- Compile inserted Jython with the installed target runtime.
- Deserialize and verify the final payload.
- Preserve permissions semantics. A null permissions object and an empty permissions collection may have different meanings.
- Install required message handlers and mailboxes before starting the client that consumes them.
- Keep handlers/mailboxes when a retained resource declares them as runtime dependencies.

Do not edit these singleton resources by text replacement or partial binary patching.

## Bindings And External Dependencies

A Vision resource can depend on assets outside its directory:

- tag providers, tags, UDT definitions/instances, and tag history;
- database connections, Named Queries, and query parameters;
- alarm configuration, users, roles, and security zones;
- templates, images, styles, fonts, and navigation targets;
- Client Tags, Client Event Scripts, message handlers, and mailboxes;
- project default tag provider and default database settings.

Inventory dependencies before mutation and keep them with retained working examples. Prefer fully qualified tag paths. If an unqualified path is intentional, prove the live project's default provider and availability.

Structural extraction can miss computed or script-built dependencies. Review bounded script/action metadata and document dependencies that cannot be resolved statically.

## Native Serialization Boundary

Vision native payloads may be gzip XML or a native binary format depending on the resource and target version.

- Use a Designer export or matching target-version serializer as the source of truth.
- Initialize serializer/deserializer defaults.
- Round-trip final bytes.
- Normalize only explicitly declared deterministic fields.
- Preserve Java types, expression parse trees/listeners, layout fields, component order, and resource metadata.
- Treat binary transcode as read-only structural evidence, not as a general writer or runtime execution surface.
- A legacy binary window may store only a basename or another stale constructor identity even when the selected project resource path is correct. Report the mismatch, but guard lifecycle operations with the selected resource path, complete resource-state hash, and exact files. Let a supported relocation/target-version serializer rewrite the identity; do not patch the embedded text manually.
- Never patch unknown binary offsets.

## Small In-Place Window Changes

Use this workflow for a narrow change to one existing window while preserving its logical resource identity, such as changing `<COMPONENT_PATH>.<PROPERTY_NAME>` or one direct or expression binding. Do not use it for relocation, whole-window replacement, client-event resources, Project Library code, or an edit whose complete impact cannot be bounded.

1. **Inspect and fingerprint.** Call live health and require the actions/features needed for resource read, export, inspection, dependency checks, import dry-run, backup, and readback. Select the exact project and resource, validate every resource-name segment, and record the complete resource-state hash, file hashes, manifest semantics, startup set, component and interaction counts, full binding projection, exact target component class/path/property, dependency readiness, relevant logs, and client-session state. Stop on truncated inspection, ambiguous target, bad dependency quality, unsafe active clients, or Designer-local state that could later overwrite the API-managed resource.
2. **Export the complete resource.** Use bounded `projectResourceExport` for the exact window and retain the returned package as the local rollback artifact. Require `resource.json` plus every payload declared by the manifest; preserve the original thumbnail and any payload not intentionally changed.
3. **Deserialize with the matching target runtime.** Use the same Ignition patch and Vision libraries as the Gateway, initialize the complete deserializer, and register the required aliases, handlers, and delegates. The runner's binary transcode is inspection evidence, not a general writing surface. Stop if a target-version serializer/deserializer or dedicated preservation helper cannot safely round-trip the resource; never replace text in XML blindly or patch opaque binary bytes.
4. **Change the actual object.** Resolve exactly one component and property and assert the expected component class and existing binding/property type before mutation. For a static property, invoke the appropriate bean setter with the correct Java type. For an expression binding, update the adapter and parsed expression while preserving the value class, bound-tag listeners, adapter settings, and adapter/listener initial `QualifiedValue` state. For a direct binding, preserve its source, quality/subscription settings, and target type except for the explicitly requested field.
5. **Serialize and round-trip.** Serialize the complete window, then deserialize the result again with the target runtime. Compare the before/after structural and binding projections and require that only the declared target changed; preserve component order, bounds, layout constraints, startup semantics, navigation, scripts, and unrelated bindings.
6. **Build the smallest complete package.** Package the preserved `resource.json`, preserved thumbnail, and only the serializer-owned payload that changed. Use the exact allowed resource prefix and retain deterministic hashes for the original export and candidate package.
7. **Dry-run and recheck the mutation boundary.** Run `projectResourceImportZip` with `dryRun:true`; require legal destinations, zero conflicts or ignored files, and an overwrite plan containing only the expected payload. Immediately re-read the live resource, dependencies, startup set, and session inventory and require the fingerprints to match the baseline before applying.
8. **Apply with recovery.** Send the documented import and overwrite confirmations, require a named rollback backup, and require project-scan completion. If the HTTP response is lost or ambiguous, reconcile resource readback and backup inventory before retrying.
9. **Verify independently.** Re-read and re-inspect the live resource. Require the requested property/binding value or source hash, unchanged non-target binding projections and structure, preserved startup and dependency behavior, Good required data, clean focused logs, safe Gateway health, and zero unintended clients. Add a fresh-client runtime and pixel check when the change makes a runtime or visual claim.
10. **Rollback on any failed gate.** Use the named API backup rather than manually swapping project files. Verify the restored payload, normalized manifest, structure, binding projection, startup set, dependencies, and health before attempting another change.

For example, the target contract may identify resource `<WINDOW_RESOURCE_PATH>`, component `Root Container/StatusPanel/StatusLabel`, property `text`, and an expression such as `if({[<PROVIDER>]<TAG_PATH>}, "ENABLED", "DISABLED")`. Treat these as placeholders: discover the real resource, component path, property type, provider, and tag path from the target Gateway.

## Import, Export, Relocation, And Rollback

Export one exact resource with bounded file/byte limits and record its hash before a change.

For import:

1. Validate package shape, normalized paths, manifests, legal names, and allowed prefix.
2. Dry-run and review unchanged/conflicting/new files.
3. Apply with exact confirmation and current-state guards.
4. Require backup, scan completion, exact readback, structural inspection, and dependency preflight.

Ignition may rewrite `resource.json` metadata while scanning an otherwise exact import. Do not require the post-import manifest bytes to equal the package bytes. Require normalized manifest semantics, exact hashes for immutable payloads such as `window.bin`, `thumbnail.png`, or `code.py`, and agreement between API readback and the live project filesystem.

For delete, require one exact manifest-backed resource, current resource-state hash, dry-run, confirmation, backup, scan, and absence verification.

For relocation, require the supported same-version format, exact source/destination identities, absent/expected destination state, legal names, dependency-impact review, structured identity rewrite, backup, scan, source absence, destination readback, and dependency preflight.

For a from-scratch replacement, keep the new window at a separate nonstartup path until it passes live proof with actual Gateway data. Require at least two completed refreshes, derived-state checks, focused client/Gateway logs, and a native screenshot. Pin the accepted proof and candidate resource/file hashes before deleting the old resource. Then delete only the exact old resource with a state guard and backup, relocate the proven candidate through the supported action, and repeat the runtime proof at the canonical path. Retain the replacement's dependencies; audit legacy dependencies separately before removing them.

Rollback through the recorded runner backup. Do not manually swap live project files. Reconcile after any lost response before retrying.

## Release And Retention Boundary

The development folder may contain evidence, test runs, outputs, plans, caches, diagnostics, screenshots, seed generators, recovery tools, and retained lab artifacts. Those are not customer skill resources.

Build releases from an exact external allowlist. Include only:

- `SKILL.md` and `agents/openai.yaml`;
- customer operational references routed from `SKILL.md`;
- portable reusable scripts routed from customer documentation;
- explicitly referenced approved assets that are necessary to perform the skill.

Exclude internal evidence/testing/handoff documents, ledgers with run history, caches, compiled files, local paths, credentials, raw/diagnostic screenshots, lab fixtures, and unreferenced helpers.
