param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $ProjectDir
& $Python scripts\desktop_client.py

