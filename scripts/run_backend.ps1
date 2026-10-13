# Launch FastAPI Backend Server
$VenvPython = "$PSScriptRoot\..\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment python not found at $VenvPython. Run installation first."
    exit 1
}

Write-Host "Starting FLODSS FastAPI Server on http://127.0.0.1:8000..." -ForegroundColor Cyan
& $VenvPython -m uvicorn app.main:app --app-dir "$PSScriptRoot\..\backend" --reload --host 127.0.0.1 --port 8000
