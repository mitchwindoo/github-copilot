<overview>
The user asked to establish a reusable Carefree PLC↔SCADA communication foundation around Modbus and robust heartbeat supervision, enforce strict naming/comment standards, and keep implementation synchronized back to the original Studio 5000 `.ACD` file. The approach was to first codify standards in repo instructions, then scaffold and iteratively harden the controller logic in exploded Logix source, validating by repeated implode/rebuild cycles. Key constraints included Carefree-specific UNS naming (`CF_`), Modbus server-only behavior, mandatory detailed comments/tag descriptions, and consistent write-back to the canonical ACD path.
</overview>

<history>
1. User asked to start new work from `Carefree_Standard.ACD`, review Modbus AOI package, create implementation plan, and enforce `CF_` prefix for SCADA read/write tags.
   - Reviewed repo instruction files and Modbus AOI package contents (`v2.04`), including client/server L5X artifacts and docs.
   - Created a draft implementation change record and a session plan artifact.
   - Updated instruction docs to require `CF_` prefix and aligned naming guidance.
   - Outcome: planning + policy baseline established.

2. User asked to incorporate Carefree UNS naming standards into PLC instructions.
   - Updated instruction docs with explicit UNS mapping rules (`Customer/Location/Asset/Equipment/TagName`), command naming (`CMD_` behavior), alarm qualifiers, units, and `_PB` pushbutton convention.
   - Outcome: UNS policy embedded in PLC instruction set.

3. User asked to explode ACD and scaffold first modular comm routine/tag set.
   - Initial explode failed due to missing Rockwell `l5xgit`.
   - Built Rockwell VCS tooling from pinned revision (`d10fae3...`) under `C:\RA\ra-logix-designer-vcs-custom-tools`.
   - Explode of original ACD failed due to file lock; copied ACD to repo `build`, exploded successfully to `src/controllers/Carefree_Standard`.
   - Scaffolded first comm routine and tags in `MainProgram`, validated via implode to L5X.
   - Outcome: initial comm scaffold completed.

4. User clarified Carefree Modbus standard: PLC should only publish/readout for radio; PLC should not read Modbus from others.
   - Updated instructions to encode server/read-oriented Modbus role.
   - Simplified scaffold logic to remove inbound-style assumptions and removed now-unneeded tags.
   - Updated change record language to match server-only posture.
   - Outcome: implementation and policy aligned with one-way Modbus role.

5. User asked to enforce “always implode back to original ACD path” in instructions and then execute it.
   - Added explicit instruction section requiring write-back to canonical engineer-provided ACD path.
   - First write-back attempt failed due to file lock; after user confirmation that file was closed, retry succeeded.
   - Outcome: policy added and canonical ACD write-back verified.

6. User requested mandatory detailed code comments and mandatory tag `<Description>` usage.
   - Updated instruction files with stricter comment/description requirements.
   - Added detailed comments to routine and descriptions to comm tags.
   - Re-validated and wrote back to canonical ACD.
   - Outcome: enforced and demonstrated in active code.

7. User asked how to make comm logic more robust.
   - Provided architecture recommendations (time-based logic, state machine, lockout/rate limiting, grace period, relay feedback, inhibit controls, richer diagnostics, tests).
   - User requested implementation of all recommendations and asked about auto-inhibit from active Studio 5000 session.

8. Implemented robust v2 communication supervisor.
   - Reworked routine into full state-machine-driven supervisor with:
     - time-based parameters (`ms`) using task period accumulation,
     - stale detection via returned heartbeat,
     - reboot pulse control,
     - recovery grace,
     - reboot rate limiting and lockout,
     - maintenance/auto inhibit,
     - relay feedback failure handling,
     - diagnostics and alarm tags.
   - Added comprehensive new tag set with descriptions.
   - Added a new test plan YAML for `Carefree_Standard` comm supervisor behaviors.
   - Clarified in comments that PLC has no reliable native “Studio 5000 session active” bit; external integration should drive `CF_CMD_Comms_AutoRebootInhibit`.
   - Validated to L5X; one ACD write-back attempt failed on file lock, then succeeded after user closed file.
   - Outcome: robust comm supervisor implemented.

9. User asked to remove `_001_` from tag names.
   - Renamed comm tags/routine references to remove `_001_`.
   - Re-validated and wrote to canonical ACD.
   - Outcome: naming simplified.

