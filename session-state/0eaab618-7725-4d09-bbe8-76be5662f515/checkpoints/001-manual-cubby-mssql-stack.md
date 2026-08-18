<overview>
The user had two main goals: (1) create a new Testbed manual-cubby workflow page based on the existing manual load workspace, and (2) add a local MSSQL service to the Docker dev stack with schema/bootstrap aligned to Ignition named-query database connection names. The approach was to implement directly in repo files, validate via local Docker/Gateway checks, and keep the workflow non-PLC for staging while preserving queue/UniPoint behavior where applicable. A key requirement was to run the Ignition project scan API after changes; this was initially blocked by a down container, then corrected by starting Docker and re-running checks.
</overview>

<history>
1. User requested a plan for a new manual loading page/workflow (manual kit operations) in Testbed, duplicating `manualLoadStationWorkspace` and adapting it to non-PLC cubby staging.
   - Loaded relevant Perspective/view/toast/style instructions.
   - Discovered source view path in Core and current Testbed BOI01 entrypoint/popup wiring.
   - Asked clarifications:
     - Include 8:00 AM PLC handoff now? User said **no** (follow-up).
     - Access path? User chose **new route + BOI01 button wiring**.
     - Persistence target? User chose **existing ProductionQueue model**.
   - Created a detailed implementation plan and todo entries.

2. Implemented initial manual-cubby workflow changes.
   - Duplicated Core manual load workspace into Testbed as `Embedded/Line/manualKitCubbyWorkspace`.
   - Added Testbed page route `/line/:lineId/manual-cubby`.
   - Rewired BOI01 “Add Part to Cubby” popup to new Testbed workspace.
   - Applied initial staging-mode safety edits in duplicated view:
     - `testMode` default set true.
     - test-mode banner/button messaging changed to “staging mode locked.”
     - direct reset action replaced with warning toast.
     - several step labels renamed from PLC-send language to staging/deferred-handoff language.
   - JSON parse validation passed.

3. Required Ignition scan failed due connectivity.
   - Initial scan attempt to `https://localhost:8043/data/api/v1/scan/projects` failed (no service reachable).
   - Reported blocked state.

4. User corrected process expectation (check/start Docker automatically if down).
   - Acknowledged and immediately checked Docker/compose status.
   - Started local stack with `docker-compose.local.yml`.
   - Waited for gateway `RUNNING`, retried scan.
   - Default token returned 401; retried using token from local `.config/ignition/gateway.env`.
   - Scan succeeded (`scanActive: true`, HTTP 200).
   - Updated plan progress and unblocked validation todo.

5. User requested adding MSSQL to stack with matching schema/connection names.
   - Inspected named-query `resource.json` values and identified DB names:
     - `SmallHoleDrilling`, `DevMS`, `Epicor_SQL_Server`, `NxLambda`, `NXSIGMA_PRODUCTION_DATA`, `SHD_ERP`.
   - Added MSSQL service + init service + bootstrap SQL scripts + setup docs.
   - Encountered multiple runtime issues while trying to finalize:
     - `mssql-init` initially failed due sqlcmd path mismatch in image.
     - Fixed script to auto-detect sqlcmd path.
     - SQL Server containers crashed repeatedly (SQLPAL/AppLoader fatal) while using bind-mounted data dir and multiple image variants.
     - Switched to Docker managed named volume and reset stack; this resolved startup/initialization.
   - Latest state before compaction: `mssql`, `mssql-init`, and `ignition` came up successfully; `mssql-init` logs show bootstrap completed.
</history>

<work_done>
Files updated/created:

- **Modified** `docker-compose.local.yml`
  - Added `mssql` service (currently `mcr.microsoft.com/mssql/server:2022-latest`, linux/amd64, port 1433).
  - Added `mssql-init` one-shot bootstrap service using `mssql-tools`.
  - Added robust sqlcmd discovery logic in init command.
  - Added dependency chain so `ignition` waits for `mssql-init` completion and `ignition-init`.
  - Added named volume `mssql-local-data` (critical change from bind mount).

- **Created** `scripts/sqlserver/init/00-create-databases.sql`
  - Creates databases matching named-query datasource database names:
    - `SmallHoleDrilling`, `DevMS`, `Epicor_SQL_Server`, `NxLambda`, `NXSIGMA_PRODUCTION_DATA`, `SHD_ERP`.

- **Created** `scripts/sqlserver/init/10-smallholedrilling-schema.sql`
  - Bootstraps core schema in `SmallHoleDrilling` for queue/dev:
    - `Job`, `JobOperation`, `ResourceGroup`, `ResourceItem`
    - `ProductionQueueJobPriority`, `ProductionQueueDurationOverride`, `ProductionQueueShelfLocation`
    - `ProductionQueueReconciliationCheckpoint`, `ProductionQueueReconciliationEvent`
    - utility tables `FaultLog`, `ProcessCells`, `EquipmentMaintenance`
  - Adds key indexes and seed shelf rows.

- **Modified** `.gitignore`
  - Added `.mssql-local/` ignore entry (kept from earlier bind-mount attempt; now using named volume but harmless).

- **Modified** `SETUP.md`
  - Updated setup language to include local SQL service in stack and local DB bootstrap behavior.
  - Added SQL password override note.
  - Added datasource-name mapping note.

