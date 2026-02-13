<#
.SYNOPSIS
    AI Image Generation Agent using Google Imagen 3

.DESCRIPTION
    /social:imagine - Claude Code slash command for AI image generation
    Generates social media graphics, thumbnails, carousel images, story covers,
    text overlay backgrounds, and freeform AI art

.PARAMETER Action
    Action to perform: graphic, thumbnail, carousel, story, overlay, art, presets, status

.PARAMETER Prompt
    Image description / generation prompt (required for most actions)

.PARAMETER Platform
    Target platform for aspect ratio optimization

.PARAMETER Style
    Visual style: modern, minimal, bold, artistic, photorealistic, flat, gradient, neon

.PARAMETER Persona
    Persona mode: professional (corporate), personal (vibrant), ceo (authoritative)

.PARAMETER AspectRatio
    Override auto-detected aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9)

.PARAMETER NumImages
    Number of image variants to generate (1-4)

.PARAMETER Slides
    Slide descriptions for carousel action (space-separated strings)

.PARAMETER Upload
    Upload generated images to Late SDK and return cloud URLs

.PARAMETER DryRun
    Show enhanced prompt without generating the image

.EXAMPLE
    /social:imagine graphic -Prompt "Modern tech startup workspace" -Platform linkedin
    Generate a LinkedIn-optimized post graphic

.EXAMPLE
    /social:imagine thumbnail -Prompt "10 Python Tips You Need" -Platform youtube
    Generate a YouTube thumbnail

.EXAMPLE
    /social:imagine carousel -Slides "Intro to AI" "Key Benefits" "Get Started" -Platform instagram
    Generate images for a 3-slide carousel

.EXAMPLE
    /social:imagine story -Prompt "Behind the scenes at PRSMTECH" -Persona personal
    Generate a story cover in BigSwizzi style

.EXAMPLE
    /social:imagine art -Prompt "Abstract neural network visualization" -Style neon -AspectRatio 16:9
    Generate freeform AI art

.EXAMPLE
    /social:imagine presets
    List available platform aspect ratio presets

.EXAMPLE
    /social:imagine graphic -Prompt "Team collaboration" -DryRun
    Show the enhanced prompt without generating
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("graphic", "thumbnail", "carousel", "story", "overlay", "art", "presets", "status")]
    [string]$Action = "status",

    [string]$Prompt,

    [ValidateSet("linkedin", "tiktok", "instagram", "youtube", "twitter",
                 "facebook", "pinterest", "threads", "bluesky", "reddit",
                 "snapchat", "telegram", "googlebusiness")]
    [string]$Platform = "instagram",

    [ValidateSet("modern", "minimal", "bold", "artistic", "photorealistic", "flat", "gradient", "neon")]
    [string]$Style = "modern",

    [ValidateSet("professional", "personal", "ceo")]
    [string]$Persona = "professional",

    [ValidateSet("1:1", "3:4", "4:3", "9:16", "16:9")]
    [string]$AspectRatio = "1:1",

    [ValidateRange(1, 4)]
    [int]$NumImages = 1,

    [string[]]$Slides,

    [switch]$Upload,

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
$args = @("-m", "lib.agents.image_agent", "--action", $Action)
$args += "--platform"
$args += $Platform
$args += "--style"
$args += $Style
$args += "--persona"
$args += $Persona
$args += "--aspect-ratio"
$args += $AspectRatio
$args += "--num-images"
$args += $NumImages

if ($Prompt) {
    $args += "--prompt"
    $args += $Prompt
}

if ($Slides) {
    $args += "--slides"
    foreach ($slide in $Slides) {
        $args += $slide
    }
}

if ($Upload) {
    $args += "--upload"
}

if ($DryRun) {
    $args += "--dry-run"
}

# Display header
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Magenta
Write-Host "            AI Image Generation Agent (Imagen 3)            " -ForegroundColor Magenta
Write-Host "===========================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Action: $Action" -ForegroundColor White
Write-Host "  Platform: $Platform" -ForegroundColor White
Write-Host "  Style: $Style" -ForegroundColor White
Write-Host "  Persona: $Persona" -ForegroundColor White

if ($Prompt) {
    $truncated = if ($Prompt.Length -gt 60) { $Prompt.Substring(0, 57) + "..." } else { $Prompt }
    Write-Host "  Prompt: $truncated" -ForegroundColor White
}

if ($Slides) {
    Write-Host "  Slides: $($Slides.Count)" -ForegroundColor White
}

if ($DryRun) {
    Write-Host "  Mode: DRY RUN (prompt only)" -ForegroundColor Yellow
}

if ($Upload) {
    Write-Host "  Upload: Yes (Late SDK)" -ForegroundColor Green
}

Write-Host ""

# Execute with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

exit $exitCode
