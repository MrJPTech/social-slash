<#
.SYNOPSIS
    Post analytics and activity viewer

.DESCRIPTION
    /social:analytics - Claude Code slash command for post analytics
    View recent posts, check post status, and see engagement metrics

.PARAMETER Action
    Action to perform: recent, post

.PARAMETER PostId
    Post ID for detailed view (required for 'post' action)

.PARAMETER Platform
    Filter recent posts by platform (optional)

.PARAMETER Limit
    Number of recent posts to show (default: 10)

.PARAMETER Json
    Output results as JSON

.EXAMPLE
    /social:analytics recent
    Show 10 most recent posts

.EXAMPLE
    /social:analytics recent -Platform twitter -Limit 5
    Show 5 most recent Twitter posts

.EXAMPLE
    /social:analytics post -PostId "abc123"
    Show detailed status and analytics for a specific post
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("recent", "post")]
    [string]$Action = "recent",

    [string]$PostId,

    [string]$Platform,

    [int]$Limit = 10,

    [switch]$Json
)

# Get project root (3 levels up from this script)
$projectRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName

# Find Python executable
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

# Build arguments
$args = @("-m", "lib.utility.analytics", "--action", $Action)

if ($PostId) {
    $args += "--post-id"
    $args += $PostId
}

if ($Platform) {
    $args += "--platform"
    $args += $Platform
}

if ($Limit -ne 10) {
    $args += "--limit"
    $args += $Limit
}

if ($Json) {
    $args += "--json"
}

# Display header
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "            Post Analytics                                   " -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

# Execute with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
