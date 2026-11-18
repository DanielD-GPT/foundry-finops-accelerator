$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    python .\scripts\build_dashboards.py
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard generation failed.' }
    python .\scripts\validate_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Asset validation failed.' }
    $pythonFiles = @(
        Get-ChildItem .\scripts\*.py | ForEach-Object FullName
    ) + @(
        (Resolve-Path .\src\cost-normalizer\function_app.py).Path
    )
    python -m py_compile @pythonFiles
    if ($LASTEXITCODE -ne 0) { throw 'Python compilation failed.' }
    python -m pytest .\instrumentation\python .\src\cost-normalizer -q
    if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }

    az bicep build --file .\infra\main.bicep --outfile .\infra\main.json
    if ($LASTEXITCODE -ne 0) { throw 'Bicep build failed.' }

    if (Get-Command dotnet -ErrorAction SilentlyContinue) {
        dotnet test .\instrumentation\dotnet\FoundryFinOps.Tests\FoundryFinOps.Tests.csproj
        if ($LASTEXITCODE -ne 0) { throw '.NET tests failed.' }
    } else {
        Write-Warning '.NET SDK is not installed; skipped .NET tests.'
    }

    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Push-Location .\instrumentation\typescript
        try {
            npm ci
            npm run build
            npm test
            if ($LASTEXITCODE -ne 0) { throw 'TypeScript validation failed.' }
        } finally {
            Pop-Location
        }
    } else {
        Write-Warning 'Node.js is not installed; skipped TypeScript tests.'
    }
} finally {
    Pop-Location
}

Write-Host 'All available accelerator validations passed.'
