param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidateSet('native','menu','hold','fault','target','rotation','suite','crash_before','crash_after')][string]$Test='native',
    [int]$Port=18959,
    [int]$Duration=600
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$workRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot 'work'))
$fixtureRoot=[IO.Path]::GetFullPath($OutputDirectory)
if (-not $fixtureRoot.StartsWith($workRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Project work output required.'}
if ($Port -eq 18944 -or $Port -lt 1024 -or $Port -gt 65535) {throw 'Isolated test port required.'}
if ($Duration -le 0) {throw 'Positive test duration required.'}
if (Test-Path -LiteralPath $fixtureRoot) {throw 'Use a new run directory; prior evidence is preserved.'}
$lock=$null
$oldDirectory=$env:CSTAMP_TEST_DIR
$oldPort=$env:CSTAMP_TEST_PORT
$bootstrap=(Join-Path $PSScriptRoot 'slicer_completion_bootstrap.py').Replace('\','/')
$started= [DateTime]::UtcNow
try {
    $lock=[IO.File]::Open((Join-Path $workRoot 'completion-fixture.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    $existing=@(Get-CimInstance Win32_Process -Filter "Name='SlicerApp-real.exe'" | Where-Object {$_.CommandLine.Replace('\','/').Contains($bootstrap)})
    if ($existing.Count) {throw 'An owned synthetic fixture is already running. Finish and close it before starting another.'}
    New-Item -ItemType Directory -Path $fixtureRoot | Out-Null
    $env:CSTAMP_TEST_DIR=$fixtureRoot.Replace('\','/')
    $env:CSTAMP_TEST_PORT=[string]$Port
    $slicerExecutable=Join-Path $env:LOCALAPPDATA 'slicer.org/3D Slicer 5.12.3/Slicer.exe'
    $launcher=Start-Process -FilePath $slicerExecutable -ArgumentList @('--no-splash','--python-script',$bootstrap) -WindowStyle Hidden -PassThru
    $deadline=[DateTime]::UtcNow.AddSeconds(90)
    $readyFile=Join-Path $fixtureRoot 'ready.json'
    while (-not (Test-Path -LiteralPath $readyFile)) {
        $errorFile=Join-Path $fixtureRoot 'startup-error.txt'
        if (Test-Path -LiteralPath $errorFile) {throw (Get-Content -LiteralPath $errorFile -Raw)}
        if ([DateTime]::UtcNow -gt $deadline) {throw 'Fixture readiness timed out.'}
        Start-Sleep -Milliseconds 200
    }
    Write-Output "Fixture ready: $fixtureRoot. Activate its returned Slicer window, then create foreground-ready.txt in this directory."
    $deadline=[DateTime]::UtcNow.AddSeconds(120)
    while (-not (Test-Path -LiteralPath (Join-Path $fixtureRoot 'foreground-ready.txt'))) {
        if ([DateTime]::UtcNow -gt $deadline) {throw 'Foreground preparation timed out; fixture will be closed.'}
        Start-Sleep -Milliseconds 200
    }
    $scripts=@{native='completion_native_test.py';menu='completion_menu_test.py';hold='completion_hold_binding_test.py';fault='completion_fault_test.py';target='completion_target_change_test.py';rotation='completion_staged_rotation.py';integrity='completion_integrity_test.py';crash_before='completion_slicer_crash_test.py';crash_after='completion_slicer_crash_test.py'}
    $pythonExecutable=Join-Path $projectRoot 'prototypes/cmos-motion-poc/.venv/Scripts/python.exe'
    $selectedTests=if($Test -eq 'suite'){@('native','hold','fault','integrity','target')}else{@($Test)}
    foreach($selectedTest in $selectedTests){
        $arguments=@((Join-Path $PSScriptRoot $scripts[$selectedTest]),$fixtureRoot)
        if($selectedTest -eq 'rotation'){$arguments+=@('--duration',[string]$Duration)}
        if($selectedTest -like 'crash_*'){$arguments+=@('--phase',($selectedTest -replace '^crash_',''),'--stage','inject')}
        & $pythonExecutable @arguments *> (Join-Path $fixtureRoot ($selectedTest+'-output.txt'))
        if($LASTEXITCODE -ne 0){throw "Test failed ($selectedTest, exit $LASTEXITCODE); see preserved output and result JSON."}
        if($selectedTest -like 'crash_*') {
            # Injection is only the first half: verify persistence in a new real process.
            $oldReady=Get-Content -LiteralPath $readyFile -Raw | ConvertFrom-Json
            $deadline=[DateTime]::UtcNow.AddSeconds(15)
            while(Get-Process -Id $oldReady.pid -ErrorAction SilentlyContinue) {
                if([DateTime]::UtcNow -gt $deadline){throw 'Injected Slicer did not exit; restart refused.'}
                Start-Sleep -Milliseconds 100
            }
            foreach($name in @('ready.json','fault-control.json','fault-ack.json')) {
                $source=Join-Path $fixtureRoot $name
                if(Test-Path -LiteralPath $source){Move-Item -LiteralPath $source -Destination (Join-Path $fixtureRoot ('before-restart-'+$name))}
            }
            $priorRestart=$env:CSTAMP_TEST_RESTART
            try {
                $env:CSTAMP_TEST_RESTART='1'
                Start-Process -FilePath $slicerExecutable -ArgumentList @('--no-splash','--python-script',$bootstrap) -WindowStyle Hidden | Out-Null
            } finally {$env:CSTAMP_TEST_RESTART=$priorRestart}
            $deadline=[DateTime]::UtcNow.AddSeconds(90)
            while(-not (Test-Path -LiteralPath $readyFile)) {
                if(Test-Path -LiteralPath (Join-Path $fixtureRoot 'startup-error.txt')){throw 'Restart bootstrap failed.'}
                if([DateTime]::UtcNow -gt $deadline){throw 'Restart readiness timed out.'}
                Start-Sleep -Milliseconds 200
            }
            Write-Output 'Restart ready. Activate the restarted synthetic window, then create restart-foreground-ready.txt.'
            $deadline=[DateTime]::UtcNow.AddSeconds(120)
            while(-not (Test-Path -LiteralPath (Join-Path $fixtureRoot 'restart-foreground-ready.txt'))) {
                if([DateTime]::UtcNow -gt $deadline){throw 'Restart foreground preparation timed out.'}
                Start-Sleep -Milliseconds 200
            }
            & $pythonExecutable (Join-Path $PSScriptRoot $scripts[$selectedTest]) $fixtureRoot --phase ($selectedTest -replace '^crash_','') --stage verify *> (Join-Path $fixtureRoot ($selectedTest+'-verify-output.txt'))
            if($LASTEXITCODE -ne 0){throw 'Crash restart verification failed; injection alone is not a pass.'}
            $verified=Get-Content -LiteralPath (Join-Path $fixtureRoot 'slicer-crash-results.json') -Raw | ConvertFrom-Json
            if($verified.passed -ne $true){throw 'Crash restart completion evidence missing.'}
        }
    }
    Write-Output "Test passed: $Test. Synthetic input in real Slicer; real-hand acceptance is separate."
} finally {
    $env:CSTAMP_TEST_DIR=$oldDirectory
    $env:CSTAMP_TEST_PORT=$oldPort
    if($lock){
        try {
            if(Test-Path -LiteralPath (Join-Path $fixtureRoot 'ready.json')) {
                & (Join-Path $PSScriptRoot 'close_completion_fixture.ps1') -OutputDirectory $fixtureRoot
            } else {
                # Readiness failed: only this launch's project bootstrap process is eligible.
                Get-CimInstance Win32_Process -Filter "Name='SlicerApp-real.exe'" | Where-Object {
                    $_.CreationDate.ToUniversalTime() -ge $started -and $_.CommandLine.Replace('\','/').Contains($bootstrap)
                } | ForEach-Object {Stop-Process -Id $_.ProcessId}
            }
        } finally {$lock.Dispose()}
    }
}
