# Package Contract

## Official Baseline

Ignition project export/import is a project backup workflow. The exported `.zip` restores/imports project resources only. In Ignition 8.1 and 8.3 docs, project exports include items such as Perspective Views, Perspective Properties, Project Properties, Named Queries, project event scripts, reports, SFCs, Transaction Groups, and Vision resources. They do not include Gateway-level configuration such as database connections, tag providers, device connections, certificates, or tags.

Official references:

- Ignition 8.1 Project Export and Import: https://www.docs.inductiveautomation.com/docs/8.1/platform/projects/project-export-and-import
- Ignition 8.3 Project Export and Import: https://docs.inductiveautomation.com/docs/8.3/platform/projects/project-export-and-import
- Ignition 8.1 resource.json File: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/resource-json-file
- Ignition 8.1 system.project.requestScan: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-project/system-project-requestScan
- Ignition 8.1 Exporting and Importing Tags: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/exporting-and-importing-tags

## Recommended Deliverable Layout

Use this layout when creating a user-facing package:

```text
deliverable/
  project/
    <ProjectName>_<date>.zip
  dependencies/
    tags/
      README.md
      *.json
    gateway-prerequisites.md
  install/
    INSTALL.md
    VALIDATION.md
  source/
    view-json/
      <view-name>.view.json
    notes/
      assumptions.md
```

If the user wants a single `.zip` to share, zip the `deliverable/` folder. Keep the Ignition project export zip inside it rather than merging tags and Gateway prerequisites into the project export.

## Seed-Export Mode

Use seed-export mode when the agent has to create a genuinely importable project export:

1. Create or obtain a blank project export from the same target Ignition version.
2. Add or replace only the target project resources.
3. Preserve each resource folder's `resource.json` structure and expected file list.
4. Re-import into a staging gateway or Designer, then export again from Ignition when possible.

This avoids inventing metadata that Ignition may reject.

For runner/API-created or imported ZIPs, do not include duplicate normalized destinations. Normalize entry names with forward slashes, remove empty and `.` path parts, and treat slash/backslash equivalents and Windows case-only path collisions as duplicates. Runner `0.3.133+` rejects `packageBase64` dry-run/apply and `projectResourceImportZip` requests with `PACKAGE_ZIP_INVALID` before package validation, backups, scans, or writes when duplicates are present.

For runner/API-created or imported ZIPs, keep each managed resource's `resource.json.files` list aligned to the final sibling data files after the package is overlaid on the target resource. Runner `0.3.140+` rejects `projectResourceImportZip` requests with `RESOURCE_MANIFEST_INVALID` and `manifestValidationPhase:"finalMergedResourceState"` before writes when the final state would have missing listed files or unlisted managed files.

For normal host-runner package `apply`, runner `0.3.142+` prunes stale optional Perspective view-managed files such as `thumbnail.png` when overwriting a view and the final `resource.json.files` omits that file. Treat `prunedStaleViewFiles` / `prunedStaleViewFileCount` as apply evidence, then read back the resource or run page validation to prove the final folder matches the manifest.

## Dependency Install Order

Use this order unless the project confirms otherwise:

1. Confirm modules and version: Perspective, Web Dev if needed, MQTT modules if bindings/scripts require them.
2. Configure Gateway prerequisites: database connections, tag providers, OPC devices, MQTT providers, certificates, security roles.
3. Import UDT definitions.
4. Import tag instances or dependency tag folders.
5. Import the project zip through Gateway or Designer.
6. Save project in Designer.
7. Run project script or timer validation commands.
8. Open the Perspective page and check Gateway/Perspective logs.

## Collision Policy Guidance

For tags, prefer a merge-style policy when changing only a small set of fields. Avoid full overwrite unless the user explicitly wants replacement and has a backup. Import UDT definitions before instances so type references resolve.

For project import conflicts, the Designer/Gateway may ask to overwrite, skip, rename, or cancel. Default to staging and manual review for conflicts.

## Validation Checklist

- Import completes without conflict surprises.
- Perspective view opens.
- Page configuration points to the intended view.
- Required project scripts are present at the exact expected Project Library path.
- Gateway timer/message handlers are present if included.
- All tag paths used by bindings/scripts exist or degrade gracefully.
- `system.tag.readBlocking` results have good quality for critical tags.
- Named queries run against the expected database connection.
- No Perspective console errors.
- Gateway logs do not show provider-not-found spam, script parse errors, or binding exceptions.
