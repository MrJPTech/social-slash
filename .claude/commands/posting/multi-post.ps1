<#
.SYNOPSIS
    Post content to multiple platforms simultaneously

.DESCRIPTION
    /social:multi-post - Convenience command for multi-platform distribution
    Posts to all specified platforms with consistent content

.PARAMETER Content
    The content/text to post

.PARAMETER Platforms
    Target platforms (default: linkedin,twitter,threads)

.PARAMETER Enhance
    Enable AI content enhancement

.PARAMETER DryRun
    Simulate posting without actually posting

.EXAMPLE
    /social:multi-post -Content "Big announcement!"

.EXAMPLE
    /social:multi-post -Content "New content" -Platforms linkedin,instagram,facebook

.EXAMPLE
    /social:multi-post -Content "Enhanced post" -Enhance -DryRun
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Content,

    [string[]]$Platforms = @("linkedin", "twitter", "threads"),

    [switch]$Enhance,

    [ValidateSet("gemini", "anthropic")]
    [string]$AIProvider = "gemini",

    [switch]$DryRun,

    [switch]$Json
)

# Get the post.ps1 script path
$scriptRoot = $PSScriptRoot
$postScript = Join-Path $scriptRoot "post.ps1"

# Build parameters
$params = @{
    Content = $Content
    Platforms = $Platforms
}

if ($Enhance) {
    $params.Enhance = $true
    $params.AIProvider = $AIProvider
}

if ($DryRun) {
    $params.DryRun = $true
}

if ($Json) {
    $params.Json = $true
}

# Display header
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SOCIAL SLASH - Multi-Platform Post" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Platforms: $($Platforms -join ', ')" -ForegroundColor White
Write-Host ""

# Execute post command
& $postScript @params
