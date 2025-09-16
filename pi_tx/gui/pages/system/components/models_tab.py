from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.tab import MDTabsBase
from kivy.metrics import dp
import uuid
from pathlib import Path

from .dialogs.model_create_dialog import ModelCreateDialog
from .dialogs.model_remove_dialog import ModelRemoveDialog
from .....infrastructure.file_cache import load_json, save_json


class ModelsTab(MDBoxLayout, MDTabsBase):
    """Tab for model selection and management."""

    def __init__(self, app=None, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "Models"
        self.icon = "folder-multiple"
        self.app = app

        # Initialize dialog references
        self.remove_dialog = None
        self.create_dialog = None

        # Button row
        button_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=8,
        )

        # Remove model button
        self.remove_button = MDRaisedButton(
            text="Remove Selected",
            icon="delete",
            theme_icon_color="Custom",
            icon_color="white",
            md_bg_color="red",
            on_release=self._show_remove_model_dialog,
            disabled=True,  # Initially disabled until a model is selected
        )

        # Create model button
        self.create_button = MDRaisedButton(
            text="Create New",
            icon="plus",
            theme_icon_color="Custom",
            icon_color="white",
            on_release=self._show_create_model_dialog,
        )

        button_layout.add_widget(self.remove_button)
        button_layout.add_widget(MDLabel())  # Spacer
        button_layout.add_widget(self.create_button)
        self.add_widget(button_layout)

        # Model list card
        model_card = MDCard(
            orientation="vertical",
            size_hint_y=1,
            padding=8,
            spacing=4,
            elevation=2,
        )

        self._model_list = MDList()
        scroll = MDScrollView()
        scroll.add_widget(self._model_list)
        model_card.add_widget(scroll)
        self.add_widget(model_card)

    def set_app(self, app):
        """Set the app reference after initialization."""
        self.app = app
        self.refresh_models()
        if hasattr(app, "bind"):
            app.bind(on_model_selected=self._on_model_changed)

    def refresh_models(self):
        """Refresh the model list display."""
        if not self.app:
            return

        self._model_list.clear_widgets()

        # Get available models
        if not self.app.available_models:
            self.app.refresh_models()

        # Get currently selected model for highlighting
        current_model = getattr(self.app, "selected_model", "")

        # Update remove button state based on selection
        self.remove_button.disabled = not current_model

        for name in self.app.available_models:
            # Use a proper closure to capture the current name value
            def create_selection_handler(model_name):
                def handler(*args):
                    self.app.select_model(model_name)

                return handler

            # Create list item with visual indication of current selection
            item = OneLineListItem(text=name, on_release=create_selection_handler(name))

            # Highlight currently selected model
            if name == current_model:
                item.theme_text_color = "Custom"
                item.text_color = item.theme_cls.primary_color

            self._model_list.add_widget(item)

    def _on_model_changed(self, app, model_name):
        """Called when a model is selected to refresh the display."""
        self.refresh_models()

    def _show_remove_model_dialog(self, *args):
        """Show confirmation dialog to remove the selected model."""
        if (
            not self.app
            or not hasattr(self.app, "selected_model")
            or not self.app.selected_model
        ):
            return

        selected_model = self.app.selected_model

        # Create dialog if it doesn't exist
        if not self.remove_dialog:
            self.remove_dialog = ModelRemoveDialog(
                on_confirm=self._remove_selected_model,
                on_cancel=self._close_remove_dialog
            )
        
        self.remove_dialog.show_dialog(selected_model)

    def _close_remove_dialog(self, *args):
        """Close the remove model dialog."""
        if self.remove_dialog:
            self.remove_dialog.close_dialog()
        return True

    def _remove_selected_model(self, *args):
        """Remove the currently selected model."""
        if (
            not self.app
            or not hasattr(self.app, "selected_model")
            or not self.app.selected_model
        ):
            self._close_remove_dialog()
            return

        try:
            model_name = self.app.selected_model
            model_file = Path("models") / f"{model_name}.json"

            if model_file.exists():
                model_file.unlink()  # Delete the file

                # Clear current selection
                self.app.selected_model = ""
                self.app._current_model = None

                # Refresh model lists
                self.app.refresh_models()
                self.refresh_models()

                # Try to auto-load another model if available
                if self.app.available_models:
                    # Select the first available model
                    first_model = self.app.available_models[0]
                    self.app.select_model(first_model)

        except Exception as e:
            print(f"Error removing model: {e}")

        self._close_remove_dialog()

    def _show_create_model_dialog(self, *args):
        """Show a dialog to create a new model with name input."""
        # Create dialog if it doesn't exist
        if not self.create_dialog:
            self.create_dialog = ModelCreateDialog(
                on_confirm=self._save_new_model,
                on_cancel=self._close_create_dialog,
                existing_models=self.app.available_models if self.app else []
            )
        
        # Update existing models list
        if self.app:
            self.create_dialog.update_existing_models(self.app.available_models)
        
        self.create_dialog.show_dialog()

    def _close_create_dialog(self, *args):
        """Close the create model dialog."""
        if self.create_dialog:
            self.create_dialog.close_dialog()
        return True

    def _save_new_model(self, model_name):
        """Save the new model with the entered name."""
        try:
            # Create model data
            model_data = {
                "name": model_name,
                "model_index": self._allocate_model_index(),
                "rx_num": self._allocate_rx_num(),
                "id": str(uuid.uuid4()),
                "channels": {},
            }

            # Save to file
            models_dir = Path("models")
            models_dir.mkdir(exist_ok=True)
            model_file = models_dir / f"{model_name}.json"

            save_json(str(model_file), model_data)

            # Refresh the app's model list and UI
            self.app.refresh_models()
            self.refresh_models()

            # Close the dialog
            self._close_create_dialog()

        except Exception as e:
            print(f"Error saving model: {str(e)}")
            # The dialog will handle displaying this error
            return False
        
        return True

    def _allocate_rx_num(self):
        """Allocate an unused RX number (0-15)."""
        used = set()
        models_dir = Path("models")
        if models_dir.exists():
            for model_file in models_dir.glob("*.json"):
                try:
                    data = load_json(str(model_file))
                    if data and "rx_num" in data:
                        used.add(int(data["rx_num"]))
                except Exception:
                    continue

        for rx_num in range(16):  # 0-15
            if rx_num not in used:
                return rx_num
        return 0  # Fallback

    def _allocate_model_index(self):
        """Allocate a unique model index."""
        used = set()
        models_dir = Path("models")
        if models_dir.exists():
            for model_file in models_dir.glob("*.json"):
                try:
                    data = load_json(str(model_file))
                    if data and "model_index" in data:
                        used.add(int(data["model_index"]))
                except Exception:
                    continue

        idx = 1
        while idx in used:
            idx += 1
        return idx
