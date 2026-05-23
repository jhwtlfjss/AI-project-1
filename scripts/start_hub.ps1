param(
  [string]$Python = "python",
  [string]$Checkpoint = "runs\tiny-lover\ckpt.pt",
  [int]$Port = 8765,
  [switch]$Https,
  [switch]$NoModel
)

$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $ProjectDir

if ($Https) {
  $CertPath = Join-Path $ProjectDir "data\certs\server.crt.pem"
  $KeyPath = Join-Path $ProjectDir "data\certs\server.key.pem"
  if (!(Test-Path $CertPath) -or !(Test-Path $KeyPath)) {
    powershell -ExecutionPolicy Bypass -File scripts\generate_self_signed_cert.ps1 | Out-Host
  }
}

$ArgsList = @("scripts\serve_lan.py", "--host", "0.0.0.0", "--port", "$Port", "--live-web")
if (!$NoModel) {
  $ArgsList += @("--checkpoint", $Checkpoint)
}
if ($Https) {
  $ArgsList += @("--ssl-cert", "data\certs\server.crt.pem", "--ssl-key", "data\certs\server.key.pem")
}

Write-Host "Starting My Companion AI hub on port $Port..."
Write-Host "Press Ctrl+C to stop."
& $Python @ArgsList

