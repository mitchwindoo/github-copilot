# Fixed Vision Client Bridge

Use this contract only for the tested Ignition 8.3.8 fixture. It is a narrow validation bridge, not a general remote-control API.

## Fixed identities

- project: `V83_SKILL_LAB`
- user: `vision_skill_lab`
- window: `00 Blank Startup`
- component: `IncrementButton`
- client message handler: `vision-p03-t03-click`
- handler resource type: `com.inductiveautomation.vision/message`
- handler thread type: `EDT`
- bridge contract: `vision-button-event-bridge-1.0.0`
- API action: `vision-skill-lab-v1`
- API operation: `invoke-button`

The native handler resource has client scope, `enabled: true`, `threadType: EDT`, and one `handleMessage.py` data file. Generate or preserve it through Ignition's 8.3.8 `ScriptConfig.MessageHandlerScript` resource contract; do not hand-invent an opaque resource.

## Required lifecycle

1. Verify exact Gateway/Vision versions and capture the live API version, action count, project archives, and WARN+ baseline.
2. Inventory Vision sessions before launching the owned client.
3. Import/read back the exact fixture and launch one fresh authenticated client.
4. Inventory sessions again and require exactly one new non-Designer session for the fixed project and user.
5. Call `invoke-button` with `dryRun: true`, `apply: false`, one bounded idempotency key, and the exact new session ID. Require `writesAttempted == false`.
6. Apply one unique request. Require one Client selection and `sendStatusVerified == true`, then independently capture the client.
7. Repeat the same request ID and independently prove the visible count did not change.
8. Send additional unique request IDs and independently prove each intended state.
9. Close only the owned client, capture the complete WARN+ window, restore both temporary projects, compare logical ZIP entries and hashes, and confirm the stable API version/action count.

## Interpretation boundary

`sendStatusVerified` means the Gateway selected one fixed client and reported `SENT`. It does not prove handler readiness, handler completion, `doClick()` execution, native event-script success, or pixels. Those require independent client evidence.

The credited cycle proved visual counts `0 → 1 → 1 → 5` in one responsive fresh client, with the duplicate request ID suppressed. It did not test concurrency, delayed registration, restart persistence, Designers, multiple matching clients, arbitrary handlers, arbitrary components, or general message payloads.

The official `/api/v1/clients` route produced the known Ignition 8.3.8 null-array warning during the cycle. Classify it separately from bridge faults; use the authenticated `vision-client-sessions-v1` fallback only after the official route fails.

## Handler-readiness gate

For the validated 8.3.8 readiness pattern:

1. Capture the non-Designer session baseline before launch.
2. Launch one owned Client and select exactly one new fixed-project/fixed-user session by set difference.
3. Require an independently transported fixed startup observation for that exact Client.
4. Only then send one fixed no-side-effect readiness probe.
5. Require the exact request, Client, contract, `handlerReady: true`, and EDT thread result.
6. Mark application messages eligible only after that result.
7. Close the exact owned PID and require both process absence and session removal before another launch.

Keep cross-scope payloads primitive and bounded. Encode epoch-millisecond observations as decimal text, validate a positive digit-only string of bounded length, and only then convert locally for timing math. In this installed Jython 2.7.4 Client, `int(system.date.now().getTime())` produced a Jython `long` that crossed Vision RPC as `java.math.BigInteger` and failed Gateway deserialization.

Ten sequential fresh Clients on the tested local Gateway produced these millisecond minimum/median/maximum values:

- process start to startup observation: `4516 / 4603 / 4689`;
- process start to Gateway session observation: `8324 / 8426 / 8491`;
- startup observation to verified handler result: `4026 / 4134.5 / 4233`;
- readiness-probe request to verified result: `107 / 118 / 131`.

These values bound one fixed fixture on one tested host; they are not portable timeout constants. Use explicit polling deadlines, preserve outliers, and diagnose a missing stage instead of assuming readiness after a sleep. The ten-launch result did not test concurrent requests, forced delayed registration, restart persistence, Designer receipt, simultaneous multi-client targeting, upgraded-project serialization, or broader payload schemas.

## Silent-handler diagnostic ladder

Use this only after exact session selection, startup evidence, handler readiness, and one bounded application dispatch have been established. It diagnoses where execution stopped; it is not a retry strategy and does not prove the application result.

1. Replace the temporary test handler with a diagnostic handler whose first executable instruction writes one fixed bounded marker to a fixed temporary result transport.
2. Launch a fresh owned Client, re-establish readiness, dispatch exactly once, and require the exact marker schema and allowlisted stage.
3. In a later bounded cycle, retain the proven first marker, add exactly one payload-independent operation such as a fixed Java import, and write a second fixed marker immediately afterward.
4. Continue only one operation per reviewed cycle. Stop before payload reads, component traversal, descriptor or bound-value access, navigation, tag-dependent values, or other application side effects.
5. Preserve the raw result and the Client/Gateway diagnostic window. Close only the owned Client, remove the temporary handler and result transport, and prove restoration before another cycle.

Interpret the stages narrowly:

- no first marker: the remaining fault is at or before compilation, registration, handler identity resolution, dispatch delivery, or entry;
- first marker only: handler entry and the first fixed write succeeded, but the next operation did not complete;
- marker after an import or fixed call: that preceding operation completed, but nothing later is implied;
- a dispatch status of `SENT` without a marker: delivery was requested, not proven complete.

Keep every stage, handler identity, destination, and request fixed and server-owned. Accept only primitive bounded fields and an allowlisted stage. Never transport exception messages, stack traces, credentials, arbitrary code, caller-selected paths, reflection targets, component names, or unrestricted payload content through this diagnostic. Use a fresh Client for each credited runtime claim, make no automatic retry, and do not promote the underlying application behavior until its independent result oracle passes.
