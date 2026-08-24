---
name: ignition-udt-forensic-analyzer
description: Audit Ignition 8.1 UDT definitions, UDT instances, exported tag JSON, and reachable Gateway tag evidence for parameters, members, scripts, alarms, historian settings, writable tags, dependencies, and validation evidence. Use when reviewing UDT health, diagnosing UDT-related project risk, comparing definitions to instances, or analyzing UDT exports without Gateway API access.
---

# Ignition UDT Forensic Analyzer

Skill version: 1.0.11  
Stack: starter-2026.06.27.03  
Target Ignition: 8.1.x

## Scope

Use this skill to audit Ignition UDT definitions and instances for configuration risk. The review should cover parameter typing, member tags, expressions, Reference tags, event scripts, alarms, historian settings, writable surfaces, dependency paths, and missing validation evidence.

Default posture is read-only. Do not create, edit, delete, import, or write Gateway resources unless the user explicitly asks for remediation.

## Choose The Mode

### API Mode

Use API Mode when the current environment has Gateway or runner access.

1. If using the approved Web Dev runner, call `health` first and inspect `runnerVersion`, `supportedActions`, `features`, and `tokenConfigured`. Treat `supportedActions` as callable actions and `features` as capability flags.
2. Discover available read-only capabilities first.
3. Inventory tag providers, UDT definitions, UDT instances, and relevant tag folders.
4. Read configuration and runtime quality/value evidence only where the available API supports it.
5. Keep configured state separate from runtime state.
6. Report unreachable providers, missing permissions, or unavailable endpoints as evidence gaps instead of guessing.

### Exported JSON Mode

Use Exported JSON Mode when the user provides Ignition tag export JSON and no live Gateway access is available.

1. Load the export and identify UDT definitions, UDT instances, member tags, parameters, alarms, scripts, historian settings, and external references.
2. If useful, run the helper:

```bash
python scripts/analyze_udt_export.py path/to/tag-export.json --json-out udt-audit.json
```

Use `--format json` when downstream tooling needs machine-readable stdout.
The helper labels exported findings and dependencies with `evidenceSource: exported-json`.
It also flags common exported alarm metadata, historian metadata, and command-like writable-surface gaps.
Use its `findingSummary`, `dependencySummary`, `memberReviewSummary`, and `scriptReviewSummary` to quickly review severity/category/evidence rollups, dependency kinds, providers, repeated targets, hard-coded provider assumptions, explicit instance member overrides, and static script-review signals.

3. Treat the result as a configuration audit only. Exported JSON cannot confirm live tag quality, OPC permissions, subscription health, historian writes, or script execution.
4. Mark runtime-only claims as unverified unless the user provides additional evidence.

## Audit Passes

Run these passes in order unless the user's question is narrower:

1. **Inventory** - Count UDT definitions, UDT instances, atomic members, folders, providers, and type relationships.
2. **Parameters** - Preserve numeric, boolean, and fractional parameter types. Do not flatten typed parameter values into strings.
3. **Members** - Review member names, value sources, nested UDTs, inherited overrides, expression tags, Reference tags, and disabled tags.
4. **Reference Tags** - Do not rely on parameterized Reference `sourceTagPath` values. Flag them for redesign or live verification before use.
5. **Scripts** - Inspect tag event scripts for side effects, writes, blocking calls, brittle path construction, missing error handling, and candidate project-library references.
6. **Alarms** - Verify alarm enablement, setpoints, priorities, labels, pipelines, display paths, and parameter-driven numeric values.
7. **Historian** - Check history enablement, provider names, sampling mode, deadband, scan class/tag group, and storage expectations.
8. **Writable Surfaces** - Identify writable memory, OPC, derived, script-driven, command, reset, start, stop, enable, and setpoint tags.
9. **Dependencies** - Map intra-UDT references, external tag paths, provider assumptions, OPC item paths, expression bindings, and nested type dependencies.
10. **Validation Evidence** - State which findings are API-verified, export-verified, inferred from configuration, or still unverified.

For detailed review criteria, load `references/forensic-checklist.md`.

## Output Contract

Produce a risk-ranked report with:

- Executive risk summary.
- Inventory and scope reviewed.
- Findings grouped by severity.
- Affected UDT definitions, instances, and tag paths.
- Evidence source for each finding: API, exported JSON, user-provided file, or inference.
- Recommended fix or next validation step.
- Explicit evidence gaps.

When helper JSON includes `evidenceSource`, carry that label into the narrative instead of replacing it with vague wording.

Use severities consistently:

- **Critical** - Likely unsafe behavior, destructive writes, broken production dependencies, or alarm/historian failure with operational impact.
- **High** - Strong evidence of broken UDT behavior, invalid paths, invalid parameterization, missing definitions, or hazardous writable surfaces.
- **Medium** - Configuration risk that needs review or targeted verification.
- **Low** - Cleanup, documentation, naming, or coverage improvement.

## Practical Rules

- Separate recommendations from evidence gaps.
- Prefer concrete tag paths, exported JSON excerpts, and API result summaries over broad claims.
- When reviewing decimals, booleans, and integers, preserve the original typed representation.
- When API access exists, prefer read-only live evidence over assumptions from an export.
- Treat administrative diagnostic code execution as a separate explicit approval path, even when the intended inspection is read-only.
- When only an export exists, say exactly what cannot be verified.
- Do not infer deleted inherited members from absence in an exported instance unless the export explicitly encodes deletion or live configuration confirms it.
- Do not recommend bulk changes until the affected UDT definitions and instance override behavior are understood.



