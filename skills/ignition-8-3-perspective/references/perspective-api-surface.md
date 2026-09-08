# Perspective API surface

Use this reference to choose an API before authoring or validating Perspective resources. Discover the live contract first; do not copy an endpoint or action name from an older Gateway without checking the current response.

## Contents

- [Availability and precedence](#availability-and-precedence)
- [Perspective builder API index](#perspective-builder-api-index)
- [Official OpenAPI operations used by the workflow](#official-openapi-operations-used-by-the-workflow)
- [Optional llmImport POST actions](#optional-llmimport-post-actions)
- [Response and evidence rules](#response-and-evidence-rules)

## Availability and precedence

Ignition 8.3 provides its official OpenAPI document at:

```text
GET /openapi.json
```

Treat that document as the authority for the current Gateway and installed modules. The OpenAPI document is platform-provided, but access may still require an authenticated API token; the tested Gateway returned 403 to an unauthenticated request. Individual module operations appear only when their module is installed and may also require sufficient token permissions.

`llmImport` is different. It is an optional, project-scoped Web Dev resource, not an Ignition platform endpoint. Before using any action below, require a successful health read:

```text
GET /system/webdev/<approved-project>/llmImport
```

Require `api: "llmImport"`, record `version`, and confirm the requested action is present in `availableActions`. If the resource is missing, returns an incompatible shape, or does not advertise the action, do not call its POST action. Use official OpenAPI operations instead. Add a new `llmImport` action only when the official API lacks the capability and the caller authorizes that extension; validate authorization, input bounds, dry-run behavior, readback, negative cases, versioning, and regressions before documenting it.

### If `llmImport` is not installed

Without a compatible `llmImport` Web Dev resource in the approved project, the route `POST /system/webdev/<approved-project>/llmImport` does not provide any usable actions. Do not call it, do not assume that an action exists, and do not substitute a similarly named URL.

Ignition's platform OpenAPI discovery document remains available at `/openapi.json`. Continue with the official operations it advertises for the installed modules and the caller's authenticated permissions. In particular, arbitrary Perspective views, page routes, bindings, and component scripts can still be authored through exact whole-project export/import; `llmImport` is not a prerequisite for that workflow.

Use this order:

1. Official OpenAPI operation.
2. An installed and advertised `llmImport` action whose tested boundary fits the request.
3. A newly implemented, narrowly bounded `llmImport` action only after proving the first two do not support the operation.

## Perspective builder API index

Use this index as the entry point; use the detailed sections below for boundaries and readback requirements.

| Need | Official Ignition API | Optional `llmImport` fallback or supplement |
|---|---|---|
| Discover the callable contract | `GET /openapi.json` | `GET /system/webdev/<approved-project>/llmImport` discovers the optional action contract. |
| Author arbitrary views, page routes, component JSON, bindings, and component scripts in an existing project | `GET /data/api/v1/projects/export/{name}`, then `POST /data/api/v1/projects/import/{name}?overwrite=true` | Fixed folder actions can create only their documented fixture shapes; they are not general view builders. |
| Coordinate direct folder-resource changes | Project scan-lock and project-scan GET/POST operations | The fixed view, route, and project-script folder actions use this lane internally. |
| Create or update binding tags and UDTs | `GET /data/api/v1/tags/export`, `POST /data/api/v1/tags/import` | General tag read/browse/write/history actions add live runtime evidence; `grouped-udt-file-v1` is a narrowly bounded adjacent helper. |
| Inspect a rendered Perspective runtime | Official session, page, and mounted-view GET operations | The fixed session-navigation action is available only when advertised and its allowlist matches. |
| Validate diagnostics | `GET /data/api/v1/logs` plus the routed client URL | Fixed runtime probes apply only to the exact advertised contract. |
| Manage Perspective themes, icons, and fonts | Official resource metadata and data-file APIs | No `llmImport` action is needed for the tested theme/icon workflows. |

There is one optional `llmImport` POST route, not one URL per action. The JSON `action` member dispatches the requested operation. Therefore, saying that an action is available requires both a compatible health response and the action name in `availableActions`.

## Official OpenAPI operations used by the workflow

The tables in this section are the complete set of official OpenAPI operations currently qualified as useful to this skill's tested Perspective authoring and validation workflows. They are not a copy of every operation in the Gateway document. Rediscover `/openapi.json` on each target because modules, versions, and permissions determine the live paths.

“Qualified” means the operation has passed live request, control, and readback gates. Keep potentially useful but unqualified operations visible in the appropriate boundary note instead of treating discovery as proof. For example, the tested OpenAPI advertised `POST /data/perspective/api/v1/themes/copy-base-themes`; theme-copy behavior remains unqualified, so do not use it until a focused test establishes its request, collision, and readback contract.

### Gateway and project discovery

| Method and path | Use |
|---|---|
| `GET /openapi.json` | Discover the live official contract. |
| `GET /data/api/v1/gateway-info` | Verify the API credential and record Gateway identity/version information. |
| `GET /data/api/v1/projects/list` | Inventory project summaries. |
| `GET /data/api/v1/projects/names` | Inventory project names. |
| `GET /data/api/v1/projects/find/{name}` | Read the approved project's configuration before mutation. |
| `GET /data/api/v1/projects/export/{name}` | Obtain the authoritative project archive for discovery, preconditions, candidate construction, and exact entry-level readback. |
| `POST /data/api/v1/projects/import/{name}?overwrite=true` | Import a bounded project archive into the already approved project. Use `Content-Type: application/zip`, require a fresh-base comparison immediately before import, normalize every ZIP entry name to `/`, reject any entry containing `\`, require the response to identify the exact approved project, and export again for exact readback. |

Do not use project create, delete, rename, copy, parent-change, or general modify operations merely to build a page in an existing approved project. The live OpenAPI may advertise `POST /data/api/v1/projects`, `DELETE` or `PUT /data/api/v1/projects/{name}`, `POST /data/api/v1/projects/copy`, and `POST /data/api/v1/projects/rename/{name}`; these are separate high-impact project-lifecycle operations and require explicit caller authorization and their own tests.

Construct the import URI without ambiguous shell interpolation. In PowerShell, use a braced variable or format operator, for example `"${baseUrl}/data/api/v1/projects/import/${project}?overwrite=true"` or `'{0}/data/api/v1/projects/import/{1}?overwrite=true' -f $baseUrl, $project`. An unbraced variable adjacent to `?overwrite` can be parsed as a different variable name and send the archive to an unintended project-name segment. Before and after import, inventory project names and require the response's changed project name to equal the approved target. On any mismatch, stop, preserve evidence, and do not automatically delete, rename, or modify the unintended project.

### Project scan coordination

| Method and path | Use |
|---|---|
| `GET /data/api/v1/scan-lock/projects` | Confirm whether a project scan lock exists. |
| `POST /data/api/v1/scan-lock/projects` | Acquire the official project scan lock according to the live request schema when a tested folder-resource workflow requires it. |
| `GET /data/api/v1/scan/projects` | Read project scan status. |
| `POST /data/api/v1/scan/projects` | Release an acquired project scan lock and request project scanning after a tested folder-resource mutation. |

Whole-project import normally performs activation without a separate manual folder scan. Do not mix a scan-lock workflow with project import unless the focused test requires and verifies it.

### Gateway configuration scan coordination

These operations are useful when an approved, bounded workflow changes Gateway configuration files rather than project resources. The tested `grouped-udt-file-v1` helper is one such case. They are not needed for official tag import/export or whole-project import.

| Method and path | Use |
|---|---|
| `GET /data/api/v1/scan-lock/config` | Confirm whether a Gateway configuration scan lock exists. |
| `POST /data/api/v1/scan-lock/config` | Acquire the official configuration scan lock according to the live request schema before a tested configuration-folder mutation. |
| `GET /data/api/v1/scan/config` | Read Gateway configuration scan status. |
| `POST /data/api/v1/scan/config` | Release an acquired configuration scan lock and request configuration scanning after a tested mutation. |

Do not acquire configuration or project scan locks speculatively. Pair each lock with the exact tested mutation family, retain the response, and verify the corresponding scan completes.

Treat canonical ZIP separators as a destructive-safety precondition. On the tested Windows/Gateway combination, an archive built with backslash entry names was accepted by transport but only `project.json` survived readback. Inspect the candidate entry map before import, reject backslashes, require the exact expected entry count, and stop immediately on any readback difference.

### Tags used by Perspective bindings

| Method and path | Use |
|---|---|
| `GET /data/api/v1/tags/export` | Export configured tags/UDTs for exact configuration readback. This does not provide live value/quality/timestamp reads. |
| `POST /data/api/v1/tags/import` | Add or update caller-approved tags/UDTs using the collision policy and body defined by the live OpenAPI. Save the raw response. On the tested 8.3.8 build, one folder plus eight memory tags returned `{"successCount":9,"failureCount":0,"failures":[]}`; an earlier OpenAPI example suggested an array, so validate the live response shape instead of assuming the example. |

Use a separate tested runtime-value API for binding evidence. Do not infer live value or quality from tag configuration export.

### Perspective runtime introspection

| Method and path | Use |
|---|---|
| `GET /data/perspective/api/v1/sessions/` | List Perspective sessions and identify the intended project/scope. |
| `GET /data/perspective/api/v1/session/{sessionId}` | Read one session's metrics, including script/expression execution correlation. |
| `GET /data/perspective/api/v1/session/{sessionId}/pages` | List pages for the selected session. |
| `GET /data/perspective/api/v1/session/{sessionId}/page/{pageId}/views` | Correlate exact mounted view resource paths and component/binding instance counts. |

Treat session and page identifiers as opaque. The official API also advertises session termination, but this skill has not established it as the normal browser-cleanup mechanism; do not terminate sessions without explicit authorization.

### Logs and routed-client checks

| Method and path | Use |
|---|---|
| `GET /data/api/v1/logs` | Query a bounded WARN-or-higher window. `startTime` and `endTime` are epoch milliseconds on the tested build. |
| `GET /data/perspective/client/{project}/{route}` | Confirm that an API-authored page route resolves over HTTP. This client URL is not itself an OpenAPI operation and HTTP 200 does not prove the intended view rendered. |

Logger-level mutation, monitoring-session creation, and logger-context modification are advertised by the live OpenAPI but are not required for ordinary Perspective page validation. Do not change logging configuration merely to obtain a clean evidence window.

### Perspective assets

The live OpenAPI advertises resource-type, names, list, find, create, modify, delete, rename, and data-file operations for these resource families:

```text
com.inductiveautomation.perspective/themes
com.inductiveautomation.perspective/icons
com.inductiveautomation.perspective/fonts
```

Expand `{kind}` below to each exact family name above and confirm the resulting operation in the current `/openapi.json`; `{kind}` is compact notation in this reference, not a literal OpenAPI path parameter.

| Method and path | Use |
|---|---|
| `GET /data/api/v1/resources/type/{kind}` | Describe the resource type and its live schema. |
| `GET /data/api/v1/resources/names/{kind}` | List resource names. |
| `GET /data/api/v1/resources/list/{kind}` | List resource summaries. |
| `GET /data/api/v1/resources/find/{kind}/{name}` | Read one resource configuration and signature. |
| `POST /data/api/v1/resources/{kind}` | Create one resource from the live request schema. |
| `PUT /data/api/v1/resources/{kind}` | Modify one resource using its required signature/preconditions. |
| `DELETE /data/api/v1/resources/{kind}/{name}/{signature}` | Delete one signed resource. Treat as destructive and require explicit authorization. |
| `POST /data/api/v1/resources/delete/{kind}` | Delete multiple resources. Treat as destructive and require explicit authorization. |
| `POST /data/api/v1/resources/rename/{kind}/{name}` | Rename one resource. Require explicit authorization and exact readback. |
| `GET /data/api/v1/resources/datafile/{kind}/{name}/{filename}` | Read one resource data file. |
| `PUT /data/api/v1/resources/datafile/{kind}/{name}/{filename}` | Create or replace one data file. |
| `DELETE /data/api/v1/resources/datafile/{kind}/{name}/{filename}` | Delete one data file. Treat as destructive and require explicit authorization. |
| `PUT /data/api/v1/resources/datafile/{kind}/{name}` | Update multiple data files using the live multipart request schema. |

Use [perspective-theme.md](perspective-theme.md) and [perspective-icons.md](perspective-icons.md) for the exact theme/icon operations that have passed signed-concurrency, data-file, and readback tests. Font authoring, theme copying, delete/rename operations, multiple-file updates, and other unlisted resource operations remain discovery-only even though they appear in OpenAPI; test them before use.

## Optional `llmImport` POST actions

This entire section is conditional. If the approved project does not contain a compatible `llmImport` Web Dev resource, none of these POST actions is callable. Do not synthesize their behavior or treat their paths as part of Ignition OpenAPI. The official `/openapi.json` discovery document and the official operations listed above remain the workflow surface, subject to installed modules, authentication, and permissions.

All actions below share one HTTP route:

```text
POST /system/webdev/<approved-project>/llmImport
Content-Type: application/json
```

The JSON body selects the operation with `action`. These are not separate platform endpoints. A deployed version may expose more or fewer actions; the health response is authoritative.

Without a compatible `llmImport` resource in the approved project, this POST route and every action below are unavailable. That does not remove Ignition's platform OpenAPI document or official endpoints. Continue with the official operations exposed by `/openapi.json`, and use official project export/import when arbitrary Perspective project-resource JSON must be authored.

### General caller-scoped tag actions

These are the preferred optional runtime helpers for Perspective tag-binding evidence.

| Action | Request fields | Tested purpose and boundary |
|---|---|---|
| `tag-read-v1` | `action`, `allowedTagPathPrefixes`, `paths` | Read bounded qualified paths and return value, quality, `isGood`, timestamp, type, and `writesAttempted:false`. The tested 0.58.3 contract serializes bounded runtime arrays and nested Document structures as JSON. |
| `tag-read-complex-v1` | `action`, `allowedTagPathPrefixes`, `paths`; optional bounded `maxRows`, `maxColumns`, `maxElements`, `maxDocumentBytes` | Independently read bounded Dataset, array, and nested Document values with type, quality, timestamp, truncation, and shape metadata. Require advertisement and the health capability before relying on it. |
| `tag-browse-v1` | `action`, `allowedTagPathPrefixes`, `basePath`; optional `recursive`, `maxResults`, `tagType`, `typeId` | Browse a bounded provider/folder and return normalized metadata. |
| `tag-write-v1` | `action`, `allowedTagPathPrefixes`, `writes`; optional `dryRun`, `apply` | Guarded writes with before/write/after verification. Dry-run defaults true; a real write requires the verified API token plus `dryRun:false` and `apply:true`. |
| `tag-document-cas-v1` | `action`, `allowedTagPathPrefixes`, one `path`, object-root `value`; optional bootstrap dry-run, while apply additionally requires `expectedTimestampMillis`, `expectedSemanticHash`, `dryRun:false`, `apply:true` | Guarded whole-Document object write with configuration check, server-issued optimistic preconditions, one blocking write, and after-read semantic verification. It is optimistic, not atomic; root-array runtime writes are not qualified. See `perspective-document-tag-writes.md`. |
| `tag-query-history-v1` | `action`, `allowedTagPathPrefixes`, `paths`, `startTimeMillis`, `endTimeMillis`; optional `includeBounds`, `maxRows` | Bounded raw-history query with epoch-millisecond window, row cap, normalized columns/rows, and no writes. |

The installed tested contract caps prefixes, paths, results, history paths/rows, and history window. Read those limits from the health response instead of hard-coding them. For array evidence, additionally require `tagApi.readArraySerialization: "json-array-v1"` and read `tagApi.maxArrayItems`. For Document evidence, require `tagApi.readDocumentSerialization: "json-structure-v1"` and read `tagApi.maxObjectMembers`; use `complexTagReadApi` and `tag-read-complex-v1` when the ordinary serializer's depth cap is insufficient. If the required capability is absent, nested Document runtime evidence is unavailable from that helper. The tested serializers preserve scalar behavior, return an array kind for a live `StringArray` and a top-level Document array, recursively serialize bounded array/object members, and report truncation. A null `StringArray` value remains JSON null; do not coerce it to `[]`. `allowedTagPathPrefixes` limits accidental scope; it is not authorization. Protect the API token and Web Dev resource separately.

For `tag-write-v1`, do not treat HTTP status alone as acceptance. One tested out-of-prefix apply returned HTTP 200 with `ok:false`, `accepted:false`, and `writesAttempted:false`; require the structured action fields plus an independent no-drift read. The tested successful scalar sequence required a dry-run with no value/timestamp change, an apply with `writesAttempted:true` and `allVerified:true`, two-session repaint, then dry-run plus verified apply to restore the original value.

Minimal read body:

```json
{
  "action": "tag-read-v1",
  "allowedTagPathPrefixes": ["[<provider>]<approved-folder>"],
  "paths": ["[<provider>]<approved-folder>/<tag>"]
}
```

The official tag export operation remains the authority for configured tag type and stored configuration. It does not replace an independent live value/quality/source-timestamp read. If `llmImport` is absent or does not advertise `tag-read-v1` plus the serialization capability required by the tested value type, do not claim that runtime evidence from this helper.

### Fixed Perspective regression actions

These actions are useful only when their fixed fixture matches the approved test environment. They are not general-purpose page builders.

| Action | Request fields | Boundary |
|---|---|---|
| `perspective-tag-read-v1` | `action` only | Reads the installed fixed Perspective tag fixture; accepts no caller path. Prefer `tag-read-v1` for a caller-scoped path. |
| `perspective-click-counter-v1` | `action` only | Runs the fixed click-counter helper contract with no external side effects. |
| `perspective-boolean-tag-write-v1` | `action`, Boolean `value`; optional `dryRun`, `apply` | Writes only the installed fixed Boolean fixture. A real write requires `dryRun:false` and `apply:true`. |
| `perspective-session-navigate-v1` | `action`, `page`, `sessionId`, `pageId`; optional Boolean `dryRun`, Boolean `apply` | Live-tested dry-run and apply for one current UUID session/page and installed fixed allowlist. Dry-run caused no navigation or observed state/timestamp drift; `dryRun:false` plus `apply:true` dispatched navigation; a non-Boolean `apply` was rejected without navigation. Prefer a painted client click for normal validation and see `perspective-page-navigation.md`. |

The complete tested Perspective-specific fixed action set is the four names in this table plus the four project-folder names below. If health omits even one requested name, that action is unavailable; do not substitute a similarly named action.

### Fixed project-folder actions

The installed folder actions internally use official project scan-lock and scan operations, exact SHA-256 preconditions, and fixed ownership checks. Their project, namespace, allowed shape, or script module may be fixed by the installed implementation.

| Action | Request fields | Boundary |
|---|---|---|
| `perspective-static-view-folder-v1` | `action`, `operation`, `viewName`, `labelText`; optional `expectedViewSha256`, `dryRun`, `apply` | Creates/updates only the installed fixed one-Label view shape beneath its fixed namespace. Update requires the exact current view hash. |
| `perspective-page-route-folder-v1` | `action`, `operation`, `route`, `title`, `viewPath`, `expectedConfigSha256`; optional `dryRun`, `apply` | Creates/updates one route only within the installed namespace/route constraints and only when the view exists. |
| `perspective-project-script-folder-v1` | `action`, `operation`, `revision`; optional `expectedCodeSha256`, `dryRun`, `apply` | Creates/updates only the installed fixed Project Library module/revisions. It does not accept arbitrary code. |
| `perspective-project-script-t11-invoke-v1` | `action`, `message`, `count` | Invokes and verifies only the installed fixed Project Library helper. No write. |

For the three folder mutations, dry-run defaults true. A real mutation requires `dryRun:false` and `apply:true`; an update also requires the appropriate exact SHA-256 precondition. Require `writeAttempted`, mutation readback, scan status 200, and an official project export afterward.

Use official project export/import for arbitrary Perspective view JSON. Do not force a requested view into the fixed static-view action merely because that action exists.

### Adjacent optional actions

An installed `llmImport` may also advertise the following tested action when a Perspective test needs UDT-backed tags:

| Action | Request fields | Boundary |
|---|---|---|
| `grouped-udt-file-v1` | `action`, `operation`, `provider`, `groupPath`, `allowedGroupPathPrefixes`; create/replace also use `content` or `contentText`; replace requires `expectedSha256`; mutation uses `dryRun` and `apply` | Inspects, creates, or compare-and-swap replaces one bounded grouped UDT-definition file. It does not scan configuration itself, does not delete, defaults to dry-run, requires a verified API token for mutation, and requires the caller to hold the official configuration scan lock and request the official configuration scan. Prefer official tag import/export unless a tested grouped-file operation is specifically required. |

The health response is authoritative for `allowedOperations`, size/count/prefix caps, compare-and-swap requirements, and test fixtures. Do not infer the UDT content schema from this action; obtain and validate it through the UDT workflow before connecting a Perspective binding to the resulting tags.

### Alarm actions for Perspective alarm views

An installed contract may advertise these optional actions when a Perspective page needs live alarm evidence or an operator-action test:

| Action | Boundary |
|---|---|
| `alarm-query-status-v1` | Bounded active-alarm query using caller-supplied qualified path/source prefixes and a result cap. |
| `alarm-query-shelved-v1` | Bounded shelved-alarm query under the installed alarm API limits. |
| `alarm-acknowledge-v1` | Guarded acknowledgement for bounded event IDs; mutation defaults to dry-run and requires the verified token plus explicit apply. |
| `alarm-shelve-v1` | Guarded bounded-duration shelve; mutation defaults to dry-run and requires the verified token plus explicit apply. |
| `alarm-unshelve-v1` | Guarded unshelve; mutation defaults to dry-run and requires the verified token plus explicit apply. |

Read `alarmApi.actions`, prefix/source/event/result limits, maximum shelve duration, write-token requirement, and dry-run default from health. These actions support alarm-backed page tests; they do not author a Perspective resource. Do not infer exact request members from the action name—use the installed tested contract and preserve raw request/response evidence.

### Runtime contract probes

The same POST dispatcher may advertise fixed, no-arbitrary-code probes such as `runtime-profile-v2`, `scope-capability-contract-v1`, `message-payload-contract-v1`, `logging-diagnostic-contract-v1`, `exception-boundaries-v1`, `date-time-contract-v1`, `system-config-read-v1`, and the `project-library-*-contract-v1` family. They are useful only when a focused Perspective scripting question exactly matches the fixed probe. They are not page-authoring endpoints and do not accept caller-supplied scripts. Require advertisement by health, consult the test-specific contract, and never infer a request body from the action name.

Other advertised Python/Jython/runtime probes are outside ordinary Perspective page construction. Do not copy the entire action list into a request: choose only a health-advertised action with a documented, tested boundary.

### Perspective-relevant `llmImport` action inventory

The following is the complete action-name inventory currently documented as useful or adjacent to building and validating Perspective pages. It is an action inventory for the single optional POST route, not a set of official OpenAPI endpoints.

| Family | Action names |
|---|---|
| General live tag evidence and guarded writes | `tag-read-v1`, `tag-read-complex-v1`, `tag-browse-v1`, `tag-write-v1`, `tag-document-cas-v1`, `tag-query-history-v1` |
| Fixed Perspective fixtures | `perspective-tag-read-v1`, `perspective-click-counter-v1`, `perspective-boolean-tag-write-v1`, `perspective-session-navigate-v1` |
| Fixed project-folder fixtures | `perspective-static-view-folder-v1`, `perspective-page-route-folder-v1`, `perspective-project-script-folder-v1`, `perspective-project-script-t11-invoke-v1` |
| UDT-backed test support | `grouped-udt-file-v1` |
| Alarm-backed test support | `alarm-query-status-v1`, `alarm-query-shelved-v1`, `alarm-acknowledge-v1`, `alarm-shelve-v1`, `alarm-unshelve-v1` |
| Focused runtime probes | `runtime-profile-v2`, `scope-capability-contract-v1`, `message-payload-contract-v1`, `date-time-contract-v1`, `logging-diagnostic-contract-v1`, `exception-boundaries-v1`, `system-config-read-v1`, `project-library-state-v1`, `project-library-import-contract-v1`, `project-library-reference-contract-v1`, `project-library-member-contract-v1`, `project-library-signature-contract-v1`, `project-library-return-contract-v1`, `project-library-callback-contract-v1` |

Do not treat actions outside this inventory as Perspective-building primitives merely because health advertises them. Low-level Python, byte/text, dependency, socket, HTTP-client, Unicode, and runtime guardrail probes belong to their own focused runtime research unless a page test explicitly depends on that boundary.

## Response and evidence rules

- Save the raw response before interpreting it.
- Treat HTTP success as transport acceptance only. Require the action-specific `accepted`, `ok` or `passed`, write-attempt flag, and exact readback.
- For tokenless or invalid input negatives, require an explicit rejection and exact zero drift.
- Never place credentials, session identifiers, private project names, or machine paths in a reusable skill or generated Perspective resource.
- If `llmImport` is unavailable, omit every `llmImport` call; official OpenAPI discovery, project export/import, scans, logs, tag import/export, asset APIs, and Perspective session reads remain available according to the live platform/module contract.
