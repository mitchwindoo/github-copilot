# Perspective guarded Boolean tag writes

Use this workflow only for a caller-approved Boolean tag in a bounded test or application namespace. Keep credentials and environment-specific paths out of Perspective resources and reusable documentation.

## Tested pattern

Put validation and the synchronous tag operation in a small top-level Project Library helper. The tested Perspective Button action called that helper, supplied the approved Boolean value, and synchronously assigned a concise result to view custom state for visible feedback.

The helper contract must:

1. Accept only the expected Boolean type. Do not rely on truthiness or implicit string coercion.
2. Restrict the target to the caller-approved provider and path.
3. Use a bounded synchronous write and inspect its returned quality.
4. Read the tag back independently and require the requested Boolean value with Good quality.
5. Return a structured, bounded result that the event converts into an explicit visible status.

Keep the component script thin. Do not embed credentials, broad path selection, tag creation, or project mutation in the event.

## Runtime proof

Before accepting the workflow:

1. Record an independent value, data type, quality, and source timestamp.
2. Invoke a valid false action and require visible success plus an independent false/Good read with a changed timestamp.
3. Invoke a deliberately invalid typed action and require visible rejection plus the exact unchanged value, quality, and source timestamp.
4. Invoke a valid true action and require visible success plus an independent true/Good read with a changed timestamp.
5. Restore the caller-approved retained state and verify it independently after the browser session closes.
6. Require unique visible enabled controls, screenshots for every state, positive in-viewport geometry, no overflow, a clean browser console, exact mounted-view/session correlation, unchanged project content during runtime, stable helper/API state, a clear scan lock, and bounded clean Gateway logs.

Use the official tag-read or other approved fixed runtime API for independent verification. Painted text alone cannot establish value type, quality, timestamp, write causality, or no-write behavior.

## Boundaries

This pattern proves only the exact synchronous guarded Boolean flow tested on the target Ignition 8.3 build. Direct bidirectional Text Field and Numeric Entry writeback to isolated String and Float8 memory tags is separately qualified in [Perspective input components](perspective-input-components.md#direct-bidirectional-tag-bindings). Checkbox Boolean and Dropdown String writeback is qualified in [Perspective selection controls](perspective-selection-controls.md). None of these workflows establishes arbitrary tag paths, other data types, asynchronous writes, security policies, bad-quality behavior, alarming, history, navigation, retry behavior, or generalized error presentation. Test each separately before reuse.
