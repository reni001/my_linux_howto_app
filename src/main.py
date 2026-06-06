
# --- Standard library ---
import requests
import os
import platform
import webbrowser
import subprocess
import sys
import traceback
import shutil
from threading import Thread
from pathlib import Path

# --- Project imports ---
from src.utils.first_run import initialize_first_run
from src.utils.runtime_paths import is_dev_mode, get_runtime_paths
from src.utils.icon_utils import get_icon_path
from src.services.update_content import update_assets, update_cache
from src.services.editor_service import is_admin_enabled
from src.screens.add_topic_screen import AddTopicScreen
from src.screens.menu_screen import MenuScreen
from src.screens.search_screen import SearchScreen
from src.screens.detail_screen import DetailScreen
from src.screens.article_screen import ArticleScreen
from src.screens.add_step_screen import AddStepScreen
from src.screens.json_viewer_screen import JsonViewerScreen
from src.screens.app_info_screen import AppInfoScreen
from src.ui.about_popup import show_about_popup
from src.ui.styled_popup import create_popup_container


from src.services.data_service import (
    fetch_database,
    load_app_metadata,
    APP_DATA,
    add_local_topic_and_steps,
    update_local_topic_and_steps,
    delete_local_topic
)
from src.ui.theme import (
    COLOR_TRANSPARENT,
    COLOR_WHITE_SOFT,
    COLOR_WHITE,
    COLOR_BLUE,
    COLOR_BLUE_MEDIUM,
    COLOR_BLUE_LIGHT,
    COLOR_BLUE_DARK,
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
    COLOR_RED_DARK,
    COLOR_ORANGE_LIGHT_UI,
    COLOR_PURPLE,
    COLOR_PURPLE_DARK
)

# --- Kivy ---
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
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
def setup_window(*args):

    # ✅ get real screen size AFTER window is ready
    screen_w, screen_h = Window.system_size

    # ✅ use most of height
    HEIGHT = int(screen_h * 0.9)

    # ✅ phone ratio (9:16)
    WIDTH = int(HEIGHT * 9 / 16)

    Window.size = (WIDTH, HEIGHT)

    # ✅ center window
    Window.left = int((screen_w - WIDTH) / 2)
    Window.top = int((screen_h - HEIGHT) / 2)

# ✅ IMPORTANT: run AFTER window is created

# ✅ Only apply on desktop
if platform.system() != "Linux" or "ANDROID_ARGUMENT" not in os.environ:
    Window.size = (650, 1200
                   )
    Window.minimum_width = 480
    Window.minimum_height = 850
    Window.resizable = True

# ✅ ensure runtime dirs & config exist
initialize_first_run()
#Clock.schedule_once(lambda dt: initialize_first_run(), 1)

