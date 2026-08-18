$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$appPath = 'C:\Users\MitchellLandreth\Git-Local\AB-Logix-Git\src\ABLogixGitManager\bin\Release\net10.0-windows\ABLogixGitManager.exe'
$configDirectory = Join-Path $env:APPDATA 'ABLogixGitManager'
$configPath = Join-Path $configDirectory 'config.json'
$backupPath = 'C:\Users\MitchellLandreth\.copilot\session-state\3a80cc13-caf6-4dc9-80dd-75c0291c6260\files\config.before-repo-dialog-test.json'
$testRoot = Join-Path $env:TEMP "ABLogixGitManager-DialogCheck-$([Guid]::NewGuid().ToString('N'))"
$repoPath = Join-Path $testRoot 'not-a-repository'
$acdPath = Join-Path $testRoot 'Controller.acd'
$process = $null
$hadConfig = Test-Path $configPath

function Wait-ForElement {
    param(
        [Parameter(Mandatory)]
        [System.Windows.Automation.AutomationElement] $Root,

        [Parameter(Mandatory)]
        [System.Windows.Automation.Condition] $Condition,

        [System.Windows.Automation.TreeScope] $Scope = [System.Windows.Automation.TreeScope]::Descendants,

        [int] $TimeoutSeconds = 10
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        $element = $Root.FindFirst($Scope, $Condition)
        if ($null -ne $element) {
            return $element
        }

        Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $deadline)

    return $null
}

try {
    if (Get-Process ABLogixGitManager -ErrorAction SilentlyContinue) {
        throw 'Close the running AB Logix Git Manager before the UI verification.'
    }

    New-Item -ItemType Directory -Force -Path $configDirectory, $repoPath | Out-Null
    Set-Content -Path $acdPath -Value '' -Encoding UTF8

    if ($hadConfig) {
        Copy-Item $configPath $backupPath -Force
    }

    $config = [ordered]@{
        l5xGitExePath = $appPath
        repos = @(
            [ordered]@{
                id = [Guid]::NewGuid()
                name = 'UI Prompt Test'
                acdFilePath = $acdPath
                gitRepoPath = $repoPath
            }
        )
    }
    $config | ConvertTo-Json -Depth 4 | Set-Content -Path $configPath -Encoding UTF8

    $process = Start-Process -FilePath $appPath -PassThru
    $processCondition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
        $process.Id)

    $mainWindow = Wait-ForElement `
        -Root ([System.Windows.Automation.AutomationElement]::RootElement) `
        -Condition $processCondition `
        -Scope ([System.Windows.Automation.TreeScope]::Children)
    if ($null -eq $mainWindow) {
        throw 'Main application window did not appear.'
    }

    $listItemCondition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::ListItem)
    $repoItem = Wait-ForElement -Root $mainWindow -Condition $listItemCondition
    if ($null -eq $repoItem) {
        throw 'Configured controller was not shown.'
    }
    $selectionPattern = $repoItem.GetCurrentPattern(
        [System.Windows.Automation.SelectionItemPattern]::Pattern)
    $selectionPattern.Select()

    $messageCondition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::AutomationIdProperty,
        'CommitMessageBox')
    $messageBox = Wait-ForElement -Root $mainWindow -Condition $messageCondition
    if ($null -eq $messageBox) {
        throw 'Commit message box was not found.'
    }
    $valuePattern = $messageBox.GetCurrentPattern(
        [System.Windows.Automation.ValuePattern]::Pattern)
    $valuePattern.SetValue('Verify repository alternatives')

    $buttonCondition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Button)
    $buttons = $mainWindow.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        $buttonCondition)
    $commitButton = $buttons |
        Where-Object { $_.Current.Name -like '*COMMIT TO GIT*' } |
        Select-Object -First 1
    if ($null -eq $commitButton) {
        throw 'Commit button was not found.'
    }
    $invokePattern = $commitButton.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern)
    $invokePattern.Invoke()

    $dialogNameCondition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        'Git Repository Required')
    $dialogCondition = [System.Windows.Automation.AndCondition]::new(
        $processCondition,
        $dialogNameCondition)
    $dialog = Wait-ForElement `
        -Root ([System.Windows.Automation.AutomationElement]::RootElement) `
        -Condition $dialogCondition `
        -Scope ([System.Windows.Automation.TreeScope]::Descendants)
    if ($null -eq $dialog) {
        $processElements = [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
            [System.Windows.Automation.TreeScope]::Descendants,
            $processCondition)
        $visibleElements = $processElements |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_.Current.Name) } |
            ForEach-Object { "$($_.Current.ControlType.ProgrammaticName): $($_.Current.Name)" }
        Write-Output ($visibleElements -join [Environment]::NewLine)
        throw 'Git Repository Required dialog did not appear.'
    }

    foreach ($buttonName in 'Initialize Git', 'Clone Repository', 'Cancel') {
        $nameCondition = [System.Windows.Automation.PropertyCondition]::new(
            [System.Windows.Automation.AutomationElement]::NameProperty,
            $buttonName)
        if ($null -eq $dialog.FindFirst(
            [System.Windows.Automation.TreeScope]::Descendants,
            $nameCondition)) {
            throw "Dialog did not show the '$buttonName' option."
        }
    }

    $cancelCondition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        'Cancel')
    $cancelButton = $dialog.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        $cancelCondition)
    $cancelPattern = $cancelButton.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern)
    $cancelPattern.Invoke()

    Write-Output 'PASS: Commit displayed Initialize Git, Clone Repository, and Cancel.'
}
finally {
    if ($null -ne $process -and -not $process.HasExited) {
        $process.CloseMainWindow() | Out-Null
        if (-not $process.WaitForExit(3000)) {
            Stop-Process -Id $process.Id -Force
        }
    }

    if ($hadConfig -and (Test-Path $backupPath)) {
        Copy-Item $backupPath $configPath -Force
        Remove-Item $backupPath -Force
    }
    elseif (-not $hadConfig) {
        Remove-Item $configPath -Force -ErrorAction SilentlyContinue
    }

    Remove-Item $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
