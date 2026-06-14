
# --- Kivy ---
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.app import App
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.app import App

# --- project ---
from src.ui.components import ExpandableSection, EntryListItem
from src.utils.icon_utils import get_icon_path
from src.ui.theme import COLOR_BLUE
from src.services.search_service import topic_matches, highlight_text, find_match_location


class DetailScreen(Screen):
    header_title = StringProperty("")

    def show_category(self, category_name):
            app = App.get_running_app()

            self.ids.list_container.clear_widgets()

            topics = [
                t for t in app.APP_DATA.get("topics", [])
                if str(t.get("Category", "")).strip() == str(category_name).strip()
            ]

            for topic in topics:
                item = EntryListItem()
                item.data = topic
                item.title = topic.get("Title", "")
                item.desc = topic.get("Description", "")
                item.icon_source = app.get_icon_path(topic.get("Topic_Icon", ""))

                # open article/topic when clicked
                item.bind(on_release=lambda instance, topic=topic: self.open_topic(topic))
                self.ids.list_container.add_widget(item)

    def on_pre_enter(self):
        self.header_title = getattr(self.manager, "selected_category", "")
        self.ids.local_search.text = ""
        self.load_content_from_cache()

    def on_kv_post(self, base_widget):
        for w in self.walk():
            if isinstance(w, TextInput):
                w.bind(focus=self._on_any_textinput_focus)

    def _on_any_textinput_focus(self, instance, focused):
        if "form_scroll" in self.ids:
            self.ids.form_scroll.do_scroll_y = not focused

    def load_content_from_cache(self, query=""):
        self.ids.list_container.clear_widgets()

        app = App.get_running_app()
        if not app.APP_DATA:
            return

        cat_label = Label(
            text=self.header_title.upper(),
            color=COLOR_BLUE,
            bold=True,
            font_size=App.get_running_app().FONT_CATEGORY,
            size_hint_y=None,
            size_hint_x=1,
            height=dp(50),
            halign='left',
            valign='middle',
            text_size=(None, None)
        )

        self.ids.list_container.add_widget(cat_label)

        target_cat = self.header_title.strip().lower()
        query = query.lower().strip()

        items = [
            t for t in app.APP_DATA.get("topics", [])
            if t and str(t.get("Category")).strip().lower() == target_cat
        ]

        if query:
            filtered = []

            for i in items:
                topic_id = str(i.get("Topic_ID"))

                steps = [
                    s for s in app.APP_DATA.get("steps", [])
                    if str(s.get("Topic_ID")) == topic_id
                ]


                if topic_matches(query, i, steps):
                    filtered.append(i)

            items = filtered

        subs = {}
        for i in items:
            sub = i.get("Subcategory", "General")
            if not sub or str(sub).lower() == "nan":
                sub = "General"

            subs.setdefault(sub, []).append(i)

        for sub_name in sorted(subs.keys()):

            def normalize_title(title):
                title = (title or "").strip().lower()

                # remove common prefixes
                for prefix in ("the ", "a ", "an "):
                    if title.startswith(prefix):
                        title = title[len(prefix):]

                return title

            sub_items = sorted(
                subs[sub_name],
                key=lambda t: normalize_title(t.get("Title"))
            )

            section = ExpandableSection(
                sub_name,
                get_icon_path(sub_items[0].get("Sub_Icon")),
            )


            app = App.get_running_app()
            all_topics = app.APP_DATA.get("topics", [])

            for item in sub_items:

                # ✅ ensure original object (with _key)
                original = next(
                    (t for t in all_topics if t.get("Topic_ID") == item.get("Topic_ID")),
                    item
                )

                #print("DEBUG fixed item:", original)   # optional

                topic_id = str(original.get("Topic_ID", "")).strip()

                steps = [
                    s for s in app.APP_DATA.get("steps", [])
                    if str(s.get("Topic_ID", "")).strip() == topic_id
                ]

                location = find_match_location(query, original, steps)

                title = highlight_text(original.get("Title", ""), query)
                desc = highlight_text(original.get("Description", ""), query)

                if location and query:
                    desc = f"{desc}\n[size=12][color=#7a7a7a]Match in: {location}[/color][/size]"

                btn = EntryListItem(
                    title=title,
                    desc=desc,
                    icon_source=get_icon_path(original.get("Topic_Icon")),
                    data=original
                )

                btn.bind(on_release=self.go_article)
                section.add_entry(btn)


            self.ids.list_container.add_widget(section)

    def go_article(self, instance):
        self.manager.last_screen = "details"

        article = self.manager.get_screen("article")
        article.current_search_query = self.ids.local_search.text.strip()
        article.setup_article(instance.data)

        self.manager.current = "article"

