## Modbus SCADA Sync Foundation Plan

1. [x] Review repo change-control and source-editing instructions plus Modbus TCP AOI package details.
2. [x] Create a draft change record for initial Carefree Services SCADA/PLC sync foundation focused on Modbus AOI integration and verification behavior.
3. [x] Define a standard controller tag-to-Modbus register mapping pattern that is reusable across ControlLogix/CompactLogix controllers.
4. [x] Add instruction updates to enforce `CF_` prefix for any PLC tags read/written by SCADA.
5. [x] Summarize proposed implementation steps and next execution actions for source-level work in `src/controllers/<Controller>/RSLogix5000Content/`.

## Carefree_Standard Scaffold Execution

1. [x] Build and use Rockwell `l5xgit` toolchain required by `tools/logix/acd.ps1`.
2. [x] Explode `Carefree_Standard.ACD` into `src/controllers/Carefree_Standard`.
3. [x] Scaffold first modular comm routine set (`MainRoutine` + `_01_CommsSyncJSR`).
4. [x] Scaffold first comm tag set with UNS-aligned `CF_` SCADA interface tags.
5. [x] Validate tree integrity via `pwsh tools/logix/acd.ps1 -FromDir ... -ToL5X ... -Force`.
