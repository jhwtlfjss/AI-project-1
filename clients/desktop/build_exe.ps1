param(
  [string]$Python = "python",
  [switch]$InstallPyInstaller
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $ProjectDir
$IconPath = Join-Path $ProjectDir "assets\app_icon.ico"
$IconPngPath = Join-Path $ProjectDir "assets\app_icon.png"
$ExePath = Join-Path $ProjectDir "dist\AI Project 1.exe"

if (!(Test-Path $IconPath) -or !(Test-Path $IconPngPath)) {
  & $Python scripts\generate_app_icon.py
}

if (Test-Path $ExePath) {
  Remove-Item -LiteralPath $ExePath -Force
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
Write-Host $ExePath

Add-Type -AssemblyName System.Drawing
$ExtractedIcon = [System.Drawing.Icon]::ExtractAssociatedIcon($ExePath)
if ($null -eq $ExtractedIcon) {
  throw "Executable was built, but Windows could not extract an associated icon from it."
}
Write-Host "Embedded icon:"
Write-Host "$($ExtractedIcon.Width)x$($ExtractedIcon.Height)"

$IconRefresh = Join-Path $env:WINDIR "System32\ie4uinit.exe"
if (Test-Path $IconRefresh) {
  & $IconRefresh -ClearIconCache 2>$null
}