10. User asked whether comm tags should live in a separate program; then asked to do it.
   - Created dedicated `CommsProgram`, moved comm routines/tags from `MainProgram`, scheduled `CommsProgram` in `MainTask`.
   - Updated comm test plan XPath from `MainProgram` to `CommsProgram`.
   - Re-validated and wrote back to canonical ACD.
   - Outcome: architectural separation completed.

11. User asked for even more detailed comments and then asked to split routines between SCADA interface logic vs IO radio reboot actions.
   - Expanded comments in comm routine with step-by-step detail.
   - Then split routine into:
     - `_01_CommsScadaSyncJSR` (SCADA-facing supervision logic),
     - `_02_CommsRadioIoJSR` (relay/reboot IO execution).
   - Updated `CommsProgram` main routine to call both in order.
   - Re-validated and wrote back to canonical ACD successfully.
   - Outcome: functional split completed with detailed commentary.
</history>

<work_done>
Files updated/created (major):
- `.github/instructions/l5x-source.instructions.md`
  - Added/expanded rules for UNS alignment, `CF_` requirement, detailed comments, tag descriptions, Modbus server-only standard, canonical ACD write-back workflow, and stricter comment/description quality expectations.
- `.github/instructions/structured-text.instructions.md`
  - Added stronger mandatory comment-depth rules and ADHD-friendly comment structure guidance.
- `docs/standards/naming-conventions.md`
  - Added Carefree UNS-aligned SCADA naming rules and `CF_` mapping guidance.
- `changes/CR-20260811-carefree-scada-modbus-foundation.md`
  - Created and updated draft CR with plan and evolving Modbus/comm strategy.
- `src/controllers/Carefree_Standard/...` (exploded source tree)
  - Initially scaffolded in `MainProgram`, later refactored to dedicated `CommsProgram`.
  - Created `CommsProgram` with routines and moved comm tags there.
  - Implemented robust supervisor state machine and later split into two routines:
    - `_01_CommsScadaSyncJSR.st`
    - `_02_CommsRadioIoJSR.st`
  - Updated `CommsProgram/Routines/MainRoutine.st` to call both.
  - Updated `Tasks/MainTask.xml` to schedule `CommsProgram`.
- `tests/cases/carefree-comms-supervisor.tests.yaml`
  - Added new test plan for comm supervisor behavior and updated XPath target program to `CommsProgram`.

Work completed:
- [x] Policy baseline for SCADA naming and Modbus role established.
- [x] ACD exploded to local source tree.
- [x] Robust communication supervisor implemented.
- [x] `_001_` naming removed from comm tags.
- [x] Comm architecture moved to dedicated `CommsProgram`.
- [x] Logic split between SCADA supervision and IO reboot execution routines.
- [x] Multiple successful implodes and canonical ACD write-backs.

Current state:
- Works: split comm architecture, robust supervisor, detailed comments, tag descriptions, ACD write-back flow.
- Known caveat: canonical ACD frequently becomes file-locked if Studio 5000 (or another process) is open; retries after closing lock-holder succeed.
- Untested runtime behavior on actual hardware/radio remains noted in test-plan `not_covered`.
</work_done>

<technical_details>
- Toolchain dependency discovered: `l5xgit` not installed initially; built from Rockwell repo at pinned revision `d10fae3d35b240ca6bf38fe83ec633b02ae5b9dc`.
- ACD lock behavior:
  - Converting directly from locked ACD fails.
  - Workaround for explode: copy ACD to temporary file in `build/`, then convert.
  - For final write-back, target canonical ACD must be closed by Studio 5000/other holder.
- Modbus design decision:
  - Carefree standard set to PLC-published telemetry (server role), no Modbus client polling for baseline path.
- SCADA naming decisions:
  - `CF_` prefix mandatory for SCADA-facing tags.
  - UNS-compatible `TagName` semantics enforced.
- Robust comm logic now includes:
  - state machine (`DISABLED`, `HEALTHY`, `STALE_PENDING`, `POWER_CYCLE_ACTIVE`, `RECOVERY_GRACE`, `LOCKOUT`),
  - heartbeat + checksum,
  - stale detection based on returned heartbeat change,
  - configurable timeout and reboot pulse,
  - reboot rate limiting per window,
  - lockout and reset PB,
  - maintenance/auto inhibit,
  - relay feedback optional validation,
  - rich diagnostic/alarm/status tags.
- Studio 5000 active-session auto-inhibit:
  - No reliable native PLC bit was identified for “Studio 5000 session active”.
  - Implemented `CF_CMD_Comms_AutoRebootInhibit` as externally driven integration point.
