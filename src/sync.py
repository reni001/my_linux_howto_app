#!/usr/bin/env python3

import json
import sys
import math
import subprocess
from datetime import datetime

import pandas as pd
import firebase_admin
from firebase_admin import credentials, db, initialize_app

from src.runtime_paths import get_runtime_paths
from src.config import load_firebase_config


# --------------------------------------------------
# JSON sanitiser
# --------------------------------------------------

def json_safe(obj):
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_safe(v) for v in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


# --------------------------------------------------
# Paths
# --------------------------------------------------

paths = get_runtime_paths()
DATA_DIR = paths["data"]

EXCEL_FILE = DATA_DIR / "main.xlsx"
CACHE_FILE = DATA_DIR / "cache.json"
FIREBASE_KEY = DATA_DIR / "serviceAccountKey.json"


# --------------------------------------------------
# Firebase setup
# --------------------------------------------------

def init_firebase():
    if not FIREBASE_KEY.exists():
        print("❌ Firebase key not found:", FIREBASE_KEY)
        sys.exit(1)

    if not firebase_admin._apps:
        cred = credentials.Certificate(str(FIREBASE_KEY))
        cfg = load_firebase_config()
        initialize_app(cred, {"databaseURL": cfg["database_url"]})


# --------------------------------------------------
# Version bump
# --------------------------------------------------

def bump_version(version):
    parts = version.split(".")
    major, minor, patch = map(int, parts)
    patch += 1
    return f"{major}.{minor}.{patch}"


# --------------------------------------------------
# Sync Excel → Firebase
# --------------------------------------------------

def sync_excel_to_firebase():

    if not EXCEL_FILE.exists():
        print("❌ Excel file not found:", EXCEL_FILE)
        sys.exit(1)

    print("📊 Reading Excel:", EXCEL_FILE)

    xl = pd.ExcelFile(EXCEL_FILE)
    sheets = {}

    # ✅ STEP 1 — update version ONCE
    version_updated = False

    for sheet in xl.sheet_names:
        df = xl.parse(sheet)

        if sheet.strip().lower() == "appinfo" and not version_updated:
            for i, row in df.iterrows():
                key = str(row.iloc[0]).strip().lower()

                if key == "version":
                    old_version = str(row.iloc[1])
                    new_version = bump_version(old_version)

                    df.iloc[i, 1] = new_version
                    print(f"✅ Version updated: {old_version} → {new_version}")

                    version_updated = True
                    break

        sheets[sheet] = df

    # ✅ STEP 2 — save Excel ONCE
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # ✅ STEP 3 — build payload ONCE
    payload = {}

    for sheet, df in sheets.items():

        if sheet.strip().lower() == "appinfo":
            meta = {}
            for _, row in df.iterrows():
                key = str(row.iloc[0]).strip()
                value = row.iloc[1]
                meta[key] = value

            payload["metadata"] = meta

        else:
            payload[sheet] = df.to_dict(orient="records")

    # ✅ STEP 4 — upload ONCE
    print("☁ Uploading data to Firebase…")

    payload = json_safe(payload)
    db.reference("/").set(payload)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("✅ Firebase sync complete")

# -------------------------------------------------
# Optional Git sync (safe)
# -------------------------------------------------

def sync_to_github(commit_message):
    print("🚀 Pushing changes to Git")

    try:
        # ✅ Always pull first (safe)
        subprocess.run(["git", "pull", "--rebase"], check=True)

        subprocess.run(["git", "add", "."], check=True)

        commit = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True,
            text=True
        )

        print(commit.stdout)

        subprocess.run(["git", "push"], check=True)

        print("✅ GitHub sync done")

    except subprocess.CalledProcessError as e:
        print("⚠ Git sync failed:", e)


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":
    print("=== Developer Sync started ===")
    init_firebase()
    sync_excel_to_firebase()
    sync_to_github("Update content + version bump")
    print("=== Developer Sync finished ===")
