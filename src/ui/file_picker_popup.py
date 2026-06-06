from pathlib import Path

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView
from kivy.metrics import dp

from src.ui.styled_popup import create_popup_container
from src.ui.theme import COLOR_WHITE, COLOR_GREY_DARK, COLOR_BLUE_MEDIUM


def open_file_picker(title, callback, filters=("*.json",), start_path=None):
    """
    Generic file picker popup (themed)
    callback(path) will be called when a file is selected
    """

    root = create_popup_container()

    inner = BoxLayout(
        orientation="vertical",
        padding=[dp(20), dp(15), dp(20), dp(20)],
        spacing=dp(12),
        size_hint=(0.95, 0.95),
        pos_hint={"center_x": 0.5, "center_y": 0.5},
    )

    # ✅ TITLE
    title_label = Label(
        text=f"[b]{title}[/b]",
        markup=True,
        color=COLOR_WHITE,
        font_size="18sp",
        size_hint_y=None,
        height=dp(30),
    )

    # ✅ FILE CHOOSER (bigger text!)
    chooser = FileChooserListView(
        filters=list(filters),
        path=start_path or str(Path.home()),
        size_hint_y=1,
    )

    # ✅ BUTTON ROW
    btn_row = BoxLayout(
        size_hint_y=None,
        height=dp(44),     # ✅ fixed compact size
        spacing=dp(10),
    )

    btn_select = Button(
        text="Select",
        background_normal="",
        background_color=COLOR_BLUE_MEDIUM,
        color=COLOR_WHITE,
        font_size="15sp",
    )

    btn_cancel = Button(
        text="Cancel",
        background_normal="",
        background_color=COLOR_GREY_DARK,
        color=COLOR_WHITE,
        font_size="15sp",
    )

    btn_row.add_widget(btn_select)
    btn_row.add_widget(btn_cancel)

    inner.add_widget(title_label)
    inner.add_widget(chooser)
    inner.add_widget(btn_row)

    root.add_widget(inner)

    popup = Popup(
        title="",
        content=root,
        size_hint=(0.7, 0.75),
        background="",
        background_color=(0, 0, 0, 0),
        separator_height=0,
    )

    def do_select(*_):
        if chooser.selection:
            callback(Path(chooser.selection[0]))
        popup.dismiss()

    def do_cancel(*_):
        popup.dismiss()

    btn_select.bind(on_release=do_select)
    btn_cancel.bind(on_release=do_cancel)

    popup.open()
