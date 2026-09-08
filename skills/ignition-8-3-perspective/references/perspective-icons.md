# Perspective icon library through official API

Use this workflow only after confirming the target is Ignition 8.3.8 or reproducing it on the installed build. It covers Gateway icon-library metadata, SVG data-file authoring, and validated use from a Perspective Icon component. Treat public client asset URLs as a separate unproven surface.

## Contents

- [Discover the live contract and installed shape](#discover-the-live-contract-and-installed-shape)
- [Create complete metadata](#create-complete-metadata)
- [Upload or update the SVG](#upload-or-update-the-svg)
- [Modify metadata safely](#modify-metadata-safely)
- [Use the library from an Icon component](#use-the-library-from-an-icon-component)
- [Completion gates](#completion-gates)

## Discover the live contract and installed shape

Read the current OpenAPI document and confirm these operations still exist for `com.inductiveautomation.perspective/icons`:

```text
GET  /data/api/v1/resources/type/com.inductiveautomation.perspective/icons
GET  /data/api/v1/resources/names/com.inductiveautomation.perspective/icons
GET  /data/api/v1/resources/list/com.inductiveautomation.perspective/icons
GET  /data/api/v1/resources/find/com.inductiveautomation.perspective/icons/{name}
POST /data/api/v1/resources/com.inductiveautomation.perspective/icons
PUT  /data/api/v1/resources/com.inductiveautomation.perspective/icons
GET  /data/api/v1/resources/datafile/com.inductiveautomation.perspective/icons/{name}/{filename}
PUT  /data/api/v1/resources/datafile/com.inductiveautomation.perspective/icons/{name}/{filename}
```

Obtain the Gateway base URL, API credential, library name, collection, filename, icon identifiers, and SVG path data at runtime. Read a representative installed library before authoring because the stored shape can change between builds.

On the tested build, an icon file used this structure:

```xml
<svg xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .icon { display: none }
      .icon:target { display: inline }
    </style>
  </defs>
  <svg viewBox="0 0 16 16">
    <g class="icon" id="&lt;icon-id&gt;">
      <path d="&lt;path-data&gt;"></path>
    </g>
  </svg>
</svg>
```

Use a unique `id` for every inner icon group. Parse the finished XML before upload and compare its shape with a live installed library. API acceptance alone does not prove that a client can target or render the icons.

## Create complete metadata

Before mutation, read names/list and prove the requested name is absent. Send metadata create as a JSON array, even for one resource:

```json
[
  {
    "name": "<library-name>",
    "collection": "<collection>",
    "enabled": true,
    "description": "<description>",
    "config": {
      "svgFileName": "<library-file>.svg"
    }
  }
]
```

Always supply `config.svgFileName` and verify it through `find`. Although OpenAPI marks it required, the tested server accepted its omission and created metadata with an empty config. Treat that response as incomplete, not successful completion.

After create, call `find` with the collection query and capture the returned resource signature. Confirm names/list contain the target exactly once, then upload the SVG immediately. The metadata-without-SVG interval produced IconManager ERROR entries on the tested build.

## Upload or update the SVG

Write the configured filename with `Content-Type: image/svg+xml` and the exact current signature:

```text
PUT /data/api/v1/resources/datafile/com.inductiveautomation.perspective/icons/{name}/{filename}?collection={collection}&signature={signature}
```

Then:

1. call `find` again and require a new signature;
2. require the configured filename in the resource data-file list;
3. GET the data file and compare its exact bytes or cryptographic hash with the intended SVG;
4. parse the readback and recheck unique icon identifiers and the installed structural contract;
5. inspect a bounded relevant log window.

For another SVG revision, repeat the find-current-signature, signed PUT, fresh-signature, and exact-readback sequence.

## Modify metadata safely

Send metadata modification as a JSON array containing the resource name, collection, current signature, enabled state, description, and complete config. Preserve fields not intended to change. After success, require a new signature and verify the SVG bytes are unchanged.

On the tested build, stale signatures for both metadata and data-file writes returned HTTP 500 with a signature-mismatch problem rather than HTTP 409. They performed no write. Do not depend on a particular conflict status: after every non-2xx response, stop, fetch fresh metadata and SVG bytes, and reconcile before retrying.

## Use the library from an Icon component

Derive the surrounding view and container shape from a live installed Ignition 8.3 resource. For the Icon component itself, use this tested shape:

```json
{
  "props": {
    "color": "<CSS color>",
    "path": "<library-name>/<icon-id>"
  },
  "type": "ia.display.icon"
}
```

The `color` property is optional. Keep the library name and SVG group identifier exact and case-sensitive. Built-in libraries use the same path form, such as `material/<icon-id>`.

Author the view and route through the supported project-resource workflow, never through browser or Designer automation. After exact project readback, apply the caller-approved visual-validation workflow. Require:

- a painted screenshot containing the icon;
- one visible, nonzero, in-viewport `svg[data-component="ia.display.icon"]` element for each expected icon;
- an exact `data-icon` value equal to `<library-name>/<icon-id>`;
- an inner icon group whose `id` equals the requested identifier;
- path data matching the retained library entry when exact target proof is required;
- the expected computed fill when a color is supplied;
- zero browser console WARN/ERROR entries;
- official session evidence that the authored view is mounted.

On the tested build, the client expanded the selected icon group and path inline inside the component SVG. It did not retain an SVG `<use>` reference. Inspect the rendered structure instead of assuming one delivery mechanism.

## Completion gates

Do not report completion until all of these pass:

- the target appears exactly once in names and list;
- enabled, collection, description, and `svgFileName` match the request;
- `config.json` and the configured SVG filename are present;
- the SVG readback is byte-exact and parses against the installed structural contract;
- icon group identifiers are present and unique;
- every successful mutation advances the resource signature;
- the bounded post-final log window has no relevant WARN-or-higher entry;
- unrelated projects and agent APIs remain unchanged.

Gateway configuration readback alone does not establish component or client behavior. Claim target resolution or visible rendering only after the component, screenshot, geometry, console, and API-visible session gates pass. Do not infer a public asset URL from inline client resolution.
