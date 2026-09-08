# Reusable UDT model patterns

## Nested command and interlock model

Use a small child UDT for each permissive with direct Boolean members:

```text
Healthy = State || Bypass
Attention = Bypass || !State
```

Nest fixed child instances beneath the command UDT and aggregate them with explicit relative paths:

```text
CanStart = AutoMode && !Faulted && Perm1/Healthy && Perm2/Healthy && Perm3/Healthy
StartAccepted = StartCmd && CanStart
StartRejected = StartCmd && !CanStart
AnyAttention = Perm1/Attention || Perm2/Attention || Perm3/Attention || Faulted || !AutoMode
```

The verified six-scenario matrix passed for healthy, unhealthy, bypassed, faulted, manual-mode, and recovered states. A bypass satisfied `Healthy` but always asserted `Attention`; never hide a bypass merely because it permits operation.

Use fixed child paths when the number of permissives is fixed. If the count is variable, model it separately rather than generating an expression that silently omits a child. Write all scenario inputs in one bounded batch, wait for expressions to settle, and read every child plus parent aggregate in one batch.

## Retry coordinator: command identity versus attempt identity

For recoverable parent-to-child fanout, do not use one tag as both the logical command ID and the delivery retry trigger. Give the parent separate `RequestedSequence` and `DispatchAttempt` Int4 tags. Give each child separate `RequestedSequence` and `AttemptTrigger`, then retain `LastAttempt`, `LastAppliedSequence`, applied/denied counts, decision, and marker.

The parent `DispatchAttempt.valueChanged` script must reject `attempt <= LastDispatchAttempt`. For a new attempt it writes the unchanged command sequence to each fixed child, then writes the new attempt trigger. Each child decides independently:

- reject an old delivery attempt;
- reject a command sequence it already applied;
- deny a current command while locally disabled, without advancing `LastAppliedSequence`;
- otherwise apply once and advance `LastAppliedSequence`.

This permits retrying command sequence 1 with attempt 2: a successful child rejects the duplicate while a previously disabled child can apply sequence 1 for the first time. A later attempt 3 is harmless for both. A parent expression should count children whose `LastAppliedSequence` equals the current `RequestedSequence`, and publish completion only when the required count is reached.

Do not use the retry attempt as business identity, advance `LastAppliedSequence` on denial, or assume parent/child callback log order. This is cooperative idempotency, not an atomic transaction. Use one authoritative parent dispatcher, exact child decisions, a parent attempt fence, completion evidence, Control-instance isolation, and bounded logs. Three live runs proved two commands, one disabled-child recovery, duplicate rejection, stale-parent rejection, and exactly one completion per command.

### Add a bounded retry budget and remediation latch

Derive from the coordinator rather than changing the proven base. Add a typed positive `MaxAttempts`, `LastBudgetSequence`, and `AttemptCountForCommand`. Reset the count to one when command identity changes; increment it only for a dispatched retry of the same command. While `RetryExhausted` is true, consume and record newer delivery attempts as `DENIED-EXHAUSTED` without reaching children.

Do not latch exhaustion inside the dispatch script because child event scripts settle asynchronously. Add `AttemptSettledCount`, then drive a `RetryEvaluationState` expression only when both child `LastAttempt` values equal the latest dispatched attempt, fewer than all children applied the command, the budget is reached, and exhaustion is not already latched. Its script must publish retained command/attempt/count context first, verify those writes, and only then set `RetryExhausted = true`.

Place `RecoveryResetTrigger` and its decision/counters in a nested Folder. Deny reset while any child remains disabled. After remediation, clear the attempt count and exhaustion latch; retry the same command with a newer delivery attempt. The previously successful child rejects the duplicate while the remediated child applies.

An alarm on `RetryExhausted` can expose the retained context as direct associated-data bindings. Guard `alarmCleared` callbacks with meaningful context such as `CommandSequence > 0`: on live 8.3.8, initial instance creation invoked clear callbacks with zero or `None` associated data before any exhaustion. Three corrected runs proved a two-attempt budget, alarm context, reset denial, dispatch denial, remediated recovery, and a clean next command.

### Add a timed retry backoff without consuming budget

Derive again and add a typed positive `RetryBackoffSeconds`, `BackoffArmed`, `NextRetryAllowedAt`, retained sequence/attempt context, and `BackoffOpenCount`. A delivery attempt received while armed should advance the parent attempt fence and record `DENIED-BACKOFF`, but must not fan out, increment `DispatchCount`, or consume `AttemptCountForCommand`. Open the window from a polling expression such as `{[.]BackoffArmed}&&now(250)>={[.]NextRetryAllowedAt}`; its callback clears the arm and deadline before logging the open marker.

Fence every inherited current-command evaluator with `RequestedSequence = LastBudgetSequence`. Publishing a new `RequestedSequence` changes child aggregates before the dispatch script resets the per-command budget; without this equality gate, stale counts from the prior command can latch exhaustion for the new one.

Expression dependencies can still expose brief intermediate combinations while sibling callbacks settle. Do not turn a transient `AppliedBranchCount < childCount` into durable backoff or exhaustion. Schedule a short asynchronous reconciliation, then re-read the expression state, command/budget equality, settled count, applied count, and latch before writing durable state. In Gateway scope, `system.util.invokeAsynchronous` is available on the verified build, but `system.util.sleep` is not; use Jython `time.sleep` inside the asynchronous function. Three corrected runs proved early denial without budget use, timed opening, same-command recovery, a clean next command, exactly 14 workflow markers, and zero ERROR-or-higher rows.

### Increase and cap backoff across failed deliveries

For capped exponential scheduling, add positive typed `BackoffMultiplier` and `MaxBackoffSeconds` parameters plus `BackoffLevel`, `CurrentBackoffSeconds`, and `LastBackoffSeconds`. On each newly settled incomplete delivery, increment the level and calculate `min(baseSeconds * multiplier^(level-1), maxSeconds)`. Retain the selected delay before arming. On confirmed command completion, asynchronously re-read the completed sequence and reset the level/current delay to zero; the next command then starts at the base delay.

Correlate each window to one delivery attempt. Require `BackoffAttempt != LastDispatchAttempt` in both the arm expression and its delayed reconciliation. Clearing `BackoffArmed` while the same attempt remains incomplete otherwise makes the expression true again and can continuously re-arm without another dispatch.

Read the arm expression itself and require Good quality before the scenario. An unsupported operator produced `Error_Configuration` with no matching Gateway ERROR row on the verified build. For pre-deadline assertions, use an immediate exact-marker barrier; a multi-sample stability wait can consume a short timer and observe the legitimate open event before the intended early-attempt step. Three corrected runs proved delays 3 then capped 5, early denials without budget use, success reset, next-command base delay, 27 exact markers, and zero ERROR-or-higher rows.

### Stagger retries across multiple instances

To avoid synchronized retries, derive again with nonnegative typed `JitterStepMillis` and per-instance `JitterSlot`. Calculate `jitterMillis = JitterStepMillis * JitterSlot` and `scheduledMillis = cappedBaseSeconds * 1000 + jitterMillis`; create the deadline with `system.date.addMillis`. Retain both `AppliedJitterMillis` and `ScheduledDelayMillis` so the schedule is observable without parsing Date serialization.

