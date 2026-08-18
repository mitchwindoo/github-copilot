# Implementation Plans — Unfinished Feature Sets

Four self-contained feature plans, each independent enough to tackle separately.

## Progress Log (updated 2026-07-28)

- **Feature Set A — Git install/repair automation + vendor-guided paths**: ✅ Done. Commit `1db505e`.
- **Feature Set D — Extended Git operations in History window**: ✅ Done. Commit `7bf16b1` + follow-up UI fixes (status-message overlap, log wrapping, log-hide toggle, Manage Remotes labeling/overflow/empty-state).
- **Studio 5000 version compatibility gate** (ad hoc request, added mid-session, not in the original four): ✅ Done. Commit `9b8838a`. Detects the Studio 5000 version an ACD/exploded project requires (ACD plain-text save history, or L5X `SoftwareRevision` as fallback) and blocks Commit/Restore when no installed Studio 5000 version matches (major.minor compare).
- **Feature Set C — GitHub Actions release workflow + smoke tests**: ✅ Done. Commit `1f99d4a`. Verified the existing self-contained publish profile actually builds and launches. Added `build-and-test.yml` (CI on push/PR), `release.yml` (tag-triggered draft release + checksum), 4 smoke tests (63 total unit tests pass). Also cleaned up two committed release binaries (~140MB combined) that had been tracked directly in git history — replaced with `.gitignore` entries and a `releases/README.md` explaining releases now come from GitHub Release assets. Updated README.md and plan.md to reflect current vs. still-outstanding gaps (provenance pinning, clean-machine validation).
- **Feature Set B — Provenance pinning and integrity checks**: ⏳ Not started. Only remaining item from the original four-part plan.

### Next up
- **B**: Pin a reviewed VCS-tools commit/tag, add SHA-256 verification (`IntegrityCheckService`) before first execution of a built `l5xgit.exe`, write a provenance sidecar, unit tests.
- Not yet pushed to `origin/main` — 8 commits ahead locally as of this update; push when ready.

---

## Feature Set A — Git Install/Repair Automation + Vendor-Guided Paths

### Current state
- `DependencyCheckerService` already detects Git, .NET SDK 10, Studio 5000, Logix Designer SDK, and l5xgit.
- `DependencyInstallerService` already installs .NET SDK 10 via winget and clones/builds Rockwell VCS tools.
- `SettingsViewModel` exposes `InstallDotNetSdkCommand`, `InstallAndBuildRockwellVcsToolsCommand`, `InstallStudioCustomToolsMenuCommand`.
- **Git has no install/repair action** — the checker detects it but the installer has no winget/guided path for it.
- **Studio 5000 and Logix Designer SDK have no actionable next step** — the checker tells the user "install from Rockwell media or FactoryTalk Hub" but there is no button, link, or guided flow to open the vendor source.

### What is needed

#### A1 — Git install/repair via winget
- Add `InstallGitAsync(Action<string> onOutput, CancellationToken ct)` to `DependencyInstallerService`.
  - Try `winget install --id Git.Git --exact --source winget --silent`.
  - Post-install: verify `git --version` succeeds; surface result.
  - If winget is unavailable, surface a message with the `https://git-scm.com/download/win` URL.
- Add `InstallGitCommand` to `SettingsViewModel` (enabled when Git is Missing/Failed and not already action-busy).
- Wire the button in `SettingsWindow.xaml` in the Git row.
- Add unit test: `InstallGitAsync_WhenGitAlreadyPresent_ReturnsSuccessWithoutLaunching`.

#### A2 — Vendor-guided paths for Studio 5000 and Logix Designer SDK
- Add `OpenFactoryTalkHubAsync()` helper (opens `https://compatibility.rockwellautomation.com/` or the FactoryTalk Hub URI).
- Expose `OpenStudio5000VendorGuideCommand` and `OpenSdkVendorGuideCommand` in `SettingsViewModel`.
  - When Studio 5000 is Missing: label "Get Studio 5000 ↗" — opens the Rockwell product page.
  - When SDK is Missing: label "Open FactoryTalk Hub ↗" — same or SDK-specific page.
  - These actions are always informational (open browser/link), never silent install.
- Wire both buttons into the matching dependency rows in `SettingsWindow.xaml`.
- Document in `docs/Settings and Dependencies.md` that Studio 5000 and SDK are vendor-installed only; update the table that currently lacks action guidance.

