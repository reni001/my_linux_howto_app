import os
from pathlib import Path

from src.utils.runtime_paths import get_runtime_paths

def get_icon_path(filename):

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
