param(
  [string]$Gradle = ".\gradlew.bat"
)

$ErrorActionPreference = "Stop"
$AndroidDir = (Resolve-Path "$PSScriptRoot").Path
Set-Location $AndroidDir

if (Test-Path $Gradle) {
  & $Gradle assembleDebug
} elseif (Get-Command gradle -ErrorAction SilentlyContinue) {
  gradle assembleDebug
} else {
  Write-Host "Gradle was not found."
  Write-Host "Open clients\android in Android Studio and use Build > Build APK(s),"
  Write-Host "or install Gradle / generate a Gradle wrapper, then rerun this script."
  exit 1
}

Write-Host "APK:"
Write-Host (Join-Path $AndroidDir "app\build\outputs\apk\debug\app-debug.apk")