Use deterministic slots when reproducibility and fleet coordination matter. Assign unique slots within the intended retry cohort and bound the largest slot so total delay remains operationally acceptable. Do not infer staggering merely because imports or dispatch writes occurred sequentially. Prove it from a midpoint state—earlier instance open while the later instance remains armed—and exact open-marker timestamps. Repeat after success reset to show the stagger is policy, not leftover state.

Two live instances with 4,000 ms base delays and slots 0/1 at a 2,000 ms step opened in order twice per run. Across three runs, the measured separations were 2,007-2,257 ms; both instances denied early attempts without budget use, recovered independently, reset to level 0, returned to level 1 on the next command, and retained 32 exact rows with zero ERROR-or-higher rows.

### Guard duplicate jitter slots at the owning fleet

When several jittered coordinators are fixed children of one parent, bind each child's `JitterSlot` through an explicitly typed nested-parameter wrapper. Give the parent Good-quality slot-value and collision expressions. Reject fleet dispatch before child writes while collision is true, and consume the denied fleet attempt so replaying that attempt cannot dispatch after repair.

Put an `OnCondition` alarm on the collision and bind numeric slot values as associated data with the alarm `Expression`/`value` shape. Verify the exact source and requested properties through bounded current status. Repairing parent parameters must propagate into the children and clear the alarm before dispatch is allowed.

Keep fleet identity, attempt, and completion evidence separate from each child's evidence. A fleet `SENT` marker proves only that the parent attempted child writes; require each child's Good runtime state and completion. Batch cleanup below the guarded API's advertised `maxWrites`. Three clean two-child runs proved collision denial without fanout, typed slot propagation, 4,000/6,000 ms schedules, backoff denial, independent recovery, one fleet completion, Control isolation, exact alarm context, 28 dedicated rows, and zero ERROR+ per run.

### Freeze a participating roster per command

If participation may change while a command is being retried, do not recompute the completion cohort on every attempt. Encode the selected children in an Int4 bit mask, and retain `RosterSequence`, `RosterMask`, and `RosterGeneration` before the first fanout for a new command. When the same sequence is retried, reuse that mask even if the live participant mask changed. Select a new mask only for a new command identity.

Evaluate slot collisions among live participants before freezing a new roster. A duplicate slot belonging only to an excluded child is harmless; enabling that child makes the collision actionable. Once a roster exists, configuration changes need a separate policy—this tested pattern freezes participation, not arbitrary slot edits.

Write only selected child paths and branch explicitly when the live mask is zero. Author completion for every supported nonzero mask, and correlate child completion to `RosterSequence`. Keep the live mask observable so operators can distinguish current configuration from the frozen in-flight roster.

Three clean runs proved a mask-7 roster survived a live change to mask 3, still retried and completed Child C, then a new command selected mask 3 and excluded C. A later zero-participant command was denied without calling `writeBlocking([], [])`. The three child slots produced retained 4,000/6,000/8,000 ms schedules, adjacent open gaps of 1,997-2,016 ms, 59 exact dedicated rows, zero ERROR+, Control isolation, and full restoration per run.

### Guard selected-roster configuration drift

Freeze configuration that affects delivery semantics along with the roster. For slot-based staggering, retain one slot per selected child and a sentinel such as `-1` for excluded children. Before reusing a same-command roster, compare only selected children against current effective slot values. Deny before child fanout if any selected value changed; an excluded child's change must not block the roster.

For a small fixed mask, prefer an explicit `if` table covering masks 0-7. A compact implication-style Boolean expression normalized on the verified Gateway but produced `Error_Configuration` with zero ERROR logs. Runtime quality, not import success or an empty ERROR query, exposed the defect.

Publish `RosterConfigurationMatches`, a drift-state alarm, denial count, and exact frozen/current associated data. Snapshot the roster and selected slots before child fanout for a new command. Restoration of the selected configuration may clear the alarm and permit retry of the same roster; changing the policy instead requires an explicit cancel or new command identity.

Three clean derived-parent runs proved selected C and selected A changes denied fanout with exact High alarm context, restoration permitted same-command retry, and excluded C drift remained nonblocking. Each run retained 49 exact dedicated rows, zero ERROR+, 4,000/6,000/8,000 ms child schedules, Control isolation, and full restoration.

### Release a completed roster through a nested Folder

Separate roster release from dispatch. Put expected sequence/generation, trigger, counters, and decisions in a nested administration Folder. From `Fleet/RosterAdministration/ReleaseTrigger`, treat `tagPath` as text: remove `ReleaseTrigger` to reach the Folder, then remove `RosterAdministration` to reach the fleet. Do not call `tagPath.getParentPath()`.

Publish a Good-quality parent `RosterReleaseEligible` expression requiring a nonzero roster, parent completion for that exact roster sequence, no selected-configuration drift, and no armed child backoff. The Folder script must still re-read expected identity, actual identity, mask, and eligibility before acting.

Distinguish `DENIED-NO-ROSTER`, `DENIED-EXPECTED`, and `DENIED-INCOMPLETE`. On success, clear only the current request and roster snapshot; preserve `RosterGeneration`, parent completion history, and child execution history. This makes release a lifecycle boundary, not a recursive reset. Use a new command identity for later work.

Three clean runs released completed generation-1/mask-7 and generation-2/mask-3 rosters exactly once, denied four invalid requests, preserved child history, retained 49 exact dedicated rows, zero ERROR+, Control isolation, and full restoration. One stopped repeat also showed that an exact intermediate logger-count observer can be overtaken by legitimate timer events; synchronize with retained decision tags and require exact cardinality only at the final bounded query.

### Retain a bounded typed decision audit

Add a typed memory `DataSet` to the nested administration Folder when the UDT needs a small operator-visible decision history without a database. Define the full empty schema in import JSON. On each decision, require Good reads, append with `system.dataset.addRow`, trim the oldest rows with `system.dataset.deleteRow`, and write the Dataset plus `AuditRowCount` and `AuditEvictionCount` together. Reset with `system.dataset.clearDataset` so column metadata survives.

Treat capacity as a typed positive parameter. A run-specific logger parameter gives exact test cardinality without interference from inherited loggers. Verify through `tag-read-complex-v1`: exact Good quality, ten typed columns, ordered rows, Date cells as `dateTimeMillis`, `truncated: false`, and an untouched Control table.

Three clean runs generated six release decisions at capacity four. The final rows were `DENIED-EXPECTED`, `RELEASED`, `DENIED-NO-ROSTER`, and `RELEASED` for triggers 3-6; eviction count was two. Reset returned the table to zero rows while retaining schema. Each complete interval contained seven exact run-specific rows, zero ERROR+, zero active alarms, Control isolation, and restored state.

### Publish a latest-decision envelope beside audit history

Add a Document memory tag beside the bounded audit DataSet when downstream consumers need the latest structured state without scanning rows. Build both representations from one captured state and one `now_millis`; use a native Date in the DataSet and the same epoch integer in the Document. Include an explicit schema version, decision identity, expected and actual roster identity, decoded selected-slot array, counters, audit dimensions, and event time.

