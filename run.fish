#!/usr/bin/env fish

set APP_DIR (dirname (status -f))
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
