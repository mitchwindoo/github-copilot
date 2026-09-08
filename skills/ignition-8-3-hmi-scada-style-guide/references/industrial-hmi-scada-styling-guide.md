# Industrial HMI and SCADA Styling Guide

Generated: 2026-06-11

Scope: This guide covers what industrial HMI, SCADA, MES, and production visualization screens should look like once the team already knows what it wants to build. It focuses only on visual style, layout, interaction presentation, component behavior, and screen consistency.

This is not an architecture guide, data-modeling guide, alarm-rationalization guide, or full ISA-101 compliance document. Use it as a practical style guide for designing screens that operators, supervisors, maintenance, quality, and leadership can read quickly and trust.

## Contents

- Styling Thesis
- Visual Priorities
- Color Principles
- Theme Principles
- Typography
- Layout Principles
- Component Styling
- Alarm and Abnormal Styling
- High-Performance HMI Style
- Executive and Manager Views
- Navigation Styling
- Iconography
- Data Quality Styling
- Responsive Styling
- Style Tokens
- Review Checklist
- Common Styling Mistakes
- Source Basis

## Styling Thesis

Industrial screens should be calm by default, obvious under stress, and consistent enough that users stop thinking about the interface. Normal operation should visually recede. Abnormal state, risk, required action, bad quality, stale data, and selected context should stand out immediately.

A good industrial screen should feel:

- clear, not decorative;
- modern, not flashy;
- dense enough for work, not crowded;
- consistent, not generic;
- calm in normal operation;
- unmistakable when something needs attention.

## Visual Priorities

The screen should answer these in order:

1. What is the current state?
2. Is anything abnormal?
3. What needs action?
4. What context explains the action?
5. Where do I go next?

Do not let branding, decorative graphics, vendor widgets, 3D equipment art, or oversized KPIs compete with state and action.

## Color Principles

### Use Color Sparingly

Color is a signal, not decoration. Reserve strong color for:

- alarms;
- abnormal states;
- warnings;
- selected items;
- required actions;
- permissive/interlock failures;
- data quality problems;
- safety or operating risk;
- major KPI exceptions.

If normal operation is colorful, abnormal operation has to fight for attention.

### Recommended Semantic Palette

| Meaning | Recommended use |
|---|---|
| Neutral gray | Backgrounds, panels, static structure, normal equipment. |
| White or near-white | Primary text on dark themes, editable fields on some themes, key contrast. |
| Black or near-black | Primary text on light themes, strong structure. |
| Blue | Selection, navigation focus, informational state, active but not dangerous. |
| Green | Confirmed good state, running, available, complete. Use carefully; do not paint the entire screen green during normal operation. |
| Yellow/amber | Warning, caution, pending, needs attention soon. |
| Red | Alarm, trip, critical fault, unsafe, stopped by fault. |
| Purple or magenta | Rare special state only if site convention supports it. Avoid as a general theme. |

### Keep Saturation Controlled

Highly saturated colors look cartoony and become tiring on industrial displays. Keep most colors in a moderate saturation range. Use high saturation only for the rare states that must pull the eye.

### Use Tinted Grays

Pure grayscale can feel lifeless. A very slightly tinted gray can make a UI feel more polished while staying calm. Blue-gray is common for technical interfaces. Keep the tint subtle enough that it still reads as neutral.

### Avoid Too Many Grays

Use a small value scale:

- page background;
- panel background;
- raised/control surface;
- border/divider;
- muted text;
- primary text.

If the design has eight or more visually distinct gray levels, simplify.

## Theme Principles

Choose either a light theme or a dark theme for the operating surface. Do not casually mix dark-theme sections inside a light-theme page or light-theme sections inside a dark-theme page.

Acceptable exceptions:

- selected navigation state;
- modal overlay;
- alarm banner;
- focused control;
- diagnostic panel with a clear purpose;
- chart plot area when contrast requires it.

The user should not feel like different sections came from different applications.

## Typography

### Use a Small Type Scale

Use only a few text sizes:

