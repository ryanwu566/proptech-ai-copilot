$ErrorActionPreference = "Stop"

$backendUrl = "http://localhost:8000"
$frontendUrl = "http://localhost:3000"
$expectedCases = @{
    "DEMO-LOW" = @{ status = "eligible"; signal = "green" }
    "DEMO-MEDIUM" = @{ status = "manual_review"; signal = "yellow" }
    "DEMO-HIGH" = @{ status = "not_eligible"; signal = "red" }
}

function Assert-Equal {
    param(
        [string]$Label,
        [object]$Actual,
        [object]$Expected
    )

    if ($Actual -ne $Expected) {
        throw "$Label mismatch: expected '$Expected', got '$Actual'."
    }
}

Write-Host "[1/4] Checking FastAPI health ..."
$health = Invoke-RestMethod -Uri "$backendUrl/health" -Method Get
Assert-Equal "Backend health" $health.status "ok"
Write-Host "      OK: backend status=$($health.status)"

Write-Host "[2/4] Checking Next.js frontend ..."
$frontend = Invoke-WebRequest -Uri $frontendUrl -Method Get -UseBasicParsing
Assert-Equal "Frontend HTTP status" $frontend.StatusCode 200
Write-Host "      OK: frontend HTTP $($frontend.StatusCode)"

Write-Host "[3/4] Checking TaxOracle demo cases ..."
$demoCases = Invoke-RestMethod -Uri "$backendUrl/demo-cases" -Method Get
foreach ($caseId in @("DEMO-LOW", "DEMO-MEDIUM", "DEMO-HIGH")) {
    $demoCase = $demoCases | Where-Object { $_.case_id -eq $caseId } | Select-Object -First 1
    if ($null -eq $demoCase) {
        throw "Demo case '$caseId' was not returned by /demo-cases."
    }

    $payload = $demoCase | ConvertTo-Json -Depth 10
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $analysis = Invoke-RestMethod -Uri "$backendUrl/taxoracle/analyze" -Method Post -ContentType "application/json; charset=utf-8" -Body $payloadBytes
    Assert-Equal "$caseId eligibility_status" $analysis.eligibility_status $expectedCases[$caseId].status
    Assert-Equal "$caseId signal_color" $analysis.signal_color $expectedCases[$caseId].signal
    Write-Host "      OK: $caseId -> $($analysis.eligibility_status) / $($analysis.signal_color)"
}

Write-Host "[4/4] Checking HTML report download endpoint ..."
$reportCase = $demoCases | Where-Object { $_.case_id -eq "DEMO-LOW" } | Select-Object -First 1
$reportPayload = $reportCase | ConvertTo-Json -Depth 10
$reportPayloadBytes = [System.Text.Encoding]::UTF8.GetBytes($reportPayload)
$report = Invoke-WebRequest -Uri "$backendUrl/taxoracle/report" -Method Post -ContentType "application/json; charset=utf-8" -Body $reportPayloadBytes -UseBasicParsing
Assert-Equal "HTML report HTTP status" $report.StatusCode 200
if ([string]::IsNullOrWhiteSpace($report.Content)) {
    throw "HTML report endpoint returned empty content."
}
Write-Host "      OK: HTML report HTTP $($report.StatusCode), bytes=$($report.RawContentLength)"

Write-Host ""
Write-Host "Demo check passed."
