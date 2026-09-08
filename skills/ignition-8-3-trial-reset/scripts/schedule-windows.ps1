param(
    [ValidateSet('Install','Remove')][string]$Mode = 'Install',
    [string]$TaskName = 'Ignition trial check',
    [string]$Gateway = 'http://localhost:8088',
    [string]$Python = (Get-Command python -ErrorAction Stop).Source
)
$ErrorActionPreference = 'Stop'
if ($Mode -eq 'Remove') {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    exit
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw 'A task with this name already exists. Inspect it before replacing it.'
}
if (-not $env:IGNITION_API_TOKEN) { throw 'Set IGNITION_API_TOKEN before installing the task.' }
$store = Join-Path $env:LOCALAPPDATA 'IgnitionTrial'
New-Item -ItemType Directory -Path $store -Force | Out-Null
$tokenFile = Join-Path $store (([guid]::NewGuid().ToString()) + '.dpapi')
ConvertTo-SecureString $env:IGNITION_API_TOKEN -AsPlainText -Force | ConvertFrom-SecureString | Set-Content -LiteralPath $tokenFile
$runner = Join-Path $PSScriptRoot 'run-scheduled.ps1'
foreach ($value in @($runner,$Python,$tokenFile,$Gateway)) {
    if ($value.Contains('"') -or $value.Contains("`n") -or $value.Contains("`r")) { throw 'Invalid argument character.' }
}
$arguments = '-NoProfile -NonInteractive -File "{0}" -Python "{1}" -TokenFile "{2}" -Gateway "{3}"' -f $runner,$Python,$tokenFile,$Gateway
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
} catch {
    Remove-Item -LiteralPath $tokenFile
    throw
}
Write-Output "Scheduled every two hours while this Windows user is logged in. Token protected with Windows DPAPI: $tokenFile"
Get-ScheduledTaskInfo -TaskName $TaskName
