from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDSeparator
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
import uuid
import json
from pathlib import Path


class LeftDrawer(MDNavigationDrawer):
    """Simple left navigation drawer hosting settings & model actions."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        # Set drawer width and anchor
        self.width = "240dp"  # Set explicit width
        self.anchor = "left"  # Ensure it's left-anchored
        container = MDBoxLayout(orientation="vertical", padding=8, spacing=8)
        self._list = MDList()
        scroll = MDScrollView()
        scroll.add_widget(self._list)
        container.add_widget(scroll)
        self.add_widget(container)

        # Listen for model selection changes to refresh the display
        if hasattr(app, "bind"):
            app.bind(on_model_selected=self._on_model_changed)

        self.refresh()

    def refresh(self):
        self._list.clear_widgets()

        # Model section header (simple as item)
        if not self.app.available_models:
            self.app.refresh_models()

        # Get currently selected model for highlighting
        current_model = getattr(self.app, "selected_model", "")

        for name in self.app.available_models:
            # Use a proper closure to capture the current name value
            def create_selection_handler(model_name):
                def handler(*args):
                    self.app.select_model(model_name)
                    self.set_state("close")

                return handler

            # Create list item with visual indication of current selection
            item_text = name
            item = OneLineListItem(
                text=item_text, on_release=create_selection_handler(name)
            )

            # Highlight currently selected model
            if name == current_model:
                item.theme_text_color = "Custom"
                item.text_color = item.theme_cls.primary_color

            self._list.add_widget(item)

        # Add dividing line
        separator = MDSeparator()
        self._list.add_widget(separator)

        # Add create model button
        create_button = OneLineListItem(
            text="Create New Model", on_release=self._show_simple_dialog
        )
        create_button.theme_text_color = "Custom"
        create_button.text_color = create_button.theme_cls.primary_color
        self._list.add_widget(create_button)

    def _open_system(self):
        # Switch navigation rail to system tab if available
        if hasattr(self.app, "_navigation_rail") and self.app._navigation_rail:
            try:
                self.app._navigation_rail.switch_to_tab("system")
            except Exception:
                pass
        self.set_state("close")

    def _on_model_changed(self, app, model_name):
        """Called when a model is selected to refresh the drawer display."""
        # Only refresh if we're not currently closing/opening
        if hasattr(self, "state") and self.state in ("close", "open"):
            self.refresh()

    def _show_simple_dialog(self, *args):
        """Show a dialog to create a new model with name input."""
        # Debug: Check if dialog is already open to prevent double-calling
        if (
            hasattr(self, "test_dialog")
            and self.test_dialog
            and self.test_dialog.parent
        ):
            # Dialog is already open, ignore this call
            return

        # Create text field for model name
        self.name_field = MDTextField(
            hint_text="Enter model name",
            helper_text="Only letters, numbers, and underscores allowed",
            helper_text_mode="on_focus",
            size_hint_y=None,
            height="56dp",
        )

        # Clear error when user starts typing
        self.name_field.bind(text=self._on_name_text_changed)

        # Create dialog with name input and buttons
        self.test_dialog = MDDialog(
            title="Create New Model",
            type="custom",
            content_cls=self.name_field,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=self._close_simple_dialog,
                ),
                MDRaisedButton(
                    text="Save",
                    on_release=self._save_new_model,
                ),
            ],
        )
        self.test_dialog.open()

    def _close_simple_dialog(self, button_instance):
        """Close the simple dialog."""
        # Simple, direct dismissal - exactly as shown in KivyMD examples
        if hasattr(self, "test_dialog") and self.test_dialog:
            self.test_dialog.dismiss()
            self.test_dialog = None
        # Return True to indicate the event was handled and prevent propagation
        return True

    def _on_name_text_changed(self, instance, text):
        """Clear error state when user starts typing."""
        if hasattr(self, "name_field") and self.name_field:
            self.name_field.error = False
            self.name_field.helper_text = (
                "Only letters, numbers, and underscores allowed"
            )

    def _save_new_model(self, button_instance):
        """Save the new model with the entered name."""
        if not hasattr(self, "name_field") or not self.name_field:
            return

        model_name = self.name_field.text.strip()

        # Debug: print the actual text to see what we're getting
        print(f"Debug: Model name entered: '{model_name}' (length: {len(model_name)})")
        print(f"Debug: After replacing underscores: '{model_name.replace('_', '')}'")
        print(f"Debug: isalnum check: {model_name.replace('_', '').isalnum()}")

        # Validate model name
        if not model_name:
            self.name_field.error = True
            self.name_field.helper_text = "Model name is required"
            return

        # Check if name contains only letters, numbers, and underscores
        if not all(c.isalnum() or c == "_" for c in model_name):
            self.name_field.error = True
            self.name_field.helper_text = (
                "Only letters, numbers, and underscores allowed"
            )
            return

        if model_name in self.app.available_models:
            self.name_field.error = True
            self.name_field.helper_text = "Model name already exists"
            return

        # Create the basic model structure
        model_data = {
            "name": model_name,
            "model_id": uuid.uuid4().hex,
            "rx_num": self._allocate_rx_num(),
            "model_index": self._allocate_model_index(),
            "channels": {},
            "processors": {},
        }

        # Save the model to JSON file
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        model_file = models_dir / f"{model_name}.json"

        try:
            with open(model_file, "w") as f:
                json.dump(model_data, f, indent=2)

            # Refresh the app's model list and UI
            self.app.refresh_models()
            self.refresh()

            # Close the dialog
            self._close_simple_dialog(button_instance)

        except Exception as e:
            self.name_field.error = True
            self.name_field.helper_text = f"Error saving model: {str(e)}"

    def _allocate_rx_num(self):
        """Allocate an unused RX number (0-15)."""
        used = set()
        models_dir = Path("models")
        if models_dir.exists():
            for model_file in models_dir.glob("*.json"):
                try:
                    with open(model_file, "r") as f:
                        data = json.load(f)
                    if "rx_num" in data:
                        used.add(int(data["rx_num"]))
                except Exception:
                    continue

        for i in range(16):
            if i not in used:
                return i
        return 0  # fallback

    def _allocate_model_index(self):
        """Allocate a unique model index."""
        used = set()
        models_dir = Path("models")
        if models_dir.exists():
            for model_file in models_dir.glob("*.json"):
                try:
                    with open(model_file, "r") as f:
                        data = json.load(f)
                    if "model_index" in data:
                        used.add(int(data["model_index"]))
                except Exception:
                    continue

        idx = 1
        while idx in used:
            idx += 1
        return idx
