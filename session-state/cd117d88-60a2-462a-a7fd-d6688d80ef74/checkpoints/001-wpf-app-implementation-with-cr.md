<overview>
The user requested full implementation of the AB Logix Git Manager WPF application based on requirements in `plan.md` and `README.md`. The application is a Windows WPF front-end for managing Allen-Bradley Logix ACD files under Git version control using Rockwell Automation's `l5xgit` CLI tool. The approach was to fix critical correctness gaps in the scaffold, add a dependency detection center, implement proper operation gating, fix pre-existing build errors, then diagnose and fix two sequential startup crashes — and the work is currently mid-session with a third crash (XAML binding) just identified.
</overview>

<history>
1. **User requested: start implementation of all plan.md requirements**
   - Read all source files: `MainViewModel.cs`, `L5xGitCliService.cs`, `AppConfigService.cs`, `MainWindow.xaml`, `App.xaml.cs`, models, views, converters
   - Baseline build failed: missing NuGet package (CommunityToolkit.Mvvm not cached) — fixed with `--source https://api.nuget.org/v3/index.json`
   - Baseline build also failed: `Spacing=` property doesn't exist on WPF's `StackPanel` (pre-existing scaffold bug), and `PlaceholderText` not a WPF TextBox property (pre-existing bug)
   - Created a structured todo list in the session SQL database

2. **Implemented all features (2 commits to worktree branch)**

   **Commit 1 `1588b13`** — Core implementation:
   - Fixed critical bug: `git pull` failure no longer continues into restore (was logging but proceeding)
   - Fixed false backup claim in UI ("ACD will be backed up" was untrue per plan.md)
   - Switched `L5xGitCliService` from `Arguments` string to `ProcessStartInfo.ArgumentList` (path safety)
   - Added path validation in service before every operation (l5xgit.exe, ACD file, git repo)
   - `RunProcessAsync` now returns exit code instead of void
   - Created `Controls/SpacedStackPanel.cs` — custom WPF panel with `Spacing` DP using `MeasureOverride`/`ArrangeOverride` to fix pre-existing build errors
   - Replaced all 14 `<StackPanel Spacing="N">` occurrences with `<controls:SpacedStackPanel Spacing="N">`
   - Created `Models/DependencyStatus.cs` (enum: Unknown, Scanning, Ready, Missing, Incompatible, Failed, AdminRequired)
   - Created `Models/DependencyInfo.cs` (record with Name, Status, Version, Message)
   - Created `Services/DependencyCheckerService.cs` — async probes for Git (PATH), l5xgit (file+launch), .NET SDK 10, Studio 5000 (registry), Logix Designer SDK (registry)
   - Created `Converters/DependencyStatusConverter.cs` — two converters: status→icon emoji, status→color brush
   - Created `ViewModels/DependencyItemViewModel.cs` and `ViewModels/SettingsViewModel.cs`
   - Created `Views/SettingsWindow.xaml` + `.xaml.cs` — dependency center UI
   - Added `IsL5xGitConfigured` property to `MainViewModel`, `OpenSettingsCommand`
   - Added yellow setup warning card in main window when l5xgit not configured
   - Added `⚙ Settings` button to top bar
   - Added `Properties/PublishProfiles/win-x64-selfcontained.pubxml`
   - Removed `PlaceholderText` (not a WPF property)
   - Build: 0 errors, 0 warnings ✅

   **Commit 2 `82c1d4b`** — Polish:
   - Added `CancellationTokenSource` to `MainViewModel`; `CancelOperationCommand`
   - Added `✕ Cancel` button to status bar (only visible when `IsBusy`)
   - Added WPF watermark on commit message TextBox (Grid overlay with DataTrigger)
   - `SettingsWindow` now auto-runs `RescanCommand` on `Loaded`
   - Updated README to reflect all implemented features

3. **User asked: run and test the application**
   - Launched via `Start-Process` — user saw nothing (silently crashing)
   - Ran via `dotnet run` to capture output
   - **Crash 1**: `NullReferenceException` in `App.xaml.cs` line 19 — `MainWindow!` is null during `OnStartup` because `StartupUri` creates the window after `OnStartup` returns
   - Fixed: replaced `MainWindow!.ContentRendered +=` with `Application.Activated` event handler (fires after first window is shown)
   - **Commit 3 `741fb45`** — fix: startup crash

4. **User asked: merge worktree into main repo and stop using worktrees**
   - Identified main repo at `C:\Users\MitchellLandreth\Git-Local\AB-Logix-Git` on `main`
   - Worktree branch: `copilot/worktree-2026-07-24T18-14-36`
   - Merged with `--no-ff` into `main` → commit `3d2028a`
   - `git worktree remove --force` deregistered the worktree from git (it no longer appears in `worktree list`)
   - Physical directory could not be deleted (VS Code session holds it as CWD) — told user to delete manually

