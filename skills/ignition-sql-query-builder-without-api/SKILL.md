---
name: ignition-sql-query-builder-without-api
description: Design and troubleshoot Ignition 8.1 SQL, Named Queries, historian/PostgreSQL queries, Perspective bindings, and database scripts from user artifacts without live Gateway API access.
---

# Ignition SQL Query Builder without API

Skill version: `1.0.74`
Stack version: `starter-2026.07.06.04`
Tested compatibility: Ignition `8.1.53`.

## Scope

Use for offline Ignition 8.1 SQL and Named Query design. Assume the LLM cannot inspect or mutate the target Gateway. Work from user-provided artifacts: SQL text, Named Query exports, project files, Perspective view/page JSON, screenshots, error messages, database schema snippets, historian table samples, and user descriptions.

Keep credentials, connection strings, host paths, and customer identifiers out of reusable output. Do not claim that a query, binding, page, or script works on the target unless the user provided target evidence. When evidence is missing, provide a concise verification checklist for the user to run in Designer, the Perspective browser session, or the database client they already use.

Do not run or generate destructive or executable SQL (`DELETE`, `UPDATE`, `INSERT`, `MERGE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, stored procedure calls) unless the user explicitly asks for that write/change. For dashboards and previews, use one bounded read-only `SELECT`/`WITH` statement and reject semicolon-chained SQL.

When scanning SQL offline, inspect executable tokens outside strings and comments: allow harmless functions such as `REPLACE(...)`, but treat mutating forms such as `REPLACE INTO` as writes. Do not classify SQL-looking text, semicolons, or comment markers inside quoted literals/comments as executable SQL, but do not use comments or literals to hide risky examples in generated SQL. Treat block-comment delimiters as part of the review: balanced non-nested comments can contain non-executable text, while unterminated or nested `/* ... */` comments can make row bounds disappear or fail target SQL parsing. Reject semicolon-chained statements for dashboard/read-only queries; use a single trailing semicolon only when the user's target tools tolerate it.

## Offline Workflow

1. Ask for or identify the target artifacts needed for the task:
   - Named Query path, `query.sql`, parameter list, parameter types, database connection placeholder, and max-return settings.
   - Perspective view/page JSON, binding JSON, route path, component names, screenshots, or error text.
   - Database schema snippets, sample rows, or target table/column lists.
   - Database connection inventory when driver-specific behavior matters: database type, status, safe placeholder name, and, if available, a Designer screenshot/export or `system.db.getConnections()` output.
   - For historian work, the database type plus relevant `sqlth_*` metadata samples if available.
2. State which assumptions are placeholders. Never assume a lab, tutorial, copied, prior-session, one-off local, or example Named Query path exists on the user's Gateway.
3. Design the SQL, Named Query parameters, Perspective bindings, and verification steps.
4. Give the user an explicit target-side check: what to open, what value to enter, what row count or label should change, and what error states would prove the design is wrong.
5. If the user returns new screenshots/errors/exports, revise from those artifacts instead of inventing target metadata.

## Reference Routes

- For SQL construction, Named Query design, dashboard bounds, aggregate/blank/numeric handling, and operator action logs, read `references/sql-and-named-query-guardrails.md`.
- For Named Query parameters, coercion, component-specific value shapes, QueryString/Database boundaries, and prepared-statement parameter rules, read `references/parameter-and-coercion-guardrails.md`.
- For Perspective URL parameters, navigation, query bindings, component binding shapes, refresh patterns, and complete binding examples, read `references/perspective-routing-and-bindings.md`.
- Before claiming a design works on the target, read `references/target-verification-checklists.md` and give the user the applicable checks.
- For Jython `system.db` call shapes, datasets, writes, generated keys, and transactions, read `references/jython-database-runtime.md`.
- For Tag Historian/PostgreSQL partition work, read `references/historian-postgres-guardrails.md` before writing SQL.
- For official source lookup, read `references/official-ignition-8.1-docs.md`.
- Prefer official Ignition 8.1 docs for syntax and behavior. Links are listed in `Ignition 8.1 Docs`.
- Treat user-provided target exports as the source of truth for project names, Named Query paths, params, database connection names, table names, and columns.
- For PostgreSQL, Tag Historian, generated-key, transaction, DateTime, or other driver-specific guidance, require target-provided database type/status evidence. If the user can only provide SQLite evidence or cannot confirm a relevant valid connection, label the behavior as target-dependent and give verification steps instead of claiming it works.

## Tag Historian PostgreSQL

For Ignition Tag Historian queries against PostgreSQL, read `references/historian-postgres-guardrails.md` before writing partition/table SQL, jitter analysis queries, or "all historized tags under this folder" queries.

Core pattern:

1. Build the time window in epoch milliseconds.
2. Resolve tag IDs from `sqlth_te`; do not assume provider prefixes or Designer casing are stored.
3. Use `sqlth_scinfo` and `sqlth_partitions` to find overlapping historian data tables.
4. Dedupe partitions by `pname`, schema-qualify `public.sqlt_data_*`, and query only discovered table names.
5. Include raw value columns and `dataintegrity` when datatype or quality matters.

If dynamic partition table names are needed, never accept table names from a user parameter. Discover them from `sqlth_partitions`, allowlist the `sqlt_data_*` shape, then build the `UNION ALL` in trusted code.

