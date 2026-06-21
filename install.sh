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
# DETECT WSL ENVIRONMENT
# ----------------------------------------

IS_WSL=false

if grep -qi microsoft /proc/version 2>/dev/null || \
   grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
    IS_WSL=true
    echo "[INFO] ✅ WSL environment detected"
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

    if [ "$IS_WSL" = true ]; then
        echo "[INFO] ⚙️ WSL detected → minimal GUI dependencies"
        echo "[INFO] Clipboard handled by Windows → skipping xclip"

        sudo apt install -y \
            python3-venv python3-dev build-essential \
            libgl1 libgles2 \
            || echo "[WARNING] dependency install failed"

    else
        echo "[INFO] Standard Linux install"

        sudo apt install -y \
            python3-venv python3-dev build-essential \
            libgl1-mesa-dev libgles2-mesa-dev \
            libgstreamer1.0-dev gstreamer1.0-plugins-base \
            libmtdev-dev libjpeg-dev libpng-dev pkg-config \
            xdg-utils \
            xclip \
            || echo "[WARNING] dependency install failed"
    fi
}

install_fedora() {
    echo "[INFO] Installing Fedora dependencies..."
    sudo dnf install -y \
        python3 python3-devel python3-pip python3-virtualenv \
        gcc gcc-c++ make \
        SDL2 SDL2_image SDL2_ttf SDL2_mixer \
        mesa-libGL mesa-libGLES \
        gstreamer1 gstreamer1-plugins-base \
        mtdev-devel libjpeg-devel libpng-devel pkgconfig
}

install_arch() {
    echo "[INFO] Installing Arch dependencies..."
    sudo pacman -Sy --needed --noconfirm \
        python python-virtualenv base-devel \
        sdl2 sdl2_image sdl2_ttf sdl2_mixer \
        mesa gst-plugins-base gst-libav \
        mtdev libjpeg-turbo libpng pkgconf
}

case "$OS" in
    *debian*) install_ubuntu ;;
    *fedora*) install_fedora ;;
    *arch*) install_arch ;;
    *suse*|*opensuse*)
        echo "[INFO] Detected SUSE/openSUSE"
        echo ""
        echo "Please install dependencies manually:"
        echo "  sudo zypper install python3-devel gcc SDL2 SDL2_image SDL2_ttf SDL2_mixer"
        echo ""
        echo "Ensure Python 3.9+ is installed"
        ;;
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
    echo "[INFO] ✅ Using Python 3.12"

elif command -v python3.11 &> /dev/null; then
    PYTHON_BIN="python3.11"
    echo "[INFO] ✅ Using Python 3.11"

elif command -v python3.10 &> /dev/null; then
    PYTHON_BIN="python3.10"
    echo "[INFO] ✅ Using Python 3.10"

elif command -v python3.9 &> /dev/null; then
    PYTHON_BIN="python3.9"
    echo "[INFO] ✅ Using Python 3.9"

elif command -v python3 &> /dev/null && \
     python3 -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)"; then

    PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

    echo "[INFO] Using system Python $PY_VERSION"

    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)"; then
        echo ""
        echo "[ERROR] Python 3.9+ required for this app"
        echo ""
        echo "Detected: Python $PY_VERSION"
        echo ""
        echo "➡️ Fix (Ubuntu 20.04):"
        echo "   sudo apt install python3.9 python3.9-venv python3.9-dev"
        echo ""
        echo "➡️ Then re-run install.sh"
        echo ""
        exit 1
    fi

    PYTHON_BIN="python3"

else
    echo "[ERROR] Python not found"
    exit 1
fi

echo "[INFO] Using $PYTHON_BIN"

# ----------------------------------------
# ENSURE MINIMUM PYTHON VERSION
# ----------------------------------------

