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

def _collect_used_assets(data):
    """
    Scan topics + steps and collect only the actually used asset files
    (icons + screenshots).
    """
    paths = get_runtime_paths()
    assets_root = paths["assets"]

    used_files = set()

    # --- topics: icons ---
    for t in data.get("topics", []):
        for key in ("Topic_Icon", "Cat_Icon", "Sub_Icon"):
            filename = str(t.get(key) or "").strip()
            if not filename:
                continue

            for sub in ["icons", "user_icons"]:
                p = assets_root / sub / filename
                if p.exists():
                    used_files.add(p)

    # --- steps: screenshots ---
    for s in data.get("steps", []):
        filename = str(s.get("Screenshot") or "").strip()
        if filename:
            p = assets_root / "screenshots" / filename
            if p.exists():
                used_files.add(p)

    return used_files

def _copy_assets_subset(data, backup_folder):
    """
    Copy only used icons + screenshots + always icons_core.
    """

    paths = get_runtime_paths()
    assets_root = paths["assets"]
    assets_dst = backup_folder / "assets"
    assets_dst.mkdir(parents=True, exist_ok=True)

    used_files = _collect_used_assets(data)

    # ✅ copy only needed files
    for src in used_files:
        rel = src.relative_to(assets_root)
        dst = assets_dst / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # ✅ ALWAYS include core icons (important!)
    core_src = assets_root / "icons_core"
    core_dst = assets_dst / "icons_core"

    if core_src.exists():
        shutil.copytree(core_src, core_dst, dirs_exist_ok=True)

    print(f"✅ Smart backup: {len(used_files)} assets copied")

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

    data = payload

    with open(backup_folder / "data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    _copy_assets_subset(data, backup_folder)


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

    # ✅ ensure structure matches list format for asset scanning
    data = payload


    with open(backup_folder / "data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    _copy_assets_subset(data, backup_folder)


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


def _topic_key(topic):
    return str(
        topic.get("Topic_ID")
        or topic.get("topic_id")
        or ""
    ).strip().lower()


def _step_key(step):
    topic_id = str(
        step.get("Topic_ID")
        or step.get("topic_id")
        or ""
    ).strip().lower()

    step_order = str(
        step.get("Step_Order")
        or step.get("order")
        or ""
    ).strip().lower()

    instruction = str(
        step.get("Instruction")
        or step.get("instruction")
        or ""
    ).strip().lower()

    # using instruction as fallback helps if order is missing
    return f"{topic_id}|{step_order}|{instruction}"


def _deduplicate_data(data):
    """
    Deduplicate a single backup dataset.
    Keeps first occurrence of each topic / step.
    """
    data = _normalise_backup_payload(data)

    seen_topics = set()
    unique_topics = []

    for topic in data.get("topics", []):
        if not isinstance(topic, dict):
            continue

        key = _topic_key(topic)
        if not key:
            continue

        if key in seen_topics:
            continue

        seen_topics.add(key)
        unique_topics.append(topic)

    seen_steps = set()
    unique_steps = []

    for step in data.get("steps", []):
        if not isinstance(step, dict):
            continue

        key = _step_key(step)
        if not key:
            continue

        if key in seen_steps:
            continue

        seen_steps.add(key)
        unique_steps.append(step)

    data["topics"] = unique_topics
    data["steps"] = unique_steps
    return data


def restore_backup_file(backup_path):
    """
    Restore backup folder contents into runtime data and assets.
    Restores ONLY the selected backup snapshot (not merged with current cache).
    """
    paths = get_runtime_paths()

    data_file = Path(backup_path) / "data.json"
    assets_src = Path(backup_path) / "assets"

    cache_file = paths["data"] / "cache.json"
    assets_dst = paths["assets"]

    if not data_file.exists():
        raise FileNotFoundError(f"Missing data.json in backup: {backup_path}")

    with open(data_file, "r", encoding="utf-8") as f:
        incoming = json.load(f)

    restored = _deduplicate_data(incoming)

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(restored, f, indent=2, ensure_ascii=False)

    # ✅ restore assets/icons too
    if assets_src.exists():
        for src in assets_src.rglob("*"):
            if not src.is_file():
                continue

            rel = src.relative_to(assets_src)
            dst = assets_dst / rel

            dst.parent.mkdir(parents=True, exist_ok=True)

            # ✅ only overwrite if newer or missing
            if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
                shutil.copy2(src, dst)

    return cache_file
