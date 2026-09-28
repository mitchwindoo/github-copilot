---
description: 'Best-effort append-only ledger of GitHub AI Credits usage from local Copilot session telemetry, with normalized repository origin for cross-system matching'
applyTo: '**'
---

# Copilot AI Credits usage ledger

Keep a running, append-only ledger of Copilot usage from the local session store. The collector records one ledger entry per observed model-usage event, plus a non-billable marker for sessions without recorded usage events.

This is **best-effort**, not a billing export. The local session store provides token and model telemetry, not an authoritative billed-credit amount. Keep actual credits `null` unless GitHub explicitly exposes the exact amount. The authoritative source is always the GitHub billing usage report.

## Ledger location

| Shell | Path |
| --- | --- |
| POSIX | `${COPILOT_HOME:-$HOME/.copilot}/copilot-usage/copilot-credit-usage.jsonl` |
| PowerShell | `$(if ($env:COPILOT_HOME) { $env:COPILOT_HOME } else { Join-Path $HOME '.copilot' })\copilot-usage\copilot-credit-usage.jsonl` |

- Create the `copilot-usage` directory and the file on first write.
- The ledger is intentionally versionable so it can be synced across systems. Treat every line as shareable: write only the fields below, never sensitive data.
- Append; never replace the source ledger. Rebuild the summary and HTML report from it after collection.
- When merging copies from multiple systems, retain all lines. `record_key` includes the session, local usage-event ID, and a fingerprint of its immutable telemetry fields, so same-ID events with different usage do not collide; rollup drops exact duplicates.
- Repository grouping is by normalized, credential-free `repo_remote` origin, not workspace path or display name. HTTPS, SSH, and scp-style remotes for the same host/path normalize to the same canonical HTTPS origin. A missing origin stays isolated by workspace/session identity; never merge it by repo name alone.
- Append only. Never rewrite, reorder, or delete existing lines, except to remove a line that contains sensitive data.

## When to record

- After each completed Copilot turn/session, run `python bin/copilot-credit-collect.py` inside the repository workspace to discover its current remote and collect from `${COPILOT_HOME:-$HOME/.copilot}/session-store.db`. Pass `--repo-origin <remote>` outside that repository; `--session-db` and `--ledger` allow explicit local paths.
- Pass `--all-repositories` to collect every session in the store in one pass, resolving each session's own origin from its recorded workspace instead of filtering to one repository. It cannot be combined with `--repo-origin`. Sessions whose workspace no longer exists fall back to the session's `owner/repo` metadata assuming `github.com`; those that still cannot be resolved are recorded with `repo_remote: "unknown"`, which means unknown, not unattributed-to-zero.
- The collector opens the session database read-only, reads only session metadata and `assistant_usage_events`, and never reads prompts, responses, or transcript content.
- It writes one **incremental** entry per usage event, never a cumulative session total. The key is `<session_id>:usage:<local_event_id>:<fingerprint>`; turn index is recorded separately. Older `<session_id>:usage:<local_event_id>` keys are recognized during migration. Existing legacy session aggregates are not combined with event rows when that could double count.
- Sessions with no usage events receive one `record_kind: "session_marker"` row with null usage values. This means **unknown**, not zero. If usage telemetry later appears, the report treats event entries as authoritative and suppresses the old marker for coverage.
- Re-running collection is safe: already-recorded usage-event and session-marker keys are skipped. Each computer collects its own local session store; merge the resulting append-only ledger copies for cross-system coverage.

## Record fields

Use `"unknown"` for missing text fields and `null` for missing numeric fields. Never guess.

| Field | Value |
| --- | --- |
| `schema_version` | `1` |
| `recorded_at_utc` | ISO 8601 UTC timestamp, for example `2026-01-31T18:04:05Z` |
| `session_id`, `turn_id`, `record_key` | Identifiers exposed by the client, else `"unknown"` |
| `record_kind` | `"usage_event"` for a source event; `"session_marker"` when a session has no usage event |
| `client` | `"vscode"`, `"copilot-cli"`, `"copilot-app"`, or another explicitly known client, else `"unknown"` |
| `workspace_path` | Current working directory or workspace root |
| `repo_remote` | Canonical, credential-free repository origin, or `"unknown"` |
| `repo_name` | `owner/repo` parsed from the remote |
| `branch` | `git branch --show-current`, else `"unknown"` |
| `model` | Model identifier exposed for the turn |
| `input_tokens`, `cached_input_tokens`, `cache_write_tokens`, `output_tokens` | Usage-event deltas; `input_tokens` excludes cached and cache-write tokens |
| `actual_ai_credits` | Credits explicitly reported for this turn in visible client output, else `null`; never derived from token counts |
| `estimated_ai_credits` | Estimate from the method below, else `null` |
| `estimate_basis` | `{ "pricing_source_url", "pricing_retrieved_utc", "tier", "usd_per_1m": { "input", "cached_input", "cache_write", "output" }, "usd_per_ai_credit" }`, else `null` |
| `notes` | Short reason for any `null`/`"unknown"` value or skipped estimate |

