# Vision Window Build And Verify Loop

Use this loop for each new Vision window capability. The validated primitives are a blank open-on-start window and a fixed-size static page with labels over native rectangular panels. Later binding, scripting, navigation, responsive-layout, or advanced-component increments must pass the same loop before they become reusable guidance.

## 1. Establish The Baseline

1. Verify the exact Gateway and Vision module identity through the environment gate.
2. Discover the live OpenAPI document and inventory its current project, scan, export/import, session, module, and diagnostic operations.
3. Record the exact target project and export it before mutation.
4. Define the owned resource names, expected package entries, dependencies, visible result, rollback package, and bounded diagnostic window.
5. Confirm that no unrelated project or resource is in the mutation scope.
6. Classify each owned item before mutation as either a durable review resource or temporary test infrastructure. A newly requested review window is durable by default; handlers, observation/result transports, and owned launcher processes are temporary unless explicitly requested otherwise.

Use both control planes as complementary evidence. Use the official API for backup, project lifecycle, import/export, scan, module health, session observation, and logs when those operations exist. Use an already validated focused `llmImport` operation for each demonstrated OpenAPI gap, and record which plane supplied every read, mutation, and diagnostic result. Do not treat either plane as a reason to skip the other plane's applicable checks.

After importing new project-library dependencies for a project-scoped WebDev resource, separate import completion from script-registration readiness. On the tested 8.3.8 host, an immediate GET raised `ImportError` for a newly added dependency even though later health calls succeeded. A repeated single-cycle test that waited five seconds before the first project-scoped GET then passed shared/project GET parity, fixed no-write POST probes, exact resource readback, and all correlated log gates. Treat five seconds as this fixture's observed bound, not a portable constant: use a bounded readiness policy, preserve the complete interval logs, and reject the import if any registration WARN/ERROR appears. Do not hide the race with an error allowlist or call a later success clean when the full-cycle log window contains the earlier failure.

### Durable Review Baseline

When the user wants created windows left in the Gateway for review:

1. Preserve the pre-action project export as the historical baseline.
2. Build the review window under one deterministic resource path and title.
3. After import and runtime verification, export the project again and define that exact logical resource set as the new durable baseline.
4. Prove every historical logical entry is unchanged. Identify the exact window payload/manifest additions and reject unrelated additions, removals, or executable-resource changes.
5. Remove only temporary Client/Gateway handlers, result transports, observation tags, and owned processes.
6. Re-export and prove the durable review window remains while every named temporary resource is absent.

Do not restore the historical project archive after a successful review-window increment, because that would delete the requested review artifact. If the increment fails before the durable window itself is verified, restore the last approved durable baseline. If it fails after the window is approved but temporary cleanup is incomplete, preserve the window and perform a separately authorized bounded teardown of only the temporary resources.

For owned review tags, use the provider-default tag group unless the design explicitly requires another group. Do not serialize a `tagGroup` override merely to restate the provider default. After every test phase and final cleanup, read the exact retained tag paths and require the expected data types, values, and Good qualities; export their definitions and verify no unintended tag-group override. Treat temporary observation/result tags as separate resources and prove they are absent without deleting the retained sources.

## 2. Build A Native Resource

- Treat the window payload as a native binary resource for the exact tested Ignition build.
- Do not hand-author opaque `data.bin` bytes or infer an 8.3 encoding from an 8.1 filename.
- Use a version-matched serializer or previously validated build capability.
- Keep `project.json` at the package root.
- Pair each native `data.bin` with its `resource.json`.
- Give the window a deterministic resource path and title.
- For a startup primitive, explicitly mark the window open on startup and set a known design size.
- For a tested fixed-bound component, serialize preferred, minimum, and maximum size with its bounds. Bounds alone may reopen at a component default size.
- Use native Vision shape components behind labels when a filled panel is required. One tested native `PMILabel` retained its explicit background, fill/opacity, foreground, font, alignment, bounds, and text through native readback and fresh-client rendering; qualify this rule to that component and exact property set.
- Keep fixed-window and maximized/responsive behavior as separate capabilities. A correct fixed-size result does not validate maximized scaling.
- Keep generated scripts compatible with the embedded Jython version and parse them before import.

Before live import, validate the archive in an isolated extraction:

- exact expected entry set;
- root layout and forward-slash entry names;
- non-empty native payloads;
- resource-manifest presence;
- per-entry hashes;
- no secrets or local development paths.

