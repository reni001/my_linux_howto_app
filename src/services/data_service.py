
# src/services/data_service.py

import requests
from threading import Thread

APP_DATA = {}

def normalize_data(data):
    # ✅ NORMALISE FIREBASE SHAPES (copied from your main.py)
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
                v = dict(v)
                v.setdefault("_key", str(idx))
                new_topics.append(v)
        data["topics"] = new_topics
    else:
        data["topics"] = []

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
                v = dict(v)
                v.setdefault("_key", str(idx))
                new_steps.append(v)
        data["steps"] = new_steps
    else:
        data["steps"] = []

    if isinstance(data.get("metadata"), list):
        data["metadata"] = data["metadata"][0] if data["metadata"] else {}

    return data


def fetch_database(app):
    from kivy.clock import Clock
    from src.utils.config import load_firebase_config

    firebase_cfg = load_firebase_config()
    DB_URL = (firebase_cfg.get("database_url") or firebase_cfg.get("databaseURL")) + "/.json"

    def _task():
        global APP_DATA
        try:
            print(f"DEBUG: Fetching from {DB_URL}")
            r = requests.get(DB_URL, timeout=10)
            if r.status_code == 200:
                data = r.json() or {}

                APP_DATA.clear()
                APP_DATA.update(normalize_data(data))

                Clock.schedule_once(lambda dt: app.refresh_ui_data())
        except Exception as e:
            print(f"DEBUG: Fetch failed: {e}")

    Thread(target=_task, daemon=True).start()


def load_app_metadata():
    global APP_DATA

    metadata = {}

    firebase_meta = APP_DATA.get("metadata", {}) or {}

    if isinstance(firebase_meta, list):
        firebase_meta = firebase_meta[0] if firebase_meta else {}

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
