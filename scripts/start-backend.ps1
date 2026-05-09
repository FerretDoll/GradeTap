$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root "backend")

conda run -p (Join-Path $Root ".conda") python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
