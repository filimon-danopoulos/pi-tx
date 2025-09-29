from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.tab import MDTabsBase
from kivy.metrics import dp

from .....config.settings import STICK_MAPPING_FILE
from .....infrastructure.file_cache import load_json


class ChannelsTab(MDBoxLayout, MDTabsBase):
    """Tab containing the channels data table."""

    # Pre-compute common dp values for better performance
    _column_widths = [dp(20), dp(35), dp(35), dp(25), dp(20)]

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
                ("Channel", self._column_widths[0]),
                ("Type", self._column_widths[1]),
                ("Device", self._column_widths[2]),
                ("Control", self._column_widths[3]),
                ("Code", self._column_widths[4]),
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
            self._table_data.append(("-", "-", "-", "-", "-"))
            return

        # Load stick mapping once (cached)
        stick_mapping = self._load_stick_mapping()

        # Pre-allocate list for better performance
        channels = self._current_model.channels
        table_rows = []

        # Process all channels in one pass
        for ch_id in sorted(channels.keys()):
            channel = channels[ch_id]

            # Format device info using cached stick_mapping
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

            # Pre-format strings to avoid repeated operations
            channel_name = f"ch{channel.channel_id}"
            control_type = channel.control_type.title()
            control_display = f"Code {channel.control_code}"
            control_code_str = str(channel.control_code)

            # Add row to batch
            table_rows.append(
                (
                    channel_name,
                    control_type,
                    device_display,
                    control_display,
                    control_code_str,
                )
            )

        # Batch assign all rows at once
        self._table_data.extend(table_rows)

    def _refresh_table(self, *args):
        """Refresh the table data and update display."""
        if hasattr(self, "_data_table") and self._data_table:
            self._update_table_data()
            self._data_table.row_data = self._table_data

    def _load_stick_mapping(self):
        """Load stick mapping from JSON file using file cache."""
        return load_json(STICK_MAPPING_FILE, default_value={})

    def _show_error(self, error_msg: str):
        """Show an error message."""
        # Clear all widgets
        self.clear_widgets()

        error_label = MDLabel(text=error_msg, theme_text_color="Error", halign="center")
        self.add_widget(error_label)

    # Actions for global FAB menu
    def get_actions(self):  # pragma: no cover (UI integration)
        return [
            {
                "text": "Model Channels: Refresh",
                "callback": self.refresh_table,
                "icon": "refresh",
            },
        ]
