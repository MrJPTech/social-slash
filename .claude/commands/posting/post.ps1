<#
.SYNOPSIS
    Post content to social media platforms via Late API

.DESCRIPTION
    /social:post - Claude Code slash command for social media posting
    Supports 13 platforms with optional AI enhancement and platform-specific options

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

.PARAMETER RedditTitle
    Reddit post title (auto-generated from first line if not provided)

.PARAMETER IgType
    Instagram content type: story, post, or reel

.PARAMETER IgFirstComment
    Instagram first comment to post after publishing

.PARAMETER IgCollaborators
    Instagram collaborator usernames (comma-separated, max 3)

.PARAMETER IgNoFeed
    For Instagram reels, don't show on main feed

.PARAMETER LiFirstComment
    LinkedIn first comment to post after publishing

.PARAMETER LiNoLinkPreview
    Disable link preview card on LinkedIn

.PARAMETER ThreadsAutoThread
    Auto-break long content into threaded Threads replies

.PARAMETER ThreadsNumber
    Add numbering to Threads posts (1/n, 2/n...)

.PARAMETER TwitterThread
    Auto-break long content into tweet thread

.PARAMETER PlatformOptions
    Raw JSON string with advanced platform-specific options

.EXAMPLE
    /social:post -Content "Lock in developers" -Platforms linkedin

.EXAMPLE
    /social:post -Content "New video!" -Platforms tiktok,instagram -Media "https://..."

.EXAMPLE
    /social:post -Content "Post" -Platforms linkedin -Enhance -DryRun

.EXAMPLE
    /social:post -Content "Multi" -Platforms linkedin,twitter,threads -Enhance -AIProvider anthropic

.EXAMPLE
    /social:post -Content "Behind the scenes!" -Platforms instagram -IgType story

.EXAMPLE
    /social:post -Content "Check this out!" -Platforms instagram -IgFirstComment "Links in bio!"

.EXAMPLE
    /social:post -Content "Big announcement" -Platforms linkedin -LiFirstComment "DM for details"

.EXAMPLE
    /social:post -Content "My Title`n`nPost body here" -Platforms reddit

.EXAMPLE
    /social:post -Content "Post body" -Platforms reddit -RedditTitle "My Custom Title"
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

    [switch]$Json,

    # Reddit options
    [string]$RedditTitle,

    # Instagram options
    [ValidateSet("story", "post", "reel")]
    [string]$IgType,

    [string]$IgFirstComment,

    [string]$IgCollaborators,

    [switch]$IgNoFeed,

    # LinkedIn options
    [string]$LiFirstComment,

    [switch]$LiNoLinkPreview,

    # Threads options
    [switch]$ThreadsAutoThread,

    [switch]$ThreadsNumber,

    # Twitter options
    [switch]$TwitterThread,

    # Advanced: Raw JSON platform options
    [string]$PlatformOptions
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

# Platform-specific options

# Reddit
if ($RedditTitle) {
    $args += "--reddit-title"
    $args += $RedditTitle
}

# Instagram
if ($IgType) {
    $args += "--ig-type"
    $args += $IgType
}

if ($IgFirstComment) {
    $args += "--ig-first-comment"
    $args += $IgFirstComment
}

if ($IgCollaborators) {
    $args += "--ig-collaborators"
    $args += $IgCollaborators
}

if ($IgNoFeed) {
    $args += "--ig-no-feed"
}

# LinkedIn
if ($LiFirstComment) {
    $args += "--li-first-comment"
    $args += $LiFirstComment
}

if ($LiNoLinkPreview) {
    $args += "--li-no-link-preview"
}

# Threads
if ($ThreadsAutoThread) {
    $args += "--threads-auto-thread"
}

if ($ThreadsNumber) {
    $args += "--threads-number"
}

# Twitter
if ($TwitterThread) {
    $args += "--twitter-thread"
}

# Advanced: Raw JSON
if ($PlatformOptions) {
    $args += "--platform-options"
    $args += $PlatformOptions
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

# Execute Python backend with PYTHONPATH set
$env:PYTHONPATH = $projectRoot
& $pythonExe @args
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Posting failed with exit code: $exitCode" -ForegroundColor Red
    exit $exitCode
}

exit 0
