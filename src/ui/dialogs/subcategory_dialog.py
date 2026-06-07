from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior

from src.ui.styled_popup import create_popup_container
from src.ui.file_picker_popup import open_file_picker

from src.services.subcategory_service import (
    load_subcategories,
    delete_subcategory_safe,
    is_subcategory_used,
    count_subcategory_usage,   # ✅ ADD THIS
    upsert_subcategory,
    apply_subcategory_change,
)

from src.services.icon_service import copy_icon_to_core


# ----------------------------
# BUTTON
# ----------------------------
class IconButton(ButtonBehavior, Image):
    pass


# ----------------------------
# DELETE HANDLER
# ----------------------------
def handle_delete(app, name, popup):
    success, reason = delete_subcategory_safe(name)

    if success:
        popup.dismiss()
        show_subcategory_dialog(app)
        return

    # ❌ cannot delete → inform user
    Popup(
        title="Cannot Delete",
        content=Label(
            text=f"'{name}' is used and cannot be deleted.\nYou can edit it instead."
        ),
        size_hint=(0.4, 0.3)
    ).open()


# ----------------------------
# MAIN DIALOG
# ----------------------------
def show_subcategory_dialog(app):

    root = create_popup_container()

    inner = BoxLayout(
        orientation="vertical",
        padding=[15, 8, 15, 12],
        spacing=8,
        size_hint=(0.95, 0.95),
        pos_hint={"center_x": 0.5, "center_y": 0.5}
    )

    inner.add_widget(Label(
        text="[b]Manage Subcategories[/b]",
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

    subs = load_subcategories()

    if not subs:
        container.add_widget(Label(
            text="No subcategories yet",
            size_hint_y=None,
            height=dp(40)
        ))
    else:
        for sub in subs:

            row = BoxLayout(
                size_hint_y=None,
                height=dp(52),
                spacing=10,
                padding=[5, 5]
            )

            icon_name = sub.get("icon") or "howtolinux-icon.png"

            row.add_widget(Image(
                source=app.get_icon_path(icon_name),
                size_hint=(None, None),
                size=(dp(40), dp(40)),
                fit_mode="contain"
            ))

            usage = count_subcategory_usage(sub["name"])

            display_name = sub["name"]
            if usage > 0:
                display_name = f"{display_name} ({usage})"

            row.add_widget(Label(
                text=display_name,
                halign="left",
                valign="middle"
            ))

            # ✅ EDIT BUTTON
            btn_edit = IconButton(
                source=app.get_icon_path("edit.png"),
                size_hint=(None, None),
                size=(dp(28), dp(28))
            )

            btn_edit.bind(
                on_release=lambda instance, item=dict(sub): show_edit_subcategory_dialog(app, popup, item)
            )

            row.add_widget(btn_edit)

            # ✅ DELETE BUTTON
            btn_del = IconButton(
                source=app.get_icon_path("delete.png"),
                size_hint=(None, None),
                size=(dp(28), dp(28))
            )

            # ✅ check usage
            is_used = is_subcategory_used(sub["name"])

            btn_del.disabled = is_used
            btn_del.opacity = 0.3 if is_used else 1

            btn_del.bind(
                on_release=lambda instance, name=sub["name"]: handle_delete(app, name, popup)
            )

            row.add_widget(btn_del)

            container.add_widget(row)

    scroll.add_widget(container)
    inner.add_widget(scroll)

    # ✅ ADD BUTTON
    btn_add = Button(
        text="Add Subcategory",
        size_hint_y=None,
        height=dp(45),
        background_normal='',
        background_color=app.COLOR_GREEN,
        color=app.COLOR_WHITE
    )

    btn_add.bind(on_release=lambda x: show_edit_subcategory_dialog(app, popup, None))

    inner.add_widget(btn_add)

    root.add_widget(inner)

    popup = Popup(
        title="",
        content=root,
        size_hint=(0.7, 0.7),
        background="",
        background_color=(0, 0, 0, 0),
        separator_height=0
    )

    popup.open()


# ----------------------------
# EDIT / ADD DIALOG
# ----------------------------
def show_edit_subcategory_dialog(app, parent_popup, sub):

    root = create_popup_container()

    inner = BoxLayout(
        orientation="vertical",
        padding=[20, 15, 20, 20],
        spacing=10,
        size_hint=(0.95, 0.95),
        pos_hint={"center_x": 0.5, "center_y": 0.5}
    )

    edit_mode = sub is not None

    old_name = sub["name"] if sub else ""
    old_icon = sub["icon"] if sub else "howtolinux-icon.png"

    title = "Edit Subcategory" if edit_mode else "Add Subcategory"

    inner.add_widget(Label(
        text=f"[b]{title}[/b]",
        markup=True,
        font_size="16sp",
        size_hint_y=None,
        height=dp(30),
        color=app.COLOR_WHITE
    ))

    name_input = TextInput(
        text=old_name,
        hint_text="Subcategory name",
        multiline=False,
        size_hint_y=None,
        height=dp(40)
    )

    preview = Image(
        source=app.get_icon_path(old_icon),
        size_hint=(None, None),
        size=(dp(42), dp(42)),
        pos_hint={"center_x": 0.5},
        fit_mode="contain"
    )

    selected_icon = {"filename": old_icon}

    def pick_icon():
        def on_selected(path):
            filename = copy_icon_to_core(str(path))
            selected_icon["filename"] = filename
            preview.source = app.get_icon_path(filename)

        open_file_picker(
            title="Select Icon",
            callback=on_selected,
            filters=("*.png", "*.jpg", "*.jpeg", "*.webp")
        )

    btn_browse = Button(
        text="Choose Icon",
        size_hint_y=None,
        height=dp(40),
        background_normal='',
        background_color=app.COLOR_BLUE_MEDIUM,
        color=app.COLOR_WHITE
    )

    btn_browse.bind(on_release=lambda x: pick_icon())

    btn_save = Button(
        text="SAVE",
        size_hint_y=None,
        height=dp(45),
        background_normal='',
        background_color=app.COLOR_GREEN,
        color=app.COLOR_WHITE
    )

    btn_cancel = Button(
        text="Cancel",
        size_hint_y=None,
        height=dp(40),
        background_normal='',
        background_color=app.COLOR_GREY_DARK,
        color=app.COLOR_WHITE
    )

    inner.add_widget(name_input)
    inner.add_widget(preview)
    inner.add_widget(btn_browse)
    inner.add_widget(btn_save)
    inner.add_widget(btn_cancel)

    root.add_widget(inner)

    popup = Popup(
        title="",
        content=root,
        size_hint=(0.55, 0.5),
        background="",
        background_color=(0, 0, 0, 0),
        separator_height=0
    )

    def do_save(instance):
        new_name = name_input.text.strip()
        new_icon = selected_icon["filename"]

        if not new_name:
            return

        if edit_mode:
            apply_subcategory_change(app, old_name, new_name, new_icon)
        else:
            upsert_subcategory(new_name, new_icon)

        popup.dismiss()

        if parent_popup:
            parent_popup.dismiss()

        app.fetch_database()
        show_subcategory_dialog(app)

    btn_save.bind(on_release=do_save)
    btn_cancel.bind(on_release=lambda x: popup.dismiss())

    popup.open()
