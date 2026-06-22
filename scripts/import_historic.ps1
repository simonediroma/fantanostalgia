<#
.SYNOPSIS
    Importa un CSV storico su FantaNostalgia (produzione).

.PARAMETER File
    Percorso al file CSV da importare.

.PARAMETER Url
    URL base del server (default: produzione Cloud Run).

.PARAMETER Username
    Username admin (default: admin).

.PARAMETER Password
    Password admin (default: changeme).

.EXAMPLE
    .\import_historic.ps1 -File ".\out_1999-2000.csv"
    .\import_historic.ps1 -File ".\out.csv" -Password "miapassword"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$File,

    [string]$Url = "https://fantanostalgia-1074392598607.europe-west1.run.app",

    [string]$Username = "admin",

    [string]$Password = "changeme"
)

$ErrorActionPreference = "Stop"

# Verifica che il file esista
if (-not (Test-Path $File)) {
    Write-Error "File non trovato: $File"
    exit 1
}

$filePath = Resolve-Path $File
$fileName = [System.IO.Path]::GetFileName($filePath)

Write-Host "File: $filePath"
Write-Host "Server: $Url"
Write-Host ""

# 1. Login
Write-Host "Login in corso..."
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Method POST `
    -Uri "$Url/auth/login" `
    -ContentType "application/json" `
    -Body "{`"username`":`"$Username`",`"password`":`"$Password`"}" `
    -SessionVariable session | Out-Null
Write-Host "Login OK."

# 2. Upload CSV con multipart/form-data
Write-Host "Upload CSV in corso..."

$fileBytes = [System.IO.File]::ReadAllBytes($filePath)
$boundary = [System.Guid]::NewGuid().ToString()
$CRLF = "`r`n"

$bodyLines = (
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: text/csv",
    "",
    [System.Text.Encoding]::UTF8.GetString($fileBytes),
    "--$boundary--"
) -join $CRLF

$result = Invoke-RestMethod -Method POST `
    -Uri "$Url/admin/historic/import" `
    -WebSession $session `
    -ContentType "multipart/form-data; boundary=$boundary" `
    -Body $bodyLines

Write-Host ""
Write-Host "Importazione completata!"
Write-Host "  Stagione:      $($result.season)"
Write-Host "  Righe CSV:     $($result.rows_processed)"
Write-Host "  Voti inseriti: $($result.ratings_imported)"
