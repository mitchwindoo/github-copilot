<overview>
The user is iteratively improving the visual design of AB Logix Git Manager — a WPF desktop application for managing Rockwell Automation Studio 5000 ACD files under Git version control, built by Advanced Control Systems (ACS). The work focused on aligning the app's color palette with its brand icons, switching from a dark to a light theme, fixing WCAG AA accessibility failures, theming previously unstyled dialogs, and polishing icon presentation. The user's most recent request (in progress at compaction) was to remove the bordered boxes around icons for a more seamless appearance.
</overview>

<history>
1. **User asked to match app colors to icons and verify accessibility**
   - Invoked `frontend-design` skill
   - Examined all XAML files, brand assets (`Square-Logo.png`, `Banner-Logo.png`, `Icon_Square_500x500.png`, SVGs), and the existing dark palette in `App.xaml`
   - Identified two WCAG AA failures: white on `SignalGreen #37B56F` (2.4:1) and white on `SignalRed #E15E5E` (3.2:1)
   - Identified `SignalRedColor` as a desaturated pink-red that clashed with the RA/Git icon reds
   - Found `AcsIcon`/`AcsLargeIcon` BitmapImage keys pointing to `Small-Icon.png` / `Large-Icon.png` — files that did not exist (build was already broken)
   - Found `GitRepositoryActionWindow` and `CloneRepositoryWindow` were completely unstyled (raw WPF defaults)
   - Fixed all issues: corrected asset paths to `Square-Logo.png` / `Banner-Logo.png`, updated `.csproj` Resource items, changed `SignalRedColor` to `#CC2A18` (4.8:1, RA red family), gave `PrimaryButton` dark `GraphiteBrush` foreground on bright green, themed both dialogs with full ACS design language
   - Build succeeded; committed as `66a515e`

2. **User updated Banner-Logo.png aspect ratio and asked it to be used as the app banner, Square-Logo.png as the icon**
   - Viewed the updated banner (wide landscape, white/off-white background) and square icon (square crop, white bg)
   - Identified that all icon containers used `Background=GraphiteBrush` (near-black), which caused white-bg PNGs to show as opaque white rectangles on dark chrome
   - Switched all four container `Border` backgrounds from `GraphiteBrush` to `White`
   - Increased banner height 44→48px in the main header
   - Build succeeded; committed as `9b765b2`

3. **User asked to change the app to a light color theme**
   - Performed a full palette redesign: surfaces flipped to `#F0F4F8` / `#FFFFFF` / `#E4E8EF`; text colors darkened for WCAG AA on white; signal colors darkened (`SignalGreen #37B56F→#15803D`, `SignalAmber #E0A24B→#B45309`); `SignalRed` unchanged at `#CC2A18`
   - Added `TerminalColor`/`TerminalBrush` (`#0F1420`) — log/terminal panels intentionally stay dark as a "readout" contrast element
   - Selection bar `SlateColor` changed from dark navy to brand crimson `#7E1D29`
   - Removed the dark-fg `GraphiteBrush` override on `PrimaryButton` (no longer needed since darker green passes with white text)
   - Updated all hardcoded hex values in `MainWindow.xaml` and `SettingsWindow.xaml` (hover states, warning cards, caution strips, empty state dot, ProgressBar bg, terminal panel header border)
   - `NeutralButton` and `GhostButton` given light backgrounds with `InkBrush` foreground
   - `InstrumentTextBox` changed to white background with light-green focus tint `#F2FAF6`
   - All text brushes verified WCAG AA: `InkBrush #1E293B` (13.2:1), `MutedBrush #475569` (7.5:1), `FaintBrush #586070` (6.3:1)
   - Build succeeded; committed as `a278258`

4. **User asked to remove borders around icons for seamless appearance** (in progress at compaction)
   - User attached a screenshot showing the bordered white boxes around the banner logo in the header and the square icon in the About section
   - Identified all four icon container `Border` elements across `MainWindow.xaml`, `SettingsWindow.xaml`, and `AddEditRepoWindow.xaml`
   - Was in the process of removing the `Border` wrappers and replacing with bare `Image` elements
</history>