### Installed-Class Render Preflight

When a tested renderer for the exact installed Vision version is available,
render the exact candidate window before importing it:

1. Deserialize the candidate's native payload with the installed classes and
   paint it at the intended design dimensions.
2. Inspect the complete original-resolution image, not a cropped preview.
3. Require every title, source, state, footer, and expected control to be
   readable and complete. Reject clipping, ellipses that hide required text,
   overlap, out-of-bounds children, unintended default sizes, and ambiguous
   visible identity between projects or windows.
4. Preserve renderer stdout, stderr, and operational log output. Inventory
   every WARN, ERROR, exception, and traceback before using focused searches;
   any unexplained signal rejects the candidate.
5. After a correction, rebuild every durable project, temporary runtime
   project, API candidate, and manifest that embeds the changed window. Rerun
   their exact inventory, hash, native-deserialization, and script checks.

Treat this as an early rejection gate only. A clean offline render proves
that the serialized component tree can be painted by that installed-class
harness; it does not prove Client startup, bindings, qualities, event
delivery, retarget behavior, responsive layout, or live pixels. Keep the
fresh-Client screenshot, state readback, and complete Client/Gateway
diagnostic gates unchanged.

### Validated Blank-Project Storage Map

For one tested seven-file blank project on Ignition 8.3.8, the installed
project tree and an independently retained project export matched exactly by
relative path, byte length, and SHA-256:

```text
project.json
ignition/global-props/data.bin
ignition/global-props/resource.json
com.inductiveautomation.vision/login-properties/data.bin
com.inductiveautomation.vision/login-properties/resource.json
com.inductiveautomation.vision/windows/<window>/data.bin
com.inductiveautomation.vision/windows/<window>/resource.json
```

The two tested Vision manifests used `scope: "C"`; the global-properties
manifest used `scope: "A"`. Each manifest used resource version `1`, named
only `data.bin` in `files`, and paired with that sibling payload. Project ZIP
entries used forward slashes even though the installed Windows tree used
native path separators.

Use this as a discovery and verification oracle for that exact primitive:

- compare the complete logical entry set, sizes, and hashes;
- require each native payload to have its sibling manifest;
- keep archive entry names normalized with forward slashes;
- use the supported project export/import lifecycle for changes.

Do not edit the installed project filesystem or hand-author `data.bin` from
this observation. It does not establish other Vision resource families,
upgraded-project layouts, Designer save behavior, or restart persistence.

### Validated Resource Manifest Families

Across 92 owned manifests in 25 generated-fixture runs, then six successful
official project readbacks, each tested resource family used exactly these
base fields:

```json
{
  "attributes": {},
  "files": ["data.bin"],
  "overridable": true,
  "restricted": false,
  "scope": "C",
  "version": 1
}
```

The exact family-specific contracts were:

| Resource family | Scope | Declared file | Attributes |
|---|---:|---|---|
| Vision window | `C` | `data.bin` | `{}` |
| Vision login properties | `C` | `data.bin` | `{}` |
| Global properties | `A` | `data.bin` | `{}` |
| Vision Client message handler | `C` | `handleMessage.py` | `{"enabled": true, "threadType": "EDT"}` |
| Gateway message handler | `G` | `handleMessage.py` | `{"enabled": true, "threadType": "Shared"}` |

For these tested families:

- require the manifest keys `attributes`, `files`, `overridable`,
  `restricted`, `scope`, and `version`;
- require every name in `files` to exist beside `resource.json`;
- reject an undeclared sibling payload during offline review;
- keep Client EDT work separate from Gateway Shared-thread work;
- compare the manifest and declared-file set again after official readback.

This is a known-good construction and verification contract, not a complete
parser acceptance matrix. Missing files, extra siblings, changed scope,
unknown attributes, other thread types, other resource families, inheritance,
restart, and direct installed-tree edits require separate live evidence.

### PMILabel Property-Persistence Primitive

For one tested native `PMILabel`, serialize and inspect the exact property set instead of treating a screenshot as a complete property oracle. The validated set is component class and name, bounds, text, bold font, foreground and background colors, fill/opacity, horizontal alignment, tooltip text, and three dynamic custom properties: primitive Boolean, primitive Int4, and `java.lang.String`.

Use a two-state test when changing a property:

