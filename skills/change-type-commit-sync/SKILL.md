---
name: change-type-commit-sync
description: 'Commit and sync repository changes in a focused thread. Use when: user asks to commit modified files by change type, split work into logical commits, write detailed commit messages, push, sync, publish, or update origin after changes.'
argument-hint: 'Optional: commit style, branch/remote target, files to include or exclude'
model: gpt-5-mini
---

# Change-Type Commit Sync

Run a focused Git workflow that reviews modified files, groups them by change type, creates one or more well-formed commits with detailed messages, and syncs the branch to origin.

## Model Requirement

Always run this workflow using the GPT-5 mini model. If the current thread is using a different model and the environment supports model selection or subagent model selection, switch to GPT-5 mini before inspecting, staging, committing, or syncing changes. If the environment cannot switch models from within the skill, stop and tell the user that GPT-5 mini must be selected manually before continuing.

## When to Use

- The user asks to commit current work, publish changes, push to origin, or sync a branch.
- The user asks to split modified files into commits by change type.
- The user wants detailed commit messages that explain what changed and why.
- The user wants a dedicated thread to perform Git hygiene after implementation is complete.

## Outcomes

The thread should produce:

- A concise inventory of changed files and which ones will be included.
- Logical commit groups by change type.
- One commit per meaningful group unless the user requests a single commit.
- Detailed commit messages with a clear subject and explanatory body.
- A synced branch, pushed to the configured origin/upstream.
- A final summary with commit hashes, messages, pushed branch, and any files intentionally left uncommitted.

## Procedure

### 1. Establish Boundaries

1. Read the user's request carefully for include/exclude rules, preferred commit style, branch target, and whether syncing means push only or pull/rebase plus push.
2. Inspect repository state before staging anything:

```bash
git status --short --branch
git diff --name-status
git diff --stat
git diff --cached --name-status
```

3. If there are already staged changes, treat them as user-owned until proven otherwise. Ask before unstaging, reshaping, or combining them.
4. Never revert, reset, delete, or overwrite unrelated work. If unrelated dirty files exist, leave them uncommitted and mention them in the final summary.
5. If a file contains mixed unrelated edits, use a precise staging method such as patch staging or ask for guidance if the split cannot be made safely.

### 2. Classify Changes

Group files by intent, not just extension. Use these default change types:

| Change Type | Include |
|-------------|---------|
| Feature | New user-facing behavior, workflows, views, scripts, APIs |
| Fix | Bug fixes, safety guards, compatibility corrections |
| Data | Named queries, migrations, tag resources, schema changes |
| UI | Perspective views, styles, page configs, visual assets |
| Tests | Verification scripts, test fixtures, diagnostics |
| Docs | README, task notes, runbooks, design docs |
| Chore | Build, config, formatting, tooling, metadata |

Prefer fewer, coherent commits over tiny file-by-file commits. Split commits when the changes would be reviewed, reverted, or explained independently.

### 3. Review Before Commit

For each proposed group:

1. Inspect the actual diff, not only filenames.
2. Confirm the group has a single understandable purpose.
3. Run appropriate verification before committing when practical. Use the repo's existing test, lint, parse, or diagnostics commands. If verification is unavailable, say so.
4. If verification fails for in-scope changes, fix the issue before committing. If failure is unrelated, document it clearly and do not broaden the commit to fix it unless requested.

### 4. Stage Precisely

1. Stage only files belonging to the current group.
2. Re-check staged content:

```bash
git diff --cached --name-status
git diff --cached --stat
git diff --cached
```

3. Confirm no excluded or unrelated file is staged.
4. If generated files are included, make sure they are necessary source artifacts for the project and not runtime output.

### 5. Write Detailed Commit Messages

Default to conventional commit prefixes (`feat`, `fix`, `docs`, `test`, `chore`, `refactor`, or `data`) unless the repository clearly uses another style. Use this format:

```text
<type>: <short imperative summary>

Why:
- <reason this change was needed>

Changed:
- <specific behavior/resource/file-area changed>
- <specific behavior/resource/file-area changed>

Verified:
- <test, parser, diagnostic, or manual verification performed>
```

Guidelines:

- Keep the subject specific and under about 72 characters when possible.
- Choose the conventional prefix from the change type, such as `fix` for bug fixes, `feat` for new behavior, `data` for queries/migrations, and `docs` for documentation.
- Mention important migrations, deployment steps, or manual verification in the body.
- Do not claim tests passed unless they were actually run.
- Include known test gaps or skipped verification honestly.

### 6. Commit Each Group

1. Commit the staged group with the prepared detailed message.
2. Record the resulting short hash and subject.
3. Repeat classify, stage, review, and commit for each remaining group.
4. After the last commit, run `git status --short --branch` and confirm only intentionally uncommitted files remain.

### 7. Sync to Origin

1. Identify the current branch and upstream:

```bash
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name @{u}
```

2. Fetch remote updates before pushing:

```bash
git fetch --prune
```

3. If the branch has no upstream, push with `-u origin <branch>` unless the user specified another remote or target.
4. If upstream is ahead, stop and report the divergence before rebasing or merging. Ask for confirmation even if the rebase appears safe.
5. After confirmation, prefer a linear sync using `git pull --rebase` when the working tree is clean. If unrelated uncommitted files remain, use a safe strategy that preserves them, such as `git pull --rebase --autostash`, only after the user confirms that approach.
6. Resolve in-scope rebase conflicts if they occur. Do not resolve conflicts in unrelated user files without confirmation.
7. Push to origin:

```bash
git push
```

8. Confirm the final local/remote status with `git status --short --branch`.

## Decision Points

- **Single commit or split commits**: Split by reviewable intent unless the user explicitly asks for one commit.
- **Dirty worktree with unrelated files**: Commit only requested/in-scope files; leave the rest untouched.
- **Pre-existing staged changes**: Ask before changing them unless the user clearly asked to commit all staged work.
- **Mixed file changes**: Patch-stage if safe; otherwise ask which hunks belong.
- **Remote divergence**: Fetch first, then ask before any rebase or merge. Prefer rebase after confirmation unless the repo commonly uses merge commits.
- **Failed verification**: Fix in-scope failures before commit; report unrelated failures without sweeping them into the commit.

## Completion Checklist

Before final response, confirm:

- `git status --short --branch` was checked.
- Each commit contains only its intended change group.
- Commit messages include meaningful body details.
- Verification was run or a reason was given for not running it.
- The branch was pushed/synced to origin or a blocker was explained.
- Any remaining uncommitted files are listed as intentionally untouched.

## Final Response Format

Keep the final response concise and concrete:

```markdown
Committed and synced `<branch>` to `<upstream>`.

Commits:
- `<hash>` `<subject>` — <change group summary>
- `<hash>` `<subject>` — <change group summary>

Verification:
- <command/check>: <result>

Left uncommitted:
- <file or "None">
```