5. **User asked: app still crashes, implement rigorous logging + code comments**
   - Ran `dotnet run` from main repo
   - **Crash 2 (current)**: `XamlParseException` — `Run.Text="{Binding RequiredFor}"` in `SettingsWindow.xaml` uses `TwoWay` binding by default, but `RequiredFor` is a read-only getter-only property
   - **This crash is identified but NOT yet fixed**
   - User also requested: rigorous file-based logging, unhandled exception handler, XML doc comments throughout codebase, and coding instructions to enforce standards going forward
</history>

<work_done>
**Repository:** `C:\Users\MitchellLandreth\Git-Local\AB-Logix-Git` on branch `main` at `3d2028a`

Files created:
- `src/ABLogixGitManager/Controls/SpacedStackPanel.cs` — custom panel fixing Spacing= build errors
- `src/ABLogixGitManager/Converters/DependencyStatusConverter.cs` — two value converters
- `src/ABLogixGitManager/Models/DependencyInfo.cs` — dependency probe result record
- `src/ABLogixGitManager/Models/DependencyStatus.cs` — status enum
- `src/ABLogixGitManager/Properties/PublishProfiles/win-x64-selfcontained.pubxml`
- `src/ABLogixGitManager/Services/DependencyCheckerService.cs` — all dependency probes
- `src/ABLogixGitManager/ViewModels/DependencyItemViewModel.cs`
- `src/ABLogixGitManager/ViewModels/SettingsViewModel.cs`
- `src/ABLogixGitManager/Views/SettingsWindow.xaml`
- `src/ABLogixGitManager/Views/SettingsWindow.xaml.cs`

Files modified:
- `App.xaml.cs` — first-run Settings trigger using `Activated` event
- `MainWindow.xaml` — SpacedStackPanel, Settings button, Cancel button, warning card, backup text fix, watermark
- `MainViewModel.cs` — IsL5xGitConfigured, OpenSettingsCommand, CancelOperationCommand, CancellationTokenSource
- `Services/L5xGitCliService.cs` — ArgumentList, exit code return, pull-abort-on-fail, path validation
- `Views/AddEditRepoWindow.xaml` — SpacedStackPanel fix
- `README.md` — updated to reflect current state

**Current state:**
- ✅ Builds: 0 errors, 0 warnings
- ❌ Crashes at runtime: `XamlParseException` in `SettingsWindow.xaml` — `{Binding RequiredFor}` needs `Mode=OneWay` (Run.Text defaults to TwoWay)
- ❌ No file-based logging — crashes leave no persistent diagnostic trace
- ❌ No global unhandled exception handler
- ❌ XML doc comments incomplete across several files
- ❌ No coding standards/instructions file
</work_done>