1. serialize and deserialize both states with the exact installed Vision runtime;
2. compare decoded semantic snapshots and require the intended property-only diff;
3. import, scan, and export each state, checking the retained window-resource hash;
4. launch a fresh client for each visible state and review both screenshots;
5. inspect bounded diagnostics;
6. restore the exact pre-test project and compare every logical archive entry.

Do not require independently generated binary resources or ZIP containers to have identical hashes. Native serialization may preserve the same decoded semantics while producing different bytes across processes. Use the hash of the exact retained fixture for live readback. Treat tooltip text as structurally persisted unless a separate hover test produces a valid visual capture, and do not claim Designer close/reopen persistence from a Gateway import/export plus fresh-client test.

### Surgical Edit of an Existing Window

For a narrow request on an existing customer window, mutate the exact retained
resource instead of rebuilding the window from a template or broad generator.
Treat unknown properties, formatting, adapters, scripts, and dependencies as
content to preserve.

1. Export and pin the current logical project inventory, target payload, and
   target metadata before editing.
2. Deserialize the exact target with the installed Vision runtime. Guard the
   expected component identity, current property or script value, and every
   dependency the requested behavior uses. Stop on drift rather than replacing
   missing content or overwriting unfamiliar logic.
3. Freeze the field-level change plan and rollback source. Apply only the
   reviewed property or adapter change; do not broadly regenerate the Window
   for a small edit.
4. Read the candidate back and compare every logical project entry. Require all
   unrelated entries and unmodified metadata to remain identical, then compare
   decoded component and script snapshots and require exactly the intended
   semantic paths.
5. Render before and after in isolated fresh processes or Clients. Localize the
   visual difference to the intended component bounds and inspect every other
   region for geometry, formatting, native-component, or quality drift. A
   shared renderer can retain native UI state, so do not accept an apparent
   difference until an isolated rerun confirms it.
6. For live credit, use a guarded import, launch a fresh owned Client, exercise
   the changed behavior, verify the target Window and session, inspect complete
   correlated Client and Gateway logs, and exercise the pinned rollback. Any
   extra semantic delta, WARN, ERROR, exception, missing dependency, or
   incomplete observability disqualifies the candidate.

Retain requested review Windows. Remove only explicitly temporary handlers,
tags, or fixtures, and verify the final retained and removed inventories.

### Cross-Project Adaptation Gate

Treat reuse in another project as an explicit dependency substitution, not a
copy-and-rename operation. Before generating resources, freeze a source
manifest and a target contract covering at least the project parent,
tag/alarm/history providers and paths, database, inherited template paths,
navigation targets, theme tokens, and every supported display profile.

1. Pin the exact qualified source archive and the payload hashes of each reused
   Window, template, script, and metadata resource.
2. Give every source assumption one explicit target value. Stop if the target
   contract omits a dependency or if a source value would be silently reused.
3. When inheritance is required, build and validate the parent and child as
   separate native projects. Keep inherited resources in the parent and the
   child parent link explicit; do not hide a missing parent by duplicating its
   template into the child.
4. Retain a real target database or Named Query resource where database use is
   part of the design. A label that merely names a database is not dependency
   evidence and never proves query execution.
5. Scan the complete target archive for the frozen source-only provider,
   database, tag root, history, template, and navigation values. Any match must
   be explained or must reject the candidate. Do not use a broad search for
   words such as `default`; compare the exact frozen dependency strings.
6. Render every retained target Window independently at each declared target
   geometry. Inspect the real native chart/table/template areas, text, bounds,
   and boundary banners. Preserve rejected renders and all created Windows.
7. Keep offline construction credit separate from live portability. Live
   credit requires official import/readback, a fresh owned Client with the
   parent mounted, target provider/database/history execution, navigation,
   actual display-profile launches, recovery behavior, and complete correlated
   Client and Gateway logs.

An isolated renderer may not resolve an inherited template instance because
the parent project is not mounted. That empty region is an explicit offline
boundary, not evidence that inheritance works or fails in a Client.

### Direct Tag Binding Primitive

The tested direct-binding increment uses one `PMINumericLabel` target and one one-way `SimpleBoundTagAdapter` whose source is the fully qualified read-only tag `[System]Gateway/UptimeSeconds`. The adapter targets the component's `value` property, declares a numeric value class, disables bidirectional writes, and retains a bounded fallback delay. Serialize the adapter map as part of the native window rather than treating the visible value as static component content.

Distinguish JavaBean properties from Vision dynamic properties when configuring an adapter:

