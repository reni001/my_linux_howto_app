from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.modalview import ModalView
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.scatter import Scatter
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.graphics.transformation import Matrix
from kivy.app import App
from kivy.utils import escape_markup
import re

from pathlib import Path
from datetime import datetime

from src.utils.runtime_paths import get_runtime_paths
from src.utils.icon_utils import get_icon_path
from src.ui.theme import COLOR_BLUE, COLOR_ORANGE, NOTE_BG, COLOR_WHITE
from src.services.system_open_service import open_url as open_external_url
from src.utils.font_utils import get_font_path

icon = get_icon_path

# ✅ GLOBAL UI CONSTANTS (like KV #:set)
def UI(app):
    return {
        "SPACING": app.FONT_TEXT * 0.8,
        "SPACING_SMALL": app.FONT_TEXT * 0.5,
        "SPACING_LARGE": app.FONT_TEXT * 1.2,
        "ICON_SIZE": app.FONT_TEXT * 1.8,
        "ICON_SMALL": app.FONT_TEXT * 1.2,
        "INPUT_HEIGHT": app.FONT_TEXT * 2.2,
        "BUTTON_WIDTH": app.FONT_TEXT * 12,
    }


class ClickableImage(ButtonBehavior, Image):
    pass

class ZoomScatter(Scatter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_rotation = False
        self.do_translation = True
        self.do_scale = True
        self.scale_min = 0.5
        self.scale_max = 4.0
        self.auto_bring_to_front = False

    def on_touch_down(self, touch):
        # ✅ mouse wheel zoom on desktop
        if touch.is_mouse_scrolling:
            old_scale = self.scale

            if touch.button == 'scrolldown':
                new_scale = min(old_scale * 1.1, self.scale_max)
            elif touch.button == 'scrollup':
                new_scale = max(old_scale * 0.9, self.scale_min)
            else:
                return super().on_touch_down(touch)

            factor = new_scale / old_scale

            # ✅ scale around mouse position
            self.apply_transform(
                Matrix().scale(factor, factor, 1),
                post_multiply=True,
                anchor=touch.pos
            )
            return True

        return super().on_touch_down(touch)

class StepCard(BoxLayout):
    def __init__(self, step_data, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, **kwargs)

        app = App.get_running_app()
        ui = UI(app)

        self.padding = ui["SPACING"]
        self.spacing = ui["SPACING_SMALL"]
        self.bind(minimum_height=self.setter('height'))

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[ui["SPACING_SMALL"]]
            )

        self.bind(pos=self._update_graphics, size=self._update_graphics)

        self.build(step_data, app)

    def build(self, step, app):
        def safe_str(val, default=""):
            if val is None or str(val).lower() == 'nan':
                return default
            return str(val).strip()

        # --- STEP HEADLINE ---
        h1 = safe_str(step.get('Headline'))
        if h1:
            lbl = Label(
                text=h1,
                color=COLOR_BLUE,
                bold=True,
                font_size=app.FONT_SUBCATEGORY * 1.3,
                size_hint_y=None,
                halign='left'
            )
            lbl.bind(
                size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                texture_size=lambda inst, val: setattr(inst, 'height', val[1])
            )
            self.add_widget(lbl)

        # --- STEP HEADER_2 ---
        h2 = safe_str(step.get('Header_2'))
        if h2:
            h2_lbl = Label(
                text=h2,
                color=COLOR_ORANGE,
                bold=True,
                font_size=app.FONT_SUBCATEGORY * 1.1,
                size_hint_y=None,
                halign='left'
            )
            h2_lbl.bind(
                size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                texture_size=lambda inst, val: setattr(inst, 'height', val[1])
            )
            self.add_widget(h2_lbl)

        # --- STEP INSTRUCTION ---
        ins = safe_str(step.get('Instruction'))
        if ins:
            ins_lbl = Label(
                text=ins,
                color=[0.2, 0.2, 0.2, 1],
                font_size=app.FONT_TEXT * 1.2,
                size_hint_y=None,
                halign='left'
            )
            ins_lbl.bind(
                size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                texture_size=lambda inst, val: setattr(inst, 'height', val[1])
            )
            self.add_widget(ins_lbl)

    def _update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

