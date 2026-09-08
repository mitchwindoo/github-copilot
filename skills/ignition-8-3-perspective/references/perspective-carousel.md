# Perspective Carousel

Use this reference only after confirming Ignition 8.3.8 or reproducing the behavior on the installed build. It qualifies one installed-source `ia.display.carousel` with three ordered descriptors and one parameterized child view. Do not infer Carousel behavior from View Canvas, Flex Repeater, Tab Container, Ignition 8.1, or documentation alone.

## Tested component shape

The tested component preserved this descriptor structure inside `props.views`:

```json
{
  "viewPath": "path/to/child",
  "viewParams": {"instance": 1},
  "alignItems": "flex-start",
  "direction": "row",
  "justify": "flex-start"
}
```

The array contained three descriptors in instance order 1, 2, 3. The parent used a 384-pixel flex basis. Preserve the complete live-discovered component and descriptor objects; this is not a minimal schema.

When adapting an installed resource, change only the approved child paths and retain order, parameters, alignment, direction, justification, geometry, and omitted/default members. The resource manifest's `files` array must match the included files exactly; do not retain a thumbnail declaration without thumbnail data.

## Rendered controls and geometry

At a 1400-by-950 viewport, the tested Carousel painted at 1400 by 384. Its active child card painted at x 45, y 100 with size 1310 by 360. The two arrow anchors occupied the left and right edges, and three dot anchors painted beneath the card. Endpoint arrows acquired a disabled class and muted paint.

Scope interaction locators beneath the page-local Carousel. Identify arrows by their contained material `arrow_back` or `arrow_forward` icon and dots by `data-index`. Do not use a global anchor index.

The tested pointer transitions centered the target in roughly 562–589 milliseconds. Treat that as an observation, not a configured or universal duration. Always wait for settled geometry, visible text, active-dot state, official topology, and bounded logs.

## Lazy cumulative child lifecycle

The tested Carousel mounted only descriptor index 0 initially. First visiting index 1 mounted child `[1]`; first visiting index 2 mounted `[2]`. Previously visited children stayed mounted when off-screen.

A direct dot jump from index 0 to index 2 produced mounts `[0,2]`; it did not instantiate unvisited index 1. Therefore reconcile mounted views as a visited-descriptor set, not as the active child alone or a prefix through the highest index.

For the tested page, each newly visited child added one official view, two components, one binding, and its own mount path. Rendered visibility alone cannot prove that off-screen child views are absent.

## Reload, fresh-session, and isolation boundaries

Same-session reload retained the exact tested active index, the same session ID, the same page ID, and every previously visited child mount. Fresh sessions opened after exact prior-session termination began at descriptor index 0 with only child `[0]` mounted.

Two simultaneous browser sessions had independent active indices and visited-child sets. Exact official termination of one session did not change the other session.

Do not assume reload reset or persistence. Observe the active dot, rendered child, session/page identity, official child mount paths, and bounded logs before classifying the behavior.

## Automatic movement and accessibility

No automatic advance occurred during the tested 12-second untouched interval with the installed shape. This qualifies only that observation; it does not prove other Carousel configurations cannot cycle automatically.

The tested arrows and dots were anchor elements without `href`, semantic role, accessible name, `aria-label`, or title. The accessibility tree exposed unnamed images. Do not claim keyboard, focus, or screen-reader usability unless accessible controls are added and independently tested.

## Runtime whole-list descriptor replacement

One separately tested fixture changed `props.views` from page-local Button action scripts. The accepted pattern copied the Perspective collection to a Python list, mutated the copy, and assigned the complete list back:

```python
carousel = self.parent.parent.getChild('Carousel')
views = list(carousel.props.views)
views.append(newDescriptor)
carousel.props.views = views
```

The same fixture used list `pop`, list `reverse`, and exact literal-list reset before whole-list reassignment. It did not qualify direct `ArrayWrapper` mutation. A sibling expression binding `len({../Carousel.props.views})` tracked the descriptor count in agreement with painted dot count.

Adding an unvisited descriptor added its dot and count without mounting its child. First visiting that index mounted it. Each first visit added one official child view, two components, and one binding in the tested child contract.

