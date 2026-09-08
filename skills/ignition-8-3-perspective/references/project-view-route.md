# Static view and page route

Use this workflow only after confirming the target is Ignition 8.3.8 or reproducing it on the installed build.

## Contents

- [Project resource layout](#project-resource-layout)
- [Page route](#page-route)
- [API-only import workflow](#api-only-import-workflow)
- [Mounted browser adoption of a view revision](#mounted-browser-adoption-of-a-view-revision)

## Project resource layout

Store a view at:

```text
com.inductiveautomation.perspective/views/<folder>/<view-name>/resource.json
com.inductiveautomation.perspective/views/<folder>/<view-name>/view.json
```

Use this tested `resource.json` shape:

```json
{
  "scope": "G",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": ["view.json"],
  "attributes": {}
}
```

Use a flex-container root with a Label child for a minimal static view:

```json
{
  "custom": {},
  "params": {},
  "props": {"defaultSize": {"height": 320, "width": 640}},
  "root": {
    "children": [
      {
        "meta": {"name": "StaticLabel"},
        "position": {"grow": 1},
        "props": {"text": "Example marker"},
        "type": "ia.display.label"
      }
    ],
    "meta": {"name": "root"},
    "props": {
      "alignItems": "stretch",
      "direction": "column",
      "justify": "center"
    },
    "type": "ia.container.flex"
  }
}
```

## Page route

Merge the route into `com.inductiveautomation.perspective/page-config/config.json`. Preserve every existing page and dock entry.

```json
{
  "pages": {
    "/example": {
      "title": "Example",
      "viewPath": "Examples/Example View"
    }
  },
  "sharedDocks": {
    "cornerPriority": "top-bottom"
  }
}
```

Store its companion `resource.json` with `scope: G`, `version: 1`, `files: ["config.json"]`, and the same restricted/overridable fields shown above.

## API-only import workflow

1. Export the current project through `GET /data/api/v1/projects/export/{name}`.
2. Use that exact export as the merge base. Preserve every entry and modify only declared target paths.
3. Immediately before import, export again and compare every entry and content hash with the merge base. Abort on any drift.
4. Package the complete project with `project.json` at the ZIP root.
5. Import through `POST /data/api/v1/projects/import/{name}?overwrite=true` using `Content-Type: application/zip`.
6. Treat HTTP 200 as acknowledgement only. Wait for the expected project API generation, export again, and verify the complete entry set plus target content.
7. Check the route with an HTTP GET and use the documented Perspective session APIs for activation evidence when a session exists.

Do not claim visual rendering from the initial Perspective HTML shell; client-rendered component content is not present in that response.

## Mounted browser adoption of a view revision

On the tested Ignition 8.3 build, an exact whole-project import that changed only one mounted view's `view.json` caused the already open browser page to adopt both the revised static marker and revised direct String tag-binding path without explicit navigation, reload, or client interaction. A second exact import restored the original resource and the mounted page returned to the original marker, path, and Good value.

Use this only as a bounded verification pattern:

1. Build both complete project revisions from the same stable export and prove their entry maps differ only in the intended `view.json`.
2. Independently read every bound tag before the test and require Good quality plus an explicit no-write result.
3. Mount the first revision naturally and record its exact URL, painted marker/path/value, screenshot, geometry, console baseline, session ID, page ID, and mounted-view identity/counts.
4. Import the second complete project through the official project-import endpoint. Do not navigate, reload, or interact with the client during the observation window.
5. Export the project and require exact second-revision readback before attributing any client change to that revision.
6. Capture the first available settled client sample and report it as an upper observation bound after import completion, not as propagation latency.
7. Restore the first complete revision while the page remains mounted, repeat the exact readback and client checks, and leave the project in the declared retained state.
8. Require final project, tag, route, health, scan-lock, log, session, and browser cleanup checks.

The tested browser preserved the same official session ID, page ID, route, view resource path, mount path, component count, and binding count across both imports. Those observations alone do not prove whether lifecycle scripts reran. A separate externally instrumented test, documented in [perspective-startup-events.md](perspective-startup-events.md), proved that the tested root view's `events.system.onStartup` reran after each exact mounted-view revision. Do not generalize that result to other lifecycle events or child views.

Each tested live revision also emitted this Perspective browser warning:

```text
store.Resources: Project resourceList was not an array!
```

Treat that exact warning as part of the observed boundary, not as a clean-console result and not as permission to ignore other console entries. Re-discover it after upgrades. This test does not establish behavior for page-configuration changes, child dependencies, project scripts, styles/themes, multiple clients, Designer scope, partial imports, redundant Gateways, reconnects, failed imports, other component/binding types, or precise propagation timing.
