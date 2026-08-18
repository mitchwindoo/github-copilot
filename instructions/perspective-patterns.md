# Ignition Perspective View Patterns

Full skill at `.github/skills/perspective-views/SKILL.md`. Key reminders:

- **NEVER `props.visible`** — use `position.display` (boolean) in flex containers
- **Iframe type is `ia.display.iframe`** — NOT `ia.display.inline-frame`
- **Integer dict keys become strings** when stored in `view.custom` (Perspective PropertyTree serialization)
- **In root message handlers, `self` is the root container, not the view** — use `self.view.custom.*`, not `self.custom.*` (root has no custom props by default)
- **Script indentation in view.json**: Ignition Designer stores ALL inline script lines with a base indent of ONE TAB (`\t`). Code inside blocks gets `\t\t`, nested blocks get `\t\t\t`, etc. This is the format Ignition reads/writes. NEVER strip the leading tab — it is required. When generating scripts programmatically, prefix every line with `\t` and add additional tabs for block nesting.
- **Toast confirm callbacks**: `toastConfirmAction` callbacks must use a scope matching the target handler. If target handler is `pageScope: true`, include `messageHandler.scope = 'page'`; otherwise Confirm can do nothing silently with no gateway log.
- Always validate view.json against the 10-point checklist in the skill
- **Flex repeater paths must match actual view resource paths**: if `props.instances` has rows but nothing renders, verify `props.path` against the real `views/.../view.json` location before chasing the query.
- **Table `event.value` only contains fields listed in `props.columns`** (both 8.1 and 8.3). If a column isn't in the `props.columns` array, it won't be in `event.value` on `onRowClick` even if the query returns it. Fix: add the field as a hidden column (`"visible": false`). This applies to `ia.display.table` with explicit column definitions.
