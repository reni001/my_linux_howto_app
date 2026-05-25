
# --- Standard library ---
import requests
import os
import platform
import webbrowser
import subprocess
import sys
import traceback
from threading import Thread
from pathlib import Path

# --- Project imports ---
from src.utils.first_run import initialize_first_run
from src.utils.config import load_firebase_config
from src.utils.runtime_paths import is_dev_mode, get_runtime_paths
from src.services.update_content import update_assets, update_excel
from src.services.editor_service import is_admin_enabled
from src.screens.add_topic_screen import AddTopicScreen
from src.screens.menu_screen import MenuScreen
from src.screens.search_screen import SearchScreen
from src.screens.detail_screen import DetailScreen
from src.screens.article_screen import ArticleScreen
from src.screens.add_step_screen import AddStepScreen
from src.screens.app_info_screen import AppInfoScreen
from src.utils.icon_utils import get_icon_path
from src.ui.theme import (
    COLOR_TRANSPARENT,
    COLOR_WHITE_SOFT,
    COLOR_WHITE,
    COLOR_BLUE,
    COLOR_BLUE_MEDIUM,
    COLOR_BLUE_LIGHT,
    COLOR_ORANGE,
    COLOR_ORANGE_SOFT,
    COLOR_BG_DARK,
    COLOR_GREY,
    COLOR_GREY_SOFT,
    COLOR_GREY_DARK,
    COLOR_GREY_HOVER,
    COLOR_PANEL,
    COLOR_TEXT_LIGHT,
    COLOR_TEXT_DARK,
    COLOR_TEXT_SOFT,
    COLOR_RED,
    COLOR_GREEN,
    COLOR_CYAN,
    COLOR_CYAN,
    COLOR_BLUE_DARK_UI,
    COLOR_GREEN_DARK_UI,
    COLOR_ORANGE_DARK_UI,
    COLOR_GREY_DARK,
    COLOR_GREY_LIGHT,
    COLOR_CYAN_DARK,
    COLOR_RED_DARK
)


# --- Kivy ---
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Line



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



# --- CLASSES ---

class AppMenu(ModalView):
    pass

# --- MAIN APP CLASS ---

class LinuxHowToApp(App):

