import requests
import zipfile
import io
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

        # ✅ Download repo
        r = requests.get(REPO_ZIP_URL, timeout=30)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)

        # ✅ Extract repo
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        # ✅ Find extracted assets folder
        extracted_root = next(p for p in Path(tmpdir).iterdir() if p.is_dir())
        assets_src = extracted_root / "assets"

        # ✅ Copy assets
        # ✅ SAFE MERGE (DO NOT DELETE EXISTING)

        for src_file in assets_src.rglob("*"):
            if not src_file.is_file():
                continue

            rel_path = src_file.relative_to(assets_src)
            dst_file = assets_dst / rel_path

            # ✅ If destination exists → DO NOTHING (protects user + existing files)
            if dst_file.exists():
                continue

            # ✅ create folder if needed
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            # ✅ copy new file
            shutil.copy2(src_file, dst_file)

            # ❗ If it exists, DO NOTHING (preserve local file)

    print("✅ Assets updated")



def update_cache():
    print("✅ JSON cache is updated via Firebase sync (Excel removed)")

