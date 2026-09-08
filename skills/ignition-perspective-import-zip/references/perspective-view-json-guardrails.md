# Perspective View JSON Guardrails

## Contents

- Scope
- Structure
- Bindings
- Scripts And Transforms
- Additional Binding And Script Rules
- Common Failure Patterns
- Smoke Test

## Scope

These rules target Ignition 8.1.x Perspective `view.json`, especially 8.1.48 style exports. Treat `view.json` as a private serialization format with no complete public schema.

## Structure

- Preserve existing top-level keys such as `custom`, `params`, `props`, `root`, `propConfig`, `events`, and `permissions`.
- The component tree starts at `root`; children are usually under `root.children`.
- Components commonly contain `type`, `meta`, `props`, `position`, `custom`, `propConfig`, `events`, and `children`.
- Do not rewrite the whole file for small changes. Patch the smallest relevant object.

## Bindings

- Dynamic values belong in `propConfig`, not directly in `props`.
- Do not place binding objects inside component property values such as `props.text`; Perspective may render the binding JSON as text instead of evaluating it.
- `propConfig` keys are property paths such as `props.text`, `props.options`, `custom.summary`, or `position.basis`.
- `propConfig` is scoped to the object that owns it. For a child component, put `propConfig` inside that component and use keys like `props.text`; do not put `root.children[...]` paths in top-level view `propConfig`.
- Binding objects keep `binding.type`, `binding.config`, and optional `binding.transforms`.
- Direct tag bindings use `binding.config.tagPath`, not `binding.config.path`.
- `{value}` exists inside transforms, not in arbitrary expression bindings. A plain expression binding that uses `{value}` can render blank/incomplete text instead of failing loudly.
- For indirect tag bindings in 8.1, keep reference values as simple strings. Object-shaped references can render plausible wrong values such as `0.0` instead of failing loudly. Example:

```json
"references": {
  "basePath": "{view.custom.diagnosticsBasePath}"
}
```

## Scripts And Transforms

- Perspective scripts run as Jython/Python 2.7 in Ignition 8.1.
- Do not use f-strings, type hints, async/await, match/case, walrus, or Python 3-only libraries.
- Script actions normally store code under `config.script`; script transforms normally store code under `code`.
- Script action objects should include an explicit `scope`, usually `"G"`; a missing/null scope can break Perspective project serialization even when route wiring validates.
- Preserve stored indentation exactly. Many exported scripts include leading tabs because Ignition wraps code inside generated functions.
- If editing script text, mentally validate it as a function body. Top-level `return` is normal in transform context but invalid in a bare Python file.
- Use Jython 2.7-compatible formatting such as `%` or `str.format`; f-strings can render `null` in Perspective script transforms instead of failing loudly.
- Compile/lint generated startup, event, and transform script bodies when tooling exists; malformed indentation can leave the page shell rendered while `view.custom` data never loads.


## Additional Binding And Script Rules

- Keep Jython scripts/transforms Python 2.7-compatible; use transform `code`, preserve Ignition's stored indentation, and avoid Python 3 syntax such as f-strings.
- Put view startup scripts under top-level `events.system.onStartup`; do not use `scripts.extensionFunctions` for view startup.
- Keep startup/event scripts as valid Jython function bodies; preserve indentation and compile/lint them before apply when tooling exists.
- Give every Perspective script action object an explicit `scope`, usually `"G"` for gateway execution; a missing/null scope can pass structural checks but break Perspective project serialization.
- For indirect tag bindings, use string references such as `"base": "{view.params.baseTagPath}"`; do not use object-shaped references.
- For indirect tag bindings, set `config.mode: "indirect"` and prefer a small `fallbackDelay`; references without indirect mode can resolve as bad/null while the page shell still renders.
- When an indirect tag path combines a fixed root with a route/page param segment, keep the fixed root literal in `tagPath` and reference only the dynamic segment, for example `"<root>/{device}/PV"` with `"device": "{view.params.deviceId}"`. Declare the route param as an input `view.params` entry and browser-test at least two concrete URLs.
- Relative property binding paths are scoped from the component that owns the `propConfig`; after wrapping/nesting components, adjust `../` depth or centralize selection in `view.custom`.
- Use `{value}` only inside binding transforms; plain expression bindings must reference explicit properties/tags.
- View startup scripts belong under top-level `events.system.onStartup` with `type`, `scope`, and `config.script`; `scripts.extensionFunctions` is not the view startup event shape.
- If only one segment of an indirect tag path is dynamic, keep the fixed root literal in `tagPath` and reference only the dynamic segment, such as `tagPath: "[provider]Area/Equipment/{device}/PV"` with `references.device: "{view.params.deviceId}"`. Do not move a static root into `references`; it can resolve to `None`.
- Relative property binding paths are evaluated from the component that owns the `propConfig`. If a bound label moves into a wrapper panel, update `../` depth or bind through `view.custom` instead.

## Common Failure Patterns

- Rebuilding a partial view and accidentally omitting `root.children`.
- Putting binding config under `props`.
- Putting child-component binding keys such as `root.children[0].props.text` in top-level view `propConfig`; this can prevent Gateway from deserializing the view.
- Serializing indirect tag references as objects when 8.1 expects strings.
- Using `{view.custom.path}/Something` directly in an indirect tag binding instead of a placeholder plus reference mapping.
- Using `system.perspective.navigate(page=..., params={...})` and expecting page params to change; page params come from mounted URL segments.
- Putting a fixed tag root in indirect binding `references` instead of leaving it literal in `tagPath`.
- Adding Python 3 syntax to Jython script actions.
- Removing leading tabs from script transforms.
- Adding extra indentation to a top-level view startup script; the page can open but the startup data load can silently fail.
- Concatenating generated script lines so a helper `def` and the next statement land on one physical line.
- Letting local syntax checks create `__pycache__` inside packaged Project Library script resources; package only `code.py` and `resource.json`.
- Hardcoding provider names without checking provider existence, causing Gateway log spam.
- Putting browse-heavy logic on a fast `now(1000)` or repeated-card binding.


For an offline package, the following live checks are handoff acceptance steps in `VALIDATION.md`, not a requirement to obtain Gateway access. Run only available, authorized checks and clearly distinguish completed offline checks from pending runtime proof.

## Smoke Test

- JSON parses.
- View opens in Designer.
- Bindings show expected preview values.
- Script actions execute without parse errors.
- All critical rows/components still exist after refactors.
- Page loads in a Perspective session.
- Gateway logs are clean after a full refresh.
