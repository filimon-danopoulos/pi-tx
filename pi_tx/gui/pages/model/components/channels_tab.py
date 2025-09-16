from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.tab import MDTabsBase
from kivy.metrics import dp
import json

from .....config.settings import STICK_MAPPING_FILE


class ChannelsTab(MDBoxLayout, MDTabsBase):
    """Tab containing the channels data table."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=0, **kwargs)
        self.title = "Channels"
        self.icon = "view-list"
        
        self._data_table = None
        self._table_data = []
        self._current_model = None

    def set_model(self, model, model_manager):
        """Set the current model and model manager reference."""
        self._current_model = model
        self._model_manager = model_manager
        self._create_channels_table()

    def refresh_table(self):
        """Refresh the table data and update display."""
        if self._data_table:
            self._update_table_data()
            self._data_table.row_data = self._table_data

    def _refresh_content(self):
        """Rebuild the content with channel data table."""
        # Clear all widgets
        self.clear_widgets()
        
        if not self._current_model:
            self._show_error("No model selected")
            return

        # Create the channels table
        self._create_channels_table()

    def _create_channels_table(self):
        """Create and display the channels data table."""
        # Prepare table data
        self._table_data = []
        self._update_table_data()

        # Create data table with dynamic sizing based on configured channels
        num_rows = len(self._table_data)
        # Use a reasonable limit for visible rows - max 15 on 480px screen
        visible_rows = min(num_rows, 15)

        self._data_table = MDDataTable(
            use_pagination=False,
            rows_num=visible_rows,  # Dynamic based on actual data
            column_data=[
                ("Channel", dp(20)),
                ("Type", dp(35)),
                ("Device", dp(35)),
                ("Control", dp(25)),
                ("Code", dp(20)),
            ],
            row_data=self._table_data,
            sorted_on="Channel",
            sorted_order="ASC",
        )

        # Add table to channels tab
        self.add_widget(self._data_table)

    def _update_table_data(self):
        """Update the table data with current model channel configuration."""
        self._table_data.clear()

        if not self._current_model or not self._current_model.channels:
            # If no model or channels, show placeholder message
            self._table_data.append(
                (
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                )
            )
            return

        # Load stick mapping to get current device names
        stick_mapping = self._load_stick_mapping()

        # Add all configured channels
        for ch_id in sorted(self._current_model.channels.keys()):
            channel = self._current_model.channels[ch_id]

            # Format device info using stick_mapping.json as source of truth
            if not channel.device_path:
                device_display = "Virtual"
            else:
                # Look up device name from stick mapping
                device_info = stick_mapping.get(channel.device_path, {})
                device_display = device_info.get("name", "Unknown Device")

                # Fallback to extracting from path if not found in mapping
                if device_display == "Unknown Device":
                    device_display = (
                        channel.device_path.split("/")[-1]
                        if "/" in channel.device_path
                        else channel.device_path
                    )

            # Format control info - use control code directly
            control_display = f"Code {channel.control_code}"

            # Add row to table data
            self._table_data.append(
                (
                    f"ch{channel.channel_id}",  # Channel column - uses chX format
                    channel.control_type.title(),
                    device_display,
                    control_display,
                    str(channel.control_code),
                )
            )

    def _refresh_table(self, *args):
        """Refresh the table data and update display."""
        if hasattr(self, "_data_table") and self._data_table:
            self._update_table_data()
            self._data_table.row_data = self._table_data

    def _load_stick_mapping(self):
        """Load stick mapping from JSON file."""
        try:
            with open(STICK_MAPPING_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _show_error(self, error_msg: str):
        """Show an error message."""
        # Clear all widgets
        self.clear_widgets()

        error_label = MDLabel(text=error_msg, theme_text_color="Error", halign="center")
        self.add_widget(error_label)