- a native JavaBean property such as `text` uses the normal setter path and must not be marked dynamic;
- a target created through `DynamicPropertyDescriptor` must set the adapter's `targetPropertyDynamic` flag;
- require the flag to survive native serialization/deserialization and exercise the installed setter path before import.

An 8.3.8 Client showed why this is a runtime gate: a `SimpleBoundTagAdapter` pointed at a dynamic custom property while its dynamic-target flag was false. The descriptor and adapter both survived offline round-trip, but Client startup reported that no property setter could be found and the underlying `DynamicPropertyDescriptor` could not be cast to a JavaBeans `PropertyDescriptor`. An installed-runtime setter test with the flag true updated primitive byte, short, long, and float dynamic values; the same adapter type kept the flag false for a native `text` property. This installed-runtime result is not live subscription or rendering credit. Require a corrected fresh-Client run with no related Client error before promoting those bindings.

For a bounded forward test:

1. Seed the numeric target with an unmistakable sentinel.
2. Launch a fresh client and wait for the final project/window title.
3. Read the exact source tag through a validated read-only interface near the screenshot time.
4. Capture the displayed value.
5. Wait for a known-changing source, read it again, and capture a second frame.
6. Require both source reads to have Good quality, the later source value to change, and each displayed value to match its adjacent source observation.
7. Confirm that the binding remains one-way and that no tag write was attempted.

This establishes a narrow initial/update visual propagation primitive. The separately tested five-type matrix also propagated one-second Good updates in one retained client for Boolean to `PMICheckBox.selected`, Int4 to `PMISpinner.intValue`, Float8 to `PMISpinner.doubleValue`, String to `PMITextField.text`, and DateTime to `PMIDateTimePopupSelector.date`. It does not establish the full binding contract. Keep the result partial until remaining standard tag types, programmatic component value/type/quality snapshots, additional bad/stale qualities, provider/network disconnect, restart, and Designer close/reopen have their own evidence.

For a quality-aware numeric control, keep the adapter's quality overlay enabled and test a deliberate missing source beside a Good control. On the tested 8.3.8 client, one missing source reported `Bad_NotFound` through the read interface and rendered a patterned value area, diagonal corner, and red-X marker. Its numeric sentinel remained visible beneath the overlay. Therefore:

- treat the displayed number and the quality indication as separate evidence;
- never interpret a retained or sentinel number as Good quality;
- keep a known-Good control in the same fresh-client run;
- correlate each screenshot with exact source quality readback;
- qualify this visual rule to the tested component and quality code.

Do not claim recovery from a steady missing-source comparison. Prove recovery separately by making a controlled source transition, observing bad then Good quality without reopening, and retaining component/source snapshots and diagnostics.

The tested recovery increment removed and recreated one owned Float8 source while the same client remained open. The component began at Good value `10`, retained `10` beneath the `Bad_NotFound` overlay after source removal, and returned to unoverlaid Good value `10` after recreation. Use this recovery oracle:

1. Record the client process identity and initial Good source/value.
2. Capture an unoverlaid initial frame.
3. Make one controlled, reversible source-unavailable transition.
4. Poll source readback until the intended bad quality appears.
5. Capture the overlay while proving the client process did not change.
6. Restore the exact source through a validated lifecycle operation.
7. Poll source readback until the intended Good value returns.
8. Capture the cleared overlay while proving the same client remains responsive.
9. Keep an independent changing Good binding visible throughout.
10. Inspect the complete action log window and restore or intentionally retain owned state.

Qualify the claim to the transition actually exercised. Exact tag deletion/recreation proves subscription recovery from source disappearance; it does not prove provider, network, device, or database reconnection behavior.

### Locale And Longest-Translation Gate

Treat localization as a separate visual and runtime increment. A clean
default-locale render does not qualify another locale.

1. Inventory the supported locales and the exact translation keys used by the
   Window.
2. Choose the longest realistic translation for every critical title,
   instruction, button, table heading, alarm message, and status value.
3. Exercise each locale separately and preserve its translated values,
   locale-sensitive number/date values, and full-window screenshot.
4. Test both the intended non-strict missing-term fallback and a strict miss
   where the design relies on it. Make the fallback recognizable rather than
   silently substituting unrelated text.
5. Reject clipped, overlapping, ellipsized, or encoding-corrupted text. Fix
   the component geometry or wrapping policy, then repeat every affected
   locale.
