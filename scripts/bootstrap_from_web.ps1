param(
  [string]$Python = "python",
  [string]$LearningConfig = "configs\learning_sources.json",
  [string]$Knowledge = "data\knowledge.jsonl",
  [string]$State = "data\learning_state.json",
  [string]$RawOut = "data\raw\learned_web_corpus.jsonl",
  [string]$TrainConfig = "configs\tiny_nvidia.json",
  [switch]$Train
)

$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $ProjectDir

$PythonCommand = Get-Command $Python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
  Write-Error "Python command not found: $Python. Install Python, add it to PATH, or pass -Python `"C:\path\to\python.exe`"."
  exit 1
}

function Stop-IfFailed {
  param([string]$StepName)
  if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Error "$StepName failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
  }
}

Write-Host "AI Project 1 web bootstrap"
Write-Host "This collects allowed web sources, saves local knowledge, then prepares train.bin/val.bin."
Write-Host ""

Write-Host "1/3 Learning from configured web sources..."
& $Python scripts\autolearn.py --config $LearningConfig --knowledge $Knowledge --state $State --force
Stop-IfFailed "autolearn"

Write-Host ""
Write-Host "2/3 Converting local knowledge into training JSONL..."
& $Python scripts\knowledge_to_training.py --knowledge $Knowledge --out $RawOut --mode both
Stop-IfFailed "knowledge_to_training"

Write-Host ""
Write-Host "3/3 Preparing tokenizer data..."
& $Python scripts\prepare_data.py --raw-dir data\raw --out-dir data
Stop-IfFailed "prepare_data"

if ($Train) {
  Write-Host ""
  Write-Host "4/4 Training the local model..."
  & $Python scripts\train.py --config $TrainConfig
  Stop-IfFailed "train"
  Write-Host ""
  Write-Host "Model checkpoint should be under runs\tiny-lover\ckpt.pt."
} else {
  Write-Host ""
  Write-Host "Training data is ready."
  Write-Host "Next step:"
  Write-Host "$Python scripts\train.py --config $TrainConfig"
}
