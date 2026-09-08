---
name: ignition-8-3-trial-reset
description: Connect to the Ignition 8.3 Gateway API, create a missing API key through the browser, reset an expired trial, and optionally schedule trial checks on Windows or Linux.
---

# 8.3 Ignition Trial Reset

Use this skill with Codex, GrokBot, or another agent that can run Python and host commands. Python 3.9 or newer is required. The scripts use only the standard library.

When the user requests a trial reset and has not chosen a mode, ask exactly: "Do you want to do this one time, or do you want to schedule it?" Honor an answer already given. A one-time request must not create a schedule.

## Connect to the Gateway

1. Identify the Gateway URL and version. Use a URL already supplied by the user. Otherwise check the current Gateway browser tab and, for Docker, use `docker ps` to inspect the image and published host port. On the Gateway's host, try `http://localhost:8088` if there is no better evidence. Verify that it is the intended Ignition 8.3 Gateway. If no Gateway is found or several candidates remain, ask for the intended URL. Docker must be running for a containerized Gateway. Do not replace or recreate its container to reset a trial.
2. Look for an API token already supplied for this Gateway or available through `IGNITION_API_TOKEN` or the configured secret store, without displaying it. If missing, ask: "I don't have an API key for this Gateway yet, and I need one to reset the trial. Would you like me to create one for you using computer use?" For an API setup request, replace "reset the trial" with "connect to the Gateway API". Wait for the user's answer before creating the key unless they already requested or approved its creation. If they agree, follow [Create an API key in the browser](references/create-api-key.md). If they decline, let them provide an existing token or create one themselves. Keep the complete value, including the name and colon prefix when supplied. Set it through `IGNITION_API_TOKEN`; do not put it in skill files, command arguments, logs, or shared packages.
3. Send the token in `X-Ignition-API-Token`. Use HTTPS for remote Gateways and retain certificate verification. The script accepts `--ca-file` for a trusted private CA. Local loopback HTTP is supported.
4. Read authenticated `/data/api/v1/gateway-info` and `/openapi.json`. The interactive documentation is at `/openapi`. Use the installed Gateway's methods, schemas, and permissions for other API operations. Ask what configuration change the user wants before performing unrelated writes.

The trial script is for Ignition 8.3. Verify the installed version before use. A missing POST entry in OpenAPI does not prove the reset route is absent. See [API notes](references/api-notes.md) for the tested behavior and documentation links.

## Create a missing API key

After the user agrees, use the available browser or computer-use tool to complete [the API key setup workflow](references/create-api-key.md). It covers Gateway discovery, user login, a security level, Gateway permissions, Basic Token creation, and a read-only connection test. Reuse an authenticated browser session when available. If the user has provided credentials for this Gateway, use them to log in. Otherwise open the login page and ask the user to sign in, then continue.

API key setup does not require a Designer project, toolkit import, Web Dev resource, or API enhancement. After verifying the key, return to the user's chosen one-time or scheduled trial operation.

## One-time operation

Run commands from this skill's directory. Set the token through the environment or the host's secret manager. In an interactive PowerShell session, a masked prompt avoids putting it in command history:

```powershell
$secure = Read-Host 'Ignition API token' -AsSecureString
$env:IGNITION_API_TOKEN = [System.Net.NetworkCredential]::new('', $secure).Password
python scripts/trial.py --gateway http://localhost:8088
python scripts/trial.py --gateway http://localhost:8088 --reset-if-expired
Remove-Item Env:IGNITION_API_TOKEN
```

The first command reads status. The reset command also reads status and sends one POST only when `expired` is exactly `true` and `trialSecondsLeft` equals `0`. It sends the retrieved status object as JSON, then reads status again to verify the reset. Active trials and Gateways with no trial modules are skipped. Never reset early or modify licensing files, clocks, or container state to force expiry.

Report `reset_verified`, `skipped_not_expired`, or the error clearly. If an active trial is skipped, report the seconds remaining and finish a one-time request. Exit code 0 means success or a deliberate skip; exit code 1 means failure. A POST timeout is ambiguous; read status before any later attempt. Do not blindly retry POST requests.

For 401/403, check the complete token, its permissions, and the Gateway's secure connection requirement. For 404, confirm the URL and installed version. For connection failures, check Docker and the port mapping. Avoid printing server error bodies or authentication headers.

## Scheduled operation

Read [scheduling](references/scheduling.md) only when the user chooses scheduling. Use a scheduler available on the execution host. Confirm the cadence and report when it actually runs. Every invocation must check expiry before POSTing. A two-hour schedule can leave an expired trial waiting almost two hours if a run occurs just before expiry. Explain this timing limitation; offer more frequent status checks if prompt recovery matters.

Keep credentials outside the distributed skill. Make the schedule removable and prevent overlapping runs. Do not enable a schedule merely to test the scheduling helper.
