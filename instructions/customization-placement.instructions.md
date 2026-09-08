---
description: 'Rules for deciding whether Copilot skills, instructions, prompts, and agents belong in user space or a repository'
applyTo: 'skills/**/SKILL.md, agents/**/*.agent.md, prompts/**/*.prompt.md, instructions/**/*.instructions.md, copilot-instructions.md, customization-scope.json'
---

# Copilot customization placement

Apply the narrowest scope that provides the required context. Global user-space guidance affects unrelated repositories, so it must remain portable and broadly correct.

## Placement rules

| Placement | Use when | Avoid when |
| --- | --- | --- |
| User | The customization is useful across unrelated repositories and does not depend on one project's structure, commands, services, or policies. | It names a client, internal service, repository path, deployment target, or project-only convention. |
| Repository | The customization encodes architecture, commands, domain rules, infrastructure, data models, or team policy that is only correct for one repository or a tightly related repository set. | The same capability can be used unchanged in unrelated work. |
| Split | A reusable workflow has a project-specific adapter, examples, or policy layer. | Splitting would only duplicate generic text. |
| Review | Automated evidence suggests narrower scope, but intent is not yet documented. | A deliberate placement decision already exists. |

## Decision test

Keep an item in user space only when every answer is **yes**:

1. Would it remain correct in an unrelated repository?
2. Does it avoid organization, client, environment, host, vault, and deployment-specific details?
3. Does it avoid assuming repository paths, frameworks, commands, schemas, or naming conventions?
4. Would loading it globally improve behavior without creating conflicting instructions?
5. Can it be shared publicly without exposing internal operating context?

If the reusable method is valuable but examples or policy are local, split the generic core into user space and move the local layer into the repository.

## Persistent decisions

- Add narrow automatic review indicators to `customization-scope.json`.
- Add an override only after a human placement decision.
- Use `repository` for items that should move; do not silently move files during an inventory review.
- Include a concrete reason so future reviewers can reassess the decision.
- Remove obsolete overrides when an item is generalized or relocated.

## Review cadence

- Regenerate `CUSTOMIZATIONS.md` after adding, renaming, or materially changing a customization.
- Review placement flags before committing.
- Review all user-space customizations quarterly for overlap, stale guidance, and accidental project coupling.
- Re-run the catalog after moving an item to confirm it is no longer globally active.
