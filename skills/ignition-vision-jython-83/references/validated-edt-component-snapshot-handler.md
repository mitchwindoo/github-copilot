# Validated EDT Component Snapshot Handler

This pattern is validated only for Ignition 8.3.8, Jython 2.7.4, the
fixed `V83_SKILL_LAB` window, and the fixed
`vision-p03-t03-click` client message handler.

## Input and thread contract

The message resource is client scope, enabled, and `threadType: EDT`.
Accept only:

```python
{
    "command": "snapshot",
    "contractVersion": "vision-button-event-bridge-1.2.0",
    "requestId": "<non-empty text, at most 128 characters>"
}
```

Reject non-dictionaries, extra or missing keys, wrong fixed values, and
invalid request IDs before UI lookup.

## Bounded handler behavior

1. Resolve `system.vision.getWindow("00 Blank Startup")`.
2. Use its root container and direct `components` collection only.
3. Require exactly five direct children with exact fixed names.
4. Resolve `IncrementButton` and `ResultLabel` by fixed name.
5. Read fixed names, classes, bounds, text, parent identity, and
   `ResultLabel.clickCount`.
6. Require `clickCount` to be the primitive Int4-backed Python `int`.
7. Verify a fixed nonexistent name returns no component.
8. Build the fixed snapshot dictionary and encode it with
   `system.util.jsonEncode`.
9. Send one flat result envelope containing only `kind`, `requestId`,
   `snapshotContract`, and `snapshotJson` to the fixed Gateway result
   handler.

Derive a full Jython-exposed class name with:

```python
def class_name(value):
    return type(value).__module__ + "." + type(value).__name__
```

On the installed 8.3.8 runtime, calling
`value.getClass().getName()` from this handler selected an incompatible
Java overload and raised `TypeError`. Use the validated Jython type
metadata form for this fixed snapshot.

Keep the cross-scope envelope primitive. Do not send the nested snapshot
dictionary directly:

```python
system.util.sendMessage(
    "V83_SKILL_LAB",
    "vision-p09-t05-snapshot-result",
    {
        "kind": "snapshot",
        "requestId": request_id,
        "snapshotContract": (
            "vision-edt-component-snapshot-1.1.0"
        ),
        "snapshotJson": system.util.jsonEncode(snapshot),
    },
    "G",
)
```

The fixed Gateway handler validates the four-key envelope, limits
`snapshotJson` to 16 KiB, decodes it locally, reconstructs the nested
fixed result, re-encodes it, and writes only the fixed temporary String
tag. Error envelopes contain only a fixed failure stage and exception
type; do not return messages, traces, component values, or arbitrary
payload content.

## Installed JSON boolean rule

After `system.util.jsonDecode`, a JSON true value has exact Python type
`bool` but is not guaranteed to be the singleton `True`. Use:

```python
def exact_true(value):
    return type(value) is bool and bool(value)
```

This accepts the installed decoded Boolean and rejects numeric `1`.
Do not use `value is True` for decoded JSON.

## Evidence and limits

The credited fresh-client cycle verified execution on
`AWT-EventQueue-0`, five exact component names, expected
`PMIButton`/`PMILabel` classes, fixed bounds, integer `clickCount`
metadata, missing lookup absence, fixed-session dispatch, temporary-tag
cleanup, and exact project rollback. Separate same-client screenshots
proved `0 -> 1 -> 1` duplicate replay `-> 5`.

This is not permission for reflection, recursive traversal,
caller-selected windows/components/properties/methods, general payloads,
concurrent snapshots, Designer control, or remote UI automation.
