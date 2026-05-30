from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
import json
from pathlib import Path
from src.utils.runtime_paths import get_runtime_paths


class JsonViewerScreen(Screen):

    def on_enter(self):
        Clock.schedule_once(self.load_json, 0)

    def load_json(self, *args):
        paths = get_runtime_paths()
        file = paths["data"] / "cache.json"

        if not file.exists():
            self.ids.json_text.text = "No cache.json found"
            return

        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.ids.json_text.text = formatted

        except Exception as e:
            self.ids.json_text.text = f"Error:\n{e}"