Reversing four fully visited descriptors preserved the numeric active index rather than descriptor identity. With index 3 active, `[1,2,3,4]` became `[4,3,2,1]` and the visible content changed from View 4 to View 1. Existing mount paths stayed index-based, while their parameter-driven content updated in place.

Removing an active last descriptor clamped the active index to the new last index and removed the deleted mount. Removing an inactive last descriptor left the active index/content unchanged. Exact reset preserved an active index that remained valid and rewrote retained mount content by index.

Visited-index history remained in the live component after descriptor removal. Re-adding a previously visited last index mounted it immediately even while another index was active. Do not derive mount state only from the current descriptor list or visible child.

Same-session reload retained the tested runtime descriptor array, active index, page identity, and all official mounted views. Immediately after reload, the browser DOM contained only the active child node while the official Views API still reported every retained mount and unchanged component/binding totals. Treat client DOM presence and Gateway mount presence as separate evidence layers.

A fresh session began from the authored array and initial mount. Two sessions maintained independent arrays, active indices, and visited-index state. In a fresh session, direct index-0-to-index-3 navigation followed by removing the active last descriptor clamped to index 2 with mounts `[0,2]`; the skipped index 1 remained unmounted.

Page-local mutation Buttons had accessible names in the tested fixture. This does not repair the Carousel's unnamed native arrows and dots.

## Multi-step form boundary

For the separately tested heterogeneous Text Field, Numeric Entry, and Summary wizard, see [perspective-carousel-wizard.md](perspective-carousel-wizard.md). Its evidence establishes that child `inout` writeback can update a descriptor while later parent replacement of a descriptor's `viewParams` is not a reactive parent-to-child delivery channel in the tested build.

## Validation workflow

1. Extract the exact parent, descriptor array, child parameter/binding contract, manifest, and dependencies with explicit UTF-8.
2. Author through the approved API with tokenless rejection, exact delta, semantic readback, route, protected/inventory/helper, and bounded authoring-log gates.
3. Capture initial and every settled slide screenshot. Measure Carousel/card geometry, active dot, arrow disabled state, clipping, quality, connection state, and browser diagnostics.
4. Query official mounted-view topology before and after each first visit. Reconcile view, component, and binding counts with child mount paths.
5. Exercise both arrows and every dot with page-local locators. Query and classify a bounded official WARN-or-higher window after every edge.
6. Observe an untouched interval before claiming automatic behavior. Test same-session reload and fresh-session baseline without assuming either outcome.
7. Run two simultaneous sessions with different active and visited-child states. Terminate one exact session and prove the other remains unchanged.
8. Terminate every test session through the exact official API, inspect termination and post-close logs, run two strict reproductions, and bracket final work with project/protected no-drift exports.
9. For runtime descriptor changes, capture descriptor count, dot count, numeric active index, visible content, mount-index-to-parameter mapping, DOM presence, official mount paths, page metrics, and session/page identity after every mutation.

## Qualification boundary

This reference qualifies the tested three-descriptor installed shape plus one exact three-to-four whole-list mutation fixture: ordered String-like input parameters, pointer arrows/dots, lazy cumulative visited-child mounting, direct nonadjacent jumps, list-copy add/pop/reverse/reset reassignment, numeric-index preservation/clamping, index-based content remapping, visited-index memory after remove/re-add, same-session runtime-list retention, DOM-versus-official-mount separation after reload, fresh-session baseline, two-session isolation, roughly observed transition timing, exact-session cleanup, geometry, screenshots, topology, and logs on Ignition 8.3.8. It does not qualify reactive parent-to-child delivery from later descriptor `viewParams` replacement; the separately tested wizard disproved that assumption for its exact pattern. It also does not qualify arbitrary descriptor counts beyond four, direct `ArrayWrapper` mutation, dynamic paths, invalid/empty descriptors, removal to zero, missing children, other parameters or alignments, automatic interval configuration, looping, swipe/touch, rapid or concurrent mutation during transition, keyboard control, accessible native controls, nested Carousels, external child projects, other writeback patterns, Designer behavior, performance limits, other configurations, or other builds.
