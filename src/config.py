import json
from src.runtime_paths import get_runtime_paths


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

    with open(cfg_file, "r", encoding="utf-8") as f:
        return json.load(f)    
