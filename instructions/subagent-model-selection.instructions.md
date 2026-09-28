---
description: 'Select subagent models by task complexity, context needs, and validation risk.'
applyTo: '**'
---

# Subagent Model Selection

Use the smallest capable model for each bounded delegation. Provide the task
objective, relevant files or symbols, constraints, observable acceptance criteria,
and required validation command.

| Task | Preferred models |
| --- | --- |
| Simple lookup, repetitive edit, or lightweight explanation | `gpt-6-luna` |
| Focused coding, review, documentation, or ordinary agent task | `gpt-5.6-terra` or `gpt-5.3-codex` |
| Multi-file debugging, architecture, or deep codebase reasoning | `gpt-5.6-sol`, `claude-sonnet-5`, or `claude-opus-5` |
| Long-running autonomous implementation or complex recovery | `gpt-6-astra`, `claude-fable-5.1`, or `claude-opus-5.5` |
| Screenshot, diagram, or UI analysis | `gpt-5.6-terra` or `claude-sonnet-5` |

## Delegation Rules

- Delegate only work that materially benefits from isolated context or parallel execution.
- Run agents in parallel only when their scopes are independent and non-overlapping.
- Use stronger reasoning models only when task complexity, uncertainty, or blast radius warrants them.
- Increase reasoning effort for architectural, debugging, safety-critical, and cross-cutting work; reduce it for mechanical work.
- Review delegated output and run the relevant validation before integrating it.
- When the task is ambiguous, plan or investigate before assigning implementation.

## Reference

Review these sources periodically before changing this policy or selecting unfamiliar models:

- https://docs.github.com/en/copilot/reference/ai-models/model-comparison
- https://code.visualstudio.com/docs/agents/best-practices#_choose-the-right-model
