
# --- Kivy ---
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.metrics import dp

# --- standard ---
from math import ceil

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
        Clock.schedule_once(self._bind_resize, 0)

    def _bind_resize(self, *_):
        # bind once
        if getattr(self, "_resize_bound", False):
            return

        self.ids.scroll_view.bind(size=self.update_menu_layout)
        self._resize_bound = True

    def check_data(self, *args):
        app = App.get_running_app()

        if not app.APP_DATA:
            Clock.schedule_once(self.check_data, 0.2)
            return

        self.populate_menu()

    def populate_menu(self, *args):
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

        Clock.schedule_once(self.update_menu_layout, 0)

    def update_menu_layout(self, *args):
        grid = self.ids.menu_container
        scroll = self.ids.scroll_view

        cards = [child for child in grid.children if isinstance(child, CategoryCard)]
        if not cards:
            return

        total_cards = len(cards)

        # ----- layout constants -----
        pad = dp(20)
        gap = dp(20)

        # minimum card width before adding a new column
        min_card_width = dp(260)

        # minimum 2 columns
        cols = max(2, int((scroll.width - 2 * pad + gap) // (min_card_width + gap)))

        # never create more columns than cards
        cols = min(cols, total_cards)

        rows = ceil(total_cards / cols)

        # usable width in the grid
        usable_width = scroll.width - 2 * pad - gap * (cols - 1)
        card_width = usable_width / cols

        # make cards rectangular, not square
        # tweak this ratio if you want slightly taller/shorter cards
        card_height = card_width * 1

        # icon size based on card height so it stays inside
        icon_size = card_height * 0.75

        grid.cols = cols
        grid.padding = [pad, pad]
        grid.spacing = [gap, gap]

        # set grid height explicitly so ScrollView works correctly
        grid.height = 2 * pad + rows * card_height + max(0, rows - 1) * gap

        for card in cards:
            card.card_height = card_height
            card.icon_size = icon_size

    def go_details(self, name):
        self.manager.selected_category = name
        self.manager.last_screen = "menu"
        self.manager.current = "details"
