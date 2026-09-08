# Perspective asynchronous page-message handoff

Use this contract only for the exact tested Ignition 8.3.8 / Perspective 3.3.8 pattern. Keep live Perspective-owned objects out of the detached worker. Capture immutable primitive values before launch, perform off-thread work, and explicitly target the originating page when sending the result.

## Tested sender pattern

In the Button event, set immediate visible state synchronously and capture the session and page identifiers as strings before launching the worker:

```python
from java.lang import Thread

self.view.custom.phase = "LAUNCHED"
started_millis = long(system.date.now().getTime())
session_id = str(self.session.props.id)
page_id = str(self.page.props.pageId)

def worker(started=started_millis, target_session=session_id, target_page=page_id):
	from java.lang import Thread
	Thread.sleep(1500L)
	completed = long(system.date.now().getTime())
	system.perspective.sendMessage(
		"async-complete",
		{
			"startedMillis": started,
			"completedMillis": completed,
			"workerThreadName": str(Thread.currentThread().getName())
		},
		scope="page",
		sessionId=target_session,
		pageId=target_page
	)

handle = system.util.invokeAsynchronous(worker, [], {}, "async-message-worker")
```

The worker's default arguments and payload contain only numbers and strings. Do not reference `self`, `event`, a component, `self.view`, `self.page`, `self.session`, or a Perspective property-tree value inside the detached worker.

## Required explicit target

The tested worker did not inherit the Button event's attached Perspective context. Calling page-scoped `system.perspective.sendMessage` without identifiers failed with:

`No perspective session attached to this thread.`

For the tested Gateway-scope call, pass both `sessionId` and `pageId`. Capturing and passing only implicit scope is not sufficient.

## Tested receiver

Store a handler under the receiving component's `scripts.messageHandlers` with `pageScope: true`, the exact matching `messageType`, and both other scope flags false. Read primitive payload fields with `payload.get(...)`, then perform the Perspective property writes in the handler.

Two fresh sessions each produced one immediate launch script and one later handler script. The handler received exactly once after 1505/1501 ms, the result remained stable for five seconds, and there were no reconnects, browser/page errors, or strict-window Gateway warnings. The worker reported `script-invoke-async`; the handler reported a distinct `perspective-worker-*` thread.

The distinct handler thread means this is a message-based ownership handoff, not proof of marshaling onto a browser/UI thread. Do not describe it as a universal UI-thread scheduler.

## Designer lesson

An earlier opening attempt produced `Unable to deserialize resource` with `ObjectClosedException`, without a matching Gateway log. The corrected explicit-target resource passed exact export parsing/readback and browser runtime validation, and the user subsequently confirmed that it opened successfully in Designer. Preserve this sequence as compatibility evidence, but do not claim the async script caused the earlier Designer error.

## Validation gates

1. Compile the Button and handler scripts with the target Gateway's Jython version.
2. Export and verify the exact event, handler, scope flags, message type, payload keys, and primitive identifier capture.
3. Prove the implicit-target negative independently; do not silently rely on inherited Perspective context.
4. Run the explicit-target flow in at least two fresh sessions and require initial, launched, completed, and delayed-stable states.
5. Require exactly one receipt, one sender plus one handler script, distinct worker/handler observations, no reconnect, and clean browser/page diagnostics.
6. Correlate the mounted view with official session reads, bound the Gateway-log window, re-export the project, and prove target/protected isolation.
7. Open the corrected retained resource in Designer before promoting the shape as Designer-compatible.

## Boundary

This contract does not qualify session/view scope, cross-page delivery, embedded receivers, multiple receivers or workers, ordering, cancellation, exception propagation, retries, navigation/close/reload/reconnect while work is pending, security rules, mutable payload objects, tags, queries, redundancy, other Perspective APIs, or other builds. Test each separately.
