---
name: ignition-udt-builder
description: Build, review, and validate Ignition 8.1 User Defined Types, UDT instances, nested UDTs, parameters, expression tags, alarms, tag event scripts, and API or import workflows. Use when Codex needs to model reusable equipment tag structures, create UDT fixtures through the Web Dev runner, or repair UDT parameter and expression behavior.
---

# Ignition UDT Builder

Skill version: `1.0.97`
Stack version: `starter-2026.07.06.04`
Ignition target: `8.1`

## Scope

Use this skill to design reusable Ignition UDT types and instances, including parameters, expression tags, memory/OPC member structure, nested UDTs, alarms, tag event scripts, and validation steps.

For live Gateway writes through the approved Web Dev runner, use this skill for the UDT model and `ignition-perspective-host-builder` for API request mechanics. For Jython bodies, also use `ignition-jython-script-builder`. For portable Perspective packages that list UDT prerequisites, also use `ignition-perspective-import-zip`.

Do not delete, prune, or clean up tags, UDTs, folders, alarms, scripts, or project resources unless the user explicitly commands deletion in the current task.

## Workflow

1. Identify the equipment class, repeated instances, member tags, expected parameters, alarms, scripts, and Perspective consumers.
2. Discover the target tag provider and root folder before authoring. Prefer `tagProviders`, `tagBrowse`, and explicit `tagRead` through the runner when available. On runner `0.3.83+`, treat `tagBrowse.truncated: true` or `totalAvailable > returnedCount` as an incomplete browse and narrow/increase the capped browse before modeling UDT rows.
3. Define UDT types under `[provider]_types_/<relative folder>`. Create instances only under normal `[provider]<folder>` tag paths.
4. Keep UDT `typeId` values relative to `_types_`, such as `Area/PumpCore`, not provider-qualified paths.
5. Dry-run every `tagConfigure` or `udtScaffold` write. Apply only with the runner confirmation string, require `allGood: true` and good returned `qualityCodes` for every relevant step, then verify with explicit member and parameter reads. Runner `0.3.112+` makes `udtScaffold` return top-level `ok: false` when a nested scaffold step returns `ok: false` or `allGood: false` and advertises `udtScaffoldStepAllGoodFailureOkFalse`; Runner `0.3.113+` adds partial-failure recovery metadata, including `recoveryRequired`, when a scaffold write fails after earlier steps. Runner `0.3.143+` advertises `udtScaffoldUnknownFailureRecovery`; if a failed confirmed non-dry-run nested `tagConfigure` step has missing, null, or empty `qualityCodes`, treat the step as unknown-mutated and inspect the recovery fields before any follow-up write. Older runners still require manual `stepResults[]` inspection.
6. Validate expression tags by reading their runtime values and qualities. Do not trust successful configuration alone.

## Core Rules