#### A3 — Repair action for a broken Git install
- Add `RepairGitAsync` (equivalent to reinstall — runs winget repair/upgrade path for `Git.Git`).
- Enabled when Git status is `Incompatible` or `Failed`.
- Surface as "Repair Git" button alongside the existing status rows in Settings.

#### Acceptance criteria
- A user with no Git can click "Install Git" in Settings and get a working Git or a clear next step.
- Studio 5000 Missing row has a "Get Studio 5000 ↗" button that opens the correct vendor URL.
- SDK Missing row has an equivalent vendor-link button.
- No action claims silent install of Studio 5000 or the SDK.
- All new installer actions log Info at start, Info or Warn at end, Error on exception.

---

## Feature Set B — Provenance Pinning and Integrity Checks for Downloads

### Current state
- `DependencyInstallerService.InstallAndBuildRockwellVcsToolsAsync` clones the Rockwell VCS repo from GitHub with no pinned commit/tag, no hash check on any downloaded files, and no signature check.
- The built `l5xgit.exe` is first-run immediately after `dotnet build` with no hash comparison against a trusted baseline.
- There is no manifest, lock file, or stored provenance record for any downloaded artifact.

### What is needed

#### B1 — Pinned upstream source version
- Define a `const string RockwellVcsToolsCommit` (or tag) in `DependencyInstallerService` that matches a reviewed upstream release — e.g. `"v1.2.3"` or a full 40-char SHA.
- After clone, run `git -C <dir> checkout <pinned-ref>` so the working tree is always at the reviewed version, even when the default branch moves.
- After `git pull`, run the same checkout to re-pin; log a `Warn` if the pull cannot advance to the pin.
- Record the resolved SHA and timestamp in a small JSON sidecar (e.g. `%APPDATA%\ABLogixGitManager\tools\vcs-provenance.json`) after a successful build.

#### B2 — Hash verification before first execution
- After `dotnet build` succeeds, compute `SHA-256` of the built `l5xgit.exe`.
- Compare against a trusted baseline hash stored in the application (embedded resource or a file in `src/ABLogixGitManager/Assets/trusted-hashes.json`).
  - Baseline format: `{ "l5xgit": { "<version-tag>": "<hex-sha256>" } }`.
  - On mismatch: abort, log Error, surface "VCS tools binary hash mismatch — installation blocked" in the Settings output.
- Add `IntegrityCheckService` with `VerifyFileHashAsync(string filePath, string expectedSha256)`.
- Unit-test `VerifyFileHashAsync` with a known file and a deliberate mismatch.

#### B3 — Provenance record and re-check on startup
- `DependencyCheckerService.CheckL5xGitAsync` should, after confirming the path exists and launches, optionally compare its SHA-256 to the stored provenance record and surface `Incompatible` with a "hash changed since last verified build" warning.
- This does not block use of a user-supplied path; it surfaces a warning when the managed path differs.

#### B4 — Git binary verification (informational)
- When `CheckGitAsync` returns `Ready`, log the resolved executable path (from `where git`) and version.
- Add a note to `docs/Settings and Dependencies.md` explaining what is and is not verified for Git.

#### Acceptance criteria
- Building VCS tools always checks out the pinned ref; the user cannot accidentally build from a newer unreviewed commit.
- The built binary is never launched if its hash does not match the trusted baseline.
- `IntegrityCheckService` has unit tests covering match, mismatch, missing file, and empty expected hash.
- The provenance sidecar is written after every successful verified build.

---

## Feature Set C — GitHub Actions Release Workflow and Smoke-Test Suite

### Current state
- `.github/` contains `agents/`, `copilot-instructions.md`, `skills/` — no `workflows/` directory, no YAML files.
- `tests/ABLogixGitManager.Tests` has unit/integration tests (xUnit).
- `tests/ABLogixGitManager.UiTests` has UI screenshot tests.
- The `src/ABLogixGitManager/publish/` folder exists but contains no publish profile.
- No signing certificate configuration, no self-contained publish settings, no release artifact definition.

### What is needed