class ArticleScreen(Screen):
    def go_back(self):
        dest = getattr(self.manager, 'last_screen', 'details')
        self.manager.current = dest

    def open_url(self, url):
        open_external_url(url)

    def _get_screenshot_path(self, filename: str) -> str:
        if not filename:
            return ""
        paths = get_runtime_paths()
        return str(paths["assets"] / "screenshots" / filename)

    def _highlight_code_simple(self, code: str) -> str:
        """
        Lightweight syntax highlighting for shell / terminal style code blocks.
        Uses Kivy markup only, no external dependency.
        """
        if not code:
            return ""

        # colours
        C_DEFAULT = "ffb347"   # warm orange
        C_COMMENT = "8a8f98"   # muted grey
        C_PROMPT  = "6aa9ff"   # blue
        C_CMD     = "ffd166"   # yellow/orange
        C_OPT     = "7fd1ff"   # cyan
        C_URL     = "66d9ef"   # bright cyan
        C_STRING  = "a6e22e"   # green

        known_cmds = {
            "sudo", "apt", "apt-get", "pacman", "dnf", "yum", "zypper",
            "systemctl", "journalctl", "chmod", "chown", "cp", "mv", "rm",
            "ls", "cd", "mkdir", "rmdir", "pwd", "find", "grep", "sed", "awk",
            "cat", "echo", "touch", "nano", "vim", "code",
            "git", "python", "python3", "pip", "pip3",
            "curl", "wget", "tar", "unzip", "zip",
            "docker", "flatpak", "snap", "export", "source", "env",
            "uname", "ip", "ifconfig", "ping", "ssh", "scp"
        }

        def colour(text, hex_colour):
            return f"[color={hex_colour}]{text}[/color]"

        def highlight_line(line: str) -> str:
            stripped = line.lstrip()

            # full-line comments
            if stripped.startswith("#"):
                return colour(escape_markup(line), C_COMMENT)

            # URLs first
            escaped = escape_markup(line)
            escaped = re.sub(
                r'(https?://[^\s]+)',
                lambda m: colour(m.group(1), C_URL),
                escaped
            )

            # quoted strings
            escaped = re.sub(
                r'(".*?"|\'.*?\')',
                lambda m: colour(m.group(1), C_STRING),
                escaped
            )

            prompt_prefix = ""
            rest = escaped

            # highlight shell prompts
            if stripped.startswith("$ "):
                prefix_index = escaped.find("$ ")
                if prefix_index >= 0:
                    prompt_prefix = escaped[:prefix_index] + colour("$", C_PROMPT) + " "
                    rest = escaped[prefix_index + 2:]
            elif stripped.startswith("# "):
                prefix_index = escaped.find("# ")
                if prefix_index >= 0:
                    prompt_prefix = escaped[:prefix_index] + colour("#", C_PROMPT) + " "
                    rest = escaped[prefix_index + 2:]
            elif stripped.startswith("> "):
                prefix_index = escaped.find("> ")
                if prefix_index >= 0:
                    prompt_prefix = escaped[:prefix_index] + colour(">", C_PROMPT) + " "
                    rest = escaped[prefix_index + 2:]

            tokens = rest.split(" ")
            out = []

            command_coloured = False
            for token in tokens:
                if not token:
                    out.append("")
                    continue

                plain = re.sub(r'\[/?color=.*?\]|\[/color\]', '', token)

                if plain in known_cmds and not command_coloured:
                    out.append(colour(token, C_CMD))
                    command_coloured = True
                elif plain.startswith("-"):
                    out.append(colour(token, C_OPT))
                else:
                    out.append(token)

            highlighted = " ".join(out)

            if not prompt_prefix and escaped == line:
                # raw line without escaped markup path
                escaped = escape_markup(line)

            return prompt_prefix + highlighted if prompt_prefix else highlighted

        lines = code.splitlines()
        return "\n".join(highlight_line(line) for line in lines)

    def _build_code_block(self, code: str, app):
        ui = UI(app)
        if not code:
            return None

        code_anchor = AnchorLayout(
            anchor_x='right',
            anchor_y='top',
            size_hint_y=None
        )

        code_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[ui["SPACING"], ui["SPACING"], ui["ICON_SIZE"] * 2, ui["SPACING"]]
        )

        with code_box.canvas.before:
            Color(rgba=[0.15, 0.15, 0.15, 1])
            code_box.bg_rect = RoundedRectangle(
                pos=code_box.pos,
                size=code_box.size,
                radius=[ui["SPACING_SMALL"]]
            )

        code_box.bind(minimum_height=code_box.setter('height'))
        code_box.bind(pos=self._update_graphics, size=self._update_graphics)

        try:
            font_path = get_font_path("JetBrainsMono-Regular.ttf")
        except:
            font_path = "DejaVuSansMono.ttf"


        # syntax-highlighted code text
        highlighted_code = self._highlight_code_simple(code)

        # font fallback
        try:
            font_path = get_font_path("JetBrainsMono-Regular.ttf")
        except:
            font_path = "DejaVuSansMono.ttf"

        code_lbl = Label(
            text=highlighted_code,
            markup=True,
            font_name=font_path,
            color=COLOR_ORANGE,
            font_size=app.FONT_CODE,
            line_height=1.4,
            padding=(0, ui["SPACING_SMALL"]),
            size_hint_y=None,
            halign='left'
        )

        code_lbl.bind(
            size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
            texture_size=lambda inst, val: setattr(inst, 'height', val[1])
        )

        code_box.add_widget(code_lbl)
        code_anchor.add_widget(code_box)

        code_box.bind(height=code_anchor.setter('height'))

        copy_btn = Button(
            text="Copy",
            size_hint=(None, None),
            size=(ui["BUTTON_WIDTH"] * 0.35, ui["INPUT_HEIGHT"]),
            font_size=app.FONT_BUTTON,
            background_color=[0.3, 0.3, 0.3, 1]
        )

        copy_btn.bind(on_release=lambda x, c=code: self.copy_to_clipboard(x, c))
        code_anchor.add_widget(copy_btn)

        return code_anchor

    def _build_step_urls(self, raw_urls: str, app):
        ui = UI(app)
        if not raw_urls:
            return []

        widgets = []

        url_list = [u.strip() for u in raw_urls.split(',') if u.strip()]

        for link in url_list:
            url_box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=ui["INPUT_HEIGHT"],
                spacing=ui["SPACING_SMALL"]
            )

            url_box.add_widget(
                Image(
                    source=icon("link2.png"),
                    size_hint_x=None,
                    width=ui["ICON_SMALL"]
                )
            )

            url_btn = Button(
                text=link,
                color=[0.1, 0.4, 0.8, 1],
                background_color=[0, 0, 0, 0],
                font_size=app.FONT_TEXT,
                halign='left',
                shorten=True,
                shorten_from='right',
                size_hint_x=1
            )

            url_btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            url_btn.bind(on_release=lambda x, u=link: self.open_url(u))

            url_box.add_widget(url_btn)
            widgets.append(url_box)

        return widgets

    def _build_step_screenshot(self, step, safe_str, app):
        ui = UI(app)
        screenshot = safe_str(step.get('Screenshot'))
        if not screenshot:
            return None

        path = self._get_screenshot_path(screenshot)

        img = ClickableImage(
            source=path,
            size_hint_y=None,
            height=ui["ICON_SIZE"] * 6,
            allow_stretch=True,
            keep_ratio=True
        )

        img.bind(on_release=lambda x, p=path: self.show_fullscreen_image(p))
        return img

    def _build_note_box(self, note: str, app):
        ui = UI(app)
        if not note:
            return None

        note_container = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            spacing=ui["SPACING"],
            padding=ui["SPACING"]
        )

        with note_container.canvas.before:
            Color(rgba=NOTE_BG)
            note_container.bg_rect = RoundedRectangle(
                pos=note_container.pos,
                size=note_container.size,
                radius=[ui["SPACING_SMALL"]]
            )

        note_container.bind(minimum_height=note_container.setter('height'))
        note_container.bind(pos=self._update_graphics, size=self._update_graphics)

        note_container.add_widget(
            Image(
                source=icon("note.png"),
                size_hint=(None, None),
                size=(ui["ICON_SIZE"], ui["ICON_SIZE"]),
                pos_hint={'top': 1}
            )
        )

        markup_text = "[b][color=ff8b02]NOTE:[/color][/b]\n" + note

        note_lbl = Label(
            text=markup_text,
            markup=True,
            color=[0.2, 0.2, 0.2, 1],
            font_size=app.FONT_TEXT * 1.1,
            italic=True,
            size_hint_y=None,
            halign='left',
            valign='top'
        )

        note_lbl.bind(
            size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
            texture_size=lambda inst, val: setattr(inst, 'height', val[1])
        )

        note_container.add_widget(note_lbl)

        return note_container

    def _build_topic_urls(self, raw_urls: str, app):
        ui = UI(app)
        if not raw_urls:
            return []

        widgets = []

        url_list = [u.strip() for u in raw_urls.split(',') if u.strip()]

        for link in url_list:
            url_box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=ui["INPUT_HEIGHT"],
                spacing=ui["SPACING_SMALL"]
            )

            url_box.add_widget(
                Image(
                    source=icon("link2.png"),
                    size_hint_x=None,
                    width=ui["ICON_SMALL"]
                )
            )

            url_btn = Button(
                text=link,
                color=[0.1, 0.4, 0.8, 1],
                background_color=[0, 0, 0, 0],
                font_size=app.FONT_TEXT * 1.1,
                halign='left',
                shorten=True,
                shorten_from='right',
                size_hint_x=1
            )

            url_btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            url_btn.bind(on_release=lambda x, u=link: self.open_url(u))

            url_box.add_widget(url_btn)

            widgets.append(url_box)

        return widgets

    def _build_topic_header(self, data, app, safe_str):
        widgets = []
        ui = UI(app)

        # --- ICON ---
        icon_name = safe_str(data.get('Topic_Icon'))

        # ✅ fallback to default icon
        if not icon_name:
            icon_name = "default.png"

        img = Image(
            source=icon(icon_name),
            size_hint_y=None,
            height=ui["ICON_SIZE"] * 5
        )
        widgets.append(img)


        # --- TITLE ---
        title = safe_str(data.get('Title'))
        if title:
            title_lbl = Label(
                text=title,
                color=COLOR_BLUE,
                font_size=app.FONT_TITLE * 1.5,
                bold=True,
                size_hint_y=None,
                halign='center'
            )

            title_lbl.bind(
                size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                texture_size=lambda inst, val: setattr(inst, 'height', val[1])
            )

            widgets.append(title_lbl)

        # --- META ---
        date_created = safe_str(data.get('Date_Created'))
        date_updated = safe_str(data.get('Date_Updated'))

        def format_date(d):
            if not d:
                return ""
            try:
                return datetime.fromisoformat(d).strftime("%d %b %Y")
            except:
                return d

        meta_parts = []

        if date_created:
            meta_parts.append(f"Created: {format_date(date_created)}")

        if date_updated:
            meta_parts.append(f"Updated: {format_date(date_updated)}")

        if meta_parts:
            meta_lbl = Label(
                text="   |   ".join(meta_parts),
                color=[0.5, 0.5, 0.5, 1],
                font_size=app.FONT_TEXT * 0.9,
                size_hint_y=None,
                halign='center'
            )

            meta_lbl.bind(
                size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                texture_size=lambda inst, val: setattr(inst, 'height', val[1])
            )

            widgets.append(meta_lbl)

        # --- DESCRIPTION ---
        desc_text = safe_str(data.get('Description'))
        if desc_text:
            desc_lbl = Label(
                text=desc_text,
                color=[0.3, 0.3, 0.3, 1],
                font_size=app.FONT_TEXT * 1.2,
                italic=True,
                size_hint_y=None,
                halign='left'
            )

            desc_lbl.bind(
                size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                texture_size=lambda inst, val: setattr(inst, 'height', val[1])
            )

            widgets.append(desc_lbl)

        return widgets

    def setup_article(self, data):
        if not data:
            return

        # ✅ STORE CURRENT TOPIC
        self.current_topic_id = data.get("Topic_ID")
        self.current_topic_key = data.get("_key")

        self.ids.content_box.clear_widgets()
        app = App.get_running_app()
        self.ids.content_box.spacing = app.FONT_TEXT * 0.8   # = SPACING
        topic_id = data.get('Topic_ID')

        def safe_str(val, default=""):
            if val is None or str(val).lower() == 'nan': return default
            return str(val).strip()

        # --- TOP HEADER ---
        header_widgets = self._build_topic_header(data, app, safe_str)

        for w in header_widgets:
            self.ids.content_box.add_widget(w)

        # --- 4. TOPIC URLS ---
        raw_topic_urls = safe_str(data.get('URLs'))

        url_widgets = self._build_topic_urls(raw_topic_urls, app)

        for w in url_widgets:
            self.ids.content_box.add_widget(w)

        # --- STEPS ---

        app = App.get_running_app()
        all_steps = app.APP_DATA.get('steps', [])
        topic_steps = [s for s in all_steps if s and s.get('Topic_ID') == topic_id]
        topic_steps.sort(key=lambda x: int(x.get('Step_Order', 999)))

        for step in topic_steps:
            card = StepCard(step)

            # --- CODE SNIPPET ---
            code = safe_str(step.get('Code_Snippet'))
            code_widget = self._build_code_block(code, app)
            if code_widget:
                card.add_widget(code_widget)

            # --- STEP SCREENSHOT ---
            screenshot_widget = self._build_step_screenshot(step, safe_str, app)
            if screenshot_widget:
                card.add_widget(screenshot_widget)

            # --- STEP URLS ---
            raw_step_urls = safe_str(step.get('URLs'))
            url_widgets = self._build_step_urls(raw_step_urls, app)


            for w in url_widgets:
                card.add_widget(w)

            # --- NOTES ---
            note = safe_str(step.get('Notes'))
            note_widget = self._build_note_box(note, app)
            if note_widget:
                card.add_widget(note_widget)

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


    def show_fullscreen_image(self, image_path):
        app = App.get_running_app()
        ui = UI(app)

        modal = ModalView(
            size_hint=(1, 1),
            auto_dismiss=True,
            background_color=(0, 0, 0, 0.95)
        )

        root = FloatLayout()

        # scatter handles pan + zoom
        scatter = ZoomScatter(
            size_hint=(None, None),
            pos=(0, 0)
        )

        # content inside scatter so border and image move together
        content = FloatLayout(
            size_hint=(None, None),
            pos=(0, 0)
        )

        img = Image(
            source=image_path,
            size_hint=(1, 1),
            pos=(0, 0),
            fit_mode="contain",
            allow_stretch=True,
            keep_ratio=True
        )

        # border belongs to the same transformed content
        with content.canvas.before:
            Color(*COLOR_WHITE)
            content.border = Line(width=2.5, rectangle=(0, 0, 0, 0))

        content.add_widget(img)
        scatter.add_widget(content)
        root.add_widget(scatter)

        close_btn = Button(
            text="X",
            size_hint=(None, None),
            size=(ui["ICON_SIZE"] * 1.8, ui["ICON_SIZE"] * 1.8),
            pos_hint={"right": 0.98, "top": 0.98},
            background_color=COLOR_ORANGE,
            color=COLOR_WHITE,
            font_size=app.FONT_TITLE,
            bold=True
        )
        close_btn.bind(on_release=lambda x: modal.dismiss())
        root.add_widget(close_btn)

        modal.add_widget(root)
        modal.open()

        def layout_content(*args):
            if not img.texture:
                return

            tex_w = img.texture.width
            tex_h = img.texture.height
            if tex_w <= 0 or tex_h <= 0:
                return

            max_w = modal.width * 0.9
            max_h = modal.height * 0.9
            ratio = tex_w / tex_h

            if max_w / ratio <= max_h:
                w = max_w
                h = w / ratio
            else:
                h = max_h
                w = h * ratio

            # size of image box before zooming
            content.size = (w, h)
            img.size = (w, h)
            content.border.rectangle = (0, 0, w, h)

            scatter.size = (w, h)
            scatter.pos = ((modal.width - w) / 2, (modal.height - h) / 2)

            # reset transform when viewer opens / window resizes
            scatter.transform = Matrix().translate(scatter.x, scatter.y, 0)
            scatter.scale = 1.0

        img.bind(texture=lambda *a: Clock.schedule_once(lambda dt: layout_content(), 0))
        modal.bind(size=lambda *a: Clock.schedule_once(lambda dt: layout_content(), 0))
        Clock.schedule_once(lambda dt: layout_content(), 0.1)

