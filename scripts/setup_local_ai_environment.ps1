$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv-ai\Scripts\python.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11 or 3.12 is required. Install it from https://www.python.org/downloads/windows/"
}
if (-not (Test-Path $VenvPython)) {
    & python -m venv (Join-Path $RepoRoot ".venv-ai")
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv-ai." }
}
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip." }
& $VenvPython -m pip install -r (Join-Path $RepoRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install the base dependencies." }

Write-Host ""
Write-Host "NEXT: install a CUDA-enabled PyTorch build inside the new .venv-ai environment."
Write-Host "1. Open https://pytorch.org/get-started/locally/ and select Windows / Pip / Python / the CUDA version matching your installed NVIDIA driver."
Write-Host "2. Copy the generated PyTorch command and run it in PowerShell, replacing the Python executable with:"
Write-Host $VenvPython
Write-Host "3. Then return to this script and continue with requirements-ai.txt."
Write-Host ""
$answer = Read-Host "Have you installed CUDA-enabled PyTorch into .venv-ai? (Y/N)"
if ($answer -notmatch '^(Y|YES)$') {
    Write-Host "Setup paused. Run this script again after installing the CUDA-enabled PyTorch build."
    exit 0
}

& $VenvPython -c "import torch; print('Torch:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
if ($LASTEXITCODE -ne 0) { throw "Could not inspect PyTorch; verify installation." }
& $VenvPython -c "import torch; assert torch.cuda.is_available(), 'CUDA is not available in this Python environment.'"
if ($LASTEXITCODE -ne 0) {
    throw "No CUDA GPU visible to PyTorch. Check GPU drivers and the selected wheel. This workflow will not switch to a paid API."
}
& $VenvPython -m pip install -r (Join-Path $RepoRoot "requirements-ai.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install local AI dependencies." }
& $VenvPython -c "import torch, diffusers; print('Ready for local FLUX.1-schnell:', diffusers.__version__, torch.cuda.get_device_name(0))"
if ($LASTEXITCODE -ne 0) { throw "Local AI environment validation failed." }

Write-Host ""
Write-Host "Local AI environment is ready."
Write-Host "First image-generation run will download the model weights to the local Hugging Face cache (several gigabytes)."
Write-Host "No hosted inference API or generation credits are used."
