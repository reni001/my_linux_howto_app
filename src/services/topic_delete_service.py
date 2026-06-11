from kivy.clock import Clock

from src.ui.dialogs.confirm_dialog import show_confirm_dialog
from src.services.editor_service import delete_topic_from_firebase
from src.services.icon_cleanup import delete_user_icon_if_unused


def delete_topic(app, data):
    topic_id = str(data.get("Topic_ID") or "")
    if not topic_id:
        return

    icon_name = str(data.get("Topic_Icon") or "")

    # -----------------------------
    # ✅ LOCAL DELETE
    # -----------------------------
    if data.get("source") == "user":

        def do_delete():
            try:
                app.backup_current_data()

                app.delete_local_topic(topic_id)
                delete_user_icon_if_unused(app.APP_DATA, icon_name, topic_id)
            except Exception as e:
                print(f"❌ Local delete failed: {e}")

        show_confirm_dialog(
            app,
            title="Delete Topic",
            message="Are you sure you want to delete this topic?",
            confirm_text="DELETE",
            confirm_color=app.COLOR_RED,
            on_confirm=do_delete,
        )

        return

    # -----------------------------
    # ✅ FIREBASE DELETE
    # -----------------------------
    node_key = str(data.get("_key") or "")

    def do_delete():
        try:
            app.backup_current_data()

            deleted_topics, deleted_steps = delete_topic_from_firebase(node_key, topic_id)
            print(f"✅ Deleted topics: {deleted_topics}, steps: {deleted_steps}")

            Clock.schedule_once(lambda dt: app.fetch_database(), 0.5)
            Clock.schedule_once(lambda dt: app.refresh_ui_data(), 0.5)

        except Exception as e:
            print(f"❌ Delete failed: {e}")

    show_confirm_dialog(
        app,
        title="Delete Topic",
        message="Are you sure you want to delete this topic?",
        confirm_text="DELETE",
        confirm_color=app.COLOR_RED,
        on_confirm=do_delete,
    )
