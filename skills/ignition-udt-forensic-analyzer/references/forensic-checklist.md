# UDT Forensic Checklist

Use this reference for deeper UDT reviews after loading the main skill.

## Inventory

- List tag providers and roots included in scope.
- Separate UDT definitions from UDT instances.
- Record each instance `typeId` and match it to a definition.
- Count atomic members, folders, nested UDTs, alarms, event scripts, and history-enabled tags.
- Identify disabled definitions, disabled members, and disabled instances.

## Parameters

- Confirm numeric parameters remain numeric, especially fractional values.
- Confirm boolean parameters remain booleans.
- Check parameter defaults, instance overrides, and nested UDT parameter passing.
- Flag stringified numbers where downstream expressions or alarms expect numbers.
- Flag placeholder values that are unresolved, ambiguous, or inconsistent by instance.

## Member Tags

- Review value sources: OPC, memory, expression, derived, query, reference, and UDT instance.
- Check tag group or scan class assumptions.
- Check inherited overrides against the parent UDT definition.
- Flag members whose names imply command, reset, start, stop, enable, setpoint, output, override, bypass, or mode.
- Flag deleted or missing inherited members when comparing instances to definitions.

## Reference Tags

- Treat parameterized `sourceTagPath` on Reference tags as unsafe unless separately verified in the target Gateway.
- Prefer concrete reference paths or expression/script alternatives with explicit validation.
- Check relative paths for ambiguous folder depth.
- Check provider-qualified paths for portability issues.

## Event Scripts

- Identify valueChanged, qualityChanged, alarmActive, alarmCleared, and other event scripts.
- Flag scripts that write tags, call blocking operations, construct paths from unchecked parameters, or swallow exceptions.
- Check whether scripts depend on project libraries, gateway scripts, system functions, or tag paths outside the UDT.
- Confirm scripts have a clear reason to run at the UDT layer instead of project or Gateway scope.

## Alarms

- Verify each alarm has an intentional priority, label/name, display path, and pipeline.
- Check setpoint and delay values for correct numeric typing.
- Check parameter-driven alarm properties against representative instance overrides.
- Identify disabled alarms and alarms that inherit questionable defaults.
- Confirm alarms are attached to the correct process value, not a command or status-only tag.

## Historian

- Verify `historyEnabled`, history provider, sample mode, deadband, interpolation, and retention expectations.
- Flag history-enabled command, reset, transient, or noisy status tags.
- Check whether UDT instance overrides change historian behavior unexpectedly.
- In API Mode, distinguish configured historian settings from actual stored history.

## Writable Surfaces

- Identify OPC and memory tags that appear writable or command-like.
- Review write permissions if available.
- Flag writable tags that can affect equipment state without clear guardrails.
- Confirm setpoints and commands have naming, permissions, and audit expectations.

## Dependencies

- Extract provider-qualified paths, relative tag paths, OPC item paths, expressions, and script-built paths.
- Map dependencies from UDT definitions to external folders, devices, and other UDT types.
- Flag hard-coded providers when the UDT is expected to be portable.
- Flag missing definitions for instance `typeId` values.

## Validation Evidence

- Mark each claim as API-verified, export-verified, inferred, or unverified.
- In Exported JSON Mode, do not claim live quality, permissions, historian storage, or script execution verification.
- In API Mode, capture enough read-only evidence to reproduce the conclusion.
- Keep unresolved evidence gaps visible in the final report.
