# Rockwell CI/CD packaging review

## Problem

Review Rockwell Automation's VCS examples and decide what, if anything, can be packaged with AB Logix Git Manager without crossing licensing or support boundaries.

## Approach

- Inventory the Rockwell examples that are already relevant to this app.
- Split them into:
  - safe to package with the app,
  - useful as repo-only CI/test assets,
  - not packageable because they are vendor software or require separate licensing.
- Keep the recommendation aligned with the current app surface:
  - [DependencyInstallerService](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/Services/DependencyInstallerService.cs)
  - [SettingsViewModel](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/src/ABLogixGitManager/ViewModels/SettingsViewModel.cs)
  - [README.md](C:/Users/MitchellLandreth/Git-Local/AB-Logix-Git/README.md)

## Planned work items

- Inventory the upstream Rockwell VCS repo for packaging candidates.
- Confirm which helpers are redistributable with the app versus repo-only.
- Recommend a minimal package set for Studio 5000 integration and release validation.

## Notes

- Current evidence points to the Studio 5000 custom tools asset as the best package candidate.
- The app already has a setup path for building Rockwell VCS tools and installing `CustomToolsMenu.xml`.
- Studio 5000, the Logix Designer SDK, and `l5xgit` binaries themselves should stay gated behind licensing/provenance checks unless explicitly approved for redistribution.

## Recommendation preview

- Package the `CustomToolsMenu.xml` integration asset and the app's elevated install helper.
- Keep Pester/E2E scripts as CI/release-validation assets, not as user-facing app payload.
- Do not bundle vendor-only Studio 5000 or SDK components inside the app release.
