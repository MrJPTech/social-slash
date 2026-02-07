<#
.SYNOPSIS
    Account management for connected social media platforms

.DESCRIPTION
    /social:accounts - Claude Code slash command for Late SDK account management
    List connected accounts and refresh account cache

.PARAMETER Action
    Action to perform: list, refresh

.PARAMETER Platform
    Filter by platform name (optional)

.PARAMETER Json
    Output results as JSON

.EXAMPLE
    /social:accounts list
    List all connected social media accounts

.EXAMPLE
    /social:accounts list -Platform instagram
    Show only Instagram accounts

.EXAMPLE
    /social:accounts refresh
    Clear account cache and re-fetch from Late API
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("list", "refresh")]
    [string]$Action = "list",

    [string]$Platform,

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
$args = @("-m", "lib.utility.accounts", "--action", $Action)

if ($Platform) {
    $args += "--platform"
    $args += $Platform
}

if ($Json) {
    $args += "--json"
}

# Display header
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "            Account Manager                                  " -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

# Execute with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
