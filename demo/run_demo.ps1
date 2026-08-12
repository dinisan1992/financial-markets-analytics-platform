$ErrorActionPreference = "Stop"

$DemoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $DemoRoot
$DemoPython = Join-Path $DemoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $DemoPython)) {
    Write-Host "The isolated demo environment does not exist yet." -ForegroundColor Yellow
    Write-Host "Creating it now..." -ForegroundColor Yellow
    & (Join-Path $DemoRoot "setup_demo.ps1")
}

if (-not (Test-Path $DemoPython)) {
    throw "Demo Python was not found at $DemoPython"
}

Write-Host "Starting Financial Markets Analytics Platform - Demo" -ForegroundColor Cyan
Write-Host "Python: $DemoPython" -ForegroundColor DarkGray
Write-Host "No MySQL connection is required by the demo data backend." -ForegroundColor Yellow

Push-Location $ProjectRoot
try {
    & $DemoPython -m streamlit run "$DemoRoot\streamlit_demo.py"
}
finally {
    Pop-Location
}
