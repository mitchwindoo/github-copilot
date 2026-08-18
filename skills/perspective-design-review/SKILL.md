---
name: perspective-design-review
description: "Run a 5-dimension design review on any Perspective view.json. Scores Style Compliance / Visual Hierarchy / Data Density / Component Patterns / Interaction Quality, each 0–10. Outputs Keep / Fix / Quick-wins lists. USE WHEN: user asks for a 'design review', 'style audit', 'view review', 'check my view', 'is this right', or 'audit against the design system'."
---

# Perspective Design Review Skill

Run a 5-dimension expert design review on any Perspective `view.json` against the NxEdge design system (`DESIGN.md`). Produces an actionable report with evidence-backed scores and prioritized fix lists.

## When to Use

- After creating or editing a Perspective view — self-check before marking done
- When user asks "review this view" or "check my styling"
- When auditing inherited views for design system compliance
- When comparing two view implementations

## What You Produce

A structured review report containing:

1. **Summary** — view name, purpose, 1-line verdict
2. **Score card** — 5 dimensions, each 0–10 with band label
3. **Evidence sections** — per-dimension citations with specific component paths
4. **Action lists:**
   - **Keep** — what's working, don't touch
   - **Fix** — P0/P1 issues that violate the design system
   - **Quick wins** — 5-minute changes with high impact

## The 5 Dimensions

### 1. Style Compliance · Design System Adherence

> Does the view use `nxedge/` style classes, correct tokens, and follow the DESIGN.md rules?

**Evidence to look for:**
- Inline hex colors instead of style classes?
- Colors not in the palette?
- Font family other than Roboto?
- Missing style classes where one exists (e.g., inline `backgroundColor: "#1a2a4e"` instead of `nxedge/colors/background/nxedgeBlue`)?
- Manual `box-shadow` instead of `shadows/depth-*`?
- Using `props.visible` instead of `position.display`?

**0–4** Multiple inline colors, wrong fonts, no style classes. **5–6** Mostly compliant, scattered inline values. **7–8** Clean, 1–2 minor inline overrides. **9–10** Perfect token usage, fully composable classes.

### 2. Visual Hierarchy · Information Architecture

> Can an operator find the most important information instantly?

**Evidence to look for:**
- Is the view's primary data visually dominant (larger, bolder, positioned first)?
- Are headers using the correct typography scale (header > subheader > section > label)?
- Status indicators visible and color-coded correctly?
- Too many accent elements competing for attention?
- Clear primary → secondary → tertiary information tiers?

**0–4** Everything same weight, operator can't prioritize. **5–6** Hero data visible but secondary items compete. **7–8** Clear tiers, occasional weight collision. **9–10** Eye moves to critical data with zero friction.

### 3. Data Density · Industrial Appropriateness

> Does the layout serve an operator making decisions under time pressure?

**Evidence to look for:**
- Excessive whitespace in data-heavy views (wasted screen real estate)?
- Critical values require scrolling to see?
- Tables/grids sized appropriately for the data they hold?
- Status-at-a-glance achievable without interaction?
- Alarm/fault information immediately visible, not buried?
- Appropriate for the target display (control room vs. tablet vs. office)?

**0–4** Mostly empty space, critical data hidden behind clicks. **5–6** Data present but poorly organized. **7–8** Dense where needed, breathing where appropriate. **9–10** Every pixel earns its place, operator sees everything they need.

### 4. Component Patterns · Structural Correctness

> Does the view follow Perspective component patterns and project conventions?

**Evidence to look for:**
- Root container is `ia.container.flex` with proper direction/gap/padding?
- Forms follow: container → title → groups → actions pattern?
- Tables use base/header/cells style classes?
- Buttons have correct class composition (primary/secondary/danger)?
- Bindings are well-structured (not over-nested transforms)?
- Event handlers follow project conventions (script transforms, sendMessage)?
- `resource.json` present with correct scope and version?
- Component types correct (e.g., `ia.display.iframe` not `ia.display.inline-frame`)?

**0–4** Wrong component types, no patterns followed. **5–6** Basic structure OK but inconsistent patterns. **7–8** Solid patterns, minor deviations. **9–10** Textbook implementation, reusable as a template.

### 5. Interaction Quality · UX Polish

> Does the view feel complete and professional to interact with?

**Evidence to look for:**
- Buttons have hover states (via style classes)?
- Disabled states properly indicated?
- Loading states present where data is async?
- Feedback on user actions (toasts, status messages)?
- Error states handled gracefully (empty alert auto-hide, error messages)?
- Navigation clear and consistent?
- Focus order logical (forms flow top-to-bottom)?

**0–4** No feedback, broken states, confusing flow. **5–6** Core interactions work, edge cases unhandled. **7–8** Polished, 1–2 missing states. **9–10** Every interaction provides feedback, gracefully degrades.

## Scoring Discipline

- **Always cite evidence** — `"scored 5 because root.children[2].props.style.color uses inline #333 instead of style class"` beats `"uses some inline styles"`.
- **Don't average up** — if one section has egregious violations, that pulls the score down even if others are perfect.
- **Don't grade-inflate** — 7 means *strong*, not *acceptable*. Most views should score 5–7 initially.
- **Industrial context matters** — a sparse HMI overlay might score 10 on Data Density even though it only shows 3 values. Context is king.

## Workflow

### Step 1 — Acquire the View

Read the `view.json` file. If multiple views mentioned, ask which one (don't review all at once).

### Step 2 — Read DESIGN.md

Load `.github/DESIGN.md` and the `nxedge-styles.instructions.md` for the full token/class inventory.

### Step 3 — Analyze Structure

Walk the component tree:
- Count inline style violations
- Check class usage patterns
- Verify container hierarchy
- Examine binding patterns
- Check for anti-patterns (`props.visible`, wrong component types, inline colors)

### Step 4 — Score with Evidence

For each dimension, provide:
- Score (0–10) with band label
- 2–4 specific citations (component paths, property names, line numbers)
- 1 Keep / Fix / Quick-win bullet

### Step 5 — Produce Action Lists

Combine into prioritized lists:

**Keep** — things done well, positive reinforcement
**Fix (P0)** — design system violations, wrong patterns, broken functionality
**Fix (P1)** — suboptimal but working, should improve
**Quick wins** — 2-minute changes with outsized impact (add a class, swap a color)

## Output Format

```markdown
## Design Review: [View Name]

**Verdict:** [1-sentence summary]
**Overall:** [average]/10

### Scores
| Dimension | Score | Band |
|-----------|-------|------|
| Style Compliance | X/10 | [band] |
| Visual Hierarchy | X/10 | [band] |
| Data Density | X/10 | [band] |
| Component Patterns | X/10 | [band] |
| Interaction Quality | X/10 | [band] |

### Evidence
[Per-dimension evidence paragraphs with citations]

### Keep
- [things working well]

### Fix
- **P0:** [critical violations]
- **P1:** [improvements]

### Quick Wins
- [fast high-impact changes]
```
