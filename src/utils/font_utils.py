from pathlib import Path
from src.utils.runtime_paths import get_runtime_paths


def get_font_path(filename: str) -> str:
    paths = get_runtime_paths()
    return str(paths["assets"] / "fonts" / filename)
