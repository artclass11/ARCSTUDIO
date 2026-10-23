$ErrorActionPreference = "Stop"
$TaskName = "ARCSTUDIO91 Daily Content Pack Download"
$DownloadScript = Join-Path $PSScriptRoot "download_latest_pack.ps1"

if (-not (Test-Path $DownloadScript)) {
    throw "Could not find $DownloadScript. Keep this installer next to download_latest_pack.ps1."
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "Install GitHub CLI from https://cli.github.com first."
}
& gh auth status --hostname github.com *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Sign in once by running 'gh auth login' in PowerShell, then run this installer again."
}

$arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $DownloadScript + '"'
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At "8:35 AM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Download and verify the latest ARCSTUDIO91 daily Reel and carousel pack from GitHub Actions." -Force | Out-Null
Write-Host ""
Write-Host "Installed: $TaskName"
Write-Host "Runs daily at 08:35 local time, after the cloud build scheduled for about 08:07 India time."
Write-Host "Destination: $env:USERPROFILE\Documents\ARCSTUDIO91\DailyPacks\YYYY-MM-DD"
Write-Host "Your PC must be powered on, connected to the internet, and your Windows user signed in."
Write-Host "Run download_latest_pack.ps1 directly to test the task."
