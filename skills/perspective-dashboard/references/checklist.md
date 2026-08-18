# Dashboard Pre-Flight Checklist

Run through this checklist before emitting any dashboard view.json.

## P0 — Must Pass (blocking)

- [ ] Root container is `ia.container.flex` with `direction: "column"`
- [ ] Every color comes from DESIGN.md tokens (no invented hex values)
- [ ] Style classes use `nxedge/` namespace (not inline styling for colors/typography)
- [ ] Using `position.display` for conditional visibility (never `props.visible`)
- [ ] `resource.json` present with `"scope": "G"`, `"version": 1`
- [ ] Component types correct (`ia.container.flex`, `ia.display.label`, `ia.input.button`, etc.)
- [ ] No external resource links (CDN fonts, images, scripts)
- [ ] Critical data visible without scrolling
- [ ] All component names are descriptive (not `flex_0`, `label_1`)

## P1 — Should Pass (quality)

- [ ] Shadows use `shadows/depth-*` classes (no manual `box-shadow`)
- [ ] Buttons use appropriate variant classes (primary, secondary, danger)
- [ ] Typography scale consistent (header > subHeader > sectionHeader > label > body)
- [ ] Status indicators use semantic color classes (`nxedge/components/status/*`)
- [ ] Spacing follows the scale: xs/sm/md/lg/xl (no arbitrary pixel values)
- [ ] KPI cards have: muted label + bold value + optional delta
- [ ] Tables have base + header + cells style classes applied
- [ ] Alarm/fault states visually dominate over normal states
- [ ] Flex `grow`/`shrink`/`basis` used for proportional sizing (not fixed widths)
- [ ] At most 2 accent-blue elements per visible viewport

## P2 — Bonus (polish)

- [ ] Hover states on interactive elements
- [ ] Shadow elevation increases on cards with hover interaction
- [ ] Timestamp/refresh indicator shows data freshness
- [ ] Empty states handled (what shows when no data/no alarms?)
- [ ] Consistent icon usage (material icon library)
- [ ] Logical reading order (scan top-left → bottom-right)
- [ ] Action buttons at bottom, not scattered throughout
