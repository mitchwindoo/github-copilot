# Perspective bindings and transforms

Use this workflow only after inspecting live Ignition 8.3 view resources on the target build. Preserve the surrounding view and component shape from a live seed; the examples below establish only the tested binding fields.

## Contents

- [Component property binding](#component-property-binding)
- [Expression binding](#expression-binding)
- [Expression transform](#expression-transform)
- [Script transform](#script-transform)
- [Scalar map transform](#scalar-map-transform)
- [Numeric format transform](#numeric-format-transform)
- [Ordered expression/script transform chain](#ordered-expressionscript-transform-chain)
- [Validation gates](#validation-gates)
- [Direct tag binding](#direct-tag-binding)
- [Tested Boolean Label representation](#tested-boolean-label-representation)
- [Indirect tag binding](#indirect-tag-binding)
- [Boundary](#boundary)

## Component property binding

A binding for a component property is stored beneath the component's `propConfig` entry for that target property:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "path": "view.custom.sourceText"
        },
        "type": "property"
      }
    }
  }
}
```

The tested client resolved `view.custom.sourceText` into the component's `props.text` value.

## Expression binding

The tested expression form uses `type: "expr"` and stores the expression string in `config.expression`:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "expression": "{view.params.prefix} + \" result: \" + {view.custom.sourceText}"
        },
        "type": "expr"
      }
    }
  }
}
```

For the tested input parameter, the view also retained this view-level parameter configuration:

```json
{
  "params": {
    "prefix": "Bound"
  },
  "propConfig": {
    "params.prefix": {
      "paramDirection": "input",
      "persistent": true
    }
  }
}
```

## Expression transform

The tested expression transform is an ordered item in the owning binding's `transforms` array. It uses `{value}` for the incoming binding value:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "path": "view.custom.sourceText"
        },
        "transforms": [
          {
            "expression": "\"Transformed: \" + {value}",
            "type": "expression"
          }
        ],
        "type": "property"
      }
    }
  }
}
```

For the tested String source `Alpha` and Label text target, this painted exact `Transformed: Alpha`.

The tested unknown-function expression returned visible `null`, did not paint the Label's stored fallback text, and placed a red `ia_qualityOverlay--error` across the component with an error icon and `ERROR` footer. Its quality detail reported subcode `Error_Configuration`, the exact target-property path, and `Invalid expression: Unknown function: 'doesNotExist'`. Browser console and Gateway WARN-or-higher logs did not expose the expression failure. Capture the painted overlay, DOM classes, and available quality detail instead of inferring error state from logs or fallback text.

Do not use division by zero as an expression-transform error fixture on the tested build: `1 / 0` painted `Infinity` without an error overlay.

### Numeric expression over an indirect tag

The exact tested numeric extension placed an expression transform on a single-reference indirect tag binding:

```json
{
  "binding": {
    "type": "tag",
    "config": {
      "mode": "indirect",
      "references": {"tagPath": "{view.params.tagPath}"},
      "tagPath": "{tagPath}"
    },
    "transforms": [
      {"type": "expression", "expression": "75 - {value}"}
    ]
  }
}
```

For one Good Float8 Speed tag, independently read value 62.5 painted 12.5. A guarded external write to 68.75 repainted 6.25 in two sessions, and restoring 62.5 repainted 12.5. Require independent value, quality, and source-timestamp evidence plus screenshots and Gateway logs for every write edge. This does not establish null/bad-quality behavior, other numeric types, bidirectional mode, multiple references, other operators, or arbitrary numeric coercion.

## Script transform

The tested script transform is also an ordered item in the owning binding's `transforms` array. Store the function body in `code`, preserve its leading indentation, and use the incoming `value` argument:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "path": "view.custom.sourceNumber"
        },
        "transforms": [
          {
            "code": "\treturn \"Scripted: \" + str(value * 3)",
            "type": "script"
          }
        ],
        "type": "property"
      }
    }
  }
}
```

For the tested numeric source `7` and Label text target, this painted exact `Scripted: 21` rather than the stored fallback.

A controlled transform containing `\traise Exception("deliberate transform failure")` painted visible `null`, did not paint the Label's stored fallback, and placed a red `ia_qualityOverlay--error` across the component with an error icon and `ERROR` footer. A bounded browser-console watcher and Gateway WARN-or-higher window were empty. Use painted DOM and screenshot evidence for the error claim instead of expecting a log entry.

Official session metrics counted the two script transforms under `scripts` and counted zero `expressions` in the isolated page. Treat those metrics as execution-count correlation only; the screenshot and DOM prove the values and overlay.

Do not infer that other script arguments, `self`, side effects, asynchronous work, chained transforms, other exceptions, targets, security contexts, or quality/fallback timing behave the same. Test each separately.

## Scalar map transform

The tested scalar map transform is an ordered item in the owning binding's `transforms` array. Store the unmatched result in `fallback`, use scalar input and output types, and list equality mappings in order:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "path": "view.custom.sourceText"
        },
        "transforms": [
          {
            "fallback": "DEFAULT_BRANCH",
            "inputType": "scalar",
            "mappings": [
              {
                "input": "MATCH",
                "output": "MATCHED_BRANCH"
              }
            ],
            "outputType": "scalar",
            "type": "map"
          }
        ],
        "type": "property"
      }
    }
  }
}
```

For the tested String source `MATCH` and Label text target, the mapping painted exact `MATCHED_BRANCH`. With the same transform and source `MISS`, the unmatched branch painted exact `DEFAULT_BRANCH`. Neither Label's stored placeholder appeared.

Official session reads reported two binding instances, while both script and expression metric counts remained zero. Use the screenshot and DOM to prove map output; those two metric categories do not enumerate the tested map transforms.

Do not infer range input, color/style/expression outputs, multiple or duplicate mappings, null or type coercion, priority beyond the tested first mapping, chains, bidirectional behavior, quality/fallback timing, or other targets. Test each separately.

## Numeric format transform

The tested numeric format transform is an ordered item in the owning binding's `transforms` array. Store its category in `formatType` and its numeric pattern in `formatValue`:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "path": "view.custom.sourceNumber"
        },
        "transforms": [
          {
            "formatType": "numeric",
            "formatValue": "##0.00",
            "type": "format"
          }
        ],
        "type": "property"
      }
    }
  }
}
```

