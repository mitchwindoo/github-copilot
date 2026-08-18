<overview>
The user is building a Windows WPF application ("AB Logix Git Manager") for Advanced Control Systems (ACS) that manages Allen-Bradley Logix ACD files under Git version control. The main goals were: (1) incorporate ACS brand guidelines into the application, and (2) fix several runtime XAML errors that appeared as the branding was applied. The approach evolved from adding prominent header branding across all windows → moving branding to a dedicated About section → using existing Assets folder images rather than external SVG files.
</overview>

<history>
1. User requested ACS brand guidelines be incorporated using logos from OneDrive
   - Read ACS org guidelines: primary color is Dark Red `#8B0000`, fonts are ITC Bauhaus Pro Bold ("ACS") and Century Gothic Paneuropean Bold (subtext)
   - Discovered ACS logo assets at `C:\Users\MitchellLandreth\OneDrive - Advanced Control Systems\SharePoint Links\Branding & Media\Media library\Logos\ACS`
   - Inspected available PNG assets: `Logo_Padded_982x350.png`, `Icon_Square_500x500.png` (red), `Icon_Square_White_500x500.png`, `Favicon_32x32.png`
   - Copied two PNG assets into `src\ABLogixGitManager\Assets\Branding\` folder
   - Rewrote `App.xaml` to adopt ACS palette (dark red `#8B0000` as primary signal color, ivory paper background `#F7F2EA`)
   - Added `BitmapImage` resources `AcsWordmark` and `AcsIcon` to `App.xaml`
   - Added ACS header to `MainWindow.xaml`, `SettingsWindow.xaml`, `AddEditRepoWindow.xaml` with wordmark logo, "Advanced Control Systems" subtitle
   - Updated `ABLogixGitManager.csproj`: Company="Advanced Control Systems", added Resource items
   - Build succeeded (alternate output `bin\BrandingCheck2\`)

2. User reported runtime error: `'#FF450000' is not a valid value for property 'Background'`
   - Root cause: `Color` resources (e.g. `PanelEdgeColor`, `SignalGreenColor`) were assigned directly to `Background`/`BorderBrush`/`CaretBrush` properties which require `Brush` types, not `Color` types
   - Fixed all 4 violations in `App.xaml`:
     - `PrimaryButton.Background` → `SignalGreenBrush` (was `SignalGreenColor`)
     - `SuccessButton.Background` → `PanelBrush` (was `PanelColor`)
     - `DarkSmallButton.Background` → `PanelEdgeBrush` (was `PanelEdgeColor`)
     - `InstrumentTextBox.CaretBrush` → `SignalGreenBrush` (was `SignalGreenColor`)
     - `InstrumentTextBox` focused trigger `BorderBrush` → `SignalGreenBrush` (was `SignalGreenColor`)
   - Build succeeded (alternate output `bin\BrandingCheck3\`)

3. User requested a full scan for any other XAML runtime issues
   - Ran diagnostics: no project-level errors
   - Searched for remaining `Color`-to-brush property assignments: none found
   - Confirmed ACS asset bindings all resolve correctly

4. User requested moving ACS branding to an About section, using logos from `src\ABLogixGitManager\Assets` (not OneDrive)
   - Found existing assets: `Large-Icon.png`, `Small-Icon.png`, `Small-Icon_TransparentBG.png` (all 1254×1254px)
   - Also found `Assets\Branding\` had been populated with OneDrive copies
   - Discovered the app had already evolved to use SharpVectors SVG (`svgc:SvgImage`) for the wordmark in some windows - this was from a prior update not visible in conversation
   - Updated `App.xaml` brand resources:
     - `AcsWordmark` → `pack://application:,,,/Assets/Large-Icon.png`
     - `AcsIcon` → `pack://application:,,,/Assets/Small-Icon_TransparentBG.png`
   - Updated `ABLogixGitManager.csproj`: replaced Branding folder resources with `Assets\Large-Icon.png` and `Assets\Small-Icon_TransparentBG.png`; removed `SharpVectors.Wpf` package reference
   - Stripped ACS header branding from `MainWindow.xaml`, `SettingsWindow.xaml`, `AddEditRepoWindow.xaml`
   - Changed window titles: `MainWindow` → "AB Logix Git Manager", `SettingsWindow` → "Dependencies — AB Logix Git Manager", `AddEditRepoWindow` → "Add / Edit Controller"
   - Added dedicated **About** card in `MainWindow.xaml` (in the instrument stack, before the empty-state panel) showing `AcsIcon` + `AcsWordmark` side by side
   - Build succeeded (alternate output `bin\BrandingCheck4\`)

5. User reported new runtime error (current issue):
   - Error: `'Provide value on 'System.Windows.StaticResourceExtension' threw an exception.' Line number '401' and line position '42'`
   - This is a StaticResource lookup failure at line 401 col 42 of `MainWindow.xaml`
   - Looking at the screenshot: SharpVectors DLLs are still in the output folder (from a prior build), and the app is running from `BrandingCheck4`
   - The About card at line ~387-410 uses `{StaticResource AcsIcon}` and `{StaticResource AcsWordmark}` - one of these is failing
</history>

<work_done>
Files modified:
- `src/ABLogixGitManager/App.xaml`: Full ACS palette retheme; brush resources use `Color`→`SolidColorBrush` correctly; brand resources `AcsWordmark` and `AcsIcon` pointing to `Assets/Large-Icon.png` and `Assets/Small-Icon_TransparentBG.png`
- `src/ABLogixGitManager/MainWindow.xaml`: Removed `xmlns:svgc` namespace, removed ACS logo from header, simplified header to title+subtitle only, added About card (lines ~386-410) with `AcsIcon`+`AcsWordmark`, window title changed to "AB Logix Git Manager"
- `src/ABLogixGitManager/Views/SettingsWindow.xaml`: Removed ACS header/icon, simplified header to just title text, removed `xmlns:svgc` namespace, title = "Dependencies — AB Logix Git Manager"
- `src/ABLogixGitManager/Views/AddEditRepoWindow.xaml`: Removed ACS header/icon, simplified header to just TextBlock title, removed `xmlns:svgc` namespace, title = "Add / Edit Controller"  
- `src/ABLogixGitManager/ABLogixGitManager.csproj`: Company="Advanced Control Systems", removed `SharpVectors.Wpf` package ref, Resource items point to `Assets\Large-Icon.png` and `Assets\Small-Icon_TransparentBG.png`

Current state:
- [x] ACS palette applied throughout
- [x] Color-to-brush XAML errors fixed
- [x] Branding moved to About section
- [x] SharpVectors/SVG references removed
- [ ] **Runtime error at MainWindow.xaml line 401** — StaticResource lookup failing for About card
</work_done>

<technical_details>
- **WPF Color vs Brush**: WPF `Background`, `BorderBrush`, `Foreground`, `Fill`, `CaretBrush` all require `Brush` types. `Color` resources (`<Color x:Key="...">`) cannot be assigned directly — must use a `SolidColorBrush` wrapper. `DropShadowEffect.Color` is the exception — it accepts `Color` directly.
- **Run.Text binding**: `Run.Text` has `BindsTwoWayByDefault=true` in WPF metadata. When binding to a get-only property, always add `Mode=OneWay` or a `XamlParseException` is thrown at startup.
- **BitmapImage as Window.Icon**: WPF `Window.Icon` expects an `ImageSource` (e.g. `BitmapImage`). Using `{StaticResource AcsIcon}` where `AcsIcon` is a `BitmapImage` is valid.
- **App.xaml resource scope**: `Application.Resources` are available globally. `BitmapImage` resources defined there can be referenced in all windows and controls.
- **SharpVectors WPF**: `SharpVectors.Wpf` package provides `svgc:SvgImage` markup extension for rendering SVG files. It was added to support an SVG wordmark (`AcsWordmark.svg`) but the SVG file doesn't exist in the Assets folder, causing crashes. This package was removed.
- **About card StaticResource failure**: The current error at line 401 `StaticResource AcsIcon` or `AcsWordmark` is failing. Likely cause: the resource URIs in `App.xaml` point to `Assets/Large-Icon.png` and `Assets/Small-Icon_TransparentBG.png` but these files may not be properly registered as `<Resource>` items in the `.csproj`, or the URI is incorrect. The `pack://` URI format requires the resource to be included as `<Resource>` in the project file.
- **Build output path workaround**: `dotnet build -p:OutputPath=bin\BrandingCheck4\` was used to avoid file-lock issues with the running app executable in the default debug output folder.
- **Asset file contents**: `Large-Icon.png` is an opaque white-background icon (corner=#FFFFFFFF). `Small-Icon_TransparentBG.png` appears fully transparent at sampled pixels (likely uses transparency for the background, content is dark/colored elsewhere). Both are 1254×1254px.
- **Palette change history**: Initial branding attempt used ivory/paper theme (`#F7F2EA` background). The app subsequently evolved to a dark control-room theme (GraphiteColor `#0B1016`, dark surfaces). There may be a discrepancy between the palette described in early conversation and what's actually in `App.xaml` now.
</technical_details>

<important_files>
- `src/ABLogixGitManager/App.xaml`
  - Defines all application-wide style resources, palette, brushes, typography, button/card styles
  - Contains `AcsWordmark` and `AcsIcon` BitmapImage resources
  - All Color resources have matching SolidColorBrush wrappers (brush/color separation is critical)
  - Current issue: verify `AcsWordmark`/`AcsIcon` URIs resolve correctly

- `src/ABLogixGitManager/ABLogixGitManager.csproj`
  - Lists `<Resource>` items for included assets — must match the `pack://` URIs in `App.xaml`
  - Currently includes `Assets\Large-Icon.png` and `Assets\Small-Icon_TransparentBG.png`
  - `SharpVectors.Wpf` package was removed

- `src/ABLogixGitManager/MainWindow.xaml`
  - Main application window (38.5 KB, 574+ lines)
  - About card lives around lines 386-410
  - Header is now a clean 2-column grid (title+subtitle / dependencies button)
  - The StaticResource error at line 401 is here

- `src/ABLogixGitManager/Views/SettingsWindow.xaml`
  - Dependencies/setup window
  - Header simplified to 2-column layout (title+scan status / rescan button)

- `src/ABLogixGitManager/Views/AddEditRepoWindow.xaml`
  - Controller mapping dialog
  - Header simplified to just a TextBlock

- `src/ABLogixGitManager/Assets/`
  - `Large-Icon.png` (1254×1254, opaque white background, used as AcsWordmark)
  - `Small-Icon.png` (1254×1254, near-white background)
  - `Small-Icon_TransparentBG.png` (1254×1254, transparent background, used as AcsIcon)
  - `Assets/Branding/` subfolder still exists with OneDrive-copied PNGs (not referenced)
</important_files>

<next_steps>
Current blocker:
- **Runtime error**: `StaticResource AcsIcon` (or `AcsWordmark`) throws at `MainWindow.xaml` line 401 col 42

Root cause to investigate:
- The `Small-Icon_TransparentBG.png` sampled as fully transparent at center — if the image content is all transparent, it may cause a WPF image resource failure, OR the resource URI is simply wrong
- Verify `App.xaml` resource URIs exactly match csproj `<Resource>` entries (case-sensitive on some builds)
- Check whether `Assets\Branding\` files are still inadvertently included/excluded

Immediate fix approach:
1. Check the exact error by reading the log at `C:\Users\ACS\AppData\Roaming\ABLogixGitManager\logs\app-2026-07-24.log`
2. Check `App.xaml` lines 14-17 (BitmapImage declarations) and `ABLogixGitManager.csproj` Resource items match
3. Consider using `Small-Icon.png` instead of `Small-Icon_TransparentBG.png` as the icon (has visible content)
4. If URI path is wrong, fix pack URI format or switch to relative path approach
5. Rebuild and verify the About card renders correctly
</next_steps>