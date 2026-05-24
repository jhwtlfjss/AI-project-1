param(
  [string]$Python = "python",
  [string]$Checkpoint = "runs\tiny-lover\ckpt.pt",
  [int]$Port = 8765,
  [switch]$Https,
  [switch]$NoModel
)

$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $ProjectDir

$PythonCommand = Get-Command $Python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
  Write-Error "Python command not found: $Python. Install Python, add it to PATH, or pass -Python `"C:\path\to\python.exe`"."
  exit 1
}

if (!$NoModel) {
  $CheckpointPath = $Checkpoint
  if (![System.IO.Path]::IsPathRooted($CheckpointPath)) {
    $CheckpointPath = Join-Path $ProjectDir $CheckpointPath
  }
  if (!(Test-Path $CheckpointPath)) {
    Write-Warning "Model checkpoint not found: $Checkpoint"
    Write-Host "The Hub will still start, but chat replies will say the model is not loaded."
    Write-Host "Create it first with: python scripts\train.py --config configs\tiny_nvidia.json"
    Write-Host ""
    $NoModel = $true
  }
}

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
Write-Host "Client URL: $(if ($Https) { 'https' } else { 'http' })://<this-computer-ip>:$Port"
Write-Host "Token file: data\server_token.txt"
if ($NoModel) {
  Write-Host "Model: not loaded yet"
} else {
  Write-Host "Model: $Checkpoint"
}
Write-Host "Press Ctrl+C to stop."
& $Python @ArgsList
