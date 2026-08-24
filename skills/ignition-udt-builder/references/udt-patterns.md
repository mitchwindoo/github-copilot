# Ignition UDT Patterns

Use this reference when a UDT task needs concrete modeling choices or validation examples.

## Contents

- Modeling Checklist
- Definition And Instance Locations
- TagConfigure Request Shapes
- Parameter Shapes
- Parameter Readback And Coercion
- Expression Tag Patterns
- Dynamic PLC Path Patterns
- Generated Address Parameters
- Nested UDTs
- Command And Interlock Modules
- Tag Event Scripts In UDTs
- Instrument Faceplate Contracts
- Variant Equipment Families
- Copy, Derive, And Update UDT Types
- Discovery
- Readback Rules
- Alarm Modeling

## Modeling Checklist

- Choose the smallest reusable equipment class: pump, valve, motor, tank, meter, skid, zone, line, or controller.
- Put repeated runtime values in member tags.
- Put per-instance constants, PLC member roots, display names, enable flags, limits, and engineering metadata in UDT parameters.
- Keep Perspective-facing member names stable, even if the PLC path changes by parameter.
- Prefer a core UDT plus parent skids/assemblies when equipment repeats inside a larger asset.
- Avoid case-only differences in sibling tag or UDT names.

## Definition And Instance Locations

UDT definitions live under the provider `_types_` area:

```text
[Provider]_types_/Area/PumpCore
```

UDT instances live under normal tag paths:

```text
[Provider]Area/Assets/PMP-001
```

Instance `typeId` values are relative to `_types_`:

```json
{"tagType": "UdtInstance", "typeId": "Area/PumpCore"}
```

Do not bind Perspective pages to `_types_` definitions. Bind to instances and members.

## TagConfigure Request Shapes

Create UDT definitions under `[Provider]_types_/...` and instances under normal provider paths. Keep writes dry-run-first and restrict `allowedTagPathPrefixes` to the exact target root.

Create a type:

```json
{
  "action": "tagConfigure",
  "basePath": "[Provider]_types_/Area",
  "allowedTagPathPrefixes": ["[Provider]_types_/Area"],
  "collisionPolicy": "a",
  "dryRun": true,
  "tags": [
    {
      "name": "PumpCore",
      "tagType": "UdtType",
      "parameters": {
        "AssetName": {"dataType": "String", "value": "PMP-001"},
        "HighLimit": 80.0
      },
      "tags": [
        {"name": "PV", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float8", "value": 0.0},
        {"name": "High", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "{[.]PV} > {HighLimit}"}
      ]
    }
  ]
}
```

Create an instance:

```json
{
  "action": "tagConfigure",
  "basePath": "[Provider]Area/Assets",
  "allowedTagPathPrefixes": ["[Provider]Area/Assets"],
  "collisionPolicy": "a",
  "dryRun": true,
  "tags": [
    {
      "name": "PMP-001",
      "tagType": "UdtInstance",
      "typeId": "Area/PumpCore",
      "parameters": {"AssetName": "PMP-001", "HighLimit": 80.0}
    }
  ]
}
```

For apply calls, set `dryRun` false and include the runner's exact confirmation string. Treat `ok: true` as only the envelope result; require `allGood: true`, good returned `qualityCodes`, and explicit member/parameter readback before relying on a UDT write. Runner `0.3.143+` advertises `udtScaffoldUnknownFailureRecovery`; if a confirmed `udtScaffold` nested `tagConfigure` step fails with missing, null, or empty `qualityCodes`, preserve the full response and inspect `writesStarted`, `completedSteps`, `preflightExistingPaths`, `preflightNewPaths`, `recoveryAttempted`, `recoveryAllGood`, `recoveryRequired`, and nested `recovery` details such as `deletePaths` and `restorePaths` before any more writes.

## Parameter Shapes

Prefer scalar overrides for numeric and Boolean UDT parameters:

```json
{"AssetName": "PMP-101", "HighLimit": 90.0, "Enabled": true}
```

Use typed objects for strings or when a tested type shape is needed. For decimal parameters, prefer `Float`; API tests preserved fractions for `Float` and truncated `Float8`/`Double` typed objects:

