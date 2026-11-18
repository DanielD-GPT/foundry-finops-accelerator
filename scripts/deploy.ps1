$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $env:AZURE_DEV_USER_AGENT = 'microsoft_foundry_skill'
    .\scripts\validate.ps1
    azd provision --no-prompt
    if ($LASTEXITCODE -ne 0) { throw 'azd provision failed.' }
    Write-Host 'Waiting 60 seconds for RBAC propagation.'
    Start-Sleep -Seconds 60
    azd deploy --no-prompt
    if ($LASTEXITCODE -ne 0) { throw 'azd deploy failed.' }
    .\scripts\postprovision.ps1
} finally {
    Remove-Item Env:\AZURE_DEV_USER_AGENT -ErrorAction SilentlyContinue
    Pop-Location
}
