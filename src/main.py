import time
import requests
import os
import platform
import webbrowser
import subprocess
import sys
import traceback
import shutil
import uuid
import re
from threading import Thread
from src.first_run import initialize_first_run
from pathlib import Path
from src.config import load_firebase_config
from src.runtime_paths import is_dev_mode
from src.update_content import update_assets, update_excel
from src.runtime_paths import get_runtime_paths
from src.editor import (
    is_admin_enabled,
    copy_icon_to_assets,
    add_topic_to_firebase,
    add_step_to_firebase,
    export_backup_excel,
)

# Kivy imports
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.properties import (
    StringProperty,
    DictProperty,
    BooleanProperty,
    NumericProperty,
    ListProperty
)
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse, Line

# ----- Check if python 3.12 is installed ---------

if sys.version_info >= (3, 14):
    print("\n⚠️ WARNING: Python 3.14 may be incompatible with Kivy")
    print("✅ The app will continue, but issues *might* occur")
    print("💡 Recommended: Use Python 3.12 if you encounter problems\n")

# --- CONFIGURATION ---
Window.size = (500, 850)

# ✅ ensure runtime dirs & config exist
initialize_first_run()
#Clock.schedule_once(lambda dt: initialize_first_run(), 1)

# ✅ now it is safe to load firebase.json
firebase_cfg = load_firebase_config()
DB_URL = (firebase_cfg.get("database_url") or firebase_cfg.get("databaseURL")) + "/.json"

# --- UI DEFINITIONS (KV) ---
# The KV layout was moved from the inlined KV string to an external file.
# This is a lossless move: main.kv contains the exact same KV content as before.
KV = None  # KV now lives in main.kv
#KV_FILE = os.path.join(SRC_DIR, "main.kv")
KV_FILE = str(Path(__file__).parent / "main.kv")
if KV_FILE not in Builder.files:
    Builder.load_file(KV_FILE)


APP_DATA = {}
# Theme Colors
COLOR_BLUE = [59/255, 101/255, 184/255, 1]
COLOR_ORANGE = [255/255, 139/255, 2/255, 1]
PANEL_COLOR = [179/255, 209/255, 255/255, 1]
NOTE_BG = [255/255, 250/255, 230/255, 1]
COLOR_GREEN = [0.2, 0.6, 0.2, 1]
COLOR_RED = [1, 0.3, 0.3, 1]

def load_app_metadata():
    global APP_DATA

    metadata = {}

    # ✅ 1. PRIMARY SOURCE: Firebase
    firebase_meta = APP_DATA.get("metadata", {}) or {}

    if isinstance(firebase_meta, list):
        firebase_meta = firebase_meta[0] if firebase_meta else {}

    if isinstance(firebase_meta, dict):
        metadata = {
            "app_name": firebase_meta.get("app_name", "Linux HowTo"),
            "version": firebase_meta.get("version", "0.0.0"),
            "last update": firebase_meta.get("last update", "unknown"),
            "description": firebase_meta.get("description", ""),
            "developer": firebase_meta.get("developer", ""),
            "changelog": firebase_meta.get("changelog", "")
        }

        print("✅ Metadata loaded from Firebase:", metadata)

    # ✅ 2. FALLBACK: Excel (only if Firebase is empty)
    if not metadata or metadata.get("version") == "0.0.0":
        try:
            import pandas as pd
            paths = get_runtime_paths()
            excel_path = paths["data"] / "main.xlsx"

            if excel_path.exists():
                df = pd.read_excel(excel_path, sheet_name="AppInfo")

                if df.shape[1] >= 2:
                    for _, row in df.iterrows():
                        key = str(row.iloc[0]).strip().lower()
                        value = "" if pd.isna(row.iloc[1]) else str(row.iloc[1]).strip()
                        metadata[key] = value

                    print("⚠️ Fallback metadata from Excel:", metadata)

        except Exception as e:
            print("[ERROR] Excel fallback failed:", e)

    metadata.setdefault("app_name", "Linux HowTo")

    return metadata

def open_url(url):
    if not url: return
    full_url = url.strip()
    if not (full_url.startswith('http://') or full_url.startswith('https://')):
        full_url = f"https://{full_url}"
    try:
        if platform.system() == "Linux":
            subprocess.Popen(['xdg-open', full_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            webbrowser.open(full_url, new=2, autoraise=True)
    except:
        webbrowser.open(full_url, new=2, autoraise=True)


def get_icon_path(filename):

    paths = get_runtime_paths()
    base = paths["assets"] / "icons"
    default_icon = base / "default.png"

    if not filename:
        return str(default_icon)

    filename = str(filename).strip()
    if filename.lower() in ("", "nan", "none"):
        return str(default_icon)

    icon_path = base / filename
    if not icon_path.is_file():
        print(f"⚠️ Missing icon file: {icon_path}")
        return str(default_icon)

    return str(icon_path)


# --- CLASSES ---

class AppMenu(ModalView):
    pass

# --- MAIN APP CLASS ---

class HoverBehavior(object):
    hovered = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return

        pos = args[1]
        inside = self.collide_point(*self.to_widget(*pos))
        if inside != self.hovered:
            self.hovered = inside

class HoverRow(BoxLayout, HoverBehavior):
    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(40)
        self.spacing = dp(6)

        from kivy.graphics import Color, RoundedRectangle
        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 0)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])

        self.bind(
            pos=self.update_rect,
            size=self.update_rect,
            hovered=self.update_bg,
            selected=self.update_bg
        )

    def update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def update_bg(self, *args):
        if self.selected:
            self.bg_color.rgba = [0.75, 0.85, 1, 1]   # ✅ strong blue (selected)
        elif self.hovered:
            self.bg_color.rgba = [0.90, 0.93, 0.98, 1]  # ✅ light blue (hover)
        else:
            self.bg_color.rgba = [1, 1, 1, 0]


    def on_hover(self, *args):
        if self.hovered:
            self.bg_color.rgba = [0.90, 0.93, 0.98, 1]
        else:
            self.bg_color.rgba = [1, 1, 1, 0]


