from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from src.services.backup_service import get_backups
from src.ui.styled_popup import create_popup_container


def show_restore_backup_dialog(app):
    backups = get_backups()
    print("DEBUG backups:", backups)

    root = create_popup_container()

    inner = BoxLayout(
        orientation="vertical",
        padding=[20, 15, 20, 20],
        spacing=10,
        size_hint=(0.95, 0.95),
        pos_hint={"center_x": 0.5, "center_y": 0.5}
    )

    inner.add_widget(Label(
        text="[b]Restore Backup[/b]",
        markup=True,
        font_size="16sp",
        size_hint_y=None,
        height=dp(30),
        color=app.COLOR_WHITE
    ))

    scroll = ScrollView(size_hint=(1, 1))

    container = BoxLayout(
        orientation="vertical",
        size_hint_y=None,
        spacing=8
    )
    container.bind(minimum_height=container.setter("height"))

    if not backups:
        container.add_widget(Label(
            text="No backups found",
            size_hint_y=None,
            height=dp(40),
            color=app.COLOR_WHITE
        ))
    else:
        for backup_file in backups[:20]:
            btn = Button(
                text=backup_file.name,
                size_hint_y=None,
                height=dp(45),
                background_normal='',
                background_color=app.COLOR_BLUE_MEDIUM,
                color=app.COLOR_WHITE
            )
            btn.bind(on_release=lambda btn, path=backup_file: app._confirm_restore(path))
            container.add_widget(btn)

    scroll.add_widget(container)
    inner.add_widget(scroll)

    btn_close = Button(
        text="Close",
        size_hint_y=None,
        height=dp(42),
        background_normal='',
        background_color=app.COLOR_GREY_DARK,
        color=app.COLOR_WHITE
    )

    inner.add_widget(btn_close)

    root.add_widget(inner)

    popup = Popup(
        title="",
        content=root,
        size_hint=(0.75, 0.75),
        background="",
        background_color=(0, 0, 0, 0),
        separator_height=0
    )

    btn_close.bind(on_release=lambda x: popup.dismiss())

    popup.open()
