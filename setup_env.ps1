# Creates a local virtual environment and installs all dependencies.
#
# Run from the project root:
#   powershell -ExecutionPolicy Bypass -File setup_env.ps1
#
# This is the ONLY place a venv gets created — it is never committed to
# git (see .gitignore). Re-run any time requirements*.txt changes.

$ErrorActionPreference = "Stop"

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3.12 -m venv .venv
} else {
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

Write-Host ""
Write-Host "Done. Activate later with: .\.venv\Scripts\Activate.ps1"
Write-Host "Run the app with:          python src\app\main.py"
Write-Host "Run the tests with:        pytest"
