<overview>
The user asked to add three new git features to the AB Logix Git Manager WPF app: viewing commit history as a graph, restoring the ACD from a specific past commit, and managing git branches. After planning in [[PLAN]] mode (with two user-confirmed design decisions), the user approved the plan and entered autopilot mode. All planned implementation work has been completed and verified through builds and a functional smoke test; no next steps remain.
</overview>

<history>
1. User requested (in plan mode) a feature plan for git history graph, commit restore, and branch management.
   - Explored repo structure: `src/ABLogixGitManager/` (WPF MVVM app), read `plan.md`, `README.md`, `MainViewModel.cs`, `L5xGitCliService.cs`, `RepoEntry.cs`, existing Views/ViewModels patterns, App.xaml styles.
   - Drafted a detailed plan (session plan.md) covering: new `GitRepositoryService`, refactor of `L5xGitCliService.PullAndRestoreAsync` to extract `RestoreAcdOnlyAsync`, new models `GitCommitInfo`/`GitBranchInfo`, new `GitHistoryViewModel`, new Views (`GitHistoryWindow`, `NewBranchWindow`), and MainWindow/MainViewModel wiring.
   - Asked two clarifying questions via `ask_user`:
     a. Confirmed restore-commit semantics should be working-tree-only (`git checkout <sha> -- .`, no HEAD/branch move) — user selected the recommended option.
     b. Confirmed branch management should include remote-branch checkout (creating a local tracking branch), not just local branches — user selected this expanded scope.
   - Updated plan.md to reflect remote-checkout support, then called `exit_plan_mode`. User approved and entered autopilot mode.
   - Tracked 7 todos in SQL (`git-models`, `git-repo-service`, `l5xgit-restore-refactor`, `git-history-viewmodel`, `git-history-window`, `main-window-wiring`, `build-and-verify`) with dependencies, all now marked `done`.

2. Implementation proceeded todo-by-todo (all completed):
   - Created `GitCommitInfo.cs` and `GitBranchInfo.cs` models.
   - Created `GitRepositoryService.cs` with commit graph parsing, branch listing, create/checkout/delete branch, uncommitted-changes check, and commit-file restore — all git-native operations, separate from `L5xGitCliService`.
   - Hit a stale-`obj`-cache build failure (pre-existing environment issue, unrelated to changes) — resolved by deleting `obj/` and rebuilding.
   - Refactored `L5xGitCliService.cs`: extracted `RestoreAcdOnlyAsync` from `PullAndRestoreAsync`, preserving existing logging/behavior.
   - Created `GitHistoryViewModel.cs` with Commits/Branches collections, Refresh/CreateBranch/CheckoutBranch/DeleteBranch/RestoreCommit/CancelOperation commands, following `MainViewModel`/`SettingsViewModel` conventions (IsBusy gating, AppLogger, CancellationTokenSource, MessageBox confirmations).
   - Created `NewBranchWindow.xaml`/`.xaml.cs` (small dialog) and `GitHistoryWindow.xaml`/`.xaml.cs` (main history/branch UI) — fixed one XAML build error (duplicate `Style` attribute on a `TextBlock`).
   - Wired `OpenHistoryCommand` into `MainViewModel.cs` and added a "GIT HISTORY" instrument card + button into `MainWindow.xaml`.
   - Built Debug and Release configurations successfully (0 warnings/errors).
   - Ran a functional smoke test: created a temp git repo with diverging branches/commits, built a standalone console harness referencing the compiled DLL, and exercised `GitRepositoryService` methods directly — all behaved as expected, including the "not fully merged" branch-delete block and successful force-delete fallback.
   - Launched the built Release `.exe`, confirmed it started and ran cleanly (verified via `AppLogger` log file — no exceptions), then stopped the process.
   - Cleaned up all temporary test artifacts (temp repo, harness project).
   - Verified via `git diff` that changes to `L5xGitCliService.cs`, `MainViewModel.cs`, and `MainWindow.xaml` are exactly as intended, with no unrelated modifications introduced by this session (pre-existing unrelated dirty/untracked files in the repo were noted but correctly left untouched).
</history>

