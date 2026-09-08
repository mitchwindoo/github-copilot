# Perspective Power Chart

Use this reference only after confirming Ignition 8.3.8 or reproducing the behavior on the installed build. It qualifies one exact installed empty component shape, one and three runtime-added historical pens, and one pen visibility hide/restore. Do not infer Power Chart serialization from Time Series Chart, XY Chart, Ignition 8.1, or documentation alone.

## Contents

- [Installed empty shape](#installed-empty-shape)
- [Add runtime historical pens](#add-runtime-historical-pens)
- [Hide and restore one pen](#hide-and-restore-one-pen)
- [Reload and session boundary](#reload-and-session-boundary)
- [Feedback and lifecycle guardrails](#feedback-and-lifecycle-guardrails)
- [Validation checklist](#validation-checklist)
- [Qualification boundary](#qualification-boundary)

## Installed empty shape

The tested installed component used:

```json
{
  "type": "ia.chart.powerchart",
  "props": {
    "config": {
      "visibility": {
        "showTagBrowser": true
      }
    },
    "interaction": {
      "chartZoomLevel": 1,
      "rangeZoomLevel": 1
    }
  }
}
```

It also used one expression binding on `props.config.tagBrowserStartPath`. The tested path grammar was:

```text
histprov:<history-provider>:/drv:<gateway-system-name>:<tag-provider>
```

The expression obtained the Gateway segment from `{[System]Gateway/SystemName}` and concatenated the remaining provider-specific text. Discover the exact history-provider and tag-provider names through authenticated reads; do not copy environment names from an example.

The empty component painted a tag browser, an eight-hour plot, and an instruction to add tags. No `props.pens` member was authored in this fixture.

## Add runtime historical pens

1. Require an active license or trial and a healthy history provider before opening the client.
2. Attach console-error, page-error, and request-failure listeners before navigation.
3. Capture the empty component, visible geometry, quality overlays, official Perspective topology, and a bounded Gateway WARN-or-higher log window.
4. Discover the rendered folder row. Click its descendant `.ia_treeComponent__expandIcon`; clicking the folder label itself was a no-op in the tested browser.
5. Assert that the row class changes from `ia_treeComponent__node--collapsed` to `ia_treeComponent__node--expanded` and that descendant tag leaves paint.
6. Discover tag labels from the rendered UI. The tested browser lowercased tag labels relative to authenticated tag-resource reads, so a case-sensitive locator based on the resource name failed.
7. Click one rendered tag leaf. Require the selected row paint and an enabled `Add Selected Tags` button.
8. Click `Add Selected Tags`, wait for history loading to settle, and require both a nonempty trace and a populated pen row. The tested row painted pen name, current value, minimum, maximum, average, axis, plot, and X Trace columns.
9. Save a screenshot and query the exact interaction's Gateway WARN-or-higher interval. A painted trace does not replace log inspection.

Adding the pen through the tag browser changed runtime state only in this fixture. It did not require a tag write or project import.

For the tested three-pen sequence, click the first rendered tag leaf and Ctrl-click the second and third leaves. Require all three selected-row states before clicking `Add Selected Tags`. Three pen rows and three distinct colored traces painted. Each visible series contributed one colored trace and one white companion path under the tested SVG filter.

Do not infer arbitrary multi-selection gestures or pen counts from this three-leaf Ctrl-selection.

## Hide and restore one pen

The tested pen table rendered one visibility control per pen:

```text
svg.pen-visibility-checkbox[data-pen-name="<rendered-pen-name>"]
```

The visible middle pen used `data-state="checked"`. Clicking the control changed it to `unchecked`, retained the pen row, removed that pen's colored trace and one white companion path, and reduced the strict trace-path count from six to four. Clicking it again restored `checked` and the exact six-path stroke-color multiset.

Assert control state, retained row, colored stroke, companion-path count, screenshot, and bounded Gateway logs together. Pen-row presence alone does not prove that a trace is visible.

## Reload and session boundary

The runtime-created pen and trace survived a page reload inside the same browser session. After the earlier session was fully retired, a genuinely fresh browser session opened the same authored view with no pen. An authenticated project export remained byte-equivalent to the post-authoring baseline.

Treat these as separate checks:

- same component immediately after add;
- same browser session after reload;
- fresh browser session after official cleanup;
- authored project resource before and after runtime interaction.

Do not infer project persistence from reload persistence.

## Feedback and lifecycle guardrails

Always inspect visible connection state by geometry and computed visibility. Raw page text can contain an offscreen `No Connection to Gateway` string while the visible Power Chart is connected.

After closing a test context, poll the official Perspective session inventory until the exact test session disappears, then inspect a post-close Gateway WARN-or-higher window. In one rejected run, immediately closing a populated context and opening another context painted a correct fresh page but emitted `Perspective.Routes: Error fetching resource.` A later standalone fresh-session run after cleanup was clean. Preserve and reject any run with an unexplained WARN-or-higher entry; do not hide it because the page rendered.

Abruptly closing a three-pen page with live history fetches also emitted the same route ERROR during teardown in one rejected run. Later strict runs qualified exactly one test session by project, browser scope, active page, and mounted test resource; terminated only its returned identifier through the official session DELETE operation; required `terminated: 1`; proved immediate absence; and then closed the browser with clean termination and post-close logs. Use this controlled cleanup only for an unambiguous caller-created test session and preserve shutdown side effects. Never terminate all sessions for a project.

On a shared Gateway, bracket the final strict runtime run with fresh authenticated project and protected-project exports. An older baseline can expose concurrent metadata changes without proving the current test caused them. Preserve and classify that evidence, then require exact before/after equality across the narrow bracket.

## Validation checklist

1. Confirm the exact component type, props, binding target, and installed build.
2. Verify the resolved history-browser start path without exposing credentials or private infrastructure names.
3. Capture the empty state before interacting.
4. Assert every settled state transition instead of treating a dispatched click as success.
5. Require painted traces and populated pen rows after adding one or the exact tested three tags.
6. For visibility, require checkbox state, retained row, color signature, companion-path count, and restore equality.
7. Test same-session reload and a fresh session only after the earlier session is gone.
8. Re-export the project and prove the runtime interaction did not mutate authored resources; use a fresh before/after bracket on a shared Gateway.
9. Save screenshots, geometry, browser diagnostics, quality state, official topology, every bounded Gateway WARN-or-higher interval, controlled cleanup evidence, and final no-drift readback.

## Qualification boundary

This reference qualifies only the exact installed empty shape, one expression-bound tag-browser start path, one folder expansion, one- and three-tag runtime addition, Ctrl selection of exactly three rendered leaves, three distinct pen rows/traces, one middle-pen visibility hide/restore, same-session reload retention, clean fresh-session reset, exact-session controlled cleanup, and bracketed no project-resource drift on the tested build. It does not qualify pen removal, edit dialogs, axis or plot edits, X Trace, range controls, settings, export, pan/zoom semantics, arbitrary pen counts, non-Ctrl multi-selection, keyboard/touch accessibility, reconnect behavior, Designer behavior, non-SQL history providers, other component configurations, or other builds.
