param(
    [int]$CameraIndex = 0,
    [string]$Config = '',
    [switch]$EnableInput,
    [switch]$SlicerConnect
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$prototypeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $prototypeRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Virtual environment is missing. Run .\setup.ps1 first.'
}

$arguments = @((Join-Path $prototypeRoot 'app.py'), '--camera-index', $CameraIndex)
if ($Config) {
    $arguments += @('--config', $Config)
}
if ($EnableInput) {
    $arguments += '--enable-input'
}
if ($SlicerConnect) {
    $arguments += '--slicer-connect'
}

& $pythonPath @arguments


# SIG # Begin signature block
# MIIFuQYJKoZIhvcNAQcCoIIFqjCCBaYCAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCAKU3A9u8Mp7kv/
# mZwmeIsoONHFd/0IMkqfFSmqkSvedqCCAyIwggMeMIICBqADAgECAhBgPJkYszIO
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
# hvcNAQkEMSIEIBnYuQnfcuGRLctHggVZr6wTlVVLF0OFFxJvqGxUkI7OMA0GCSqG
# SIb3DQEBAQUABIIBAB0BLeylGRBzgWfbZFgtQPS9CrgqkJjwHlSk+p6E5RyNpyik
# 1rvICEshZ41cALZRT9kA/s08AqnD6V7o9+H5/mlcdwQcIt+JPsa4ZdefMW/iWzz8
# yvsnZa4Qg+Y1L/XgVzdI4NU8hRbzEd1wvzNuuMYj/ndwQvJcnyZpAVdmvMf8DgCB
# VVPkZ7pWGakX86oZRuM+/vlkt6wwmy/fmWe1OOLGAWtlWn2o7cG2dwPfgYZ+MTZa
# UlKdjSN2ZKFcyoTZlrSe0hG4r1G6d/H3h8QGl2ToplLhOYjOT+bCLoJKjs6ONAKF
# aWi1E1SPsxqRoTyI8M9RftXO494yp585s+i1ei0=
# SIG # End signature block
