$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
node (Join-Path $Root "scripts/start-dev.mjs")
