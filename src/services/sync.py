#!/usr/bin/env python3
import json
import sys
import math
import hashlib
import shutil
import subprocess
from datetime import datetime
from copy import deepcopy
from pathlib import Path

import pandas as pd
import firebase_admin
from firebase_admin import credentials, db, initialize_app

from src.runtime_paths import get_runtime_paths
from src.config import load_firebase_config

# ---------------------------
# JSON safety
# ---------------------------
def json_safe(obj):
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return obj

def stable_dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ---------------------------
# Runtime paths
# ---------------------------
paths = get_runtime_paths()
DATA_DIR = paths["data"]
EXCEL_FILE = DATA_DIR / "main.xlsx"
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

# ---------------------------
# Version + date
# ---------------------------
def bump_version(version: str) -> str:
    try:
        major, minor, patch = map(int, version.strip().split("."))
        return f"{major}.{minor}.{patch + 1}"
    except Exception:
        return "0.0.1"


def today_ddmmyyyy() -> str:
    return datetime.now().strftime("%d.%m.%Y")

# ---------------------------
# Excel <-> payload helpers
# ---------------------------
def read_all_sheets(xlsx: Path) -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(xlsx)
    return {name: xl.parse(name) for name in xl.sheet_names}


def appinfo_df_to_meta(df: pd.DataFrame) -> dict:
    """
    Supports:
    A) columns: app_name + value column
    B) first two columns key/value
    """
    meta = {}
    cols = [str(c).strip() for c in df.columns]
    lower_cols = [c.lower() for c in cols]

    if "app_name" in lower_cols and len(cols) >= 2:
        key_col = cols[lower_cols.index("app_name")]
        value_col = next(c for c in cols if c != key_col)
        for _, row in df.iterrows():
            k = row.get(key_col)
            if k is None or (isinstance(k, float) and pd.isna(k)):
                continue
            meta[str(k).strip()] = row.get(value_col)
        return meta

    for _, row in df.iterrows():
        if len(row) < 2:
            continue
        k = row.iloc[0]
        v = row.iloc[1]
        if k is None or (isinstance(k, float) and pd.isna(k)):
            continue
        meta[str(k).strip()] = v
    return meta


def meta_to_appinfo_df(existing: pd.DataFrame, meta: dict) -> pd.DataFrame:
    df = existing.copy()
    if df.shape[1] < 2:
        df = pd.DataFrame(columns=["Key", "Value"])

    key_series = df.iloc[:, 0].astype(str).str.strip()
    idx_map = {k.lower(): i for i, k in enumerate(key_series) if k and k.lower() != "nan"}

    for k, v in meta.items():
        lk = str(k).strip().lower()
        if lk in idx_map:
            df.iat[idx_map[lk], 1] = v
        else:
            df.loc[len(df)] = [k, v]
    return df


def sheets_to_payload(sheets: dict[str, pd.DataFrame]) -> dict:
    payload = {}
    for sheet, df in sheets.items():
        if sheet.strip().lower() == "appinfo":
            payload["metadata"] = appinfo_df_to_meta(df)
        else:
            payload[sheet] = df.to_dict(orient="records")
    return payload


def normalise_for_change_detection(payload: dict) -> dict:
    """Ignore volatile metadata fields so version/date changes don't trigger bumps."""
    p = deepcopy(payload)
    meta = p.get("metadata", {})
    if isinstance(meta, dict):
        meta.pop("version", None)
        meta.pop("last update", None)
        meta.pop("last_update", None)
    p["metadata"] = meta
    return p


def load_cached_payload() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# ----------------------------
# DETECT ASSET CHANGES
# ----------------------------

def assets_changed(runtime_assets, repo_assets):
    if not repo_assets.exists():
        return True

    runtime_files = set(str(p.relative_to(runtime_assets)) for p in runtime_assets.rglob("*") if p.is_file())
    repo_files = set(str(p.relative_to(repo_assets)) for p in repo_assets.rglob("*") if p.is_file())

    return runtime_files != repo_files

