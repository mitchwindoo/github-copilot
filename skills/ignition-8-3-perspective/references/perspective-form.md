# Perspective Form

Use this shape only after inspecting the installed Form descriptor and palette template on the target Ignition 8.3 build. The Form widget union is large; clone the installed widget template and change only proven members instead of inventing a minimized schema.

## Contents

- [Resource shape](#resource-shape)
- [Tested widget overrides](#tested-widget-overrides)
- [File upload widget](#file-upload-widget)
- [Actions and events](#actions-and-events)
- [Validation behavior](#validation-behavior)
- [Submit and Cancel lifecycle](#submit-and-cancel-lifecycle)
- [Submission handler resource](#submission-handler-resource)
- [Submission response lifecycle](#submission-response-lifecycle)
- [Runtime validation](#runtime-validation)
- [Boundary](#boundary)

## Resource shape

Use component type `ia.input.form`. The tested layout placed rows beneath one column:

```json
{
  "type": "ia.input.form",
  "meta": {"name": "NativeForm"},
  "props": {
    "name": "approved-form-name",
    "disabled": false,
    "readOnly": false,
    "columns": {
      "align": "stretch",
      "items": [{"rows": {"items": []}}]
    },
    "data": {
      "operator": "",
      "target": 50,
      "confirm": false
    },
    "validation": {},
    "actions": {}
  }
}
```

Treat this as an outline, not a complete widget schema. On Perspective 3.3.8, each row and widget was cloned from the installed palette template. The cloned widget retained the descriptor's variant branches and common label, info, style, visibility, enablement, read-only, layout, and tab-index members. Only its `id`, `type`, relevant variant, label, and info values were changed.

The widget `id` becomes the key in `props.data`, `onChange.event.key`, and action-event dynamic members. Keep IDs unique and validate all three surfaces.

## Tested widget overrides

The tested heading used a cloned widget with `id: "section"`, `type: "none"`, `label.text` as the heading, and caption text in `info.text`.

The tested text override was:

```json
{
  "id": "operator",
  "type": "text",
  "text": {
    "placeholder": "Enter at least 3 characters",
    "validation": {
      "constraints": {
        "required": {"enabled": true},
        "minLength": {"enabled": true, "value": 3}
      }
    }
  }
}
```

The tested number override was:

```json
{
  "id": "target",
  "type": "number",
  "number": {
    "placeholder": "0 to 100",
    "validation": {
      "constraints": {
        "required": {"enabled": true},
        "min": {"enabled": true, "value": 0},
        "max": {"enabled": true, "value": 100},
        "step": {"enabled": true, "value": 5}
      }
    }
  }
}
```

The tested Boolean checkbox override was:

```json
{
  "id": "confirm",
  "type": "checkbox",
  "checkbox": {
    "type": "boolean",
    "options": [{
      "text": "I reviewed the values",
      "value": "",
      "triState": false
    }],
    "validation": {
      "constraints": {
        "required": {"enabled": true}
      }
    }
  }
}
```

Merge these overrides into the cloned installed widget. Do not discard unshown descriptor members.

## File upload widget

The tested file widget was cloned from the installed Form palette widget and changed with this override:

```json
{
  "id": "attachments",
  "type": "file-upload",
  "file-upload": {
    "validation": {
      "constraints": {
        "required": {"enabled": true},
        "fileSizeLimit": {"value": 1},
        "maxUploads": {"enabled": true, "value": 2},
        "supportedFileTypes": {"enabled": true, "value": ["txt"]}
      }
    }
  }
}
```

On Perspective 3.3.8 this rendered a hidden native file input with `accept=".txt"` and `multiple`, but without the native `required` attribute. Form-managed validation still disabled Submit when empty. `maxUploads:2` was a maximum, not an exact-count requirement: one accepted file satisfied the native Form constraint and enabled Submit after the other required field committed. Enforce an exact file count in the submission handler when the application requires it.

An unsupported file remained as a painted error row with an extension message and fired Form `onChange` with zero accepted files. A valid file could be added while that rejected row remained; removing the rejected row cleared that validation error. A third valid file similarly remained as an error row, preserved the two accepted files, and disabled Submit until removed.

The visible list painted newest-first while the component event, submission event, and Gateway handler preserved accepted order. Do not infer payload order from row order.

For a file-widget change, `onChange.event.files` exposed the accepted `UploadedFile` objects. The tested synchronous members were `name`, `size`, `contentType`, `getString()`, and `getBytes()`. A change to a non-file widget did not expose `event.files`; gate file inspection on `event.key` instead of wrapping every change in one broad fallback that overwrites prior diagnostics:

```python
self.view.custom.lastChangeKey = unicode(event.key)
if unicode(event.key) == "attachments":
	items = list(event.files)
	self.view.custom.fileNames = "|".join([unicode(item.name) for item in items])
```

With `fireSubmissionEvent:true`, the tested `onSubmitActionPerformed` exposed file metadata objects under `event.data.get("attachments", [])` and the corresponding `UploadedFile` objects under `event.files.get("attachments", [])`. The Gateway handler received the same grouping in its `data` and `files` arguments:

```python
def handleSubmission(session, name, data, files, formContext, sessionContext, retry):
    uploads = [] if files is None else list(files.get("attachments", []))
    metadata = list(data.get("attachments", []))
    names = [unicode(item.name) for item in uploads]
    contents = [unicode(item.getString()) for item in uploads]
    byte_lengths = [len(item.getBytes()) for item in uploads]
    if len(uploads) != 2:
        return {
            "success": False,
            "title": "Upload rejected",
            "message": "Choose exactly two valid files.",
            "fieldErrors": {
                "attachments": {
                    "title": "Two files required",
                    "message": "Choose exactly two valid files."
                }
            }
        }
    return {
        "success": True,
        "title": "Upload accepted",
        "message": "Both files were read.",
        "custom": {
            "names": "|".join(names),
            "byteLengths": "|".join([unicode(value) for value in byte_lengths]),
            "metadataCount": len(metadata)
        }
    }
```

Read file contents synchronously inside the component event or Gateway handler. Asynchronous or retained-object access after those callbacks return was not tested.

## Actions and events

The tested action configuration used:

```json
{
  "actions": {
    "disabled": false,
    "fixed": false,
    "layout": "row",
    "align": "center",
    "justify": "end",
    "submit": {
      "disabled": false,
      "fireComponentEvent": true,
      "fireSubmissionEvent": false,
      "includeDisabledFieldValues": true,
      "includeHiddenFieldValues": true,
      "autoDisable": true,
      "resetOn": "success",
      "awaitResponse": false
    },
    "cancel": {
      "disabled": false,
      "fireComponentEvent": true,
      "reset": true
    }
  }
}
```

Store component actions beneath `events.component` using the standard Perspective script-action wrapper:

```json
{
  "events": {
    "component": {
      "onChange": {"type": "script", "scope": "G", "config": {"script": "\t..."}},
      "onSubmitActionPerformed": {"type": "script", "scope": "G", "config": {"script": "\t..."}},
      "onCancelActionPerformed": {"type": "script", "scope": "G", "config": {"script": "\t..."}}
    }
  }
}
```

When a local validation file wraps code in `def runAction(self, event):`, remove only the signature before serialization. Preserve the body's leading indentation. Importing the full wrapper or removing the required body indentation both failed Gateway compilation on the tested build. Always exercise each action and inspect Gateway logs; standalone compilation of the wrapper does not validate the serialized body extraction.

## Validation behavior

Treat Form validation as the authority for `autoDisable`. In the tested minimum-length state, a two-character text value painted the Form's invalid class and length message and kept Submit disabled even though the native input reported `valid:true`, `tooShort:false`, and the native form reported `checkValidity():true`.

The required Boolean checkbox similarly rendered a native checkbox with `required:false` and native-valid state. The Form still painted its required message and disabled Submit while unchecked. Do not use native constraint validity alone to judge these Form-managed constraints.

The tested out-of-range stepped number exposed native `rangeOverflow:true` and `stepMismatch:true`; the Form painted the maximum-value message and kept Submit disabled.

## Submit and Cancel lifecycle

After each completed tested field edit, `onChange` exposed the widget ID as `event.key` and its value as `event.value`. Invalid text and numeric drafts also produced the tested change event. Submit and Cancel reset did not produce an additional `onChange` in the reproduced sequence.

With a valid Form, `onSubmitActionPerformed` exposed the same values through both `self.props.data.<widgetId>` and `event.<widgetId>`. With `fireSubmissionEvent:false`, `resetOn: "success"` had no submission response to act on; the component Submit event ran and the values remained painted.

With Cancel `reset:true`, the Form cleared its data before `onCancelActionPerformed`. Direct access to `self.props.data.<widgetId>` failed because the members were absent, while `event.<widgetId>` retained the pre-reset values. Guard all post-reset `self.props.data` access and use the event payload when the pre-reset values are required. The tested reset cleared the text and number; it did not restore the initial numeric value from `props.data` and did not invoke `onChange`.

## Submission handler resource

On Perspective 3.3.8, a tested Gateway Form Submission handler used this project-resource folder:

```text
com.inductiveautomation.perspective/form-submission-handler/<handler-name>/
  resource.json
  handleSubmission.py
```

The tested `resource.json` shape was:

```json
{
  "scope": "G",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": ["handleSubmission.py"],
  "attributes": {"enabled": true}
}
```

The script entry point was:

```python
def handleSubmission(session, name, data, files, formContext, sessionContext, retry):
    files_count = 0 if files is None else len(files)
    return {
        "success": True,
        "title": "Accepted",
        "message": "The submission was accepted.",
        "custom": {"filesCount": files_count}
    }
```

Set Form Submit `fireSubmissionEvent:true` and `submissionHandler` to the resource folder name. The installed response reader recognized `success`, `title`, `message`, `fieldErrors`, and `custom`.

A Form with no file widget passed `files` as `None`, not an empty dictionary. Guard it before `len`, iteration, or mapping access. In the tested build, an unhandled `len(None)` exception produced a Gateway warning but the client followed a default-success path, fired `onSuccess`, and applied the configured success reset. Always catch expected failures and return an explicit error response; do not rely on a thrown handler exception becoming a visible error.

The tested field-error response used the widget ID as its key:

```python
return {
    "success": False,
    "title": "Rejected",
    "message": "Correct the highlighted field.",
    "fieldErrors": {
        "operator": {
            "title": "Rejected value",
            "message": "Enter an accepted value."
        }
    },
    "custom": {"branch": "ERROR"}
}
```

## Submission response lifecycle

For the tested 900 ms Gateway handler, `awaitResponse:true` plus `autoDisable:true` left the Submit button enabled during both in-flight submissions. The Form added `ia_form--submitted`, but that class is paint evidence, not duplicate-submission prevention. Add and separately test an application-level guard when duplicate submissions matter.

An explicit `success:false` response retained the Form values, painted response title/message and the keyed field error, and invoked component `onError`. Editing the rejected field did not clear the server field error or prior response; both remained through the next in-flight submission until the next response arrived.

In the multipart test, the `onError` event exposed the returned title and message, but attempted access to the handler's returned `event.custom` members fell into the guarded missing-data path. Do not assume custom payload symmetry between `onSuccess` and `onError`; validate the exact response branch and guard optional members.

An explicit `success:true` response invoked component `onSuccess` before the configured `resetOn:"success"` reset. The handler could still read the submitted value from `self.props.data` during `onSuccess`. Afterward, the tested text, number, and Boolean fields painted empty, empty, and false. The reset did not restore the initial numeric value and did not invoke `onChange`.

For the tested multipart success, `onSuccess` received the custom metadata/content summary while both uploaded files were still present in `self.props.data`; the subsequent success reset cleared the text field and file rows without a reset-generated `onChange`.

Response text may exist in the DOM while lying outside the fixed Form box. Size the Form for validation and response rows, then verify original-resolution screenshots plus response-node rectangles against the native Form rectangle. DOM text presence alone is insufficient visual evidence.

## Runtime validation

Require at least these states in fresh sessions:

1. Initial data paint and required-state Submit disablement.
2. Too-short text with Form message and disabled Submit.
3. Valid text with required checkbox still blocking Submit.
4. Out-of-range/step-mismatched number with exact message.
5. Valid number with the checkbox still blocking Submit.
6. Checked confirmation enabling Submit.
7. Submit event with matching data-object and dynamic event members and the expected reset behavior.
8. New text and numeric values after Submit.
9. Unchecked confirmation with required message and disabled Submit.
10. Cancel with cleared paint, absent post-reset data members, preserved pre-reset event members, and no reset-generated change event.

For a submission-handler test, additionally require error-ready, error-in-flight, error-settled, edited-with-persistent-feedback, success-in-flight, success-settled, and delayed-stable states. Save the response title/message/field-error geometry, `onSuccess`/`onError` traces, submitted versus post-reset data, Submit disabled state, Form class, and one bounded Gateway log window at every edge. Run tolerant discovery before two fresh strict confirmations.

For a file-upload test, additionally require unsupported-extension, one-valid-file, handler-enforced count error, two-valid-file, maximum-plus-one rejection, restored-two-file, success/reset, and delayed-stable states. Save accepted-event order separately from visible row order, and verify metadata plus synchronous content/byte reads in the component event, submit event, and handler.

For every state, save a screenshot, Form/input/button geometry, Form validation messages and classes, native validity as diagnostic evidence, exact official session/page/view topology, script/reconnect metrics, browser diagnostics, and a bounded Gateway WARN-or-higher window. Query logs after Submit and Cancel even when the screen appears correct. Terminate only the exact matching browser session and inspect the final delayed log window.

## Boundary

This evidence covers one column with a heading plus tested text, number, Boolean checkbox, and file-upload widgets; initial data; required, minimum-length, numeric minimum/maximum/step, file-size, maximum-count, and extension constraints; component Submit and Cancel; one Gateway Form Submission handler; explicit success/error/field-error/custom responses; both `files is None` and one keyed multipart file group; synchronous uploaded-file metadata/string/byte access; one 900 ms and one 700 ms awaited response; success reset; and `onChange`, `onSubmitActionPerformed`, `onCancelActionPerformed`, `onSuccess`, and `onError` on Ignition 8.3.8 / Perspective 3.3.8.

It does not establish other widget types, multiple columns, responsive layouts, email/URL/pattern/maximum-length validation, multi-checkbox values, large files, server upload limits, executable/binary files, non-UTF-8 encodings, persistence destinations, asynchronous file-object access, multiple file widgets, disabled or hidden field exclusion, retries/offline queues, timeouts, exception behavior beyond the exact `len(None)` negative, multiple handlers, duplicate-click prevention, other response shapes/reset modes/delays, keyboard/touch-only upload, accessibility behavior, navigation/reload persistence, reconnects, Designer behavior, or other builds. Test each separately.
