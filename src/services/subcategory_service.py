import json

from src.utils.runtime_paths import get_runtime_paths
from src.services.data_service import APP_DATA
from src.services.editor_service import add_topic_to_firebase
from src.services.data_service import update_local_topic_and_steps
from src.services.data_service import add_local_topic_and_steps  # optional if needed


def _get_path():
    return get_runtime_paths()["data"] / "subcategories.json"


def _norm(value):
    return str(value or "").strip().lower()


def load_subcategories():
    path = _get_path()
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_subcategories(data):
    path = _get_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_from_topics(app, overwrite=False):
    path = _get_path()

    if path.exists() and not overwrite:
        print("ℹ️ Subcategories already exist → skipping generation")
        return

    subs = {}

    for topic in app.APP_DATA.get("topics", []):
        sub = str(topic.get("Subcategory") or "").strip()
        icon = str(topic.get("Sub_Icon") or "").strip()   # ✅ CORRECT FIELD

        if not sub:
            continue

        key = _norm(sub)

        # keep first icon found unless empty
        if key not in subs:
            subs[key] = {
                "name": sub,
                "icon": icon or "howtolinux-icon.png"
            }

    data = list(subs.values())
    save_subcategories(data)
    print(f"✅ Generated {len(data)} subcategories")

def upsert_subcategory(name, icon):
    """
    Add new or update existing entry in subcategories.json only.
    """
    data = load_subcategories()
    norm_name = _norm(name)

    found = False
    for item in data:
        if _norm(item.get("name")) == norm_name:
            item["name"] = name
            item["icon"] = icon or item.get("icon", "howtolinux-icon.png")
            found = True
            break

    if not found:
        data.append({
            "name": name,
            "icon": icon or "howtolinux-icon.png"
        })

    save_subcategories(data)

def delete_subcategory_safe(name):
    """
    Deletes subcategory only if not used.
    Returns: (success: bool, reason: str)
    """

    if is_subcategory_used(name):
        return False, "Subcategory is used by topics"

    data = load_subcategories()
    data = [s for s in data if s["name"] != name]
    save_subcategories(data)

    return True, ""


def _steps_for_topic(app, topic_id):
    return [
        dict(step) for step in app.APP_DATA.get("steps", [])
        if str(step.get("Topic_ID") or "") == str(topic_id)
    ]


def apply_subcategory_change(app, old_name, new_name, new_icon):
    """
    Update subcategory registry AND all topics using that subcategory.
    Works for both local and official topics.
    """
    old_norm = _norm(old_name)
    new_name = str(new_name or "").strip()
    new_icon = str(new_icon or "").strip()

    if not new_name:
        raise ValueError("New subcategory name cannot be empty")

    # 1) update subcategory registry
    data = load_subcategories()
    replaced = False

    for item in data:
        if _norm(item.get("name")) == old_norm:
            item["name"] = new_name
            item["icon"] = new_icon or item.get("icon", "howtolinux-icon.png")
            replaced = True
            break

    if not replaced:
        data.append({
            "name": new_name,
            "icon": new_icon or "howtolinux-icon.png"
        })

    save_subcategories(data)

    # 2) update all topics using this subcategory
    for topic in app.APP_DATA.get("topics", []):
        if _norm(topic.get("Subcategory")) != old_norm:
            continue

        updated_topic = dict(topic)
        updated_topic["Subcategory"] = new_name
        updated_topic["Sub_Icon"] = new_icon

        # local topic
        if str(topic.get("source") or "") == "user":
            topic_id = str(updated_topic.get("Topic_ID") or "")
            steps = _steps_for_topic(app, topic_id)
            update_local_topic_and_steps(topic_id, updated_topic, steps)

        # official topic
        else:
            updated_topic["_key"] = topic.get("_key")
            updated_topic["Topic_ID"] = topic.get("Topic_ID")
            add_topic_to_firebase(updated_topic, overwrite=True)

def is_subcategory_used(name):
    name = str(name or "").strip().lower()

    for topic in APP_DATA.get("topics", []):
        if str(topic.get("Subcategory") or "").strip().lower() == name:
            return True

    return False

def delete_subcategory_safe(name):
    """
    Deletes subcategory only if not used.
    Returns: (success: bool, reason: str)
    """
    if is_subcategory_used(name):
        return False, "Subcategory is used"

    data = load_subcategories()
    data = [s for s in data if s["name"] != name]
    save_subcategories(data)

    return True, ""


def count_subcategory_usage(name):
    name = str(name or "").strip().lower()
    count = 0

    for topic in APP_DATA.get("topics", []):
        if str(topic.get("Subcategory") or "").strip().lower() == name:
            count += 1

    return count
