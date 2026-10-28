param(
    [string]$ResultPath,
    [switch]$ObserveActualProcesses
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$workspace = 'C:\Projects\Cardiac-CT-Motion-Control'
$release = 'D:\Signed Releases'
$rows = @()
$functions = @()
$actual = @()
# Tests load only the local predicate AST. They never invoke release entry points,
# alter signatures, launch/stop applications, or write release pointers.
$cases = @(
    @{name='slicer'; command='SlicerApp-real.exe'; process='SlicerApp-real.exe'; expected=$true},
    @{name='absolute source'; command='python.exe C:\Projects\Cardiac-CT-Motion-Control\prototypes\cmos-motion-poc\app.py'; expected=$true},
    @{name='quoted source spaces'; command='"C:\Python Runtime\python.exe" "C:\Project Space\cmos-motion-poc\app.py"'; expected=$true},
    @{name='absolute payload'; command='python.exe "D:\Signed Releases\v1\payload\cmos-motion-poc\app.py"'; expected=$true},
    @{name='case forward slashes'; command='PYTHON.EXE D:/release/PAYLOAD/CMOS-MOTION-POC/APP.PY'; expected=$true},
    @{name='absolute replay'; command='python.exe D:\release\payload\cmos-motion-poc\replay_sequence.py'; expected=$true},
    @{name='component relative'; command='python.exe prototypes\cmos-motion-poc\app.py'; expected=$true},
    @{name='actual relative normal'; command='python.exe app.py --config C:\Projects\Cardiac-CT-Motion-Control\artifacts\cstamp\recognizer-standard.json --slicer-connect --trial-log C:\Projects\Cardiac-CT-Motion-Control\work\trial.jsonl'; expected=$true},
    @{name='relative suspicious connection'; command='python.exe app.py --slicer-connect'; expected=$true},
    @{name='dot relative connection'; command='python.exe .\app.py --slicer-connect'; expected=$true},
    @{name='relative replay connection'; command='python.exe replay_sequence.py --slicer-connect'; expected=$true},
    @{name='unbuffered relative'; command='python.exe -u app.py --slicer-connect'; expected=$true},
    @{name='python option value'; command='python.exe -X utf8 -W ignore --check-hash-based-pycs always app.py --slicer-connect'; expected=$true},
    @{name='python combined option'; command='python.exe -Xutf8 -Wignore app.py --slicer-connect'; expected=$true},
    @{name='cluster module following flag'; command='python.exe -Im app.py --slicer-connect'; expected=$false},
    @{name='cluster code following flag'; command='python.exe -uc app.py --slicer-connect'; expected=$false},
    @{name='cluster extended separate value'; command='python.exe -IX utf8 app.py --slicer-connect'; expected=$true},
    @{name='cluster extended attached value'; command='python.exe -IXutf8 app.py --slicer-connect'; expected=$true},
    @{name='cluster warning separate value'; command='python.exe -IW ignore app.py --slicer-connect'; expected=$true},
    @{name='cluster warning attached value'; command='python.exe -IWignore app.py --slicer-connect'; expected=$true},
    @{name='cluster module attached name'; command='python.exe -Immodule app.py --slicer-connect'; expected=$false},
    @{name='cluster code attached text'; command='python.exe -Icprint(1) app.py --slicer-connect'; expected=$false},
    @{name='lowercase x does not consume value'; command='python.exe -x app.py --slicer-connect'; expected=$true},
    @{name='cluster lowercase x does not consume value'; command='python.exe -Ix app.py --slicer-connect'; expected=$true},
    @{name='warning value contains module option character'; command='python.exe -IWi::ImportWarning app.py --slicer-connect'; expected=$true},
    @{name='extended value contains code option character'; command='python.exe -IXdev app.py --slicer-connect'; expected=$true},
    @{name='end options'; command='python.exe -- app.py --slicer-connect'; expected=$true},
    @{name='project config only'; command='python.exe app.py --config C:\Projects\Cardiac-CT-Motion-Control\artifacts\cstamp\recognizer-standard.json'; expected=$true},
    @{name='payload config equal'; command='python.exe app.py "--config=D:\Signed Releases\v1\payload\config\recognizer.json"'; expected=$true},
    @{name='source interpreter'; command='python.exe app.py'; executable='C:\Projects\Cardiac-CT-Motion-Control\prototypes\cmos-motion-poc\.venv\Scripts\python.exe'; expected=$true},
    @{name='payload interpreter'; command='python.exe app.py'; executable='D:\Signed Releases\v1\payload\recognizer-runtime\Scripts\python.exe'; expected=$true},
    @{name='pythonw'; command='pythonw.exe app.py --slicer-connect'; process='pythonw.exe'; expected=$true},
    @{name='generic unrelated'; command='python.exe app.py'; expected=$false},
    @{name='unrelated config'; command='python.exe app.py --config C:\OtherProject\config.json'; expected=$false},
    @{name='prefix sibling config'; command='python.exe app.py --config C:\Projects\Cardiac-CT-Motion-Control-extra\config.json'; expected=$false},
    @{name='absolute unrelated'; command='python.exe C:\OtherProject\app.py --slicer-connect'; expected=$false},
    @{name='path merely data'; command='python.exe other.py --input C:\Projects\Cardiac-CT-Motion-Control\prototypes\cmos-motion-poc\app.py'; expected=$false},
    @{name='relative merely data'; command='python.exe other.py app.py --slicer-connect'; expected=$false},
    @{name='code string'; command='python.exe -c "print(''cmos-motion-poc/app.py'')" --slicer-connect'; expected=$false},
    @{name='module string'; command='python.exe -m unittest cmos-motion-poc/app.py --slicer-connect'; expected=$false},
    @{name='stdin arguments'; command='python.exe - cmos-motion-poc/app.py --slicer-connect'; expected=$false},
    @{name='combined module'; command='python.exe -mpip app.py --slicer-connect'; expected=$false},
    @{name='flag merely quoted data'; command='python.exe app.py --label "test --slicer-connect text"'; expected=$false},
    @{name='different connect flag'; command='python.exe app.py --no-slicer-connect'; expected=$false},
    @{name='different extension'; command='python.exe C:\project\cmos-motion-poc\app.py.bak'; expected=$false},
    @{name='non-python'; command='node app.py --slicer-connect'; process='node.exe'; expected=$false},
    @{name='interpreter only'; command='python.exe'; expected=$false},
    @{name='no command'; command=$null; expected=$false},
    @{name='shell metacharacters as data'; command='python.exe app.py --label "$(Remove-Item x); & evil"'; expected=$false}
)
if ($ObserveActualProcesses) {
    $actual = @(Get-CimInstance Win32_Process -Filter "Name='SlicerApp-real.exe' OR Name='python.exe' OR Name='pythonw.exe'")
}
$actualRows = @()
foreach ($entry in @('activate_completion_release.ps1','start_completion_release.ps1')) {
    $path = Join-Path $projectRoot "tools/$entry"
    $tokens = $null; $parseErrors = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
    $function = @($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Test-CompletionInputProcess'}, $true))
    if ($function.Count -ne 1) { throw 'Exactly one predicate definition is required.' }
    $functions += $function[0].Extent.Text
    . ([scriptblock]::Create($function[0].Extent.Text))
    foreach ($case in $cases) {
        $name = if ($case.process) { $case.process } else { 'python.exe' }
        $process = [PSCustomObject]@{Name=$name;CommandLine=$case.command;ExecutablePath=$case.executable}
        $observed = Test-CompletionInputProcess -Process $process -WorkspaceRoot $workspace -ReleaseRoot $release
        $rows += [PSCustomObject]@{entry=$entry;name=$case.name;expected=$case.expected;observed=$observed;passed=($observed -eq $case.expected)}
    }
    foreach ($process in $actual) {
        $legacy = $process.Name -eq 'SlicerApp-real.exe' -or ($process.Name -match '^python(w)?\.exe$' -and $process.CommandLine -match '(?i)[\\/]cmos-motion-poc[\\/](app\.py|replay[^\\/\s"]*\.py)(?=["\s]|$)')
        $observed = Test-CompletionInputProcess -Process $process -WorkspaceRoot $workspace -ReleaseRoot $release
        if ($legacy -or $observed -or $process.ProcessId -in @(90380,81264)) {
            $actualRows += [PSCustomObject]@{entry=$entry;pid=$process.ProcessId;name=$process.Name;
                legacy_detected=$legacy;corrected_detected=$observed;command_line=$process.CommandLine;executable_path=$process.ExecutablePath}
        }
    }
}
if ($functions[0] -cne $functions[1]) { throw 'The two signed-entry predicates diverged.' }
$result = [PSCustomObject]@{kind='self-verification of pure process predicates and read-only CIM observation';
    timestamp_utc=[DateTime]::UtcNow.ToString('o');passed=(@($rows | Where-Object { -not $_.passed }).Count -eq 0);
    cases_per_entry=$cases.Count;checked=$rows.Count;rows=$rows;actual_processes=$actualRows;
    same_snapshot_for_legacy_and_corrected=$true;process_control_performed=$false;signature_gates_executed_or_bypassed=$false}
if ($ResultPath) {
    if (Test-Path -LiteralPath $ResultPath) { throw 'Evidence exists; use a new output path.' }
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ResultPath -Encoding utf8
}
[PSCustomObject]@{passed=$result.passed;checked=$result.checked;failed=@($rows | Where-Object { -not $_.passed });actual=$actualRows} | ConvertTo-Json -Depth 6
if (-not $result.passed) { exit 1 }
