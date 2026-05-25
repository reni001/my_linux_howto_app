from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App

from src.services.editor_service import save_metadata_to_firebase


class AppInfoScreen(Screen):


    def on_pre_enter(self):
        app = App.get_running_app()

        # ✅ fetch fresh data
        app.fetch_database()

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
            app.fetch_database()
            Clock.schedule_once(lambda dt: self.on_pre_enter(), 0.5)

            self.ids.status_label.text = "✅ Metadata saved"

        except Exception as e:
            self.ids.status_label.text = f"❌ Save failed: {e}"