Write the Document, DataSet, and their evidence counters together, inspect every write quality, then read both complex values back and assert cross-consistency. Do not describe the batch as atomic. Reset the DataSet with `clearDataset` and independently replace the Document with a complete RESET envelope. Three clean API-only runs proved mask-7 and mask-3 arrays, exact final Document/DataSet field and timestamp agreement, Control isolation, seven exact run-specific rows, zero ERROR+, zero active alarms, and restoration.

### Acknowledge a versioned decision envelope

Compose a small acknowledger child UDT beside the producer Folder. Bind the parent fleet name, logger name, and accepted schema version into the child with typed parameter wrappers. From the child trigger, remove the member and child segments as text, then read the sibling `RosterAdministration/LastDecisionEnvelope` Document.

Require Good quality and classify in a stable order: schema mismatch, RESET/no envelope, stale expected epoch, expected-decision mismatch, duplicate last-accepted epoch, then accepted. Retain observed schema, epoch, decision, trigger, roster mask, decoded selected-slot count, and the last accepted identity. A Good trigger write is not an acknowledgement; require the decision/counters and exact logger marker.

Compile every event body with the target Jython jar before import. Three clean runs accepted two distinct envelope epochs, rejected no-envelope/stale/mismatch, counted one duplicate, isolated Control, reset producer and consumer independently, retained ten exact rows, and had zero ERROR+. The pattern is an in-memory application handshake, not durable delivery, authentication, transactional consumption, or exactly-once processing.

### Publish and verify an acknowledgement receipt

Extend the in-memory handshake with two sibling Folders on the parent UDT: `AcknowledgementReceipt` and `ReceiptVerification`. The publisher reads the producer envelope and retained acknowledger identity, requires Good quality and exact epoch/decision/trigger correlation, then writes a versioned Document containing a receipt sequence, producer identity, acknowledgement identity, and publication epoch. The verifier rereads both receipt and current producer envelope, rejects RESET/no receipt, schema mismatch, stale producer identity, and duplicate receipt sequence before recording VERIFIED.

Keep receipt publication, verification, acknowledgement, and producer reset independent and observable. Use exact script markers and bounded ERROR logs for each creation attempt. A clean three-run matrix produced two verified receipts, one pre-ack publish denial, one no-receipt denial, one duplicate, and one stale rejection per run with 16 exact focused rows and zero ERROR+.

Do not try to introduce `AcknowledgementReceipt` beneath an inherited nested `EnvelopeAcknowledgement` instance through an override; the Gateway rejects new children there. Place it as a sibling or revise the child UDT definition. When two producer envelopes can share the same decision string, wait for a monotonic write count or the exact new identity before accepting the Document read.

### Observe a verified receipt without mutating its producers

Compose a small observer child UDT beside the producer, receipt, and verifier subtrees. Bind fleet identity, logger name, and confirmation schema version as typed parameters. On an explicit observation trigger, read the verifier decision/count, receipt Document, current producer Document, and the observer's last confirmed receipt sequence. Require Good quality for every read.

Reject when verification is not currently VERIFIED, the receipt is absent, the receipt identity differs from the current producer, or the receipt sequence was already confirmed. On success, write a versioned confirmation Document containing observation sequence, receipt identity/publication epoch, producer identity, verifier evidence, and confirmation epoch. Do not write back into the producer, acknowledger, receipt, or verifier subtrees.

Three clean runs confirmed two receipt epochs, denied observation before verification, fenced one duplicate, denied retained prior verification after producer advance, reset all five planes independently, retained 19 exact logs, and had zero ERROR+. This remains an in-memory cooperative workflow, not durable delivery or a transaction.

### Journal admitted confirmations

Compose a separate journal child beside the observer. On an explicit trigger, read the observer confirmation, current producer envelope, bounded DataSet, last-journaled observation sequence, and counters. Admit only a current CONFIRMED identity that has not already been journaled. Append a typed row, apply oldest-row eviction to the configured capacity, and retain journaled/denied/duplicate/eviction counts plus the last admitted observation and receipt sequences.

Exercise capacity with more admitted confirmations than retained rows. A capacity-one matrix proved missing-confirmation denial, first append, duplicate rejection, stale denial after producer advance, second append, first-row eviction, exact typed Date cells, and schema-preserving reset. Keep this as bounded in-memory evidence, not durable audit or exactly-once storage.

### Fan one confirmation out to independent journal consumers

Instantiate the same journal child type twice when two consumers need identical admission logic but different retention policy. Bind shared fleet/logger parameters into both instances and bind distinct typed capacity parameters, such as one row for Operations and two rows for Compliance. Trigger and verify each consumer independently.

At the parent, calculate current-consumer count and all-current only by comparing each child's last journaled receipt sequence with the observer's current confirmed receipt sequence. Require the current sequence to be positive. This makes a new confirmation reset current completion to zero despite retained historical rows, then exposes partial and complete catch-up.

Three clean runs proved 0→1→2 progression twice, duplicate isolation, capacity-one eviction versus capacity-two retention, Good aggregate qualities, seven-plane reset, 22 exact logs, and zero ERROR+. This is independent in-memory fan-out, not transactional multicast or guaranteed delivery.

### Dispatch only stale journal consumers

Add a parent `JournalDispatch` Folder when the same confirmation must reach several independent child consumers. On an explicit trigger, read the current confirmation identity and each child's last-consumed identity together, require every QualifiedValue to be Good, and append a child trigger path only when that child's identity differs from the current identity. If there is no current confirmation, deny. If the target list is empty, report `ALREADY-CURRENT` and do not call `writeBlocking`.

For a nonempty list, write the trigger to only the selected child paths and check every returned quality. Retain `LastDecision`, dispatch/denial counts, selected target names/count, and the dispatched correlation identity. These values prove selection and write acceptance. They do not prove the child event scripts finished.

Prove completion later by reading every child's correlated last-consumed identity and a parent aggregate such as current-consumer count/all-current. Three clean API-only runs dispatched both journals for confirmation 1, performed an already-current no-op, and then dispatched only stale Compliance for confirmation 2 after Operations caught up independently. Each run retained 26 exact focused logs, zero ERROR+, zero alarms, Control isolation, and restored state.

### Observe dispatch completion separately

Add a sibling completion-observer Folder when dispatch acceptance and business completion must remain distinct. Read the dispatch decision, dispatched receipt identity, selected target names, current confirmation identity, every selected child's last-consumed identity, and local completion fence together. Require Good quality before classifying:

- `DENIED-NO-DISPATCH` when no accepted dispatch identity exists;
- `DENIED-STALE-DISPATCH` when the current confirmation advanced beyond it;
- `DUPLICATE` when that dispatch identity was already completed;
- `PENDING` with exact pending target names when any selected child is behind;
- `COMPLETED` only when every selected child matches the dispatched identity.

Do not reuse a child trigger value when the child relies on `valueChanged`. A same-value write can return Good without changing the value, so the event handler does not run. In the verified matrix, the parent accepted trigger 2 for both children, but pre-seeded Compliance remained behind while Operations journaled; the observer named `ComplianceJournal` as pending. Writing Compliance trigger 3 caused actual execution and allowed completion. Use changing or monotonic trigger values and require downstream identity evidence.