On the tested runtime and locale, numeric source `12.3456` painted exact Label text `12.35`; the Label's stored placeholder did not paint. Official session reads reported one binding instance, while script and expression metric counts remained zero. Use painted DOM and screenshot evidence for the formatted value.

Keep the claim tied to this exact pattern, source, target, runtime, and locale. Do not infer other patterns, grouping, signs, currency, percent, date/time, null/NaN/infinity handling, rounding modes, chains, quality behavior, or other targets.

## Ordered expression/script transform chain

Items in the tested binding's `transforms` array evaluated sequentially in listed order. Each expression item received the preceding result as `{value}`, and each script item received it as `value`:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "path": "view.custom.sourceText"
        },
        "transforms": [
          {
            "expression": "{value} + \"-EXPR\"",
            "type": "expression"
          },
          {
            "code": "\treturn \"SCRIPT(\" + str(value) + \")\"",
            "type": "script"
          }
        ],
        "type": "property"
      }
    }
  }
}
```

For tested String source `Alpha`, the expression-only control painted `Alpha-EXPR`, the script-only control painted `SCRIPT(Alpha)`, and the sequence above painted exact `SCRIPT(Alpha-EXPR)`. Reversing the same two items painted distinct `SCRIPT(Alpha)-EXPR`, proving listed-order evaluation rather than merely proving that both transforms ran.

Require single-item controls alongside an order-sensitive chain whose reversed order would produce a different result. Export and compare the exact transform array, then prove every control and final value with painted DOM and screenshot evidence. Treat official script/expression metrics only as execution correlation: reload or reconnect can make execution counts differ from the number of configured items.

This establishes only the exact tested String expression/script items in both two-item orders on Label `props.text`. Do not infer longer chains, other transform types, null/quality behavior, errors, coercion, side effects, asynchronous work, other sources or targets, execution-count guarantees, or performance.

## Validation gates

1. Export the project before mutation and derive the candidate from that exact base.
2. Import or write through the approved API, then export and compare the exact stored `propConfig` structure.
3. Render the retained route only with caller-approved programmatic browser validation.
4. Assert the exact evaluated text, positive and in-viewport geometry, no clipping or document overflow, a painted screenshot, and a clean browser console.
5. Correlate the exact mounted view and binding-instance count through official Perspective session reads.
6. Re-export and require the declared project delta, stable agent API state, a clear scan lock, and clean bounded Gateway logs.

For an error-transform test, mount a distinct fresh page after any resource revision. Require the exact stored expression, visible result, overlay class/icon/footer, fallback presence or absence, geometry, screenshot, console, page ID, and binding/expression counts. Project import does not prove an already mounted page reloaded.

Official mounted-view `bindingCount` reports instances, not evaluated values or quality. Use screenshot and DOM evidence for the visible value and separate API instrumentation for values or quality that are not exposed by the session read.

## Direct tag binding

The tested direct form is stored under the component target property just like the other tested bindings:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[<provider>]<approved-path>"
        },
        "type": "tag"
      }
    }
  }
}
```

