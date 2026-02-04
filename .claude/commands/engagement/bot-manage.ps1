<#
.SYNOPSIS
    Bot Account Manager for engagement automation

.DESCRIPTION
    /social:bot-manage - Claude Code slash command for bot account management
    Configure dedicated accounts for automated engagement

.PARAMETER Action
    Action to perform: list, available, register, deactivate, activate, set-primary, stats

.PARAMETER Platform
    Platform filter or target

.PARAMETER AccountId
    Late account ID for register/update actions

.PARAMETER Name
    Bot display name

.PARAMETER Primary
    Set as primary bot for platform

.PARAMETER Style
    Response style: professional, friendly, casual, enthusiastic, supportive

.PARAMETER MaxReplies
    Max replies per hour (default: 60)

.PARAMETER Cooldown
    Cooldown between replies in seconds (default: 300)

.EXAMPLE
    /social:bot-manage available
    List all Late accounts available to use as bots

.EXAMPLE
    /social:bot-manage register -Platform instagram -AccountId abc123 -Primary
    Register an Instagram account as primary bot

.EXAMPLE
    /social:bot-manage list
    List all configured bot accounts
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("list", "available", "register", "deactivate", "activate", "set-primary", "stats")]
    [string]$Action = "list",

    [string]$Platform,

    [string]$AccountId,

    [string]$Name,

    [switch]$Primary,

    [ValidateSet("professional", "friendly", "casual", "enthusiastic", "supportive")]
    [string]$Style = "professional",

    [int]$MaxReplies = 60,

    [int]$Cooldown = 300
)

# Get project root
$projectRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
$pythonScript = Join-Path $projectRoot "lib\agents\bot_manager.py"

# Find Python executable
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

# Build arguments
$args = @($pythonScript, "--action", $Action)

if ($Platform) {
    $args += "--platform"
    $args += $Platform
}

if ($AccountId) {
    $args += "--account-id"
    $args += $AccountId
}

if ($Name) {
    $args += "--name"
    $args += $Name
}

if ($Primary) {
    $args += "--primary"
}

if ($Style -ne "professional") {
    $args += "--style"
    $args += $Style
}

if ($MaxReplies -ne 60) {
    $args += "--max-replies"
    $args += $MaxReplies
}

if ($Cooldown -ne 300) {
    $args += "--cooldown"
    $args += $Cooldown
}

# Display header
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           Bot Account Manager                              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Action: $Action" -ForegroundColor White
if ($Platform) {
    Write-Host "  Platform: $Platform" -ForegroundColor White
}
Write-Host ""

# Execute with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
