#!/usr/bin/env python3
import json
import sys
import shutil
import subprocess
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, db, initialize_app

from src.utils.runtime_paths import get_runtime_paths
from src.utils.config import load_firebase_config
from src.services.backup_service import backup_runtime_snapshot

# ---------------------------
# Runtime paths
# ---------------------------
paths = get_runtime_paths()
DATA_DIR = paths["data"]
CACHE_FILE = DATA_DIR / "cache.json"
FIREBASE_KEY = DATA_DIR / "serviceAccountKey.json"


# ---------------------------
# Firebase init
# ---------------------------
def init_firebase():
    if not FIREBASE_KEY.exists():
        print("❌ Firebase key not found:", FIREBASE_KEY)
        sys.exit(1)

    if not firebase_admin._apps:
        cred = credentials.Certificate(str(FIREBASE_KEY))
        cfg = load_firebase_config()
        db_url = cfg.get("database_url") or cfg.get("databaseURL")

        if not db_url:
            raise KeyError("firebase.json must contain 'database_url' or 'databaseURL'")

        initialize_app(cred, {"databaseURL": db_url})


# ✅ Promote user icons to official icons (for Git sync)
user_icons = paths["assets"] / "user_icons"
icons = paths["assets"] / "icons"

if user_icons.exists():
    for f in user_icons.glob("*"):
        if not f.is_file():
            continue

        dest = icons / f.name

        # ✅ only copy if not already present
        if not dest.exists():
            shutil.copy2(f, dest)

    print("✅ User icons copied to icons/ for sync")


# ---------------------------
# Git helpers
# ---------------------------
def git(repo_root: Path, *args, check=True):
    return subprocess.run(["git", "-C", str(repo_root), *args], check=check)


def is_git_repo(repo_root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False


def git_sync(repo_root: Path, version: str):
    if not is_git_repo(repo_root):
        print("ℹ️ Not a git repo → skip Git sync")
        return

    print("🔄 Git: pulling…")
    try:
        git(repo_root, "pull", "--rebase", "--autostash")
    except Exception as e:
        print("⚠️ Git pull failed:", e)
        return

    print("➕ Git: adding content…")
    git(repo_root, "add", "data/cache.json", "assets")

    result = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--cached", "--quiet"]
    )

    if result.returncode == 0:
        print("ℹ️ Nothing to commit")
        return

    print("✅ Git: committing…")
    git(repo_root, "commit", "-m", f"content sync v{version}")

    print("🚀 Git: pushing…")
    try:
        git(repo_root, "push")
        print("✅ Git sync complete")
    except Exception as e:
        print("⚠️ Git push failed:", e)


# ---------------------------
# Main sync
# ---------------------------
def main():
    print("=== SAFE SYNC (Firebase → JSON cache) ===")

    print("☁ Downloading data from Firebase…")
    data = db.reference("/").get()

    if not data:
        print("❌ Firebase empty → abort")
        return

    if "topics" not in data or not data["topics"]:
        print("❌ No topics → abort")
        return

    # ✅ Full backup before overwriting cache/assets
    backup_runtime_snapshot(
        data=data,
        assets_path=paths["assets"],
        max_keep=15
    )

    # ✅ Save JSON cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ cache.json updated")

    # ✅ Copy assets to repo
    repo_root = Path(__file__).resolve().parents[2]
    runtime_assets = paths["assets"]
    repo_assets = repo_root / "assets"

    if runtime_assets.exists():
        shutil.copytree(runtime_assets, repo_assets, dirs_exist_ok=True)
        print("📦 Assets copied")

    # ✅ Git sync
    version = str(data.get("metadata", {}).get("version", "unknown"))
    git_sync(repo_root, version)

    print("✅ Sync finished")


# ---------------------------
# Entry point
# ---------------------------
if __name__ == "__main__":
    print("=== Developer Sync started ===")
    init_firebase()
    main()
    print("=== Developer Sync finished ===")
