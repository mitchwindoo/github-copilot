---
description: 'Require dispatched sub-agents to check in with the orchestrator on blockers, escalate to experts when needed, and escalate unresolved issues to the human.'
applyTo: '**'
---

# Sub-Agent Blocker Escalation Protocol

Use this protocol whenever an orchestrator agent dispatches one or more sub-agents.

## Core Model

- Treat each sub-agent like a junior engineer working in a partially unknown area.
- A sub-agent must not silently stall, guess, or skip blockers.
- The orchestrator owns unblocking and escalation.

## Sub-Agent Check-In Rules (Mandatory)

- On a blocker, the sub-agent shall pause implementation and check in with the orchestrator.
- A blocker includes: missing context, conflicting requirements, repeated failed attempts, tool limitations, or low confidence in a risky change.
- Before check-in, the sub-agent shall document what was attempted and why it failed.
- The sub-agent shall ask a focused unblocking question, not a vague status note.

## Required Check-In Format

Sub-agent check-ins should include:

1. **Task context**: what it was trying to complete.
2. **Current blocker**: exact obstacle and impact.
3. **Attempts made**: concrete steps already tried.
4. **Evidence**: logs/errors/files investigated.
5. **Unblocking request**: the precise question or decision needed.
6. **Proposed next step**: what it will do once unblocked.

## Orchestrator Escalation Flow

When a sub-agent checks in with a blocker, the orchestrator shall follow this sequence:

1. **Attempt direct unblock**: provide missing context, constraints, or a concrete decision.
2. **If still blocked, dispatch an expert agent**: route to the most relevant specialist with full context and explicit success criteria.
3. **If expert path fails or remains ambiguous, escalate to human**: present a concise decision request with options, tradeoffs, and recommended default.

## Expert Agent Dispatch Rules

- Use the narrowest expert capable of resolving the blocker.
- Include the full blocker package (context, attempts, evidence, and question).
- Require a direct recommendation and validation steps, not generic advice.
- If expert output is inconclusive after reasonable follow-up, stop and escalate to human.

## Human Escalation Rules

- Escalate when decisions are product-critical, ambiguous after expert review, or require business/domain authority.
- Provide:
  - short problem statement,
  - options considered,
  - risks/tradeoffs,
  - recommended option,
  - exact decision needed from the human.
- Do not continue with speculative assumptions once this threshold is reached.

## Prohibited Behaviors

- Silent failure or silent waiting by sub-agents.
- Repeating the same failed approach without new information.
- Escalating to human before attempting orchestrator and expert unblocking.
- Claiming completion when blocker resolution is still pending.

## Completion Condition

A blocked sub-task is complete only when it is:

- unblocked by orchestrator guidance, or
- resolved by an expert agent with actionable output, or
- explicitly handed to the human with a clear decision request.