| Text role | Use |
|---|---|
| Screen title | Current area, line, machine, or dashboard name. |
| Section heading | Groups of related controls or values. |
| Primary value | Important live values, KPIs, state labels. |
| Body text | Labels, descriptions, table contents. |
| Helper text | Units, timestamps, source, data quality notes. |

Avoid hero-scale typography inside operating screens. Industrial displays need readable hierarchy, not marketing drama.

### Label Clearly

Labels should be short, specific, and operational:

- `Line State`
- `Active Run`
- `Target Rate`
- `Actual Count`
- `Reject Count`
- `Downtime Reason`
- `Last Update`
- `Data Quality`

Avoid vague labels:

- `Status`
- `Value`
- `Info`
- `Data`
- `Misc`

### Always Show Units

Any numeric process value should show its unit unless the unit is physically obvious and site-standard:

- `125 psi`
- `72.4 degF`
- `14.2 A`
- `480 V`
- `56 ppm`
- `82.1 %`
- `42 parts/min`

Do not show a bare number when the user needs unit, range, or consequence.

## Layout Principles

### Use a Stable Grid

Pick a grid and stick to it. Use consistent margins, gutters, and alignment. A user may not consciously notice that one screen uses a 10 px margin and another uses 18 px, but the inconsistency makes the system feel untrustworthy.

Recommended rule: define spacing tokens such as `4`, `8`, `12`, `16`, `24`, and `32`, then avoid one-off spacing.

### Put Attention Where It Belongs

The most important information should be visible without hunting. Place the main state, alarm summary, selected asset, and primary operating context in stable locations.

Common pattern:

- top bar: area, line, selected asset, user/session, alarm summary;
- left side: navigation or process hierarchy;
- center: operating display;
- right side or lower band: details, trends, events, diagnostics, or actions.

### Avoid Equal-Quadrant Thinking

Do not split a screen into four equal quadrants just because there are four things to show. Equal quadrants often create weak hierarchy. Size and position should reflect importance, scan frequency, and workflow.

### Keep Related Things Together

Group:

- command and feedback;
- value and unit;
- value and trend;
- alarm and response context;
- state and duration;
- run and product context;
- count and target;
- downtime reason and edit action.

Do not make users mentally join scattered fragments across the screen.

## Component Styling

### Indicators

Indicators should look like read-only information.

Use:

- flat readout surfaces;
- clear labels;
- units;
- value formatting;
- state color only when meaningful;
- timestamp or freshness when needed.

Avoid:

- indicator styles that look clickable;
- shiny buttons used as status lights;
- unlabeled icon-only indicators;
- color without text or shape support.

### Controls

Controls should look actionable and describe the action.

Use action-verb labels:

- `Start Pump`
- `Stop Conveyor`
- `Open Valve`
- `Close Valve`
- `Hold Run`
- `Release Batch`
- `Acknowledge Alarm`
- `Apply Reason`

Avoid ambiguous labels:

- `Pump On`
- `Valve Open`
- `Motor`
- `Enable`
- `Submit`

For dangerous or irreversible actions, use confirmation, role permission, and clear consequence text.

### Toggles

Use toggles carefully. They are often ambiguous because they show both state and control.

If you use a toggle:

- label both states;
- make the current state obvious;
- show what will happen when changed;
- avoid color conventions that invert expectation;
- avoid toggles for high-risk commands.

For industrial controls, two explicit buttons are often clearer:

- `Start` and `Stop`
- `Open` and `Close`
- `Enable` and `Disable`

### Editable Fields

Editable values must look editable. Read-only values must not look editable.

Use:

- consistent input background;
- clear unit;
- allowed range;
- current value;
- pending/apply state;
- validation error state;
- audit-sensitive confirmation where needed.

Do not let operators guess whether a number can be changed.

### Tables

Tables should be scan-friendly.

Use:

- fixed columns for key identity and state;
- row highlighting for selected or abnormal rows;
- status text plus color;
- sortable columns where useful;
- timestamp formatting that matches the plant standard;
- compact but readable row height.

Avoid:

- zebra striping so strong it competes with alarm/status colors;
- wrapping critical values unpredictably;
- hidden horizontal scroll for important columns;
- color-only state indicators.

