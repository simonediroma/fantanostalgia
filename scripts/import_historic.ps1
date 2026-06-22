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
    .\scripts\import_historic.ps1 -File ".\out_1999-2000.csv"
    .\scripts\import_historic.ps1 -File ".\out.csv" -Password "miapassword"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$File,

    [string]$Url = "https://fantanostalgia-1074392598607.europe-west1.run.app",

    [string]$Username = "admin",

    [string]$Password = "changeme"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $File)) {
    Write-Error "File non trovato: $File"
    exit 1
}

$filePath = Resolve-Path $File
$fileName = [System.IO.Path]::GetFileName($filePath)

Write-Host "File:   $filePath"
Write-Host "Server: $Url"
Write-Host ""

# 1. Login con WebRequestSession per raccogliere il cookie
Write-Host "Login in corso..."
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Method POST `
    -Uri "$Url/auth/login" `
    -ContentType "application/json" `
    -Body "{`"username`":`"$Username`",`"password`":`"$Password`"}" `
    -SessionVariable session | Out-Null
Write-Host "Login OK."

# Estrai il cookie di sessione dalla WebRequestSession
$cookieHeader = ""
foreach ($cookie in $session.Cookies.GetCookies($Url)) {
    $cookieHeader += "$($cookie.Name)=$($cookie.Value); "
}

# 2. Upload CSV con HttpClient (gestisce multipart correttamente)
Write-Host "Upload CSV in corso..."

Add-Type -AssemblyName System.Net.Http

$httpClient = New-Object System.Net.Http.HttpClient
$httpClient.DefaultRequestHeaders.Add("Cookie", $cookieHeader.TrimEnd("; "))

$fileBytes = [System.IO.File]::ReadAllBytes($filePath)
$fileContent = New-Object System.Net.Http.ByteArrayContent(,$fileBytes)
$fileContent.Headers.ContentType = `
    [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("text/csv")

$multipart = New-Object System.Net.Http.MultipartFormDataContent
$multipart.Add($fileContent, "file", $fileName)

$response = $httpClient.PostAsync("$Url/admin/historic/import", $multipart).GetAwaiter().GetResult()
$responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

if (-not $response.IsSuccessStatusCode) {
    Write-Error "Errore server ($([int]$response.StatusCode)): $responseBody"
    exit 1
}

$result = $responseBody | ConvertFrom-Json

Write-Host ""
Write-Host "Importazione completata!"
Write-Host "  Stagione:      $($result.season)"
Write-Host "  Righe CSV:     $($result.rows_processed)"
Write-Host "  Voti inseriti: $($result.ratings_imported)"