class LinuxHowToApp(App):
    COLOR_BLUE_DARK   = [59/255, 101/255, 184/255, 1]   # already your main theme
    COLOR_BLUE_MEDIUM = [100/255, 140/255, 210/255, 1]
    COLOR_BLUE_LIGHT  = [170/255, 200/255, 240/255, 1]

    project_root = StringProperty("")

    # --- Update button visuals ---
    update_text = StringProperty("Update Content")
    update_bg = ListProperty([1, 0.7, 0.3, 1])          # orange
    update_fg = ListProperty([0.1, 0.25, 0.45, 1])     # dark blue text
    update_border = ListProperty([0, 0, 0, 0])         # ✅ NEW

    #--- Sync button visuals ---
    # --- Sync button state (MUST be Properties) ---
    sync_text = StringProperty("Developer Sync (Firebase & Git)")
    sync_bg = ListProperty([1, 0.5, 0, 1])          # orange
    sync_fg = ListProperty([0.1, 0.25, 0.45, 1])            # dark text
    sync_border = ListProperty([0, 0, 0, 0])        # invisible

    admin_enabled = BooleanProperty(False)   # ✅ for disabeling admin buttons
    admin_override = BooleanProperty(False)

    def open_app_info(self):
        self.sm.current = "app_info"

    def _open_app_info_from_popup(self, popup):
        popup.dismiss()              # ✅ close popup first
        self.sm.current = "app_info" # ✅ then switch screen

    def get_icon_path(self, filename):
        return get_icon_path(filename)


    def update_version_labels(self):
        """
        Update all version labels using self.metadata (Excel)
        """
        if not hasattr(self, 'sm'):
            return

        version = self.metadata.get("version", "0.0.0")
        last_update = self.metadata.get("last update", "")

        version_str = f"v{version} | {last_update}"

        screen_map = {
            'menu': 'version_label_menu',
            'search': 'version_label_search',
            'details': 'version_label_details',
            'article': 'version_label_article'
        }

        for screen_name, label_id in screen_map.items():
            try:
                screen = self.sm.get_screen(screen_name)
                if label_id in screen.ids:
                    screen.ids[label_id].text = version_str
            except Exception as e:
                print(f"DEBUG: Could not update {screen_name}: {e}")


    def on_start(self):
        pass


    def toggle_orientation(self):
        w, h = Window.size
        Window.size = (850, 500) if w < h else (500, 850)

    def open_app_menu(self):
        self._menu_popup = AppMenu()
        self._menu_popup.open()


    def open_database(self):
        paths = get_runtime_paths()
        target_file = str(paths["data"] / "main.xlsx")

        if not os.path.exists(target_file):
            return

        try:
            if platform.system() == "Windows":
                os.startfile(target_file)
            elif platform.system() == "Darwin":
                subprocess.Popen(['open', target_file])
            else:
                subprocess.Popen(['xdg-open', target_file])
        except Exception:
            pass

    def open_assets_folder(self):
        from src.runtime_paths import get_runtime_paths
        paths = get_runtime_paths()
        target_dir = str(paths["assets"])

        if not os.path.exists(target_dir):
            return

        try:
            if platform.system() == "Windows":
                os.startfile(target_dir)
            elif platform.system() == "Darwin":
                subprocess.Popen(['open', target_dir])
            else:
                subprocess.Popen(['xdg-open', target_dir])
        except Exception:
            pass

       
    def fetch_database(self):
        def _task():
            global APP_DATA
            try:
                print(f"DEBUG: Fetching from {DB_URL}")
                r = requests.get(DB_URL, timeout=10)
                if r.status_code == 200:
                    data = r.json() or {}

                    # ✅ NEVER reassign APP_DATA
                    APP_DATA.clear()

                    # ✅ update in place so UI keeps reference
                    APP_DATA.update(data)


                    # ✅ NORMALISE FIREBASE SHAPES (push keys -> dicts)
                    # topics: {pushKey: {...}}  -> [{...}, {...}]
                    if isinstance(APP_DATA.get("topics"), dict):
                        APP_DATA["topics"] = [
                            {"_key": k, **v} for k, v in APP_DATA["topics"].items()
                            if isinstance(v, dict)
                        ]

                    if isinstance(APP_DATA.get("steps"), dict):
                        APP_DATA["steps"] = [
                            {"_key": k, **v} for k, v in APP_DATA["steps"].items()
                            if isinstance(v, dict)
                        ]

                    if isinstance(APP_DATA.get("metadata"), list):
                        APP_DATA["metadata"] = APP_DATA["metadata"][0] if APP_DATA["metadata"] else {}


                    print("DEBUG: Data fetched successfully")

                    # ✅ Check for missing icons AFTER data is loaded
                    for t in APP_DATA.get("topics", []):
                        for k in ("Cat_Icon", "Sub_Icon", "Topic_Icon"):
                            if not t.get(k):
                                print(f"⚠️ Empty {k} in topic:", t.get("Title"))

                    if 'metadata' in APP_DATA:
                        print(f"DEBUG: Found Metadata: {APP_DATA['metadata']}")

                    # FIX: Change 'update_ui_after_fetch' to the correct method name 'update_menu'
                    # or whatever your stable version uses to draw the icons.
                    Clock.schedule_once(lambda dt: self.refresh_ui_data())
                else:
                    print(f"DEBUG: Server returned status {r.status_code}")
            except Exception as e:
                print(f"DEBUG: Fetch failed: {e}")

        Thread(target=_task, daemon=True).start()

    def refresh_ui_data(self):
        self.metadata = load_app_metadata()
        self.update_version_labels()
        """Updates the version label across all application screens."""
        if not hasattr(self, 'sm'):
            Clock.schedule_once(lambda dt: self.refresh_ui_data(), 0.1)
            return

        version = self.metadata.get("version", "0.0.0")
        last_update = self.metadata.get("last update", "")

        version_str = f"v{version} | {last_update}"

        # Map of Screen Name -> Label ID we created in KV
        screen_map = {
            'menu': 'version_label_menu',
            'search': 'version_label_search',
            'details': 'version_label_details',
            'article': 'version_label_article'
        }

        for screen_name, label_id in screen_map.items():
            try:
                screen_obj = self.sm.get_screen(screen_name)
                if label_id in screen_obj.ids:
                    screen_obj.ids[label_id].text = version_str
            except Exception as e:
                print(f"DEBUG: Could not update version on {screen_name}: {e}")

        # Also trigger the standard menu population
        try:
            menu_screen = self.sm.get_screen('menu')
            menu_screen.ids.menu_container.clear_widgets()
            menu_screen.populate_menu()

            # ✅ NEW: If user is currently on DetailScreen, reload it after data refresh
            try:
                if self.sm.current == "details":
                    detail_screen = self.sm.get_screen("details")

                    # keep current search filter if present
                    q = ""
                    if "local_search" in detail_screen.ids:
                        q = detail_screen.ids.local_search.text

                    detail_screen.load_content_from_cache(q)
            except Exception as e:
                print("DEBUG: detail screen refresh failed:", e)

            try:
                if self.sm.current == "article":
                    article_screen = self.sm.get_screen("article")
                    current_id = getattr(article_screen, "current_topic_id", None)

                    if current_id:
                        exists = any(
                            t.get("Topic_ID") == current_id
                            for t in APP_DATA.get("topics", [])
                        )
                        if not exists:
                            self.sm.current = "details"
            except Exception as e:
                print("DEBUG: article screen refresh failed:", e)


        except Exception as e:
            print(f"[ERROR] Failed to open file: {e}")
            pass

    def build(self):
        self.admin_enabled = is_admin_enabled()
        self.admin_override = False

        self.icon = get_icon_path("howtolinux-icon.png")
        self.sm = ScreenManager(transition=FadeTransition())
        self.sm.add_widget(MenuScreen(name='menu'))
        self.sm.add_widget(SearchScreen(name='search'))
        self.sm.add_widget(DetailScreen(name='details'))
        self.sm.add_widget(ArticleScreen(name='article'))
        self.sm.add_widget(AddTopicScreen(name="add_topic"))
        self.sm.add_widget(AddStepScreen(name="add_step"))
        self.sm.add_widget(AppInfoScreen(name="app_info"))

        self.fetch_database()
        return self.sm      

    def is_admin_mode(self):
        if self.admin_override:
            return not self.admin_enabled   # ✅ flips mode
        return self.admin_enabled          # ✅ normal behaviour

    def toggle_admin_mode(self):
        self.admin_override = not self.admin_override
        print(f"DEBUG: override = {self.admin_override}")

        # ✅ close and reopen menu so UI refreshes
        self._reopen_app_menu()

    def _reopen_app_menu(self):
        # close current popup - helper -
        if hasattr(self, "_menu_popup") and self._menu_popup:
            self._menu_popup.dismiss()

        # reopen fresh instance
        self.open_app_menu()

    def run_sync_script(self, *args):

        # --- UI: syncing state (IMMEDIATE) ---

        """Runs the sync.py script in the background."""
        try:
            import pandas  # noqa
        except ImportError:
            self.sync_text = "Developer Sync unavailable (pandas missing)"
            self.sync_fg = [1, 0, 0, 1]
            self.sync_border = [1, 0, 0, 1]
            return


        from pathlib import Path
        sync_script = str(Path(__file__).parent / "sync.py")

        if not os.path.exists(sync_script):
            self.sync_text = "sync.py missing!"
            self.sync_fg = [1, 0, 0, 1]
            self.sync_border = [1, 0, 0, 1]
            return

        # --- UI: syncing state ---

        self.sync_text = "Syncing…"
        self.sync_bg = [0.9, 0.9, 0.9, 1]
        self.sync_fg = [0.1, 0.25, 0.45, 1]
        self.sync_border = [0, 0, 0, 0]

        def run_proc():
            try:
                process = subprocess.Popen(
                    [sys.executable, "-m", "src.sync"],
                    cwd=Path(__file__).resolve().parent.parent,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                stdout, stderr = process.communicate()

                if process.returncode == 0:
                    Clock.schedule_once(self.sync_success, 0)
                else:

                    print("❌ Sync failed:\n", stderr)
                    Clock.schedule_once(lambda dt: self.sync_failed(), 0)

            except Exception as e:
                Clock.schedule_once(self.sync_failed, 0)

        Thread(target=run_proc, daemon=True).start()


    #--------- editin and deleting --------
    def edit_topic(self, data):
        screen = self.sm.get_screen("add_topic")

        # ✅ build taxonomy FIRST
        screen._build_taxonomy_maps()

        screen.edit_mode = True
        screen.edit_topic_id = str(data.get("Topic_ID") or "")
        screen.edit_topic_key = str(data.get("_key") or "")

        # ✅ store originals for restore logic (THIS FIXES "no stored category")
        screen._edit_category = str(data.get("Category") or "").strip()
        screen._edit_subcategory = str(data.get("Subcategory") or "").strip()

        # ✅ show Topic_ID in form (do NOT clear it)
        if "topic_id" in screen.ids:
            screen.ids.topic_id.text = screen.edit_topic_id

        # ✅ populate spinner values
        screen.ids.category.values = sorted(screen.cat_to_icon.keys(), key=str.lower)

        # start with empty, we will fill it via on_category_changed
        screen.ids.subcategory.values = []

        # ✅ temporarily block KV-triggered callbacks while setting text
        screen._skip_callbacks = True
        screen.ids.category.text = screen._edit_category
        screen.ids.subcategory.text = screen._edit_subcategory
        screen._skip_callbacks = False

        # ✅ NOW build subcategory list properly and set icons
        screen.on_category_changed(screen._edit_category)
        screen.on_subcategory_changed(screen._edit_subcategory)

        # ✅ fill fields
        screen.ids.title.text = data.get("Title", "")
        screen.ids.description.text = data.get("Description", "")
        screen.ids.urls.text = data.get("URLs", "")
        screen.ids.cat_icon.text = data.get("Cat_Icon", "")
        screen.ids.sub_icon.text = data.get("Sub_Icon", "")
        screen.ids.topic_icon.text = data.get("Topic_Icon", "")
        screen.ids.icon_path.text = ""
        screen.ids.topic_icon.text = data.get("Topic_Icon", "")

        # ✅ set header icon
        icon_file = data.get("Topic_Icon", "")

        if "header_icon" in screen.ids:
            if icon_file:
                try:
                    screen.ids.header_icon.source = self.get_icon_path(icon_file)
                except Exception as e:
                    print("DEBUG: failed loading topic icon:", e)
            else:
                # fallback
                screen.ids.header_icon.source = self.get_icon_path("howtolinux-icon.png")

        # ✅ LOAD STEPS BEFORE UI SWITCH
        screen.pending_steps = []

        for step in APP_DATA.get("steps", []):
            if step.get("Topic_ID") == data.get("Topic_ID"):
                screen.pending_steps.append({
                    "Step_Order": step.get("Step_Order"),
                    "Headline": step.get("Headline"),
                    "Header_2": step.get("Header_2"),
                    "Instruction": step.get("Instruction"),
                    "Code_Snippet": step.get("Code_Snippet"),
                    "Notes": step.get("Notes"),
                })

        screen.pending_steps.sort(key=lambda x: int(x.get("Step_Order", 999)))
        screen.refresh_steps_preview()
        screen.refresh_steps_list()

        # ✅ NOW switch screen
        self.sm.current = "add_topic"
        Clock.schedule_once(lambda dt: screen.refresh_steps_list(), 0)

        # ✅ ONLY ONE callback re-enable
        #Clock.schedule_once(
        #    lambda dt: setattr(screen, "_skip_callbacks", False),
        #    0.1
        #)

    def delete_topic(self, data):
        from src.editor import delete_topic_from_firebase


        node_key = str(data.get("_key") or "")
        topic_id = str(data.get("Topic_ID") or "")

        if not topic_id:
            return

        def confirm_delete(instance):
            popup.dismiss()

            try:
                deleted_topics, deleted_steps = delete_topic_from_firebase(node_key, topic_id)
                print(f"✅ Deleted topics: {deleted_topics}, steps: {deleted_steps}")

                # ✅ Step 1: trigger fresh fetch

                # 👇 IMPORTANT: chain refresh AFTER fetch
                self.fetch_database()
                Clock.schedule_once(after_fetch, 0.5)

            except Exception as e:
                print(f"❌ Delete failed: {e}")
        print("DEBUG deleting Topic_ID:", topic_id)


        # ✅ Popup UI
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        content.add_widget(Label(text="Are you sure you want to delete this topic?"))

        btn_box = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

        btn_yes = Button(text="DELETE", background_color=[1, 0.3, 0.3, 1])
        btn_no = Button(text="Cancel")

        btn_box.add_widget(btn_yes)
        btn_box.add_widget(btn_no)
        content.add_widget(btn_box)

        popup = Popup(
            #title="About Application",
            title="Delete Topic",
            content=content,
            size_hint=(0.5, 0.4),

            background="",                      # ✅ remove default background
            background_color=(0, 0, 0, 0)       # ✅ fully transparent
        )

        btn_yes.bind(on_release=confirm_delete)
        btn_no.bind(on_release=lambda x: popup.dismiss())

        popup.open()


    #---- update button behaviour -----

    def update_app_from_git(self, *args):

        # UI state
        self.update_text = "Updating…"
        self.update_bg = [0.9, 0.9, 0.9, 1]
        self.update_fg = [0.1, 0.25, 0.45, 1]

        def run_update():
            try:
                print(f"DEBUG: is_dev_mode = {is_dev_mode()}")

                if is_dev_mode():
                    print("🔄 DEV MODE: Updating application from Git…")

                    subprocess.run(["git", "pull"], check=True)

                    paths = get_runtime_paths()
                    repo_root = Path(__file__).resolve().parent.parent
                    repo_assets = repo_root / "assets"
                    runtime_assets = paths["assets"]

                    print(f"DEBUG repo_assets: {repo_assets}")
                    print(f"DEBUG runtime_assets: {runtime_assets}")

                    if repo_assets.exists():
                        import shutil
                        shutil.copytree(repo_assets, runtime_assets, dirs_exist_ok=True)

                        print("✅ Runtime assets updated from Git")

                        # verification
                        copied_files = list((runtime_assets / "icons").glob("*"))
                        print(f"DEBUG copied icons count: {len(copied_files)}")

                    else:
                        print("⚠ Repo assets folder not found!")

                else:
                    print("🌍 PROD MODE: Updating via HTTP")
                    update_assets()
                    update_excel()

                Clock.schedule_once(self.update_success, 0)

            except Exception as e:
                print(f"❌ Update failed: {e}")
                traceback.print_exc()
                Clock.schedule_once(self.update_failed, 0)

        Thread(target=run_update, daemon=True).start()


    def update_success(self, *args):
        self.update_text = "Update successful ✓"
        self.update_bg = [0.9, 0.95, 0.9, 1]        # light background
        self.update_fg = [0.1, 0.5, 0.1, 1]         # dark green text
        self.update_border = [0.3, 0.8, 0.3, 1]     # green border
        self.metadata = load_app_metadata()
        self.refresh_ui_data()

        Clock.schedule_once(self.restore_update_button, 2)


    def update_failed(self, *args):
        self.update_text = "Update failed ✗"
        self.update_bg = [0.98, 0.9, 0.9, 1]        # light red
        self.update_fg = [0.7, 0.1, 0.1, 1]         # dark red text
        self.update_border = [1, 0.2, 0.2, 1]       # ✅ red border
        self.metadata = load_app_metadata()
        self.refresh_ui_data()

        Clock.schedule_once(self.restore_update_button, 3)


    def restore_update_button(self, *args):
        self.update_text = "Update App & Icons"
        self.update_bg = [1, 0.7, 0.3, 1]            # orange
        self.update_fg = [0.1, 0.25, 0.45, 1]
        self.update_border = [0, 0, 0, 0]            # ✅ reset


    #---- syncronize button behaviour -----

    def sync_success(self, *args):
        self.sync_text = "Sync successful ✓"
        self.sync_bg = [0.9, 0.95, 0.9, 1]        # light background
        self.sync_fg = [0.1, 0.5, 0.1, 1]         # dark green text
        self.sync_border = [0.3, 0.8, 0.3, 1]     # green border
        self.metadata = load_app_metadata()
        self.refresh_ui_data()


        Clock.schedule_once(self.restore_sync_button, 3)


    def sync_failed(self, *args):
        self.sync_text = "Sync failed ✗"
        self.sync_bg = [0.98, 0.9, 0.9, 1]
        self.sync_fg = [0.7, 0.1, 0.1, 1]         # dark red text
        self.sync_border = [1, 0.2, 0.2, 1]       # red border

        Clock.schedule_once(self.restore_sync_button, 3)

    def restore_sync_button(self, *args):
        self.sync_text = "Developer Sync (Firebase & Git)"
        self.sync_bg = [1, 0.5, 0, 1]              # orange
        self.sync_fg = [0.1, 0.25, 0.45, 1]        # dark text
        self.sync_border = [0, 0, 0, 0]            # no border

    def show_about(self):
        metadata = self.metadata

        name = metadata.get('app_name', 'Linux HowTo')
        version = metadata.get('version', '0.0.0')
        last_update = metadata.get('last update', 'unknown')
        dev_name = metadata.get('developer', '')
        desc = metadata.get('description', '')
        change = metadata.get('changelog', '').replace("\\n", "\n")

        RADIUS = 22
        BORDER_W = 2

        # ✅ ONE rounded outer container (background + orange border)
        root_layout = FloatLayout()

        with root_layout.canvas.before:
            Color(0.12, 0.18, 0.30, 1)  # darker blue
            root_layout.bg = RoundedRectangle(pos=root_layout.pos, size=root_layout.size, radius=[RADIUS])

        with root_layout.canvas.after:
            Color(1, 0.55, 0, 1)  # orange
            root_layout.border = Line(
                rounded_rectangle=(root_layout.x + 1, root_layout.y + 1,
                                root_layout.width - 2, root_layout.height - 2,
                                RADIUS),
                width=BORDER_W
            )

        def _sync_popup_bg(*_):
            root_layout.bg.pos = root_layout.pos
            root_layout.bg.size = root_layout.size
            root_layout.border.rounded_rectangle = (
                root_layout.x + 1, root_layout.y + 1,
                root_layout.width - 2, root_layout.height - 2,
                RADIUS
            )

        root_layout.bind(pos=_sync_popup_bg, size=_sync_popup_bg)
        _sync_popup_bg()  # ✅ apply once immediately

        # ✅ Content (NO inner border/card)
        outer = BoxLayout(
            orientation='vertical',
            padding=[20, 15, 20, 20],
            spacing=15,
            size_hint=(0.95, 0.95),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        # ✅ Header block
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=110,
            spacing=20
        )

        # ✅ left: TEXT BLOCK
        text_block = BoxLayout(
            orientation="vertical",
            spacing=4
        )

        text_block.add_widget(Label(
            text=f"[b]{name}[/b]",
            markup=True,
            font_size="28sp",   # ✅ bigger title
            halign="left",
            valign="middle",
            color=[1, 1, 1, 1],
            size_hint_y=None,
            height=35
        ))

        text_block.add_widget(Label(
            text=f"Version {version}",
            halign="left",
            color=[0.9, 0.9, 1, 1],
            size_hint_y=None,
            height=25
        ))

        text_block.add_widget(Label(
            text=f"Last update: {last_update}",
            halign="left",
            color=[0.9, 0.9, 1, 1],
            size_hint_y=None,
            height=25
        ))

        text_block.add_widget(Label(
            text=f"[color=ffaa33]{dev_name}[/color]",
            markup=True,
            halign="left",
            size_hint_y=None,
            height=25
        ))

        header.add_widget(text_block)

        # ✅ right: LOGO
        header.add_widget(Image(
            source=self.get_icon_path("howtolinux-icon.png"),
            size_hint=(None, None),
            size=(95, 95),
            pos_hint={"center_y": 0.5}
        ))

        outer.add_widget(header)
        # ✅ subtle divider under header
        divider = BoxLayout(
            size_hint_y=None,
            height=1,
            padding=[0, 5, 0, 5]
        )

        with divider.canvas.before:
            Color(1, 0.55, 0, 0.3)   # ✅ very subtle light line
            divider.line = Line(points=[])

        def update_line(*_):
            divider.line.points = [
                divider.x, divider.y + divider.height / 2,
                divider.right, divider.y + divider.height / 2
            ]

        divider.bind(pos=update_line, size=update_line)

        outer.add_widget(divider)

        # ✅ Scrollable content
        scroll = ScrollView(size_hint=(1, 1), bar_width=8)

        scroll_content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=10,
            padding=[15, 10]
        )
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        desc_label = Label(
            text=f"[i]{desc}[/i]",
            markup=True,
            size_hint_y=None,
            halign='center',
            valign='top',
            color=[0.9, 0.9, 1, 1]
        )
        desc_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val, None)),
            texture_size=lambda inst, val: setattr(inst, 'height', val[1])
        )
        scroll_content.add_widget(desc_label)

        title_label = Label(
            text="[b]WHAT'S NEW[/b]",
            markup=True,
            size_hint_y=None,
            height=30,
            halign='left',
            valign='middle',
            color=[1, 1, 1, 1]
        )
        title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        scroll_content.add_widget(title_label)

        changelog_label = Label(
            text=change,
            size_hint_y=None,
            halign='left',
            valign='top',
            color=[0.9, 0.9, 1, 1]
        )
        changelog_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val, None)),
            texture_size=lambda inst, val: setattr(inst, 'height', val[1])
        )
        scroll_content.add_widget(changelog_label)

        scroll.add_widget(scroll_content)
        outer.add_widget(scroll)

        # ✅ Buttons row
        btn_row = BoxLayout(size_hint_y=None, height=50, spacing=10)

        btn_close = Button(
            text='CLOSE',
            background_normal='',
            background_color=self.COLOR_BLUE_MEDIUM,
            color=[1, 1, 1, 1],
            bold=True
        )

        app = App.get_running_app()

        btn_edit = Button(
            size_hint=(None, None),
            size=(40, 40),
            disabled=not app.is_admin_mode(),
            opacity=1 if app.is_admin_mode() else 0.3,
            background_normal=self.get_icon_path("edit.png"),
            background_down=self.get_icon_path("edit.png"),
            background_color=[1, 1, 1, 1],
            border=(0, 0, 0, 0),
            text=""
        )

        btn_row.add_widget(btn_close)
        btn_row.add_widget(btn_edit)
        outer.add_widget(btn_row)

        root_layout.add_widget(outer)

        popup = Popup(
            title="About the App",
            content=root_layout,
            size_hint=(0.9, 0.9),
            background="",
            background_color=(0, 0, 0, 0),
            separator_height=0   # ✅ THIS removes the top line
        )

        btn_close.bind(on_release=popup.dismiss)
        btn_edit.bind(on_release=lambda x: self._open_app_info_from_popup(popup))

        popup.open()

    def open_new_topic(self):
        screen = self.sm.get_screen("add_topic")

        # ✅ FIRST build taxonomy maps
        screen._build_taxonomy_maps()

        # ✅ THEN set mode
        screen.edit_mode = False
        screen.edit_topic_id = ""

        # ✅ TEMPORARILY disable callbacks
        screen._skip_callbacks = True

        # ✅ THEN reset form safely
        screen.cancel_edit()

        # ✅ populate dropdowns AFTER reset
        screen._populate_category_spinner()

        # ✅ re-enable callbacks AFTER UI update
        Clock.schedule_once(
            lambda dt: setattr(screen, "_skip_callbacks", False), 0.1
        )

        self.sm.current = "add_topic"


