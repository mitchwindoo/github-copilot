---
applyTo: '**'
---
**Organization & Style**

* Prefer clarity over cleverness. Write small, single-purpose functions with descriptive names. Use guard clauses and early returns.
* Keep dependencies minimal and portable. Default to standard libraries when practical.
* Favor immutability and pure functions when reasonable; isolate side effects at boundaries.
* Comments explain **why**, not **what**. Keep them concise. Public functions include brief docstrings with inputs/outputs and edge cases.

**Languages**

* **Python 3.x**: Follow PEP 8. Use type hints. Prefer `pathlib`, f-strings, and `logging`. Provide docstring examples where helpful.
* **Jython 2.7 (Ignition scripting)**: Remain Python-2.7 compatible (no f-strings/`pathlib`/type hints). Use `system.*` APIs, avoid blocking the UI thread, and write thread-safe gateway/event scripts.
* **Java** (Ignition modules/SDK): Prefer clear composition over inheritance. Use standard logging. Avoid heavy frameworks.
* **TypeScript/JavaScript**: Default to TypeScript with strict typing. Use modern ES modules, async/await, and functional React components with hooks.
* **SQL**: Be explicit and readable. Use parameterized queries always. Name columns clearly; prefer UTC timestamps.
* **PowerShell/YAML/JSON/HTML/CSS**: Emphasize portability and readability. Validate inputs; keep configs declarative.

**Frameworks & Ecosystem**

* **Ignition 8.1 (Vision/Perspective, Gateway scripts, Tag Change, Alarm Pipelines)**:

  * Use system functions (`system.tag`, `system.db`, `system.alarm`, etc.).
  * Make long-running work asynchronous or gateway-scoped; handle retries with exponential backoff.
  * Never hard-code credentials or gateway paths; centralize configuration.
* **React + TypeScript** (for web tools/dashboards):

  * Functional components, hooks, and composition. Keep components small and testable.
  * State co-located or lifted thoughtfully; avoid unnecessary global state.
* **M365/SharePoint/Power Automate** (scripts/tools):

  * Prefer API-first, least-privilege access; handle token refresh and throttling.
  * Keep tenant/site IDs, list names, and secrets out of code; use env/config.

**Error Handling & Logging**

* Fail fast on invalid inputs. Validate early.
* Log actionable messages (who/what/where) with levels (INFO/WARN/ERROR).
* Surface human-readable errors; include remediation hints.

**Security & Data**

* No plaintext secrets, tokens, or connection strings in code or logs.
* Parameterize SQL; never string-concatenate queries.
* Sanitize/validate all external inputs (forms, params, files, tags).

**Testing & Maintainability**

* Write code that’s unit-test friendly: dependency injection, pure functions, stable interfaces.
* Provide small usage examples in docstrings where helpful.
* Prefer deterministic behavior; avoid hidden globals and time-dependent logic.

**Performance & Reliability**

* Readability first; optimize hotspots only with evidence.
* Use timeouts and bounded retries with jitter for I/O.
* Aim for idempotent operations, especially in automation and SCADA contexts.

**Conventions**

* Python: `snake_case` for functions/variables, `PascalCase` for classes.
* TypeScript/JS: `camelCase` for variables/functions, `PascalCase` for components.
* Timestamps stored/handled in **UTC**; when interacting with existing tables, prefer the canonical timestamp column name `Time_Stamp` when applicable.

**Behavior**

* When requirements are ambiguous, propose a clear, minimal default and annotate assumptions.
* Prefer explicit configuration and clear interfaces over “magic.”
* Generate code that’s consistent, documented, and easy to extend.