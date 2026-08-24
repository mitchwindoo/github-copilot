# Acknowledgement, Shelving, And Service Security

Use this reference when ack, notes, clear, shelving, UI permissions, Gateway script authority, or remote Gateway service permissions are central to the issue.

## Acknowledgement

- Identify the current EventId before acknowledging; friendly labels are not enough.
- Treat EventId as the acknowledgement boundary. Do not use source path or display path as a substitute when retrying, batching, or handling a later event from the same source.
- Preserve the configured ack mode before reasoning about acknowledged dropout or pipeline entry.
- Manual, Auto, and Unused ack modes can produce different status and journal shapes.
- For notes-required alarms, keep omitted notes, null notes, empty notes, and non-empty notes as separate cases.
- Record returned errors or failed-ID lists and query the follow-up state before retrying. In batch acknowledgement, a failed list can coexist with successful state changes for other IDs.
- For duplicate or stale acknowledgement retries, confirm whether the returned failed IDs match the old EventIds and then re-query the current event by its own EventId.
- Treat client UI acknowledgement, Gateway-scope scripting, and notification-channel acknowledgement as separate surfaces until proven on the target.

## Clear And Dropout

- Clear state can stop, continue, or enter a different pipeline depending on assignment and dropout rules.
- Compare active, clear, and ack transitions by EventId and source path.
- If a clear notification is expected, prove the clear pipeline assignment and the message data used at clear time.

## Shelving

- Confirm the alarm's configured shelving policy, but do not treat that policy as proof for every execution path.
- Check actor, execution scope, permission path, shelved-path inventory, normal status, and status with shelved events included.
- Client Alarm Status Table availability, Gateway scripts, and remote service permissions can differ.
- Record requested timeout and observed expiration when shelving matters. Short shelves can expire back into normal status while the alarm condition remains active, and re-shelving can update the existing expiration.
- Treat timeout-zero and explicit unshelve as mutation paths that need follow-up status and shelved-path checks.
- Prefer qualified source paths for unambiguous mutation proof. Display paths may work on some targets, but source paths from current status or journal evidence are easier to correlate.
- Use wildcard-style shelving only after proving the affected path set; broad patterns can shelve more than one alarm.
- Clear-unacknowledged events can still be affected by source-level shelving, so check both normal and shelved-included status when a cleared event appears to disappear.
- Treat unshelve behavior as a new proof point; do not assume unshelving creates a new notification entry.

## Gateway Network And Service Security

For remote alarm work, collect a read-only preflight first:

- Owning Gateway and visible remote peers.
- Security zones that apply to the remote path.
- Alarm status service permission.
- Detailed acknowledge and shelving permission settings when exposed.
- Alarm Notification module placement and remote notification profile visibility.
- Whether the topology actually contains more than one Gateway.

Do not assume a Gateway that can display an alarm can acknowledge or shelve it. Do not test remote mutation until the user names the topology and safe target.
