import shutil
from pathlib import Path

from src.utils.runtime_paths import get_runtime_paths


def copy_icon_to_assets(source_file: str) -> str:
    paths = get_runtime_paths()
    icons_dir = paths["assets"] / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    src = Path(source_file)
    if not src.exists():
        raise FileNotFoundError(source_file)

    filename = src.name.replace(" ", "_")
    dest = icons_dir / filename
    shutil.copy(src, dest)

    return filename


def export_backup_excel(app_data: dict):
    import pandas as pd

    paths = get_runtime_paths()
    excel_path = paths["data"] / "main.xlsx"

    topics = app_data.get("topics", []) or []
    steps = app_data.get("steps", []) or []
    meta = app_data.get("metadata", {}) or {}

    meta_df = pd.DataFrame(list(meta.items()), columns=["key", "value"])

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame(topics).to_excel(writer, sheet_name="topics", index=False)
        pd.DataFrame(steps).to_excel(writer, sheet_name="steps", index=False)
        meta_df.to_excel(writer, sheet_name="AppInfo", index=False)
