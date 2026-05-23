param(
  [string]$TaskName = "MyCompanionAI-AutoLearn",
  [string]$Python = "python",
  [string]$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path,
  [int]$IntervalMinutes = 720
)

$Action = New-ScheduledTaskAction `
  -Execute $Python `
  -Argument "scripts\autolearn.py --config configs\learning_sources.json --knowledge data\knowledge.jsonl --state data\learning_state.json --force" `
  -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
  -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)

$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Autonomous learning cycle for My Companion AI"

Write-Host "Registered task '$TaskName' every $IntervalMinutes minutes."

