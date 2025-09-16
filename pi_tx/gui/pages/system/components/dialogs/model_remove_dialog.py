from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton


class ModelRemoveDialog:
    """Dialog for confirming model removal."""

    def __init__(self, on_confirm=None, on_cancel=None):
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.dialog = None
        self.current_model = None

    def show_dialog(self, model_name):
        """Show the remove confirmation dialog for the specified model."""
        self.current_model = model_name
        
        # Create confirmation dialog
        self.dialog = MDDialog(
            title="Remove Model",
            text=f"Are you sure you want to remove the model '{model_name}'?\n\nThis action cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=self._on_cancel_pressed,
                ),
                MDRaisedButton(
                    text="Remove",
                    theme_icon_color="Custom",
                    icon_color="white",
                    md_bg_color="red",
                    on_release=self._on_confirm_pressed,
                ),
            ],
        )
        self.dialog.open()

    def close_dialog(self):
        """Close the remove confirmation dialog."""
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
            self.current_model = None

    def _on_cancel_pressed(self, *args):
        """Handle cancel button press."""
        if self.on_cancel:
            self.on_cancel()
        self.close_dialog()

    def _on_confirm_pressed(self, *args):
        """Handle confirm button press."""
        if self.on_confirm:
            self.on_confirm()
        self.close_dialog()
