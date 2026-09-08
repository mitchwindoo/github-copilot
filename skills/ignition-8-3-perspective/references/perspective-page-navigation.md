# Perspective page navigation

Use this reference for the exact live-tested Ignition 8.3 page-route and navigation forms. Keep route authoring API-only. A programmatic browser may validate the painted client, URL, history, and click behavior after authoring.

## Contents

- [Dynamic page route](#dynamic-page-route)
- [Button navigation event](#button-navigation-event)
- [Optional agent-dispatched navigation](#optional-agent-dispatched-navigation)
- [Browser history and evidence](#browser-history-and-evidence)
- [Two-route replacement lifecycle](#two-route-replacement-lifecycle)
- [Same-route dynamic-parameter lifecycle](#same-route-dynamic-parameter-lifecycle)
- [Query-string navigation lifecycle](#query-string-navigation-lifecycle)
- [Strict boundary](#strict-boundary)

## Dynamic page route

One String path segment was proven with this page-config shape:

```json
{
  "/detail/:message": {
    "title": "Detail",
    "viewPath": "Examples/Detail"
  }
}
```

The primary view declared the matching persistent input parameter:

```json
{
  "params": {
    "message": "DEFAULT"
  },
  "propConfig": {
    "params.message": {
      "paramDirection": "input",
      "persistent": true
    }
  }
}
```

Loading `/detail/FROM_URL` mounted the configured primary view and populated `view.params.message` with `FROM_URL`. A Label expression of `"Child message: " + {view.params.message}` painted the supplied segment. A static route to a different primary view was also proven in the same client.

Treat the colon-prefixed segment name and view parameter name as an exact pair. Export and read back both page config and view JSON, require the concrete route to return HTTP 200, and then prove the expected primary view, parameter value, URL, and painted content in one bounded client session.

## Button navigation event

The following component event shape navigated to both tested dynamic and static page paths:

```json
{
  "events": {
    "component": {
      "onActionPerformed": {
        "config": {
          "script": "\tsystem.perspective.navigate(page=\"/detail/FROM_URL\")"
        },
        "scope": "G",
        "type": "script"
      }
    }
  }
}
```

Use one exact literal destination during initial qualification. Guard the click with a unique locator, record the URL before and after, correlate mounted views through the official session/page APIs, inspect the painted result, and require an empty unexpected browser-console and Gateway WARN-or-higher window.

## Optional agent-dispatched navigation

An installed `llmImport` may advertise `perspective-session-navigate-v1`. This is an optional project-scoped Web Dev POST action, not an Ignition OpenAPI operation. If the approved project has no compatible `llmImport`, this action cannot be used; use official OpenAPI for authoring and a painted client click for runtime navigation validation.

The tested request contains:

```json
{
  "action": "perspective-session-navigate-v1",
  "page": "/detail/FROM_URL",
  "sessionId": "<opaque-session-uuid>",
  "pageId": "<opaque-page-uuid>",
  "dryRun": true,
  "apply": false
}
```

Before calling it:

- Read the optional health route and require the action in `availableActions`.
- Select exactly one current session and one active page using official Perspective session reads; treat both identifiers as opaque UUID strings.
- Require the destination in the installed action's fixed allowlist.
- Send JSON Booleans for `dryRun` and `apply`. A string, number, or serialized shell switch is not interchangeable with a Boolean.

The tested dry-run used `dryRun:true` and `apply:false`. It returned a verified dry-run result, reported no navigation attempt, and left the URL, mounted views, observed runtime value, and source timestamp unchanged. The tested mutation used `dryRun:false` and `apply:true`; it reported navigation dispatched for the same selected session/page and navigated that browser page to the allowlisted destination. A non-Boolean `apply` value was rejected without a navigation attempt.

Require action-specific acceptance, pass status, `navigationAttempted`, external-side-effect classification, selected session/page readback, final exact URL, expected mounted view, and painted content. HTTP success alone is insufficient.

## Browser history and evidence

Each tested script/API navigation added a history entry. Browser Back and Forward restored the exact prior dynamic, parent, or static URL and painted view in the unchanged session/page. Capture `popstate` observations and history length as supporting evidence, not as a cross-version timing or count guarantee.

For every accepted state, save:

- the exact URL and browser-history snapshot;
- painted screenshot and viewport;
- visible component geometry, clipping, and overflow checks;
- official session, page, and mounted-view reads;
- browser console/page errors and a bounded Gateway log query;
- pre/post project entry hashes proving runtime navigation did not mutate the project.

A hidden DOM node may contain disconnected-state text even when no error is visible. Do not reject a rendered page from raw body text alone; test computed visibility and inspect the screenshot pixels.

## Two-route replacement lifecycle

Treat same-page route changes as view replacement, not as reload. In the tested two-route topology, route A and route B each mounted one primary parent and one direct embedded child. All four views had separate external startup/shutdown counters, fresh mount tokens, local message state, and one session-scope handler. One literal Button navigation from A to B and Browser Back/Forward were reproduced in discovery and two fresh confirmations.

The exact settled sequence was:

| Transition | Script delta | Lifecycle evidence | Identity and local state |
|---|---:|---|---|
| Fresh A mount | +2 | A parent and child startup once | initial A tokens and empty local message state |
| A parent send | +3 | sender plus A parent/child handlers | A local count became one |
| Navigate A to B | +5 | navigation Button + A parent/child shutdown + B parent/child startup | same session/page, zero reconnects, fresh B tokens and empty B local state |
| B parent send | +3 | sender plus B parent/child handlers | B local count became one |
| Browser Back to A | +4 | B parent/child shutdown + fresh A parent/child startup | same session/page, new A tokens, prior A local message state reset |
| A child send | +3 | sender plus current A parent/child handlers | no B receiver executed |
| Browser Forward to B | +4 | A parent/child shutdown + fresh B parent/child startup | same session/page, new B tokens, prior B local message state reset |
| B child send | +3 | sender plus current B parent/child handlers | no A receiver executed |

At every accepted state, official mounted-view inventory contained the active route's parent/child pair and excluded the opposite route's pair. The official Perspective session ID and page ID stayed unchanged, Browser Back/Forward emitted the expected history transitions, and reconnects remained zero. Screenshots, geometry, exact URL, painted tokens/state, external counters, official topology, browser diagnostics, and complete Gateway log windows must all agree before promoting this behavior.

After browser automation closes, do not reset shared lifecycle tags merely because the browser object is gone. A failed exploration showed that a retained server-side page can run delayed shutdown scripts after a reset and contaminate the next run. First poll official topology until the exact test session is absent, or use the authenticated official session-termination operation described in [session introspection](session-introspection.md) against only the exact prevalidated session ID. Termination itself runs shutdown scripts, so capture final counters and logs after termination. The tested cleanup terminated exactly one selected test session in each of three runs and all eight lifecycle counters settled to two.

## Same-route dynamic-parameter lifecycle

Do not apply the two-route replacement result when only the dynamic segment changes and the page configuration still selects the same primary view resource. In the tested topology, one route `/:tab` mounted one parent and one direct embedded child. The route populated the parent's String input parameter, and a property binding passed that value to the child's matching input. Both views had external startup/shutdown counters, mount tokens, local message state, and one session-scope handler.

Discovery and two fresh confirmations reproduced this exact sequence:

| Transition | Script delta | Lifecycle and identity | Local/message state |
|---|---:|---|---|
| Fresh ALPHA mount | +2 | parent/child startup once; stop counters zero | tokens created; counts zero |
| Parent send | +3 | sender plus parent/child handlers | both counts one, origin Parent |
| Navigate ALPHA to BRAVO | +1 | Button only; no startup/shutdown, remount, view-ID change, reconnect, or session/page change | both parameters changed to BRAVO; tokens and counts one persisted |
| Child send | +3 | same two handlers | both counts two, origin Child |
| Browser Back to ALPHA | 0 | no lifecycle script, remount, identity change, or reconnect | both parameters returned to ALPHA; tokens and counts two persisted |
| Parent send | +3 | same two handlers | both counts three, origin Parent |
| Browser Forward to BRAVO | 0 | no lifecycle script, remount, identity change, or reconnect | both parameters returned to BRAVO; tokens and counts three persisted |
| Child send | +3 | same two handlers | both counts four, origin Child |

The exact script sequence was `2,5,6,9,9,12,12,15`. Throughout navigation and history, external lifecycle values stayed parent/child start `1/1` and stop `0/0`; official mounted-view IDs and mount paths stayed unchanged; one parent and one child remained mounted; and the official session/page IDs stayed unchanged with zero reconnects. Exact-session termination after each run executed the only parent/child shutdowns and settled all four lifecycle counters to one.

Use the browser URL and painted parameters as URL/parameter authority. On the tested build, official page inventory exposed the page ID, timestamps, connection count, and view/component/binding counts but no client URL. A failed harness assertion that expected `page.url` is negative evidence; do not synthesize URL proof from the session API.

Validate the boundary with fresh sessions, exact URL/history/popstate capture, painted parent and child parameters, mount tokens, local state, external lifecycle counters, official session/page/view topology, message deltas, screenshots, geometry, browser diagnostics, project hashes, exact-session cleanup, and complete Gateway logs. Treat expression-count changes as supporting correlation only.

This qualifies only one literal ALPHA-to-BRAVO navigation plus Back/Forward on one String dynamic segment, one unchanged primary parent, one direct embedded child, and one session-scope receiver per view. It does not establish same-route behavior for query parameters, multiple or non-String segments, different parameter names/directions, same-URL navigation, rapid/repeated history traversal, redirects, auth changes, popup/dock routes, deeper/multiple children, other message scopes, reload/reconnect, project imports during the session, or other builds.

## Query-string navigation lifecycle

Treat query values as page properties, not route-view parameters. In the tested resource, the parent read one query String with this expression reference:

```text
{page.props.urlParams.mode}
```

The parent passed the value into one direct embedded child's declared String input with this property-binding path. A later independent test repeated the same shape for a second String key named `note`:

```json
{
  "props.params.mode": {
    "binding": {
      "config": {
        "path": "page.props.urlParams.mode"
      },
      "type": "property"
    }
  }
}
```

```json
{
  "props.params.note": {
    "binding": {
      "config": {
        "path": "page.props.urlParams.note"
      },
      "type": "property"
    }
  }
}
```

The tested Button used URL navigation rather than page navigation. Substitute the actual deployment values and URL-encode dynamic data:

```python
system.perspective.navigate(
    url="<gatewayUrl>/data/perspective/client/<projectName>/detail/ALPHA?mode=SECOND&note=GAMMA%20%26%20DELTA"
)
```

Do not pass the query dictionary through the `params` argument for this page-navigation case. The tested `params` argument belongs to view navigation, while this exact query workflow used the URL itself.

The first discovery plus two fresh confirmations started at `.../ALPHA?mode=FIRST`, navigated to the same route and segment with `mode=SECOND`, then used Browser Back and Forward. Both the parent expression and child input painted `FIRST -> SECOND -> FIRST -> SECOND`. The navigation created one history entry.

A separate discovery plus two fresh confirmations repeated the sequence with `.../ALPHA?mode=FIRST&note=ALPHA%20BETA` and `.../ALPHA?mode=SECOND&note=GAMMA%20%26%20DELTA`. In all 24 accepted states, the parent and child independently painted the matching `mode` and decoded `note`: `%20` became a space, while `%26` became an ampersand inside the `note` value rather than a new query separator. Browser `URLSearchParams` returned exactly the ordered keys `mode`, `note` and decoded values `ALPHA BETA` or `GAMMA & DELTA`.

A third discovery plus two fresh confirmations distinguished four exact `note` forms:

| URL form | Browser parse | Perspective `page.props.urlParams.note` |
|---|---|---|
| key absent | `has=false`, `get=null`, `getAll=[]` | blank paint with `Bad_Stale` quality overlay |
| `note=` | present empty String | blank paint with Good quality and no overlay |
| `note=ALPHA+BETA` | `ALPHA BETA` | `ALPHA BETA` |
| `note=FIRST&note=SECOND` | `get=FIRST`, `getAll=[FIRST,SECOND]` | `SECOND` |

Thus missing and present-empty are not quality-equivalent. For the exact duplicate ordering tested, Perspective collapsed the key to its last occurrence even though browser `URLSearchParams.get()` returned the first and `getAll()` retained both. Do not use browser query parsing as a substitute for Perspective binding evidence.

The missing direct reference produced no Gateway WARN-or-higher entry. Clicking its visible client overlay reported subcode `Bad_Stale` and property `root/RawNote.text`. Always combine painted-overlay inspection, optional overlay-detail interaction, browser diagnostics, official topology, and Gateway logs; a clean log window does not prove Good binding quality.

The expression `try({page.props.urlParams.note}, "<MISSING>")` did not recover from this bad quality: it still painted blank with an overlay. The following exact expression returned `<MISSING>` with Good paint in both a parent Label and an expression-bound embedded-child input, while preserving present-empty as an empty String:

```text
if(isBad({page.props.urlParams.note}), "<MISSING>", {page.props.urlParams.note})
```

Use this only for the tested missing query-property case. Do not infer that it handles null values, bad tag qualities, uncertain quality, other subcodes, type conversion, or exceptions.

The exact settled sequence was:

| Transition | Script delta | Reconnect delta | Lifecycle and identity | Local/query state |
|---|---:|---:|---|---|
| Fresh `mode=FIRST` mount | +2 | 0 | parent/child startup once | tokens created; counts zero |
| Parent send | +3 | 0 | sender plus both handlers | both counts one |
| URL navigate to `mode=SECOND` | +1 | +1 | no startup/shutdown, remount, view-ID change, or session/page change | both query paints changed; tokens/counts persisted |
| Child send | +3 | 0 | same two handlers | both counts two |
| Browser Back to `mode=FIRST` | 0 | +1 | no lifecycle or identity change | both query paints reverted; tokens/counts persisted |
| Parent send | +3 | 0 | same two handlers | both counts three |
| Browser Forward to `mode=SECOND` | 0 | +1 | no lifecycle or identity change | both query paints advanced; tokens/counts persisted |
| Child send | +3 | 0 | same two handlers | both counts four |

Both the one-key and two-key tests reproduced the exact script sequence `2,5,6,9,9,12,12,15` and reconnect counts `0,0,1,1,2,2,3,3`. The four-form test used one parent plus raw and guarded children; its three Button navigations produced scripts `3,4,5,6`, six Back/Forward edges added no scripts, and reconnects advanced once on every navigation/history edge from zero through nine. External startup/shutdown values stayed `1/0` per mounted view during query/history edges. Mount tokens, mounted-view IDs and paths, and official session/page IDs persisted. Exact official session termination executed the only shutdown scripts and settled every lifecycle counter to one.

This reconnect result is the essential contrast with the tested same-route dynamic-segment `page=` navigation, whose navigation and history edges had zero reconnects. Do not treat `url=` query navigation as a silent in-place parameter write even though mounted view identity and local state survived in this test. Because the page's JavaScript environment reloaded, the test did not obtain persistent `popstate` observations; exact browser URLs and reconnect metrics were the stronger evidence.

The official page inventory again exposed no client URL on the tested build. Use the browser URL for query/history proof and official APIs for session/page/view identity. Save logs after every query edge and after exact-session termination; all accepted edge and termination windows were clean.

This qualifies one or two String keys; the exact uppercase `mode` values; the exact present, missing, empty, plus-decoded, percent-decoded, and duplicate `note` forms above; one unchanged route segment; the tested parent/child topologies; and the exact navigate/Back/Forward sequences on the tested build. It does not establish reversed or three-plus duplicate ordering, percent-encoded key names, malformed escapes, other reserved or Unicode characters, null values, non-String coercion, fragments, repeated same-URL navigation, rapid history traversal, redirects, authentication, new tabs, other origins, deeper trees, other scopes, reload persistence beyond the observed reconnect, or other builds.

## Strict boundary

This evidence proves one exact String dynamic segment, one exact input-parameter match, literal dynamic/static destinations, Button `onActionPerformed` navigation, one advertised fixed-allowlist agent action, Back/Forward behavior in one browser page, the exact two-route parent/child replacement sequence, the contrasting exact same-route dynamic-parameter sequence, and the bounded query sequences and quality guard above. It does not prove other query shapes, ordering, encoding, quality-recovery cases, multiple or non-String route segments, optional/wildcard segments, redirects, history replacement, new tabs, popup/dock navigation, view-parameter dictionaries passed to page navigation, authentication redirects, invalid destinations, arbitrary allowlists, multi-session dispatch, rapid/repeated navigation, deeper view trees, other message scopes, or timing guarantees. Test each separately before use.