- Prefer parameterized UDTs over copied tag trees. Use parameters for PLC paths, asset names, engineering limits, enable flags, display paths, and reusable setpoints.
- For real OPC tags, parameterize OPC item paths per the official UDT parameter rules. The low-touch runner blocks OPC writes, so use memory/expression fixtures for API tests unless site-approved device paths exist.
- Use scalar parameter overrides for numeric and Boolean UDT parameters unless a tested typed object is required. For decimal typed objects, prefer `{"dataType": "Float", "value": 4.5}` and validate `Parameters.*` readback before binding.
- Avoid value-only parameter objects such as `{"value": "480"}` because they can configure as null or wrong-typed parameters even when `tagConfigure` reports `allGood`.
- Do not send numeric or Boolean UDT parameter overrides as strings when expressions or Perspective row models need real numbers/booleans. Expression multiplication/comparison may coerce strings, but `+` can concatenate.
- After parameter writes that affect expressions, validate dependent member quality as well as value. Bad strings can configure successfully and then produce `Error_ExpressionEval` at runtime.
- Faceplate-safe computed values should expose quality/status helpers next to the value, such as `PVGood`, `PVBadOrError`, and `FaceplateStatus`. Use `isGood()` or `isBadOrError()` for expression-error guards; `isBad()` alone may not catch `Error_ExpressionEval`.
- In UDT expression tags, UDT parameters use `{ParamName}` and member tag references use relative tag paths such as `{[.]PV}`.
- For dynamic full tag paths in UDT expression tags, use `tag({FullPathParam})` without quotes. For assembled paths, concatenate strings inside `tag(...)`; do not use `tag("{FullPathParam}")` or direct brace paths like `{[Provider]{Root}/PV}`.
- Treat official `{Param+offset|format}` syntax as UDT member-property substitution, especially for OPC item paths. In expression tags, brace offset/format placeholders inside quoted strings stayed literal; use expression-language arithmetic plus `numberFormat(...)` when building generated strings or `tag()` paths.
- Do not rely on UDT parameters inside Reference tag `sourceTagPath`; use static Reference tags or expression tags with `tag(...)` for parameter-driven indirection, then validate value and quality.
- Expression language cannot browse tags. If a use case needs to scan child tags, discover UDT instances, or aggregate a variable number of members, use Jython or a parent model instead of an expression tag.
- Build nested UDTs cautiously. When using raw API `tagConfigure`, nested child parameters set to strings like `{ParentParam}` can stay literal; explicitly configure nested instance parameters per parent instance or verify readback before relying on parameter pass-through.
- For command/interlock equipment modules, model repeated permissives as child UDT instances and aggregate a fixed set of child `Healthy`/`Bypass` members with parent expression tags such as `PermissivesOK`, `CanStart`, `StartAccepted`, `StartRejected`, and `InterlockActive`; keep bypass visible as an attention flag.
- For inherited UDT types, set the child `UdtType.typeId` to the parent type's relative path, then verify inherited member and parameter reads on an instance.
- For equipment families with variants, keep common Perspective-facing members and metadata on the base UDT, put variant-only members on derived UDTs, and browse each concrete relative `typeId`; a base-type browse only confirms direct base instances.
- Treat `None` as a real null value. Do not use the string `"null"` unless the literal text is intentionally different from null. If the default should apply, omit the override when possible.
- For Perspective row models and bindings, preserve the distinction between null, empty string, literal `"null"`, valid values, and omitted defaults. Guard numeric null before arithmetic, and do not put `{ParamName}` inside quoted expression strings because it can remain literal.
- Missing or nonexistent parameter references can literalize in string outputs. Read generated address/token members before using them as Perspective labels or dynamic paths.
- Updating a UDT definition parameter default propagates to instances and derived types that did not override it; derived type parameter defaults and explicit instance parameter overrides remain unchanged. Validate each case with `Parameters.ParamName` and expression member reads.
- Read UDT instance members and `Parameters.ParamName` paths for validation. Reading the UDT instance root may return a document-style snapshot; reading a folder path can be unsupported.
- Use `system.tag.configure()` with collision policy `"m"` for targeted UDT type edits. Build fresh minimal configs; do not write back raw `getConfiguration()` output as a clone payload. A partial `"o"` overwrite can remove omitted UDT members.
- When editing an existing UDT type, set `basePath` to the parent `_types_` folder and `name` to the type name. A dry-run with `basePath` set to the type path plans a nested `<Type>/<Type>` target.
- For UDT tag event scripts, read parameters with `tag["parameters"]["ParamName"]`, cast values before math, guard `initialChange`, and use `[.]Sibling` relative reads/writes for result/status tags. A later event can see a merged instance parameter update without restarting the UDT. Avoid legacy `{ParamName}` script expansion and `.format(...)` placeholders in event bodies.
- For UDT discovery, browse bounded roots with both `tagType: "UdtInstance"` and the relative concrete `typeId`. For multiple equipment classes or derived variants, run one browse per concrete `typeId`, merge unique instance paths, then filter by child/member values after readback; duplicate `typeId` keys are not OR.
- For Perspective-facing UDT row models, make display/sort/filter metadata explicit UDT parameters such as `AssetName`, `DisplayName`, `Area`, `EquipmentType`, `Variant`, `DetailViewKey`, `SortOrder`, and `Units`; batch-read those `Parameters.*` paths plus stable members such as `PV`, `Status`, `Running`, and alarm/attention flags.
- Predefined parameters such as `{InstanceName}`, `{TagName}`, `{PathToTag}`, `{PathToParentFolder}`, and `{RootInstanceName}` can be useful row/detail metadata, but nested semantics are context-sensitive; validate `{ParentInstanceName}` and `{RootInstanceName}` in the exact member shape.
- Normalize numeric and Boolean `Parameters.*` readback before sorting, filtering, comparisons, or Perspective bindings; Ignition can read parameter values as strings even when dependent expression tags evaluate numerically.
- For UDT alarms through `tagConfigure`, keep numeric alarm setpoints concrete in the type or merge concrete per-instance alarm overrides; do not rely on UDT parameter placeholders or parameter-binding objects for numeric alarm properties.
- Alarm `displayPath`, `label`, and notes-style string metadata can use plain UDT parameters only after runtime alarm reads and current alarm status rows confirm the exact generated shape.
- Do not set alarm `priority` to a UDT parameter placeholder such as `"{AlarmPriority}"`; use a concrete type priority or merge a concrete per-instance alarm override.
- Treat alarm `enabled` parameters as target-shape sensitive. Read `PV/Alarms/<Name>.Enabled`, `IsActive`, and filtered current alarm rows before assuming a true parameter enabled the alarm.
- For per-instance alarm overrides, merge the alarm config onto the instance member with `collisionPolicy: "m"` before changing the PV/value that activates the alarm; otherwise current alarm status can capture the type-default display path.
- Apply priority/display/label/enabled overrides before the event becomes active; runtime alarm paths may update after a late override, but the current active alarm status row keeps activation-time display and priority.
- For UDT-backed alarm rollup/navigation pages, make alarm `displayPath` include stable area and asset segments, then validate runtime `PV/Alarms/<Name>.DisplayPath`, per-area `alarmStatusQuery` counts, and browser-visible rollup/detail params before claiming the page is correct.

