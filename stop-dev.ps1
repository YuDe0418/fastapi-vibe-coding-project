$ErrorActionPreference = 'Stop'
$recordPath = Join-Path $PSScriptRoot 'data\dev-logs\processes.json'
if (-not (Test-Path -LiteralPath $recordPath)) { Write-Host 'No recorded development servers.'; exit }
$records = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
foreach ($record in $records) {
    $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().ToString('o') -eq $record.started) {
        Stop-Process -Id $process.Id
        Write-Host "Stopped development server $($process.Id)"
    }
}
Remove-Item -LiteralPath $recordPath
