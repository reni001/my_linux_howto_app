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
# INSTALL SYSTEM DEPENDENCIES
# ----------------------------------------

echo "[INFO] Detecting operating system..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=${ID_LIKE:-$ID}
else
    OS=$(uname -s)
fi

echo "[INFO] OS detected: $OS"

install_ubuntu() {
    echo "[INFO] Installing Ubuntu/Debian dependencies..."
    sudo apt update
    sudo apt install -y \
        python3-venv python3-dev build-essential \
        libgl1-mesa-dev libgles2-mesa-dev \
        libgstreamer1.0-dev gstreamer1.0-plugins-base \
        libmtdev-dev libjpeg-dev libpng-dev pkg-config
}

install_fedora() {
    echo "[INFO] Installing Fedora dependencies..."
    sudo dnf install -y \
        python3-devel gcc gcc-c++ make \
        SDL2 SDL2_image SDL2_ttf SDL2_mixer \
        mesa-libGL mesa-libGLES \
        gstreamer1 gstreamer1-plugins-base \
        mtdev-devel libjpeg-devel libpng-devel pkgconfig
}

install_arch() {
    echo "[INFO] Installing Arch dependencies..."
    sudo pacman -Sy --needed --noconfirm \
        python base-devel \
        sdl2 sdl2_image sdl2_ttf sdl2_mixer \
        mesa gst-plugins-base gst-libav \
        mtdev libjpeg-turbo libpng pkgconf
}

case "$OS" in
    *debian*) install_ubuntu ;;
    *fedora*) install_fedora ;;
    *arch*) install_arch ;;
    *)
        echo "[WARNING] Unsupported OS: $OS"
        ;;
esac

# ----------------------------------------
# PYTHON DETECTION
# ----------------------------------------

echo "[INFO] Detecting Python..."

if command -v python3.12 &> /dev/null; then
    PYTHON_BIN="python3.12"

elif command -v python3.11 &> /dev/null; then
    PYTHON_BIN="python3.11"

elif command -v python3.10 &> /dev/null; then
    PYTHON_BIN="python3.10"

elif command -v python3 &> /dev/null; then
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
        echo "[ERROR] Python too old (<3.8)"
        exit 1
    fi
    PYTHON_BIN="python3"

else
    echo "[ERROR] Python not found"
    exit 1
fi

echo "[INFO] Using $PYTHON_BIN"

# ----------------------------------------
# CREATE VENV
# ----------------------------------------

echo "[INFO] Creating virtual environment..."

if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_BIN -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ----------------------------------------
# INSTALL PYTHON DEPENDENCIES
# ----------------------------------------

echo "[INFO] Installing Python dependencies..."

pip install --upgrade pip setuptools wheel

if ! pip install -r requirements.txt; then
    echo "[WARNING] Fallback install..."
    pip install "kivy[base]" pillow requests firebase_admin
fi

pip list

# ----------------------------------------
# CREATE RUNTIME DIRECTORIES
# ----------------------------------------

mkdir -p "$DATA_DIR" "$ASSETS_DIR"

# ----------------------------------------
# COPY CONFIG + ASSETS
# ----------------------------------------

cp "$APP_DIR/config/firebase.json" "$DATA_DIR/firebase.json"

rsync -av --delete "$APP_DIR/assets/" "$ASSETS_DIR/" || cp -r "$APP_DIR/assets" "$ASSETS_DIR"


# ----------------------------------------
# ENSURE PYTHON PACKAGE STRUCTURE
# ----------------------------------------

if [ ! -f "$APP_DIR/src/__init__.py" ]; then
    echo "[INFO] Creating src/__init__.py"
    touch "$APP_DIR/src/__init__.py"
fi


chmod +x "$APP_DIR/run.sh"
chmod +x "$APP_DIR/run.fish"


# ----------------------------------------
# TEST RUN
# ----------------------------------------

echo "[INFO] Running first test..."

cd "$APP_DIR"

if "$VENV_DIR/bin/python" -m src.main; then
    echo "[INFO] ✅ App started successfully"
else
    echo "[WARNING] First run produced warnings"
fi

# ----------------------------------------
# DONE
# ----------------------------------------

echo ""
echo "✅ INSTALL COMPLETE"
echo ""
echo "Run with:"
echo "cd $APP_DIR && source venv/bin/activate && python -m src.main"
echo "or: ./run.sh"
