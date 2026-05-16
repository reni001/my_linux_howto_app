import time
import requests
import os
import platform
import webbrowser
import subprocess
import sys
import traceback
from threading import Thread
from src.first_run import initialize_first_run
from pathlib import Path
from src.config import load_firebase_config
from src.runtime_paths import is_dev_mode
from src.update_content import update_assets, update_excel

from src.runtime_paths import get_runtime_paths


# Kivy imports
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.properties import StringProperty, DictProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse
from kivy.metrics import dp
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

# ----- Check if python 3.12 is installed ---------

if sys.version_info >= (3, 14):
    print("\n⚠️ WARNING: Python 3.14 may be incompatible with Kivy")
    print("✅ The app will continue, but issues *might* occur")
    print("💡 Recommended: Use Python 3.12 if you encounter problems\n")

# --- CONFIGURATION ---
Window.size = (500, 850)

# ✅ ensure runtime dirs & config exist
#initialize_first_run()
Clock.schedule_once(lambda dt: initialize_first_run(), 1)

# ✅ now it is safe to load firebase.json
firebase_cfg = load_firebase_config()
DB_URL = firebase_cfg["database_url"] + "/.json"

APP_DATA = {}
for t in APP_DATA.get("topics", []):
    for k in ("Cat_Icon", "Sub_Icon", "Topic_Icon"):
        if t.get(k) == "":
            print(f"⚠️ Empty {k} in topic:", t.get("Title"))



# --- UI DEFINITIONS (KV) ---
# The KV layout was moved from the inlined KV string to an external file.
# This is a lossless move: main.kv contains the exact same KV content as before.
KV = None  # KV now lives in main.kv
#KV_FILE = os.path.join(SRC_DIR, "main.kv")
KV_FILE = str(Path(__file__).parent / "main.kv")
Builder.load_file(KV_FILE)


APP_DATA = {}
# Theme Colors
COLOR_BLUE = [59/255, 101/255, 184/255, 1]
COLOR_ORANGE = [255/255, 139/255, 2/255, 1]
PANEL_COLOR = [179/255, 209/255, 255/255, 1]
NOTE_BG = [255/255, 250/255, 230/255, 1]

# --- HELPER FUNCTIONS ---
def load_app_metadata():
    import pandas as pd
    from pathlib import Path

    metadata = {}

    # ✅ 1. Try Excel first
    try:
        paths = get_runtime_paths()
        excel_path = paths["data"] / "main.xlsx"

        if excel_path.exists():
            df = pd.read_excel(excel_path, sheet_name="AppInfo")

            for _, row in df.iterrows():
                key = str(row.iloc[0]).strip().lower()
                value = str(row.iloc[1]).strip()

                metadata[key] = value

            print("✅ Metadata loaded from Excel:", metadata)

    except Exception as e:
        print("[ERROR] Excel metadata failed:", e)

    # ✅ 2. FALLBACK to Firebase if Excel failed
    if not metadata:
        global APP_DATA
        firebase_meta = APP_DATA.get("metadata", {})

        print("✅ Using Firebase metadata:", firebase_meta)

        metadata = {
            "version": firebase_meta.get("version", "0.0.0"),
            "last_update": firebase_meta.get("last update", "unknown"),
            "description": firebase_meta.get("description", ""),
            "developer": firebase_meta.get("developer", ""),
            "changelog": firebase_meta.get("changelog", "")
        }

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

