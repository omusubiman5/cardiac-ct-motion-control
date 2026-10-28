param(
    [Parameter(Mandatory=$true)][string]$Manifest,
    [Parameter(Mandatory=$true)][string]$ReleaseRoot,
    [switch]$Rollback
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
# This tool changes a release pointer only. It never changes certificate trust.
$signature = Get-AuthenticodeSignature -LiteralPath $PSCommandPath
if ($signature.Status -ne 'Valid') { throw 'A trusted distribution signature is required.' }
$root = [IO.Path]::GetFullPath($ReleaseRoot)
New-Item -ItemType Directory -Path $root -Force | Out-Null
$releaseLock = [IO.File]::Open((Join-Path $root 'release.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
$activeTools = @(Get-CimInstance Win32_Process -Filter "Name='SlicerApp-real.exe' OR Name='python.exe' OR Name='pythonw.exe'" | Where-Object {
    Test-CompletionInputProcess -Process $_ -WorkspaceRoot (Split-Path $PSScriptRoot -Parent) -ReleaseRoot $root
})
if ($activeTools.Count -gt 0) { throw 'Stop Slicer and all normal/replay input before update or rollback.' }
$pointer = Join-Path $root 'current-release.json'
$previous = Join-Path $root 'previous-release.json'
if ($Rollback) {
    if (-not (Test-Path -LiteralPath $previous)) { throw 'No verified previous release is registered.' }
    $candidate = Get-Content -LiteralPath $previous -Raw | ConvertFrom-Json
} else {
    $candidate = [PSCustomObject]@{ manifest = [IO.Path]::GetFullPath($Manifest) }
}
if (-not [IO.Path]::GetFullPath($candidate.manifest).StartsWith($root + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Release manifest must stay inside the selected release root.'
}
$data = Get-Content -LiteralPath $candidate.manifest -Raw | ConvertFrom-Json
# Require a separately trusted signed catalog binding the exact manifest digest.
$catalogPath = "$($candidate.manifest).ps1"
$catalogSignature = Get-AuthenticodeSignature -LiteralPath $catalogPath
if ($catalogSignature.Status -ne 'Valid') { throw 'Manifest catalog has no trusted signature.' }
$manifestHash = (Get-FileHash -LiteralPath $candidate.manifest -Algorithm SHA256).Hash.ToLowerInvariant()
if ((Get-FileHash -LiteralPath (Join-Path ([IO.Path]::GetDirectoryName($candidate.manifest)) 'sbom.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $data.sbom_sha256) {
    throw 'SBOM digest mismatch.'
}
$catalog = Get-Content -LiteralPath $catalogPath -Raw
if ($catalog -notmatch "(?m)^# manifest-sha256: $manifestHash\r?$") { throw 'Signed catalog does not bind this manifest.' }
foreach ($component in $data.components.PSObject.Properties) {
    if ($component.Name -notin @('slicer-cstamp','cmos-motion-poc','tools')) { throw 'Unknown release component.' }
    $base = Join-Path ([IO.Path]::GetDirectoryName($candidate.manifest)) "payload/$($component.Name)"
    $baseFull = [IO.Path]::GetFullPath($base) + [IO.Path]::DirectorySeparatorChar
    foreach ($file in $component.Value.files) {
        $target = [IO.Path]::GetFullPath((Join-Path $base $file.path))
        if (-not $target.StartsWith($baseFull,[StringComparison]::OrdinalIgnoreCase)) { throw 'Payload path escaped its component.' }
        $actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $file.sha256) { throw "Payload hash mismatch: $($component.Name)/$($file.path)" }
    }
}
$candidate | Add-Member -NotePropertyName manifest_sha256 -NotePropertyValue $manifestHash -Force
$temporary = Join-Path $root ('release-' + [Guid]::NewGuid().ToString('N') + '.tmp')
[IO.File]::WriteAllText($temporary, ($candidate | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
if (Test-Path -LiteralPath $pointer) {
    [IO.File]::Replace($temporary,$pointer,$previous)
} else {
    [IO.File]::Move($temporary,$pointer)
}
Write-Output 'Verified stopped-state release pointer updated. Start tools from the selected payload explicitly.'
} finally { $releaseLock.Dispose() }

# SIG # Begin signature block
# MIIFuQYJKoZIhvcNAQcCoIIFqjCCBaYCAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCCwlupD1KxGMze9
# YLcsdu3b0wImc2UM47QVkLxaI+jncaCCAyIwggMeMIICBqADAgECAhBgPJkYszIO
# sEfqOeXOekbhMA0GCSqGSIb3DQEBCwUAMCcxJTAjBgNVBAMMHENTdGFtcFBvQy1E
# ZXYgKG5vbi1jbGluaWNhbCkwHhcNMjYxMDA5MTcwMjQxWhcNMjgxMDA5MTcxMjQy
# WjAnMSUwIwYDVQQDDBxDU3RhbXBQb0MtRGV2IChub24tY2xpbmljYWwpMIIBIjAN
# BgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApE7lp7rXypmcNn4N34DeiLrAfDg/
# dKNCI42IRUSdI6Z/KiGfNT77Waw8dBII/h7SKgpPr+liZ+1feNj/40gYo7oQ8bMy
# f1j12xn2EhcXlC33tZvo85o0ePk4OK1dPlMxoRIQcJ6FMSjmsEpNprlfYU7w4p1E
# xbmkB+qijET+8U0VLdLLvtRG/MIkDUdiAvbbZmxHkuMhbsawBh0ANvywAzp2Guje
# JxXF2/lYzhmETN9ab6RUhO9cKan4ygKC71AlJmlII+m2UUon1hR1dflRu/sQJ22I
# nUv8unqcqkTR2Gsr8gaYMiZoTc8p/gjbGnSlcsGmNWSXzEcqTnTIBAzgxQIDAQAB
# o0YwRDAOBgNVHQ8BAf8EBAMCB4AwEwYDVR0lBAwwCgYIKwYBBQUHAwMwHQYDVR0O
# BBYEFIgaGICPT5lQXDEWieHVXYBcaamRMA0GCSqGSIb3DQEBCwUAA4IBAQCQEoRZ
# z42lv5RzvPuJuIdVt3WlxpxyvQrOHNt+BlF3tCm7l6SAgPgAFrBssnkMaP3ygaJm
# NJvNNxyzJYRbjIvNmJaXZhwf0YMRIZ2p2quEIkQ5xsn9e0Sdih17NOeIB17NNM2O
# cHWMNYpguLgJnEwfgHAIHm0vMYkpxVidvw4qhB6XojaNEYm8OW+ym1ZhYJzpOfl8
# DlfQqs9F+mMgybUC6mhuPh8/Q0dr4ZDZyRGaXtoBoutx5IHDoH7R78fcnNG8VzFB
# pOs4hrSXjpbRiDlzz7FQKtJgw0dQkMWRLeBgmxUL+6d4FGK8Rp/AIQ46cUY28drP
# Nz26dpZogZwAtYOaMYIB7TCCAekCAQEwOzAnMSUwIwYDVQQDDBxDU3RhbXBQb0Mt
# RGV2IChub24tY2xpbmljYWwpAhBgPJkYszIOsEfqOeXOekbhMA0GCWCGSAFlAwQC
# AQUAoIGEMBgGCisGAQQBgjcCAQwxCjAIoAKAAKECgAAwGQYJKoZIhvcNAQkDMQwG
# CisGAQQBgjcCAQQwHAYKKwYBBAGCNwIBCzEOMAwGCisGAQQBgjcCARUwLwYJKoZI
# hvcNAQkEMSIEIHxu5E++4CjaRFKPEfklW1Gqw+8cEjrHieK2PJn9wyTyMA0GCSqG
# SIb3DQEBAQUABIIBAHtAfDOFKCFEm9LWmy3S3poowO+pFuHWSzy4f3gbo4Kinlpv
# puJJyC4OFDxEhiH5pVcMrGijetlj2rwFRJGGlS4CRVCdbK2FPs+pTF2P3HFd5fId
# HI1zA9GbWidpS7m+mqMfQGfXB9HvPhRJ2GytivTm47hEZPObgy7E+yiTsq6opVny
# Cg6RaT7tpYqy9y6Jp5REpeRAmPCDurPMjtncpZ4fQiBdv8d2EdLhrMKr/p3yh58i
# sjw8+mPpJxPFUc7zEMSW3G2+KFF9OwxUvSggmXxFz/FD7dELsVeAD/+1dpztfbGC
# h1KqPWJXSAvnhCteKKlf+LR3kqYeKirK+bLAdC8=
# SIG # End signature block
