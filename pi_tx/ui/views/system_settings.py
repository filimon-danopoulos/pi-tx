from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDSeparator, MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import (
    MDFlatButton,
    MDRaisedButton,
    MDIconButton,
    MDFloatingActionButton,
)
from kivymd.uix.textfield import MDTextField
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.metrics import dp
import uuid
import json
import os
from pathlib import Path

from ...domain.value_store import value_store


class ModelsTab(MDBoxLayout, MDTabsBase):
    """Tab for model selection and management."""

    def __init__(self, app=None, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "Models"
        self.icon = "folder-multiple"
        self.app = app

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

        # Create confirmation dialog
        self.remove_dialog = MDDialog(
            title="Remove Model",
            text=f"Are you sure you want to remove the model '{selected_model}'?\n\nThis action cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=self._close_remove_dialog,
                ),
                MDRaisedButton(
                    text="Remove",
                    theme_icon_color="Custom",
                    icon_color="white",
                    md_bg_color="red",
                    on_release=self._remove_selected_model,
                ),
            ],
        )
        self.remove_dialog.open()

    def _close_remove_dialog(self, button_instance):
        """Close the remove model dialog."""
        if hasattr(self, "remove_dialog") and self.remove_dialog:
            self.remove_dialog.dismiss()
            self.remove_dialog = None
        return True

    def _remove_selected_model(self, button_instance):
        """Remove the currently selected model."""
        if (
            not self.app
            or not hasattr(self.app, "selected_model")
            or not self.app.selected_model
        ):
            self._close_remove_dialog(button_instance)
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

        self._close_remove_dialog(button_instance)

    def _show_create_model_dialog(self, *args):
        """Show a dialog to create a new model with name input."""
        # Check if dialog is already open
        if (
            hasattr(self, "create_dialog")
            and self.create_dialog
            and self.create_dialog.parent
        ):
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
        self.create_dialog = MDDialog(
            title="Create New Model",
            type="custom",
            content_cls=self.name_field,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=self._close_create_dialog,
                ),
                MDRaisedButton(
                    text="Save",
                    on_release=self._save_new_model,
                ),
            ],
        )
        self.create_dialog.open()

    def _close_create_dialog(self, button_instance):
        """Close the create model dialog."""
        if hasattr(self, "create_dialog") and self.create_dialog:
            self.create_dialog.dismiss()
            self.create_dialog = None
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
        if model_name in self.app.available_models:
            self.name_field.error = True
            self.name_field.helper_text = "Model with this name already exists"
            return

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

            with open(model_file, "w") as f:
                json.dump(model_data, f, indent=2)

            # Refresh the app's model list and UI
            self.app.refresh_models()
            self.refresh_models()

            # Close the dialog
            self._close_create_dialog(button_instance)

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
        self._selected_row = None
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
        # Create a simple dialog for adding system values
        if not hasattr(self, "_add_dialog") or not self._add_dialog:
            # Create text field for channel input
            self._channel_field = MDTextField(
                hint_text="Channel number (1-16)",
                helper_text="Enter a channel number between 1 and 16",
                helper_text_mode="persistent",
                size_hint_x=None,
                width=dp(200),
            )

            # Create the dialog
            self._add_dialog = MDDialog(
                title="Add System Value",
                type="custom",
                content_cls=self._channel_field,
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_release=lambda *args: self._add_dialog.dismiss(),
                    ),
                    MDRaisedButton(text="ADD", on_release=self._add_system_value),
                ],
            )

        self._add_dialog.open()

    def _show_remove_confirmation(self, selected_rows):
        """Show confirmation dialog for removing selected system values."""
        if not selected_rows:
            print("No rows selected for removal")
            return

        try:
            # Create list of row IDs to display in confirmation
            row_ids = []
            for row in selected_rows:
                if isinstance(row, (list, tuple)) and len(row) > 0:
                    row_ids.append(row[0])  # ID column at index 0
                else:
                    print(f"Invalid row selection format: {row}")
                    return

            if not row_ids:
                print("No valid rows to remove")
                return

            # Create confirmation message
            if len(row_ids) == 1:
                confirmation_text = f"Are you sure you want to remove {row_ids[0]}?"
            else:
                row_list = ", ".join(row_ids)
                confirmation_text = f"Are you sure you want to remove {len(row_ids)} system values?\n\n{row_list}"

        except Exception as e:
            print(f"Error processing selected rows: {e}")
            return

        if not hasattr(self, "_remove_dialog") or not self._remove_dialog:
            self._remove_dialog = MDDialog(
                title="Remove System Values",
                text=confirmation_text,
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_release=lambda *args: self._remove_dialog.dismiss(),
                    ),
                    MDRaisedButton(
                        text="REMOVE ALL" if len(row_ids) > 1 else "REMOVE",
                        md_bg_color=(0.9, 0.3, 0.3, 1.0),  # Red color
                        on_release=lambda *args: self._remove_system_values(
                            selected_rows
                        ),
                    ),
                ],
            )
        else:
            # Update the dialog for current selections
            self._remove_dialog.title = "Remove System Values"
            self._remove_dialog.text = confirmation_text
            # Update button text
            for button in self._remove_dialog.buttons:
                if hasattr(button, "text") and "REMOVE" in button.text:
                    button.text = "REMOVE ALL" if len(row_ids) > 1 else "REMOVE"
                    button.on_release = lambda *args: self._remove_system_values(
                        selected_rows
                    )

        self._remove_dialog.open()

    def _add_system_value(self, *args):
        """Add a new system value based on user input."""
        try:
            channel_text = self._channel_field.text.strip()
            if not channel_text:
                print("No channel number entered")
                return

            channel_num = int(channel_text)
            if not (1 <= channel_num <= 16):
                print(f"Invalid channel number: {channel_num}. Must be 1-16")
                return

            # Add a basic configuration for the channel
            if not hasattr(value_store, "_channel_values"):
                print("Value store not properly initialized")
                return

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

            # Close the dialog
            self._add_dialog.dismiss()

            print(f"Added system value for channel {channel_num}")

        except ValueError:
            print(f"Invalid channel number: {self._channel_field.text}")
        except Exception as e:
            print(f"Error adding system value: {e}")

    def _remove_system_value(self, *args):
        """Remove the selected system value."""
        try:
            if not self._selected_row:
                print("No row selected for removal")
                return

            # Extract channel number from row ID (e.g., "var5" -> 5)
            # ID column is back at index 0 (using built-in checkboxes)
            if (
                isinstance(self._selected_row, (list, tuple))
                and len(self._selected_row) > 0
            ):
                row_id = self._selected_row[0]  # ID column back at index 0
            else:
                print(f"Invalid row selection format: {self._selected_row}")
                return

            if row_id and row_id.startswith("var"):
                channel_num = int(row_id[3:])  # Remove "var" prefix
            else:
                print(f"Cannot determine channel number from row ID: {row_id}")
                return

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

            # Clear selection
            self._selected_row = None

            # Refresh the table to remove the entry
            self._refresh_table()

            # Close the dialog
            self._remove_dialog.dismiss()

            print(f"Removed system value for channel {channel_num}")

        except ValueError as e:
            print(f"Error parsing channel number: {e}")
        except Exception as e:
            print(f"Error removing system value: {e}")

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

            # Close the dialog
            self._remove_dialog.dismiss()

            # Report results
            if removed_channels:
                print(
                    f"Successfully removed {len(removed_channels)} system values: channels {removed_channels}"
                )
            if failed_removals:
                print(
                    f"Failed to remove {len(failed_removals)} items: {failed_removals}"
                )

        except Exception as e:
            print(f"Error removing system values: {e}")


