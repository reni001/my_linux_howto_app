import json
from src.utils.runtime_paths import get_runtime_paths
from src.services.data_service import APP_DATA
from src.services.editor_service import add_topic_to_firebase
from src.services.data_service import update_local_topic_and_steps



def _get_path():
    return get_runtime_paths()["data"] / "categories.json"


def _norm(value):
    return str(value or "").strip().lower()


def load_categories():
    path = _get_path()
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_categories(data):
    path = _get_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_categories_from_topics(app, overwrite=False):
    path = _get_path()

    print("DEBUG category_service -> target path:", path)
    print("DEBUG category_service -> topics count:", len(app.APP_DATA.get("topics", [])))

    if path.exists() and not overwrite:
        print("ℹ Categories already exist → skipping generation")
        return

    cats = {}

    for topic in app.APP_DATA.get("topics", []):
        cat = str(topic.get("Category") or "").strip()
        icon = str(topic.get("Cat_Icon") or "").strip()

        print("DEBUG category topic ->", cat, "| icon:", icon)

        if not cat:
            continue

        key = _norm(cat)

        if key not in cats:
            cats[key] = {
                "name": cat,
                "icon": icon or "howtolinux-icon.png"
            }

    data = list(cats.values())

    print("DEBUG category_service -> generated data:", data)

    save_categories(data)
    print(f"✅ Generated {len(data)} categories")


# ----------------------------
# USAGE
# ----------------------------
def is_category_used(name):
    name = _norm(name)

    for topic in APP_DATA.get("topics", []):
        if _norm(topic.get("Category")) == name:
            return True

    return False


def count_category_usage(name):
    name = _norm(name)
    count = 0

    for topic in APP_DATA.get("topics", []):
        if _norm(topic.get("Category")) == name:
            count += 1

    return count


# ----------------------------
# CRUD
# ----------------------------
def upsert_category(name, icon):
    data = load_categories()
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

    save_categories(data)


def delete_category_safe(name):
    if is_category_used(name):
        return False, "Category is used"

    data = load_categories()
    data = [c for c in data if c["name"] != name]
    save_categories(data)

    return True, ""


# ----------------------------
# APPLY CHANGE
# ----------------------------
def apply_category_change(app, old_name, new_name, new_icon):

    old_norm = _norm(old_name)
    new_name = str(new_name or "").strip()
    new_icon = str(new_icon or "").strip()

    if not new_name:
        return

    # ✅ update json
    data = load_categories()
    replaced = False

    for item in data:
        if _norm(item.get("name")) == old_norm:
            item["name"] = new_name
            item["icon"] = new_icon or item.get("icon", "")
            replaced = True
            break

    if not replaced:
        data.append({
            "name": new_name,
            "icon": new_icon
        })

    save_categories(data)

    # ✅ update topics
    for topic in app.APP_DATA.get("topics", []):
        if _norm(topic.get("Category")) != old_norm:
            continue

        updated_topic = dict(topic)
        updated_topic["Category"] = new_name
        updated_topic["Cat_Icon"] = new_icon

        if str(topic.get("source") or "") == "user":
            topic_id = str(updated_topic.get("Topic_ID") or "")
            steps = [
                dict(s) for s in app.APP_DATA.get("steps", [])
                if str(s.get("Topic_ID")) == topic_id
            ]
            update_local_topic_and_steps(topic_id, updated_topic, steps)
        else:
            updated_topic["_key"] = topic.get("_key")
            add_topic_to_firebase(updated_topic, overwrite=True)
