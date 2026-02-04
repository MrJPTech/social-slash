<#
.SYNOPSIS
    DM Reply Agent for automated engagement

.DESCRIPTION
    /social:dm-agent - Claude Code slash command for DM automation
    Monitors conversations and generates AI-powered replies

.PARAMETER Action
    Action to perform: start, stop, status, review, approve, reject

.PARAMETER Platforms
    Target platforms (comma-separated)

.PARAMETER AutoReply
    Auto-send replies without human review

.PARAMETER PollInterval
    Seconds between conversation checks (default: 30)

.PARAMETER ResponseDelay
    Seconds to wait before sending reply (default: 30)

.PARAMETER DryRun
    Simulate without actually sending replies

.PARAMETER ReviewId
    Review ID for approve/reject actions

.EXAMPLE
    /social:dm-agent start -Platforms instagram,telegram
    Start monitoring DMs on Instagram and Telegram

.EXAMPLE
    /social:dm-agent review
    List pending DM replies for review

.EXAMPLE
    /social:dm-agent approve -ReviewId 123
    Approve and send a pending DM reply
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "status", "review", "approve", "reject")]
    [string]$Action = "status",

    [ValidateSet("instagram", "telegram", "reddit", "facebook", "bluesky", "all")]
    [string[]]$Platforms = @("instagram", "telegram", "reddit"),

    [switch]$AutoReply,

    [int]$PollInterval = 30,

    [int]$ResponseDelay = 30,

    [switch]$DryRun,

    [int]$ReviewId,

    [string]$ModifiedReply,

    [switch]$Json
)

# Get project root
$projectRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
$pythonScript = Join-Path $projectRoot "lib\agents\dm_agent.py"

# Find Python executable
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

# Expand "all"
if ($Platforms -contains "all") {
    $Platforms = @("instagram", "telegram", "reddit", "facebook", "bluesky")
}

# Build arguments
$args = @($pythonScript, "--action", $Action)
$args += "--platforms"
$args += ($Platforms -join ",")

if ($PollInterval -ne 30) {
    $args += "--poll-interval"
    $args += $PollInterval
}

if ($ResponseDelay -ne 30) {
    $args += "--response-delay"
    $args += $ResponseDelay
}

if ($AutoReply -and -not $DryRun) {
    $args += "--auto-reply"
}

if ($DryRun) {
    $args += "--dry-run"
}

if ($ReviewId) {
    $args += "--review-id"
    $args += $ReviewId
}

# Display header
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           DM Reply Agent                                   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Action: $Action" -ForegroundColor White
Write-Host "  Platforms: $($Platforms -join ', ')" -ForegroundColor White

if ($Action -eq "start") {
    Write-Host "  Poll Interval: ${PollInterval}s" -ForegroundColor White
    Write-Host "  Response Delay: ${ResponseDelay}s" -ForegroundColor White
    if ($AutoReply -and -not $DryRun) {
        Write-Host "  Mode: AUTO-REPLY (messages sent immediately)" -ForegroundColor Yellow
    } else {
        Write-Host "  Mode: REVIEW (replies queued for approval)" -ForegroundColor Green
    }
    if ($DryRun) {
        Write-Host "  DRY RUN: No actual replies will be sent" -ForegroundColor Magenta
    }
}
Write-Host ""

# Execute
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