## Pattern Reference

Read [references/udt-patterns.md](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-udt-builder/references/udt-patterns.md) when the task needs concrete JSON shapes, nested UDT guidance, expression examples, validation reads, or scripting patterns.

## API Pattern

For concrete `tagConfigure` UDT type and instance request shapes, read [references/udt-patterns.md](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-udt-builder/references/udt-patterns.md#tagconfigure-request-shapes).

Keep API writes dry-run-first. For apply calls, set `dryRun` false and include the runner's exact confirmation string.

## Validation Reads

After creating or editing a UDT, read:

- `[provider]folder/Instance/Parameters.ParamName`
- For generated page models, use dot-style `Parameters.ParamName` reads as the canonical parameter path shape and record `tagPath` plus `typeId` for detail/navigation params.
- For derived UDT variants, include `variant` or `detailViewKey` in row/detail params and read variant-only members only for the concrete `typeId` that declares them; unguarded reads on base instances can return bad/not-found quality.
- `[provider]folder/Instance/Member`
- `[provider]folder/Instance/ExpressionMember`
- Any alarm runtime paths and current alarm query filters that the page or script will use
- For alarms, include `IsActive`, `DisplayPath`, `Priority`, `Enabled`, `Label`, and `SetpointA` runtime reads plus filtered current alarm status rows
- For tag event scripts, result/status/error tags plus `Parameters.ParamName` reads after any instance-parameter merge
- The current Gateway logs only as diagnostics, not as confirmation
- Dependent expression tags after parameter overrides, because bad string or wrong-shaped parameter values can configure successfully and fail only at expression runtime
- Generated address/token members and any `tag()` reads built from parameters, including source tag value, generated token, generated path value, and quality
- For parameter-driven computed members, read both the value and quality/status helpers such as `PVGood`, `PVBadOrError`, `RangeBad`, and `FaceplateStatus` before exposing the value in Perspective
- For command/interlock modules, scenario reads for accepted, rejected, bypassed, and faulted states, including child `State`, `Bypass`, `Healthy`, `Attention`, and parent aggregate expressions

Stop and repair if a parameter read is literal text such as `{OtherParam}`, a value has bad quality, or an expression output does not match the expected member and parameter values.

## Official Docs

Use Ignition 8.1 documentation unless the user explicitly asks for another version:

- User Defined Types: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/user-defined-types-udts
- UDT Parameters: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/user-defined-types-udts/udt-parameters
- Tag Event Scripts: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/tag-event-scripts
- `system.tag.configure`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-configure
- `system.tag.browse`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-browse
- Expression quality functions: https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/logic/isGood and https://www.docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/logic/isBadOrError
