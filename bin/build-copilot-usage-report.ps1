[CmdletBinding()]
param(
    [switch]$NoOpen,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ReportArguments
)

$scriptPath = Join-Path $PSScriptRoot 'copilot-credit-report.py'
$arguments = @($scriptPath) + $ReportArguments
if (-not $NoOpen) {
    $arguments += '--open'
}

& python @arguments
exit $LASTEXITCODE
