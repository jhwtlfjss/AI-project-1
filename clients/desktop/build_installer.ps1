param(
  [string]$InnoSetupCompiler = "iscc"
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $ProjectDir

$ExePath = Join-Path $ProjectDir "dist\AI Project 1.exe"
if (!(Test-Path $ExePath)) {
  Write-Host "Executable is missing. Build it first:"
  Write-Host "powershell -ExecutionPolicy Bypass -File clients\desktop\build_exe.ps1 -InstallPyInstaller"
  exit 1
}

if (!(Get-Command $InnoSetupCompiler -ErrorAction SilentlyContinue)) {
  Write-Host "Inno Setup compiler was not found."
  Write-Host "Install Inno Setup, then rerun this script."
  exit 1
}

& $InnoSetupCompiler clients\desktop\installer.iss
Write-Host "Installer:"
Write-Host (Join-Path $ProjectDir "dist\AIProject1Setup.exe")