Three clean runs also fenced duplicate completion and an old dispatch after a newer confirmation. Each retained 32 exact focused rows, zero ERROR+, zero alarms, Control isolation, reset, and restoration.

### Sequence requests separately from dispatch triggers

Use two identities when a parent accepts requests and then fans out work: a changing caller request value and a script-generated downstream dispatch sequence. In the request Folder, read the current correlation identity, last issued sequence, dispatcher trigger, and every child trigger together. Require Good quality, then choose `max(retained sequences) + 1` before writing the dispatcher trigger. Retain the request value, issued sequence, decision, and counters independently.

Do not assume `qualifiedValueChanged` with `changeTypes: ["TIMESTAMP"]` makes redundant memory writes executable. On the verified 8.3.8 memory tag, two same-value writes were Good and all-verified but retained the exact prior timestamp, emitted no event marker, and changed no state. Because no new QualifiedValue timestamp existed, the TIMESTAMP-qualified handler had nothing to observe.

Require the caller's request identity to change. Three clean runs used changed request values 2, 3, and 4 to generate downstream sequences 1, 2, and 3. The first and third dispatched both journals for two confirmation identities; the second executed the dispatcher and correctly reported already current. Completion remained independently correlated. Each run retained 33 exact logs, zero ERROR+, zero alarms, Control isolation, reset, and restoration.

### Fence replayed request identities

Retain two request identities: the highest observed request and the last accepted request. Evaluate `request <= highest observed` first. On replay, increment a dedicated denial count but preserve the highest observed request, accepted request, issued sequence, dispatcher state, and child state. On a new higher request without a valid business precondition, deny it but deliberately advance the observed fence. On an accepted higher request, advance both request fields and issue the independently calculated downstream sequence.

Three clean runs consumed request 1 before confirmation, accepted request 2, denied changed lower request 1, accepted request 3 as an already-current dispatcher no-op, denied changed lower request 2, and accepted request 4 for the next confirmation. Final counts were three issued, three denied, and two replay-denied, with highest observed/accepted request 4 and downstream sequence 3. Each replay produced a marker but no dispatcher or child mutation.

This policy provides in-memory ordering and observable idempotency within the retained UDT state. It is not durable deduplication across resets, provider replacement, or Gateway loss.

### Fence lifecycle reset by request generation

Add `RequestGeneration`, `ExpectedResetGeneration`, and `ResetDeniedCount` beside the sequencer evidence. Increment request generation for each genuinely new higher request according to the chosen consumption policy, including a higher request denied by a business precondition. Do not increment it for a replay.

Before reset, read all three values together and require Good quality. Deny when current generation is zero or when the expected generation differs. A denied reset may update denial evidence, but must preserve request, issued-sequence, dispatcher, journal, and completion state. Clear the full sequencer plane only when the expected and current positive generations match.

The verified matrix advanced generations 1 through 4, preserved generation 2 and all downstream state through a stale reset and a replay, then cleared only with expected generation 4. Accepted request scripts called the sibling dispatcher, whose script called both child journal UDTs; exact logs proved the full cross-Folder chain. This is an observable in-memory lifecycle fence, not durable deduplication or atomic compare-and-set.

### Prepare and commit a generation-fenced reset

Use a sibling coordinator Folder when reset approval and execution occur in separate calls. On prepare, snapshot both the target generation and its request identity. On commit, re-read the live pair. Deny a missing or stale preparation without touching the target; retain stale preparation long enough to diagnose or cancel it. Re-prepare after the target advances.

On a matching commit, write and verify `ExpectedResetGeneration` first, then write the target `ResetTrigger`. Do not batch those dependent writes and assume ordering. Clear the coordinator's prepared fields after the trigger is accepted, but wait separately for the target's reset state and execution marker. Reset unrelated dispatcher, journal, and completion planes independently.

This pattern is not database two-phase commit, atomic compare-and-set, or durable coordination. The verified caller `COMMITTED` marker occurred before the callee `RESET` marker, demonstrating why caller success is only accepted dispatch.

### Lease a prepared reset

Add a typed duration parameter, a native DateTime deadline, matching Int8 epoch milliseconds, an independent arm Boolean, expiration counters/identity, and a Boolean expression such as:

```text
Prepared && ExpiryArmed && now(250) >= PreparedExpiresAt
```

On prepare, write and verify the prepared identity plus both deadline forms while the arm is false; arm only in a second write. In the expression event, re-read every dependency with Good quality and revalidate prepared, armed, positive deadline, and current time before clearing the preparation. Retain which generation/request expired and the observed epoch.

Cancel, commit, expiry, and coordinator reset must clear both deadline and arm. To prove suppression, capture the old deadline, wait beyond it, then require unchanged state and exact log count. The verified timer fired 91–212 ms after its deadline; `now(250)` is polling behavior, not an exact scheduler or durable lease.

### Renew a prepared-reset lease

Require expected prepared generation and request identity in addition to a live prepared+armed lease. Reject either mismatch without changing the current deadline. On acceptance, disarm, calculate the new DateTime from the retained deadline, write the DateTime and epoch evidence, then rearm. Retain previous/new deadlines and renewal counters.

Extending from the current deadline guarantees the full configured increment; recalculating from `now` can shorten an early renewal. In the verified matrix, two renewals each added exactly 4,000 ms. The preparation remained live beyond both superseded deadlines and expired once after the final deadline. Renewal after expiry was denied and did not reset the target lifecycle.

This remains an in-memory, non-atomic application lease. Concurrent renew/cancel/commit callers need additional external serialization if stronger guarantees are required.

### Cap prepared-reset renewals

Add a typed `MaxPreparationRenewals` parameter and a dedicated limit-denial counter when renewable preparation must be bounded. Evaluate policy in this order: require prepared+armed state, reject an expired deadline, require expected generation/request identity, then compare the accepted renewal count with the maximum. This prevents an invalid caller from consuming or being misclassified against the budget.

At the boundary, accept while `RenewedCount < MaxPreparationRenewals`. Beyond it, record `DENIED-RENEWAL-LIMIT`, increment both the general renewal-denial count and the limit-specific count, and preserve prepared state, arm state, and the last accepted deadline exactly. Do not disarm, recalculate, or reset the target as a side effect of denial. Clear budget evidence only during the explicit coordinator lifecycle reset.

Test exactly at the maximum and once beyond it. Verify exact previous/new/current deadline equality on denial, wait beyond superseded deadlines with stable state and exact logs, and require one expiry only after the preserved final deadline. Remember that an imported `Int4` UDT parameter may export from Ignition as canonical `Integer`; compare the semantic numeric type rather than the request spelling.

### Alarm on renewal-budget exhaustion

Expose `RenewalsRemaining` and `RenewalBudgetExhausted` as parameter-aware expression tags beneath the coordinator Folder. Alarm the exhausted Boolean with an `OnCondition` alarm and bind prepared generation, request, accepted count, maximum, and final deadline as associated data. Keep this alarm observational: activation must not change renewal policy, and a later denied renewal must retain the same alarm event rather than create another occurrence.

