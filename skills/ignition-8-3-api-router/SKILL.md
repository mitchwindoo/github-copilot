---
name: ignition-8-3-api-router
description: Route Ignition 8.3 API requests to the correct endpoint family using the local OpenAPI reference file resources/ignition-8-3-8-api.json. Use for endpoint discovery, method validation, request shaping, and safe operation ordering.
---

# Ignition 8.3 API Router

## Purpose

Use this skill as the first stop whenever a task needs the Ignition 8.3 HTTP API.
The source of truth is:

- `/Users/mitch/Git-Local/SHD-Ignition-BOI1/resources/ignition-8-3-8-api.json`

## When To Use

- User asks to call an Ignition API endpoint.
- You need to find the correct method/path/body for an operation.
- You need to avoid guessing endpoint names.
- You need to select between core gateway API and module APIs.

## Routing Map

### Core gateway (`/data/api/v1/...`)

- Projects: `/projects/*`
- Resources/config entities: `/resources/*`
- System scan and locks: `/scan/*`, `/scan-lock/*`
- Gateway status and ops: `/gateway-info`, `/overview`, `/mode`, `/restart-tasks`
- Diagnostics: `/diagnostics/*`, `/logs/*`, `/systemPerformance/*`
- Security and activation: `/api-token/*`, `/activation/*`, `/scim/*`

### Module APIs (`/data/<module>/api/v1/...`)

- Perspective: `/data/perspective/api/v1/*`
- OPC UA: `/data/opc-ua/api/v1/*`
- Reporting: `/data/reporting/api/v1/*`
- SFC: `/data/sfc/api/v1/*`
- Vision: `/data/vision/api/v1/*`
- Alarm Notification: `/data/alarm-notification/api/v1/*`
- EAM: `/data/eam/api/v1/*`
- FSQL: `/data/fsql/api/v1/*`
- Event Stream: `/data/event-stream/api/v1/*`

## Discovery Workflow

1. Confirm path+method exist in spec before drafting any call.
2. Prefer read/list/find endpoints before update/delete.
3. For destructive ops, capture current state first.
4. Run project scan when filesystem-backed project resources changed.
5. Verify response status and key fields; do not silently continue on failure.

## Local Validation Commands

```bash
# List all paths
jq -r '.paths | keys[]' resources/ignition-8-3-8-api.json | sort

# Show methods for one endpoint
jq -r '.paths["/data/api/v1/projects/list"] | keys[]' resources/ignition-8-3-8-api.json

# Find endpoints by keyword
jq -r '.paths | keys[]' resources/ignition-8-3-8-api.json | rg 'projects|resources|scan|diagnostics'
```

## Operating Rules

- Never invent endpoints that are not present in the reference JSON.
- Never skip auth/error handling.
- For automation, report: endpoint, method, response code, and outcome.
- If multiple endpoint options exist, choose least-destructive first.
