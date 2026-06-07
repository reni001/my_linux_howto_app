import json
import shutil
from datetime import datetime
from pathlib import Path
from src.utils.runtime_paths import get_runtime_paths


def _normalise_backup_payload(data):
    """
    Ensure backup payload always uses lists for topics / steps,
    regardless of whether source came from app.APP_DATA or raw Firebase.
    """
    out = dict(data or {})

    topics = out.get("topics", [])
    steps = out.get("steps", [])

    if isinstance(topics, dict):
        topics = list(topics.values())

    if isinstance(steps, dict):
        steps = list(steps.values())

    # keep only dict items
    topics = [t for t in topics if isinstance(t, dict)]
    steps = [s for s in steps if isinstance(s, dict)]

    out["topics"] = topics
    out["steps"] = steps

    return out


def backup_database(app):
    """
    Full backup from running app state (APP_DATA + assets).
    Used before delete / destructive operations inside app.
    """
    paths = get_runtime_paths()
    backup_dir = paths["data"] / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_folder = backup_dir / f"backup_{timestamp}"
    backup_folder.mkdir(parents=True, exist_ok=True)

    payload = _normalise_backup_payload(app.APP_DATA)

    with open(backup_folder / "data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    assets_src = paths["assets"]
    assets_dst = backup_folder / "assets"

    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    print(f"✅ Full backup created: {backup_folder}")

    cleanup_old_backups(max_keep=15)


def backup_runtime_snapshot(data, assets_path, max_keep=15):
    """
    Full backup from runtime snapshot (used by sync.py).
    Saves provided data + assets into the same folder-based backup format.
    """
    paths = get_runtime_paths()
    backup_dir = paths["data"] / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_folder = backup_dir / f"backup_{timestamp}"
    backup_folder.mkdir(parents=True, exist_ok=True)

    payload = _normalise_backup_payload(data)

    with open(backup_folder / "data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    assets_src = Path(assets_path)
    assets_dst = backup_folder / "assets"

    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    print(f"✅ Snapshot backup created: {backup_folder}")

    cleanup_old_backups(max_keep=max_keep)


def cleanup_old_backups(max_keep=15):
    paths = get_runtime_paths()
    backup_dir = paths["data"] / "backups"

    if not backup_dir.exists():
        return

    backups = [p for p in backup_dir.iterdir() if p.is_dir()]
    backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    for old in backups[max_keep:]:
        try:
            shutil.rmtree(old)
        except Exception:
            pass


def get_backups():
    paths = get_runtime_paths()
    backup_dir = paths["data"] / "backups"

    if not backup_dir.exists():
        return []

    backups = [p for p in backup_dir.iterdir() if p.is_dir()]
    backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return backups


def restore_backup_file(backup_path):
    """
    Restore backup folder contents into runtime data and assets.
    Returns the path to restored cache.json
    """
    paths = get_runtime_paths()

    data_file = Path(backup_path) / "data.json"
    assets_src = Path(backup_path) / "assets"

    cache_file = paths["data"] / "cache.json"
    assets_dst = paths["assets"]

    if not data_file.exists():
        raise FileNotFoundError(f"Missing data.json in backup: {backup_path}")

    shutil.copy2(data_file, cache_file)

    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    return cache_file
