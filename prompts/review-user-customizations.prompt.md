---
name: review-user-customizations
description: "Inventory and review user-level Copilot skills, instructions, prompts, and agents, with flags for items that should move to repository scope."
mode: agent
---

Review the Copilot customizations in this user directory.

1. Run `pwsh ./bin/review-customizations.ps1`.
2. Read `CUSTOMIZATIONS.md`, `customization-scope.json`, and `instructions/customization-placement.instructions.md`.
3. Inspect every item under **Placement flags** and verify the evidence in the source file.
4. Identify duplicate, conflicting, stale, overly broad, or repository-specific customizations.
5. Recommend one action for each finding: keep in user space, move to a repository, split reusable and local content, merge, revise, or remove.
6. Do not move or delete files without explicit approval.
7. Finish by running `pwsh ./bin/review-customizations.ps1 -Check`.

Report counts by type, placement findings, high-impact conflicts, and the smallest ordered cleanup plan.
