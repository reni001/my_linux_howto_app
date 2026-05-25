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
from kivy.metrics import dp

# --- Python ---
import os
import re
from pathlib import Path

# --- Your project ---
from src.services.editor_service import (
    is_admin_enabled,
    copy_icon_to_assets,
    add_topic_to_firebase,
    add_step_to_firebase,
    export_backup_excel
)
from src.logic.taxonomy import build_taxonomy
from src.ui.components import HoverRow, EntryListItem, ExpandableSection



class AddTopicScreen(Screen):
    edit_topic_key = StringProperty("")
    edit_mode = BooleanProperty(False)     # ✅ THIS FIXES YOUR CRASH
    edit_topic_id = StringProperty("")     # ✅ needed for edit tracking
    pending_steps = ListProperty([])  # list of step dicts to save together with the topic
    selected_step_index = NumericProperty(-1)   # -1 means "no step selected"

    def on_pre_enter(self):
        if not is_admin_enabled():
            self.ids.status_label.text = "Editor disabled (admin key missing)."
        else:
            self.ids.status_label.text = ""


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
            from kivy.app import App
            self.ids.header_icon.source = App.get_running_app().get_icon_path("howtolinux-icon.png")

        self.refresh_steps_preview()
        self.refresh_steps_list()
        self._schedule_populate_dropdowns()

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
        if not hasattr(self, "sub_to_icon"):
            return

        if getattr(self, "_skip_callbacks", False):
            return

        #if category_text == "Click to choose category":
        #    return
        """
        Called by KV on category spinner change.
        Updates subcategory dropdown and auto-fills cat_icon / sub_icon.
        """
        cat = str(category_text).strip()

        # auto-fill Cat_Icon
        cat_icon = self.cat_to_icon.get(cat, "")
        self.ids.cat_icon.text = cat_icon

        # update subcategory list
        subs = sorted(
            [s.capitalize() for s in self.all_subcategories],
            key=str.lower
        )


        if not subs:
            subs = ["General"]   # ✅ fallback

        self.ids.subcategory.values = subs

        # start clean: do NOT keep old selection
        if not self.edit_mode:
            # only reset in add mode
            self.ids.subcategory.text = "Select Subcategory"
            self.ids.sub_icon.text = ""


    def on_subcategory_changed(self, subcategory_text):

        if getattr(self, "_skip_callbacks", False):
            return

        if subcategory_text == "Click to choose subcategory":
            return

        """
        Called by KV on subcategory spinner change.
        Auto-fills Sub_Icon using the (Category, Subcategory) mapping.
        """
        cat = str(self.ids.category.text).strip()
        sub = str(subcategory_text).strip().lower()

        # ✅ first try category-specific
        sub_icon = self.sub_to_icon.get((cat, sub), "")

        # ✅ fallback to GLOBAL mapping
        if not sub_icon:
            sub_icon = self.sub_icon_global.get(sub, "")

        # ✅ fallback to category icon
        if not sub_icon:
            sub_icon = self.ids.cat_icon.text

        self.ids.sub_icon.text = sub_icon


    def cancel_edit(self):
        self.edit_mode = False

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
    def pick_icon(self):
        # You already use a file picker pattern elsewhere; simplest: keep text path entry.
        # If you want a FileChooser popup later, we can add it – for now this won't crash.
        #self.ids.status_label.text = "Tip: paste an icon path into 'icon_path' then Save."

        layout = BoxLayout(orientation="vertical")

        filechooser = FileChooserListView(
            path=str(Path.home()),
            filters=["*.png", "*.jpg", "*.jpeg"]
        )

        def select_file(instance):
            if filechooser.selection:
                selected = filechooser.selection[0]
                self.ids.icon_path.text = selected

                # ✅ update header icon immediately
                from kivy.app import App
                try:
                    filename = Path(selected).name
                    # ✅ preview direct file (correct)
                    self.ids.header_icon.source = selected
                    # ✅ keep UI consistent
                    self.ids.topic_icon.text = Path(selected).name

                except Exception as e:
                    print("DEBUG: preview icon failed:", e)

            popup.dismiss()

        btn = Button(text="Select", size_hint_y=None, height=50)
        btn.bind(on_release=select_file)

        layout.add_widget(filechooser)
        layout.add_widget(btn)

        popup = Popup(title="Select Icon", content=layout, size_hint=(0.9, 0.9))
        popup.open()


    def on_topic_icon_change(self, value):
        if "header_icon" not in self.ids:
            return

        from kivy.app import App
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
            self.ids.status_label.text = "Step_Order must be an integer (e.g. 1, 2, 3)."
            return

        instruction = self.ids.step_instruction.text.strip()
        if not instruction:
            self.ids.status_label.text = "Instruction is required."
            return

        # Build step dict
        step = {
            "Step_Order": step_order,
            "Headline": self.ids.step_headline.text.strip(),
            "Header_2": self.ids.step_header2.text.strip(),
            "Instruction": instruction,
            "Code_Snippet": self.ids.step_code.text.strip(),
            "Notes": self.ids.step_notes.text.strip(),
        }

        # ✅ If a step is selected → overwrite that slot
        if self.selected_step_index != -1 and 0 <= self.selected_step_index < len(self.pending_steps):
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

        self.ids.status_label.text = f"Step saved."


    def remove_last_step(self):
        if self.pending_steps:
            self.pending_steps = self.pending_steps[:-1]
            self.renumber_steps()
            self.refresh_steps_preview()
            self.refresh_steps_list()
            self.ids.status_label.text = "Last step removed."

    def clear_step_form(self):
        self.ids.step_order.text = ""
        self.ids.step_headline.text = ""
        self.ids.step_header2.text = ""
        self.ids.step_instruction.text = ""
        self.ids.step_code.text = ""
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
                text=f"{order}. {title}",
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


    # -----------------------------
    # SAVE TOPIC + ALL STEPS TO FIREBASE
    # -----------------------------
    def save_topic(self):
        if not is_admin_enabled():
            self.ids.status_label.text = "Editor disabled (admin key missing)."
            return

        # Copy icon if a file path is provided
        icon_filename = self.ids.topic_icon.text.strip()
        icon_path = self.ids.icon_path.text.strip()
        if icon_path:
            try:
                icon_filename = copy_icon_to_assets(icon_path)
                # ✅ sync UI with saved filename
                self.ids.topic_icon.text = icon_filename

                # ✅ update header icon after saving
                if "header_icon" in self.ids:
                    from kivy.app import App
                    try:
                        self.ids.header_icon.source = App.get_running_app().get_icon_path(icon_filename)
                    except Exception as e:
                        print("DEBUG: header icon update failed:", e)

            except Exception as e:
                self.ids.status_label.text = f"Icon copy failed: {e}"
                return


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

        # ✅ 2. Optional user-provided Topic_ID
        if "topic_id" in self.ids:
            user_id = self.ids.topic_id.text.strip()
            if self.edit_mode and user_id:
                topic["Topic_ID"] = user_id

        if not topic["Category"] or not topic["Title"]:
            self.ids.status_label.text = "Category and Title are required."
            return

        try:
            if self.edit_mode:
                # ✅ keep Firebase key (VERY IMPORTANT)
                topic["_key"] = self.edit_topic_key

                # ✅ keep Topic_ID or updated one
                topic["Topic_ID"] = self.edit_topic_id

                topic_key, topic_id = add_topic_to_firebase(topic, overwrite=True)

            else:
                topic_key, topic_id = add_topic_to_firebase(topic)

            # ✅ FORCE STRING ID (important)
            topic_id = str(topic_id)

            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id

            # ✅ update header icon after save
            if "header_icon" in self.ids:
                from kivy.app import App

                icon_file = self.ids.topic_icon.text.strip()

                if icon_file:
                    try:
                        self.ids.header_icon.source = App.get_running_app().get_icon_path(icon_file)
                    except Exception as e:
                        print("DEBUG: header icon update failed:", e)
                else:
                    self.ids.header_icon.source = App.get_running_app().get_icon_path("howtolinux-icon.png")

            # ✅ Delete old steps (FIXED TYPE)
            from src.services.editor_service import delete_steps_for_topic
            delete_steps_for_topic(topic_id)

            # ✅ Save steps
            for s in self.pending_steps:
                payload = dict(s)
                payload["Topic_ID"] = topic_id
                add_step_to_firebase(payload)

            # ✅ refresh + export backup (FIXED)

            #if not self.edit_mode:
            #    self.reset_form_only()

            # ✅ Keep topic fields so user can continue editing after save
            # Only clear the step entry inputs (not the topic data)
            self.clear_step_form()

            app = App.get_running_app()

            # reload data from Firebase
            app.fetch_database()
            # fetch_database is async -> repopulate menu shortly after
            Clock.schedule_once(lambda dt: app.root.get_screen("menu").populate_menu(), 0.5)

            # ✅ refresh visible UI (IMPORTANT)
            try:
                app.root.get_screen("menu").populate_categories()
            except Exception as e:
                print("UI refresh error:", e)

            # ✅ FIXED EXPORT (no crash anymore)


            app = App.get_running_app()
            export_backup_excel(app.APP_DATA.copy())


            # Reset UI
            #self.pending_steps = []
            self.refresh_steps_preview()
            self.clear_step_form()


            # THEN set ID again
            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id


            self.ids.status_label.text = f"✅ Saved topic + steps (Topic_ID: {str(topic_id)[:8]}…)"

            # ✅ ensure Topic_ID stays visible
            if "topic_id" in self.ids:
                self.ids.topic_id.text = topic_id

            # ✅ mark screen as edit mode after first save
            self.edit_mode = True
            self.edit_topic_id = topic_id
            self.edit_topic_key = topic_key  # returned from add_topic_to_firebase

        except Exception as e:
            self.ids.status_label.text = f"❌ Save failed: {e}"

    def on_kv_post(self, base_widget):
        from kivy.uix.textinput import TextInput

        for widget in self.walk():
            if isinstance(widget, TextInput) and not widget.readonly:
                widget.bind(focus=self._handle_focus)

    def _handle_focus(self, instance, value):

        # ✅ DO NOT disable scrolling anymore
        pass
    def reset_form_only(self):
        self.edit_mode = False
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

        # set icon
        icon_file = data.get("Topic_Icon", "")
        if "header_icon" in self.ids:
            if icon_file:
                try:
                    from kivy.app import App
                    app = App.get_running_app()
                    self.ids.header_icon.source = app.get_icon_path(icon_file)
                except Exception as e:
                    print("DEBUG: icon load failed:", e)
            else:
                from kivy.app import App
                app = App.get_running_app()
                self.ids.header_icon.source = app.get_icon_path("howtolinux-icon.png")

        # load steps
        self.pending_steps = []

        from kivy.app import App
        app = App.get_running_app()

        for step in app.APP_DATA.get("steps", []):
            if step.get("Topic_ID") == data.get("Topic_ID"):
                self.pending_steps.append({
                    "Step_Order": step.get("Step_Order"),
                    "Headline": step.get("Headline"),
                    "Header_2": step.get("Header_2"),
                    "Instruction": step.get("Instruction"),
                    "Code_Snippet": step.get("Code_Snippet"),
                    "Notes": step.get("Notes"),
                })

        self.pending_steps.sort(key=lambda x: int(x.get("Step_Order", 999)))

        # update UI
        self.refresh_steps_preview()
        self.refresh_steps_list()

        # IMPORTANT: rebuild dropdowns AFTER everything is set
        self._schedule_populate_dropdowns()
