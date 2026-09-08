# Scheduling

## Windows Task Scheduler

Use Task Scheduler when the operation should run independently of the agent application. Keep this skill folder at a stable path. With `IGNITION_API_TOKEN` set, run:

```powershell
powershell.exe -NoProfile -File scripts/schedule-windows.ps1 -Gateway http://localhost:8088
```

The helper schedules an expiry check every two hours, starting one minute after registration. It runs as the current Windows user while that user is logged in. The machine must be awake and the Gateway reachable. Missed starts run when available. The task skips overlapping instances and has a two-minute execution limit.

The helper stores the token outside the skill under `%LOCALAPPDATA%\IgnitionTrial`, encrypted with Windows DPAPI for the current user on this machine. It passes only that file's path to the task. Clear the setup shell's `IGNITION_API_TOKEN` after registration.

Inspect the registered action and run history:

```powershell
Get-ScheduledTask -TaskName 'Ignition trial check' | Select-Object -ExpandProperty Actions
Get-ScheduledTaskInfo -TaskName 'Ignition trial check'
```

`LastTaskResult` 0 means success or a deliberate skip after a run. Remove the schedule with:

```powershell
powershell.exe -NoProfile -File scripts/schedule-windows.ps1 -Mode Remove
```

Before removing, record the token file path from the action. Delete that exact file afterward if no task uses it. The helper does not configure execution while logged out. If that is required, configure a suitable service account and secret access for that account with the user.

## Codex scheduling

If the user wants a Codex-managed schedule and the automation tool is available, create a thread heartbeat through that tool. Have it run the script with `--reset-if-expired` every two hours using a securely provisioned token. Keep it quiet for active-trial skips and notify on a reset, failure, or required user action. Use the automation tool to update or remove it. Do not also install an OS task for the same Gateway.

## Linux cron

For an agent running on Linux, first confirm `cron` and `flock` are available. Create a protected wrapper at a stable absolute path that obtains `IGNITION_API_TOKEN` from a secret manager or a user-readable file with mode 600, exports it, then executes:

```sh
exec /usr/bin/python3 /absolute/path/ignition-gateway-api/scripts/trial.py --gateway https://gateway.example.com --reset-if-expired
```

Use the actual Python path from that host. Add one entry to the current user's crontab, preserving existing entries:

```cron
0 */2 * * * /usr/bin/flock -n /absolute/private/path/ignition-trial.lock /absolute/path/run-ignition-trial.sh >> /absolute/private/path/ignition-trial.log 2>&1
```

This runs at even-numbered hours in the cron host's timezone. Secure and rotate the log. Never embed the token in crontab. Verify the installed entry with `crontab -l`; remove only that entry when stopping. Inside a container, `localhost` names that container, so configure a reachable Gateway URL.
