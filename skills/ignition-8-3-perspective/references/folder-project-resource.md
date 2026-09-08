# Folder-based Perspective resources

Use this workflow only after confirming the target is Ignition 8.3.8 or reproducing it on the installed build. It applies when an authenticated, bounded agent API can create or update known Perspective project resources in the Gateway project folder.

The Ignition OpenAPI operations for project scan locking and scanning coordinate external folder changes. They do not provide general project-file, Perspective-view, or page-route CRUD. When a required folder mutation is unavailable through OpenAPI, expose only the smallest typed operation through the approved agent API. Do not expose arbitrary paths, arbitrary files, or arbitrary JSON writes.

## Static view operation

Generate only a view shape already reproduced on the installed build. For the minimal static Flex-and-Label shape, use the resource layout and JSON documented in [project-view-route.md](project-view-route.md).

The operation must:

1. Accept a validated project identifier, caller-approved Perspective namespace, view name, and typed view fields.
2. Resolve and verify that every target remains beneath the selected project and namespace.
3. Reject traversal, separators in a single path segment, unexpected fields, invalid values, and writes outside the bounded resource type.
4. Support dry-run without changing project files or scan metadata.
5. Distinguish create from update. Reject an existing target during create and a missing target during update.
6. Require the exact current content hash for update.
7. Acquire the official project scan lock before rechecking preconditions.
8. Create the resource directory atomically or replace only the declared content file atomically.
9. Request an official project scan and release the lock through that scan operation.
10. Export the project and verify the exact target contents, project entry set, and all non-target resources.

If any failure occurs before the atomic replacement, leave the existing resource unchanged. Return structured results that identify the operation, target, precondition hashes, write status, scan status, and readback status without returning credentials.

## Page route operation

Treat page configuration as a shared resource. Read the current page configuration and require its exact content hash before mutation and again while holding the scan lock.

The operation must:

1. Restrict the URL route and target view path to caller-approved namespaces.
2. Verify the target view exists during dry-run and apply.
3. Reject route creation when the route already exists and route update when it does not.
4. Preserve every existing page entry and the complete `sharedDocks` value.
5. Change only the declared route entry, atomically replace the configuration, request a project scan, and export for semantic comparison.

Do not reconstruct page configuration from a partial example. The snippet in [project-view-route.md](project-view-route.md) illustrates fields, not a replacement document.

## Scan and comparison rules

- Check for an existing scan lock, acquire the official lock, re-read and re-hash the target, write atomically, then request the official scan.
- Abort on a held lock, drift, authorization failure, scan failure, unexpected export entry, or unexpected semantic change.
- A scan can update generated modification attributes in project `resource.json` files even when their non-attribute fields and content files are unchanged. Compare parsed metadata as well as bytes; allow only specifically identified scan-generated attribute changes.
- Never suppress an unexplained difference as scan churn. Verify all non-attribute fields, all content files, and the complete project entry set.

## Validation boundary

An HTTP GET returning the Perspective application shell proves that the route is registered and reachable. It does not prove that the browser mounted the view, rendered components, evaluated bindings, or ran client events. Claim those behaviors only from a documented Perspective session API or other API-observable runtime evidence.
