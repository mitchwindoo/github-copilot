---
name: perspective-dashboard
description: "Create an industrial dashboard/HMI overview Perspective view. USE WHEN: user asks for a 'dashboard', 'overview', 'HMI', 'status screen', 'KPI view', 'monitoring view', 'process overview', or 'control panel' Perspective view. Produces a complete view.json with KPI cards, status indicators, and data grids following NxEdge design patterns."
---

# Perspective Dashboard Skill

Produce a Perspective `view.json` for an industrial dashboard / HMI overview screen. This is the most common view pattern in the NxEdge system — a status-at-a-glance page for operators monitoring process lines, equipment, or production metrics.

## Resource Map

```
.github/skills/perspective-dashboard/
├── SKILL.md                     ← you're reading this
└── references/
    ├── layouts.md               ← section layout patterns
    └── checklist.md             ← pre-flight validation
```

## Workflow

### Step 0 — Pre-flight

1. **Read `.github/DESIGN.md`** — all colors, typography, spacing, and component patterns come from there. Do not invent tokens.
2. **Read `.github/instructions/nxedge-styles.instructions.md`** — the full style class inventory.
3. **Read `.github/skills/perspective-views/SKILL.md`** — the view.json structural rules.
4. **Identify the data domain** from the user's brief: what process/line/equipment is this monitoring?

### Step 1 — Classify the Dashboard Type

| Type | Description | Primary Content |
|------|-------------|-----------------|
| **Process Overview** | Line/cell status at a glance | Equipment status cards + alarm summary |
| **KPI Dashboard** | Production metrics | Numeric KPIs + trend sparklines |
| **Equipment Status** | Single machine detail | Parameters + status + recent history |
| **Alarm Summary** | Active alarm display | Alarm table + counts by severity |

State the chosen type to the user before writing. They can redirect cheaply now.

### Step 2 — Plan the Section Layout

Standard dashboard rhythm:

```
┌─────────────────────────────────────────────────┐
│ Header (view title + timestamp/refresh)         │
├───────┬───────┬───────┬───────┬────────────────-┤
│ KPI 1 │ KPI 2 │ KPI 3 │ KPI 4 │  (row of cards) │
├───────────────────────┬─────────────────────────┤
│ Primary content       │ Secondary content       │
│ (chart/table/status)  │ (alarms/events/detail)  │
├───────────────────────┴─────────────────────────┤
│ Footer / action bar (optional)                  │
└─────────────────────────────────────────────────┘
```

### Step 3 — Build the Component Tree

Root structure:
```json
{
  "custom": {},
  "params": {},
  "propConfig": {},
  "props": { "defaultSize": { "height": 900, "width": 1400 } },
  "root": {
    "type": "ia.container.flex",
    "props": { "direction": "column", "style": { "gap": "1rem", "padding": "1rem" } },
    "meta": { "name": "root" },
    "children": []
  }
}
```

#### Header Section
```json
{
  "type": "ia.container.flex",
  "meta": { "name": "header" },
  "props": {
    "direction": "row",
    "justify": "space-between",
    "alignItems": "center",
    "style": { "classes": "nxedge/typography/header" }
  },
  "children": [
    {
      "type": "ia.display.label",
      "meta": { "name": "title" },
      "props": { "text": "[Dashboard Title]" }
    },
    {
      "type": "ia.display.label",
      "meta": { "name": "timestamp" },
      "props": {
        "text": "Last updated: {timestamp}",
        "style": { "fontSize": "0.8rem", "color": "var(--neutral-60)" }
      }
    }
  ]
}
```

#### KPI Card Row
Each KPI card:
```json
{
  "type": "ia.container.flex",
  "meta": { "name": "kpiCard_[metric]" },
  "props": {
    "direction": "column",
    "style": {
      "classes": "nxedge/components/form/base shadows/depth-1",
      "padding": "1rem",
      "gap": "0.25rem",
      "textAlign": "center"
    }
  },
  "position": { "grow": 1, "basis": "200px" },
  "children": [
    {
      "type": "ia.display.label",
      "meta": { "name": "kpiLabel" },
      "props": {
        "text": "[Metric Name]",
        "style": { "fontSize": "0.85em", "fontWeight": "600", "color": "var(--neutral-60)" }
      }
    },
    {
      "type": "ia.display.label",
      "meta": { "name": "kpiValue" },
      "props": {
        "text": "[Value]",
        "style": { "fontSize": "1.8rem", "fontWeight": "bold", "color": "#1a2a4e" }
      }
    },
    {
      "type": "ia.display.label",
      "meta": { "name": "kpiDelta" },
      "props": {
        "text": "[+/- vs prior]",
        "style": { "fontSize": "0.8em" }
      }
    }
  ]
}
```

#### Status Indicator Pattern
```json
{
  "type": "ia.container.flex",
  "meta": { "name": "statusRow" },
  "props": { "direction": "row", "alignItems": "center", "style": { "gap": "0.5rem" } },
  "children": [
    {
      "type": "ia.display.icon",
      "meta": { "name": "statusDot" },
      "props": {
        "path": "material/fiber_manual_record",
        "style": { "classes": "nxedge/components/status/base nxedge/components/status/success" }
      }
    },
    {
      "type": "ia.display.label",
      "meta": { "name": "statusLabel" },
      "props": { "text": "[Equipment Name]" }
    }
  ]
}
```

### Step 4 — Apply Bindings

Dashboard views typically bind to:
- **Tag bindings** for real-time values (direct tag paths)
- **Named query bindings** for aggregated/historical data
- **Expression bindings** for computed displays (status text from numeric codes)

Example tag binding on a KPI value:
```json
"propConfig": {
  "props.text": {
    "binding": {
      "type": "tag",
      "config": { "path": "[default]Path/To/Tag" }
    }
  }
}
```

Example expression binding for status color:
```json
"propConfig": {
  "props.style.color": {
    "binding": {
      "type": "expr",
      "config": {
        "expression": "if({[default]Path/To/Status} = 1, 'var(--success)', if({[default]Path/To/Status} = 2, 'var(--warning)', 'var(--error)'))"
      }
    }
  }
}
```

### Step 5 — Self-Check

Before emitting the view, verify:

- [ ] Every color from DESIGN.md tokens — no inline hex
- [ ] All containers are `ia.container.flex`
- [ ] Style classes from `nxedge/` namespace applied
- [ ] Using `position.display` for conditional visibility (not `props.visible`)
- [ ] Component names descriptive (`kpiCard_production` not `flex_1`)
- [ ] KPIs use bold large numbers with muted labels
- [ ] Status indicators use semantic color classes
- [ ] Shadows from `shadows/depth-*` classes
- [ ] `resource.json` included with `"scope": "G"`
- [ ] Font is Roboto (via style classes, not inline)

### Step 6 — Emit the View

Output two files:
1. `view.json` — the complete component tree
2. `resource.json` — standard resource metadata

## Hard Rules

- **Data is king.** In an industrial dashboard, every component must serve data visibility. No decorative elements.
- **Alarm colors dominate.** If something is in alarm state, it must be visually louder than everything else on screen.
- **No scrolling for critical data.** The most important 4–6 metrics must be visible without scrolling.
- **Labels explain, values communicate.** Small muted label + large bold value. Always.
- **Status at a glance.** An operator should understand the overall state within 2 seconds of looking at the screen.
- **Use real metric names.** No "Metric 1" or "Value A" placeholders. Use domain-specific names from the user's brief.

## Output Contract

```
views/<Category>/<ViewName>/
├── view.json
└── resource.json
```

State the file path before the JSON. Provide both files in full.
