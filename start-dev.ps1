param(
    [switch]$Install,
    [ValidateRange(1, 65535)][int]$BackendPort = 8000,
    [ValidateRange(1, 65535)][int]$FrontendPort = 5173
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendPath = Join-Path $projectRoot 'backend'
$frontendPath = Join-Path $projectRoot 'frontend'
$logPath = Join-Path $projectRoot 'data\dev-logs'
$recordPath = Join-Path $logPath 'processes.json'
if ($BackendPort -eq $FrontendPort) { throw 'Choose different ports for the backend and frontend.' }
$listenerPorts = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners().Port
foreach ($port in @($BackendPort, $FrontendPort)) {
    if ($listenerPorts -contains $port) {
        throw "Port $port is already in use. Stop the running copy with its stop-dev.ps1, or choose free ports with -BackendPort and -FrontendPort."
    }
}
if (Test-Path -LiteralPath $recordPath) {
    $records = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    foreach ($record in $records) {
        $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().ToString('o') -eq $record.started) {
            throw 'This copy is already running. Run stop-dev.ps1 from this folder before starting it again.'
        }
    }
}

$pythonCandidates = @((Join-Path $projectRoot '.venv\Scripts\python.exe'), (Join-Path (Split-Path $projectRoot -Parent) '.venv\Scripts\python.exe'))
$pythonExe = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $pythonExe) { throw 'No virtual environment found. Run: python -m venv .venv' }
$nodeExe = (Get-Command node.exe -ErrorAction Stop).Source
if ($Install) {
    & $pythonExe -X utf8 -m pip install -r (Join-Path $backendPath 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed' }
    Push-Location $frontendPath
    try { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed' } } finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendPath 'node_modules\vite\bin\vite.js'))) { throw 'Run start-dev.ps1 -Install first' }
New-Item -ItemType Directory -Path $logPath -Force | Out-Null
Push-Location $backendPath
try { & $pythonExe -X utf8 -m app.core.init_env; if ($LASTEXITCODE -ne 0) { throw 'Environment initialization failed' } } finally { Pop-Location }
$backendUrl = "http://127.0.0.1:$BackendPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"
$displayHost = if ($FrontendPort -eq 5173) { 'localhost' } else { '127.0.0.1' }
$previousBackendPort = $env:COMMON_GROUND_BACKEND_PORT
$previousDevOrigins = $env:COMMON_GROUND_DEV_ORIGINS
$backendProcess = $null
$frontendProcess = $null
try {
    $env:COMMON_GROUND_BACKEND_PORT = [string]$BackendPort
    if ($BackendPort -ne 8000 -or $FrontendPort -ne 5173) {
        $env:COMMON_GROUND_DEV_ORIGINS = "$frontendUrl,http://localhost:$FrontendPort,$backendUrl,http://localhost:$BackendPort"
    }
    $backendProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-X', 'utf8', '-m', 'uvicorn', 'app.main:app', '--app-dir', ('"' + $backendPath + '"'), '--host', '127.0.0.1', '--port', $BackendPort) -WorkingDirectory $backendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'backend.log') -RedirectStandardError (Join-Path $logPath 'backend-error.log') -PassThru
    $viteEntry = Join-Path $frontendPath 'node_modules\vite\bin\vite.js'
    $frontendProcess = Start-Process -FilePath $nodeExe -ArgumentList @(('"' + $viteEntry + '"'), '--host', '127.0.0.1', '--port', $FrontendPort, '--strictPort') -WorkingDirectory $frontendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'frontend.log') -RedirectStandardError (Join-Path $logPath 'frontend-error.log') -PassThru
    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if ($backendProcess.HasExited -or $frontendProcess.HasExited) { throw "Server exited. Inspect logs in $logPath" }
        try {
            $null = Invoke-RestMethod -Uri "$backendUrl/health" -TimeoutSec 2
            $front = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2
            if ($front.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw "Startup timeout. Inspect logs in $logPath" }
    @(@{ id = $backendProcess.Id; started = $backendProcess.StartTime.ToUniversalTime().ToString('o') }, @{ id = $frontendProcess.Id; started = $frontendProcess.StartTime.ToUniversalTime().ToString('o') }) | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
    Write-Host "Frontend: http://${displayHost}:$FrontendPort"
    Write-Host "Backend:  http://${displayHost}:$BackendPort"
    Write-Host "Swagger:  http://${displayHost}:$BackendPort/docs"
    Write-Host 'Stop: powershell -ExecutionPolicy Bypass -File .\stop-dev.ps1'
} catch {
    if ($frontendProcess -and -not $frontendProcess.HasExited) { Stop-Process -Id $frontendProcess.Id }
    if ($backendProcess -and -not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id }
    throw
} finally {
    $env:COMMON_GROUND_BACKEND_PORT = $previousBackendPort
    $env:COMMON_GROUND_DEV_ORIGINS = $previousDevOrigins
}
