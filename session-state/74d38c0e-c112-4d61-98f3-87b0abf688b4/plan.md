# Plan: Git History, Commit Restore, and Branch Management

## Problem

The manager currently only supports two git-backed workflows per repo mapping:
`Commit` (write sidecar + `l5xgit commit`) and `Pull and Restore` (`git pull` +
`l5xgit restoreacd`). There is no way to:

1. View prior commits / the repository's history graph.
2. Restore the ACD to the state of a specific (non-latest) commit.
3. Create, switch, or delete git branches.

This plan adds a new **Git History** window reachable from the main toolbar
(enabled only when a repo is selected and is a valid git working tree) that
covers all three asks.

## Approach

### 1. New read/write git service (separate from `L5xGitCliService`)

Add `Services/GitRepositoryService.cs` dedicated to git-native operations
(history, branches, working-tree state). Keep `L5xGitCliService` focused on
the `l5xgit`-orchestrated commit/restore workflow it already owns; the new
service only shells out to `git` itself, using the same `RunProcessAsync`-style
pattern (`ProcessStartInfo.ArgumentList`, streamed stdout/stderr, full
`AppLogger` coverage, cancellation support).

Planned methods:

- `GetCommitGraphAsync(repoPath, maxCount, ct)` — runs
  `git log --all --date=iso-strict --pretty=format:"%H%x1f%h%x1f%an%x1f%ad%x1f%s%x1f%D" --graph`
  and parses each line into a `GitCommitInfo`. The ASCII graph glyphs git emits
  before the formatted fields (`*`, `|`, `/`, `\`, spaces) are extracted with a
  regex that strips the trailing 40-hex-char SHA from the first field, so the
  leading non-hex prefix becomes the `GraphPrefix` rendered in a monospace
  column; the rest becomes the parsed metadata.
- `GetBranchesAsync(repoPath, ct)` — runs `git branch --list` (local) and
  `git branch -r` (remote) to build `GitBranchInfo` entries, flagging the
  current branch (`*` marker) and marking remote-only entries `IsRemote`.
  Remote branches are selectable for checkout (see `CheckoutBranchAsync`
  below) but are not directly deletable/renameable from this UI.
- `HasUncommittedChangesAsync(repoPath, ct)` — `git status --porcelain`;
  used as a safety gate before checkout/restore-commit.
- `CreateBranchAsync(repoPath, name, startPoint, onOutput, ct)` — `git branch <name> [<startPoint>]`, validates the name is non-empty and not already present.
- `CheckoutBranchAsync(repoPath, name, isRemote, onOutput, ct)` — blocks with
  an actionable error (not a silent stash) if uncommitted changes exist.
  For a local branch: `git checkout <name>`. For a remote branch
  (e.g. `origin/xyz`): derives the local tracking name (`xyz`), checks whether
  a local branch with that name already exists (checks it out directly if so,
  matching normal git behavior) and otherwise runs
  `git checkout --track -b <xyz> <origin/xyz>` to create the local tracking
  branch.
- `DeleteBranchAsync(repoPath, name, force, onOutput, ct)` — refuses to delete
  the current branch; tries `git branch -d` first, and only runs `git branch -D`
  when the caller explicitly confirms a force-delete after seeing the "not
  fully merged" failure.
- `RestoreCommitFilesAsync(repoPath, sha, onOutput, ct)` — `git checkout <sha> -- .`,
  which repopulates tracked working-tree files from that commit **without**
  moving `HEAD` or the current branch (keeps the destructive surface identical
  in shape to the existing restore workflow: overwritten working files, no
  branch/history rewrite).

### 2. Extract a restore-only path in `L5xGitCliService`

`PullAndRestoreAsync` currently couples `git pull` with `l5xgit restoreacd`.
Factor out a `RestoreAcdOnlyAsync(repo, l5xGitExePath, onOutput, ct)` (reusing
the existing `ValidatePathsForRestore` + `EnsureL5xGitYml` + `restoreacd`
process launch) so the new "restore this commit into the ACD" flow can run
`GitRepositoryService.RestoreCommitFilesAsync` followed by the same
`l5xgit restoreacd` step, without duplicating validation/sidecar logic.
`PullAndRestoreAsync` is refactored to call the extracted method after a
successful pull; its public behavior and log messages are unchanged.

### 3. New models

- `Models/GitCommitInfo.cs` — `Sha`, `ShortSha`, `Author`, `Date`, `Subject`,
  `RefNames` (branch/tag decorations), `GraphPrefix`.
- `Models/GitBranchInfo.cs` — `Name`, `IsCurrent`, `IsRemote`.

### 4. New ViewModel — `GitHistoryViewModel`

Owns: `ObservableCollection<GitCommitInfo> Commits`,
`ObservableCollection<GitBranchInfo> Branches`, `SelectedCommit`,
`SelectedBranch`, `IsBusy`, `StatusMessage`/log text (reusing the same
pattern as `MainViewModel`'s log panel). Commands:

- `RefreshCommand` — reloads commits + branches.
- `CreateBranchCommand` — opens a small name-input dialog, then calls
  `CreateBranchAsync`.
- `CheckoutBranchCommand` (CanExecute: a non-current branch selected) —
  confirms with the user, checks for uncommitted changes first and surfaces
  the block message if any exist.
- `DeleteBranchCommand` (CanExecute: a non-current branch selected) —
  confirms, attempts safe delete, offers a second explicit force-delete
  confirmation only on "not fully merged" failure.
- `RestoreCommitCommand` (CanExecute: a commit selected) — shows an explicit
  overwrite warning (mirrors the existing restore warning language), checks
  for uncommitted changes and requires a second confirmation to discard them,
  then runs `RestoreCommitFilesAsync` + `L5xGitCliService.RestoreAcdOnlyAsync`.

Every command follows existing conventions: `IsBusy` gating, cancellation via
a `CancellationTokenSource`, and `AppLogger` Info/Warn/Error calls at start,
validation failure, and completion — matching the repo's logging standard.

### 5. New Views

- `Views/GitHistoryWindow.xaml` (+ code-behind) — modal-ish window (owned by
  `MainWindow`, non-modal so the log stays visible) with:
  - Left panel: branch list (current branch highlighted) with
    New/Checkout/Delete buttons.
  - Right panel: commit list rendered as a `ListView`/`ItemsControl` with a
    monospace `GraphPrefix` column plus short SHA, author, date, subject, and
    ref decorations columns; a "Restore This Commit" button tied to the
    selection.
  - Bottom: shared log/output panel + a Cancel button, styled consistently
    with `MainWindow`'s existing dark ACS theme and `GhostButton`/log styles.
- `Views/NewBranchWindow.xaml` (+ code-behind) — small dialog for branch name
  (and optional start point, defaulting to current `HEAD`), following the
  same simple dialog pattern as `CloneRepositoryWindow`.

### 6. MainWindow / MainViewModel wiring

- Add an `OpenHistoryCommand` (CanExecute: `SelectedRepo is not null`) to
  `MainViewModel`, opening `GitHistoryWindow` for `SelectedRepo.ToModel()` and
  the configured `L5xGitExePath`.
- Add a toolbar/action button (e.g. "📜 HISTORY") next to the existing
  Commit/Pull-and-Restore actions, using the same `GhostButton`/button style
  already in `MainWindow.xaml`.

### 7. Safety and logging checklist (per repo conventions)

- Validate the repo path is a git working tree before any history/branch
  operation (`L5xGitCliService.IsGitWorkingTree` is already public and
  reusable).
- Never silently discard uncommitted changes — always block or require an
  explicit second confirmation.
- Never auto-force-delete a branch — force is only offered after a safe
  delete fails and the user confirms.
- Log every command's start, validation failure, exit code, and exception
  (full `Exception` object) via `AppLogger`, matching the existing
  `L5xGitCliService` style.
- Keep restoring a commit's files scoped to `git checkout <sha> -- .`
  (working-tree only) — do not move `HEAD`, rewrite branches, or perform a
  hard reset, so the destructive surface stays no worse than the existing
  restore workflow.

## Out of scope (explicitly not building)

- Push/pull/fetch/merge of branches, remotes management, tags UI.
- Interactive rebase, cherry-pick, or commit amend/rewrite.
- A pixel-accurate multi-lane graph renderer beyond git's own `--graph` ASCII
  output rendered in a monospace column.

## Notes / assumptions to confirm

- History/branch features operate on the git repo folder (`RepoEntry.GitRepoPath`),
  the same folder already used by Commit/Restore — consistent with current
  scope (no new per-repo config fields needed).
- "Restoring a commit" is defined as restoring working-tree file contents
  (not moving branch/HEAD), then re-running `l5xgit restoreacd` to rebuild the
  ACD — this needs explicit confirmation from you before implementation
  begins, since it's a safety-sensitive design decision.
