from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from ......logging_config import get_logger


class ValueRemoveDialog:
    """Dialog for confirming removal of system values."""

    def __init__(self, on_confirm=None, on_cancel=None):
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.dialog = None
        self.selected_rows = None
        self._log = get_logger(__name__)

    def show_dialog(self, selected_rows):
        """Show the remove confirmation dialog for selected system values."""
        if not selected_rows:
            self._log.info("No rows selected for removal")
            return

        self.selected_rows = selected_rows

        try:
            # Create list of row IDs to display in confirmation
            row_ids = []
            for row in selected_rows:
                if isinstance(row, (list, tuple)) and len(row) > 0:
                    row_ids.append(row[0])  # ID column at index 0
                else:
                    self._log.warning("Invalid row selection format: %s", row)
                    return

            if not row_ids:
                self._log.info("No valid rows to remove")
                return

            # Create confirmation message
            if len(row_ids) == 1:
                confirmation_text = f"Are you sure you want to remove {row_ids[0]}?"
            else:
                row_list = ", ".join(row_ids)
                confirmation_text = f"Are you sure you want to remove {len(row_ids)} system values?\n\n{row_list}"

        except Exception as e:
            self._log.error("Error processing selected rows: %s", e)
            return

        # Create confirmation dialog
        self.dialog = MDDialog(
            title="Remove System Values",
            text=confirmation_text,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=self._on_cancel_pressed,
                ),
                MDRaisedButton(
                    text="REMOVE ALL" if len(row_ids) > 1 else "REMOVE",
                    md_bg_color=(0.9, 0.3, 0.3, 1.0),  # Red color
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
            self.selected_rows = None

    def _on_cancel_pressed(self, *args):
        """Handle cancel button press."""
        if self.on_cancel:
            self.on_cancel()
        self.close_dialog()

    def _on_confirm_pressed(self, *args):
        """Handle confirm button press."""
        if self.on_confirm and self.selected_rows:
            self.on_confirm(self.selected_rows)
        self.close_dialog()