### Charts and Trends

Charts should explain value in context.

Use:

- engineering units;
- time window;
- setpoint or target;
- high/low limits;
- safe operating band;
- event markers;
- current value marker;
- legend only when it adds clarity.

Avoid:

- decorative charts with no decision purpose;
- too many series;
- unexplained colors;
- auto-scaling that hides limit violations;
- trend windows that reset unexpectedly.

### Status Badges

Status badges should be short and consistent.

Recommended examples:

- `Running`
- `Stopped`
- `Faulted`
- `Blocked`
- `Starved`
- `Changeover`
- `Planned Down`
- `No Order`
- `Held`
- `Manual`
- `Auto`
- `Stale`
- `Bad Quality`

State badges should use both text and visual treatment. Do not rely on color alone.

## Alarm and Abnormal Styling

### Alarm Visual Hierarchy

Use different visual weight for different urgency:

| Priority | Visual treatment |
|---|---|
| Critical | Strong red, clear label, alarm banner/list, audible or flashing only if allowed by alarm philosophy. |
| High | Red or red-accented, prominent but not visually identical to critical if critical exists. |
| Medium | Amber/yellow, visible in context. |
| Low | Muted amber/blue/gray depending on site convention. |
| Diagnostic/event | Do not style as alarm unless operator response is required. |

### Normal Should Be Quiet

Normal states should not scream. A running pump does not need to be bright green if there are 200 running pumps on the screen. Use subdued normal state treatment and reserve strong visual contrast for deviation.

### Flashing and Animation

Avoid animation by default.

Use animation only when:

- it communicates real motion or transition that matters;
- it is infrequent;
- it does not distract from alarms;
- it is approved by the HMI/alarm philosophy;
- it does not create fatigue for repeated use.

Do not use animation to impress stakeholders.

## High-Performance HMI Style

High-performance HMI styling is an attention-management strategy.

Use:

- neutral backgrounds;
- low-contrast normal equipment;
- limited color;
- clear abnormal emphasis;
- embedded trends;
- operating ranges;
- shape and position cues;
- consistent display hierarchy.

Avoid:

- photorealistic tanks, pipes, flames, motors, and shadows;
- 3D bevels and shiny gradients;
- decorative motion;
- color-coded everything;
- P&ID clutter copied directly into an operator display.

Modern high-performance screens do not have to look old or ugly. They should look disciplined, current, and serious.

## Executive and Manager Views

Executive and manager screens can be more polished and visually engaging than operator SCADA screens, but they must not use different truths.

Use:

- clean KPI tiles;
- trend context;
- plan-versus-actual;
- exception highlighting;
- drilldown links;
- clear date/window definitions;
- source and freshness indicators.

Avoid:

- unlabeled demo data;
- fake or manually massaged numbers;
- KPI definitions that differ from production screens;
- vanity dashboards with no decision owner.

If a view uses simulation, demo data, or training data, label it clearly and restrict it from being mistaken for production.

## Navigation Styling

Navigation should be consistent and boring in the best way.

Use:

- stable location;
- clear selected state;
- readable area names;
- breadcrumbs for deep views;
- alarm jump links;
- return-to-overview action;
- consistent icons only where they are familiar.

Avoid:

- hidden menus for critical operations;
- right-click navigation;
- hover-only actions;
- unlabeled icons for uncommon functions;
- different navigation patterns per area.

## Iconography

Use icons as support, not as the only meaning.

Good uses:

- alarm bell with alarm count;
- trend icon for historian;
- wrench for maintenance;
- lock for permission;
- warning triangle for caution;
- check for complete;
- X for failed;
- pause/stop/play for obvious run controls, when paired with labels for industrial commands.

Avoid:

- custom icons nobody understands;
- icons that change meaning by screen;
- icon-only buttons for hazardous actions;
- decorative icon clutter.

## Data Quality Styling

Bad data should look different from bad process.

Separate:

- process alarm;
- machine fault;
- stale value;
- communication loss;
- bad quality;
- manual override;
- simulated value;
- estimated value;
- missing value.

