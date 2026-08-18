<overview>
The user is iteratively expanding the AB Logix Git Manager WPF app with Git History features (commit graph, branch management, commit restore), while establishing progressively stricter testing/validation practices after catching real bugs I initially missed. Most recently, the user asked me to (1) add a standing requirement that finished UI work must be validated with a screen recording shown in chat before handoff, and (2) install the `kepano/obsidian-skills` GitHub skill and begin building an Obsidian-vault-style wiki under `docs/` documenting how to use the app, with screenshots. I was in the middle of investigating how to "install" that external skill into this repo's `.github/skills/` convention when the conversation was compacted.
</overview>

<history>
1. (Earlier, summarized previously) User asked for Git History/branch management/commit-restore features, then demanded automated UI test validation, then caught a real "New Branch dialog cutoff" bug my FlaUI test missed, then demanded screenshot-based visual testing.
   - Built `tests/ABLogixGitManager.Tests` (12 passing xUnit integration tests) and `tests/ABLogixGitManager.UiTests` (FlaUI end-to-end test).
   - Root-caused and fixed the New Branch dialog cutoff: `NewBranchWindow.xaml` `Height="240"` → `SizeToContent="Height"`.
   - Added a `Snapshot(label)` helper to `GitHistoryUiTests.cs` using `Capture.MainScreen()` (per-element capture proved unreliable in this environment) that saves numbered screenshots to `%TEMP%\ABLogixGitManagerUiTestScreenshots\` at every meaningful step.
   - Verified fix + screenshot integration via rebuild + test reruns + manual visual review of images; documented in `tests/README.md`, `tasks/todo.md`, `tasks/lessons.md`.

2. User: "In the start from menu for new branches, it should show a dropdown of previous commits instead of a freeform text entry allowing typos."
   - Changed `NewBranchWindow.xaml`'s Start Point field from a `TextBox` to a read-only `ComboBox`, populated from `GitHistoryViewModel.Branches`/`Commits`, defaulting to a "Current HEAD" option.
   - Added new `InstrumentComboBox`/`InstrumentComboBoxItem` styles to `App.xaml` (no ComboBox style existed previously) matching the existing dark ACS theme.
   - Updated `NewBranchWindow.xaml.cs` (new `StartPointOption` class, new constructor signature) and `GitHistoryViewModel.CreateBranchAsync` call site.
   - Built clean; ran UI test — first run failed at the checkout-confirmation step (traced via screenshots to unrelated apps like Snipping Tool/Teams stealing focus, not caused by this change); immediate rerun passed cleanly with all 7 screenshots showing correct rendering including the new dropdown.
   - Ran integration suite (12/12 passing) as regression check.
   - Updated `README.md`, `tasks/todo.md`, `tasks/lessons.md`, and inserted an SQL todo row documenting the change.

3. User: "Add to our testing criteria, that when a test has fully passed and youre ready to hand off, run a screen recording showing the new feature or change working, and present the recording in chat for review and acceptance."
   - Installed `ffmpeg` via `winget install Gyan.FFmpeg` (not previously present).
   - Attempted live screen recording via `ffmpeg -f gdigrab -i desktop` while running the real UI test — discovered this is **unreliable in this environment**: extracted frames across the entire 60s recording and the app never appeared, only VS Code, despite the app being confirmed on-screen and correctly rendering at that exact time (cross-checked against the UI test's own `Capture.MainScreen()` screenshots taken during the same run).
   - Pivoted: built the recording by assembling the test's real, already-verified screenshots into an `.mp4` via ffmpeg's `concat` demuxer (image-sequence encoding, not live capture) — produced `new-branch-dropdown-demo.mp4` in the session workspace `files/` folder, showing the full flow ending with the dropdown feature.
   - Extracted and visually reviewed 3 frames from the final video in chat (start, New Branch dialog with "Current HEAD" dropdown, branch checked out) to satisfy "present the recording in chat for review."
   - Documented the new requirement and the environment quirk in `tests/README.md` and `tasks/lessons.md`, added a review section to `tasks/todo.md`, and an SQL todo row.
   - Cleaned up scratch verification frames, keeping only the final recording.

4. User: "We should also be keeping a wiki detailing how to use the app, complete with screenshots in an obsidian vault format under docs/. Install this skill to properly utilize obsidian [kepano/obsidian-skills GitHub link]."
   - Checked existing `.github/skills/` convention in the repo — found `.github/skills/frontend-design/SKILL.md` (+ `NOTICE.md`) already following a `name`/`description`/`license` frontmatter pattern, confirming this repo supports adding project-level skills this way.
   - Fetched `https://github.com/kepano/obsidian-skills` — found it's a multi-skill repo following the "Agent Skills specification," with install instructions for various agents (Claude Code plugin marketplace, `npx skills add`, Codex `~/.codex/skills`, OpenCode `~/.opencode/skills/`). The repo structure is `skills/<skill-name>/SKILL.md` at its root (need to fetch further to confirm exact skill names/contents — not yet done).
   - Was about to fetch the actual skill file contents from the repo (e.g. via GitHub raw URLs or the repo's file listing) to replicate them under `.github/skills/obsidian/` (or similarly named per-skill folders) when compaction occurred. No files have been created for this request yet.
</history>

<work_done>
Files modified/created this segment (items 2 and 3 above; fully done and verified):
- `src/ABLogixGitManager/Views/NewBranchWindow.xaml` — Start Point `TextBox` → `ComboBox` (`IsEditable="False"`, `IsReadOnly="True"`, `DisplayMemberPath="Display"`, `SelectedValuePath="Value"`, `Style="{StaticResource InstrumentComboBox}"`); caption text simplified from "START POINT (BLANK = CURRENT HEAD)" to "START POINT".
- `src/ABLogixGitManager/Views/NewBranchWindow.xaml.cs` — added private `StartPointOption` class (`Display`, `Value`); constructor now takes `IEnumerable<GitBranchInfo> branches, IEnumerable<GitCommitInfo> commits, string? defaultStartPoint = null`; builds "Current HEAD" + branch + commit options list; `StartPoint` property now reads `StartPointBox.SelectedValue as string`.
- `src/ABLogixGitManager/App.xaml` — added `InstrumentComboBoxItem` style (defined first, ~line 278) and `InstrumentComboBox` style (~line 303) with a custom `ToggleButton`+`Popup` template matching the app's dark ACS theme; `InstrumentComboBox` sets `ItemContainerStyle` to `InstrumentComboBoxItem`.
- `src/ABLogixGitManager/ViewModels/GitHistoryViewModel.cs` — `CreateBranchAsync` now calls `new NewBranchWindow(Branches, Commits, SelectedBranch?.Name)`.
- `README.md` — added a sentence documenting the New Branch start-point dropdown behavior.
- `tests/README.md` — added a "Screen recording for handoff" section documenting the new requirement, the ffmpeg `concat`-demuxer approach, and the gdigrab live-capture quirk.
- `tasks/lessons.md` — added two new lesson entries: (1) "UIA-only UI test assertions are not sufficient — visually screenshot every interaction" (from the earlier cutoff bug), (2) "Handoff requires a screen recording of the feature working, not just a passing test" (with the gdigrab quirk documented).
- `tasks/todo.md` — added two new review sections: "New Branch start point: drop-down instead of freeform text" and "Handoff screen recording added as a standing testing requirement," each with validation evidence and remaining-risk notes.
- SQL `todos` table — inserted `new-branch-startpoint-dropdown` and `handoff-screen-recording`, both marked `done`.

Session-workspace-only artifacts (not in repo):
- `C:\Users\MitchellLandreth\.copilot\session-state\74d38c0e-c112-4d61-98f3-87b0abf688b4\files\new-branch-dropdown-demo.mp4` — final handoff recording (built from real screenshots via ffmpeg concat demuxer), ~280KB, ~20s, shows main window → repo selected → Git History window → New Branch dialog with dropdown → branch created/checked out.
- Scratch verification frames (`demo-frames/`, `demo-verify/`, temp `list.txt`) were created and then cleaned up.

Verification status (all done, confirmed working):
- Main app builds clean (0 warnings/errors) after the ComboBox change.
- `dotnet test tests\ABLogixGitManager.UiTests\...` — passing (after one unrelated flaky failure, traced to other apps stealing focus, confirmed via screenshots not caused by this change).
- `dotnet test tests\ABLogixGitManager.Tests\...` — 12/12 passing (regression check).
- Manually viewed screenshots and video frames confirming the New Branch dialog's Start Point dropdown renders correctly with no cutoff, showing "Current HEAD" as default.

Not yet started (item 4, in progress at time of compaction):
- Installing/adapting the `kepano/obsidian-skills` skill into this repo (likely under `.github/skills/`).
- Creating the `docs/` Obsidian vault wiki structure.
- Writing any wiki content or taking any app screenshots for the wiki.
</work_done>

<technical_details>
- **No ComboBox style existed in the app before this session** — `InstrumentComboBoxItem` must be defined in `App.xaml` *before* `InstrumentComboBox` since the latter's `ItemContainerStyle` setter references it via `StaticResource`, and WPF resource dictionaries resolve `StaticResource` references sequentially at parse time (forward references to same-dictionary keys fail).
- **ComboBox template structure**: outer `ControlTemplate` contains a `ToggleButton` (with its own nested `ControlTemplate` for the flat bordered box + dropdown arrow `Path`), a `ContentPresenter` bound to `SelectionBoxItem`/`SelectionBoxItemTemplate`, and a `Popup` (bound to `IsDropDownOpen`) containing a `Border`/`ScrollViewer`/`ItemsPresenter` for the dropdown list. Background/BorderBrush must be explicitly `TemplateBinding`'d onto the `ToggleButton` element (not inherited automatically) since its own nested template needs `TemplateBinding` down to that level.
- **`ffmpeg` was not installed** on this dev machine; installed via `winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements --silent`. The executable ends up at a path under `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_...\ffmpeg-*-full_build\bin\ffmpeg.exe`; PATH updates from winget require a fresh shell to take effect, so the full path was used directly in this session.
- **Critical new environment quirk discovered**: `ffmpeg -f gdigrab -i desktop` (live screen/desktop capture) does **not reliably see the WPF app window** in this environment — it consistently captured only the VS Code/editor window for an entire 60-second recording, even while the app was independently confirmed to be correctly on-screen at that exact wall-clock moment (verified via the UI test's own in-process `Capture.MainScreen()` screenshots taken during the same test run). This appears to be a capture-session isolation issue affecting *external* GDI screen-capture processes specifically, distinct from (though similar in nature to) the earlier-discovered `Capture.Element`/`Capture.Rectangle` per-element capture mismatch quirk (both are documented together in `tasks/lessons.md`).
  - **Workaround established and documented**: build recordings by encoding the UI test's already-captured, already-verified `Capture.MainScreen()` PNG screenshots into an `.mp4` using ffmpeg's `-f concat -safe 0` demuxer with an explicit list file (each entry: `file '<path>'` + `duration 2.5`, with the last file repeated without a duration line per concat demuxer requirements). This sidesteps live capture entirely and is still valid evidence since each frame is a real screenshot of the running app.
  - Exact working command pattern is documented in `tests/README.md` for reuse.
- **Skill installation mechanism for this repo**: confirmed via `.github/skills/frontend-design/SKILL.md` that this repo supports project-level skills placed under `.github/skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`, `license`) plus a `NOTICE.md`. This is the pattern to follow for installing the `obsidian-skills` repo's skill(s), though the exact skill name(s)/folder structure inside `kepano/obsidian-skills` (its `skills/<skill-name>/SKILL.md` layout per the repo's own README) still needs to be fetched and adapted — **not yet done**.
- **Unresolved/open questions for the next segment**:
  - Which specific skill(s) from `kepano/obsidian-skills` should be installed (the repo appears to bundle multiple skills under `skills/`, not just one) — need to fetch the repo's file tree to enumerate them.
  - How to best adapt the skill for this environment given there's no direct "install skill from URL" tool available — the plan is to manually fetch and copy the relevant `SKILL.md` (and any supporting files) into `.github/skills/`.
  - The user wants the wiki "under docs/" in Obsidian vault format with screenshots — need to determine vault structure conventions (e.g. `.obsidian/` config folder, Markdown files with wikilinks, possibly Canvas/Bases per the skill's stated scope) once the skill is reviewed.
</technical_details>

<important_files>
- `src/ABLogixGitManager/Views/NewBranchWindow.xaml` / `.xaml.cs`
  - Contains this session's dropdown feature implementation. Fully working and verified.
- `src/ABLogixGitManager/App.xaml`
  - New `InstrumentComboBox`/`InstrumentComboBoxItem` styles added (~lines 276–384). First ComboBox styling in the app; reusable for any future dropdown needs.
- `src/ABLogixGitManager/ViewModels/GitHistoryViewModel.cs`
  - `CreateBranchAsync` (~line 135) updated to pass `Branches`/`Commits` into the dialog.
- `tests/ABLogixGitManager.UiTests/GitHistoryUiTests.cs`
  - Contains the `Snapshot()` screenshot helper (from earlier segment) that both the dropdown feature verification and the handoff recording relied on. Not modified this segment but central to how validation evidence is produced.
- `tests/README.md`, `tasks/lessons.md`, `tasks/todo.md`
  - All three updated with the new dropdown feature and the new screen-recording handoff requirement + ffmpeg gdigrab quirk. These are the canonical record of testing practices going forward.
- `.github/skills/frontend-design/SKILL.md` (+ `NOTICE.md`)
  - Reference example for how project-level skills are structured/installed in this repo; template for installing the obsidian skill.
- `new-branch-dropdown-demo.mp4` (session workspace `files/`, not repo)
  - The delivered handoff recording for the dropdown feature; already presented/reviewed in chat via extracted frames.
</important_files>

<next_steps>
Immediate (interrupted by compaction):
1. Fetch the `kepano/obsidian-skills` GitHub repo's file tree (e.g. via `web_fetch` on the repo's file listing or raw GitHub URLs) to enumerate the actual skill(s) under its `skills/` directory and read their `SKILL.md` contents.
2. Adapt and install the relevant skill(s) into this repo under `.github/skills/<skill-name>/` (following the `frontend-design` pattern: `SKILL.md` with frontmatter + any `NOTICE.md`/license), so the skill becomes available for future use in this repo.
3. Once the skill is available, invoke it (per the tool instructions: "When a skill is relevant, you must invoke this tool IMMEDIATELY as your first action") before proceeding with the actual wiki-building work.
4. Design and scaffold the Obsidian vault structure under `docs/` (e.g. `docs/wiki/` or similar, with `.obsidian/` config, Markdown pages, possibly an index/home note) per the installed skill's guidance.
5. Take real app screenshots (using the established `Capture.MainScreen()`/FlaUI approach, or manual screenshots) to illustrate the wiki pages — likely need a small screenshot-capture pass similar to the earlier scratch tooling, but organized as permanent wiki assets under `docs/`.
6. Write actual wiki content documenting how to use the app (main window, repo management, Git History, branch management, commit restore, settings/dependencies) — scope and page structure not yet defined; may need to ask the user for confirmation on structure/depth once the skill's conventions are understood.
7. Verify the vault opens/renders correctly if possible, and update `tasks/todo.md`/`plan.md` with progress once this phase begins in earnest.

No user-facing blockers yet, but the exact skill name(s) and vault conventions need to be discovered before file creation begins.
</next_steps>