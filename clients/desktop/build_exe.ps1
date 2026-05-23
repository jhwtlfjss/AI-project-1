param(
  [string]$Python = "python",
  [switch]$InstallPyInstaller
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $ProjectDir
$IconPath = Join-Path $ProjectDir "assets\app_icon.ico"
$IconPngPath = Join-Path $ProjectDir "assets\app_icon.png"

if (!(Test-Path $IconPath) -or !(Test-Path $IconPngPath)) {
  & $Python scripts\generate_app_icon.py
}

try {
  & $Python -m PyInstaller --version | Out-Null
} catch {
  if (!$InstallPyInstaller) {
    Write-Host "PyInstaller is not installed."
    Write-Host "Run:"
    Write-Host "powershell -ExecutionPolicy Bypass -File clients\desktop\build_exe.ps1 -InstallPyInstaller"
    exit 1
  }
  & $Python -m pip install pyinstaller
}

& $Python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "AI Project 1" `
  --icon "$IconPath" `
  --add-data "$IconPngPath;assets" `
  --add-data "$IconPath;assets" `
  --paths "$ProjectDir" `
  clients\desktop\app\ai_project1_client.py

Write-Host "Executable:"
Write-Host (Join-Path $ProjectDir "dist\AI Project 1.exe")
