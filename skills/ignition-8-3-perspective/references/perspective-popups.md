# Perspective popups

Use this reference only for the exact popup behavior reproduced on Ignition 8.3. The page and popup views must already be authored through an approved API workflow; `system.perspective.openPopup`, `closePopup`, and `togglePopup` are client script functions, not OpenAPI endpoints.

## Contents

- [Popup view inputs](#popup-view-inputs)
- [Open a modal popup](#open-a-modal-popup)
- [Return a result and close](#return-a-result-and-close)
- [Identifier controls](#identifier-controls)
- [Enabled interaction variants](#enabled-interaction-variants)
- [Empty-ID close](#empty-id-close)
- [Dismissible modal](#dismissible-modal)
- [Toggle open and close](#toggle-open-and-close)
- [Multiple popup focus and stacking](#multiple-popup-focus-and-stacking)
- [Runtime gate](#runtime-gate)

## Popup view inputs

The tested child view declared two persistent input parameters:

```json
{
  "params": {
    "message": "DEFAULT_MESSAGE",
    "popupId": "DEFAULT_POPUP_ID"
  },
  "propConfig": {
    "params.message": {
      "paramDirection": "input",
      "persistent": true
    },
    "params.popupId": {
      "paramDirection": "input",
      "persistent": true
    }
  }
}
```

Do not infer other parameter types or directions from this result.

## Open a modal popup

The tested Button `onActionPerformed` script used one stable ID and named optional arguments:

```python
	popup_id = "<stable-popup-id>"
	system.perspective.openPopup(
		popup_id,
		"<approved-popup-view-path>",
		params={"message": "<message>", "popupId": popup_id},
		title="<popup-title>",
		position={"left": 360, "top": 150, "width": 560, "height": 360},
		showCloseIcon=False,
		draggable=False,
		resizable=False,
		modal=True,
		overlayDismiss=False,
		viewportBound=True
	)
```

On the tested 1280 by 720 viewport, the popup painted at exactly left 360, top 150, width 560, and height 360. The modal overlay covered the viewport, an outside click did not dismiss the popup, no close-icon Button appeared, and the client marked the popup controls non-draggable. Treat geometry and CSS observations as viewport- and version-specific evidence, not a general layout guarantee.

## Return a result and close

The tested child sent a page-scoped dictionary payload before closing itself by the same ID:

```python
	payload = {
		"result": "ACCEPTED",
		"message": str(self.view.params.message),
		"popupId": str(self.view.params.popupId)
	}
	system.perspective.sendMessage(
		"<message-type>",
		payload=payload,
		scope="page"
	)
	system.perspective.closePopup(str(self.view.params.popupId))
```

The parent used the exact component message-handler serialization in [perspective-component-messages.md](perspective-component-messages.md), with `pageScope: true`. The visible parent result and handler count updated, the child mount disappeared, and the same session/page remained active. This proves the tested synchronous send-then-close sequence only; it does not establish delivery guarantees for other scopes, multiple receivers, navigation, asynchronous work, or reversed ordering.

## Identifier controls

Two focused controls passed:

- `system.perspective.closePopup("<unknown-id>")` returned without an exception and left the existing popup mounted.
- Two synchronous `openPopup` calls using the same ID both returned, but the first popup title and input remained painted. The second call did not replace or update it and produced no browser or Gateway runtime warning.

Use unique popup IDs. Treat the same-ID result as an observed first-wins boundary for the exact tested sequence, not as a supported update mechanism.

## Enabled interaction variants

The tested non-modal popup enabled all three visible interaction affordances:

```python
	system.perspective.openPopup(
		"<stable-popup-id>",
		"<approved-popup-view-path>",
		params={"message": "INTERACTIVE", "popupId": "<stable-popup-id>"},
		title="<popup-title>",
		position={"left": 260, "top": 100, "width": 500, "height": 300},
		showCloseIcon=True,
		draggable=True,
		resizable=True,
		modal=False,
		overlayDismiss=False,
		viewportBound=True
	)
```

At 1280 by 720, a guarded parent Button remained clickable while the child stayed mounted, proving non-modal background interaction for that layout. A title-bar drag moved the exact popup rectangle from `(260, 100, 500, 300)` to `(380, 170, 500, 300)`. A southeast-handle drag then changed it to `(380, 170, 610, 375)`. Eight directional resize zones and one rendered close icon were present. Clicking the close icon unmounted the child without executing a component script.

Treat these as exact pointer-interaction observations. Do not infer other handles, directions, limits, viewport sizes, pointer types, keyboard behavior, or drag/resize persistence.

## Empty-ID close

The child-side call below closed the most recently focused popup and removed its mounted child:

```python
	system.perspective.closePopup("")
```

With one popup, this closed that instance. With distinct A and B popups, B initially painted above A; clicking A's exposed title bar raised A above B, and the same empty-ID call then closed A while B remained. Treat this as the exact observed focus history, not an arbitrary focus-order guarantee.

## Dismissible modal

The tested modal variant used `modal=True`, `overlayDismiss=True`, no close icon, no drag, and no resize. One outside click closed the popup and removed the child mount without executing another component script. This is the complement of the earlier `overlayDismiss=False` result; do not infer other overlay events or input devices.

## Toggle open and close

No separate official popup-update function was documented. The tested Button used the documented toggle function:

```python
	system.perspective.togglePopup(
		"<stable-popup-id>",
		"<approved-popup-view-path>",
		params={"message": "TOGGLE", "popupId": "<stable-popup-id>"},
		title="<popup-title>",
		position={"left": 390, "top": 120, "width": 500, "height": 300},
		showCloseIcon=True,
		draggable=False,
		resizable=False,
		modal=False,
		overlayDismiss=False,
		viewportBound=True
	)
```

The first call opened and mounted the popup. A second call with the same ID closed it and removed the child mount. Use this only as the tested open/close toggle; it does not prove parameter, title, geometry, or view updates on an already open popup.

## Multiple popup focus and stacking

Two `openPopup` calls with distinct IDs mounted two instances of the same child resource with independent String inputs. Official session reads reported the parent plus two child mounts. At their overlap point, the second-opened popup was topmost. Clicking the first popup's exposed title bar swapped their relative computed z-order without moving either rectangle or executing a component script.

After the focus change, `closePopup("")` removed the first popup and retained the second. Reopening the first made it topmost; `closePopup("<second-id>")` then removed the nonfocused second popup and retained the focused first. Exact-ID close is therefore independent of the tested focus order.

A third modal popup then mounted above both non-modal popups. A normal parent Button click timed out behind the modal overlay and its visible counter remained unchanged. Closing the modal from its own child removed only that child; both underlying popups remained mounted and the previously top non-modal popup was topmost again. Subsequent exact-ID calls removed the two underlying popups independently.

The tested relative z-order changed by one client layer per focus/open transition, but numeric z-index values are implementation details and must not be hard-coded. Do not infer more than three simultaneous popup children, arbitrary focus histories, nested modals, keyboard/Escape focus, rapid concurrent calls, or cross-page behavior.

## Runtime gate

For each popup state, require:

1. A painted screenshot and exact popup/body/control geometry with no clipping or document overflow.
2. The requested modal/non-modal, overlay-dismiss, title, inputs, close-icon, drag, resize, and toggle observations.
3. One stable browser session and page; official mounted-view reads should change parent-only to parent-plus-popup and back to parent-only.
4. Exact parent result and handler-count changes after the send-and-close action.
5. Zero unexpected browser console/page errors and bounded Gateway WARN-or-higher entries.
6. Exact project export stability, clear project scan lock, route HTTP 200, and natural browser-page cleanup.

Project import activation may temporarily make a client route unavailable even after exact export readback. Poll route readiness with a bounded timeout and save any server diagnostic; do not treat a fixed sleep or the import response alone as runtime proof.