6. Repeat the complete Client and Gateway diagnostic gate for locale changes,
   restart, and retarget. A deterministic offline preview is an early geometry
   check only; it does not prove translation-database lookup, expression
   reevaluation, alarm/table localization, or Client persistence.

### Touchscreen Keyboard And Keypad Gate

Treat touchscreen input as a Client-runtime behavior layered on native input
components. A clean field render does not prove that the keyboard or keypad
can open, return a value, cancel, or preserve focus.

1. Use a native `PMITextField` or `PMINumericTextField` property with a real
   JavaBean getter/setter. Do not route the touchscreen listener through an
   unqualified dynamic-property descriptor.
2. On the tested Vision 12.3.8 runtime, touchscreen mode `0` ignores touch
   editing, `1` opens on one click, and `2` opens on a double click. Preserve
   and read back the exact mode.
3. For explicit scripts, use `system.vision.showTouchscreenKeyboard` for text
   and `system.vision.showNumericKeypad` for numeric values. Treat a `None`
   result as cancellation and leave the prior value unchanged.
4. Convert and range-check numeric results before assigning the native
   `intValue` or `doubleValue` property. Keep the component's native
   min/max/bounds configuration as a second independent guard.
5. Inventory keyboard layouts and screens at runtime. Test the project
   touchscreen settings and keyboard-width property, default and intended
   custom layouts, repeated focus, secondary-monitor placement, and restart.
6. Never log entered text, passwords, or numeric values merely to prove the
   dialog worked. Preserve only bounded acceptance/cancellation status.
7. Inspect the complete owned-Client and Gateway diagnostic windows. Any
   setter lookup, binding, descriptor cast, focus, layout, serialization, or
   modal exception blocks acceptance even when the dialog or Window looks
   correct.

Offline native deserialization and a full-window render are useful preflight
gates only. Keep touchscreen behavior partial until a fresh Client exercises
accept, cancel, invalid input, repeated focus, the intended monitor/layout,
restart, screenshots, and every required diagnostic plane.

### File Export, Capture, And Print Gate

Treat file dialogs and output functions as Client-local user operations. Do
not expose a caller-selected filesystem path through a remote API merely to
make a test easier.

1. Use `system.vision.openFile`, `saveFile`, and the `exportCSV`,
   `exportExcel`, or `exportHTML` function appropriate to the intended format.
   Treat a `None` result as cancellation and create no file.
2. Use a fixed, bounded dataset whose schema exercises the types and text that
   matter. Include null, Unicode, commas, quotes, and HTML-like text when those
   cases are supported, then inspect the produced bytes rather than trusting
   the API return value.
3. Keep the destination user-selected or constrained by a separately tested
   local allowlist. Do not log or return local paths unnecessarily, and do not
   auto-open the result as proof.
4. For image capture, obtain the destination first and call
   `system.vision.printToImage` only after acceptance. Verify file existence,
   format signature, dimensions, nonblank pixels, and hash.
5. For printing, retain the system print dialog unless a named noninteractive
   target has been explicitly approved and tested. Verify the selected target
   or spool artifact; `job.print()` returning is not sufficient proof.
6. Test cancel, existing-file overwrite, invalid and denied destinations,
   empty selection, and a bounded large dataset. Require no partial artifact
   after every failed or canceled operation.
7. Inspect the complete owned-Client and Gateway diagnostic windows. Any
   encoding, workbook, filesystem, permission, image, print, spool,
   serialization, setter, or UI exception blocks acceptance.

Use ASCII-safe Unicode escapes in generated Jython fixtures when source-file
decoding is not independently controlled. Validate exact resulting code
points and inspect the rendered pixels; comparing output to constants loaded
through the same source path can reproduce the same corruption and create a
false pass.

## 3. Apply Through Supported Project Lifecycle

1. Capture a pre-action Gateway diagnostic baseline.
2. Import the reviewed project package through the documented project API.
3. Request or await project scan completion with a bounded timeout.
4. Export the project immediately after the scan.
5. Compare the exported logical entry set and decisive content hashes with the intended fixture.
6. Confirm no unrelated project changed.

Do not require the pre-import and post-import ZIP files to be byte identical. Archive timestamps or packaging metadata may differ even when every logical project file is restored exactly.

## 4. Verify Independent Evidence Planes

Do not let one successful response stand in for the whole result. Collect the planes required by the claim:

