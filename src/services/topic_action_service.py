from src.ui.dialogs.confirm_dialog import show_confirm_dialog
from src.ui.dialogs.promotion_dialog import show_promotion_dialog
from src.services.topic_service import do_promote_topic, do_demote_topic


def promote_topic(app, data):

    duplicate = app._find_official_duplicate(data)

    def do_promote():
        do_promote_topic(app, data)

    show_promotion_dialog(
        app,
        data,
        duplicate,
        on_confirm=do_promote
    )


def demote_topic(app, data):

    if str(data.get("source") or "") == "user":
        return

    def do_demote():
        do_demote_topic(app, data)

    show_confirm_dialog(
        app,
        title="Demote Topic",
        message="This will remove the topic from official content and make it local.\n\nContinue?",
        confirm_text="DEMOTE",
        confirm_color=app.COLOR_ORANGE,
        on_confirm=do_demote,
    )
