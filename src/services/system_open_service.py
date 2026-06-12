import os
import html
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



def _wsl_to_windows_path(path):
    try:
        result = subprocess.check_output(['wslpath', '-w', path])
        return result.decode().strip()
    except Exception:
        return path


def open_path(path: str):
    if not os.path.exists(path):
        print(f"[OPEN] Path does not exist: {path}")
        return

    if is_wsl():
        win_path = _wsl_to_windows_path(path)
        _run_async(['explorer.exe', win_path])

    elif platform.system() == "Windows":
        _run_async(['explorer.exe', path])

    elif platform.system() == "Darwin":
        subprocess.Popen(['open', path])  # ✅ no thread

    else:
        subprocess.Popen(['xdg-open', path])  # ✅ no thread



def open_url(url: str):
    if not url:
        return

    # Decode HTML entities like &amp;
    url = html.unescape(url.strip())

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        if is_wsl():
            # WSL: open URL via Windows directly
            _run_async([
                'powershell.exe',
                '-NoProfile',
                '-Command',
                'Start-Process',
                url
            ])

        elif platform.system() == "Windows":
            os.startfile(url)

        elif platform.system() == "Darwin":
            subprocess.Popen(
                ['open', url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        else:
            subprocess.Popen(
                ['xdg-open', url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    except Exception as e:
        print(f"[OPEN] Failed to open URL: {url}")
        print(e)
