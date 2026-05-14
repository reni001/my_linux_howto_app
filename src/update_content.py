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
    paths = get_runtime_paths()
    assets_dir = paths["assets"]

    print("⬇️ Downloading assets from repo…")
    r = requests.get(REPO_ZIP_URL, timeout=30)
    r.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(r.content))

    # GitHub ZIP has a top-level folder like: my_linux_howto_app-main/
    top = z.namelist()[0].split("/")[0] + "/"
    prefix = top + "assets/"

    for member in z.namelist():
        if member.startswith(prefix) and not member.endswith("/"):
            rel = member[len(prefix):]        # path relative to assets/
            target = assets_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())

    print("✅ Assets updated")



def update_excel():
    paths = get_runtime_paths()
    excel_path = paths["data"] / "main.xlsx"

    print("⬇️ Downloading Excel…")
    r = requests.get(EXCEL_URL, timeout=15)
    r.raise_for_status()

    # XLSX is a ZIP; must start with PK
    if not r.content.startswith(b"PK"):
        raise RuntimeError("Downloaded Excel is not a valid .xlsx (missing PK header).")

    tmp = excel_path.with_suffix(".xlsx.tmp")
    with open(tmp, "wb") as f:
        f.write(r.content)
    tmp.replace(excel_path)

    print("✅ Excel updated")

