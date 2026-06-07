from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup

from src.ui.styled_popup import create_popup_container


def show_confirm_dialog(
    app,
    title="Confirm Action",
    message="Are you sure?",
    confirm_text="Confirm",
    confirm_color=None,
    on_confirm=None,
):

    root = create_popup_container()

    inner = BoxLayout(
        orientation="vertical",
        padding=[20, 15, 20, 20],
        spacing=15,
        size_hint=(0.95, 0.95),
        pos_hint={"center_x": 0.5, "center_y": 0.5},
    )

    inner.add_widget(Label(
        text=f"[b]{title}[/b]",
        markup=True,
        font_size="18sp",
        color=app.COLOR_WHITE,
    ))

    inner.add_widget(Label(
        text=message,
        color=app.COLOR_WHITE
    ))

    btn_box = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

    btn_yes = Button(
        text=confirm_text,
        background_normal="",
        background_color=confirm_color or app.COLOR_BLUE_MEDIUM,
        color=app.COLOR_WHITE,
    )

    btn_no = Button(
        text="Cancel",
        background_normal="",
        background_color=app.COLOR_GREY_DARK,
        color=app.COLOR_WHITE,
    )

    btn_box.add_widget(btn_yes)
    btn_box.add_widget(btn_no)
    inner.add_widget(btn_box)

    root.add_widget(inner)

    popup = Popup(
        title="",
        content=root,
        size_hint=(0.7, 0.4),
        background="",
        background_color=(0, 0, 0, 0),
        separator_height=0,
    )

    def confirm_action(_instance):
        popup.dismiss()
        if on_confirm:
            on_confirm()

    btn_yes.bind(on_release=confirm_action)
    btn_no.bind(on_release=lambda x: popup.dismiss())

    popup.open()
