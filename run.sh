#!/usr/bin/env bash

set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"

echo "=========================================="
echo " Linux HowTo App – Run"
echo "=========================================="

# ----------------------------------------
# CHECK VENV
# ----------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo "[ERROR] venv not found."
    echo "Run ./install.sh first."
    exit 1
fi

# ----------------------------------------
# ACTIVATE VENV
# ----------------------------------------
echo "[INFO] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# ----------------------------------------
# VERIFY PYTHON
# ----------------------------------------
echo "[INFO] Python in use:"
python --version
echo "[INFO] Executable:"
which python

# ----------------------------------------
# RUN APP
# ----------------------------------------
echo "[INFO] Starting application..."
python -m src.main

