param(
    [switch]$DryRun,
    [string]$TargetPath = "$HOME/.copilot"
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
$targetPath = [System.IO.Path]::GetFullPath($TargetPath)

Write-Host "Repo root: $repoRoot"
Write-Host "Target path: $targetPath"

if (Test-Path $targetPath) {
    $resolvedTarget = (Resolve-Path $targetPath).Path
    if ([System.IO.Path]::GetFullPath($resolvedTarget) -eq [System.IO.Path]::GetFullPath($repoRoot)) {
        Write-Host "This repo is already installed as the active Copilot config root. Nothing to do."
        exit 0
    }

    if ($DryRun) {
        Write-Host "[dry-run] Refusing to overwrite an existing non-matching target directory: $targetPath"
        exit 0
    }

    Write-Error "A different Copilot config already exists at '$targetPath'. Remove it or choose a different -TargetPath before running this installer."
    exit 1
}

if ($DryRun) {
    Write-Host "[dry-run] Would create a symlink from $targetPath -> $repoRoot"
    exit 0
}

$parent = Split-Path -Parent $targetPath
if (-not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

try {
    New-Item -ItemType SymbolicLink -Path $targetPath -Target $repoRoot | Out-Null
    Write-Host "Portable Copilot setup installed at $targetPath"
    Write-Host "Keep this repo under version control and pull updates on each machine."
} catch {
    Write-Error "Could not create the symbolic link automatically. Use a directory junction or move this repo to $targetPath manually."
    throw
}
