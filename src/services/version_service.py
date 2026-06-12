import os
from pathlib import Path
from src.utils.runtime_paths import get_runtime_paths

def load_local_version():
    try:
        paths = get_runtime_paths()
        version_file = paths["data"] / "version.txt"

        print(f"DEBUG version file path: {version_file}")

        if version_file.exists():
            version = version_file.read_text().strip()
            print(f"✅ Loaded local version: {version}")
            return version

        print("⚠️ version.txt not found")

    except Exception as e:
        print(f"⚠️ Could not read local version: {e}")

    return "0.0.0"


def get_remote_version(metadata: dict):
    return metadata.get("version", "0.0.0")


def is_upgrade_available(local_version: str, remote_version: str):
    return local_version != remote_version



def write_local_version(version: str):
    try:
        paths = get_runtime_paths()
        version_file = paths["data"] / "version.txt"
        version_file.write_text(version)
        print(f"✅ Local version updated to {version}")
    except Exception as e:
        print(f"❌ Failed to write version.txt: {e}")


def is_appimage():
    return "APPIMAGE" in os.environ
