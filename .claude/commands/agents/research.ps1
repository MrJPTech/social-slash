<#
.SYNOPSIS
    SWIZZ Voice Research Agent for trend and content research

.DESCRIPTION
    /social:research - Claude Code slash command for content research
    Researches hashtags, suggests content ideas, analyzes trends, builds content calendars

.PARAMETER Action
    Action to perform: hashtags, suggest, trending, calendar, status

.PARAMETER Topic
    Research topic (required for hashtags)

.PARAMETER Theme
    Content theme (required for suggest)

.PARAMETER Platform
    Target platform for research

.PARAMETER Count
    Number of results (default: 5)

.PARAMETER Days
    Calendar days for calendar action (default: 7)

.PARAMETER Persona
    Persona mode: professional (Swizzimatic) or personal (BigSwizzi)

.EXAMPLE
    /social:research hashtags -Topic "web development" -Platform instagram
    Research relevant hashtags for web development on Instagram

.EXAMPLE
    /social:research suggest -Theme "spring marketing" -Count 10
    Generate 10 content ideas around spring marketing

.EXAMPLE
    /social:research trending -Platform tiktok
    Analyze current trends on TikTok

.EXAMPLE
    /social:research calendar -Days 14 -Platform instagram
    Build a 14-day content calendar for Instagram

.EXAMPLE
    /social:research status
    Show research agent status
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("hashtags", "suggest", "trending", "calendar", "status")]
    [string]$Action = "status",

    [string]$Topic,

    [string]$Theme,

    [ValidateSet("linkedin", "tiktok", "instagram", "youtube", "twitter",
                 "facebook", "pinterest", "threads", "bluesky", "reddit",
                 "snapchat", "telegram", "googlebusiness")]
    [string]$Platform = "instagram",

    [int]$Count = 5,

    [int]$Days = 7,

    [ValidateSet("professional", "personal")]
    [string]$Persona = "professional"
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
$args = @("-m", "lib.agents.research_agent", "--action", $Action)
$args += "--platform"
$args += $Platform
$args += "--persona"
$args += $Persona

if ($Topic) {
    $args += "--topic"
    $args += $Topic
}

if ($Theme) {
    $args += "--theme"
    $args += $Theme
}

if ($Count -ne 5) {
    $args += "--count"
    $args += $Count
}

if ($Days -ne 7) {
    $args += "--days"
    $args += $Days
}

# Display header
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "            SWIZZ Voice Research Agent                       " -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Action: $Action" -ForegroundColor White
Write-Host "  Platform: $Platform" -ForegroundColor White
Write-Host "  Persona: $Persona" -ForegroundColor White

if ($Topic) {
    Write-Host "  Topic: $Topic" -ForegroundColor White
}
if ($Theme) {
    Write-Host "  Theme: $Theme" -ForegroundColor White
}
if ($Action -eq "suggest") {
    Write-Host "  Count: $Count" -ForegroundColor White
}
if ($Action -eq "calendar") {
    Write-Host "  Days: $Days" -ForegroundColor White
}
Write-Host ""

# Execute with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
