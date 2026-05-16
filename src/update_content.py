import requests
import zipfile
import io
from src.runtime_paths import get_runtime_paths

# 🔧 Adjust these URLs to your real GitHub raw links
#ASSETS_ZIP_URL = "https://raw.githubusercontent.com/reni001/my_linux_howto_app/main/assets.zip"
#EXCEL_URL = "https://raw.githubusercontent.com/reni001/my_linux_howto_app/main/data/main.xlsx"


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
        with open(zip_path, "wb") as f:
            f.write(r.content)

        # ✅ Extract repo
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        # ✅ Find extracted assets folder
        extracted_root = next(Path(tmpdir).glob("*"))
        assets_src = extracted_root / "assets"

        # ✅ Copy assets
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    print("✅ Assets updated")


def update_excel():
    print("🔄 Updating Excel from Firebase...")

    # You can keep your existing logic or call sync logic
    print("✅ Excel update handled via Firebase sync at app start")
