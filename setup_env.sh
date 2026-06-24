#!/usr/bin/env bash
# Creates a local virtual environment and installs all dependencies.
#
# Run from the project root:
#   ./setup_env.sh
#
# The shipped app targets Windows, but the CV/ML core can be developed on
# any OS — this script is for that. Never commit the resulting .venv/.

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo
echo "Done. Activate later with: source .venv/bin/activate"
echo "Run the app with:          python src/app/main.py"
echo "Run the tests with:        pytest"
