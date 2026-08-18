# GUI rebuild — AB Logix Git Manager (frontend-design skill applied)

## Task
1. Install the anthropics `frontend-design` skill. ✅ vendored to
   `.github/skills/frontend-design/SKILL.md` (+ NOTICE.md provenance).
2. Rebuild the WPF GUI using the skill's design method.

## Subject grounding (per skill)
- Product: desktop tool for **Allen-Bradley Logix controls engineers** to put PLC
  ACD projects under Git via Rockwell's `l5xgit`.
- Audience: automation / OT / controls engineers who live in front of HMIs and
  control panels.
- Page's single job: pick a controller project, then **Commit** it to Git or
  **Pull & Restore** it from Git — safely (restore overwrites the ACD).

## Aesthetic direction — "Engineering control panel / HMI faceplate"
Not one of the three AI defaults (cream+serif, black+acid, broadsheet). Grounded
in the subject's real world: brushed-graphite panel faces, engraved DIN legends,
industrial signal-color LEDs, and a phosphor terminal readout.

### Signature element
Status **indicator LEDs** on the faceplate and on each instrument card
(ready = green, busy = amber pulse, needs-config = amber, danger = red), plus the
output log rendered as a genuine amber/green phosphor terminal. The two primary
operations read as physical panel actions.

### Tokens
- Palette: Graphite `#1B1E24`, Panel `#252A32`, Steel `#EDF0F3`, Card `#FFFFFF`,
  Line `#D9DEE6`; signal Green `#1FA463`, Amber `#E08A00`, Red `#C6303A`,
  phosphor `#5BE38A`; selection slate `#3C6E9A`.
- Type (Windows built-ins, subject-true): **Bahnschrift** (DIN — the machinery
  standard) for engraved legends/titles with tracking; **Segoe UI** for body;
  **Consolas** for paths/versions/log (instrument readout). All with fallbacks.
- Structure device: engraved eyebrow legend + LED per card (encodes real state,
  NOT decorative 01/02/03 numbering — commit & restore are parallel, not a
  sequence).
- Motion (restrained): single amber LED pulse while an operation runs; quiet
  button hover. Nothing else.

## Constraints preserved
- All existing bindings, `x:Name`s, event handlers, converters, commands.
- Resource keys reused (PrimaryButton/SuccessButton/DangerButton/NeutralButton/
  Card/SectionHeader/*Brush) and extended.
- WPF gotchas: `Run.Text` OneWay; no `StackPanel.Spacing` (use SpacedStackPanel);
  no `TextBox.PlaceholderText` (Grid watermark overlay).

## Files
- `App.xaml` — tokens/styles/templates.
- `MainWindow.xaml` — faceplate + selector rail + instrument cards + terminal.
- `Views/SettingsWindow.xaml`, `Views/AddEditRepoWindow.xaml` — matched skin.

## Verification
- `dotnet build` clean (0 warn/0 err). Launch smoke check if environment allows.

## Review — COMPLETE
- Skill installed: `.github/skills/frontend-design/SKILL.md` (8260 B, byte-identical
  to upstream) + `NOTICE.md` provenance.
- Rebuilt `App.xaml`, `MainWindow.xaml`, `Views/SettingsWindow.xaml`,
  `Views/AddEditRepoWindow.xaml` in the "control-panel / HMI faceplate" direction.
- Verification:
  - `dotnet build` clean (0 warn / 0 err) — final confirmed.
  - Fixed a runtime bug found by launching: `BorderBrush` bound to `Color`
    resources (`PanelEdgeColor`, `SignalAmberColor`); added `PanelEdgeBrush`,
    `SignalGreen/Amber/RedBrush` and repointed refs.
  - Live UI Automation launch: MainWindow captured (clean hero screenshot,
    `files/main_selected.png`); Settings + Add/Edit windows confirmed to load and
    expose their templated controls (no XamlParseException).
- Residual risk / not validated here:
  - Dialog screenshots could not be captured (host screen locked mid-run — env
    issue, not the app). Loads verified via automation instead.
  - Real dependency-scan / l5xgit execution, Studio 5000/SDK flows unchanged and
    not exercised.
- Untouched pre-existing uncommitted changes in the tree (README.md,
  DependencyCheckerService.cs, MainViewModel.cs, SettingsViewModel.cs,
  SettingsWindow.xaml.cs, DependencyInstallerService.cs, tasks/todo.md) — left as-is.
- No commit made (not requested).
