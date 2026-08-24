# Fixed Vision Client Bridge Pattern

## Contents

- [Purpose and ownership](#purpose-and-ownership)
- [Required contract](#required-contract)
- [Addressing and validation](#addressing-and-validation)
- [Bounded EDT work](#bounded-edt-work)
- [Typed response and mailbox](#typed-response-and-mailbox)
- [Temporary configuration and restoration](#temporary-configuration-and-restoration)
- [Failure handling](#failure-handling)
- [Rejected designs](#rejected-designs)
- [Handoff to the external API workflow](#handoff-to-the-external-api-workflow)

## Purpose And Ownership

A fixed client bridge lets a Gateway-side runner request one Vision-only observation or action that cannot be performed safely in Gateway scope. The Jython skill owns the in-client handler implementation. The external `ignition-vision` workflow owns resource installation, client selection/launch, mailbox lifecycle, dispatch, screenshots, logs, and independent validation.

A bridge is a narrow capability, not a generic remote shell.

## Required Contract

Define these constants before implementation:

- exact project name and optional exact client ID;
- handler name and request kind/schema version;
- resource/window/component identity and expected concrete class;
- fixed operation and any fixed accessors/properties;
- dedicated response mailbox path and baseline type;
- request ID format and short expiration window;
- response schema and size caps;
- permitted UI mutation, tag write, navigation, database, historian, or project-update counts;
- restoration rules for mailbox and temporary component state.

The caller may supply correlation and bounded filter values only when the contract explicitly allows them. It may not select code, methods, expressions, arbitrary components, properties, templates, queries, or tag paths.

## Addressing And Validation

A handler should ignore messages that are not addressed to it and reject malformed addressed messages before side effects.

```jython
import time

EXPECTED_KIND = 'fixed-component-query'
EXPECTED_PROJECT = 'CustomerProject'
MAX_CLOCK_SKEW_MS = 60000

def validate_payload(payload):
    if not isinstance(payload, dict):
        return None
    if payload.get('kind') != EXPECTED_KIND:
        return None
    if payload.get('project') != EXPECTED_PROJECT:
        return None

    request_id = payload.get('requestId')
    expires_at = payload.get('expiresAtEpochMillis')
    if not isinstance(request_id, basestring) or not request_id or len(request_id) > 120:
        raise ValueError('Invalid requestId')
    if not isinstance(expires_at, (int, long)):
        raise ValueError('Invalid expiry')
    now = long(time.time() * 1000)
    if expires_at < now or expires_at > now + MAX_CLOCK_SKEW_MS:
        raise ValueError('Expired or excessive request lifetime')
    return {'requestId': request_id, 'expiresAtEpochMillis': expires_at}
```

Use fixed component lookup and class validation:

```jython
def resolve_component():
    window_path = 'Operations/Diagnostics'
    if window_path not in list(system.gui.getOpenedWindowNames()):
        raise ValueError('Required window is not open')
    window = system.gui.getWindow(window_path)
    component = window.rootContainer.getComponent('Content').getComponent('Target')
    class_name = component.getClass().getName()
    if class_name != 'com.inductiveautomation.factorypmi.application.components.PMILabel':
        raise ValueError('Unexpected component class: ' + class_name)
    return component
```

Do not discover arbitrary components by caller-provided path.

## Bounded EDT Work

Perform only the fixed UI read/action on the EDT:

```jython
from java.lang import Runnable
from javax.swing import SwingUtilities

class UiSnapshot(Runnable):
    def __init__(self, holder):
        self.holder = holder

    def run(self):
        component = resolve_component()
        self.holder['text'] = unicode(component.getText() or '')[:256]
        bounds = component.getBounds()
        self.holder['bounds'] = [bounds.x, bounds.y, bounds.width, bounds.height]

def capture_snapshot():
    holder = {}
    task = UiSnapshot(holder)
    if SwingUtilities.isEventDispatchThread():
        task.run()
    else:
        SwingUtilities.invokeAndWait(task)
    return holder
```

Do not query a database/historian, sleep, poll, serialize a large object, or scan the component tree without strict caps on the EDT.

## Typed Response And Mailbox

Return primitives, bounded strings, bounded lists, and small dictionaries. Include correlation and actual side-effect counts.

```jython
import json

RESPONSE_TAG = '[Client]Automation/FixedBridgeResponse'

def write_response(request_id, snapshot):
    response = {
        'schemaVersion': 1,
        'ok': True,
        'requestId': request_id,
        'kind': EXPECTED_KIND,
        'project': EXPECTED_PROJECT,
        'snapshot': snapshot,
        'sideEffects': {
            'componentMutations': 0,
            'tagWrites': 0,
            'databaseCalls': 0,
            'navigationCalls': 0
        }
    }
    qualities = system.tag.writeBlocking([RESPONSE_TAG], [json.dumps(response)])
    if len(qualities) != 1 or not qualities[0].isGood():
        raise ValueError('Response mailbox write failed')
```

The outer workflow must snapshot the mailbox before dispatch and restore it after every terminal path. The handler should not accept a caller-selected response path.

Treat the handler-to-mailbox pairing as part of the fixed capability identity. Dispatch through the exact handler and mailbox named by the action contract; another healthy diagnostic mailbox cannot stand in for it. Require the correlated typed response before interpreting the operation as executed.

## Temporary Configuration And Restoration

If one fixed operation requires temporary component settings:

1. Resolve and validate the exact component on the EDT.
2. Snapshot every allowlisted property.
3. Change only values that differ.
4. Re-read and verify the temporary state.
5. Perform one fixed operation.
6. Restore in `finally` on the EDT.
7. Re-read and verify the restored state.
8. Return success only after restoration verification.

Do not serialize temporary primitive setter signatures into the window merely to support the query. Keep temporary behavior inside the fixed handler.

## Failure Handling

Use a single bounded error envelope:

```jython
from java.lang import Throwable

def bounded_error(request_id, exc):
    text = unicode(exc or '')
    if len(text) > 300:
        text = text[:300] + '<truncated>'
    return {
        'schemaVersion': 1,
        'ok': False,
        'requestId': request_id,
        'kind': EXPECTED_KIND,
        'error': text,
        'sideEffects': {
            'componentMutations': 0,
            'tagWrites': 0,
            'databaseCalls': 0,
            'navigationCalls': 0
        }
    }
```

Catch `Throwable` and `Exception` only around the narrow operation/response boundary. Never return unrestricted stack traces, component objects, datasets, credentials, tokens, cookies, or arbitrary payload fragments.

## Rejected Designs

Reject handlers that accept or evaluate:

- Jython/Python source, expressions, imports, or module names;
- arbitrary methods, reflection targets, bean properties, components, or window paths;
- arbitrary tag paths/values, queries/SQL, files, URLs, commands, or navigation destinations;
- unrestricted dataset/log/object serialization;
- caller-selected mailboxes;
- unbounded waits, loops, retries, scans, or result sizes.

Do not treat `SENT` as operation success. Do not return success when component or mailbox restoration is uncertain.

## Handoff To The External API Workflow

Provide `ignition-vision` with:

- the handler name and exact Client Event Script resource scope;
- source SHA-256 and installed-target Jython compile result;
- exact payload and response schemas;
- exact component/resource identity and required structural preflight;
- mailbox path/type and restoration contract;
- confirmation token for the matching first-class action;
- session-selection requirements;
- side-effect budget and independent validation plan.

The external workflow must install through dry-run/state-guarded apply, start a fresh authenticated client, dispatch only through the matching fixed action, verify the typed correlated response, restore the mailbox, query focused logs, and validate state/pixels on their correct evidence planes.
