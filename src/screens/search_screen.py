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
from src.services.search_service import topic_matches, highlight_text, find_match_location


class SearchScreen(Screen):

    def on_enter(self):
        self.ids.search_input.focus = True
        self.filter_results(self.ids.search_input.text)

    def go_back(self):
        self.ids.search_input.text = ""
        self.manager.current = "menu"

    def go_article(self, instance):
        self.manager.last_screen = "search"

        article = self.manager.get_screen("article")
        article.current_search_query = self.ids.search_input.text.strip()
        article.setup_article(instance.data)

        self.manager.current = "article"


    def filter_results(self, query):
        self.ids.results_container.clear_widgets()

        if not query or len(query) < 2:
            return

        query = query.lower().strip()

        app = App.get_running_app()
        all_topics = app.APP_DATA.get('topics', [])

        # ✅ filter EXACTLY like original        
        matches = []

        for t in all_topics:
            if not t:
                continue

            topic_id = str(t.get("Topic_ID", "")).strip()

            # ✅ DEBUG: show topic id
            print("\n==== TOPIC DEBUG ====")
            print("TITLE:", t.get("Title"))
            print("TOPIC_ID:", topic_id)

            # ✅ DEBUG: inspect first 3 steps to see real key names
            all_steps = app.APP_DATA.get("steps", [])
            for idx, s in enumerate(all_steps[:3]):
                print(f"STEP SAMPLE {idx+1}:", s)

            # ✅ TEMPORARY ROBUST MATCH:
            # try several possible key names for topic linkage
            steps = [
                s for s in all_steps
                if str(s.get("Topic_ID", "")).strip() == topic_id
                or str(s.get("topic_id", "")).strip() == topic_id
                or str(s.get("Topic Id", "")).strip() == topic_id
                or str(s.get("topicId", "")).strip() == topic_id
            ]

            print("FOUND STEPS FOR TOPIC:", len(steps))

            if topic_matches(query, t, steps):
                matches.append(t)

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
                topic_id = str(item.get("Topic_ID", "")).strip()

                steps = [
                    s for s in app.APP_DATA.get("steps", [])
                    if str(s.get("Topic_ID", "")).strip() == topic_id
                ]

                location = find_match_location(query, item, steps)

                raw_title = item.get("Title", "")
                raw_desc = item.get("Description", "")

                title = highlight_text(raw_title, query)
                desc = highlight_text(raw_desc, query)

                if location:
                    desc = f"{desc}\n[size=12][color=#7a7a7a]Match in: {location}[/color][/size]"

                btn = EntryListItem(
                    title=title,
                    desc=desc,
                    icon_source=get_icon_path(item.get('Topic_Icon')),
                    data=item
                )

                btn.bind(on_release=self.go_article)
                self.ids.results_container.add_widget(btn)

