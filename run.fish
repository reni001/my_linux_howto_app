#!/usr/bin/env fish

set -e

set APP_DIR (cd (dirname (realpath (status -f))) ; pwd)
set VENV_DIR "$APP_DIR/venv"

echo "=========================================="
echo " Linux HowTo App – Run (Fish)"
echo "=========================================="

# ----------------------------------------
# CHECK VENV
# ----------------------------------------
if not test -d $VENV_DIR
    echo "[ERROR] venv not found"
    echo "Run ./install.sh first"
    exit 1
end

# ----------------------------------------
# ACTIVATE VENV
# ----------------------------------------
echo "[INFO] Activating virtual environment..."
source $VENV_DIR/bin/activate.fish

# ----------------------------------------
# DETECT WSL ENVIRONMENT
# ----------------------------------------

set IS_WSL false

if grep -qi microsoft /proc/version 2>/dev/null
    set IS_WSL true
    echo "[INFO] WSL environment detected"
end

# ----------------------------------------
# WSL DISPLAY CONFIGURATION
# ----------------------------------------

if test "$IS_WSL" = true; and test -z "$DISPLAY"
    set -x DISPLAY (grep nameserver /etc/resolv.conf | awk '{print $2}'):0
    set -x LIBGL_ALWAYS_INDIRECT 1

    echo "[INFO] DISPLAY set to $DISPLAY"
end

# ----------------------------------------
# GUI CHECK
# ----------------------------------------

echo "[INFO] DISPLAY = " (test -z "$DISPLAY"; and echo "not set"; or echo $DISPLAY)

set GUI_AVAILABLE true

if test -z "$DISPLAY"
    set GUI_AVAILABLE false
end

# ----------------------------------------
# WSL GUI WARNING
# ----------------------------------------

if test "$IS_WSL" = true; and test "$GUI_AVAILABLE" = false
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
    echo "   set -x DISPLAY (grep nameserver /etc/resolv.conf | awk '{print \$2}'):0"
    echo ""
    echo "4. Run the app again"
    echo ""
end

# ----------------------------------------
# VERIFY ENV
# ----------------------------------------
echo "[INFO] Python in use:"
$VENV_DIR/bin/python --version

echo "[INFO] Executable:"
which python

# verify kivy
if not $VENV_DIR/bin/python -c "import kivy" ^/dev/null
    echo "[ERROR] Kivy not installed."
    echo "Run ./install.sh again."
    exit 1
end

# ----------------------------------------
# ENSURE PYTHON PACKAGE STRUCTURE
# ----------------------------------------

if not test -f "$APP_DIR/src/__init__.py"
    echo "[WARNING] src/__init__.py missing → creating it"
    touch "$APP_DIR/src/__init__.py"
end

# ----------------------------------------
# RUN APP
# ----------------------------------------
echo "[INFO] Starting application..."

cd $APP_DIR

if test "$GUI_AVAILABLE" = true
    $VENV_DIR/bin/python -m src.main
else
    echo "[ERROR] Cannot start GUI application (no display)"
    echo "See instructions above to enable GUI in WSL"
    exit 1
end
