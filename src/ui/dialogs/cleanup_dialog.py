from threading import Thread

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

from src.services.icon_cleanup import find_unused_icons, clean_unused_icons
from src.ui.styled_popup import create_popup_container
from src.utils.runtime_paths import get_runtime_paths


def show_cleanup_dialog(app):
    root = create_popup_container()

    inner = BoxLayout(
        orientation="vertical",
        padding=[20, 15, 20, 20],
        spacing=15,
        size_hint=(0.95, 0.95),
        pos_hint={"center_x": 0.5, "center_y": 0.5},
    )

    title_label = Label(
        text="[b]Cleanup Unused Icons[/b]",
        markup=True,
        font_size="18sp",
        color=app.COLOR_WHITE,
        size_hint_y=None,
        height=dp(28),
    )

    scroll = ScrollView()

    message_label = Label(
        text=app.txt("Clean all unused icons?"),
        halign="left",
        valign="top",
        size_hint_y=None,
        markup=True,
    )

    def update_size(*_):
        message_label.text_size = (scroll.width - dp(20), None)

    scroll.bind(size=update_size)
    message_label.bind(
        texture_size=lambda instance, size: setattr(instance, "height", max(size[1], dp(40)))
    )

    scroll.add_widget(message_label)

    btn_box = BoxLayout(size_hint_y=None, height="40dp", spacing=10)

    btn_yes = Button(
        text="CLEAN",
        background_normal="",
        background_color=app.COLOR_BLUE_MEDIUM,
        color=app.COLOR_WHITE,
    )

    btn_cancel = Button(
        text="Cancel",
        background_normal="",
        background_color=app.COLOR_GREY_DARK,
        color=app.COLOR_WHITE,
    )

    btn_box.add_widget(btn_yes)
    btn_box.add_widget(btn_cancel)

    inner.add_widget(title_label)
    inner.add_widget(scroll)
    inner.add_widget(btn_box)
    root.add_widget(inner)

    popup = Popup(
        title="",
        content=root,
        size_hint=(0.7, 0.6),
        background="",
        background_color=(0, 0, 0, 0),
        separator_height=0,
    )

    def run_cleanup(_instance):
        message_label.text = app.txt("Scanning…")
        message_label.texture_update()

        btn_yes.disabled = True
        btn_cancel.disabled = True

        def do_scan():
            try:
                icons, screenshots = find_unused_icons(app.APP_DATA)

                def show_preview(_dt):
                    total = len(icons) + len(screenshots)

                    if total == 0:
                        message_label.text = app.txt("✔ No unused files found")
                        message_label.texture_update()

                        btn_box.clear_widgets()

                        btn_close = Button(
                            text="CLOSE",
                            background_normal="",
                            background_color=app.COLOR_BLUE_MEDIUM,
                            color=app.COLOR_WHITE,
                        )
                        btn_close.bind(on_release=lambda x: popup.dismiss())
                        btn_box.add_widget(btn_close)
                        return

                    icon_list = "\n".join(
                        f"[font=RobotoMono]{name}[/font]"
                        for name in icons[:20]
                    )
                    screen_list = "\n".join(
                        f"[font=RobotoMono]{name}[/font]"
                        for name in screenshots[:20]
                    )

                    more_icons = "\n..." if len(icons) > 20 else ""
                    more_screens = "\n..." if len(screenshots) > 20 else ""

                    preview_text = app.txt(
                        f"[b]Unused Icons ({len(icons)})[/b]\n"
                        f"{icon_list}{more_icons}\n\n"
                        f"[b]Unused Screenshots ({len(screenshots)})[/b]\n"
                        f"{screen_list}{more_screens}\n\n"
                        f"[color=#aaaaaa]Proceed with deletion?[/color]"
                    )

                    message_label.text = preview_text
                    message_label.texture_update()

                    btn_box.clear_widgets()

                    btn_delete = Button(
                        text="DELETE",
                        background_normal="",
                        background_color=app.COLOR_RED,
                        color=app.COLOR_WHITE,
                    )

                    btn_cancel2 = Button(
                        text="Cancel",
                        background_normal="",
                        background_color=app.COLOR_GREY_DARK,
                        color=app.COLOR_WHITE,
                    )

                    btn_box.add_widget(btn_delete)
                    btn_box.add_widget(btn_cancel2)

                    def do_delete(_instance2):
                        # keep backup for undo
                        app._last_deleted_backup = (icons[:], screenshots[:])

                        result = clean_unused_icons(app.APP_DATA)

                        message_label.text = app.txt(
                            f"✔ Deleted:\n\n"
                            f"{result['icons']} icons\n"
                            f"{result['screenshots']} screenshots"
                        )
                        message_label.texture_update()

                        btn_box.clear_widgets()

                        btn_undo = Button(
                            text="UNDO",
                            background_normal="",
                            background_color=app.COLOR_ORANGE,
                            color=app.COLOR_WHITE,
                        )

                        btn_close = Button(
                            text="CLOSE",
                            background_normal="",
                            background_color=app.COLOR_BLUE_MEDIUM,
                            color=app.COLOR_WHITE,
                        )

                        btn_undo.bind(on_release=lambda x: undo_cleanup(app, popup, message_label, btn_box))
                        btn_close.bind(on_release=lambda x: popup.dismiss())

                        btn_box.add_widget(btn_undo)
                        btn_box.add_widget(btn_close)

                    btn_delete.bind(on_release=do_delete)
                    btn_cancel2.bind(on_release=lambda x: popup.dismiss())

                Clock.schedule_once(show_preview)

            except Exception as e:
                def show_error(_dt):
                    message_label.text = app.txt(f"Error: {e}")
                    message_label.texture_update()

                Clock.schedule_once(show_error)

        Thread(target=do_scan, daemon=True).start()

    btn_yes.bind(on_release=run_cleanup)
    btn_cancel.bind(on_release=lambda x: popup.dismiss())

    popup.open()


def undo_cleanup(app, popup=None, message_label=None, btn_box=None):
    """
    Restore the last deleted icon/screenshot file placeholders.
    Note: this restores placeholder files, matching your original behaviour.
    """
    if not hasattr(app, "_last_deleted_backup"):
        return

    icons, screenshots = app._last_deleted_backup
    paths = get_runtime_paths()

    restored = 0

    for name in icons:
        target = paths["assets"] / "icons" / name
        if not target.exists():
            target.touch()
            restored += 1

    for name in screenshots:
        target = paths["assets"] / "screenshots" / name
        if not target.exists():
            target.touch()
            restored += 1

    if message_label is not None:
        message_label.text = app.txt(f"↩ Restored approx {restored} files")
        message_label.texture_update()

    if btn_box is not None:
        btn_box.clear_widgets()

        btn_close = Button(
            text="CLOSE",
            background_normal="",
            background_color=app.COLOR_BLUE_MEDIUM,
            color=app.COLOR_WHITE,
        )
        btn_close.bind(on_release=lambda x: popup.dismiss() if popup else None)
        btn_box.add_widget(btn_close)
