# Perspective Coordinate Pipes

Use this reference for the twice-reproduced Ignition 8.3.8 recursive pipe tree, nested branch-mutation and conversion, canonical pipe-and-child-layout restoration, two-independent-pipe, and runtime-added third-pipe fixtures in a Perspective Coordinate Container. Read [perspective-coordinate-container.md](perspective-coordinate-container.md) first for the container's fixed/percent position model and mode-transition lifecycle.

## Contents

- [Tested pipe shape](#tested-pipe-shape)
- [Recursive point tree](#recursive-point-tree)
- [Rendered SVG structure](#rendered-svg-structure)
- [Visibility changes](#visibility-changes)
- [Multiple independent pipes](#multiple-independent-pipes)
- [Runtime array mutation](#runtime-array-mutation)
- [Runtime insertion and three-pipe order](#runtime-insertion-and-three-pipe-order)
- [Runtime recursive branch mutation](#runtime-recursive-branch-mutation)
- [Runtime-expanded branch conversion](#runtime-expanded-branch-conversion)
- [Canonical pipe and child layout restoration](#canonical-pipe-and-child-layout-restoration)
- [Fixed and percent conversion](#fixed-and-percent-conversion)
- [Child lifecycle and session isolation](#child-lifecycle-and-session-isolation)
- [Scripted access](#scripted-access)
- [Runtime validation](#runtime-validation)
- [API boundary](#api-boundary)
- [Qualification boundary](#qualification-boundary)

## Tested pipe shape

The retained Coordinate Container used one explicit pipe beneath `props.pipes`:

```json
{
  "type": "ia.container.coord",
  "meta": { "name": "CoordinateContainer" },
  "props": {
    "mode": "fixed",
    "aspectRatio": "",
    "pipes": [
      {
        "appearance": "simple",
        "end": "none",
        "fill": "#2563eb",
        "flanges": false,
        "lineVariant": "solid",
        "name": "MainPipe",
        "origin": {
          "x": 800,
          "y": 160,
          "connections": [
            {
              "x": 500,
              "y": 160,
              "connections": [
                {
                  "x": 500,
                  "y": 80,
                  "connections": [{ "x": 140, "y": 80 }]
                },
                {
                  "x": 500,
                  "y": 400,
                  "connections": [{ "x": 140, "y": 400 }]
                }
              ]
            }
          ]
        },
        "start": "none",
        "stroke": "",
        "visible": true,
        "width": 12
      }
    ]
  }
}
```

Keep every tested member explicit. This shape qualifies only the `simple` appearance, no start/end decorations, no flanges, solid line variant, one fill color, one width, and one visible recursive tree.

## Recursive point tree

The pipe begins at `origin`. Every point may contain a `connections` array whose members use the same recursive point shape. The retained tree had six points:

```text
origin (800,160)
└── junction (500,160)
    ├── top turn (500,80)
    │   └── top leaf (140,80)
    └── bottom turn (500,400)
        └── bottom leaf (140,400)
```

Do not flatten the tree into a list. Preserve the nested `connections` arrays in exact export readback and traverse the same hierarchy when reading or mutating it at runtime.

## Rendered SVG structure

With `visible: true`, the tested pipe rendered one `svg.ia_piping`. Two strict runs reproduced 41 captured descendants:

- 20 `rect` elements;
- 12 `g` elements;
- 9 `circle` elements.

The primary group had:

```html
<g data-fill="#2563eb" class="ia_pipe ia_pipeIsolate pipe-blend-mode-lighten">
```

The SVG also contained generated mask IDs, `ia_pipeSegment`, `ia_pipeSegmentNode`, `ia_pipeSegmentOverlay`, and mask rectangles. Treat generated IDs as runtime values; assert stable class/attribute structure and geometry instead of hard-coding an ID.

In the initial fixed-wide state, the Coordinate outer box was 1000 by 600 with a three-pixel border and a 994-by-594 content box. The SVG bounding box filled that content box, while its inline style described the pipe's maximum positive extent as `width: 800px; height: 406px`. At a 700-pixel outer width, the fixed pipe retained the 800-pixel inline extent and contributed horizontal overflow.

Use both DOM attributes and painted screenshots. An SVG bounding rectangle alone did not expose all internal mask changes.

## Visibility changes

Assigning the nested member directly worked:

```python
p = self.parent.getSibling("CoordinateContainer").props.pipes[0]
p.visible = not p.visible
```

At `visible: false`, the runtime kept one empty `svg.ia_piping` shell and removed all 41 captured pipe descendants. It did not remove the SVG element itself. The Coordinate's three Embedded View endpoints retained their instances and local state.

At `visible: true`, the runtime rebuilt the 41 descendants without remounting the endpoints. In both strict runs, restoring visibility while narrow changed the SVG bounding width from the prior 800-pixel fixed extent to the 694-pixel content width. Its rebuilt inline SVG style and background mask dimensions were zero even though the pipe painted:

```html
<svg class="ia_piping" style="width: 0px; height: 0px;">
```

Do not treat pipe visibility, SVG existence, or an HTTP 200 response as sufficient proof. Require the expected descendant structure, screenshot, geometry, browser diagnostics, official topology, and Gateway logs after both hide and restore.

## Multiple independent pipes

A second retained fixture proved that `props.pipes` accepts two explicit independent `simple` pipes. The tested shapes were:

```json
[
  {
    "appearance": "simple",
    "end": "none",
    "fill": "#2563eb",
    "flanges": false,
    "lineVariant": "solid",
    "name": "BlueHorizontal",
    "origin": {
      "x": 850,
      "y": 180,
      "connections": [{ "x": 120, "y": 180 }]
    },
    "start": "none",
    "stroke": "",
    "visible": true,
    "width": 18
  },
  {
    "appearance": "simple",
    "end": "none",
    "fill": "#d97706",
    "flanges": false,
    "lineVariant": "solid",
    "name": "AmberVertical",
    "origin": {
      "x": 500,
      "y": 430,
      "connections": [{ "x": 500, "y": 60 }]
    },
    "start": "none",
    "stroke": "",
    "visible": true,
    "width": 12
  }
]
```

The lines crossed at `(500,180)`. The runtime rendered one shared `svg.ia_piping`, not one SVG per pipe. With both visible, the SVG contained two direct primary groups in array order:

```html
<g data-fill="#2563eb" class="ia_pipe ia_pipeIsolate pipe-blend-mode-lighten">...</g>
<g data-fill="#d97706" class="ia_pipe ia_pipeIsolate pipe-blend-mode-lighten">...</g>
```

The simple one-segment fixture produced three rectangles and four groups across the SVG. Each primary pipe group had two descendants. Hiding either pipe produced one primary group in the surviving pipe's original array position and reduced the captured SVG to two rectangles and two groups.

The later amber pipe painted over the earlier blue pipe at the crossing. Original-resolution pixel samples reproduced these exact RGBA values in both strict runs:

- both visible: amber `(217,119,6,255)`;
- pipe 0 hidden: amber `(217,119,6,255)`;
- pipe 1 hidden: blue `(37,99,235,255)`;
- each restore: amber `(217,119,6,255)`.

This proves ordering only for the tested two direct `simple` groups with these colors, widths, and a perpendicular crossing. Do not generalize it to other appearances, overlap modes, strokes, collinear segments, or runtime array reorder.

Direct indexed visibility changes were independent:

```python
p0 = self.parent.getSibling("CoordinateContainer").props.pipes[0]
p0.visible = not p0.visible

p1 = self.parent.getSibling("CoordinateContainer").props.pipes[1]
p1.visible = not p1.visible
```

The surviving pipe and all four Embedded View markers retained their instances and local state. Restoring either pipe rebuilt both direct groups in original blue-then-amber order without remounting markers.

The shared SVG's inline extent metadata lagged one visibility edge in a repeatable way. Before visibility changes at the narrow size, it was `850px` by `430px`. Restoring blue while amber was already visible produced `506px` by `430px`, matching the previously visible amber extent. Restoring amber while blue was already visible produced `850px` by `189px`, matching the previously visible blue extent. Both groups nevertheless painted. Resizing wide recomputed the combined `850px` by `430px` extent.

Treat this as an observation boundary, not as a safe sizing contract. After a visibility mutation, verify current inline dimensions, SVG bounding geometry, both group structures, and the screenshot. Triggering a resize happened to recompute the combined extent in the tested fixture; do not rely on that as a production workaround without a dedicated test.

## Runtime array mutation

The retained two-pipe fixture also qualified guarded runtime reorder, removal, and canonical restoration of `props.pipes`. The Perspective property value was an Ignition `ArrayWrapper`, not a Python list. Calling an in-place list method failed and left the array unchanged:

```python
coord = self.parent.getSibling("CoordinateContainer")
try:
    coord.props.pipes.reverse()
except AttributeError as exc:
    self.view.custom.actionResult = "ACTION INPLACE ERROR %s" % exc
```

The twice-reproduced exception was:

```text
AttributeError: 'com.inductiveautomation.perspective.gateway.script' object has no attribute 'reverse'
```

Copy the wrapper into a Python list, mutate the copy, and reassign the complete property:

```python
coord = self.parent.getSibling("CoordinateContainer")
pipes = list(coord.props.pipes)
pipes.reverse()
coord.props.pipes = pipes
```

This changed the runtime array from blue-then-amber to amber-then-blue. The direct SVG primary groups followed that new array order, and the crossing pixel changed from amber `(217,119,6,255)` to blue `(37,99,235,255)`. All four Embedded View marker instances and their local state were retained.

Structural removal used the same copy-and-reassign rule:

```python
coord = self.parent.getSibling("CoordinateContainer")
pipes = list(coord.props.pipes)
removed = pipes.pop(1)
coord.props.pipes = pipes
```

After reversal, removing index 1 removed `BlueHorizontal`; the one remaining direct SVG group was amber, and the crossing pixel was amber. No marker remounted.

Restore from a separately held canonical JSON value when exact original order and members matter:

```python
coord = self.parent.getSibling("CoordinateContainer")
coord.props.pipes = system.util.jsonDecode(canonicalPipesJson)
```

The tested restore returned the exact blue-then-amber array and original values. Do not treat a live `ArrayWrapper` reference as the canonical backup.

A direct member assignment still settled correctly after reorder, but a read of that same member later in the same action script returned the prior value:

```python
p = coord.props.pipes[0]
p.visible = not p.visible
# p.visible observed here was the pre-write value in the tested action.
```

The settled DOM and next capture reflected the write. After reversal, index 0 referred to `AmberVertical`; hiding it left only blue, and restoring it returned amber-then-blue group order with blue painted over amber. Publish immediate feedback from the intended value or wait for a later settled read; do not use same-script member readback as commit proof.

Whole-array mutation retained the shared SVG element. Its inline extent metadata again lagged the current content: removal of blue retained the prior combined `850px` by `430px` extent; restoring both pipes after amber-only produced `506px` by `430px`; a later narrow/wide resize recomputed `850px` by `430px`. Require painted screenshots, direct-group structure, current pixel evidence, and geometry rather than trusting inline extent metadata alone.

## Runtime insertion and three-pipe order

Treat `ArrayWrapper` methods as individually qualified. The same wrapper that lacked `reverse()` accepted a direct `append()` of one JSON-decoded pipe:

```python
coord = self.parent.getSibling("CoordinateContainer")
green = system.util.jsonDecode(greenPipeJson)
coord.props.pipes.append(green)
```

The tested third pipe was explicit:

```json
{
  "appearance": "simple",
  "end": "none",
  "fill": "#16a34a",
  "flanges": false,
  "lineVariant": "solid",
  "name": "GreenDiagonal",
  "origin": {
    "x": 250,
    "y": 430,
    "connections": [{ "x": 600, "y": 80 }]
  },
  "start": "none",
  "stroke": "",
  "visible": true,
  "width": 10
}
```

It crossed the blue horizontal and amber vertical pipes at `(500,180)`. Direct append produced exact property and direct-group order:

```text
BlueHorizontal, AmberVertical, GreenDiagonal
#2563eb, #d97706, #16a34a
```

The last green group painted over both earlier groups. Original-resolution crossing samples were green `(22,163,74,255)` in both strict runs.

List-copy append plus whole-array reassignment produced the same three-entry order and green crossing pixel:

```python
pipes = list(coord.props.pipes)
pipes.append(system.util.jsonDecode(greenPipeJson))
coord.props.pipes = pipes
```

Insert at index 1 through a Python list when index placement matters:

```python
pipes = list(coord.props.pipes)
pipes.insert(1, system.util.jsonDecode(greenPipeJson))
coord.props.pipes = pipes
```

This produced:

```text
BlueHorizontal, GreenDiagonal, AmberVertical
#2563eb, #16a34a, #d97706
```

Amber remained the last group and painted at the crossing as `(217,119,6,255)`. The runtime used one shared `svg.ia_piping` with three direct primary groups; it did not create a separate SVG for the inserted pipe.

After index-1 insertion, indexed access immediately referred to `GreenDiagonal`. Direct visibility assignment hid and restored only green. As with the reordered two-pipe fixture, same-action `p.visible` readback exposed the prior value; the next capture and settled DOM exposed the committed value. List-copy `pop(1)` plus reassignment removed `GreenDiagonal` and restored the exact original blue-then-amber array.

All four Embedded View markers retained instance IDs, startup counts, and local state across direct append, list append, index-1 insertion, indexed visibility, removal, JSON restoration, and resize. A second browser session stayed at the original two-pipe state. Each tested page retained six official mounted-view records.

The shared SVG extent metadata remained non-authoritative. Initial and three-pipe addition edges reported `850px` by `430px`. Resetting or removing the visible diagonal reported `850px` by `433.536px`, reflecting the prior diagonal's rotated bounding extent even though only blue and amber remained. Restoring green after a hide returned `850px` by `430px`; a later narrow/wide resize also recomputed the original two-pipe `850px` by `430px` extent. Validate current groups, pixels, bounding geometry, and screenshots instead of using inline width/height as a membership test.

## Runtime recursive branch mutation

The retained one-pipe fixture also qualified mutation of the junction's nested `connections` array. Start from the exact six-point tree in [Recursive point tree](#recursive-point-tree), validate the expected hierarchy, and obtain the junction explicitly:

```python
coord = self.parent.getSibling("CoordinateContainer")
pipe = coord.props.pipes[0]
junction = pipe.origin.connections[0]
```

The nested property value was also an Ignition `ArrayWrapper`. Its direct `append()` accepted a JSON-decoded recursive branch:

```python
branch = system.util.jsonDecode(
    '{"x":700,"y":280,"connections":[{"x":850,"y":280}]}'
)
junction.connections.append(branch)
```

This produced an appended branch at index 2:

```text
B0=500,80>140,80
B1=500,400>140,400
B2=700,280>850,280
```

Do not infer that every `ArrayWrapper` supports every Python-list method. The tested top-level wrapper accepted `append()` but rejected `reverse()` in a separate fixture. Treat each wrapper method, nesting level, and value shape as independently qualified.

List-copy mutation plus reassignment also worked for the nested array:

```python
branches = list(junction.connections)
branches.append(system.util.jsonDecode(branchJson))
junction.connections = branches
```

Insert at the tested index when branch order matters:

```python
branches = list(junction.connections)
branches.insert(1, system.util.jsonDecode(branchJson))
junction.connections = branches
```

The settled recursive order became:

```text
B0=500,80>140,80
B1=700,280>850,280
B2=500,400>140,400
```

Exact removal used the same copy-and-reassign form:

```python
branches = list(junction.connections)
removed = branches.pop(1)
junction.connections = branches
```

The twice-reproduced removed coordinates were `700,280>850,280`, and the remaining tree exactly matched the original two branches. To restore the complete model independently of current wrapper state, assign a separately held canonical JSON array to `coord.props.pipes`:

```python
coord.props.pipes = system.util.jsonDecode(canonicalPipesJson)
```

The retained snapshot label was an explicit capture, not a reactive binding. It continued to show the prior tree immediately after each mutation or reset and changed only after the separate capture action. Do not use a previously captured custom value as mutation readback; recapture the live hierarchy after the action has settled.

The original tree rendered 41 captured SVG descendants: 20 rectangles, 12 groups, and 9 circles, with 26 children beneath the one direct primary pipe group. Adding the two-point branch produced 56 descendants: 28 rectangles, 16 groups, and 12 circles, with 36 primary-group children. It remained one `svg.ia_piping` and one blue direct primary group; a nested branch does not create another primary pipe group.

Original-resolution screenshots and a pixel at Coordinate-local `(780,280)` proved paint state. The sample was background `(226,232,240,255)` initially and after reset/removal, and blue `(37,99,235,255)` after direct append, list-copy append, and index-1 insertion. All four Embedded View markers retained instance IDs, startup counts, and local state across every mutation, reset, capture, and resize. A second browser session remained at the original tree, and each page retained six official mounted-view records.

Inline SVG extent metadata again lagged the current model. The original and branch-addition action edges reported `800px` by `406px`; the immediately following reset reported `850px` by `406px`, reflecting the branch that had just been removed. A later branch addition returned `800px` by `406px`, and its removal again retained `850px` by `406px`. A narrow/wide resize recomputed the original `800px` by `406px` extent. Treat this as a repeatable one-edge observation in this fixture, not a sizing contract or a membership test.

## Runtime-expanded branch conversion

A separate retained fixture twice reproduced fixed/percent conversion after directly appending the exact two-point branch from [Runtime recursive branch mutation](#runtime-recursive-branch-mutation). This qualifies one interaction sequence: append at junction branch index 2 while fixed and wide, convert the expanded eight-point tree to percent, resize percent mode narrow, convert back to fixed while narrow, resize fixed mode wide, then restore canonical pipe JSON.

At the 994-by-594 wide content size, the expanded fixed tree was:

```text
O=800,160 J=500,160
B0=500,80>140,80
B1=500,400>140,400
B2=700,280>850,280
```

Fixed-to-percent converted all eight points and preserved branch index 2:

```text
O=0.8048,0.2694 J=0.503,0.2694
B0=0.503,0.1347>0.1408,0.1347
B1=0.503,0.6734>0.1408,0.6734
B2=0.7042,0.4714>0.8551,0.4714
```

The added coordinates use the same independent content-box math as authored points: `700 / 994 -> 0.7042`, `850 / 994 -> 0.8551`, and `280 / 594 -> 0.4714`. Resizing percent mode to a 694-by-594 content box retained those normalized values and scaled the painted branch.

Percent-to-fixed conversion at that narrow content size produced:

```text
O=558.53,160.02 J=349.08,160.02
B0=349.08,80.01>97.72,80.01
B1=349.08,400>97.72,400
B2=488.71,280.01>593.44,280.01
```

The added coordinates again follow the same math: `0.7042 * 694 -> 488.71`, `0.8551 * 694 -> 593.44`, and `0.4714 * 594 -> 280.01`. A later wide resize in fixed mode retained all narrow-scaled values. Runtime-added points are not exempt from the Coordinate's size-dependent, non-lossless mode round trip.

The expanded state retained one `svg.ia_piping`, one blue primary group, 56 captured descendants, and 36 primary-group children through both conversions and the percent resize. Branch paint survived at the expected original and scaled positions. Eight twice-reproduced pixel checks used background `(226,232,240,255)` and blue `(37,99,235,255)` to prove:

- no branch initially;
- blue branch after fixed append and wide percent conversion;
- blue branch at the scaled narrow percent and fixed positions;
- the scaled branch remains after a later wide fixed resize while its original wide location is empty;
- canonical restoration removes the branch.

Each mode transition remounted all four Embedded View markers, ran startup once on each replacement, and reset local state. Append, explicit capture, same-mode resize, canonical pipe restoration, and later fixed resize retained the current marker instances. The second browser session remained at the original fixed six-point tree with its initial marker instances and state.

Canonical pipe restoration is scoped to `coord.props.pipes`:

```python
coord.props.pipes = system.util.jsonDecode(canonicalPipesJson)
```

It restored the original six pipe points but did not restore Coordinate child positions or sizes that had been converted during the narrow round trip. In the tested visual fixture, marker width began at 240 fixed pixels, converted to about 167.53 pixels while narrow, became 167.52 fixed pixels after percent-to-fixed conversion, and remained 167.52 after pipe restoration and a later wide resize. Preserve and restore a separate canonical child layout if both pipe and child geometry must return to the authored model.

Screenshot review is a functional gate, not decoration. The first authored fixture used 160-pixel marker widths; narrow percent conversion reduced them to about 112 pixels and made their fixed child text overlap and clip. Before strict testing, an API-only resource update increased authored marker width to 240 pixels and moved the right-side markers inward. Narrow percent width then became about 167.53 pixels, the text remained readable, and the rightmost marker stayed inside the Coordinate. Save the rejected screenshots and correction evidence; DOM, logs, and assertions can all be clean while the screen is still poorly designed.

Inline SVG extent metadata remained non-authoritative across this interaction. The original and appended fixed edges reported `800px` by `406px`; converted wide percent reported `849.97px` by `406px`; narrow percent and narrow-scaled fixed states reported `593.44px` by `406px`. Restoring the canonical six-point pipe retained stale `593.44px` width until a later resize recomputed `800px`. Use current recursive capture, SVG structure, geometry, screenshots, and pixels together.

## Canonical pipe and child layout restoration

A subsequent retained fixture twice reproduced complete restoration after the expanded-tree, cross-size mode round trip. The tested action order was pipe first, then exact direct writes to every child position member:

```python
coord = self.parent.getSibling("CoordinateContainer")
coord.props.pipes = system.util.jsonDecode(canonicalPipesJson)

layout = {
    "TopLeaf": (40, 30, 240, 80),
    "BottomLeaf": (40, 350, 240, 80),
    "OriginEnd": (740, 110, 240, 80),
    "BranchLeaf": (720, 330, 240, 80)
}
for name in ["TopLeaf", "BottomLeaf", "OriginEnd", "BranchLeaf"]:
    child = coord.getChild(name)
    x, y, width, height = layout[name]
    child.position.x = x
    child.position.y = y
    child.position.width = width
    child.position.height = height
```

Before this action, the retained control state required both restorations: the canonical-size branch had been re-appended to the pipe, while all four children still had the narrow-converted fixed layout. The captured scaled layout was:

```text
TopLeaf=27.9,30,167.53,80.01
BottomLeaf=27.9,349.98,167.53,80.01
OriginEnd=516.68,110.01,167.53,80.01
BranchLeaf=502.66,330.03,167.53,80.01
```

The combined action removed the runtime-added branch and restored the exact authored child members shown in the script. Settled DOM geometry already showed the four 240-pixel-wide authored rectangles before a separate capture action refreshed the displayed tree and layout snapshots. A pipe-only control restored the six-point tree but retained every scaled child member, proving the child result did not come from pipe replacement or resize.

The combined action retained all current fixed-phase Embedded View instance timestamps, startup counts, and local state. It did not introduce another remount boundary. Later fixed-mode narrow and wide resizes retained the authored child members. The second browser session remained at the initial tree and layout throughout.

Pipe replacement again left stale shared-SVG extent metadata: removing the re-appended branch reported `850px` by `406px` until a later resize recomputed `800px` by `406px`. Validate live tree capture, child member capture, painted rectangles, SVG structure, screenshots, instances, official topology, and logs together.

Do not read a previously captured label as same-action commit proof. In the retained fixture, the explicit tree and layout snapshot labels still showed their prior values immediately after the combined action and changed only after the separate capture action. The DOM had already settled to the restored geometry.

One invalid discovery run crossed the Gateway trial-expiration boundary. Five Gateway-scoped clicks were ignored with browser console messages containing `No connection to Gateway`; no page error, request failure, or Gateway WARN was required for this failure mode. Archive the run, reject all later interaction evidence from that session, re-check `/data/api/v1/trial`, open fresh browser sessions, and repeat the complete sequence after the trial is active. Always gate every run on browser console diagnostics even when the page continues to paint.

## Fixed and percent conversion

Changing `Coordinate.props.mode` recursively converted every point in the pipe tree in addition to child positions.

Starting from the 994-by-594 content box, fixed to percent produced four-decimal point values:

```text
O=0.8048,0.2694
J=0.503,0.2694
T=0.503,0.1347
TL=0.1408,0.1347
B=0.503,0.6734
BL=0.1408,0.6734
```

The math used the content box independently by axis: `800 / 994 -> 0.8048`, `160 / 594 -> 0.2694`, and so on.

Resizing percent mode to a 700-by-600 outer box used its 694-by-594 content box for paint. Converting back to fixed at that narrow size produced two-decimal values:

```text
O=558.53,160.02
J=349.08,160.02
T=349.08,80.01
TL=97.72,80.01
B=349.08,400
BL=97.72,400
```

Returning to a 1000-pixel outer width in fixed mode did not restore the original fixed pipe tree; the scaled fixed values remained. This is the same size-dependent, non-lossless round-trip boundary as Coordinate child positions. Preserve a canonical pipe model elsewhere if the original geometry must survive cross-size mode changes.

The two-pipe fixture converted both array entries in place. At the 994-by-594 content size, fixed to percent produced:

```text
P0=BlueHorizontal:0.8551,0.303>0.1207,0.303
P1=AmberVertical:0.503,0.7239>0.503,0.101
```

Converting back to fixed at the 694-by-594 narrow content size produced:

```text
P0=BlueHorizontal:593.44,179.98>83.77,179.98
P1=AmberVertical:349.08,430>349.08,59.99
```

Both pipes retained array order, names, fills, widths, and visibility. A later wide fixed resize retained the narrow-scaled point values.

## Child lifecycle and session isolation

The retained Coordinate also had three Embedded Views placed near the top leaf, bottom leaf, and origin. Resizing fixed mode and toggling pipe visibility retained every endpoint instance and local counter.

Each fixed-to-percent or percent-to-fixed transition remounted all three endpoints, ran startup once on each replacement, assigned new instance timestamps, and reset local counters. This lifecycle comes from the Coordinate mode topology change, not from pipe visibility.

A second browser session remained at the initial fixed/visible state, kept its original endpoint instances, retained `PIPE NOT CAPTURED`, and received none of the first session's mode, visibility, capture, or local-counter changes.

## Scripted access

The retained fixture captured all six values by following the known hierarchy:

```python
coord = self.parent.getSibling("CoordinateContainer")
p = coord.props.pipes[0]
o = p.origin
j = o.connections[0]
t = j.connections[0]
tl = t.connections[0]
b = j.connections[1]
bl = b.connections[0]
self.view.custom.pipeSnapshot = (
    "O=%s,%s J=%s,%s T=%s,%s TL=%s,%s B=%s,%s BL=%s,%s" %
    (o.x, o.y, j.x, j.y, t.x, t.y, tl.x, tl.y, b.x, b.y, bl.x, bl.y)
)
```

This traversal is fixture-specific. Validate connection counts and branch order before using indexed access on another tree. Wait for a mode conversion to settle before capturing converted values.

An expression binding successfully read indexed pipe members:

```text
{../CoordinateContainer.props.pipes[0].visible}
{../CoordinateContainer.props.pipes[0].width}
```

The exact sibling-relative component path depends on the tested parent hierarchy.

## Runtime validation

1. Export the approved project and require exact readback of every pipe member and nested point.
2. Open two independent browser sessions and require the expected Coordinate, three endpoints, one SVG, and five official mounted-view records per page.
3. Capture the initial fixed tree and assert the six exact point values.
4. Resize fixed mode narrow and wide; require unchanged point values, endpoint instances/state, pipe extent, overflow, and paint.
5. Toggle `visible` false; require one empty SVG shell, zero pipe descendants, retained endpoints, a screenshot, browser diagnostics, topology, and bounded Gateway logs.
6. Toggle `visible` true; require the rebuilt 41-element structure, painted screenshot, current SVG/mask dimensions, retained endpoints, and clean feedback surfaces.
7. Convert fixed to percent while wide and capture all six four-decimal values. Require endpoint remount/reset.
8. Resize percent mode narrow; require content-box scaling and retained percent-phase instances.
9. Convert back to fixed while narrow and capture all six two-decimal values. Require another endpoint remount/reset.
10. Resize fixed mode wide; prove the narrow-scaled fixed values remain rather than assuming restoration.
11. At every edge save paired screenshots, exact geometry, SVG attributes/classes, browser errors, official topology, and bounded official Gateway WARN-or-higher logs.
12. Close both sessions, poll official topology to zero, then query logs again. The qualified strict runs required about 60 seconds before active pages cleared; do not stop the log window early.
13. Repeat the entire sequence independently and require zero project, protected-resource, and optional `llmImport` drift.

For two independent pipes, additionally require one shared SVG, two direct groups in exact array order, distinct `data-fill` values, independent hidden/restored states, screenshot pixel evidence at the crossing, current shared-SVG inline and bounding dimensions, conversion of both entries, four marker lifecycle records, six official mounted-view records per page, and isolated state in the second session.

For runtime array mutation, additionally require the guarded in-place-method negative, exact no-write proof, list-copy reorder plus whole-array reassignment, direct-group and crossing-pixel order proof, post-reorder indexed visibility with a later settled read, list-copy removal plus reassignment, canonical JSON restoration, marker-instance/state retention, both stale and recomputed shared-SVG extents, and an isolated second session. Repeat the entire sequence independently.

For runtime insertion, additionally require the direct-append outcome, list-copy append plus reassignment, list-copy index-1 insertion plus reassignment, exact three-entry property and direct-group order, crossing pixels for append and index-1 insertion, post-insertion index targeting with a later settled read, exact inserted-item removal, canonical restoration, four retained marker instances, six official views per page, isolated second-session state, stale and recomputed SVG extents, and delayed cleanup logs. Repeat the entire sequence independently.

For recursive branch mutation, additionally require exact hierarchy preconditions, direct nested append, list-copy nested append plus reassignment, list-copy index-1 insertion plus reassignment, exact branch ordering after a settled recapture, exact removed coordinates, canonical whole-pipe-array restoration, one primary SVG group with 41-versus-56 descendant counts, branch paint/background pixels, four retained marker instances, six official views per page, isolated second-session state, stale and recomputed SVG extents, and delayed cleanup logs. Repeat the entire sequence independently.

For runtime-expanded branch conversion, additionally require the exact expanded fixed, percent, and narrow-scaled fixed eight-point trees; branch index retention; three marker-instance phases; local-state reset at both mode transitions; retained instances during append, same-mode resize, pipe restore, and final resize; 56-element expanded SVG structure; original and scaled branch pixels; proof that the original wide branch location is empty after the non-lossless round trip; six-point canonical pipe restoration; independent proof that child geometry remains narrow-scaled; readable/clipping-free screenshots; isolated second-session state; stale and recomputed inline extents; and delayed cleanup logs. Repeat the entire sequence independently.

For combined canonical restoration, additionally require a pre-action state in which both the pipe tree and child layout differ from canonical; a pipe-only control proving child geometry remains scaled; exact pipe-first action ordering; direct writeback of all four members on all four known children; settled DOM restoration before explicit recapture; exact later tree and layout capture; retained fixed-phase child instances/state; isolated second-session state; stale and recomputed SVG extents; browser-console gating; and delayed cleanup logs. Repeat the entire sequence independently.

## API boundary

Author the view and page route through the official authenticated project APIs exposed by the live `/openapi.json`. Use the optional project-scoped `llmImport` POST dispatcher only if its health response advertises the required action and official OpenAPI lacks the capability.

The retained fixture required no new `llmImport` feature. Whole-project import was sufficient and was guarded by current export, exact declared delta, tokenless rejection, authenticated success, scan locks, semantic export readback, route activation, project/protected parity, and log inspection.

Use a headless browser only after API authoring, for runtime feedback and validation. Never use it to create or edit the Perspective resource.

## Qualification boundary

This reference does not qualify four or more pipes, omitted members, `appearance` values other than `simple`, `mimic` or PID rendering, start/end decorations, arrows, flanges, non-solid line variants, a non-empty stroke, hidden initial state, additional fill/width combinations beyond the exact three-pipe fixture, collinear overlap, overlapping recursive branches, cycles, delegated connectors, anchors, rotation, bindings on pipe members, direct wrapper methods other than the tested `append`, list insertion at indices other than 1, repeated/duplicate insertion, direct dictionary insertion without JSON decoding, nested branch reorder, removal at indices other than 1, conversion after nested insertion/reorder/removal or duplicate append, mutation without the tested direct append or whole-array/nested-array reassignment forms, rapid or concurrent mutations, mode conversion with three pipes, child-first combined restoration, successful whole-`position` object assignment or its use inside combined pipe restoration, omitted child position members, different child names/counts or canonical rectangles, nested Coordinate Containers, navigation, touch, keyboard accessibility, security policies, or other Ignition builds. Test each separately before relying on it.