Before client validation, independently read the exact tag through an approved runtime API and record its value, quality, and timestamp. While the page is mounted, require the painted value to equal a fresh independent read, require Good quality for a normal-value claim, and repeat the independent read after finalization. A visible value or official `bindingCount` alone does not prove quality or source timestamp.

Keep the tag provider and path caller-approved and bounded. Do not place credentials or environment-specific paths in reusable documentation.

### Direct missing path

For the tested static comparison, one direct String binding targeted an independently verified Good qualified path and an adjacent binding with the same shape targeted a nonexistent qualified child path. Both targeted Label `props.text` and used a 2.5-second fallback delay.

The Good direct binding painted the exact independently read value without its stored fallback or a quality overlay. The missing direct binding painted literal `null`, did not paint its distinct stored fallback, and added `ia_qualityOverlay ia_qualityOverlay--error`, the error icon, and `ERROR` footer. Its quality detail reported subcode `Bad_NotFound`, the exact nested target-property path, and the nonexistent qualified tag path. Independent reads before, during, and after the client session preserved both signatures and reported zero writes.

Capture the Good and missing controls together so binding shape and visible outcomes can be compared. Open the missing target's quality detail; if its body is scrollable, use a semantic locator to reveal and capture the complete property and description. Official `bindingCount` proves only the two mounted instances, so retain independent value, quality, and timestamp evidence.

For the exact tested runtime, path, String source, Label target, and fallback delay, this static direct missing binding and the separately tested indirect missing state shared literal `null`, stored-fallback suppression, the red error overlay, and `Bad_NotFound`. Treat this as a comparison of two proven fixtures, not as general equivalence between direct and indirect bindings.

This does not establish a direct binding changing or recovering after mount, null or malformed paths, tag creation or deletion while mounted, other quality codes, other types or targets, bidirectional behavior, writes, reconnects, or different fallback delays.

## Tested Boolean Label representation

For the tested direct Boolean tag binding whose target was a Label `props.text`, the client painted lowercase `true` and `false`. Validate both states against independent Good-quality tag reads before relying on that representation.

This is a narrow observed conversion for the tested target property. Do not infer the same formatting for other components, target properties, data types, locales, transforms, or overlays.

## Indirect tag binding

The tested read-only form resolves one named reference from a persistent view input parameter. The reference value is an exact caller-approved tag path, while `config.tagPath` contains the matching brace-delimited template:

```json
{
  "params": {
    "tagPath": "[<provider>]<approved-path>"
  },
  "propConfig": {
    "params.tagPath": {
      "paramDirection": "input",
      "persistent": true
    }
  },
  "root": {
    "children": [
      {
        "propConfig": {
          "props.text": {
            "binding": {
              "config": {
                "fallbackDelay": 2.5,
                "mode": "indirect",
                "references": {
                  "tagPath": "{view.params.tagPath}"
                },
                "tagPath": "{tagPath}"
              },
              "type": "tag"
            }
          }
        },
        "type": "ia.display.label"
      }
    ]
  }
}
```