```json
{
  "AssetName": {"dataType": "String", "value": "PMP-101"},
  "Scale": {"dataType": "Float", "value": 2.5}
}
```

Avoid value-only objects:

```json
{"AssetName": {"value": "PMP-101"}}
```

Avoid string numeric/Boolean overrides when expressions or Perspective rows need real values:

```json
{"HighLimit": "90.0", "Enabled": "false"}
```

Use `None` or omit the parameter for null/default behavior. Do not use `"null"` as a string sentinel.

## Parameter Readback And Coercion

Read `Parameters.ParamName` paths directly, but normalize types before using values in Perspective row models. Parameter reads can return strings such as `"5"`, `"1"`, `"0"`, or `"4.5"` even when dependent expression tags evaluate as numbers or booleans.

Validate dependent expression tags after every non-trivial parameter shape change. Bad strings can configure successfully and only fail later as expression quality errors. String numeric parameters can also surprise math: multiplication/comparison may coerce, while `+` can concatenate.

## Expression Tag Patterns

Parameter compare:

```text
{VoltageClass} = "480"
```

Member plus parameter:

```text
{VoltageClass} = "480" && {[.]VLAvg} > {HighLimit}
```

Sibling expression aggregation:

```text
{[.]MeterA/HighAlarmExpr} || {[.]MeterB/HighAlarmExpr}
```

Expression language does not browse tags. If the number of children is variable, use a script or parent view model.



## Dynamic PLC Path Patterns

Official UDT parameter syntax is designed for parameterized OPC item paths. In the low-touch runner, OPC tag writes are blocked, so API tests should use safe memory tags plus expression or static Reference fixtures unless a site-specific device test is approved.

Reference tags:

```json
{"name": "StaticReference", "tagType": "AtomicTag", "valueSource": "reference", "dataType": "Float8", "sourceTagPath": "[Provider]Area/Source/PV"}
```

Static Reference tags worked standalone and inside a UDT. Reference `sourceTagPath` values containing UDT parameters stayed literal and read `Uncertain_InitialValue`:

```json
{"name": "ParamReference", "valueSource": "reference", "sourceTagPath": "{FlowPath}"}
{"name": "PieceReference", "valueSource": "reference", "sourceTagPath": "[Provider]{Root}/PV"}
```

Prefer expression tags for simulated dynamic paths:

```text
tag({FlowPath})
tag("[Provider]" + {Root} + "/PV")
tag({FlowPath}) > {HighLimit}
```

Avoid these forms:

```text
tag("{FlowPath}")
{[Provider]{Root}/PV}
```

The quoted form attempted to parse the literal `{FlowPath}`. The brace path with an embedded UDT parameter produced `Error_Configuration`.

Validation reads:

```text
[Provider]Area/Source/PV
[Provider]Area/Assets/Pump101/Parameters.FlowPath
[Provider]Area/Assets/Pump101/DynamicPV
[Provider]Area/Assets/Pump101/DynamicHigh
```

Require good quality and expected values for both the source tag and the dynamic member. Keep bad-path instances in tests when useful; they should return bad/not-found or uncertain quality, not misleading good values.


## Generated Address Parameters

Official UDT parameter syntax supports offsets, formatting, and simple math in member properties:

```text
DataPoint{BaseAddress+0|000}
DataPoint{BaseAddress+1|000}
DataPoint{BaseAddress+(Channel*2)|000}
```

Use that form for properties that perform UDT parameter substitution, such as OPC item paths. The low-touch runner blocks OPC writes, so verify real OPC paths only with site approval.

Inside expression tags, do not put offset/format placeholders inside quoted strings or `tag("...")` path literals:

```text
"DataPoint{BaseAddress+1|000}"
tag("[Provider]Area/DataPoint{BaseAddress+1|000}")
```

In expression tags, those can stay literal and the `tag()` path can fail with expression-eval quality. Build the same generated strings with expression-language math and `numberFormat`:

```text
"DataPoint" + numberFormat({BaseAddress}+1, "000")
"DataPoint" + numberFormat({BaseAddress}+({Channel}*2), "000")
{StationPrefix} + "-" + numberFormat({DeviceNumber}, "000")
tag("[Provider]Area/DataPoint" + numberFormat({BaseAddress}+1, "000"))
```

