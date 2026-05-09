$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root "frontend")

conda run -p (Join-Path $Root ".conda") npm run dev -- --host 127.0.0.1 --port 5173
