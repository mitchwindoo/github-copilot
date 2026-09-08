# Perspective theme through official API

Use this workflow only after confirming the target is Ignition 8.3.8 or reproducing it on the installed build. It proves Gateway theme metadata and data-file authoring. It does not prove that a Perspective client selected, loaded, cascaded, or rendered the theme.

## Discover the live contract

Read the current OpenAPI document and confirm these resource operations still exist for `com.inductiveautomation.perspective/themes`:

```text
GET  /data/api/v1/resources/type/com.inductiveautomation.perspective/themes
GET  /data/api/v1/resources/names/com.inductiveautomation.perspective/themes
GET  /data/api/v1/resources/list/com.inductiveautomation.perspective/themes
GET  /data/api/v1/resources/find/com.inductiveautomation.perspective/themes/{name}
POST /data/api/v1/resources/com.inductiveautomation.perspective/themes
PUT  /data/api/v1/resources/com.inductiveautomation.perspective/themes
GET  /data/api/v1/resources/datafile/com.inductiveautomation.perspective/themes/{name}/{filename}
PUT  /data/api/v1/resources/datafile/com.inductiveautomation.perspective/themes/{name}/{filename}
```

Obtain the Gateway base URL, API credential, theme name, collection, and CSS at runtime. Do not embed any of them in the skill or reusable project resources.

## Create metadata

Before mutation, read names/list and prove the requested name is absent. Send metadata create as a JSON array, even for one resource:

```json
[
  {
    "name": "<theme-name>",
    "collection": "<collection>",
    "enabled": true,
    "description": "<description>",
    "config": {
      "entrypoint": "index.css",
      "isPrivate": false
    }
  }
]
```

After a successful response, call `find` with the collection query and capture the returned resource signature. Confirm names/list contain the target exactly once.

Metadata exists before its entrypoint data file is uploaded. On the tested build, this interval generated a ThemeManager warning that the theme was unusable. Upload the entrypoint immediately, minimize the interval, and require a clean bounded log window after finalization.

## Upload or update CSS

Write the entrypoint with `Content-Type: text/css` and the exact current signature:

```text
PUT /data/api/v1/resources/datafile/com.inductiveautomation.perspective/themes/{name}/index.css?collection={collection}&signature={signature}
```

Then:

1. call `find` again and require a new signature;
2. require `index.css` in the resource data-file list;
3. GET the data file and compare its exact bytes or a cryptographic hash with the intended CSS;
4. record the returned content type and inspect a bounded relevant log window.

For another CSS revision, repeat the same find-current-signature, signed PUT, fresh-signature, and exact-readback sequence.

## Modify metadata

Send metadata modification as a JSON array containing the resource name, collection, current signature, enabled state, description, and complete config. Preserve fields that are not intended to change. After success, require a new signature and exact find/list readback.

On the tested 8.3.8 build, stale signatures for both metadata and data-file writes returned HTTP 500 with a signature-mismatch problem rather than HTTP 409. They performed no write. Do not depend on a particular conflict status: after every non-2xx response, stop, fetch fresh metadata and data-file bytes, and reconcile before retrying.

## Completion gates

Do not report completion until all of these pass:

- the target appears exactly once in names and list;
- enabled, collection, description, entrypoint, and privacy fields match the request;
- the expected data files are present;
- the entrypoint readback is byte-exact;
- the final resource signature differs from the pre-mutation signature;
- the bounded post-final log window has no relevant WARN-or-higher entry;
- unrelated projects and agent APIs remain unchanged.

Gateway configuration readback does not establish client behavior. Require a separate documented API-visible Perspective client session and observable evidence before claiming theme selection, asset loading, CSS cascade, or visible rendering.