For bad parameter values, the instance can still configure successfully while generated-address members fail later:

```text
Parameters.BaseAddress = "bad"
AddressExpr0 -> Error_ExpressionEval
RegExpr0 -> Error_ExpressionEval
```

Validate generated address UDTs with all of these reads:

```text
[Provider]Area/Asset/Parameters.BaseAddress
[Provider]Area/Asset/AddressExpr0
[Provider]Area/Asset/RegExpr0
[Provider]Area/Source/DataPoint098
```

Predefined UDT parameters are useful for labels and navigation metadata:

```text
{InstanceName}
{TagName}
{PathToTag}
{PathToParentFolder}
{RootInstanceName}
```

For nested UDTs, read the exact predefined parameter outputs before relying on them. Nested expression-member semantics can be surprising: `{InstanceName}` may return the child instance name, `{RootInstanceName}` should be checked for the top-level UDT instance, and `{ParentInstanceName}` may not be the containing top instance in every context.


## Nested UDTs

A parent UDT can contain child UDT instances. The surprising API edge is parameter pass-through: raw `tagConfigure` child parameters such as `"{MeterAClass}"` can read back as the literal string rather than resolving to the parent parameter.

Safer API workflow:

1. Create the core child UDT type.
2. Create the parent UDT type.
3. Create the parent UDT instance.
4. Configure nested child instance parameters explicitly under the parent instance path with collision policy `"m"`.
5. Read `Parent/Child/Parameters.ParamName` and expression outputs before binding pages or scripts.

Example targeted child parameter update:

```json
{
  "action": "tagConfigure",
  "basePath": "[Provider]Area/Assets/Skid001",
  "allowedTagPathPrefixes": ["[Provider]Area/Assets/Skid001"],
  "collisionPolicy": "m",
  "dryRun": true,
  "tags": [
    {
      "name": "MeterA",
      "tagType": "UdtInstance",
      "typeId": "Area/MeterCore",
      "parameters": {"VoltageClass": "480", "HighLimit": 480.0}
    }
  ]
}
```

Verify:

```text
[Provider]Area/Assets/Skid001/MeterA/Parameters.VoltageClass
[Provider]Area/Assets/Skid001/MeterA/HighAlarmExpr
[Provider]Area/Assets/Skid001/AnyHighExplicit
```

## Command And Interlock Modules

For reusable command panels, separate command intent, status, permissives, bypasses, and aggregate decisions:

- Put each repeated permissive/interlock bit in a small child UDT with stable members such as `State`, `Bypass`, `Healthy`, and `Attention`.
- Put fixed aggregate decisions on the parent equipment UDT as expression tags such as `PermissivesOK`, `CanStart`, `StartAccepted`, `StartRejected`, and `InterlockActive`.
- Use fixed child member paths in parent expressions when the number of children is known. If the number of children varies, build the aggregate in a script or page model instead of trying to browse from an expression tag.
- Treat bypass as satisfying command logic only when intentional, and keep a separate visible attention flag so bypassed permissives are not hidden from operators.

Child permissive UDT shape:

```json
{
  "name": "PermissiveBit",
  "tagType": "UdtType",
  "parameters": {"Code": {"dataType": "String", "value": "PERM"}, "Label": {"dataType": "String", "value": "Permissive"}, "RequiredState": true},
  "tags": [
    {"name": "State", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": false},
    {"name": "Bypass", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": false},
    {"name": "Healthy", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "{[.]Bypass} || ({[.]State} = {RequiredState})"},
    {"name": "Attention", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "{[.]Bypass} || ({[.]Healthy} = false)"}
  ]
}
```

Parent aggregate expressions:

```text
PermissivesOK:
{[.]Permissives/SuctionValveOpen/Healthy} && {[.]Permissives/DischargeValveOpen/Healthy} && {[.]Permissives/TankLevelOK/Healthy}

CanStart:
{[.]AutoMode} && ({[.]Faulted} = false) && {[.]PermissivesOK}

StartRejected:
{[.]StartCmd} && ({[.]CanStart} = false)
```

