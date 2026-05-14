from pathlib import Path

APP_NAME = "linux-howto"

USER_DATA_DIR = Path.home() / ".local" / "share" / APP_NAME
ASSETS_DIR = USER_DATA_DIR / "assets"
DATA_DIR = USER_DATA_DIR / "data"



def ensure_runtime_dirs():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_runtime_paths():
    ensure_runtime_dirs()
    return {
        "assets": ASSETS_DIR,
        "data": DATA_DIR,
    }
    
def get_icon_path(filename):
    from src.runtime_paths import get_runtime_paths

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
        print(f"⚠️ Missing icon file: {icon_path}")
        return str(default_icon)

    return str(icon_path)    
    


# ✅ PHASE 3 ADDITION (ONLY THIS)
def is_dev_mode():
    """
    DEV = running from Git checkout
    PROD = AppImage or copied folder
    """
    return (Path.cwd() / ".git").exists()    
