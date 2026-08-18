# ACS branding update plan

## Checklist

- [x] Add ACS logo assets to the WPF project and expose them as resources.
- [x] Retheme shared app resources to the ACS palette and typography guidance.
- [x] Update the main shell, settings window, and controller dialog to use the ACS brand mark and window titles.
- [x] Refresh any project metadata that still shows the old company branding.
- [x] Build and inspect the app for XAML/resource errors.

## Review

The ACS wordmark and icon are now packaged with the app, the shell windows use the ACS palette and titles, and a clean alternate-output build succeeded.
Residual risk: the exact Bauhaus/Century Gothic face names may fall back to installed substitutes on machines without those fonts.

## Follow-up

Fixed a runtime XAML issue where a `Color` resource had been assigned to a `Background`/`CaretBrush`/`BorderBrush` slot that expects a `Brush`. The shared styles now use the corresponding brush resources.

## Validation

- Project diagnostics: clean
- XAML resource scan: no remaining `Color`-to-brush bindings in the edited app surfaces

## Branding relocation update

- Moved ACS brand presentation into a dedicated **About** card in the main window content.
- Removed prominent ACS branding from the main/settings/dialog headers.
- Repointed logo/icon resources to assets under `src\ABLogixGitManager\Assets` and removed SVG/SharpVectors usage.
- Rebuilt and verified no XAML/compiler diagnostics.