Before mounting the page, independently read the exact resolved path through an approved runtime API and record value, quality, and source timestamp. Repeat that read while the page is active and after cleanup, require zero write calls for a read-only test, and require the painted Label text to equal the independently read Good value. Export readback must preserve both the view parameter configuration and binding structure exactly.

This base form establishes only one named reference that resolves an exact String tag path from a persistent view input parameter into Label `props.text`. Apply the focused workflows below before claiming a direct post-mount path change, missing-path recovery, or the exact tested two-reference assembly. The base form alone does not establish multiple references, nested composition, polling or rate behavior, bidirectional mode, transforms, other data types, other targets, or writes.

### Direct post-mount path changes

For the tested primary root view, a Gateway-scope Button action directly assigned another approved qualified path to the persistent input parameter:

```json
{
  "events": {
    "component": {
      "onActionPerformed": {
        "config": {
          "script": "\tself.view.params.tagPath = \"[<provider>]<approved-second-path>\""
        },
        "scope": "G",
        "type": "script"
      }
    }
  },
  "type": "ia.input.button"
}
```

The mounted indirect Label re-resolved to the second Good String tag without a remount, and a second fixed Button assignment restored the first path and value. Before mounting and at every visible state, independently read both qualified paths and require exact values, Good quality, stable source timestamps, and an explicit no-write result. Require the visible current-path marker and bound value to change together, save each state as a screenshot, and verify the original pair after switching back.

This proves only direct assignment to a persistent input parameter on the tested primary root view, with one read-only reference and two Good String sources targeting Label text. It does not prove parent-driven changes, embedded views, multiple references, rapid changes, missing paths, polling or debounce timing, bidirectional behavior, quality transitions, reload/reconnect persistence, other data types or targets, or writes.

### Missing indirect path and recovery

For the tested single-reference indirect String binding, one fixed Button assigned a nonexistent qualified path to the same persistent root-view parameter. After waiting beyond the configured 2.5-second fallback delay, the current-path marker changed and the bound Label painted literal `null`. It did not paint the Label's distinct stored fallback.

Perspective placed `ia_qualityOverlay ia_qualityOverlay--error` across the Label with the error icon and `ERROR` footer. The quality detail reported subcode `Bad_NotFound`, the exact target-property path, and the nonexistent qualified tag path. Independently reading that path returned null with `Bad_NotFound` and explicitly reported no write.

A second fixed Button restored the original Good path. The exact Good String value returned without remounting, and the error overlay, icon, footer, and detail popover disappeared. Independent reads before, during, after recovery, and after browser cleanup preserved the Good source's value, quality, and timestamp and reported zero writes.

Use a distinct stored fallback so its presence can be detected. Capture the Good, missing, quality-detail, and recovered states. If the diagnostic body exceeds the visible popover, scroll it through a semantic locator and capture the complete detail rather than assuming clipped text is absent. Correlate the visible missing state with an independent quality read; official mounted-view `bindingCount` does not expose value or quality.

This proves only direct parameter assignment on the tested primary root view, one nonexistent child path, one Label text target, one String source, and a 2.5-second fallback delay. It does not establish direct-binding behavior, null or malformed parameters, other missing-path qualities, tag creation or deletion while mounted, multiple references, embedded or parent-driven values, rapid changes, other data types or targets, bidirectional bindings, writes, reconnects, or other fallback delays.

### Two-reference path assembly and one-child recovery

The tested read-only form assembled one qualified path from two named persistent String inputs. The binding used one reference for the approved parent path, one for its child name, and a slash-delimited template containing both placeholders:

```json
{
  "params": {
    "basePath": "[<provider>]<approved-parent-path>",
    "tagName": "<approved-child-name>"
  },
  "propConfig": {
    "params.basePath": {
      "paramDirection": "input",
      "persistent": true
    },
    "params.tagName": {
      "paramDirection": "input",
      "persistent": true
    }
  },
  "root": {
    "children": [
      {
        "propConfig": {
          "props.text": {
            "binding": {
              "config": {
                "fallbackDelay": 2.5,
                "mode": "indirect",
                "references": {
                  "basePath": "{view.params.basePath}",
                  "tagName": "{view.params.tagName}"
                },
                "tagPath": "{basePath}/{tagName}"
              },
              "type": "tag"
            }
          }
        },
        "type": "ia.display.label"
      }
    ]
  }
}
```

