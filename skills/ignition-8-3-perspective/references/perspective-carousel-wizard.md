# Perspective Carousel wizard

Use this reference only after confirming Ignition 8.3.8 or reproducing the behavior on the installed build. It qualifies one retained three-step Carousel containing a Text Field child, Numeric Entry child, and read-only Summary child. Preserve live-discovered component and resource shapes; the excerpts below describe the tested data flow, not a complete public schema.

## Child parameters and input commit

Each editable child declared one persistent `inout` view parameter. Its input property used a bidirectional property binding to that parameter.

```json
{
  "params": {"name": "Alpha"},
  "propConfig": {
    "params.name": {"paramDirection": "inout", "persistent": true}
  }
}
```

The Text Field used deferred updates. Filling the HTML input changed only the editor until Enter committed the value. The tested Text Field was itself the component-bearing `input`; do not assume it contains another input.

The Numeric Entry component contained a nested input that was initially read-only. The accepted pointer flow was:

1. Click the nested visible input.
2. Wait until its `readOnly` property becomes false.
3. Fill the numeric text.
4. Press Enter.
5. Wait for the value feedback and read-only editor state.

Typing without commit did not change the child parameter or Carousel descriptor. Enter committed the value through the bidirectional binding and persistent `inout` parameter into the corresponding descriptor `viewParams`.

## Descriptor replacement is not reactive parameter delivery

The parent copied `props.views` to a Python list, replaced the Summary descriptor with new `viewParams`, and assigned the whole list back. A sibling expression label bound directly to descriptor 2 proved that the parent property tree changed.

The Summary child did not receive those later descriptor values:

- replacement before its first mount still produced the originally authored Summary values;
- replacement while the Summary was mounted did not update it;
- navigating away and back did not update it.

Therefore treat Carousel descriptor `viewParams` as tested initial/snapshot inputs plus child `inout` writeback, not as a qualified reactive parent-to-child channel. Do not mistake a changed parent descriptor for changed child parameters.

## Qualified session-local Summary handoff

The accepted wizard defined namespaced session custom defaults in the project's Perspective session-properties resource:

```json
{
  "custom": {
    "wizardState": {
      "summary": {"name": "Alpha", "setpoint": 12.5}
    }
  }
}
```

Choose a collision-resistant namespace appropriate to the caller's project. Do not copy this generic example over existing session custom properties; merge the narrow new branch into a fresh export and require an exact delta.

After reading the committed editable descriptors, the parent action wrote only the predefined session-custom leaves:

```python
self.session.custom.wizardState.summary.name = name
self.session.custom.wizardState.summary.setpoint = setpoint
```

The Summary labels used expression bindings to those leaves:

```text
"SUMMARY NAME: " + toStr({session.custom.wizardState.summary.name})
"SUMMARY SETPOINT: " + toStr({session.custom.wizardState.summary.setpoint})
```

This pattern produced the committed values on the Summary's first mount, while mounted, after navigation away and back, and after same-session browser reload. A Reset action restored both the exact authored descriptor list and the session-custom leaves.

## Reload and isolation

The tested browser reload resumed the same Perspective session, page, active Summary step, mounted children, editable values, descriptors, and session-custom Summary. Do not wait for an assumed initial step after refresh. First observe the active dot, visible title, session/page identity, inputs, parent descriptor feedback, Summary feedback, official topology, and logs.

Two simultaneous browser sessions received different session IDs and maintained different Summary values without leakage. Exact official termination of both sessions left zero target sessions and zero cleanup WARN+.

Session custom properties are appropriate only when session-local persistence is intended. They are not a substitute for shared tags, database state, durable submission, or cross-session coordination.

## Diagnostics and validation

1. Qualify the live Text Field, Numeric Entry, bidirectional property-binding, persistent `inout`, Carousel, Button, expression-binding, and session-properties shapes.
2. Export immediately before authoring. Merge a namespaced session custom branch without replacing unrelated custom properties.
3. Require tokenless rejection, exact changed-entry set, authenticated success, semantic readback, route activation, protected-resource preservation, and bounded authoring logs.
4. Render independent feedback for the child parameter, parent descriptor, session-backed Summary, and action status. Never infer all layers from one label.
5. Capture screenshots, element geometry, accessibility snapshots, browser console/page/request diagnostics, official view/component/binding topology, and bounded Gateway WARN+ logs after every commit, navigation, action, reload, termination, and close.
6. Test uncommitted versus committed Text Field and Numeric Entry state explicitly.
7. Test Summary synchronization before first mount, while mounted, after remount, and after same-session reload.
8. Open two isolated browser contexts, assign different values, prove both remain independent, terminate each exact session through the official API, and inspect delayed cleanup logs.
9. Reject and preserve any run containing a WARN-or-higher entry, even when its logger appears unrelated; classify it and repeat cleanly.
10. Finish with two consecutive identical project exports, protected-resource inventory, route/readback assertions, zero target sessions, and a clean final log window.

## Qualification boundary

This reference qualifies one exact three-step Carousel wizard on Ignition 8.3.8: deferred String Text Field commit, numeric edit-mode/Enter commit, persistent `inout` child-to-descriptor writeback, the non-reactive parent-to-child descriptor-replacement boundary, one namespaced String/numeric session-custom Summary handoff, Reset, cumulative mounts, first-mount Summary delivery, remount, same-session reload resumption, two-session isolation, geometry, accessibility snapshots, official topology, screenshots, exact-session cleanup, and mandatory logs.

It does not qualify validation errors, form submission, shared or durable storage, automatic step advancement, dynamic child paths, descriptor counts other than three, additional parameter types, object/list handoff, concurrent writers inside one session, cross-project children, popups, Designer behavior, other Carousel configurations, other builds, or public-schema guarantees.
