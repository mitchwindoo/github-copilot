[CmdletBinding()]
param(
    [string]$RootPath = (Join-Path $PSScriptRoot ".."),
    [string]$OutputPath = "CUSTOMIZATIONS.md",
    [string]$ScopeConfigPath = "customization-scope.json",
    [switch]$Check
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AbsolutePath {
    param(
        [Parameter(Mandatory)]
        [string]$BasePath,
        [Parameter(Mandatory)]
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $BasePath $Path))
}

function Get-Frontmatter {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $result = @{}
    $lines = $Content -split "\r?\n"
    if ($lines.Count -eq 0 -or $lines[0].Trim() -ne "---") {
        return $result
    }

    $end = -1
    for ($index = 1; $index -lt $lines.Count; $index++) {
        if ($lines[$index].Trim() -eq "---") {
            $end = $index
            break
        }
    }

    if ($end -lt 0) {
        return $result
    }

    $index = 1
    while ($index -lt $end) {
        if ($lines[$index] -notmatch "^([A-Za-z0-9_-]+):\s*(.*)$") {
            $index++
            continue
        }

        $key = $Matches[1]
        $value = $Matches[2].Trim()
        if ($value -in @("|", ">")) {
            $separator = if ($value -eq ">") { " " } else { "`n" }
            $parts = [System.Collections.Generic.List[string]]::new()
            $index++
            while ($index -lt $end -and ($lines[$index].Trim().Length -eq 0 -or $lines[$index] -match "^\s+")) {
                if ($lines[$index].Trim().Length -gt 0) {
                    $parts.Add($lines[$index].Trim())
                }
                $index++
            }
            $result[$key] = $parts -join $separator
            continue
        }

        if ($value.Length -ge 2 -and (($value.StartsWith("'") -and $value.EndsWith("'")) -or ($value.StartsWith('"') -and $value.EndsWith('"')))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $result[$key] = $value
        $index++
    }

    return $result
}

function Get-MarkdownTitle {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $match = [regex]::Match($Content, "(?m)^#\s+(.+?)\s*$")
    if ($match.Success) {
        return $match.Groups[1].Value.Trim()
    }

    return ""
}

function ConvertTo-MarkdownCell {
    param(
        [AllowEmptyString()]
        [string]$Value,
        [int]$MaximumLength = 180
    )

    $normalized = ($Value -replace "\r?\n", " " -replace "\|", "\|").Trim()
    if ($normalized.Length -le $MaximumLength) {
        return $normalized
    }

    return $normalized.Substring(0, $MaximumLength - 3).TrimEnd() + "..."
}

function Get-RelativePath {
    param(
        [Parameter(Mandatory)]
        [string]$BasePath,
        [Parameter(Mandatory)]
        [string]$Path
    )

    return [System.IO.Path]::GetRelativePath($BasePath, $Path).Replace("\", "/")
}

function Get-Placement {
    param(
        [Parameter(Mandatory)]
        [string]$RelativePath,
        [Parameter(Mandatory)]
        [string]$Content,
        [Parameter(Mandatory)]
        [pscustomobject]$ScopeConfig
    )

    $overrideProperty = $ScopeConfig.overrides.PSObject.Properties[$RelativePath]
    if ($null -ne $overrideProperty) {
        return [pscustomobject]@{
            Placement = $overrideProperty.Value.placement.ToUpperInvariant()
            Reason = $overrideProperty.Value.reason
        }
    }

    $reasons = [System.Collections.Generic.List[string]]::new()
    foreach ($reviewPattern in $ScopeConfig.reviewPatterns) {
        if ([regex]::IsMatch($Content, $reviewPattern.pattern)) {
            $reasons.Add($reviewPattern.reason)
        }
    }

    if ($reasons.Count -gt 0) {
        return [pscustomobject]@{
            Placement = "REVIEW"
            Reason = ($reasons | Select-Object -Unique) -join "; "
        }
    }

    return [pscustomobject]@{
        Placement = "USER"
        Reason = "Reusable across unrelated repositories."
    }
}

function Add-Definition {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[object]]$Definitions,
        [Parameter(Mandatory)]
        [string]$Type,
        [Parameter(Mandatory)]
        [System.IO.FileInfo]$File,
        [Parameter(Mandatory)]
        [string]$Root,
        [Parameter(Mandatory)]
        [pscustomobject]$ScopeConfig
    )

    $content = [System.IO.File]::ReadAllText($File.FullName)
    $frontmatter = Get-Frontmatter -Content $content
    $relativePath = Get-RelativePath -BasePath $Root -Path $File.FullName
    $fallbackName = switch ($Type) {
        "Skill" { $File.Directory.Name }
        "Agent" { $File.Name -replace "\.agent\.md$", "" }
        "Prompt" { $File.Name -replace "\.prompt\.md$", "" }
        default { $File.Name -replace "\.instructions\.md$", "" -replace "\.md$", "" }
    }
    $name = if ($frontmatter.ContainsKey("name") -and $frontmatter["name"]) {
        $frontmatter["name"]
    } else {
        $title = Get-MarkdownTitle -Content $content
        if ($title) { $title } else { $fallbackName }
    }
    $description = if ($frontmatter.ContainsKey("description")) { $frontmatter["description"] } else { "" }
    $placement = Get-Placement -RelativePath $relativePath -Content $content -ScopeConfig $ScopeConfig

    $Definitions.Add([pscustomobject]@{
        Type = $Type
        Name = $name
        Description = $description
        Path = $relativePath
        Placement = $placement.Placement
        Reason = $placement.Reason
    })
}

