# Perspective input components

Use these forms only after inspecting the installed Ignition 8.3 component descriptors on the target build. Preserve the surrounding live view shape and qualify each component through browser interaction, official topology, screenshots, geometry, and bounded Gateway logs.

## Contents

- [Text Field](#text-field)
- [Numeric Entry Field](#numeric-entry-field)
- [Date Time Input](#date-time-input)
- [Date Time Picker](#date-time-picker)
- [Date and time runtime validation](#date-and-time-runtime-validation)
- [Slider](#slider)
- [Slider runtime validation](#slider-runtime-validation)
- [One-Shot Button](#one-shot-button)
- [One-Shot Button runtime validation](#one-shot-button-runtime-validation)
- [Signature Pad](#signature-pad)
- [Signature Pad runtime validation](#signature-pad-runtime-validation)
- [Bidirectional draft bindings](#bidirectional-draft-bindings)
- [Direct bidirectional tag bindings](#direct-bidirectional-tag-bindings)
- [Guarded local submit and reset](#guarded-local-submit-and-reset)
- [Runtime validation](#runtime-validation)
- [Boundary](#boundary)

## Text Field

Use `ia.input.text-field` and bind its writable `props.text` property. The tested retained shape used deferred updates and rejected external updates while focused:

```json
{
  "meta": {"name": "NameInput"},
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "path": "view.custom.draftName",
          "bidirectional": true
        },
        "type": "property"
      }
    }
  },
  "props": {
    "deferUpdates": true,
    "enabled": true,
    "placeholder": "Enter a required name",
    "rejectUpdatesWhileFocused": true,
    "spellcheck": false,
    "text": "STORED_FALLBACK"
  },
  "type": "ia.input.text-field"
}
```

With the exact tested configuration, typing `Beta` while the field remained focused changed the browser input but left the property-bound draft marker at `Alpha`. Pressing Enter kept focus on the field and propagated `Beta` into the bidirectionally bound view-custom String.

Treat the stored component value as a detectable fallback only. Require the bound initial value to replace it at runtime.

## Numeric Entry Field

Use `ia.input.numeric-entry-field` and bind its writable `props.value` property. The tested direct-mode shape used numeric bounds and an explicit invalid style:

```json
{
  "meta": {"name": "SetpointInput"},
  "propConfig": {
    "props.value": {
      "binding": {
        "config": {
          "path": "view.custom.draftSetpoint",
          "bidirectional": true
        },
        "type": "property"
      }
    }
  },
  "props": {
    "align": "right",
    "enabled": true,
    "format": "0,0.0#",
    "inputBounds": {
      "minimum": 0,
      "maximum": 100,
      "invalidStyle": {
        "backgroundColor": "#fee2e2",
        "border": "3px solid #dc2626"
      }
    },
    "mode": "direct",
    "placeholder": "0 to 100",
    "spinner": {"enabled": true, "increment": 0.5},
    "value": -999
  },
  "type": "ia.input.numeric-entry-field"
}
```

In the exact tested direct mode, the idle browser input was read-only. One pointer click entered edit mode, removed read-only state, focused the input, and exposed the numeric spinner. Replacing `12.5` with in-range `25.5` and pressing Enter exited edit mode and propagated numeric `25.5` into the bound draft.

Typing out-of-range `150` while focused kept `150` visible and applied the configured invalid border and background, but the bound draft remained `25.5`. Pressing Enter rejected the edit, exited edit mode, restored visible `25.5`, removed the invalid style, and did not write the invalid value into the view-custom draft.

## Date Time Input

Use `ia.input.date-time-input`. The tested date-mode shape was:

```json
{
  "type": "ia.input.date-time-input",
  "props": {
    "format": "YYYY-MM-DD",
    "pickerType": "date"
  },
  "propConfig": {
    "props.value": {
      "binding": {
        "type": "expr",
        "config": {"expression": "now(0)"}
      }
    }
  }
}
```

On the tested build, its painted text input was read-only. A pointer click opened a calendar popup containing 35 visible day tiles; Escape removed that popup. Do not automate direct text entry merely because the component contains an HTML input.

For time mode, set `pickerType` to `time`; the tested format was `HH:mm:ss A`. It painted inline hour, minute, and second text inputs, an AM/PM select, and increment/decrement buttons. One pointer increment changed only the current session; another simultaneous session remained unchanged.

## Date Time Picker

Use `ia.input.date-time-picker`. It renders an inline calendar and time editor rather than a collapsed popup field on the tested build:

```json
{
  "type": "ia.input.date-time-picker",
  "props": {
    "format": "YYYY-MM-DD HH:mm:ss ZZ"
  },
  "propConfig": {
    "props.value": {
      "binding": {
        "type": "expr",
        "config": {"expression": "now(0)"}
      }
    }
  }
}
```

For the tested calendar-day boundary, bind `minDate` and `maxDate` separately:

```json
{
  "props.minDate": {
    "binding": {
      "type": "expr",
      "config": {"expression": "addDays(now(0), -7)"}
    }
  },
  "props.maxDate": {
    "binding": {
      "type": "expr",
      "config": {"expression": "addDays(now(0), 7)"}
    }
  }
}
```

When that range remained inside one calendar month and year, the month select still contained 12 options but disabled 11, while the year select contained only the permitted year. Clicking an out-of-range tile left the selected day unchanged; clicking an enabled in-range tile moved the selected-day marker. This proves client selection and range enforcement only. It does not prove bidirectional persistence or tag writeback.

## Date and time runtime validation

Treat intrinsic picker height as unknown until rendered. In the exact tested 1280-pixel-wide column-flex fixture, a 94-pixel basis clipped the day grid and a 290-pixel basis exposed the calendar but overlapped the time editor. A 390-pixel basis contained both. These are fixture measurements, not universal sizing constants; capture original-resolution screenshots and require every visible input, select, and button to remain within its component root.

For a bounded qualification, use two fresh sessions and require at least:

1. Exact component types, formats, picker modes, bindings, and resource readback.
2. Date-mode read-only state, popup creation, screenshot/geometry, and Escape dismissal.
3. Time-mode spinner behavior and cross-session isolation.
4. Inline picker month/year option counts before interaction.
5. An out-of-range click that does not move the selected-day marker.
6. An enabled click that does move the marker in only the interacting session.
7. No clipping, native error screen, quality overlay, browser/page/request failure, unexpected Gateway WARN-or-higher entry, project drift, or protected-resource drift.
8. Official session topology showing both pages during the test and zero active test pages after delayed cleanup. Browser closure can precede server topology cleanup, so poll rather than assuming immediate removal.

DOM class names such as the selected, out-of-range, and adjacent-month tile markers are observed test selectors, not a public application contract. Rediscover them on another Perspective build.

## Slider

Use `ia.input.slider`. The tested horizontal shape used explicit bounds, steps, labels, and a bidirectional persistent view-custom binding:

```json
{
  "type": "ia.input.slider",
  "props": {
    "enabled": true,
    "labels": {"interval": 25, "show": true},
    "min": -100,
    "max": 100,
    "step": 25,
    "value": 999
  },
  "propConfig": {
    "props.value": {
      "binding": {
        "type": "property",
        "config": {
          "path": "view.custom.sliderValue",
          "bidirectional": true
        }
      }
    }
  }
}
```

Declare the bound numeric source and its persistence separately:

```json
{
  "custom": {"sliderValue": 0},
  "propConfig": {
    "custom.sliderValue": {"persistent": true}
  }
}
```

The binding replaced the stored component fallback before interaction. A read-only Label bound to the same view-custom value exposed every accepted change.

The live focus target was a `div` with `role="slider"`, `tabindex="0"`, and numeric `aria-valuemin`, `aria-valuemax`, and `aria-valuenow` attributes. It was not a native range input. On the tested horizontal control, ArrowRight advanced one configured step, Home selected the minimum, End selected the maximum, and a real pointer drag settled on a configured step. Each accepted action updated the bound Label.

For a vertical control, set `props.orientation` to `vertical`. ArrowUp advanced one configured step, while Home and End still selected the minimum and maximum. A real vertical pointer drag changed the value and bound Label. Do not calculate an expected value from raw rail percentage alone: the exact tested drag aimed at the lower fifth of the rail but settled at the adjacent configured step. Observe the rendered handle/rail geometry and assert the actual step result.

A disabled Slider still exposed a focusable role-slider element on the tested build, but carried `aria-disabled="true"`. End and a real pointer drag left its value unchanged. Do not infer editability from `tabindex` or programmatic focus success; require the disabled state and no-change proof.

## Slider runtime validation

For a new Slider shape, validate at least:

1. Exact project readback of type, min/max/step/value, labels, orientation, enabled state, and binding placement.
2. Stored-fallback replacement by the bound initial numeric value.
3. Role-slider ARIA min/max/current/disabled state and positive root/rail/handle geometry.
4. One step key plus Home and End on each qualified orientation.
5. One real pointer drag performed through browser pointer coordinates, not direct DOM value assignment or synthetic JavaScript dispatch.
6. Bound Label propagation after every accepted change.
7. A disabled keyboard attempt and pointer attempt that both preserve the value.
8. A simultaneous second session that preserves its independent initial values.
9. Original-resolution screenshots proving all labels, handles, rails, ticks, and page evidence rows are visible. Matching document and viewport dimensions alone does not prove authored content is unclipped.
10. Stable official topology, zero browser/page/request failures, unchanged project/protected resources during runtime, delayed cleanup to zero active test pages, and bounded Gateway log inspection at every edge and after close.

The tested Slider DOM classes and exact pixel geometry are build- and fixture-specific test evidence, not public application contracts. Rediscover them before using selectors on another build.

## One-Shot Button

Use `ia.input.oneshotbutton` when one activation should write a configured target value and keep the control unavailable until the independently bound live value differs again. The tested direct-tag form was:

```json
{
  "type": "ia.input.oneshotbutton",
  "props": {
    "setValue": 1,
    "enabled": true,
    "primary": true,
    "readyState": {
      "text": "WRITE 1",
      "icon": {"path": "material/touch_app"},
      "style": {"padding": "12px"}
    },
    "writingState": {
      "text": "WRITING 1...",
      "icon": {"path": "material/hourglass_empty"},
      "style": {"padding": "12px"}
    }
  },
  "propConfig": {
    "props.value": {
      "binding": {
        "type": "tag",
        "config": {
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Command",
          "fallbackDelay": 2.5,
          "bidirectional": true
        }
      }
    }
  }
}
```

`props.value` is the observed/writable live value and `props.setValue` is the one-time write target. On the tested build, equality selected `writingState` and set the underlying native submit button's `disabled` property. A control whose bound value already equaled its `setValue` therefore mounted in the disabled writing state. When another approved writer changed the shared value away from that target, it returned to `readyState` and became enabled.

A real pointer press held for 500 milliseconds did not change the independently read value or source timestamp. Releasing the pointer wrote `setValue`, advanced the source timestamp, and moved every simultaneously mounted session that shared the tag into the same equality-derived state. Focused Enter also wrote `setValue`; once equality disabled that control, browser focus moved to `BODY` in the tested sequence.

For a confirmation gate, add only the qualified switch:

```json
{"confirm": {"enabled": true}}
```

The tested activation opened a session-local popup containing `Are you sure?`, `No`, and `Yes`. Opening it and selecting No left the live value and timestamp unchanged. Selecting Yes wrote `setValue`. Stored custom confirmation title/message members did not replace that default popup text in the tested fixture, so do not rely on them without inspecting the installed descriptor and reproducing their runtime behavior.

Setting `enabled` to false produced a native disabled submit button. It had no `aria-disabled` attribute, could not take focus, and a real pointer attempt did not change the value or timestamp. Do not infer accessibility or editability from the component type alone; inspect the rendered button state.

## One-Shot Button runtime validation

For a new One-Shot Button shape, validate at least:

1. Exact project readback of `props.value` binding placement, `setValue`, `readyState`, `writingState`, `enabled`, `primary`, and `confirm.enabled`.
2. Independent initial live value, runtime type, Good quality, and source timestamp.
3. A pointer-down hold proving no value/timestamp change, followed by pointer release proving the exact write and timestamp advance.
4. Equality-derived writing text and native disabled state in every session sharing the tag.
5. A separate approved write that makes the value differ and restores the ready state.
6. Confirmation open and No with exact no-write evidence, followed by Yes with exact write evidence; also prove the popup remains session-local.
7. A native-disabled pointer/focus attempt with no write, and a focused Enter activation on an enabled control.
8. Screenshots and positive in-viewport geometry for ready, held, writing, confirmation, confirmed-writing, and restored states.
9. Official two-session topology at every edge, zero browser/page/request failures, exact project/protected-resource isolation, delayed cleanup to zero active test pages, and bounded Gateway WARN-or-higher inspection at every edge and after close.

Official tag import/export is the configuration surface; it is not an independent runtime value/quality/timestamp observer. Use a health-advertised, caller-scoped live-read helper when available. For a runtime-only test reset, prefer a qualified live-value write surface with dry-run and verified apply when the official configuration import cannot perform the reset without delayed warnings. If no approved live write exists, require external fixture restoration rather than disguising a configuration rewrite as clean runtime control.

## Signature Pad

Use `ia.input.signature-pad` for pointer-drawn input. The tested enabled shape was:

```json
{
  "type": "ia.input.signature-pad",
  "meta": {"name": "Signature"},
  "props": {
    "enabled": true,
    "status": {"touched": false},
    "actionBar": {
      "position": "bottom",
      "clearButton": {"text": "Clear", "enabled": true, "primary": false},
      "submitButton": {"text": "Submit", "enabled": true, "primary": true}
    },
    "pad": {
      "canvas": {
        "clearColor": "#ffffff",
        "style": {"backgroundColor": "#ffffff"}
      },
      "pen": {"color": "#111827", "width": 3}
    }
  }
}
```

The installed component events were `onSignatureSubmitted` and `onSignatureCleared`, placed beneath `events.component` with the ordinary Perspective component-event script shape. On the tested build, `onSignatureSubmitted.event.signature` was a Jython `unicode` value beginning with `data:image/png;base64,`. `event.keys()` returned no enumerable keys for either tested event, so do not use key enumeration as proof that the submit payload is empty. Access `event.signature` explicitly inside the submit handler.

Treat signature content as sensitive, potentially large data. Do not persist it merely to prove that the event fired. A bounded diagnostic may record only the member name, runtime type, format classification, and character length, then discard the data URI. Production persistence, transport, authorization, retention, audit, and maximum-size rules require their own design and tests.

Submitting invoked the installed multipart PNG endpoint beneath `/data/perspective/signature-submitted/...`, returned HTTP 200 in the tested fixture, fired `onSignatureSubmitted`, and left the canvas drawn. It did not clear the pad. Clear reset the canvas to `clearColor`, fired `onSignatureCleared`, and did not submit an image. A blank Submit still produced a valid PNG data URI; do not equate a nonempty payload with a drawn signature.

Setting top-level `enabled` to false prevented pointer drawing and rendered both action buttons as native disabled submit buttons, even though their nested `enabled` members were true. A custom right-side action bar used:

```json
{
  "actionBar": {
    "position": "right",
    "clearButton": {"text": "RESET", "enabled": true, "primary": false},
    "submitButton": {"text": "OK", "enabled": true, "primary": false}
  },
  "pad": {
    "canvas": {
      "clearColor": "#0A0A21",
      "style": {"backgroundColor": "#0A0A21"}
    },
    "pen": {"color": "#FF9527", "width": 4}
  }
}
```

On the tested desktop geometry, `position: "bottom"` rendered a row below the canvas and `position: "right"` rendered a column beside it. Treat the installed CSS classes and exact pixels as build- and fixture-specific evidence, not a public DOM contract.

## Signature Pad runtime validation

For a new Signature Pad shape, validate at least:

1. Exact project readback of `enabled`, action-bar position and button members, canvas clear/style colors, pen color/width, and component-event names.
2. Original-resolution initial geometry proving the canvas and every action button are visible and in the intended row or column.
3. Real pointer drawing with pixel-backed before/after evidence; synthetic DOM events alone are insufficient.
4. Submit handler metadata proving explicit `event.signature` access, Jython runtime type, `data:image/png;base64,` classification, and bounded length without retaining the signature content.
5. The installed multipart request and response status, plus proof that Submit does not clear the canvas.
6. Clear event count/order and pixel-backed restoration to `clearColor`.
7. Blank Submit behavior, including a smaller but still valid PNG data URI in the tested fixed geometry.
8. Disabled pointer and button attempts that produce no drawing, event count, or upload.
9. Custom pen/canvas colors and right-action-bar geometry, including custom Submit/no-clear and Clear/reset behavior.
10. A simultaneous second session that remains blank and event-isolated throughout the first session's interactions.
11. Zero browser-console/page/request failures, exact project/protected/helper isolation, delayed cleanup to zero active test pages, and bounded official Gateway log inspection at every edge and after close. Save and classify every WARN-or-higher item; do not silently filter known environmental warnings or misattribute them to the component.

## Bidirectional draft bindings

Declare persistent view-custom properties with the exact source types before mounting the input components:

```json
{
  "custom": {
    "draftName": "Alpha",
    "draftSetpoint": 12.5
  },
  "propConfig": {
    "custom.draftName": {"persistent": true},
    "custom.draftSetpoint": {"persistent": true}
  }
}
```

Store `bidirectional: true` inside the property binding's `config` object. Bind separate read-only Labels to the draft properties so a browser test can distinguish the editor's temporary value from accepted property propagation.

This establishes the local bidirectional property-binding form. Use the separately tested direct tag-binding form below when the accepted value must persist outside the mounted view.

## Direct bidirectional tag bindings

For a caller-approved memory tag, put `bidirectional: true` inside the direct tag binding's `config` object. The tested String editor used:

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "config": {
          "fallbackDelay": 2.5,
          "mode": "direct",
          "tagPath": "[ApprovedProvider]Approved Folder/Name",
          "bidirectional": true
        },
        "type": "tag"
      }
    }
  },
  "props": {
    "deferUpdates": true,
    "rejectUpdatesWhileFocused": true
  },
  "type": "ia.input.text-field"
}
```

Use the same binding form on `props.value` for the tested direct-mode Numeric Entry Field. In the reproduced String/Float8 memory-tag case:

- typing while focused did not change the independent tag value or source timestamp;
- Enter committed a valid String, an empty String, or an in-range Float8 and changed only the corresponding tag timestamp;
- an out-of-range numeric draft painted the configured invalid style without changing the tag value or timestamp;
- Enter rejected that invalid draft, restored the prior accepted numeric value, and still did not write;
- independent read-only direct tag bindings repainted each accepted value; and
- the view contained zero component scripts.

Create and reset test tags through official tag import/export operations when available. Because configuration export does not prove live quality or timestamps, use an approved independent live-read surface when available. Require Good quality, exact runtime type, exact value, source-timestamp transitions, and zero write attempts by the observation helper. Do not treat mirror paint alone as write proof.

## Guarded local submit and reset

Keep submit validation explicit and synchronous. In the tested Button event, increment the attempt counter before validation, reject a blank trimmed String, reject non-numeric or out-of-range values, and copy only accepted drafts into separate committed properties:

```python
name = self.view.custom.draftName
setpoint = self.view.custom.draftSetpoint
self.view.custom.submitCount = self.view.custom.submitCount + 1
if not isinstance(name, basestring) or not name.strip():
	self.view.custom.status = "REJECTED: NAME_REQUIRED"
	return
if type(setpoint) not in (int, long, float) or setpoint < 0 or setpoint > 100:
	self.view.custom.status = "REJECTED: SETPOINT_RANGE"
	return
self.view.custom.committedName = name.strip()
self.view.custom.committedSetpoint = setpoint
self.view.custom.status = "ACCEPTED"
```

Use a separate reset action when the intended behavior is draft-only restoration:

```python
self.view.custom.draftName = "Alpha"
self.view.custom.draftSetpoint = 12.5
self.view.custom.resetCount = self.view.custom.resetCount + 1
self.view.custom.status = "RESET"
```

The tested reset restored both bound inputs and both draft markers while preserving the last accepted committed name and setpoint.

## Runtime validation

Require at least these distinct states:

1. Bound initial values replace stored component fallbacks.
2. Text typed while focused differs from the unchanged draft marker.
3. Enter commits the Text Field value into the draft.
4. Clicking the Numeric Entry Field enters editable focused mode.
5. An in-range numeric value commits into the draft.
6. Submit copies valid drafts into committed state and increments the attempt count.
7. An empty committed Text Field value is rejected without changing committed state.
8. An out-of-bounds numeric value paints the configured invalid style while the draft remains unchanged.
9. Enter rejects the out-of-bounds edit and restores the prior accepted numeric value.
10. Reset restores draft defaults without replacing committed state.

For every state, save a screenshot and DOM inspection; require positive in-viewport geometry, no document overflow, no unexpected quality overlay, zero browser/page errors, stable official session/page/view identity, zero reconnects, exact mounted-view topology, and a bounded clean Gateway WARN-or-higher window. For tag writeback, also capture independent value/type/quality/source-timestamp evidence at every state. Terminate only the exact matching test session through official Perspective OpenAPI when it remains present, poll its absence, and inspect shutdown logs. If the session is already absent, record zero matches rather than claiming a termination.

## Boundary

This evidence covers one Text Field with `deferUpdates: true`, one direct-mode Numeric Entry Field, date/time modes of Date Time Input, two inline Date Time Pickers with one expression-bounded to plus/minus seven calendar days, horizontal/disabled/vertical Sliders with persistent numeric property bindings and exact tested keyboard/pointer sequences, four One-Shot Buttons sharing one direct bidirectional Int4 memory tag with target values 0/1/2/3, enabled/disabled/custom Signature Pads with bottom/right action bars and bounded Clear/Submit metadata, one String and one numeric bidirectional property binding, one direct bidirectional String memory-tag binding, one direct bidirectional Float8 memory-tag binding, exact `0..100` numeric bounds, one invalid style, Enter-based commit/rejection, synchronous Button validation, and draft-only reset on Ignition 8.3.8 / Perspective 3.3.8.

It does not establish blur-only Text Field commit, `deferUpdates: false`, external updates while focused, paste/IME/mobile behavior, other Numeric Entry modes, negative/empty/NaN/infinity/scientific numeric input, inclusive numeric-boundary behavior, locale-dependent date/time formatting, manual date entry, Date Time Input day selection, time-field commit rules, meridiem changes, date/time bidirectional binding, timezone conversion, DST selection, min/max ranges crossing month/year boundaries, Date Time Picker navigation arrows, date/time component events, Slider tag writeback, Slider component events, ArrowLeft/ArrowDown/PageUp/PageDown behavior, arbitrary fractional steps, dynamic Slider min/max/step/enable/orientation changes, touch/mobile Slider input, Slider color/style precedence, external Slider updates while focused, One-Shot Button touch/mobile behavior, custom confirmation text, rapid/double activation, write timeout/failure/rejection, bad/stale quality, non-integer or non-memory backing values, same-target redundant writes from another writer, dynamic target/binding/enable changes, tag security, competing writers, network loss, alarming/history, Signature Pad touch/mobile/stylus/pressure behavior, keyboard drawing, undo, dynamic style/enable/action-bar changes, maximum signature size, slow/failed upload, authentication/authorization of the installed upload endpoint, image persistence, encryption, retention, audit, multiple rapid submits, navigation/reload persistence, reconnects, live resource revision, Designer behavior, or other builds. Test each independently before relying on it.
