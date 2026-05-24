from __future__ import annotations
import re
import shutil
from datetime import datetime
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, db, initialize_app

from src.runtime_paths import get_runtime_paths
from src.config import load_firebase_config


def _ensure_admin_firebase():
    paths = get_runtime_paths()
    key_path = paths["data"] / "serviceAccountKey.json"
    if not key_path.exists():
        raise FileNotFoundError(f"Missing admin key: {key_path}")

    if not firebase_admin._apps:
        cfg = load_firebase_config()
        db_url = cfg.get("database_url") or cfg.get("databaseURL")
        if not db_url:
            raise KeyError("firebase.json must contain 'database_url' or 'databaseURL'")
        cred = credentials.Certificate(str(key_path))
        initialize_app(cred, {"databaseURL": db_url})


def is_admin_enabled() -> bool:
    """
    Admin editor is enabled only when serviceAccountKey.json exists.
    """
    paths = get_runtime_paths()
    return (paths["data"] / "serviceAccountKey.json").exists()


def copy_icon_to_assets(source_file: str) -> str:
    """
    Copy a selected icon into runtime assets/icons and return the filename to store in Firebase.
    """
    paths = get_runtime_paths()
    icons_dir = paths["assets"] / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    src = Path(source_file)
    if not src.exists():
        raise FileNotFoundError(source_file)

    # keep original filename, but make sure it's safe
    filename = src.name.replace(" ", "_")
    dest = icons_dir / filename
    shutil.copy(src, dest)
    return filename


def add_topic_to_firebase(topic: dict, overwrite: bool = False):
    """
    Firebase node key: numeric string (71, 72, ...)
    Topic_ID field: semantic string (arch_app_name)
    """
    _ensure_admin_firebase()

    topics_ref = db.reference("/topics")
    all_topics = topics_ref.get() or {}

    topic = dict(topic)

    # --- determine semantic Topic_ID ---
    # collect existing Topic_IDs first (so we can avoid duplicates)
    existing_ids = set()

    if isinstance(all_topics, dict):
        iterable = all_topics.values()
    elif isinstance(all_topics, list):
        iterable = all_topics
    else:
        iterable = []

    for v in iterable:
        if isinstance(v, dict) and v.get("Topic_ID"):
            existing_ids.add(str(v.get("Topic_ID")))

    provided = str(topic.get("Topic_ID") or "").strip()

    if overwrite:
        # editing: keep the Topic_ID (do not regenerate)
        topic_id = provided or str(topic.get("Topic_ID") or "").strip()
    else:
        # adding new: if user typed an ID, make it unique; else generate
        if provided:
            topic_id = suffix_if_needed(provided, existing_ids)
        else:
            topic_id = generate_topic_id(topic, existing_ids)

    topic["Topic_ID"] = topic_id

    # --- overwrite/edit uses stored firebase key (_key) ---
    if overwrite:
        node_key = str(topic.get("_key") or "").strip()
        if not node_key:
            raise ValueError("Missing _key for overwrite. Cannot update topic without Firebase node key.")
        topic["_key"] = node_key
        topics_ref.child(node_key).set(topic)
        return node_key, topic_id
        # Note: next_id is safe for single-writer (developer) usage. For multi-writer, use a transaction/counter.

    # --- new topic: choose next numeric node key ---
    numeric_keys = []
    if isinstance(all_topics, dict):
        for k in all_topics.keys():
            if str(k).isdigit():
                numeric_keys.append(int(k))

    next_id = (max(numeric_keys) + 1) if numeric_keys else 1

    # avoid collisions
    while topics_ref.child(str(next_id)).get() is not None:
        next_id += 1

    node_key = str(next_id)
    topic["_key"] = node_key

    topics_ref.child(node_key).set(topic)

    # verify write
    if topics_ref.child(node_key).get() is None:
        raise RuntimeError("Firebase write failed: topic missing after write")
    return node_key, topic_id

#---------- delete entry----------

def delete_topic_from_firebase(node_key: str, topic_id: str):
    _ensure_admin_firebase()

    topics_ref = db.reference("/topics")
    steps_ref = db.reference("/steps")

    deleted_topics = 0
    deleted_steps = 0

    # ✅ delete topic by KEY (correct!)
    if topics_ref.child(str(node_key)).get() is not None:
        print(f"✅ deleting node {node_key}")
        topics_ref.child(str(node_key)).delete()
        deleted_topics = 1
    else:
        print(f"❌ node {node_key} not found")

    # ✅ delete steps by Topic_ID (correct!)
    all_steps = steps_ref.get() or {}
    if isinstance(all_steps, dict):
        for sk, step in all_steps.items():
            if isinstance(step, dict) and str(step.get("Topic_ID")) == str(topic_id):
                steps_ref.child(sk).delete()
                deleted_steps += 1

    return deleted_topics, deleted_steps

