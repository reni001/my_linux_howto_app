import shutil
from pathlib import Path
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from src.utils.runtime_paths import ensure_runtime_dirs, get_runtime_paths
from src.ui.file_picker_popup import open_file_picker

# ----------------------------------------
# REPO PATHS
# ----------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG = REPO_ROOT / "config"
DEFAULT_DATA = REPO_ROOT / "data"
DEFAULT_ASSETS = REPO_ROOT / "assets"

# ----------------------------------------
# FILE COPY HELPERS
# ----------------------------------------

def copy_file(src: Path, dst: Path):
    try:
        shutil.copy(src, dst)
        print(f"[OK] Copied → {dst}")
    except Exception as e:
        print(f"[ERROR] Failed to copy {src}")
        print(f"        {e}")


def copy_folder(src: Path, dst: Path):
    try:
        shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"[OK] Copied folder → {dst}")
    except Exception as e:
        print(f"[ERROR] Failed to copy folder {src}")
        print(f"        {e}")

# ----------------------------------------
# FILE PICKER (KIVY)
# ----------------------------------------

def ask_for_service_account(target_path: Path):

    def on_selected(path: Path):
        copy_file(path, target_path)

    open_file_picker(
        title="Select serviceAccountKey.json (optional)",
        callback=on_selected,
        filters=("*.json",)
    )

# ----------------------------------------
# MAIN INITIALIZATION
# ----------------------------------------

def initialize_first_run():
    print("\n===================================")
    print("[INIT] First run setup starting...")
    print("===================================\n")

    ensure_runtime_dirs()
    paths = get_runtime_paths()

    data_dir = paths["data"]
    base_dir = data_dir.parent
    assets_dir = base_dir / "assets"

    # ----------------------------------------
    # ✅ firebase.json (auto)
    # ----------------------------------------

    print("[STEP] Checking firebase.json...")

    firebase_src = DEFAULT_CONFIG / "firebase.json"
    firebase_dst = data_dir / "firebase.json"

    if not firebase_dst.exists():
        if firebase_src.exists():
            copy_file(firebase_src, firebase_dst)
        else:
            print("[WARNING] firebase.json not found in repo")
    else:
        print(f"[OK] Found → {firebase_dst}")

    # ----------------------------------------
    # ✅ serviceAccountKey.json (file picker)
    # ----------------------------------------

    print("\n[STEP] Checking serviceAccountKey.json...")

    service_dst = data_dir / "serviceAccountKey.json"

    if not service_dst.exists():
        print("[INFO] Opening file picker for serviceAccountKey.json...")

        # ⚠️ must be delayed until UI is ready
        Clock.schedule_once(lambda dt: ask_for_service_account(service_dst), 0.5)
    else:
        print(f"[OK] Found → {service_dst}")

    # ----------------------------------------
    # ✅ DATA FILES (Excel etc.)
    # ----------------------------------------

    print("\n[STEP] Checking data files...")

    if DEFAULT_DATA.exists():
        for file in DEFAULT_DATA.iterdir():
            if file.is_file():
                dst = data_dir / file.name

                if not dst.exists():
                    print(f"[INFO] Copying {file.name}")
                    copy_file(file, dst)
                else:
                    print(f"[OK] Exists → {file.name} (skipped)")
    else:
        print("[WARNING] No data folder found in repo")

    # ----------------------------------------
    # ✅ ASSETS
    # ----------------------------------------

    print("\n[STEP] Checking assets...")

    if not assets_dir.exists() or not any(assets_dir.iterdir()):
        if DEFAULT_ASSETS.exists():
            copy_folder(DEFAULT_ASSETS, assets_dir)
        else:
            print("[WARNING] assets folder missing in repo")
    else:
        print(f"[OK] Assets already exist")

    print("\n[DONE] First run setup complete\n")
    return True