#### C1 — Self-contained publish profile
- Add `Properties/PublishProfiles/SelfContainedWin-x64.pubxml` to the main project:
  - `RuntimeIdentifier: win-x64`, `SelfContained: true`, `PublishSingleFile: true` (validate WPF compat).
  - `IncludeNativeLibrariesForSelfExtract: true` for native DLLs if needed.
  - `PublishDir: publish\win-x64\`.
- Validate the profile builds on the current machine before wiring CI.

#### C2 — CI workflow (`build-and-test.yml`)
- `.github/workflows/build-and-test.yml` runs on every push and PR to `main`/`develop`:
  - `windows-latest` runner.
  - Restore, build `Release`, run `ABLogixGitManager.Tests` (unit + integration, no UI runner needed).
  - Upload test results as an artifact.
- Do **not** run `ABLogixGitManager.UiTests` in CI — they require an interactive desktop session.

#### C3 — Release workflow (`release.yml`)
- Triggered on push of a `v*.*.*` tag.
- Steps:
  1. Restore and build.
  2. Run unit tests (fail fast).
  3. `dotnet publish` with the `SelfContainedWin-x64` profile.
  4. Compute SHA-256 of the output EXE; write `checksums.txt`.
  5. (Optional/deferred) Code sign if a signing certificate secret is available.
  6. Upload EXE and `checksums.txt` as a GitHub Release draft.
- The release stays a draft until manually promoted; this preserves the clean-machine validation gate from `plan.md`.

#### C4 — Smoke-test suite
- Add `tests/ABLogixGitManager.Tests/SmokeTests.cs` with:
  - `AppConfigService_LoadAndSave_RoundTrips`: creates a temp config, saves, reloads, asserts equality.
  - `DependencyCheckerService_CheckGitAsync_DoesNotThrow`: calls the real checker; asserts it returns a non-null `DependencyInfo` without exception (git may or may not be present — just no crash).
  - `AppLogger_WriteAllLevels_DoesNotThrow`: calls Info/Warn/Error with and without exception; asserts no throw.
- These run in the CI workflow without UI or git-repo scaffolding beyond what already exists.

#### C5 — Document the release process
- Update `docs/Settings and Dependencies.md` with the release format (self-contained, no .NET install required).
- Add a `docs/Release Process.md` describing the tag → workflow → draft release → clean-machine validation → promote flow.

#### Acceptance criteria
- Every PR to `main` runs the CI workflow and reports pass/fail on unit tests.
- Pushing `v*.*.*` produces a GitHub Release draft with the EXE and `checksums.txt`.
- The release remains a draft until clean-machine validation is completed.
- All four new smoke tests pass in the CI workflow.

---

## Feature Set D — Extended Git Operations in History Window

### Current state (already in `GitRepositoryService`)
- `GetCommitGraphAsync`, `GetBranchesAsync`, `CreateBranchAsync`, `CheckoutBranchAsync`, `DeleteBranchAsync`
- `GetRemotesAsync`, `GetCurrentBranchNameAsync`, `HasUncommittedChangesAsync`, `RestoreCommitFilesAsync`

### Current state (`GitHistoryViewModel` / `GitHistoryWindow`)
- Refresh, Create Branch, Checkout Branch, Delete Branch, Restore Commit to ACD, Cancel.

### What is needed

The new operations are grouped into three surface areas.

#### D1 — Remote sync: Fetch, Push, Pull-merge
Add to `GitRepositoryService`:
- `FetchAsync(repoPath, remote = "origin", allRemotes = false, onOutput, ct)` — `git fetch [remote | --all]`.
- `PushAsync(repoPath, remote, branch, setUpstream, onOutput, ct)` — `git push [-u] <remote> <branch>`.
- `PullMergeAsync(repoPath, remote, branch, onOutput, ct)` — `git pull <remote> <branch>` (distinct from the L5xGit-orchestrated pull-restore in `MainViewModel`).
- `GetRemoteDetailsAsync(repoPath, ct)` — returns name+URL list via `git remote -v` for the management UI.

Add to `GitHistoryViewModel`:
- `FetchCommand` — fetches origin (or all remotes if configured), refreshes graph.
- `PushCommand` — pushes current branch to its upstream; prompts to set `-u` if no upstream is configured.
- `PullMergeCommand` — pulls current branch, merges; warns if uncommitted changes are present.

#### D2 — Remote management
Add to `GitRepositoryService`:
- `AddRemoteAsync(repoPath, name, url, onOutput, ct)` — `git remote add <name> <url>`.
- `RemoveRemoteAsync(repoPath, name, onOutput, ct)` — `git remote remove <name>`.
- `RenameRemoteAsync(repoPath, oldName, newName, onOutput, ct)` — `git remote rename <old> <new>`.

Add a `ManageRemotesWindow` (XAML + code-behind) and `ManageRemotesViewModel`:
- Lists current remotes (name + fetch URL).
- Buttons: Add, Remove (with confirm), Rename.
- Opened via a "Manage Remotes" button in `GitHistoryWindow` header.

#### D3 — Tags
Add to `GitRepositoryService`:
- `GetTagsAsync(repoPath, ct)` — `git tag --list --sort=-version:refname` returning `List<GitTagInfo>` (name, sha, message when annotated).
- `CreateTagAsync(repoPath, tagName, message, commitSha, onOutput, ct)` — lightweight (`git tag <name>`) or annotated (`git tag -a <name> -m <msg>`) based on whether message is provided.
- `DeleteTagAsync(repoPath, tagName, onOutput, ct)` — `git tag -d <name>`.
- `PushTagAsync(repoPath, remote, tagName, onOutput, ct)` — `git push <remote> <tagName>`.

Add a `GitTagInfo` model record: `{ Name, Sha, IsAnnotated, Message }`.

Add to `GitHistoryWindow`: a **Tags** tab or panel (below branches or alongside them), with Create, Delete, Push Tag buttons.

Add to `GitHistoryViewModel`:
- `Tags` observable collection.
- `SelectedTag` property.
- `CreateTagCommand`, `DeleteTagCommand`, `PushTagCommand` with appropriate confirmation dialogs.
- Tags are refreshed alongside branches in `RefreshAsync`.

#### D4 — History rewriting: Amend, Cherry-pick, Rebase
Add to `GitRepositoryService`:
- `AmendLastCommitAsync(repoPath, newMessage, onOutput, ct)` — `git commit --amend -m <msg>`.
- `CherryPickAsync(repoPath, commitSha, onOutput, ct)` — `git cherry-pick <sha>`.
- `RebaseAsync(repoPath, onto, onOutput, ct)` — `git rebase <onto>` (interactive rebase is deferred; this covers non-interactive rebase onto a branch/sha).

Add to `GitHistoryViewModel`:
- `AmendCommand` (enabled when selected commit is HEAD; prompts for new message via a simple input dialog).
- `CherryPickCommand` (enabled when a non-HEAD commit is selected; confirms "apply commit X to current branch?").
- `RebaseCommand` (enabled when a branch is selected in the left panel; confirms "rebase current branch onto <selected>?").

> **Safety note**: All three are destructive/history-rewriting operations. Each must:
> 1. Require `HasUncommittedChangesAsync` to return false before proceeding.
> 2. Show a prominent warning that mentions pushed history cannot be safely rewritten without `--force-push`.
> 3. Abort (not continue) on nonzero exit code.

#### D5 — UI integration for D1–D4 in GitHistoryWindow
- **Header toolbar** gains: `⬇ FETCH`, `⬆ PUSH`, `⇅ PULL` buttons (D1) and a `⚙ REMOTES` button (D2).
- **Left branch panel footer** gains: existing CHECKOUT + DELETE + new `MERGE INTO HERE` and `REBASE ONTO` buttons.
- **Right commit panel toolbar** gains: `🍒 CHERRY-PICK` and `✏ AMEND` buttons (visible/enabled only when appropriate).
- **New Tags panel**: collapsible section below the Branches list, or a second tab, showing `Tags` list with Create/Delete/Push buttons.

#### Testing
- Add `GitRepositoryServiceTests` cases for each new service method using `TempGitRepo`:
  - `FetchAsync_WhenNoRemote_ReturnsNonzeroExitButDoesNotThrow`
  - `PushAsync_ToLocalBareRemote_Succeeds`
  - `GetTagsAsync_ReturnsCreatedTags`
  - `CreateTagAsync_LightweightAndAnnotated`
  - `DeleteTagAsync_RemovesTag`
  - `AmendLastCommitAsync_ChangesCommitMessage`
  - `CherryPickAsync_AppliesCommitToCurrentBranch`

#### Acceptance criteria
- All new service methods are covered by integration tests using `TempGitRepo`.
- Fetch/Push/Pull surface progress in the log panel; nonzero exit code surfaces as a warning, not a silent failure.
- Remote management window prevents adding a remote with a blank name or URL.
- Tag creation is blocked when no commits exist.
- Amend, cherry-pick, and rebase all show the destructive-action warning and are blocked when uncommitted changes are present.
- New UI buttons follow the existing style conventions (`PrimaryButton`, `DangerButton`, `NeutralButton`).
- `docs/Git History.md` is updated to document all new operations.
