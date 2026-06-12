
# --- Standard library ---
import requests
import os
import platform
import webbrowser
import subprocess
import sys
import traceback
import shutil
import json
from threading import Thread
from pathlib import Path
import logging

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# ---- debugging -----
# ✅ Reduce Kivy console noise
#os.environ["KIVY_NO_CONSOLELOG"] = "1"
#os.environ["KIVY_LOG_LEVEL"] = "warning"

# ✅ ENABLE DEBUG
os.environ.pop("KIVY_NO_CONSOLELOG", None)
os.environ["KIVY_LOG_LEVEL"] = "debug"


def global_exception_hook(exc_type, exc_value, exc_traceback):
    print("\n💥 FULL CRASH TRACE:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_hook


# --- Project imports ---
from src.utils.first_run import initialize_first_run
from src.utils.runtime_paths import is_dev_mode, get_runtime_paths

from src.screens.add_topic_screen import AddTopicScreen
from src.screens.menu_screen import MenuScreen
from src.screens.search_screen import SearchScreen
from src.screens.detail_screen import DetailScreen
from src.screens.article_screen import ArticleScreen
from src.screens.add_step_screen import AddStepScreen
from src.screens.json_viewer_screen import JsonViewerScreen
from src.screens.app_info_screen import AppInfoScreen

# --- Data / Core services ---
from src.services.data_service import (
    fetch_database,
    load_app_metadata,
    APP_DATA,
    add_local_topic_and_steps,
    update_local_topic_and_steps,
    delete_local_topic
)
from src.services.category_service import generate_categories_from_topics
from src.services.subcategory_service import generate_from_topics

# --- Topic / Editor logic ---
from src.services.editor_service import is_admin_enabled, delete_topic_from_firebase
from src.services.topic_service import do_promote_topic, do_demote_topic

# --- Backup / Update / Restore/ delete ---
from src.services.backup_service import (
    get_backups,
    restore_backup_file,
    backup_database
)
from src.services.update_content import update_assets, update_cache
from src.services.restore_service import restore_backup as svc_restore_backup
from src.ui.dialogs.restore_dialog import show_restore_backup_dialog as ui_show_restore_dialog
from src.services.topic_delete_service import delete_topic as svc_delete_topic

from src.services.topic_action_service import (
    promote_topic as svc_promote_topic,
    demote_topic as svc_demote_topic,
)

# --- Icons ---
from src.services.icon_service import (
    get_icon_path as resolve_icon_path,
    copy_user_icon_to_official,
    copy_official_icon_to_user_icons,
    delete_official_icon_if_unused
)
from src.services.icon_cleanup import (
    clean_unused_icons,
    delete_user_icon_if_unused,
    find_unused_icons
)

# --- UI / dialogs ---
from src.ui.about_popup import show_about_popup
from src.ui.dialogs.cleanup_dialog import show_cleanup_dialog, undo_cleanup
from src.ui.dialogs.confirm_dialog import show_confirm_dialog
from src.ui.dialogs.subcategory_dialog import show_subcategory_dialog
from src.ui.dialogs.promotion_dialog import show_promotion_dialog
from src.ui.dialogs.category_dialog import show_category_dialog
from src.ui.styled_popup import create_popup_container
from src.ui.window_manager import apply_desktop_window_defaults, toggle_orientation

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
from kivy.core.text import LabelBase
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.uix.boxlayout import BoxLayout
#from kivy.uix.floatlayout import FloatLayout
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

# ------ Font registration --------
# ✅ Register custom fonts

paths = get_runtime_paths()
fonts_path = paths["assets"] / "fonts"

LabelBase.register(
    name="RobotoMono",
    fn_regular=str(fonts_path / "RobotoMono.ttf")
)

LabelBase.register(
    name="NotoSans",
    fn_regular=str(fonts_path / "NotoSans.ttf")
)

LabelBase.register(
    name="NotoSymbols",
    fn_regular=str(fonts_path / "NotoSansSymbols2-Regular.ttf")
)

# ✅ ensure runtime dirs & config exist
# ✅ Only run once per session (no repeat)
if not getattr(sys, "_app_initialized", False):
    initialize_first_run()
    sys._app_initialized = True

# --- UI DEFINITIONS (KV) --
# The KV layout was moved from the inlined KV string to an external file.
# This is a lossless move: main.kv contains the exact same KV content as before.

KV = None
KV_FILE = str(Path(__file__).parent / "main.kv")



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

    # --- Typography scale ---
    FONT_CATEGORY = NumericProperty(26)
    FONT_SUBCATEGORY = NumericProperty(21)
    FONT_TITLE = NumericProperty(24)
    FONT_TEXT = NumericProperty(19)
    FONT_MENU_TITLE = NumericProperty(20)
    FONT_MENU_STATUS = NumericProperty(17)
    FONT_BUTTON = NumericProperty(20)
    FONT_CODE = NumericProperty(18)

    # --- Backup button visuals ---
    backup_text = StringProperty("Create Backup")
    backup_bg = ListProperty(list(COLOR_PURPLE))
    backup_fg = ListProperty(list(COLOR_WHITE))
    backup_border = ListProperty([0, 0, 0, 0])

    # --- Update button visuals ---
    update_text = StringProperty("Update Data")
    update_bg = ListProperty([1, 0.7, 0.3, 1])          # orange
    update_fg = ListProperty([0.1, 0.25, 0.45, 1])     # dark blue text
    update_border = ListProperty([0, 0, 0, 0])         # ✅ NEW

    # --- Upgrade button visuals ---
    upgrade_text = StringProperty("Upgrade App")
    upgrade_bg = ListProperty([1, 0.7, 0.3, 1])          # orange
    upgrade_fg = ListProperty([0.1, 0.25, 0.45, 1])     # dark blue text
    upgrade_border = ListProperty([0, 0, 0, 0])         # ✅ NEW

    #--- Sync button visuals ---
    # --- Sync button state (MUST be Properties) ---
    sync_text = StringProperty("Developer Sync (Firebase & Git)")
    sync_bg = ListProperty([1, 0.5, 0, 1])          # orange
    sync_fg = ListProperty([0.1, 0.25, 0.45, 1])            # dark text
    sync_border = ListProperty([0, 0, 0, 0])        # invisible

    admin_enabled = BooleanProperty(False)   # ✅ for disabeling admin buttons
    admin_override = BooleanProperty(False)

    is_landscape = False
    previous_size = None


    def toggle_orientation(self):
        """
        Bridge method called from KV.
        Delegates the real logic to src.ui.window_manager.toggle_orientation.
        """
        toggle_orientation(self)

    def get_icon_path(self, filename):
        if not filename:
            return ""
        return resolve_icon_path(filename)

    #----------helpers-----------

    def update_typography_scale(self, *args):

        if hasattr(self, "_font_initialized"):
            return
        self._font_initialized = True

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
        self.FONT_SUBCATEGORY = 21 * scale
        self.FONT_TITLE = 24 * scale
        self.FONT_TEXT = 19 * scale
        self.FONT_MENU_TITLE = 20 * scale
        self.FONT_MENU_STATUS = 17 * scale #admin vs user
        self.FONT_BUTTON = 20 * scale
        self.FONT_CODE = 18 * scale


    def build_step_index(self):
        self.STEPS_BY_TOPIC = {}

        for step in self.APP_DATA.get("steps", []):
            tid = step.get("Topic_ID")
            if not tid:
                continue
            self.STEPS_BY_TOPIC.setdefault(tid, []).append(step)

        for steps in self.STEPS_BY_TOPIC.values():
            steps.sort(key=lambda x: int(x.get("Step_Order", 999)))

    def confirm_clean_icons(self):
        show_cleanup_dialog(self)

    def undo_cleanup(self, *args):
        undo_cleanup(self)

    def check_connection(self):
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


    def fetch_database(self):
        # 1) Load data from Firebase / cache
        fetch_database(self)

        # 2) Build step index from the freshly loaded data
        Clock.schedule_once(self._generate_taxonomies_when_ready, 0.2)
        self.build_step_index()

    def _generate_taxonomies_when_ready(self, _dt=0):

        if getattr(self, "_taxonomy_attempts", 0) > 10:
            return
        self._taxonomy_attempts = getattr(self, "_taxonomy_attempts", 0) + 1

        if getattr(self, "_taxonomy_ready", False):
            return

        topics = self.APP_DATA.get("topics", [])

        # wait until data is really loaded
        if not topics:
            Clock.schedule_once(self._generate_taxonomies_when_ready, 0.2)
            return

        # ✅ now safe to run
        generate_from_topics(self, overwrite=False)
        generate_categories_from_topics(self, overwrite=False)

        print("✅ Taxonomy generation completed")

        # ✅ mark as done ONLY AFTER execution
        self._taxonomy_ready = True

    def refresh_data_only(self):
        fetch_database(self)          # ✅ lightweight data refresh
        self.build_step_index()

    def refresh_all(self):
        """
        Centralised refresh after data changes.
        Keeps behaviour identical to current implementation.
        """
        self.refresh_data_only()

    def _apply_local_change(self, action):
        """
        Safely apply local change + refresh.
        """
        action()
        self._data_changed = True
        self.refresh_all()

    def save_local_topic(self, topic: dict, steps: list[dict]):
        self._apply_local_change(
            lambda: add_local_topic_and_steps(topic, steps)
        )

    def update_local_topic(self, topic_id: str, topic: dict, steps: list[dict]):
        self._apply_local_change(
            lambda: update_local_topic_and_steps(topic_id, topic, steps)
        )

    def delete_local_topic(self, topic_id: str):
        self._apply_local_change(
            lambda: delete_local_topic(topic_id)
        )

    def restore_backup(self, backup_path):
        svc_restore_backup(self, backup_path, restore_backup_file)

    def show_restore_backup_dialog(self):
        ui_show_restore_dialog(self)

    def _confirm_restore(self, backup_path):
        show_confirm_dialog(
            self,
            title="Restore Backup",
            message=f"Restore this backup?\n\n{backup_path.name}",
            confirm_text="RESTORE",
            confirm_color=self.COLOR_ORANGE,
            on_confirm=lambda: self.restore_backup(backup_path),
        )

    def reload_data(self):
        self.APP_DATA = fetch_database(force_reload=True)
        self.refresh_ui()

    #----------- update version ----------
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
            Clock.schedule_once(lambda dt: self.refresh_ui_data(), 0.6)
            return

        version = self.metadata.get("version", "0.0.0")
        last_update = self.metadata.get("last update", "")

        self.version_string = f"v{version} | {last_update}"


        # Also trigger the standard menu population
        try:
            menu_screen = self.sm.get_screen('menu')

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

            menu_screen = self.sm.get_screen("menu")
            if getattr(self, "_data_changed", True):
                menu_screen.force_reload_menu()
                self._data_changed = False


        except Exception as e:
            print(f"[ERROR] Failed to open file: {e}")
            pass

    def build(self):
        if KV_FILE not in Builder.files:
            Builder.load_file(KV_FILE)
        self.APP_DATA = APP_DATA
        self.admin_enabled = is_admin_enabled()
        self.admin_override = False

        self.icon = resolve_icon_path("howtolinux-icon.png")
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

        apply_desktop_window_defaults()

        Clock.schedule_once(self._startup_sequence, 0.5)

        return self.sm

    def _startup_sequence(self, dt):
        self.fetch_database()
        Clock.schedule_once(lambda dt: setattr(self, "_data_changed", False), 0.2)

        Window.bind(size=self.update_typography_scale)
        Clock.schedule_once(self.update_typography_scale, 0)

    def txt(self, text: str) -> str:
        return f"[font=NotoSans]{text}[/font]"

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
                screen.force_reload_menu()

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
        svc_delete_topic(self, data)

    # -------- duplicate helper -------
    def _norm(self, value):
        return str(value or "").strip().lower()

    # --------- backup --------
    def backup_current_data(self, *args):

        # --- UI: show running ---
        self.backup_text = "Creating backup..."
        self.backup_bg = [0.9, 0.9, 0.9, 1]
        self.backup_fg = list(self.COLOR_BLUE_DARK)
        self.backup_border = list(self.COLOR_TRANSPARENT)

        def run_backup():
            try:
                backup_database(self)
                Clock.schedule_once(self.backup_success, 0)
            except Exception as e:
                print(f"❌ Backup failed: {e}")
                Clock.schedule_once(self.backup_failed, 0)

        Thread(target=run_backup, daemon=True).start()

    def backup_success(self, *args):
        self.backup_text = "Backup created ✓"
        self.backup_bg = self.COLOR_WHITE_SOFT
        self.backup_fg = self.COLOR_GREEN
        self.backup_border = self.COLOR_GREEN

        Clock.schedule_once(self.restore_backup_button, 2)

    def backup_failed(self, *args):
        self.backup_text = "Backup failed x"
        self.backup_bg = self.COLOR_WHITE_SOFT
        self.backup_fg = self.COLOR_RED
        self.backup_border = self.COLOR_RED

        Clock.schedule_once(self.restore_backup_button, 3)

    def restore_backup_button(self, *args):
        self.backup_text = "Create Backup"
        self.backup_bg = self.COLOR_PURPLE
        self.backup_fg = self.COLOR_WHITE
        self.backup_border = self.COLOR_TRANSPARENT

    # -------- promote topic (make it public) --------
    def promote_topic(self, data):
        svc_promote_topic(self, data)

    #---- demote topic (make it private) -------

    def demote_topic(self, data):
        svc_demote_topic(self, data)

    # ---- update data button behaviour -----
    def update_app_from_git(self, *args):
        """
        Backward-compatible wrapper.
        Old KV/button references may still call this.
        """
        return self.update_data(*args)

    def update_data(self, *args):
        self.update_text = "Updating data..."
        self.update_bg = [0.9, 0.9, 0.9, 1]
        self.update_fg = [0.1, 0.25, 0.45, 1]
        self.update_border = [0, 0, 0, 0]

        def run_update():
            try:
                print("🔄 Updating data (assets + latest content)")

                if is_dev_mode():
                    # In dev mode, copy local repo assets into runtime assets
                    paths = get_runtime_paths()
                    repo_root = Path(__file__).resolve().parent.parent
                    repo_assets = repo_root / "assets"
                    runtime_assets = paths["assets"]

                    if repo_assets.exists():
                        shutil.copytree(repo_assets, runtime_assets, dirs_exist_ok=True)
                        print("✅ Dev assets copied into runtime")
                else:
                    # In packaged / normal mode, fetch new assets from GitHub zip
                    update_assets()

                # Refresh latest content from Firebase/cache
                self.refresh_data_only()

                Clock.schedule_once(self.update_success, 0)

            except Exception as e:
                print(f"❌ Data update failed: {e}")
                traceback.print_exc()
                Clock.schedule_once(self.update_failed, 0)

        Thread(target=run_update, daemon=True).start()


    def update_success(self, *args):
        self.update_text = "Data updated ✓"
        self.update_bg = self.COLOR_WHITE_SOFT
        self.update_fg = self.COLOR_GREEN
        self.update_border = self.COLOR_GREEN
        self.refresh_ui_data()

        Clock.schedule_once(self.restore_update_button, 2)


    def update_failed(self, *args):
        self.update_text = "Data update failed"
        self.update_bg = self.COLOR_WHITE_SOFT
        self.update_fg = self.COLOR_RED
        self.update_border = self.COLOR_RED

        Clock.schedule_once(self.restore_update_button, 3)


    def restore_update_button(self, *args):
        self.update_text = "Update Data"
        self.update_bg = self.COLOR_ORANGE_LIGHT_UI
        self.update_fg = self.COLOR_BLUE_DARK
        self.update_border = self.COLOR_TRANSPARENT


    #---- upgrade App ------
    def upgrade_app(self, *args):
        self.upgrade_text = "Upgrading app..."
        self.upgrade_bg = [0.9, 0.9, 0.9, 1]
        self.upgrade_fg = [0.1, 0.25, 0.45, 1]
        self.upgrade_border = [0, 0, 0, 0]

        def run_upgrade():
            try:
                if not is_dev_mode():
                    raise RuntimeError("App upgrade is only configured in development mode right now.")

                print("🔄 Upgrading app source from Git...")

                repo_root = Path(__file__).resolve().parent.parent
                subprocess.run(["git", "-C", str(repo_root), "pull"], check=True)

                Clock.schedule_once(self.upgrade_success, 0)

            except Exception as e:
                print(f"❌ App upgrade failed: {e}")
                traceback.print_exc()
                Clock.schedule_once(self.upgrade_failed, 0)

        Thread(target=run_upgrade, daemon=True).start()

    def upgrade_success(self, *args):
        self.upgrade_text = "Upgrade ready - restart app"
        self.upgrade_bg = self.COLOR_WHITE_SOFT
        self.upgrade_fg = self.COLOR_GREEN
        self.upgrade_border = self.COLOR_GREEN

        Clock.schedule_once(self.restore_upgrade_button, 3)

    def upgrade_failed(self, *args):
        self.upgrade_text = "Upgrade unavailable"
        self.upgrade_bg = self.COLOR_WHITE_SOFT
        self.upgrade_fg = self.COLOR_RED
        self.upgrade_border = self.COLOR_RED

        Clock.schedule_once(self.restore_upgrade_button, 3)

    def restore_upgrade_button(self, *args):
        self.upgrade_text = "Upgrade App"
        self.upgrade_bg = self.COLOR_ORANGE_LIGHT_UI
        self.upgrade_fg = self.COLOR_BLUE_DARK
        self.upgrade_border = self.COLOR_TRANSPARENT

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

    def open_category_dialog(self):
        show_category_dialog(self)

    def open_subcategory_dialog(self):
        show_subcategory_dialog(self)

class LazyImage(Image):
    def on_kv_post(self, base_widget):
        if self.source:
            src = self.source
            self.source = ""

            # load icon in next frame → non-blocking
            Clock.schedule_once(
                lambda dt: setattr(self, "source", src),
                0
            )

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
