# UI/UX Modernization Plan — Studio 5000 Git Manager

## Problem statement

The app works as a single `MainWindow` with a fixed light "ACS control-room"
theme: a left rail list of controllers, a right-hand stack of "instrument"
cards (About / Commit / Pull & Restore / Git History launcher), a collapsible
dark terminal log, and a status footer. Settings, Git History, Add/Edit
Controller, Clone Repository, New Branch, and the Git-repo-init prompt are
all **separate top-level `Window`s** (`ShowInTaskbar="False"`, modal via
`ShowDialog`), not in-app navigation or dialogs.

This is a reasonable WPF scaffold, but several patterns diverge from what
users of modern Windows productivity/dev tools (VS Code, GitHub Desktop,
Fluent/WinUI 3 apps, JetBrains IDEs) expect in 2025: window-per-feature
navigation instead of a persistent nav rail with in-place content, a
"floating card stack" instead of a task-focused workspace, no theme choice,
limited use of progressive disclosure for a destructive multi-step action
(Pull & Restore), and a log/terminal treated as an afterthought rather than
a first-class diagnostics panel.

This plan catalogs concrete weaknesses tied to specific files, and proposes
a phased set of adjustments. It is a **UI/UX-only** plan — it does not touch
process/Git/l5xgit safety behavior described in `plan.md`, and it must not
regress any of the safety-sensitive workflows called out there (overwrite
warnings, stop-on-failed-pull, elevation boundaries).

## Findings — where the current implementation is weak

### 1. Window-per-feature navigation (biggest structural gap)
Settings (`SettingsWindow.xaml`), Git History (`GitHistoryWindow.xaml`),
Add/Edit Controller (`AddEditRepoWindow.xaml`), Clone Repository
(`CloneRepositoryWindow.xaml`), New Branch (`NewBranchWindow.xaml`), and the
Git-init prompt (`GitRepositoryActionWindow.xaml`) are all independent
top-level windows opened via `ShowDialog`/`Show`. Modern single-purpose
desktop tools (GitHub Desktop, VS Code, most WinUI3/Fluent apps) keep the
user inside one primary window with a persistent left nav rail and swap the
center content pane; secondary windows are reserved for things that are
genuinely detachable (e.g., a diff viewer users may want side-by-side).
Today, opening "Dependencies" or "Git History" fully context-switches the
user away from the controller they were just working on, and back-stacked
modal windows compound (History → New Branch → confirm dialogs).

### 2. Everything-is-a-card, no task focus on the main surface
`MainWindow.xaml` stacks About, the setup warning, the controller name
plate, Commit, Pull & Restore, and a Git-History launcher card vertically
in one scrolling column (`MainWindow.xaml` lines ~360-636). There's no
tabbed or segmented separation between "day-to-day" actions (Commit,
Restore) and "reference" content (About). The About card is always present
and full-height even though it's static, pushing the two actionable
instruments below the fold on smaller windows.

### 3. Pull & Restore is a high-risk action with weak progressive disclosure
The branch selector, a static red warning strip, and the destructive button
are all shown flat, all the time (`MainWindow.xaml` lines 555-605). Modern
UX for a "this will overwrite a file" action uses a short confirmation step
(inline expand-and-confirm, or a lightweight confirm dialog naming the exact
file being overwritten) rather than a permanently-visible warning strip that
users learn to tune out. There is also no visible indicator of *what will be
overwritten* (the actual ACD file name) at the point of commitment — only in
the name plate above.

### 4. No theming/appearance choice, and a hybrid dark/light aesthetic
The app hardcodes one light theme (`App.xaml` "ACS DESIGN LANGUAGE" palette),
with an intentionally dark terminal panel embedded inside it. There's no
light/dark/system theme toggle, which is now a baseline expectation for
Windows desktop apps (and trivial to add with WPF `DynamicResource` theme
dictionaries, which the app doesn't use — colors are `StaticResource`,
requiring app restart or manual resource-dictionary swapping to change).

### 5. Log/terminal treated as a secondary, undifferentiated stream
Both `MainWindow.xaml` (lines 301-356) and `GitHistoryWindow.xaml` (lines
202-216) render `LogOutput`/`ActionLogOutput` as a single monochrome
`TextBox` with no line-level severity coloring, no search/filter, and no way
to jump to the last error. Every log line uses the same phosphor-green
color regardless of whether it's informational stdout or a failure.

