---
description: 'Best-effort per-session ledger of GitHub AI Credits usage (reported or estimated from token/model usage) with workspace and repository origin, appended to a versionable JSONL file'
applyTo: '**'
---

# Copilot AI Credits usage ledger

Keep a running, per-session tally of GitHub AI Credits by appending one incremental record per completed turn to a local JSONL ledger.

This is **best-effort**. Instructions cannot read hidden billing telemetry, and no session-end callback is guaranteed. Record only values that are explicitly visible in the current context (for example a usage summary, tool result, or client status output). Do not infer, recall, or approximate hidden counters. The authoritative source is always the GitHub billing usage report.

## Ledger location

| Shell | Path |
| --- | --- |
| POSIX | `${COPILOT_HOME:-$HOME/.copilot}/copilot-usage/copilot-credit-usage.jsonl` |
| PowerShell | `$(if ($env:COPILOT_HOME) { $env:COPILOT_HOME } else { Join-Path $HOME '.copilot' })\copilot-usage\copilot-credit-usage.jsonl` |

- Create the `copilot-usage` directory and the file on first write.
- The ledger is intentionally versionable so it can be committed and synced across systems with these instructions. Treat every line as shareable: write only the fields below, never sensitive data.
- When merging copies from multiple systems, keep all lines and drop exact duplicate `record_key` values other than `unknown`.
- Append only. Never rewrite, reorder, or delete existing lines, except to remove a line that contains sensitive data.

## When to record

- Append exactly one record at the end of each completed turn, after the turn's work is done.
- Record **incremental** usage for that turn only. Never write a cumulative session total as a usage value; the running tally is the sum of the session's records.
- Build `record_key` as `<session_id>:<turn_id>` when both are exposed. Before appending, skip the write if that key already exists in the ledger. When either part is `unknown`, append without dedupe and set `record_key` to `unknown`.
- If the client only exposes cumulative session counters, store the difference from the previous record for the same session. If no previous value exists for that session, set token fields to `null` with a reason instead of writing the cumulative value.

## Record fields

Use `"unknown"` for missing text fields and `null` for missing numeric fields. Never guess.

| Field | Value |
| --- | --- |
| `schema_version` | `1` |
| `recorded_at_utc` | ISO 8601 UTC timestamp, for example `2026-01-31T18:04:05Z` |
| `session_id`, `turn_id`, `record_key` | Identifiers exposed by the client, else `"unknown"` |
| `client` | `"vscode"`, `"copilot-cli"`, `"copilot-app"`, or another explicitly known client, else `"unknown"` |
| `workspace_path` | Current working directory or workspace root |
| `repo_remote` | `git remote get-url origin` with any `user:token@` credentials removed |
| `repo_name` | `owner/repo` parsed from the remote |
| `branch` | `git branch --show-current`, else `"unknown"` |
| `model` | Model identifier exposed for the turn |
| `input_tokens`, `cached_input_tokens`, `cache_write_tokens`, `output_tokens` | Turn deltas when exposed; `input_tokens` excludes cached tokens |
| `actual_ai_credits` | Credits explicitly reported for this turn in visible client output, else `null`; never derived from token counts |
| `estimated_ai_credits` | Estimate from the method below, else `null` |
| `estimate_basis` | `{ "pricing_source_url", "pricing_retrieved_utc", "tier", "usd_per_1m": { "input", "cached_input", "cache_write", "output" }, "usd_per_ai_credit" }`, else `null` |
| `notes` | Short reason for any `null`/`"unknown"` value or skipped estimate |

- Keep `actual_ai_credits` and `estimated_ai_credits` separate; never copy one into the other.
- A configured session or budget limit is not spend; never record it as usage.

## Estimating AI credits

Estimate only when the model and token deltas for the turn are exposed and exact credits are not.

