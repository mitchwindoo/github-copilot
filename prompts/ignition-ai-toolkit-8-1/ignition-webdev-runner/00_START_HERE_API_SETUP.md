# Ignition Web Dev Runner: Start Here

Runner API version: `0.3.224`

The package contains exactly three files: this guide, the paste-ready `01_PASTE_INTO_WEBDEV_DOPOST.py`, and the copy-ready `02_VERIFY_API_ACCESS_PROMPT.md`.

## 1. Create the Web Dev resource

In Ignition Designer, create an enabled Web Dev Python Resource named `llmImport` with HTTP Method `doPost` in the project you want the agent to use. No `doGet` resource is required.

## 2. Configure and paste the runner

Open `01_PASTE_INTO_WEBDEV_DOPOST.py`, set `TOKEN` near the top to a unique long value, then paste the complete file into the `llmImport` doPost editor. Save and publish the project.

Your endpoint is:

```text
<GATEWAY_URL>/system/webdev/<HOST_PROJECT>/llmImport
```

The compressed block is expected. It keeps the full Jython 2.7.3-compatible API below Ignition's method-size limit.

## 3. Verify access

Open `02_VERIFY_API_ACCESS_PROMPT.md`, replace the three bracketed values, and give the prompt to an AI agent that can reach the Gateway. A successful health response includes `ok: true`, `tokenConfigured: true`, and runner version `0.3.224`.

Use HTTPS and the Gateway, network, project, and role controls required by your site. Keep the token only with authorized users and agents.
