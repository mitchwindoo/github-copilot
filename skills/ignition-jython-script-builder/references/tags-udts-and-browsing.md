# Tags, UDTs, And Browsing

Read this before constructing tag paths, reading or writing tags, configuring tags or UDTs, writing tag event scripts, or browsing resources.

## Contents

- [Tag Path Construction](#tag-path-construction)
- [Tags](#tags)
- [Tag Configuration](#tag-configuration)
- [Tag Event Scripts](#tag-event-scripts)
- [Browsing](#browsing)
- [Additional Customer Runtime Rules](#additional-customer-runtime-rules)

## Tag Path Construction

For Gateway, Web Dev, and Project Library helper scripts, prefer fully qualified tag paths assembled from configurable parts:

```python
def clean_segment(name, value):
    text = str(value).strip("/")
    if text == "" or "[" in text or "]" in text or "//" in text:
        fail("bad %s: %s" % (name, value))
    return text

def make_tag_path(provider, root, instance, member):
    return "[%s]%s/%s/%s" % (
        clean_segment("provider", provider),
        clean_segment("root", root),
        clean_segment("instance", instance),
        clean_segment("member", member)
    )
```

Path validation:

- Fully qualified generated paths such as `[Sample_Tags]LLM Tests/<run>/Tank_A/Level` read Good values and supported write/readback.
- A path without provider brackets (`LLM Tests/<run>/Tank_A/Level`) read Good in this Web Dev project because a project default provider resolved it locally. Treat this as non-portable; Gateway/tag contexts may not have a project default provider.
- `[~]LLM Tests/<run>/...` failed from Web Dev/Gateway script scope as `Tag provider '~' not found`.
- `[.]Level` failed from Web Dev/Gateway script scope as `Tag provider '.' not found`.
- `system.tag.browse(...)` returned dict items whose `fullPath` values should be converted with `str(...)` before appending members, logging, or JSON output.

Use `[.]` and `[~]` only where Ignition supplies tag-relative context, such as tag bindings, UDT definitions, and tested tag event scripts. Library functions should accept the base path/provider as an argument instead of assuming a relative tag context.


## Tags

`system.tag.readBlocking()` returns QualifiedValue objects:

- `.value`
- `.quality`
- `.timestamp`

Good quality does not guarantee non-null value. Check both quality and nullness for critical reads.

`system.tag.readBlocking(path)` with a single string path still returned a list. Missing paths returned a bad QualifiedValue (`Bad_NotFound`) with `value == None`, not an exception. Always iterate the returned list and inspect each QualityCode.

`system.tag.writeBlocking()` returns quality results. Check all of them. Missing paths, expression/read-only tags, and datatype mismatches returned `Bad_NotFound`, `Bad_ReadOnly`, or `Error_TypeConversion` QualityCodes instead of throwing in local tests.

Never use truthiness to decide whether a read/write succeeded. Validation notes:

- `bool(qv)` was `True` for both good and bad QualifiedValues.
- `bool(qv.quality)` was `True` even when quality was `Bad_NotFound`.
- `bool(qc)` was `True` even when a write returned `Bad_NotFound`.
- Valid values such as `0`, `False`, and `""` were falsey even with Good quality.

Use explicit checks:

```python
qv = system.tag.readBlocking([tagPath])[0]
if not qv.quality.isGood():
    fail("bad read quality: %s" % qv.quality)
value = qv.value

qc = system.tag.writeBlocking([tagPath], [value])[0]
if not qc.isGood():
    fail("bad write quality: %s" % qc)
```

Scalar write forms such as `system.tag.writeBlocking(path, value)` may be accepted by some Gateway/script contexts, but reusable scripts should still use path/value lists:

```python
results = system.tag.writeBlocking([tagPath], [newValue])
for qc in results:
    if not qc.isGood():
        fail("write failed: %s" % qc)
```

When copying values from one tag to another, prefer explicit `.value` extraction unless you intentionally want to pass the full QualifiedValue:

```python
qv = system.tag.readBlocking([sourcePath])[0]
if not qv.quality.isGood():
    fail("bad source quality: %s" % qv.quality)
system.tag.writeBlocking([destPath], [qv.value])
```

Validation notes:

- `system.tag.writeBlocking([dest], [qv.value])` wrote the value.
- `system.tag.writeBlocking([dest], readBlocking([source]))` also wrote the value because the source read list exactly paralleled the destination path list.
- `system.tag.writeBlocking([dest], qv)` scalar form also worked locally.
- `system.tag.writeBlocking([dest], [readBlocking([source])])` failed with `Error_TypeConversion` because it wrapped the list as one nested value.

Use the explicit `.value` form as the default skill pattern. Passing QualifiedValues can be valid when quality/timestamp propagation is intentional, but it should be a deliberate choice and still requires returned QualityCode checks.

`system.tag.exists()` does not confirm a tag value is usable.

### Async Tag Reads/Writes

`system.tag.readAsync()` and `system.tag.writeAsync()` return `None`; the callback is where continuation logic belongs. Do not write code that expects an async call to return values to the next line.

Validation notes:

- `readAsync([path], callback)` returned `None`.
- The read callback received a list of QualifiedValues and wrote a result tag.
- `writeAsync([path], [value], callback)` returned `None`.
- The write callback received a list of QualityCodes and wrote a result tag.

Use blocking calls when the current script needs the value/result immediately:

```python
qv = system.tag.readBlocking([tagPath])[0]  # use now
```

Use async calls only when the callback can own the next step:

```python
def read_done(qvs, resultPath=resultPath):
    import system
    qv = qvs[0]
    if qv.quality.isGood():
        system.tag.writeBlocking([resultPath], ["value=%s" % qv.value])

system.tag.readAsync([tagPath], read_done)
```

Pass state into callbacks explicitly through default args, callable objects, or other stable storage. Import `system` inside callbacks for Gateway-event portability; a Web Dev callback may work without it, but Gateway timer/tag callback scope is known to be less forgiving.

When comparing source tags to MQTT/reference/output tags, normalize types when appropriate:

```python
def same_value(actual, expected):
    return str(actual) == str(expected)
```

Do not create siblings whose names differ only by case. A local `system.tag.configure(..., "a")` test treated `ObjDataType` and `ObjDatatype` as the same path: the second configure returned a collision and reading the case-variant path resolved to the first tag.


## Tag Configuration

Use `system.tag.getConfiguration()` for inspection. Do not mutate the returned object and pass it back into `system.tag.configure()`.

Build a fresh minimal payload:

```python
cfg = {
    "name": "<instanceName>",
    "tagType": "UdtInstance",
    "typeId": "<udtTypeId>"
}
system.tag.configure("[<tagProvider>]<parentFolder>", [cfg], "m")
```

The configure path is the parent folder. The child name is inside the config.

Do not treat `getConfiguration()` output as portable JSON. Validation notes:

- `path` was a `BasicTagPath`.
- `tagType`, `dataType`, and alarm `mode` were Java/Ignition-backed objects.
- `system.util.jsonEncode(original_cfg)` failed with recursion depth / Java `StackOverflowError`.
- A deep-copied config whose `name` was changed but whose `path` was retained returned `Error_Configuration(...)` because the copied path object was not coercible back into a `TagPath`.

Do not deep-copy/rename a returned config and write it as a clone. Build a fresh minimal config. If you are intentionally salvaging a copied config in a controlled migration, remove `path` and internal/generated fields first and verify every QualityCode; fresh minimal config is still preferred.

Do not overwrite `tagType` on a returned config object. Those objects can contain Ignition-backed internal types; structural mutation can cause `TagObjectType` cast errors or null path errors.

For targeted edits, use collision policy `"m"` and check every returned quality code:

```python
results = system.tag.configure(parentPath, [cfg], "m")
for qc in results:
    if not qc.isGood():
        raise Exception("Configure failed: %s" % qc)
```

Collision-policy validation:

- `"m"` with a partial config preserved unspecified properties (`dataType`, `valueSource`, `documentation`, `enabled`, `engUnit`) and applied the specified value change.
- `"o"` with a partial config replaced the tag configuration and removed unspecified properties, even though the write QualityCode was Good.
- `"i"` returned Good with an ignored/collision message and left the tag unchanged.
- `"a"` returned a bad QualityCode instead of throwing in this run and left the tag unchanged.

Reusable rule: do not use partial `"o"` for small edits. Use fresh complete configs for intentional replacement, `"m"` for targeted edits, and always inspect returned QualityCodes plus readback/config shape.

For UDT instance parameter overrides, pass either the scalar value or a full typed object:

```python
system.tag.configure("[<provider>]<folder>", [{
    "name": "Pump001",
    "tagType": "UdtInstance",
    "typeId": "<relative/type/path>",
    "parameters": {"AssetName": "MOTOR_A"}
}], "m")

system.tag.configure("[<provider>]<folder>", [{
    "name": "Pump002",
    "tagType": "UdtInstance",
    "typeId": "<relative/type/path>",
    "parameters": {"AssetName": {"dataType": "String", "value": "MOTOR_B"}}
}], "m")
```

Do not use a value-only object:

```python
"parameters": {"AssetName": {"value": "MOTOR_A"}}  # wrong
```

Validation notes: the value-only object configured with Good quality but `getConfiguration()` reported `{datatype=Integer, value=null}`. Direct scalar and full `dataType` object produced `{datatype=String, value=...}`.


## Tag Event Scripts

For Ignition 8.1 tag event JSON, use `eventScripts` with lowercase `eventid` values such as `valueChanged`.

Store script text as the indented body of the event function:

```python
cfg = {
    "name": "<tagName>",
    "tagType": "AtomicTag",
    "valueSource": "memory",
    "dataType": "Int4",
    "eventScripts": [{
        "eventid": "valueChanged",
        "script": "\tif initialChange:\n\t\treturn\n\t# script body..."
    }]
}
```

For `valueChanged`, guard `initialChange`, check `missedEvents`, and treat `currentValue` and `previousValue` as QualifiedValues. Use `.value` for the value and `.quality.isGood()` before critical logic. `currentValue == 10` can be false while `currentValue.value == 10` is true.

Ignition 8.1.32+ `valueChanged` behavior is value-change focused. On the local 8.1.53 Gateway, a write from `10` to `10` returned Good quality but did not increment the event counter; a later write from `10` to `11` did. Do not use same-value writes as a trigger mechanism.

Treat `tagPath` as a full string path unless the context confirms it is a richer object. For same-folder tag event reads/writes, prefer Ignition relative paths such as `[.]Sibling` when the target context validates that scope:

```python
countQv = system.tag.readBlocking(["[.]EventCount"])[0]
system.tag.writeBlocking(["[.]EventCount", "[.]Status"], [int(countQv.value) + 1, "updated"])
```

Use string operations on `str(tagPath)` when you need to derive paths outside the same folder or need explicit path evidence.

Keep tag event scripts short. Move heavy logic to a Project Library or Gateway script and call it from the event.

### UDT Parameters And Curly Braces

In UDT tag event scripts, prefer the modern parameter dictionary:

```python
asset_name = tag["parameters"]["AssetName"]
```

Validation notes: a UDT tag event using `tag["parameters"]["AssetName"]` read `MOTOR_A`, then after a parameter merge update read `MOTOR_B` on the next event without restarting the UDT.

Avoid legacy curly-brace parameter expansion inside UDT tag event bodies:

```python
asset_name = {AssetName}  # wrong for string parameters
```

Validation notes: with `AssetName = "MOTOR_A"`, the legacy line failed as `global name 'MOTOR_A' is not defined`, because the expanded string was not quoted Python.

Also avoid Python `.format(...)` placeholders in UDT tag event bodies:

```python
text = "{0}_ACK".format(currentValue.value)  # unsafe in UDT tag events
```

Validation notes: on plain memory tag event scripts, `{0}` `.format`, `%` formatting, dict literals, and concatenation all ran. On UDT tag event scripts, `%` formatting, concatenation, and a simple dict literal ran, but the `{0}` `.format` case never updated result tags (`EventCount=0`, `Status="Waiting"`). Use `%` formatting or concatenation in UDT tag events, or delegate formatting to a Project Library function after project scope is verified.


## Browsing

Use `results.getResults()` and treat each browse item as a dictionary. Browse items may be dictionaries, and attribute access such as `item.fullPath` can fail.

```python
results = system.tag.browse(root, {"recursive": True})
for item in results.getResults():
    name = str(item["name"])
    full_path = str(item["fullPath"])  # BasicTagPath -> string
```

Do not JSON-encode browse result dictionaries directly. Validation notes:

- `item["fullPath"]` was a `BasicTagPath`.
- `system.util.jsonEncode(item)` failed with recursion / Java `StackOverflowError`.
- `system.util.jsonEncode({"fullPath": item["fullPath"]})` also failed in the fixture browse.
- `results.getContinuationPoint()` existed and returned `""` for this completed browse; `results.hasMoreResults()` did not exist in the local wrapper.

Before browsing a provider root, verify the provider exists. A missing-provider browse may not throw in every context; it can return no useful nodes and lead the script to make a false "no tags exist" conclusion.

For UDT auto-discovery, browse a bounded root with recursive UDT instance filters and then read member paths from discovered instances:

```python
root = "[<provider>]<folder>"
type_id = "<relative/typeId>"
results = system.tag.browse(root, {
    "recursive": True,
    "tagType": "UdtInstance",
    "typeId": type_id
})

instances = []
for item in results.getResults():
    instances.append(str(item["fullPath"]))

member_paths = []
for base in instances:
    member_paths.append(base + "/Speed")
    member_paths.append(base + "/Nested/State")
qvs = system.tag.readBlocking(member_paths)
```

Validation notes: `{"recursive": True, "typeId": type_id}` by itself returned UDT instances plus child folders/member tags. Pair `typeId` with `tagType: "UdtInstance"` when the goal is an instance list. Cast `fullPath` to string before concatenating child paths. Use `maxResults`/caps for broad recursive browses and check continuation metadata when present.

Browse filters are simple key/value filters, not SQL-like predicates:

- `name` supports `*` wildcards.
- A Python expression such as `{"tagType": "Folder"} or {"tagType": "UdtInstance"}` evaluates to the first non-empty dict, so it browsed only folders locally.
- Duplicate keys in one dict keep only one effective value. A local duplicate `tagType` dict behaved like the last `tagType` value.
- Browse does not filter UDT instances by the value of a child member tag. Browse the instances first, then read member paths and filter in script.

Example:

```python
instances = []
for item in system.tag.browse(root, {
    "recursive": True,
    "tagType": "UdtInstance",
    "typeId": type_id
}).getResults():
    instances.append(str(item["fullPath"]))

status_paths = [path + "/Status" for path in instances]
qvs = system.tag.readBlocking(status_paths)
active = []
for path, qv in zip(instances, qvs):
    if qv.quality.isGood() and qv.value is True:
        active.append(path)
```

## Additional Customer Runtime Rules

Use these detailed tag, UDT, browsing, configuration, event, and safety rules.

- Treat `system.tag.getConfiguration()` output as inspection data. It can contain Java-backed objects such as `BasicTagPath` and alarm mode objects; do not JSON-encode, deep-copy/rename, or write it back as a clone. For writes, build a fresh minimal dictionary.
- Call `system.tag.configure()` on the parent path with child config names. Prefer collision policy `"m"` for targeted edits; partial `"o"` overwrites can remove unspecified properties. Check QualityCodes and verify readback/config shape.
- Do not delete, remove, prune, or clean up files, tags, UDTs, project resources, database rows, backups, or temp resources unless the user explicitly commands that deletion in the current task. Default to create/update/merge/validate; if deletion seems required, stop and ask.
- `system.tag.readBlocking()` returns a list of QualifiedValue objects even for one path. Missing paths can return bad QualifiedValues instead of throwing. Never rely on truthiness: bad QualifiedValues and bad QualityCodes are still truthy. Check `.quality.isGood()` and then inspect `.value` explicitly.
- `system.tag.writeBlocking()` should use parallel path/value lists: `system.tag.writeBlocking([path], [value])`. Missing paths, read-only tags, datatype mismatches, and nested list values can return bad/error QualityCodes instead of throwing; path/value count mismatches throw. Never rely on `if qc`, because bad QualityCodes are truthy. Check `qc.isGood()` and verify critical readback.
- When copying tag values, write `[qv.value]` unless intentionally propagating a QualifiedValue's quality/timestamp. A list returned by `readBlocking()` can be used as the values list only when it exactly parallels the destination paths; never wrap that read list in another list.
- `system.tag.readAsync()` and `writeAsync()` return `None`; the callback is the continuation. Use blocking calls when the next line needs the result. Callback args are lists of QualifiedValues or QualityCodes; pass state explicitly and import `system` inside callbacks for Gateway-event portability.
- Check every `system.tag.configure()` result quality code before treating a tag/UDT configuration change as successful.
- `system.tag.exists()` is only a structural check. It does not prove quality, datatype, freshness, or usability.
- Validate tag provider/root availability before broad browse. Missing-provider browse may fail silently or return no useful nodes; do not treat that as proof no tags exist.
- For Gateway, Web Dev, and Project Library helper scripts, build fully qualified tag paths from configurable provider/root/instance/member values and validate path segments before read/write. Do not use `[.]` or `[~]` unless the code is actually running in a tag-relative context such as a tag event or tag binding; in Gateway/Web Dev scope they can be treated as provider names. Unqualified paths may resolve through a project default provider in some contexts, but are not portable.
- For tag browse and UDT discovery, call `results.getResults()`, treat each item as a dict, use bracket/key access, and cast `fullPath`/`name` with `str(...)` before JSON, logging, or appending member paths. Do not JSON-encode browse result dictionaries directly.
- For Perspective startup scripts that build dynamic Flex Repeater/list models from tag browse/read results, assign only JSON-simple lists/dicts/scalars into `view.custom`. Check every member's QualityCode before formatting, cast tag paths to strings, sort instances deterministically, and for Flex Repeater put child params as top-level instance keys while reserving `instanceStyle`/`instancePosition` for layout/styling.
- For UDT instance discovery, browse a bounded root with `{"recursive": True, "tagType": "UdtInstance", "typeId": "<relative/typeId>"}` and cast `fullPath` with `str(...)` before appending member paths. `typeId` alone can still return child folders/tags.
- Browse filters are not SQL predicates. For OR conditions, run separate browses and merge; duplicate dict keys keep only one value. To filter UDTs by child/member tag values, first browse the UDT instances, then read those member paths and filter in script.
- Do not create sibling tags, UDTs, or folders whose names differ only by case; case-only names can collide.
- For tag event scripts, store/configure the script body with leading indentation, guard `initialChange`, check `missedEvents`, use `currentValue.value` / `previousValue.value`, use `[.]SiblingTagName` for same-folder sibling tags when appropriate, and treat `tagPath` as a full string path unless the context proves otherwise. In Ignition 8.1.32+, `valueChanged` fires on value changes only; do not rely on same-value writes to retrigger it.
- In UDT tag event scripts, read UDT parameters with `tag["parameters"]["ParamName"]`, cast before math, and validate through result/status tags plus `Parameters.ParamName` reads after any instance-parameter merge. Avoid legacy `{ParamName}` expansion and Python `.format(...)` placeholders such as `{0}` in the event body; UDT parameter expansion can occur before script execution. Use `%` formatting, concatenation, or a Project Library function.
- For UDT instance parameter overrides through `system.tag.configure()`, pass a scalar value (`{"AssetName": "MOTOR_A"}`) or a full typed object (`{"dataType": "String", "value": "MOTOR_A"}`). Do not pass value-only objects (`{"value": "MOTOR_A"}`), which were accepted as null Integer parameters.
- When a Perspective/Gateway script intentionally edits UDT instance parameters, write copied instance parameter paths such as `[<tagProvider>]<folder>/<Instance>/Parameters.ParamName` with parallel `system.tag.writeBlocking(paths, values)` lists. Check every QualityCode, then verify both `Parameters.ParamName` and dependent member/expression paths; normalize Boolean/numeric parameter readback such as `"0"`, `"1"`, and numeric strings before comparisons or UI use.
- For UDT-backed Perspective row-model scripts, preserve `None`, empty string, and literal `"null"` as distinct states; omit overrides when defaults should apply, guard numeric null before arithmetic, and do not build quoted expression strings containing `{ParamName}` placeholders.

### Common safe helpers

Prefer helper functions like these, adapting names to the script:

```python
from java.lang import Thread

def sleep_ms(milliseconds):
    Thread.sleep(long(milliseconds))

def fail(reason):
    raise Exception("IGNITION SCRIPT ABORTED: " + str(reason))

def read_good(path):
    qv = system.tag.readBlocking([path])[0]
    if not qv.quality.isGood():
        fail("Bad quality at %s: %s" % (path, qv.quality))
    if qv.value is None:
        fail("Null value at %s" % path)
    return qv.value

def write_checked(paths, values, timeoutMs=45000):
    results = system.tag.writeBlocking(paths, values, timeoutMs)
    for path, value, qc in zip(paths, values, results):
        if not qc.isGood():
            fail("Write failed: %s value=%s result=%s" % (path, value, qc))
    return results

def check_quality_results(action, results):
    for idx, qc in enumerate(results):
        if not qc.isGood():
            fail("%s failed at index %s: %s" % (action, idx, qc))
    return results
```
