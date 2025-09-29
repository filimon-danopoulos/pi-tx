from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.metrics import dp

from .....domain.value_store import value_store
from .....logging_config import get_logger
from .dialogs.value_add_dialog import ValueAddDialog
from .dialogs.value_remove_dialog import ValueRemoveDialog


class ValueStoreTab(MDBoxLayout, MDTabsBase):
    """Tab for viewing value store data in read-only mode (FAB removed)."""

    # Required properties for MDTabsBase
    icon = "table"
    title = "System Values"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 0
        self.padding = 0
        # Ensure tab fills available space
        self.size_hint = (1, 1)

        # Logger
        self._log = get_logger(__name__)

        # Table and selection state
        self._data_table = None
        self._table_data = []
        self._selected_rows = []  # Track multiple selected rows
        # Dialog references
        self._add_dialog = None
        self._remove_dialog = None

        # Layout container (previously held FAB; now table only)
        self._float_layout = MDFloatLayout()

        # Create the table immediately
        self._create_data_table()

        # Add the float layout to the main container
        self.add_widget(self._float_layout)

    def _create_data_table(self):
        """Create the data table as the only content."""
        # Prepare table data
        self._table_data = []
        self._update_table_data()

        # Create data table with dynamic sizing based on configured channels
        num_rows = len(self._table_data)
        # Use a reasonable limit for visible rows - max 15 on 480px screen
        visible_rows = min(num_rows, 15)

        self._data_table = MDDataTable(
            use_pagination=False,
            check=True,  # Enable built-in checkboxes
            rows_num=visible_rows,  # Dynamic based on actual data
            column_data=[
                ("Id", dp(20)),
                ("Device", dp(35)),
                ("Control", dp(30)),
                ("Type", dp(30)),
                ("Reversed", dp(25)),
            ],
            row_data=self._table_data,
        )

        # Bind to row selection and checkbox events
        self._data_table.bind(on_row_press=self._on_row_selected)
        self._data_table.bind(on_check_press=self._on_checkbox_press)

        # Add table to the float layout instead of directly to the tab
        self._float_layout.add_widget(self._data_table)

    def on_size(self, instance, size):  # noqa: D401 (simple handler)
        """Called when tab size changes (unused)."""
        pass

    def _update_table_data(self):
        """Update the table data with current value store state."""
        self._table_data.clear()

        # Only show channels that have some configuration or non-default values
        for ch in range(1, value_store.size() + 1):
            ch_type = value_store.get_channel_type(ch)
            is_reversed = value_store.is_reversed(ch)

            # Skip channels with all default values (unipolar, not reversed)
            has_config = (
                ch_type != "unipolar"  # Non-default channel type
                or is_reversed  # Channel is reversed
            )

            # Only add channels that have some meaningful configuration
            if has_config:
                device_name = value_store.get_device_name(ch)
                control_name = value_store.get_control_name(ch)
                row_id = f"var{ch}"

                # Create row data (no manual checkbox column needed)
                self._table_data.append(
                    (
                        row_id,  # Id column (first)
                        device_name,  # Device column
                        control_name,  # Control column
                        ch_type,  # Type column
                        "Yes" if is_reversed else "No",  # Reversed column
                    )
                )

        # If no channels have configuration, show a placeholder message
        if not self._table_data:
            self._table_data.append(
                (
                    "-",
                    "No configured channels",
                    "-",
                    "-",
                    "-",
                )
            )

    def _refresh_table(self, *args):  # noqa: D401
        """Refresh the table data and update display."""
        self._update_table_data()
        self._data_table.row_data = self._table_data
        # Clear selection when refreshing
        self._selected_rows = []

    def _on_row_selected(self, instance, row):  # noqa: D401
        """Handle row selection in the data table (no extra logic)."""
        try:
            self._log.debug("Row selected: %s (type: %s)", row, type(row))
        except Exception as e:  # pragma: no cover - defensive
            self._log.warning("Row selection handler error: %s", e)

    def _on_checkbox_press(self, instance, current_row):  # noqa: D401
        """Handle checkbox press events."""
        try:
            self._log.debug("Checkbox pressed: %s", current_row)

            if hasattr(self._data_table, "get_row_checks") and callable(
                self._data_table.get_row_checks
            ):
                self._selected_rows = self._data_table.get_row_checks()
                self._log.debug("All selected rows: %s", self._selected_rows)
            else:
                if current_row and len(current_row) > 0:
                    if current_row in self._selected_rows:
                        self._selected_rows.remove(current_row)
                        self._log.debug("Unchecked row: %s", current_row)
                    else:
                        self._selected_rows.append(current_row)
                        self._log.debug("Checked row: %s", current_row)
                    self._log.debug("Selected rows: %s", self._selected_rows)

        except Exception as e:  # pragma: no cover - defensive
            self._log.warning("Checkbox handler error: %s", e)
            self._selected_rows = []

    def _show_add_dialog(self):
        """Show dialog to add new system value."""
        if not self._add_dialog:
            self._add_dialog = ValueAddDialog(
                on_confirm=self._add_system_value,
                on_cancel=lambda: None,
            )
        self._add_dialog.show_dialog()

    def _show_remove_confirmation(self, selected_rows):
        """Show confirmation dialog for removing selected system values."""
        if not selected_rows:
            self._log.info("No rows selected for removal")
            return

        if not self._remove_dialog:
            self._remove_dialog = ValueRemoveDialog(
                on_confirm=self._remove_system_values,
                on_cancel=lambda: None,
            )
        self._remove_dialog.show_dialog(selected_rows)

    def _add_system_value(self, channel_num):
        """Add a new system value based on user input."""
        try:
            if not hasattr(value_store, "_channel_values"):
                self._log.error("Value store not initialized")
                return False

            value_store._channel_values[channel_num] = {  # type: ignore[attr-defined]
                "control_type": "unipolar",
                "device_path": "manual",
                "control_code": f"manual_{channel_num}",
            }
            value_store.save_configuration()
            self._refresh_table()
            self._log.info("Added system value for channel %s", channel_num)
            return True
        except Exception as e:  # pragma: no cover - defensive
            self._log.error("Error adding system value: %s", e)
            return False

    def _remove_system_values(self, selected_rows):
        """Remove multiple selected system values."""
        try:
            if not selected_rows:
                self._log.info("No rows selected for removal")
                return

            removed_channels = []
            failed_removals = []

            for row in selected_rows:
                try:
                    if isinstance(row, (list, tuple)) and len(row) > 0:
                        row_id = row[0]
                    else:
                        self._log.warning("Invalid row selection format: %s", row)
                        failed_removals.append(str(row))
                        continue

                    if row_id and isinstance(row_id, str) and row_id.startswith("var"):
                        channel_num = int(row_id[3:])
                        if (
                            hasattr(value_store, "_channel_values")
                            and channel_num in value_store._channel_values  # type: ignore[attr-defined]
                        ):
                            del value_store._channel_values[channel_num]  # type: ignore[attr-defined]
                        value_store.set_reverse(channel_num, False)
                        value_store.save_configuration()
                        removed_channels.append(channel_num)
                        self._log.info(
                            "Removed system value for channel %s", channel_num
                        )
                    else:
                        self._log.warning(
                            "Cannot determine channel number from row ID: %s", row_id
                        )
                        failed_removals.append(str(row_id))
                except (ValueError, IndexError) as e:
                    self._log.warning("Error processing row %s: %s", row, e)
                    failed_removals.append(str(row))
                    continue

            self._selected_rows = []
            self._refresh_table()

            if removed_channels:
                self._log.info(
                    "Removed %d system values: %s",
                    len(removed_channels),
                    removed_channels,
                )
            if failed_removals:
                self._log.warning(
                    "Failed to remove %d items: %s",
                    len(failed_removals),
                    failed_removals,
                )
            return True
        except Exception as e:  # pragma: no cover - defensive
            self._log.error("Error removing system values: %s", e)
            return False

    # New action provider for global FAB menu
    def get_actions(self):  # pragma: no cover (UI integration)
        """Return list of unique action dicts for this tab.

        Each action: { 'text': str, 'callback': callable }
        Text values are unique across tabs for testing.
        """
        return [
            {"text": "Values: Add", "callback": self._show_add_dialog, "icon": "plus"},
            {
                "text": "Values: Remove Selected",
                "callback": lambda: self._show_remove_confirmation(self._selected_rows),
                "icon": "delete",
            },
            {
                "text": "Values: Refresh",
                "callback": self._refresh_table,
                "icon": "refresh",
            },
        ]
