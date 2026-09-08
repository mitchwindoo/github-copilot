# Perspective view parameters

Use these forms only after inspecting a live Ignition 8.3 view seed on the target build. Preserve the surrounding view and Embedded View component shapes. The tested values were Strings.

## Contents

- [Output parameter](#output-parameter)
- [In/out parameter](#inout-parameter)
- [Dynamic replacement](#dynamic-replacement)
- [Carousel descriptor boundary](#carousel-descriptor-boundary)
- [Validation](#validation)
- [Boundaries](#boundaries)

## Output parameter

Declare an output parameter and bind it from state owned inside the child view:

```json
{
  "custom": {
    "outputSource": "CHILD_OUTPUT"
  },
  "params": {
    "outputValue": "OUTPUT_DEFAULT"
  },
  "propConfig": {
    "params.outputValue": {
      "binding": {
        "config": {
          "path": "view.custom.outputSource"
        },
        "type": "property"
      },
      "paramDirection": "output",
      "persistent": true
    }
  }
}
```

Store a same-named field under the parent Embedded View's `props.params`. Observe that property from the parent, such as with a sibling property binding to `../EmbeddedView.props.params.outputValue`. In the tested flow, changing `self.view.custom.outputSource` inside the child changed `view.params.outputValue`, the Embedded View property, and the parent's painted observation.

Do not bind the output from parent state. The tested output source was owned and property-bound inside the child.

## In/out parameter

Declare the child parameter with the exact direction string `inout`:

```json
{
  "params": {
    "inoutValue": "INOUT_DEFAULT"
  },
  "propConfig": {
    "params.inoutValue": {
      "paramDirection": "inout",
      "persistent": true
    }
  }
}
```

Store the matching property on the parent Embedded View and bridge it to parent state with one bidirectional property binding:

```json
{
  "props": {
    "params": {
      "inoutValue": "PARENT_INITIAL"
    }
  },
  "propConfig": {
    "props.params.inoutValue": {
      "binding": {
        "config": {
          "bidirectional": true,
          "path": "view.custom.inoutParent"
        },
        "type": "property"
      }
    }
  }
}
```

The exact synchronous assignments passed in both directions:

```python
# Inside the child: propagate to the Embedded View and parent custom value.
self.view.params.inoutValue = "CHILD_VALUE"

# Inside the parent: propagate through the bidirectional binding to the child.
self.view.custom.inoutParent = "PARENT_VALUE"
```

Render the parent custom value and child parameter independently. A single painted label is insufficient to prove both sides.

## Dynamic replacement

The tested parent property-bound `props.path` between two known-Good children that declared the same output and in/out parameters. The settled sequence proved:

- each newly mounted child published its own internally bound output;
- the newly mounted child received the parent's current in/out value;
- child-to-parent and parent-to-child in/out assignments worked on both children;
- restoring the first child created a fresh instance, restored that child's initial output, and retained the parent's current in/out value.

Separate startup counters ended parent/first-child/second-child at `1/2/1`. Treat that sequence as replacement evidence for this exact direct embedded composition, not as a caching or timing guarantee.

## Carousel descriptor boundary

Do not extend the direct Embedded View result to a Carousel descriptor. In one tested three-step Carousel, an editable child's persistent `inout` parameter wrote its committed value back into that child's descriptor `viewParams`. The reverse assumption did not hold: replacing another descriptor with new `viewParams` and reassigning the whole `props.views` list changed the parent property tree but did not update that descriptor's child before first mount, while mounted, or after navigating away and back.

Use independent parent feedback bound to the descriptor and independent child feedback bound to `view.params` to distinguish descriptor mutation from parameter delivery. For the qualified multi-step handoff, use [perspective-carousel-wizard.md](perspective-carousel-wizard.md).

## Validation

1. Export the approved project and require missing-resource preconditions before adding the parent, two children, route, and dedicated counters.
2. Import only a canonical `/`-separated archive through the official project API and require an exact per-entry hash-map readback.
3. Require the readback to contain the exact `output` and `inout` direction strings on the intended child parameters.
4. Paint and independently inspect the child source/parameter, Embedded View output observation, parent in/out state, and child in/out state before and after each guarded assignment.
5. Replace the child in both directions and correlate the painted identity, official mounted-view path, startup counters, one stable session/page, and zero reconnects.
6. Capture screenshots and geometry for every settled state; require no clipping, overflow, visible error overlay, console/page error, or unexpected Gateway WARN-or-higher entry.
7. Require the exact final project, Good final counters, route success, clear scan lock, and natural browser cleanup.

Treat script and expression metrics as observation-window correlation. Do not make fixed semantic-count claims from them.

## Boundaries

This proves only String `output` and `inout` parameters in one direct Embedded View composition, an output property binding from child custom state, one parent observation of the Embedded View output property, one bidirectional property bridge for in/out, direct synchronous assignments, and one known-Good first-child to second-child to first-child replacement sequence.

It does not prove input parameters beyond their separately tested references, output assignment from outside the child, non-String values, objects/lists, multiple parameters of one direction, popup/page/dock/repeater behavior, nested or sibling embedded views, binding cycles, multiple writers, concurrent or rapid assignments, transaction or atomicity semantics, exact propagation timing, null/missing/malformed values, validation errors, permissions, reconnect/reload/navigation/import behavior while mounted, failures, async scripts, redundancy, or other binding types. Carousel descriptor behavior is separately bounded above and must not be inferred from the direct Embedded View results.
