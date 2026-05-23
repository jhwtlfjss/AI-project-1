param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $ProjectDir
& $Python clients\desktop\app\ai_project1_client.py
