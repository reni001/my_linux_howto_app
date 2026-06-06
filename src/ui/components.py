from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.app import App
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.properties import (
    StringProperty, BooleanProperty, NumericProperty,
    ListProperty, DictProperty
)
from kivy.metrics import dp
from kivy.graphics import Rotate, PushMatrix, PopMatrix
from kivy.properties import BooleanProperty
from kivy.core.window import Window
from kivy.base import EventLoop


from src.utils.icon_utils import get_icon_path
from src.ui.theme import COLOR_ORANGE



class CategoryCard(ButtonBehavior, BoxLayout):
    name = StringProperty("")
    icon_source = StringProperty("")
    card_height = NumericProperty(dp(180))
    icon_size = NumericProperty(dp(100))


class EntryListItem(ButtonBehavior, BoxLayout):
    title = StringProperty("")
    desc = StringProperty("")
    icon_source = StringProperty("")
    data = DictProperty({})


class ClickableHeader(ButtonBehavior, BoxLayout):
    pass


class RotatableArrow(Image):
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.bind(angle=self._update_canvas, pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *args):
        self.canvas.before.clear()

        with self.canvas.before:
            PushMatrix()
            Rotate(angle=self.angle, origin=self.center)

        self.canvas.after.clear()
        with self.canvas.after:
            PopMatrix()


class ExpandableSection(BoxLayout):
    is_open = BooleanProperty(True)
    stored_widgets = ListProperty([])

    def __init__(self, title, icon, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, **kwargs)
        self.spacing = dp(8)
        app = App.get_running_app()

        # ---------- HEADER ----------
        self.header = ClickableHeader(
            orientation="horizontal",
            size_hint_y=None,
            height=app.FONT_SUBCATEGORY * 2.2,
            padding=[dp(10), dp(6)],
            spacing=dp(10)
        )

        # LEFT ICON
        self.header.add_widget(
            Image(
                source=get_icon_path(icon) if icon else get_icon_path("default.png"),
                size_hint=(None, None),
                size=(dp(26), dp(26))
            )
        )

        # TITLE (sub-category like APPLICATION / HARDWARE)
        self.title_label = Label(
            text=str(title).upper(),
            color=COLOR_ORANGE,
            bold=True,
            font_size=app.FONT_SUBCATEGORY,
            size_hint_x=None,
            halign="left",
            valign="middle"
        )

        # ✅ dynamic update when scaling changes
        app.bind(FONT_SUBCATEGORY=lambda instance, value: setattr(self.title_label, "font_size", value))

        # ✅ FIX: keep label compact like before
        self.title_label.bind(
            texture_size=lambda inst, val: setattr(inst, "width", val[0] + dp(10))
        )
        self.title_label.text_size = (None, None)

        self.header.add_widget(self.title_label)

        # ✅ SPACER → pushes arrow right (important!)
        self.header.add_widget(BoxLayout(size_hint_x=1))

        # RIGHT ARROW
        self.arrow = RotatableArrow(
            source=get_icon_path("down_arrow.png"),
            size_hint=(None, None),
            size=(dp(20), dp(20))
        )

        self.header.add_widget(self.arrow)

        self.header.bind(on_release=self.toggle)
        self.add_widget(self.header)

        # ---------- CONTENT ----------
        self.list_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(8)
        )
        self.list_box.bind(minimum_height=self.list_box.setter("height"))

        self.add_widget(self.list_box)

        # Resize section automatically
        self.bind(minimum_height=self.setter("height"))

    def add_entry(self, widget):
        self.stored_widgets.append(widget)
        if self.is_open:
            self.list_box.add_widget(widget)


    def toggle(self, *args):
        self.is_open = not self.is_open

        self.list_box.clear_widgets()

        if self.is_open:
            for w in self.stored_widgets:
                self.list_box.add_widget(w)
            self.arrow.angle = 0
        else:
            self.arrow.angle = 90

class HoverBehavior(object):
    hovered = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return

        pos = args[1]
        inside = self.collide_point(*self.to_widget(*pos))
        if inside != self.hovered:
            self.hovered = inside

class HoverRow(HoverBehavior, BoxLayout):
    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(40)
        self.spacing = dp(6)

        from kivy.graphics import Color, RoundedRectangle
        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 0)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])

        self.bind(
            pos=self.update_rect,
            size=self.update_rect,
            hovered=self.update_bg,
            selected=self.update_bg
        )

    def update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def update_bg(self, *args):
        if self.selected:
            self.bg_color.rgba = [0.75, 0.85, 1, 1]   # ✅ strong blue (selected)
        elif self.hovered:
            self.bg_color.rgba = [0.90, 0.93, 0.98, 1]  # ✅ light blue (hover)
        else:
            self.bg_color.rgba = [1, 1, 1, 0]


    def on_hover(self, *args):
        if self.hovered:
            self.bg_color.rgba = [0.90, 0.93, 0.98, 1]
        else:
            self.bg_color.rgba = [1, 1, 1, 0]