def export_backup_excel(app_data: dict):
    """
    Export app_data to Excel backup (main.xlsx).
    - topics -> sheet 'topics'
    - steps  -> sheet 'steps'
    - metadata -> sheet 'AppInfo' as key/value (NOT transposed)
    """
    import pandas as pd

    paths = get_runtime_paths()
    excel_path = paths["data"] / "main.xlsx"

    topics = app_data.get("topics", []) or []
    steps  = app_data.get("steps", []) or []
    meta   = app_data.get("metadata") or app_data.get("AppInfo") or {}

    # normalise metadata to dict
    if isinstance(meta, list):
        # if someone stored metadata as [ { ... } ] take first dict
        meta = meta[0] if meta and isinstance(meta[0], dict) else {}

    if meta is None:
        meta = {}

    # ensure required key exists
    meta.setdefault("app_name", "Linux HowTo")

    # write key/value sheet for AppInfo
    meta_df = pd.DataFrame(list(meta.items()), columns=["key", "value"])

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame(topics).to_excel(writer, sheet_name="topics", index=False)
        pd.DataFrame(steps).to_excel(writer, sheet_name="steps", index=False)
        meta_df.to_excel(writer, sheet_name="AppInfo", index=False)


#------------ Steps section --------

# assumes you already have _ensure_admin_firebase() in this module

def add_step_to_firebase(step: dict) -> str:
    _ensure_admin_firebase()

    ref = db.reference("/steps")
    all_steps = ref.get() or {}

    step = dict(step)

    # ✅ hard requirements
    if not step.get("Topic_ID"):
        raise ValueError("Step payload missing Topic_ID")

    # ✅ ensure Step_Order is numeric (sorting/filtering relies on it)
    try:
        step["Step_Order"] = int(step.get("Step_Order", 0) or 0)
    except Exception:
        step["Step_Order"] = 0

    # ✅ assign a stable numeric Step_ID for convenience (not used as Firebase key)
    max_step_id = 0
    if isinstance(all_steps, dict):
        for v in all_steps.values():
            if isinstance(v, dict):
                try:
                    max_step_id = max(max_step_id, int(v.get("Step_ID", 0) or 0))
                except Exception:
                    pass
    step["Step_ID"] = max_step_id + 1
    step["created_at"] = datetime.utcnow().isoformat()

    # ✅ push creates a unique key (prevents overwriting)
    new_ref = ref.push(step)
    step_key = new_ref.key

    # ✅ store the key inside the record (optional but useful)
    if step_key:
        new_ref.update({"_key": step_key})

    # ✅ verify write (fail loud)
    if not step_key or ref.child(step_key).get() is None:
        raise RuntimeError("Firebase write failed: step missing after push")

    return step_key



def delete_steps_for_topic(topic_id: str):
    _ensure_admin_firebase()

    steps_ref = db.reference("/steps")
    all_steps = steps_ref.get() or {}

    if isinstance(all_steps, dict):
        for key, step in all_steps.items():
            if isinstance(step, dict) and str(step.get("Topic_ID")) == str(topic_id):
                steps_ref.child(key).delete()


def save_metadata_to_firebase(metadata: dict):
    _ensure_admin_firebase()

    ref = db.reference("/metadata")

    # overwrite existing metadata
    ref.set(metadata)

def suffix_if_needed(base: str, existing_ids: set[str]) -> str:
    if base not in existing_ids:
        return base
    n = 2
    while f"{base}_{n}" in existing_ids:
        n += 1
    return f"{base}_{n}"

def generate_topic_id(topic: dict, existing_ids: set[str] | None = None) -> str:
    """
    Short Topic_ID format:
      cat4_sub4_title6
    If duplicate, append number: cat4_sub4_title62, ...63, etc.
    """

    def slug(s: str) -> str:
        s = (str(s) if s is not None else "").lower().strip()
        s = s.replace(" ", "_")
        # keep only a-z 0-9 and underscore
        s = re.sub(r"[^a-z0-9_]+", "", s)
        # collapse multiple underscores
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    cat = slug(topic.get("Category", ""))[:4] or "catx"
    sub = slug(topic.get("Subcategory", ""))[:4] or "subx"
    title = slug(topic.get("Title", ""))[:6] or "titlex"

    base = f"{cat}_{sub}_{title}"

    if not existing_ids:
        return base

    if base not in existing_ids:
        return base

    n = 2
    while f"{base}{n}" in existing_ids:
        n += 1
    return f"{base}_{n}"


