# Storage Qualification Forensics

Use this reference when the question is whether a tag value should have been stored at all. This covers History Enabled state, Storage Provider, Sample Mode, Historical Tag Group, Sample Rate, min/max timers, Deadband Style, Deadband Mode, Historical Deadband, analog compression, discrete deadband, quality-change storage, short pulse capture, and Dataset type tags. If the value qualified but may have queued, arrived late, quarantined, or dropped before database delivery, read `store-forward-quarantine-forensics.md`.

Official references:

- Configuring Tag History: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/configuring-tag-history
- Tag Properties: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/tag-properties
- Tag Groups: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/tag-groups
- `system.tag.queryTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-queryTagHistory

This reference targets Ignition 8.1. Confirm the target Gateway version/build and use matching official documentation before final claims about exact property names, defaults, or changed behavior.

## Contents

- Core Rule
- Sample Mode
- Min And Max Time Between Samples
- Deadband Style And Mode
- Analog Compression
- Discrete And Boolean Pulses
- Evidence Workflow
- Report Language

## Core Rule

Historian storage is conditional. A realtime value can be correct while its changes did not qualify for storage. Before calling data missing, collect configuration evidence and raw/on-change evidence that can answer whether the tag was configured to store, checked at the relevant times, and changed enough to qualify.

Required configuration evidence:

- History Enabled / `historyEnabled`
- Storage Provider
- Sample Mode / `sampleMode`
- Historical Tag Group / `historyTagGroup` when Sample Mode is Tag Group
- Sample Rate / `historySampleRate` and sample rate units when Sample Mode is Periodic
- Min Time Between Samples / `historyTimeDeadband`
- Max Time Between Samples / `historyMaxAge`
- Deadband Style / `historicalDeadbandStyle`
- Deadband Mode / `historicalDeadbandMode`
- Historical Deadband / `historicalDeadband`
- Data type and interpolation mode
- Current tag quality and timestamp during the incident window when available
- Store-and-forward delivery state if rows qualified but did not arrive

Dataset type tags are not supported by the Tag History system. If a dataset tag is involved, classify that as unsupported tag type evidence unless a different stored child or derived tag is identified.

## Sample Mode

Sample Mode controls when Ignition checks whether a historical record should be collected:

- On Change: evaluate storage when the tag value changes.
- Periodic: evaluate at the configured Sample Rate and units.
- Tag Group: evaluate at the rate of the Historical Tag Group.

Do not assume a row should exist at every realtime tag execution. A tag can execute faster than the Historical Tag Group, and a Periodic or Tag Group sample may miss a short pulse that occurred between checks.

For Tag Group mode, compare the tag's normal execution rate with the Historical Tag Group rate. If the Historical Tag Group is slower, a short event can be missed even when the current tag is healthy. If it is faster than the tag's own execution, it can check the same value multiple times without creating useful new storage evidence.

## Min And Max Time Between Samples

Min Time Between Samples prevents rapid consecutive storage. In On Change investigations, a value change inside the minimum-time window can be suppressed or represented by a later qualifying timestamp. Do not call the suppressed value deleted without checking the minimum timer.

Max Time Between Samples can force a row when no sample has been collected for the configured interval. A value of `0` disables automatic max-age collection. The setting cannot be less than 1000 ms. When Sample Mode is Tag Group, non-default max-time settings on the targeted Tag Group can take precedence over the tag property.

Max-time rows prove periodic confirmation, not every intermediate value. They do not prove that a short pulse occurred unless raw/on-change edge evidence, a counter, or explicit event rows show it.

## Deadband Style And Mode

Deadband Style changes the storage rule:

- Discrete: a new value qualifies when the absolute value difference from the last stored value is greater than or equal to the deadband. Interpolation returns the previous known value until the next stored value.
- Analog: the deadband is used as an analog compression threshold with a Sliding Window style algorithm. The system stores the first value, stores when the slope envelope is broken, and always stores quality changes.
- Auto: selects Analog for float and double data types and Discrete for other data types.

Deadband Style JSON values include `Auto`, `Analog_Compressed`, and `Discrete`.

Deadband Mode changes how the deadband amount is interpreted:

- Absolute: use the configured deadband as an absolute engineering-unit value.
- Percent: calculate deadband from the engineering unit span.
- Off: equivalent to a zero deadband; values pass through if their timestamp changes.

Historical Deadband applies specifically to historical evaluation. Do not confuse it with display formatting, alarm deadbands, or unrelated numeric deadbands.

## Analog Compression

Analog compression is not the same as a simple "value changed by more than deadband" rule. It can suppress intermediate values while preserving a compressed trend. A sparse analog history can be expected behavior when:

- History Enabled is true.
- The tag is numeric and Deadband Style is Analog or Auto selecting Analog.
- Historical Deadband and Deadband Mode explain the compression threshold.
- Raw/on-change rows show first values, slope-envelope breakpoints, max-time rows, or quality changes rather than every small movement.

Do not blame analog compression from a chart alone. Confirm configuration and compare raw/on-change rows with the user's expected process movement.

## Discrete And Boolean Pulses

Discrete values and booleans are usually event/state evidence, not periodic evidence. For a short pulse:

1. Compare pulse width with tag execution and Historical Tag Group or Sample Rate.
2. Check whether both edges occurred between historian checks.
3. Use raw/on-change rows to prove exact stored edge timestamps when available.
4. Use CountOn, CountOff, DurationOn, and DurationOff only as aggregate summaries.
5. Recommend a non-resetting counter or explicit event rows when pulses must be auditable and the sample path cannot reliably capture both edges.

A short pulse that is narrower than the execution or historical sample interval is a sampling risk, not automatic evidence of historian loss.

## Evidence Workflow

1. Capture the exact tag path, provider, history provider, and incident window.
2. Export or inspect tag configuration for the required history properties.
3. Check current value, quality, and timestamp separately from history.
4. Use a raw/on-change query with exact time bounds when storage qualification is the question.
5. If raw rows are absent but configuration suggests they should qualify, check store-and-forward, quality, tag group execution, retention, identity, and SQL partition evidence before saying data was lost.
6. Keep configuration evidence, query evidence, and database evidence separate in the report.

## Report Language

Use precise labels:

- "Observed storage configuration" when History Enabled and history properties are reviewed.
- "Observed storage-qualified row" when raw/on-change or database evidence shows a value row that qualified.
- "Inferred did-not-qualify" when configuration and value movement explain absence but raw source samples are incomplete.
- "Unverified storage qualification" when history properties or source value movement are missing.
- "Sampling risk" when a short pulse may have occurred between historical checks.
- "Approval-required remediation" for changing history enablement, Sample Mode, Historical Tag Group, Sample Rate, min/max timers, Deadband Style, Deadband Mode, or Historical Deadband.
