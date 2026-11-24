<#
.SYNOPSIS
    Installer script for NanoVault Sanctuary v1.3.0 on Windows.
#>
[CmdletBinding()]
param (
    [string]$PythonVersion = "3.12",
    [string]$VenvDir = ".venv"
)

$ErrorActionPreference = "Stop"
$AppName = "NanoVault Sanctuary"
$Version = "1.3.0"

function Write-Info($Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Warn($Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Err($Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Ensure-Winget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Err "winget was not found. Please install 'App Installer' from the Microsoft Store or install wget and Python manually."
    }
}

function Ensure-Wget {
    if (Get-Command wget.exe -ErrorAction SilentlyContinue) {
        Write-Info "wget found: $((wget.exe --version | Select-Object -First 1))"
        return
    }

    Write-Warn "wget not found. Installing via winget..."
    Ensure-Winget
    winget install --id GNU.Wget2 --exact --accept-source-agreements --accept-package-agreements `
        || winget install --id JernejSimoncic.Wget --exact --accept-source-agreements --accept-package-agreements

    # Refresh PATH for current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")

    if (-not (Get-Command wget.exe -ErrorAction SilentlyContinue)) {
        Write-Warn "wget installed, but you may need to restart your terminal so PATH updates take effect."
    } else {
        Write-Info "wget ready: $((wget.exe --version | Select-Object -First 1))"
    }
}

function Test-CompatiblePython([string]$ExePath) {
    if (-not (Get-Command $ExePath -ErrorAction SilentlyContinue)) {
        return $false
    }
    & $ExePath -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Python {
    $candidates = @("python", "python3")
    foreach ($cmd in $candidates) {
        if (Test-CompatiblePython $cmd) {
            $pyFull = (Get-Command $cmd).Source
            $verText = & $pyFull --version
            Write-Info "Using compatible Python: $pyFull ($verText)"
            return $pyFull
        }
    }

    Write-Warn "Compatible Python (3.10+) not found. Installing Python $PythonVersion via winget..."
    Ensure-Winget
    winget install --id "Python.Python.$PythonVersion" --exact --accept-source-agreements --accept-package-agreements

    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")

    foreach ($cmd in @("py", "python", "python3")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            if ($cmd -eq "py") {
                $pyFull = (& py -$PythonVersion -c "import sys; print(sys.executable)").Trim()
            } else {
                $pyFull = (Get-Command $cmd).Source
            }
            if ($pyFull -and (Test-CompatiblePython $pyFull)) {
                Write-Info "Python ready: $pyFull ($(& $pyFull --version))"
                return $pyFull
            }
        }
    }

    Write-Err "Python installation completed, but no 3.10+ executable was detected in PATH. Open a new PowerShell window and run this script again."
}

function Setup-VenvAndDeps([string]$PythonExe) {
    Write-Info "Creating virtual environment in '$VenvDir'..."
    & $PythonExe -m venv $VenvDir

    $venvPython = Join-Path $PSScriptRoot "$VenvDir\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        $venvPython = Join-Path (Get-Location) "$VenvDir\Scripts\python.exe"
    }

    & $venvPython -m pip install --upgrade pip

    if (Test-Path "requirements.txt") {
        Write-Info "Installing dependencies from requirements.txt..."
        & $venvPython -m pip install -r requirements.txt
    } elseif (Test-Path "pyproject.toml") {
        Write-Info "Installing project dependencies from pyproject.toml..."
        & $venvPython -m pip install -e .
    } else {
        Write-Warn "No requirements.txt or pyproject.toml found; skipping package install."
    }
}

function Show-LaunchInstructions {
    Write-Host ""
    Write-Host "====================================================================" -ForegroundColor Green
    Write-Host "  $AppName v$Version — Installation Complete" -ForegroundColor Green
    Write-Host "====================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start the server:"
    Write-Host ""
    Write-Host "  1. Activate the virtual environment:"
    Write-Host "     .\$VenvDir\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "  2. Launch the FastAPI backend:"
    Write-Host "     uvicorn main:app --host 127.0.0.1 --port 8000 --reload" -ForegroundColor White
    Write-Host "     (Adjust 'main:app' or port if your entry module uses a different name.)"
    Write-Host ""
    Write-Host "  3. Open your browser to:"
    Write-Host "     http://127.0.0.1:8000" -ForegroundColor White
    Write-Host ""
    Write-Host "====================================================================" -ForegroundColor Green
}

Write-Info "Starting $AppName v$Version Windows installer..."
Ensure-Wget
$pythonExe = Ensure-Python
Setup-VenvAndDeps $pythonExe
Show-LaunchInstructions