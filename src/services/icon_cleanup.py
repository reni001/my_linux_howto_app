from src.utils.runtime_paths import get_runtime_paths

def find_unused_icons(app_data):
    """
    Returns lists of unused icons and screenshots WITHOUT deleting them.
    """

    paths = get_runtime_paths()

    icons_dir = paths["assets"] / "icons"
    user_dir = paths["assets"] / "user_icons"
    screens_dir = paths["assets"] / "screenshots"

    used_icons = set()
    used_screenshots = set()

    for topic in app_data.get("topics", []):
        for key in ["Topic_Icon", "Cat_Icon", "Sub_Icon"]:
            name = str(topic.get(key) or "").strip()
            if name:
                used_icons.add(name)

    for step in app_data.get("steps", []):
        shot = str(step.get("Screenshot") or "").strip()
        if shot:
            used_screenshots.add(shot)

    unused_icons = []
    unused_screenshots = []

    for folder in [icons_dir, user_dir]:
        if folder.exists():
            for file in folder.iterdir():
                if file.is_file() and file.name not in used_icons:
                    unused_icons.append(file.name)

    if screens_dir.exists():
        for file in screens_dir.iterdir():
            if file.is_file() and file.name not in used_screenshots:
                unused_screenshots.append(file.name)

    return unused_icons, unused_screenshots


def clean_unused_icons(app_data):
    """
    Remove unused icons from:
      - icons/
      - user_icons/
    and unused screenshots from:
      - screenshots/

    icons_core/ is NEVER touched.
    """

    paths = get_runtime_paths()

    icons_dir = paths["assets"] / "icons"
    user_dir = paths["assets"] / "user_icons"
    screens_dir = paths["assets"] / "screenshots"

    used_icons = set()
    used_screenshots = set()

    # ✅ collect used icons
    for topic in app_data.get("topics", []):
        for key in ["Topic_Icon", "Cat_Icon", "Sub_Icon"]:
            name = str(topic.get(key) or "").strip()
            if name:
                used_icons.add(name)

    # ✅ collect used screenshots
    for step in app_data.get("steps", []):
        shot = str(step.get("Screenshot") or "").strip()
        if shot:
            used_screenshots.add(shot)

    deleted_icons = []
    deleted_screenshots = []

    # ✅ clean icons (dynamic only)
    for folder in [icons_dir, user_dir]:
        if folder.exists():
            for file in folder.iterdir():
                if file.is_file() and file.name not in used_icons:
                    try:
                        file.unlink()
                        deleted_icons.append(file.name)
                    except Exception as e:
                        print(f"⚠️ Failed deleting {file}: {e}")

    # ✅ clean screenshots
    if screens_dir.exists():
        for file in screens_dir.iterdir():
            if file.is_file() and file.name not in used_screenshots:
                try:
                    file.unlink()
                    deleted_screenshots.append(file.name)
                except Exception as e:
                    print(f"⚠️ Failed deleting {file}: {e}")

    return {
        "icons": len(deleted_icons),
        "screenshots": len(deleted_screenshots)
    }


def delete_user_icon_if_unused(app_data, icon_filename, removed_topic_id):
    """
    Delete user icon if no other topic uses it.
    """

    if not icon_filename:
        return

    still_used = False

    for topic in app_data.get("topics", []):
        if str(topic.get("Topic_ID") or "") == str(removed_topic_id):
            continue

        if str(topic.get("Topic_Icon") or "") == str(icon_filename):
            still_used = True
            break

    if still_used:
        return

    paths = get_runtime_paths()
    icon_path = paths["assets"] / "user_icons" / icon_filename

    try:
        if icon_path.exists():
            icon_path.unlink()
    except Exception as e:
        print(f"⚠️ Could not delete icon {icon_path}: {e}")
