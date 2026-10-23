param(
    [string]$Destination = (Join-Path $env:USERPROFILE "Documents\ARCSTUDIO91\DailyPacks")
)

$ErrorActionPreference = "Stop"
$Repo = "artclass11/ARCSTUDIO"
$Workflow = "daily-publish.yml"
$ArtifactName = "ARCSTUDIO91-Daily-Pack"
$LogDir = Join-Path $env:USERPROFILE "Documents\ARCSTUDIO91\logs"
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "daily-pack-download.log"

function Write-Log([string]$Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required. Install it from https://cli.github.com and run 'gh auth login' once."
}
& gh auth status --hostname github.com *> $null
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not signed in. Run 'gh auth login' in a terminal and then retry."
}

$json = & gh run list --repo $Repo --workflow $Workflow --status completed --limit 60 --json databaseId,createdAt,conclusion
if ($LASTEXITCODE -ne 0) { throw "Could not list ARCSTUDIO91 Actions runs. Check network and GitHub CLI login." }
$runs = @($json | ConvertFrom-Json)
if ($runs.Count -eq 0) { throw "No completed daily workflow runs were found yet." }

$downloaded = 0
$skippedExisting = 0
$skippedUnavailable = 0
foreach ($run in $runs) {
    $runId = [string]$run.databaseId
    $runDay = [DateTimeOffset]::Parse($run.createdAt).ToLocalTime().ToString("yyyy-MM-dd")
    $target = Join-Path $Destination $runDay

    # Avoid downloading the same day's pack repeatedly.
    if ((Test-Path (Join-Path $target "package_manifest.json")) -and
        (Test-Path (Join-Path $target "reel.mp4"))) {
        $skippedExisting++
        continue
    }

    $temp = Join-Path $env:TEMP ("arcstudio91-pack-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $temp -Force | Out-Null
    try {
        & gh run download $runId --repo $Repo --name $ArtifactName --dir $temp *> $null
        if ($LASTEXITCODE -ne 0) {
            $skippedUnavailable++
            continue
        }

        $manifestPath = Get-ChildItem -Path $temp -Filter "package_manifest.json" -File -Recurse |
            Select-Object -First 1 -ExpandProperty FullName
        if (-not $manifestPath) {
            $skippedUnavailable++
            continue
        }
        $payloadRoot = Split-Path -Parent $manifestPath
        $manifest = Get-Content -Raw -Path $manifestPath | ConvertFrom-Json
        $packDay = [string]$manifest.date
        if ($packDay -notmatch '^\d{4}-\d{2}-\d{2}$') {
            Write-Log "Skipped run $runId because its manifest date was invalid."
            $skippedUnavailable++
            continue
        }
        $target = Join-Path $Destination $packDay
        if ((Test-Path (Join-Path $target "package_manifest.json")) -and
            (Test-Path (Join-Path $target "reel.mp4"))) {
            $skippedExisting++
            continue
        }

        # Validate checksums from the manifest before accepting the downloaded pack.
        $badFiles = @()
        foreach ($entry in $manifest.files) {
            $file = Join-Path $payloadRoot ([string]$entry.name)
            if (-not (Test-Path $file)) {
                $badFiles += "$($entry.name): missing"
                continue
            }
            $actualHash = (Get-FileHash -Algorithm SHA256 -Path $file).Hash.ToLowerInvariant()
            if ($actualHash -ne ([string]$entry.sha256).ToLowerInvariant()) {
                $badFiles += "$($entry.name): SHA-256 mismatch"
            }
        }
        if ($badFiles.Count -gt 0) {
            Write-Log "Rejected run $runId ($packDay): $($badFiles -join '; ')"
            $skippedUnavailable++
            continue
        }

        New-Item -ItemType Directory -Path $target -Force | Out-Null
        Get-ChildItem -Path $payloadRoot -Force | Copy-Item -Destination $target -Recurse -Force
        $status = [ordered]@{
            downloaded_at = (Get-Date).ToString("o")
            github_repository = $Repo
            workflow_run_id = $runId
            package_date = $packDay
            sha256_checks = "passed"
        }
        $status | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $target "local_download_status.json") -Encoding UTF8
        Write-Log "Saved and verified pack for $packDay to $target"
        $downloaded++
    }
    catch {
        Write-Log "Run $runId download attempt failed: $($_.Exception.Message)"
        $skippedUnavailable++
    }
    finally {
        Remove-Item -Path $temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Log "Complete. New packs: $downloaded; already present: $skippedExisting; unavailable/failed: $skippedUnavailable."
if ($downloaded -eq 0 -and $skippedExisting -eq 0) {
    throw "No daily content packs could be downloaded. The workflow may not have produced an artifact yet; check https://github.com/artclass11/ARCSTUDIO/actions"
}
