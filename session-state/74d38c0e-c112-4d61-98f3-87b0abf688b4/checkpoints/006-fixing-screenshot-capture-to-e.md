<overview>
The user is iteratively expanding the AB Logix Git Manager WPF app with Git History features, progressively stricter UI testing/screenshot validation, and an Obsidian-vault wiki under `docs/`. All prior work was committed and pushed to `main` (commit `a26a601`). This session's focus was fixing a user-reported bug: wiki/UI-test screenshots showed VS Code bleeding into the frame instead of a clean crop of just the app window. This required discovering and fixing a chain of five compounding root causes in the screenshot-capture helper, then re-verifying every regenerated screenshot visually (not just trusting green test runs) before committing.
</overview>

<history>
1. (Prior session, summarized before this segment) User requested Git History features, automated UI test validation, caught a dialog-cutoff bug, demanded screenshot-based visual testing, requested screen-recording handoff, requested an Obsidian wiki under `docs/`, then said "Commit and push our codebase" (done as commit `a26a601`), then reported: "The screenshots you are using dont show the whole application window, and includes part of visual studio code in the background."
   - Root-caused the VS Code bleed to the earlier `Capture.MainScreen()` (full-desktop capture) approach.
   - Created `tests/ABLogixGitManager.UiTests/WindowCapture.cs` with DPI-awareness fix + GDI `CopyFromScreen`-based window/union cropping.
   - Rewrote `WikiScreenshotTests.cs` fully to use the new cropped capture.
   - Began (but left incomplete) converting `GitHistoryUiTests.cs` similarly — only usings/doc comments updated, method body still broken.

