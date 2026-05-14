#!/usr/bin/env python3

import json
import sys
import math
from datetime import datetime

import pandas as pd
import firebase_admin
from firebase_admin import credentials, db, initialize_app

from src.runtime_paths import get_runtime_paths
from src.config import load_firebase_config



# --------------------------------------------------
# JSON sanitiser (CRITICAL)
# --------------------------------------------------

def json_safe(obj):
    """
    Recursively convert objects to JSON-safe types:
    - datetime -> ISO string
    - NaN / inf -> None
    """
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

    else:
        return obj


# --------------------------------------------------
# Runtime paths
# --------------------------------------------------

paths = get_runtime_paths()
DATA_DIR = paths["data"]

EXCEL_FILE = DATA_DIR / "main.xlsx"
CACHE_FILE = DATA_DIR / "cache.json"
FIREBASE_KEY = DATA_DIR / "serviceAccountKey.json"


# --------------------------------------------------
# Helpers
# --------------------------------------------------
#def make_json_safe(df):
#    """Ensure all DataFrame values are JSON-serialisable."""
    #return df.where(pd.notnull(df), None)


# --------------------------------------------------
# Firebase setup
# --------------------------------------------------

def init_firebase():
    if not FIREBASE_KEY.exists():
        print("❌ Firebase key not found:")
        print(FIREBASE_KEY)
        sys.exit(1)

    if not firebase_admin._apps:
        cred = credentials.Certificate(str(FIREBASE_KEY))
        cfg = load_firebase_config()
        initialize_app(cred, {"databaseURL": cfg["database_url"]})


# --------------------------------------------------
# Sync Excel → Firebase
# --------------------------------------------------

def sync_excel_to_firebase():
    if not EXCEL_FILE.exists():
        print("❌ Excel file not found:", EXCEL_FILE)
        sys.exit(1)

    print("📊 Reading Excel:", EXCEL_FILE)
    xl = pd.ExcelFile(EXCEL_FILE)

    payload = {}
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        payload[sheet] = df.to_dict(orient="records")

    print("☁ Uploading data to Firebase…")

    # ✅ FINAL GUARANTEE: only JSON-safe data reaches Firebase
    payload = json_safe(payload)
    db.reference("/").set(payload)

    # Cache locally
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("✅ Firebase sync complete")

# -------------------------------------------------
# Optional Git sync (safe)
# -------------------------------------------------

def sync_to_github(commit_message):
    print("🚀 Pushing changes to Git")

    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=False
        )
        subprocess.run(["git", "push"], check=True)
        print("✅ GitHub sync done")
    except subprocess.CalledProcessError as e:
        print("⚠ Git push failed:", e)



# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":
    print("=== Developer Sync started ===")
    init_firebase()
    sync_excel_to_firebase()
    print("=== Developer Sync finished ===")

















