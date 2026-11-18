$ErrorActionPreference = 'Stop'

$envValues = azd env get-values
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read the azd environment.'
}

foreach ($line in $envValues) {
    if ($line -notmatch '=') { continue }
    $name, $value = $line -split '=', 2
    [Environment]::SetEnvironmentVariable($name, $value.Trim('"'), 'Process')
}

Write-Host 'Waiting 60 seconds for managed-identity role assignments to propagate.'
Start-Sleep -Seconds 60

python .\scripts\build_dashboards.py
python .\scripts\seed_reference_data.py
python .\scripts\import_dashboards.py

Write-Host ''
Write-Host "Managed Grafana: $env:GRAFANA_ENDPOINT"
Write-Host 'Actual Cost panels will remain pending until Azure Cost Management publishes the first export.'
