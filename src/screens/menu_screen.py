
# --- Kivy ---
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App

# --- project ---
from src.ui.components import CategoryCard
from src.utils.icon_utils import get_icon_path


class MenuScreen(Screen):

    def open_category(self, category_name):
        app = App.get_running_app()
        detail_screen = app.root.get_screen("details")
        detail_screen.show_category(category_name)
        app.root.current = "details"

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
        topics = sorted(
            app.APP_DATA.get("topics", []),
            key=lambda t: (
                (t.get("Category") or "").lower(),
                (t.get("Subcategory") or "").lower(),
                (t.get("Title") or "").lower()
            )
        )

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