# (Rest of the Screen and Widget classes remain same as your main.py)
class RotatableArrow(Image):
    angle = NumericProperty(0)

class CategoryCard(ButtonBehavior, BoxLayout):
    name = StringProperty("")
    icon_source = StringProperty("")

class EntryListItem(ButtonBehavior, BoxLayout):
    title = StringProperty("")
    desc = StringProperty("")
    icon_source = StringProperty("")
    data = DictProperty({})

# --- Restoration of Expandable Logic ---

class ClickableHeader(ButtonBehavior, BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(50)
        self.padding = [dp(10), dp(5)]
        self.spacing = dp(10)

class ExpandableSection(BoxLayout):
    is_open = BooleanProperty(True)
    stored_widgets = ListProperty([])

    def __init__(self, title, icon, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, **kwargs)
        self.spacing = dp(5)

        # Header setup
        self.header = ClickableHeader()
        self.header.add_widget(Image(source=icon, size_hint_x=None, width=dp(30)))

        self.title_label = Label(
            text=str(title).upper(),
            color=COLOR_ORANGE,
            bold=True,
            font_size='16sp',
            halign='left',
            valign='middle'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        self.header.add_widget(self.title_label)

        self.arrow = RotatableArrow(
            source=get_icon_path("down_arrow.png"), size_hint_x=None, width=dp(25)
        )
        self.header.add_widget(self.arrow)

        self.header.bind(on_release=self.toggle)
        self.add_widget(self.header)

        # Content setup
        self.list_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self.list_box.bind(minimum_height=self.list_box.setter('height'))
        self.add_widget(self.list_box)

        # Bind total height to children
        self.bind(minimum_height=self.setter('height'))

    def add_entry(self, widget):
        self.stored_widgets.append(widget)
        if self.is_open:
            self.list_box.add_widget(widget)

    def toggle(self, *args):
        self.is_open = not self.is_open
        if self.is_open:
            for w in self.stored_widgets:
                self.list_box.add_widget(w)
            self.arrow.angle = 0
        else:
            self.list_box.clear_widgets()
            self.arrow.angle = +90

#---------------Screen Classes--------------------

class MenuScreen(Screen):
    def on_enter(self):
        self.check_data()
        #if not self.ids.menu_container.children: self.check_data()

    def check_data(self, *args):
        if not APP_DATA:
            Clock.schedule_once(self.check_data, 0.2)
            return

        self.populate_menu()

    def populate_menu(self):
        topics = APP_DATA.get('topics', [])
        unique_cats = {}
        for t in topics:
            if isinstance(t, dict) and t.get("Category"):
                unique_cats[t['Category']] = t.get('Cat_Icon')
        self.ids.menu_container.clear_widgets()
        for name, icon in unique_cats.items():
            card = CategoryCard(name=name, icon_source=get_icon_path(icon))
            card.bind(on_release=lambda x, n=name: self.go_details(n))
            self.ids.menu_container.add_widget(card)
    def go_details(self, name):
        self.manager.selected_category = name
        self.manager.last_screen = 'menu'
        self.manager.current = 'details'

class SearchScreen(Screen):
    def on_enter(self):
        self.ids.search_input.focus = True
        self.filter_results(self.ids.search_input.text)
    def go_back(self):
        self.ids.search_input.text = ""
        self.manager.current = 'menu'
    def go_article(self, instance):
        self.manager.last_screen = 'search'
        self.manager.get_screen('article').setup_article(instance.data)
        self.manager.current = 'article'
    def filter_results(self, query):
        self.ids.results_container.clear_widgets()
        if not query or len(query) < 2: return
        query = query.lower().strip()
        all_topics = APP_DATA.get('topics', [])
        matches = [t for t in all_topics if t and (query in str(t.get('Title','')).lower() or query in str(t.get('Category','')).lower() or query in str(t.get('Description', '')).lower())]
        matches.sort(key=lambda x: str(x.get('Category','')).upper())
        current_category = None
        for item in matches:
            cat_name = str(item.get('Category','')).upper()
            if cat_name != current_category:
                current_category = cat_name
                header = Label(text=f"  {current_category}", color=COLOR_ORANGE, bold=True, font_size='18sp', size_hint_y=None, height=dp(50), halign='left', text_size=(Window.width-dp(40), None))
                self.ids.results_container.add_widget(header)
            btn = EntryListItem(title=item.get('Title',''), desc=item.get('Description',''), icon_source=get_icon_path(item.get('Topic_Icon')), data=item)
            btn.bind(on_release=self.go_article)
            self.ids.results_container.add_widget(btn)

class DetailScreen(Screen):
    header_title = StringProperty("")

    def on_pre_enter(self):
        self.header_title = getattr(self.manager, 'selected_category', "")
        self.ids.local_search.text = ""
        self.load_content_from_cache()

    def on_kv_post(self, base_widget):
        """
        Called after KV ids are ready.
        Bind focus handlers to all TextInput fields so ScrollView stops     stealing focus.
        """
        for w in self.walk():
            if isinstance(w, TextInput):
                w.bind(focus=self._on_any_textinput_focus)

    def _on_any_textinput_focus(self, instance, focused):
        """
        When a TextInput is focused, disable scrolling.
        When focus is lost, re-enable scrolling.
        """
        if "form_scroll" in self.ids:
            self.ids.form_scroll.do_scroll_y = not focused

    def load_content_from_cache(self, query=""):
        self.ids.list_container.clear_widgets()
        if not APP_DATA: return
        cat_label = Label(text=self.header_title.upper(), color=COLOR_BLUE, bold=True, font_size='24sp', size_hint_y=None, height=dp(50), halign='left', text_size=(Window.width - dp(30), None))
        self.ids.list_container.add_widget(cat_label)
        target_cat = self.header_title.strip().lower()
        query = query.lower().strip()
        all_topics = APP_DATA.get('topics', [])
        items = [t for t in all_topics if t and str(t.get('Category')).strip().lower() == target_cat]
        if query:
            items = [i for i in items if query in str(i.get('Title','')).lower() or query in str(i.get('Description','')).lower()]
        subs = {}
        for i in items:
            s = i.get('Subcategory', 'General')
            if not s or str(s).lower() == 'nan': s = 'General'
            if s not in subs: subs[s] = []
            subs[s].append(i)
        for sub_name in sorted(subs.keys()):
            sub_items = subs[sub_name]
            section = ExpandableSection(sub_name, get_icon_path(sub_items[0].get('Sub_Icon')))
            for item in sub_items:
                btn = EntryListItem(title=item.get('Title',''), desc=item.get('Description',''), icon_source=get_icon_path(item.get('Topic_Icon')), data=item)
                btn.bind(on_release=self.go_article)
                section.add_entry(btn)
            self.ids.list_container.add_widget(section)
    def go_article(self, instance):
        self.manager.last_screen = 'details'
        self.manager.get_screen('article').setup_article(instance.data)
        self.manager.current = 'article'

#---------- Article Screen ------

class ArticleScreen(Screen):
    def go_back(self):
        dest = getattr(self.manager, 'last_screen', 'details')
        self.manager.current = dest

    def setup_article(self, data):
        if not data:
            return

        # ✅ STORE CURRENT TOPIC
        self.current_topic_id = data.get("Topic_ID")
        self.current_topic_key = data.get("_key")

        self.ids.content_box.clear_widgets()
        self.ids.content_box.spacing = dp(15)
        topic_id = data.get('Topic_ID')

        def safe_str(val, default=""):
            if val is None or str(val).lower() == 'nan': return default
            return str(val).strip()

        # --- 1. TOP ICON ---
        self.ids.content_box.add_widget(Image(
            source=get_icon_path(safe_str(data.get('Topic_Icon'))),
            size_hint_y=None,
            height=dp(120)
        ))

        # --- 2. TOPIC TITLE ---
        title_lbl = Label(
            text=safe_str(data.get('Title')),
            color=COLOR_BLUE,
            font_size='28sp',
            bold=True,
            size_hint_y=None,
            halign='center'
        )
        title_lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                       texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
        self.ids.content_box.add_widget(title_lbl)

        # --- 3. TOPIC DESCRIPTION ---
        desc_text = safe_str(data.get('Description'))
        if desc_text:
            desc_lbl = Label(
                text=desc_text,
                color=[0.3, 0.3, 0.3, 1],
                font_size='18sp',
                italic=True,
                size_hint_y=None,
                halign='left'
            )
            desc_lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                          texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
            self.ids.content_box.add_widget(desc_lbl)

        # --- 4. TOPIC URLS ---
        raw_topic_urls = safe_str(data.get('URLs'))
        if raw_topic_urls:
            url_list = [u.strip() for u in raw_topic_urls.split(',') if u.strip()]
            for link in url_list:
                url_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30), spacing=dp(10))
                url_box.add_widget(Image(source='assets/icons/link2.png', size_hint_x=None, width=dp(20)))
                url_btn = Button(text=link, color=[0.1, 0.4, 0.8, 1], background_color=[0,0,0,0], font_size='15sp', underline=True, halign='left', shorten=True, shorten_from='right', size_hint_x=1)
                url_btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
                url_btn.bind(on_release=lambda x, u=link: open_url(u))
                url_box.add_widget(url_btn)
                self.ids.content_box.add_widget(url_box)

        # --- 5. STEPS (The Loop where Header_2 lives) ---
        all_steps = APP_DATA.get('steps', [])
        topic_steps = [s for s in all_steps if s and s.get('Topic_ID') == topic_id]
        topic_steps.sort(key=lambda x: int(x.get('Step_Order', 999)))

        for step in topic_steps:
            card = BoxLayout(orientation='vertical', size_hint_y=None, padding=dp(20), spacing=dp(12))
            card.bind(minimum_height=card.setter('height'))
            with card.canvas.before:
                Color(rgba=[1, 1, 1, 1])
                card.bg_rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12),])
            card.bind(pos=self._update_graphics, size=self._update_graphics)

            # --- STEP HEADLINE ---
            h1 = safe_str(step.get('Headline'))
            if h1:
                lbl = Label(text=h1, color=COLOR_BLUE, bold=True, font_size='20sp', size_hint_y=None, halign='left')
                lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)), texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
                card.add_widget(lbl)

            # --- STEP HEADER_2 (Sub Headline) ---
            h2 = safe_str(step.get('Header_2'))
            if h2:
                # Styled as Orange, Bold, slightly smaller than Headline
                h2_lbl = Label(text=h2, color=COLOR_ORANGE, bold=True, font_size='17sp', size_hint_y=None, halign='left')
                h2_lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)), texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
                card.add_widget(h2_lbl)

            # --- STEP INSTRUCTION ---
            ins = safe_str(step.get('Instruction'))
            if ins:
                lbl = Label(text=ins, color=[0.2, 0.2, 0.2, 1], font_size='18sp', size_hint_y=None, halign='left')
                lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)), texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
                card.add_widget(lbl)

            # --- CODE SNIPPET (Stable Logic) ---
            code = safe_str(step.get('Code_Snippet'))
            if code:
                code_anchor = AnchorLayout(anchor_x='right', anchor_y='top', size_hint_y=None)
                code_box = BoxLayout(orientation='vertical', size_hint_y=None, padding=[dp(12), dp(12), dp(80), dp(12)])
                with code_box.canvas.before:
                    Color(rgba=[0.15, 0.15, 0.15, 1])
                    code_box.bg_rect = RoundedRectangle(pos=code_box.pos, size=code_box.size, radius=[dp(6),])
                code_box.bind(minimum_height=code_box.setter('height'))
                code_box.bind(pos=self._update_graphics, size=self._update_graphics)
                code_lbl = Label(text=code, font_family='Roboto', color=[1, 0.5, 0, 1], font_size='15sp', size_hint_y=None, halign='left')
                code_lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)), texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
                code_box.add_widget(code_lbl)
                code_anchor.add_widget(code_box)
                code_box.bind(height=code_anchor.setter('height'))
                copy_btn = Button(text="Copy", size_hint=(None, None), size=(dp(70), dp(40)), background_color=[0.3, 0.3, 0.3, 1])
                copy_btn.bind(on_release=lambda x, c=code: self.copy_to_clipboard(x, c))
                code_anchor.add_widget(copy_btn)
                card.add_widget(code_anchor)

            # --- NOTES (Stable Logic) ---
            note = safe_str(step.get('Notes'))
            if note:
                note_container = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(12), padding=dp(12))
                with note_container.canvas.before:
                    Color(rgba=NOTE_BG)
                    note_container.bg_rect = RoundedRectangle(pos=note_container.pos, size=note_container.size, radius=[dp(6),])
                note_container.bind(minimum_height=note_container.setter('height'))
                note_container.bind(pos=self._update_graphics, size=self._update_graphics)
                note_container.add_widget(
                    Image(source=get_icon_path("note.png"),
                        size_hint=(None, None), 
                        size=(dp(24), dp(24)), pos_hint={'top': 1})
                )
                markup_text = "[b][color=ff8b02]NOTE:[/color][/b]\n" + note
                n_lbl = Label(text=markup_text, markup=True, color=[0.2, 0.2, 0.2, 1], font_size='16sp', italic=True, size_hint_y=None, halign='left', valign='top')
                n_lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)), texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
                note_container.add_widget(n_lbl)
                card.add_widget(note_container)

            self.ids.content_box.add_widget(card)

    def _update_graphics(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    def copy_to_clipboard(self, btn, text):
        Clipboard.copy(text)
        btn.text = "Copied!"
        btn.background_color = [0.1, 0.6, 0.1, 1]
        Clock.schedule_once(lambda dt: setattr(btn, 'text', 'Copy'), 2)
        Clock.schedule_once(lambda dt: setattr(btn, 'background_color', [0.3, 0.3, 0.3, 1]), 2)

#-------------- editor screen---------------
class AddTopicScreen(Screen):
    edit_topic_key = StringProperty("")
    edit_mode = BooleanProperty(False)     # ✅ THIS FIXES YOUR CRASH
    edit_topic_id = StringProperty("")     # ✅ needed for edit tracking
    pending_steps = ListProperty([])  # list of step dicts to save together with the topic
    selected_step_index = NumericProperty(-1)   # -1 means "no step selected"

    def on_pre_enter(self):
        if not is_admin_enabled():
            self.ids.status_label.text = "Editor disabled (admin key missing)."
            self.ids.save_btn.disabled = True
            self.ids.add_step_btn.disabled = True
        else:
            self.ids.status_label.text = ""
            self.ids.save_btn.disabled = False
            self.ids.add_step_btn.disabled = False

        if self.edit_mode:
            # keep Topic_ID locked
            if "topic_id" in self.ids:
                self.ids.topic_id.readonly = True

            self.refresh_steps_preview()
            self.refresh_steps_list()

            # ✅ ensure dropdowns exist in edit mode too
            self._schedule_populate_dropdowns()
            return

        # ✅ ADD MODE (only here)
        if "topic_id" in self.ids:
            self.ids.topic_id.text = ""
            self.ids.topic_id.readonly = False

        if "header_icon" in self.ids:
            from kivy.app import App
            self.ids.header_icon.source = App.get_running_app().get_icon_path("howtolinux-icon.png")

        self.refresh_steps_preview()
        self.refresh_steps_list()
        self._schedule_populate_dropdowns()

    def _schedule_populate_dropdowns(self):
        # APP_DATA might still be empty if fetch is in progress
        def _try(_dt):
            global APP_DATA
            if isinstance(APP_DATA, dict) and APP_DATA.get("topics"):
                self._build_taxonomy_maps()
                self._populate_category_spinner()

                if self.edit_mode:
                    Clock.schedule_once(lambda dt: self._restore_edit_values(), 0.1)

            else:
                Clock.schedule_once(_try, 0.2)
        Clock.schedule_once(_try, 0)

    def _build_taxonomy_maps(self):

        global APP_DATA
        topics = APP_DATA.get("topics", [])


        self.cat_to_icon = {}
        self.all_subcategories = set()
        self.sub_to_icon = {}        # ✅ REQUIRED
        self.sub_icon_global = {}    # ✅ REQUIRED

        for t in topics:
            if not isinstance(t, dict):
                continue
            cat = str(t.get("Category", "")).strip()
            sub = str(t.get("Subcategory", "")).strip()

            # ✅ normalise case (important!)
            sub = sub.lower()

            if not cat:
                continue

            # Category icon
            if cat not in self.cat_to_icon:
                icon = str(t.get("Cat_Icon", "") or "").strip()
                self.cat_to_icon[cat] = icon

            # Subcategory list
            if sub and sub.lower() != "nan":
                sub = sub.lower()              # ✅ normalize (fix duplicates)
                self.all_subcategories.add(sub)


            # ✅ GLOBAL subcategory icon (NEW)
            if sub and sub != "nan":
                sicon = str(t.get("Sub_Icon", "") or "").strip()

                if sicon:
                    # ✅ global mapping
                    if sub not in self.sub_icon_global:
                        self.sub_icon_global[sub] = sicon

                    # ✅ keep category-specific mapping
                    key = (cat, sub)
                    if key not in self.sub_to_icon:
                        self.sub_to_icon[key] = sicon


    def _populate_category_spinner(self):
        #if self.edit_mode:
        #    return

        cats = sorted(self.cat_to_icon.keys(), key=str.lower)

        self.ids.category.values = cats

        # ✅ Always force placeholder AFTER values set
        if not self.edit_mode:
            self.ids.category.text = "Click to choose category"

        # ✅ Reset subcategory as well
        if not self.edit_mode:
            self.ids.subcategory.values = []
            self.ids.subcategory.text = "Click to choose subcategory"


        # ✅ Clear icons until selection is made
        self.ids.cat_icon.text = ""
        self.ids.sub_icon.text = ""

    def on_category_changed(self, category_text):
        if not hasattr(self, "sub_to_icon"):
            return

        if getattr(self, "_skip_callbacks", False):
            return

        #if category_text == "Click to choose category":
        #    return
        """
        Called by KV on category spinner change.
        Updates subcategory dropdown and auto-fills cat_icon / sub_icon.
        """
        cat = str(category_text).strip()

        # auto-fill Cat_Icon
        cat_icon = self.cat_to_icon.get(cat, "")
        self.ids.cat_icon.text = cat_icon

        # update subcategory list
        subs = sorted(
            [s.capitalize() for s in self.all_subcategories],
            key=str.lower
        )


        if not subs:
            subs = ["General"]   # ✅ fallback

        self.ids.subcategory.values = subs

        # start clean: do NOT keep old selection
        if not self.edit_mode:
            # only reset in add mode
            self.ids.subcategory.text = "Select Subcategory"
            self.ids.sub_icon.text = ""


    def on_subcategory_changed(self, subcategory_text):

        if getattr(self, "_skip_callbacks", False):
            return

        if subcategory_text == "Click to choose subcategory":
            return

        """
        Called by KV on subcategory spinner change.
        Auto-fills Sub_Icon using the (Category, Subcategory) mapping.
        """
        cat = str(self.ids.category.text).strip()
        sub = str(subcategory_text).strip().lower()

        # ✅ first try category-specific
        sub_icon = self.sub_to_icon.get((cat, sub), "")

        # ✅ fallback to GLOBAL mapping
        if not sub_icon:
            sub_icon = self.sub_icon_global.get(sub, "")

        # ✅ fallback to category icon
        if not sub_icon:
            sub_icon = self.ids.cat_icon.text

        self.ids.sub_icon.text = sub_icon


    def cancel_edit(self):
        self.edit_mode = False

        # reset fields
        self.ids.category.text = "Click to choose category"
        self.ids.subcategory.text = "Click to choose subcategory"
        self.ids.title.text = ""
        self.ids.description.text = ""
        self.ids.urls.text = ""
        self.ids.cat_icon.text = ""
        self.ids.sub_icon.text = ""
        self.ids.topic_icon.text = ""
        self.ids.icon_path.text = ""

        self.pending_steps = []
        self.refresh_steps_preview()

        # go back
        App.get_running_app().sm.current = "menu"

    # -----------------------------
    # ICON PICKER
    # -----------------------------
    def pick_icon(self):
        # You already use a file picker pattern elsewhere; simplest: keep text path entry.
        # If you want a FileChooser popup later, we can add it – for now this won't crash.
        #self.ids.status_label.text = "Tip: paste an icon path into 'icon_path' then Save."

        layout = BoxLayout(orientation="vertical")

        filechooser = FileChooserListView(
            path=str(Path.home()),
            filters=["*.png", "*.jpg", "*.jpeg"]
        )

        def select_file(instance):
            if filechooser.selection:
                selected = filechooser.selection[0]
                self.ids.icon_path.text = selected

                # ✅ update header icon immediately
                from kivy.app import App
                try:
                    filename = Path(selected).name
                    # ✅ preview direct file (correct)
                    self.ids.header_icon.source = selected
                    # ✅ keep UI consistent
                    self.ids.topic_icon.text = Path(selected).name

                except Exception as e:
                    print("DEBUG: preview icon failed:", e)

            popup.dismiss()

        btn = Button(text="Select", size_hint_y=None, height=50)
        btn.bind(on_release=select_file)

        layout.add_widget(filechooser)
        layout.add_widget(btn)

        popup = Popup(title="Select Icon", content=layout, size_hint=(0.9, 0.9))
        popup.open()


    def on_topic_icon_change(self, value):
        if "header_icon" not in self.ids:
            return

        from kivy.app import App
        icon_path = App.get_running_app().get_icon_path(value)

        if value and os.path.exists(icon_path):
            self.ids.header_icon.source = icon_path
        else:
            # ✅ fallback icon
            self.ids.header_icon.source = App.get_running_app().get_icon_path("howtolinux-icon.png")

    # -----------------------------
    # STEPS (local buffer)
    # -----------------------------
    def add_step_local(self):
        try:
            step_order = int(self.ids.step_order.text.strip())
        except Exception:
            self.ids.status_label.text = "Step_Order must be an integer (e.g. 1, 2, 3)."
            return

        instruction = self.ids.step_instruction.text.strip()
        if not instruction:
            self.ids.status_label.text = "Instruction is required."
            return

        # Build step dict
        step = {
            "Step_Order": step_order,
            "Headline": self.ids.step_headline.text.strip(),
            "Header_2": self.ids.step_header2.text.strip(),
            "Instruction": instruction,
            "Code_Snippet": self.ids.step_code.text.strip(),
            "Notes": self.ids.step_notes.text.strip(),
        }

        # ✅ If a step is selected → overwrite that slot
        if self.selected_step_index != -1 and 0 <= self.selected_step_index < len(self.pending_steps):
            self.pending_steps[self.selected_step_index] = step
            self.selected_step_index = -1
            if "add_step_btn" in self.ids:
                self.ids.add_step_btn.text = "Add Step"
        else:
            # fallback: replace any existing step with same order
            self.pending_steps = [s for s in self.pending_steps if int(s.get("Step_Order", 9999)) != step_order]
            self.pending_steps.append(step)

        # reorder + renumber
        self.pending_steps.sort(key=lambda s: int(s.get("Step_Order", 9999)))
        self.renumber_steps()

        self.clear_step_form()
        self.refresh_steps_preview()
        self.refresh_steps_list()
        self.ids.form_scroll.scroll_y = 0.3

        self.ids.status_label.text = f"Step saved."


    def remove_last_step(self):
        if self.pending_steps:
            self.pending_steps = self.pending_steps[:-1]
            self.renumber_steps()
            self.refresh_steps_preview()
            self.refresh_steps_list()
            self.ids.status_label.text = "Last step removed."

    def clear_step_form(self):
        self.ids.step_order.text = ""
        self.ids.step_headline.text = ""
        self.ids.step_header2.text = ""
        self.ids.step_instruction.text = ""
        self.ids.step_code.text = ""
        self.ids.step_notes.text = ""

        # ✅ 🔥 RESET selection highlight
        self.selected_step_index = -1
        self.refresh_steps_list()

        # ✅ reset button text
        if "add_step_btn" in self.ids:
            self.ids.add_step_btn.text = "Add Step"

    def refresh_steps_preview(self):
        # Only update if you still have a steps_preview label in KV
        if "steps_preview" not in self.ids:
            return

        if not self.pending_steps:
            self.ids.steps_preview.text = "No steps added yet."
            return

        lines = []
        for s in self.pending_steps:
            order = s.get("Step_Order", "?")
            title = s.get("Headline") or s.get("Header_2") or "(no headline)"
            lines.append(f"{order}. {title}")
        self.ids.steps_preview.text = "\n".join(lines)


    def _clean_step_title(self, title: str) -> str:
        """Remove leading numbering like '3.' or '3)' from stored titles."""
        if not title:
            return "(no headline)"
        return re.sub(r'^\s*\d+[\.\)\:\-]\s*', '', str(title).strip())

    def refresh_steps_list(self):
        if "steps_container" not in self.ids:
            return

        container = self.ids.steps_container
        container.clear_widgets()

        if not self.pending_steps:
            container.add_widget(Label(
                text="No steps added yet.",
                size_hint_y=None,
                height=dp(30),
                color=[0.3, 0.3, 0.3, 1]
            ))
            return

        app = App.get_running_app()

        for idx, s in enumerate(self.pending_steps):
            order = int(s.get("Step_Order", idx + 1))
            title_raw = s.get("Headline") or s.get("Header_2") or ""
            title = self._clean_step_title(title_raw)

            row = HoverRow()
            row.selected = (idx == self.selected_step_index)

            # LEFT: TEXT (flexible width)
            lbl = Label(
                text=f"{order}. {title}",
                size_hint_x=1,          # ✅ takes remaining space
                halign="left",
                valign="middle",
                color=[0.1, 0.25, 0.45, 1]   # ✅ dark reada
            )
            lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            row.add_widget(lbl)

            # RIGHT: BUTTON GROUP (fixed width!)
            btn_box = BoxLayout(
                orientation="horizontal",
                size_hint_x=None,
                width=dp(160),          # ✅ FIXED SPACE for buttons
                spacing=dp(4)
            )

            # EDIT

            btn_edit = Button(
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                background_normal=app.get_icon_path("edit.png"),
                background_down=app.get_icon_path("edit.png"),
                background_color=[1, 1, 1, 1],
                border=(0, 0, 0, 0),
                text=""
            )

            btn_edit.bind(on_release=lambda _b, i=idx: self.load_step_into_form(i))
            btn_box.add_widget(btn_edit)

            # DELETE
            btn_del = Button(
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                background_normal=app.get_icon_path("delete.png"),
                background_down=app.get_icon_path("delete.png"),
                background_color=[1, 1, 1, 1],
                border=(0, 0, 0, 0),
                text=""
            )
            btn_del.bind(on_release=lambda _b, i=idx: self.delete_step(i))
            btn_box.add_widget(btn_del)


            # UP
            btn_up = Button(
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                background_normal=app.get_icon_path("up.png"),
                background_down=app.get_icon_path("up.png"),
                background_color=[1, 1, 1, 1],
                border=(0, 0, 0, 0),
                text=""
            )
            btn_up.bind(on_release=lambda _b, i=idx: self.move_step(i, -1))
            btn_box.add_widget(btn_up)

            # DOWN
            btn_down = Button(
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                background_normal=app.get_icon_path("down.png"),
                background_down=app.get_icon_path("down.png"),
                background_color=[1, 1, 1, 1],
                border=(0, 0, 0, 0),
                text=""
            )
            btn_down.bind(on_release=lambda _b, i=idx: self.move_step(i, +1))
            btn_box.add_widget(btn_down)

            row.add_widget(btn_box)
            container.add_widget(row)


    def load_step_into_form(self, idx):
        """Load a pending step into the step form for editing."""
        if idx < 0 or idx >= len(self.pending_steps):
            return

        s = self.pending_steps[idx]
        self.selected_step_index = idx
        self.refresh_steps_list()

        self.ids.step_order.text = str(s.get("Step_Order", ""))
        self.ids.step_headline.text = s.get("Headline", "") or ""
        self.ids.step_header2.text = s.get("Header_2", "") or ""
        self.ids.step_instruction.text = s.get("Instruction", "") or ""
        self.ids.step_code.text = s.get("Code_Snippet", "") or ""
        self.ids.step_notes.text = s.get("Notes", "") or ""

        # visual cue: turn Add Step button into Update
        if "add_step_btn" in self.ids:
            self.ids.add_step_btn.text = "Update Step"

    def renumber_steps(self):
        """Force Step_Order to be 1..n in the current order."""
        for i, s in enumerate(self.pending_steps):
            s["Step_Order"] = i + 1

        self.refresh_steps_preview()
        self.refresh_steps_list()

    def delete_step(self, idx):
        if idx < 0 or idx >= len(self.pending_steps):
            return
        self.pending_steps.pop(idx)
        self.selected_step_index = -1
        if "add_step_btn" in self.ids:
            self.ids.add_step_btn.text = "Add Step"
        self.renumber_steps()
        self.refresh_steps_preview()
        self.refresh_steps_list()

    def move_step(self, idx, direction):
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.pending_steps):
            return

        self.pending_steps[idx], self.pending_steps[new_idx] = self.pending_steps[new_idx], self.pending_steps[idx]
        self.renumber_steps()
        self.refresh_steps_preview()
        self.refresh_steps_list()


    # -----------------------------
    # SAVE TOPIC + ALL STEPS TO FIREBASE
    # -----------------------------
    def save_topic(self):
        if not is_admin_enabled():
            self.ids.status_label.text = "Editor disabled (admin key missing)."
            return

        # Copy icon if a file path is provided
        icon_filename = self.ids.topic_icon.text.strip()
        icon_path = self.ids.icon_path.text.strip()
        if icon_path:
            try:
                icon_filename = copy_icon_to_assets(icon_path)
                # ✅ sync UI with saved filename
                self.ids.topic_icon.text = icon_filename

                # ✅ update header icon after saving
                if "header_icon" in self.ids:
                    from kivy.app import App
                    try:
                        self.ids.header_icon.source = App.get_running_app().get_icon_path(icon_filename)
                    except Exception as e:
                        print("DEBUG: header icon update failed:", e)

            except Exception as e:
                self.ids.status_label.text = f"Icon copy failed: {e}"
                return


        # ✅ 1. Build topic dict FIRST
        topic = {
            "Category": self.ids.category.text.strip(),
            "Subcategory": self.ids.subcategory.text.strip(),
            "Title": self.ids.title.text.strip(),
            "Description": self.ids.description.text.strip(),
            "URLs": self.ids.urls.text.strip(),
            "Cat_Icon": self.ids.cat_icon.text.strip(),
            "Sub_Icon": self.ids.sub_icon.text.strip(),
            "Topic_Icon": icon_filename,
        }

        # ✅ 2. Optional user-provided Topic_ID
        if "topic_id" in self.ids:
            user_id = self.ids.topic_id.text.strip()
            if self.edit_mode and user_id:
                topic["Topic_ID"] = user_id

        if not topic["Category"] or not topic["Title"]:
            self.ids.status_label.text = "Category and Title are required."
            return

        try:
            if self.edit_mode:
                # ✅ keep Firebase key (VERY IMPORTANT)
                topic["_key"] = self.edit_topic_key

                # ✅ keep Topic_ID or updated one
                topic["Topic_ID"] = self.edit_topic_id

                topic_key, topic_id = add_topic_to_firebase(topic, overwrite=True)

            else:
                topic_key, topic_id = add_topic_to_firebase(topic)

            # ✅ FORCE STRING ID (important)
            topic_id = str(topic_id)

            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id

            # ✅ update header icon after save
            if "header_icon" in self.ids:
                from kivy.app import App

                icon_file = self.ids.topic_icon.text.strip()

                if icon_file:
                    try:
                        self.ids.header_icon.source = App.get_running_app().get_icon_path(icon_file)
                    except Exception as e:
                        print("DEBUG: header icon update failed:", e)
                else:
                    self.ids.header_icon.source = App.get_running_app().get_icon_path("howtolinux-icon.png")

            # ✅ Delete old steps (FIXED TYPE)
            from src.editor import delete_steps_for_topic
            delete_steps_for_topic(topic_id)

            # ✅ Save steps
            for s in self.pending_steps:
                payload = dict(s)
                payload["Topic_ID"] = topic_id
                add_step_to_firebase(payload)

            # ✅ refresh + export backup (FIXED)

            #if not self.edit_mode:
            #    self.reset_form_only()

            # ✅ Keep topic fields so user can continue editing after save
            # Only clear the step entry inputs (not the topic data)
            self.clear_step_form()

            app = App.get_running_app()

            # reload data from Firebase
            app.fetch_database()
            # fetch_database is async -> repopulate menu shortly after
            Clock.schedule_once(lambda dt: app.root.get_screen("menu").populate_menu(), 0.5)

            # ✅ refresh visible UI (IMPORTANT)
            try:
                app.root.get_screen("menu").populate_categories()
            except Exception as e:
                print("UI refresh error:", e)

            # ✅ FIXED EXPORT (no crash anymore)

            from src.main import APP_DATA
            export_backup_excel(APP_DATA.copy())

            # Reset UI
            #self.pending_steps = []
            self.refresh_steps_preview()
            self.clear_step_form()


            # THEN set ID again
            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id


            self.ids.status_label.text = f"✅ Saved topic + steps (Topic_ID: {str(topic_id)[:8]}…)"

            # ✅ ensure Topic_ID stays visible
            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id

            # ✅ mark screen as edit mode after first save
            self.edit_mode = True
            self.edit_topic_id = topic_id
            self.edit_topic_key = topic_key  # returned from add_topic_to_firebase

        except Exception as e:
            self.ids.status_label.text = f"❌ Save failed: {e}"

    def on_kv_post(self, base_widget):
        from kivy.uix.textinput import TextInput

        for widget in self.walk():
            if isinstance(widget, TextInput) and not widget.readonly:
                widget.bind(focus=self._handle_focus)

    def _handle_focus(self, instance, value):

        # ✅ DO NOT disable scrolling anymore
        pass
    def reset_form_only(self):
        self.edit_mode = False
        self.edit_topic_id = ""
        self.selected_step_index = -1
        self.pending_steps = []

        self.ids.category.text = "Select Category"
        self.ids.subcategory.text = "Click to choose subcategory"
        self.ids.subcategory.values = []

        self.ids.title.text = ""
        self.ids.description.text = ""
        self.ids.urls.text = ""
        self.ids.cat_icon.text = ""
        self.ids.sub_icon.text = ""
        self.ids.topic_icon.text = ""
        self.ids.icon_path.text = ""

        self.refresh_steps_list()

    def _restore_edit_values(self):
        if not self.edit_mode:
            return

        cat = getattr(self, "_edit_category", "")
        sub = getattr(self, "_edit_subcategory", "")

        if not cat:
            print("ERROR: no stored category")
            return

        # set category safely
        self._skip_callbacks = True
        self.ids.category.text = cat
        self._skip_callbacks = False

        # build sub list
        self.on_category_changed(cat)

        def _set_sub(_dt):
            if sub:
                self.ids.subcategory.text = sub
                self.on_subcategory_changed(sub)

        Clock.schedule_once(_set_sub, 0.05)