<work_done>
Files updated:
- `src/ABLogixGitManager/App.xaml`: Asset paths fixed; full light palette applied; signal colors darkened for AA; `TerminalBrush` added; button styles updated; text brushes updated; LED glow opacities reduced; card shadow reduced; Data TextBlock foreground updated; `InstrumentTextBox` lightened
- `src/ABLogixGitManager/ABLogixGitManager.csproj`: Resource items corrected from non-existent files to `Square-Logo.png` and `Banner-Logo.png`
- `src/ABLogixGitManager/MainWindow.xaml`: All hardcoded dark hex values replaced with light-theme equivalents; warning card colors updated; terminal panel bg switched to `TerminalBrush`; icon containers switched to white bg; banner height increased
- `src/ABLogixGitManager/Views/SettingsWindow.xaml`: Themed with ACS styles; icon container whitened; subtitle text brush corrected; terminal readout uses `TerminalBrush`
- `src/ABLogixGitManager/Views/AddEditRepoWindow.xaml`: Themed with ACS styles; icon container whitened
- `src/ABLogixGitManager/Views/GitRepositoryActionWindow.xaml`: Fully restyled from raw WPF defaults — `SteelBrush` bg, `LegendFont` title, styled buttons, footer/body layout
- `src/ABLogixGitManager/Views/CloneRepositoryWindow.xaml`: Fully restyled — header, themed inputs (`InstrumentTextBox`), styled buttons, `SpacedStackPanel` footer

Work completed:
- [x] Fixed broken build (missing icon asset references)
- [x] Aligned `SignalRedColor` with RA/Git icon red family
- [x] Fixed WCAG AA failures on PrimaryButton and DangerButton
- [x] Themed `GitRepositoryActionWindow` and `CloneRepositoryWindow`
- [x] Fixed icon container backgrounds for white-bg PNGs
- [x] Full light color theme with verified WCAG AA contrast ratios
- [ ] Remove borders around icon containers (in progress — identified all 4 locations, not yet applied)
</work_done>

<technical_details>
- **WCAG AA contrast requirements**: 4.5:1 for normal text, 3:1 for large text/UI components. `SignalGreen #37B56F` (2.4:1 with white) required darkening to `#15803D` (5.5:1). `SignalRed #E15E5E` (3.2:1) replaced with `#CC2A18` (4.8:1) which also matches the RA icon red family.
- **WPF `Run.Text` binding quirk**: `Run.Text` has `BindsTwoWayByDefault=true` in its DP metadata; omitting `Mode=OneWay` when binding to a get-only property causes `XamlParseException` at startup. `SettingsWindow.xaml` already handles this correctly.
- **TerminalBrush pattern**: Log/terminal panels are intentionally kept dark (`#0F1420`) within the light interface as a "readout" contrast element — mimicking the feel of a physical terminal/HMI. These panels use `PhosphorBrush` (`#DDEBD8`) for their text. `DarkSmallButton` (`#2A3444`) is used inside these panels and is hardcoded so it works on both the light footer and the dark terminal panel.
- **PNG background mismatch**: `Square-Logo.png` and `Banner-Logo.png` both have white/off-white backgrounds (not transparent). Placing them in dark `GraphiteBrush` containers makes the white areas appear as opaque rectangles. Containers must use `Background="White"` or be removed entirely.
- **`SpacedStackPanel`**: Custom WPF control in the project at `clr-namespace:ABLogixGitManager.Controls`. Replaces `StackPanel` when uniform spacing between children is needed. Used in footer button rows.
- **`SharpVectors.Wpf`**: NuGet package used for SVG rendering (`svgc:` xmlns). The ACS wordmark SVG (`Logo_Padded_Solid_8B0000.svg`) is loaded via `{svgc:SvgImage}` markup extension in the About section.
- **Build output path**: `src\ABLogixGitManager\bin\Debug\net10.0-windows\ABLogixGitManager.exe` (no custom output path in csproj).
- **`OnDarkMuteBrush`/`OnDarkBrush`**: These remain valid for text appearing ON dark surfaces (terminal panel headers, `SuccessButton`/`DangerButton` foregrounds). They should NOT be used for text on light surfaces — those should use `MutedBrush`/`InkBrush`. Several `OnDarkMuteBrush` usages in window subtitles were corrected to `MutedBrush`.
- **`SuccessButton`** uses `PanelBrush` (`#7E1D29`, deep crimson) — this is the "Pull & Restore" button, visually differentiated from `PrimaryButton` (green). White text on `#7E1D29` achieves ~8.5:1 contrast, WCAG AAA.
</technical_details>

