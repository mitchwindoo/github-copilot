# OPC members in UDTs

Use parameter binding objects for OPC properties. Plain strings containing `{Parameter}` are not bindings in imported JSON.

## Known-good parameterized member

```json
{
  "name": "PV",
  "tagType": "AtomicTag",
  "valueSource": "opc",
  "dataType": "Float8",
  "opcServer": {
    "bindType": "parameter",
    "binding": "{OpcServer}"
  },
  "opcItemPath": {
    "bindType": "parameter",
    "binding": "ns=1;s=[Device]Path/Value{Index}"
  }
}
```

Define `OpcServer` as a String parameter and `Index` using the intended scalar type. A binding may also reference a parameter containing the entire path:

```json
"opcItemPath": {"bindType": "parameter", "binding": "{OpcItemPath}"}
```

The verified target exported these objects unchanged and resolved instance overrides at runtime. Both OPC server and item-path binding objects worked.

## Forms that failed

- `"opcServer": "{OpcServer}"` treated the braces literally and returned `Error_Configuration` because that server name did not exist.
- `"opcItemPath": "{OpcItemPath}"` treated the braces literally and returned an OPC `Bad_NodeIdUnknown` diagnostic.
- Quoting the placeholder did not turn it into a binding.

Do not generalize expression/alarm placeholder behavior to OPC properties. Use the property-specific binding object.

## Instance overrides

Prefer changing UDT parameters. For an irregular device, a concrete member override also worked:

```json
{
  "name": "Pump-002",
  "tagType": "UdtInstance",
  "typeId": "Equipment/Pump",
  "tags": [
    {
      "name": "PV",
      "tagType": "AtomicTag",
      "valueSource": "opc",
      "dataType": "Float8",
      "opcServer": "Ignition OPC UA Server",
      "opcItemPath": "ns=1;s=[Device]Irregular/PV"
    }
  ]
}
```

Export the instance afterward and read the overridden member. Other bound members still follow their parameters.

## Runtime verification

OPC members can begin at `Uncertain_InitialValue`. Poll a bounded direct member read until it becomes Good or a deadline expires; the tested concrete member took about one second to settle. Preserve exact failures:

- missing server: `Error_Configuration` with the server name;
- missing node: OPC error containing `Bad_NodeIdUnknown`;
- valid subscription: Good value after settling.

For writes, require all three layers:

1. Good write quality;
2. the UDT member reads the requested value;
3. the source OPC value reads the requested value and is restored when testing.

Good write quality alone was insufficient on the tested sample device: both the UDT member and direct source tag immediately read the old value. Treat write-through as device-specific and unproven until post-read equality passes.