Verify configuration and runtime through different surfaces. Export proves label, exact-case `ackMode`, alarm binding shapes, expressions, and callbacks. Active alarm status proves source, priority, event UUID, and evaluated associated data; it need not expose configuration label.

Do not assume an `alarmCleared` callback sees the active-time bound values. If expiry clears preparation and deadline tags, the callback can receive generation/request/deadline as zero. On `alarmActive`, retain `unicode(alarmEvent.getId())` and a local was-active Boolean in sibling memory tags after checking every write quality. On clear, read both with Good quality, gate initialization noise with the Boolean, compare/log `alarmEvent.getId()` against the retained UUID, then clear the Boolean. Treat the retained UUID as audit evidence and reset it explicitly when restoring the test instance.

### Warn before renewal-budget exhaustion

Add a Low Auto-ack warning expression such as `Prepared && RenewalsRemaining = 1` beside the Medium exhaustion expression. Give each alarm its own exact source, associated data, active/clear callbacks, was-active Boolean, and retained event UUID. Do not reuse one correlation latch for multiple alarm tiers.

Test the full tier progression: no alarm at the initial maximum, only Low at one remaining, only Medium at zero, stable Medium through a denied extra renewal, and no active alarm after expiry. When the second renewal changes one remaining to zero, warning clear and exhaustion active are asynchronous consequences of the same state change. Wait for exact expression values, both correlated callback markers, and the final active-source set. Do not treat the observed callback ordering as contractual.

Keep the tiers observational and mutually exclusive. Warning activation/clear must not alter renewal counts or deadlines, exhaustion must not issue commands, and neither tier may reset the target sequencer. Use exact-case `Low`, `Medium`, and `Auto` values in JSON; lowercase variants are not portable configuration values.

### Suppress transient renewal warnings

Add a concrete numeric `timeOnDelaySeconds` to the Low warning when one-remaining states shorter than the persistence threshold should not create an event. A derived nested-tag override must restate the complete expression-backed member, alarm list, and callback list; omitted member properties are replaced rather than merged.

Exercise both branches. Move from two renewals remaining through one to zero in less than the configured delay and require the warning expression to become true then false without an active Low source, latch, event UUID, or callback marker. In a fresh cycle, hold one remaining beyond the delay, require the exact Low source/context and active callback, then cancel and correlate the clear callback by the same UUID. In three one-second-delay runs, transient intervals of 312/322/323 ms were suppressed and sustained intervals activated exactly once; each complete bounded interval had 17 focused INFO rows and zero ERROR+.

### Delay warning clear across an alarm-tier handoff

Add a concrete numeric `timeOffDelaySeconds` when operators should retain the outgoing Low event briefly after its expression clears. Do not describe alarm sources as mutually exclusive merely because their source expressions are: during the off-delay, Low can remain active while the immediate Medium exhaustion alarm is already active.

After Low has activated, move remaining budget from one to zero. Require Low=false and Medium=true expression values, then query both exact active sources before the off-delay expires. Their UUIDs must be distinct. Continue bounded polling until only Medium remains, require the Low clear callback to use its original UUID no earlier than the configured delay, and prove Medium retained the same UUID. In three one-second runs, Low cleared after 1,280/1,159/1,349 ms; all runs retained 11 focused INFO rows and zero ERROR+.

### Require acknowledgement after a delayed warning clears

Change the Low warning to `ackMode: "Manual"` and add the exact `alarmAcked` callback when an operator must acknowledge the occurrence even after the warning expression has cleared. Restate the complete nested member, including `alarmActive`, `alarmCleared`, and `alarmAcked`; add local sibling tags for the acknowledgement UUID/evidence when runtime observability is required.

After the off-delay, an active-only query should contain only Medium while the Low occurrence remains `ClearUnacked`. Query all four alarm states by exact source and UUID. Dry-run acknowledgement with a username and note, and require no state, evidence, callback, or log change. Apply the same exact UUID; require `allAcknowledged`, no failed IDs, `ClearAcked`, one unchanged UUID, and the callback's sibling writes. In three clean runs, the Low event followed state codes 2→0→1, Medium remained independent, and each bounded interval contained 12 focused INFO rows and zero ERROR+.

## Analog faceplate quality contract

A reliable model separates calculation, quality, range, and display status:

```text
PV = if(Enabled, Raw * Scale + Offset, 0)
PVGood = isGood(PV)
PVBad = isBad(PV)
PVBadOrError = isBadOrError(PV)
RangeBad = PV < LowLimit || PV > HighLimit
FaceplateStatus = Disabled | Bad | OutOfRange | Good
```

Verified behavior:

- nominal Raw 10, Scale 2, Offset 1 produced PV 21, Good;
- Scale `"bad"` produced `Error_ExpressionEval`, `isBad` false, and `isBadOrError` true;
- null Scale produced `Error_ExpressionEval` and the same helper truth table;
- disabled state short-circuited the bad scale, produced PV 0 Good, and status `Disabled`;
- inverted limits produced Good PV with `RangeBad` true and status `OutOfRange`.

Therefore gate consumers with `isBadOrError`, not `isBad` alone. Do not publish a numeric PV as healthy unless its own quality is Good. Keep range validity distinct from data quality.

## Digital faceplate semantics

Use real Boolean parameters for alarm-state comparison:

```text
InAlarm = State = AlarmState
StateText = if(State, StateLabelTrue, StateLabelFalse)
FaceplateStatus = Bad | Alarm | Normal
```

Verified truth table:

- Boolean false or numeric 0 alarm-state parameters alarmed only when State was false;
- Boolean true alarmed only when State was true;
- string `"false"` and null alarm-state parameters produced Good `InAlarm = false` for both states, silently disabling alarm semantics;
- label selection remained correct and independent of the alarm-state parameter.

Preserve raw parameter value/type in diagnostics. Reject string and null Boolean parameters before import instead of trusting Good expression quality.

## Gate reset on an acknowledged warning occurrence

Use a sibling Folder as an in-memory authorization gate:

```text
RequestTrigger
ExpectedWarningEventId
LastDecision
DeniedExpectedCount
DeniedUnacknowledgedCount
AcceptedCount
LastForwardedTrigger
LastConsumedWarningEventId
PreviousConsumedWarningEventId
DeniedReplayCount
```

On each changing request, derive the UDT root from text `tagPath`, read the warning's retained occurrence UUID plus acknowledgement UUID/Boolean from the coordinator Folder, and deny blank, stale, or unacknowledged identities without writing the reset trigger. Only an exact acknowledged occurrence may forward the request identity to the coordinator's reset trigger.

Treat `LastDecision = FORWARDED` as caller evidence, not completion. Wait for the coordinator's independent `RESET` decision and final state, then inspect exact dedicated INFO rows and all ERROR-or-higher rows from the mutation's bounded Gateway-log interval.

If authorization is single-use, compare the current acknowledged UUID with `LastConsumedWarningEventId`. On the first accepted request, retain the UUID and forward. On later requests for that UUID, set `DENIED-REPLAY`, increment `DeniedReplayCount`, preserve `AcceptedCount`, and do not rewrite the target trigger. Clear the consumption latch only at the explicitly chosen gate lifecycle boundary; do not assume the coordinator reset clears acknowledgement or consumption evidence.

