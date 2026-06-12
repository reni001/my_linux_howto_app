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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._resize_bound = False
        self._menu_signature = None
        self._cards_by_name = {}
        self._pending_cards = []
        self._batch_mode = False

    def open_category(self, category_name):
        app = App.get_running_app()
        detail_screen = app.root.get_screen("details")
        detail_screen.show_category(category_name)
        app.root.current = "details"

    def on_enter(self):
        self.check_data()
        Clock.schedule_once(self._bind_resize, 0)

    def _bind_resize(self, *_):
        if self._resize_bound:
            return

        self.ids.scroll_view.bind(size=self.update_menu_layout)
        self._resize_bound = True

    def check_data(self, *args):
        app = App.get_running_app()

        if not app.APP_DATA:
            Clock.schedule_once(self.check_data, 0.2)
            return

        if self._menu_signature is None:
            self.populate_menu()

    def force_reload_menu(self, *args):
        """
        Public entry point from main.py after data changes.
        Only updates what changed.
        """
        self.populate_menu(force=True)

    def _build_category_map(self):
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

        return dict(sorted(unique_cats.items(), key=lambda kv: kv[0].lower()))

    def _make_signature(self, category_map):
        return tuple((name, category_map[name] or "") for name in category_map.keys())

    def populate_menu(self, *args, force=False):
        category_map = self._build_category_map()
        new_signature = self._make_signature(category_map)

        # ✅ Nothing changed: no rebuild needed
        if not force and new_signature == self._menu_signature:
            Clock.schedule_once(self.update_menu_layout, 0)
            return

        container = self.ids.menu_container

        # --- remove deleted categories ---
        removed_names = [name for name in list(self._cards_by_name.keys()) if name not in category_map]
        for name in removed_names:
            card = self._cards_by_name.pop(name, None)
            if card and card.parent is container:
                container.remove_widget(card)

        # --- update icons on existing cards if needed ---
        for name, icon in category_map.items():
            if name in self._cards_by_name:
                card = self._cards_by_name[name]
                new_icon_source = get_icon_path(icon)
                if getattr(card, "icon_source", "") != new_icon_source:
                    card.icon_source = new_icon_source

        # --- prepare NEW cards only ---
        existing_names = set(self._cards_by_name.keys())
        self._pending_cards = [
            (name, icon)
            for name, icon in category_map.items()
            if name not in existing_names
        ]

        self._menu_signature = new_signature

        # First load: use progressive batches
        if self._pending_cards:
            self._batch_mode = True
            Clock.schedule_once(self._add_menu_batch, 0)
        else:
            Clock.schedule_once(self._reorder_and_layout, 0)

    def _add_menu_batch(self, dt):
        container = self.ids.menu_container
        batch_size = 6

        batch = self._pending_cards[:batch_size]
        self._pending_cards = self._pending_cards[batch_size:]

        for name, icon in batch:
            card = CategoryCard(
                name=name,
                icon_source=get_icon_path(icon)
            )
            card.bind(on_release=lambda x, n=name: self.go_details(n))
            self._cards_by_name[name] = card
            container.add_widget(card)

        if self._pending_cards:
            Clock.schedule_once(self._add_menu_batch, 0)
        else:
            self._batch_mode = False
            Clock.schedule_once(self._reorder_and_layout, 0)

    def _reorder_and_layout(self, dt):
        container = self.ids.menu_container

        ordered_names = sorted(self._cards_by_name.keys(), key=lambda x: x.lower())

        # ✅ Only reorder if actually needed
        current_order = [getattr(card, "name", "") for card in container.children]
        desired_order = list(reversed(ordered_names))  # because Kivy reverses children

        if current_order == desired_order:
            self.update_menu_layout()
            return

        container.clear_widgets()

        for name in ordered_names:
            container.add_widget(self._cards_by_name[name])

        self.update_menu_layout()

    def update_menu_layout(self, *args):
        grid = self.ids.menu_container
        scroll = self.ids.scroll_view

        cards = [child for child in grid.children if isinstance(child, CategoryCard)]
        if not cards:
            return

        total_cards = len(cards)

        pad = dp(20)
        gap = dp(20)
        min_card_width = dp(260)

        cols = max(2, int((scroll.width - 2 * pad + gap) // (min_card_width + gap)))
        cols = min(cols, total_cards)

        rows = ceil(total_cards / cols)

        usable_width = scroll.width - 2 * pad - gap * (cols - 1)
        card_width = usable_width / cols
        card_height = card_width * 1
        icon_size = card_height * 0.75

        grid.cols = cols
        grid.padding = [pad, pad]
        grid.spacing = [gap, gap]
        grid.height = 2 * pad + rows * card_height + max(0, rows - 1) * gap

        for card in cards:
            card.card_height = card_height
            card.icon_size = icon_size

    def go_details(self, name):
        self.manager.selected_category = name
        self.manager.last_screen = "menu"
        self.manager.current = "details"
