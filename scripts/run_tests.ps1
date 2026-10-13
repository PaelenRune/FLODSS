# Execute Backend Test Suite
$VenvPytest = "$PSScriptRoot\..\backend\.venv\Scripts\pytest.exe"
if (-not (Test-Path $VenvPytest)) {
    Write-Error "Pytest not found in virtual environment. Install dev dependencies first."
    exit 1
}

Write-Host "Running Backend Unit Tests..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot\..\backend"
& $VenvPytest tests -v
