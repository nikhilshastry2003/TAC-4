# PowerShell script to start Natural Language SQL Interface
# Windows equivalent of start.sh

$ErrorActionPreference = "Stop"

Write-Host "Starting Natural Language SQL Interface..." -ForegroundColor Blue

# Get the script's directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Check if .env exists in server directory
$ServerEnvPath = Join-Path $ProjectRoot "app\server\.env"
if (-not (Test-Path $ServerEnvPath)) {
    Write-Host "Warning: No .env file found in app/server/." -ForegroundColor Red
    Write-Host "Please:"
    Write-Host "  1. cd app\server"
    Write-Host "  2. Copy-Item .env.sample .env"
    Write-Host "  3. Edit .env and add your API keys"
    exit 1
}

# Store process IDs for cleanup
$global:BackendProcess = $null
$global:FrontendProcess = $null

# Function to cleanup on exit
function Cleanup {
    Write-Host "`nShutting down services..." -ForegroundColor Blue

    if ($global:BackendProcess -and -not $global:BackendProcess.HasExited) {
        Stop-Process -Id $global:BackendProcess.Id -Force -ErrorAction SilentlyContinue
    }

    if ($global:FrontendProcess -and -not $global:FrontendProcess.HasExited) {
        Stop-Process -Id $global:FrontendProcess.Id -Force -ErrorAction SilentlyContinue
    }

    # Also kill any processes on the ports
    $ports = @(5173, 8000)
    foreach ($port in $ports) {
        $netstat = netstat -ano | Select-String ":$port\s"
        if ($netstat) {
            $pids = $netstat | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -Unique
            foreach ($pid in $pids) {
                if ($pid -match '^\d+$' -and $pid -ne '0') {
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }

    Write-Host "Services stopped successfully." -ForegroundColor Green
}

# Register cleanup on script exit
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup } | Out-Null

try {
    # Start backend
    Write-Host "Starting backend server..." -ForegroundColor Green
    $BackendDir = Join-Path $ProjectRoot "app\server"
    $global:BackendProcess = Start-Process -FilePath "uv" -ArgumentList "run", "python", "main.py" -WorkingDirectory $BackendDir -PassThru -NoNewWindow

    # Wait for backend to start
    Write-Host "Waiting for backend to start..."
    Start-Sleep -Seconds 3

    # Check if backend is running
    if ($global:BackendProcess.HasExited) {
        Write-Host "Backend failed to start!" -ForegroundColor Red
        exit 1
    }

    # Start frontend
    Write-Host "Starting frontend server..." -ForegroundColor Green
    $FrontendDir = Join-Path $ProjectRoot "app\client"
    $global:FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $FrontendDir -PassThru -NoNewWindow

    # Wait for frontend to start
    Start-Sleep -Seconds 3

    # Check if frontend is running
    if ($global:FrontendProcess.HasExited) {
        Write-Host "Frontend failed to start!" -ForegroundColor Red
        Cleanup
        exit 1
    }

    Write-Host "Services started successfully!" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:5173" -ForegroundColor Blue
    Write-Host "Backend:  http://localhost:8000" -ForegroundColor Blue
    Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all services..."

    # Wait for processes
    while (-not $global:BackendProcess.HasExited -and -not $global:FrontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Cleanup
    exit 1
}
finally {
    Cleanup
}
