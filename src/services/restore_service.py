import json

from src.services.data_service import add_local_topic_and_steps


def restore_backup(app, backup_path, restore_backup_file):
    try:
        cache_file = restore_backup_file(backup_path)

        print(f"✅ Restored backup: {backup_path}")

        with open(cache_file, "r", encoding="utf-8") as f:
            restored_data = json.load(f)

        topics = restored_data.get("topics", [])
        steps = restored_data.get("steps", [])

        if isinstance(topics, dict):
            topics = list(topics.values())

        if isinstance(steps, dict):
            steps = list(steps.values())

        restored_topics = [t for t in topics if isinstance(t, dict)]
        restored_steps = [s for s in steps if isinstance(s, dict)]

        restored_count = 0
        skipped_count = 0

        existing_topic_ids = {
            str(t.get("Topic_ID") or "").strip().lower()
            for t in app.APP_DATA.get("topics", [])
            if isinstance(t, dict)
        }

        for topic in restored_topics:
            tid = str(topic.get("Topic_ID") or "").strip()

            if not tid:
                skipped_count += 1
                continue

            norm_tid = tid.lower()

            if norm_tid in existing_topic_ids:
                print(f"↪ Skipping duplicate topic during restore: {tid}")
                skipped_count += 1
                continue

            topic["source"] = "user"

            topic_steps = [
                s for s in restored_steps
                if str(s.get("Topic_ID") or "").strip().lower() == norm_tid
            ]

            try:
                add_local_topic_and_steps(topic, topic_steps)
                existing_topic_ids.add(norm_tid)
                restored_count += 1
            except Exception as e:
                print(f"⚠ Skipped topic {tid}: {e}")
                skipped_count += 1

        print(f"✅ Restored {restored_count} topics as LOCAL content")
        print(f"↪ Skipped {skipped_count} duplicate / invalid topics")

        app.refresh_all()

    except Exception as e:
        print(f"❌ Restore failed: {e}")
