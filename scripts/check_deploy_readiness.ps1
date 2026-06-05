$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Assert-Exists([string]$Path) {
    if (-not (Test-Path $Path)) {
        throw "Missing required deployment file: $Path"
    }
    Write-Host "[OK] $Path"
}

Write-Host "Checking required deployment files..."
@(
    "backend/api_main.py",
    "frontend_next/package.json",
    "data/mock_tax_cases.csv",
    "data/mock_map_points.json",
    "requirements.txt"
) | ForEach-Object { Assert-Exists $_ }

Write-Host "Checking tracked sensitive files..."
$trackedSensitive = git ls-files | Where-Object {
    $_ -match '(^|/)(\.env|\.env\.local|secrets\.toml)$'
}
if ($trackedSensitive) {
    throw "Sensitive files are tracked by git: $($trackedSensitive -join ', ')"
}
Write-Host "[OK] No .env, .env.local, or secrets.toml files are tracked."

Write-Host "Running pytest..."
python -m pytest -q

Write-Host "Running Next.js production build..."
npm.cmd --prefix frontend_next run build

Write-Host "Deployment readiness checks passed."
