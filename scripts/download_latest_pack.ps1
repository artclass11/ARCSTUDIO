param(
    [string]$Destination = (Join-Path $env:USERPROFILE "Documents\ARCSTUDIO91\DailyPacks")
)

$ErrorActionPreference = "Stop"
$Repo = "artclass11/ARCSTUDIO"
$Workflow = "daily-publish.yml"
$ArtifactName = "ARCSTUDIO91-Cloud-Source-Pack"
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
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv-ai\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { $VenvPython = (Get-Command python -ErrorAction Stop).Source }
& git -C $RepoRoot pull --ff-only
if ($LASTEXITCODE -ne 0) {
    throw "Could not update the ARCSTUDIO scripts. Ensure the cloned repo is clean, then run git pull --ff-only."
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
    $runDay = [DateTimeOffset]::Parse($run.createdAt).UtcDateTime.ToString("yyyy-MM-dd")
    $target = Join-Path $Destination $runDay

    # Avoid downloading the same day's pack repeatedly.
    if ((Test-Path (Join-Path $target "package_manifest.json")) -and
        (Test-Path (Join-Path $target "reel.mp4"))) {
        $skippedExisting++
        continue
    }

    $temp = Join-Path $env:TEMP ("arcstudio91-pack-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $temp -Force | Out-Null
    $processingStarted = $false
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
        if ($packDay -notmatch '^\d{4}-\d{2}-\d{2}
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

        # Treat the GitHub artifact as a concept seed only. It is NOT a ready-to-post pack.
        # Final images and Reel must be rendered locally with the free open-weight model.
        $stagePack = Join-Path $Destination ($packDay + ".processing")
        if (Test-Path $stagePack) { Remove-Item -Path $stagePack -Recurse -Force }
        New-Item -ItemType Directory -Path $stagePack -Force | Out-Null
        Get-ChildItem -Path $payloadRoot -Force | Copy-Item -Destination $stagePack -Recurse -Force

        $processingStarted = $true
        $previousOutput = $env:ARCSTUDIO_OUTPUT_DIR
        $env:ARCSTUDIO_OUTPUT_DIR = $stagePack
        try {
            Push-Location $RepoRoot
            & $VenvPython -c "import torch, diffusers; assert torch.cuda.is_available(), 'No CUDA GPU available'"
            if ($LASTEXITCODE -ne 0) {
                throw "Free local AI setup is incomplete. Install CUDA-enabled PyTorch and requirements-ai.txt; no paid fallback is permitted."
            }
            & $VenvPython scripts/generate_free_ai_pack.py
            if ($LASTEXITCODE -ne 0) { throw "Local FLUX.1-schnell artwork generation failed; no pack marked ready." }
            & $VenvPython scripts/generate_reel.py
            if ($LASTEXITCODE -ne 0) { throw "Marathi-first Reel rendering failed; no pack marked ready." }
            & $VenvPython scripts/package_daily.py
            if ($LASTEXITCODE -ne 0) { throw "Final AI package quality checks failed; no pack marked ready." }
        }
        finally {
            Pop-Location
            if ($null -eq $previousOutput) {
                Remove-Item Env:ARCSTUDIO_OUTPUT_DIR -ErrorAction SilentlyContinue
            } else {
                $env:ARCSTUDIO_OUTPUT_DIR = $previousOutput
            }
        }

        $finalManifestPath = Join-Path $stagePack "package_manifest.json"
        if (-not (Test-Path $finalManifestPath)) {
            throw "Final manifest missing after local AI processing."
        }
        $finalManifest = Get-Content -Raw -Path $finalManifestPath | ConvertFrom-Json
        foreach ($entry in $finalManifest.files) {
            $file = Join-Path $stagePack ([string]$entry.name)
            if (-not (Test-Path $file)) { throw "Final AI pack is missing $($entry.name)." }
            $actualHash = (Get-FileHash -Algorithm SHA256 -Path $file).Hash.ToLowerInvariant()
            if ($actualHash -ne ([string]$entry.sha256).ToLowerInvariant()) {
                throw "Final AI pack SHA-256 check failed for $($entry.name)."
            }
        }
        $aiManifestPath = Join-Path $stagePack "ai_generation_manifest.json"
        if (-not (Test-Path $aiManifestPath)) {
            throw "AI provenance manifest missing; refusing to save as ready-to-post."
        }
        $aiManifest = Get-Content -Raw -Path $aiManifestPath | ConvertFrom-Json
        if ($aiManifest.model_id -ne "black-forest-labs/FLUX.1-schnell" -or
            $aiManifest.mode -ne "local open-weight inference; no paid hosted API") {
            throw "AI provenance check failed; refusing to save as ready-to-post."
        }

        if (Test-Path $target) { Remove-Item -Path $target -Recurse -Force }
        Move-Item -Path $stagePack -Destination $target
        $status = [ordered]@{
            downloaded_at = (Get-Date).ToString("o")
            github_repository = $Repo
            workflow_run_id = $runId
            package_date = $packDay
            sha256_checks = "passed for cloud concept seed and final package QA"
            ai_model = $aiManifest.model_id
            ai_model_license = $aiManifest.model_license
            local_render_status = "verified by package_daily.py"
            publish_status = "not published"
        }
        $status | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $target "local_download_status.json") -Encoding UTF8

        # Create one convenient ZIP alongside the complete dated folder.
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zipPath = Join-Path $Destination ("ARCSTUDIO91_Daily_AI_Pack_" + $packDay + ".zip")
        if (Test-Path $zipPath) { Remove-Item -Path $zipPath -Force }
        [System.IO.Compression.ZipFile]::CreateFromDirectory($target, $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)
        $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
        try {
            $zipNames = @($zip.Entries | ForEach-Object { $_.FullName })
            foreach ($requiredName in @("reel.mp4", "reel_cover.jpg", "reel_caption.txt",
                                        "slide_01.jpg", "slide_02.jpg", "slide_03.jpg", "slide_04.jpg",
                                        "ai_generation_manifest.json")) {
                if ($zipNames -notcontains $requiredName) {
                    throw "Final daily ZIP is missing $requiredName."
                }
            }
        }
        finally {
            $zip.Dispose()
        }
        Write-Log "Saved AI-generated, verified folder for $packDay to $target"
        Write-Log "Created final daily ZIP: $zipPath"
        $downloaded++
    }
    catch {
        Write-Log "Run $runId download attempt failed: $($_.Exception.Message)"
        $skippedUnavailable++
        if ($processingStarted) {
            throw "Strict local AI rendering failed for concept seed $runDay. No older concept will be substituted."
        }
    }
    finally {
        Remove-Item -Path $temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Log "Complete. New packs: $downloaded; already present: $skippedExisting; unavailable/failed: $skippedUnavailable."
if ($downloaded -eq 0 -and $skippedExisting -eq 0) {
    throw "No final AI content packs could be downloaded. Check the cloud workflow and local GPU/model setup: https://github.com/artclass11/ARCSTUDIO/actions"
}
) {
            Write-Log "Skipped run $runId because its manifest date was invalid."
            $skippedUnavailable++
            continue
        }
        if ($packDay -ne $runDay) {
            Write-Log "Skipped run $runId because seed date $packDay does not match run date $runDay."
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

        # Treat the GitHub artifact as a concept seed only. It is NOT a ready-to-post pack.
        # Final images and Reel must be rendered locally with the free open-weight model.
        $stagePack = Join-Path $Destination ($packDay + ".processing")
        if (Test-Path $stagePack) { Remove-Item -Path $stagePack -Recurse -Force }
        New-Item -ItemType Directory -Path $stagePack -Force | Out-Null
        Get-ChildItem -Path $payloadRoot -Force | Copy-Item -Destination $stagePack -Recurse -Force

        $previousOutput = $env:ARCSTUDIO_OUTPUT_DIR
        $env:ARCSTUDIO_OUTPUT_DIR = $stagePack
        try {
            Push-Location $RepoRoot
            & $VenvPython -c "import torch, diffusers; assert torch.cuda.is_available(), 'No CUDA GPU available'"
            if ($LASTEXITCODE -ne 0) {
                throw "Free local AI setup is incomplete. Install CUDA-enabled PyTorch and requirements-ai.txt; no paid fallback is permitted."
            }
            & $VenvPython scripts/generate_free_ai_pack.py
            if ($LASTEXITCODE -ne 0) { throw "Local FLUX.1-schnell artwork generation failed; no pack marked ready." }
            & $VenvPython scripts/generate_reel.py
            if ($LASTEXITCODE -ne 0) { throw "Marathi-first Reel rendering failed; no pack marked ready." }
            & $VenvPython scripts/package_daily.py
            if ($LASTEXITCODE -ne 0) { throw "Final AI package quality checks failed; no pack marked ready." }
        }
        finally {
            Pop-Location
            if ($null -eq $previousOutput) {
                Remove-Item Env:ARCSTUDIO_OUTPUT_DIR -ErrorAction SilentlyContinue
            } else {
                $env:ARCSTUDIO_OUTPUT_DIR = $previousOutput
            }
        }

        $finalManifestPath = Join-Path $stagePack "package_manifest.json"
        if (-not (Test-Path $finalManifestPath)) {
            throw "Final manifest missing after local AI processing."
        }
        $finalManifest = Get-Content -Raw -Path $finalManifestPath | ConvertFrom-Json
        $aiManifestPath = Join-Path $stagePack "ai_generation_manifest.json"
        if (-not (Test-Path $aiManifestPath)) {
            throw "AI provenance manifest missing; refusing to save as ready-to-post."
        }
        $aiManifest = Get-Content -Raw -Path $aiManifestPath | ConvertFrom-Json
        if ($aiManifest.model_id -ne "black-forest-labs/FLUX.1-schnell" -or
            $aiManifest.mode -ne "local open-weight inference; no paid hosted API") {
            throw "AI provenance check failed; refusing to save as ready-to-post."
        }

        if (Test-Path $target) { Remove-Item -Path $target -Recurse -Force }
        Move-Item -Path $stagePack -Destination $target
        $status = [ordered]@{
            downloaded_at = (Get-Date).ToString("o")
            github_repository = $Repo
            workflow_run_id = $runId
            package_date = $packDay
            sha256_checks = "passed for cloud concept seed and final package QA"
            ai_model = $aiManifest.model_id
            ai_model_license = $aiManifest.model_license
            local_render_status = "verified by package_daily.py"
            publish_status = "not published"
        }
        $status | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $target "local_download_status.json") -Encoding UTF8
        Write-Log "Saved AI-generated, verified content pack for $packDay to $target"
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
    throw "No final AI content packs could be downloaded. Check the cloud workflow and local GPU/model setup: https://github.com/artclass11/ARCSTUDIO/actions"
}
