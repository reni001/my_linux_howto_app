from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
from src.ui.theme import COLOR_BG_DARK, COLOR_ORANGE


def create_popup_container():
    root_layout = FloatLayout()

    RADIUS = 22
    BORDER_W = 2

    with root_layout.canvas.before:
        Color(*COLOR_BG_DARK)
        root_layout.bg = RoundedRectangle(
            pos=root_layout.pos,
            size=root_layout.size,
            radius=[RADIUS]
        )

    with root_layout.canvas.after:
        Color(*COLOR_ORANGE)
        root_layout.border = Line(
            rounded_rectangle=(
                root_layout.x + 1,
                root_layout.y + 1,
                root_layout.width - 2,
                root_layout.height - 2,
                RADIUS
            ),
            width=BORDER_W
        )

    def _update(*_):
        root_layout.bg.pos = root_layout.pos
        root_layout.bg.size = root_layout.size
        root_layout.border.rounded_rectangle = (
            root_layout.x + 1,
            root_layout.y + 1,
            root_layout.width - 2,
            root_layout.height - 2,
            RADIUS
        )

    root_layout.bind(pos=_update, size=_update)

    return root_layout
