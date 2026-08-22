# Mitchell Universal 1-Click Installer for Windows
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install.ps1

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Mitchell Autonomous Multi-Agent Hive Installer  " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python 3 is not installed or not in PATH. Please install Python 3.10+."
    exit 1
}

# 2. Virtual Environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment in .\venv..." -ForegroundColor Yellow
    python -m venv venv
}

# 3. Activate and Install
Write-Host "Upgrading pip and installing Mitchell dependencies..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install --upgrade pip
& .\venv\Scripts\python.exe -m pip install -e ".[dev]"

# 4. Playwright Browsers
Write-Host "Installing Playwright Chromium browser..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m playwright install chromium

# 5. Initialize .env
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created default .env from .env.example" -ForegroundColor Green
    }
}

Write-Host "==================================================" -ForegroundColor Green
Write-Host "  Mitchell Installation Complete!                 " -ForegroundColor Green
Write-Host "  Run '.\venv\Scripts\mitchell studio' to start.  " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Green
