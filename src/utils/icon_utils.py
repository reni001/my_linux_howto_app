import os
from pathlib import Path

from src.utils.runtime_paths import get_runtime_paths


def get_icon_path(filename):
    paths = get_runtime_paths()

    icons_core = paths["assets"] / "icons_core"
    icons = paths["assets"] / "icons"
    user_icons = paths["assets"] / "user_icons"

    # ✅ fallback now from core (IMPORTANT)
    default_icon = icons_core / "default.png"

    if not filename:
        return str(default_icon)

    filename = str(filename).strip()
    if filename.lower() in ("", "nan", "none"):
        return str(default_icon)

    # ✅ 1 — CORE icons (NEW!)
    core_path = icons_core / filename
    if core_path.is_file():
        return str(core_path)

    # ✅ 2 — user icons (if prefixed)
    if filename.startswith("user_"):
        user_path = user_icons / filename
        if user_path.is_file():
            return str(user_path)

        # fallback
        icon_path = icons / filename
        if icon_path.is_file():
            return str(icon_path)

        print(f"⚠ Missing user icon file: {filename}")
        return str(default_icon)

    # ✅ 3 — official icons
    icon_path = icons / filename
    if icon_path.is_file():
        return str(icon_path)

    # ✅ 4 — fallback: user icons
    user_path = user_icons / filename
    if user_path.is_file():
        return str(user_path)

    # ✅ 5 — final fallback
    print(f"⚠ Missing icon file: {filename}")
    return str(default_icon)
