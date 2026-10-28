param(
    [Parameter(Mandatory=$true)][string]$ReleaseRoot,
    [Parameter(Mandatory=$true)][string]$SlicerExecutable,
    [string]$WorkspaceRoot = 'C:\Projects\Cardiac-CT-Motion-Control',
    [int]$CameraIndex = 1
)
function Test-CompletionInputProcess {
    param(
        [Parameter(Mandatory=$true)]$Process,
        [string]$WorkspaceRoot = '',
        [string]$ReleaseRoot = ''
    )
    if ($Process.Name -eq 'SlicerApp-real.exe') { return $true }
    if ($Process.Name -notmatch '^python(w)?\.exe$') { return $false }
    if ([string]::IsNullOrWhiteSpace([string]$Process.CommandLine)) { return $false }
    # Parse Windows quoting/backslashes as argv data; never evaluate command text.
    # This function is embedded in each signed entry point, with no unsigned
    # helper loaded before payload verification.
    if (-not ('CardiacCompletionProcessArguments' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class CardiacCompletionProcessArguments {
    [DllImport("shell32.dll", SetLastError=true)]
    static extern IntPtr CommandLineToArgvW([MarshalAs(UnmanagedType.LPWStr)] string value, out int count);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr pointer);
    public static string[] Split(string value) {
        int count;
        IntPtr pointer = CommandLineToArgvW(value, out count);
        if (pointer == IntPtr.Zero) throw new System.ComponentModel.Win32Exception();
        try {
            var result = new string[count];
            for (int index = 0; index < count; index++)
                result[index] = Marshal.PtrToStringUni(Marshal.ReadIntPtr(pointer, index * IntPtr.Size));
            return result;
        } finally { LocalFree(pointer); }
    }
}
'@
    }
    $processArguments = [CardiacCompletionProcessArguments]::Split([string]$Process.CommandLine)
    $argumentIndex = 1
    while ($argumentIndex -lt $processArguments.Count) {
        $argument = $processArguments[$argumentIndex]
        if ($argument -eq '--') { $argumentIndex++; break }
        if ($argument -eq '-') { return $false } # stdin program; following arguments are data
        if ($argument.StartsWith('--')) {
            if ($argument -ceq '--check-hash-based-pycs') { $argumentIndex += 2 }
            else { $argumentIndex++ }
            continue
        }
        if ($argument.StartsWith('-')) {
            $argumentIndex++
            # Python accepts short-option clusters such as -Im, -uc and -IX.
            # c/m consume the program; W/X consume the rest of this token or
            # the following token as their value. Option case is significant.
            for ($shortIndex = 1; $shortIndex -lt $argument.Length; $shortIndex++) {
                $shortOption = [string]$argument[$shortIndex]
                if ($shortOption -ceq 'c' -or $shortOption -ceq 'm') { return $false }
                if ($shortOption -ceq 'W' -or $shortOption -ceq 'X') {
                    if ($shortIndex -eq $argument.Length-1) { $argumentIndex++ }
                    break
                }
            }
            continue
        }
        break
    }
    if ($argumentIndex -ge $processArguments.Count) { return $false }
    $scriptArgument = $processArguments[$argumentIndex]
    if ($scriptArgument -match '(?i)(?:^|[\\/])cmos-motion-poc[\\/](app\.py|replay[^\\/]*\.py)$') { return $true }
    $scriptName = [IO.Path]::GetFileName($scriptArgument.Replace('/', '\'))
    if ($scriptName -notmatch '^(app\.py|replay[^\\/]*\.py)$') { return $false }
    if ([IO.Path]::IsPathFullyQualified($scriptArgument)) { return $false }
    $scriptArguments = @($processArguments | Select-Object -Skip ($argumentIndex+1))
    # The relative path's CWD is unavailable from Win32_Process. A real input
    # connection flag is sufficient evidence to require an explicit stop.
    if ($scriptArguments -contains '--slicer-connect') { return $true }
    if ([string]$Process.ExecutablePath -match '(?i)[\\/]cmos-motion-poc[\\/]\.venv[\\/]Scripts[\\/]pythonw?\.exe$|[\\/]payload[\\/]recognizer-runtime[\\/]Scripts[\\/]pythonw?\.exe$') { return $true }
    # Also recognize a prepared source/payload config with a generic interpreter.
    for ($optionIndex = 0; $optionIndex -lt $scriptArguments.Count; $optionIndex++) {
        $configPath = $null
        if ($scriptArguments[$optionIndex] -eq '--config' -and $optionIndex+1 -lt $scriptArguments.Count) {
            $configPath = $scriptArguments[$optionIndex+1]
        } elseif ($scriptArguments[$optionIndex].StartsWith('--config=')) {
            $configPath = $scriptArguments[$optionIndex].Substring(9)
        }
        if (-not $configPath -or -not [IO.Path]::IsPathFullyQualified($configPath)) { continue }
        foreach ($candidateRoot in @($WorkspaceRoot, $ReleaseRoot)) {
            if ([string]::IsNullOrWhiteSpace($candidateRoot)) { continue }
            $prefix = [IO.Path]::GetFullPath($candidateRoot).TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
            if ([IO.Path]::GetFullPath($configPath).StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { return $true }
        }
    }
    return $false
}

$ErrorActionPreference = 'Stop'
if ((Get-AuthenticodeSignature -LiteralPath $PSCommandPath).Status -ne 'Valid') {
    throw 'A trusted distribution signature is required.'
}
$releaseLock = [IO.File]::Open((Join-Path ([IO.Path]::GetFullPath($ReleaseRoot)) 'release.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
$active = @(Get-CimInstance Win32_Process -Filter "Name='SlicerApp-real.exe' OR Name='python.exe' OR Name='pythonw.exe'" | Where-Object {
    Test-CompletionInputProcess -Process $_ -WorkspaceRoot $WorkspaceRoot -ReleaseRoot $ReleaseRoot
})
if ($active.Count) { throw 'Stop all Slicer and recognition/replay instances before starting a release.' }
$pointer = Get-Content -LiteralPath (Join-Path $ReleaseRoot 'current-release.json') -Raw | ConvertFrom-Json
$manifest = [IO.Path]::GetFullPath($pointer.manifest)
if (-not $manifest.StartsWith([IO.Path]::GetFullPath($ReleaseRoot) + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Release pointer escaped the selected release root.'
}
$hash = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $pointer.manifest_sha256) { throw 'Release pointer digest mismatch.' }
$catalog = "$manifest.ps1"
if ((Get-AuthenticodeSignature -LiteralPath $catalog).Status -ne 'Valid') { throw 'Untrusted manifest catalog.' }
if ((Get-Content -LiteralPath $catalog -Raw) -notmatch "(?m)^# manifest-sha256: $hash\r?$") { throw 'Catalog binding mismatch.' }
$data = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
if (-not $data.external_executables.Count) { throw 'External executable inventory is missing.' }
foreach ($binary in $data.external_executables) {
    if ((Get-FileHash -LiteralPath $binary.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $binary.sha256) {
        throw 'External executable differs from the prepared release.'
    }
}
$preparedSlicer = @($data.external_executables | Where-Object role -eq 'slicer_launcher')
if ($preparedSlicer.Count -ne 1 -or [IO.Path]::GetFullPath($preparedSlicer[0].path) -ne [IO.Path]::GetFullPath($SlicerExecutable)) {
    throw 'Requested Slicer executable differs from selected release.'
}
if ((Get-FileHash -LiteralPath (Join-Path ([IO.Path]::GetDirectoryName($manifest)) 'sbom.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $data.sbom_sha256) {
    throw 'SBOM digest mismatch.'
}
if (-not $data.deployment_configuration.Count) { throw 'Deployment configuration is missing.' }
$configurationBase = [IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetDirectoryName($manifest)) 'payload')) + [IO.Path]::DirectorySeparatorChar
foreach ($file in $data.deployment_configuration) {
    $target = [IO.Path]::GetFullPath((Join-Path $configurationBase $file.payload_path))
    if (-not $target.StartsWith($configurationBase,[StringComparison]::OrdinalIgnoreCase)) { throw 'Configuration path escaped payload.' }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) { throw 'Deployment configuration changed.' }
}
$payload = Join-Path ([IO.Path]::GetDirectoryName($manifest)) 'payload'
foreach ($component in $data.components.PSObject.Properties) {
    if ($component.Name -notin @('slicer-cstamp','cmos-motion-poc','tools')) { throw 'Unknown release component.' }
    $base = [IO.Path]::GetFullPath((Join-Path $payload $component.Name)) + [IO.Path]::DirectorySeparatorChar
    foreach ($file in $component.Value.files) {
        $target = [IO.Path]::GetFullPath((Join-Path $base $file.path))
        if (-not $target.StartsWith($base,[StringComparison]::OrdinalIgnoreCase)) { throw 'Payload path escape.' }
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) { throw 'Payload hash mismatch.' }
    }
}
$python = Join-Path $payload 'recognizer-runtime/Scripts/python.exe'
$installed = @(& $python -m pip freeze | Sort-Object)
if ($LASTEXITCODE -ne 0) { throw 'Python dependency inventory failed.' }
$expected = @($data.python_dependencies.name_version | Sort-Object)
if (-not $expected.Count) { throw 'Release dependency inventory is empty.' }
if (Compare-Object $installed $expected) { throw 'Python dependencies differ from release manifest.' }
$venvRoot = [IO.Path]::GetFullPath((Join-Path $payload 'recognizer-runtime')) + [IO.Path]::DirectorySeparatorChar
if (-not $data.runtime_dependencies.files.Count) { throw 'Runtime file inventory is missing.' }
foreach ($file in $data.runtime_dependencies.files) {
    $target = [IO.Path]::GetFullPath((Join-Path $venvRoot $file.path))
    if (-not $target.StartsWith($venvRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Runtime file path escaped the virtual environment.' }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) { throw 'Runtime dependency file changed.' }
}
# Environment is scoped to the launched child; source/data paths are separate.
$slicerInfo = [Diagnostics.ProcessStartInfo]::new($SlicerExecutable)
$slicerInfo.UseShellExecute = $false
$slicerInfo.Arguments = '--python-script "' + (Join-Path $payload 'slicer-cstamp/start_server_session.py') + '"'
$slicerInfo.Environment['CSTAMP_WORKSPACE_ROOT'] = [IO.Path]::GetFullPath($WorkspaceRoot)
$slicerInfo.Environment['CSTAMP_TARGET_REGISTRY'] = Join-Path $payload 'config/targets.json'
$slicerInfo.Environment['CSTAMP_RUNTIME_MANIFEST'] = Join-Path $payload 'config/runtime.json'
$nonce = [Guid]::NewGuid().ToString('N')
$runtimeConfiguration = Get-Content -LiteralPath (Join-Path $payload 'config/runtime.json') -Raw | ConvertFrom-Json
if ($runtimeConfiguration.recognizer.settings.camera_index -ne $CameraIndex) {
    throw 'Camera index differs from the signed runtime configuration.'
}
# Derive the exact AppConfig from the already hash-verified runtime, including
# the selected recognizer and model. Defaults must not replace release settings.
$recognizerConfiguration = Join-Path $ReleaseRoot "startup-$nonce-recognizer.json"
[IO.File]::WriteAllText($recognizerConfiguration, ($runtimeConfiguration.recognizer.settings | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))
$ready = Join-Path $ReleaseRoot "startup-$nonce.json"
$slicerInfo.Environment['CSTAMP_STARTUP_NONCE'] = $nonce
$slicerInfo.Environment['CSTAMP_STARTUP_READY'] = $ready
$startedAt = Get-Date
$slicerProcess = [Diagnostics.Process]::Start($slicerInfo)
try {
    $deadline = (Get-Date).AddSeconds(60)
    do {
        if (Test-Path -LiteralPath $ready) {
            $observed = Get-Content -LiteralPath $ready -Raw | ConvertFrom-Json
            if ($observed.nonce -ne $nonce -or $observed.armed -ne $false) { throw 'Startup readiness identity mismatch.' }
            $expectedModule = Join-Path $payload 'slicer-cstamp/CStampModule.py'
            if ([IO.Path]::GetFullPath($observed.module_path) -ne [IO.Path]::GetFullPath($expectedModule) -or
                $observed.module_sha256 -ne (Get-FileHash -LiteralPath $expectedModule -Algorithm SHA256).Hash.ToLowerInvariant()) {
                throw 'Loaded Slicer source differs from selected release.'
            }
            break
        }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $deadline)
    if (-not $observed) { throw 'Slicer startup readiness timed out.' }
$recognizerInfo = [Diagnostics.ProcessStartInfo]::new($python)
$recognizerInfo.UseShellExecute = $false
$recognizerInfo.WorkingDirectory = Join-Path $payload 'cmos-motion-poc'
$recognizerInfo.CreateNoWindow = $true
$recognizerInfo.Environment['CSTAMP_WORKSPACE_ROOT'] = [IO.Path]::GetFullPath($WorkspaceRoot)
$runDirectory = Join-Path $WorkspaceRoot "work/runs/$nonce"
New-Item -ItemType Directory -Path $runDirectory -ErrorAction Stop | Out-Null
$commandTrace = Join-Path $runDirectory 'commands.jsonl'
$recognizerInfo.Arguments = ('"' + (Join-Path $payload 'cmos-motion-poc/app.py') + '" --config "' + $recognizerConfiguration + '" --slicer-connect --trial-log "' + $commandTrace + '"')
$recognizerProcess = [Diagnostics.Process]::Start($recognizerInfo)
$deadline = (Get-Date).AddSeconds(30)
$recognizerReady = $null
$readinessProbe = @'
import sys,json,time
sys.path.insert(0,sys.argv[1])
from ui_bridge import MemoryChannel
channel=MemoryChannel('state')
try:
    value=channel.read() or {}
    age=time.time()-value.get('ts',0)
    print(json.dumps({'fresh':0<=age<2,'connected':value.get('connected') is True,
        'armed':value.get('armed'),'generation':value.get('input',{}).get('generation',0),'ts':value.get('ts')}))
finally:channel.close()
'@
$recognizerObservation = $null
do {
    $endpoints = @(Get-ChildItem -LiteralPath (Join-Path $WorkspaceRoot 'work/input-switch') -Filter 'normal-*.json' -ErrorAction SilentlyContinue)
    foreach ($endpoint in $endpoints) {
        $value = Get-Content -LiteralPath $endpoint.FullName -Raw | ConvertFrom-Json
        if ($value.phase -eq 'normal' -and $value.created_ts -ge ([DateTimeOffset]$startedAt).ToUnixTimeMilliseconds()/1000.0 -and
            [IO.Path]::GetFullPath($value.argv[1]) -eq [IO.Path]::GetFullPath((Join-Path $payload 'cmos-motion-poc/app.py'))) {
            $probeText = & $python -c $readinessProbe (Join-Path $payload 'cmos-motion-poc')
            if ($LASTEXITCODE -ne 0) { throw 'Recognizer readiness observation failed.' }
            $probe = $probeText | ConvertFrom-Json
            if ($probe.fresh -and $probe.connected -and $probe.armed -eq $false -and $probe.generation -ge 1 -and
                (Get-Process -Id $value.pid -ErrorAction SilentlyContinue)) {
                $recognizerReady = $value; $recognizerObservation = $probe; break
            }
        }
    }
    if ($recognizerReady) { break }
    Start-Sleep -Milliseconds 200
} while ((Get-Date) -lt $deadline)
if (-not $recognizerReady) { throw 'Recognizer failed to reach connected stopped readiness.' }
[PSCustomObject]@{ manifest=$manifest; slicer_pid=$observed.pid; recognizer_pid=$recognizerReady.pid;
    armed=$recognizerObservation.armed; connected=$recognizerObservation.connected;
    observed_ts=$recognizerObservation.ts; generation=$recognizerObservation.generation }
} catch {
    # Stop only children launched from this exact selected payload during this attempt.
    $owned = @(Get-CimInstance Win32_Process | Where-Object {
        $_.CreationDate -ge $startedAt -and $_.CommandLine -and
        ($_.CommandLine.Contains((Join-Path $payload 'slicer-cstamp/start_server_session.py')) -or
         $_.CommandLine.Contains((Join-Path $payload 'cmos-motion-poc/app.py')))
    })
    foreach ($process in $owned) { Stop-Process -Id $process.ProcessId -ErrorAction SilentlyContinue }
    throw
}
} finally { $releaseLock.Dispose() }

# SIG # Begin signature block
# MIIFlAYJKoZIhvcNAQcCoIIFhTCCBYECAQExCzAJBgUrDgMCGgUAMGkGCisGAQQB
# gjcCAQSgWzBZMDQGCisGAQQBgjcCAR4wJgIDAQAABBAfzDtgWUsITrck0sYpfvNR
# AgEAAgEAAgEAAgEAAgEAMCEwCQYFKw4DAhoFAAQUSacLQ6g2MKxO3lIjb92f3Gxa
# KIigggMiMIIDHjCCAgagAwIBAgIQYDyZGLMyDrBH6jnlznpG4TANBgkqhkiG9w0B
# AQsFADAnMSUwIwYDVQQDDBxDU3RhbXBQb0MtRGV2IChub24tY2xpbmljYWwpMB4X
# DTI2MTAwOTE3MDI0MVoXDTI4MTAwOTE3MTI0MlowJzElMCMGA1UEAwwcQ1N0YW1w
# UG9DLURldiAobm9uLWNsaW5pY2FsKTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCC
# AQoCggEBAKRO5ae618qZnDZ+Dd+A3oi6wHw4P3SjQiONiEVEnSOmfyohnzU++1ms
# PHQSCP4e0ioKT6/pYmftX3jY/+NIGKO6EPGzMn9Y9dsZ9hIXF5Qt97Wb6POaNHj5
# ODitXT5TMaESEHCehTEo5rBKTaa5X2FO8OKdRMW5pAfqooxE/vFNFS3Sy77URvzC
# JA1HYgL222ZsR5LjIW7GsAYdADb8sAM6dhro3icVxdv5WM4ZhEzfWm+kVITvXCmp
# +MoCgu9QJSZpSCPptlFKJ9YUdXX5Ubv7ECdtiJ1L/Lp6nKpE0dhrK/IGmDImaE3P
# Kf4I2xp0pXLBpjVkl8xHKk50yAQM4MUCAwEAAaNGMEQwDgYDVR0PAQH/BAQDAgeA
# MBMGA1UdJQQMMAoGCCsGAQUFBwMDMB0GA1UdDgQWBBSIGhiAj0+ZUFwxFonh1V2A
# XGmpkTANBgkqhkiG9w0BAQsFAAOCAQEAkBKEWc+Npb+Uc7z7ibiHVbd1pcaccr0K
# zhzbfgZRd7Qpu5ekgID4ABawbLJ5DGj98oGiZjSbzTccsyWEW4yLzZiWl2YcH9GD
# ESGdqdqrhCJEOcbJ/XtEnYodezTniAdezTTNjnB1jDWKYLi4CZxMH4BwCB5tLzGJ
# KcVYnb8OKoQel6I2jRGJvDlvsptWYWCc6Tn5fA5X0KrPRfpjIMm1Aupobj4fP0NH
# a+GQ2ckRml7aAaLrceSBw6B+0e/H3JzRvFcxQaTrOIa0l46W0Yg5c8+xUCrSYMNH
# UJDFkS3gYJsVC/uneBRivEafwCEOOnFGNvHazzc9unaWaIGcALWDmjGCAdwwggHY
# AgEBMDswJzElMCMGA1UEAwwcQ1N0YW1wUG9DLURldiAobm9uLWNsaW5pY2FsKQIQ
# YDyZGLMyDrBH6jnlznpG4TAJBgUrDgMCGgUAoHgwGAYKKwYBBAGCNwIBDDEKMAig
# AoAAoQKAADAZBgkqhkiG9w0BCQMxDAYKKwYBBAGCNwIBBDAcBgorBgEEAYI3AgEL
# MQ4wDAYKKwYBBAGCNwIBFTAjBgkqhkiG9w0BCQQxFgQUALMenp9TrJLrHK6PAoUu
# d42m5HMwDQYJKoZIhvcNAQEBBQAEggEAigPj3a4oOTtAr0ml0D8rO/L/qxuz6Nnl
# oblmbStG+fCBXPcYa0h0tGysyZxRvnoxSpBshzYfrq+Q8An3gDxJuz7cCgu5tdeu
# x5n8e2mHPvHOVe7jpXiESznX4Z/6nmd4AMG7+yYdkuUj3WnOzuH8KTiGn2Me/Fkd
# Pf1LRihvV3d8THGlFUQVqrfYC6oy5r0HZBsRMJkt7FcO/pF2LmVLcGVPsMDFVscO
# SIOd6psjHVBqmAECGlcn5rDr9jMD1Q+ud6vF4g1yutQ5mRWZi6EaoyP4hbQjGZGY
# uXgtcy3U6jGL0yaFplzxOeqvGEY7MqZJv2SokuBXlGfJR3yLxBmtuA==
# SIG # End signature block
