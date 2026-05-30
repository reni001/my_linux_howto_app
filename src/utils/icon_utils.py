import os
from pathlib import Path

from src.utils.runtime_paths import get_runtime_paths



def get_icon_path(filename):
    paths = get_runtime_paths()

    icons = paths["assets"] / "icons"
    user_icons = paths["assets"] / "user_icons"

    default_icon = icons / "default.png"

    if not filename:
        return str(default_icon)

    filename = str(filename).strip()
    if filename.lower() in ("", "nan", "none"):
        return str(default_icon)

    # ✅ private icons are explicitly marked with user_
    if filename.startswith("user_"):
        user_path = user_icons / filename
        if user_path.is_file():
            return str(user_path)

        # fallback just in case
        icon_path = icons / filename
        if icon_path.is_file():
            return str(icon_path)

        print(f"⚠️ Missing user icon file: {filename}")
        return str(default_icon)

    # ✅ official icons
    icon_path = icons / filename
    if icon_path.is_file():
        return str(icon_path)

    # fallback just in case
    user_path = user_icons / filename
    if user_path.is_file():
        return str(user_path)

    print(f"⚠️ Missing icon file: {filename}")
    return str(default_icon)