| Plane | Minimum evidence |
|---|---|
| Structure | Exported resource paths, entry count, manifests, and hashes |
| Runtime | Client process started, remained responsive, and showed the expected project/window identity |
| Visual | Screenshot captured from the intended client and reviewed against an explicit expected result |
| Diagnostics | Bounded Gateway, launcher, and client-relevant logs with baseline/action correlation |
| Session | Supported session readback when available and functioning |
| Restoration | Owned client/temp state closed, durable review resources retained, and exact approved-baseline readback |

If a session or diagnostic endpoint returns an error, retain the failure and classify the plane as unavailable. Do not convert an endpoint failure into “no sessions,” “no errors,” or a clean diagnostic result. Use other independent planes, but keep the limitation explicit.

For every owned Client run, inspect all available Client-side error planes, not just Gateway logs:

1. capture any modal error dialog before it is dismissed, including its Details text when available;
2. preserve the complete owned-Client log window from process start through close;
3. correlate each error to the project, window, component/property path, and test phase;
4. inspect Gateway WARN+ separately because a Client-only failure may not appear there;
5. treat any unexplained Client exception as a failed gate for the affected behavior, even when screenshots render and the Gateway action reports success;
6. after correction, use a fresh Client and require the prior error signature to be absent across the whole run.

This inspection is mandatory on every run, including runs whose API envelope, tag readback, session result, and screenshots all pass. Inspect the complete correlated time window before declaring the resource correct. Do not sample only the expected logger or search only for a known error string: first inventory every WARN/ERROR/exception on each available process plane, then use focused filters to correlate the target resource and action. If a required plane is unavailable or its time window is incomplete, record an observability gap and keep the result nonclean. Never replace log evidence with an assumption that a visually correct window is internally healthy.

## 5. Iterate One Capability At A Time

Advance in small increments:

1. blank startup window;
2. fixed-window static label and native-panel display;
3. layout and resize behavior;
4. direct tag binding and quality behavior;
5. navigation and multiple windows;
6. component event scripts;
7. reusable templates and data-driven components.

For every increment:

- state the one new behavior being tested;
- preserve the prior passing fixture as the control;
- add a negative or malformed control where practical;
- import, scan, export, launch, inspect, and diagnose again;
- promote only the behavior actually observed;
- retain the verified review window, remove temporary test infrastructure, and record the new approved durable baseline for the next increment.

## 6. Completion Decision

Call an increment passed only when:

- the native package contract passes offline;
- the live import and scan succeed;
- export readback contains the intended logical resources;
- the client is responsive and the expected window is visually confirmed;
- the screenshot was captured after the final project/window title appeared, not from a transient launcher state;
- fixed-bound components are not clipped, reset to default sizes, or shifted by an untested layout mode;
- no unexplained new warning or error appears in the bounded diagnostic window;
- session evidence is present or its unavailability is explicitly qualified;
- the retained review window and owned source tags match the approved durable baseline, and every named temporary resource is absent.

Keep a result partially passed when a required plane such as restart comparison, clean shutdown, session registration, or diagnostics is missing or failing, even if the screenshot looks correct.

### Client State, Lock, And Read-Only Gate

Treat these as independent state planes:

- connection mode: `1` disconnected, `2` read-only, `3` read/write;
- screen lock: unlocked, visibly locked, or opaquely locked;
- project authorization: authenticated identity, roles, permissions, and
  component security.

Never describe read-only mode as authorization or a locked screen as logout.
Before a mode or lock test, capture the initial mode and lock state. Restore
the captured mode after the test. Do not expose a disconnected-mode control
until reconnect behavior and recovery time are independently qualified.

For read-only acceptance, test provider-tag reads/subscriptions and SELECT
separately from provider-tag writes and INSERT/UPDATE/DELETE. Test ClientTag
writes and navigation/UI edits as separate cases rather than inferring their
behavior from provider tags. Correlate every action with the complete owned
Client log, modal error details, and Gateway WARN+ window. Identity snapshots
should use presence or counts unless the evidence contract explicitly
requires values; never log usernames, roles, Client IDs, or addresses merely
for diagnostics.

### Fallback And Disconnection Recovery Gate

Do not collapse these mechanisms into one claim:

- connection mode `1` is a Client-side disconnected mode that disables tag
  and query features;
- a Vision Client Launcher fallback application is selected only after its
  configured retries are exceeded;
