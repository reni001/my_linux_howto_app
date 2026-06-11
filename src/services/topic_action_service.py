from src.ui.dialogs.confirm_dialog import show_confirm_dialog
from src.ui.dialogs.promotion_dialog import show_promotion_dialog
from src.services.topic_service import do_promote_topic, do_demote_topic

def find_official_duplicate(app, data):
    wanted_cat = str(data.get("Category") or "").strip().lower()
    wanted_sub = str(data.get("Subcategory") or "").strip().lower()
    wanted_title = str(data.get("Title") or "").strip().lower()

    for topic in app.APP_DATA.get("topics", []):
        if topic.get("source") == "user":
            continue

        if (
            str(topic.get("Category") or "").strip().lower() == wanted_cat and
            str(topic.get("Subcategory") or "").strip().lower() == wanted_sub and
            str(topic.get("Title") or "").strip().lower() == wanted_title
        ):
            return topic

    return None


def promote_topic(app, data):

    duplicate = find_official_duplicate(app, data)

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
