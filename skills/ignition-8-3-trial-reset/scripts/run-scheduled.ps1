param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$TokenFile,
    [string]$Gateway = 'http://localhost:8088'
)
$ErrorActionPreference = 'Stop'
try {
    $secure = Get-Content -LiteralPath $TokenFile -Raw | ConvertTo-SecureString
    $env:IGNITION_API_TOKEN = [System.Net.NetworkCredential]::new('', $secure).Password
    & $Python (Join-Path $PSScriptRoot 'trial.py') --gateway $Gateway --reset-if-expired
    $result = $LASTEXITCODE
} finally {
    Remove-Item Env:IGNITION_API_TOKEN -ErrorAction SilentlyContinue
}
exit $result
