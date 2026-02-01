<#
.SYNOPSIS
    Schedule a post for future publishing

.DESCRIPTION
    /social:schedule - Schedule content for future posting
    Supports relative time (e.g., "in 2 hours") or absolute ISO datetime

.PARAMETER Content
    The content/text to post

.PARAMETER Platforms
    Target platforms

.PARAMETER At
    When to post - ISO datetime or relative time

.PARAMETER Enhance
    Enable AI content enhancement

.PARAMETER DryRun
    Simulate without actually scheduling

.EXAMPLE
    /social:schedule -Content "Morning post" -Platforms linkedin -At "2024-12-01T09:00:00Z"

.EXAMPLE
    /social:schedule -Content "Afternoon content" -Platforms twitter -At "in 3 hours"

.EXAMPLE
    /social:schedule -Content "Tomorrow's post" -Platforms threads -At "tomorrow 10am"
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Content,

    [Parameter(Mandatory=$true)]
    [string[]]$Platforms,

    [Parameter(Mandatory=$true)]
    [string]$At,

    [switch]$Enhance,

    [ValidateSet("gemini", "anthropic")]
    [string]$AIProvider = "gemini",

    [switch]$DryRun,

    [switch]$Json
)

# Parse relative time to ISO format
function Convert-ToISODateTime {
    param([string]$TimeSpec)

    $now = Get-Date

    # Check if already ISO format
    if ($TimeSpec -match '^\d{4}-\d{2}-\d{2}T') {
        return $TimeSpec
    }

    # Parse relative times
    switch -Regex ($TimeSpec.ToLower()) {
        '^in\s+(\d+)\s+hour' {
            $hours = [int]$matches[1]
            return $now.AddHours($hours).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        }
        '^in\s+(\d+)\s+minute' {
            $minutes = [int]$matches[1]
            return $now.AddMinutes($minutes).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        }
        '^in\s+(\d+)\s+day' {
            $days = [int]$matches[1]
            return $now.AddDays($days).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        }
        '^tomorrow\s+(\d+)(am|pm)?$' {
            $hour = [int]$matches[1]
            if ($matches[2] -eq 'pm' -and $hour -lt 12) { $hour += 12 }
            return $now.Date.AddDays(1).AddHours($hour).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        }
        default {
            # Try to parse as datetime
            try {
                $parsed = [DateTime]::Parse($TimeSpec)
                return $parsed.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            } catch {
                Write-Error "Could not parse time: $TimeSpec"
                Write-Host "Use ISO format (2024-12-01T10:00:00Z) or relative (in 2 hours)"
                exit 1
            }
        }
    }
}

# Convert time specification
$scheduleTime = Convert-ToISODateTime -TimeSpec $At

# Get the post.ps1 script path
$scriptRoot = $PSScriptRoot
$postScript = Join-Path $scriptRoot "post.ps1"

# Build parameters
$params = @{
    Content = $Content
    Platforms = $Platforms
    Schedule = $scheduleTime
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
Write-Host " SOCIAL SLASH - Scheduled Post" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Scheduled for: $scheduleTime" -ForegroundColor Yellow
Write-Host "Platforms: $($Platforms -join ', ')" -ForegroundColor White
Write-Host ""

# Execute post command with schedule
& $postScript @params