1. Read current rates from the official GitHub page [Models and pricing for GitHub Copilot](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing). Do not use third-party rates, memory, or cached tables from another session.
2. Confirm the USD-to-credit conversion from the same page or [GitHub Copilot billing](https://docs.github.com/en/billing/concepts/product-billing/github-copilot-billing). As of this writing it is `1 AI credit = $0.01 USD`.
3. Select the row matching the model and tier. Use the long-context tier only when the turn's input tokens exceed the published threshold.
4. Compute:
   `usd = (input * rate_input + cached_input * rate_cached + cache_write * rate_cache_write + output * rate_output) / 1_000_000`
   `estimated_ai_credits = usd / usd_per_ai_credit`
5. Round to 4 decimal places and store the exact rates and source in `estimate_basis`.

Set `estimated_ai_credits` to `null` and explain in `notes` when the model is not listed, the tier is ambiguous, the pricing page is unreachable, or any required token delta is missing.

## Privacy and safety

- Never write prompts, responses, file contents, transcripts, secrets, tokens, or credentials to the ledger.
- Never retrieve or use personal access tokens or other credentials to look up usage.
- Strip credentials from remote URLs before recording.
- Keep `notes` short and factual; never include user content or sensitive identifiers in it.
- Before committing the ledger, scan new lines for secrets, prompts, or transcript text and remove the entire offending line if one is found.

## Writing a record

Prefer the client's file-editing tool. When only a shell is available, serialize one compact JSON object per line; never use heredocs or multi-line redirection.

```powershell
$ledgerRoot = if ($env:COPILOT_HOME) { $env:COPILOT_HOME } else { Join-Path $HOME '.copilot' }
$ledger = Join-Path $ledgerRoot 'copilot-usage\copilot-credit-usage.jsonl'
New-Item -ItemType Directory -Force -Path (Split-Path $ledger) | Out-Null
$record | ConvertTo-Json -Compress -Depth 5 | Add-Content -LiteralPath $ledger -Encoding utf8
```

## Reporting the tally

When asked for session usage, sum `actual_ai_credits` and `estimated_ai_credits` separately for records sharing the `session_id`, and state how many records had unknown usage.

## Rollups and billing codes

Run `python bin/copilot-credit-rollup.py` to regenerate `copilot-usage/copilot-credit-usage-summary.json`. It buckets records by ISO week and by ACS billing period (the 21st through the next 21st, named by the billing date), and breaks every bucket down by repository and then by branch, each sorted by name.

`copilot-usage/acs-billing-projects.json` maps `repo_name` (or `workspace_path`) to the ACS billing project code. Edit it by hand when a new repository appears; the rollup stamps `billing_code`, `project_name`, and `client` onto each repository grouping and lists anything unmatched under `unmapped_repositories`. Use that file as the source of billing codes for any report generated from the ledger.

Use `--check` to verify the committed summary matches the ledger without rewriting it, and `bin/copilot-credit-rollup-selftest.py` after changing the rollup.

Run `bin\build-copilot-usage-report.ps1` on Windows to regenerate both the summary and the self-contained `copilot-usage/copilot-credit-usage-report.html`, then open the report in the default browser. Pass `-NoOpen` to build without opening it; `python bin\copilot-credit-report.py --open` is the direct Python equivalent. The report embeds the ledger aggregates and supports ACS billing-cycle, manual date-range, repository, and branch filters without a server or internet connection.

## Repository workflow preference: ledger changes on main (no worktrees)
Ledger maintenance (backfills, rollups, and one-off ledger fixes) should operate on this repository's main checkout (no worktrees). When performing ledger changes, fetch origin, verify local main is up-to-date with origin/main, stage only the ledger/summary/scripts/instructions changes, commit, and push to origin/main. Do not bypass branch protection; if push is rejected, stop and report rather than force-pushing or merging a PR. This guidance applies specifically to ledger work and does not mean every assistant turn creates a commit; only commit/push ledger changes when explicitly requested by the user.