$root = [System.IO.Path]::GetFullPath($RootPath)
$output = Get-AbsolutePath -BasePath $root -Path $OutputPath
$scopeConfigFile = Get-AbsolutePath -BasePath $root -Path $ScopeConfigPath
if (-not (Test-Path -LiteralPath $scopeConfigFile -PathType Leaf)) {
    throw "Scope configuration not found: $scopeConfigFile"
}

$scopeConfig = Get-Content -LiteralPath $scopeConfigFile -Raw | ConvertFrom-Json
$definitions = [System.Collections.Generic.List[object]]::new()

$globalInstructions = Join-Path $root "copilot-instructions.md"
if (Test-Path -LiteralPath $globalInstructions -PathType Leaf) {
    Add-Definition -Definitions $definitions -Type "Instruction" -File (Get-Item $globalInstructions) -Root $root -ScopeConfig $scopeConfig
}

$skillRoot = Join-Path $root "skills"
if (Test-Path -LiteralPath $skillRoot -PathType Container) {
    Get-ChildItem -LiteralPath $skillRoot -Directory |
        ForEach-Object {
            $skillFile = Join-Path $_.FullName "SKILL.md"
            if (Test-Path -LiteralPath $skillFile -PathType Leaf) {
                Add-Definition -Definitions $definitions -Type "Skill" -File (Get-Item $skillFile) -Root $root -ScopeConfig $scopeConfig
            }
        }
}

foreach ($definitionType in @(
    @{ Type = "Agent"; Directory = "agents"; Filter = "*.agent.md" },
    @{ Type = "Prompt"; Directory = "prompts"; Filter = "*.prompt.md" },
    @{ Type = "Instruction"; Directory = "instructions"; Filter = "*.instructions.md" }
)) {
    $directory = Join-Path $root $definitionType.Directory
    if (Test-Path -LiteralPath $directory -PathType Container) {
        Get-ChildItem -LiteralPath $directory -File -Recurse -Filter $definitionType.Filter |
            ForEach-Object {
                Add-Definition -Definitions $definitions -Type $definitionType.Type -File $_ -Root $root -ScopeConfig $scopeConfig
            }
    }
}

