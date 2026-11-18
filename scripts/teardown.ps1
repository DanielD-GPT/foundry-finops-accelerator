param(
    [Parameter(Mandatory = $true)]
    [string]$EnvironmentName,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    azd env select $EnvironmentName
    if ($LASTEXITCODE -ne 0) { throw "Unknown azd environment '$EnvironmentName'." }
    $values = azd env get-values
    $resourceGroup = ($values | Where-Object { $_ -like 'AZURE_RESOURCE_GROUP=*' }) -replace '^AZURE_RESOURCE_GROUP=', '' -replace '"', ''
    $exportName = ($values | Where-Object { $_ -like 'COST_EXPORT_NAME=*' }) -replace '^COST_EXPORT_NAME=', '' -replace '"', ''
    Write-Host "Resource group to delete: $resourceGroup"
    Write-Host "Cost export to delete:    $exportName"
    if (-not $Force) {
        $confirmation = Read-Host "Type '$EnvironmentName' to continue"
        if ($confirmation -ne $EnvironmentName) {
            throw 'Teardown cancelled.'
        }
    }
    if ($exportName) {
        az costmanagement export delete --name $exportName --scope "/subscriptions/$env:AZURE_SUBSCRIPTION_ID"
    }
    azd down --purge --force --no-prompt
} finally {
    Pop-Location
}
