#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Kill all processes using MCP server ports (8000-8003)

.DESCRIPTION
    This script finds and terminates all processes listening on ports 8000, 8001, 8002, and 8003.
    Useful for cleaning up server processes before starting new ones.

.EXAMPLE
    .\kill_servers.ps1
    Kills all processes on ports 8000-8003
#>

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "  Killing MCP Server Processes" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

$ports = @(8000, 8001, 8002, 8003)
$killedAny = $false

foreach ($port in $ports) {
    Write-Host "Checking port $port..." -NoNewline
    
    # Find processes using this port
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        
        foreach ($pid in $pids) {
            try {
                $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($process) {
                    $processName = $process.ProcessName
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                    Write-Host " [KILLED]" -ForegroundColor Red
                    Write-Host "  └─ Process: $processName (PID: $pid)" -ForegroundColor Gray
                    $killedAny = $true
                }
            }
            catch {
                Write-Host " [ERROR]" -ForegroundColor Red
                Write-Host "  └─ Failed to kill PID $pid : $_" -ForegroundColor Gray
            }
        }
    }
    else {
        Write-Host " [FREE]" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan

if ($killedAny) {
    Write-Host "  All server processes terminated" -ForegroundColor Green
} else {
    Write-Host "  No processes found on ports 8000-8003" -ForegroundColor Yellow
}

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""
