from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField


class ModelCreateDialog:
    """Dialog for creating new models with name validation."""

    def __init__(self, on_confirm=None, on_cancel=None, existing_models=None):
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.existing_models = existing_models or []
        
        self.dialog = None
        self.name_field = None

    def update_existing_models(self, models):
        """Update the list of existing models for validation."""
        self.existing_models = models or []

    def show_dialog(self):
        """Show the create model dialog."""
        # Check if dialog is already open
        if self.dialog and self.dialog.parent:
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

        # Create dialog
        self.dialog = MDDialog(
            title="Create New Model",
            type="custom",
            content_cls=self.name_field,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=self._on_cancel_pressed,
                ),
                MDRaisedButton(
                    text="Save",
                    on_release=self._on_save_pressed,
                ),
            ],
        )
        self.dialog.open()

    def close_dialog(self):
        """Close the create model dialog."""
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
            self.name_field = None

    def _on_cancel_pressed(self, *args):
        """Handle cancel button press."""
        if self.on_cancel:
            self.on_cancel()
        self.close_dialog()

    def _on_name_text_changed(self, instance, text):
        """Clear error state when user starts typing."""
        if self.name_field:
            self.name_field.error = False
            self.name_field.helper_text = (
                "Only letters, numbers, and underscores allowed"
            )

    def _on_save_pressed(self, *args):
        """Handle save button press with validation."""
        if not self.name_field:
            return

        model_name = self.name_field.text.strip()

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

        # Check if model already exists
        if model_name in self.existing_models:
            self.name_field.error = True
            self.name_field.helper_text = "Model with this name already exists"
            return

        # Call the confirm callback
        if self.on_confirm:
            success = self.on_confirm(model_name)
            if success is not False:  # Allow None or True
                self.close_dialog()
        else:
            self.close_dialog()
