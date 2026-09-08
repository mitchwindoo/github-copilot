# UDT event scripts and Project Library modules

Use this pattern when a UDT member event delegates work to reusable Project Library code, especially when the member is inside a child or grandchild UDT.

## Required Gateway context

Gateway-scoped tag event scripts can resolve user script libraries only through the Gateway Scripting Project. Read the current singleton first:

```text
GET /data/api/v1/resources/singleton/ignition/system-properties
```

If `config.gatewayScriptingProject` is absent or blank, a tag event cannot reliably import the helper project. Selecting a project is a Gateway-wide configuration mutation. In a test Gateway, capture the complete returned config and signature, select a dedicated helper project with the official system-properties `PUT`, verify readback, run the bounded matrix, and restore the exact original config in `finally`. Do not change this setting casually on a production Gateway.

The modification body is an array even for this singleton. On Windows PowerShell 5.1, preserve a one-element array with `ConvertTo-Json -InputObject $payload`; piping a one-element array into `ConvertTo-Json` unwraps it and the Gateway returns HTTP 400.

## Project Library ZIP layout

Script resources must be leaves. A folder used as a namespace must not also contain its own `resource.json` and `code.py` when it contains child script resources.

Verified layout:

```text
project.json
ignition/script-python/
  UDTScriptCalls/                 # folder-only namespace
    RootOps/
      resource.json
      code.py
    ChildOps/
      resource.json
      code.py
    Deep/                         # folder-only namespace
      GrandOps/
        resource.json
        code.py
```

The rejected layout put `resource.json` and `code.py` directly in `UDTScriptCalls` while also placing `ChildOps` and `Deep/GrandOps` below it. The project import returned success, but the project scan dropped the parent `code.py`, logged `Error creating dataFile`, and the tag event saw a package object without `root_event`. Validate every helper ZIP before import:

```text
python scripts/validate_project_library_zip.py helper-project.zip
```

Require root `project.json`, forward-slash ZIP names, complete `resource.json`/`code.py` pairs, declared files that exist, no compiled class files, and no script resource that contains descendant script resources.

Project import with `overwrite=true` is not proof that absent old resources were removed. A live overwrite left a stale parent `resource.json` behind. For disposable tests, use a new project name. For an owned existing project, export and inventory first, then use the official delete/recreate route only when removal is intended and the exact backup is available.

## Imports at different depths

Use explicit leaf imports in the event script:

```python
	if not initialChange:
		from UDTScriptCalls import RootOps
		RootOps.root_event(tagPath, currentValue.value, tag['parameters']['ScopeName'])
```

```python
	if not initialChange:
		from UDTScriptCalls import ChildOps
		ChildOps.child_event(tagPath, currentValue.value, tag['parameters']['ScopeName'])
```

```python
	if not initialChange:
		from UDTScriptCalls.Deep import GrandOps
		GrandOps.grand_event(tagPath, currentValue.value, tag['parameters']['ScopeName'])
```

Do not call a folder-only namespace as if it were a module. A nested module may import and call sibling or ancestor leaves; the live grandchild helper imported `ChildOps` and `RootOps`, then called through both successfully.

## Resolving UDT paths

In the verified 8.3.8 tag-event runtime, `tagPath` is unicode text. Derive levels by removing path segments:

```python
def parent(path):
	value = unicode(path)
	if "/" not in value:
		raise ValueError("tag_path_has_no_parent")
	return value.rsplit("/", 1)[0]
```

For a source at `Probe/Child/Grandchild/GrandSource`:

- `parent(tagPath)` is the grandchild UDT instance;
- `parent(parent(tagPath))` is the child UDT instance;
- `parent(parent(parent(tagPath)))` is the root UDT instance.

Build sibling and descendant paths explicitly from those anchors. Read related values in one bounded `system.tag.readBlocking` call, require every quality to be Good, then write one observable marker with `system.tag.writeBlocking`. Pass UDT parameters from the event dictionary (`tag['parameters']['Name']`) rather than inventing parameter tag paths.

## Actual Folder members inside one UDT

A `Folder` member adds a tag-path segment but does not create a new UDT parameter scope. In two clean runs, scripts at all three locations below read the same owning parameter through `tag['parameters']['AssetName']`:

```text
Probe/RootSource
Probe/AreaA/FolderSource
Probe/AreaA/Deep/DeepSource
```

For the deep source:

```python
deep = parent(tagPath)       # Probe/AreaA/Deep
area = parent(deep)          # Probe/AreaA
root = parent(area)          # Probe
```

From `root`, the helper successfully read all of these in one call:

```text
RootSibling
AreaA/FolderSibling
AreaA/Deep/DeepSibling
AreaB/OtherSibling
```

This is different from a nested `UdtInstance`: a nested instance can introduce its own parameter values, while a plain Folder only organizes members. Count path segments from the event member to a known root; do not assume every visual level is a UDT boundary.

## Live-proven matrix

Two clean API-only runs on Ignition 8.3.8 proved all of the following with identical helper-project bytes:

- a root member called `UDTScriptCalls.RootOps`;
- a child UDT member called `UDTScriptCalls.ChildOps`;
- a grandchild UDT member called `UDTScriptCalls.Deep.GrandOps`;
- the grandchild module called through the child and root modules;
- every helper read root, child-sibling, and grandchild-sibling values and wrote an exact result marker;
- parameters resolved as `ROOT`, `CHILD`, and `GRAND` at their respective UDT levels;
- a deliberate `GrandOps.no_such_function` call left its marker unchanged and produced the sole correlated dispatcher `AttributeError`;
- source values and the prior Gateway Scripting Project were restored.

Two more clean runs proved the parallel Folder-member matrix: root, one-Folder, and two-Folder-deep scripts called matching Project Library depths, shared the owning `ASSET-001` parameter, crossed from `AreaA/Deep` to sibling `AreaB`, produced exact markers, and restored all state with only the intentional missing-function ERROR.

Do not count import/export as runtime proof. After initialization, reset markers, write each source separately, wait for the exact marker, capture a narrow logger window, run one malformed control, and require no unexpected ERROR logs. Restore source values before restoring the Gateway Scripting Project so cleanup events still have their library context.
