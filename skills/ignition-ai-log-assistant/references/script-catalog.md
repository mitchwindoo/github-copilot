# Script Catalog

Load this reference before choosing or running a bundled helper.

## Runtime And Safety

Run the helpers with Python 3.9 or newer. They use only the Python standard library and make no network calls. Inputs are read locally; results are written to standard output unless an explicit output argument is supplied. Write generated output outside the installed skill folder.

Treat every helper result as intermediate evidence. Inspect output for sensitive data before sharing it. Built-in redaction is a first pass, not a guarantee. Never run an IDB helper against an active Gateway database, and keep archive, file-count, byte, row, and time bounds in place.

`query_gateway_idb.py` and `query_wrapper_logs.py` support `--no-redact`. Use that option only for an explicitly justified, controlled local investigation. Never publish, upload, or share its unredacted output without a separate human review.

Use `python scripts/<name>.py --help` for the complete current arguments.

## Collection And Inspection

| Script | Purpose | Primary input and behavior |
|---|---|---|
| `query_gateway_idb.py` | Query copied or exported Gateway Diagnostic Logs. | Opens a copied `system_logs*.idb` read-only, discovers its schema, applies bounded filters, and emits JSON. Supports `--json-out`; never target a live IDB. |
| `query_wrapper_logs.py` | Query local or exported wrapper logs. | Reads supplied files or directories with file-count and byte caps, optional rotated siblings, time/logger/message filters, and JSON output. It does not modify logs. |
| `inspect_diagnostic_bundle.py` | Inventory and classify a diagnostic ZIP or directory before deeper parsing. | Reads archive metadata without extracting it, caps entries and optional hashing, and emits a routing inventory. Filename classifications remain hints requiring review. |
| `compare_thread_dumps.py` | Compare repeated signatures across two or more JVM thread dumps. | Reads dumps in capture order, caps returned rows, and emits JSON; `--json-out` optionally writes it. Correlate persistent stacks with logs or metrics. |
| `sanitize_log_evidence.py` | Apply first-pass sanitization to text or JSON evidence. | Reads one bounded local file and emits sanitized content plus findings. `--text-out` and `--json-out` write explicit output files. Human review remains required. |

## Normalization And Analysis

| Script | Purpose | Primary input and behavior |
|---|---|---|
| `normalize_log_rows.py` | Normalize source-labeled parser/helper JSON before grouping. | Reads one or more JSON inputs, writes normalized JSON to stdout, and optionally writes `--json-out`. It does not diagnose the incident. |
| `group_log_findings.py` | Group repeated findings while preserving source and follow-on relationships. | Reads normalized source-labeled rows, limits evidence samples per group, and emits JSON. Categories are triage aids requiring human verification. |
| `route_log_technical_sources.py` | Map logger and category clues to relevant official technical reading. | Reads rows, grouped findings, or a diagnostic brief and emits a source-routing plan. It does not browse or prove root cause. |
| `route_module_sources.py` | Route installed module/version evidence to appropriate vendor release sources. | Reads a `gatewayInfo` response or module-list JSON and emits a routing plan. It does not browse or establish compatibility by itself. |

## Requests And Reports

| Script | Purpose | Primary input and behavior |
|---|---|---|
| `build_evidence_request.py` | Build the smallest useful source-specific evidence request. | Reads incident metadata JSON and emits a collection checklist. `--json-out` and `--text-out` optionally write files. It does not collect evidence. |
| `build_diagnostic_brief.py` | Format grouped findings into a source-labeled diagnostic brief. | Reads grouped-findings JSON with optional environment and source-check JSON, then emits JSON and Markdown. It is a reporting scaffold, not an autonomous diagnosis. |

## Fallback

If Python is unavailable, follow the equivalent bounded workflow manually: preserve source labels, work only from copied/exported evidence, record source hashes and coverage, enforce input and result caps, sanitize before sharing, and state which automated checks were not performed.
