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
# DETECT WSL ENVIRONMENT
# ----------------------------------------

IS_WSL=false

if grep -qi microsoft /proc/version 2>/dev/null; then
    IS_WSL=true
    echo "[INFO] WSL environment detected"
fi

# ----------------------------------------
# WSL DISPLAY CONFIGURATION
# ----------------------------------------

if [ "$IS_WSL" = true ] && [ -z "$DISPLAY" ]; then
    # Auto-set DISPLAY for X server / WSLg fallback
    export DISPLAY=$(grep nameserver /etc/resolv.conf | awk '{print $2}'):0
    export LIBGL_ALWAYS_INDIRECT=1

    echo "[INFO] DISPLAY set to $DISPLAY"
fi

# ----------------------------------------
# GUI CHECK
# ----------------------------------------
echo "[INFO] DISPLAY = ${DISPLAY:-not set}"

GUI_AVAILABLE=true

if [ -z "$DISPLAY" ]; then
    GUI_AVAILABLE=false
fi

# ----------------------------------------
# WSL GUI WARNING
# ----------------------------------------

if [ "$IS_WSL" = true ] && [ "$GUI_AVAILABLE" = false ]; then
    echo ""
    echo "⚠️  GUI NOT AVAILABLE IN WSL"
    echo ""
    echo "Your system does not have a working display server."
    echo ""
    echo "✅ FIX (Windows 11 - recommended):"
    echo "Run in PowerShell:"
    echo ""
    echo "  wsl --update"
    echo "  wsl --shutdown"
    echo ""
    echo "Then restart WSL and run the app again."
    echo ""
    echo "✅ FIX (Windows 10 or fallback):"
    echo "1. Install VcXsrv (X server)"
    echo "2. Start VcXsrv on Windows"
    echo "3. Run in WSL:"
    echo ""
    echo "   export DISPLAY=\$(grep nameserver /etc/resolv.conf | awk '{print \$2}'):0"
    echo ""
    echo "4. Run the app again"
    echo ""
fi

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


if [ "$GUI_AVAILABLE" = true ]; then
    "$VENV_DIR/bin/python" -m src.main
else
    echo "[ERROR] Cannot start GUI application (no display)"
    echo "See instructions above to enable GUI in WSL"
    exit 1
fi

