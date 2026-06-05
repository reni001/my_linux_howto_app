from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.widget import Widget

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


    name_lbl = Label(
        text=f"[b]{name}[/b]",
        markup=True,
        font_size="24sp",
        halign="left",
        valign="middle",
        size_hint_y=None,
        height=35
    )
    text_block.add_widget(name_lbl)


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

    # ✅ container for formatted changelog
    changelog_box = BoxLayout(
        orientation='vertical',
        size_hint_y=None,
        spacing=8,
    )
    changelog_box.bind(minimum_height=changelog_box.setter('height'))

    icon_map = {
        "features": "feature.png",
        "improvements": "improvement.png",
        "fixes": "fix.png",
        "sync & update": "improvement.png",
    }

    # ✅ visual levels (latest vs older)
    LATEST_VERSION_COLOR = (1, 1, 1, 0.98)
    OLDER_VERSION_COLOR = (0.82, 0.88, 0.95, 0.78)

    LATEST_SECTION_COLOR = (0.65, 0.85, 1, 0.95)
    OLDER_SECTION_COLOR = (0.65, 0.85, 1, 0.72)

    LATEST_TEXT_COLOR = (0.8, 0.88, 0.95, 0.95)
    OLDER_TEXT_COLOR = (0.8, 0.88, 0.95, 0.70)

    def is_version_header(text):
        lower = text.lower().strip()
        return lower.startswith("version") or lower.startswith("dev version")

    # -----------------------------
    # 1) Split changelog into version blocks
    # -----------------------------
    version_blocks = []
    current_header = None
    current_lines = []

    for raw in change.split("\n"):
        line = raw.strip()
        if not line:
            continue

        if is_version_header(line):
            if current_header is not None:
                version_blocks.append((current_header, current_lines))
            current_header = line
            current_lines = []
        else:
            current_lines.append(line)

    if current_header is not None:
        version_blocks.append((current_header, current_lines))

    # -----------------------------
    # 2) helper to build one version body
    # -----------------------------
    def build_version_body(lines, is_latest_block):
        body = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=6,
        )
        body.bind(minimum_height=body.setter('height'))

        for line in lines:
            lower_line = line.lower().strip()

            matched = None
            for key in icon_map:
                if key in lower_line:
                    matched = key
                    break

            # section header
            if matched:
                row = BoxLayout(
                    size_hint_y=None,
                    height=dp(28),
                    spacing=dp(8),
                )

                row.add_widget(Image(
                    source=get_icon_path(icon_map[matched]),
                    size_hint=(None, None),
                    size=(dp(22), dp(22)),
                    pos_hint={"center_y": 0.5},
                ))

                lbl = Label(
                    text=f"[b]{line}[/b]",
                    markup=True,
                    font_size="14sp",
                    size_hint_x=1,
                    size_hint_y=None,
                    halign="left",
                    valign="middle",
                    color=LATEST_SECTION_COLOR if is_latest_block else OLDER_SECTION_COLOR,
                )
                lbl.bind(
                    size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                    texture_size=lambda i, v: setattr(i, "height", v[1])
                )

                row.add_widget(lbl)
                body.add_widget(row)

            # normal text
            else:
                lbl = Label(
                    text=line,
                    size_hint_y=None,
                    halign="left",
                    valign="top",
                    color=LATEST_TEXT_COLOR if is_latest_block else OLDER_TEXT_COLOR,
                )
                lbl.padding = (dp(26), 0)
                lbl.bind(
                    size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
                    texture_size=lambda i, v: setattr(i, "height", v[1])
                )
                body.add_widget(lbl)

        return body

    # -----------------------------
    # 3) render version blocks
    #    latest expanded, older collapsed
    # -----------------------------
    for idx, (version_header, version_lines) in enumerate(version_blocks):
        is_latest_block = (idx == 0)

        # divider between version blocks
        if idx > 0:
            divider_lbl = Label(
                text="[color=#ffaa55]--------------------------------[/color]",
                markup=True,
                size_hint_y=None,
                height=dp(12),
                halign="center",
                valign="middle",
            )

            divider_lbl.bind(
                size=lambda s, w: setattr(s, "text_size", w)
            )
            changelog_box.add_widget(divider_lbl)
            changelog_box.add_widget(
                Widget(size_hint_y=None, height=dp(8))   # ✅ creates gap after line
            )

        # smaller spacing than before
        changelog_box.add_widget(
            Widget(size_hint_y=None, height=dp(3))
        )

        # each version gets its own section
        section = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(2),   # ✅ smaller internal spacing
        )
        section.bind(minimum_height=section.setter("height"))

        # header row
        header_row = BoxLayout(
            size_hint_y=None,
            height=dp(40),   # slightly tighter
            spacing=dp(10),
        )

        header_row.add_widget(Image(
            source=get_icon_path("version.png"),
            size_hint=(None, None),
            size=(dp(26), dp(26)),
            pos_hint={"center_y": 0.5},
        ))

        header_lbl = Label(
            text=f"[b]{version_header}[/b]",
            markup=True,
            font_size="18sp",
            size_hint_x=1,
            size_hint_y=None,
            halign="left",
            valign="middle",
            color=LATEST_VERSION_COLOR if is_latest_block else OLDER_VERSION_COLOR,
        )
        header_lbl.bind(
            size=lambda s, w: setattr(s, 'text_size', (w[0], None)),
            texture_size=lambda i, v: setattr(i, "height", v[1])
        )

        header_row.add_widget(header_lbl)

        toggle_btn = None
        if not is_latest_block:
            toggle_btn = Button(
                text="+",
                size_hint=(None, None),
                size=(dp(32), dp(32)),
                background_normal='',
                background_down='',
                background_color=(1, 1, 1, 0.08),
                color=(1, 1, 1, 0.9),
                bold=True
            )
            header_row.add_widget(toggle_btn)

        section.add_widget(header_row)

        # build body
        version_body = build_version_body(version_lines, is_latest_block)

        # latest stays open
        if is_latest_block:
            section.add_widget(version_body)

        else:
            def toggle_body(_btn, sec=section, body=version_body, btn=toggle_btn):
                expanded = (body.parent is sec)

                if expanded:
                    sec.remove_widget(body)
                    btn.text = "+"
                else:
                    sec.add_widget(body)
                    btn.text = "−"

            toggle_btn.bind(on_release=toggle_body)

        changelog_box.add_widget(section)


    scroll_content.add_widget(changelog_box)

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