$sortedDefinitions = @($definitions | Sort-Object Type, Name, Path)
$flaggedDefinitions = @($sortedDefinitions | Where-Object { $_.Placement -ne "USER" })
$typeCounts = @{}
foreach ($type in @("Skill", "Instruction", "Prompt", "Agent")) {
    $typeCounts[$type] = @($sortedDefinitions | Where-Object Type -eq $type).Count
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("# Copilot customization catalog")
$lines.Add("")
$lines.Add('> Generated by `bin/review-customizations.ps1`. Do not edit this file directly.')
$lines.Add("")
$lines.Add("## Summary")
$lines.Add("")
$lines.Add("| Type | Count |")
$lines.Add("| --- | ---: |")
foreach ($type in @("Skill", "Instruction", "Prompt", "Agent")) {
    $lines.Add("| $type | $($typeCounts[$type]) |")
}
$lines.Add("| **Total** | **$($sortedDefinitions.Count)** |")
$lines.Add("")
$lines.Add("- User-space candidates: $(@($sortedDefinitions | Where-Object Placement -eq 'USER').Count)")
$lines.Add("- Placement review required: $(@($sortedDefinitions | Where-Object Placement -eq 'REVIEW').Count)")
$lines.Add("- Repository-specific overrides: $(@($sortedDefinitions | Where-Object Placement -eq 'REPOSITORY').Count)")
$lines.Add("")
$lines.Add("## Placement flags")
$lines.Add("")
if ($flaggedDefinitions.Count -eq 0) {
    $lines.Add("No customizations are currently flagged.")
} else {
    $lines.Add("| Placement | Type | Name | Reason | Path |")
    $lines.Add("| --- | --- | --- | --- | --- |")
    foreach ($definition in $flaggedDefinitions) {
        $name = ConvertTo-MarkdownCell $definition.Name
        $reason = ConvertTo-MarkdownCell $definition.Reason
        $lines.Add("| $($definition.Placement) | $($definition.Type) | $name | $reason | [$($definition.Path)](./$($definition.Path)) |")
    }
}

foreach ($type in @("Skill", "Instruction", "Prompt", "Agent")) {
    $lines.Add("")
    $lines.Add("## ${type}s")
    $lines.Add("")
    $lines.Add("| Name | Placement | Description | Path |")
    $lines.Add("| --- | --- | --- | --- |")
    foreach ($definition in @($sortedDefinitions | Where-Object Type -eq $type)) {
        $name = ConvertTo-MarkdownCell $definition.Name
        $description = ConvertTo-MarkdownCell $definition.Description
        $lines.Add("| $name | $($definition.Placement) | $description | [$($definition.Path)](./$($definition.Path)) |")
    }
}

$lines.Add("")
$lines.Add("## Review workflow")
$lines.Add("")
$lines.Add("1. Run `pwsh ./bin/review-customizations.ps1` after adding or changing a customization.")
$lines.Add("2. Review every item under **Placement flags** against [the placement rules](./instructions/customization-placement.instructions.md).")
$lines.Add("3. Record deliberate placement decisions in [`customization-scope.json`](./customization-scope.json).")
$lines.Add("4. Run `pwsh ./bin/review-customizations.ps1 -Check` before committing.")
$lines.Add("")

$expectedContent = ($lines -join "`n")
if ($Check) {
    if (-not (Test-Path -LiteralPath $output -PathType Leaf)) {
        Write-Error "Customization catalog is missing: $output"
        exit 1
    }

    $actualContent = [System.IO.File]::ReadAllText($output).Replace("`r`n", "`n")
    if ($actualContent -ne $expectedContent) {
        Write-Error "Customization catalog is stale. Run: pwsh ./bin/review-customizations.ps1"
        exit 1
    }

    Write-Host "Customization catalog is current: $output"
    exit 0
}

[System.IO.File]::WriteAllText($output, $expectedContent, [System.Text.UTF8Encoding]::new($false))
Write-Host "Customization catalog updated: $output"
Write-Host "Definitions: $($sortedDefinitions.Count); flagged: $($flaggedDefinitions.Count)"
