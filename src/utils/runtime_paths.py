import os
from pathlib import Path

APP_NAME = "linux-howto"


USER_DATA_DIR = Path(
    os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
) / APP_NAME
ASSETS_DIR = USER_DATA_DIR / "assets"
DATA_DIR = USER_DATA_DIR / "data"



def ensure_runtime_dirs():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_runtime_paths():
    ensure_runtime_dirs()
    return {
        "base": USER_DATA_DIR,
        "assets": ASSETS_DIR,
        "data": DATA_DIR,
        "icons": ASSETS_DIR / "icons",
    }

    
def get_icon_path(filename):
    #from src.runtime_paths import get_runtime_paths

    paths = get_runtime_paths()
    base = paths["assets"] / "icons"
    default_icon = base / "default.png"

    if not filename:
        return str(default_icon)

    filename = str(filename).strip()
    if filename.lower() in ("", "nan", "none"):
        return str(default_icon)

    icon_path = base / filename
    if not icon_path.is_file():
        print(f"⚠️ Missing icon → fallback used: {filename}")
        return str(default_icon)

    return str(icon_path)    
    

# ✅ PHASE 3 ADDITION (ONLY THIS)
def is_dev_mode():
    """
    DEV = running from Git checkout
    PROD = AppImage or copied folder
    """
    def is_dev_mode():
        try:
            return (Path(__file__).resolve().parent.parent / ".git").exists()
        except Exception:
                return False

