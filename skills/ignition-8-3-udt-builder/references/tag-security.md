# UDT member security

Use tag security when access must follow the tag everywhere it is consumed. `readOnly` is a Boolean. Conditional read and write access use `readPermissions` and `writePermissions` on the UDT member definition or as a member override under a `UdtInstance`.

## Canonical permission JSON

```json
{
  "name": "Command",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "Boolean",
  "readPermissions": {
    "type": "AnyOf",
    "securityLevels": [
      {
        "name": "Authenticated",
        "children": [
          {
            "name": "Roles",
            "children": [
              {"name": "Operator", "children": []}
            ]
          }
        ]
      }
    ]
  },
  "writePermissions": {
    "type": "AllOf",
    "securityLevels": [
      {"name": "API_RW", "children": []}
    ]
  }
}
```

`type` is exactly `AnyOf` or `AllOf`. `securityLevels` is always an array, including when it has one element. Each level is an object with `name` and an array-valued `children`; selected leaves use `children: []`. The tree path must match the target Gateway's current security-level hierarchy. Fetch `GET /data/api/v1/resources/singleton/ignition/security-levels` when the live OpenAPI exposes it, then verify every requested path against `config.securityLevels` before import.

Do not add an implicit `Public` node. For public access, omit the corresponding permission property. Do not use an empty `securityLevels` array as shorthand for Public.

### One-element array trap

The 8.3.8 import accepted a transport-successful UDT definition when PowerShell had unwrapped a one-element `securityLevels` array into an object, but it silently removed the permission during export. Preserve the array explicitly. In PowerShell, wrap function output at the call site:

```powershell
$levels = @(New-SecurityLevelTree)
```

Do not trust the import count. Export the exact UDT type and compare `type`, the complete tree, and every empty leaf array.

The tested Gateway also normalized lowercase `anyof` and `allof` to `AllOf`; the result was not an error. Reject casing mistakes locally. Arrays of path strings exported as empty trees, scalar/wrong-shape permissions disappeared, and an obsolete role/zone permission array disappeared. Unknown/deleted level names persisted, matching the Gateway behavior described for deleted configured levels, so persistence alone does not prove that a current principal can satisfy the rule.

## Instance member overrides

Override a member beneath the UDT instance with a partial child object:

```json
{
  "name": "Pump-001",
  "tagType": "UdtInstance",
  "typeId": "Equipment/Pump",
  "tags": [
    {
      "name": "Command",
      "tagType": "AtomicTag",
      "writePermissions": {
        "type": "AllOf",
        "securityLevels": [
          {"name": "API_RW", "children": []}
        ]
      }
    }
  ]
}
```

On the verified build, both a permission override and `readOnly: false` persisted under the instance while the type retained its original settings. Export the type and instance separately: inherited properties can be omitted from the instance export, while explicit overrides appear.

## What API-only evidence proves

Import/export proves configuration persistence, normalization, inheritance source, and explicit instance overrides. `CanRead` and `CanWrite` are evaluated for the caller's security context. Reads made inside a Gateway-scoped WebDev script returned `true` even for an unknown-level control and therefore do not prove Perspective/Vision/client authorization enforcement.

To claim enforcement, use a bounded API operation that genuinely evaluates the intended session or authenticated principal and verify both an allowed and denied principal. Do not add arbitrary principal impersonation to `llmImport.py`. If the live OpenAPI lacks a safe principal-scoped tag read/write operation, report enforcement as untested rather than extending the API merely to make the test pass.

`readOnly` is independent of conditional write permissions. A type-level `readOnly: true` exported correctly; an instance override of `readOnly: false` also exported and made the Gateway-scope `CanWrite` property true in the verified fixture.
