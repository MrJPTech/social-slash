<#
.SYNOPSIS
    SWIZZ Voice Writing Agent for social content generation

.DESCRIPTION
    /social:write - Claude Code slash command for AI-powered content generation
    Generates posts, threads, and captions in the SWIZZ voice persona

.PARAMETER Action
    Action to perform: generate, thread, caption, status

.PARAMETER Topic
    Content topic or media description (required for generate/thread/caption)

.PARAMETER Platform
    Target platform for content optimization

.PARAMETER PostType
    Post type: announcement, resource_share, casual, business, promo, hype

.PARAMETER Persona
    Persona mode: professional (Swizzimatic) or personal (BigSwizzi)

.PARAMETER NumPosts
    Number of posts for thread action (default: 3)

.PARAMETER DryRun
    Preview without posting

.EXAMPLE
    /social:write generate -Topic "New product launch" -Platform instagram
    Generate a casual Instagram post about a product launch

.EXAMPLE
    /social:write thread -Topic "AI workflow tips" -Platform twitter -NumPosts 5
    Generate a 5-post Twitter thread

.EXAMPLE
    /social:write caption -Topic "Studio flat lay photo" -Persona personal
    Generate a media caption in BigSwizzi voice

.EXAMPLE
    /social:write status
    Show writing agent status and configuration
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("generate", "thread", "caption", "status")]
    [string]$Action = "status",

    [string]$Topic,

    [ValidateSet("linkedin", "tiktok", "instagram", "youtube", "twitter",
                 "facebook", "pinterest", "threads", "bluesky", "reddit",
                 "snapchat", "telegram", "googlebusiness")]
    [string]$Platform = "instagram",

    [ValidateSet("announcement", "resource_share", "casual", "business", "promo", "hype")]
    [string]$PostType = "casual",

    [ValidateSet("professional", "personal")]
    [string]$Persona = "professional",

    [int]$NumPosts = 3,

    [switch]$DryRun
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
$args = @("-m", "lib.agents.writing_agent", "--action", $Action)
$args += "--platform"
$args += $Platform
$args += "--persona"
$args += $Persona
$args += "--post-type"
$args += $PostType

if ($Topic) {
    $args += "--topic"
    $args += $Topic
}

if ($NumPosts -ne 3) {
    $args += "--num-posts"
    $args += $NumPosts
}

if ($DryRun) {
    $args += "--dry-run"
}

# Display header
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "            SWIZZ Voice Writing Agent                        " -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Action: $Action" -ForegroundColor White
Write-Host "  Platform: $Platform" -ForegroundColor White
Write-Host "  Persona: $Persona" -ForegroundColor White

if ($Topic) {
    Write-Host "  Topic: $Topic" -ForegroundColor White
}

if ($Action -eq "generate") {
    Write-Host "  Post Type: $PostType" -ForegroundColor White
}

if ($Action -eq "thread") {
    Write-Host "  Thread Posts: $NumPosts" -ForegroundColor White
}

if ($DryRun) {
    Write-Host "  DRY RUN: Preview only" -ForegroundColor Magenta
}
Write-Host ""

# Execute with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
