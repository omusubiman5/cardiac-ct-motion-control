param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$workRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'work')) + [IO.Path]::DirectorySeparatorChar
$fixtureRoot = [IO.Path]::GetFullPath($OutputDirectory)
if (-not $fixtureRoot.StartsWith($workRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Fixture output must stay within this project work directory.'
}
$readyFile = Join-Path $fixtureRoot 'ready.json'
$ready = Get-Content -LiteralPath $readyFile -Raw | ConvertFrom-Json
$fixturePid = [int]$ready.pid
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$fixturePid"
if (-not $process) { Write-Output 'Fixture already stopped.'; exit 0 }
$script = (Join-Path $projectRoot 'tools/slicer_completion_bootstrap.py').Replace('\','/')
if ($process.Name -ne 'SlicerApp-real.exe' -or -not $process.CommandLine.Replace('\','/').Contains($script)) {
    throw 'PID does not belong to this project synthetic fixture; refusing to stop it.'
}
$readyTime = (Get-Item -LiteralPath $readyFile).LastWriteTimeUtc
$created = $process.CreationDate.ToUniversalTime()
if ($created -gt $readyTime -or ($readyTime - $created).TotalSeconds -gt 120) {
    throw 'PID creation time does not match fixture readiness; refusing to stop a reused PID.'
}
Stop-Process -Id $fixturePid
[pscustomobject]@{StoppedFixturePid=$fixturePid; NormalSlicerTouched=$false}
