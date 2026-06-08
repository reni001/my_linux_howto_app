# src/services/firebase_service.py
from __future__ import annotations

import re
import hashlib
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, db, initialize_app

from src.utils.config import load_firebase_config
from src.services.auth_service import require_admin_key

def _ensure_admin_firebase() -> None:
    """
    Initialise Firebase Admin SDK once per process using serviceAccountKey.json.
    """
    key_path = require_admin_key()

    if not firebase_admin._apps:
        cfg = load_firebase_config()
        db_url = cfg.get("database_url") or cfg.get("databaseURL")
        if not db_url:
            raise KeyError("firebase.json must contain 'database_url' or 'databaseURL'")

        cred = credentials.Certificate(str(key_path))
        initialize_app(cred, {"databaseURL": db_url})

def suffix_if_needed(base: str, existing_ids: set[str]) -> str:
    if base not in existing_ids:
        return base
    n = 2
    while f"{base}_{n}" in existing_ids:
        n += 1
    return f"{base}_{n}"


def generate_topic_id(topic: dict, existing_ids: set[str] | None = None) -> str:
    """
    Improved Topic_ID:
    format: cat6_sub6_title12_hash4

    Example:
    archli_appli_micro_texted_7f4a
    """

    def slug(s: str) -> str:
        s = (str(s) if s is not None else "").lower().strip()
        s = s.replace(" ", "_")
        s = re.sub(r"[^a-z0-9_]+", "", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    # ✅ slightly longer slices (better uniqueness)
    cat = slug(topic.get("Category"))[:6] or "catx"
    sub = slug(topic.get("Subcategory"))[:6] or "subx"
    title = slug(topic.get("Title"))[:12] or "titlex"

    base = f"{cat}_{sub}_{title}"

    # ✅ deterministic hash based on content
    hash_input = f"{topic.get('Category','')}_{topic.get('Subcategory','')}_{topic.get('Title','')}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:4]

    candidate = f"{base}_{short_hash}"

    # ✅ final safety fallback (very rare)
    if existing_ids:
        if candidate not in existing_ids:
            return candidate

        n = 2
        while f"{candidate}_{n}" in existing_ids:
            n += 1
        return f"{candidate}_{n}"

    return candidate

def add_topic_to_firebase(topic: dict, overwrite: bool = False):
    """
    Firebase node key: automatic Firebase push key
    Topic_ID field: semantic string (cat_sub_title)
    """
    _ensure_admin_firebase()
    topics_ref = db.reference("/topics")
    all_topics = topics_ref.get() or {}

    topic = dict(topic)

    # Collect existing Topic_IDs
    existing_ids: set[str] = set()
    iterable = all_topics.values() if isinstance(all_topics, dict) else (all_topics if isinstance(all_topics, list) else [])
    for v in iterable:
        if isinstance(v, dict) and v.get("Topic_ID"):
            existing_ids.add(str(v.get("Topic_ID")))

    provided = str(topic.get("Topic_ID") or "").strip()

    if overwrite:
        topic_id = provided or str(topic.get("Topic_ID") or "").strip()
    else:
        if provided:
            topic_id = suffix_if_needed(provided, existing_ids)
        else:
            topic_id = generate_topic_id(topic, existing_ids)
        topic["Topic_ID"] = topic_id

    # ✅ EDIT / OVERWRITE existing topic
    if overwrite:
        node_key = str(topic.get("_key") or "").strip()
        if not node_key:
            raise ValueError("Missing _key for overwrite. Cannot update topic without Firebase node key.")

        topic["_key"] = node_key
        topics_ref.child(node_key).set(topic)
        return node_key, topic_id

    # ✅ NEW topic → let Firebase generate unique key
    new_ref = topics_ref.push()
    node_key = new_ref.key

    if not node_key:
        raise RuntimeError("Firebase push failed: no key returned")

    topic["_key"] = node_key
    new_ref.set(topic)

    if topics_ref.child(node_key).get() is None:
        raise RuntimeError("Firebase write failed: topic missing after write")

    return node_key, topic_id

def delete_topic_from_firebase(node_key: str, topic_id: str):
    _ensure_admin_firebase()
    topics_ref = db.reference("/topics")
    steps_ref = db.reference("/steps")

    deleted_topics = 0
    deleted_steps = 0

    # delete topic by node key
    if topics_ref.child(str(node_key)).get() is not None:
        topics_ref.child(str(node_key)).delete()
        deleted_topics = 1

    # delete steps by Topic_ID
    all_steps = steps_ref.get() or {}
    if isinstance(all_steps, dict):
        for sk, step in all_steps.items():
            if isinstance(step, dict) and str(step.get("Topic_ID")) == str(topic_id):
                steps_ref.child(sk).delete()
                deleted_steps += 1

    return deleted_topics, deleted_steps

def add_step_to_firebase(step: dict) -> str:
    _ensure_admin_firebase()
    ref = db.reference("/steps")
    all_steps = ref.get() or {}

    step = dict(step)

    if not step.get("Topic_ID"):
        raise ValueError("Step payload missing Topic_ID")

    # ensure Step_Order numeric
    try:
        step["Step_Order"] = int(step.get("Step_Order", 0) or 0)
    except Exception:
        step["Step_Order"] = 0

    # stable numeric Step_ID (convenience)
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

    new_ref = ref.push(step)
    step_key = new_ref.key

    if step_key:
        new_ref.update({"_key": step_key})

    if not step_key or ref.child(step_key).get() is None:
        raise RuntimeError("Firebase write failed: step missing after push")

    return step_key

def delete_steps_for_topic(topic_id: str) -> None:
    _ensure_admin_firebase()
    steps_ref = db.reference("/steps")
    all_steps = steps_ref.get() or {}
    if isinstance(all_steps, dict):
        for key, step in all_steps.items():
            if isinstance(step, dict) and str(step.get("Topic_ID")) == str(topic_id):
                steps_ref.child(key).delete()

def save_metadata_to_firebase(metadata: dict) -> None:
    _ensure_admin_firebase()
    ref = db.reference("/metadata")
    ref.set(metadata)
