---
name: ignition-8-3-api-diagnostics-and-ops
description: Operational diagnostics and gateway admin API workflows for Ignition 8.3 using /data/api/v1 diagnostics, logs, gateway-network, executors, and system performance endpoints from resources/ignition-8-3-8-api.json.
---

# Ignition 8.3 Diagnostics And Operations API

## Purpose

Use this skill for operational health checks, diagnostics capture, thread analysis, logging inspection, and controlled admin actions.

Reference spec:

- `/Users/mitch/Git-Local/SHD-Ignition-BOI1/resources/ignition-8-3-8-api.json`

## Key Endpoint Families

- Gateway info: `/data/api/v1/gateway-info`
- Overview and mode: `/data/api/v1/overview`, `/data/api/v1/mode`
- Diagnostics bundle: `/data/api/v1/diagnostics/bundle/*`
- Thread diagnostics: `/data/api/v1/diagnostics/threads/*`
- Logs: `/data/api/v1/logs/*`
- Executors: `/data/api/v1/executors/shared`, `/data/api/v1/executors/private`
- Gateway network: `/data/api/v1/gateway-network*`
- System performance: `/data/api/v1/systemPerformance*`
- Restart tasks: `/data/api/v1/restart-tasks*`

## Standard Health Check Flow

1. Read gateway info and overview.
2. Read logs and executor health.
3. Check gateway-network status if distributed.
4. If thread deadlock suspected, pull thread dump endpoints.
5. If deeper triage needed, generate diagnostics bundle and poll status before download.

## Incident Workflow

```bash
# gateway basics
curl -sS "${IGNITION_BASE_URL}/data/api/v1/gateway-info"

# thread deadlocks
curl -sS "${IGNITION_BASE_URL}/data/api/v1/diagnostics/threads/deadlocks"

# diagnostics bundle generation
curl -sS -X POST "${IGNITION_BASE_URL}/data/api/v1/diagnostics/bundle/generate"
```

## Safety And Reporting

- Separate read-only diagnostics from state-changing admin actions.
- For any action endpoint, capture reason, request time, response code, and post-check result.
- Never report success without a follow-up status check.
- If endpoint returns zero results where non-zero expected, explicitly note it as a potential issue.