<work_done>
Files created:
- `src/ABLogixGitManager/Models/GitCommitInfo.cs` — parsed commit row model (Sha, ShortSha, Author, Date, Subject, RefNames, GraphPrefix).
- `src/ABLogixGitManager/Models/GitBranchInfo.cs` — branch model (Name, IsCurrent, IsRemote).
- `src/ABLogixGitManager/Services/GitRepositoryService.cs` — new service for git-native read/write operations (log/graph parsing, branch list/create/checkout/delete, uncommitted-changes check, commit-file restore). Includes `RunCapturingAsync` (parses stdout) and `RunStreamingAsync` (streams to `onOutput`) private helpers.
- `src/ABLogixGitManager/ViewModels/GitHistoryViewModel.cs` — view model for the history window with full command set and safety gating.
- `src/ABLogixGitManager/Views/GitHistoryWindow.xaml` + `.xaml.cs` — main history/branch UI (branch panel left, commit graph + restore + log right).
- `src/ABLogixGitManager/Views/NewBranchWindow.xaml` + `.xaml.cs` — small branch-name/start-point dialog.

Files modified:
- `src/ABLogixGitManager/Services/L5xGitCliService.cs` — extracted `RestoreAcdOnlyAsync(repo, l5xGitExePath, onOutput, ct)` from `PullAndRestoreAsync`, preserving all prior validation/logging; `PullAndRestoreAsync` now calls the extracted method.
- `src/ABLogixGitManager/ViewModels/MainViewModel.cs` — added `OpenHistoryCommand` (CanExecute: `HasSelectedRepo`), opens `GitHistoryWindow`; added `NotifyCanExecuteChangedFor(nameof(OpenHistoryCommand))` to the `SelectedRepo` property.
- `src/ABLogixGitManager/MainWindow.xaml` — added a "GIT HISTORY · GRAPH, BRANCHES & RESTORE" instrument card with an "OPEN GIT HISTORY" button bound to `OpenHistoryCommand`, placed after the Pull & Restore card.

Work completed (all todos in SQL marked `done`):
- [x] git-models
- [x] git-repo-service
- [x] l5xgit-restore-refactor
- [x] git-history-viewmodel
- [x] git-history-window
- [x] main-window-wiring
- [x] build-and-verify

Verification performed:
- `dotnet build ... -c Debug` and `-c Release` — both succeeded with 0 warnings/errors (after one obj-cache cleanup and one XAML duplicate-Style fix).
- Standalone console harness against a real temp git repo confirmed: commit graph parsing (graph prefix + SHA correctly split via regex), branch listing (local + remote), branch create, branch checkout (local), commit-file restore (`git checkout <sha> -- .`), uncommitted-changes detection, delete-current-branch block, and safe-delete failing correctly on unmerged branch (then verified force-delete `-D` works via manual git command).
- Launched the built Release exe; confirmed clean startup via `AppLogger` log (no exceptions), then closed it.
- Confirmed via `git diff` that only the intended files were changed by this session.

No known issues remain; nothing left untested that was in scope. Pre-existing unrelated dirty files in the repo (e.g., `README.md`, `plan.md`, `DependencyCheckerService.cs`, etc., and some untracked files) exist in the working tree from before this session and were intentionally left untouched per the "don't fix pre-existing unrelated issues" rule.
</work_done>