When a parent UDT embeds child UDT instances, do not trust child parameters like `"{SuctionLabel}"` until readback confirms they resolved. The safe API sequence is:

1. Create the child UDT type.
2. Create the parent UDT type with fixed child UDT instance names.
3. Create parent UDT instances.
4. Patch each nested child UDT instance's parameters under the parent instance path with `collisionPolicy: "m"`.
5. Write scenario values and read child `State`/`Bypass`/`Healthy`/`Attention` plus parent aggregate expressions.

For Perspective command/status tables, build rows by batch-reading parent metadata and aggregate expressions plus selected child health/bypass members:

```text
[Provider]Area/PMP-101/Parameters.AssetName
[Provider]Area/PMP-101/CanStart
[Provider]Area/PMP-101/StartRejected
[Provider]Area/PMP-101/InterlockActive
[Provider]Area/PMP-101/Permissives/DischargeValveOpen/Healthy
[Provider]Area/PMP-101/Permissives/DischargeValveOpen/Bypass
```


## Tag Event Scripts In UDTs

Inside a UDT tag event script, use the modern parameter dictionary and cast values before math:

```python
if initialChange:
    return
asset = str(tag["parameters"]["AssetName"])
scale = float(tag["parameters"]["Scale"])
value = float(currentValue.value)
system.tag.writeBlocking(["[.]LastAsset", "[.]LastComputed"], [asset, value * scale])
```

Avoid:

```python
asset = "{AssetName}"
message = "Value {0}".format(currentValue.value)
```

UDT parameter expansion and Python `.format(...)` placeholders can collide. Prefer `%` formatting, concatenation, or a Project Library helper. When validating merged instance parameter updates, confirm later events see updated `tag["parameters"]` values by using result/status tags plus `Parameters.ParamName` reads.





## Instrument Faceplate Contracts

For analog/digital instrument faceplates, put common row/detail metadata and status flags on a base UDT, then put process-value members on concrete derived types.

Base members should stay safe for every instrument row:

```json
{
  "name": "InstrumentBase",
  "tagType": "UdtType",
  "parameters": {
    "AssetName": {"dataType": "String", "value": "INST-001"},
    "DisplayName": {"dataType": "String", "value": "Instrument"},
    "InstrumentType": {"dataType": "String", "value": "instrument"},
    "DetailViewKey": {"dataType": "String", "value": "instrument-base"},
    "SortOrder": {"dataType": "Integer", "value": 100},
    "Units": {"dataType": "String", "value": ""}
  },
  "tags": [
    {"name": "Faulted", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": false},
    {"name": "MaintenanceMode", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": false},
    {"name": "Bypass", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": false},
    {"name": "SignalGood", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": true},
    {"name": "Attention", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "{[.]Faulted} || ({[.]SignalGood}=false) || {[.]MaintenanceMode} || {[.]Bypass}"}
  ]
}
```

Analog derived types should keep computed values and quality/status helpers together:

```json
{
  "name": "AnalogInstrument",
  "tagType": "UdtType",
  "typeId": "Area/InstrumentBase",
  "parameters": {
    "InstrumentType": {"dataType": "String", "value": "analog"},
    "DetailViewKey": {"dataType": "String", "value": "instrument-analog"},
    "LowLimit": {"dataType": "Float", "value": 0.0},
    "HighLimit": {"dataType": "Float", "value": 100.0},
    "Scale": {"dataType": "Float", "value": 1.0},
    "Offset": {"dataType": "Float", "value": 0.0}
  },
  "tags": [
    {"name": "Raw", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float8", "value": 0.0},
    {"name": "PV", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Float8", "expression": "({[.]Raw} * {Scale}) + {Offset}"},
    {"name": "PVGood", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "isGood({[.]PV})"},
    {"name": "PVBadOrError", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "isBadOrError({[.]PV})"},
    {"name": "RangeBad", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "try(({[.]PV} < {LowLimit}) || ({[.]PV} > {HighLimit}), true)"}
  ]
}
```

A bad string override such as `Scale = "bad"` can configure successfully but make `PV` read `Error_ExpressionEval`. `PVGood` can be false while `PVBad` stays false; use `PVBadOrError` for error-quality guards. For faceplates, suppress the displayed value unless the value quality is good and carry a status such as `Calc Error`.

