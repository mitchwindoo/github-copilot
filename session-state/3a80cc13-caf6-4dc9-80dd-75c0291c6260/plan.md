# Commit feedback follow-up

## Checklist
- [x] Reproduce and understand why the non-git commit flow is not visible enough.
- [x] Update the commit flow so the repository-choice dialog is forced to the foreground.
- [x] Add a visible success/failure status in the main window so hidden logs are not required.
- [x] Route the CLI service's exact missing-repository result back into the setup dialog and retry.
- [x] Rebuild the app and verify the new behavior.

## Review
- Validation performed:
  - Release build passed with 0 warnings and 0 errors.
  - Focused service harness confirmed nested folders are not accepted as repository roots and return `GitRepositoryRequired`.
  - WPF UI automation confirmed Commit shows Initialize Git, Clone Repository, and Cancel.
- Remaining risk:
  - Studio 5000/l5xgit execution remains dependent on the external vendor tooling and was not part of this focused prompt test.

# Dark mode / SVG branding

## Checklist
- [x] Add a vector ACS wordmark and wire it into the window chrome and about panel.
- [x] Replace the light palette with a dark ACS control-room theme.
- [x] Build the updated app and confirm the SVG logo renders correctly at runtime.

# Company logo SVG

## Checklist
- [x] Swap the main-window logo over to the supplied `Logo_Padded_Solid_8B0000.svg`.
- [x] Rebuild and verify the updated logo renders in the app without breaking the dark theme.

## Review
- Validation performed:
  - `dotnet build .\\src\\ABLogixGitManager\\ABLogixGitManager.csproj -c Release` in a clean copy — passed with 0 warnings and 0 errors.
  - UI automation against the refreshed build confirmed the main window launches and the Add / Edit Controller dialog still opens with image-backed branding controls.
- Remaining risk:
  - The settings dialog did not surface during automated inspection, so that specific runtime path still needs manual confirmation if you want it checked explicitly.
