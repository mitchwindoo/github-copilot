# Screenshot-backed Perspective validation

Use this workflow only when the caller approves programmatic browser validation. Keep all authoring, project changes, tag changes, and Gateway configuration changes on supported APIs. Do not use the browser or Designer to create or edit resources.

## Define the visual contract first

Before opening a route, record:

- the exact route and expected destination routes;
- the expected visible markers and interactive control names;
- the viewport or responsive breakpoints being claimed;
- geometry, clipping, overflow, console, session, log, and side-effect gates;
- the API baseline that proves the project and controlled resources are unchanged unless the test declares a mutation.

A screenshot proves only the captured viewport and state. Test every breakpoint required by the requested claim.

## Capture a painted state

Navigate directly to the approved Perspective route and wait for the expected DOM state. DOM availability and positive rectangles do not prove that a screenshot has painted. On the tested build, an immediate DOM-ready capture was blank while a bounded paint-settle capture showed the complete UI.

For every accepted state, save together:

1. a PNG screenshot;
2. the exact URL and page title;
3. a bounded DOM snapshot or equivalent locator evidence;
4. viewport width, height, and device-pixel ratio;
5. bounding rectangles for expected markers and controls;
6. visibility, enabled state, in-viewport state, and document overflow/clipping indicators;
7. browser console WARN/ERROR entries.

Inspect the screenshot pixels before accepting it. If the pixels do not show the expected UI, keep the failed capture as internal timing evidence, wait for a concrete painted-state condition or bounded settle, and capture again.

## Gate the Perspective trial state

On the tested Ignition 8.3.8 build, `GET /data/api/v1/trial` returned `licenseMode`, `trialState`, `trialSecondsLeft`, and `expired`. Query and save this official status before a long headless sequence when the Gateway is in trial mode, and recheck it when a native Trial Expired page appears.

Reject the complete observation run if trial expiry replaces any tested state, even when earlier checkpoints passed and Gateway/browser error streams remain empty. Restore controlled fixtures, close remaining sessions, preserve the expiry screenshot, require active trial status, and repeat the full sequence from fresh sessions.

The observed OpenAPI described trial status as GET-only and exposed no trial-restart operation. Do not invent a Web Dev license-control endpoint or use browser automation to restart a trial. Trial activation or restart requires separately authorized Gateway administration outside the Perspective authoring workflow.

## Test navigation like a user

Before each click:

1. take or reuse a current DOM snapshot;
2. build a stable locator from that snapshot;
3. require the locator count to equal one;
4. require the control to be visible and enabled;
5. click it once;
6. wait for the exact expected URL;
7. capture a fresh screenshot, DOM state, and geometry at the destination.

Do not infer navigation from the stored script or an HTTP 200 shell. Require both the exact URL change and visible destination evidence.

## Correlate with official APIs

While the browser session exists, use official Perspective session APIs to confirm a UUID browser session for the target project and inventory its active page and mounted views. After interaction:

- read every controlled tag or state value that the test expected to change;
- compare a fresh project export with the baseline;
- verify the project scan lock is clear;
- inspect a bounded relevant Gateway WARN-or-higher log window;
- distinguish unrelated concurrent Gateway activity by logger, resource namespace, and message;
- require a clean post-final window.

Gateway log inspection is mandatory for every test, including apparent successes. Do not make log capture conditional on a visible error, failed assertion, browser warning, or expected exception. Record the start and end timestamps, query the official log endpoint, save the raw result, and classify every WARN-or-higher entry by logger, project, resource, and unique marker where available. An empty result is evidence only when its exact bounded window is preserved.

Rendered paint, an HTTP 200, clean browser diagnostics, and correct Perspective session metrics are independent signals; none replaces the Gateway log query. Conversely, some binding-quality failures paint an overlay without a Gateway WARN, so the required log check does not replace screenshot, DOM, quality-detail, or console evidence.

Do not claim event causality when the controlled outcome already had the expected value at baseline.

## Reporting boundary

Report accepted screenshots, viewport sizes, geometry/clipping results, exact click destinations, console findings, official session evidence, controlled side effects, project isolation, and relevant logs. Keep development URLs, private session IDs, raw screenshots, and environment-specific geometry out of reusable guidance.