To accept later occurrences without clearing the fence, require the alarm system to supply a different event UUID. On a fresh accepted UUID, copy `LastConsumedWarningEventId` to `PreviousConsumedWarningEventId`, then store the new UUID as current. On denial, preserve both values. This is a compact diagnostic history, not durable event storage.

For a bounded diagnostic trail, add `ConsumedWarningHistory` as a typed DataSet, `ConsumedHistoryEvictionCount`, `HistoryResetTrigger`, and an Int4 capacity parameter. On acceptance, append `[eventId, previousEventId, requestTrigger, system.date.now()]`; evict oldest rows until within capacity. On replay or other denial, exclude the DataSet and eviction counter from `writeBlocking` entirely. Reset history only through the explicit trigger. This remains in-memory evidence; it is not durable audit storage or an exactly-once transaction.

Prove FIFO behavior with capacity at least two before reusing this model. At the first overflow, assert exact retained order and lineage rather than only row count: the oldest row must disappear, the former newest row must become row zero, and the fresh row must become the last row. Increment eviction once per deleted row, not once per request.

For explicit maintenance compaction, retain `HistoryCompactTrigger`, `LastCompactionRemovedCount`, `CompactionCount`, and `NoOpCompactionCount`. A compaction may change history retention but must not alter accepted/replay counts, current/previous consumed UUIDs, acknowledgement evidence, or the downstream command trigger. Test both `COMPACTED` and `NOOP` branches and keep their logger markers distinct.

For denial diagnostics, use a separate bounded `DeniedRequestHistory` DataSet and `DeniedHistoryEvictionCount`. Store the decision plus request, expected, live warning, acknowledged UUIDs, and a native Date so each rejected branch can be reconstructed. Append only on denial; accepted requests and accepted-history compaction must leave denial rows and their QualifiedValue timestamp unchanged. Reset denial history through its own trigger. Three clean capacity-two runs retained the final two replay denials after six total denials, counted four evictions, preserved accepted authorization/history, cleared both histories independently, produced 45 exact focused INFO rows, zero ERROR+, no alarms, Control isolation, and restored state.

Add `DeniedHistorySummary` when a latest-denial projection is useful. Populate its schema version, DENIED/RESET state, retained rows, evictions, latest decision/request/UUIDs, and observed milliseconds from the same captured state used for the DataSet row. Cross-check the newest row against the Document after every write. Three clean runs proved exact correlation through six mixed denials and four FIFO evictions, timestamp-stable no-write behavior on three accepts and two accepted-history compactions, a complete RESET projection, 45 focused INFO, zero ERROR+, Control isolation, no alarms, and restoration.

## Bound repeated cooldown extensions

Use two independent limits: `MaxCooldownExtensionSeconds` bounds one request, while typed positive `MaxCooldownExtensionsPerOccurrence` bounds how often one cooldown occurrence may be extended. Scope the second count with `LastCooldownSourceEventId`; do not use cooldown generation because every accepted extension increments generation to invalidate the old expiry request. Retain `AcceptedExtensionsThisCooldown`, `ExtensionCountSourceEventId`, and cumulative `DeniedExtendLimitCount`. Reset only the occurrence-scoped count and source when a new nonempty occurrence UUID is published. A limit denial may update decision evidence but must not disarm, advance generation, move either deadline representation, or rewrite the expiry request.

Add a bounded `ExtensionAttemptHistory` DataSet when operators need the recent decision sequence. A useful schema is `Decision`, `RequestTrigger`, `SourceEventId`, `ExpectedGeneration`, `GenerationBefore`, `GenerationAfter`, `DeadlineBefore`, `DeadlineAfter`, `ExtensionSeconds`, and `ObservedAt`. Append on every handled extension branch so denials are diagnosable; keep cancel and expiry events out of this history. Use an independent reset trigger and eviction counter. This remains volatile diagnostic evidence, not an audit profile or durable transaction log.

Add `ExtensionAttemptSummary` when consumers need the latest attempt without decoding a DataSet. Build it from the same callback snapshot and timestamp as the row, expose a typed schema version, and include retained-row/eviction totals plus the full latest identity and scheduling lineage. Write the DataSet, eviction count, and Document together. The reset action must clear the DataSet and replace the Document with a complete `RESET` projection in the same write operation.

## Alarm on repeated extension-limit pressure

Add expression observers for `DeniedExtendLimitCount` and `ExtendedCount` when the underlying extension handler is already proven and should remain untouched. On a denial-count increase, advance `ConsecutiveExtensionLimitDenials` and retain the command trigger and observation time. On an accepted-count increase, clear a nonzero streak. Also clear the occurrence-scoped streak and evidence when the outer cooldown source UUID changes.

Drive an `OnCondition` alarm from `ConsecutiveExtensionLimitDenials >= {ExtensionLimitDenialAlarmThreshold}` with a typed positive threshold and explicit on-delay. Bind the streak, last denied trigger, last denied time, and latest decision as associated data. Latch `alarmEvent.getId()` in `alarmActive`; in `alarmCleared`, compare the callback UUID with the retained UUID before clearing the local active latch. Treat these memory tags as diagnostic evidence, not an alarm journal. Prove the configured delay from alarm `EventTime` minus the bound denial-observation milliseconds, and preserve the raw status query in the test result.

When operator acknowledgement is required, use `ackMode: Manual`, Boolean `ackNotesReqd`, and a complete `alarmAcked` callback. Retain the exact UUID, qualified `ackedBy`, acknowledgement time, Boolean latch, and cumulative count. Clear occurrence-specific acknowledgement fields in every `alarmActive` callback rather than only when the outer source changes: a successful extension can clear the pressure alarm and later denials can create a fresh occurrence under the same source UUID. Test both active-before-clear and clear-before-ack orderings through exact alarm states and guarded API dry-run/apply calls.

Add a bounded acknowledgement DataSet when operators need recent occurrence history rather than only the latest scalar evidence. Write the scalar fields, DataSet row, and eviction counter together from one `alarmAcked` callback snapshot. Keep active and cleared callbacks out of the DataSet. Use an independent reset trigger and treat the history as volatile diagnostics, not durable audit storage.

Add `ExtensionLimitAckSummary` beside that DataSet when consumers need the latest acknowledgement without scanning rows. Include schema version, `RECORDED`/`RESET` state, retained rows, evictions, event UUID, qualified actor, alarm state, cleared Boolean, and acknowledgement milliseconds. Build the row and Document from the same callback snapshot and native Date, then compare the Document time with the newest row's `dateTimeMillis`. Reset both representations in one checked write batch, but preserve the cumulative scalar acknowledgement fields so history maintenance does not erase occurrence evidence.

Add a separate lifecycle DataSet when operators need callback ordering rather than acknowledgement-only history. Use one row shape across `alarmActive`, `alarmCleared`, and `alarmAcked`: transition, event UUID, alarm state, actor, cleared flag, and native Date. Keep the acknowledgement DataSet owned only by `alarmAcked`; active and clear callbacks must not synthesize acknowledgement rows. Apply a separate capacity, eviction counter, and reset trigger so lifecycle retention can be maintained without erasing acknowledgement evidence.

