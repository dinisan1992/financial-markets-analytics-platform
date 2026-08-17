$ErrorActionPreference = "Stop"

$DemoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $DemoRoot
$DemoPython = Join-Path $DemoRoot ".venv\Scripts\python.exe"
$PreviousPythonPath = $env:PYTHONPATH

if (-not (Test-Path $DemoPython)) {
    Write-Host "The isolated demo environment does not exist yet." -ForegroundColor Yellow
    Write-Host "Creating it now..." -ForegroundColor Yellow
    & (Join-Path $DemoRoot "setup_demo.ps1")
}

$env:PYTHONPATH = "$DemoRoot;$ProjectRoot"
if ($PreviousPythonPath) {
    $env:PYTHONPATH = "$env:PYTHONPATH;$PreviousPythonPath"
}

Write-Host "Using isolated demo Python: $DemoPython" -ForegroundColor DarkGray

Push-Location $ProjectRoot
try {
    Write-Host "[0/6] Runtime dependency check" -ForegroundColor Cyan
    & $DemoPython -c "import streamlit, sqlalchemy, pandas, numpy, plotly, requests, pymysql, mysql.connector; print('Runtime dependencies OK')"

    Write-Host "[1/6] Demo unit tests" -ForegroundColor Cyan
    & $DemoPython "$DemoRoot\tests\test_demo_mode.py"

    Write-Host "[2/6] Project-aware demo smoke test" -ForegroundColor Cyan
    & $DemoPython "$DemoRoot\project_scripts\diagnostics\demo_mode_smoke.py"

    Write-Host "[3/6] Demo Streamlit page test" -ForegroundColor Cyan
    & $DemoPython "$DemoRoot\project_scripts\diagnostics\validate_demo_pages.py"

    Write-Host "[4/6] Compile demo files" -ForegroundColor Cyan
    & $DemoPython -m compileall -q `
        "$DemoRoot\demo" `
        "$DemoRoot\streamlit_demo.py" `
        "$DemoRoot\project_scripts\diagnostics\demo_mode_smoke.py" `
        "$DemoRoot\project_scripts\diagnostics\validate_demo_pages.py" `
        "$DemoRoot\tests\test_demo_mode.py"

    Write-Host "[5/6] Basic application import check" -ForegroundColor Cyan
    & $DemoPython -c "import sys; sys.path.insert(0, r'$DemoRoot'); sys.path.insert(1, r'$ProjectRoot'); from demo.runtime import activate_demo_mode; activate_demo_mode(); import app_pages.asset_explorer, app_pages.correlations, app_pages.fed_macro, app_pages.euro_macro; print('Application imports OK')"

    Write-Host ""
    Write-Host "Demo validation passed." -ForegroundColor Green
}
finally {
    Pop-Location
    $env:PYTHONPATH = $PreviousPythonPath
}
