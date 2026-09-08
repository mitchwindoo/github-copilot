# Perspective Coordinate Container

Use this reference for the live-tested Ignition 8.3.8 Perspective Coordinate Container. The qualified component type is `ia.container.coord`. It places children by `x`, `y`, `width`, and `height` in either fixed-pixel or normalized-percent mode.

## Contents

- [Tested resource shape](#tested-resource-shape)
- [Fixed mode](#fixed-mode)
- [Percent mode](#percent-mode)
- [Percent aspect ratio and letterboxing](#percent-aspect-ratio-and-letterboxing)
- [Runtime mode conversion](#runtime-mode-conversion)
- [Child lifecycle and state](#child-lifecycle-and-state)
- [Scripted access](#scripted-access)
- [Runtime position mutation](#runtime-position-mutation)
- [Geometry, topology, and log proof](#geometry-topology-and-log-proof)
- [API authoring and validation](#api-authoring-and-validation)
- [Runtime validation checklist](#runtime-validation-checklist)
- [Qualification boundary](#qualification-boundary)

## Tested resource shape

The retained fixture used an explicit initial mode, empty aspect ratio, empty pipes, and three Embedded Views:

```json
{
  "type": "ia.container.coord",
  "meta": { "name": "CoordinateContainer" },
  "props": {
    "mode": "fixed",
    "aspectRatio": "",
    "pipes": []
  },
  "children": [
    {
      "type": "ia.display.view",
      "meta": { "name": "CardA" },
      "position": {
        "x": 40,
        "y": 40,
        "width": 240,
        "height": 160
      },
      "props": {
        "path": "Folder/Card View",
        "params": { "label": "A" },
        "style": { "height": "100%", "width": "100%" }
      }
    }
  ]
}
```

The other tested starting rectangles were B `(360,100,300,220)` and C `(760,380,360,180)`. Use numbers, not CSS strings, in the four child `position` members.

The retained test explicitly authored `mode: "fixed"`. Installed examples showed that omitted mode also rendered fixed, but omission was not exercised by the twice-reproduced retained fixture. Keep the explicit value when deterministic authoring matters.

## Fixed mode

Fixed mode treated all four position members as pixels. Resizing the Coordinate Container from an outer width of 1180 to 720 and back did not change authored child positions, painted child rectangles, Embedded View instances, or unbound local state.

The container had a three-pixel border, so its content widths were 1174 and 714. At the narrow width, the furthest child ended at `x + width = 760 + 360 = 1120`; the container's `scrollWidth` became exactly 1120. This reproduced the fixed-mode coordinate-ghost behavior: content can extend to the maximum child right or bottom edge. At the wide width, `scrollWidth` was the 1174-pixel content width because it already exceeded the furthest child edge.

Fixed mode rendered Embedded View wrappers directly beneath the Coordinate Container. The tested root had no direct `.inner-container` and no `.no-zone` elements.

## Percent mode

Percent mode used normalized fractions in the same `position.x`, `position.y`, `position.width`, and `position.height` members. For example, the first fixed rectangle converted to:

```json
{
  "x": 0.0341,
  "y": 0.0576,
  "width": 0.2044,
  "height": 0.2305
}
```

The conversion used the Coordinate Container's content box, not its outer border box: `40 / 1174` became `0.0341`, and `40 / 694` became `0.0576` for the tested 1180-by-700 outer rectangle with a three-pixel border.

Resizing percent mode from outer width 1180 to 720 retained normalized position values and all three Embedded View instances. Horizontal painted positions and widths scaled by the content-width ratio `714 / 1174`; the fixed 700-pixel outer height kept vertical geometry stable.

Percent mode rendered one direct `.inner-container` plus two `.no-zone` elements. Embedded View wrappers were descendants of the inner container rather than direct children of the Coordinate root.

## Percent aspect ratio and letterboxing

In percent mode, a valid colon-separated `props.aspectRatio` constrains `.inner-container` to the largest centered rectangle with that width-to-height ratio inside the Coordinate content box. The two direct `.no-zone` elements occupy the unused space. Child fractions apply to the constrained inner rectangle, not to the full Coordinate root.

The retained aspect fixture used a 1180-by-700 outer rectangle with a three-pixel border, so the content box was 1174 by 694.

With `aspectRatio: "4:3"` at the wide size:

- the inner rectangle was approximately 925.33 by 694;
- the two side no-zones were approximately 124.33 and 124.34 pixels wide;
- the root included `aspect-horizontal` and used row flex direction.

At outer width 720, the content box was 714 by 694. The same `4:3` ratio changed orientation:

- the inner rectangle was exactly 714 by 535.5;
- top and bottom no-zones were each 79.25 pixels high;
- the root included `aspect-vertical` and used column flex direction.

With valid `aspectRatio: "1:1"`, the wide inner rectangle was 694 by 694 with 240-pixel side zones. At outer width 720, it remained 694 by 694 with 10-pixel side zones.

The installed export included `aspectRatio: "1x1"`, but two strict retained runs proved that this value did not constrain the tested Ignition 8.3.8 runtime. It behaved like an empty aspect value: the inner rectangle filled the content box, side no-zones had zero width, the root reported horizontal/row orientation, and normalized children used the full content area. Do not infer runtime support from an installed example's serialized value. Use the tested colon syntax and prove painted geometry.

Changing among `4:3`, invalid/no-constraint `1x1`, valid `1:1`, and empty string did not remount any of the three Embedded Views. Resizing across the 4:3 horizontal/vertical orientation change also retained every instance and unbound local counter. Normalized positions remained stable; the painted card rectangles followed the current inner rectangle exactly:

```text
painted x      = inner x + position.x * inner width
painted y      = inner y + position.y * inner height
painted width  = position.width * inner width
painted height = position.height * inner height
```

The tested narrow 4:3 geometry made some child evidence controls too short for their fixed internal typography. This was not a Coordinate calculation error: the outer Embedded View rectangles matched their normalized positions. Design embedded child content responsively when aspect letterboxing can reduce its bounds.

## Runtime mode conversion

Assigning `coord.props.mode` at runtime converted and wrote all four position members for every child. Two strict runs reproduced these rounding limits:

- fixed to percent wrote fractions rounded to at most four decimal places;
- percent to fixed wrote pixels rounded to at most two decimal places.

Changing from fixed to percent at the wide size preserved painted rectangles within subpixel rounding. Changing back to fixed at the narrow size converted the first rectangle to `(24.35,39.97,145.94,159.97)` and preserved its narrow painted geometry.

Mode conversion is size-dependent and is not a lossless round trip across different sizes. After converting fixed to percent while wide, resizing narrow, converting to fixed, resizing wide, and converting to percent again, the first normalized rectangle became `(0.0207,0.0576,0.1243,0.2305)`. Its fixed pixel geometry had remained narrow-sized while the container widened. Do not toggle modes at arbitrary sizes when the original normalized layout must be preserved; retain a canonical position model outside the container and restore from it deliberately.

## Child lifecycle and state

Every fixed-to-percent and percent-to-fixed transition remounted all three tested Embedded Views. Each new child ran startup once, received a new instance timestamp, and reset its unbound local counter. The wrapper topology change is therefore a lifecycle boundary, not only a CSS layout change.

Resizing without changing mode retained all child instances and local state in both fixed and percent phases. A simultaneous second browser session remained fixed, kept its original child instances, and did not receive session A's local counter or mode changes.

Do not store durable UI state only inside Coordinate children when it must survive mode changes. Store it above the Coordinate Container or in another explicitly qualified persistent source.

## Scripted access

A Button inside a sibling controls container successfully toggled the Coordinate Container with:

```python
coord = self.parent.getSibling("CoordinateContainer")
if coord.props.mode == "fixed":
    coord.props.mode = "percent"
else:
    coord.props.mode = "fixed"
```

The sibling call depends on the tested hierarchy: `self.parent` was the controls container, and the Coordinate Container was that controls container's sibling.

Current child positions were readable after conversion through component-tree access:

```python
coord = self.parent.getSibling("CoordinateContainer")
parts = []
for name in ["CardA", "CardB", "CardC"]:
    child = coord.getChild(name)
    parts.append("%s x=%s y=%s w=%s h=%s" % (
        name,
        child.position.x,
        child.position.y,
        child.position.width,
        child.position.height
    ))
self.view.custom.positionSnapshot = " | ".join(parts)
```

Wait for conversion to settle before reading position values. Revalidate traversal whenever the component hierarchy changes.

## Runtime position mutation

Write the four Coordinate position members directly when changing a child layout at runtime:

```python
child = coord.getChild("TopLeaf")
child.position.x = 80
child.position.y = 50
child.position.width = 210
child.position.height = 90
```

A retained four-child fixture twice reproduced direct member mutation from one fixed layout to another and back from component actions. All four painted rectangles and later captures matched the assigned values exactly. The current Embedded View instances, startup counts, and local state were retained; the recursive pipe tree and SVG structure did not change; a second session remained isolated.

The same four-member pattern is separately qualified inside a page-scoped component message handler for one known child. Two strict runs each applied alternate, canonical, alternate, and canonical layouts. Every handler reached its post-write `COMPLETE` marker, and exact captures plus DOM geometry reproduced `(80,50,210,90)` and `(40,30,240,80)` twice. The three non-target children, recursive pipe, Embedded View instances/startup/local state, and second session remained unchanged, with clean claim-relevant logs and browser diagnostics.

One valid page-scoped batch also scaled this pattern to all four known children: sixteen sequential member assignments per message. Alternate/canonical/alternate/canonical cycles twice reproduced every tuple and painted rectangle while retaining all Embedded View instances, startup/local state, pipe topology, and session isolation. The handler updated a visible target index after each child and reported final completion only after all four.

This sequence is not transactional. A separately retained handler wrote alternate members for `TopLeaf` and `BottomLeaf`, then attempted missing child `MissingChild` before `OriginEnd`. It stopped at visible progress `APPLIED alternate BottomLeaf 2/4` and emitted `AttributeError: 'NoneType' object has no attribute 'position'`. Exact recapture and DOM geometry proved Top/Bottom remained alternate while Origin/Branch remained canonical: earlier writes were not rolled back.

A subsequent valid canonical batch recovered every canonical tuple and rectangle without remounting the four Embedded Views or changing the pipe. A valid alternate batch and second canonical recovery also completed. Validate all targets and values before starting when partial layout is unacceptable; retain per-target progress and a tested recovery action. Other failures, rollback approaches, intermediate paint, concurrency, and rapid re-entry remain unqualified.

One tested existence-prevalidation pattern resolved all requested children into a dictionary before the first position write, collected `None` results, and returned with visible `REJECTED MissingChild BEFORE WRITES` feedback when any target was absent. Two strict runs exercised rejection from both canonical and alternate layouts. Every tuple and DOM rectangle remained exact, no Gateway WARN+ occurred, and later valid alternate/canonical batches still completed without remounts or pipe changes.

Prevalidate more than existence when required. This result does not qualify missing position members, nonnumeric/invalid values, permissions, later assignment failures, concurrency, or rollback.

One tested value-prevalidation extension checked all required `x`, `y`, `width`, and `height` members for every target before the mutation loop. It explicitly rejected Boolean and values outside `(int, long, float)`. With candidate `OriginEnd.width = "wide"`, two strict runs produced visible `REJECTED OriginEnd.width NONNUMERIC BEFORE WRITES` feedback from canonical and alternate states, preserved every property/rectangle exactly, emitted no WARN+, and allowed later valid batches.

This does not establish finite/range/unit validation, NaN/infinity, numeric-string coercion, permissions, or later assignment success. Add and test those checks separately when required.

Do not replace the complete `position` object from a Perspective component action on the tested Ignition 8.3.8 build. Each of four target-specific assignments failed in both directions:

```python
value = system.util.jsonDecode(
    '{"x":80,"y":50,"width":210,"height":90}'
)
coord.getChild("TopLeaf").position = value
```

Every attempt emitted a `perspective.actions.script` WARN whose exception originated at `PropertyTree.merge`:

```text
java.lang.IllegalStateException: Must be executed in execution queue.
```

The eight tested assignments covered `TopLeaf`, `BottomLeaf`, `OriginEnd`, and `BranchLeaf`, once from the authored layout toward an alternate layout and once in the reverse direction. Each failed before changing the targeted child. Exact recaptures, all four DOM rectangles, screenshots, and pixels proved no partial layout write. The failures also retained all child instances and local state.

The V2 target-specific actions intentionally left the Java exception unhandled so the Gateway warning was observable. An earlier preserved Top-only action wrapped the assignment in `try/except Exception`; that Java failure still escaped the handler and the action-result label remained unchanged. This catch boundary is qualified only for that exact Top action and exception. Do not assume another Python exception clause or Java-throwable handling form behaves the same without testing it.

A separately retained page-scoped component-message test did not bypass this boundary. Its receiver incremented a visible count and reached a `START` marker before the same whole-`position` assignment, but never reached `COMPLETE`. Both an equal canonical assignment and a canonical assignment over a known-good alternate member-written layout failed at `PropertyTree.merge` with the same execution-queue exception. The latter retained `TopLeaf=(80,50,210,90)` exactly, proving no partial write. In this execution surface, the warning logger was `com.inductiveautomation.perspective.ComponentModel` and the traceback included `MessageHandlerCollection$MessageHandlerImpl`; component actions used `perspective.actions.script` instead.

Do not infer from the exception text that a component message handler is the required execution queue. For the exact receiver serialization and sender/handler evidence pattern, use [perspective-component-messages.md](perspective-component-messages.md).

Use direct member writes as the tested runtime pattern. Keep explicit capture separate from mutation: action-edge DOM geometry settled before the previously captured layout label changed.

## Geometry, topology, and log proof

At every mode or resize edge, record:

- exact viewport, document, Coordinate outer rectangle, content dimensions, and scroll dimensions;
- every child rectangle and computed absolute left/top/width/height;
- displayed mode and all four runtime position values per child;
- direct-child classes, `.inner-container` count, and `.no-zone` count;
- child startup count, instance timestamp, and unbound local counter;
- exact URL, original-resolution screenshot, console errors, page errors, and failed requests;
- official sessions and mounted-view topology;
- a bounded official Gateway WARN-or-higher log query.

The strict fixture kept two active browser sessions, two pages, and five official mounted-view records per page at every edge. Official topology remained registered across remounts, so instance/startup evidence was necessary to prove lifecycle replacement.

Query logs again after the browser closes and official active browser pages reach zero. HTTP 200 is only a shell-level route observation: an early installed-sample attempt received 200 for guessed child-view URLs that never mounted a Coordinate Container. Derive client routes from exported page configuration and require the expected component and official topology to appear.

## API authoring and validation

Use the authenticated official project export/import and scan-lock operations exposed by the live OpenAPI document when whole-project import is the selected workflow. Require a declared delta, tokenless rejection, authenticated success, exact export readback, route activation, protected-resource parity, stable project inventory, and bounded logs.

`llmImport` is optional and project-scoped. Read its health response and require an action in `availableActions` before calling its POST route. Do not add a Coordinate-specific action when official project import or an existing general folder-resource action is sufficient. If `llmImport` is absent, continue with official OpenAPI capabilities.

Use browser automation only after API authoring, for rendering, screenshots, exact geometry, bounded interactions, diagnostics, and correlation with official topology and logs.

## Runtime validation checklist

1. Export the approved project, declare the exact route and view delta, and author through an authenticated API operation.
2. Verify exact mode, aspect ratio, pipes, child identity, Embedded View path/parameters, and all four starting position members in export readback.
3. Open two independent sessions. Capture positions and increment one child in initial fixed mode.
4. Resize fixed mode narrow and wide; require absolute geometry, position values, instances, and local state to remain unchanged. Validate coordinate-ghost scroll dimensions.
5. Toggle to percent while wide; require four-decimal normalized writeback, the inner/no-zone topology, painted-geometry continuity, child remount/startup, and local-state reset.
6. Resize percent mode narrow; require stable normalized values, content-ratio geometry scaling, and retained instances. Mutate one child's local state.
7. Toggle to fixed while narrow; require two-decimal pixel writeback, direct-child topology, painted-geometry continuity, remount/startup, and state reset.
8. Resize fixed wide and toggle percent again; prove size-dependent conversion rather than assuming round-trip restoration.
9. At every edge save screenshots, geometry, exact URLs, browser diagnostics, official topology, and bounded Gateway logs. Query logs again after delayed zero-page cleanup.
10. Repeat the entire sequence independently, then re-export target and protected resources and require exact parity with the accepted baseline.

For a percent aspect-ratio test, keep mode and child fractions constant. Exercise a wide and narrow `4:3` container, valid `1:1`, the required empty/no-constraint state, and any serialized syntax that must be treated as a negative. At every edge assert the content-box-derived inner rectangle, both no-zone rectangles, orientation class/flex direction, normalized card geometry, retained instances/state, isolated second session, screenshots, topology, diagnostics, and bounded logs.

## Qualification boundary

This child-position and aspect-ratio reference does not qualify omitted `mode` in the retained fixture, fixed-mode aspect ratio, separators other than tested colon syntax and the tested invalid `1x1` negative, whitespace/case variants, invalid/zero/negative ratios, delegated connectors, successful whole-`position` object replacement, non-JSON-decoded whole objects, whole-object assignment from handler scopes other than the tested page scope or from other threads, deferred/invoked-later assignment, omitted/extra position members, alternative exception-catching forms, `position.rotate.anchor`, actual visual transforms, negative or out-of-range coordinates, overlap hit testing, z-index, vertical overflow beyond the tested coordinate ghost, runtime child creation/removal, nested Coordinate Containers, non-Embedded-View children, tag/property bindings, output parameters, navigation, asynchronous scripts, rapid toggles or aspect changes, touch behavior, keyboard movement, focus restoration, accessibility conformance, security policies, or other Ignition builds. For the separately qualified non-empty recursive pipe shape, use [perspective-coordinate-pipes.md](perspective-coordinate-pipes.md). Test every other pipe form separately before relying on it.