<technical_details>
- **Restore-commit semantics (user-confirmed)**: "Restoring a commit" means `git checkout <sha> -- .` — repopulates working-tree files from that commit WITHOUT moving HEAD or branches. Leaves an uncommitted diff the user can re-commit or discard. This was an explicit design choice confirmed via `ask_user`, not assumed.
- **Remote branch checkout (user-confirmed)**: `CheckoutBranchAsync` supports remote branches — derives local name by stripping the remote prefix, checks if a local branch with that name already exists (checks it out directly if so), otherwise runs `git checkout --track -b <local> <remote>`.
- **Commit graph parsing trick**: `git log --all --graph --pretty=format:...` prepends ASCII graph glyphs (`*`, `|`, `/`, `\`, spaces) directly before the formatted output with no separator. Since a full commit SHA is always exactly 40 hex chars, a regex `^(?<prefix>[^0-9a-fA-F]*)(?<sha>[0-9a-fA-F]{40})$` reliably splits the graph prefix from the SHA on the first field (using `\u001f` as the field separator between other fields, matching `%x1f`).
- **Safety conventions followed** (per repo's custom instructions): every destructive git operation (checkout, branch delete, commit restore) requires explicit UI confirmation via `MessageBox`; uncommitted changes block checkout/restore with a message rather than silent stash/discard; branch delete never force-deletes without a second explicit confirmation after the safe `-d` fails; every operation logs start/validation/exit/exception via `AppLogger`.
- **Pattern consistency**: Followed existing codebase conventions exactly — `[RelayCommand(CanExecute = nameof(X))]` from CommunityToolkit.Mvvm, `ProcessStartInfo.ArgumentList` (never string `Arguments`), `IsBusy` gating with `CancellationTokenSource`, dark ACS theme styles (`Card`, `PrimaryButton`, `SuccessButton`, `DangerButton`, `NeutralButton`, `GhostButton`, `InstrumentTextBox`, `TerminalBrush`/`PhosphorBrush` for log panels, `Caption`/`Body`/`Eyebrow` text styles).
- **Known WPF gotcha re-encountered**: Setting `Style="{StaticResource X}"` as an attribute AND also declaring `<TextBlock.Style>` inline causes `MC3024` (property set twice) — fixed by removing the attribute-form Style when an inline trigger-based Style is needed.
- **Build environment quirk**: A stale `obj/` folder from a previous locked build caused spurious `CSC : error CS2001` (missing generated `.g.cs` files) unrelated to any code change — resolved by deleting `src/ABLogixGitManager/obj` and rebuilding. This matches a known issue noted in the repo's own `tasks/todo.md` history.
- **Verification approach for a WPF app without browser tooling**: Built a temporary standalone console harness project (`net10.0-windows`, `UseWPF=true`) referencing the compiled `ABLogixGitManager.dll` directly via `<Reference><HintPath>`, to call `GitRepositoryService` methods against a real temp git repo — validated logic without needing full UI automation. This harness and its temp git repo were deleted after verification.
- No unresolved questions remain; both open design decisions were explicitly confirmed with the user before implementation.
</technical_details>

<important_files>
- `src/ABLogixGitManager/Services/GitRepositoryService.cs`
  - New service; core of the git history/branch feature. Contains `GetCommitGraphAsync`, `GetBranchesAsync`, `CreateBranchAsync`, `CheckoutBranchAsync`, `DeleteBranchAsync`, `HasUncommittedChangesAsync`, `RestoreCommitFilesAsync`, plus private `RunCapturingAsync`/`RunStreamingAsync` process helpers.
- `src/ABLogixGitManager/Services/L5xGitCliService.cs`
  - Refactored to expose `RestoreAcdOnlyAsync` (new public method), reused by both `PullAndRestoreAsync` and the new commit-restore flow. `PullAndRestoreAsync` behavior/logging preserved exactly.
- `src/ABLogixGitManager/ViewModels/GitHistoryViewModel.cs`
  - Drives the new history window: commands for Refresh, CreateBranch, CheckoutBranch, DeleteBranch (with force-confirm), RestoreCommit (with uncommitted-changes confirm), CancelOperation.
- `src/ABLogixGitManager/Views/GitHistoryWindow.xaml` / `.xaml.cs`
  - New window: branch panel (New/Checkout/Delete) + commit graph `ListView` (monospace graph/SHA column via `GridViewColumn.CellTemplate`) + restore button + terminal log panel.
- `src/ABLogixGitManager/Views/NewBranchWindow.xaml` / `.xaml.cs`
  - Small dialog for branch name + optional start point.
- `src/ABLogixGitManager/Models/GitCommitInfo.cs`, `Models/GitBranchInfo.cs`
  - New data models feeding the history UI.
- `src/ABLogixGitManager/ViewModels/MainViewModel.cs`
  - Added `OpenHistoryCommand` (near `OpenSettings` command, ~line 332+) and `NotifyCanExecuteChangedFor` on `SelectedRepo`.
- `src/ABLogixGitManager/MainWindow.xaml`
  - Added the "GIT HISTORY" instrument card (after the Pull & Restore card, before the closing `</controls:SpacedStackPanel>` tags, around former line 592).
- Session plan file: `C:/Users/MitchellLandreth/.copilot/session-state/74d38c0e-c112-4d61-98f3-87b0abf688b4/plan.md`
  - Canonical plan document for this feature; reflects the final approach including the two user-confirmed decisions.
</important_files>

<next_steps>
No pending work remains — all planned todos are implemented, built (Debug + Release, 0 warnings/errors), and functionally verified via a service-level harness test plus a clean app startup smoke test. The user has not requested any further action beyond this feature set. If asked to continue, potential natural follow-ups (not yet requested) could include: updating `README.md`/`plan.md` in the actual repo to document the new History/Branch feature (not yet done, since those files already show pre-existing unrelated modifications and were left alone), or adding more automated tests — but neither was requested and both are optional.
</next_steps>