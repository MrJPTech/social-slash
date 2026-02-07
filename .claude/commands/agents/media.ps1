<#
.SYNOPSIS
    SWIZZ Voice Media Agent for media captioning and format suggestions

.DESCRIPTION
    /social:media - Claude Code slash command for media content generation
    Generates reel captions, story text, carousel captions, alt text, and format suggestions

.PARAMETER Action
    Action to perform: caption, story, carousel, alt, suggest, status

.PARAMETER Description
    Media description or content idea (required for most actions)

.PARAMETER Context
    Additional context for caption generation

.PARAMETER Platform
    Target platform for content optimization

.PARAMETER Persona
    Persona mode: professional (Swizzimatic) or personal (BigSwizzi)

.PARAMETER Slides
    Slide descriptions for carousel action (space-separated strings)

.EXAMPLE
    /social:media caption -Description "Product flat lay photo" -Platform instagram
    Generate a reel caption for a product photo

.EXAMPLE
    /social:media story -Description "Behind the scenes at the studio" -Persona personal
    Generate story text in BigSwizzi voice

.EXAMPLE
    /social:media carousel -Slides "Slide 1 intro" "Slide 2 details" "Slide 3 CTA"
    Generate carousel captions for multiple slides

.EXAMPLE
    /social:media alt -Description "Team photo at conference booth"
    Generate accessible alt text for an image

.EXAMPLE
    /social:media suggest -Description "Tutorial on API integration" -Platform tiktok
    Get media format recommendation for content idea

.EXAMPLE
    /social:media status
    Show media agent status
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("caption", "story", "carousel", "alt", "suggest", "status")]
    [string]$Action = "status",

    [string]$Description,

    [string]$Context = "",

    [ValidateSet("linkedin", "tiktok", "instagram", "youtube", "twitter",
                 "facebook", "pinterest", "threads", "bluesky", "reddit",
                 "snapchat", "telegram", "googlebusiness")]
    [string]$Platform = "instagram",

    [ValidateSet("professional", "personal")]
    [string]$Persona = "professional",

    [string[]]$Slides
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
$args = @("-m", "lib.agents.media_agent", "--action", $Action)
$args += "--platform"
$args += $Platform
$args += "--persona"
$args += $Persona

if ($Description) {
    $args += "--description"
    $args += $Description
}

if ($Context) {
    $args += "--context"
    $args += $Context
}

if ($Slides) {
    $args += "--slides"
    foreach ($slide in $Slides) {
        $args += $slide
    }
}

# Display header
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "            SWIZZ Voice Media Agent                          " -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Action: $Action" -ForegroundColor White
Write-Host "  Platform: $Platform" -ForegroundColor White
Write-Host "  Persona: $Persona" -ForegroundColor White

if ($Description) {
    $truncated = if ($Description.Length -gt 60) { $Description.Substring(0, 57) + "..." } else { $Description }
    Write-Host "  Description: $truncated" -ForegroundColor White
}

if ($Slides) {
    Write-Host "  Slides: $($Slides.Count)" -ForegroundColor White
}
Write-Host ""

# Execute with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
