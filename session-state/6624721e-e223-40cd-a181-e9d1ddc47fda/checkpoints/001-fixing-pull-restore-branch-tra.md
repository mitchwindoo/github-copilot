<overview>
The user first asked for a full end-to-end validation of the AB Logix Git Manager app (commit an ACD to git, then recompile it back to ACD) using a real ACD file and git path. That test surfaced a blocking Logix Designer SDK version mismatch (environment limitation, not an app bug — confirmed and accepted by the user). The user then reported a second, separate real workflow problem discovered while testing with their own already-exploded project: `git pull` fails with "no tracking information for the current branch" during Pull & Restore, and requested three concrete feature/bugfix improvements to the Add/Edit Controller workflow and Pull & Restore workflow. I am now implementing those three items directly in the C# WPF codebase.
</overview>

<history>
1. User asked to run a full process test committing `C:\Users\MitchellLandreth\Downloads\WSS_20150210.ACD` to git repo `C:\Users\MitchellLandreth\Git-Local\Logix-Git-Testing` and recompiling back to ACD.
   - Explored repo structure, README, tasks/todo.md, tasks/lessons.md.
   - Found `l5xgit.exe` already built at `%APPDATA%\ABLogixGitManager\tools\ra-logix-designer-vcs-custom-tools\artifacts\bin\Release\l5xgit.exe`; verified git 2.52.0 and dotnet 10.0.301 present.
   - Built the app in Release, set `l5xGitExePath` in `%APPDATA%\ABLogixGitManager\config.json`, backed up the original ACD, set up a bare git remote (`Logix-Git-Testing-origin.git`) so Pull & Restore's plain `git pull` would succeed later.
   - Launched the real compiled app and drove it via Windows UI Automation from PowerShell (`Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes`): selected the repo in `RepoListBox` (AutomationId), set `CommitMessageBox` value, invoked the "▲ COMMIT TO GIT" button.
   - Commit failed: `l5xgit.exe commit` invoked the Rockwell Logix Designer SDK, which threw `OperationFailedException: Required Logix Designer version: 20.1 is not installed.` Confirmed only Logix Designer v38 is installed on this machine (`C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU\v38`).
   - Confirmed no partial state (git repo still had zero commits) and cleaned up scratch artifacts (bare remote, ACD backup).
   - Asked the user how to proceed (different ACD authored in v38, install v20.1, or stop). User chose to stop.

