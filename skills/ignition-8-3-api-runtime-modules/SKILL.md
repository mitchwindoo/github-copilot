---
name: ignition-8-3-api-runtime-modules
description: Use Ignition 8.3 runtime module APIs (Perspective, OPC UA, Reporting, SFC, Vision, EAM, FSQL, Event Stream, Alarm Notification) with endpoint discipline based on resources/ignition-8-3-8-api.json.
---

# Ignition 8.3 Runtime Module APIs

## Purpose

Use this skill when the task targets runtime module state, sessions, clients, certificates, reports, charts, or controller/agent operations.

Reference spec:

- `/Users/mitch/Git-Local/SHD-Ignition-BOI1/resources/ignition-8-3-8-api.json`

## Module Endpoint Families

### Perspective

- `/data/perspective/api/v1/sessions`
- `/data/perspective/api/v1/session/{sessionId}`
- `/data/perspective/api/v1/session/{sessionId}/pages`
- `/data/perspective/api/v1/session/{sessionId}/page/{pageId}/views`

### OPC UA

- `/data/opc-ua/api/v1/{routeType}/certificate`
- `/data/opc-ua/api/v1/{routeType}/certificate/download`
- `/data/opc-ua/api/v1/{routeType}/certificate/regenerate`
- `/data/opc-ua/api/v1/client/pki/...`
- `/data/opc-ua/api/v1/server/pki/...`

### Reporting

- `/data/reporting/api/v1/reports/current`
- `/data/reporting/api/v1/reports/completed`
- `/data/reporting/api/v1/reports/published`
- `/data/reporting/api/v1/reports/upcoming`
- `/data/reporting/api/v1/reports/totals`
- `/data/reporting/api/v1/cancel/{project}`

### SFC

- `/data/sfc/api/v1/charts/status`
- `/data/sfc/api/v1/charts/totals`
- `/data/sfc/api/v1/charts/{projectName}/{chartPath}`
- `/data/sfc/api/v1/charts/{uuid}/pause|resume|cancel`

### Vision

- `/data/vision/api/v1/clients`
- `/data/vision/api/v1/client/{id}`

### EAM

- `/data/eam/api/v1/agents*`
- `/data/eam/api/v1/eam-tasks/*`
- `/data/eam/api/v1/storage/*`
- `/data/eam/api/v1/agent-management/*`

### Other runtime modules

- Alarm Notification: `/data/alarm-notification/api/v1/*`
- FSQL: `/data/fsql/api/v1/status/*`
- Event Stream: `/data/event-stream/api/v1/streams/*`

## Runtime Troubleshooting Pattern

1. Query status/list endpoint first.
2. Capture identifiers (`sessionId`, `pageId`, `uuid`, `serverid`, etc.).
3. Call detail/action endpoint with bounded scope.
4. Re-query status to verify effect.
5. Report before/after state.

## Guardrails

- Do not run destructive actions (`cancel`, `pause`, `delete`) without explicit user intent.
- Prefer per-entity operations over bulk where practical.
- Include module name and endpoint in every operational summary.
