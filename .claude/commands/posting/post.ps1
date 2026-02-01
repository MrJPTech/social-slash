<#
.SYNOPSIS
    Post content to social media platforms via Late API

.DESCRIPTION
    /social:post - Claude Code slash command for social media posting
    Supports 13 platforms with optional AI enhancement

.PARAMETER Content
    The content/text to post

.PARAMETER Platforms
    Target platforms (comma-separated or array)

.PARAMETER Enhance
    Enable AI content enhancement

.PARAMETER AIProvider
    AI provider for enhancement (gemini or anthropic)

.PARAMETER Media
    Media URLs to attach (comma-separated)

.PARAMETER Schedule
    ISO datetime for scheduled posting

.PARAMETER DryRun
    Simulate posting without actually posting

.PARAMETER Json
    Output results as JSON

.EXAMPLE
    /social:post -Content "Lock in developers" -Platforms linkedin

.EXAMPLE
    /social:post -Content "New video!" -Platforms tiktok,instagram -Media "https://..."

.EXAMPLE
    /social:post -Content "Post" -Platforms linkedin -Enhance -DryRun

.EXAMPLE
    /social:post -Content "Multi" -Platforms linkedin,twitter,threads -Enhance -AIProvider anthropic
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Content,

    [Parameter(Mandatory=$true, Position=1)]
    [ValidateSet("linkedin", "tiktok", "instagram", "youtube", "twitter",
                 "facebook", "pinterest", "threads", "bluesky", "reddit",
                 "snapchat", "telegram", "googlebusiness")]
    [string[]]$Platforms,

    [switch]$Enhance,

    [ValidateSet("gemini", "anthropic")]
    [string]$AIProvider = "gemini",

    [string[]]$Media,

    [string]$Schedule,

    [switch]$DryRun,

    [switch]$Json
)

# Get project root (3 levels up from this script)
$scriptRoot = $PSScriptRoot
$projectRoot = (Get-Item $scriptRoot).Parent.Parent.Parent.FullName
$pythonScript = Join-Path $projectRoot "lib\posting\poster.py"

# Check if Python script exists
if (-not (Test-Path $pythonScript)) {
    Write-Error "Python backend not found: $pythonScript"
    exit 1
}

# Find Python executable
$pythonPaths = @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe"),
    "python",
    "python3"
)

$pythonExe = $null
foreach ($path in $pythonPaths) {
    if (Get-Command $path -ErrorAction SilentlyContinue) {
        $pythonExe = $path
        break
    }
    if (Test-Path $path) {
        $pythonExe = $path
        break
    }
}

if (-not $pythonExe) {
    Write-Error "Python not found. Install Python or create a virtual environment."
    exit 1
}

# Build arguments
$args = @(
    $pythonScript,
    "--content", $Content,
    "--platforms", ($Platforms -join ",")
)

if ($Enhance) {
    $args += "--enhance"
    $args += "--ai-provider"
    $args += $AIProvider
}

if ($Media) {
    $args += "--media"
    $args += ($Media -join ",")
}

if ($Schedule) {
    $args += "--schedule"
    $args += $Schedule
}

if ($DryRun) {
    $args += "--dry-run"
}

if ($Json) {
    $args += "--json"
}

# Display command info
Write-Host ""
Write-Host "[SOCIAL SLASH] Posting to: $($Platforms -join ', ')" -ForegroundColor Cyan

if ($Enhance) {
    Write-Host "[AI] Enhancement enabled ($AIProvider)" -ForegroundColor Yellow
}

if ($DryRun) {
    Write-Host "[MODE] Dry run - no actual post will be made" -ForegroundColor Yellow
}

Write-Host ""

# Execute Python backend
& $pythonExe @args
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Posting failed with exit code: $exitCode" -ForegroundColor Red
    exit $exitCode
}

exit 0
