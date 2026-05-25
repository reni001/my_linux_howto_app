
# --- Kivy ---
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App

# --- project ---
from src.ui.components import CategoryCard
from src.utils.icon_utils import get_icon_path


class MenuScreen(Screen):

    def on_enter(self):
        self.check_data()

    def check_data(self, *args):
        app = App.get_running_app()

        if not app.APP_DATA:
            Clock.schedule_once(self.check_data, 0.2)
            return

        self.populate_menu()

    def populate_menu(self):
        app = App.get_running_app()
        topics = app.APP_DATA.get("topics", [])

        unique_cats = {}

        for t in topics:
            if isinstance(t, dict) and t.get("Category"):
                unique_cats[t["Category"]] = t.get("Cat_Icon")

        self.ids.menu_container.clear_widgets()

        for name, icon in unique_cats.items():
            card = CategoryCard(
                name=name,
                icon_source=get_icon_path(icon)
            )
            card.bind(on_release=lambda x, n=name: self.go_details(n))
            self.ids.menu_container.add_widget(card)

    def go_details(self, name):
        self.manager.selected_category = name
        self.manager.last_screen = "menu"
        self.manager.current = "details"


