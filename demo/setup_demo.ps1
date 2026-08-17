$ErrorActionPreference = "Stop"

$DemoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $DemoRoot
$DemoPython = Join-Path $DemoRoot ".venv\Scripts\python.exe"

Write-Host "Preparing isolated demo environment..." -ForegroundColor Cyan
Write-Host "Demo root: $DemoRoot" -ForegroundColor DarkGray
Write-Host "Project root: $ProjectRoot" -ForegroundColor DarkGray

if (-not (Test-Path $DemoPython)) {
    Write-Host "Creating demo\.venv..." -ForegroundColor Yellow
    python -m venv (Join-Path $DemoRoot ".venv")
}

if (-not (Test-Path $DemoPython)) {
    throw "Could not create demo virtual environment at $DemoRoot\.venv"
}

Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $DemoPython -m pip install --upgrade pip

$Requirements = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path $Requirements) {
    Write-Host "Installing project runtime dependencies from requirements.txt..." -ForegroundColor Cyan
    & $DemoPython -m pip install -r $Requirements
}
else {
    Write-Host "requirements.txt was not found; installing required runtime packages directly..." -ForegroundColor Yellow
    & $DemoPython -m pip install `
        "mysql-connector-python==9.4.0" `
        "numpy==2.3.3" `
        "pandas==2.3.3" `
        "plotly==6.3.1" `
        "PyMySQL==1.1.2" `
        "requests==2.32.5" `
        "SQLAlchemy==2.0.43" `
        "streamlit==1.57.0"
}

Write-Host "Checking imports..." -ForegroundColor Cyan
& $DemoPython -c "import streamlit, sqlalchemy, pandas, numpy, plotly, requests, pymysql, mysql.connector; print('Demo runtime dependencies OK')"

Write-Host ""
Write-Host "Demo environment ready." -ForegroundColor Green
Write-Host "Next: .\demo\validate_demo.ps1" -ForegroundColor Green
