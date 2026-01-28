# LMBench One-Command Installer for Windows
Write-Host "🚀 Starting LMBench Installation..." -ForegroundColor Cyan

# 1. Check for Python
$pythonExists = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonExists) {
    Write-Host "Python not found. Installing via winget..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install Python via winget. Please install it manually from python.org" -ForegroundColor Red
        exit
    }
    # Refresh PATH for the current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# 2. Install LMBench
Write-Host "Installing LMBench dependencies..." -ForegroundColor Blue
python -m pip install --upgrade pip
python -m pip install -e .

Write-Host "`n✅ Installation Complete!" -ForegroundColor Green
Write-Host "You can now run LMBench using: " -NoNewline
Write-Host "lmbench --help" -ForegroundColor Cyan
