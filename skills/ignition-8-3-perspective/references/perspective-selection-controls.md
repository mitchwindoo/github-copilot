# Perspective selection controls

Use these forms only after inspecting the installed Ignition 8.3 component descriptors on the target build. Qualify writes with independent live value, type, quality, and source-timestamp evidence; painted labels alone are insufficient.

## Contents

- [Checkbox](#checkbox)
- [Toggle Switch](#toggle-switch)
- [Radio Group](#radio-group)
- [Document-bound Radio Group choices](#document-bound-radio-group-choices)
- [Searchable single-select Dropdown](#searchable-single-select-dropdown)
- [Document-bound single-select options](#document-bound-single-select-options)
- [Searchable multi-select Dropdown](#searchable-multi-select-dropdown)
- [Observed interaction behavior](#observed-interaction-behavior)
- [Multi-select interaction behavior](#multi-select-interaction-behavior)
- [Toggle and Radio dependency behavior](#toggle-and-radio-dependency-behavior)
- [Multi-State Button](#multi-state-button)
- [Multi-State Button interaction behavior](#multi-state-button-interaction-behavior)
- [Runtime validation](#runtime-validation)
- [Boundary](#boundary)

## Checkbox

Use `ia.input.checkbox`. Bind Boolean `props.selected` directly to a caller-approved memory tag with `bidirectional: true` inside the tag binding configuration:

```json
{
  "meta": {"name": "EnabledCheckbox"},
  "propConfig": {
    "props.selected": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Enabled",
          "bidirectional": true
        },
        "type": "tag"
      }
    }
  },
  "props": {
    "enabled": true,
    "selected": true,
    "text": "Enabled",
    "textPosition": "right",
    "triState": false
  },
  "type": "ia.input.checkbox"
}
```

Use a deliberately opposite stored fallback when testing initial binding replacement. The installed 3.3.8 descriptor permits Boolean or null `selected`; this test qualifies only two-state Boolean behavior with `triState: false`.

## Toggle Switch

Use `ia.input.toggle-switch`. Bind Boolean `props.selected` directly and bidirectionally to an approved Boolean memory tag. The installed 3.3.8 shape uses nested `label` and `color` objects:

```json
{
  "meta": {"name": "EnabledToggle"},
  "propConfig": {
    "props.selected": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Enabled",
          "bidirectional": true
        },
        "type": "tag"
      }
    }
  },
  "props": {
    "selected": true,
    "enabled": true,
    "label": {"text": "Radio Group Enabled", "position": "right", "style": {}},
    "color": {"selected": "#16a34a", "unselected": "#94a3b8", "disabled": "#cbd5e1"}
  },
  "type": "ia.input.toggle-switch"
}
```

## Radio Group

Use `ia.input.radio-group`. Its choices are in `props.radios`, not Dropdown-style `props.options`. Each installed 3.3.8 radio item requires `value`, `text`, and `selected`; store `enabled` and `style` explicitly for a reproducible shape. Bind `props.value` bidirectionally to the approved String tag. A second read-only direct binding may bind `props.enabled` to a Boolean tag:

```json
{
  "meta": {"name": "ModeRadioGroup"},
  "propConfig": {
    "props.value": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Mode",
          "bidirectional": true
        },
        "type": "tag"
      }
    },
    "props.enabled": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Enabled"
        },
        "type": "tag"
      }
    }
  },
  "props": {
    "value": "RUN",
    "index": 0,
    "radios": [
      {"enabled": true, "text": "Run", "selected": true, "value": "RUN", "style": {}},
      {"enabled": true, "text": "Hold", "selected": false, "value": "HOLD", "style": {}},
      {"enabled": true, "text": "Maintenance", "selected": false, "value": "MAINT", "style": {}}
    ],
    "orientation": "row",
    "align": "center",
    "justify": "space-evenly",
    "textPosition": "right",
    "enabled": true
  },
  "type": "ia.input.radio-group"
}
```

## Document-bound Radio Group choices

Bind `props.radios` read-only to an approved `Document` memory tag while binding `props.value` bidirectionally to a separate String tag:

```json
{
  "meta": {"name": "DynamicModeRadioGroup"},
  "propConfig": {
    "props.radios": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Radios"
        },
        "type": "tag"
      }
    },
    "props.value": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Mode",
          "bidirectional": true
        },
        "type": "tag"
      }
    }
  },
  "props": {
    "value": "STORED_FALLBACK",
    "index": 0,
    "radios": [
      {"enabled": true, "text": "Stored fallback", "selected": false, "value": "STORED_FALLBACK", "style": {}}
    ],
    "orientation": "row",
    "align": "center",
    "justify": "space-evenly",
    "textPosition": "right",
    "enabled": true
  },
  "type": "ia.input.radio-group"
}
```

Use a Document array whose members have exact `value`, `text`, `selected`, `enabled`, and `style` keys. On Ignition 8.3.8 / Perspective 3.3.8, changing this Document repainted order, labels, enabled state, and selection in one continuously mounted page.

Treat each nested `selected` member as active state, not display-only metadata. With `props.value` bidirectionally bound, the tested component reconciled Document changes into that String binding:

- reordering, relabeling, and disabling items while keeping RUN selected preserved Good `RUN` and its source timestamp;
- a real pointer click on dynamically disabled HOLD caused no Document or String write;
- selecting enabled MAINT wrote Good `MAINT` to the String tag without writing the read-only Document binding;
- removing the currently selected MAINT item cleared live selection and wrote a Good empty String, not null, to the String tag;
- restoring MAINT with every item `selected:false` retained the empty String and no painted selection without another String write;
- after pointer selection had established Good `Mode=MAINT`, changing only the Document so RUN became `selected:true` and MAINT became `selected:false` made the changed Document win the direct conflict: the component painted RUN and wrote Good `RUN` to the String tag; and
- replacing that Document with an equivalent baseline that still selected RUN did not produce an additional String write.

Avoid competing authorities. If `props.radios` is dynamic and `props.value` is bidirectional, normalize nested `selected` fields to agree with the intended value before writing the Document. A changed Document's nested selection overrode the already bound String value in the tested MAINT-versus-RUN conflict. Removing the current value is also a write-producing operation at this boundary, so validate downstream handling of the empty String explicitly.

## Searchable single-select Dropdown

Use `ia.input.dropdown`. Each static option object requires `value` and `label`; use `isDisabled: true` for a disabled option. Bind `props.value` to the approved String memory tag:

```json
{
  "meta": {"name": "ModeDropdown"},
  "propConfig": {
    "props.value": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Mode",
          "bidirectional": true
        },
        "type": "tag"
      }
    }
  },
  "props": {
    "allowCustomOptions": false,
    "enabled": true,
    "multiSelect": false,
    "options": [
      {"value": "RUN", "label": "Run", "isDisabled": false},
      {"value": "HOLD", "label": "Hold", "isDisabled": false},
      {"value": "STOP", "label": "Stop", "isDisabled": true}
    ],
    "placeholder": {"text": "Choose mode"},
    "search": {
      "enabled": true,
      "matching": "any",
      "noResultsText": "No matching mode",
      "searchParam": ""
    },
    "showClearIcon": false,
    "value": "STORED_FALLBACK"
  },
  "type": "ia.input.dropdown"
}
```

## Observed interaction behavior

On Ignition 8.3.8 / Perspective 3.3.8 with the exact shapes above:

- each Checkbox pointer click changed the Boolean tag once, changed its source timestamp, repainted the checkbox icon, and left the String tag unchanged;
- opening the Dropdown displayed all three options without a write;
- pointer selection of enabled `Hold` and `Run` options wrote `HOLD` and `RUN` respectively and changed only the String source timestamp;
- a real pointer click at the center of disabled `Stop` left the menu open, retained `HOLD`, and caused no value or timestamp change;
- typing `hol` filtered the visible option list to `Hold` without a write;
- pressing Enter immediately after filtering closed the menu without selecting or writing; and
- reopening, filtering, pressing ArrowDown, then Enter selected `HOLD` and changed the String timestamp.

The Dropdown's painted label used the option `label`, while the tag and read-only mirror used the option `value`. Do not assume label and value are interchangeable.

## Document-bound single-select options

Bind `props.options` read-only to an approved `Document` memory tag while keeping `props.value` bidirectional to a separate String tag:

```json
{
  "propConfig": {
    "props.options": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Options"
        },
        "type": "tag"
      }
    },
    "props.value": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Mode",
          "bidirectional": true
        },
        "type": "tag"
      }
    }
  },
  "props": {
    "multiSelect": false,
    "options": [
      {"value": "RUN", "label": "Stored fallback", "isDisabled": false}
    ],
    "value": "STORED_FALLBACK"
  },
  "type": "ia.input.dropdown"
}
```

Use a Document array whose members have exact `value`, `label`, and `isDisabled` keys. On Ignition 8.3.8 / Perspective 3.3.8, a changed Document value updated order and labels in one already-mounted page. When the selected `value` remained present, changing only its label repainted the selected label without changing the bound String value or its source timestamp. Restoring the Document repainted the baseline label with the same no-write behavior. The open single-select menu displayed all options, including the selected option; a disabled option remained inert under a real pointer click.

Use official tag import/export for configuration mutation and readback. Use a separately tested live-value API for value, quality, and source timestamp. An identical Document import may leave the timestamp unchanged; require a timestamp advance only when the Document value actually changes.

## Searchable multi-select Dropdown

Bind `props.value` bidirectionally to an approved `StringArray` memory tag. Set `multiSelect`, `wrapMultiSelectValues`, and `showClearIcon` explicitly:

```json
{
  "meta": {"name": "ModesDropdown"},
  "propConfig": {
    "props.value": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/SelectedModes",
          "bidirectional": true
        },
        "type": "tag"
      }
    }
  },
  "props": {
    "allowCustomOptions": false,
    "enabled": true,
    "multiSelect": true,
    "wrapMultiSelectValues": true,
    "showClearIcon": true,
    "options": [
      {"value": "RUN", "label": "Run", "isDisabled": false},
      {"value": "HOLD", "label": "Hold", "isDisabled": false},
      {"value": "MAINT", "label": "Maintenance", "isDisabled": false},
      {"value": "STOP", "label": "Stop (disabled)", "isDisabled": true}
    ],
    "placeholder": {"text": "Choose one or more modes"},
    "search": {
      "enabled": true,
      "matching": "any",
      "noResultsText": "No matching mode",
      "searchParam": ""
    },
    "value": ["STORED_FALLBACK"]
  },
  "type": "ia.input.dropdown"
}
```

The installed 3.3.8 descriptor permits array values and defaults `wrapMultiSelectValues` to true, but store it explicitly for a reproducible authored shape.

## Multi-select interaction behavior

On Ignition 8.3.8 / Perspective 3.3.8 with the exact shape above and a `StringArray` tag:

- selected options rendered as ordered removable pills and were omitted from the open menu;
- pointer additions preserved selection order in the tag;
- filtering `maint`, then ArrowDown and Enter, appended `MAINT`; filtering and ArrowDown alone did not write;
- a pointer click on disabled `STOP` left the value and source timestamp unchanged;
- an individual pill remove control removed only that value;
- selecting `HOLD` and then `RUN` produced `HOLD,RUN` in both pills and the tag; and
- the global clear control wrote a Good-quality null, not an empty array, painted the placeholder, and did not itself toggle the menu's existing open/closed state.

Treat clear-to-null as part of the component contract for this tested boundary. If downstream logic requires `[]`, design and independently test an explicit normalization policy instead of assuming the clear icon supplies it.

The bound tag is authoritative on a fresh page. If a retained `StringArray` tag contains `RUN`, the Dropdown immediately paints a Run pill; that is binding hydration, not an open-menu selection. For an empty review/demo state, retain a Good null tag value. In fresh headless sessions, a real pointer click opened the menu from Good null without creating a pill, changing the null value or source timestamp, or producing browser, page, request, or Gateway WARN-or-higher errors. The word `Run` appearing as the first row of the open menu is only an available option; it is not evidence that Run is selected. Distinguish menu-option visibility from a painted selected pill, and always read the bound tag and timestamp before attributing a selection to the click itself.

## Toggle and Radio dependency behavior

On Ignition 8.3.8 / Perspective 3.3.8 with the exact Toggle Switch and Radio Group shapes above:

- selecting `HOLD`, `MAINT`, and `RUN` changed only the Good String tag and its source timestamp;
- toggling off changed only the Good Boolean tag and immediately added `ia_radioGroupComponent__disabled` while disabling all three native radio inputs;
- a real pointer click at the center of disabled Maintenance caused exact zero Boolean/String value or timestamp drift;
- toggling on changed only the Boolean tag, removed the disabled state, and preserved the selected String value; and
- two independent seven-state runs reproduced the sequence with zero component scripts, browser/page/request errors, quality overlays, claim-relevant warnings, or unclassified warnings.

Inspect live selection using the native radio input's `checked` DOM property and selected icon, not the serialized `checked` HTML attribute alone. After selecting Hold, one observed `outerHTML` snapshot retained `checked=""` on the originally stored Run input while the live property and selected icon correctly identified Hold. Attribute serialization was stale for that runtime state.

## Multi-State Button

Use `ia.input.multi-state-button`. Keep requested command and indication explicit rather than assuming one value serves both purposes:

```json
{
  "type": "ia.input.multi-state-button",
  "props": {
    "enabled": true,
    "orientation": "row",
    "primary": true,
    "states": [
      {
        "text": "Hand",
        "value": 2,
        "selectedStyle": {"backgroundColor": "#facc15", "classes": ""},
        "unselectedStyle": {"classes": ""}
      },
      {
        "text": "Off",
        "value": 0,
        "selectedStyle": {"backgroundColor": "#ef4444", "classes": ""},
        "unselectedStyle": {"classes": ""}
      },
      {
        "text": "Auto",
        "value": 1,
        "selectedStyle": {"backgroundColor": "#22c55e", "classes": ""},
        "unselectedStyle": {"classes": ""}
      }
    ]
  },
  "propConfig": {
    "props.controlValue": {
      "binding": {
        "type": "property",
        "config": {
          "path": "view.custom.commandValue",
          "bidirectional": true
        }
      }
    },
    "props.indicatorValue": {
      "binding": {
        "type": "property",
        "config": {"path": "view.custom.indicatorValue"}
      }
    }
  }
}
```

Declare the two numeric view-custom properties and their persistence separately. Bind read-only Labels to both values so runtime tests can distinguish the requested command from the current indication.

For an explicit local acknowledgment fixture, use a second Multi-State Button whose bidirectional `controlValue` and one-way `indicatorValue` both reference the indication property. This is a testing and UI pattern, not a device-acknowledgment implementation.

Set `props.orientation` to `column` for the tested vertical button stack. Preserve the `states` array order; the tested non-numeric sequence painted `Hand`, `Off`, `Auto` for values `2`, `0`, `1` in exactly that authored order.

## Multi-State Button interaction behavior

On the tested build, clicking a state changed `controlValue` but selected paint continued to follow `indicatorValue`:

- initial command/indicator `0/0` selected Off;
- clicking command Auto produced `1/0` while Off remained selected;
- clicking command Hand produced `2/0` while Off remained selected;
- acknowledging Hand changed only indication to `2` and selected Hand on both command and acknowledgment controls;
- clicking command Auto then produced `1/2` while Hand remained selected; and
- acknowledging Auto converged to `1/1` and selected Auto on both controls.

Repeating the already requested Hand command preserved every visible and bound value in this script-free fixture. That is visible-state evidence only; it does not prove event suppression because no event counter was installed.

Each state rendered as a native `button type="submit"`. Enabled selected buttons exposed no `aria-pressed` or `aria-selected` attribute; selected paint was represented by a build-specific class and selected inline style. Treat that class as a test selector to rediscover, not as a public application contract.

When the component was disabled, all three native buttons carried `disabled`. A real pointer click was inert, programmatic focus did not make the button active, and Enter from the unchanged active element was inert. The independently configured indicated state remained visibly selected despite the control being disabled.

The column-oriented synchronized control accepted Off by pointer and Auto by focused Enter, changing its persistent value from `2` to `0` to `1` and moving selected paint accordingly. A simultaneous second session retained its independent initial command/indicator/column values throughout.

## Runtime validation

Require at least these distinct states:

1. Bound Boolean and String values replace stored fallbacks.
2. Checkbox on and off each produce one matching Good Boolean write and timestamp transition.
3. Opening the menu produces the exact enabled/disabled options without tag drift.
4. Pointer-selecting two enabled options produces exact Good String writes.
5. Pointer-clicking the disabled option leaves menu, selected label, live value, and timestamp unchanged.
6. Search text filters the visible options without writing.
7. Plain Enter after filtering closes without selecting.
8. ArrowDown then Enter selects the filtered option.
9. Final pointer selection restores the retained baseline.

For every state, save a screenshot and DOM/geometry inspection, including open-menu and option rectangles. Require exact selected labels, native Checkbox checked/icon state, independent tag value/type/quality/timestamps, read-only mirror paint, stable official session/page/view topology, zero component scripts, zero reconnects, zero browser/page errors, no quality overlays, and classified Gateway WARN-or-higher logs. If a matching session remains after browser close, terminate exactly that session through official Perspective OpenAPI; otherwise record zero matches. Always inspect post-close logs.

For multi-select, additionally require ordered pill labels and exact ordered array values; selected-option omission from the menu; no-write timestamp checks for search, ArrowDown, menu open, and disabled-option edges; one individual pill removal; clear from both an open and a closed menu; explicit null value/type/kind evidence after each clear; reordered selection; final baseline restoration; and a delayed post-close tag/log/session check. Use a live-read API that preserves arrays as JSON arrays and preserves null as null. Do not wrap a null response in a host-language array during normalization.

For Document-bound options, additionally keep one page mounted while changing only the Options tag. Require exact option order, labels, and disabled state; selected-label repaint; stable session/page/view identity; unchanged selected String value and timestamp across each options-only change; an advancing Options timestamp for each real value change; exact baseline restoration; and live reads that preserve nested objects rather than stringifying them or returning only their keys.

For a Toggle-Switch-controlled Radio Group, additionally require the Toggle's native checkbox property, all Radio Group native input `checked` and `disabled` properties, the selected icon, the group disabled class, exact Boolean/String tag values and source timestamps, a real disabled-choice pointer edge, preservation of the selected String while disabling/re-enabling, and final baseline restoration.

For Document-bound Radio Group choices, additionally keep one page mounted while reordering/relabeling/disabling items, selecting an enabled item, directly conflicting that bound value with a different nested selection, removing a current item, restoring all items with `selected:false`, and then setting one nested `selected:true`. At every state, require exact live order, text, native `checked` and `disabled` properties, selected icon, independent Document/String values and timestamps, and stable session/page/view identity. Prove that the disabled pointer edge is inert, the pointer selection writes only the String, the changed Document wins the direct nested-selection conflict, selected-item removal writes an empty String, neutral restoration causes no second String write, and a later nested `selected:true` transition writes that value through the bidirectional String binding. Restore and verify an exact baseline at the end.

For Multi-State Button, additionally require exact authored state text/value order; independent command and indicator Labels; selected paint derived separately from focus; one pending command, one acknowledgment, a second pending command and acknowledgment; one same-state visible no-change edge; native button type/disabled attributes; absence or presence of ARIA selected/pressed state; a real disabled pointer edge; a failed disabled-focus plus Enter edge; row and column geometry; one column pointer selection; one focused Enter activation; and a simultaneous unchanged second session. Preserve complete screenshots because focus and selected paint can legitimately identify different states.

## Boundary

This evidence covers one two-state Checkbox bound to a Boolean memory tag; one Toggle Switch bound to a Boolean memory tag; one static Radio Group with three String choices whose value is bound bidirectionally to a String tag and whose enabled state is bound read-only to that Boolean tag; one Radio Group whose three choices are directly bound to a Document tag and whose value is bidirectionally bound to a separate String tag; one searchable single-select Dropdown bound to a String memory tag with three static String options; one searchable single-select Dropdown whose options are directly bound to a Document tag with four String-valued objects; one searchable multi-select Dropdown bound to a StringArray memory tag with four static String options; and four three-state Multi-State Buttons using persistent numeric property bindings for command, indication, acknowledgment, and synchronized column state. The Toggle/Radio boundary includes enabled selection, tag-mediated disable/re-enable, selected-value preservation, and one disabled pointer edge. The dynamic-Radio boundary includes one continuously mounted page; reorder/relabel/disable; one disabled-item pointer edge; enabled selection; a direct stored-MAINT-versus-nested-RUN conflict; selected-item removal to an empty String; neutral restoration; nested `selected:true` propagation; and exact baseline restoration. The Document-options Dropdown boundary includes one live reorder/relabel, one restoration, preserved selected values, selected-label repaint, one disabled pointer edge, and timestamp-backed no-write proof. The multi-select boundary includes wrapped pills, clear icon, ordered pointer selections, one individual removal, exact `maint` filtering, ArrowDown-plus-Enter, one disabled option, clear from open and closed menus, null readback, and final restoration. The Multi-State Button boundary includes non-numeric state order, row/column orientation, command/indicator divergence, two acknowledgments, selected paint, one same-state visible edge, native disabled behavior, pointer/Enter input, and two-session isolation on Ignition 8.3.8 / Perspective 3.3.8.

It does not establish tri-state Checkbox behavior, disabled Checkbox behavior, disabled Toggle Switch behavior, static per-radio disabled-item behavior, Radio Group column orientation or other align/justify/text positions, multiple simultaneously true nested Radio `selected` fields, duplicate Radio values, empty/non-array Radio Documents, unwrapped multi-select values, custom options, conversion of Dropdown clear-time null to an empty array, datasets, dynamically bound multi-select Dropdown options, non-Document dynamic sources, numeric/Boolean/object/array Dropdown option values, removal of the currently selected value from a live Dropdown options list, duplicate Dropdown values/labels, no-result behavior, other search strings/matching modes, arbitrary keyboard navigation, Multi-State Button tag writeback, device acknowledgment or latency, optimistic/pending styling, Multi-State Button component events or event suppression, duplicate/non-numeric Multi-State Button values, empty/dynamic state arrays, per-state security, Space/arrow-key Multi-State Button behavior, touch/mobile input, arbitrary style precedence, accessibility semantics beyond the exact observed attributes, focus/blur edge cases, bad quality, tag security, external competing writers, network loss, navigation/reload persistence, Designer behavior, or other builds. Test each independently.