On the tested primary root view, the initial parent/child pair resolved to an independently verified Good String value. A fixed Gateway-scope Button changed only `view.params.tagName` to a known nonexistent child while leaving `basePath` unchanged. Controlled property-bound markers showed the state and complete assembled path independently of tag-binding success.

After the configured 2.5-second fallback delay, the Label painted literal `null`, did not paint its distinct stored fallback, and showed the red error overlay, icon, and `ERROR` footer. Quality detail reported `Bad_NotFound`, the exact Label target-property path, and the complete assembled missing path. Restoring only the child-name parameter recovered the original Good value and removed the overlay, icon, footer, and popover without remounting.

Independently read both complete qualified paths before mounting, during the missing state, after restoration, and after browser cleanup. Require exact value, quality, and timestamp signatures and an explicit zero-write result. Capture the initial Good, missing, complete quality-detail, and restored states. If the diagnostic panel is shorter than its content, scroll the panel and prove every value is inside the viewport.

This proves only two named String references, exact slash-delimited `{basePath}/{tagName}` assembly, changing one child-name reference, one Label text target, direct root-view assignments, one known missing child, and a 2.5-second fallback delay. It does not establish three or more references, repeated placeholders, delimiter escaping, null/empty/malformed individual segments, changing both references together, parent-driven or embedded values, rapid changes, other data types or targets, bidirectional behavior, writes, reconnects, or other fallback delays.

### Coordinated two-reference Good-path changes

For the tested primary root view, one Gateway-scope Button event assigned both persistent String reference inputs sequentially so the final pair resolved to a second independently verified Good path. A second event assigned both original inputs sequentially to restore the first Good path:

```python
self.view.params.basePath = "[<provider>]<approved-second-parent>"
self.view.params.tagName = "<approved-second-child>"
```

Use controlled property-bound state and complete-path markers that are updated after both reference assignments. Before mounting and at every settled state, independently read both complete qualified paths and require exact Good values, qualities, source timestamps, and explicit zero-write results.

On the tested client, a five-second settle after each click produced the exact first Good value, second Good value, and restored first Good value without remounting. The stored fallback, quality overlay, error icon, and quality popover were absent in all three captured states. The complete marker and bound value were synchronized in each screenshot.

The two assignments inside each event are sequential, not an atomic object replacement. This test did not observe the interval between assignments and cannot prove that Perspective never attempted an intermediate mixed path. Report the result as settled two-reference re-resolution, not atomic switching. Do not shorten the tested settle interval or make claims about intermediate quality without a focused timing test.

This proves only two named String references, two independently verified Good parent/child pairs, direct sequential assignments within one synchronous Button event, settled results after five seconds, one Label text target, and restoration. It does not establish atomicity, intermediate-path behavior, shorter timing, three or more references, repeated placeholders, delimiter escaping, invalid segments, parent-driven or embedded values, rapid changes, other types or targets, bidirectional behavior, writes, reconnects, or other delays.

### Parent-driven embedded-child references

For the tested single embedded child, the parent owned two custom String properties and property-bound each one into the corresponding embedded-view parameter:

```json
{
  "custom": {
    "basePath": "[<provider>]<approved-parent-path>",
    "tagName": "<approved-child-name>"
  },
  "root": {
    "children": [
      {
        "propConfig": {
          "props.params.basePath": {
            "binding": {
              "config": { "path": "view.custom.basePath" },
              "type": "property"
            }
          },
          "props.params.tagName": {
            "binding": {
              "config": { "path": "view.custom.tagName" },
              "type": "property"
            }
          }
        },
        "props": {
          "params": {
            "basePath": "<distinct-stored-fallback>",
            "tagName": "<distinct-stored-fallback>"
          },
          "path": "<approved-child-view-path>"
        },
        "type": "ia.display.view"
      }
    ]
  }
}
```

The child declared both inputs at view level and used them in its two-reference indirect tag binding:

