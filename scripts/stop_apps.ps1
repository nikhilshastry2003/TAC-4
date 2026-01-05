# PowerShell script to stop Natural Language SQL Interface
# Windows equivalent of stop_apps.sh

Write-Host "Stopping Natural Language SQL Interface..." -ForegroundColor Blue

# Kill processes on specific ports
$ports = @(5173, 8000, 8001)
foreach ($port in $ports) {
    Write-Host "Killing processes on port $port..." -ForegroundColor Green
    $netstat = netstat -ano | Select-String ":$port\s"
    if ($netstat) {
        $pids = $netstat | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -Unique
        foreach ($pid in $pids) {
            if ($pid -match '^\d+$' -and $pid -ne '0') {
                try {
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                    Write-Host "  Killed process $pid" -ForegroundColor Yellow
                }
                catch {
                    # Process may have already exited
                }
            }
        }
    }
}

# Kill webhook server processes
Write-Host "Killing webhook server processes..." -ForegroundColor Green
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*trigger_webhook*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill node/npm processes related to the frontend
Write-Host "Killing frontend processes..." -ForegroundColor Green
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*app\client*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Services stopped successfully!" -ForegroundColor Green