<technical_details>
- **WPF `StackPanel.Spacing`**: Not a native WPF property (it's UWP/WinUI only). Solution: `SpacedStackPanel` subclass with custom `MeasureOverride`/`ArrangeOverride` that adds spacing gaps between children without mutating child margins. Children with `Visibility.Collapsed` are skipped.
- **WPF `TextBox.PlaceholderText`**: Not a WPF property. Solution: Grid overlay with a `TextBlock` that uses a `DataTrigger` on `CommitMessage == ""` to show/hide.
- **`Run.Text` binding defaults to `TwoWay`**: Inside a `TextBlock`, `Run.Text` binding mode defaults to `TwoWay`. Read-only properties on the VM will crash with `XamlParseException`. Fix: always add `Mode=OneWay` to `Run.Text` bindings.
- **`App.OnStartup` — `MainWindow` is null**: `StartupUri` creates the window asynchronously after `OnStartup` returns. Accessing `MainWindow` during `OnStartup` throws `NullReferenceException`. Use `Application.Activated` event (fires once the first window becomes foreground) to safely reference `MainWindow`.
- **`ProcessStartInfo.ArgumentList` vs `Arguments`**: `.ArgumentList` handles paths with spaces correctly without manual quoting. Each argument is a separate string item.
- **git pull abort**: `RunProcessAsync` now returns `int` exit code. `PullAndRestoreAsync` checks it and returns early with an error message if nonzero — prevents restoring from stale content.
- **NuGet restore requires explicit source**: `dotnet restore` on this machine requires `--source https://api.nuget.org/v3/index.json` explicitly (no default NuGet.config pointing to nuget.org).
- **Worktree deregistration**: `git worktree remove` successfully deregistered the worktree from git tracking even though the physical directory couldn't be deleted (VS Code CWD lock). The merge to `main` was clean.
- **`DependencyCheckerService` registry probes**: Checks both `SOFTWARE\Rockwell Automation\*` and `SOFTWARE\WOW6432Node\Rockwell Automation\*` paths. Returns version from `Version` or `InstallVersion` value, or `"(version unknown)"` if key exists but has no version value.
- **`SpacedStackPanel` styling**: When a `SpacedStackPanel` has an inline `<Style>` via element syntax, the `TargetType` must be `{x:Type controls:SpacedStackPanel}`, not `TargetType="StackPanel"`, otherwise the style silently doesn't apply or causes errors.
</technical_details>

<important_files>
- `src/ABLogixGitManager/App.xaml.cs`
  - First-run detection and Settings auto-open
  - Fixed NullReferenceException using `Activated` event
  - **NEEDS**: global unhandled exception handler + file logger initialization

- `src/ABLogixGitManager/Views/SettingsWindow.xaml`
  - Dependency center UI — currently crashing
  - **IMMEDIATE FIX NEEDED**: line 138 — `<Run Text="{Binding RequiredFor}"/>` → add `Mode=OneWay`
  - Also check all other `Run.Text` and plain `TextBlock.Text` bindings for read-only properties

- `src/ABLogixGitManager/ViewModels/DependencyItemViewModel.cs`
  - `RequiredFor` is getter-only (line 24) — the read-only property that causes the binding crash
  - `Name`, `Status`, `Version`, `Message` are `[ObservableProperty]`

- `src/ABLogixGitManager/Services/L5xGitCliService.cs`
  - Core subprocess logic — completely rewritten with ArgumentList, exit codes, path validation, pull-abort
  - `RunProcessAsync` returns `int`; `PullAndRestoreAsync` aborts on nonzero git pull

- `src/ABLogixGitManager/Services/DependencyCheckerService.cs`
  - All 5 dependency probes; `CheckAllAsync` runs them concurrently
  - Uses `Microsoft.Win32.Registry` (Windows-only, fine for net10.0-windows)

- `src/ABLogixGitManager/ViewModels/MainViewModel.cs`
  - `IsL5xGitConfigured`, `CancelOperationCommand`, `CancellationTokenSource`, `OpenSettingsCommand`
  - `_cts` disposed in `finally` block of both operation commands

- `src/ABLogixGitManager/Controls/SpacedStackPanel.cs`
  - Fixes pre-existing build error; used in all XAML files
  - Override `MeasureOverride` and `ArrangeOverride` — does NOT mutate child margins

- `src/ABLogixGitManager/MainWindow.xaml`
  - All `<StackPanel Spacing="N">` replaced with `<controls:SpacedStackPanel Spacing="N">`
  - Warning card bound to `IsL5xGitConfigured`, cancel button bound to `CancelOperationCommand`
  - Commit message watermark via Grid overlay
</important_files>

<next_steps>
**Immediate fix (blocking — app crashes on launch):**
1. In `SettingsWindow.xaml` line 138: change `<Run Text="{Binding RequiredFor}"/>` to `<Run Text="{Binding RequiredFor, Mode=OneWay}"/>` — also audit all other bindings to read-only properties and add `Mode=OneWay`

**Required by user (logging + comments):**
2. Add `Services/AppLogger.cs` — file-based logger writing to `%APPDATA%\ABLogixGitManager\logs\app-YYYY-MM-DD.log` with timestamped entries (Info, Warning, Error levels)
3. Update `App.xaml.cs` to register global handlers:
   - `DispatcherUnhandledException` — catches WPF dispatcher exceptions, logs them, shows user-friendly dialog
   - `AppDomain.CurrentDomain.UnhandledException` — catches background thread crashes
   - `TaskScheduler.UnobservedTaskException` — catches unobserved async task exceptions
4. Thread `AppLogger` calls through all services and view models (especially `DependencyCheckerService`, `L5xGitCliService`, `SettingsViewModel`, `MainViewModel`)
5. Add XML `<summary>` doc comments to all public types and members that are currently undocumented
6. Create `tasks/lessons.md` (per repo instructions) with the discovered gotchas
7. Create a coding standards instruction file (`.github/copilot-instructions.md` or similar) mandating: file-based logging for all exceptions, `Mode=OneWay` on read-only bindings, `ArgumentList` not `Arguments`, WPF-compatible alternatives for UWP-only properties

**Then:**
8. Rebuild and verify app launches cleanly
9. Test: Settings window opens, dependency scan runs, main window shows correctly
</next_steps>