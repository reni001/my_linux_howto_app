from kivy.clock import Clock

from src.utils.runtime_paths import get_runtime_paths
from src.services.icon_service import (
    copy_user_icon_to_official,
    copy_official_icon_to_user_icons,
    delete_official_icon_if_unused,
)
from src.services.editor_service import delete_topic_from_firebase
from src.services.firebase_service import add_topic_to_firebase, add_step_to_firebase


def do_promote_topic(app, data):
    """
    Promote a local topic to official Firebase content.
    Keeps UI-related refresh/navigation through the passed app instance.
    """
    print(f"🚀 Promoting topic: {data.get('Title')}")

    try:
        local_topic_id = str(data.get("Topic_ID") or "")

        # 1. Copy icon from user_icons → official icons
        icon_filename = data.get("Topic_Icon", "")
        icon_filename = copy_user_icon_to_official(icon_filename)

        # 2. Prepare official topic payload
        topic = dict(data)
        topic["Topic_Icon"] = icon_filename

        # remove local-only fields
        for key in ["source", "_key", "local_only"]:
            topic.pop(key, None)

        # Let Firebase assign a fresh official Topic_ID
        topic.pop("Topic_ID", None)

        # 3. Upload topic
        topic_key, new_topic_id = add_topic_to_firebase(topic)

        # 4. Upload steps
        for step in app.APP_DATA.get("steps", []):
            if str(step.get("Topic_ID")) == local_topic_id:
                payload = dict(step)
                for key in ["source", "_key", "local_only"]:
                    payload.pop(key, None)
                payload["Topic_ID"] = str(new_topic_id)
                add_step_to_firebase(payload)

        # 5. Remove local version after successful publish
        app.delete_local_topic(local_topic_id)

        # 6. Remove user icon after successful promote
        original_user_icon_name = str(data.get("Topic_Icon") or "")
        if original_user_icon_name:
            paths = get_runtime_paths()
            user_icon_path = paths["assets"] / "user_icons" / original_user_icon_name

            try:
                if user_icon_path.exists():
                    user_icon_path.unlink()
                    print(f"✅ Removed user icon after promote: {user_icon_path}")
                else:
                    print(f"ℹ️ No user icon to remove after promote: {user_icon_path}")
            except Exception as e:
                print(f"⚠️ Could not delete user icon after promote: {e}")

        print(f"✅ Promotion complete → official Topic_ID: {new_topic_id}")
        app.refresh_data_only()

    except Exception as e:
        print(f"❌ Promotion failed: {e}")


def do_demote_topic(app, data):
    """
    Demote an official Firebase topic into a local-only topic.
    Keeps UI-related refresh/navigation through the passed app instance.
    """
    topic_id = str(data.get("Topic_ID") or "")
    topic_key = str(data.get("_key") or "")
    category = data.get("Category", "")

    try:
        # 1. collect steps
        steps = [
            dict(s) for s in app.APP_DATA.get("steps", [])
            if str(s.get("Topic_ID") or "") == topic_id
        ]

        # 2. copy icon to user_icons
        icon_name = str(data.get("Topic_Icon") or "")
        new_icon_name = copy_official_icon_to_user_icons(icon_name)

        # 3. create local topic
        local_topic = dict(data)
        local_topic["Topic_Icon"] = new_icon_name
        local_topic["source"] = "user"
        local_topic["local_only"] = True
        local_topic["_key"] = topic_id
        local_topic["Topic_ID"] = topic_id

        app.update_local_topic(topic_id, local_topic, steps)

        # 4. delete from Firebase
        delete_topic_from_firebase(topic_key, topic_id)

        # 5. delete icon if unused
        delete_official_icon_if_unused(app.APP_DATA, icon_name, topic_id)

        # 6. refresh + restore category
        app.refresh_data_only()

        app.sm.current = "menu"

        def _restore(_dt):
            try:
                detail = app.root.get_screen("details")
                detail.header_title = category
                detail.show_category(category)
                app.root.current = "details"
            except Exception as e:
                print("DEBUG restore failed:", e)

        Clock.schedule_once(_restore, 0.4)

        print(f"✅ Topic demoted: {topic_id}")

    except Exception as e:
        print("❌ Demotion failed:", e)