#-----------------------

class AddStepScreen(Screen):
    """
    Admin-only screen: add a Step tied to a Topic_ID.
    """
    topic_map = {}   # display_text -> topic_id

    def on_pre_enter(self):
        if not is_admin_enabled():
            self.ids.status_label.text = "Editor disabled (admin key missing)."
            self.ids.save_btn.disabled = True
            self.ids.add_step_btn.disabled = True
        else:
            self.ids.status_label.text = ""
            self.ids.save_btn.disabled = False
            self.ids.add_step_btn.disabled = False

        # ✅ ALWAYS reset when NOT editing
        if not self.edit_mode:
            if "topic_id" in self.ids:
                self.ids.topic_id.text = ""

            self.reset_form()

        self.refresh_steps_preview()
        self.refresh_steps_list()
        self._schedule_populate_dropdowns()

        def reset_form(self):
            self.ids.category.text = "Select Category"
            self.ids.subcategory.text = "Select Subcategory"

            self.ids.title.text = ""
            self.ids.description.text = ""
            self.ids.urls.text = ""

            self.ids.cat_icon.text = ""
            self.ids.sub_icon.text = ""
            self.ids.topic_icon.text = ""
            self.ids.icon_path.text = ""

            self.pending_steps = []
            self.selected_step_index = -1

    def populate_topics(self):
        global APP_DATA
        topics = APP_DATA.get("topics", []) if isinstance(APP_DATA, dict) else []

        values = []
        self.topic_map = {}

        for t in topics:
            if not isinstance(t, dict):
                continue
            topic_id = t.get("Topic_ID")
            title = str(t.get("Title", "")).strip()
            cat = str(t.get("Category", "")).strip()

            if not topic_id or not title:
                continue

            # display string: Category — Title (short id)
            display = f"{cat} — {title} ({str(topic_id)[:8]})"
            values.append(display)
            self.topic_map[display] = topic_id

        values.sort()

        # update spinner
        self.ids.topic_spinner.values = values
        if values:
            self.ids.topic_spinner.text = values[0]
        else:
            self.ids.topic_spinner.text = "No topics available"

    def save_step(self):
        if not is_admin_enabled():
            self.ids.step_status.text = "Editor disabled (admin key missing)."
            return

        chosen = self.ids.topic_spinner.text
        topic_id = self.topic_map.get(chosen)

        if not topic_id:
            self.ids.step_status.text = "Please select a valid topic."
            return

        # Validate Step_Order
        try:
            step_order = int(self.ids.step_order.text.strip())
        except Exception:
            self.ids.step_status.text = "Step_Order must be an integer (e.g. 1, 2, 3)."
            return

        step = {
            "Topic_ID": topic_id,
            "Step_Order": step_order,
            "Headline": self.ids.step_headline.text.strip(),
            "Header_2": self.ids.step_header2.text.strip(),
            "Instruction": self.ids.step_instruction.text.strip(),
            "Code_Snippet": self.ids.step_code.text.strip(),
            "Notes": self.ids.step_notes.text.strip(),
        }

        # Basic validation
        if not step["Instruction"]:
            self.ids.step_status.text = "Instruction is required."
            return

        try:
            key = add_step_to_firebase(step)
            self.ids.step_status.text = f"Saved step to Firebase (key: {key})"

            # Refresh data in the background
            app = App.get_running_app()
            app.fetch_database()

            # Backup export (optional, but matches your 'Excel is backup' goal)
            ##export_backup_excel(globals().get("APP_DATA", {}))

            # Clear fields except topic + step order
            self.ids.step_headline.text = ""
            self.ids.step_header2.text = ""
            self.ids.step_instruction.text = ""
            self.ids.step_code.text = ""
            self.ids.step_notes.text = ""

        except Exception as e:
            self.ids.step_status.text = f"Save failed: {e}"

