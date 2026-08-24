# Tag Identity Forensics

Use this reference when historian evidence may be under a different tag identity than the current tag path: renamed, moved, deleted/recreated, datatype-changed, provider-changed, historical-path, UDT-instance, remote-provider, virtual/backfilled, or direct-SQL candidate-mismatch cases.

Official references:

- Tag Paths: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/tag-paths
- Tag Providers: https://www.docs.inductiveautomation.com/docs/8.1/platform/tags/tag-providers
- Tag History Providers: https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/tag-history-providers
- `system.tag.queryTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-queryTagHistory
- `system.tag.browseHistoricalTags`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-browseHistoricalTags
- `system.tag.storeTagHistory`: https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-tag/system-tag-storeTagHistory
- Ignition Database Table Reference: https://www.docs.inductiveautomation.com/docs/8.1/appendix/reference-pages/ignition-database-table-reference

This reference targets Ignition 8.1. Confirm the Gateway version/build and the configured realtime provider, history provider, and database connection before treating an identity comparison as decisive.

## Identity Surfaces

Keep these surfaces separate until evidence ties them together:

- Realtime tag path: `[Provider]Folder/Tag`, used for current values and most live tag reads.
- Historical tag path: `histprov:...`, used by historical browsing, some components, and `system.tag.queryTagHistory`.
- History provider: the configured provider that stores/query historian data.
- Realtime provider: the provider associated with the tag at store time or query time.
- SQL historian identity: `sqlth_te.id` plus `tagpath`, `created`, `retired`, `datatype`, `scid`, `drvid`, and the matching `sqlth_drv` driver/provider.

Do not collapse these into "same tag" because the leaf name matches. A Good current read proves the current realtime path at its timestamp; it does not prove old rows were stored under the same SQL historian identity.

## First Evidence To Capture

Record:

- Exact displayed path from the chart, binding, script, or report.
- Fully qualified realtime path, including provider.
- Historical tag path if the source uses one, especially a `histprov:` path.
- Realtime provider, history provider, database connection or historian provider, and Gateway name/build when available.
- Whether the tag is a UDT instance. Query instance paths, not `_types_` definition paths.
- Whether the tag was renamed, moved, deleted/recreated, imported, changed datatype, changed tag group, changed provider, or backfilled.
- The exact incident start/end timestamps with timezone; identity rows must overlap the incident window.

## Realtime Paths Versus Historical Paths

Ignition's `system.tag.queryTagHistory` supports both realtime tag paths and historical tag paths. Historical paths are not the same string format as realtime paths. If a user provides a `histprov:` path or a component exports one, do not rewrite it to `[Provider]Folder/Tag` unless you have verified the equivalent realtime identity.

Use `system.tag.browseHistoricalTags` only when historical browsing itself is needed. Start from the narrowest historical path that can answer the question, use `maxSize`/continuation when available, and avoid broad provider-root browsing on large historians unless the user accepts the cost.

## Rename, Move, Delete, Recreate, And Datatype Changes

When tags are renamed, moved, deleted/recreated, or changed in ways that create new metadata, historical rows can be split across identities. Direct SQL should list all plausible `sqlth_te` candidates before querying data tables.

For each candidate, preserve:

- `sqlth_te.id`
- `tagpath`
- `created`
- `retired`
- `datatype`
- `querymode`
- `scid`
- `sqlth_scinfo.drvid`
- `sqlth_drv.name` and `sqlth_drv.provider`

Filter candidates by time overlap, not by "current row" status alone:

```sql
WHERE te.created < :end_ms
  AND (te.retired IS NULL OR te.retired > :start_ms)
```

If more than one candidate overlaps, report the ambiguity. Do not choose the unretired row for a past incident if a retired row is the only row that overlaps the incident window.

## Provider And Driver Mismatch

The same path text can appear under different realtime providers, history providers, Gateways, or drivers. Compare `scid` and `drvid`, then join to `sqlth_drv` before querying partitions. `sqlth_partitions.drvid` must match the driver for the candidate tag identity; rows in another driver's partition do not prove this tag has history.

For remote or migrated systems, note which Gateway executed the tag and which historian provider stored the data. A visible tag in one Gateway can represent a tag whose history was executed or stored by another Gateway.

## Virtual And Backfilled Paths

`system.tag.storeTagHistory` can store rows for paths that do not exist in the realtime provider, and a typo can create a valid historical identity under the wrong path. If SQL or historical browsing finds rows but the realtime tag is missing, classify the state as virtual, stale, or separately stored until provider/path evidence resolves it.

Treat backfill path strings as needing to be typed precisely. A wrong folder, provider, casing convention, or instance name can create usable history under an unintended identity.

Before recommending or performing any backfill, use the remediation safety rules in `SKILL.md` and `query-semantics.md`. Backfill is a write path, not a diagnostic shortcut.

## Diagnostic Decision Rules

- If current tag read succeeds but history is empty, check whether the queried path/provider is the same identity used during the incident.
- If a chart path and script path differ, report the difference before comparing row counts.
- If a UDT is involved, use the instance path and provider. `_types_` paths are design definitions, not historian row identities.
- If direct SQL returns no rows for the current `sqlth_te.id`, check retired candidates and driver/provider mismatch before declaring no stored history.
- If historical browsing finds a path that no longer has a realtime tag, do not call it absent data; call it historical-only, virtual, or stale until confirmed.
- If several identities partially match, grade the finding as observed for each evidence surface and inferred only for the cross-surface linkage.
