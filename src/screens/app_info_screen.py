from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.metrics import dp

from src.services.editor_service import save_metadata_to_firebase
from src.services.data_service import fetch_database


class AppInfoScreen(Screen):


    def on_pre_enter(self):
        app = App.get_running_app()

        # ✅ fetch fresh data
        fetch_database(app)

        # ✅ delay load
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
        self.render_changelog()


    def save_metadata(self):
        from src.services.editor_service import save_metadata_to_firebase

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
            fetch_database(app)
            Clock.schedule_once(lambda dt: self.on_pre_enter(), 0.5)

            self.ids.status_label.text = "✅ Metadata saved"

        except Exception as e:
            self.ids.status_label.text = f"❌ Save failed: {e}"

    def render_changelog(self):
        app = App.get_running_app()
        container = self.ids.changelog_display
        container.clear_widgets()

        icon_map = {
            "features": "feature.png",
            "improvements": "improvement.png",
            "fixes": "fix.png",
        }

        text = self.ids.changelog.text.split("\n")

        for line in text:
            line = line.strip()
            if not line:
                continue

            is_version = line.lower().startswith("version")

            matched = None
            for key in icon_map:
                if key in line.lower():
                    matched = key
                    break

            # ✅ VERSION HEADER
            if is_version:
                row = BoxLayout(
                    size_hint_y=None,
                    height=app.FONT_TITLE * 1.6,
                    spacing=app.FONT_TEXT * 0.4
                )

                row.add_widget(Image(
                    source=App.get_running_app().get_icon_path("version.png"),
                    size_hint=(None, None),
                    size=(app.FONT_TEXT * 1.2, app.FONT_TEXT * 1.2),
                    pos_hint={"center_y": 0.5}
                ))

                lbl = Label(
                    text=f"[b]{line}[/b]",
                    markup=True,
                    font_size=app.FONT_TITLE,
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    valign="middle",
                    color=[0.05, 0.2, 0.4, 1],
                )

                lbl.bind(
                    size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                    texture_size=lambda i, v: setattr(i, "height", v[1])
                )

                row.add_widget(lbl)
                container.add_widget(row)

            # ✅ SECTION HEADERS
            elif matched:
                row = BoxLayout(
                    size_hint_y=None,
                    height=app.FONT_SUBCATEGORY * 1.8,
                    spacing=app.FONT_TEXT * 0.4
                )

                row.add_widget(Image(
                    source=App.get_running_app().get_icon_path(icon_map[matched]),
                    size_hint=(None, None),
                    size=(app.FONT_TEXT * 1.1, app.FONT_TEXT * 1.1),
                    pos_hint={"center_y": 0.5}
                ))

                lbl = Label(
                    text=f"[b]{line}[/b]",
                    markup=True,
                    font_size=app.FONT_TEXT,
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    valign="middle",
                    color=[0.1, 0.25, 0.45, 1],
                )

                lbl.bind(
                    size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                    texture_size=lambda i, v: setattr(i, "height", v[1])
                )

                row.add_widget(lbl)
                container.add_widget(row)

            # ✅ NORMAL TEXT
            else:
                lbl = Label(
                    text=line,
                    font_size=app.FONT_TEXT,
                    size_hint_y=None,
                    halign="left",
                    valign="top",
                    color=[0.1, 0.25, 0.45, 1],
                )

                lbl.padding = (app.FONT_TEXT * 1.5, 0)   # ✅ indent

                lbl.bind(
                    size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                    texture_size=lambda i, v: setattr(i, "height", v[1])
                )

                container.add_widget(lbl)

    def on_enter(self):
        if not hasattr(self, "_changelog_bound"):
            self.ids.changelog.bind(text=lambda *a: self.render_changelog())
            self._changelog_bound = True

        self.render_changelog()
