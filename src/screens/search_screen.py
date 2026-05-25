
# --- Kivy ---
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window

# --- project ---
from src.ui.components import EntryListItem
from src.utils.icon_utils import get_icon_path
from src.ui.theme import COLOR_ORANGE


class SearchScreen(Screen):

    def on_enter(self):
        self.ids.search_input.focus = True
        self.filter_results(self.ids.search_input.text)

    def go_back(self):
        self.ids.search_input.text = ""
        self.manager.current = "menu"

    def go_article(self, instance):
        self.manager.last_screen = "search"
        self.manager.get_screen("article").setup_article(instance.data)
        self.manager.current = "article"

    def filter_results(self, query):
        self.ids.results_container.clear_widgets()

        if not query or len(query) < 2:
            return

        query = query.lower().strip()

        app = App.get_running_app()
        all_topics = app.APP_DATA.get('topics', [])

        # ✅ filter EXACTLY like original
        matches = [
            t for t in all_topics
            if t and (
                query in str(t.get('Title','')).lower()
                or query in str(t.get('Category','')).lower()
                or query in str(t.get('Description','')).lower()
            )
        ]

        # ✅ FIX: remove duplicates (new issue after refactor)
        unique = {}
        for t in matches:
            key = t.get("Topic_ID") or t.get("Title")
            unique[key] = t

        matches = list(unique.values())

        # ✅ group properly BEFORE rendering
        grouped = {}
        for t in matches:
            cat = str(t.get('Category','')).upper()
            grouped.setdefault(cat, []).append(t)

        # ✅ sort categories
        for cat in sorted(grouped.keys()):

            # ✅ add header only if category has items
            header = Label(
                text=f"  {cat}",
                color=COLOR_ORANGE,
                bold=True,
                font_size='18sp',
                size_hint_y=None,
                height=dp(50),
                halign='left',
                text_size=(Window.width - dp(40), None)
            )

            self.ids.results_container.add_widget(header)

            # ✅ add items under this category
            for item in grouped[cat]:
                btn = EntryListItem(
                    title=item.get('Title',''),
                    desc=item.get('Description',''),
                    icon_source=get_icon_path(item.get('Topic_Icon')),
                    data=item
                )

                btn.bind(on_release=self.go_article)
                self.ids.results_container.add_widget(btn)



