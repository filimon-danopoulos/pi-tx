from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivy.metrics import dp


class ValueAddDialog:
    """Dialog for adding new system values."""

    def __init__(self, on_confirm=None, on_cancel=None):
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.dialog = None
        self.channel_field = None

    def show_dialog(self):
        """Show the add system value dialog."""
        # Create text field for channel input
        self.channel_field = MDTextField(
            hint_text="Channel number (1-16)",
            helper_text="Enter a channel number between 1 and 16",
            helper_text_mode="persistent",
            size_hint_x=None,
            width=dp(200),
        )

        # Create the dialog
        self.dialog = MDDialog(
            title="Add System Value",
            type="custom",
            content_cls=self.channel_field,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=self._on_cancel_pressed,
                ),
                MDRaisedButton(
                    text="ADD", 
                    on_release=self._on_add_pressed
                ),
            ],
        )

        self.dialog.open()

    def close_dialog(self):
        """Close the add dialog."""
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
            self.channel_field = None

    def _on_cancel_pressed(self, *args):
        """Handle cancel button press."""
        if self.on_cancel:
            self.on_cancel()
        self.close_dialog()

    def _on_add_pressed(self, *args):
        """Handle add button press with validation."""
        if not self.channel_field:
            return

        try:
            channel_text = self.channel_field.text.strip()
            if not channel_text:
                self.channel_field.error = True
                self.channel_field.helper_text = "Channel number is required"
                return

            channel_num = int(channel_text)
            if not (1 <= channel_num <= 16):
                self.channel_field.error = True
                self.channel_field.helper_text = "Channel number must be between 1 and 16"
                return

            # Call the confirm callback
            if self.on_confirm:
                success = self.on_confirm(channel_num)
                if success is not False:  # Allow None or True
                    self.close_dialog()
                else:
                    self.channel_field.error = True
                    self.channel_field.helper_text = "Failed to add system value"
            else:
                self.close_dialog()

        except ValueError:
            self.channel_field.error = True
            self.channel_field.helper_text = "Please enter a valid number"