### 4a. Git History's commit list is a raw `GridView`, not a graph
`GitHistoryWindow.xaml` (lines 233-261) renders "GRAPH / SHA" as a text
column (`GraphPrefix` + `ShortSha`) inside a `ListView`/`GridView`. This is
functional but reads as a data table, not a commit graph — modern Git UIs
(GitHub Desktop, GitKraken, VS Code's Git Graph) draw the branch lines and
commit dots visually and let you scan topology at a glance.

### 6. Controller list has no search/filter and minimal metadata
The left rail `ListBox` in `MainWindow.xaml` (lines 222-290) shows name and
ACD path only, with no filter box, no last-commit/last-sync timestamp, and
no status glyph (e.g., "up to date" / "uncommitted changes" / "never
synced"). This will not scale past a handful of controllers, and it hides
the piece of information users most want before clicking in: *is this
controller in sync with git?*

### 7. Command surface is a single top-right button, no discoverability aids
`MainWindow.xaml` header (lines 26-58) only exposes a "⚙ Dependencies"
button. There's no menu bar, no keyboard shortcuts, no tooltips-with-accelerator
hints, and no command palette — all now common in modern Windows tools for
power users, and low-cost to add via `KeyBinding`s/`InputGestureText`.

### 8. Empty and loading states are minimal
The "no controller selected" empty state (`MainWindow.xaml` lines 424-453)
is a plain centered text block with no illustration/guidance beyond one
sentence, and there is no first-run/onboarding path distinct from
"Settings opens automatically" (per `README.md`). Long-running operations
show only an indeterminate progress bar and status text — no per-step
progress (e.g., "Exporting ACD… / Converting to L5X… / Committing…") even
though the underlying `l5xgit`/git calls are sequential and could report
coarse phase text.

### 9. Inconsistent secondary-window chrome
Some secondary windows show `ShowInTaskbar="False"` with custom
header/footer chrome duplicating standard title-bar affordances (close
button as a styled `Button`, not the native title bar control), which is
fine as a stylistic choice but is inconsistently applied — `MainWindow`
keeps the native title bar, while child windows fully replace it. This is a
minor but real inconsistency in what "chrome" looks like across the app.

## Recommended adjustments (industry-standard patterns to adopt)

1. **Introduce a persistent navigation rail + single content region** in
   `MainWindow.xaml`: keep the existing controller rail, but add top-level
   nav destinations (Home/Controller, Git History, Settings) so History and
   Settings render as swapped content in the same window instead of opening
   new top-level windows. Reserve real secondary windows only for
   short-lived, task-scoped dialogs (Add/Edit Controller, New Branch,
   Clone Repository) — those can stay as dialogs, ideally converted to
   in-window overlay/`ContentDialog`-style modals for visual consistency.
2. **Split the main surface into tabs or a segmented view**: "Overview"
   (name plate + status) and "Actions" (Commit / Restore) as distinct
   regions, with About/branding moved to a footer link or a dedicated
   "About" entry rather than a permanent full-width card.
3. **Add a confirm step to Pull & Restore** that names the exact ACD file
   and shows a one-line diff/summary ("will overwrite `Line3.ACD`, last
   modified <date>") before the destructive action fires, replacing (or
   supplementing) the static warning strip with a just-in-time confirmation.
4. **Add a theme toggle** (Light / Dark / Match Windows) using
   `DynamicResource`-based resource dictionaries so the whole app — not just
   the terminal — supports dark mode, matching Windows 11 app conventions.
5. **Upgrade the log panel**: color-code lines by severity (info/warn/error)
   already present in `AppLogger`/service output, add a search/filter box,
   and add a "jump to first/last error" action.
6. **Render an actual commit graph** in Git History (branch lines + commit
   dots) instead of a text `GraphPrefix` column, or adopt a lightweight
   graph-drawing control/canvas overlay if a full graph library is out of
   scope.
7. **Add a filter box and status glyph to the controller list**: show
   "clean / uncommitted changes / unknown" per controller (derivable from
   `git status --porcelain` at low cost) and a relative last-sync timestamp.
8. **Add a menu bar or command-discoverability layer**: at minimum,
   `KeyBinding`s for Commit/Restore/Open History/Open Settings with
   `InputGestureText` shown in tooltips; a full menu bar is optional.
9. **Improve empty/first-run and progress states**: a richer first-run
   panel with a 2-3 step "Add your first controller" callout, and
   phase-labeled progress text during multi-step commit/restore instead of
   a single indeterminate bar.
10. **Normalize secondary-window chrome**: either adopt the custom
    header/footer + hidden native title bar consistently everywhere, or
    keep native title bars everywhere — pick one and apply it uniformly.

## Explicit non-goals / guardrails

- Do not change or weaken any safety-sensitive behavior from `plan.md`:
  restore must still stop on failed `git pull`; overwrite confirmation must
  not become *weaker* than today (item 3 adds a stronger, more specific
  confirmation, not a bypass); elevation/process-launch behavior is
  unaffected by this plan.
- Do not claim any packaging/release readiness change — this is UI/UX only.
- Any navigation-model change (item 1) is the highest-risk item structurally
  (it changes `MainWindow` composition and how `SettingsWindow`/
  `GitHistoryWindow` are invoked) and should be validated against existing
  UI automation tests in `tests/ABLogixGitManager.UiTests` before/after.

## Suggested phased execution

1. **Low-risk visual/interaction polish** (no structural navigation change):
   log severity coloring, controller list filter + status glyph, richer
   empty state, phase-labeled progress text, confirm-step wording for
   restore.
2. **Theming**: convert `App.xaml` palette to swappable `DynamicResource`
   dictionaries; add a Light/Dark/System toggle exposed from Settings.
3. **Navigation restructuring**: introduce in-window nav for Settings and
   Git History; keep Add/Edit Controller, Clone Repository, New Branch as
   dialogs (or convert to in-window overlays as a stretch goal).
4. **Git History graph rendering**: replace the text graph column with a
   drawn graph once navigation restructuring lands (since History moves
   in-window).
5. **Command discoverability**: keyboard shortcuts and tooltips last, since
   they're additive and don't depend on the other phases.

Re-run `dotnet build src\ABLogixGitManager\ABLogixGitManager.csproj` and the
existing `tests\ABLogixGitManager.UiTests` suite after each phase that
touches `MainWindow.xaml`, window navigation, or control templates.

## 2026-07-27 progress update

- Implemented core UI modernization pass (filtering, status glyphs, stronger restore confirmation, log filtering/severity, shortcuts, and theme controls).
- User feedback indicates the introduced color system felt poor.
- Immediate corrective action applied: System theme now resolves to the original ACS light palette to avoid surprise dark-mode palette shifts; log severity colors now use semantic app brush resources instead of hardcoded neon-like values.
- Remaining follow-up: propose a stricter tokenized dark-theme design pass before re-enabling OS-driven automatic dark selection.
- 2026-07-27 follow-up: completed strict color-token cleanup after user feedback.
  - Replaced ad-hoc palette swap with tokenized light/dark sets in AppThemeService.
  - System theme now follows Windows preference again.
  - Semantic alias brushes (Primary/Success/Danger) now sync from signal tokens.
  - Input/ghost/neutral/dark-button surfaces now use explicit token brushes in App.xaml.
  - Log severity rendering now binds to app semantic brushes instead of hardcoded neon values.

## 2026-07-27 current status (post-tab refactor + placement fixes)

- Completed and validated the workspace/tab restructuring iterations:
  - Actions / History / Config tab model in [MainWindow.xaml](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/MainWindow.xaml)
  - Inline History experience replacing launch-button workflow
  - Controller management placement refinements based on user review
  - Add Controller restored to controller rail top; removed from per-controller Config panel
- Validation baseline for latest phase:
  - `dotnet build src\ABLogixGitManager\ABLogixGitManager.csproj -c Release` passed
  - `dotnet test tests\ABLogixGitManager.Tests\ABLogixGitManager.Tests.csproj -c Release` passed
  - `dotnet test tests\ABLogixGitManager.UiTests\ABLogixGitManager.UiTests.csproj -c Release` passed

## Next phase recommendation

1. Implement the remaining pending UX item: render a true visual commit graph in History (not text-prefix lanes) while preserving current restore/safety flows.
2. Update [docs/Git History.md](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/docs/Git%20History.md) and [docs/Main Window.md](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/docs/Main%20Window.md) to reflect any visual/interaction changes.
3. Re-run build + unit tests + UI tests; leave the app open for review after phase commit.

## 2026-07-27 phase completion: visual commit graph lanes

- Completed the final pending UI todo: History commit graph now renders shape-based lane geometry from git's graph prefix instead of text glyphs.
- Applied to both [MainWindow.xaml](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/MainWindow.xaml) inline History and [GitHistoryWindow.xaml](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/Views/GitHistoryWindow.xaml) for consistency.
- Validation completed:
  - `dotnet build .\src\ABLogixGitManager\ABLogixGitManager.csproj -c Release` passed
  - `dotnet test .\tests\ABLogixGitManager.Tests\ABLogixGitManager.Tests.csproj -c Release` passed (19/19)
  - `dotnet test .\tests\ABLogixGitManager.UiTests\ABLogixGitManager.UiTests.csproj -c Release` passed (2/2)

## 2026-07-27 hardening polish completion

- Restored inline History log parity in [MainWindow.xaml](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/MainWindow.xaml):
  - severity-colored RichText rendering
  - **COPY LOG** action in the history log toolbar
  - auto-scroll and live updates from `HistoryWorkspace.LogOutput`
- Documentation updated in [Git History.md](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/docs/Git%20History.md).
- Validation completed:
  - `dotnet build .\src\ABLogixGitManager\ABLogixGitManager.csproj -c Release` passed
  - `dotnet test .\tests\ABLogixGitManager.Tests\ABLogixGitManager.Tests.csproj -c Release` passed (19/19)
  - `dotnet test .\tests\ABLogixGitManager.UiTests\ABLogixGitManager.UiTests.csproj -c Release` passed (2/2)

## 2026-07-27 phase completion: empty/loading state polish

- Updated empty state guidance and quick actions in [MainWindow.xaml](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/MainWindow.xaml):
  - clearer no-selection instructions
  - direct **+ ADD CONTROLLER** and **OPEN DEPENDENCIES** buttons
- Added in-panel operation progress card shown while busy with status text and cancellation guidance.
- Updated workflow status text in [MainViewModel.cs](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/ViewModels/MainViewModel.cs) to explicit step-based messages for commit/restore/setup flows.
- Updated [Main Window.md](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/docs/Main%20Window.md).
- Validation completed:
  - `dotnet build .\src\ABLogixGitManager\ABLogixGitManager.csproj -c Release` passed
  - `dotnet test .\tests\ABLogixGitManager.Tests\ABLogixGitManager.Tests.csproj -c Release` passed (19/19)
  - `dotnet test .\tests\ABLogixGitManager.UiTests\ABLogixGitManager.UiTests.csproj -c Release` passed (2/2)

## 2026-07-27 phase completion: dependency minimum-version callouts

- Updated [SettingsWindow.xaml](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/Views/SettingsWindow.xaml) to show a **MINIMUM REQUIRED VERSION** line for each dependency row.
- Added per-row minimum-version metadata in [DependencyItemViewModel.cs](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/ViewModels/DependencyItemViewModel.cs) and seeded values in [SettingsViewModel.cs](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/ViewModels/SettingsViewModel.cs).
- Updated [Settings and Dependencies.md](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/docs/Settings%20and%20Dependencies.md) with the same baselines.
- Validation completed:
  - `dotnet build .\src\ABLogixGitManager\ABLogixGitManager.csproj -c Release` passed
  - `dotnet test .\tests\ABLogixGitManager.Tests\ABLogixGitManager.Tests.csproj -c Release` passed (19/19)
  - `dotnet test .\tests\ABLogixGitManager.UiTests\ABLogixGitManager.UiTests.csproj -c Release` passed (2/2)

## 2026-07-27 shipping prep: README + repository release executable

- Built Release binary and copied it to [releases/ABLogixGitManager.exe](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/releases/ABLogixGitManager.exe).
- Updated [README.md](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/README.md) to document the repository release artifact path and caveat that it is not yet a fully validated GitHub Release package.
- Validation completed:
  - `dotnet build .\src\ABLogixGitManager\ABLogixGitManager.csproj -c Release` passed.

## 2026-07-27 hotfix: release executable now self-contained

- Reproduced failure from repository release artifact: the prior file was an apphost-only build output requiring colocated DLLs (`...releases\ABLogixGitManager.dll` missing).
- Published via `win-x64-selfcontained` profile and replaced [releases/ABLogixGitManager.exe](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/releases/ABLogixGitManager.exe) with the self-contained executable.
- Updated [README.md](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/README.md) wording to reflect self-contained packaging for the repository artifact.
- Validation completed:
  - `dotnet publish .\src\ABLogixGitManager\ABLogixGitManager.csproj /p:PublishProfile=win-x64-selfcontained` passed.
  - Launch check confirmed the new `releases\ABLogixGitManager.exe` starts and remains running.

## Plan mode request: set Git identity

### Problem

Set Git author identity to:
- Name: `Mitchell Landreth`
- Email: `mitch@advancedcontrol.com`

### Approach

1. Confirm scope of configuration:
   - global (`git config --global`) or
   - repository-only (`git config` in this repo).
2. Apply the requested name/email for the selected scope.
3. Verify by reading back `user.name` and `user.email` from the same scope.

### Notes

- No source-code changes are required.
- This is a local environment configuration change.
