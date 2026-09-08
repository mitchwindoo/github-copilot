# UDT and tag JSON patterns

## Minimal definition

```json
{
  "name": "PumpCore",
  "tagType": "UdtType",
  "parameters": {
    "AssetName": {"dataType": "String", "value": "PMP-DEFAULT"},
    "HighLimit": {"dataType": "Float", "value": 80.0}
  },
  "tags": [
    {
      "name": "PV",
      "tagType": "AtomicTag",
      "valueSource": "memory",
      "dataType": "Float8",
      "value": 0.0
    },
    {
      "name": "High",
      "tagType": "AtomicTag",
      "valueSource": "expr",
      "dataType": "Boolean",
      "expression": "{[.]PV} > {HighLimit}"
    }
  ]
}
```

Import definitions under `_types_/<folder>`. On the verified target, an AtomicTag `dataType` of `Integer` was rejected; `Int4` succeeded. Use the live tag data-type enum and direct negative tests rather than guessing aliases.

## Minimal instance

```json
{
  "name": "PMP-001",
  "tagType": "UdtInstance",
  "typeId": "Equipment/PumpCore",
  "parameters": {
    "AssetName": "PMP-001",
    "HighLimit": 10.0
  }
}
```

`typeId` is provider-relative and does not include `_types_`. Browse using `tagType: UdtInstance` plus the concrete relative `typeId`.

## Parameter rules

- Prefer typed definition parameters and scalar instance overrides.
- Preserve raw types in verification. On the verified target, Boolean parameter reads appeared as numeric `0`/`1`, while Boolean expressions still evaluated correctly.
- Do not pass numeric or Boolean values as strings. A string `"9"` used with `+ 1` produced `91`, not 10.
- Do not encode parameters as value-only objects. They produced null or truncated values on the verified target.
- Omitted, JSON `null`, literal string `"null"`, and empty string are distinct. Test dependent expressions for every supported nullability case.

## Expression and path rules

- Relative member: `{[.]PV}`
- Parameter: `{HighLimit}`
- Dynamic tag lookup: `tag({SourcePath})`
- Concatenated dynamic lookup: `tag({RootPath} + "/PV")`

Do not quote a parameter placeholder that must be evaluated. `"prefix-{Mode}"` and a missing `{Parameter}` remained literal text in verified cases. Invalid expression syntax can import successfully and fail later with error quality.

For indirect references, an expression using `tag({SourcePath})` worked. A Reference tag with `sourceTagPath: "{SourcePath}"` remained unresolved on the verified build. Prefer a proven static Reference or expression indirection and verify runtime quality.

## Nested UDTs

Nested child `parameters` set to strings such as `"{ParentName}"` stayed literal in the verified fixture. For dynamic parent-to-child propagation, use the explicitly typed binding wrapper proven in `nested-udt-composition.md`. Read every child parameter and dependent member after creation and after a controlled parent-parameter change.

## Inheritance

A derived UDT definition uses a relative `typeId` pointing to its base definition. Use the live data-type enum for new members. Browse base and derived concrete types separately: querying the base `typeId` did not return derived instances in the verified fixture.

`MergeOverwrite` changes to a base default propagated to non-overridden instances and new base members propagated to base and derived instances. Existing derived overrides remained. Verify all branches after every base change.

For exact base-to-derived-to-instance parameter, event-script, alarm, documentation, value, and nested Folder override shapes, read `inheritance-overrides.md`. In particular, reproduce the Folder ancestry as nested stubs and treat empty inherited export stubs as inheritance artifacts rather than full standalone member definitions.

## Targeted instance member override

```json
{
  "name": "PMP-001",
  "tagType": "UdtInstance",
  "typeId": "Equipment/PumpCore",
  "tags": [
    {"name": "PV", "tagType": "AtomicTag", "value": 20.0}
  ]
}
```

Use `MergeOverwrite` for a targeted patch. Export afterward and confirm no sibling overrides or members were introduced unexpectedly.

## Predefined expression values

Verified values included `InstanceName`, `TagName`, `PathToTag`, `PathToParentFolder`, `RootInstanceName`, and `ParentInstanceName`. In a nested child, `RootInstanceName` identified the root instance while `ParentInstanceName` identified the child instance itself. Test the exact nesting shape before using these values for identity.