2. User reported they tried working around the issue using an already-exploded project (`SHD-BOI-Line`) and hit a new real bug: Pull & Restore fails with git stderr `There is no tracking information for the current branch. ... git pull <remote> <branch>`. The user requested three concrete improvements:
   1. Add/Edit Controller dialog should support pointing to an existing repo (online or local) or creating a new one; when connecting to an existing remote to pull, the ACD path should be allowed to not exist yet (it will be created).
   2. When there's no existing ACD file, support "pull and create" / "create from local" workflows.
   3. In the restore/"compile to ACD" workflow, allow selecting which branch to build the ACD from.
   - I explored the codebase in depth: `MainViewModel.cs`, `L5xGitCliService.cs`, `GitRepositoryService.cs`, `AddEditRepoWindow.xaml(.cs)`, `CloneRepositoryWindow.xaml.cs`, `GitRepositoryActionWindow.xaml.cs`, `GitHistoryViewModel.cs`, `NewBranchWindow.xaml(.cs)`, `Models/GitBranchInfo.cs`, `Models/GitRepositoryAction.cs`, `RepoEntry.cs`, `RepoEntryViewModel.cs`, `MainWindow.xaml`.
   - Confirmed `ValidatePathsForRestore` already permits a missing ACD file (good — partially satisfies request #2), but plain `git pull` in `PullAndRestoreAsync` has no fallback for missing upstream tracking, and `PullAndRestoreAsync` (unlike `CommitAsync`) never calls the `EnsureGitRepositoryReadyAsync` preflight that offers Initialize/Clone/Cancel.
   - Logged a 5-item todo/plan in the SQL `todos`/`todo_deps` tables and began implementing, building after each change to catch errors early.
   - Implemented and verified (build succeeded, 0 warnings/errors) three of five todos so far; currently mid-implementation on the fourth (AddEditRepoWindow source-mode selector), having just finished the XAML edit and about to update the code-behind.
</history>

<work_done>
Files created:
- `src/ABLogixGitManager/Models/RestoreBranchOption.cs` — new model: `Display` (string), `Value` (string?, null = current branch), `IsRemote` (bool). Used to populate the new Pull & Restore branch drop-down.

Files modified:
- `src/ABLogixGitManager/Services/GitRepositoryService.cs`
  - Added `GetRemotesAsync(repoPath, ct)` → `List<string>` via `git remote`.
  - Added `GetCurrentBranchNameAsync(repoPath, ct)` → `string?` via `git rev-parse --abbrev-ref HEAD` (returns null if detached/unknown/"HEAD").
  - Both inserted just before the existing "Working-tree state" region comment.
- `src/ABLogixGitManager/Services/L5xGitCliService.cs`
  - Added `using System.Linq;`.
  - Added `private readonly GitRepositoryService _gitService = new();` field.
  - Rewrote `PullAndRestoreAsync` signature to add `string? branchName = null` parameter (backward compatible, added last).
  - New logic order: validate paths → if `branchName` given, call new private `SwitchToBranchAsync` to checkout it (blocks on uncommitted changes, resolves local vs remote branch via `_gitService.GetBranchesAsync`, uses `_gitService.CheckoutBranchAsync`) → call `_gitService.GetRemotesAsync`; if zero remotes, skip `git pull` entirely and log/output that restore will use the local working tree only; if remotes exist, run bare `git pull`, and if that fails, call new private `RetryPullWithExplicitBranchAsync` which resolves the current branch via `GetCurrentBranchNameAsync`, picks `origin` if present else the first remote, retries with `git pull <remote> <branch>`, and on success best-effort runs `git branch --set-upstream-to=<remote>/<branch> <branch>` (failure here is non-fatal, just logged) → proceeds to existing `RestoreAcdOnlyAsync`.
  - Updated XML doc comments accordingly.
  - Build verified clean (0 warnings/errors) after this change.
- `src/ABLogixGitManager/ViewModels/MainViewModel.cs`
  - Added `private readonly GitRepositoryService _gitService = new();`.
  - Added `ObservableCollection<RestoreBranchOption> RestoreBranchOptions` property and `[ObservableProperty] private RestoreBranchOption? _selectedRestoreBranchOption;`.
  - `PullAndRestoreAsync` command: now calls `if (!await EnsureGitRepositoryReadyAsync()) return;` at the top (mirroring `CommitAsync`'s preflight, satisfying request #2 for repos not yet initialized/cloned), passes `branchName: SelectedRestoreBranchOption?.Value` into `_cliService.PullAndRestoreAsync`, and calls `await RefreshRestoreBranchOptionsAsync();` in a `finally`-adjacent spot after the try/catch/finally block completes.
  - Added `partial void OnSelectedRepoChanged(RepoEntryViewModel? value) => _ = RefreshRestoreBranchOptionsAsync();` (CommunityToolkit.Mvvm generated-property changed-hook, no other repo in the codebase used this pattern yet but it's supported out of the box).
  - Added `RefreshRestoreBranchOptionsAsync()` helper: clears and reseeds `RestoreBranchOptions` with a "Current branch (HEAD)" entry (Value=null, always selected first), returns early if `SelectedRepo` is null or `L5xGitCliService.IsGitWorkingTree(...)` is false, otherwise loads `_gitService.GetBranchesAsync` and adds each as a `RestoreBranchOption` (labeling the current one "(current)").
  - Build verified clean after this change.
- `src/ABLogixGitManager/MainWindow.xaml`
  - In the "PULL & RESTORE INSTRUMENT" card: updated the description text to mention no-remote fallback behavior; added a new "BUILD ACD FROM BRANCH" `Caption` label + `ComboBox` (`AutomationId="RestoreBranchBox"`, `Style="{StaticResource InstrumentComboBox}"`, `ItemsSource="{Binding RestoreBranchOptions}"`, `SelectedItem="{Binding SelectedRestoreBranchOption}"`, `DisplayMemberPath="Display"`, disabled while `IsBusy`) placed above the existing overwrite-caution strip and Pull & Restore button.
  - Build verified clean after this change (XAML compiles, no runtime UI check performed yet for this specific control).
- `src/ABLogixGitManager/Views/AddEditRepoWindow.xaml`
  - Just rewrote the form `Grid`: added `SOURCE`/"REPOSITORY SOURCE" `ComboBox` (`x:Name="SourceModeBox"`) with 3 `ComboBoxItem`s ("Use an existing local folder", "Clone a remote repository (git clone)", "Create a new local repository (git init)") wired to a new `SelectionChanged="SourceModeBox_SelectionChanged"` handler (not yet implemented in code-behind — **this is the immediate next step**).
  - Added a collapsed-by-default `RemoteUrlLabel`/`RemoteUrlBox` pair (shown only in Clone mode, toggled in code-behind).
  - Added a hint `TextBlock` under the ACD path field: "This file does not need to exist yet — use Pull & Restore after saving to create it from the repository."
  - Added `x:Name="GitRepoPathLabel"` to the existing "GIT REPO / EXPLODED DIRECTORY PATH" label (so code-behind can retext it per mode) and a new collapsed `x:Name="StatusText"` TextBlock at the bottom for showing clone/init errors inline.
  - **This edit has NOT yet been verified to build** — it was the last action before compaction. `AddEditRepoWindow.xaml.cs` has NOT yet been updated to match (still has the old 3-field-only Ok_Click/constructor); this will cause a build break (missing `SourceModeBox_SelectionChanged` handler) until the code-behind is updated next.

Todo status (SQL `todos` table):
- `fix-pull-tracking` — done
- `restore-branch-selector` — done
- `restore-preflight-repo-setup` — done
- `addedit-repo-source-modes` — in_progress (XAML done, code-behind pending)
- `build-and-verify` — pending (depends on all above)

Work NOT yet done:
- `AddEditRepoWindow.xaml.cs`: needs a `SourceMode` enum/tracking field, `SourceModeBox_SelectionChanged` handler (toggle `RemoteUrlLabel`/`RemoteUrlBox` visibility and update `GitRepoPathLabel` text per mode), constructor update to set `SourceModeBox.SelectedIndex` appropriately for edit mode (existing entries should default to "Use an existing local folder"), and an async `Ok_Click` that — for Clone mode — calls `L5xGitCliService.CloneRepositoryAsync(remoteUrl, gitRepoPath, onOutput)` before accepting, and for Create-New mode calls `L5xGitCliService.InitializeGitRepositoryAsync(gitRepoPath, onOutput)` before accepting; on failure, populate `StatusText` and keep the dialog open instead of closing.
- Need to add a `L5xGitCliService` instance field to `AddEditRepoWindow` (`private readonly L5xGitCliService _cliService = new();`) since it currently has no service dependencies.
- Full rebuild + `dotnet test tests\ABLogixGitManager.Tests\ABLogixGitManager.Tests.csproj` verification not yet run since the AddEditRepoWindow XAML change.
- Manual/UI-driven verification against the real `Logix-Git-Testing` scenario (local branch with no upstream + origin remote) reproducing the originally reported "no tracking information" error and confirming the fix resolves it — not yet performed. Note: the bare origin remote and ACD backup created during the first test session were already cleaned up/deleted, so this would need to be re-created if manual verification is desired.
- README.md documentation update for the new capabilities — not yet done (custom instructions require updating docs directly related to changes).
- tasks/todo.md review section — not yet written (custom instructions require a checklist + review section for multi-step work; so far only the SQL `todos` table has been used, not the actual `tasks/todo.md` file, which should probably also be updated per the repo's own custom instructions).
</work_done>

<technical_details>
- **Logix Designer SDK version coupling**: `l5xgit.exe commit` uses the Rockwell Logix Designer SDK to open the ACD via `LogixProject.OpenLogixProjectAsync`, which throws `OperationFailedException` if the ACD's authored Logix Designer version isn't installed side-by-side. This is a hard vendor/licensing constraint, not fixable in this app. Only Logix Designer v38 is installed on this dev machine; `WSS_20150210.ACD` requires v20.1.
- **UI Automation from PowerShell**: `Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes` works well for driving the real compiled WPF app from PowerShell without needing FlaUI/a test project. Gotcha: `[System.Windows.Automation.AutomationElement]::ProcessIdProperty` `PropertyCondition` requires an actual `Int32`, not a boxed value from a pipeline that could become an array — always cast explicitly `[int]$proc.Id` after `Get-Process -Name X` (a bare `$proc.Id` sometimes fails type coercion in this environment). WPF auto-derives `AutomationId` from `x:Name` even when `AutomationProperties.AutomationId` isn't explicitly set, which simplified locating `CommitMessageBox` and `LogTextBox`.
- **`git pull` tracking gotcha**: A bare `git pull` fails with "There is no tracking information for the current branch" whenever the checked-out branch has no configured upstream — common right after `git init` + `git remote add`, or after checking out a newly created local branch by name (not via `--track`). Git's own suggested fix (`git pull <remote> <branch>`) is exactly what the new `RetryPullWithExplicitBranchAsync` fallback does, followed by a best-effort `git branch --set-upstream-to=...` so future plain pulls succeed.
- **Existing safety patterns to preserve**: `GitRepositoryService.CheckoutBranchAsync` already refuses to switch branches over uncommitted changes (returns `false` with a message) — the new `L5xGitCliService.SwitchToBranchAsync` explicitly re-checks `HasUncommittedChangesAsync` itself before calling checkout, to fail fast with a restore-specific message rather than relying solely on the downstream check.
- **CommunityToolkit.Mvvm partial change hooks**: `partial void On<PropertyName>Changed(TType value)` is auto-wired by the `[ObservableProperty]` source generator without any extra declaration/attribute — confirmed this works by building successfully; no prior usage existed elsewhere in the codebase to copy from.
- **`GitRepositoryAction` enum** (`Models/GitRepositoryAction.cs`) currently only has `Initialize` and `Clone` — used by `GitRepositoryActionWindow` for the reactive (post-commit-attempt) setup flow. This is separate from the new proactive `AddEditRepoWindow` source-mode selector being built now; the two are not currently unified, which is an intentional scope decision to avoid overengineering, though it does mean there are now two separate places offering "clone" and "initialize" actions (worth being aware of for consistency/future refactor, not a bug).
- **`InstrumentComboBox` style** already exists in `App.xaml` (added for `NewBranchWindow`'s start-point dropdown) and is reused as-is for both the new `RestoreBranchBox` (MainWindow) and `SourceModeBox`/mode selector (AddEditRepoWindow) — no new styling work needed. No `RadioButton` style exists in the app, which is why a `ComboBox` was chosen over radio buttons for the source-mode selector.
- **Open assumption**: For `AddEditRepoWindow`, in Edit mode (existing repo), the source-mode selector should probably default to/lock on "Use an existing local folder" since re-cloning or re-initializing an already-configured mapping doesn't make sense — this needs to be handled explicitly in the constructor when `existing is not null`, not yet implemented.
</technical_details>

<important_files>
- `src/ABLogixGitManager/Services/L5xGitCliService.cs`
  - Core CLI orchestration service; houses `CommitAsync`, `PullAndRestoreAsync`, `RestoreAcdOnlyAsync`, `InitializeGitRepositoryAsync`, `CloneRepositoryAsync`, path validation, and the l5xgit sidecar writer.
  - Modified: added `_gitService` field, extended `PullAndRestoreAsync` with `branchName` param + no-remote/no-tracking fallback logic, added private `RetryPullWithExplicitBranchAsync` and `SwitchToBranchAsync` helpers.
  - Will need to be referenced again from `AddEditRepoWindow.xaml.cs` (needs its own `_cliService` instance) for the pending Clone/Init-on-Save work.
- `src/ABLogixGitManager/Services/GitRepositoryService.cs`
  - Read/write git metadata helper (branches, commits, checkout, uncommitted-changes check).
  - Modified: added `GetRemotesAsync` and `GetCurrentBranchNameAsync`, inserted before the "Working-tree state" region.
- `src/ABLogixGitManager/ViewModels/MainViewModel.cs`
  - Main window's view model; owns `Repos`, `SelectedRepo`, Commit/PullAndRestore/OpenHistory commands.
  - Modified: added `_gitService`, `RestoreBranchOptions`/`SelectedRestoreBranchOption`, `OnSelectedRepoChanged` hook, `RefreshRestoreBranchOptionsAsync`, and updated `PullAndRestoreAsync` to call `EnsureGitRepositoryReadyAsync` + pass branch + refresh options afterward.
- `src/ABLogixGitManager/MainWindow.xaml`
  - Main window UI; Pull & Restore card modified to add the `RestoreBranchBox` ComboBox and updated description text.
- `src/ABLogixGitManager/Views/AddEditRepoWindow.xaml` / `.xaml.cs`
  - Add/Edit Controller dialog — the file currently being modified for request #1.
  - `.xaml` already rewritten with `SourceModeBox`, `RemoteUrlLabel`/`RemoteUrlBox`, ACD-path hint text, `GitRepoPathLabel` (named), and `StatusText`.
  - `.xaml.cs` **still has the OLD implementation** (3-field-only constructor/Ok_Click, no `SourceModeBox_SelectionChanged` handler) — **this is an active build break waiting to be fixed** since the XAML references a `Click`/`SelectionChanged` handler and named elements that the code-behind doesn't yet know about (the code-behind itself won't fail to compile from missing handler, but `InitializeComponent()` binding to `SourceModeBox_SelectionChanged` will fail at compile time via the generated partial class expecting that method — must add it).
- `src/ABLogixGitManager/Models/RestoreBranchOption.cs` — new file backing the restore branch dropdown.
- `tasks/todo.md` / `tasks/lessons.md` — repo's own planning/lessons files per its custom instructions; not yet updated with this session's work (only the SQL `todos` table has been used so far).
</important_files>

<next_steps>
Immediate next step (was in-progress at compaction):
1. Update `src/ABLogixGitManager/Views/AddEditRepoWindow.xaml.cs` to match the new XAML:
   - Add `private readonly L5xGitCliService _cliService = new();`.
   - Add a `SourceModeBox_SelectionChanged` handler toggling `RemoteUrlLabel`/`RemoteUrlBox` visibility and retexting `GitRepoPathLabel` per mode (e.g. "CLONE DESTINATION FOLDER" / "NEW REPOSITORY FOLDER" / original label).
   - Update constructor: default `SourceModeBox.SelectedIndex = 0` for new entries; for `existing is not null` (edit mode), force/lock to "Use an existing local folder" (index 0) since re-cloning/re-initing an existing mapping isn't meaningful.
   - Change `Ok_Click` to `async void`, validate per-mode required fields (remote URL required only in Clone mode), and before setting `Result`/`DialogResult = true`:
     - Clone mode: call `_cliService.CloneRepositoryAsync(remoteUrl, gitRepoPath, onOutput)`; on failure, show `StatusText` with the error and keep the dialog open (don't set `DialogResult`).
     - Create-New mode: ensure the destination folder exists (`Directory.CreateDirectory` if needed) then call `_cliService.InitializeGitRepositoryAsync(gitRepoPath, onOutput)`; same failure handling.
     - Existing-folder mode: keep current behavior (just validate non-blank paths, no I/O).
   - Disable the SAVE/CANCEL buttons or show a busy indicator while the async clone/init runs, per the app's existing IsBusy-disabling pattern elsewhere.
2. Rebuild (`dotnet build src\ABLogixGitManager\ABLogixGitManager.csproj -c Release`) and fix any compile errors.
3. Run `dotnet test tests\ABLogixGitManager.Tests\ABLogixGitManager.Tests.csproj` to check for regressions (no service-level tests were added for the new methods yet — consider whether new tests are warranted for `GetRemotesAsync`/`GetCurrentBranchNameAsync`/the pull-retry logic, consistent with the repo's existing test coverage patterns).
4. Perform focused manual/UI verification of the original reported bug: recreate a local repo + bare remote scenario with an untracked local branch, run Pull & Restore through the real app, and confirm it now falls back to `git pull <remote> <branch>` successfully instead of erroring (the bare remote and ACD backup used in the first test session were already deleted during cleanup, so this scaffolding needs to be rebuilt if this verification is performed).
5. Update `README.md` to document the new Pull & Restore branch selector and Add/Edit Controller source-mode options, per the custom instructions requiring docs to stay in sync with implemented behavior.
6. Update `tasks/todo.md` with a checklist + review section (validation performed, remaining risks) per the repo's own custom-instruction workflow, mirroring the style already used for prior features in that file.
7. Mark `addedit-repo-source-modes` and `build-and-verify` done in the SQL `todos` table once verified.
</next_steps>