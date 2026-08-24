---
name: ignition-8-3-api-auth-and-scan
description: Authentication and project-scan workflow for Ignition 8.3 API calls, including the /data/api/v1/scan/projects hook and strict pre-refresh sequencing.
---

# Ignition 8.3 API Auth And Scan

## Purpose

Use this skill for secure API invocation and for forcing filesystem/project sync before Perspective validation.

Reference spec:

- `/Users/mitch/Git-Local/SHD-Ignition-BOI1/resources/ignition-8-3-8-api.json`

## Required Sequence For UI Validation

1. Make change.
2. Review diff (`git status`, `git diff --name-only`, `git diff`).
3. Call project scan endpoint.
4. Confirm success response.
5. Refresh browser / continue validation.

## Endpoint

- `POST /data/api/v1/scan/projects`

## Auth Strategy

- Prefer environment variables over hardcoded secrets.
- Keep API key/token out of committed files.

Suggested environment variables:

- `IGNITION_BASE_URL` (example: `http://localhost:8088`)
- `IGNITION_API_TOKEN` (or token variable used by your gateway policy)

## Call Template

```bash
curl -sS -X POST \
  -H 'Accept: application/json' \
  -H "X-Ignition-API-Token: ${IGNITION_API_TOKEN}" \
  "${IGNITION_BASE_URL}/data/api/v1/scan/projects"
```

## Success Contract

Expected HTTP status:

- `200`

Expected fields:

- `scanActive` should be `true`
- `lastScanTimestamp` should be present
- `lastScanDuration` should be present

## Failure Contract

If HTTP is `401` or `403`:

1. Stop workflow.
2. Verify key format and header name against gateway configuration.
3. Verify the key has access to this endpoint.
4. Retry once after correction.
5. If still unauthorized, use Gateway UI fallback (`Platform -> Projects -> Scan File System`) and record fallback usage.

If HTTP is `5xx`:

1. Capture body.
2. Check gateway health and logs.
3. Retry with bounded backoff.

## Guardrails

- Do not proceed to browser validation if scan call failed.
- Do not silently swallow auth failures.
- Always report status code and JSON response summary.
