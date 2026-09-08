# Perspective Flex Repeater

Use this reference for the exact static Flex Repeater and repeated-child shapes qualified on Ignition 8.3.8 / Perspective 3.3.8.

## Contents

- [Parent component](#parent-component)
- [Child parameters and automatic index](#child-parameters-and-automatic-index)
- [Standalone and Designer default mounts](#standalone-and-designer-default-mounts)
- [Dynamic instance list](#dynamic-instance-list)
- [Tested child lifecycle](#tested-child-lifecycle)
- [Authoring and validation](#authoring-and-validation)

## Parent component

Serialize the component as `ia.display.flex-repeater`. Point `props.path` at an existing child view and place one object per child mount in `props.instances`:

```json
{
  "type": "ia.display.flex-repeater",
  "props": {
    "path": "App/Repeated Child",
    "instances": [
      {
        "instancePosition": {},
        "instanceStyle": {},
        "label": "ALPHA",
        "accent": "#dc2626"
      },
      {
        "instancePosition": { "basis": "34%" },
        "instanceStyle": {},
        "label": "BRAVO",
        "accent": "#16a34a"
      }
    ],
    "direction": "row",
    "wrap": "nowrap",
    "justify": "space-between",
    "alignItems": "stretch",
    "elementPosition": { "basis": "28%", "grow": 0, "shrink": 0 },
    "elementStyle": { "margin": "12px 8px" },
    "useDefaultViewHeight": false,
    "useDefaultViewWidth": false
  }
}
```

The tested runtime mounted children in instance-array order. Shared `elementPosition` and `elementStyle` values applied to every child; the middle instance's `instancePosition.basis` overrode the shared basis and painted wider than its siblings. Treat `instancePosition` and `instanceStyle` as explicit objects even when empty until another 8.3 shape is tested.

## Child parameters and automatic index

Each ordinary key in an instance object can supply the matching child view input parameter. Declare those parameters in the child view and set `paramDirection` explicitly:

```json
{
  "params": {
    "label": "DEFAULT",
    "accent": "#64748b",
    "index": -1
  },
  "propConfig": {
    "params.label": { "paramDirection": "input", "persistent": true },
    "params.accent": { "paramDirection": "input", "persistent": true },
    "params.index": { "paramDirection": "input", "persistent": true }
  }
}
```

In the qualified three-instance fixture, the instance objects omitted `index`, while the runtime supplied `0`, `1`, and `2` in array order. Do not write an `index` key into instance objects when relying on this automatic value.

The child used a normal property binding for its accent and an expression binding for visible label/index proof:

```json
{
  "props.style.backgroundColor": {
    "binding": { "type": "property", "config": { "path": "view.params.accent" } }
  },
  "props.text": {
    "binding": {
      "type": "expr",
      "config": {
        "expression": "{view.params.label} + \" | INDEX \" + toStr({view.params.index})"
      }
    }
  }
}
```

Place each binding in the `propConfig` object of the component or container that owns the target property.

## Standalone and Designer default mounts

Treat every declared child-parameter default as a real runtime input. Opening the tested repeated child directly in Designer mounted it with its stored `label: "DEFAULT"` before any Flex Repeater instance supplied `ALPHA`, `BRAVO`, `CHARLIE`, or `DELTA`. Its test-only startup allowlist rejected `DEFAULT` and emitted `ValueError: t68_unknown_label:DEFAULT` through the Gateway `perspective.actions.script` logger.

Do not write a startup or shutdown script that assumes a repeater-supplied parameter is already present merely because the child is normally embedded. Choose one of these explicitly and test it:

- make the stored default a valid no-op sentinel and skip external side effects for that sentinel;
- make the stored default a fully valid operational value with a corresponding target; or
- avoid opening the child standalone and accept that Designer compatibility remains unqualified.

The third option is not acceptable when the retained child must open cleanly in Designer. Query official Gateway logs after Designer opening because Gateway-executed lifecycle exceptions are API-visible even though Designer-local deserialization and connection popups may not be.

The tested API-authored recovery treated `DEFAULT` as a no-op sentinel: startup set only local `startupCount` to zero, and shutdown skipped the external tag write. Two fresh standalone browser sessions painted `DEFAULT | INDEX -1 | START 0` with clean browser diagnostics and saved empty Gateway WARN-or-higher windows. Two more fresh parent sessions reproduced all five original lifecycle states; route-leave shutdowns settled after 7.0 and 7.5 seconds. Exact project readback and unrelated-project isolation passed.

After a Gateway reload, the first Designer lifecycle still emitted one old-shape DEFAULT shutdown warning even though the current export contained both guards. One later bounded open/close interval initially appeared clean, but a still-later user close produced another official `system.onShutdown` WARN with `t68_unknown_label:DEFAULT`; a separate Designer Child@C startup/shutdown pair showed the same failure. Therefore the earlier clean interval does not qualify Designer compatibility. The current export and Designer-executed shape disagreed for an unknown reason; do not label it a cache defect or Ignition bug from this evidence. Always query Gateway logs after both Designer open and close.

## Dynamic instance list

To drive the repeater from parent state, store the complete instance array in one persistent custom property. Keep an empty fallback in `props.instances` and put the property binding on the repeater itself:

```json
{
  "custom": {
    "instances": [
      {
        "instancePosition": {},
        "instanceStyle": {},
        "label": "ALPHA",
        "accent": "#dc2626"
      }
    ]
  },
  "propConfig": {
    "custom.instances": { "persistent": true }
  }
}
```

```json
{
  "props": { "instances": [] },
  "propConfig": {
    "props.instances": {
      "binding": {
        "type": "property",
        "config": { "path": "view.custom.instances" }
      }
    }
  }
}
```

The tested Button events replaced the whole list with a newly constructed list of complete instance dictionaries, then updated a separate visible state marker. This exact sequence painted initial three, reversed three, appended fourth, removed fourth, and reset three states without navigation or reconnect. Official child registrations changed with the list length.

After every whole-list replacement, automatic `index` values matched the new zero-based array order. Reordering changed the label associated with each index; adding produced the next index; removing and reset restored the expected index range.

Prefer whole-list replacement for this qualified workflow. Direct append/pop, member-only mutation, duplicate items, middle insertion/removal, empty/large arrays, and rapid or concurrent changes are not established here.

Mounted-view identifiers remained keyed by repeater position in the tested sequence. Do not treat those identifiers alone as lifecycle evidence; use an external counter or equivalent observable effect when lifecycle behavior matters.

## Tested child lifecycle

One focused fixture added view-level `events.system.onStartup` and `events.system.onShutdown` scripts to the repeated child. Each script synchronously incremented a distinct external counter selected from the child's `label` input. The parent then performed the same whole-list initial, reverse, add, remove, and reset sequence described above.

The exact observed counter sequence was:

| State | Startup counters `ALPHA/BRAVO/CHARLIE/DELTA` | Shutdown counters `ALPHA/BRAVO/CHARLIE/DELTA` |
|---|---:|---:|
| Initial three | `1/1/1/0` | `0/0/0/0` |
| Reversed three | `1/1/1/0` | `0/0/0/0` |
| Added `DELTA` | `1/1/1/1` | `0/0/0/0` |
| Removed `DELTA` | `1/1/1/1` | `0/0/0/1` |
| Reset original three | `1/1/1/1` | `0/0/0/1` |

For this exact sequential whole-list workflow, reordering the three existing labels did not rerun their startup scripts, adding the fourth label ran only its startup, removing it ran only its shutdown, and resetting the remaining three did not rerun startup. Official mounted-child counts simultaneously changed `3 -> 3 -> 4 -> 3 -> 3`, and every painted child reported startup count `1`.

After route navigation followed by client teardown, the three remaining shutdown counters eventually reached `1`, but they were still `0` at the tested one-second observation. In the later default-sentinel recovery regression, two fresh sessions settled those remaining counters after 7.0 and 7.5 seconds. Treat final route/page teardown as asynchronous; these two observations are not a general timing guarantee.

In a separate context-close-only observation, none of the three remaining shutdown callbacks appeared during a 30-second official tag poll. Do not treat closing a headless browser context as proof that Perspective delivered view shutdown events; navigate away and observe the application-level lifecycle when shutdown behavior is part of the test.

This evidence applies only to distinct repeater-supplied labels, the exact end-add/end-remove/reset sequence, and the narrow browser-runtime `DEFAULT` no-op recovery. Designer compatibility remains unqualified because later open/close lifecycle warnings contradicted the earlier clean window. It does not establish the cause of the apparent old-shape execution, identity rules for duplicates, middle insertion/removal, replacement with changed parameter values, arbitrary reorder patterns, in-place mutations, rapid/concurrent writes, reconnects, reloads, project revisions, nested repeaters, or failed/long-running lifecycle scripts.

### Middle insertion and removal

A second focused fixture changed the distinct-label list from `ALPHA, BRAVO, CHARLIE` to `ALPHA, ECHO, BRAVO, CHARLIE` by inserting at index 1, removed index 1, repeated the insertion, and reset. Each label again had independent external startup and shutdown counters.

The inserted `ECHO` content did not receive startup or shutdown callbacks. Existing mounted positions accepted the shifted parameters without rerunning startup. The new terminal position started with the current terminal label `CHARLIE`; removing the middle item removed that terminal position and ran shutdown with `CHARLIE` as the current label.

| State | Painted list and captured startup counts | `Startup_CHARLIE` | `Shutdown_CHARLIE` | `Startup_ECHO` / `Shutdown_ECHO` |
|---|---|---:|---:|---:|
| Initial | `ALPHA 1, BRAVO 1, CHARLIE 1` | 1 | 0 | `0 / 0` |
| Insert index 1 | `ALPHA 1, ECHO 1, BRAVO 1, CHARLIE 2` | 2 | 0 | `0 / 0` |
| Remove index 1 | `ALPHA 1, BRAVO 1, CHARLIE 1` | 2 | 1 | `0 / 0` |
| Insert index 1 again | `ALPHA 1, ECHO 1, BRAVO 1, CHARLIE 3` | 3 | 1 | `0 / 0` |
| Reset | `ALPHA 1, BRAVO 1, CHARLIE 1` | 3 | 2 | `0 / 0` |

Official mounted-child counts were `3 -> 4 -> 3 -> 4 -> 3`. Two complete sequences produced the same counter matrices and painted values. For this exact workflow, treat repeated children as position-mounted when reasoning about lifecycle; do not assume a logical instance dictionary carries its own startup/shutdown identity when it moves to another index.

This does not establish behavior for duplicates, an insertion/removal at another index, changing only one instance member, swapping arbitrary pairs, simultaneous multiple changes, explicit user identity keys, in-place mutation, or rapid/concurrent updates. Test each before using lifecycle scripts to manage instance-specific external resources.

## Authoring and validation

Derive the component from a live installed 8.3 export before changing untested properties. Use the official project export/import operations when a narrower tested resource API is unavailable. Require a fresh-base hash comparison, exact expected ZIP delta, tokenless negative, exact authenticated target, activation, and exact export readback.

For runtime proof, require every expected label and parameter-derived style, left-to-right geometry, width relationships, clipping checks, a painted screenshot, browser diagnostics, and official session/page/view correlation. Count repeated child registrations by exact `resourcePath`; one registration per painted child is stronger evidence than aggregate component counts alone.

This reference does not qualify in-place list mutation, tag/query/expression instance sources, empty or large arrays, duplicates, middle insertion/removal beyond the exact index-1 sequence, row-reverse/column/wrap behavior, default child sizing, grow/shrink beyond the shown zeros, min/max sizing, other position/style members, output/in-out parameters, automatic-index collisions, lifecycle identity beyond the exact instrumented sequences, teardown timing, nested repeaters, rapid/concurrent updates, live revisions, failure recovery, performance, responsive layouts, reload, reconnect, or redundancy behavior.