2. This segment picked up mid-fix, continuing the compaction-interrupted work:
   - Finished converting `GitHistoryUiTests.cs`: updated the `Snapshot` method signature to take an `AutomationElement window` parameter and rewired all 7 call sites (`mainWindow`, `historyWindow`, `dialog`, `confirmDialog`) to use `WindowCapture.SaveWindow`.
   - Rebuilt main app + both test projects (had to clean `obj`/`bin` once due to a stale BAML cache error).
   - Ran `WikiScreenshotTests` — passed, but visual review revealed **new bugs**: `git-history-window.png` showed a real File Explorer window overlapping/obscuring the Git History window (GDI `CopyFromScreen` captures whatever's on top of a screen region, not the target window itself).
   - **First fix attempt**: added `BringToForeground()` to `WindowCapture` using `Window.SetForeground()`/`AutomationElement.Focus()` before capture. Rebuilt, reran — fixed `git-history-window.png`, but a *different* screenshot (`main-window-empty-selection.png`) now captured a totally wrong region (a VS Code Copilot chat panel), proving `SetForegroundWindow` was silently refused by Windows' foreground-lock policy for the background test process.
   - **Root-caused via FlaUI source inspection** (fetched `Window.cs`/`AutomationElement.cs` from GitHub) that `SetForeground()` just calls `User32.SetForegroundWindow`, which is fundamentally unreliable from a non-foreground process.
   - **Second fix (major rewrite)**: rewrote `WindowCapture.cs` entirely to use the `PrintWindow` Win32 API (with `PW_RENDERFULLCONTENT` for WPF's GPU compositing) to capture a window's own rendered content directly by HWND, immune to both DPI and foreground/z-order issues. Deleted and recreated `WindowCapture.cs`.
   - Rebuilt/reran — screenshots were now un-obscured but **badly clipped on right/bottom edges** — traced to accidentally dropping the `[ModuleInitializer]` DPI-awareness fix during the rewrite (without it, `GetWindowRect` returns undersized/virtualized coordinates). Re-added `EnsureProcessIsDpiAware()`.
   - Rebuilt/reran — most screenshots now correct, but `git-history-window.png` intermittently showed a stale "Loading history…" frame despite the test's `Retry.WhileFalse` UIA-based wait already passing — diagnosed as a WPF dispatcher/DirectComposition render-lag (UIA property updates can outrun the actual compositor frame). **Fix**: added a `SettleBeforeCapture()` (`Thread.Sleep(200)`) before every capture.
   - Rebuilt/reran — all single-window screenshots now correct, but `new-branch-dialog-startpoint-dropdown-open.png` (a union capture of dialog + open ComboBox popup) still showed the dropdown collapsed. Debugged via temporary diagnostic `_output.WriteLine` calls: discovered the WPF Popup's items report `NativeWindowHandle: 0` and their `.Parent` chain never surfaces a distinct "Window" ancestor — the popup genuinely renders as a separate real HWND, but UI Automation doesn't expose it as discoverable via `.Parent` walks, `Window.Popup` (FlaUI's built-in heuristic, returned null), or even `Application.GetAllTopLevelWindows(...)` (also didn't find it after excluding known windows).
   - **Final fix for the dropdown case**: added `WindowCapture.SaveElementBoundsUnion(...)`, a narrowly-scoped fallback that unions each element's raw `BoundingRectangle` and uses GDI `CopyFromScreen` directly (bypassing HWND resolution entirely) — justified as safe *only* because it runs immediately after the interaction that opened the popup, so nothing else can have been drawn on top of it yet. Removed the now-dead `SaveWindowUnion` (HWND-based union) method entirely as it couldn't find the popup's HWND. Updated `WikiScreenshotTests.cs`'s dropdown-open call site to use the new method with `startPointBox.Items` directly (reverting the earlier `Popup`/`GetAllTopLevelWindows` diagnostic attempts).
   - Rebuilt/reran — dropdown-open screenshot now correctly shows the expanded list. All 8 wiki screenshots and 7 GitHistory screenshots visually confirmed correct via the `view` tool.
   - **Discovered and fixed a second, unrelated bug**: running both UI test classes (`WikiScreenshotTests` + `GitHistoryUiTests`) together via `dotnet test` (no filter) caused *both* to fail (COM HRESULT error and a "0 commits found" race) — root-caused to xUnit's default test-class parallelization colliding since both launch real interactive GUI app instances competing for focus/desktop state. **Fixed** by adding `tests/ABLogixGitManager.UiTests/AssemblyInfo.cs` with `[assembly: CollectionBehavior(DisableTestParallelization = true)]`. Reran the full UI test project — both passed together (17s total).
   - Ran `ABLogixGitManager.Tests` (unit tests) — 12/12 passed, confirming no regression.
   - Updated `tasks/lessons.md`: revised the outdated "Capture.MainScreen() is the reliable pattern" guidance (now marked superseded/wrong) and added a new detailed lesson section "Per-window screenshot cropping needs `PrintWindow`, not `BoundingRectangle` + screen capture" documenting all five root causes found this session plus the test-parallelization fix, with an explicit rule: always visually review every regenerated screenshot, and always run the whole UI test project together, not just one file.
</history>

<work_done>
Files created:
- `tests/ABLogixGitManager.UiTests/WindowCapture.cs` — final version uses `PrintWindow` (HWND-based capture, DPI-aware via `[ModuleInitializer]`) for `SaveWindow`, and a separate `SaveElementBoundsUnion` (GDI `CopyFromScreen` over raw `BoundingRectangle` union) as a narrow fallback for the one case (open ComboBox popup) where HWND resolution doesn't work. Fully built and verified working.
- `tests/ABLogixGitManager.UiTests/AssemblyInfo.cs` — new file, disables xUnit test-class parallelization for this assembly (both test classes drive a real interactive desktop and collide if run concurrently).

Files modified:
- `tests/ABLogixGitManager.UiTests/WikiScreenshotTests.cs` — all `Snapshot(...)` calls use `WindowCapture.SaveWindow`; the dropdown-open screenshot uses `WindowCapture.SaveElementBoundsUnion(new AutomationElement[] { newBranchDialog }.Concat(startPointBox.Items), ...)`. Updated class remarks referencing `WindowCapture`.
- `tests/ABLogixGitManager.UiTests/GitHistoryUiTests.cs` — fully converted: `Snapshot(AutomationElement window, string label)` now calls `WindowCapture.SaveWindow(window, path, paddingPx: 4)`; all 7 call sites pass the correct window/dialog reference (`mainWindow`, `historyWindow`, `dialog`, `confirmDialog`).
- `tasks/lessons.md` — corrected/superseded the old "Capture.MainScreen() is reliable" lesson; added a new detailed lesson documenting the 5-layer root cause chain (DPI awareness → foreground/z-order unreliability → PrintWindow fix → render-lag settle delay → WPF Popup HWND undiscoverability) plus the test-parallelization fix.

Work completed and verified:
- [x] `GitHistoryUiTests.cs` conversion to window-cropped capture (was left broken by prior compaction, now complete and building).
- [x] Main app + both test projects rebuild cleanly (0 errors).
- [x] `WikiScreenshotTests` run individually — passes, all 8 screenshots visually confirmed correct (no VS Code bleed, no clipping, no stale "Loading" frames, dropdown shown expanded).
- [x] `GitHistoryUiTests` run individually — passes, all 7 screenshots visually confirmed correct.
- [x] Both UI test classes run together via `dotnet test` (no filter) — both pass (previously failed due to parallelization collision, now fixed).
- [x] `ABLogixGitManager.Tests` (unit tests) — 12/12 pass, no regression.
- [x] `tasks/lessons.md` updated with corrected/detailed root-cause documentation.

Not yet done (in progress when context compaction occurred):
- `tests/README.md` still references the old `Capture.MainScreen()` full-desktop-capture rationale and needs updating to describe the new `PrintWindow`-based approach.
- `tasks/todo.md` needs a review section added documenting this fix, evidence, and remaining risk (per repo's planning conventions).
- The corrected screenshots and test code (in `docs/assets/screenshots/*.png`, `WindowCapture.cs`, `WikiScreenshotTests.cs`, `GitHistoryUiTests.cs`, `AssemblyInfo.cs`, `tasks/lessons.md`) have **not yet been committed or pushed** — the previous commit (`a26a601`) already pushed the flawed full-desktop screenshots to `origin/main`, so this is an outstanding bug-fix follow-up commit the user will expect (they explicitly asked to "commit and push our codebase" previously, and this segment was triggered by them catching a bug in that pushed work).
</work_done>

<technical_details>
- **Five compounding root causes** were found and fixed in sequence for the screenshot-cropping bug (see `tasks/lessons.md` for full writeup):
  1. Test host process wasn't DPI-aware → `GetWindowRect`/GDI coordinates disagreed with UIA's physical-pixel `BoundingRectangle`. Fixed via `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4)` in a `[ModuleInitializer]`-attributed method (guaranteed to run once, before any window/automation code).
  2. `Window.SetForeground()` (→ Win32 `SetForegroundWindow`) can be silently refused by Windows' foreground-lock policy for a background process — not a reliable fix for "other window overlapping the capture region."
  3. **Real fix**: `PrintWindow` Win32 API with `PW_RENDERFULLCONTENT` flag (required for GPU-composited/WPF windows) renders a window's own content by HWND directly, immune to both DPI-virtualization and foreground/z-order issues.
  4. WPF's UI Automation property updates (e.g. list item count) can be observed by a `Retry.WhileFalse` check *before* the DirectComposition compositor has actually pushed the corresponding visual frame — `PrintWindow` can then capture a stale frame. Fixed with an unconditional short settle delay (`Thread.Sleep(200)`) before every capture.
  5. A WPF `ComboBox`'s open `Popup` renders as a genuine separate Win32 HWND, but UI Automation does **not** expose it as discoverable via `.Parent` ancestor walks from the popup's items (parent resolves to the ComboBox's own logical tree, not a Window), nor via FlaUI's `Window.Popup` heuristic, nor via `Application.GetAllTopLevelWindows(...)`. For this one case, fell back to raw `BoundingRectangle` + `Graphics.CopyFromScreen` (the technique otherwise rejected for being z-order-unsafe) — justified as safe only immediately after the interaction that opened the popup.
- **Test parallelization**: xUnit parallelizes test classes by default; UI tests that launch real interactive GUI app instances and manipulate desktop focus/z-order will collide if run concurrently. Fixed via `[assembly: CollectionBehavior(DisableTestParallelization = true)]` — this is a one-time assembly-level fix, not per-test.
- **FlaUI API details learned** (via fetching source from `github.com/FlaUI/FlaUI`):
  - `AutomationElement.Focus()` calls `SetForeground()` if `ControlType == ControlType.Window`, else `FocusNative()` (Win32 `SetFocus` via thread-input attach) or falls back to UIA `SetFocus()`.
  - `Window.SetForeground()` is just `User32.SetForegroundWindow(handle)` — no special reliability guarantees.
  - `Window.Popup` (FlaUI's built-in property) looks for a WPF popup as `FindFirstChild` on the *main window* with empty name + class "Popup" — didn't work for our case (dialog-owned popup, or a naming/class mismatch with the custom `InstrumentComboBox` style).
  - `AutomationElement.Capture()`/`CaptureToFile()` internally use `Capturing.Capture.Element(this)`, which is GDI-region-based, not `PrintWindow` — confirms the built-in FlaUI capture helpers share the same z-order/DPI limitations this session worked around.
- **Build gotcha**: hit a stale BAML cache error (`BG1002: File '...GitRepositoryActionWindow.baml' cannot be found`) requiring a full `Remove-Item -Recurse -Force obj, bin` + rebuild of the main app project before the UI test project would build cleanly.
- **`.NET 10 SDK 10.0.301`**, `net10.0-windows` target confirmed still current for this repo.
- Assumption not fully verified: whether `PrintWindow` with `PW_RENDERFULLCONTENT` will behave identically across different DPI scale factors or multi-monitor setups beyond this single dev machine — not tested, but reasoned to be robust since it doesn't depend on screen coordinates at all.
</technical_details>

<important_files>
- `tests/ABLogixGitManager.UiTests/WindowCapture.cs`
  - Central shared capture helper. Final implementation: `EnsureProcessIsDpiAware()` (module initializer), `SaveWindow(AutomationElement, path, paddingPx)` using `PrintWindow`-by-HWND, `SaveElementBoundsUnion(IEnumerable<AutomationElement>, path, paddingPx)` using GDI `CopyFromScreen` over raw bounding-rect union (popup-specific fallback), `SettleBeforeCapture()` render-lag delay, `GetWindowHandle` (walks `.Parent` to find nearest element with a valid `NativeWindowHandle`), `GetWindowRect`/`CaptureWindow`/`SavePadded` helpers, and P/Invoke declarations for `PrintWindow`, `GetWindowRect`, `SetProcessDpiAwarenessContext`. Extensive remarks doc-comment explains the full rejected-approaches history for future maintainers.
- `tests/ABLogixGitManager.UiTests/WikiScreenshotTests.cs`
  - Drives the real app to generate all 8 `docs/assets/screenshots/*.png` files used by the wiki. All snapshot calls now use the fixed `WindowCapture` methods; verified passing and visually correct.
- `tests/ABLogixGitManager.UiTests/GitHistoryUiTests.cs`
  - End-to-end FlaUI test for Git History feature; also captures 7 screenshots to `%TEMP%\ABLogixGitManagerUiTestScreenshots\`. Fully converted from the broken intermediate state left by prior compaction; verified passing and visually correct.
- `tests/ABLogixGitManager.UiTests/AssemblyInfo.cs`
  - New file; disables test-class parallelization, fixing a real concurrency bug where both UI test classes failed when run together.
- `docs/assets/screenshots/*.png` (8 files)
  - Regenerated this session with the fixed capture pipeline; all visually confirmed correct (no VS Code bleed, no clipping, no stale frames, dropdown correctly shown expanded). Not yet committed.
- `tasks/lessons.md`
  - Updated with corrected screenshot-capture guidance (superseding the earlier, now-known-wrong "Capture.MainScreen() is reliable" lesson) and a new detailed 5-cause root-cause writeup plus the test-isolation fix.
- `tests/README.md`
  - **Not yet updated** — still documents the old `Capture.MainScreen()` full-desktop rationale; needs revision to describe the new `PrintWindow`-based approach and the `SaveElementBoundsUnion` popup exception.
- `tasks/todo.md`
  - **Not yet updated** — needs a review section per repo conventions documenting this fix, validation performed, and residual risk.
</important_files>

<next_steps>
Immediate (interrupted by compaction — was about to update `tests/README.md` next, based on the flow of work):
1. Update `tests/README.md` to replace the old `Capture.MainScreen()`/full-desktop-capture description with the new `PrintWindow`-based `WindowCapture` approach, including the `SaveElementBoundsUnion` exception for dropdown popups and the note about disabled test parallelization.
2. Add a review section to `tasks/todo.md` documenting: the bug (VS Code bleeding into screenshots), the fix (5-layer root cause chain, see `tasks/lessons.md`), validation performed (visual review of all 15 screenshots, full UI test suite passing together, unit test regression check), and residual risk (untested across different DPI scales/multi-monitor setups; `PrintWindow` reliability not verified on other Windows versions).
3. Commit all changes (`WindowCapture.cs`, `AssemblyInfo.cs`, `WikiScreenshotTests.cs`, `GitHistoryUiTests.cs`, `tasks/lessons.md`, updated `tests/README.md` and `tasks/todo.md`, and the 8 regenerated `docs/assets/screenshots/*.png` files) with a message describing this as a bug-fix follow-up to the previously-pushed flawed screenshots.
4. Push to `origin/main`.
5. Report back to the user: summarize the bug, root cause(s) found, the fix, and point them to the regenerated screenshots for their own review (per the repo's completion standard — ask whether the fix addresses the root cause, remains simple, and would withstand skeptical review).

No blockers currently known; all verification steps performed so far have passed. The main remaining risk is that this was only validated on this one dev machine/DPI configuration.
</next_steps>