Recommended display patterns:

- `Stale` badge for old values;
- diagonal hatch or muted state for unavailable equipment;
- tooltip/detail showing last good timestamp;
- gray or outlined value for disconnected data;
- explicit `Simulated` or `Manual` label where applicable.

Do not show stale values as if they are live.

## Responsive Styling

Design for named target formats, not every possible screen size.

Recommended targets:

- line-side panel;
- desktop workstation;
- large overhead display;
- tablet;
- phone, only where a mobile workflow exists.

Each target may need a different layout. Do not crush a desktop HMI into a phone screen and call it responsive.

Mobile rules:

- fewer controls;
- larger touch targets;
- no hover-only interactions;
- no right-click;
- simplified navigation;
- view-only by default unless mobile control is explicitly required and governed.

## Style Tokens

Define these once and enforce them.

### Color Tokens

```text
background-page
background-panel
background-control
border-subtle
text-primary
text-muted
state-running
state-stopped
state-faulted
state-warning
state-selected
state-stale
alarm-critical
alarm-high
alarm-medium
alarm-low
quality-bad
quality-uncertain
```

### Spacing Tokens

```text
space-1 = 4
space-2 = 8
space-3 = 12
space-4 = 16
space-5 = 24
space-6 = 32
```

### Type Tokens

```text
title
section-heading
label
body
value
helper
table-cell
button
```

### Component Tokens

```text
button-primary
button-secondary
button-danger
button-disabled
indicator-normal
indicator-abnormal
input-editable
input-readonly
status-badge
alarm-banner
trend-card
faceplate
navigation-selected
```

## Review Checklist

Before approving a screen, ask:

- Can a first-time user distinguish controls from indicators?
- Are all controls labeled with clear action verbs?
- Does color mean the same thing everywhere?
- Is normal operation visually calm?
- Does the most important abnormal condition stand out in three seconds?
- Are numbers contextualized with units, ranges, limits, trends, or targets?
- Are stale, simulated, manual, and bad-quality values visibly different?
- Is navigation consistent with the rest of the system?
- Are margins, typography, and component styles consistent?
- Does the screen still work when values are long, missing, stale, or abnormal?
- Does the screen reduce net operator work?
- Would this screen still be maintainable by the next developer?

## Common Styling Mistakes

- Making an indicator look like a button.
- Labeling a button with state instead of action.
- Using red, yellow, and green as decoration.
- Showing raw numbers without units or context.
- Using too many font sizes.
- Mixing dark and light themes on the same operating surface.
- Copying a P&ID directly into an HMI.
- Using 3D tanks, pipes, shadows, and gradients that add no operational value.
- Animating normal operation.
- Hiding important actions in right-click menus.
- Designing for executives instead of the people who operate the process.
- Making every screen unique.
- Overbuilding a framework so maintainers cannot understand it.
- Claiming full responsiveness instead of designing for named devices.

## Source Basis

This styling guide is synthesized primarily from these IIOTUniversity sources:

- `C:\IIOTUniversity\raw\summary-cards\Mentorship\November 17 Call - Good UI w Evan McKee Part 2 - summary card.md`
- `C:\IIOTUniversity\raw\transcripts\Mentorship\November 17 Call - Good UI w Evan McKee Part 2.md`
- `C:\IIOTUniversity\raw\summary-cards\Mentorship\02 16 24 - Good UI UX Design Part 2 - summary card.md`
- `C:\IIOTUniversity\raw\transcripts\Mentorship\02 16 24 - Good UI UX Design Part 2.md`
- `C:\IIOTUniversity\raw\transcripts\Mentorship\Mentorship Group Call - 11 4 20 - ISA-101 High Performance HMI, Factory Studio Frameworks, and Unified Namespace.md`
- `C:\IIOTUniversity\raw\transcripts\Mentorship\Mentorship Group Call - 8 12 2022 - High Performance HMI and MES Discussion.md`
- `C:\IIOTUniversity\concepts\data-to-decisions-operating-model.md`
- `C:\IIOTUniversity\concepts\steelco-virtual-factory-case-study.md`