# --- Core ---
    COLOR_TRANSPARENT = COLOR_TRANSPARENT
    COLOR_WHITE = COLOR_WHITE
    COLOR_WHITE_SOFT = COLOR_WHITE_SOFT

    # --- Primary colours ---
    COLOR_BLUE = COLOR_BLUE
    COLOR_BLUE_MEDIUM = COLOR_BLUE_MEDIUM
    COLOR_BLUE_LIGHT = COLOR_BLUE_LIGHT
    COLOR_BLUE_DARK_UI = COLOR_BLUE_DARK_UI

    COLOR_ORANGE = COLOR_ORANGE
    COLOR_ORANGE_SOFT = COLOR_ORANGE_SOFT
    COLOR_ORANGE_DARK_UI = COLOR_ORANGE_DARK_UI

    COLOR_CYAN = COLOR_CYAN
    COLOR_CYAN_DARK = COLOR_CYAN_DARK

    # --- Status colours ---
    COLOR_GREEN = COLOR_GREEN
    COLOR_GREEN_DARK_UI = COLOR_GREEN_DARK_UI

    COLOR_RED = COLOR_RED
    COLOR_RED_DARK = COLOR_RED_DARK

    # --- Background / layout ---
    COLOR_BG_DARK = COLOR_BG_DARK
    COLOR_PANEL = COLOR_PANEL

    COLOR_GREY = COLOR_GREY
    COLOR_GREY_SOFT = COLOR_GREY_SOFT
    COLOR_GREY_HOVER = COLOR_GREY_HOVER
    COLOR_GREY_DARK = COLOR_GREY_DARK
    COLOR_GREY_LIGHT = COLOR_GREY_LIGHT

    # --- Text ---
    COLOR_TEXT_LIGHT = COLOR_TEXT_LIGHT
    COLOR_TEXT_DARK = COLOR_TEXT_DARK
    COLOR_TEXT_SOFT = COLOR_TEXT_SOFT



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
        from src.utils.runtime_paths import get_runtime_paths
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
                    raw_topics = APP_DATA.get("topics")
                    if isinstance(raw_topics, dict):
                        APP_DATA["topics"] = [
                            {"_key": str(k), **v}
                            for k, v in raw_topics.items()
                            if isinstance(v, dict)
                        ]
                    elif isinstance(raw_topics, list):
                        # If someone stored topics as a list, create _key from index (stable for overwrite)
                        new_topics = []
                        for idx, v in enumerate(raw_topics):
                            if isinstance(v, dict):
                                v = dict(v)
                                v.setdefault("_key", str(idx))
                                new_topics.append(v)
                        APP_DATA["topics"] = new_topics
                    else:
                        APP_DATA["topics"] = []

                    raw_steps = APP_DATA.get("steps")
                    if isinstance(raw_steps, dict):
                        APP_DATA["steps"] = [
                            {"_key": str(k), **v}
                            for k, v in raw_steps.items()
                            if isinstance(v, dict)
                        ]
                    elif isinstance(raw_steps, list):
                        new_steps = []
                        for idx, v in enumerate(raw_steps):
                            if isinstance(v, dict):
                                v = dict(v)
                                v.setdefault("_key", str(idx))
                                new_steps.append(v)
                        APP_DATA["steps"] = new_steps
                    else:
                        APP_DATA["steps"] = []

                    # metadata: keep dict
                    if isinstance(APP_DATA.get("metadata"), list):
                        APP_DATA["metadata"] = APP_DATA["metadata"][0] if APP_DATA["metadata"] else {}

                    print("DEBUG first topic keys:", list((APP_DATA.get("topics") or [{}])[0].keys()))

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
        self.APP_DATA = APP_DATA
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

        # ✅ AUTO-RECOVER missing _key
        if "_key" not in data:
            print("⚠️ Missing _key — recovering from APP_DATA")

            for t in self.APP_DATA.get("topics", []):
                if t.get("Topic_ID") == data.get("Topic_ID"):
                    data["_key"] = t.get("_key")
                    break

        screen = self.sm.get_screen("add_topic")
        screen.load_topic_for_edit(data)
        self.sm.current = "add_topic"


    def delete_topic(self, data):
        from src.services.editor_service import delete_topic_from_firebase


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
        self.update_bg = self.COLOR_WHITE_SOFT   # soft highlight
        self.update_fg = self.COLOR_GREEN        # text
        self.update_border = self.COLOR_GREEN    # border
        self.metadata = load_app_metadata()
        self.refresh_ui_data()

        Clock.schedule_once(self.restore_update_button, 2)


    def update_failed(self, *args):
        self.update_text = "Update failed ✗"
        self.update_bg = self.COLOR_WHITE_SOFT
        self.update_fg = self.COLOR_RE
        self.update_border = self.COLOR_RED       # ✅ red border
        self.metadata = load_app_metadata()
        self.refresh_ui_data()

        Clock.schedule_once(self.restore_update_button, 3)


    def restore_update_button(self, *args):
        self.update_text = "Update App & Icons"
        self.update_bg = self.COLOR_ORANGE
        self.update_fg = self.COLOR_TEXT_DARK
        self.update_border = self.COLOR_TRANSPARENT           # ✅ reset


    #---- syncronize button behaviour -----

    def sync_success(self, *args):
        self.sync_text = "Sync successful ✓"
        self.sync_bg = self.COLOR_WHITE_SOFT
        self.sync_fg = self.COLOR_GREEN
        self.sync_border = self.COLOR_GREEN
        self.metadata = load_app_metadata()
        self.refresh_ui_data()


        Clock.schedule_once(self.restore_sync_button, 3)


    def sync_failed(self, *args):
        self.sync_text = "Sync failed ✗"
        self.sync_bg = self.COLOR_WHITE_SOFT
        self.sync_fg = self.COLOR_RED
        self.sync_border = self.COLOR_RED


        Clock.schedule_once(self.restore_sync_button, 3)

    def restore_sync_button(self, *args):
        self.sync_text = "Developer Sync (Firebase & Git)"
        self.sync_bg = self.COLOR_ORANGE
        self.sync_fg = self.COLOR_TEXT_DARK
        self.sync_border = self.COLOR_TRANSPARENT


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
            Color(*COLOR_BG_DARK)  # darker blue
            root_layout.bg = RoundedRectangle(pos=root_layout.pos, size=root_layout.size, radius=[RADIUS])

        with root_layout.canvas.after:
            Color(*COLOR_ORANGE)  # orange
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
            color=self.COLOR_WHITE,
            size_hint_y=None,
            height=35
        ))

        text_block.add_widget(Label(
            text=f"Version {version}",
            halign="left",
            color=self.COLOR_TEXT_LIGHT,
            size_hint_y=None,
            height=25
        ))

        text_block.add_widget(Label(
            text=f"Last update: {last_update}",
            halign="left",
            color=self.COLOR_TEXT_LIGHT,
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
            Color(*self.COLOR_ORANGE_SOFT)   # ✅ very subtle light line
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
            color=self.COLOR_TEXT_LIGHT
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
            color=self.COLOR_WHITE
        )
        title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        scroll_content.add_widget(title_label)

        changelog_label = Label(
            text=change,
            size_hint_y=None,
            halign='left',
            valign='top',
            color=self.COLOR_TEXT_LIGHT
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
            color=self.COLOR_WHITE,
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
            background_color=self.COLOR_WHITE,
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

        # ✅ THEN set mode
        screen.edit_mode = False
        screen.edit_topic_id = ""

        # ✅ TEMPORARILY disable callbacks
        screen._skip_callbacks = True

        # ✅ THEN reset form safely
        screen.cancel_edit()

        # ✅ re-enable callbacks AFTER UI update
        Clock.schedule_once(
            lambda dt: setattr(screen, "_skip_callbacks", False), 0.1
        )

        self.sm.current = "add_topic"


class ClickableHeader(ButtonBehavior, BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(50)
        self.padding = [dp(10), dp(5)]
        self.spacing = dp(10)



if __name__ == '__main__':
    LinuxHowToApp().run()
