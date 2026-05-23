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
  $CommonPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
  )
  foreach ($Path in $CommonPaths) {
    if (Test-Path $Path) {
      $InnoSetupCompiler = $Path
      break
    }
  }
}

if (!(Test-Path $InnoSetupCompiler) -and !(Get-Command $InnoSetupCompiler -ErrorAction SilentlyContinue)) {
  Write-Host "Inno Setup compiler was not found. Falling back to the built-in .NET installer builder."
  & "$PSScriptRoot\build_dotnet_installer.ps1"
  exit $LASTEXITCODE
}

& $InnoSetupCompiler clients\desktop\installer.iss
Write-Host "Installer:"
Write-Host (Join-Path $ProjectDir "dist\AIProject1Setup.exe")
