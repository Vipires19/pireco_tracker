$BackendUrl = if ($env:BACKEND_URL) { $env:BACKEND_URL } else { "http://localhost:8000" }
$GatewayUrl = if ($env:GATEWAY_URL) { $env:GATEWAY_URL } else { "http://localhost:5024" }
$FrontendUrl = if ($env:FRONTEND_URL) { $env:FRONTEND_URL } else { "http://localhost:3000" }

Write-Host "=== Vehicle Tracker Health Check ==="

function Test-Service {
    param([string]$Name, [string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] $Name — $Url"
            return $true
        }
    } catch {}
    Write-Host "[FAIL] $Name — $Url"
    return $false
}

$allOk = $true
$allOk = (Test-Service "Backend" "$BackendUrl/health") -and $allOk
$allOk = (Test-Service "Gateway" "$GatewayUrl/health") -and $allOk
$allOk = (Test-Service "Frontend" "$FrontendUrl/api/health") -and $allOk

if (-not $allOk) { exit 1 }
Write-Host "=== All services healthy ==="
