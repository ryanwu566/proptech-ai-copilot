$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "Starting FastAPI backend at http://localhost:8000 ..."
python -m uvicorn backend.api_main:app --reload --host 127.0.0.1 --port 8000
