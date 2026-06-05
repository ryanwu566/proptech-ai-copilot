$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $projectRoot "frontend_next")

Write-Host "Starting Next.js frontend at http://localhost:3000 ..."
npm.cmd run dev