- Keep `actual_ai_credits` and `estimated_ai_credits` separate; never copy one into the other.
- A configured session or budget limit is not spend; never record it as usage.

## Estimating AI credits

Estimate only when the model and all required token deltas for the usage event are present and exact credits are not.

1. The collector fetches the current official [Models and pricing for GitHub Copilot](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing) page on every run. No third-party, memory, or stale rate table is used.
2. Confirm `1 AI credit = $0.01 USD` on that page. If the page cannot be retrieved or its pricing table cannot be parsed, keep estimates `null` and report the collection as degraded.
3. Select the row matching the model. Apply a long-context tier only when that event's total input tokens exceed the published threshold.
4. Compute per event: `uncached_input = input_tokens_total - cached_input - cache_write`; then `usd = (uncached_input * rate_input + cached_input * rate_cached + cache_write * rate_cache_write + output * rate_output) / 1_000_000`; `estimated_ai_credits = usd / usd_per_ai_credit`.
5. Round to 4 decimal places and store the exact rates, tier, retrieval date, and source in `estimate_basis`. The session store's `total_nano_aiu` and request multiplier are not used as actual credits.

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

When asked for session usage, sum `actual_ai_credits` and `estimated_ai_credits` separately for records sharing the `session_id`, and state how many records had unknown usage. Report session coverage separately; a no-telemetry marker is not evidence of zero spend.

## Rollups and billing codes

Run `python bin/copilot-credit-rollup.py` to regenerate `copilot-usage/copilot-credit-usage-summary.json`. It buckets records by ISO week and by ACS billing period (the 21st through the next 21st, named by the billing date), and breaks every bucket down by repository and then by branch, each sorted by name.

`copilot-usage/acs-billing-projects.json` maps normalized `repo_origin` first, then `repo_name` or `workspace_path`, to the ACS billing project code. Edit it by hand when a new repository appears; the rollup stamps `billing_code`, `project_name`, and `client` onto each origin grouping and lists anything unmatched under `unmapped_repositories`. Use that file as the source of billing codes for any report generated from the ledger.

Use `--check` to verify the committed summary matches the ledger without rewriting it, and `bin/copilot-credit-rollup-selftest.py` after changing the rollup.

Collect first, then run `python bin/copilot-credit-report.py --open` to regenerate the summary and self-contained `copilot-usage/copilot-credit-usage-report.html` and open the report. Note: `copilot-usage/copilot-credit-usage-report.html` is a generated artifact and is no longer tracked in this repository; regenerate it on demand with `python bin\copilot-credit-report.py`.

The report embeds ledger aggregates and supports ACS billing-cycle, manual date-range, repository-origin, and branch filters without a server. It shows sessions with captured usage separately from sessions with unknown usage. Every page of a printed or PDF-exported report carries `Page X of Y`, and page 1 leads with a labeled **Report scope** block naming the selected repository, branch, billing code, model, period, and matching record count, so a printed copy always records what it represents. Use the same Python commands from the Copilot configuration root on Windows.

The same command always writes `copilot-usage/copilot-credit-usage-by-repo.csv` (override with `--repo-csv`). It is generated from the same ledger and rollup code path as the HTML report, so the two can never disagree. It has **one row per repository**, aggregating all branches, which is how spend is expensed:

`billing_code`, `project_name`, `client`, `repo_origin`, `repo_name`, `records`, `records_with_estimate`, `coverage_pct`, `estimated_credits`, `estimated_cost_usd`, `input_tokens`, `cached_input_tokens`, `cache_write_tokens`, `output_tokens`, `first_date`, `last_date`.

Rows are sorted by `estimated_cost_usd` descending. Repositories with no entry in `acs-billing-projects.json` are written with `billing_code` of `unmapped` rather than being dropped or guessed. Records with no resolvable origin keep their own row with `repo_origin` of `unknown` and are never merged into a real repository. Session markers and records without an estimate count toward `records` but never toward credits, tokens, or cost; `coverage_pct` reports that honestly, so unknown usage is never rendered as zero spend. As with every artifact here, the credit and cost columns are ESTIMATES; the authoritative source is the GitHub billing usage report. That caveat is printed to stdout by the generator rather than written as a comment line above the CSV header, which would break standard CSV parsers.

## Repository workflow preference: ledger changes on main (no worktrees)
Ledger maintenance (backfills, rollups, and one-off ledger fixes) should operate on this repository's main checkout (no worktrees). When performing ledger changes, fetch origin, verify local main is up-to-date with origin/main, stage only the ledger/summary/scripts/instructions changes, commit, and push to origin/main. Do not bypass branch protection; if push is rejected, stop and report rather than force-pushing or merging a PR. This guidance applies specifically to ledger work and does not mean every assistant turn creates a commit; only commit/push ledger changes when explicitly requested by the user.
