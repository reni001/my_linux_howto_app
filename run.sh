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
# VERIFY ENV
# ----------------------------------------
echo "[INFO] Python in use:"
"$VENV_DIR/bin/python" --version

echo "[INFO] Executable:"
which python

# verify kivy installed
if ! "$VENV_DIR/bin/python" -c "import kivy" &> /dev/null; then
    echo "[ERROR] Kivy not installed in venv."
    echo "Run ./install.sh again."
    exit 1
fi

# ----------------------------------------
# ENSURE PYTHON PACKAGE STRUCTURE
# ----------------------------------------

if [ ! -f "$APP_DIR/src/__init__.py" ]; then
    echo "[WARNING] src/__init__.py missing → creating it"
    touch "$APP_DIR/src/__init__.py"
fi

# ----------------------------------------
# RUN APP
# ----------------------------------------
echo "[INFO] Starting application..."

cd "$APP_DIR"

"$VENV_DIR/bin/python" -m src.main
