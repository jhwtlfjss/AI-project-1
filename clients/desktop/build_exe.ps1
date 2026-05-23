param(
  [string]$Python = "python",
  [switch]$InstallPyInstaller
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $ProjectDir

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
  --paths "$ProjectDir" `
  clients\desktop\app\ai_project1_client.py

Write-Host "Executable:"
Write-Host (Join-Path $ProjectDir "dist\AI Project 1.exe")

