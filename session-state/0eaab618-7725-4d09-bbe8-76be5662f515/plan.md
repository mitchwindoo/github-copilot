# Manual Cubby Staging Page Plan (Testbed)

## Problem
Create a new manual loading page/workflow in `NxSigma_Testbed` by duplicating the existing Manual Load Station workspace and adapting it to a **non-PLC-interactive** flow:
- operator proofs/validates part data with UniPoint,
- operator confirms physical placement into a cubby,
- part is staged for later queue handoff,
- **no immediate PLC writes/handoffs in this flow**.

The 8:00 AM PLC queue handoff is explicitly out of scope for this change set.

## Proposed Approach
1. Duplicate the existing workspace view into Testbed as a new view resource.
2. Remove or bypass PLC-coupled prerequisite/start behaviors in the duplicated view.
3. Preserve UniPoint validation/proofing and staged-attribute persistence behavior.
4. Add a cubby-placement completion action that persists to the existing Testbed ProductionQueue model.
5. Expose the view on a dedicated page route and wire the BOI01 “Add Part to Cubby” entry point to the new Testbed view.
6. Validate behavior via project scan + browser validation loop + targeted script/log checks.

## Planned Change Surfaces
- `NxSigma_Testbed/com.inductiveautomation.perspective/views/...` (new duplicated/adapted workspace view)
- `NxSigma_Testbed/com.inductiveautomation.perspective/page-config/config.json` (new route)
- `NxSigma_Testbed/com.inductiveautomation.perspective/views/Embedded/Line/BOI01-PRODUCTION/view.json` (button wiring to new view)
- `NxSigma_Testbed/ignition/script-python/SHD/ProductionQueue/code.py` (only if needed for a queue-staging API boundary)
- `NxSigma_Testbed/ignition/named-query/ProductionQueue/...` (only if needed for durable cubby staging writes)
- Resource-level docs under `resources/docs/...` for each touched Perspective/script resource

## Todos
1. **Create Testbed manual cubby workspace view**
   - Copy `Embedded/Resources/41-MKIT/manualLoadStationWorkspace` into Testbed as a new workspace view resource.
   - Keep schema-safe event format (`config` + sibling `scope`/`type`).

2. **Decouple PLC start/prerequisite logic from page workflow**
   - Remove PLC readiness gates and PLC list-clearing/start-job side effects from the Testbed copy.
   - Update step labels/status objects to reflect UniPoint proof + cubby staging only.
   - Keep operator feedback through canonical top-nav toast payloads.

3. **Implement cubby placement staging into ProductionQueue persistence**
   - Map “part placed in cubby” to durable queue-aware state in existing Testbed ProductionQueue model.
   - Reuse existing query/script boundaries where possible; add minimal new named query/script wrapper only if no compatible write path exists.
   - Ensure failures are explicit (toast + logger), with no silent success defaults.

4. **Wire user access paths**
   - Add dedicated route in Testbed page-config (manual cubby page).
   - Update BOI01 “Add Part to Cubby” action to open/use the new Testbed workspace path.

5. **Validate and document**
   - Run targeted validation:
     - JSON integrity + Perspective action schema checks.
     - Ignition scan API (`scanActive: true`) after changes.
     - Browser route validation on localhost testbed page.
   - Update/create required resource-level docs for all touched views/scripts.

## Notes / Constraints
- In scope: staging workflow and persistence for overnight hold.
- Out of scope: scheduled 8:00 AM PLC queue handoff implementation.
- Maintain NxEdge style-system conventions and Perspective-view guardrails (`position.display`, `props.style.gap`, toast contracts, page-scoped sendMessage).

## Progress Update (2026-08-12)
- Completed:
  - Duplicated manual workspace into Testbed as `Embedded/Line/manualKitCubbyWorkspace`.
  - Wired BOI01 Add Part button to the new Testbed workspace.
  - Added Testbed route `/line/:lineId/manual-cubby`.
  - Applied initial PLC-safe staging adjustments (locked staging mode messaging and disabled direct line reset action in this workflow).
  - Started local Docker stack (`ignition-local`) after connectivity failure.
  - Verified gateway reachability on `8043` and `8088`.
  - Completed required filesystem scan API with local configured token (`scanActive: true`, HTTP 200).
- Remaining:
  - Complete browser validation loop for route and popup flows.
  - Confirm/finish durable ProductionQueue staging persistence path for cubby placement event.
  - Finish docs sync tasks for touched resources if required for this change set.
