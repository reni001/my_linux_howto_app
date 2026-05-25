from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button

from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color, RoundedRectangle
from kivy.app import App
from kivy.uix.screenmanager import Screen

from src.utils.icon_utils import get_icon_path
from src.ui.theme import COLOR_BLUE, COLOR_ORANGE, NOTE_BG


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

        app = App.get_running_app()
        all_steps = app.APP_DATA.get('steps', [])
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
