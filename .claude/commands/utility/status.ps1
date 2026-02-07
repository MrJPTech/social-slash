<#
.SYNOPSIS
    Social Slash project status dashboard

.DESCRIPTION
    /social:status - Claude Code slash command for project status
    Aggregates connected accounts, bot accounts, and API health status

.PARAMETER Section
    Status section: all, accounts, bots, api

.PARAMETER Json
    Output results as JSON

.EXAMPLE
    /social:status
    Show full project status dashboard

.EXAMPLE
    /social:status accounts
    Show only connected accounts

.EXAMPLE
    /social:status api --json
    Show API health status as JSON
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("all", "accounts", "bots", "api")]
    [string]$Section = "all",

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
$args = @("-m", "lib.utility.status", "--section", $Section)

if ($Json) {
    $args += "--json"
}

# Execute with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
