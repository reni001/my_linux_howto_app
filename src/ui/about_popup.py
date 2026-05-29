from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.app import App

from src.utils.icon_utils import get_icon_path
from src.ui.theme import COLOR_BG_DARK, COLOR_ORANGE, COLOR_ORANGE_SOFT


def show_about_popup(app):
    metadata = app.metadata

    name = metadata.get('app_name', 'Linux HowTo')
    version = metadata.get('version', '0.0.0')
    last_update = metadata.get('last update', 'unknown')
    dev_name = metadata.get('developer', '')
    desc = metadata.get('description', '')
    change = metadata.get('changelog', '').replace("\\n", "\n")

    RADIUS = 22
    BORDER_W = 2

    root_layout = FloatLayout()

    with root_layout.canvas.before:
        Color(*COLOR_BG_DARK)
        root_layout.bg = RoundedRectangle(pos=root_layout.pos, size=root_layout.size, radius=[RADIUS])

    with root_layout.canvas.after:
        Color(*COLOR_ORANGE)
        root_layout.border = Line(
            rounded_rectangle=(root_layout.x + 1, root_layout.y + 1,
                               root_layout.width - 2, root_layout.height - 2,
                               RADIUS),
            width=BORDER_W
        )

    def _sync_popup_bg(*_):
        root_layout.bg.pos = root_layout.pos
        root_layout.bg.size = root_layout.size
        root_layout.border.rounded_rectangle = (
            root_layout.x + 1, root_layout.y + 1,
            root_layout.width - 2, root_layout.height - 2,
            RADIUS
        )

    root_layout.bind(pos=_sync_popup_bg, size=_sync_popup_bg)

    outer = BoxLayout(
        orientation='vertical',
        padding=[20, 15, 20, 20],
        spacing=15,
        size_hint=(0.95, 0.95),
        pos_hint={"center_x": 0.5, "center_y": 0.5}
    )

    header = BoxLayout(orientation="horizontal", size_hint_y=None, height=110, spacing=20)

    text_block = BoxLayout(orientation="vertical", spacing=4)

    Label(
        text=f"[b]{name}[/b]",
        markup=True,
        font_size="28sp",
        halign="left",
        valign="middle",
        size_hint_y=None,
        height=35
    )

    text_block.add_widget(Label(text=f"Version {version}", size_hint_y=None, height=25))
    text_block.add_widget(Label(text=f"Last update: {last_update}", size_hint_y=None, height=25))
    text_block.add_widget(Label(text=f"[color=ffaa33]{dev_name}[/color]", markup=True, size_hint_y=None, height=25))

    header.add_widget(text_block)

    header.add_widget(Image(
        source=get_icon_path("howtolinux-icon.png"),
        size_hint=(None, None),
        size=(95, 95)
    ))

    outer.add_widget(header)

    divider = BoxLayout(size_hint_y=None, height=1)

    with divider.canvas.before:
        Color(*COLOR_ORANGE_SOFT)
        divider.line = Line(points=[])

    def update_line(*_):
        divider.line.points = [
            divider.x,
            divider.center_y,
            divider.right,
            divider.center_y
        ]

    divider.bind(pos=update_line, size=update_line)


    outer.add_widget(divider)

    scroll = ScrollView(size_hint=(1, 1), bar_width=8)

    scroll_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10, padding=[15, 10])
    scroll_content.bind(minimum_height=scroll_content.setter('height'))
    scroll_content.spacing = 10


    desc_label = Label(
        text=f"[i]{desc}[/i]",
        markup=True,
        halign="center",
        valign="top",
        size_hint_y=None,
    )

    desc_label.bind(
        width=lambda inst, val: setattr(inst, "text_size", (val, None)),
        texture_size=lambda inst, val: setattr(inst, "height", val[1])
    )

    scroll_content.add_widget(desc_label)

    scroll.add_widget(scroll_content)
    outer.add_widget(scroll)

    title_label = Label(
        text="[b]WHAT'S NEW[/b]",
        markup=True,
        size_hint_y=None,
        height=30
    )
    scroll_content.add_widget(title_label)

    changelog_label = Label(
        text=change,
        size_hint_y=None,
    )

    changelog_label.bind(
        width=lambda inst, val: setattr(inst, "text_size", (val, None)),
        texture_size=lambda inst, val: setattr(inst, "height", val[1]),
    )

    scroll_content.add_widget(changelog_label)

    # ✅ Buttons row
    btn_row = BoxLayout(size_hint_y=None, height=50, spacing=10)

    btn_close = Button(
        text="CLOSE",
        size_hint=(1, None),
        height=40,
        background_normal='',
        background_color=app.COLOR_BLUE_MEDIUM,
        color=app.COLOR_WHITE,
        bold=True
    )

    btn_row.add_widget(btn_close)

    # ✅ only add edit button in ADMIN mode
    if app.is_admin_mode():
        btn_edit = Button(
            size_hint=(None, None),
            size=(32, 32),
            background_normal=get_icon_path("edit.png"),
            background_down=get_icon_path("edit.png"),
            background_color=(1, 1, 1, 1),
            border=(0, 0, 0, 0),
            text=""
        )
        btn_row.add_widget(btn_edit)

    outer.add_widget(btn_row)

    popup = Popup(
        title="About the App",
        content=root_layout,
        size_hint=(0.9, 0.9),
        background="",
        background_color=(0, 0, 0, 0),
        separator_height=0
    )

    btn_close.bind(on_release=popup.dismiss)


    if app.is_admin_mode():
        def on_edit(_):
            app._open_app_info_from_popup(popup)

        btn_edit.bind(on_release=on_edit)


    root_layout.add_widget(outer)
    popup.open()