if [[ "$PYTHON_BIN" == "python3" ]]; then
    PY_OK=$($PYTHON_BIN -c "import sys; print(int(sys.version_info >= (3,9)))")

    if [ "$PY_OK" -ne 1 ]; then
        echo "[INFO] Python version too old → installing Python 3.9..."

        sudo apt update
        sudo apt install -y python3.9 python3.9-venv python3.9-dev \
            || {
                echo "[ERROR] Could not install Python 3.9 automatically"
                echo "Please install a compatible Python version (3.10–3.12 recommended)"
                exit 1
            }

        PYTHON_BIN="python3.9"
    fi
fi

# ----------------------------------------
# CREATE VENV
# ----------------------------------------

echo "[INFO] Creating virtual environment..."


if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating venv using $PYTHON_BIN"
    $PYTHON_BIN -m venv "$VENV_DIR" || {
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    }
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

#pip list

# ----------------------------------------
# CREATE RUNTIME DIRECTORIES
# ----------------------------------------

mkdir -p "$DATA_DIR" "$ASSETS_DIR"

# ----------------------------------------
# COPY CONFIG + ASSETS
# ----------------------------------------

cp "$APP_DIR/config/firebase.json" "$DATA_DIR/firebase.json"

if command -v rsync &> /dev/null; then
    rsync -av "$APP_DIR/assets/" "$ASSETS_DIR/"
else
    echo "[INFO] rsync not found → using cp fallback"
    cp -r "$APP_DIR/assets" "$ASSETS_DIR"
fi

# ----------------------------------------
# CREATE VERSION FILE (IMPORTANT)
# ----------------------------------------

echo "Creating version file..."

echo "2.5.0" > "$DATA_DIR/version.txt"

echo "[INFO] version.txt created with version 2.5.0"


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
# GUI CHECK / WSL WARNING
# ----------------------------------------

if [ "$IS_WSL" = true ] && [ -z "$DISPLAY" ]; then
    echo ""
    echo "⚠️  GUI NOT CONFIGURED IN WSL"
    echo ""
    echo "Your application installed successfully, but GUI support is not active."
    echo ""

    echo "✅ FIX (Windows 11 - recommended):"
    echo "Run in PowerShell (outside WSL):"
    echo ""
    echo "  wsl --update"
    echo "  wsl --shutdown"
    echo ""
    echo "Then restart WSL and run the app again using:"
    echo "  ./run.sh"
    echo ""

    echo "✅ FIX (Windows 10 or fallback):"
    echo "1. Install VcXsrv (X server)"
    echo "2. Start VcXsrv"
    echo "3. In WSL run:"
    echo ""
    echo "   export DISPLAY=\$(grep nameserver /etc/resolv.conf | awk '{print \$2}'):0"
    echo ""
    echo "4. Run:"
    echo "   ./run.sh"
    echo ""
fi

# ----------------------------------------
# TEST RUN
# ----------------------------------------

echo "[INFO] Skipping auto-run test..."

if [ "$IS_WSL" = false ]; then
    if "$VENV_DIR/bin/python" -m src.main; then
        echo "[INFO] ✅ App started successfully"
    else
        echo "[WARNING] First run produced warnings"
    fi
else
    echo "[INFO] Run manually in WSL with:"
    echo "  ./run.sh"
fi


# ----------------------------------------
# DONE
# ----------------------------------------

echo ""
echo "✅ INSTALL COMPLETE"
echo ""
echo "✔ Python version: $("$VENV_DIR/bin/python" --version)"
echo ""
echo "Run with:"
echo "cd $APP_DIR && source venv/bin/activate && python -m src.main"
echo "or: ./run.sh"


if [ "$IS_WSL" = true ]; then
    echo ""
    echo "------------------------------------------"
    echo " WSL Notes"
    echo "------------------------------------------"
    echo ""
    echo "✔ Files open in Windows apps automatically"
    echo "✔ Browser links open in Windows browser"
    echo ""
    echo "If something does not open:"
    echo "  Ensure Windows default apps are configured"
    echo ""
fi