Add `ExtensionLimitLifecycleSummary` when consumers need the latest transition without scanning lifecycle rows. Every callback that appends a lifecycle row must create the versioned projection from that same transition object and Date, then write DataSet, eviction count, and Document in one checked batch. Include complete `RECORDED` and `RESET` shapes. Keep acknowledgement history and its summary independent: lifecycle reset must not erase acknowledgement evidence.

Add a monotonic Int8 lifecycle sequence when timestamps alone cannot guarantee callback identity or ordering. Put the sequence in the first DataSet column and in every `RECORDED`/`RESET` Document. Increment once in each callback that actually appends; do not advance it on dry-run, source reset, ignored clear, or history maintenance. Clear retained rows without resetting the scalar so future transitions never reuse prior identities. Treat a scalar-plus-history update as cooperative evidence rather than a lock-free transaction if callbacks may truly execute concurrently; the verified model proves serialized alarm callbacks, not arbitrary multi-writer atomicity.

Add a separate integrity projection when consumers need to know whether the retained lifecycle window is contiguous. Let the DataSet event read the authoritative sequence and eviction count, scan adjacent sequence values, and write only a versioned diagnostic Document. Report missing identities separately from duplicate/reversed identities. A scalar-only perturbation must leave the observer timestamp unchanged until a new DataSet commit arrives; that commit can then surface `GAP` without changing alarm or acknowledgement ownership. Give the observer its own logger and an empty-history-only reset trigger so cleanup can restore the projection even when a repeated empty DataSet write produces no value-change event.

Add a bounded integrity-incident DataSet when operators need distinct episodes rather than every changing GAP observation. Latch the first GAP transition, use the cumulative Int8 incident count as identity, omit history/counters on persistent GAP callbacks, and re-arm only after CONTIGUOUS or EMPTY. Keep incident reset independent from lifecycle and acknowledgement maintenance, allow it only while unlatched, clear rows/evictions, and preserve cumulative identity.

Add `ExtensionLimitIntegrityIncidentSummary` when downstream consumers need the latest distinct incident. Build its `RECORDED` projection from the same values and native Date as the appended row, including current retained rows/evictions and cumulative count. Duplicate GAP callbacks and lifecycle resets must leave both value and timestamp unchanged. The incident reset must write a complete RESET object with the preserved cumulative count; final restoration must rebuild that object after clearing the scalar count. Treat the checked multi-tag write as correlated evidence, not an atomic transaction.

Apply the same paired-evidence pattern to acknowledgement-integrity incidents: the first GAP after re-arm appends one typed row and publishes one `RECORDED` Document from the same committed integrity snapshot and millisecond. Persistent GAP suppression and EMPTY re-arm do not rewrite either representation. Reset history and the Document together while retaining the cumulative incident count, then rebuild RESET after clearing that count during restoration.

Add an acknowledgement-integrity review plane when an operator action must target one exact incident. Compare an expected Int8 sequence with the current `RECORDED` incident summary; deny no incident, blank actor, stale sequence, and duplicate review separately. Accept by writing qualified actor, reviewed sequence/time, state, and count. Clear only review identity on a newly recorded incident; persistent GAP, EMPTY re-arm, and incident maintenance preserve the review plane. Split large restoration writes below the API guard and check every batch.

Add bounded review history when counters cannot reconstruct recent operator attempts. Append every accepted and denied decision to a six-column typed DataSet with decision, trigger, expected/current incident identities, actor, and native Date. Capture time once; accepted rows must equal the reviewed-at scalar millisecond. Evict oldest-first and give history its own reset/logger. History maintenance clears only rows and evictions, preserving review state/counters and incident evidence.

Add a versioned latest-review Document when consumers should not scan the bounded DataSet. Publish `RECORDED` from the same decision, identities, actor, and captured time as the appended row; include retained rows and evictions. Write both representations in the same checked batch. Reset both to empty/complete `RESET` together while preserving review state/counters and incident evidence. Treat this as correlated evidence, not a transactional guarantee.

Add a sequence-fenced review plane when operator disposition must be associated with one exact integrity incident. Keep `ExpectedIncidentSequence`, qualified actor, changing trigger, state, reviewed identity/actor/time, accepted count, denial counters, and last decision as typed siblings. Compare the request sequence with the current `RECORDED` summary before accepting. Reject no-incident, invalid-actor, stale, and duplicate requests independently; keep the incident DataSet/Document out of every review-command write.

Clear review identity only when the observer appends a new distinct incident, not on a persistent GAP, lifecycle reset, or incident-history maintenance. Retain the prior accepted review even if history is cleared; the absence of a current `RECORDED` summary then fences another review. Use a dedicated logger for review commands and new-incident review clears, and restore its 13-tag plane in a separate bounded API write when necessary.

Add `ExtensionLimitIntegrityReviewHistory` when the review counters are insufficient for reconstructing recent operator attempts. Store decision, trigger, expected/current incident identity, actor, and native Date in a typed bounded DataSet. Append accepted and denied branches alike, cap oldest-first, and maintain a separate Int8 eviction count. Use the same captured Date milliseconds as accepted review time so the accepted scalar and its row can be correlated.

Give review history its own reset trigger and logger. Its reset clears only rows and evictions; it must preserve current review state, accepted/denial counters, and incident history/summary. Alarm callbacks, new incident publication, duplicate GAP callbacks, lifecycle maintenance, and incident maintenance must omit review history. At capacity, wait on eviction and command-log barriers before asserting the same-cardinality DataSet.

Add `ExtensionLimitIntegrityReviewSummary` when a consumer needs the newest review attempt without scanning the bounded DataSet. Publish a versioned `RECORDED` Document from the same branch snapshot and native Date as the row. Include retained-row and eviction totals so the projection explains its FIFO context. Correlate every field with the newest row, and for accepted decisions also correlate its milliseconds with the reviewed-at scalar.

Treat the summary as part of the review-history maintenance plane, not the accepted-review state plane. Reset the DataSet and a complete `RESET` Document together while preserving accepted review identity and all decision counters. Unrelated alarm, lifecycle, incident, and duplicate-GAP callbacks must omit both values. Verify no-write behavior using the DataSet value/timestamp and named Document fields plus its timestamp; dictionary key order is not stable evidence.

Add a two-row decision distribution when retained history alone cannot answer lifetime questions. Use one fixed typed schema for `SchemaVersion`, `Scope`, `Total`, the five decision counts, and native `UpdatedAt`. Derive RETAINED only from rows that survived FIFO eviction; derive CUMULATIVE only from the authoritative lifetime counters. This avoids incorrectly treating retained row counts as historical totals.

Give the distribution an independent reset when consumers need to discard the projection without erasing review history. Rebuild it on the next command. When review history itself resets, publish retained zeros and preserved cumulative totals so maintenance does not imply the lifetime counters were cleared. Test both reset orders and prove each non-owning plane is value- and timestamp-stable.

Add a distribution-summary Document only as a second representation of the same computed snapshot. Include schema/state, all retained and cumulative category totals, and update milliseconds. Build the two DataSet rows and Document from one set of local variables and one Date, then check every write quality and correlate all fields at runtime.

