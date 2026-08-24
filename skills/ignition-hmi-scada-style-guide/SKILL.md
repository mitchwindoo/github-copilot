---
name: ignition-hmi-scada-style-guide
description: Style Ignition Perspective, HMI, SCADA, MES, OEE, downtime, and production visualization screens for industrial users. Use when Codex needs visual design rules, component appearance, semantic color, layout hierarchy, alarm/abnormal-state styling, typography, chart/table styling, or high-performance HMI guidance for an industrial interface after the functional scope is already known.
---

# Ignition HMI/SCADA Style Guide

Skill version: `1.0.22`
Stack version: `starter-2026.07.06.04`

## Scope

Use this skill to make industrial screens look and behave consistently. Keep the focus on styling, visual hierarchy, component appearance, state presentation, and screen-level composition.

Do not use this skill as the primary source for Perspective JSON structure, package import mechanics, Gateway/Web Dev deployment, Jython scripting, SQL, UDT modeling, or alarm rationalization. Pair it with the relevant Ignition skill when the task also requires implementation.

## Skill Properties

- Primary platform: Ignition 8.1 Perspective.
- Adjacent platforms: HMI, SCADA, MES, OEE, downtime, line-performance, production, quality, and maintenance dashboards.
- Guidance type: styling and visual design principles only.
- Source basis: IIOT University UI/UX, high-performance HMI, SCADA, MES, UNS, and data-to-decisions notes, with ISA-101-style high-performance HMI principles.
- Design posture: calm normal operation, strong abnormal-state contrast, consistent controls, clear data context, and operator-first decision support.

## Reference

Load `references/industrial-hmi-scada-styling-guide.md` when the user asks for a style guide, visual rules, screen styling, component appearance, HMI design principles, SCADA look-and-feel, high-performance HMI styling, or a review of whether an industrial screen looks right.

Use the reference as the authoritative guide for:

- color and semantic palette rules;
- typography and density;
- layout hierarchy;
- indicator, control, table, trend, chart, badge, and navigation styling;
- alarm, warning, stale-data, bad-quality, and abnormal-state presentation;
- high-performance HMI visual style;
- executive or manager view styling differences;
- responsive industrial screen rules;
- review checklist and common styling mistakes.

## Core Rules

Normal operation should be calm and visually quiet. Reserve saturated color, motion, strong contrast, and attention marks for abnormal state, risk, action, selection, bad quality, stale data, or operating exceptions.

Make controls and indicators visibly different. Controls should look interactive and use action-oriented labels. Indicators should look read-only and never invite random clicking.

Show numbers with context: units, precision, expected range, target, trend, quality, timestamp, source, or operating state when those details affect the user's decision.

Keep navigation, margins, typography, color semantics, and component states consistent across screens. If a screen is part of an operator workflow, repeated use matters more than novelty.

Avoid decorative 3D, heavy animation, novelty gradients, and highly saturated normal-state graphics. Use process graphics only when they help the user understand state, flow, constraints, or action.

For operator SCADA/HMI pages, make the current state, abnormal condition, and next action obvious first. For supervisor and executive pages, allow more polish, but do not sacrifice trust, source context, or exception visibility.

## Working With Other Skills

- Use `ignition-perspective-import-zip` when the styled design must become a portable Perspective package.
- Use `ignition-perspective-host-builder` when the styled design must be applied or validated on a reachable Gateway.
- Use `ignition-udt-builder` when the styling depends on UDT-facing metadata such as display name, area, units, state, quality, alarm rollups, or sort/filter fields.
- Use `ignition-sql-query-builder` when tables, trends, KPIs, or dashboard components need safe database or historian query patterns.
