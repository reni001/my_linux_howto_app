from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup

from src.ui.styled_popup import create_popup_container


def show_promotion_dialog(app, data, duplicate, on_confirm):

    title = data.get("Title", "this topic")

    if duplicate:
        dup_title = duplicate.get("Title", "")
        dup_cat = duplicate.get("Category", "")
        dup_sub = duplicate.get("Subcategory", "")
        dup_id = duplicate.get("Topic_ID", "")

        message = (
            f"Possible duplicate detected.\n\n"
            f"Local topic:\n{title}\n\n"
            f"Existing official topic:\n"
            f"{dup_title}\n"
            f"Category: {dup_cat}\n"
            f"Subcategory: {dup_sub}\n"
            f"Topic_ID: {dup_id}\n\n"
            f"Do you want to promote it anyway?"
        )
        popup_title = "Possible Duplicate"
        confirm_text = "PROMOTE ANYWAY"

    else:
        message = f"Promote this topic to official content?\n\n{title}"
        popup_title = "Promote Topic"
        confirm_text = "PROMOTE"

    root = create_popup_container()

    inner = BoxLayout(
        orientation="vertical",
        padding=[20, 15, 20, 20],
        spacing=15,
        size_hint=(0.95, 0.95),
        pos_hint={"center_x": 0.5, "center_y": 0.5},
    )

    inner.add_widget(Label(
        text=f"[b]{popup_title}[/b]",
        markup=True,
        font_size="18sp",
        color=app.COLOR_WHITE,
    ))

    inner.add_widget(Label(
        text=message,
        halign="center",
    ))

    btn_box = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

    btn_yes = Button(
        text=confirm_text,
        background_normal="",
        background_color=app.COLOR_BLUE_MEDIUM,
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
        size_hint=(0.7, 0.5),
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
