<overview>
The user is iteratively refining the WPF GUI of the "AB Logix Git Manager" (a Windows .NET 10 desktop app for putting Rockwell Studio 5000 ACD projects under Git via `l5xgit`). This checkpoint's task: change the main window's title bar to "Studio 5000 Git Manager" and subtitle to "Version Control System for Rockwell Automation Studio 5000 Programs". A prior turn already made this exact change, but the user reports it was undone in the latest build, so the task is to re-apply it. My edits succeeded, but the build is now blocked by pre-existing environment/dependency issues unrelated to the text change.
</overview>

<history>
1. The user asked to redo the title bar/subtitle changes (report: "it looks like it was undone in the latest build").
   - Grepped MainWindow.xaml: confirmed the title was reverted AND the faceplate had been restructured by someone else. Current state found: `Title="AB Logix Git Manager — ACS"`, and a new faceplate layout using an SVG wordmark image (`AcsWordmark.svg` via `svgc:SvgImage`) plus `TextBlock Text="AB LOGIX GIT MANAGER"` (FontSize 24, InkBrush) and subtitle `TextBlock Text="Advanced Control Systems"`.
   - Applied two edits to MainWindow.xaml:
     - `Title="AB Logix Git Manager — ACS"` → `Title="Studio 5000 Git Manager"`
     - Faceplate title `"AB LOGIX GIT MANAGER"` → `"STUDIO 5000 GIT MANAGER"` (kept uppercase to match current styling); subtitle `"Advanced Control Systems"` → `"Version Control System for Rockwell Automation Studio 5000 Programs"` (kept title-case to match current subtitle styling).
   - Attempted build → FAILED with `NU1100: Unable to resolve 'SharpVectors.Wpf (>= 1.8.5)'`.
   - Ran `dotnet nuget list source` → "No sources found." SharpVectors not in local cache.
   - Added nuget.org source (`dotnet nuget add source https://api.nuget.org/v3/index.json -n nuget.org`) → restore then SUCCEEDED.
   - Rebuilt → FAILED with `CS2001: Source file '...\obj\...\*.g.cs' could not be found` (WPF markup temp-project errors).
   - Cleaned obj/bin and rebuilt → same CS2001 errors.
   - Ran build with error filtering → revealed the REAL current blocker: `MSB4018: The "GenerateDepsFile" task failed unexpectedly. System.IO.IOException: The process cannot access the file '...\bin\Debug\net10.0-windows\ABLogixGitManager.deps.json' because it is being used by another process.` This is a file-lock issue — a running app instance (or stale process) is holding the output files.
   - This is where the conversation was compacted. The build has NOT yet succeeded; the title edits ARE in place in source.
</history>

<work_done>
Files updated:
- `src/ABLogixGitManager/MainWindow.xaml`:
  - Line 7: `Title="Studio 5000 Git Manager"` (was `"AB Logix Git Manager — ACS"`)
  - Faceplate (around lines 44-53): title TextBlock now `"STUDIO 5000 GIT MANAGER"`; subtitle TextBlock now `"Version Control System for Rockwell Automation Studio 5000 Programs"`.

Environment changes made:
- Added a user/machine-level NuGet source `nuget.org` (was previously "No sources found") to enable package restore. This was required — without any source the project cannot restore `SharpVectors.Wpf` and can never build.

Work completed:
- [x] Re-applied the title bar + faceplate title + subtitle text edits in MainWindow.xaml.
- [x] Restored packages (after adding nuget.org source).
- [ ] Build — STILL FAILING due to `GenerateDepsFile`/`deps.json` file lock (another process using the file). NOT yet resolved.
- [ ] Runtime verification via UI Automation (blocked until build succeeds).
- [ ] Cleanup: remove any seeded config, confirm environment restored.

Most recent action: diagnosing the build failure. Confirmed it is NOT caused by my text edit — it's a `deps.json` file-lock (MSB4018/IOException), almost certainly a leftover running `ABLogixGitManager` process holding the file.
</work_done>

