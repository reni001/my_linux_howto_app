# --- Python ---
import os
import re
import shutil
from pathlib import Path
from datetime import datetime

# --- Kivy ---
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.clock import Clock
from kivy.app import App

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from kivy.factory import Factory
from kivy.uix.textinput import TextInput

# --- Your project ---
from src.services.editor_service import (
    is_admin_enabled,
    #copy_icon_to_assets,
    add_topic_to_firebase,
    add_step_to_firebase,
)
from src.logic.taxonomy import build_taxonomy
from src.ui.components import HoverRow, EntryListItem, ExpandableSection
from src.ui.file_picker_popup import open_file_picker
from src.services.subcategory_service import load_subcategories
from src.ui.styled_popup import create_popup_container


class AddTopicScreen(Screen):
    edit_topic_key = StringProperty("")
    edit_mode = BooleanProperty(False)     
    edit_topic_id = StringProperty("")     # ✅ needed for edit tracking
    edit_is_local = BooleanProperty(False)   
    pending_steps = ListProperty([])  # list of step dicts to save together with the topic
    selected_step_index = NumericProperty(-1)   # -1 means "no step selected"
    
    def _txt(self, text: str) -> str:
        """
        Wrap text with safe font (NotoSans) for full unicode support.
        """
        return f"[font=NotoSans]{text}[/font]"

    def _load_defined_subcategories(self):
        """
        Load subcategories only from subcategories.json.
        Returns:
            - a sorted list of subcategory names
            - a mapping {subcategory_name_lower: icon_filename}
        """
        subs_data = load_subcategories()

        names = []
        icon_map = {}

        for item in subs_data:
            name = str(item.get("name") or "").strip()
            icon = str(item.get("icon") or "").strip()

            if not name:
                continue

            names.append(name)
            icon_map[name.lower()] = icon

        names = sorted(set(names), key=str.lower)
        return names, icon_map

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def import_screenshot(self, filepath):
        if not filepath:
            return ""

        from src.utils.runtime_paths import get_runtime_paths

        paths = get_runtime_paths()
        dest_dir = paths["assets"] / "screenshots"
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(filepath).name
        dest = dest_dir / filename

        # reuse if already present
        if dest.exists():
            print(f"ℹ️ Reusing existing screenshot: {dest}")
            return filename

        shutil.copy2(filepath, dest)
        print(f"✓ Imported screenshot: {dest}")
        return filename

    from src.ui.file_picker_popup import open_file_picker

    def pick_step_screenshot(self):
        from src.utils.runtime_paths import get_runtime_paths

        paths = get_runtime_paths()
        screenshots_dir = paths["assets"] / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        def on_selected(path):
            try:
                fname = self.import_screenshot(str(path))
                self.ids.step_screenshot.text = fname
                self.ids.status_label.text = self._txt(f"✔ Screenshot selected: {fname}")
            except Exception as e:
                self.ids.status_label.text = self._txt(f"✖ Screenshot import failed: {e}")

        open_file_picker(
            title="Select Screenshot",
            callback=on_selected,
            filters=("*.png", "*.jpg", "*.jpeg", "*.webp"),
            start_path=str(screenshots_dir)
        )


    def on_pre_enter(self):
        self.set_save_state("idle")

        app = App.get_running_app()

        if not app.is_admin_mode():
            self.ids.status_label.text = self._txt("User mode: saving locally")
        else:
            self.ids.status_label.text = self._txt("")

        if self.edit_mode:
            # keep Topic_ID locked
            if "topic_id" in self.ids:
                self.ids.topic_id.readonly = True

            self.refresh_steps_preview()
            self.refresh_steps_list()

            # ✅ ensure dropdowns exist in edit mode too
            self._schedule_populate_dropdowns()
            return

        # ✅ ADD MODE (only here)
        if "topic_id" in self.ids:
            self.ids.topic_id.text = ""
            self.ids.topic_id.readonly = False

        if "header_icon" in self.ids:
            self.ids.header_icon.source = App.get_running_app().get_icon_path("howtolinux-icon.png")

        self.refresh_steps_preview()
        self.refresh_steps_list()
        self._schedule_populate_dropdowns()

        # ✅ set dates for new topic
        if not self.edit_mode:
            now = self._now()
            self.ids.date_created.text = now
            self.ids.date_updated.text = now


    def _schedule_populate_dropdowns(self):

        def _try(_dt):
            app = App.get_running_app()

            if isinstance(app.APP_DATA, dict) and app.APP_DATA.get("topics"):
                data = app.APP_DATA
                topics = data.get("topics", [])

                (
                    self.cat_to_icon,
                    self.sub_to_icon,
                    self.sub_icon_global,
                    self.all_subcategories,
                ) = build_taxonomy(topics)

                # ✅ NEW: load subcategories only from json definition
                self.defined_subcategories, self.defined_sub_icons = self._load_defined_subcategories()

                self._populate_category_spinner()

                if self.edit_mode:
                    Clock.schedule_once(lambda dt: self._restore_edit_values(), 0.1)
            else:
                Clock.schedule_once(_try, 0.2)

        Clock.schedule_once(_try, 0)

    def _populate_category_spinner(self):
        #if self.edit_mode:
        #    return

        cats = sorted(self.cat_to_icon.keys(), key=str.lower)

        self.ids.category.values = cats

        # ✅ Always force placeholder AFTER values set
        if not self.edit_mode:
            self.ids.category.text = "Click to choose category"

        # ✅ Reset subcategory as well
        if not self.edit_mode:
            self.ids.subcategory.values = []
            self.ids.subcategory.text = "Click to choose subcategory"


        # ✅ Clear icons until selection is made
        self.ids.cat_icon.text = ""
        self.ids.sub_icon.text = ""

    def on_category_changed(self, category_text):
        if not hasattr(self, "cat_to_icon"):
            return

        if getattr(self, "_skip_callbacks", False):
            return

        cat = str(category_text).strip()

        # auto-fill Cat_Icon
        cat_icon = self.cat_to_icon.get(cat, "")
        self.ids.cat_icon.text = cat_icon

        # ✅ use only subcategories defined in subcategories.json
        subs = list(getattr(self, "defined_subcategories", []))

        if not subs:
            subs = ["General"]

        self.ids.subcategory.values = subs

        if not self.edit_mode:
            self.ids.subcategory.text = "Select Subcategory"
            self.ids.sub_icon.text = ""


    def on_subcategory_changed(self, subcategory_text):

        if getattr(self, "_skip_callbacks", False):
            return

        if subcategory_text in ("Click to choose subcategory", "Select Subcategory"):
            return

        sub = str(subcategory_text).strip().lower()

        # ✅ FIRST: icon from subcategories.json
        sub_icon = getattr(self, "defined_sub_icons", {}).get(sub, "")

        # optional fallback to old taxonomy-based mapping
        if not sub_icon:
            cat = str(self.ids.category.text).strip()

            sub_icon = self.sub_to_icon.get((cat, sub), "")

            if not sub_icon:
                sub_icon = self.sub_icon_global.get(sub, "")

            if not sub_icon:
                sub_icon = self.ids.cat_icon.text

        self.ids.sub_icon.text = sub_icon



    def cancel_edit(self):
        self.edit_mode = False
        self.edit_is_local = False

        # reset fields
        self.ids.category.text = "Click to choose category"
        self.ids.subcategory.text = "Click to choose subcategory"
        self.ids.title.text = ""
        self.ids.description.text = ""
        self.ids.urls.text = ""
        self.ids.cat_icon.text = ""
        self.ids.sub_icon.text = ""
        self.ids.topic_icon.text = ""
        self.ids.icon_path.text = ""

        self.pending_steps = []
        self.refresh_steps_preview()

        # go back
        App.get_running_app().sm.current = "menu"

    # -----------------------------
    # ICON PICKER
    # -----------------------------
    # Helper

    def _import_icon(self, src_path: str) -> str:
        """
        Import icon depending on mode:
        - ADMIN → assets/icons
        - USER → assets/user_icons
        """

        from src.utils.runtime_paths import get_runtime_paths
        import shutil
        from pathlib import Path
        from kivy.app import App

        if not src_path:
            return ""

        app = App.get_running_app()
        paths = get_runtime_paths()

        # ✅ SELECT TARGET BASED ON MODE
        if app.is_admin_mode():
            target_dir = paths["assets"] / "icons"
        else:
            target_dir = paths["assets"] / "user_icons"

        official_dir = paths["assets"] / "icons"

        target_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(src_path).name

        target_path = target_dir / filename
        official_target = official_dir / filename


        # ✅ 1. already in target → reuse
        if target_path.exists():
            print(f"ℹ️ Reusing existing icon: {filename}")
            return filename

        # ✅ 2. already in official folder → reuse
        if official_target.exists():
            print(f"ℹ️ Using existing official icon: {filename}")
            return filename

        # ✅ 3. copy to correct folder
        shutil.copy2(src_path, target_path)
        print(f"✓ Imported icon: {target_path}")

        return filename

    #--------

    def pick_icon(self):

        def on_selected(path):
            try:
                filename = self._import_icon(str(path))

                self.ids.topic_icon.text = filename
                self.ids.header_icon.source = str(path)
                self.ids.icon_path.text = ""

            except Exception as e:
                print("DEBUG: icon import failed:", e)

        open_file_picker(
            title="Select Icon",
            callback=on_selected,
            filters=("*.png", "*.jpg", "*.jpeg")
        )

    def on_topic_icon_change(self, value):
        if "header_icon" not in self.ids:
            return

        icon_path = App.get_running_app().get_icon_path(value)

        if value and os.path.exists(icon_path):
            self.ids.header_icon.source = icon_path
        else:
            # ✅ fallback icon
            self.ids.header_icon.source = App.get_running_app().get_icon_path("howtolinux-icon.png")

    # -----------------------------
    # STEPS (local buffer)
    # -----------------------------
    def add_step_local(self):
        try:
            step_order = int(self.ids.step_order.text.strip())
        except Exception:
            self.ids.status_label.text = self._txt("! Step_Order must be an integer (e.g. 1, 2, 3).")
            return

        instruction = self.ids.step_instruction.text.strip()
        if not instruction:
            self.ids.status_label.text = self._txt("! Instruction is required.")
            return
        # Build step dict
        step = {
            "Step_Order": step_order,
            "Headline": self.ids.step_headline.text.strip(),
            "Header_2": self.ids.step_header2.text.strip(),
            "Instruction": instruction,
            "Code_Snippet": self.ids.step_code.text.strip(),

            # ✅ NEW FIELDS
            "Screenshot": self.ids.step_screenshot.text.strip(),
            "URLs": self.ids.step_urls.text.strip(),

            "Notes": self.ids.step_notes.text.strip(),
        }

        # ✅ If a step is selected → overwrite that slot
        if self.selected_step_index != -1 and 0 <=self.selected_step_index < len(self.pending_steps):
            self.pending_steps[self.selected_step_index] = step
            self.selected_step_index = -1
            if "add_step_btn" in self.ids:
                self.ids.add_step_btn.text = "Add Step"
        else:
            # fallback: replace any existing step with same order
            self.pending_steps = [s for s in self.pending_steps if int(s.get("Step_Order", 9999)) != step_order]
            self.pending_steps.append(step)

        # reorder + renumber
        self.pending_steps.sort(key=lambda s: int(s.get("Step_Order", 9999)))
        self.renumber_steps()

        self.clear_step_form()
        self.refresh_steps_preview()
        self.refresh_steps_list()
        self.ids.form_scroll.scroll_y = 0.3

        self.ids.status_label.text = self._txt(f"✓ Step saved.")


    def remove_last_step(self):
        if self.pending_steps:
            self.pending_steps = self.pending_steps[:-1]
            self.renumber_steps()
            self.refresh_steps_preview()
            self.refresh_steps_list()
            self.ids.status_label.text = self._txt("Last step removed.")

    def clear_step_form(self):
        self.ids.step_order.text = ""
        self.ids.step_headline.text = ""
        self.ids.step_header2.text = ""
        self.ids.step_instruction.text = ""
        self.ids.step_code.text = ""
        self.ids.step_screenshot.text = ""
        self.ids.step_urls.text = ""
        self.ids.step_notes.text = ""

        # ✅ 🔥 RESET selection highlight
        self.selected_step_index = -1
        self.refresh_steps_list()

        # ✅ reset button text
        if "add_step_btn" in self.ids:
            self.ids.add_step_btn.text = "Add Step"

    def refresh_steps_preview(self):
        # Only update if you still have a steps_preview label in KV
        if "steps_preview" not in self.ids:
            return

        if not self.pending_steps:
            self.ids.steps_preview.text = "No steps added yet."
            return

        lines = []
        for s in self.pending_steps:
            order = s.get("Step_Order", "?")
            title = s.get("Headline") or s.get("Header_2") or "(no headline)"
            lines.append(f"{order}. {title}")
        self.ids.steps_preview.text = "\n".join(lines)


    def _clean_step_title(self, title: str) -> str:
        """Remove leading numbering like '3.' or '3)' from stored titles."""
        if not title:
            return "(no headline)"
        return re.sub(r'^\s*\d+[\.\)\:\-]\s*', '', str(title).strip())

    def _norm(self, value):
        return str(value or "").strip().lower()

    def _find_duplicate_topic(self, candidate: dict):
        """
        Find any duplicate in APP_DATA by Category + Subcategory + Title,
        excluding the topic currently being edited.
        """
        app = App.get_running_app()

        wanted_cat = self._norm(candidate.get("Category"))
        wanted_sub = self._norm(candidate.get("Subcategory"))
        wanted_title = self._norm(candidate.get("Title"))

        current_id = str(self.edit_topic_id or "")

        for topic in app.APP_DATA.get("topics", []):
            other_id = str(topic.get("Topic_ID") or "")

            # ✅ ignore self when editing
            if current_id and other_id == current_id:
                continue

            if (
                self._norm(topic.get("Category")) == wanted_cat and
                self._norm(topic.get("Subcategory")) == wanted_sub and
                self._norm(topic.get("Title")) == wanted_title
            ):
                return topic

        return None

    def _merge_urls(self, existing_urls: str, new_urls: str) -> str:
        items = []
        for raw in [existing_urls, new_urls]:
            for part in str(raw or "").split(","):
                value = part.strip()
                if value and value not in items:
                    items.append(value)
        return ", ".join(items)

    def _step_signature(self, step: dict):
        return (
            str(step.get("Headline", "")).strip().lower(),
            str(step.get("Header_2", "")).strip().lower(),
            str(step.get("Instruction", "")).strip().lower(),
            str(step.get("Code_Snippet", "")).strip().lower(),
            str(step.get("Notes", "")).strip().lower(),
        )

    def _merge_steps(self, existing_steps: list[dict], new_steps: list[dict]) -> list[dict]:
        merged = [dict(s) for s in existing_steps]
        seen = {self._step_signature(s) for s in merged}

        for step in new_steps:
            sig = self._step_signature(step)
            if sig not in seen:
                merged.append(dict(step))
                seen.add(sig)

        # Renumber cleanly
        for i, step in enumerate(merged, start=1):
            step["Step_Order"] = i

        return merged

    def _apply_description_strategy(self, old_desc: str, new_desc: str, strategy: str) -> str:
        old_desc = str(old_desc or "").strip()
        new_desc = str(new_desc or "").strip()
        strategy = str(strategy or "Add").strip()

        if strategy == "Skip":
            return old_desc

        if strategy == "Replace":
            return new_desc if new_desc else old_desc

        # default = Add
        if not new_desc:
            return old_desc
        if not old_desc:
            return new_desc
        if old_desc == new_desc:
            return old_desc
        if new_desc in old_desc:
            return old_desc
        if old_desc in new_desc:
            return new_desc

        return f"{old_desc}\n\n--- merged addition ---\n{new_desc}"

    def _apply_urls_strategy(self, old_urls: str, new_urls: str, strategy: str) -> str:
        strategy = str(strategy or "Add").strip()

        old_urls = str(old_urls or "").strip()
        new_urls = str(new_urls or "").strip()

        if strategy == "Skip":
            return old_urls

        if strategy == "Replace":
            return new_urls if new_urls else old_urls

        # default = Add
        return self._merge_urls(old_urls, new_urls)

    def _apply_steps_strategy(self, existing_steps: list[dict], new_steps: list[dict], strategy: str) -> list[dict]:
        strategy = str(strategy or "Add").strip()

        if strategy == "Skip":
            return [dict(s) for s in existing_steps]

        if strategy == "Replace":
            replaced = [dict(s) for s in new_steps]
            for i, step in enumerate(replaced, start=1):
                step["Step_Order"] = i
            return replaced

        # default = Add
        return self._merge_steps(existing_steps, new_steps)

    def _show_merge_popup(self, new_topic, duplicate_topic):
        
        container = create_popup_container()

        content = BoxLayout(
            orientation="vertical",
            spacing=10,
            padding=10,
            size_hint=(0.95, 0.95),
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )

        container.add_widget(content)

        preview_lines = []
        preview_lines.append(f"Merging into existing topic:\n{duplicate_topic.get('Title')}\n")

        old_desc = str(duplicate_topic.get("Description", "")).strip()
        new_desc = str(new_topic.get("Description", "")).strip()
        if new_desc and new_desc != old_desc:
            preview_lines.append("Description differs.")

        old_urls = set(u.strip() for u in duplicate_topic.get("URLs", "").split(",") if u.strip())
        new_urls = set(u.strip() for u in new_topic.get("URLs", "").split(",") if u.strip())
        if new_urls - old_urls:
            preview_lines.append("URLs differ.")

        if self.pending_steps:
            preview_lines.append("New steps are present.")

        preview_text = "\n".join(preview_lines) or "Duplicate detected."

        scroll = ScrollView(size_hint=(1, 1))
        msg = Label(
            text=preview_text,
            halign="left",
            valign="top",
            size_hint_y=None
        )

        def _update_height(*_):
            msg.text_size = (msg.width, None)
            msg.texture_update()
            msg.height = max(msg.texture_size[1], dp(100))

        msg.bind(width=lambda *_: _update_height())
        _update_height()

        scroll.add_widget(msg)
        content.add_widget(scroll)

        # ✅ strategy selectors
        strategy_box = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        strategy_box.bind(minimum_height=strategy_box.setter("height"))

        # Description
        row_desc = BoxLayout(size_hint_y=None, height=dp(36), spacing=8)
        row_desc.add_widget(Label(text="Description", size_hint_x=0.45, halign="left"))
        desc_spinner = Spinner(
            text="Add",
            values=("Add", "Replace", "Skip"),
            size_hint_x=0.55
        )
        row_desc.add_widget(desc_spinner)
        strategy_box.add_widget(row_desc)

        # URLs
        row_urls = BoxLayout(size_hint_y=None, height=dp(36), spacing=8)
        row_urls.add_widget(Label(text="URLs", size_hint_x=0.45, halign="left"))
        urls_spinner = Spinner(
            text="Add",
            values=("Add", "Replace", "Skip"),
            size_hint_x=0.55
        )
        row_urls.add_widget(urls_spinner)
        strategy_box.add_widget(row_urls)

        # Steps
        row_steps = BoxLayout(size_hint_y=None, height=dp(36), spacing=8)
        row_steps.add_widget(Label(text="Steps", size_hint_x=0.45, halign="left"))
        steps_spinner = Spinner(
            text="Add",
            values=("Add", "Replace", "Skip"),
            size_hint_x=0.55
        )
        row_steps.add_widget(steps_spinner)
        strategy_box.add_widget(row_steps)

        content.add_widget(strategy_box)
        
        btn_box = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(10),
            padding = [dp(5), dp(5)]
        )
        
        btn_merge = Factory.SuccessButton(
            text="MERGE"
        )

        btn_cancel = Factory.SecondaryButton(
            text="Cancel"
        )

        btn_merge.size_hint_x = 1
        btn_cancel.size_hint_x = 1

        btn_box.add_widget(btn_merge)
        btn_box.add_widget(btn_cancel)
        content.add_widget(btn_box)

        popup = Popup(
            title="Preview Merge",
            content=container,
            size_hint=(0.82, 0.78),
            background="",
            background_color=(0, 0, 0, 0),
            separator_height=0
        )

        def do_merge(instance):
            popup.dismiss()
            Clock.schedule_once(
                lambda dt: self._perform_merge(
                    new_topic,
                    duplicate_topic,
                    desc_spinner.text,
                    urls_spinner.text,
                    steps_spinner.text
                ),
                0
            )

        btn_merge.bind(on_release=do_merge)
        btn_cancel.bind(on_release=lambda x: popup.dismiss())

        popup.open()


    def _perform_merge(
        self,
        new_topic: dict,
        duplicate_topic: dict,
        desc_strategy: str = "Add",
        urls_strategy: str = "Add",
        steps_strategy: str = "Add",
    ):
        print("✅ MERGE STARTED")  
        
        app = App.get_running_app()

        try:
            existing_topic_id = str(duplicate_topic.get("Topic_ID") or "")

            existing_steps = [
                dict(step) for step in app.APP_DATA.get("steps", [])
                if str(step.get("Topic_ID")) == existing_topic_id
            ]

            new_steps = [dict(step) for step in self.pending_steps]

            merged_steps = self._apply_steps_strategy(
                existing_steps,
                new_steps,
                steps_strategy
            )

            merged_topic = dict(duplicate_topic)

            # ✅ update modification date
            merged_topic["Date_Updated"] = self._now()

            # ✅ URLs strategy
            merged_topic["URLs"] = self._apply_urls_strategy(
                duplicate_topic.get("URLs", ""),
                new_topic.get("URLs", ""),
                urls_strategy
            )

            # ✅ Description strategy
            merged_topic["Description"] = self._apply_description_strategy(
                duplicate_topic.get("Description", ""),
                new_topic.get("Description", ""),
                desc_strategy
            )

            # ✅ keep existing icon unless empty
            if not str(merged_topic.get("Topic_Icon", "")).strip():
                merged_topic["Topic_Icon"] = new_topic.get("Topic_Icon", "")

            # ✅ LOCAL duplicate → update local JSON
            if str(duplicate_topic.get("source") or "") == "user":
                merged_topic["Topic_ID"] = existing_topic_id
                merged_topic["_key"] = existing_topic_id
                merged_topic["source"] = "user"
                merged_topic["local_only"] = True

                app.update_local_topic(existing_topic_id, merged_topic, merged_steps)
                print("✅ LOCAL MERGE DONE")
                self.ids.status_label.text = self._txt("✓ Local topics merged")

            # ✅ OFFICIAL duplicate → update Firebase
            else:
                from src.services.editor_service import delete_steps_for_topic

                merged_topic["_key"] = duplicate_topic.get("_key")
                merged_topic["Topic_ID"] = existing_topic_id

                add_topic_to_firebase(merged_topic, overwrite=True)
                print("✅ FIREBASE MERGE DONE")

                delete_steps_for_topic(existing_topic_id)

                for step in merged_steps:
                    payload = dict(step)
                    payload["Topic_ID"] = existing_topic_id
                    add_step_to_firebase(payload)

                self.ids.status_label.text = self._txt("✓ Official topics merged")

            # ✅ cleanup local duplicate if editing another local topic
            try:
                if self.edit_mode and self.edit_is_local:
                    current_id = str(self.edit_topic_id or "")
                    existing_id = str(duplicate_topic.get("Topic_ID") or "")

                    if current_id and current_id != existing_id:
                        app.delete_local_topic(current_id)
                        print(f"✓ Removed duplicate local topic: {current_id}")

            except Exception as e:
                print("DEBUG: cleanup failed:", e)
            
            # ✅ remember target category
            target_category = merged_topic.get("Category", "")

            # ✅ reload data first
            app.fetch_database()

            def _open_merged_category(_dt):
                try:
                    print(f"✅ OPEN MERGED CATEGORY: {target_category}")

                    # rebuild menu first
                    menu = app.root.get_screen("menu")
                    menu.populate_menu()

                    # ✅ use existing menu navigation to go to DetailScreen
                    menu.open_category(target_category)

                except Exception as e:
                    print("DEBUG: open merged category failed:", e)

            # ✅ IMPORTANT:
            # Your log shows Firebase refresh finishes AFTER the earlier 0.3 / 0.4 timing.
            # So we wait longer before opening the category.
            Clock.schedule_once(_open_merged_category, 1.5)

        except Exception as e:
            self.ids.status_label.text = self._txt(f"✖ Merge failed: {e}")


    def refresh_steps_list(self):
        if "steps_container" not in self.ids:
            return

        container = self.ids.steps_container
        container.clear_widgets()

        if not self.pending_steps:
            container.add_widget(Label(
                text="No steps added yet.",
                size_hint_y=None,
                height=dp(30),
                color=[0.3, 0.3, 0.3, 1]
            ))
            return

        app = App.get_running_app()

        for idx, s in enumerate(self.pending_steps):
            order = int(s.get("Step_Order", idx + 1))
            title_raw = s.get("Headline") or s.get("Header_2") or ""
            title = self._clean_step_title(title_raw)

            row = HoverRow()
            row.selected = (idx == self.selected_step_index)

            # LEFT: TEXT (flexible width)
            lbl = Label(
                text=f"[font=NotoSans]{order}. {title}[/font]",
                markup=True,
                size_hint_x=1,          # ✅ takes remaining space
                halign="left",
                valign="middle",
                color=[0.1, 0.25, 0.45, 1]   # ✅ dark reada
            )
            lbl.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            row.add_widget(lbl)

            # RIGHT: BUTTON GROUP (fixed width!)
            btn_box = BoxLayout(
                orientation="horizontal",
                size_hint_x=None,
                width=dp(160),          # ✅ FIXED SPACE for buttons
                spacing=dp(4)
            )

            # EDIT

            btn_edit = Button(
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                background_normal=app.get_icon_path("edit.png"),
                background_down=app.get_icon_path("edit.png"),
                background_color=[1, 1, 1, 1],
                border=(0, 0, 0, 0),
                text=""
            )

            btn_edit.bind(on_release=lambda _b, i=idx: self.load_step_into_form(i))
            btn_box.add_widget(btn_edit)

            # DELETE
            btn_del = Button(
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                background_normal=app.get_icon_path("delete.png"),
                background_down=app.get_icon_path("delete.png"),
                background_color=[1, 1, 1, 1],
                border=(0, 0, 0, 0),
                text=""
            )
            btn_del.bind(on_release=lambda _b, i=idx: self.delete_step(i))
            btn_box.add_widget(btn_del)


            # UP
            btn_up = Button(
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                background_normal=app.get_icon_path("up.png"),
                background_down=app.get_icon_path("up.png"),
                background_color=[1, 1, 1, 1],
                border=(0, 0, 0, 0),
                text=""
            )
            btn_up.bind(on_release=lambda _b, i=idx: self.move_step(i, -1))
            btn_box.add_widget(btn_up)

            # DOWN
            btn_down = Button(
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                background_normal=app.get_icon_path("down.png"),
                background_down=app.get_icon_path("down.png"),
                background_color=[1, 1, 1, 1],
                border=(0, 0, 0, 0),
                text=""
            )
            btn_down.bind(on_release=lambda _b, i=idx: self.move_step(i, +1))
            btn_box.add_widget(btn_down)

            row.add_widget(btn_box)
            container.add_widget(row)


    def load_step_into_form(self, idx):
        """Load a pending step into the step form for editing."""
        if idx < 0 or idx >= len(self.pending_steps):
            return

        s = self.pending_steps[idx]
        self.selected_step_index = idx
        self.refresh_steps_list()

        self.ids.step_order.text = str(s.get("Step_Order", ""))
        self.ids.step_headline.text = s.get("Headline", "") or ""
        self.ids.step_header2.text = s.get("Header_2", "") or ""
        self.ids.step_instruction.text = s.get("Instruction", "") or ""
        self.ids.step_code.text = s.get("Code_Snippet", "") or ""
        self.ids.step_screenshot.text = s.get("Screenshot", "") or ""
        self.ids.step_urls.text = s.get("URLs", "") or ""
        self.ids.step_notes.text = s.get("Notes", "") or ""

        # visual cue: turn Add Step button into Update
        if "add_step_btn" in self.ids:
            self.ids.add_step_btn.text = "Update Step"

    def renumber_steps(self):
        """Force Step_Order to be 1..n in the current order."""
        for i, s in enumerate(self.pending_steps):
            s["Step_Order"] = i + 1

        self.refresh_steps_preview()
        self.refresh_steps_list()

    def delete_step(self, idx):
        if idx < 0 or idx >= len(self.pending_steps):
            return
        self.pending_steps.pop(idx)
        self.selected_step_index = -1
        if "add_step_btn" in self.ids:
            self.ids.add_step_btn.text = "Add Step"
        self.renumber_steps()
        self.refresh_steps_preview()
        self.refresh_steps_list()

    def move_step(self, idx, direction):
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.pending_steps):
            return

        self.pending_steps[idx], self.pending_steps[new_idx] = self.pending_steps[new_idx], self.pending_steps[idx]
        self.renumber_steps()
        self.refresh_steps_preview()
        self.refresh_steps_list()

    def set_save_state(self, state):
        if "save_btn" not in self.ids: 
            return

        btn = self.ids.save_btn

        if state == "saving":
            btn.text = "saving ..."
            btn.disabled = True

        elif state == "success":
            btn.text = "Saved ✔"
            btn.disabled = False

        elif state == "error":
            btn.text = "Error"
            btn.disabled = False

        else:
            btn.text = "Save"
            btn.disabled = False

    # -----------------------------
    # SAVE TOPIC + ALL STEPS TO FIREBASE
    # -----------------------------

    def save_topic(self):
        # ✅ show saving state immediately
        self.set_save_state("saving")
        
        # ✅ run save on next UI tick (safe, no thread crash)
        Clock.schedule_once(lambda dt: self._save_topic_internal(), 0.05)

    def _save_topic_internal(self):
        app = App.get_running_app()
        now = self._now()

        # ✅ Do NOT copy icon yet
        icon_filename = self.ids.topic_icon.text.strip()
        icon_path = self.ids.icon_path.text.strip()

        # ✅ 1. Build topic dict FIRST
        topic = {
            "Category": self.ids.category.text.strip(),
            "Subcategory": self.ids.subcategory.text.strip(),
            "Title": self.ids.title.text.strip(),
            "Description": self.ids.description.text.strip(),
            "URLs": self.ids.urls.text.strip(),
            "Cat_Icon": self.ids.cat_icon.text.strip(),
            "Sub_Icon": self.ids.sub_icon.text.strip(),
            "Topic_Icon": icon_filename,
        }

        # ✅ DATE HANDLING
        if self.edit_mode:
            topic["Date_Created"] = self.ids.date_created.text.strip()
        else:
            topic["Date_Created"] = now

        topic["Date_Updated"] = now


        # ✅ 2. Optional Topic_ID while editing
        if "topic_id" in self.ids:
            user_id = self.ids.topic_id.text.strip()
            if self.edit_mode and user_id:
                topic["Topic_ID"] = user_id

        # ✅ 3. Required fields
        
        category = topic.get("Category", "").strip()
        subcategory = topic.get("Subcategory", "").strip()
        title = topic.get("Title", "").strip()

        if (
            not category
            or category in ("Click to choose category",)
            or not subcategory
            or subcategory in ("Click to choose subcategory", "Select Subcategory")
            or not title
        ):
            self.ids.status_label.text = self._txt("! Category, Subcategory and Title are required.")

            app = App.get_running_app()
            default_bg = app.COLOR_WHITE
            error_bg = app.COLOR_ERROR_BG   # ✅ soft theme color

            # ✅ RESET FIRST
            if "category" in self.ids:
                self.ids.category.background_color = default_bg
            if "subcategory" in self.ids:
                self.ids.subcategory.background_color = default_bg
            if "title" in self.ids:
                self.ids.title.background_color = default_bg

            # ✅ APPLY ERROR COLOR
            if category in ("", "Click to choose category"):
                self.ids.category.background_color = error_bg

            if subcategory in ("", "Click to choose subcategory", "Select Subcategory"):
                self.ids.subcategory.background_color = error_bg

            if not title:
                self.ids.title.background_color = error_bg

            self.set_save_state("error")
            Clock.schedule_once(lambda dt: self.set_save_state("idle"), 2.5)
            return
        
        # ✅ 4. Duplicate check BEFORE any icon copy or save
        duplicate = self._find_duplicate_topic(topic)
        if duplicate:
            self.set_save_state("idle")
            self._show_merge_popup(topic, duplicate)
            return

        # ✅ 6. LOCAL SAVE PATH
        # Rule:
        # - if editing a local topic -> always stay local
        # - if user mode and creating a new topic -> save local
        if self.edit_is_local or not app.is_admin_mode():
            try:
                topic_payload = dict(topic)
                step_payloads = list(self.pending_steps)

                # ✅ ensure dates exist (important for local topics)
                topic_payload["Date_Created"] = topic.get("Date_Created", "")
                topic_payload["Date_Updated"] = topic.get("Date_Updated", "")

                # update existing local topic
                if self.edit_mode and self.edit_topic_id:
                    topic_payload["Topic_ID"] = self.edit_topic_id
                    topic_payload["_key"] = self.edit_topic_id
                    topic_payload["source"] = "user"
                    topic_payload["local_only"] = True

                    app.update_local_topic(self.edit_topic_id, topic_payload, step_payloads)
                    self.ids.status_label.text = self._txt("✓ Local topic updated")
                    self.set_save_state("success")
                    Clock.schedule_once(lambda dt: self.set_save_state("idle"), 2)

                # create new local topic
                else:
                    app.save_local_topic(topic_payload, step_payloads)
                    self.ids.status_label.text = self._txt("✓ Topic saved locally")                  
                    self.set_save_state("success")
                    Clock.schedule_once(lambda dt: self.set_save_state("idle"), 2)

                target_category = topic.get("Category", "")

                app.sm.current = "menu"

                def _restore_category(_dt):
                    try:
                        menu = app.root.get_screen("menu")
                        menu.open_category(target_category)
                    except Exception as e:
                        print("DEBUG: restore category failed:", e)

                Clock.schedule_once(_restore_category, 0.4)

                return

            except Exception as e:
                self.ids.status_label.text = self._txt(f"✖ Local save failed: {e}")
                self.set_save_state("error")
                Clock.schedule_once(lambda dt: self.set_save_state("idle"), 3)          
                return

        # ✅ 7. OFFICIAL / FIREBASE SAVE PATH
        try:
            if self.edit_mode:
                topic["_key"] = self.edit_topic_key
                topic["Topic_ID"] = self.edit_topic_id
                topic_key, topic_id = add_topic_to_firebase(topic, overwrite=True)
            else:
                topic_key, topic_id = add_topic_to_firebase(topic)

            topic_id = str(topic_id)

            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id

            if "header_icon" in self.ids:
                icon_file = self.ids.topic_icon.text.strip()

                if icon_file:
                    try:
                        self.ids.header_icon.source = App.get_running_app().get_icon_path(icon_file)
                    except Exception as e:
                        print("DEBUG: header icon update failed:", e)
                else:
                    self.ids.header_icon.source = App.get_running_app().get_icon_path("howtolinux-icon.png")

            from src.services.editor_service import delete_steps_for_topic
            delete_steps_for_topic(topic_id)

            for s in self.pending_steps:
                payload = dict(s)
                payload["Topic_ID"] = topic_id
                add_step_to_firebase(payload)

            self.clear_step_form()

            app.fetch_database()
            Clock.schedule_once(lambda dt: app.root.get_screen("menu").populate_menu(), 0.5)

            try:
                app.root.get_screen("menu").populate_categories()
            except Exception as e:
                print("UI refresh error:", e)

            self.refresh_steps_preview()
            self.clear_step_form()

            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id

            self.ids.status_label.text = self._txt(f"✓ Saved topic + steps (Topic_ID: {str(topic_id)[:8]}…)")            
            self.set_save_state("success")
            Clock.schedule_once(lambda dt: self.set_save_state("idle"), 2)

            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id

            self.edit_mode = True
            self.edit_topic_id = topic_id
            self.edit_topic_key = topic_key

        except Exception as e:
            self.ids.status_label.text = self._txt(f"✖ Save failed: {e}")
            self.set_save_state("error")           
            Clock.schedule_once(lambda dt: self.set_save_state("idle"), 3)

    def _clear_error_on_input(self, instance, value):
        app = App.get_running_app()

        if value and value.strip():
            instance.background_color = app.COLOR_WHITE
    
    def on_kv_post(self, base_widget):     
        for widget in self.walk():
            # ✅ for text inputs
            if isinstance(widget, TextInput) and not widget.readonly:
                widget.bind(focus=self._handle_focus)
                widget.bind(text=self._clear_error_on_input)   # ✅ NEW

            # ✅ for dropdowns (category/subcategory)
            if isinstance(widget, Spinner):
                widget.bind(text=self._clear_error_on_input)   # ✅ NEW

        for widget in self.walk():
            if isinstance(widget, TextInput) and not widget.readonly:
                widget.bind(focus=self._handle_focus)

    def _handle_focus(self, instance, value):

        # ✅ DO NOT disable scrolling anymore
        pass

    def reset_form_only(self):
        self.edit_mode = False
        self.edit_is_local = False
        self.edit_topic_id = ""
        self.selected_step_index = -1
        self.pending_steps = []

        self.ids.category.text = "Select Category"
        self.ids.subcategory.text = "Click to choose subcategory"
        self.ids.subcategory.values = []

        self.ids.title.text = ""
        self.ids.description.text = ""
        self.ids.urls.text = ""
        self.ids.cat_icon.text = ""
        self.ids.sub_icon.text = ""
        self.ids.topic_icon.text = ""
        self.ids.icon_path.text = ""

        self.refresh_steps_list()

    def _restore_edit_values(self):
        if not self.edit_mode:
            return

        cat = getattr(self, "_edit_category", "")
        sub = getattr(self, "_edit_subcategory", "")

        if not cat:
            print("ERROR: no stored category")
            return

        # set category safely
        self._skip_callbacks = True
        self.ids.category.text = cat
        self._skip_callbacks = False

        # build sub list
        self.on_category_changed(cat)

        def _set_sub(_dt):
            if sub:
                self.ids.subcategory.text = sub
                self.on_subcategory_changed(sub)

        Clock.schedule_once(_set_sub, 0.05)


    def load_topic_for_edit(self, data):
        self.edit_mode = True
        self.edit_topic_id = str(data.get("Topic_ID") or "")
        self.edit_topic_key = str(data.get("_key") or "")
        self.edit_is_local = (str(data.get("source") or "") == "user")

        # store category (needed for dropdown restore)
        self._edit_category = str(data.get("Category") or "").strip()
        self._edit_subcategory = str(data.get("Subcategory") or "").strip()

        # fill text fields
        if "topic_id" in self.ids:
            self.ids.topic_id.text = self.edit_topic_id

        self.ids.title.text = data.get("Title", "")
        self.ids.description.text = data.get("Description", "")
        self.ids.urls.text = data.get("URLs", "")
        self.ids.cat_icon.text = data.get("Cat_Icon", "")
        self.ids.sub_icon.text = data.get("Sub_Icon", "")
        self.ids.topic_icon.text = data.get("Topic_Icon", "")
        self.ids.icon_path.text = ""

        # ✅ load dates
        self.ids.date_created.text = data.get("Date_Created") or self._now()
        self.ids.date_updated.text = data.get("Date_Updated") or self._now()


        # set icon
        icon_file = data.get("Topic_Icon", "")
        if "header_icon" in self.ids:
            if icon_file:
                try:
                    app = App.get_running_app()
                    self.ids.header_icon.source = app.get_icon_path(icon_file)
                except Exception as e:
                    print("DEBUG: icon load failed:", e)
            else:
                app = App.get_running_app()
                self.ids.header_icon.source = app.get_icon_path("howtolinux-icon.png")

        # load steps
        self.pending_steps = []

        app = App.get_running_app()

        for step in app.APP_DATA.get("steps", []):
            if step.get("Topic_ID") == data.get("Topic_ID"):
                self.pending_steps.append({
                    "Step_Order": step.get("Step_Order"),
                    "Headline": step.get("Headline"),
                    "Header_2": step.get("Header_2"),
                    "Instruction": step.get("Instruction"),
                    "Code_Snippet": step.get("Code_Snippet"),
                    "Screenshot": step.get("Screenshot"),
                    "URLs": step.get("URLs"),
                    "Notes": step.get("Notes"),
                })

        self.pending_steps.sort(key=lambda x: int(x.get("Step_Order", 999)))

        # update UI
        self.refresh_steps_preview()
        self.refresh_steps_list()

        # IMPORTANT: rebuild dropdowns AFTER everything is set
        self._schedule_populate_dropdowns()
