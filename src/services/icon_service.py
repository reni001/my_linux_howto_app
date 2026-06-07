import shutil
from pathlib import Path
from src.utils.runtime_paths import get_runtime_paths



def get_icon_path(filename: str) -> str:
    """
    Resolve icons in this order:
    1. icons_core
    2. icons
    3. user_icons
    4. fallback
    """
    paths = get_runtime_paths()

    core = paths["assets"] / "icons_core" / filename
    if core.exists():
        return str(core)

    icons = paths["assets"] / "icons" / filename
    if icons.exists():
        return str(icons)

    user = paths["assets"] / "user_icons" / filename
    if user.exists():
        return str(user)

    fallback = paths["assets"] / "icons_core" / "howtolinux-icon.png"
    return str(fallback)


def copy_icon_to_core(src_path: str) -> str:
    """
    Copy a chosen icon into assets/icons_core and return the filename.
    Reuse existing file if already present.
    """
    if not src_path:
        return ""

    paths = get_runtime_paths()
    core_dir = paths["assets"] / "icons_core"
    core_dir.mkdir(parents=True, exist_ok=True)

    filename = Path(src_path).name
    target = core_dir / filename

    if not target.exists():
        shutil.copy2(src_path, target)

    return filename


def copy_user_icon_to_official(icon_filename: str) -> str:
    if not icon_filename:
        return ""

    paths = get_runtime_paths()
    user_icon = paths["assets"] / "user_icons" / icon_filename
    official_dir = paths["assets"] / "icons"
    official_dir.mkdir(parents=True, exist_ok=True)

    official_target = official_dir / icon_filename

    if official_target.exists():
        return official_target.name

    if user_icon.exists():
        shutil.copy2(user_icon, official_target)
        return official_target.name

    return icon_filename


def copy_official_icon_to_user_icons(icon_filename: str) -> str:
    if not icon_filename:
        return ""

    paths = get_runtime_paths()
    official_dir = paths["assets"] / "icons"
    user_dir = paths["assets"] / "user_icons"
    user_dir.mkdir(parents=True, exist_ok=True)

    src = official_dir / icon_filename
    dest = user_dir / icon_filename

    if dest.exists():
        return dest.name

    if src.exists():
        shutil.copy2(src, dest)
        return dest.name

    return icon_filename


def delete_official_icon_if_unused(app_data, icon_filename: str, removed_topic_id: str):
    if not icon_filename:
        return

    still_used = False

    for topic in app_data.get("topics", []):
        if str(topic.get("Topic_ID")) == str(removed_topic_id):
            continue
        if str(topic.get("source")) == "user":
            continue
        if str(topic.get("Topic_Icon")) == str(icon_filename):
            still_used = True
            break

    if still_used:
        return

    paths = get_runtime_paths()
    icon_path = paths["assets"] / "icons" / icon_filename

    if icon_path.exists():
        icon_path.unlink()