```json
{
  "params": {
    "basePath": "<distinct-child-fallback>",
    "tagName": "<distinct-child-fallback>"
  },
  "propConfig": {
    "params.basePath": { "paramDirection": "input", "persistent": true },
    "params.tagName": { "paramDirection": "input", "persistent": true }
  }
}
```

Use parent-side property-bound state and complete-path markers plus a child-side expression marker that assembles the two received parameters. Independently read both complete tag paths through an approved zero-write API. Require the parent marker, child marker, and child-bound value to agree at every captured settled state.

On the tested client, sequentially changing both parent custom properties in one synchronous Button event propagated both values into the mounted child. After a settle longer than the configured 2.5-second fallback delay, the child marker and indirect Label resolved to the second independently verified Good String path and value. Sequentially restoring both parent properties returned the first path and value without remounting. Stored fallbacks and error indicators were absent in all captured states.

The two parent assignments are sequential. This does not prove atomic propagation or the absence of an intermediate mixed child path. Report only settled behavior. The result is limited to one direct parent, one embedded child with a static `props.path`, two String input parameters, one indirect Label target, two Good paths, synchronous Button assignments, and the tested settle interval. It does not establish multiple children, deeper nesting, dynamic embedded-view paths, parameter output direction, other types or targets, invalid paths, rapid changes, reconnect persistence, bidirectional behavior, writes, or shorter timing.

### Null, empty, and malformed indirect inputs

For the tested single-reference indirect String binding, fixed Gateway-scope Buttons directly assigned `None`, an empty String, malformed `[<provider>`, and the original Good qualified path to the persistent root-view input parameter. Separate property-bound markers displayed controlled state names and human-readable parameter representations so path-binding failure did not obscure which input was active.

All three invalid inputs painted literal `null`, did not paint the distinct stored fallback, and added the red error overlay, icon, and `ERROR` footer. Their quality details were not equivalent:

- Null reported `Error_InvalidPathSyntax` and described that the named indirection reference did not produce a value.
- Empty String reported `Bad_NotFound`, the exact target-property path, and no Description section.
- The tested unmatched opening-provider-bracket string reported `Error_InvalidPathSyntax` and identified the illegal `[` character at line 1, character 1.

Restoring the original qualified Good path after the ordered null, empty, and malformed sequence restored the exact Good value and removed the overlay, icon, footer, and popover without remounting. Independent API reads of valid qualified Good and known-missing paths remained value/quality/timestamp exact and reported zero writes. Do not send null, empty, or malformed values to a caller-scoped tag API whose contract accepts qualified paths; use painted quality detail for those client-only invalid inputs.

Capture every invalid state and its quality detail independently. A popover may require both internal panel scrolling and root-view scrolling to expose the complete diagnostic. The tested empty state had no Description section, so preserve DOM section inventory instead of assuming missing text was clipped.

This proves only the exact single-reference binding, Label target, direct root-view assignments, null/empty/unmatched-opening-bracket values, and 2.5-second fallback delay. It does not establish other malformed strings or provider forms, multiple references, embedded or parent-driven parameters, rapid changes, direct bindings, other types or targets, bidirectional behavior, writes, reconnects, or other delays.

## Boundary

This contract does not establish three-or-more-reference, repeated-placeholder, delimiter-escaping, atomic, intermediate-resolution, shorter-than-tested-settle, multi-child, deeper-nested, dynamic-child-path, rapidly changing, or reconnect-persistent indirect bindings, nested indirect composition beyond the exact tested single parent-to-child handoff, polling or rate behavior, range/color/style/expression map variants, other format patterns/types/locales, longer or different transform chains, bidirectional behavior, fallback timing or invalid-path behavior beyond the exact tested direct/indirect String and null/empty/malformed cases, other overlay/error behavior, general client quality propagation, direct-binding path changes or recovery, tag lifecycle changes while mounted, general writeback beyond the exact guarded Float8 fixture, alarming, history, other tag types, arbitrary expression functions or numeric operators, other script-transform forms or side effects, coercion among other property types, or unlisted component-event execution. Test each behavior independently before adding it to a reusable skill.