# --- UI DEFINITIONS (KV) ---
# The KV layout was moved from the inlined KV string to an external file.
# This is a lossless move: main.kv contains the exact same KV content as before.
KV = None  # KV now lives in main.kv
#KV_FILE = os.path.join(SRC_DIR, "main.kv")
KV_FILE = str(Path(__file__).parent / "main.kv")
if KV_FILE not in Builder.files:
    Builder.load_file(KV_FILE)


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
    COLOR_ORANGE_LIGHT_UI = COLOR_ORANGE_LIGHT_UI

    COLOR_CYAN = COLOR_CYAN
    COLOR_CYAN_DARK = COLOR_CYAN_DARK


    COLOR_PURPLE = COLOR_PURPLE
    COLOR_PURPLE_DARK = COLOR_PURPLE_DARK


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
    COLOR_BLUE_DARK = COLOR_BLUE_DARK

    version_string = StringProperty("v0.0.0")
    connection_status = StringProperty("Checking...")

    project_root = StringProperty("")

    # --- Typography scale ---   _CATEGORY = NumericProperty(26)
    FONT_SUBCATEGORY = NumericProperty(20)
    FONT_TITLE = NumericProperty(22)
    FONT_TEXT = NumericProperty(17)
    FONT_MENU_TITLE = NumericProperty(20)
    FONT_MENU_STATUS = NumericProperty(17)
    FONT_BUTTON = NumericProperty(20)
    FONT_CODE = NumericProperty(18)

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

    #----------helpers-----------
    def _get_protected_icons(self):
        """
        Icons that must NEVER be deleted (UI / fallback / system icons)
        """
        return {
            "howtolinux-icon.png",   # ✅ default fallback
            "howtolinux-256_256.png",
            "arrow_back.png",
            "cancel.png",
            "default.png",
            "delete.png",
            "down.png",
            "down_arrow.png",
            "download.png",
            "edit.png",
            "feature.png",
            "fix.png",
            "improvement.png",
            "link2.png",
            "local.png",
            "menu.png",
            "note.png",
            "screenformate.png",
            "status_green.png",
            "status_grey.png",
            "search.png",
            "tips_category.png",
            "top.png",
            "up.png",
            "upload.png",
            "version.png"

            # ✅ add more if needed later
        }

    def _get_protected_screenshots(self):
        """
        Screenshots that must NEVER be deleted
        """
        return {
            "start.png",
            "menu.png",
            "detailscreen.png",
            "articlescreen.png"
            # ✅ add more if needed
        }

    def update_typography_scale(self, *args):
        """
        Scale fonts based on current window width.
        Baseline: desktop layout around 900 px wide = 1.0 scale
        Clamped so phone remains readable and desktop doesn't grow too much.
        """
        base_width = 900.0
        scale = Window.width / base_width

        # clamp so fonts don't get too tiny or too huge
        scale = max(0.90, min(scale, 1.25))

        self.FONT_CATEGORY = 26 * scale
        self.FONT_SUBCATEGORY = 20 * scale
        self.FONT_TITLE = 22 * scale
        self.FONT_TEXT = 17 * scale
        self.FONT_MENU_TITLE = 20 * scale
        self.FONT_MENU_STATUS = 17 * scale #admin vs user
        self.FONT_BUTTON = 20 * scale
        self.FONT_CODE = 18 * scale


    def clean_unused_icons(self):
        """
        Scan both icon folders and remove unused icons safely.
        Respects protected icon list.
        """

        print("🧹 Starting icon cleanup...")

        paths = get_runtime_paths()
        icons_dir = paths["assets"] / "icons"
        user_dir = paths["assets"] / "user_icons"
        screens_dir = paths["assets"] / "screenshots"

        protected = self._get_protected_icons()

        # ✅ 1. Collect all used icons from topics
        used_icons = set()
        used_screenshots = set()

        for topic in self.APP_DATA.get("topics", []):
            for key in ["Topic_Icon", "Cat_Icon", "Sub_Icon"]:
                name = str(topic.get(key) or "").strip()
                if name:
                    used_icons.add(name)

        print(f"DEBUG: used icons = {used_icons}")

        # ✅ collect screenshots used in steps
        for step in self.APP_DATA.get("steps", []):
            shot = str(step.get("Screenshot") or "").strip()
            if shot:
                used_screenshots.add(shot)

        print(f"DEBUG: used screenshots = {used_screenshots}")

        deleted_icons = []
        deleted_screenshots = []


        # ✅ helper to process a folder
        def process_folder(folder, used_set, protected_set, deleted_list):

            if not folder.exists():
                return

            for file in folder.iterdir():
                if not file.is_file():
                    continue

                name = file.name

                if name in protected_set:
                    continue

                if name in used_set:
                    continue

                try:
                    file.unlink()
                    deleted_list.append(name)
                    print(f"✅ Deleted unused file: {file}")
                except Exception as e:
                    print(f"⚠️ Failed deleting {file}: {e}")

        # ✅ scan both folders
        protected_icons = self._get_protected_icons()
        protected_screens = self._get_protected_screenshots()

        # ✅ icons
        process_folder(icons_dir, used_icons, protected_icons, deleted_icons)
        process_folder(user_dir, used_icons, protected_icons, deleted_icons)

        # ✅ screenshots
        process_folder(screens_dir, used_screenshots, protected_screens, deleted_screenshots)

        print("🧹 Cleanup complete.")
        print(f"Icons removed: {len(deleted_icons)}")
        print(f"Screenshots removed: {len(deleted_screenshots)}")

        self.sync_text = f"Cleanup: {len(deleted_icons + deleted_screenshots)} removed"

        return {
            "icons": len(deleted_icons),
            "screenshots": len(deleted_screenshots)
        }


    def build_step_index(self):
        self.STEPS_BY_TOPIC = {}

        for step in self.APP_DATA.get("steps", []):
            tid = step.get("Topic_ID")
            if not tid:
                continue
            self.STEPS_BY_TOPIC.setdefault(tid, []).append(step)

        for steps in self.STEPS_BY_TOPIC.values():
            steps.sort(key=lambda x: int(x.get("Step_Order", 999)))


    def fetch_database(self):
        fetch_database(self)          # ✅ real fetch from data_service
        self.build_step_index()       # ✅ rebuild cached step index


    def refresh_data_only(self):
        fetch_database(self)          # ✅ refresh data only
        self.build_step_index()

    def confirm_clean_icons(self):

        root = create_popup_container()

        inner = BoxLayout(
            orientation="vertical",
            padding=[20, 15, 20, 20],
            spacing=15,
            size_hint=(0.95, 0.95),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        # ✅ title
        title_label = Label(
            text="[b]Cleanup Unused Icons[/b]",
            markup=True,
            font_size="18sp",
            color=self.COLOR_WHITE
        )

        message_label = Label(
            text="Clean all unused icons?",
            halign="center"
        )

        btn_box = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

        btn_yes = Button(
            text="CLEAN",
            background_normal='',
            background_color=self.COLOR_BLUE_MEDIUM,
            color=self.COLOR_WHITE
        )

        btn_cancel = Button(
            text="Cancel",
            background_normal='',
            background_color=self.COLOR_GREY_DARK,
            color=self.COLOR_WHITE
        )

        btn_box.add_widget(btn_yes)
        btn_box.add_widget(btn_cancel)

        inner.add_widget(title_label)
        inner.add_widget(message_label)
        inner.add_widget(btn_box)

        root.add_widget(inner)

        popup = Popup(
            title="",
            content=root,
            size_hint=(0.7, 0.4),
            background="",
            background_color=(0, 0, 0, 0),
            separator_height=0
        )

        def run_cleanup(instance):

            # ✅ step 1 → show "cleaning..."
            message_label.text = "Cleaning…"
            btn_yes.disabled = True
            btn_cancel.disabled = True

            def do_cleanup():
                try:
                    result = self.clean_unused_icons()

                    # ✅ step 2 → update UI AFTER cleaning
                    def update_ui(dt):

                        icons = result.get("icons", 0)
                        screenshots = result.get("screenshots", 0)

                        message_label.text = (
                            f"- Cleaning complete -\n\n"
                            f"{icons} icons deleted\n"
                            f"{screenshots} screenshots deleted"
                        )

                        # ✅ replace buttons with CLOSE
                        btn_box.clear_widgets()

                        btn_close = Button(
                            text="CLOSE",
                            background_normal='',
                            background_color=self.COLOR_BLUE_MEDIUM,
                            color=self.COLOR_WHITE
                        )

                        btn_close.bind(on_release=lambda x: popup.dismiss())
                        btn_box.add_widget(btn_close)

                    Clock.schedule_once(update_ui)

                except Exception as e:
                    def show_error(dt, err=e):   # ✅ capture error here
                        message_label.text = f"!!! Cleanup failed\n{err}"
                    Clock.schedule_once(show_error)

            # ✅ run in background thread (so UI does not freeze)
            Thread(target=do_cleanup, daemon=True).start()

        btn_yes.bind(on_release=run_cleanup)
        btn_cancel.bind(on_release=lambda x: popup.dismiss())


        popup.open()

    def _delete_user_icon_if_unused(self, icon_filename: str, removed_topic_id: str):
        """
        Delete icon from user_icons ONLY if no other topic uses it.
        """

        if not icon_filename:
            return

        if icon_filename in self._get_protected_icons():
            print(f"🛡️ Protected icon skipped: {icon_filename}")
            return


        still_used = False

        for topic in self.APP_DATA.get("topics", []):
            if str(topic.get("Topic_ID") or "") == str(removed_topic_id):
                continue

            if str(topic.get("Topic_Icon") or "") == str(icon_filename):
                still_used = True
                break

        if still_used:
            print(f"ℹ️ User icon still used elsewhere: {icon_filename}")
            return

        paths = get_runtime_paths()
        icon_path = paths["assets"] / "user_icons" / icon_filename

        try:
            if icon_path.exists():
                icon_path.unlink()
                print(f"✅ Deleted unused user icon: {icon_path}")
        except Exception as e:
            print(f"⚠️ Could not delete user icon {icon_path}: {e}")

    def check_connection(self):
        import requests
        try:
            requests.get("https://www.google.com", timeout=1)
            self.connection_status = "ONLINE"
        except:
            self.connection_status = "OFFLINE"

    def open_app_info(self):
        self.sm.current = "app_info"

    def _open_app_info_from_popup(self, popup):
        popup.dismiss()              # ✅ close popup first
        self.sm.current = "app_info" # ✅ then switch screen

    def get_icon_path(self, filename):
        return get_icon_path(filename)

    def fetch_database(self):
        fetch_database(self)          # ✅ call imported service
        self.build_step_index()       # ✅ rebuild index after data loads

    def refresh_data_only(self):
        fetch_database(self)          # ✅ lightweight data refresh
        self.build_step_index()

    def save_local_topic(self, topic: dict, steps: list[dict]):
        add_local_topic_and_steps(topic, steps)
        self.refresh_data_only()

    def update_local_topic(self, topic_id: str, topic: dict, steps: list[dict]):
        update_local_topic_and_steps(topic_id, topic, steps)
        self.refresh_data_only()

    def delete_local_topic(self, topic_id: str):
        delete_local_topic(topic_id)
        self.refresh_data_only()

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

    def on_screen_change(self, *args):
        self.check_connection()
        #self.refresh_ui_data()

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
        target_file = str(paths["data"] / "cache.json")

        if not os.path.exists(target_file):
            return

        # ✅ Android fallback → open inside app
        if platform.system() == "Linux" and "ANDROID_ARGUMENT" in os.environ:
            self.sm.current = "json_viewer"
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

    def refresh_ui_data(self):
        self.metadata = load_app_metadata()

        """Updates the version label across all application screens."""
        if not hasattr(self, 'sm'):
            Clock.schedule_once(lambda dt: self.refresh_ui_data(), 0.1)
            return

        version = self.metadata.get("version", "0.0.0")
        last_update = self.metadata.get("last update", "")

        self.version_string = f"v{version} | {last_update}"



        # Also trigger the standard menu population
        try:
            menu_screen = self.sm.get_screen('menu')

            #if not getattr(menu_screen, "_is_populated", False):
            menu_screen.ids.menu_container.clear_widgets()
            menu_screen.populate_menu()
            menu_screen._is_populated = True


            # ✅ NEW: If user is currently on DetailScreen, reload it after data refresh
            try:
                if self.sm.current == "details":
                    detail_screen = self.sm.get_screen("details")

                    # keep current search filter if present
                    q = ""
                    if "local_search" in detail_screen.ids:
                        q = detail_screen.ids.local_search.text

                    detail_screen.load_content_from_cache(q)

                    if getattr(detail_screen, "_last_query", None) != q:
                        detail_screen._last_query = q
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


                        if getattr(article_screen, "_last_topic", None) == current_id:
                            return

                        article_screen._last_topic = current_id

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
        self.sm.bind(current=self.on_screen_change)
        self.sm.add_widget(MenuScreen(name='menu'))
        self.sm.add_widget(SearchScreen(name='search'))
        self.sm.add_widget(DetailScreen(name='details'))
        self.sm.add_widget(ArticleScreen(name='article'))
        self.sm.add_widget(AddTopicScreen(name="add_topic"))
        self.sm.add_widget(AddStepScreen(name="add_step"))
        self.sm.add_widget(AppInfoScreen(name="app_info"))
        self.sm.add_widget(JsonViewerScreen(name="json_viewer"))

        Clock.schedule_once(lambda dt: self.fetch_database(), 0)
        Clock.schedule_once(lambda dt: self.refresh_ui_data(), 0.1)

        Window.bind(size=self.update_typography_scale)
        Clock.schedule_once(self.update_typography_scale, 0)

        return self.sm


    def is_admin_mode(self):
        if self.admin_override:
            return not self.admin_enabled   # ✅ flips mode
        return self.admin_enabled          # ✅ normal behaviour

    def refresh_current_screen(self):
        """
        Force full UI refresh after mode switch.
        """
        if not hasattr(self, "sm"):
            return

        try:
            current = self.sm.current
            screen = self.sm.get_screen(current)

            # ✅ refresh main data
            self.refresh_ui_data()

            # ✅ refresh specific screens
            if current == "details":
                q = ""
                if "local_search" in screen.ids:
                    q = screen.ids.local_search.text
                screen.load_content_from_cache(q)

            elif current == "search":
                q = ""
                if "search_input" in screen.ids:
                    q = screen.ids.search_input.text
                screen.filter_results(q)

            elif current == "menu":
                screen.ids.menu_container.clear_widgets()
                screen.populate_menu()

        except Exception as e:
            print(f"DEBUG: refresh_current_screen failed: {e}")

    def toggle_admin_mode(self):
        self.admin_override = not self.admin_override
        print(f"DEBUG: override = {self.admin_override}")

        # ✅ close popup
        if hasattr(self, "_menu_popup") and self._menu_popup:
            self._menu_popup.dismiss()

        # ✅ refresh UI AFTER popup closes
        Clock.schedule_once(lambda dt: self.refresh_current_screen(), 0.1)

        # ✅ reopen menu with updated state
        Clock.schedule_once(lambda dt: self.open_app_menu(), 0.2)

    def _reopen_app_menu(self):
        # close current popup - helper -
        if hasattr(self, "_menu_popup") and self._menu_popup:
            self._menu_popup.dismiss()

        # reopen fresh instance
        self.open_app_menu()

    def run_sync_script(self, *args):

        # --- UI: syncing state (IMMEDIATE) ---

        from pathlib import Path
        sync_script = str(Path(__file__).parent / "services" /"sync.py")

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
                    [sys.executable, "-m", "src.services.sync"],
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


    #--------- editing and deleting --------

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
        if data.get("source") == "user":
            topic_id = str(data.get("Topic_ID") or "")
            if not topic_id:
                return

            title = data.get("Title", "this topic")

            # ✅ Popup UI (same structure as Firebase)
            root = create_popup_container()

            inner = BoxLayout(
                orientation="vertical",
                padding=[20, 15, 20, 20],
                spacing=15,
                size_hint=(0.95, 0.95),
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            )

            inner.add_widget(Label(
                text="[b]Delete Topic[/b]",
                markup=True,
                font_size="18sp"
            ))

            inner.add_widget(Label(
                text="Are you sure you want to delete this topic?"
            ))

            btn_box = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

            btn_yes = Button(
                text="DELETE",
                background_normal='',
                background_color=self.COLOR_RED,
                color=self.COLOR_WHITE
            )

            btn_no = Button(
                text="Cancel",
                background_normal='',
                background_color=self.COLOR_GREY_DARK,
                color=self.COLOR_WHITE
            )

            btn_box.add_widget(btn_yes)
            btn_box.add_widget(btn_no)
            inner.add_widget(btn_box)

            root.add_widget(inner)

            popup = Popup(
                title="",
                content=root,
                size_hint=(0.7, 0.4),
                background="",
                background_color=(0, 0, 0, 0),
                separator_height=0
            )

            def confirm_delete(instance):
                popup.dismiss()
                try:
                    icon_name = str(data.get("Topic_Icon") or "")

                    self.delete_local_topic(topic_id)

                    # ✅ new: clean icon
                    self._delete_user_icon_if_unused(icon_name, topic_id)

                except Exception as e:
                    print(f"❌ Local delete failed: {e}")

            btn_yes.bind(on_release=confirm_delete)
            btn_no.bind(on_release=lambda x: popup.dismiss())

            popup.open()

            return

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
                Clock.schedule_once(lambda dt: self.fetch_database(), 0)
                Clock.schedule_once(lambda dt: self.refresh_ui_data(), 0.5)

            except Exception as e:
                print(f"❌ Delete failed: {e}")
        print("DEBUG deleting Topic_ID:", topic_id)

        # ✅ Popup UI
        root = create_popup_container()

        inner = BoxLayout(
            orientation="vertical",
            padding=[20, 15, 20, 20],
            spacing=15,
            size_hint=(0.95, 0.95),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        inner.add_widget(Label(
            text="[b]Delete Topic[/b]",
            markup=True,
            font_size="18sp",
            color=self.COLOR_WHITE
        ))

        inner.add_widget(Label(
            text="Are you sure you want to delete this topic?"
        ))

        btn_box = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

        btn_yes = Button(
            text="DELETE",
            background_normal='',
            background_color=self.COLOR_RED,
            color=self.COLOR_WHITE
        )

        btn_no = Button(
            text="Cancel",
            background_normal='',
            background_color=self.COLOR_GREY_DARK,
            color=self.COLOR_WHITE
        )

        btn_box.add_widget(btn_yes)
        btn_box.add_widget(btn_no)
        inner.add_widget(btn_box)

        root.add_widget(inner)

        popup = Popup(
            title="",
            content=root,
            size_hint=(0.7, 0.4),
            background="",
            background_color=(0, 0, 0, 0),
            separator_height=0
        )

        btn_yes.bind(on_release=confirm_delete)
        btn_no.bind(on_release=lambda x: popup.dismiss())

        popup.open()

    # -------- duplicate helper -------
    def _norm(self, value):
        return str(value or "").strip().lower()

    def _find_official_duplicate(self, data):
        """
        Check duplicates only against OFFICIAL topics
        (not local user topics).
        """
        wanted_cat = self._norm(data.get("Category"))
        wanted_sub = self._norm(data.get("Subcategory"))
        wanted_title = self._norm(data.get("Title"))

        for topic in self.APP_DATA.get("topics", []):
            if topic.get("source") == "user":
                continue

            if (
                self._norm(topic.get("Category")) == wanted_cat and
                self._norm(topic.get("Subcategory")) == wanted_sub and
                self._norm(topic.get("Title")) == wanted_title
            ):
                return topic

        return None

    def _copy_user_icon_to_official(self, icon_filename: str) -> str:
        """
        Copy icon from user_icons → icons ONLY if it does not already exist.
        If already present, reuse existing one.
        """

        if not icon_filename:
            return ""

        paths = get_runtime_paths()
        user_icon = paths["assets"] / "user_icons" / icon_filename
        official_dir = paths["assets"] / "icons"
        screens_dir = paths["assets"] / "screenshots"
        official_dir.mkdir(parents=True, exist_ok=True)

        official_target = official_dir / icon_filename

        # ✅ CASE 1: already exists → reuse
        if official_target.exists():
            print(f"ℹ️ Icon already exists → reusing: {official_target.name}")
            return official_target.name

        # ✅ CASE 2: user icon exists → copy
        if user_icon.exists():
            shutil.copy2(user_icon, official_target)
            print(f"✅ Icon promoted → {official_target.name}")
            return official_target.name

        # ✅ fallback (should not normally happen)
        return icon_filename

    # -------- promote topic (make it public) --------

    def _do_promote_topic(self, data):
        from src.services.firebase_service import add_topic_to_firebase, add_step_to_firebase

        print(f"🚀 Promoting topic: {data.get('Title')}")

        try:
            local_topic_id = str(data.get("Topic_ID") or "")

            # ✅ 1. Copy icon from user_icons → official icons
            icon_filename = data.get("Topic_Icon", "")
            icon_filename = self._copy_user_icon_to_official(icon_filename)

            # ✅ 2. Prepare official topic payload
            topic = dict(data)
            topic["Topic_Icon"] = icon_filename

            # remove local-only fields
            for key in ["source", "_key", "local_only"]:
                topic.pop(key, None)

            # IMPORTANT:
            # Let Firebase assign a fresh official Topic_ID instead of reusing local user_topic_X
            topic.pop("Topic_ID", None)

            # ✅ 3. Upload topic
            topic_key, new_topic_id = add_topic_to_firebase(topic)

            # ✅ 4. Upload steps
            for step in self.APP_DATA.get("steps", []):
                if str(step.get("Topic_ID")) == local_topic_id:
                    payload = dict(step)
                    for key in ["source", "_key", "local_only"]:
                        payload.pop(key, None)
                    payload["Topic_ID"] = str(new_topic_id)
                    add_step_to_firebase(payload)

            # ✅ 5. Remove local version after successful publish
            self.delete_local_topic(local_topic_id)

            # ✅ 6. remove user icon after successful promote
            original_user_icon_name = str(data.get("Topic_Icon") or "")
            if original_user_icon_name:
                paths = get_runtime_paths()
                user_icon_path = paths["assets"] / "user_icons" / original_user_icon_name

                try:
                    if user_icon_path.exists():
                        user_icon_path.unlink()
                        print(f"✅ Removed user icon after promote: {user_icon_path}")
                    else:
                        print(f"ℹ️ No user icon to remove after promote: {user_icon_path}")
                except Exception as e:
                    print(f"⚠️ Could not delete user icon after promote: {e}")

            print(f"✅ Promotion complete → official Topic_ID: {new_topic_id}")
            self.refresh_data_only()

        except Exception as e:
            print(f"❌ Promotion failed: {e}")


    def promote_topic(self, data):

        title = data.get("Title", "this topic")
        duplicate = self._find_official_duplicate(data)

        if duplicate:
            dup_title = duplicate.get("Title", "")
            dup_cat = duplicate.get("Category", "")
            dup_sub = duplicate.get("Subcategory", "")
            dup_id = duplicate.get("Topic_ID", "")

            message = (
                f"Possible duplicate detected.\n\n"
                f"Local topic:\n{title}\n\n"
                f"Existing official topic:\n"
                f"{dup_title}\n"
                f"Category: {dup_cat}\n"
                f"Subcategory: {dup_sub}\n"
                f"Topic_ID: {dup_id}\n\n"
                f"Do you want to promote it anyway?"
            )
            popup_title = "Possible Duplicate"
            confirm_text = "PROMOTE ANYWAY"
        else:
            message = f"Promote this topic to official content?\n\n{title}"
            popup_title = "Promote Topic"
            confirm_text = "PROMOTE"

        # ✅ SAME STYLE AS ABOUT POPUP
        root = create_popup_container()

        inner = BoxLayout(
            orientation="vertical",
            padding=[20, 15, 20, 20],
            spacing=15,
            size_hint=(0.95, 0.95),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        # ✅ Title
        inner.add_widget(Label(
            text=f"[b]{popup_title}[/b]",
            markup=True,
            font_size="18sp",
            color=self.COLOR_WHITE
        ))

        # ✅ Message
        inner.add_widget(Label(
            text=message,
            halign="center"
        ))

        # ✅ Buttons
        btn_box = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

        btn_yes = Button(
            text=confirm_text,
            background_normal='',
            background_color=self.COLOR_BLUE_MEDIUM,
            color=self.COLOR_WHITE
        )

        btn_no = Button(
            text="Cancel",
            background_normal='',
            background_color=self.COLOR_GREY_DARK,
            color=self.COLOR_WHITE
        )

        btn_box.add_widget(btn_yes)
        btn_box.add_widget(btn_no)
        inner.add_widget(btn_box)

        root.add_widget(inner)

        popup = Popup(
            title="",
            content=root,
            size_hint=(0.7, 0.5),
            background="",
            background_color=(0, 0, 0, 0),
            separator_height=0
        )

        def confirm_promote(instance):
            popup.dismiss()
            self._do_promote_topic(data)

        btn_yes.bind(on_release=confirm_promote)
        btn_no.bind(on_release=lambda x: popup.dismiss())

        popup.open()

    #---- demote topic (make it private) -------

    def demote_topic(self, data):
        from src.services.editor_service import delete_topic_from_firebase
        from src.utils.runtime_paths import get_runtime_paths

        if str(data.get("source") or "") == "user":
            return

        topic_id = str(data.get("Topic_ID") or "")
        topic_key = str(data.get("_key") or "")
        category = data.get("Category", "")

        if not topic_id or not topic_key:
            print("❌ Missing Topic_ID or _key")
            return

        try:
            # ✅ 1. collect steps
            steps = [
                dict(s) for s in self.APP_DATA.get("steps", [])
                if str(s.get("Topic_ID") or "") == topic_id
            ]

            # ✅ 2. copy icon to user_icons
            icon_name = str(data.get("Topic_Icon") or "")
            new_icon_name = self._copy_official_icon_to_user_icons(icon_name)

            # ✅ 3. create local topic
            local_topic = dict(data)
            local_topic["Topic_Icon"] = new_icon_name
            local_topic["source"] = "user"
            local_topic["local_only"] = True
            local_topic["_key"] = topic_id
            local_topic["Topic_ID"] = topic_id

            self.update_local_topic(topic_id, local_topic, steps)

            # ✅ 4. delete from Firebase
            delete_topic_from_firebase(topic_key, topic_id)
            icon_name = str(data.get("Topic_Icon") or "")

            # ✅ 5. delete icon if unused
            self._delete_official_icon_if_unused(icon_name, topic_id)

            # ✅ 6. refresh + restore category
            self.refresh_data_only()

            self.sm.current = "menu"

            def _restore(_dt):
                try:
                    detail = self.root.get_screen("details")
                    detail.header_title = category
                    detail.show_category(category)
                    self.root.current = "details"
                except Exception as e:
                    print("DEBUG restore failed:", e)

            Clock.schedule_once(_restore, 0.4)

            print(f"✅ Topic demoted: {topic_id}")

        except Exception as e:
            print("❌ Demotion failed:", e)

    def _copy_official_icon_to_user_icons(self, icon_filename: str) -> str:
        """
        Copy icon from assets/icons -> assets/user_icons ONLY if needed.
        Reuse existing user icon if already present.
        """
        if not icon_filename:
            return ""

        paths = get_runtime_paths()
        official_dir = paths["assets"] / "icons"
        user_dir = paths["assets"] / "user_icons"
        user_dir.mkdir(parents=True, exist_ok=True)

        src = official_dir / icon_filename
        dest = user_dir / icon_filename

        # ✅ if already present locally, reuse it
        if dest.exists():
            print(f"ℹ️ User icon already exists -> reusing: {dest.name}")
            return dest.name

        # ✅ copy only if missing
        if src.exists():
            shutil.copy2(src, dest)
            print(f"✅ Copied official icon -> user_icons: {dest.name}")
            return dest.name

        # fallback
        return icon_filename

    def _delete_official_icon_if_unused(self, icon_filename: str, removed_topic_id: str):
        """
        Delete icon from assets/icons only if no other official topic still uses it.
        """
        if not icon_filename:
            return

        if icon_filename in self._get_protected_icons():
            print(f"🛡️ Protected icon skipped: {icon_filename}")
            return


        # Check all current official topics except the one being demoted
        still_used = False
        for topic in self.APP_DATA.get("topics", []):
            if str(topic.get("Topic_ID") or "") == str(removed_topic_id):
                continue
            if str(topic.get("source") or "") == "user":
                continue
            if str(topic.get("Topic_Icon") or "") == str(icon_filename):
                still_used = True
                break

        if still_used:
            print(f"ℹ️ Official icon still used elsewhere: {icon_filename}")
            return

        paths = get_runtime_paths()
        icon_path = paths["assets"] / "icons" / icon_filename

        try:
            if icon_path.exists():
                icon_path.unlink()
                print(f"✅ Deleted unused official icon: {icon_path}")
        except Exception as e:
            print(f"⚠️ Could not delete official icon {icon_path}: {e}")

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
                    update_cache()

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
        self.update_fg = self.COLOR_RED
        self.update_border = self.COLOR_RED       # ✅ red border
        self.metadata = load_app_metadata()
        self.refresh_ui_data()

        Clock.schedule_once(self.restore_update_button, 3)

    def restore_update_button(self, *args):
        self.update_text = "Update App & Icons"
        self.update_bg = self.COLOR_ORANGE_LIGHT_UI
        self.update_fg = self.COLOR_BLUE_DARK
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
        self.sync_fg = self.COLOR_BLUE_DARK
        self.sync_border = self.COLOR_TRANSPARENT

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

    def open_about_popup(self, *args):
        show_about_popup(self)

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
