# Perspective component custom methods

Use this reference for the exact live-tested Ignition 8.3 component custom-method shape and bounded same-view calls. Treat shorter Ignition 8.1 examples as hypotheses; stored-resource acceptance alone does not prove the client can deserialize and execute the method.

## Complete component script shape

When a component has a custom method, retain all three arrays under `scripts`:

```json
{
  "scripts": {
    "customMethods": [
      {
        "name": "formatResult",
        "params": ["marker", "value"],
        "script": "\tresult = '%s:%02d' % (marker, value)\n\treturn result"
      }
    ],
    "extensionFunctions": [],
    "messageHandlers": []
  }
}
```

The tested method body is indented as a function body. `params` contains only the ordered caller-supplied names; do not include `self`. The installed 8.3 project accepted and exported a shorter `scripts` object containing only `customMethods`, but the routed client failed during resource deserialization. Adding the two empty companion arrays produced exact export readback and a working routed client. Therefore require all three arrays when authoring this shape through project JSON.

## Tested calls

An `onActionPerformed` script on the method-owning Button called:

```python
self.view.custom.result = self.formatResult("SAME", 7)
```

It returned the painted String `SAME:07`. A sibling Button beneath the same immediate parent called the method owner by component name:

```python
self.view.custom.result = self.getSibling("MethodHostButton").formatResult("SIBLING", 8)
```

It returned the painted String `SIBLING:08`. These results establish parameter order, one String plus one integer input, return-value use, owning-component dispatch, and same-immediate-parent sibling dispatch for this exact method.

## Negative controls

A same-parent sibling call with one required argument omitted raised `TypeError`. A call to an absent method on the known sibling raised `AttributeError`. The focused test caught each exception inside the event script, painted its class, kept the same session/page with zero reconnects, and then successfully called the valid owning-component method again.

Use caught negatives only in an explicitly designed test fixture. For ordinary pages, validate method existence and argument count before deployment and surface failures through a bounded status path. Do not treat a successful project import or exact export as runtime proof.

## Activation and validation

After official project import:

1. Require the import response to identify the exact approved project.
2. Export and compare every project entry, including the three-array `scripts` object and method body.
3. Poll the concrete client route within a bounded activation window until it returns 200. A fixed short sleep was insufficient in the focused test; transient route 500 responses produced classified route warnings.
4. Open one fresh programmatic browser page only after route readiness.
5. Capture initial, owning-call, sibling-call, caught-negative, and recovery screenshots plus exact painted text and geometry.
6. Correlate one stable official session/page and the exact mounted view. Use script/expression metrics as correlation, not semantic counts.
7. Require no unexpected browser console/page errors or Gateway WARN-or-higher entries during the client run, exact project stability, and natural page teardown.

## Strict boundary

This evidence does not establish root, parent, child, cousin, embedded-view, or cross-view method calls; custom methods invoked by transforms; other parameter counts or types; default, keyword, variadic, or overloaded arguments; mutable return values; asynchronous work; uncaught-error presentation; security behavior; multiple writers; rapid or concurrent calls; reload/reconnect behavior; or other component hierarchies. Discover and test each separately.