Reset the DataSet and summary together. Use a complete zeroed RESET Document for distribution maintenance, but use RECORDED retained-zero/cumulative-preserved evidence after history maintenance. This distinction states whether the distribution was intentionally absent or validly rebuilt from still-authoritative lifetime counters.

Add a typed sibling analytics Folder when downstream consumers need scalar values but must not own the producer's review plane. Attach one `valueChanged` consumer to the committed distribution-summary Document, derive the shared parent from the concrete member path, and write only the sibling analytics tags. A useful retained projection is state, total, denied total, integer denial permille, and source-update milliseconds. Validate `retainedTotal == retainedReviewed + all retained denial categories` before writing; check every returned quality.

Let producer state control consumer state. A `RECORDED` summary produces `VALID` analytics and copies the exact source-update milliseconds; a complete `RESET` summary zeros all analytics and publishes `RESET`. Do not use floating-point output when a typed integer ratio is sufficient: compute permille with integer arithmetic, define the destination as `Int4`, and reject fractional fixture defaults. Keep the consumer logger separate so each source commit has an independently countable marker.

Add a manually triggered validation probe when operators need evidence that a derived scalar plane still agrees with its complex source. Keep a monotonic trigger, last-validated trigger, `MATCH`/`MISMATCH`/`DENIED-STALE` state, validated source state/time, cumulative validation and mismatch counts, and validation time as typed siblings. Read the source Document and all compared scalars in one bounded call, require Good quality, reconstruct the expected values independently, then write only validation evidence.

Treat mismatch detection and repair as separate ownership. A validation probe may report `MISMATCH` but must not rewrite producer-owned analytics. Drive the next real producer commit and prove it repairs the analytics; invoke validation again to prove `MATCH`. A same-value trigger can verify transport without executing `valueChanged`, while a lower or repeated sequence after re-arming must be explicitly denied without advancing counters or validation time.

Add a local expression alarm when a validation mismatch needs an operator-visible occurrence. Drive a Boolean expression from `ValidationState == MISMATCH`; do not alarm directly on raw producer fields because the validation commit is the owned decision boundary. Bind trigger, validation/source states, source time, total validation count, and mismatch count as associated data. Keep active/clear UUID and count evidence in local siblings and use a separate alarm logger.

When that validation alarm requires Manual acknowledgement, make `ackNotesReqd` a Boolean and add an exact `alarmAcked` callback. Capture `unicode(ackedBy)` as the qualified actor, retain the occurrence UUID from `alarmEvent.getId()`, write one native-millisecond observation and cumulative count, and check every write quality. Keep acknowledgement separate from producer repair: repairing the source does not reevaluate the validation-owned mismatch or clear the alarm; only a fresh validation commit may transition the same acknowledged UUID to clear.

Add bounded validation-alarm acknowledgement history only inside `alarmAcked`. Store UUID, qualified actor, callback alarm state, cleared Boolean, and one native Date; append oldest-to-newest and evict row zero while over a typed capacity. Write scalar acknowledgement evidence, DataSet, and eviction count in one checked batch. Give the DataSet its own reset trigger that clears rows and evictions but preserves cumulative scalar acknowledgement evidence.

Add a versioned latest-acknowledgement Document from that same callback snapshot when consumers should not scan the DataSet. Include retained rows, evictions, UUID, actor, alarm state, cleared Boolean, and exact acknowledgement milliseconds. Reset the DataSet, eviction counter, and a complete RESET Document together while preserving cumulative scalar acknowledgement evidence.

Producer repair and alarm clear are deliberately distinct. Repairing analytics while validation state remains MISMATCH must retain the same active UUID and emit no extra callback. Only a fresh validation MATCH should make the expression false and clear that occurrence. This proves that detection, repair, validation, and alarm lifecycle remain separately owned.

Use monotonic identity for acknowledgement-only history when each alarm occurrence should receive exactly one in-session acknowledgement identity. In `alarmAcked`, read the scalar, DataSet, and evictions; increment once; build the row and versioned Document from the same UUID, qualified actor, alarm state, cleared flag, native Date, and sequence; then write scalar acknowledgement evidence, sequence, DataSet, evictions, and Document in one checked batch. Activation, clear, dry-run, validation, and pair reset must not increment. Pair reset must omit the scalar write, retain its value and QualifiedValue timestamp, and put that sequence in RESET. After resetting at 2, a fresh UUID must receive 3 rather than 1. During restoration, write scalar zero and invoke the reset trigger again; wait for both RESET state and sequence zero because a state-only waiter can return the previous asynchronous projection.

Add a separate acknowledgement-integrity projection when consumers need to distinguish a contiguous retained identity window from a gap. Attach the observer to the DataSet, not to scalar sequence, so scalar-only changes are intentionally invisible until the next committed history snapshot. Report `EMPTY`, `CONTIGUOUS`, or `GAP` with authoritative sequence, retained first/last identities, row/eviction counts, missing-identity count, out-of-order count, and observation time. Write only the diagnostic Document and use a separate logger. Provide an empty-history-only reset trigger because writing an already-empty DataSet may not fire `valueChanged`; use it after restoring scalar zero so the EMPTY projection also returns to sequence zero.

Add first-transition-only incident history when operators need distinct GAP episodes instead of every GAP projection. Consume the committed integrity Document. On GAP with latch false, create one row using a cumulative incident identity, acknowledgement sequence, retained first/last identities, missing/out-of-order counts, retained rows, and the Document observation time converted to a native Date; write history, evictions, latch, and count together. On GAP with latch true, write no incident tags. Clear only the latch on CONTIGUOUS or EMPTY. Reset incident history only while unlatched, clear rows/evictions, and preserve cumulative count. This separates diagnostic observation from incident ownership and avoids duplicate incidents during a persistent fault.

Add a two-scope decision distribution when consumers need both a bounded operational view and lifetime totals. Use exactly ordered `RETAINED` and `CUMULATIVE` rows with schema version, total, five category counts, and native Date. After applying FIFO eviction, iterate the committed history to count RETAINED. Use authoritative accepted and denial counters, including the current command, for CUMULATIVE. Build both rows from the command's same Date and write them with history and latest-decision Document in one checked batch. Clearing distribution alone must not touch sources; the next command reconstructs it. Clearing history must publish retained zeros while preserving cumulative counts.

Add a latest distribution-summary Document when consumers should not parse DataSet rows. Mirror retained total and five retained category counts plus cumulative total and five cumulative category counts. Build it from the same local variables and native Date as the two rows, and write all four representations together. A distribution reset clears the DataSet and publishes a complete zeroed RESET summary in one batch. A history reset publishes a RECORDED summary with retained zeros and preserved cumulative totals. Do not let either reset rewrite review state/counters or incident evidence.

Add a sibling summary consumer when downstream tags need a stable, simple contract. Attach one event script to the committed source Document, validate retained and cumulative arithmetic before writing, and publish all outputs with one `writeBlocking`. A useful five-tag projection is retained total, retained denied, cumulative total, cumulative denied, and source milliseconds. On RESET, publish five zeros. Do not read the source DataSet or raw counters again: doing so creates cross-tag race windows that the committed Document was designed to eliminate.
