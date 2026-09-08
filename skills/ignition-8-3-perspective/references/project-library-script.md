# Project Library helper

Use this workflow only after confirming the target is Ignition 8.3.8 or reproducing it on the installed build. It covers a top-level Project Library module. Do not infer nested-package behavior from it.

## Resource layout

Store a top-level module at:

```text
ignition/script-python/<module-name>/resource.json
ignition/script-python/<module-name>/code.py
```

Use this tested `resource.json` shape:

```json
{
  "scope": "G",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": ["code.py"],
  "attributes": {}
}
```

A project scan can populate or change generated modification attributes. Do not treat attribute churn as a source-code change, and do not ignore changes to any other metadata field.

## Authoring workflow

1. Discover the installed Gateway build, Jython version, OpenAPI operations, and documented agent API actions. Recheck whether OpenAPI now provides project-script or project-resource CRUD.
2. Export the project and hash every entry. Confirm the target module is absent for create or is an owned, fully recognized resource for update.
3. Compile and test the complete helper with the installed Jython runtime and library path before Gateway mutation. Keep Perspective component event scripts thin and move testable behavior into the Project Library helper.
4. Prefer a documented typed operation that generates a bounded known script shape. Do not expose caller-selected paths, modules, functions, or source evaluation through a fixed test action.
5. For create, acquire the official project scan lock, recheck absence, write both files in a temporary sibling directory, and atomically move the directory into place.
6. For update, require the exact current `code.py` hash, acquire the scan lock, re-read and re-hash the owned resource, atomically replace only `code.py`, and preserve `resource.json`.
7. Request the official project scan, confirm the lock is released, export the project, and compare the complete entry set and content hashes.

When no bounded folder operation supports the required helper, use an approved exact fresh-base whole-project import instead of introducing an arbitrary-source endpoint.

## Activation proof

Storage and scan success do not prove that the helper is callable. Invoke one fixed, typed, side-effect-bounded function through a documented agent API action when OpenAPI has no script-invocation operation.

The invocation action must:

- authenticate independently;
- fix or allowlist the module and function;
- validate every argument and reject unexpected fields;
- avoid `eval`, `exec`, caller-selected imports, and caller-supplied source;
- return structured input/output and the helper revision without credentials;
- run after create and again after update so the new revision changes the observed result.

Run the existing action regression suite and reject an unknown action after changing the agent API.

## Perspective boundary

A successful Gateway-scope invocation proves Project Library activation and update behavior. It does not prove that a Perspective component event ran, a session mounted the view, component state changed, or the client rendered a result. Prove those separately through a documented API-visible Perspective session before claiming end-to-end event behavior.
