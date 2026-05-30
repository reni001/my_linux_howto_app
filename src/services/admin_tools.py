import shutil
from pathlib import Path

from src.utils.runtime_paths import get_runtime_paths


def _next_available_filename(folder: Path, filename: str) -> str:
    candidate = filename
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    i = 2

    while (folder / candidate).exists():
        candidate = f"{stem}_{i}{suffix}"
        i += 1

    return candidate


def copy_icon_to_assets(source_file: str, official: bool = False) -> str:
    paths = get_runtime_paths()

    # ✅ official/admin icons go to icons/
    # ✅ private user icons go to user_icons/
    target_dir = paths["assets"] / ("icons" if official else "user_icons")
    target_dir.mkdir(parents=True, exist_ok=True)

    src = Path(source_file)
    if not src.exists():
        raise FileNotFoundError(source_file)

    original_name = src.name.replace(" ", "_")

    # ✅ keep user/private icons obviously separate by name too
    # this avoids any collision with official names in UI loading
    wanted_name = original_name if official else f"user_{original_name}"

    filename = _next_available_filename(target_dir, wanted_name)
    dest = target_dir / filename

    shutil.copy2(src, dest)
    print(f"✅ SAVED ICON → {dest}")

    return filename