<technical_details>
- BLOCKER (current): `MSB4018: GenerateDepsFile task failed ... deps.json ... being used by another process`. Fix: kill the running app process, then rebuild. Per environment rules, MUST use `Stop-Process -Id <PID>` with a literal PID (name-based kills and `Stop-Process -Name` are disallowed; `$pid` is a read-only automatic var — do not use as a param name; use `$procId`). Standard pattern that has worked all session: `Get-Process ABLogixGitManager -EA SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }` then rebuild. The earlier CS2001 `.g.cs` errors were downstream noise from the same locked/failed build; a clean rebuild after killing the locking process should clear them.
- The faceplate/branding was restructured by ANOTHER developer/branch between my prior turn and now: it now uses `SharpVectors.Wpf` `svgc:SvgImage` to render `/Assets/Branding/AcsWordmark.svg`. This introduced the `SharpVectors.Wpf (>=1.8.5)` dependency. My prior-turn title edits were overwritten by this restructure (explains "undone in the latest build").
- NuGet had NO sources configured ("No sources found"). I added nuget.org. Do NOT revert this — removing it re-breaks the build. Worth mentioning to the user as an environment change.
- Design decision: kept the faceplate title UPPERCASE (`STUDIO 5000 GIT MANAGER`) to match the existing restructured layout's casing (previous sibling was `AB LOGIX GIT MANAGER`), and kept the subtitle in title-case to match the previous `Advanced Control Systems` styling. The OS `Window.Title` uses the exact requested casing `Studio 5000 Git Manager`. NOTE: this differs from my prior turn where I had used a middot form `STUDIO 5000 · GIT MANAGER`; the current layout has no middot so I matched it.
- Verification approach that works reliably this session: UI Automation (`UIAutomationClient`) to read Window Name (OS title bar) and Text element Names (faceplate strings), because screen-capture on this shared machine is flaky (focus-stealing: captures grab background browser/lock screen instead of the app). To read the app cleanly, seed `%APPDATA%\ABLogixGitManager\config.json` with a valid-looking path so the first-run Dependencies dialog does NOT auto-open.
- CRITICAL config detail: `AppConfig` uses `[JsonPropertyName("l5xGitExePath")]` and `[JsonPropertyName("repos")]` (camelCase), and System.Text.Json is case-sensitive by default. Seed JSON MUST be `{"l5xGitExePath":"C:\\dummy\\l5xgit.exe","repos":[]}` (correct casing) or the path reads empty and the Dependencies dialog auto-opens (via `App.xaml.cs` first-run logic when `string.IsNullOrWhiteSpace(config.L5xGitExePath)`).
- Original environment had NO `config.json` — always remove the seeded file afterward to restore state.
- Build target: `net10.0-windows`, SDK 10.0.301 at `C:\Program Files\dotnet`. Detected present deps: .NET SDK 10 (10.0.301), Git for Windows (2.52.0). Studio 5000/l5xgit NOT installed (so real busy-state/commit flows can't be exercised here).
</technical_details>

<important_files>
- `src/ABLogixGitManager/MainWindow.xaml`
   - The file being edited this task. Contains the OS `Window.Title` (line 7) and the restructured faceplate header (~lines 34-60): an ACS SVG wordmark `Border`/`Image` (Grid.Column 0), a title+subtitle `StackPanel` (Grid.Column 1, ~lines 44-53), and the `⚙ DEPENDENCIES` button (Grid.Column 2).
   - Changes made: Title → `Studio 5000 Git Manager`; faceplate title → `STUDIO 5000 GIT MANAGER`; subtitle → `Version Control System for Rockwell Automation Studio 5000 Programs`.
   - Also contains (from earlier checkpoints, still present): the collapsible output log panel bound to `IsLogVisible`, the footer SHOW/HIDE OUTPUT LOG toggle with an `IsBusy` activity LED, and footer status LED/text.
- `src/ABLogixGitManager/ABLogixGitManager.csproj`
   - Now references `SharpVectors.Wpf (>= 1.8.5)` (added by another dev for SVG branding). This is the source of the restore requirement.
- `src/ABLogixGitManager/Models/AppConfig.cs`
   - Defines config schema with camelCase JsonPropertyName attributes — critical for correctly seeding config.json during verification.
- `src/ABLogixGitManager/App.xaml.cs`
   - First-run logic (~line 25-39): auto-opens the Dependencies/Settings window when `L5xGitExePath` is empty. Relevant to why seeding config matters for clean UIA inspection.
- `.github/skills/frontend-design/SKILL.md` + `NOTICE.md`
   - The vendored Anthropic frontend-design skill installed in an earlier checkpoint (context for the overall GUI work).
</important_files>

<next_steps>
Immediate next steps (to unblock and verify the already-applied edits):
1. Kill the locking process: `Get-Process ABLogixGitManager -EA SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }` (also check for stale error-dialog processes). This should release `deps.json`.
2. Clean and rebuild: `Remove-Item -Recurse -Force .\obj, .\bin` then `dotnet build ABLogixGitManager.csproj -c Debug`. Expect the MSB4018/CS2001 errors to clear once the lock is gone. If CS2001 `.g.cs` errors persist after a clean build with no lock, investigate the `svgc:SvgImage` XAML markup / SharpVectors markup-compile (verbose build, look for the first real markup error).
3. Verify via UI Automation (screen capture is unreliable here): seed `%APPDATA%\ABLogixGitManager\config.json` = `{"l5xGitExePath":"C:\\dummy\\l5xgit.exe","repos":[]}`, launch, confirm Window Name == "Studio 5000 Git Manager" and faceplate Text elements == "STUDIO 5000 GIT MANAGER" and "Version Control System for Rockwell Automation Studio 5000 Programs".
4. Cleanup: stop the app, delete the seeded config.json (originally none existed).
5. Report to the user: (a) edits re-applied and verified; (b) the prior change was overwritten by the ACS SVG-branding restructure; (c) I added a nuget.org NuGet source because none was configured (needed for `SharpVectors.Wpf` restore) — leave in place; (d) note the build had a transient deps.json file-lock from a running instance.

Open question for the user (previously raised, still open): whether to also rename other occurrences of "AB Logix Git Manager" (Dependencies window title suffix `Dependencies — AB Logix Git Manager`, README, assembly name `ABLogixGitManager`) for consistency with the new "Studio 5000 Git Manager" name.
</next_steps>