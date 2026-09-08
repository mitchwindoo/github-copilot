# Perspective docked views

Use this reference for the exact route-local and shared-dock shapes and runtime behaviors qualified on Ignition 8.3.8 / Perspective 3.3.8. Treat combinations and reconnect persistence as unverified unless stated below.

## Contents

- [Persisted page configuration](#persisted-page-configuration)
- [Tested session calls](#tested-session-calls)
- [Registration versus painted visibility](#registration-versus-painted-visibility)
- [Shared docks across routes](#shared-docks-across-routes)
- [Automatic breakpoint behavior](#automatic-breakpoint-behavior)
- [Modal dock behavior](#modal-dock-behavior)
- [Resizable dock behavior](#resizable-dock-behavior)
- [Top and bottom docks with north anchors](#top-and-bottom-docks-with-north-anchors)
- [Four-sided corner priority](#four-sided-corner-priority)
- [API boundary](#api-boundary)
- [Opposite-side multiple docks](#opposite-side-multiple-docks)
- [Unverified boundary](#unverified-boundary)

## Persisted page configuration

In the exported `com.inductiveautomation.perspective/page-config/config.json`, put route-specific docks inside the route object under `docks`. The live-tested side keys are `left`, `right`, `top`, and `bottom`; each value is an array. Do not infer that every field combination has been tested on every side.

```json
{
  "pages": {
    "/<route>": {
      "docks": {
        "left": [
          {
            "anchor": "fixed",
            "autoBreakpoint": 700,
            "content": "cover",
            "handle": "hide",
            "iconUrl": "",
            "id": "<dock-id>",
            "modal": false,
            "resizable": false,
            "show": "onDemand",
            "size": 280,
            "viewParams": {"message": "PAGE_CONFIG_PARAM"},
            "viewPath": "<view-path>"
          }
        ]
      },
      "title": "<title>",
      "viewPath": "<primary-view-path>"
    }
  }
}
```

The persisted names differ from two runtime `alterDock` configuration names: the exported route uses `viewPath` and `show`; the documented runtime configuration uses `view` and `display`. Do not interchange them without a focused test.

Preserve every unrelated page and the complete `sharedDocks` object. Obtain a fresh project export immediately before import, declare the page-config plus new-view delta, import only the approved project through the official project-import endpoint, and require exact archive readback.

## Tested session calls

These exact component-event calls ran in Perspective Session scope:

```python
system.perspective.openDock("<dock-id>", params={"message": "OPEN_PARAM"})
system.perspective.closeDock("<dock-id>")
system.perspective.toggleDock("<dock-id>")

system.perspective.alterDock("<dock-id>", {
    "size": 360,
    "content": "push",
    "handle": "show",
    "viewParams": {"message": "ALTERED_PARAM"}
})
```

`openDock` requires a preconfigured dock ID. In the tested page, its `params` dictionary reached the dock's matching persistent input. `closeDock` hid that dock. A subsequent `toggleDock` reopened with the most recent `openDock` parameter rather than restoring the original serialized route parameter.

Changing a closed dock to 360px, `push`, and `handle: show` moved its hidden wrapper from x=-280 to x=-360 and painted a 24px handle at x=0. Clicking that handle opened the dock, passed `ALTERED_PARAM`, and shifted the 1280px-wide primary view to x=360 with width 920. This user-click path did not increment the script metric.

Changing the open dock to 420px, `cover`, and a new `viewParams` value immediately painted the new value, returned the primary view to x=0/width 1280, painted the dock at x=0/width 420, and placed the handle at x=420. A button inside the dock could call `closeDock` for its own configured ID; the wrapper then moved to x=-420 and the handle returned to x=0.

## Registration versus painted visibility

Do not use the official page Views API count as a dock-open test. In every tested state—including closed states—the API listed both the primary resource and the dock resource. When closed, the dock wrapper remained present off-screen and the child view collapsed to 0 by 0; when open, the child painted at the configured width. Use DOM text, computed geometry, screenshots, and the dock wrapper/handle state for visibility, while using the official API for session/page identity and resource registration.

## Shared docks across routes

The tested root-level serialization adds a side array beside the preserved corner priority:

```json
{
  "sharedDocks": {
    "cornerPriority": "top-bottom",
    "left": [
      {
        "anchor": "fixed",
        "autoBreakpoint": 700,
        "content": "push",
        "handle": "hide",
        "iconUrl": "",
        "id": "<shared-dock-id>",
        "modal": false,
        "resizable": false,
        "show": "onDemand",
        "size": 240,
        "viewParams": {"message": "SHARED_CONFIG"},
        "viewPath": "<shared-view-path>"
      }
    ]
  }
}
```

Two tested routes contained only `title` and primary `viewPath`; both inherited one shared child registration. The official Views API always returned the current primary plus the shared child, even while the on-demand dock was closed, off-screen at x=-240, and its child width was 0.

On its origin route, `openDock` parameters painted immediately and 240px `push` geometry moved the primary to x=240/width 1040. Entering another route did not retain that as the settled state. Frame traces showed this sequence for component navigation with an open dock:

1. The destination primary first appeared with the dock still open and the caller's `openDock` parameter.
2. The parameter changed to serialized `SHARED_CONFIG` while the wrapper animated left.
3. The destination settled with the wrapper at x=-240, child width 0, and primary x=0/width 1280.

The same settled-close rule occurred from either primary route. Browser Back from an open dock began on the destination with serialized parameters, then animated closed. Browser Forward from an already closed state stayed closed. These transitions occurred in one stable session and page ID; component navigation incremented the script metric, while Back/Forward did not.

Treat `show: "onDemand"` as a per-route-entry initial state in this exact shared-dock workflow. Do not promise that an open shared dock stays open across route navigation merely because the definition and child registration are shared. If persistent open state is required, design and separately validate explicit state restoration after navigation.

## Automatic breakpoint behavior

The tested responsive route-local dock used this exact combination:

```json
{
  "autoBreakpoint": 900,
  "content": "push",
  "handle": "show",
  "iconUrl": "material/menu",
  "show": "auto",
  "size": 260
}
```

The breakpoint is inclusive on the tested runtime: the dock was automatically visible at 1200px and exactly 900px, then automatically hidden at 899px. Open geometry was wrapper x=0/width 260 and primary x=260/width `viewport - 260`; hidden geometry was wrapper x=-260, child width 0, and primary x=0/full viewport width.

With `handle: "show"`, a 24 by 48 handle remained painted in every tested state. It was at x=260 while open and x=0 while hidden. Clicking it at 899px opened the dock with serialized parameters and did not increment the script metric. Resizing wide preserved the open dock; crossing from 900px to 899px hid it again, including after a handle open or explicit `openDock`.

An explicit open at 899px painted the caller parameter. That value persisted at 900px, disappeared from the painted DOM when the 899px crossing hid the dock, and returned when `toggleDock` reopened it at 899px. The second toggle closed it. Do not interpret automatic hiding as clearing the last explicit runtime parameters.

In the retained test project, one prior global left shared dock and the route-local auto left dock were both listed by the official Views API, but only one left wrapper—the route-local 260px auto dock—was painted. Treat that same-side route/shared interaction as an exact observation, not a general precedence rule.

## Modal dock behavior

The tested route-local right dock used this exact persisted combination:

```json
{
  "content": "cover",
  "handle": "hide",
  "id": "<dock-id>",
  "modal": true,
  "resizable": false,
  "show": "onDemand",
  "size": 320,
  "viewParams": {"message": "MODAL_CONFIG"},
  "viewPath": "<dock-view-path>"
}
```

At a 1280 by 720 viewport, exact-ID `openDock` painted the right wrapper at x=960/width 320 and the child at the same rectangle. Because `content` was `cover`, the primary remained x=0/width 1280. The client also painted one full-viewport 1280 by 720 modal layer with a 50% black computed background beneath the dock and above the primary.

That modal layer intercepted a normal click on a visible primary Button; the automated click reported interception and the bound background counter did not change. The child remained interactive and closed its own dock with exact-ID `closeDock`. A click on the modal layer outside the dock also dismissed the dock. The outside dismissal incremented neither the script metric nor the visible parent counter.

After explicit open with `{"message":"EXPLICIT_OPEN"}`, child self-close, and later outside dismissal, exact-ID `toggleDock` reopened with the last explicit parameter instead of the serialized `MODAL_CONFIG` value. In closed states the wrapper remained at x=1280/width 320 while the child collapsed to 0 by 0. The official Views API continued to list the primary, modal child, and a retained shared child in every state, so registration still did not prove painted visibility.

Treat outside-click dismissal as the observed modal-dock behavior for this exact runtime; it is not the popup `overlayDismiss` contract, and no corresponding persisted dock field was tested. Do not infer keyboard/Escape behavior, focus trapping, touch input, stacked modal docks, other sides, push-modal geometry, handles, resizable modal docks, or reload/navigation persistence.

## Resizable dock behavior

The tested route-local left dock was on-demand, nonmodal, pushed the primary, and persisted these relevant fields:

```json
{
  "content": "push",
  "handle": "hide",
  "id": "<dock-id>",
  "modal": false,
  "resizable": true,
  "show": "onDemand",
  "size": 300,
  "viewParams": {"message": "RESIZABLE_CONFIG"},
  "viewPath": "<dock-view-path>"
}
```

After exact-ID open at 1280 by 720, the client painted a 22px `dock-border drag-border` containing a 20px `resize-zone` with computed `cursor: ew-resize`. In this exact styled fixture, persisted `size: 300` produced a 318px total wrapper, 296px measured child root, and primary x=318/width 962. Treat those offsets as measured client geometry, not a general formula for `size`.

Four real pointer drags produced this total-wrapper sequence: 318 → 438 → 238 → 318 → 378. The corresponding primary geometry always remained x=`wrapper width`, width=`1280 - wrapper width`. Every sampled animation step was monotonic in the requested direction. Dragging did not increment the component-script metric, and the last explicit `openDock` parameter remained painted throughout.

Closing at 238px and reopening restored 238px. Dragging back to 318px, closing from the parent, and reopening restored 318px. A later 378px width also remained on the hidden off-screen wrapper after child close. Thus, user-resized width persisted across the exact tested close/reopen sequence within one session/page; do not infer persistence across navigation, reload, reconnect, or another session.

Extreme exploratory drags are a warning boundary. Dragging toward x=0 reached an 18px wrapper while the 24px child and 20px resize zone overlapped outside it; subsequent normal pointer drags did not restore the width and the child close Button became pointer-inaccessible. In a fresh session, dragging toward the far viewport edge reached a 1280px wrapper and 1258px child while the pushed primary measured x=1290/width 24; child close still succeeded. Do not use those extremes as supported layout limits. Constrain or avoid user resizing near unusable widths until a separate product-level minimum/maximum design is implemented and tested.

Do not combine these claims with `alterDock`. In the retained same-side shared-dock environment, exploratory alterations changed which left dock painted, so no reusable resizable-plus-alter behavior was promoted.

## Top and bottom docks with north anchors

Two isolated routes used the same horizontal child resource twice per route with distinct IDs and parameters. Each route persisted one top and one bottom dock:

```json
{
  "docks": {
    "top": [{
      "anchor": "fixed",
      "content": "push",
      "handle": "hide",
      "id": "<top-id>",
      "modal": false,
      "resizable": false,
      "show": "visible",
      "size": 110,
      "viewParams": {"label": "FIXED TOP"},
      "viewPath": "<horizontal-child-path>"
    }],
    "bottom": [{
      "anchor": "fixed",
      "content": "push",
      "handle": "hide",
      "id": "<bottom-id>",
      "modal": false,
      "resizable": false,
      "show": "visible",
      "size": 90,
      "viewParams": {"label": "FIXED BOTTOM"},
      "viewPath": "<horizontal-child-path>"
    }]
  }
}
```

`show: "visible"` painted both docks without a component script. At a 1280 by 720 viewport, the top child was x=0/y=0/width=1280/height=110 and the bottom child was x=0/y=630/width=1280/height=90. The primary root started at y=110 and was 1900px tall. The official Views API listed the current primary, two entries for the same horizontal child resource, and one retained shared child. Resource-path multiplicity proved two configured child instances; geometry and text proved both were painted.

The only deliberate difference between the two routes was the top dock's `anchor`. Real wheel input moved `#app-container` through scroll positions 0, 650, and 1290:

| North anchor | Top dock y sequence | Primary y sequence | Bottom dock y sequence |
|---|---:|---:|---:|
| `fixed` | 0, 0, 0 | 110, -540, -1180 | 630, 630, 630 |
| `scrollable` | 0, -650, -1290 | 110, -540, -1180 | 630, 630, 630 |

All primary markers moved by the exact scroll delta. Thus, for this route-local visible/push fixture, `fixed` kept the north dock at the viewport top, while `scrollable` moved it with the scrolling page. The south dock stayed at the viewport bottom in both routes. The `anchor` value persisted on the south definitions only to keep the fixtures structurally parallel; no south-anchor meaning is claimed because the official runtime contract limits `anchor` to north docks.

A painted Button navigation from the fixed route to the scrollable route and Browser Back both passed in one stable session/page with zero reconnects, browser errors, or final-runtime Gateway WARN+. Browser Back restored the fixed route at scroll 0. Treat that restoration as the exact observed history sequence, not a general scroll-restoration guarantee.

Do not combine these results with shared top/bottom docks, cover, modal, resizable, auto, on-demand, multiple same-side docks, corner-priority changes, other view heights or viewport sizes, touch/keyboard input, reload/reconnect, or cross-page targeting without a focused test.

## Four-sided corner priority

For a route-local page, persist corner priority inside the route's `docks` object, beside the four side arrays:

```json
{
  "pages": {
    "/<route>": {
      "docks": {
        "cornerPriority": "left-right",
        "top": [{"id": "<top-id>", "size": 100}],
        "bottom": [{"id": "<bottom-id>", "size": 80}],
        "left": [{"id": "<left-id>", "size": 180}],
        "right": [{"id": "<right-id>", "size": 160}]
      },
      "viewPath": "<primary-view-path>"
    }
  }
}
```

The abbreviated dock objects above show placement only. Preserve every required field from the complete tested dock shape elsewhere in this reference. The live-tested `cornerPriority` values are `top-bottom` and `left-right`.

Do not place this property beside `docks` in the route object. The tested Gateway accepted and exported that unknown placement without an import or route error, but ignored it at runtime; both routes inherited the root shared `top-bottom` priority. Moving only those values to `pages.<route>.docks.cornerPriority` changed the painted geometry exactly.

At 1280 by 720 with visible push docks sized top 100, bottom 80, left 180, and right 160:

| Priority | Top x/y/w/h | Bottom x/y/w/h | Left x/y/w/h | Right x/y/w/h | Primary x/y/w/h |
|---|---|---|---|---|---|
| `top-bottom` | 0/0/1280/100 | 0/640/1280/80 | 0/100/180/540 | 1120/100/160/540 | 180/100/940/540 |
| `left-right` | 180/0/940/100 | 180/640/940/80 | 0/0/180/720 | 1120/0/160/720 | 180/100/940/540 |

Thus the prioritized pair reached both corresponding viewport edges, while the opposing pair was constrained between it. The primary center rectangle was identical for both priority values. One dock resource mounted four times with distinct IDs/parameters; the official Views API returned four identical child resource paths plus the current primary and one retained shared child registration.

This exact result used one route-local visible/push/nonmodal/nonresizable dock per side. Do not infer inherited-only behavior, shared four-sided layouts, multiple docks per side, other sizes/viewports, mixed content modes, scrolling combinations, responsive behavior, reload/reconnect, or cross-Gateway behavior.

## API boundary

Use official OpenAPI project export/import for arbitrary page-config and view JSON. Use official session, page, view, and log reads for runtime correlation. `llmImport` is not required for this workflow and is not an Ignition platform API.

If a compatible project-scoped `llmImport` resource is absent, none of its POST actions can be called. That does not affect `/openapi.json` or the official operations advertised by the Gateway. See [perspective-api-surface.md](perspective-api-surface.md) for the full qualified official endpoint inventory and conditional `llmImport` POST-action inventory.

## Opposite-side multiple docks

One tested route configured both `docks.left[]` and `docks.right[]` with distinct IDs while pointing both definitions at the same child view resource. The left dock was 260px and the right dock was 300px. Both were on-demand, nonmodal, nonresizable covers initially.

Distinct `openDock` parameter dictionaries painted independent left/right child instances. Opening, closing, reopening, and toggling the right ID did not change the left dock's open/closed state. A self-close button in the shared child called `closeDock(str(self.view.params.dockId))`; the right instance closed without closing the left, then the left instance closed independently.

At a 1280px viewport:

| State | Left wrapper | Right wrapper | Primary view |
|---|---:|---:|---:|
| both hidden | x=-260, w=260 | x=1280, w=300 | x=0, w=1280 |
| both cover | x=0, w=260 | x=980, w=300 | x=0, w=1280 |
| left push, right cover | x=0, w=260 | x=980, w=300 | x=260, w=1020 |
| both push | x=0, w=260 | x=980, w=300 | x=260, w=720 |
| left push, right hidden | x=0, w=260 | x=1280, w=300 | x=260, w=1020 |

The official Views API listed the primary plus two same-resource child entries in every state, including when both children were hidden and collapsed. Exact resource-path multiplicity proves configured instance registration, not painted visibility.

In this exact same-resource two-dock test, calling `alterDock` on the left with only `{"content":"push"}` repainted both child instances with their serialized route `viewParams`, replacing the most recent per-instance `openDock` values. A subsequent right alteration retained those serialized values. Do not assume an alteration preserves runtime open parameters; pass and validate the desired `viewParams` when that distinction matters. This result does not establish whether different child resources behave identically.

## Unverified boundary

Do not generalize these results to top/bottom shared docks, multiple shared docks, shared auto initial states, route-local/shared ID collisions, other breakpoint values, device-pixel ratios, orientation changes, runtime `display` changes, `view` replacement, modal combinations beyond the exact right on-demand cover case, resizable cases beyond the exact left on-demand push sequence, cover/modal resizing, resize constraints, `autoHide`, other custom icons, north-anchor combinations beyond the exact visible/push pair, more than two route-local docks, different-resource alteration effects, mobile/touch, keyboard access, rapid resize/call races, reload/reconnect persistence, explicit state restoration, cross-page targeting, Gateway-scope calls, or arbitrary parameter types. Test each separately.
