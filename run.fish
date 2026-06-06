#!/usr/bin/env fish

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
# VERIFY ENV
# ----------------------------------------
echo "[INFO] Python in use:"
$VENV_DIR/bin/python --version

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
$VENV_DIR/bin/python -m src.main
