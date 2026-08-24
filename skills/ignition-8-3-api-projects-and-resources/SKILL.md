---
name: ignition-8-3-api-projects-and-resources
description: Safely manage Ignition 8.3 projects and gateway resources with exact /data/api/v1/projects and /data/api/v1/resources endpoint families from resources/ignition-8-3-8-api.json.
---

# Ignition 8.3 Projects And Resources API

## Purpose

Use this skill for project lifecycle operations and gateway resource CRUD using API-first workflows.

Reference spec:

- `/Users/mitch/Git-Local/SHD-Ignition-BOI1/resources/ignition-8-3-8-api.json`

## Projects Endpoints (Core)

- `POST /data/api/v1/projects`
- `POST /data/api/v1/projects/copy`
- `GET /data/api/v1/projects/list`
- `GET /data/api/v1/projects/names`
- `GET /data/api/v1/projects/find/{name}`
- `PUT /data/api/v1/projects/{name}`
- `DELETE /data/api/v1/projects/{name}`
- `POST /data/api/v1/projects/rename/{name}`
- `GET /data/api/v1/projects/export/{name}`
- `POST /data/api/v1/projects/import/{name}`
- `GET /data/api/v1/projects/parents`
- `GET /data/api/v1/projects/parents/{name}`

## Resources Endpoints (Core Families)

- List/lookup: `/resources/list/*`, `/resources/names/*`, `/resources/find/*`
- Upsert/delete by type: `/resources/<provider>/<type>`, `/resources/.../{name}/{signature}`
- Batch or helper ops: `/resources/copy`, `/resources/move`, `/resources/delete/*`, `/resources/rename/*`
- Singleton config: `/resources/singleton/*`
- Datafiles: `/resources/datafile/*`

## Safe Change Workflow

1. Discover current state with `list` or `find` endpoint.
2. Export/backup project or resource payload before mutation.
3. Apply create/update/rename/move.
4. Verify with read-back endpoint.
5. Trigger `POST /data/api/v1/scan/projects` if filesystem-backed project artifacts were changed.
6. Validate runtime behavior.

## Common Patterns

```bash
# list project names
curl -sS "${IGNITION_BASE_URL}/data/api/v1/projects/names"

# find one project
curl -sS "${IGNITION_BASE_URL}/data/api/v1/projects/find/${PROJECT_NAME}"

# list resource names for a type
curl -sS "${IGNITION_BASE_URL}/data/api/v1/resources/names/ignition/tag-provider"
```

## Guardrails

- Never perform delete/rename/move without prior read-back evidence.
- Preserve signatures where required by delete endpoints.
- For automation scripts, log what changed and what remained unchanged.
