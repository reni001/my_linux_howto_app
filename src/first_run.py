import shutil
from pathlib import Path

from src.runtime_paths import ensure_runtime_dirs, get_runtime_paths

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ASSETS = REPO_ROOT / "assets"
DEFAULT_DATA   = REPO_ROOT / "data"
DEFAULT_CONFIG = REPO_ROOT / "config"


def initialize_first_run():
    # ✅ ensure runtime dirs exist
    ensure_runtime_dirs()

    # ✅ ALWAYS resolve runtime paths dynamically
    paths = get_runtime_paths()
    data_dir = paths["data"]
    assets_dir = paths["assets"]

    # ---- firebase.json ----
    cfg_src = DEFAULT_CONFIG / "firebase.json"
    cfg_dst = data_dir / "firebase.json"
    if cfg_src.exists() and not cfg_dst.exists():
        shutil.copy(cfg_src, cfg_dst)
        print(f"✅ Copied firebase.json → {cfg_dst}")

    # ---- Excel ----
    excel_src = DEFAULT_DATA / "main.xlsx"
    excel_dst = data_dir / "main.xlsx"
    if excel_src.exists() and not excel_dst.exists():
        shutil.copy(excel_src, excel_dst)
        print(f"✅ Copied main.xlsx → {excel_dst}")

    # ---- Assets ----
    if not assets_dir.exists() or not any(assets_dir.iterdir()):
        shutil.copytree(DEFAULT_ASSETS, assets_dir, dirs_exist_ok=True)
        print(f"✅ Copied assets → {assets_dir}")
