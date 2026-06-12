import requests
import zipfile
import tempfile
from pathlib import Path
import shutil
from src.utils.runtime_paths import get_runtime_paths

# ✅ Always-existing GitHub repo ZIP
REPO_ZIP_URL = "https://github.com/reni001/my_linux_howto_app/archive/refs/heads/main.zip"


def update_assets():
    print("🔄 Updating assets from GitHub...")

    paths = get_runtime_paths()
    assets_dst = paths["assets"]

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "repo.zip"

        r = requests.get(REPO_ZIP_URL, timeout=30)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        extracted_root = next(p for p in Path(tmpdir).iterdir() if p.is_dir())
        assets_src = extracted_root / "assets"

        for src_file in assets_src.rglob("*"):
            if not src_file.is_file():
                continue

            rel_path = src_file.relative_to(assets_src)
            dst_file = assets_dst / rel_path

            # ✅ preserve existing local/runtime files
            if dst_file.exists():
                continue

            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    print("✅ Assets updated")


def update_cache():
    print("✅ JSON cache is updated via Firebase sync (Excel removed)")


def upgrade_app_files():
    """
    Upgrade the application source files from GitHub ZIP.
    Copies code/UI files into the project/app root, but does NOT overwrite user data.
    """
    print("🔄 Upgrading full app from GitHub...")

    # For local/dev execution this points to the project root.
    # If you later package the app, you may want a different strategy.
    app_root = Path(__file__).resolve().parent.parent.parent

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "repo.zip"

        r = requests.get(REPO_ZIP_URL, timeout=30)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        extracted_root = next(p for p in Path(tmpdir).iterdir() if p.is_dir())

        for src_file in extracted_root.rglob("*"):
            if not src_file.is_file():
                continue

            rel_path = src_file.relative_to(extracted_root)

            # ✅ never overwrite runtime/user data
            if rel_path.parts and rel_path.parts[0] == "data":
                continue
            if rel_path.parts and rel_path.parts[0] == "__pycache__":
                continue
            if rel_path.suffix in {".pyc", ".pyo"}:
                continue

            dst_file = app_root / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    print("✅ Full app upgrade completed")