- local Client fallback uses a local Gateway, requires port 6501, and requires
  a published fallback project with at least one main window.

A connection-mode simulation is not proof of cable loss, Gateway loss, or
local fallback. Local Client fallback does not automatically transfer back to
the main Gateway; require a tested explicit return mechanism when automatic
recovery is desired.

For a real fallback test, preserve five correlated phases: baseline, loss,
fallback, restore, and recovered. At every phase capture the visible project
identity, project version, representative values and qualities, navigation,
fixed safe write attempts, screenshots, complete owned-Client logs, and
Gateway logs. Treat cached values as stale unless their freshness is
independently established. Pass only when return to the authoritative project
is explicit and no hidden stale state remains. Never stop a Gateway or change
network state without a separately authorized, bounded recovery plan.

## Five evidence-plane gate

Do not treat any one validation plane as universal. For each retained Vision
Window, correlate all five:

1. **Structure** — inspect the serialized component tree, property adapters,
   action adapters, dynamic-property descriptors, and resource metadata.
2. **Dependency** — prove every Window, Template, tag, query, script module,
   image, and project-library reference exists and matches its expected scope.
3. **Runtime** — use a fresh owned Client to execute the bounded fixed action
   and query the resulting component/session state.
4. **Visual** — inspect screenshots at the intended dimensions for clipping,
   overlap, alignment, containment, readability, and state identity.
5. **Logs** — inspect the complete correlated Client and Gateway interval,
   including WARN and ERROR records and known setter, descriptor-cast,
   ClassCastException, PropertyDescriptor, and NullPointer signatures.

A clean screenshot cannot clear a broken dynamic-property adapter, an absent
navigation target, or an event exception. Conversely, clean structure and
runtime evidence cannot clear a visual overlap. Preserve a valid control and
one-defect-at-a-time negative variants when testing the gate. If any image or
log exposes an unrelated defect, reject that build, preserve its evidence, and
iterate before promotion.

## Keep process logs separate

Treat Gateway, Designer, Vision Client Launcher, and Vision Client output as
four different process sources. A healthy Gateway log does not prove a healthy
Client, and Designer console output is not a launched Client log.

For each captured record preserve:

- source process and PID;
- timestamp and timezone;
- logger or stream and thread;
- project and action or Window identity;
- Client session or launcher identity when applicable;
- one stable test or request ID;
- file/segment name and ordering when logs rotate;
- completeness and truncation metadata;
- redacted message and stack information.

Require a fixed expected error to appear only in its intended source capture.
Search the other sources explicitly instead of assuming absence. When a log
rotates, include the predecessor segment or mark the capture incomplete. When
response limits omit records, record the omitted count and block a clean
claim. Preserve the authoritative launcher exit code separately from wrapper
stdout/stderr. Never copy credentials, authorization values, tokens, session
secrets, or private keys into retained logs.

## Make screenshots attributable

Do not accept a bare image as proof of a Vision result. Pair every screenshot
with:

- Gateway/project and exact Window or Template identity;
- selected Client PID and session identity for live captures;
- user, locale, state marker, resolution, and DPI;
- capture scope and supported method;
- capture timestamp and timezone;
- image SHA-256 and relevant source-resource or archive SHA-256;
- expected component or state identity;
- selection trace when multiple similar Clients exist.

Require visible identity and metadata to agree. Reject an image paired with
another Window's identity, a stale source hash, a missing timestamp, ambiguous
Client selection, unexpected dimensions, or a state marker that does not match
the tested phase. Record minimized, covered, unavailable, and closed-client
captures as explicit negative results instead of silently accepting a stale or
blank image. Screenshot capture must not drive or alter a user-owned Designer.

## Use visual automation as decision support

Save the exact image regions, thresholds, source-image hashes, and detector
version with every automated visual result. Useful bounded checks include:

- blank-image variance and color-count checks;
- required-component region comparison;
- overlap-marker or geometry checks;
- content at an expected offscreen boundary;
- clipping-region comparison against an accepted reference;
- required color/state markers and required text structure.

Seed each critical defect and preserve the false-positive and false-negative
report. If a threshold changes, retain the failed attempt, the measured value,
the reason for the correction, and the accepted rerun. A threshold tuned to a
fixed corpus is not a universal pixel-equivalence rule.

