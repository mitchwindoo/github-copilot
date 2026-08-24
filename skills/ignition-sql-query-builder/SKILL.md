---
name: ignition-sql-query-builder
description: Design and validate Ignition 8.1 SQL, Named Queries, historian/PostgreSQL queries, Perspective bindings, and runner-assisted previews when live Gateway API access is available.
---

# Ignition SQL Query Builder

Skill version: `1.0.200`
Stack version: `starter-2026.07.06.04`

## Scope

Use for Ignition 8.1 SQL and Named Query design. Keep credentials, connection strings, host paths, and customer identifiers out of reusable output.

Do not run or generate destructive or executable SQL (`DELETE`, `UPDATE`, `INSERT`, `MERGE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, stored procedure calls) unless the user explicitly asks for that write/change. For dashboards and previews, use one bounded read-only `SELECT`/`WITH` statement and reject semicolon-chained SQL.

When scanning SQL, inspect executable tokens outside strings and comments: allow harmless functions such as `REPLACE(...)`, but treat mutating forms such as `REPLACE INTO` as writes. Do not treat SQL-looking text inside quoted literals or comments as executable, but do not use comments or literals to hide risky examples in generated SQL. Treat block-comment delimiters as part of the review: balanced non-nested comments can contain non-executable text, while unterminated or nested `/* ... */` comments can make row bounds disappear or fail target SQL parsing.

## Workflow

1. Discover the customer's database connection, schema, resource names, parameters, and target Ignition context. Do not guess deployment-specific names.
2. If a live Gateway runner or API is available, begin with its health/capability discovery and read [Runner API Workflow](runner-api-workflow.md) before using any runner action. Treat live capabilities as authoritative.
3. Read the references required for the requested workflow before producing SQL, bindings, scripts, previews, or packages.
4. Default to bounded read-only discovery and preview. Use mutation or package apply behavior only when the user explicitly requests it and after the required validation or dry run.
5. Validate parameter types, query bounds, output shape, and Ignition/Perspective integration behavior. Read back applied resources when the available API supports it.
6. Do not update, replace, or self-modify a runner unless the user explicitly asks for runner maintenance.

## Customer References

- Read [Runner API Workflow](runner-api-workflow.md) for live API discovery, supported runner actions, version/capability gates, preview rules, and dry-run/apply packaging.
- Read [SQL and Named Query Guardrails](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-sql-query-builder/references/sql-and-named-query-guardrails.md) for Named Query design, dashboard SQL safety, bounded reads, and operator action logging.
- Read [Parameter and Coercion Guardrails](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-sql-query-builder/references/parameter-and-coercion-guardrails.md) before choosing parameter types, validating inputs, or handling dates, collections, JSON, and coercion.
- Read [Perspective Query Bindings](perspective-query-bindings.md) before creating or reviewing Perspective query bindings and database-backed pages.
- Read [Jython Database Runtime](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-sql-query-builder/references/jython-database-runtime.md) before using Ignition database functions or consuming database results in Jython.
- Read [Historian PostgreSQL Guardrails](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-sql-query-builder/references/historian-postgres-guardrails.md) for verified Tag Historian table relationships, partition-aware querying, and schema caveats.
- Read [Official Ignition 8.1 Documentation](Home%20Vault/Business%20ideas/ignition%20skills%20md/skills/Ignition%208.1%20Skills/ignition-sql-query-builder/references/official-ignition-8.1-docs.md) when official API, component, binding, Named Query, or database-function documentation is needed.

## Tag Historian PostgreSQL

For Ignition Tag Historian queries against PostgreSQL, read `references/historian-postgres-guardrails.md` before writing partition/table SQL, jitter analysis queries, or "all historized tags under this folder" queries.

Core pattern:

1. Build the time window in epoch milliseconds.
2. Resolve tag IDs from `sqlth_te`; do not assume provider prefixes or Designer casing are stored.
3. Use `sqlth_scinfo` and `sqlth_partitions` to find overlapping historian data tables.
4. Dedupe partitions by `pname`, schema-qualify `public.sqlt_data_*`, and query only discovered table names.
5. Include raw value columns and `dataintegrity` when datatype or quality matters.

If dynamic partition table names are needed, never accept table names from a user parameter. Discover them from `sqlth_partitions`, allowlist the `sqlt_data_*` shape, then build the `UNION ALL` in trusted code.
