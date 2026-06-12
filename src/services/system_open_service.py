import os
import subprocess
import platform
import shutil
import webbrowser
from threading import Thread


def _run_async(cmd):
    def runner():
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            print("[OPEN ERROR] Command:", cmd)
            print("[OPEN ERROR]", e)

            import traceback
            traceback.print_exc()   # ✅ THIS IS IMPORTANT

    Thread(target=runner, daemon=True).start()

def is_wsl():
    return "microsoft" in platform.release().lower()


def open_path(path: str):
    if not os.path.exists(path):
        print(f"[OPEN] Path does not exist: {path}")
        return

    if is_wsl():
        _run_async(['explorer.exe', path])

    elif platform.system() == "Windows":
        _run_async(['explorer.exe', path])

    elif platform.system() == "Darwin":
        subprocess.Popen(['open', path])  # ✅ no thread

    else:
        subprocess.Popen(['xdg-open', path])  # ✅ no thread


def open_url(url: str):
    if not url:
        return

    # ✅ FIXED LINE
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        if is_wsl():
            _run_async(['explorer.exe', url])

        elif platform.system() == "Windows":
            _run_async(['explorer.exe', url])

        elif platform.system() == "Darwin":
            subprocess.Popen(['open', url])

        elif platform.system() == "Linux":
            subprocess.Popen(
                ['xdg-open', url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        else:
            webbrowser.open(url, new=2, autoraise=True)

    except Exception as e:
        print(f"[OPEN] Failed to open URL: {url}")
        print(e)
