# PowerShell script to start Azurite local emulator
$AzuriteDir = Join-Path $PSScriptRoot "..\.azurite"
if (!(Test-Path $AzuriteDir)) {
    New-Item -ItemType Directory -Path $AzuriteDir | Out-Null
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Azurite Local Azure Storage Emulator...        " -ForegroundColor Cyan
Write-Host " Location: $AzuriteDir                                    " -ForegroundColor Cyan
Write-Host " Blob Endpoint: http://127.0.0.1:10000/devstoreaccount1   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

azurite --silent --skipApiVersionCheck --location $AzuriteDir --blobHost 127.0.0.1 --blobPort 10000
