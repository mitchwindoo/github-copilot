<overview>
The user is iteratively expanding the AB Logix Git Manager WPF app with Git History features, progressively stricter UI testing/screenshot validation, and an Obsidian-vault wiki under `docs/`. All prior work was committed and pushed to `main` (commit `a26a601`). Most recently, the user reported that the wiki screenshots (e.g. `add-edit-controller-dialog.png`) don't show the whole application window and include part of VS Code in the background — I'm mid-fix, replacing full-desktop screenshot captures with window-cropped captures across both UI test files.
</overview>

<history>
1. (Prior, summarized previously) User requested Git History features (commit graph, branch management, commit restore), then automated UI test validation, caught a real dialog-cutoff bug, demanded screenshot-based visual testing, requested a screen-recording handoff requirement, then requested an Obsidian-vault wiki under `docs/` plus installing the `kepano/obsidian-skills` GitHub skill.
   - Built `tests/ABLogixGitManager.Tests` (12 passing xUnit tests) and `tests/ABLogixGitManager.UiTests` (FlaUI end-to-end tests).
   - Fixed New Branch dialog cutoff; added New Branch start-point dropdown (replacing freeform text) with new `InstrumentComboBox` WPF styles.
   - Established a screenshot-per-interaction testing discipline using `FlaUI.Core.Capturing.Capture.MainScreen()` (full desktop capture), saved to `%TEMP%\ABLogixGitManagerUiTestScreenshots\`.
   - Built a screen-recording handoff workflow using ffmpeg's `concat` demuxer to assemble already-captured screenshots into an `.mp4` (live `gdigrab` desktop capture proved unreliable in this environment).
   - Installed `kepano/obsidian-skills` (`obsidian-cli`, `obsidian-markdown`, `obsidian-bases`, `json-canvas`, `defuddle`) into `.github/skills/` with `NOTICE.md` provenance files and a shared MIT `LICENSE` under `.github/skills/_vendor/obsidian-skills/`.
   - Scaffolded `docs/` as an Obsidian vault: `.obsidian/` config files + 13 cross-linked Markdown pages (Home, Getting Started, Main Window, Repository Mappings, Committing Changes, Pulling and Restoring, Git History, Branch Management, Restoring a Commit, Settings and Dependencies, Troubleshooting, Screenshots Index, Contributing to This Wiki).
   - Added `tests/ABLogixGitManager.UiTests/WikiScreenshotTests.cs`, a non-assertion FlaUI test that drives the real app and saves 8 full-screen (`Capture.MainScreen()`) screenshots into `docs/assets/screenshots/`. Ran it successfully; visually reviewed 4 of the 8 images and believed they were correct (they were NOT — see below).
   - Updated `README.md`, `tests/README.md`, `tasks/todo.md`, `tasks/lessons.md`, and inserted SQL todo rows.

2. User: "Commit and push our codebase."
   - Staged all changes with `git add` (GitKraken MCP tool errored on `git_commit` with "Transport closed", so fell back to plain `git` via PowerShell).
   - Committed as `a26a601` — "feat: add Git History (commit graph, branches, restore), UI/screenshot testing, and docs wiki" (84 files changed, 7196 insertions).
   - Pushed to `origin/main` (`08c5265..a26a601`), fast-forward, no conflicts. Working tree confirmed clean.

3. User: "The screenshots you are using dont show the whole application window, and includes part of visual studio code in the background" — attached `add-edit-controller-dialog.png` as proof, showing the VS Code editor filling most of the frame with a small app dialog floating over it.
   - Root-caused: the earlier full-desktop (`Capture.MainScreen()`) approach was chosen specifically because `Capture.Element`/`Capture.Rectangle` (which crop to `AutomationElement.BoundingRectangle`) had previously produced *mismatched* crops — attributed at the time to vague "DPI/RDP quirks." Investigated FlaUI's actual `Capture.cs` source (fetched from GitHub) to confirm `Capture.Element` just crops to `element.BoundingRectangle` via GDI `CopyFromScreen`-style logic, and reasoned the real root cause is that the **test host process itself was not DPI-aware**, so UIA-reported bounding rectangles (physical pixels) didn't match the GDI/screen-capture coordinate space used by the capturing process (DPI-virtualized) — not a fundamentally unreliable technique.
   - Created a new shared helper file `tests/ABLogixGitManager.UiTests/WindowCapture.cs`:
     - `EnsureProcessIsDpiAware()` — a `[ModuleInitializer]`-attributed method that calls `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4)` via P/Invoke, guaranteed to run once before any test code/window creation.
     - `SaveWindow(AutomationElement window, string path, int paddingPx)` — crops to a single element's `BoundingRectangle` using GDI (`Bitmap` + `Graphics.CopyFromScreen`).
     - `SaveWindowUnion(IEnumerable<AutomationElement> elements, string path, int paddingPx)` — unions multiple elements' bounding rectangles (for cases like an open ComboBox dropdown whose popup renders as a separate top-level window potentially extending beyond the dialog's own bounds).
   - Rewrote `WikiScreenshotTests.cs`: removed the `Capture.MainScreen()`-based `Snapshot(string)` helper and the `FlaUI.Core.Capturing` using directive; replaced with `Snapshot(AutomationElement window, string fileName)` calling `WindowCapture.SaveWindow(...)`, and updated every call site to pass the specific window/dialog being demonstrated (`mainWindow`, `addDialog`, `settingsWindow`, `historyWindow`, `newBranchDialog`). For the "dropdown open" screenshot specifically, switched to `WindowCapture.SaveWindowUnion` combining `newBranchDialog` + `startPointBox.Items` (the visible dropdown list items) so the open popup isn't clipped. Updated the class's XML doc remarks to describe the new cropped-capture approach and reference `WindowCapture`.
   - Began the same fix in `GitHistoryUiTests.cs`: updated the `using` directives (removed `FlaUI.Core.Capturing`) and rewrote the class's XML doc remarks to reference `WindowCapture` instead of the old full-screen-only rationale. **This edit was in progress (only the top of the file — usings and doc comments — has been changed) when compaction occurred; the actual `Snapshot` method body and its 7 call sites in `GitHistoryUiTests.cs` still need to be converted from `Capture.MainScreen()` to `WindowCapture.SaveWindow(...)`.**
</history>

<work_done>
Files created:
- `tests/ABLogixGitManager.UiTests/WindowCapture.cs` — new shared capture helper (DPI-awareness fix + window/union cropping). Fully written, not yet build-verified.

Files modified (this segment):
- `tests/ABLogixGitManager.UiTests/WikiScreenshotTests.cs` — fully converted to window-cropped screenshots via `WindowCapture`. All 8 snapshot call sites updated. **Not yet rebuilt or re-run.**
- `tests/ABLogixGitManager.UiTests/GitHistoryUiTests.cs` — **only partially edited**: `using FlaUI.Core.Capturing;` removed and class-level XML doc remarks updated to reference `WindowCapture`. The `Snapshot(string label)` private method (still calls `Capture.MainScreen()`) and its 7 call sites (`Snapshot("main-window")`, `Snapshot("repo-selected")`, `Snapshot("git-history-window")`, `Snapshot("new-branch-dialog")`, `Snapshot("branch-created")`, `Snapshot("checkout-confirm-dialog")`, `Snapshot("branch-checked-out")`) have **not yet been changed** and will currently fail to compile since `Capture` (from the now-removed `FlaUI.Core.Capturing` using) is still referenced in the method body but the type reference is now unqualified/missing the using. This file is in a broken/incomplete state.

Not yet done in this segment:
- Finish converting `GitHistoryUiTests.cs`'s `Snapshot` method and call sites to use `WindowCapture.SaveWindow`, passing the correct window reference at each step (the currently-relevant top-level window: `mainWindow` for "main-window"/"repo-selected", `historyWindow` for "git-history-window"/"branch-created"/"branch-checked-out", the New Branch `dialog` for "new-branch-dialog", and the checkout `confirmDialog` for "checkout-confirm-dialog" — need to check the method signatures/local variable names in that file to wire this correctly).
- Rebuild the main app and both test projects.
- Re-run `WikiScreenshotTests` and `GitHistoryUiTests` to regenerate all screenshots.
- Visually re-review the regenerated screenshots to confirm they are now tightly cropped to just the app window with no VS Code/desktop visible.
- Re-run `ABLogixGitManager.Tests` (12/12) as a regression check (not expected to be affected, but should confirm).
- Update `tasks/lessons.md`/`tasks/todo.md` with a new entry documenting the real root cause (DPI awareness, not an inherent capture-technique limitation) and correcting the earlier (now known to be partially wrong) "Capture.Element is unreliable in this environment" lesson.
- Re-commit and push the corrected screenshots and test code once verified working, since the previous commit (`a26a601`) already pushed the flawed full-desktop screenshots to `origin/main`.
</work_done>

<technical_details>
- **Root cause of the "shows VS Code in background" bug**: the FlaUI/xUnit test host process (`testhost.exe`/`dotnet.exe`) was not DPI-aware. `AutomationElement.BoundingRectangle` (from UI Automation) reports true physical-pixel screen coordinates, but GDI screen-capture calls (and `GetSystemMetrics`) from a non-DPI-aware process are DPI-virtualized by Windows, so the two coordinate spaces disagreed — cropping to the "window" rectangle from a non-DPI-aware process captured the wrong region of the screen (which happened to catch whatever was behind the actual app window, e.g. VS Code). This invalidates the earlier lesson recorded in `tasks/lessons.md` (and in code comments) that per-element/per-window capture is "unreliable in this environment due to DPI/RDP display-scaling quirks" — the real issue was specifically the capturing process's own DPI awareness setting, which is fixable.
- **Fix**: call `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)` (`(IntPtr)(-4)`) via P/Invoke as early as possible in the test process's lifetime — implemented via a `[ModuleInitializer]`-attributed static method (`WindowCapture.EnsureProcessIsDpiAware`), which the CLR guarantees runs once, before any other code in the assembly, including before any `Application.Launch`/`UIA3Automation` calls in either test file.
- **ComboBox dropdown popups can render as separate top-level Win32 windows** that extend beyond their owning dialog's bounds — capturing just the dialog's `BoundingRectangle` could clip the open dropdown list. Fixed via `WindowCapture.SaveWindowUnion`, which unions the dialog's rect with each dropdown item's (`startPointBox.Items`) `BoundingRectangle` before cropping.
- **FlaUI's `Capture.Element`/`Capture.Rectangle` source** (fetched from `github.com/FlaUI/FlaUI` `src/FlaUI.Core/Capturing/Capture.cs`) confirmed these just wrap `element.BoundingRectangle` and a Win32-backed `Rectangle(...)` capture — nothing inherently broken about the technique itself, supporting the DPI-awareness diagnosis over "FlaUI capture is unreliable here."
- **`ImplicitUsings=enable`** in this SDK-style project already brings in `System.Linq` implicitly (confirmed via existing `.FirstOrDefault()` calls with no explicit `using System.Linq;`), so the new `.Concat(...)` call in `WikiScreenshotTests.cs` needs no additional using directive.
- **Unresolved/open concern**: `SetProcessDpiAwarenessContext` can fail (returns `false`/throws) if the process's DPI awareness has already been explicitly set by a manifest or an earlier call — wrapped in a `try/catch` as best-effort per the code's own doc comments, but this has **not yet been empirically verified to actually fix the crop** in this environment (build/run not yet done in this segment). This must be confirmed by actually rebuilding and rerunning before declaring the fix successful.
- **`GitHistoryUiTests.cs` is currently in a broken intermediate state** — the `using FlaUI.Core.Capturing;` was removed but the `Snapshot` method body still calls `Capture.MainScreen()`, which will fail to compile. This must be fixed before any build/test run will succeed.
</technical_details>

<important_files>
- `tests/ABLogixGitManager.UiTests/WindowCapture.cs`
  - New shared helper central to fixing the reported bug. Contains the DPI-awareness fix (`[ModuleInitializer]`) and the two capture methods (`SaveWindow`, `SaveWindowUnion`) both test files now depend on.
- `tests/ABLogixGitManager.UiTests/WikiScreenshotTests.cs`
  - Fully converted to window-cropped screenshots this segment. All 8 `Snapshot(...)` call sites now pass the specific window/dialog (`mainWindow`, `addDialog`, `settingsWindow`, `historyWindow`, `newBranchDialog`). The dropdown-open screenshot uses `WindowCapture.SaveWindowUnion`. Needs a rebuild + rerun to verify.
- `tests/ABLogixGitManager.UiTests/GitHistoryUiTests.cs`
  - **Currently broken/incomplete** — only the top-of-file `using` directives and class XML-doc remarks were updated; the `Snapshot(string label)` method (still references `Capture.MainScreen()`) and its 7 call sites still need conversion to `WindowCapture.SaveWindow(<relevant window>, label)`. This is the very next thing to fix.
- `docs/assets/screenshots/*.png` (8 files)
  - The currently-committed screenshots (from commit `a26a601`) are the flawed full-desktop captures the user complained about. These need to be regenerated and re-committed once the fix is verified.
- `tasks/lessons.md`
  - Contains the (now partially incorrect) lesson about `Capture.Element`/`Capture.Rectangle` being "unreliable in this environment" — should be corrected/superseded once the DPI-awareness fix is confirmed working, to avoid future confusion.
- `tests/README.md`
  - Documents the screenshot approach and rationale (`Capture.MainScreen()` full-desktop capture); will need updating once the new window-cropped approach is confirmed working.
</important_files>

<next_steps>
Immediate (interrupted by compaction):
1. Finish converting `GitHistoryUiTests.cs`: update the `Snapshot` method (or its call sites) to use `WindowCapture.SaveWindow`, passing the correct window reference at each of the 7 call sites. Need to re-view the file's current full content first to identify exact local variable names for `mainWindow`, `historyWindow`, the New Branch `dialog`, and the checkout `confirmDialog` at each snapshot point (the method signatures like `CreateBranchThroughRealDialog`/`CheckoutBranchThroughRealDialog` take `Window` parameters that should be passed through).
2. Rebuild the main app (`dotnet build src\ABLogixGitManager\ABLogixGitManager.csproj`) and both test projects to confirm no compile errors.
3. Run `WikiScreenshotTests` (`dotnet test tests\ABLogixGitManager.UiTests\... --filter "FullyQualifiedName~WikiScreenshotTests"`) and visually review all 8 regenerated screenshots to confirm they now show only the app window (no VS Code/desktop bleed).
4. Run `GitHistoryUiTests` similarly and review its 7 screenshots.
5. Run `ABLogixGitManager.Tests` (12/12 expected) as an unrelated regression check.
6. Update `tasks/lessons.md` and `tests/README.md` to correct the earlier "full-desktop capture only, per-element capture is unreliable" guidance with the real root cause (DPI awareness) and the new approach.
7. Update `tasks/todo.md` with a review section documenting this fix, evidence, and remaining risk.
8. Commit and push the corrected code + regenerated screenshots (the user previously asked to commit/push, and the flawed screenshots are already live on `origin/main`, so this is effectively a bug-fix follow-up commit).

No user-facing blockers, but the DPI-awareness fix's actual effectiveness in this specific environment (RDP/dev machine) is unverified until step 3 completes — if screenshots are still wrong after the fix, may need to fall back to a manual `GetWindowRect` P/Invoke-based crop (using the window's native handle) instead of relying on `AutomationElement.BoundingRectangle` + DPI awareness alone.
</next_steps>