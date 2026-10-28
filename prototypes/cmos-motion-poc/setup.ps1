$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$prototypeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $prototypeRoot '.venv'
$pythonPath = Join-Path $venvPath 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv $venvPath
}

& $pythonPath -m pip install --upgrade pip
& $pythonPath -m pip install -r (Join-Path $prototypeRoot 'requirements-dev.txt')

Write-Host "Setup complete: $pythonPath"


# SIG # Begin signature block
# MIIFuQYJKoZIhvcNAQcCoIIFqjCCBaYCAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCDhwqsH2aUqGXXa
# FjHJ7lgZR1fStgFLWW+xZdZB8dKMQ6CCAyIwggMeMIICBqADAgECAhBgPJkYszIO
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
# hvcNAQkEMSIEIMLD7hOWY1oqxdh5T0xiKbfTqQMgrvT+XubOiT0eUCYIMA0GCSqG
# SIb3DQEBAQUABIIBAFkBbRPjdUedi0l219mn1/LH6EaqZYodQfKtTuNJhZKMzQqe
# QorxeDvBf6AoB+pgAUxUxMUCvjoaV+NnJGkW+FQCN+dnMR9EQKHbP0zvBSobgirq
# 1lV/WfHoO2ogWxyhlMmMhDu4XB+9BVwoE4dheTcJxxZOWLPM6mcjX1B4f/n6jFF4
# CQEvkI8UQqQ6I0oxL5h9LfGFxqc/TGNebMLf6rri6iITLyg81O6r0YXORcxQvspx
# iv6tylOXbgfeVgs0lGIFCtfGJzYce5HqNvN7PlfdUbEgkeKIHVDFNaqE0J6VxTA7
# lT2jeinK8IoK6yl6G0Z7dRjnYMhaiAFSa6U08d4=
# SIG # End signature block
