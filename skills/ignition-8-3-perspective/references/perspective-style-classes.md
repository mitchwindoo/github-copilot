# Perspective Style Classes

Use this reference for the exact project Style Class resource, component reference, precedence, and hover shapes qualified on Ignition 8.3.8 / Perspective 3.3.8.

## Project resource shape

Store one class as two project files:

```text
com.inductiveautomation.perspective/style-classes/<style-path>/resource.json
com.inductiveautomation.perspective/style-classes/<style-path>/style.json
```

Use a normal project-resource `resource.json` whose `files` array contains `style.json`. Discover a live 8.3 Style Class resource before constructing metadata; do not translate an 8.1 export.

The tested static payload uses `base.style`:

```json
{
  "base": {
    "style": {
      "backgroundColor": "#0f766e",
      "borderColor": "#134e4a",
      "borderRadius": "12px",
      "borderStyle": "solid",
      "borderWidth": "4px",
      "color": "#ffffff",
      "fontSize": "22px"
    }
  }
}
```

Use explicit border members. In the tested project, a CSS-like `border: "4px solid ..."` member survived project import/export but produced no rendered border. Replacing it with `borderColor`, `borderStyle`, and `borderWidth` produced the expected computed border.

## Component reference

Reference a class through the component style object:

```json
{
  "props": {
    "style": {
      "classes": "app/styles/alpha-base"
    }
  }
}
```

The tested multiple-class form is one space-separated String. Keep each tested class path segment free of spaces because spaces delimit paths:

```json
"classes": "app/styles/zulu-override app/styles/alpha-base"
```

The runtime added one `psc-<style-path>` DOM class token per stored path. Do not depend on that generated token for authoring; use it only as supporting client-validation evidence.

## Precedence

The tested multiple-class component stored the alphabetically later `zulu-override` path before `alpha-base` in the String. At runtime, zulu still won the conflicting `color` and `fontSize`, while alpha supplied its non-conflicting background and border. Thus stored token order did not override the observed alphabetical class precedence.

An inline `props.style.color` and `props.style.fontSize` overrode those same class properties while the class background and border remained active.

Validate precedence with exact stored JSON, DOM tokens, computed styles, and pixels. Do not infer precedence for themes, advanced stylesheets, `!important`, inherited styles, or component-internal selectors.

## Hover variant

Use a `variants` item with `pseudo: "hover"`:

```json
{
  "base": { "style": { "backgroundColor": "#1d4ed8", "color": "#ffffff" } },
  "variants": [
    {
      "pseudo": "hover",
      "style": { "backgroundColor": "#f59e0b", "color": "#111827" }
    }
  ]
}
```

The tested Button changed to the variant while a real pointer hovered it and restored every checked base value after the pointer exited. Capture before, during, and after screenshots plus computed styles; DOM presence alone does not prove the pseudo state painted.

## Authoring and validation

Use official project export/import for arbitrary Style Class JSON unless a separately tested narrower project-resource API exists. Require a fresh-base comparison, exact expected ZIP delta, authentication negative, exact response target, exact export readback, route paint, computed styles, geometry, screenshots, browser diagnostics, official session correlation, Gateway logs, project inventory, and unrelated-project isolation.

This reference does not qualify bindings on `style.classes`, animations, media queries, other pseudo states, the advanced stylesheet resource, inheritance, renaming/deletion, protection, Designer editing, other component types, view/root classes, cross-theme behavior, touch/focus behavior, or live resource revision.
