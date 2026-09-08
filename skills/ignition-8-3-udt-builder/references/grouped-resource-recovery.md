# Grouped UDT resource conflict and recovery

Use this workflow only for a caller-approved lab or a deliberately authorized recovery. Official tag import/export remains the normal UDT interface. Direct grouped-file work is a last-resort configuration operation; it is not a faster replacement for tag import.

## Resource shape

On the verified Ignition 8.3.8 build, UDT definitions under one logical type folder were stored together as:

```text
config/resources/core/ignition/tag-type-definition/<provider>/<groupPath>/
  unary-resource.json
  udts.json
```

`unary-resource.json` declares `udts.json`; `udts.json` is an array of `UdtType` objects. Validate that array with `scripts/validate_grouped_udts_file.py`. This differs from the official tag-import document, which must be one root object.

Never infer this filesystem mapping on another build. Confirm it from a known-good API-created fixture and the authenticated live contract.

## Safe mutation protocol

1. Export the exact logical target and every grouped sibling through the official tag API.
2. Inspect the grouped resource and preserve its exact content, SHA-256, parsed UDT names, and semantic snapshot.
3. Acquire `POST /data/api/v1/scan-lock/config` with bounded acquire and hold timeouts. A lock prevents Ignition from applying queued resource changes; it does not create a file-version precondition.
4. Immediately before replacement, compare the current grouped-file SHA-256 with the expected snapshot. On mismatch, return a conflict with `writeAttempted: false`. Refresh and rebase; never retry the stale bytes.
5. Write a same-directory temporary file, flush it, and atomically replace the target. For a new grouped resource, build a complete temporary directory containing both files and atomically move the directory into place.
6. Call `POST /data/api/v1/scan/config` once. This releases the lock and requests a scan. Poll `GET /data/api/v1/scan/config` to idle with a bounded deadline.
7. Verify official exports for every sibling, then verify affected instances and direct runtime members. Compare semantics, not merely HTTP status or file hash.
8. On any exception while holding the lock, request a scan in `finally` to release it. Repair malformed resources and restore intended content before ending the run.

## Two-plane visibility

An official tag import can update tag export/runtime state before the corresponding grouped file changes. Do not compute the filesystem conflict hash immediately after the first successful export. Poll both planes:

- official export reaches the intended revision;
- grouped-file inspection reaches the same semantic revision.

Only then treat the file hash as the post-API version. The verified build showed this lag during an API-A/file-B conflict test.

## Conflict test

For two definitions `TypeA` and `TypeB` in one grouped file:

1. Capture baseline bytes/hash and prepare filesystem proposal B from that baseline.
2. Apply API proposal A to `TypeA`; wait for both API and file semantic visibility.
3. Submit stale B with the baseline hash. Require `stale_sha256` and `writeAttempted: false`.
4. Refresh the whole grouped file, change only `TypeB`, replace with the refreshed hash under the scan lock, scan once, and require both API-A and file-B revisions.
5. Reverse the order: apply a fresh file change to `TypeA`, then an API change to `TypeB`; wait for both planes and require both revisions.
6. Restore the exact baseline content under the scan lock. Require the baseline SHA-256 and both baseline semantic revisions.

Blind last-writer-wins is a failed test even if both actors report success.

## Malformed-file recovery

A truncated `udts.json` produced one time-correlated Gateway error on the verified build:

```text
logger: tags.storage.resource
message: onResourcesCreated unable to deserialize resource.
```

The official tag export for the broken logical type returned HTTP 200 with `tagType: "Unknown"`; it did not return 404. Classify the body, not status alone.

Recovery is an exact compare-and-swap replacement of the malformed file with locally validated grouped JSON, followed by one scan and an official export/readback. The generic error does not identify a filename, so correlate it using the bounded scan time and the exact resource created by the test. Require no other new ERROR logs.

## Deployment safety for a custom action

Prove a new grouped-file action in a minimal isolated project first. After import, test health and POST, request one project scan, export the project, and require the complete expected inventory again. A successful import response is not persistence proof.

In testing, repackaging a large existing project with an unverified generic ZIP workflow initially loaded in memory, then failed to persist many unrelated resources and collapsed the export to `project.json`. The preserved authenticated backup allowed recovery. Do not repeat that path: use a ZIP-aware overlay process, compare entry inventories before import, and verify export both before and after a project scan.

If an existing project becomes an empty shell and replacement repeatedly fails with a collection-manager error, confirm the shell through official export/find, preserve and hash the complete backup, delete only that named broken shell with the official confirmed delete route, recreate it immediately from the backup, and verify GET, POST, and full export. Do not generalize this recovery to a healthy project.

## Claim limits

These tests prove scan-lock/atomic-write behavior, stale-hash rejection, sibling preservation, malformed recovery, and deterministic rollback on the tested build. They do not prove Gateway restart persistence, redundancy coordination, multi-node locking, production deployment-mode behavior, or client/session authorization. Restart testing requires explicit restart authority.