- Commenting/documentation standard evolved:
  - user requested highly explicit block-level, branch-level, result/action/safety commentary.
  - instruction files updated accordingly.
- “Install and utilize i-have-adhd skill” request:
  - direct runtime skill invocation failed (skill not available in environment).
  - its guidance was fetched from GitHub and incorporated into instruction style updates (action-first/structured clarity principles).
- Potential inconsistency to verify:
  - During iterative refactors, one earlier large routine variant was replaced/split; should re-open final split routines to ensure all intended robust behaviors are preserved exactly as expected (especially lockout/recovery transitions and cross-routine state ownership).
</technical_details>

<important_files>
- `.github/instructions/l5x-source.instructions.md`
  - Why important: primary PLC source editing policy and new hard requirements.
  - Changes: added CF/UNS standards, Modbus role, canonical ACD write-back requirement, detailed comment/tag-description quality bar.
  - Key sections: Hard rules, SCADA UNS mapping, Comment/tag-description quality bar, Local implementation file consistency.

- `.github/instructions/structured-text.instructions.md`
  - Why important: coding style contract for all ST logic.
  - Changes: strengthened mandatory detailed-comment requirements and structure expectations.
  - Key sections: Formatting, Comment depth standard, ADHD-friendly structure.

- `src/controllers/Carefree_Standard/RSLogix5000Content/Programs/CommsProgram/Routines/_01_CommsScadaSyncJSR.st`
  - Why important: SCADA-facing supervision core (heartbeat, stale detection, transitions).
  - Changes: created during split; contains state transitions and non-IO supervisory logic with detailed comments.
  - Key sections: config clamping, heartbeat/return freshness, stale->reboot decision gates, lockout/reset paths.

- `src/controllers/Carefree_Standard/RSLogix5000Content/Programs/CommsProgram/Routines/_02_CommsRadioIoJSR.st`
  - Why important: IO-side execution for radio relay reboot and recovery.
  - Changes: created during split; contains relay command behavior, feedback validation, recovery grace actions.
  - Key sections: POWER_CYCLE_ACTIVE handling, relay feedback failure path, RECOVERY_GRACE transitions.

- `src/controllers/Carefree_Standard/RSLogix5000Content/Programs/CommsProgram/Routines/MainRoutine.st`
  - Why important: orchestration order for split routines.
  - Changes: now calls `_01_CommsScadaSyncJSR` then `_02_CommsRadioIoJSR`.

- `src/controllers/Carefree_Standard/RSLogix5000Content/Tasks/MainTask.xml`
  - Why important: scheduler wiring.
  - Changes: added scheduled `CommsProgram` entry.

- `src/controllers/Carefree_Standard/RSLogix5000Content/Programs/CommsProgram/Tags/` (folder)
  - Why important: full comm interface/state/config/diagnostic tag set now centralized in dedicated program.
  - Changes: moved from `MainProgram`; expanded significantly for robust supervisor.
  - Key files: `CF_CMD_Comms_*`, `CF_Comms_*`, `COMMS_STATE_*`, and internal `Comms_*` accumulators/caches.

- `tests/cases/carefree-comms-supervisor.tests.yaml`
  - Why important: regression scaffold for comm behavior.
  - Changes: created and pointed to `CommsProgram` tag paths.
  - Key sections: cases for heartbeat progression, stale timeout behavior, grace/reboot/lockout/inhibit/reset patterns.

- `changes/CR-20260811-carefree-scada-modbus-foundation.md`
  - Why important: change-control record for this initiative.
  - Changes: created and updated to reflect evolving design (server-only Modbus posture, comm strategy).
</important_files>

<next_steps>
1. Re-verify final split logic coherence end-to-end:
   - Confirm `_01_CommsScadaSyncJSR` and `_02_CommsRadioIoJSR` together preserve all previously implemented robust behaviors (no lost transitions/flags during split).
2. Review and tune default timing values in `CF_CMD_Comms_*Ms` tags against actual task period and expected one-minute/30-minute/5-second behavior.
3. Validate test plan compatibility with current final state logic and constants; run targeted comm supervisor tests when harness/environment is available.
4. Optionally add/adjust lockout and alarm reset behavior per operations preference (e.g., stale event counter reset conditions).
5. Continue enforcing detailed comments/tag descriptions on any additional refactors.
</next_steps>