Digital derived types can parameterize state semantics:

```json
{
  "name": "DigitalInstrument",
  "tagType": "UdtType",
  "typeId": "Area/InstrumentBase",
  "parameters": {
    "InstrumentType": {"dataType": "String", "value": "digital"},
    "DetailViewKey": {"dataType": "String", "value": "instrument-digital"},
    "AlarmState": true,
    "StateLabelTrue": {"dataType": "String", "value": "On"},
    "StateLabelFalse": {"dataType": "String", "value": "Off"}
  },
  "tags": [
    {"name": "State", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": false},
    {"name": "InAlarm", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "{[.]State} = {AlarmState}"},
    {"name": "StateText", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "String", "expression": "if({[.]State}, {StateLabelTrue}, {StateLabelFalse})"}
  ]
}
```

Build rows by browsing concrete analog and digital `typeId` values separately. Read common base members for every row and analog/digital-only members only for the matching type. An unguarded read such as `DigitalSwitch/PV` should be treated as bad/not-found evidence, not a reason to add fake members to every type.

When updating engineering limits, edit the derived type default with collision policy `"m"` and verify both a non-overridden instance and an explicitly overridden instance:

```text
[Provider]Area/AIT-100/Parameters.HighLimit
[Provider]Area/AIT-100/RangeBad
[Provider]Area/AIT-101/Parameters.HighLimit
[Provider]Area/AIT-101/RangeBad
```

Non-overridden instances inherit the new default. Explicit instance overrides remain unchanged.


## Variant Equipment Families

Use inheritance for equipment families when a base UDT can provide stable Perspective-facing members and metadata, while derived types add only real variant members.

Base UDT examples:

```json
{
  "name": "PumpFamilyBase",
  "tagType": "UdtType",
  "parameters": {
    "AssetName": {"dataType": "String", "value": "PMP-001"},
    "EquipmentType": {"dataType": "String", "value": "pump"},
    "Variant": {"dataType": "String", "value": "fixed-speed"},
    "DetailViewKey": {"dataType": "String", "value": "pump-basic"},
    "NominalFlow": {"dataType": "Float", "value": 100.0}
  },
  "tags": [
    {"name": "PV", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float8", "value": 0.0},
    {"name": "Running", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": false},
    {"name": "Faulted", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": false},
    {"name": "HighFlow", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "{[.]PV} > {NominalFlow}"}
  ]
}
```

Derived variants add their own members and may override base parameter defaults:

```json
{
  "name": "PumpFamilyVFD",
  "tagType": "UdtType",
  "typeId": "Area/PumpFamilyBase",
  "parameters": {
    "Variant": {"dataType": "String", "value": "vfd"},
    "DetailViewKey": {"dataType": "String", "value": "pump-vfd"},
    "NominalFlow": {"dataType": "Float", "value": 150.0}
  },
  "tags": [
    {"name": "SpeedHz", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float8", "value": 0.0},
    {"name": "SpeedHigh", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "{[.]SpeedHz} > {SpeedHighLimit}"}
  ]
}
```

Discovery should browse every concrete type:

```python
for type_id in ["Area/PumpFamilyBase", "Area/PumpFamilyVFD", "Area/PumpFamilyDosing"]:
    system.tag.browse(root, {"recursive": True, "tagType": "UdtInstance", "typeId": type_id})
```

A base-type browse can find only direct base instances; derived variants can require concrete derived `typeId` browses. A base parameter default update can propagate to derived types that did not override it, while derived type defaults and explicit instance overrides remain unchanged.

For Perspective rows, read common base members for every instance and variant-only members only for the concrete type that declares them. An unguarded read such as `BasePump/SpeedHz` can return bad/not-found quality. Include `variant` or `detailViewKey` with `tagPath` and `typeId` in detail params.

## Copy, Derive, And Update UDT Types

For inherited UDT definitions, create the parent type first, then create the child `UdtType` with a relative parent `typeId`:

```json
{
  "name": "PumpWithRuntime",
  "tagType": "UdtType",
  "typeId": "Area/PumpBase",
  "parameters": {"RuntimeLimit": {"dataType": "Float8", "value": 10.0}},
  "tags": [
    {"name": "RuntimeHours", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float8", "value": 0.0}
  ]
}
```

For targeted updates to an existing type, use the parent `_types_` folder as `basePath` and the type name in the payload:

```json
{
  "action": "tagConfigure",
  "basePath": "[Provider]_types_/Area",
  "collisionPolicy": "m",
  "tags": [
    {
      "name": "PumpBase",
      "tagType": "UdtType",
      "parameters": {"HighLimit": {"dataType": "Float8", "value": 80.0}},
      "tags": [
        {"name": "MaintenanceDue", "tagType": "AtomicTag", "valueSource": "expr", "dataType": "Boolean", "expression": "{[.]PV} > {MaintenanceLimit}"}
      ]
    }
  ]
}
```

Do not set `basePath` to the type itself when editing the type; a dry-run will plan a nested path like `[Provider]_types_/Area/PumpBase/PumpBase`.

Use `collisionPolicy: "m"` for partial edits. A partial `"o"` overwrite on a sacrificial type can remove omitted members from the type and instance. Use `"o"` only when intentionally replacing the full type payload.

When changing a definition parameter default, test both cases:

```text
[Provider]Area/Assets/PumpDefault/Parameters.HighLimit
[Provider]Area/Assets/PumpDefault/High
[Provider]Area/Assets/PumpOverride/Parameters.HighLimit
[Provider]Area/Assets/PumpOverride/High
```

Instances without an override inherit the new default. Instances with explicit parameter overrides keep their override. A cloned type built from a fresh minimal config stays independent from later base type changes.

## Discovery

To discover instances of one type:

```python
results = system.tag.browse("[Provider]Area", {
    "recursive": True,
    "tagType": "UdtInstance",
    "typeId": "Area/PumpCore"
})
```

Use `tagType` with `typeId`. A recursive `typeId` filter alone can return folders and atomic member tags, so do not feed typeId-only browse results directly into Perspective tables.

For multiple equipment classes, run one browse per relative `typeId` and merge by `fullPath`. Do not express OR logic by repeating `typeId` keys in one Jython/Python dictionary; only the last key survives.

Build Perspective-facing row models by batch-reading parameters and stable members after discovery:

```python
pump_rows = system.tag.browse("[Provider]Area", {"recursive": True, "tagType": "UdtInstance", "typeId": "Area/PumpCore"})
valve_rows = system.tag.browse("[Provider]Area", {"recursive": True, "tagType": "UdtInstance", "typeId": "Area/ValveCore"})
paths = sorted(set([str(row["fullPath"]) for row in list(pump_rows.getResults()) + list(valve_rows.getResults())]))
read_paths = []
for path in paths:
    read_paths.extend([
        path + "/Parameters.AssetName",
        path + "/Parameters.DisplayName",
        path + "/Parameters.Area",
        path + "/Parameters.EquipmentType",
        path + "/Parameters.SortOrder",
        path + "/Status",
        path + "/PV",
    ])
values = system.tag.readBlocking(read_paths)
```

Use dot-style `Parameters.ParamName` paths as the canonical read shape for generated row models. Include `tagPath` and `typeId` in each row so detail pages, embedded views, and navigation params do not have to rediscover the instance.

To filter by status, alarm, mode, or other member values, read member paths after discovery and filter the row model.

## Readback Rules

Read parameter and member paths directly:

```text
[Provider]Area/Assets/PMP-001/Parameters.AssetName
[Provider]Area/Assets/PMP-001/PV
[Provider]Area/Assets/PMP-001/High
```

UDT root reads can return a document-style child snapshot. Folder reads can return unsupported. Neither replaces member-level validation.

## Alarm Modeling

For common equipment alarms, define the alarm on the atomic source member inside the UDT and verify runtime alarm paths:

```json
{
  "name": "PV",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "Float8",
  "value": 0.0,
  "alarms": [
    {
      "name": "HighPV",
      "mode": "AboveValue",
      "setpointA": 80.0,
      "priority": "High",
      "displayPath": "{DisplayPath}",
      "enabled": "{HighEnabled}"
    }
  ]
}
```