- **Created** session plan note:
  - `C:\Users\MitchellLandreth\.copilot\session-state\...\plan.md`
  - Includes progress updates and remaining actions.

- **Modified** Perspective workflow files (earlier request):
  - `NxSigma_Testbed/com.inductiveautomation.perspective/views/Embedded/Line/manualKitCubbyWorkspace/view.json` (new copied/adapted view)
  - `NxSigma_Testbed/com.inductiveautomation.perspective/views/Embedded/Line/manualKitCubbyWorkspace/resource.json` (copied)
  - `NxSigma_Testbed/com.inductiveautomation.perspective/page-config/config.json` (added manual-cubby route)
  - `NxSigma_Testbed/com.inductiveautomation.perspective/views/Embedded/Line/BOI01-PRODUCTION/view.json` (rewired popup path/text)

Completed outcomes:
- [x] Manual-cubby view duplicated and wired into Testbed route + BOI01 entrypoint.
- [x] Ignition scan requirement eventually satisfied after container startup (`scanActive: true`, 200).
- [x] MSSQL service + bootstrap scripts integrated into compose and docs.
- [x] MSSQL init execution now reaches completion message.

Current state:
- Compose recently reached:
  - `mssql` up
  - `mssql-init` exited 0
  - `ignition` started (health starting at last check)
- Not yet fully re-verified after final MSSQL changes with explicit SQL query checks listing DBs/tables (this was the next immediate verification step when compaction request arrived).
</work_done>

<technical_details>
- Critical local workflow requirement: after any repo file edits, run Ignition project scan API on `https://localhost:8043/data/api/v1/scan/projects`.
- Gateway connectivity/process lesson: if scan/connectivity fails, first verify Docker stack status and start it.
- Token behavior:
  - “Copilot_Test:…” token failed (401) once gateway was running.
  - Local token from `.config/ignition/gateway.env` succeeded for scan.
- SQL container instability root cause path:
  - Initial failures included `sqlcmd` binary path mismatch in init image and SQLPAL crashes.
  - Significant stabilization came from switching SQL data persistence to **Docker named volume** instead of host bind mount for `/var/opt/mssql`.
- `mssql-init` command needed escaping for compose interpolation:
  - Shell variable references required `$$` in YAML command string.
- Database naming decision:
  - Matched named-query `resource.json` database names so local Ignition datasource naming can map cleanly.
- Schema scope:
  - Focused on `SmallHoleDrilling` tables required by ProductionQueue and related job/resource queries plus known create-table resources.
  - Other DBs created as placeholders for connectivity/name parity.
- Remaining uncertainty:
  - Whether all named queries across all projects can execute against this bootstrap schema (likely not full ERP parity); current schema is development-oriented, queue-centric bootstrap, not a full production clone.
</technical_details>

<important_files>
- `docker-compose.local.yml`
  - Central orchestration for Ignition + MSSQL + init lifecycle.
  - Most important changes: `mssql`/`mssql-init` services, named volume, dependency gating, sqlcmd auto-discovery logic.
  - Key sections: service definitions at top, `ignition.depends_on`, bottom `volumes:` block.

- `scripts/sqlserver/init/00-create-databases.sql`
  - Ensures local DB names match project expectations from named-query metadata.
  - Foundation for datasource parity in dev.

- `scripts/sqlserver/init/10-smallholedrilling-schema.sql`
  - Core local schema bootstrap for queue and job/resource operations.
  - Defines tables/indexes used by `NxSigma_Testbed` ProductionQueue named queries and several core utilities.

- `SETUP.md`
  - Developer onboarding and local run instructions.
  - Updated to reflect SQL stack inclusion, password/env controls, and expected local DB names.

- `NxSigma_Testbed/com.inductiveautomation.perspective/page-config/config.json`
  - Added `/line/:lineId/manual-cubby` route to reach new workflow directly.

- `NxSigma_Testbed/com.inductiveautomation.perspective/views/Embedded/Line/BOI01-PRODUCTION/view.json`
  - BOI01 “Add Part to Cubby” action now opens new Testbed manual-cubby workspace.

- `NxSigma_Testbed/com.inductiveautomation.perspective/views/Embedded/Line/manualKitCubbyWorkspace/view.json`
  - Copied/adapted workflow view for staging-mode operation; contains initial PLC-safe behavior edits and text changes.

- `.config/ignition/gateway.env`
  - Source of working local API token used for successful scan call; important for local gateway automation calls.
</important_files>

<next_steps>
1. Final runtime verification (finish the “done” criteria for MSSQL addition):
   - Confirm compose steady state:
     - `mssql` running
     - `mssql-init` exited 0
     - `ignition` healthy
   - Run SQL connectivity check via `sqlcmd` and verify:
     - DB existence for all 6 expected names
     - table existence in `SmallHoleDrilling` for key bootstrap tables.

2. Validate Ignition still accessible with new dependency chain:
   - `StatusPing`/gateway health check.
   - Re-run project scan API once stable.

3. Optional cleanup/hardening:
   - Keep `.mssql-local/` ignore entry only if still desired (now using named volume).
   - Consider adding a short troubleshooting note in `SETUP.md` for SQL startup delays and first-run image pulls.

4. Todo state sync:
   - Mark MSSQL-related todos done after SQL/table verification passes.
   - Keep validation/doc todo aligned with final verification evidence.
</next_steps>