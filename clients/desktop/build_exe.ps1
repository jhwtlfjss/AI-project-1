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
$SourcePath = Join-Path $ProjectDir "clients\desktop\winforms\AiProject1Client.cs"

if (!(Test-Path $IconPath) -or !(Test-Path $IconPngPath)) {
  & $Python scripts\generate_app_icon.py
}

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectDir "dist") | Out-Null
if (Test-Path $ExePath) {
  Remove-Item -LiteralPath $ExePath -Force
}

$Csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (!(Test-Path $Csc)) {
  $Csc = "C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
}
if (!(Test-Path $Csc)) {
  throw ".NET Framework C# compiler was not found. This native desktop build does not use Tkinter."
}

& $Csc `
  /nologo `
  /target:winexe `
  /out:"$ExePath" `
  /win32icon:"$IconPath" `
  /reference:System.dll `
  /reference:System.Core.dll `
  /reference:System.Drawing.dll `
  /reference:System.Web.Extensions.dll `
  /reference:System.Windows.Forms.dll `
  "$SourcePath"

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