class LinuxHowToApp(App):
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

    def update_version_labels(self):
        """
        Update all version labels using self.metadata (Excel)
        """
        if not hasattr(self, 'sm'):
            return

        version = self.metadata.get("version", "0.0.0")
        last_update = self.metadata.get("last_update", "")

        version_str = f"v{version}\n{last_update}"

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
        #self.metadata = load_app_metadata()

        #self.update_version_labels()



    def toggle_orientation(self):
        w, h = Window.size
        Window.size = (850, 500) if w < h else (500, 850)

    def open_app_menu(self):
        AppMenu().open()

    def open_database(self):
        from src.runtime_paths import get_runtime_paths
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
                    APP_DATA = r.json()
                    print("DEBUG: Data fetched successfully")

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
        last_update = self.metadata.get("last_update", "")

        version_str = f"v{version}"
        version_str = f"v{version}\n{last_update}"

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
            if hasattr(menu_screen, 'populate_menu'):
                menu_screen.populate_menu()
        except:
            pass

    def build(self):
        #initialize_first_run()
        initialize_first_run()

        self.icon = get_icon_path("howto.png")

        self.sm = ScreenManager(transition=FadeTransition())
        self.sm.add_widget(MenuScreen(name='menu'))
        self.sm.add_widget(SearchScreen(name='search'))
        self.sm.add_widget(DetailScreen(name='details'))
        self.sm.add_widget(ArticleScreen(name='article'))

        self.fetch_database()
        return self.sm      

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

        # ✅ OUTER layout (fixed size)
        outer = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # ✅ HEADER (no scroll)
        outer.add_widget(Label(
           text=f"[b][size=28sp]{name}[/size][/b]\n"
                f"[size=16sp]Version {version}[/size]\n"
                f"[size=14sp]Last update: {last_update}[/size]\n"
                f"[size=14sp][color=888888]Developed by: {dev_name}[/color][/size]",
            markup=True,
            size_hint_y=None,
            height=120,
            halign='center'
        ))

        # ✅ SCROLLABLE AREA
        scroll = ScrollView(size_hint=(1, 1))

        scroll_content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=10,
            padding=[15, 10]
        )

        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        # ✅ DESCRIPTION
        desc_label = Label(
            text=f"[i]{desc}[/i]",
            markup=True,
            size_hint_y=None,
            halign='center',
            valign='top'
        )

        desc_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val, None)),
            texture_size=lambda inst, val: setattr(inst, 'height', val[1])
        )

        scroll_content.add_widget(desc_label)

        # ✅ CHANGELOG TITLE
        title_label = Label(
            text="[b]WHAT'S NEW[/b]",
            markup=True,
            size_hint_y=None,
            height=30,
            halign='left',
            valign='middle',
            color=[0.7, 0.7, 1, 1]
        )

        title_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val, None))
        )

        scroll_content.add_widget(title_label)


        # ✅ CHANGELOG TEXT (NOW SCROLLABLE ✅)
        changelog_label = Label(
            text=change,
            size_hint_y=None,
            halign='left',
            valign='top'
        )

        changelog_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val, None)),
            texture_size=lambda inst, val: setattr(inst, 'height', val[1])
        )


        changelog_label.bind(
            texture_size=lambda inst, val: setattr(inst, 'height', val[1])
        )

        scroll_content.add_widget(changelog_label)

        scroll.add_widget(scroll_content)
        outer.add_widget(scroll)

        # ✅ CLOSE BUTTON (fixed bottom)
        btn = Button(
            text='CLOSE',
            size_hint_y=None,
            height=50
        )

        outer.add_widget(btn)

        popup = Popup(
            title="About Application",
            content=outer,
            size_hint=(0.9, 0.9)
        )

        btn.bind(on_release=popup.dismiss)
        popup.open()


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
            source='assets/icons/down_arrow.png', size_hint_x=None, width=dp(25)
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

class MenuScreen(Screen):
    def on_enter(self):
        if not self.ids.menu_container.children: self.check_data()
    def check_data(self, *args):
        if APP_DATA: self.populate_menu()
        else: Clock.schedule_once(self.check_data, 0.2)
    def populate_menu(self):
        topics = APP_DATA.get('topics', [])
        unique_cats = {}
        for t in topics:
            if t and 'Category' in t:
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

############# Article Screen
class ArticleScreen(Screen):
    def go_back(self):
        dest = getattr(self.manager, 'last_screen', 'details')
        self.manager.current = dest

    def setup_article(self, data):
        if not data: return
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
                    Image(source='assets/icons/note.png', 
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


if __name__ == '__main__':
    LinuxHowToApp().run()