Plain string UDT parameters can work for alarm `displayPath` and `enabled`, but validate the target Gateway before relying on them. Numeric alarm properties such as `setpointA` may not accept `"{HighLimit}"` or `{"bindType": "parameter", "binding": "{HighLimit}"}` through runner `tagConfigure`; on runner `0.3.111+` this should return top-level `ok: false` with `TAG_CONFIGURE_BAD_QUALITY`, while older runners could return HTTP/`ok: true` with `allGood: false` and a bad QualityCode that prevented type creation.


String metadata parameters can also drive display-oriented fields when runtime/status readback confirms the shape:

```json
{
  "name": "HighPV",
  "mode": "AboveValue",
  "setpointA": 80.0,
  "priority": "High",
  "displayPath": "{DisplayPath}",
  "enabled": true,
  "label": "{AlarmLabel}",
  "notes": "{AlarmNotes}"
}
```

Do not parameterize alarm priority in generated UDTs:

```json
{"priority": "{AlarmPriority}"}
```

In local API tests, that shape fired the alarm but runtime `Priority` read null and current alarm status fell back to Low even when the instance parameter was `Critical`. Use concrete priority values on the type or merge a concrete per-instance override.

For per-instance priority/display/label overrides, merge concrete alarm metadata before the member value activates the alarm:

```json
{
  "action": "tagConfigure",
  "basePath": "[Provider]Area/Assets/PMP-001",
  "collisionPolicy": "m",
  "tags": [
    {
      "name": "PV",
      "tagType": "AtomicTag",
      "alarms": [
        {
          "name": "HighPV",
          "mode": "AboveValue",
          "setpointA": 80.0,
          "priority": "Critical",
          "enabled": true,
          "displayPath": "Area/PMP-001/PV",
          "label": "PMP-001 Critical High"
        }
      ]
    }
  ]
}
```

For per-instance numeric setpoints, use a two-step member merge:

```json
{
  "action": "tagConfigure",
  "basePath": "[Provider]Area/Assets/PMP-001",
  "collisionPolicy": "m",
  "tags": [
    {
      "name": "PV",
      "tagType": "AtomicTag",
      "alarms": [
        {"name": "HighPV", "mode": "AboveValue", "setpointA": 150.0, "enabled": true, "displayPath": "Area/PMP-001/PV"}
      ]
    }
  ]
}
```

Then merge the member value in a second `tagConfigure` call. If the alarm config and activating PV value change in the same write, current alarm status can capture the old/type-default display path even though runtime alarm properties later read correctly.

Late alarm metadata overrides have the same snapshot behavior: runtime `Priority`, `DisplayPath`, and `Label` can update after the alarm is already active, but the current active alarm status row can keep the activation-time display path and priority.

Validate:

```text
[Provider]Area/Assets/PMP-001/PV/Alarms/HighPV.IsActive
[Provider]Area/Assets/PMP-001/PV/Alarms/HighPV.DisplayPath
[Provider]Area/Assets/PMP-001/PV/Alarms/HighPV.SetpointA
[Provider]Area/Assets/PMP-001/PV/Alarms/HighPV.Enabled
[Provider]Area/Assets/PMP-001/PV/Alarms/HighPV.Priority
[Provider]Area/Assets/PMP-001/PV/Alarms/HighPV.Label
```

Treat enabled parameters as shape-sensitive: a simple `{HighEnabled}` alarm worked in one test, while a metadata-heavy generated shape read the true parameter but kept runtime `Enabled` false. Always read runtime `Enabled`, `IsActive`, and current alarm status rows.

Also query current alarm status with the same provider/display/source filters a Perspective Alarm Status Table will use. Keep current alarm status and alarm journal/history separate; historical alarm views require a configured alarm journal/profile.

For UDT-backed alarm area rollups, keep `DisplayPath` stable enough to filter by area and asset, for example `<root>/<area>/<asset>`. Validate the runtime `PV/Alarms/<Name>.DisplayPath` reads, the per-area `alarmStatusQuery` row counts, the parent overview rows, and the browser-visible reusable detail params in the same run before promoting the pattern.
