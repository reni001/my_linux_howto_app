from kivy.uix.screenmanager import Screen
from kivy.app import App

from src.services.editor_service import add_step_to_firebase, is_admin_enabled
from src.ui.components import HoverRow, EntryListItem, ExpandableSection
#from src.utils.config import is_admin_enabled

class AddStepScreen(Screen):
    """
    Admin-only screen: add a Step tied to a Topic_ID.
    """
    topic_map = {}   # display_text -> topic_id

    def _txt(self, text: str) -> str:
        return f"[font=NotoSans]{text}[/font]"

    def on_pre_enter(self):
        if not is_admin_enabled():
            self.ids.status_label.text = self._txt("⚠️ Editor disabled (admin key missing).")
            self.ids.save_btn.disabled = True
            self.ids.add_step_btn.disabled = True
        else:
            self.ids.status_label.text = self._txt("")
            self.ids.save_btn.disabled = False
            self.ids.add_step_btn.disabled = False

        # ✅ ALWAYS reset when NOT editing
        if not self.edit_mode:
            if "topic_id" in self.ids:
                self.ids.topic_id.text = ""

            self.reset_form()

        self.refresh_steps_preview()
        self.refresh_steps_list()
        self._schedule_populate_dropdowns()

        def reset_form(self):
            self.ids.category.text = "Select Category"
            self.ids.subcategory.text = "Select Subcategory"

            self.ids.title.text = ""
            self.ids.description.text = ""
            self.ids.urls.text = ""
            self.ids.cat_icon.text = ""
            self.ids.sub_icon.text = ""
            self.ids.topic_icon.text = ""
            self.ids.icon_path.text = ""

            self.ids.date_created.text = ""
            self.ids.date_updated.text = ""

            self.pending_steps = []
            self.selected_step_index = -1

    def populate_topics(self):
        global APP_DATA
        app = App.get_running_app()
        topics = app.APP_DATA.get("topics", []) if isinstance(APP_DATA, dict) else []

        values = []
        self.topic_map = {}

        for t in topics:
            if not isinstance(t, dict):
                continue
            topic_id = t.get("Topic_ID")
            title = str(t.get("Title", "")).strip()
            cat = str(t.get("Category", "")).strip()

            if not topic_id or not title:
                continue

            # display string: Category — Title (short id)
            display = f"{cat} — {title} ({str(topic_id)[:8]})"
            values.append(display)
            self.topic_map[display] = topic_id

        values.sort()

        # update spinner
        self.ids.topic_spinner.values = values
        if values:
            self.ids.topic_spinner.text = values[0]
        else:
            self.ids.topic_spinner.text = "No topics available"

    def save_step(self):
        if not is_admin_enabled():
            self.ids.status_label.text = self._txt("⚠️ Editor disabled (admin key missing).")
            return

        chosen = self.ids.topic_spinner.text
        topic_id = self.topic_map.get(chosen)

        if not topic_id:
            self.ids.step_status.text = "Please select a valid topic."
            return

        # Validate Step_Order
        try:
            step_order = int(self.ids.step_order.text.strip())
        except Exception:
            self.ids.step_status.text = "Step_Order must be an integer (e.g. 1, 2, 3)."
            return

        step = {
            "Topic_ID": topic_id,
            "Step_Order": step_order,
            "Headline": self.ids.step_headline.text.strip(),
            "Header_2": self.ids.step_header2.text.strip(),
            "Instruction": self.ids.step_instruction.text.strip(),
            "Code_Snippet": self.ids.step_code.text.strip(),
            "Notes": self.ids.step_notes.text.strip(),
        }

        # Basic validation
        if not step["Instruction"]:
            self.ids.step_status.text = "Instruction is required."
            return

        try:
            key = add_step_to_firebase(step)
            self.ids.step_status.text = f"Saved step to Firebase (key: {key})"

            # Refresh data in the background
            app = App.get_running_app()
            app.fetch_database()

            # Clear fields except topic + step order
            self.ids.step_headline.text = ""
            self.ids.step_header2.text = ""
            self.ids.step_instruction.text = ""
            self.ids.step_code.text = ""
            self.ids.step_notes.text = ""

        except Exception as e:
            self.ids.step_status.text = f"Save failed: {e}"