<important_files>
- `src/ABLogixGitManager/App.xaml`
  - Central design system: all palette tokens, brushes, typography, and shared control styles
  - Fully updated with light theme palette, corrected asset paths, darkened signal colors, `TerminalBrush` addition
  - Key sections: lines 15–17 (asset keys), 19–36 (palette colors), 38–49 (brushes), 51–56 (semantic brushes), 57–62 (text brushes), 100–113 (Led style), 136–149 (Card style), 152–265 (button/input styles)

- `src/ABLogixGitManager/MainWindow.xaml`
  - Primary application window; largest XAML file (~605 lines)
  - Contains all major UI: header with banner logo, controller rail (left), instrument panels (right), terminal readout panel, status footer
  - All hardcoded dark hex values updated to light equivalents; icon container border still present (pending removal)
  - Key sections: lines 35–42 (banner logo container — needs border removal), 408–415 (About section icon — needs border removal), 363–395 (l5xgit warning card), 576–587 (overwrite caution strip)

- `src/ABLogixGitManager/ABLogixGitManager.csproj`
  - Build file; had broken Resource item references to non-existent files
  - Fixed: now references `Assets\Square-Logo.png` and `Assets\Banner-Logo.png`

- `src/ABLogixGitManager/Views/SettingsWindow.xaml`
  - Dependencies/settings window; icon container border still present (pending removal at line 32–38)

- `src/ABLogixGitManager/Views/AddEditRepoWindow.xaml`
  - Add/Edit controller mapping dialog; icon container border still present (pending removal at lines 24–30)

- `src/ABLogixGitManager/Views/GitRepositoryActionWindow.xaml`
  - Dialog shown when git repo is not initialized; fully restyled from raw WPF defaults

- `src/ABLogixGitManager/Views/CloneRepositoryWindow.xaml`
  - Clone repository dialog; fully restyled from raw WPF defaults

- `src/ABLogixGitManager/Assets/Square-Logo.png`
  - Square icon (RA + Git logos composition, white bg); used as `AcsIcon` — window icon in taskbar/chrome and About section thumbnail

- `src/ABLogixGitManager/Assets/Banner-Logo.png`
  - Wide landscape banner (RA + arrow + file+Git logos, white bg); used as `AcsLargeIcon` — main header banner
</important_files>

<next_steps>
Remaining work:
- Remove the `Border` wrapper containers around all icon `Image` elements (4 locations), replacing them with bare `Image` elements and preserving margin/sizing

Immediate next steps — edits needed at these exact locations:

**MainWindow.xaml — Header banner (lines ~35–42)**
Replace:
```xml
<Border Grid.Column="0" Padding="6,4" CornerRadius="6"
        Background="White"
        BorderBrush="{StaticResource LineBrush}" BorderThickness="1">
    <Image Source="{StaticResource AcsLargeIcon}"
           Height="48" Stretch="Uniform"
           RenderOptions.BitmapScalingMode="HighQuality"/>
</Border>
```
With:
```xml
<Image Grid.Column="0" Source="{StaticResource AcsLargeIcon}"
       Height="48" Stretch="Uniform"
       RenderOptions.BitmapScalingMode="HighQuality"
       VerticalAlignment="Center"/>
```

**MainWindow.xaml — About section icon (lines ~408–415)**
Replace `Border` + `Image` with bare `Image Grid.Column="0"` at 52px height.

**SettingsWindow.xaml — Header icon (lines ~32–38)**
Replace `Border` + `Image` with bare `Image Grid.Column="0"` at 34px height with right margin.

**AddEditRepoWindow.xaml — Header icon (lines ~24–30)**
Replace `Border` + `Image` with bare `Image Grid.Column="0"` at 30px height with right margin `Margin="0,0,14,0"`.

After all four edits: run `dotnet build` to verify, then commit.
</next_steps>