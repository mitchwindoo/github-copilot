# Fixed EDT Component Snapshot

Use this only with Ignition 8.3.8, Vision 12.3.8, `llmImport` API
0.85.0, and `vision-skill-lab-v1` contract 1.4.0. It is a fixed
validation fixture, not a general component-inspection API.

## Fixed identities

- project: `V83_SKILL_LAB`
- user: `vision_skill_lab`
- window: `00 Blank Startup`
- client handler: `vision-p03-t03-click`
- Gateway result handler: `vision-p09-t05-snapshot-result`
- temporary tag: `[default]_VisionSkillLabP09T05/Snapshot`
- snapshot contract: `vision-edt-component-snapshot-1.1.0`
- bridge contract: `vision-button-event-bridge-1.2.0`
- fixed components: `IncrementButton`, `ResultLabel`, `Header`,
  `Instruction`, and `Footer`

The operation accepts only one idempotency key and one verified
non-Designer client session ID for the fixed project and user. It accepts
no caller project, window, component, handler, payload, tag path, timing,
property, method, class, or code.

## Required lifecycle

1. Verify exact Gateway/Vision versions, API 0.85.0, 72 actions,
   `acceptsArbitraryCode == false`, both Vision actions, and the fixed
   contract.
2. Capture both project archives, session inventory, tag absence, and a
   WARN+ baseline.
3. Import and read back the exact fixture, launch one fresh authenticated
   client, and select exactly one new non-Designer session.
4. Call `snapshot-button` with `dryRun: true`, `apply: false`; require no
   tag configuration or message send.
5. Apply once with a new idempotency key. Require:
   - `code == "component_snapshot_verified"`
   - `snapshotValidationStage == "verified"`
   - `ok`, `sessionVerified`, `sendStatusVerified`, and
     `cleanupVerified`
   - one Good configure quality and one Good delete quality
   - one dispatch and the exact snapshot/bridge contracts
6. Validate the bounded snapshot independently:
   - execution on the Swing EDT;
   - five exact component names;
   - one `PMIButton` and four `PMILabel` classes;
   - button bounds `[300, 245, 400, 105]`;
   - result bounds `[250, 390, 500, 95]`;
   - `clickCount == 0`, declared Java type `int`, and Python type `int`;
   - the fixed missing-component lookup is absent.
7. Require the temporary tag to be absent after the response. Close only
   the owned client.
8. Restore both projects, compare every logical ZIP entry and hash,
   recheck stable health/tag/process state, and disposition every WARN+.

## Transport and interpretation

The client sends only a flat, bounded `snapshotJson` string plus fixed
contract and request fields. The Gateway handler validates that shape,
decodes the string locally, reconstructs the nested fixed result, and
writes it to the fixed temporary String tag. This avoids relying on
nested dictionary transport across client/Gateway message scopes.

Ignition 8.3.8 `system.util.jsonDecode` returns Jython objects. In
particular, a decoded true value has exact Python type `bool` but is not
guaranteed to be the singleton `True`. Validate it with exact bool type
plus truth, and reject numeric `1`; do not use `value is True` after JSON
decode.

`snapshotValidationStage` is one fixed redacted stage name. It can locate
a failed fixed schema check without returning arbitrary client content.
It does not authorize relaxed schemas or caller-selected inspection.

The credited cycle also used same-client screenshots and fixed button
dispatches to prove `0 -> 1 -> 1` duplicate replay `-> 5`. That visual
evidence is separate from the snapshot response.

## Claim boundary

This proves one fixed EDT-safe snapshot, one exact request/response
bridge, fixed session targeting, and temporary-state cleanup. It does not
prove arbitrary introspection, recursive traversal, caller-selected
properties or methods, unrestricted client control, concurrent snapshots,
Designer receipt, restart durability, or production remote automation.
