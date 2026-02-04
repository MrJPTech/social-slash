<#
.SYNOPSIS
    Comment Reply Agent for automated engagement

.DESCRIPTION
    /social:comment-agent - Claude Code slash command for comment automation
    Monitors posts for new comments and generates AI-powered replies

.PARAMETER Action
    Action to perform: start, stop, status, review, approve, reject

.PARAMETER Platforms
    Target platforms (comma-separated)

.PARAMETER AutoApprove
    Auto-approve and send replies without human review

.PARAMETER PollInterval
    Seconds between comment checks (default: 60)

.PARAMETER DryRun
    Simulate without actually sending replies

.PARAMETER ReviewId
    Review ID for approve/reject actions

.PARAMETER ModifiedReply
    Modified reply text when approving

.EXAMPLE
    /social:comment-agent start -Platforms instagram,reddit
    Start monitoring comments on Instagram and Reddit

.EXAMPLE
    /social:comment-agent review
    List pending comment replies for review

.EXAMPLE
    /social:comment-agent approve -ReviewId 123
    Approve and send a pending reply
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "status", "review", "approve", "reject")]
    [string]$Action = "status",

    [ValidateSet("instagram", "reddit", "youtube", "facebook", "linkedin",
                 "bluesky", "tiktok", "all")]
    [string[]]$Platforms = @("instagram", "reddit"),

    [switch]$AutoApprove,

    [int]$PollInterval = 60,

    [switch]$DryRun,

    [int]$ReviewId,

    [string]$ModifiedReply,

    [switch]$Json
)

# Get project root (3 levels up from this script)
$projectRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
$pythonScript = Join-Path $projectRoot "lib\agents\comment_agent.py"

# Find Python executable
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

# Expand "all" to all platforms
if ($Platforms -contains "all") {
    $Platforms = @("instagram", "reddit", "youtube", "facebook", "linkedin", "bluesky", "tiktok")
}

# Build arguments
$args = @($pythonScript, "--action", $Action)
$args += "--platforms"
$args += ($Platforms -join ",")

if ($PollInterval -ne 60) {
    $args += "--poll-interval"
    $args += $PollInterval
}

if ($AutoApprove -and -not $DryRun) {
    $args += "--auto-approve"
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
Write-Host "║           Comment Reply Agent                              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Action: $Action" -ForegroundColor White
Write-Host "  Platforms: $($Platforms -join ', ')" -ForegroundColor White

if ($Action -eq "start") {
    Write-Host "  Poll Interval: ${PollInterval}s" -ForegroundColor White
    if ($AutoApprove -and -not $DryRun) {
        Write-Host "  Mode: AUTO-APPROVE (replies sent immediately)" -ForegroundColor Yellow
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
