$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot "backend\venv\Scripts\python.exe"
$Manage = Join-Path $RepoRoot "backend\manage.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Python venv not found at backend\venv\Scripts\python.exe" -ForegroundColor Yellow
    Write-Host "From repo root run:" -ForegroundColor Yellow
    Write-Host "  cd backend" -ForegroundColor Cyan
    Write-Host "  py -3.12 -m venv venv" -ForegroundColor Cyan
    Write-Host "  .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Cyan
    exit 1
}

& $VenvPython $Manage ensure_default_admin @args
