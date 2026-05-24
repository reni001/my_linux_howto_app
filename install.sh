#!/usr/bin/env bash

set -e

echo ""
echo "=========================================="
echo " Linux HowTo App – Installer"
echo "=========================================="
echo ""

# ----------------------------------------
# PATHS (FIXED)
# ----------------------------------------

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENV_DIR="$APP_DIR/venv"
BASE_DIR="$HOME/.local/share/linux-howto"
DATA_DIR="$BASE_DIR/data"
ASSETS_DIR="$BASE_DIR/assets"

# ----------------------------------------
# DETECT DISPLAY SERVER (Wayland vs X11)
# ----------------------------------------

echo "[INFO] Detecting display server..."

SESSION_TYPE="${XDG_SESSION_TYPE:-x11}"
echo "[INFO] Session type: $SESSION_TYPE"

if [ "$SESSION_TYPE" = "wayland" ]; then
    echo "[INFO] Wayland detected → forcing X11 compatibility for Kivy"
    export KIVY_GL_BACKEND=gl
    export SDL_VIDEODRIVER=${SDL_VIDEODRIVER:-x11}
else
    echo "[INFO] X11 detected"
fi

# ----------------------------------------
# PYTHON AUTO DETECTION
# ----------------------------------------

echo "[INFO] Detecting Python..."


echo "[INFO] Detecting Python..."

if command -v python3.12 &> /dev/null; then
    PYTHON_BIN="python3.12"
    echo "[INFO] ✅ Using Python 3.12 (recommended)"

elif command -v python3.11 &> /dev/null; then
    PYTHON_BIN="python3.11"
    echo "[INFO] ✅ Using Python 3.11"

elif command -v python3.10 &> /dev/null; then
    PYTHON_BIN="python3.10"
    echo "[INFO] ✅ Using Python 3.10"

elif command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

    echo "[WARNING] ⚠️ Using system Python $PY_VERSION"
    echo "[WARNING] Some features (sync, Kivy, pandas) may behave differently"

    PYTHON_BIN="python3"

else
    echo "[ERROR] ❌ Python not found. Please install Python 3.8+"
    exit 1
fi


echo "[INFO] Using $PYTHON_BIN"

# ----------------------------------------
# CREATE VIRTUAL ENVIRONMENT
# ----------------------------------------

echo "[INFO] Creating virtual environment..."

if [ -d "$VENV_DIR" ]; then
    echo "[INFO] Reusing existing virtual environment"
else
    $PYTHON_BIN -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# ----------------------------------------
# INSTALL DEPENDENCIES
# ----------------------------------------

echo "[INFO] Installing dependencies..."
echo "[INFO] If Kivy installation fails, install system deps:"
echo " Arch: sudo pacman -S base-devel sdl2 sdl2_image sdl2_ttf sdl2_mixer mesa"
echo " Ubuntu: sudo apt install build-essential libsdl2-dev"


if ! ping -c 1 github.com &> /dev/null; then
    echo "[ERROR] No internet connection detected"
    exit 1
fi

pip install --upgrade pip setuptools wheel
pip install kivy pandas requests firebase-admin openpyxl cython


# ----------------------------------------
# CREATE RUNTIME DIRECTORIES
# ----------------------------------------

echo "[INFO] Creating runtime directories..."

mkdir -p "$DATA_DIR"
mkdir -p "$ASSETS_DIR"

# ----------------------------------------
# COPY firebase.json (CRITICAL PART)
# ----------------------------------------

echo "[INFO] Installing firebase.json..."

if [ -f "$APP_DIR/config/firebase.json" ]; then
    cp "$APP_DIR/config/firebase.json" "$DATA_DIR/firebase.json"
    echo "[INFO] ✅ firebase.json copied to:"
    echo "       $DATA_DIR/firebase.json"
else
    echo "[ERROR] ❌ firebase.json NOT found!"
    echo ""
    echo "Expected at:"
    echo "   $APP_DIR/config/firebase.json"
    echo ""
    echo "Fix:"
    echo "   Make sure the file exists after cloning the repo."
    echo ""
    exit 1
fi

#-----------------------------------------
# COPY assets
#-----------------------------------------

echo "[INFO] Copying assets to runtime directory..."

ASSETS_SRC="$APP_DIR/assets"
ASSETS_DST="$HOME/.local/share/linux-howto/assets"

mkdir -p "$ASSETS_DST"

if [ -d "$ASSETS_SRC" ]; then

    if command -v rsync &> /dev/null; then
        rsync -av --delete "$ASSETS_SRC/" "$ASSETS_DST/"
    else
        echo "[WARNING] rsync not found → using cp fallback"
        rm -rf "$ASSETS_DST"
        cp -r "$ASSETS_SRC" "$ASSETS_DST"
    fi

    echo "[INFO] ✅ Assets (icons + screenshots) copied successfully"
else
    echo "[ERROR] ❌ Assets folder not found at: $ASSETS_SRC"
    exit 1
fi

# ----------------------------------------
# VERIFY INSTALLATION (VERY IMPORTANT)
# ----------------------------------------

echo "[INFO] Verifying installation..."

if [ -f "$DATA_DIR/firebase.json" ]; then
    echo "[INFO] ✅ firebase.json is correctly installed"
else
    echo "[ERROR] ❌ firebase.json missing after copy!"
    exit 1
fi

# ----------------------------------------
# OPTIONAL FIRST RUN TEST
# ----------------------------------------

echo "[INFO] Running first test..."

if $PYTHON_BIN -m src.main; then
    echo "[INFO] ✅ App started successfully"
else
    echo "[WARNING] App exited with warnings (can be normal on first run)"
fi

# ----------------------------------------
# DONE
# ----------------------------------------

echo ""
echo "=========================================="
echo " ✅ INSTALLATION COMPLETE"
echo "=========================================="
echo ""
echo "To run the app:"
echo ""
echo "cd $APP_DIR"
echo "source venv/bin/activate"
echo "python -m src.main"
echo ""
echo "Or use:"
echo "   ./run.sh"
echo ""

echo "[INFO] Verifying assets..."

if [ -d "$ASSETS_DST/icons" ] && [ "$(ls -A "$ASSETS_DST/icons")" ]; then
    echo "[INFO] ✅ Icons installed"
else
    echo "[WARNING] ⚠️ Icons missing"
fi

