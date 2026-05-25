import json
from src.utils.runtime_paths import get_runtime_paths


def load_firebase_config():
    """
    Load Firebase configuration from the runtime data directory.
    """

    paths = get_runtime_paths()
    cfg_file = paths["data"] / "firebase.json"

    if not cfg_file.exists():
        raise FileNotFoundError(
            f"Missing firebase.json in {paths['data']}"
        )

    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in firebase.json: {e}")

    # ✅ validate required keys (adjust if needed)
    # ✅ Only require database URL (Admin SDK does not need apiKey)
    db_url = config.get("databaseURL") or config.get("database_url")

    if not db_url:
        raise KeyError("firebase.json must contain 'databaseURL' or 'database_url'")

    print(f"[CONFIG] Loaded firebase config from: {cfg_file}")

    return config
