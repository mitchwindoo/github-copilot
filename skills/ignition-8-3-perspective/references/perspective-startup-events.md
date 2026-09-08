# Perspective view startup events

Use this workflow only after inspecting a live Ignition 8.3 view seed on the target build. Preserve the surrounding view-resource shape and treat other lifecycle events as separate contracts.

## Contents

- [Tested serialization](#tested-serialization)
- [Causal validation gates](#causal-validation-gates)
- [Mounted resource revision behavior](#rerun-after-an-exact-mounted-view-resource-revision)
- [Runtime parameter changes](#runtime-parent-to-child-input-changes)
- [Dynamic path replacement](#dynamic-embedded-view-path-replacement)
- [One-String handoff](#dynamic-child-string-parameter-handoff)
- [Two-String painted boundary](#two-string-painted-handoff-boundary)
- [Nested object input and mutation](#nested-string-object-input-and-mutation)
- [Three-String list input and mutation](#three-string-list-input-and-mutation)
- [Structural String-list append and pop](#structural-string-list-append-and-pop)
- [Missing child recovery](#dynamic-missing-child-and-recovery)
- [Shutdown lifecycle](#dynamic-child-shutdown-on-replacement-and-page-close)
- [Controlled shutdown failure](#controlled-synchronous-shutdown-failure)
- [Same-page route replacement](#same-page-route-replacement)
- [Boundaries](#boundaries)

## Tested serialization

A tested view-level system startup script is stored beside the view's custom properties, parameters, props, and root:

```json
{
  "custom": {
    "status": "NOT_STARTED"
  },
  "events": {
    "system": {
      "onStartup": {
        "config": {
          "script": "\tprevious = self.custom.status\n\tself.custom.status = \"STARTED\""
        },
        "scope": "G",
        "type": "script"
      }
    }
  }
}
```

The tested script executed synchronously on a naturally fresh primary-view mount and changed property-bound visible view custom state. Keep Jython indentation and string escaping exact in the JSON resource.

## Causal validation gates

1. Store a deterministic baseline that differs from the expected runtime result. Export and verify both the baseline and exact event object.
2. Before client launch, use official Perspective session reads to establish that the target resource is not already mounted.
3. Create a new browser page and open the retained route. Do not use project import, continued mounted-view presence, or a pre-existing page as startup evidence.
4. Require unique painted baseline/result markers that jointly show the transition, positive in-viewport geometry, no overflow, a screenshot, and a clean browser console.
5. Correlate one exact mounted resource through official session, page, and mounted-view reads. Reconcile component and binding counts; treat session script metrics as supporting evidence, not as the visible result.
6. Require unchanged project content during runtime, stable supporting APIs, a clear scan lock, bounded clean Gateway logs, and session cleanup after closing the browser page.

## Rerun after an exact mounted-view resource revision

For the tested primary root view, an exact whole-project import that changed only its mounted `view.json` reran `events.system.onStartup` even though the official Perspective session ID, page ID, route, resource path, mount path, component count, and binding count stayed unchanged. Restoring the first exact `view.json` revision through a second import reran startup again.

Do not infer this from session script counts or client-local custom state alone. Use an external, dedicated test value:

1. Create one bounded memory tag beneath the caller-approved test namespace through the official tag-import endpoint. Use collision policy `Abort`, verify an independent missing-path precondition, require an empty failure list, then read and export the exact created tag.
2. When the official API has no general value-write operation, use the optional caller-scoped API only after its health response advertises the write action. Require an authorized dry run, a verified apply, exact readback, and a fixed allowed prefix to reset the counter.
3. Use the same guarded startup script in both complete project revisions. The script should read the fixed counter, require Good quality and a bounded integer, write exactly `current + 1`, require Good write quality, verify the post-write value, and place the verified count into a visible String status property.
4. Also bind a visible component directly to the counter so the painted external value is independent of the status property assigned by the script.
5. On the fresh initial mount, require external value 1, visible status 1, direct-bound value 1, and official session script count 1.
6. Import the second exact project revision without navigation, reload, or client interaction. Require exact project readback, the second static revision marker, external/status/direct-bound value 2, and script count 2.
7. Restore the first exact revision while the same page remains mounted. Require exact readback, the first marker, external/status/direct-bound value 3, and script count 3.
8. Leave the dedicated tag at the declared final evidence value; do not silently reset or delete it after the audit.

This exact 1 → 2 → 3 external sequence proves the tested startup event reran after both mounted-root-view resource revisions. Stable session/page IDs do not prove startup was skipped. Each tested live import also emitted the browser warning documented in [project-view-route.md](project-view-route.md); preserve it as an expected-warning boundary rather than calling the run console-clean.

### Byte-identical embedded child under a parent-only revision

A separate test used one primary parent and one static-path embedded child, each with its own dedicated external Int4 startup counter, guarded startup increment, verified visible status, and direct counter binding. Complete project revisions A and B differed in exactly one entry: the parent `view.json`. The child `view.json` and companion `resource.json` were byte-identical.

The natural mount produced parent/child external counters 1/1 and aggregate session script count 2. Importing parent revision B without navigation or reload produced 2/2 and script count 4. Restoring parent revision A produced 3/3 and script count 6. Parent and child resource paths, mount paths, component counts, binding counts, session ID, and page ID stayed stable throughout.

Use separate counters and require exact revision-diff proof. A shared counter cannot establish that both scripts ran, and mounted-view identity/counts cannot establish lifecycle continuity. Require:

- missing-path preconditions and official tag import/export for both dedicated counters;
- one health-gated optional write dry run and verified reset scoped only to the two counters;
- exact A/B entry maps whose sole difference is the parent `view.json`;
- byte-identical child view/resource entries;
- independent Good parent and child reads at 1/1, 2/2, and 3/3;
- two visible verified-status Strings plus two direct-bound values at every state;
- official parent and child mount correlation and aggregate script counts 2, 4, and 6;
- exact final parent revision, declared final counter values, classified browser warnings, bounded logs, lock, route, and cleanup.

This proves the tested byte-identical child startup reran when its parent resource was revised. It does not identify every internal remount/replacement mechanism or establish deeper nesting, multiple children, dynamic child paths, parameter-only changes, other lifecycle events, partial imports, multiple sessions, Designer scope, reconnects, failures, redundancy, or timing.

### Byte-identical parent under a child-only revision

A complementary test kept the parent `view.json` and companion resource byte-identical while complete project revisions differed only in the mounted static-path child's `view.json`. The parent and child again used separate dedicated external counters, guarded startup increments, visible verified statuses, and direct counter bindings.

The natural mount produced parent/child counters 1/1 and aggregate script count 2. Importing child revision B without navigation or reload produced 1/2 and script count 3. Restoring child revision A produced 1/3 and script count 4. The parent resource path, mount path, component/binding counts, session ID, and page ID remained stable.

Use the same independent-counter and exact-diff gates as the parent-only test, but require these asymmetric outcomes:

- the sole A/B entry difference is the child `view.json`;
- both parent files and the child companion resource are byte-identical;
- independent Good reads progress parent `1 -> 1 -> 1` and child `1 -> 2 -> 3`;
- visible verified statuses and direct-bound values match those independent reads;
- aggregate script count progresses `2 -> 3 -> 4` with zero reconnects;
- final project is exact restored A, and the retained counters have the declared final values.

This proves that, for the tested direct static-path composition, a mounted child-only resource revision reran the child's startup without rerunning the byte-identical parent's startup. It does not prove internal implementation details, precise timing, parameter-only changes, dynamic paths, siblings, deeper nesting, partial imports, failures, reconnects, or other lifecycle events.

### Runtime parent-to-child input changes

For one tested direct static-path composition, a parent property binding fed one persistent String input parameter on the embedded child. Two unique guarded Button events changed only the live parent property from A to B and restored A. No project import, route change, navigation, reload, or tag write occurred after the natural mount.

The parent and child parameter displays agreed at A, B, and restored A. Separate parent and child startup counters remained 1/1 throughout. Aggregate script count progressed `2 -> 3 -> 4`, accounting for the two startup scripts and then one script per Button event; aggregate expression count progressed `2 -> 3 -> 4` as the child parameter display reevaluated. Exact project entry maps, session ID, page ID, mount paths, component/binding counts, and zero reconnects stayed unchanged.

To validate this boundary:

1. Use separate external startup counters for parent and child and establish a verified zero baseline before natural mount.
2. Bind one parent custom property into one declared persistent child input parameter; display the parent source value and child received value independently.
3. Use unique guarded controls that accept only the expected A -> B -> A sequence and assign only live view state.
4. Export the project before mount and after every interaction; require byte-identical entry maps.
5. After each painted transition, independently read both counters and require them to remain at 1, correlate only the expected Button-script and parameter-expression metrics, and require stable session/page/mount identity with zero reconnects.
6. Capture each state at the approved viewport, verify positive control geometry, require empty browser consoles and bounded Gateway logs, then verify final tags, route, lock, and cleanup.

This proves that the tested ordered runtime String-input propagation did not rerun startup on either the parent or child. It does not prove arbitrary parameter types, rapid or concurrent assignments, dynamic child paths, sibling or deeper composition, bidirectional parameters, reconnects, reloads, navigation reuse, failure timing, or other lifecycle events.

### Dynamic Embedded View path replacement

For one tested Embedded View, `props.path` used a property binding to a parent custom String. The initial value selected known Good child A. Unique guarded Button events selected known Good child B and restored A without project import, route change, navigation, reload, or tag write.

The painted and official mounted-child sequence was A -> B -> A at the same embedded mount path. Separate external counters progressed:

- parent: `1 -> 1 -> 1`;
- child A: `1 -> 1 -> 2`;
- child B: `0 -> 1 -> 1`;
- aggregate scripts: `2 -> 4 -> 6`.

Each path change accounted for one guarded Button script and one startup script on the newly selected child. Returning to child A created a fresh child-A instance and reran its startup. Parent startup did not rerun; the parent mount, session ID, page ID, component/binding counts, project entry map, and zero-reconnect state stayed unchanged.

To validate this behavior:

1. Retain two distinct known Good child resources and instrument the parent and both children with separate dedicated external startup counters.
2. Bind the Embedded View `props.path` to one parent property initialized to child A; display the selected path state and each child's unique identity.
3. Use unique guarded controls that allow only the expected A -> B -> A sequence and assign only live parent state.
4. Require independent counter reads and official mounted-view reads after every painted state. Verify the selected child resource changes at the same mount path while the parent mount remains stable.
5. Reconcile aggregate scripts as Button plus selected-child startup executions, require exact project maps throughout runtime, and require stable session/page IDs with zero reconnects.
6. Capture screenshots and control geometry, require empty browser consoles and bounded Gateway logs, and verify final tags, route, lock, and cleanup.

This proves Good-path dynamic replacement and selected-child startup only for the tested pair. It does not prove nonexistent or invalid paths, shutdown events on the replaced child, parameters beyond the separately tested exact String handoff sequence, siblings, nested dynamic views, rapid switching, caching guarantees, reconnects, reloads, navigation reuse, or failures.

### Dynamic child String-parameter handoff

One tested extension combined the property-bound Embedded View path with one property-bound persistent String input parameter declared identically on two known Good children. The parent began with child A and `ALPHA`, changed only the live parameter to `BETA`, replaced A with B while retaining `BETA`, changed only the live parameter to `GAMMA`, then replaced B with A while retaining `GAMMA`.

The painted and official mounted sequence was A/ALPHA -> A/BETA -> B/BETA -> B/GAMMA -> A/GAMMA. Separate parent/A/B startup counters progressed `1/1/0 -> 1/1/0 -> 1/1/1 -> 1/1/1 -> 1/2/1`. Aggregate scripts progressed `2 -> 3 -> 5 -> 6 -> 8`: same-child value changes added only the guarded Button script, while each path replacement added the Button script plus the incoming child's startup. Aggregate expressions progressed `2 -> 3 -> 4 -> 5 -> 7`; the newly mounted final A produced two observed expression executions before settling.

To validate this boundary:

1. Declare the same persistent input parameter and `paramDirection: "input"` on both children. Bind the parent's Embedded View `props.params.<name>` to one parent property and `props.path` to a separate parent property.
2. Display the parent source value and each selected child's received parameter independently. Use distinct child identities and separate external startup counters.
3. Use unique guarded controls for an exact value-change -> path-change -> value-change -> path-change sequence. Assign only live parent state after natural mount.
4. After every painted state, require exact parameter agreement, the expected external counters, official mounted-child resource path, aggregate script/expression counts, the same session/page, and zero reconnects.
5. Require byte-identical project entry maps throughout runtime, positive control geometry, 1280x720 screenshots, empty browser consoles, zero unexpected WARN-or-higher Gateway logs, route success, a clear scan lock, and browser-session cleanup.

This proves current-value handoff only for one synchronous String input, two direct known-Good children, and the exact ordered sequence above. It does not prove output or bidirectional parameters, other parameter types, absent/malformed/unauthorized paths, rapid or concurrent value/path changes, parameter counts beyond the separately tested exact two-String case, deeper or sibling composition, shutdown ordering, caching guarantees, reloads, reconnects, navigation reuse, imports, failures, or redundancy.

### Two-String painted handoff boundary

One focused extension declared the same two persistent String inputs on two known-Good children and property-bound both Embedded View parameter fields plus the dynamic child path. The sequence was A/`ALPHA_ONE|ALPHA_TWO`, one guarded script assigning both BETA values, replacement with B, a deliberate sequential first-GAMMA assignment, the second-GAMMA assignment, then replacement with A.

A requestAnimationFrame trace and a MutationObserver trace recorded the painted client boundary. The single-script BETA assignment painted the parent BETA pair while child A still showed the complete ALPHA pair, then child A showed the complete BETA pair; neither trace recorded a mixed BETA child pair. The deliberate sequential control did paint `GAMMA_ONE|BETA_TWO` in both parent and child before the complete GAMMA pair, proving the trace could detect a mixed state. Each path replacement briefly had no painted child pair, then mounted the selected child with the complete current pair.

Separate parent/A/B startup counters progressed `1/1/0 -> 1/1/0 -> 1/1/1 -> 1/1/1 -> 1/1/1 -> 1/2/1`; scripts progressed `2 -> 3 -> 5 -> 6 -> 7 -> 9`. Expression metrics increased throughout the observation window but changed with capture settle time, so use them only as execution correlation, not fixed semantic counts. The tested propagation/remount gaps were roughly 105-107 ms, but that timing is observation evidence, not a guarantee.

To validate this boundary:

1. Declare both persistent String inputs identically on both children and bind each `props.params.<name>` plus `props.path` to separate parent properties.
2. Trace painted parent and child pairs on every animation frame and with a mutation observer. Include a deliberate sequential mixed-state control so a zero-mixed result has demonstrated detector sensitivity.
3. Require no mixed child frame for the one-script pair assignment, the deliberate mixed pair on both trace surfaces, and complete current pairs after both child replacements.
4. Correlate every settled screenshot with separate startup counters, official mounted-view reads, scripts, one stable session/page, and zero reconnects. Do not require fixed expression counts.
5. Require exact functional project-resource stability, positive geometry, empty browser diagnostics, a bounded clean Gateway log window, route success, clear scan lock, and natural browser teardown.

This proves only the observed painted client boundary for two synchronous String assignments in one script and one deliberate sequential control. It does not prove internal atomicity, server-side transaction semantics, other parameter counts or types, exact propagation timing, rapid repeated changes, async scripts, deeper composition, missing paths, reloads, reconnects, navigation, failures, or redundancy.

### Nested String-object input and mutation

One tested child input used this exact persistent object shape on two known-Good children:

```json
{
  "params": {
    "payload": {
      "name": "CHILD_FALLBACK",
      "code": "CHILD_FALLBACK",
      "detail": { "mode": "CHILD_FALLBACK" }
    }
  },
  "propConfig": {
    "params.payload": {
      "paramDirection": "input",
      "persistent": true
    }
  }
}
```

The parent's Embedded View stored a fallback object under `props.params.payload` and property-bound `props.params.payload` to `view.custom.payload`. Child expressions read `{view.params.payload.name}`, `{view.params.payload.code}`, and `{view.params.payload.detail.mode}`.

These synchronous component-script forms passed for the exact all-String object:

```python
self.view.custom.payload = {
    "name": "BETA",
    "code": "TWO",
    "detail": {"mode": "INNER_BETA"}
}
self.view.custom.payload.name = "GAMMA"
self.view.custom.payload.detail.mode = "INNER_GAMMA"
self.view.custom.payload.code = "THREE"
```

The settled sequence was A/`ALPHA|ONE|INNER_ALPHA` -> A/`BETA|TWO|INNER_BETA` -> B/complete BETA -> B/`GAMMA|TWO|INNER_BETA` -> B/`GAMMA|TWO|INNER_GAMMA` -> B/`GAMMA|THREE|INNER_GAMMA` -> A/complete GAMMA. Parent/A/B startup counters progressed `1/1/0 -> 1/2/1`; scripts progressed `2 -> 3 -> 5 -> 6 -> 7 -> 8 -> 10`. Expression metrics correlated with execution but remain observation-window dependent.

Animation-frame and mutation traces showed the parent update first, the child retaining its previous complete object, then the child's complete new object. Whole-object BETA replacement produced no painted partial BETA combination on either trace. Each in-place top-level or nested mutation produced only its deliberately changed field while preserving the other current fields. A -> B and B -> A replacement briefly painted no child payload, then mounted the selected child with the complete current object. The observed propagation/remount gaps were about 105-107 ms; do not treat that timing as a guarantee.

Validate this exact boundary by requiring all of these:

1. Preserve the complete fallback object under both child `params` and Embedded View `props.params`; declare the object property itself as the persistent input.
2. Render every top-level and nested field independently in parent and child expressions so stale, missing, or partially propagated fields are visible.
3. Trace each painted parent/child object on animation frames and DOM mutations. Maintain an allowlist of exact complete states and reject any unexpected field combination.
4. Correlate the seven settled states with separate startup counters, scripts, official mounts, one stable session/page, zero reconnects, screenshots, geometry, browser diagnostics, and bounded Gateway logs. Treat expression counts only as correlation.
5. Require exact functional project stability, Good final tag reads, route success, a clear scan lock, and natural browser teardown.

This proves only one input object whose existing fields are Strings, one nested object level, whole-object replacement, and mutation of existing top-level/nested fields from synchronous component scripts. It does not prove numeric/Boolean/null values, arbitrary depth, adding/deleting/renaming keys, list behavior beyond the separately tested exact three-String list, general serialization, bidirectional/output parameters, internal atomicity, exact timing, rapid/async changes, missing paths, reloads, reconnects, navigation, failures, or redundancy.

### Three-String list input and mutation

One tested child input used this exact persistent all-String list shape on two known-Good children:

```json
{
  "params": {
    "items": ["CHILD_FALLBACK_0", "CHILD_FALLBACK_1", "CHILD_FALLBACK_2"]
  },
  "propConfig": {
    "params.items": {
      "paramDirection": "input",
      "persistent": true
    }
  }
}
```

The parent Embedded View stored a three-String fallback under `props.params.items` and property-bound the complete `props.params.items` value to `view.custom.items`. Parent and child expressions read the three known indexes with `{view.custom.items[0]}` and `{view.params.items[0]}` forms, repeated for indexes 1 and 2.

These synchronous component-script forms passed for the exact three-element list:

```python
self.view.custom.items = ["BETA_0", "BETA_1", "BETA_2"]
self.view.custom.items[0] = "GAMMA_0"
self.view.custom.items[1] = "GAMMA_1"
self.view.custom.items[2] = "GAMMA_2"
```

The settled sequence was A/complete ALPHA list -> A/complete BETA list -> B/complete BETA list -> B/`GAMMA_0|BETA_1|BETA_2` -> B/`GAMMA_0|GAMMA_1|BETA_2` -> B/complete GAMMA list -> A/complete GAMMA list. Parent/A/B startup counters progressed `1/1/0 -> 1/2/1`; scripts progressed `2 -> 3 -> 5 -> 6 -> 7 -> 8 -> 10`. Expression metrics correlated with execution but remain observation-window dependent.

Animation-frame and mutation traces recorded 13 exact painted transitions. Each update painted the parent first, the child retaining its previous complete list, then the child at the new complete state. Whole-list BETA replacement produced no painted partial BETA combination in its mutation window. The deliberate one-index-at-a-time GAMMA sequence painted each expected mixed list state, demonstrating that the trace detected individual index changes. Each child replacement briefly painted no child list, then the selected child received the complete current list. Observed propagation/remount gaps were about 105-108 ms; do not treat that timing as a guarantee.

Validate this exact boundary by requiring all of these:

1. Preserve the exact-length all-String fallback under both child `params` and Embedded View `props.params`; declare the list property itself as the persistent input.
2. Render every known index independently in parent and child expressions so stale, missing, or partially propagated elements are visible.
3. Trace every painted parent/child list on animation frames and DOM mutations. Include deliberate one-index changes as detector-positive controls and reject any state outside the exact allowlist.
4. Correlate all seven settled states with separate startup counters, scripts, official mounts, one stable session/page, zero reconnects, screenshots, geometry, browser diagnostics, and bounded Gateway logs. Treat expression counts only as correlation.
5. Require exact project stability, Good final tag reads, route success, a clear scan lock, and natural browser teardown.

This proves only one persistent input list of exactly three Strings, expressions for known indexes 0-2, whole-list replacement with the same length/type shape, mutation of those three existing indexes, and current-list handoff across the exact A -> B -> A sequence. By itself it does not prove other lengths or value types, nested objects/lists, structural operations, invalid or dynamic indexes, arbitrary iteration/serialization, output/bidirectional parameters, internal atomicity, exact timing, rapid/async changes, missing paths, reloads, reconnects, navigation, failures, or redundancy; use the separately tested structural boundary below only for its exact append/pop forms.

### Structural String-list append and pop

One focused extension began with the exact three-String input above and rendered arbitrary observed length through a property binding plus this script transform form on the parent and selected child:

```python
items = [str(item) for item in value]
return "items(%d): %s" % (len(items), " | ".join(items))
```

These exact synchronous component-script operations passed:

```python
# Direct mutation of the Perspective property-array wrapper.
items = self.view.custom.items
items.append("DIRECT_3")
removed = items.pop()

# Copy, structurally mutate, then reassign the complete list.
items = list(self.view.custom.items)
items.append("COPY_4")
self.view.custom.items = items

items = list(self.view.custom.items)
removed = items.pop()
self.view.custom.items = items
```

The tested length/value sequence was 3/ALPHA -> direct append to 4 with `DIRECT_3` -> copy/reassign append to 5 with `COPY_4` -> fresh child B at the complete length-5 list -> direct last-item pop back to 4 -> copy/reassign last-item pop back to the original length-3 ALPHA list -> fresh child A at the complete current list. Direct append and pop changed the wrapper immediately, repainted the parent, and propagated to the mounted child. Both copy/reassign operations did the same.

Animation-frame and mutation traces recorded 13 exact transitions. Each structural change painted the parent at the new complete list while the child still showed its previous complete list, then painted the child at the new complete list. Each path replacement briefly painted no child and then mounted the fresh child with the complete current list. The observed gaps were about 106-108 ms; do not treat this timing as a guarantee.

Validate this boundary by requiring all of these:

1. Keep the direct wrapper call and copy/reassign call as distinct guarded operations; do not use one as an unreported fallback for the other.
2. Render length and every value from the binding input so length-changing propagation is independently visible in parent and child.
3. Record the exact removed value for `pop()` and require the resulting complete list, not only its length.
4. Trace every painted status/list combination and correlate all settled states with external startup counters, official mounts, scripts/expressions, one stable session/page, zero reconnects, screenshots, geometry, browser diagnostics, and bounded Gateway logs.
5. Require exact project stability, Good final tags, route success, clear scan lock, and natural browser teardown.

This proves only append of one String at the end, no-argument pop of the last String, and the exact copy/reassign equivalents for one 3 -> 4 -> 5 -> 4 -> 3 sequence. It does not prove insert, indexed pop, remove-by-value, slice, clear, extend, sort, reverse, reorder, repeated/batched operations, non-String or nested members, arbitrary lengths, invalid/dynamic indexes, arbitrary iteration/serialization, output/bidirectional parameters, internal atomicity, exact timing, rapid/async changes, missing paths, reloads, reconnects, navigation, failures, or redundancy.

### Dynamic missing child and recovery

A focused extension used the same property-bound Embedded View path shape with one known Good child and one independently absent child path. A guarded control selected the absent path; a second guarded control restored the Good path. No import, navigation, reload, tag write, or reconnect occurred during the interaction sequence.

The initial Good child mounted at the embedded mount path and incremented its dedicated startup counter to 1. Selecting the missing path unmounted the child while the parent stayed mounted, left both counters at 1, and painted Ignition's native `View Not Found` state with secondary text `View with configured path not found in the project`. The browser console emitted one warning matching `Cannot subscribe to "ProjectDefinition" state ... does not exist.` Restoring the Good path mounted a fresh child instance at the same embedded mount path, incremented only the child counter to 2, removed the error state, and left the parent counter at 1.

Validate this boundary with all of these gates:

1. Prove the selected missing resource has zero matching entries in the authoritative project export before the test.
2. Keep separate parent and child startup counters, reset them before natural mount, and require the Good -> missing -> Good values `1/1 -> 1/1 -> 1/2`.
3. Require official mounted-view reads to show parent plus child, parent only, then parent plus child at the same embedded mount path in one unchanged session/page with zero reconnects.
4. Reconcile scripts as two startup executions initially, one missing-selection Button execution, then one recovery Button plus one fresh-child startup execution.
5. Capture the native primary/secondary error messages, error-state classes, positive geometry, recovery screenshot, and the single expected missing-resource console warning. Do not call the warning-bearing console clean.
6. Require byte-identical project exports throughout runtime, bounded Gateway logs, final tag exports, route success, clear scan lock, and browser-session cleanup.

This proves recoverability only for one exact absent String path selected and restored by guarded controls. It does not prove shutdown event behavior, malformed/null/empty/unauthorized paths, parameters on the replaced child, rapid switching, multiple or nested dynamic mounts, caching guarantees, reloads, reconnects, navigation reuse, or timing.

### Dynamic child shutdown on replacement and page close

An official 8.3 project export supplied this view-level shutdown event shape:

```json
{
  "events": {
    "system": {
      "onShutdown": {
        "config": {
          "script": "\t# synchronous bounded script"
        },
        "scope": "G",
        "type": "script"
      }
    }
  }
}
```

A focused test placed synchronous guarded counter increments in `onStartup` and `onShutdown` on two known Good dynamic children. The parent used a separate startup counter and guarded controls selected A -> B -> A. Each child had independent startup and shutdown counters visible in the parent and selected child.

The interaction sequence was:

- initial A: parent start 1, A start/stop 1/0, B start/stop 0/0, scripts 2;
- switch to B: parent 1, A 1/1, B 1/0, scripts 5;
- restore A: parent 1, A 2/1, B 1/1, scripts 8.

Each replacement added exactly one Button script, one outgoing-child shutdown script, and one incoming-child startup script. Official mounted-view reads changed A -> B -> A at the same embedded mount while the parent mount, session ID, page ID, project map, and zero-reconnect state stayed unchanged. Closing the page then incremented the final mounted A child's shutdown counter once more, producing final A start/stop 2/2 after the browser session cleaned up.

Validate this boundary with separate external counters and all of these gates:

1. Derive the event object from a live 8.3 seed; do not infer `onShutdown` from the startup name.
2. Establish missing tag preconditions, official tag import/export, and a health-gated verified reset for parent start plus both children’s start/stop counters.
3. Require painted and independent reads for every counter after natural mount and after each replacement.
4. Reconcile aggregate scripts as `2 -> 5 -> 8`, correlate the exact outgoing/incoming official mounts, and require stable session/page plus zero reconnects.
5. Require byte-identical runtime project exports, screenshots, positive control geometry, empty browser consoles, bounded Gateway logs, route, lock, and cleanup.
6. After the browser session disappears, independently require one additional shutdown increment on the final mounted child and export the retained final tags.

This proves synchronous shutdown execution only for two direct known-Good dynamic child replacements and one normal page close. It does not establish exact ordering within the replacement beyond the externally observed settled state, asynchronous completion, failure/exception behavior, missing or malformed paths, rapid switching, parameters, multiple/nested children, navigation reuse, reloads, reconnects, live imports, redundancy, Designer scope, or Gateway shutdown.

### Controlled synchronous shutdown failure

A focused failure test used the same direct known-Good A -> B -> A replacement. Child A's synchronous `onShutdown` first incremented and verified an external attempt counter, then raised a uniquely identified `ValueError`. A separate completion counter had no write before the exception and remained 0. Child B retained the successful startup/shutdown instrumentation.

The settled observations were:

- initial A: parent/A-start/A-attempt/A-completed/B-start/B-stop `1/1/0/0/0/0`, scripts 2;
- select B through failing A shutdown: `1/1/1/0/1/0`, scripts 5;
- recover A: `1/2/1/0/1/1`, scripts 8;
- after normal page close: `1/2/2/0/1/1`.

The exception did not block the incoming B mount, did not paint an error state, and did not emit a browser-console event. The Gateway emitted one `perspective.actions.script` WARN for the replacement attempt with `system.onShutdown` and the unique failure marker. Guarded recovery mounted a fresh A in the same session/page with zero reconnects. Closing the page ran A's failing shutdown again, removed the browser session, and emitted the second expected WARN. Project exports stayed byte-identical throughout.

Validate this boundary without hiding the failure:

1. Write and verify a dedicated external attempt marker before raising; keep a separate completion marker that must remain unchanged.
2. Use a unique exception marker and query a bounded Gateway log window. Require exactly one matching WARN after replacement and exactly two after final page cleanup.
3. Capture painted state, error-overlay classes, browser console, independent counter reads, aggregate scripts, official mounts, session/page identity, reconnects, and exact project maps before and after the failure.
4. Invoke recovery only through a visible guarded control when the observed post-failure state permits it; do not repair state through tags or project import.
5. Require the final failing shutdown attempt, session cleanup, final tag exports, route, lock, and stable supporting APIs.

This proves only one synchronous `ValueError` after a successful bounded external write. It does not prove exceptions before external evidence, other exception types, failed tag writes, asynchronous failures, partial side effects beyond the marker, exact internal ordering, missing/malformed paths, rapid/multiple/nested replacements, navigation/reload/reconnect/import/redundancy behavior, Designer scope, or Gateway shutdown. Do not treat clean client paint as successful shutdown; preserve and classify the server WARN.

## Same-page route replacement

The tested two-route lifecycle used one parent plus one direct embedded child per route, with separate external startup/shutdown counters and fresh mount tokens on all four views. Literal A-to-B navigation added one Button script, two outgoing shutdowns, and two incoming startups for a total delta of five. Browser Back and Forward each added two outgoing shutdowns plus two incoming startups for a delta of four. All three transitions preserved the official session/page IDs and had zero reconnects.

Back and Forward created new mount tokens and reset the returned route's prior local message state; they did not restore the earlier view instances. Official topology contained only the active route pair. Terminating the exact test session through the official API ran the final active parent/child shutdowns. See [page navigation](perspective-page-navigation.md) for the complete sequence and mandatory cleanup rule.

This qualifies only the exact A-to-B, Back-to-A, Forward-to-B sequence reproduced three times. It does not establish behavior for same-route parameter-only navigation, rapid history traversal, redirects, reload, reconnect, multiple/deeper children, popups/docks, query changes, authorization transitions, or other builds.

## Boundaries

The tested fresh mount, exact A → B → A parent-only and child-only imports, ordered runtime String-input changes, two-resource Good-path replacement, exact one- and two-String handoff sequences, one nested all-String object, one exact three-String list plus one exact direct/copy append-pop sequence, exact missing-path recovery, synchronous outgoing-child shutdown, one controlled post-marker shutdown exception, and final-child shutdown on page close establish behavior only for one primary root and one direct embedded mount. They do not establish exactly-once behavior outside those sequences, precise ordering/timing, reloads, reconnects, deeper/multiple dynamic children, malformed/null/empty/unauthorized dynamic paths, other parameter types or directions, other object/list shapes or structural operations, rapid/concurrent changes, sibling effects, same-page navigation reuse, page-configuration or other resource changes, partial imports, multiple sessions, Designer scope, redundancy, other exception points/types, shutdown during import/reload/reconnect, asynchronous work, or other lifecycle events. Test those cases independently before relying on them.
