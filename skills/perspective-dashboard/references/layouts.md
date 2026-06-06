# Dashboard Layout Patterns

Paste-ready section patterns for Perspective dashboard views. Each section is a complete `ia.container.flex` subtree.

---

## 1. KPI Row (3–5 cards)

A horizontal row of equal-width metric cards. Each card: muted label, bold value, optional delta.

```json
{
  "type": "ia.container.flex",
  "meta": { "name": "kpiRow" },
  "props": {
    "direction": "row",
    "style": { "gap": "1rem" },
    "wrap": "wrap"
  },
  "children": [
    "// Repeat 3–5 KPI cards, each with position: { grow: 1, basis: '200px' }"
  ]
}
```

**When to use:** Top of every dashboard. 3–5 headline metrics.

---

## 2. Two-Column Split (60/40 or 50/50)

Primary content left, secondary right.

```json
{
  "type": "ia.container.flex",
  "meta": { "name": "splitSection" },
  "props": {
    "direction": "row",
    "style": { "gap": "1rem" }
  },
  "children": [
    {
      "type": "ia.container.flex",
      "meta": { "name": "primaryColumn" },
      "position": { "grow": 3, "basis": "0" },
      "props": { "direction": "column", "style": { "gap": "1rem" } },
      "children": []
    },
    {
      "type": "ia.container.flex",
      "meta": { "name": "secondaryColumn" },
      "position": { "grow": 2, "basis": "0" },
      "props": { "direction": "column", "style": { "gap": "1rem" } },
      "children": []
    }
  ]
}
```

**When to use:** Chart + alarm table, process diagram + parameter list.

---

## 3. Status Grid (equipment cards)

Grid of equipment status cards, each showing name + status indicator + key value.

```json
{
  "type": "ia.container.flex",
  "meta": { "name": "statusGrid" },
  "props": {
    "direction": "row",
    "wrap": "wrap",
    "style": { "gap": "0.5rem" }
  },
  "children": [
    "// Each child: flex column card with status dot + name + value"
    "// position: { basis: '220px', grow: 1 }"
  ]
}
```

**When to use:** Equipment overview, line status, cell monitoring.

---

## 4. Data Table Section

Table with styled header and data rows. Use Perspective table component.

```json
{
  "type": "ia.container.flex",
  "meta": { "name": "tableSection" },
  "props": {
    "direction": "column",
    "style": {
      "classes": "nxedge/components/table/base",
      "overflow": "auto"
    }
  },
  "position": { "grow": 1 },
  "children": [
    {
      "type": "ia.display.table",
      "meta": { "name": "dataTable" },
      "props": {
        "style": { "classes": "nxedge/components/table/base" }
      }
    }
  ]
}
```

**When to use:** Alarm lists, event logs, production records, batch history.

---

## 5. Chart Container

Wrapper for Perspective chart components.

```json
{
  "type": "ia.container.flex",
  "meta": { "name": "chartContainer" },
  "props": {
    "direction": "column",
    "style": {
      "classes": "nxedge/components/chart/base",
      "minHeight": "300px"
    }
  },
  "position": { "grow": 1 },
  "children": [
    {
      "type": "ia.display.label",
      "meta": { "name": "chartTitle" },
      "props": {
        "text": "[Chart Title]",
        "style": { "classes": "nxedge/typography/subHeader" }
      }
    },
    {
      "type": "ia.chart.timeseries",
      "meta": { "name": "chart" },
      "position": { "grow": 1 }
    }
  ]
}
```

**When to use:** Trend data, production rate over time, temperature/pressure history.

---

## 6. Alarm Summary Bar

Horizontal bar showing alarm counts by severity.

```json
{
  "type": "ia.container.flex",
  "meta": { "name": "alarmSummary" },
  "props": {
    "direction": "row",
    "alignItems": "center",
    "style": { "gap": "1rem", "padding": "0.5rem 1rem" }
  },
  "children": [
    {
      "type": "ia.display.label",
      "meta": { "name": "alarmTitle" },
      "props": {
        "text": "Active Alarms",
        "style": { "fontWeight": "600", "fontSize": "0.85em" }
      }
    },
    {
      "type": "ia.display.label",
      "meta": { "name": "criticalCount" },
      "props": {
        "text": "0",
        "style": { "classes": "nxedge/components/badge/base nxedge/components/badge/danger" }
      }
    },
    {
      "type": "ia.display.label",
      "meta": { "name": "warningCount" },
      "props": {
        "text": "0",
        "style": { "classes": "nxedge/components/badge/base nxedge/components/badge/warning" }
      }
    },
    {
      "type": "ia.display.label",
      "meta": { "name": "infoCount" },
      "props": {
        "text": "0",
        "style": { "classes": "nxedge/components/badge/base nxedge/components/badge/info" }
      }
    }
  ]
}
```

**When to use:** Any dashboard that monitors alarms. Usually placed below KPI row or in header.

---

## 7. Action Bar (bottom)

Horizontal bar with navigation/action buttons.

```json
{
  "type": "ia.container.flex",
  "meta": { "name": "actionBar" },
  "props": {
    "direction": "row",
    "justify": "flex-end",
    "alignItems": "center",
    "style": {
      "gap": "0.5rem",
      "padding": "0.5rem 0",
      "borderTop": "1px solid #b0b7c3"
    }
  },
  "children": [
    {
      "type": "ia.input.button",
      "meta": { "name": "btnRefresh" },
      "props": {
        "text": "Refresh",
        "style": { "classes": "nxedge/components/button/secondary" }
      }
    },
    {
      "type": "ia.input.button",
      "meta": { "name": "btnDetails" },
      "props": {
        "text": "View Details",
        "style": { "classes": "nxedge/components/button/primary" }
      }
    }
  ]
}
```

**When to use:** When the dashboard has drill-down navigation or refresh actions.

---

## Standard Compositions

### Process Overview Dashboard
```
Header → Alarm Summary → KPI Row (4) → Two-Column Split (Status Grid | Data Table) → Action Bar
```

### Production KPI Dashboard
```
Header → KPI Row (5) → Two-Column Split (Chart | Chart) → Data Table → Action Bar
```

### Equipment Detail Dashboard
```
Header → KPI Row (3, equipment params) → Two-Column Split (Chart | Status Grid) → Data Table (events)
```

### Alarm Dashboard
```
Header → Alarm Summary → KPI Row (severity counts) → Data Table (full alarm list) → Action Bar
```
