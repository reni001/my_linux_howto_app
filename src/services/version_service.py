from pathlib import Path


def load_local_version():
    try:
        version_file = Path(__file__).resolve().parent.parent.parent / "version.txt"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception as e:
        print(f"⚠️ Could not read local version: {e}")

    return "0.0.0"


def get_remote_version(metadata: dict):
    return metadata.get("version", "0.0.0")


def is_upgrade_available(local_version: str, remote_version: str):
    return local_version != remote_version

def write_local_version(version: str):
    try:
        version_file = Path(__file__).resolve().parent.parent.parent / "version.txt"
        version_file.write_text(version)
        print(f"✅ Local version updated to {version}")
    except Exception as e:
        print(f"❌ Failed to write version.txt: {e}")
