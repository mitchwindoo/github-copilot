# Rosters, Contacts, And Schedules

Use this reference when notification routing depends on who should receive the alarm, which channel is eligible, or whether a user was on shift at the event time.

## Recipient Chain

Trace recipients in this order:

1. Alarm event and pipeline path.
2. Notification block or calculated roster expression.
3. Roster name and roster source.
4. Static membership order or calculated output.
5. User source for each selected user.
6. Contact record type needed by the profile.
7. Schedule membership at the event timestamp.
8. Sink, Test Mode, provider, or log evidence for delivery.

## Contact Checks

- Prove the roster/profile resolves users from the expected user source.
- Treat email, SMS, phone/voice, multiple contacts, and no-contact users as different cases.
- Capture the full contact-method list when a user has multiple entries for one channel; do not choose an address or number by assumption.
- A non-empty roster is not proof of channel eligibility.
- A matching contact record is not proof of delivery; delivery still needs sink, provider, Test Mode, or module evidence.

## Static Rosters

For static roster work, read back:

- Exact roster name.
- Member names in order.
- Empty roster state when applicable.
- User source and contact types for each member.
- Cleanup state after any lab roster is removed.

## Calculated Rosters

Calculated roster behavior must be proven on the target:

- Confirm input query, script, or expression source.
- Preserve raw output keys and values before assuming they map to notification contacts.
- Check dedupe rules when multiple groups or rosters can return the same person.
- Treat schedule pruning and contact eligibility as separate proof steps.

## Contact And Roster Edge Cases

- Roster APIs can preserve names with spaces or punctuation, but expression and direct-assignment surfaces still need quoted, escaped, target-specific proof.
- When combining rosters or calculated contacts, show the raw candidate list and the deduped recipient list; overlapping rosters can otherwise duplicate notifications.
- API roster membership is not the same as effective notification recipients after schedules, contact matching, profile type, and block settings.

## Schedules And Holidays

- Evaluate the exact event timestamp in the Gateway timezone.
- Distinguish assigned schedule model from scheduled-user membership.
- Compare "active now" only when the event time is actually now.
- For holiday behavior, compare a holiday-observing user and a holiday-ignoring control at the same timestamp before, during, and after the holiday change.
- Do not infer rotating on-call behavior from a schedule name or repeat settings alone; prove scheduled and unscheduled boundaries for the same fixture user.
