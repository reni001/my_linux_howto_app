import json
import requests
from threading import Thread
from pathlib import Path

from kivy.clock import Clock

from src.utils.runtime_paths import get_runtime_paths
from src.utils.config import load_firebase_config

APP_DATA = {}


def _cache_file() -> Path:
    paths = get_runtime_paths()
    return paths["data"] / "cache.json"

def _user_file() -> Path:
    paths = get_runtime_paths()
    return paths["data"] / "user_data.json"


def ensure_user_data_file() -> None:
    user_file = _user_file()
    user_file.parent.mkdir(parents=True, exist_ok=True)

    if not user_file.exists():
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump({"topics": [], "steps": []}, f, indent=2, ensure_ascii=False)

def save_cache(data: dict) -> None:
    cache_file = _cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_cache() -> dict:
    cache_file = _cache_file()
    if not cache_file.exists():
        return {}

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read cache.json: {e}")
        return {}


def normalize_data(data: dict) -> dict:
    data = data or {}

    # topics
    raw_topics = data.get("topics")
    if isinstance(raw_topics, dict):
        data["topics"] = [
            {"_key": str(k), **v}
            for k, v in raw_topics.items()
            if isinstance(v, dict)
        ]
    elif isinstance(raw_topics, list):
        new_topics = []
        for idx, v in enumerate(raw_topics):
            if isinstance(v, dict):
                item = dict(v)
                item.setdefault("_key", str(idx))
                new_topics.append(item)
        data["topics"] = new_topics
    else:
        data["topics"] = []

    # steps
    raw_steps = data.get("steps")
    if isinstance(raw_steps, dict):
        data["steps"] = [
            {"_key": str(k), **v}
            for k, v in raw_steps.items()
            if isinstance(v, dict)
        ]
    elif isinstance(raw_steps, list):
        new_steps = []
        for idx, v in enumerate(raw_steps):
            if isinstance(v, dict):
                item = dict(v)
                item.setdefault("_key", str(idx))
                new_steps.append(item)
        data["steps"] = new_steps
    else:
        data["steps"] = []

    # metadata
    raw_meta = data.get("metadata", {})
    if isinstance(raw_meta, list):
        data["metadata"] = raw_meta[0] if raw_meta else {}
    elif isinstance(raw_meta, dict):
        data["metadata"] = raw_meta
    else:
        data["metadata"] = {}

    return data

def load_user_data() -> dict:
    ensure_user_data_file()
    file = _user_file()

    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {"topics": [], "steps": []}

        data.setdefault("topics", [])
        data.setdefault("steps", [])
        return data

    except Exception as e:
        print(f"⚠️ Failed to read user_data.json: {e}")
        return {"topics": [], "steps": []}


def save_user_data(data: dict) -> None:
    ensure_user_data_file()
    file = _user_file()

    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_app_metadata() -> dict:
    global APP_DATA

    metadata = {}
    firebase_meta = APP_DATA.get("metadata", {}) or {}

    if isinstance(firebase_meta, dict):
        metadata = {
            "app_name": firebase_meta.get("app_name", "Linux HowTo"),
            "version": firebase_meta.get("version", "0.0.0"),
            "last update": firebase_meta.get("last update", "unknown"),
            "description": firebase_meta.get("description", ""),
            "developer": firebase_meta.get("developer", ""),
            "changelog": firebase_meta.get("changelog", "")
        }

    metadata.setdefault("app_name", "Linux HowTo")
    return metadata

def merge_datasets(global_data: dict, user_data: dict) -> dict:
    merged = {
        "topics": [],
        "steps": [],
        "metadata": global_data.get("metadata", {})
    }

    merged["topics"] = list(global_data.get("topics", [])) + list(user_data.get("topics", []))
    merged["steps"] = list(global_data.get("steps", [])) + list(user_data.get("steps", []))

    return merged


def add_local_topic_and_steps(topic: dict, steps: list[dict]) -> None:
    data = load_user_data()

    topic = dict(topic)
    topic.setdefault("source", "user")
    topic.setdefault("local_only", True)

    # Create stable local key/id
    topic_id = str(topic.get("Topic_ID") or "").strip()
    if not topic_id:
                    topic_id = f"user_topic_{len(data['topics']) + 1}"

    topic["_key"] = topic_id
    topic["Topic_ID"] = topic_id

    data["topics"].append(topic)

    for i, step in enumerate(steps or [], start=1):
        step = dict(step)
        step.setdefault("source", "user")
        step.setdefault("local_only", True)
        step["Topic_ID"] = topic_id
        step.setdefault("_key", f"{topic_id}_step_{i}")
        data["steps"].append(step)

    save_user_data(data)


def delete_local_topic(topic_id: str) -> None:
    data = load_user_data()

    data["topics"] = [
        t for t in data.get("topics", [])
        if str(t.get("Topic_ID")) != str(topic_id)
    ]

    data["steps"] = [
        s for s in data.get("steps", [])
        if str(s.get("Topic_ID")) != str(topic_id)
    ]

    save_user_data(data)

def fetch_database(app):

    def _task():
        global APP_DATA

        source = "unknown"

        try:
            cfg = load_firebase_config()
            db_url = (cfg.get("database_url") or cfg.get("databaseURL")) + "/.json"

            print(f"DEBUG: Fetching from Firebase: {db_url}")
            r = requests.get(db_url, timeout=10)
            r.raise_for_status()

            data = r.json() or {}
            if not isinstance(data, dict):
                raise ValueError("Firebase root payload is not a dict")

            if "topics" not in data:
                raise ValueError("Firebase payload missing 'topics'")


            data = normalize_data(data)
            save_cache(data)

            # ✅ merge with user data
            user_data = normalize_data(load_user_data())
            merged = merge_datasets(data, user_data)

            APP_DATA.clear()
            APP_DATA.update(merged)

            source = "firebase"
            print("✅ Data loaded from Firebase, cache.json updated, user_data.json merged")

        except Exception as e:
            print(f"⚠️ Firebase unavailable, using cache.json instead: {e}")


            cached = normalize_data(load_cache())
            user_data = normalize_data(load_user_data())
            merged = merge_datasets(cached, user_data)

            APP_DATA.clear()
            APP_DATA.update(merged)

            source = "cache"
            print("✅ Data loaded from cache.json and user_data.json merged")


        def _finish(dt):
            app.APP_DATA = APP_DATA
            app.last_data_source = source   # optional, useful for debugging/UI
            app.refresh_ui_data()

        Clock.schedule_once(_finish, 0)

    Thread(target=_task, daemon=True).start()
