# Store-And-Forward And Quarantine Forensics

Use this reference when historian rows may be delayed, queued, quarantined, dropped, or recovered later through store-and-forward. This covers Memory Buffer, Disk Store, Local Cache, Disk Cache, Database Sink, Write Time, Write Size, Forward Settings, Store Settings, Quarantined Items, Total Quarantine, Total Dropped, database connection recovery, disabled history providers, retry/delete/export/import actions, and disk-cache archive/load decisions.

Official references:

- Store and Forward: https://www.docs.inductiveautomation.com/docs/8.1/platform/database-connections/store-and-forward
- Configuring Store and Forward: https://www.docs.inductiveautomation.com/docs/8.1/platform/database-connections/store-and-forward/configuring-store-and-forward
- Controlling Quarantine Data: https://www.docs.inductiveautomation.com/docs/8.1/platform/database-connections/store-and-forward/controlling-quarantine-data
- Connections - Store & Forward: https://www.docs.inductiveautomation.com/docs/8.1/platform/gateway/status/connections/connections-store-and-forward
- How the Tag Historian System Works: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/how-the-tag-historian-system-works
- Tag History Providers: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/tag-history-providers

Confirm the target Gateway version/build and provider type before making version-sensitive claims.

## Contents

- Core Rule
- Delivery Path
- Queue And Forward Triggers
- Quarantine Evidence
- Dropped Records And Disabled Providers
- Action Safety
- Evidence Workflow
- Report Language

## Core Rule

Store-and-forward evidence answers delivery questions after a History Set has been collected. It does not by itself prove that a tag was configured to store, that a sample qualified for storage, or that a query retrieved every stored row. Keep these states separate:

- **Delayed:** data is in Memory Buffer, Local Cache, or Disk Cache, or a database connection was faulted and later recovered.
- **Quarantined:** data repeatedly failed forwarding or could not be stored because of an error or configuration issue, and it was moved out of the normal forward queue.
- **Dropped:** records could not be added to a buffer/cache or were discarded because capacity or disk-cache conditions did not allow preservation.
- **Delivered:** rows reached the historian database, but a query, chart, aggregate, provider, identity, retention, or time-window issue may still hide them.

Do not call queued, quarantined, or dropped records proof of never stored unless provider, tag identity, event timestamp, incident window, logs, and row evidence close the loop.

## Delivery Path

For Tag Historian storage, a collected sample becomes part of a History Set. The History Set passes through store-and-forward before reaching the historian database.

Track these stages:

- **Memory Buffer:** first-stage in-memory queue. A full memory buffer can lead to dropped records. It cannot preserve quarantine if disk storage is unavailable.
- **Disk Store:** local disk stage.
- **Local Cache / Disk Cache:** holds data that has not yet forwarded to the Database Sink. It can also hold quarantined data when Disk Cache Enabled is true.
- **Database Sink:** groups samples into SQL transactions, writes to the database, and may retry individual failed samples before quarantine.

When a later query shows rows that an earlier query missed, compare event timestamp, query execution time, Gateway log time, and arrival time before calling the rows a manual backfill.

## Queue And Forward Triggers

Capture the store-and-forward settings for the database connection or engine:

- Store Settings: Disk Cache Enabled, Max Records, Write Size, Write Time.
- Forward Settings: Write Size, Write Time, Enable Schedule, Schedule Pattern.
- Whether the database connection was connected, faulted, disabled, or recovering.
- Store Throughput and Forward Throughput around the incident window.
- Memory Buffer and Local Cache or Disk Cache current/max counts when available.

Write Time and Write Size act as forwarding triggers. Queued records may wait until a trigger fires. A schedule hold can leave data cached until the next allowed execution period. This is delayed delivery evidence, not loss proof.

## Quarantine Evidence

Use Gateway Store & Forward details, logs, or exported quarantine details to collect:

- Store-and-forward engine or database connection name.
- Total Quarantine and per-engine quarantine count.
- Quarantined Items with ID, Count, Description, and Reason.
- First/last observed log or UI time.
- Provider, tag identity, datatype, and whether the item overlaps the incident window.
- Whether the error points to schema mismatch, disabled provider, database constraint, connection fault, or another cause.

A global quarantine count is only context. It becomes incident-linked evidence only when the item description/reason, provider, tag identity, and timestamp range match the affected data.

Quarantine can explain delayed or absent rows, but it is not a repair instruction. Fix the root cause before retrying records.

## Dropped Records And Disabled Providers

Total Dropped means records could not be accepted into a store-and-forward buffer. Dropped-record evidence is more severe than queue delay and different from quarantine. Capture memory-buffer capacity, Disk Cache Enabled state, Max Records, disk/cache health, and any related log messages before saying records were lost.

If a datasource history provider is disabled, it will not accept history data. Ignition documentation notes that data logged to a disabled datasource history provider can error out and be quarantined by store-and-forward if possible. Classify this as history provider disabled evidence, then check whether disk cache was enabled and whether matching quarantine items exist.

## Action Safety

These are not read-only proof steps:

- Retry
- Delete
- Import
- Archive Disk Cache
- Load Disk Cache

Treat them as approval-required remediation or operational recovery. Export can support preservation, but it can still expose or move operational data, so treat it as a preservation/remediation support step rather than a simple diagnostic. Use export before destructive actions when recovery is being planned.

Disk-cache Archive Disk Cache and Load Disk Cache actions can affect active cache behavior. Do not recommend them as routine diagnostics.

## Evidence Workflow

1. Confirm storage qualification first when the question is whether the value should have entered historian collection.
2. Capture the exact database connection, history provider, realtime provider, and tag identity.
3. Record event timestamp, query execution time, Gateway log time, store-and-forward arrival time, and database row timestamp separately.
4. Review database connection status and focused store-and-forward or quarantine logs around the incident window.
5. Capture Memory Buffer, Local Cache or Disk Cache, Store Throughput, Forward Throughput, Total Quarantine, Total Dropped, and Quarantined Items when available.
6. If quarantine is present, preserve ID, Count, Description, and Reason before any retry/delete/export/import action.
7. Compare direct query or SQL row evidence after recovery with the original incident query. A late row with the original event timestamp supports delayed delivery. A row timestamped at the recovery time may indicate manual write, wrong timestamp source, or a different event.
8. If old rows are absent after delivery evidence is reviewed, check retention/pruning, identity, and query semantics before saying rows were lost.

## Report Language

Use narrow labels:

- **Observed delayed queue:** buffer/cache counts, database fault, schedule hold, or logs show data waiting to forward.
- **Observed late arrival:** rows appeared later with event timestamps in the incident window and matching provider/tag identity.
- **Observed quarantine:** matching Quarantined Items or logs identify affected provider/tag/window and Reason.
- **Quarantine context only:** global counts or unrelated reasons exist, but provider/tag/window matching is missing.
- **Dropped-record risk:** Total Dropped, buffer-full, cache-full, disabled-cache, or similar evidence indicates possible data loss.
- **Disabled-provider risk:** history provider disabled evidence explains errors or quarantine risk.
- **Delivery unverified:** no queue/quarantine/drop evidence was reviewed, so delivery state is unknown.

Avoid saying "quarantine deleted the data" unless there is explicit delete action evidence tied to the item. Avoid saying "retried records prove the original data was present" unless the exported or retried item can be matched to provider, tag identity, event timestamp, quality, and incident window. Avoid saying "not in the query means never stored" when store-and-forward delivery evidence is missing; no-row query evidence is not proof of never stored.
