# src/services/auth_service.py
from __future__ import annotations
from pathlib import Path
from src.utils.runtime_paths import get_runtime_paths

ADMIN_KEY_FILENAME = "serviceAccountKey.json"

def admin_key_path() -> Path:
    paths = get_runtime_paths()
    return paths["data"] / ADMIN_KEY_FILENAME

def is_admin_enabled() -> bool:
    """
    Admin editor is enabled only when serviceAccountKey.json exists in runtime data dir.
    """
    return admin_key_path().exists()

def require_admin_key() -> Path:
    """
    Return key path or raise a clear error.
    """
    key = admin_key_path()
    if not key.exists():
        raise FileNotFoundError(f"Missing admin key: {key}")
    return key
