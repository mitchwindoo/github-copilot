# Guarded Document tag writes for Perspective observers

Use this reference only when the approved project contains a compatible `llmImport` Web Dev resource that advertises `tag-document-cas-v1`. This is an optional project-scoped action, not an Ignition OpenAPI operation. If it is absent, omit it; official OpenAPI remains available for project and tag-configuration authoring.

The workflow below was reproduced twice on Ignition 8.3.8 with Perspective 3.3.8 and a compatible `llmImport` 0.61.0 contract.

## Contents

- [Qualified shape](#qualified-shape)
- [Discover the live contract](#discover-the-live-contract)
- [Two-step write protocol](#two-step-write-protocol)
- [Required no-write controls](#required-no-write-controls)
- [Two-client sequential contention](#two-client-sequential-contention)
- [Atomicity and safety boundary](#atomicity-and-safety-boundary)
- [Root-array boundary](#root-array-boundary)
- [Runtime proof](#runtime-proof)
- [Boundaries](#boundaries)

## Qualified shape

The tested target was one Document memory tag whose root was an object. Its `items` member held the array consumed by a generic Tree:

```json
{
  "items": [
    {
      "label": "Area A",
      "expanded": true,
      "data": {"revision": 1},
      "items": []
    }
  ],
  "metadata": {"revision": 1}
}
```

Bind the Tree read-only to the nested member:

```json
"props.items": {
  "binding": {
    "type": "tag",
    "config": {
      "mode": "direct",
      "tagPath": "[<provider>]<approved-folder>/<document-tag>['items']",
      "fallbackDelay": 2.5
    }
  }
}
```

Do not add `bidirectional:true`. The explicit API owns whole-Document mutation; the Perspective page is an observer.

## Discover the live contract

First read:

```text
GET /system/webdev/<approved-project>/llmImport
```

Require all of the following before using the action:

- compatible API version;
- `tag-document-cas-v1` in `availableActions`;
- `documentTagWriteApi.action: "tag-document-cas-v1"`;
- `documentTagWriteApi.documentRoot: "object"`;
- `writeRequiresVerifiedApiToken: true`;
- `writeDefaultsToDryRun: true`;
- `precondition: "timestamp-and-sha256"`;
- an `atomicity` statement that identifies the operation as optimistic, not atomic.

Read all current limits from `documentTagWriteApi`; do not hard-code its prefix, byte, depth, member, element, node, or text caps.

## Two-step write protocol

All requests use the single optional dispatch route:

```text
POST /system/webdev/<approved-project>/llmImport
Content-Type: application/json
X-Ignition-API-Token: <runtime credential>
```

Bootstrap with a no-precondition dry run:

```json
{
  "action": "tag-document-cas-v1",
  "allowedTagPathPrefixes": ["[<provider>]<approved-folder>"],
  "path": "[<provider>]<approved-folder>/<document-tag>",
  "value": {"items": [], "metadata": {"revision": 2}},
  "dryRun": true,
  "apply": false
}
```

Require `accepted:true`, `ok:true`, `code:"dry_run_ok"`, `writesAttempted:false`, `externalSideEffects:"none"`, `preconditionsMatched:null`, a 64-character `beforeSemanticHash`, and `beforeTimestampMillis`.

Treat the returned semantic hash as an opaque server-issued token. Do not recreate it with a different JSON serializer: object ordering and runtime-number/string encoding can differ across languages even when parsed values are equal.

Apply with the exact bootstrap tokens:

```json
{
  "action": "tag-document-cas-v1",
  "allowedTagPathPrefixes": ["[<provider>]<approved-folder>"],
  "path": "[<provider>]<approved-folder>/<document-tag>",
  "expectedTimestampMillis": 0,
  "expectedSemanticHash": "<exact bootstrap token>",
  "value": {"items": [], "metadata": {"revision": 2}},
  "dryRun": false,
  "apply": true
}
```

Replace the timestamp placeholder with the exact bootstrap value. Require:

- `accepted:true`, `authorized:true`, and `ok:true`;
- `code:"write_completed"`;
- `writesAttempted:true` and `allVerified:true`;
- `configuredDataType:"Document"`;
- Good write and after-read quality;
- `afterSemanticHash` equal to `requestedSemanticHash`;
- a later after timestamp for a semantic change;
- independent `tag-read-complex-v1` readback of the complete untruncated object.

For an already-identical requested object, the tested apply returned `code:"already_current"`, `ok:true`, `allVerified:true`, and `writesAttempted:false`. In the tested contract, this response did not include after-timestamp fields. Prove no timestamp change with independent complete reads immediately before and after the request.

## Required no-write controls

Prove each rejection independently and verify the exact value and source timestamp remained unchanged:

| Control | Expected code |
|---|---|
| stale timestamp | `stale_timestamp` |
| current timestamp with stale semantic token | `stale_semantic_hash` |
| path outside the caller-supplied prefix | `path_outside_allowed_prefixes` |
| scalar root | `document_root_required` |
| array root | `document_object_root_required` |
| oversized/deep/over-count structure | the matching bounded-validation code |
| apply without both preconditions | `preconditions_required` |
| missing or rejected API token | the matching authorization code |

Every rejection must report `writesAttempted:false`.

## Two-client sequential contention

The stale-precondition behavior was reproduced twice with two independent API clients and two concurrent read-only Perspective sessions:

1. Bootstrap client A's revision-2 object and client B's different revision-3 object before either writes. Require identical `beforeTimestampMillis` and `beforeSemanticHash` values.
2. Apply client A with its exact pair and require one verified write.
3. Apply client B with its original pair. Require `code:"stale_timestamp"`, `writesAttempted:false`, and independent before/after proof that client A's value and source timestamp remain exact.
4. Bootstrap client B again, require tokens for client A's committed revision, then apply client B successfully.
5. Replay client A's original tokens and require another stale no-write rejection with independent value/timestamp preservation.
6. Submit the current object with current tokens and prove `already_current` using independent before/after reads.

At every edge, require both observer sessions to show only the accepted revision, with stable session/page identity, screenshots, deep tag readback, exact project exports, and bounded Gateway logs.

This establishes sequential stale-writer rejection. It does not force two requests into the comparison-to-write gap and does not prove atomic compare-and-swap behavior.

## Atomicity and safety boundary

The action performs an optimistic timestamp/hash comparison immediately before one `system.tag.writeBlocking` call. It is not a storage-level atomic compare-and-swap primitive; another writer can race between the comparison and the write. Use it only where that residual race is acceptable, or add a stronger serialized-owner design and test it separately.

`allowedTagPathPrefixes` is an accidental-scope guard, not authorization. Protect the Web Dev resource and API credential separately. The endpoint must reject arbitrary code and unknown fields.

The tested implementation checks `system.tag.getConfiguration` and requires configured data type `Document` before writing. This is necessary because runtime value type alone is insufficient: a Document whose root is an array can read as type `array`.

## Root-array boundary

A root-array Document accepted official tag import and rendered through a read-only Tree. However, a runtime Python-list write read back as semantically equal while changing the reported runtime representation to `PyDocumentObjectAdapter`; the two open Perspective Trees did not receive the expected model update. That failed sequence had no browser or Gateway warning.

Therefore the qualified writer accepts an object root only, with the Tree array beneath `items`. Do not claim root-array runtime writes from this contract. Use official whole-tag import for a root-array configuration/value workflow, or establish a separate typed `DocumentArray` construction contract with its own two-run visual and log evidence.

## Runtime proof

For every bootstrap, rejection, successful write, idempotent no-write, and restoration state:

1. Save the raw API response.
2. Read the complete Document independently with `tag-read-complex-v1` and require Good, untruncated evidence.
3. Capture every concurrent observer session and verify exact rows, revision text, and positive geometry.
4. Save screenshots and inspect clipping, overflow, and containment.
5. Correlate exact session/page/view identity through official Perspective APIs.
6. Export the target and protected projects and require exact expected state.
7. Query and classify the bounded official Gateway WARN-or-higher window even when the API, tag readback, and screen all appear correct.
8. Close or officially terminate only the exact test sessions, prove none remain, and query post-close logs.

## Boundaries

This evidence does not establish root-array writes, atomic multi-writer safety, multiple-path transactions, Document tags from OPC/query sources, tag permissions, redundancy, very large Documents beyond advertised caps, partial-member writes, arbitrary Perspective component models, or other Ignition builds. Test each independently.
