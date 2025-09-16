from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.button import MDFloatingActionButton
from kivy.metrics import dp

from .....domain.value_store import value_store
from .dialogs.value_add_dialog import ValueAddDialog
from .dialogs.value_remove_dialog import ValueRemoveDialog


class ValueStoreTab(MDBoxLayout, MDTabsBase):
    """Tab for viewing value store data in read-only mode."""

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

        self._data_table = None
        self._table_data = []
        self._selected_rows = []  # Track multiple selected rows

        # Initialize dialogs
        self._add_dialog = None
        self._remove_dialog = None

        # Create a float layout to contain the table and FAB
        self._float_layout = MDFloatLayout()

        # Create the table immediately
        self._create_data_table()

        # Add FAB for adding new system values
        self._fab = MDFloatingActionButton(
            icon="plus",
            pos_hint={"center_x": 0.9, "center_y": 0.1},
            on_release=self._on_fab_pressed,
        )
        self._float_layout.add_widget(self._fab)

        # Add the float layout to the main container
        self.add_widget(self._float_layout)

        # Initialize FAB state
        self._update_fab_state()

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

    def on_size(self, instance, size):
        """Called when tab size changes (e.g., when becoming active)."""
        # Tab size changed - could be used for responsive behavior
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

    def _refresh_table(self, *args):
        """Refresh the table data and update display."""
        self._update_table_data()
        self._data_table.row_data = self._table_data
        # Clear selection when refreshing
        self._selected_rows = []
        self._update_fab_state()

    def _on_row_selected(self, instance, row):
        """Handle row selection in the data table."""
        try:
            print(f"Row selected (CellRow object): {row} (type: {type(row)})")

            # Since we have built-in checkboxes, we don't need to extract row data here
            # The checkbox handler will handle the actual selection logic
            # This handler can be used for additional row-based logic if needed in the future

        except Exception as e:
            print(f"Error in row selection handler: {e}")

    def _on_checkbox_press(self, instance, current_row):
        """Handle checkbox press events."""
        try:
            print(f"Checkbox pressed for row: {current_row}")

            # Get all currently selected rows from the data table
            # MDDataTable should maintain the list of selected rows internally
            if hasattr(self._data_table, "get_row_checks") and callable(
                self._data_table.get_row_checks
            ):
                self._selected_rows = self._data_table.get_row_checks()
                print(f"All selected rows: {self._selected_rows}")
            else:
                # Fallback: maintain our own list
                if current_row and len(current_row) > 0:
                    # Check if row is already selected
                    if current_row in self._selected_rows:
                        # Remove from selection (unchecked)
                        self._selected_rows.remove(current_row)
                        print(f"Unchecked row: {current_row}")
                    else:
                        # Add to selection (checked)
                        self._selected_rows.append(current_row)
                        print(f"Checked row: {current_row}")

                    print(f"Selected rows: {self._selected_rows}")

            self._update_fab_state()
        except Exception as e:
            print(f"Error in checkbox handler: {e}")
            # Fallback to empty selection on error
            self._selected_rows = []
            self._update_fab_state()

    def _update_fab_state(self):
        """Update FAB icon and functionality based on selection state."""
        try:
            # Check if we have any valid selections (not placeholder rows)
            valid_selections = [
                row
                for row in self._selected_rows
                if (
                    isinstance(row, (list, tuple)) and len(row) > 0 and row[0] != "-"
                )  # Filter out placeholder rows
            ]

            if valid_selections:
                # Change to remove mode
                self._fab.icon = "delete"  # Trash can icon
                self._fab.md_bg_color = (0.9, 0.3, 0.3, 1.0)  # Red color for remove
                print(f"FAB in remove mode - {len(valid_selections)} selected")
            else:
                # Change to add mode
                self._fab.icon = "plus"
                self._fab.md_bg_color = (0.3, 0.6, 0.9, 1.0)  # Blue color for add
                print("FAB in add mode")
        except Exception as e:
            print(f"Error updating FAB state: {e}")
            # Default to add mode on error
            self._fab.icon = "plus"
            self._fab.md_bg_color = (0.3, 0.6, 0.9, 1.0)  # Blue color for add

    def _on_fab_pressed(self, *args):
        """Handle FAB press - either add or remove based on current state."""
        # Check if we have any valid selected rows
        valid_selections = [
            row
            for row in self._selected_rows
            if (
                isinstance(row, (list, tuple)) and len(row) > 0 and row[0] != "-"
            )  # Filter out placeholder rows
        ]

        if valid_selections:
            # Remove mode - show confirmation dialog for multiple rows
            self._show_remove_confirmation(valid_selections)
        else:
            # Add mode - show add dialog
            self._show_add_dialog()

    def _show_add_dialog(self):
        """Show dialog to add new system value."""
        if not self._add_dialog:
            self._add_dialog = ValueAddDialog(
                on_confirm=self._add_system_value,
                on_cancel=lambda: None
            )
        
        self._add_dialog.show_dialog()

    def _show_remove_confirmation(self, selected_rows):
        """Show confirmation dialog for removing selected system values."""
        if not selected_rows:
            print("No rows selected for removal")
            return

        if not self._remove_dialog:
            self._remove_dialog = ValueRemoveDialog(
                on_confirm=self._remove_system_values,
                on_cancel=lambda: None
            )
        
        self._remove_dialog.show_dialog(selected_rows)

    def _add_system_value(self, channel_num):
        """Add a new system value based on user input."""
        try:
            # Add a basic configuration for the channel
            if not hasattr(value_store, "_channel_values"):
                print("Value store not properly initialized")
                return False

            # Create a basic channel configuration
            value_store._channel_values[channel_num] = {
                "control_type": "unipolar",
                "device_path": "manual",
                "control_code": f"manual_{channel_num}",
            }

            # Save the configuration changes
            value_store.save_configuration()

            # Refresh the table to show the new entry
            self._refresh_table()

            print(f"Added system value for channel {channel_num}")
            return True

        except Exception as e:
            print(f"Error adding system value: {e}")
            return False

    def _remove_system_values(self, selected_rows):
        """Remove multiple selected system values."""
        try:
            if not selected_rows:
                print("No rows selected for removal")
                return

            removed_channels = []
            failed_removals = []

            # Process each selected row
            for row in selected_rows:
                try:
                    if isinstance(row, (list, tuple)) and len(row) > 0:
                        row_id = row[0]  # ID column at index 0
                    else:
                        print(f"Invalid row selection format: {row}")
                        failed_removals.append(str(row))
                        continue

                    if row_id and row_id.startswith("var"):
                        channel_num = int(row_id[3:])  # Remove "var" prefix

                        # Remove the channel configuration from value store
                        if (
                            hasattr(value_store, "_channel_values")
                            and channel_num in value_store._channel_values
                        ):
                            del value_store._channel_values[channel_num]

                        # Reset the reverse flag to default
                        value_store.set_reverse(channel_num, False)

                        # Save the configuration changes
                        value_store.save_configuration()

                        removed_channels.append(channel_num)
                        print(f"Removed system value for channel {channel_num}")
                    else:
                        print(f"Cannot determine channel number from row ID: {row_id}")
                        failed_removals.append(row_id)

                except (ValueError, IndexError) as e:
                    print(f"Error processing row {row}: {e}")
                    failed_removals.append(str(row))
                    continue

            # Clear all selections
            self._selected_rows = []

            # Refresh the table to remove the entries
            self._refresh_table()

            # Update FAB state after clearing selections
            self._update_fab_state()

            # Report results
            if removed_channels:
                print(
                    f"Successfully removed {len(removed_channels)} system values: channels {removed_channels}"
                )
            if failed_removals:
                print(
                    f"Failed to remove {len(failed_removals)} items: {failed_removals}"
                )

            return True

        except Exception as e:
            print(f"Error removing system values: {e}")
            return False
