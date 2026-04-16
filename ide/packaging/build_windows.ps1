$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Mode = if ($args.Length -gt 0) { $args[0] } else { "standalone" }

if (-not (Test-Path $Python)) {
    throw "Python not found at $Python"
}

& $Python "$PSScriptRoot\build_nuitka.py" --mode $Mode
