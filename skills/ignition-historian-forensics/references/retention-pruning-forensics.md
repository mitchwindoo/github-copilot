# Retention And Pruning Forensics

Use this reference when historian data is missing from an older window, the requested range may exceed configured retention, a provider has pruning or point/time limits, an archive or replica may be involved, or the question is compliance retention rather than immediate collection. If the "archive" evidence is a quarantine export, disk-cache archive, delayed store-and-forward recovery, dropped-record count, or cache load operation, also read `store-forward-quarantine-forensics.md`.

Official references:

- Tag History Providers: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/tag-history-providers
- How the Tag Historian System Works: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/how-the-tag-historian-system-works
- Ignition Database Table Reference: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/ignition-database-table-reference
- Ignition Edge: https://www.docs.inductiveautomation.com/docs/8.1/other-editions/ignition-edge

This reference targets Ignition 8.1. Confirm the Gateway version/build, provider type, product edition, and active history provider before treating no-row evidence as a retention finding.

## Core Rule

No rows in the active historian for an old window proves only active-store absence until retention, pruning, provider limits, archives, backups, replicas, and partition metadata are reviewed. Do not phrase the conclusion as "never stored" when the stronger supported finding is "not present in the active store reviewed."

## Provider Types To Separate

- Datasource history provider: stores to a database connection and can use partitioning, pre-processed partitions, and data pruning settings.
- Internal historian provider: stores inside the Ignition installation and can prune by time limit or point limit. Internal historian rows do not contain tag group execution data, so stale-execution evidence differs from external SQL providers.
- Remote history provider: points at another Gateway's historical provider; retention settings must be checked on the original provider, not only the local remote link.
- Edge historian provider: Edge uses an internal historian provider with local-history constraints and automatic pruning behavior.
- Third-party or custom storage engines: do not assume the `sqlth_*` schema or Ignition datasource pruning behavior applies.

## Datasource Data Pruning

For datasource history providers, capture:

- History provider name and database connection.
- Whether data pruning is enabled.
- Prune age and prune age units.
- Partition length and partition units.
- Whether pre-processed partitions are enabled.
- Whether duplicate history providers point at the same database connection.
- Whether external database maintenance, archive, replication, or backup jobs move or delete historian tables.

Data pruning deletes old partitions. A partition can contain rows older than the prune age and still remain if it also contains data younger than the prune age. Conversely, once a whole partition has no data younger than the prune age, absence of that partition is compatible with pruning.

When two datasource history providers point at the same source, compare their pruning settings before attributing deleted table data to tag behavior. A second provider with stricter pruning can affect shared table data.

## Partition Evidence

For old-window SQL checks:

1. Resolve the tag identity first using `tag-identity-forensics.md` when needed.
2. Join to the correct `drvid`.
3. Query `sqlth_partitions` for rows overlapping the window.
4. If no partition row overlaps, check pruning settings and external maintenance before querying data tables by guessed name.
5. If a partition overlaps, query only discovered `pname` tables and keep the result as active-store evidence.

Use `historian-sql-forensics.md` for table-shape details and safe read-only query construction. Never create a missing partition table name from user input or from a date alone.

## Internal And Edge Historian Limits

For internal historian providers, capture:

- Time Limited Enabled setting.
- Time Limit Size and Units.
- Point Limit Enabled setting.
- Point Limit Size.
- Whether remote sync is enabled and the remote provider target.
- Whether the Gateway is Standard Ignition or Edge.

For Edge systems, identify the Edge product and whether the requested window exceeds local-history limits. Current Ignition 8.1 Edge documentation describes local tag history storage as limited to 35 days or 10 million data points on affected builds, with automatic pruning. Check the exact Gateway version/build and sync evidence before declaring data unavailable globally; local Edge absence may still leave remote synchronized history or backups.

Do not apply external datasource SQL assumptions to internal or Edge-only evidence. Internal historian evidence may require historical browsing/query evidence, provider settings, sync evidence, or Gateway-exported evidence instead of `sqlth_*` tables.

## Archives, Backups, And Replicas

Distinguish:

- Active historian: the provider/database currently serving `queryTagHistory` or component bindings.
- Archive database: a separate store that may contain old partitions or exported rows.
- Database replica: a read replica that may lag or omit archived partitions.
- Gateway backup: configuration backup, not automatically a proof of historian row contents.
- SQL backup: database backup that may prove historical rows if restored or inspected safely.
- Exported history or quarantine export: evidence only if provider, tag identity, timestamps, and qualities match the incident window.

If the user needs a compliance answer, state whether the reviewed evidence proves active availability, archived availability, restored availability, or only that the active query path lacks rows.

## Report Language

Use precise classifications:

- **Observed active-store absence:** exact active provider/database/query was reviewed and returned no rows or no partition coverage.
- **Observed retained active data:** active rows or partitions cover the window.
- **Pruning-compatible absence:** provider pruning/limits and partition dates make deletion plausible, but no audit/archive proof was reviewed.
- **Observed pruned/retention-limited:** pruning configuration, partition absence, provider limits, logs, audit records, or controlled archive evidence directly explain absence.
- **Archive required:** active store lacks data and the next proof step is archive, backup, replica, or sync evidence.
- **Never-stored unverified:** active store lacks rows, but retention/pruning/archive evidence is missing, so never-stored is not proven.

Avoid saying "historian lost the data" unless retention, pruning, deletion, migration, or archive evidence directly supports that wording.