# ---------------------------
# Git helpers (CONTENT-ONLY + CONFLICT-PROOF)
# ---------------------------
def is_git_repo(repo_root: Path) -> bool:
    try:
        subprocess.run(["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def git(repo_root: Path, *args, check=True, capture=False):
    if capture:
        return subprocess.run(["git", "-C", str(repo_root), *args], check=check, text=True, capture_output=True)
    return subprocess.run(["git", "-C", str(repo_root), *args], check=check)


def git_status_porcelain(repo_root: Path) -> list[str]:
    r = git(repo_root, "status", "--porcelain", check=True, capture=True)
    return [line for line in r.stdout.splitlines() if line.strip()]


def repo_has_conflict_markers(repo_root: Path) -> bool:
    r = git(
        repo_root,
        "grep",
        "-n",
        "<<<<<<<",
        "--",
        # ✅ EXCLUDE sync.py (important fix)
        ":(exclude)src/sync.py",
        check=False,
        capture=True,
    )
    return bool(r.stdout.strip())


def git_has_non_content_changes(repo_root: Path, allowed: set[str]) -> bool:
    lines = git_status_porcelain(repo_root)

    for ln in lines:
        path = ln[3:].strip().replace("\\", "/")

        # ✅ allow anything inside allowed folders
        if any(path.startswith(a.rstrip("/") + "/") or path == a for a in allowed):
            continue

        return True

    return False


def git_commit_if_needed(repo_root: Path, msg: str, stage_paths: list[str]) -> bool:
    for p in stage_paths:
        git(repo_root, "add", p, check=True)

    # only commit if staged diff exists
    diff = subprocess.run(["git", "-C", str(repo_root), "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        print("ℹ️ No git changes to commit.")
        return False

    r = git(repo_root, "commit", "-m", msg, check=True, capture=True)
    if r.stdout.strip():
        print(r.stdout.strip())
    return True


def git_sync_content_only(repo_root: Path, version: str):
    """
    GitHub sync that cannot break src/main.py or src/main.kv:
    - refuses to run if src/main.kv is missing
    - refuses to run if conflict markers exist
    - refuses to run if there are any changes outside allowlist
    - stages/commits ONLY data/main.xlsx
    """
    if not is_git_repo(repo_root):
        print("ℹ️ Not a git repo here — skipping GitHub sync.")
        return

    # Hard safety: refuse if KV missing (prevents accidental deletion commit)
    kv_path = repo_root / "src" / "main.kv"
    if not kv_path.exists():
        print("⚠️ Git sync blocked: src/main.kv is missing in the repo working tree.")
        print("👉 Restore it first (example): git restore src/main.kv")
        return

    # Hard safety: refuse if any conflict markers exist
    if repo_has_conflict_markers(repo_root):
        print("⚠️ Git sync blocked: conflict markers (<<<<<<<) found in tracked files.")
        print("👉 Resolve conflicts and commit before syncing.")
        return

    allowed = {
        "data/main.xlsx",
        "assets/icons",
        "assets/screenshots"
    }

    # If repo has code/UI changes, don't pull/rebase (this is how main.py got corrupted)
    if git_has_non_content_changes(repo_root, allowed):
        print("⚠️ Repo has non-content changes (code/UI/etc).")
        print("ℹ️ To prevent conflicts or accidental deletions, Git sync is skipped.")
        print("👉 Commit/push code changes manually, then re-run sync.")
        return

    # Pull safely (content-only clean state)
    print("🔄 Git: pulling latest (rebase + autostash)…")
    try:
        git(repo_root, "pull", "--rebase", "--autostash", check=True)
    except subprocess.CalledProcessError as e:
        # Abort any partial rebase so we don't leave conflict markers behind
        git(repo_root, "rebase", "--abort", check=False)
        print("⚠ Git pull/rebase failed; Git sync skipped to avoid corrupting files.")
        print("   Error:", e)
        return

    # Commit only if needed; message includes version
    msg = f"content: v{version}"
    created = git_commit_if_needed(repo_root, msg, ["data/main.xlsx", "assets/icons", "assets/screenshots"])


    if not created:
        print("ℹ️ Skipping push (no new commit).")
        return

    print("🚀 Git: pushing…")
    try:
        git(repo_root, "push", check=True)
        print("✅ GitHub sync done")
    except subprocess.CalledProcessError as e:
        print("⚠ Git push failed:", e)
        print("ℹ️ Remote may be ahead. Run `git pull --rebase` manually and retry.")

# ---------------------------
# Main sync
# ---------------------------
def main():
    print("=== SAFE SYNC (Firebase → Excel) ===")

    # ✅ 1. Get data from Firebase FIRST
    print("☁ Downloading data from Firebase…")
    data = db.reference("/").get()

    if not data:
        print("❌ Firebase is empty — aborting to protect Excel")
        return

    if "topics" not in data or not data["topics"]:
        print("❌ Firebase seems EMPTY (no topics) — aborting")
        return

    print("✅ Firebase data retrieved")


    required = ["topics", "steps", "metadata"]
    missing = [k for k in required if k not in data]
    if missing:
        print(f"❌ Firebase missing keys {missing} — aborting")
        return


    # 3) Bump version + date
    #meta = payload_pre.get("metadata", {}) if isinstance(payload_pre.get("metadata", {}), dict) else {}
    #old_version = str(meta.get("version", "0.0.0"))
    #new_version = bump_version(old_version)
    #meta["version"] = new_version
    #meta["last update"] = today_ddmmyyyy()

    #print(f"✅ Version updated: {old_version} → {new_version}")
    #print(f"📅 Last update set to: {meta['last update']}")

    # ✅ 2. Write to Excel
    print("📊 Writing data to Excel:", EXCEL_FILE)

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        for key, value in data.items():

            if key == "metadata":
                df = pd.DataFrame(list(value.items()), columns=["Key", "Value"])
                df.to_excel(writer, sheet_name="AppInfo", index=False)

            else:
                df = pd.DataFrame(value)
                df.to_excel(writer, sheet_name=key, index=False)

    print("✅ Excel updated from Firebase")

    # ✅ 3. Cache (safe)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # ✅ 4. Copy Excel to repo
    repo_root = Path(__file__).resolve().parent.parent
    repo_excel = repo_root / "data" / "main.xlsx"
    repo_excel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EXCEL_FILE, repo_excel)

    print(f"📦 Copied Excel to repo: {repo_excel}")

    # ✅ 5. Copy assets
    runtime_assets = paths["assets"]
    repo_assets = repo_root / "assets"

    if runtime_assets.exists():
        shutil.copytree(runtime_assets, repo_assets, dirs_exist_ok=True)
        print("📦 Copied assets to repo")

    # 6) Build final payload and upload --> writing excel to firebase
    #payload = json_safe(sheets_to_payload(sheets))
    #print("☁ Uploading data to Firebase…")
    #db.reference("/").set(payload)
    #print("✅ Firebase sync complete")

    # ✅ 6. Git sync (safe, no Firebase impact)
    version = str(data.get("metadata", {}).get("version", "unknown"))
    git_sync_content_only(repo_root, version)

    print("✅ Sync finished (SAFE MODE)")

if __name__ == "__main__":
    print("=== Developer Sync started ===")
    init_firebase()
    main()
    print("=== Developer Sync finished ===")
