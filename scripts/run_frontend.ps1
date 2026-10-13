# Launch React + TypeScript Frontend Development Server
$env:Path = "$env:LOCALAPPDATA\Programs\nodejs;$env:Path"

Write-Host "Starting FLODSS Frontend Dev Server on http://localhost:3000..." -ForegroundColor Green
Set-Location "$PSScriptRoot\..\frontend"
npm.cmd run dev
