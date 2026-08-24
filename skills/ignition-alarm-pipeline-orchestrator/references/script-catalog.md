# Customer Script Catalog

Use this reference before running the bundled notification safety gate or when its Python runtime is unavailable.

## Notification Safety Gate

Script: `scripts/notification_safety_gate.py`

Purpose: inspect a proposed alarm-notification JSON plan before any email, SMS, voice, phone, webhook, HTTP, or remote-Gateway path is used. The script does not contact Ignition, make network calls, send notifications, or mutate Gateway resources.

Runtime: Python 3.9 or newer, using only the Python standard library.

Invocation:

```text
python scripts/notification_safety_gate.py <plan.json>
python scripts/notification_safety_gate.py <plan.json> --out <result.json>
```

The optional `--out` argument writes the same classified and redacted result that the script prints. Without `--out`, the script writes no files.

## Input Fields

Provide a JSON object. The safety gate recognizes:

- Channel selection: `channel`, `channels`, `profileType`, `profileTypes`, or entries under `notificationProfiles`.
- Send intent: `sendMode`, `mode`, or `intent`.
- Sandbox approval: `sandboxApproved` and a non-empty `sandboxTarget`.
- Live approval: `liveSendApproved` and a non-empty `approvalRef`.
- Recipients and endpoints: strings anywhere in the plan are scanned for real-looking email addresses, phone numbers, URLs, hostnames, bearer values, and sensitive keys.

Deployment-specific fields may be added as needed. Keep secrets and real credentials out of reusable plan files.

## Result And Exit Codes

The result contains:

- `ok`: whether no blockers were found.
- `blockers`: conditions that must stop the send or configuration action.
- `warnings`: bounded cautions that do not independently block the plan.
- `channels` and `externalChannels`: detected channel names.
- Counts of real-looking email, phone, and external URL values.
- `redactedPlan`: a sanitized copy for review or evidence.

Exit code `0` means the plan passed the gate. Exit code `2` means blockers remain. A passing result does not authorize a live send; it only confirms that the declared sandbox or live-approval fields satisfy the gate.

## Safety Requirements

- Stop when `ok` is false.
- Do not replace a named sandbox target with a production recipient.
- Require both `liveSendApproved` and `approvalRef` for a live external send.
- Review the redacted output rather than copying unredacted plans into reports or support material.
- Treat local sink acceptance, Ignition send attempts, and provider or carrier delivery as separate proof layers.

## Manual Fallback

When Python 3.9 or newer is unavailable, perform the same checks manually and report that the bundled gate was not executed:

1. List every external channel, recipient, endpoint, profile, and environment.
2. Require a named sandbox target or explicit live-send approval.
3. Require a concrete approval reference for every approved live send.
4. Reject real-looking recipients or external URLs without the corresponding approval.
5. Redact credentials, authorization values, private hosts, email addresses, phone numbers, and endpoint details before producing reusable output.
6. Stop before any external action if one of these facts is missing or contradictory.
