# Perspective session introspection

Use this workflow only after confirming the target is Ignition 8.3.8 or reproducing it on the installed build. It inventories already existing sessions and their mounted resources. Its optional final step can terminate an exact prevalidated test session; it does not create, navigate, message, or render one.

## Discover the live contract

Read the current OpenAPI document and confirm these authenticated operations still exist:

```text
GET /data/perspective/api/v1/sessions/
GET /data/perspective/api/v1/session/{sessionId}
GET /data/perspective/api/v1/session/{sessionId}/pages
GET /data/perspective/api/v1/session/{sessionId}/page/{pageId}/views
DELETE /data/perspective/api/v1/sessions?sessionId={sessionId}&message={message}
```

Obtain the Gateway base URL and API credential at runtime. Treat session IDs and page IDs as opaque API-returned values. Percent-encode each complete identifier when inserting it into a path segment; page identifiers can contain spaces and slashes.

Do not assume every session ID is a UUID. The tested read operations accepted a non-UUID Designer-scoped identifier. This does not imply that a separate navigation or mutation operation accepts the same identifier.

## Inventory and reconcile

1. List sessions and record each returned `id`, `project`, `sessionScope`, `authorized`, `activePages`, and `pageIds` field that is present.
2. Read session detail for the selected returned ID. Reconfirm project, scope, authorization, and active-page count before continuing.
3. List pages for that session. A page item can expose `id`, `viewCount`, `componentCount`, and `bindingCount` plus connection/timing metadata.
4. For each returned page ID, list its mounted views. A mounted-view item can expose `id`, `resourcePath`, `mountPath`, `componentCount`, and `bindingCount`.
5. Require session `activePages` to match the returned page count for the same snapshot.
6. Require each page's `viewCount` to match its returned mounted-view count. Sum per-view component and binding counts and compare them with the page totals.
7. Repeat session inventory after the probe. If the session changed naturally, discard cross-response count comparisons and retry from a new snapshot.

Missing or invalid authentication returned HTTP 401 on the tested build. An unknown session or page identifier returned HTTP 404. Treat every non-2xx response as a failed snapshot and do not infer that a session or view is absent until authenticated readback confirms it.

## Evidence boundary

A returned `resourcePath` and `mountPath` prove that the Gateway reports that resource as mounted in the selected session page. Component and binding counts prove only countable instances in that inventory.

These responses did not expose:

- component property values;
- view parameter values;
- binding values, quality, or evaluation results;
- custom state;
- script inputs, outputs, or causality;
- client pixels or visible rendering.

Do not promote any of those claims from view presence or a nonzero binding count. Add separate bounded instrumentation and API readback for the exact value or behavior when needed.

Do not treat successful project import, project activation, or continued mounted-view presence as proof that an existing Designer-scoped page reloaded. On the tested build, an exact one-view project import left the page creation timestamp unchanged and did not rerun the mounted child's startup event. Require independent remount evidence, such as a new page/view lifetime plus an exact controlled outcome, before attributing behavior to the imported revision.

## Exact-session termination for test cleanup

The authenticated official OpenAPI operation `DELETE /data/perspective/api/v1/sessions` accepts one or more repeated `sessionId` query values and an optional client message. Its tested success response was an object containing the numeric `terminated` count.

Use it only for deterministic cleanup of sessions created by the current test:

1. Inventory sessions and select candidates by the approved project, browser scope, active page, and exact test view resource paths.
2. Require an unambiguous exact match. If no session or more than the expected test set matches, do nothing; never terminate an unrelated or merely stale-looking session.
3. Preserve the exact opaque ID returned by the official list/detail response and pass that value as `sessionId` with normal query encoding.
4. Require HTTP 200 and `terminated` equal to the number of exact IDs submitted.
5. Poll official session inventory until every submitted ID is absent while unrelated sessions remain unchanged.
6. Capture external lifecycle counters and a complete Gateway WARN-or-higher window after termination.

Termination is behavior, not silent garbage collection. In the tested two-route lifecycle, terminating the one exact browser test session executed the currently mounted parent and child shutdown scripts. Three clean runs each terminated exactly one selected session and ended with all eight external startup/shutdown counters at two. Therefore, never terminate and then reset shared external test state without first observing termination-side effects and log settlement.

An absent match is a safety stop, not evidence that another session should be chosen. Do not use partial identifiers, user names alone, ordinal position, guessed UUIDs, or broad project-wide termination.

## Completion gates

Report the tested Gateway build, session scope, project, page and mounted-resource identifiers supplied by the runtime, reconciled counts, authentication/not-found results, snapshot stability, any exact-session termination count and post-termination absence check, shutdown/log side effects, and all behavior that remains unobservable. Do not save private session identifiers, user names, client addresses, or runtime URLs in reusable skill content.
