# Import and runtime failure modes

The official tag-import route frequently accepts malformed semantics. Local validation and runtime readback are mandatory.

## Verified single-fault matrix

| Fault | Import result | Persisted/runtime result |
|---|---|---|
| malformed JSON | HTTP 200, zero success, one failure | diagnostic contained JSON EOF location |
| array at document root | HTTP 200, zero success, one failure | diagnostic reported `Not a JSON Object`; wrap siblings in one `Folder.tags` object |
| missing root name | HTTP 200, zero success, zero failure | ambiguous no-op envelope; reject locally |
| UdtInstance missing `typeId` | success 1 | persisted as a type-less `UdtInstance`; root read returned Good empty document |
| duplicate sibling name | success 1 | only one sibling persisted; the later value won |
| unknown root property | success 1 | property persisted and was readable as a custom tag property |
| invalid `valueSource` | success 1 | value source persisted; member runtime quality was `Error_Configuration` |
| invalid `dataType` | HTTP 200, zero success, one failure | diagnostic named the invalid enum |
| invalid alarm mode | success 1 | mode was omitted/null with Good property quality; alarm stayed inactive |
| invalid event ID | success 1 | unknown event ID and script text persisted; execution was not established |
| invalid expression syntax | success | dependent member read with error quality |
| member-style alarm binding object (`parameter`/`binding`) | success | wrong schema; alarm could disappear from runtime paths |
| alarm `Expression` object using `binding` instead of `value` | success | normalized to an empty expression and remained Good/inactive |
| plain string `activeCondition` tag reference | success | normalized to static false and remained Good/inactive |

## Required response checks

Do not use `successCount == 0 && failureCount == 0` as proof of a safe no-op. Treat it as ambiguous and export/inventory. Likewise, `successCount == 1` means only that an object was persisted—not that it is usable.

## Required local checks

Before import, reject:

- invalid JSON;
- any document root that is not one JSON object;
- missing/invalid names and tag types;
- a UDT instance without a nonempty relative `typeId`;
- duplicate sibling names;
- unknown `valueSource` values;
- invalid Ignition 8.3 JSON data-type names;
- unsupported event IDs.

Unknown properties are not universally invalid because Ignition preserves custom tag properties. Maintain an explicit property policy per project: allow approved custom keys and flag unexpected keys for review.

Alarm modes and other property enums still need exact runtime/export verification because the basic preflight intentionally does not claim a complete schema for every tag extension and module.

## Readback after accepted faults

For every accepted import:

1. Export the exact object.
2. Compare sibling count and names; duplicate inputs may collapse.
3. Read the UDT root and every created member.
4. Read runtime properties for alarms, references, expressions, value source, and data type.
5. Reject null enum properties or any non-Good member quality.
6. Do not retry an ambiguous result until inventory establishes actual state.
7. For multi-tag writes, inventory every item and its UDT-side evidence independently. A failed batch may have committed a valid subset; retrying the entire batch can duplicate non-idempotent work.
