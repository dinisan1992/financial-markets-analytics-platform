$ErrorActionPreference = "Stop"

$DemoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $DemoRoot
$DemoPython = Join-Path $DemoRoot ".venv\Scripts\python.exe"
$PreviousPythonPath = $env:PYTHONPATH

if (-not (Test-Path $DemoPython)) {
    & (Join-Path $DemoRoot "setup_demo.ps1")
}

$env:PYTHONPATH = "$DemoRoot;$ProjectRoot"
if ($PreviousPythonPath) {
    $env:PYTHONPATH = "$env:PYTHONPATH;$PreviousPythonPath"
}

Push-Location $ProjectRoot
try {
    Write-Host "[1/3] Public snapshot integrity" -ForegroundColor Cyan
    & $DemoPython "$DemoRoot\validate_public_snapshot.py"

    Write-Host "[2/3] Compile snapshot demo" -ForegroundColor Cyan
    & $DemoPython -m compileall -q `
        "$DemoRoot\demo" `
        "$DemoRoot\streamlit_demo.py" `
        "$DemoRoot\validate_public_snapshot.py"

    Write-Host "[3/3] Application import safety" -ForegroundColor Cyan
    & $DemoPython -c "import sys; sys.path.insert(0, r'$DemoRoot'); sys.path.insert(1, r'$ProjectRoot'); from demo.runtime import activate_demo_mode; activate_demo_mode(); import app_pages.asset_explorer, app_pages.correlations, app_pages.fed_macro, app_pages.euro_macro; print('Application imports OK')"

    Write-Host ""
    Write-Host "Exact-snapshot demo validation passed." -ForegroundColor Green
}
finally {
    Pop-Location
    $env:PYTHONPATH = $PreviousPythonPath
}
