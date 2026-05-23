param(
  [string]$Python = "python",
  [string]$Config = "configs\tiny_3080.json",
  [string]$Checkpoint = "runs\tiny-lover\ckpt.pt",
  [string]$OutDir = "",
  [int]$AdditionalSteps = 2000,
  [switch]$Promote,
  [switch]$Train
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $ProjectDir

Write-Host "Step 1: Build review queue from conversation logs."
& $Python scripts\build_review_queue.py --append

if (!$Promote) {
  Write-Host ""
  Write-Host "Review data\review_queue.jsonl and change approved=false to approved=true for examples you like."
  Write-Host "Then run:"
  Write-Host "powershell -ExecutionPolicy Bypass -File scripts\growth_cycle.ps1 -Promote"
  exit 0
}

Write-Host "Step 2: Promote approved samples."
& $Python scripts\promote_review.py

Write-Host "Step 3: Rebuild train/val data."
& $Python scripts\prepare_data.py --raw-dir data\raw --out-dir data

if (!$Train) {
  Write-Host ""
  Write-Host "Training data is ready. To continue training, run:"
  Write-Host "powershell -ExecutionPolicy Bypass -File scripts\growth_cycle.ps1 -Promote -Train"
  exit 0
}

Write-Host "Step 4: Continue training."
$ArgsList = @("scripts\train.py", "--config", $Config, "--init-from", $Checkpoint, "--additional-steps", "$AdditionalSteps")
if ($OutDir -ne "") {
  $ArgsList += @("--out-dir", $OutDir)
}
& $Python @ArgsList