Allow small antialiasing, font-rasterization, DPI, and look-and-feel variance
when structure, meaning, and readability remain intact. Require manual review
of the complete image for semantic correctness, clipping, alignment,
containment, state identity, and unexpected content. An automated pass cannot
replace the mandatory Client/Gateway error-log gate or human sign-off. Record
whether the reviewer was independent and blind; do not claim blind review when
the reviewer knew the seeded labels.

## Preflight substantial project updates

Before importing a substantial generated update, build it deterministically
from the last approved logical payload map. For every added project-library
resource require the expected code/metadata pair, parse the metadata, compile
the code with the target Jython runtime, read the complete archive back, and
prove every pre-existing payload is unchanged. Rebuild the same input and
compare its logical entries and payload hashes. Include negative controls that
remove one paired file and alter one baseline payload; both must be rejected.

Local ZIP build, readback, and validation timings are preflight costs only.
They do not establish a safe Gateway import size, live update duration, memory
envelope, or Client reliability limit. Determine a live envelope only through
separately authorized increasing-size imports. At each size verify:

- exact official import and project-resource readback;
- update behavior and interaction in an already-open owned Client;
- complete owned-Client and Gateway diagnostic windows;
- a clean fresh-Client restart with no stale resource or missing-setter fault;
- exact rollback and temporary-resource cleanup after any failure.

Stop increasing size at the first incomplete observation, unexplained
WARN/ERROR, stale resource, missing entry, interaction failure, or rollback
failure. Preserve the failed size and report the last fully proven live size;
do not hide a failure by extending waits or quoting the faster local preflight.

## Preserve resources under concurrent configuration changes

Snapshot every target resource and its current signature before mutation.
Serialize operations against the same resource. Parallelize separate-resource
work only when each actor has a distinct target and the exact signature it
observed. Treat stale signatures, already-existing creates, and occupied rename
targets as explicit conflict outcomes; never silently overwrite the winner.

Stage a complete replacement before committing it. An interrupted operation
must leave either the complete old resource or the complete new resource,
never a partial resource. Verify recovery by retrying from a fresh snapshot.
Preserve all valid resource attributes, including unfamiliar extension
attributes. A serializer that keeps only known fields is destructive; include
an attribute-dropping negative control and require it to fail.

An offline threaded store can test scheduling and conflict invariants, but it
does not prove Gateway persistence. Live acceptance requires separately
authorized Designer/API actors, official export and exact resource readback,
restart persistence, actor-attributed observations, and complete correlated
Client/Gateway WARN/ERROR inspection.

## Derive performance guardrails from contextual distributions

Never promote one elapsed time into a universal Vision timeout. Record the
Gateway and Vision versions, JVM, OS, processor and memory context, project
identity, workload size, cache state, Client launch mode, and sample count.
Measure cold and warm runs separately. Report at least median and upper
percentiles, plus failures and outliers; retain the raw observations.

Distinguish process start, session registration, startup-ready, first
meaningful paint, and interaction-ready. Measure navigation, binding/query
settlement, table/chart load, repeater creation, and message-bridge latency as
separate workloads. Monitor EDT heartbeat and Client/Gateway CPU, memory, and
log rate over the same correlated interval. Include a bounded blocking
negative so heartbeat monitoring is proven capable of detecting an
unresponsive UI.

Set bounded waits from the matching workload and hardware distribution with
explicit headroom. Re-measure after project, hardware, JVM, module, dataset, or
launch-profile changes. Local archive, serialization, or synthetic Swing EDT
benchmarks validate the harness only; they cannot establish Vision Client or
Gateway performance.
## Skill-versus-control claim gate

Do not claim that the skill improves Vision work from skill-conditioned runs
alone, a single control, historical tasks with different tools, or evaluator
impressions. Before comparing conditions, freeze the exact model build,
reasoning setting, task text and order, operation limits, tool access, runtime
environment, scoring rubric, primary endpoint, and safety margin.

Use multiple paired replicates with a fresh isolated context and workspace for
every run. Randomize condition order, hide condition and skill-identifying
metadata from independent reviewers, adjudicate disagreements, and retain
passes, failures, timeouts, repairs, complete diagnostics, and unintended
changes in the dataset. Never discard a run because it weakens the result.

Report the paired effect with uncertainty and task-level weak areas. Require a
precommitted meaningful-improvement threshold and show that safety is not
worse within the fixed margin. When control runs, repeated skill runs, blinded
scores, correlated logs, or the uncertainty analysis are missing, report the
comparison as incomplete and make no superiority or release claim.