class GeneralTab(MDBoxLayout, MDTabsBase):
    """Tab for general system settings."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "General"
        self.icon = "cog"

        # Placeholder content for future system settings
        self.add_widget(
            MDLabel(
                text="General system settings coming soon...\n\n• Serial/UART configuration\n• Input device selection\n• Theme settings\n• Logging options",
                halign="left",
                valign="top",
            )
        )


class SystemSettingsView(MDBoxLayout):
    """System-wide settings with tabbed interface.

    Features:
      - Model management in Models tab
      - General system settings in General tab
    """

    def __init__(self, app=None, **kwargs):
        super().__init__(orientation="vertical", padding=0, spacing=0, **kwargs)
        self.app = app
        # Ensure this view fills available space
        self.size_hint = (1, 1)

        # Create tabs with explicit sizing
        self._tabs = MDTabs(size_hint=(1, 1))

        # Create tab instances
        self._models_tab = ModelsTab(app=app)
        self._value_store_tab = ValueStoreTab()
        self._general_tab = GeneralTab()

        # Add tabs to the tab widget
        self._tabs.add_widget(self._models_tab)
        self._tabs.add_widget(self._value_store_tab)
        self._tabs.add_widget(self._general_tab)

        # Add tabs to main container
        self.add_widget(self._tabs)

    def set_app(self, app):
        """Set the app reference after initialization."""
        self.app = app
        self._models_tab.set_app(app)

    def refresh_models(self):
        """Refresh the model list display."""
        if self._models_tab:
            self._models_tab.refresh_models()
