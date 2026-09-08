# Vision Failure and Recovery

Inject only one controlled failure at a time. Capture the baseline resource,
value, quality, signature, request identity, session, and relevant log window
before the fault. Define the expected visible Client state and the
authoritative recovery proof before starting.

## Required failure classes

Exercise bad tag quality, database and historian unavailability, a missing
image or template, a script exception, Client network loss, expired
authentication, project conflict, lost API response, stale signature, scan
lock, and Gateway restart separately. Do not combine faults until each one has
an independently proven recovery path.

For every case:

1. Prove the expected failure is visible and bounded.
2. Record the exact request, target, source signature, and action interval.
3. Inspect the complete correlated Client and Gateway diagnostic window.
4. Run the predefined recovery or stop procedure.
5. Read back the authoritative final state and its signature or hash.
6. Confirm temporary state is absent and unrelated resources are unchanged.

## Reconcile before retry

When a write response is lost or times out, do not repeat the request merely
because the caller did not receive success. Read back the exact target and
correlate the request ID, expected payload, signature, and audit/log interval.

- If readback proves the request committed exactly once, accept it and suppress
  retry.
- If readback proves the old state and the operation is safe and idempotent,
  rebuild from the current signature before a bounded retry.
- If readback shows another state, stop for an explicit merge or rollback.
- If readback or correlated logs are incomplete, treat the final state as
  ambiguous and do not retry the write.

Never overwrite a project conflict or stale signature silently. Preserve the
other actor's state, export/read back the current resource, and require an
explicit merge or rollback decision.

## Require explicit evidence completeness

Every mutation helper must accept or generate one stable request ID and return
an explicit completeness contract. Include:

- `responseComplete` and `logsComplete` Booleans;
- `truncated`, returned count, total count, and a bounded continuation cursor
  when evidence is paged or capped;
- the source signature, desired signature, and authoritative final signature;
- the server-side accepted request identity when available;
- mutation count or duplicate-suppression disposition;
- a final disposition such as accepted, retried, already-current, stopped, or
  ambiguous.

Never infer that an omitted completeness field means complete. Continue
read-only pagination to collect truncated evidence, but do not repeat a write
to obtain a larger response. An HTTP success code, message `SENT` status,
partial logs, or a missing caller response cannot independently prove that a
mutation committed.

If a timeout is proven to have occurred before commit and readback proves the
old state, a bounded retry must reuse the same request ID. If readback proves
the target payload is already current—even under a different request
identity—return already-current without writing again. If readback, audit, or
the correlated log window is unavailable, preserve the request ID and stop.

## Recovery evidence

A cleared error banner is not proof of recovery. Require fresh values and
qualities, restored resource identities, final hashes, Client interaction,
and clean correlated logs. After a Client disconnect, perform a full state
refresh before another action. After authentication recovery, do not replay
queued writes. After a Gateway restart, wait for the service and project to be
ready, then verify persisted resources and launch a fresh owned Client.

An expected failure log is acceptable only when it matches the injected fault
and no additional unexplained signal exists. Missing, truncated, or
uncorrelated logs are an observability gap and block a clean recovery claim.

## Qualify restart and cache independence

Do not promote behavior observed only in one long-lived Designer or Client
session. A restart/cache qualification needs independent evidence rather than
an unchanged screen:

- capture the authoritative resource hash and fixed runtime-value/quality
  manifest before and after restart;
- prove a new Gateway boot generation when the claim includes restart;
- use fresh isolated launcher profiles and independently launched Clients A
  and B;
- record each Client/profile identity without treating the identifier itself
  as a value that must remain equal;
- compare screenshots at a fixed size together with resource and runtime
  hashes;
- inspect complete correlated startup, action, and settle logs for every
  generation and Client; and
- produce a field-level difference report that explains every accepted delta.

Reject qualification when a stale launcher artifact differs from authoritative
resource state, client B cannot reproduce client A, behavior changes when the
Designer is closed, the boot generation did not change, or any required log
window is incomplete. Matching screenshots alone do not prove restart safety
or cache independence.
