---
name: verification-loop
description: Verify completed code changes with the repository's build, type, lint, test, security, and diff checks before claiming readiness.
metadata:
  origin: ECC
  adapted_for: GitHub Copilot
---

# Verification Loop

Use after a feature, bug fix, refactor, configuration change, or before a pull request.

## Required Sequence

1. **Inspect the change**: review status, diff, changed files, and the relevant tests.
2. **Build**: run the repository's documented build or compile command.
3. **Types/static checks**: run the narrowest applicable type checker or analyzer.
4. **Lint/format**: run the repository's configured lint or formatting check.
5. **Tests**: run targeted tests first, then the smallest broader suite needed for confidence.
6. **Security**: use the repository's existing secret scanner and security checks; inspect changed trust boundaries manually.
7. **Diff review**: confirm no unrelated files changed, errors are surfaced, and edge cases are covered.

## Rules

- Discover commands from project manifests and documentation; do not assume npm, pnpm, pytest, or Unix shell syntax.
- Stop and fix build or test failures before declaring the change ready.
- Do not report a check as passed when it was skipped or unavailable.
- Prefer targeted checks, but escalate when the change crosses module or integration boundaries.
- Keep credentials, tokens, and private data out of commands and logs.

## Report

Return:

```text
VERIFICATION REPORT
Build: PASS/FAIL/SKIPPED
Types/static checks: PASS/FAIL/SKIPPED
Lint/format: PASS/FAIL/SKIPPED
Tests: PASS/FAIL/SKIPPED
Security: PASS/FAIL/SKIPPED
Diff review: PASS/FAIL
Overall: READY/NOT READY
Issues: numbered list with evidence and next remediation
```