#-------------------------

class AppInfoScreen(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()

        # ✅ fetch fresh data
        app.fetch_database()

        # ✅ load after short delay
        Clock.schedule_once(lambda dt: self._load_after_fetch(app), 0.3)


    def _load_after_fetch(self, app):
        meta = app.metadata

        print("DEBUG metadata in AppInfo:", meta)

        self.ids.app_name.text = meta.get("app_name", "")
        self.ids.version.text = meta.get("version", "")
        self.ids.last_update.text = meta.get("last update", "")
        self.ids.developer.text = meta.get("developer", "")
        self.ids.description.text = meta.get("description", "")
        self.ids.changelog.text = meta.get("changelog", "")

    def save_metadata(self):
        from src.editor import save_metadata_to_firebase

        metadata = {
            "app_name": self.ids.app_name.text.strip(),
            "version": self.ids.version.text.strip(),
            "last update": self.ids.last_update.text.strip(),
            "developer": self.ids.developer.text.strip(),
            "description": self.ids.description.text.strip(),
            "changelog": self.ids.changelog.text.strip(),
        }

        try:
            save_metadata_to_firebase(metadata)

            # refresh UI
            app = App.get_running_app()
            app.fetch_database()
            Clock.schedule_once(lambda dt: self.on_pre_enter(), 0.5)

            self.ids.status_label.text = "✅ Metadata saved"

        except Exception as e:
            self.ids.status_label.text = f"❌ Save failed: {e}"

#----------

if __name__ == '__main__':
    LinuxHowToApp().run()
