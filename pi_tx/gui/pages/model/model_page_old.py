from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.datatables import MDDataTable
from kivy.metrics import dp
from kivy.clock import Clock
import threading
from datetime import datetime
import json
from pathlib import Path

STICK_MAPPING_FILE = Path(__file__).parents[4] / 'input' / 'mappings' / 'stick_mapping.json'

from ...services.model_manager import ModelManager
from ....domain.model_json import Model
from .components.channels_tab import ChannelsTab
from .components.settings_tab import SettingsTab


class ChannelsTab(MDBoxLayout, MDTabsBase):
    """Tab containing the channels data table."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=0, **kwargs)
        self.title = "Channels"
        self.icon = "view-list"


class SettingsTab(MDBoxLayout, MDTabsBase):
    """Legacy settings tab (simplified)."""

    def __init__(self, parent_view=None, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "Settings"
        self.icon = "cog"
        self.parent_view = parent_view

    def _save_bind_timestamp(self):  # kept for backward compatibility
        if not self.parent_view or not getattr(self.parent_view, "_current_model", None):
            return
        try:
            model = self.parent_view._current_model
            model.bind_timestamp = datetime.now().isoformat()
            repo = self.parent_view._model_manager._repo
            repo.save_model(model)
            from ....logging_config import get_logger as _get_logger
            _get_logger(__name__).info("Saved bind timestamp for model %s", model.name)
        except Exception as e:
            from ....logging_config import get_logger as _get_logger
            _get_logger(__name__).warning("Error saving bind timestamp: %s", e)


class ModelPage(MDBoxLayout):
    """Model configuration page showing detailed model settings.

    Displays:
      - Basic model information (name, ID, RX number, etc.)
      - Channel configurations with device mappings
      - Processor configurations (reverse, differential, aggregate)

    Future enhancements:
      - Rename model
      - Edit channel config (reverse, trim, expo)
      - Persistence / duplication actions
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=0, spacing=0, **kwargs)

        # Create tabs
        self._tabs = MDTabs()

        # Create tab instances
        self._channels_tab = ChannelsTab()
        self._settings_tab = SettingsTab(parent_view=self)

        # Add tabs to the tab widget
        self._tabs.add_widget(self._channels_tab)
        self._tabs.add_widget(self._settings_tab)

        # Add tabs to main container
        self.add_widget(self._tabs)

        # Model manager for loading model details
        self._model_manager = ModelManager()
        self._current_model: Model | None = None
        self._raw_data = {}
        self._data_table = None
        self._table_data = []
        self._current_model_name = "No Model Selected"

    def set_model(self, name: str):
        """Load and display the full model configuration."""
        try:
            # Try to get cached model first, fall back to loading from file
            self._current_model = self._model_manager.get_cached_model(name)
            if self._current_model is None:
                self._current_model = self._model_manager._repo.load_model(name)

            self._current_model_name = f"Model: {name}"

            # Update bind button text in settings tab
            self._settings_tab._update_bind_button_text()

            # Use the already loaded model instead of re-reading the file
            # The raw JSON data can be reconstructed if needed, but most display
            # fields should be available from the parsed model object
            self._raw_data = {}  # Clear previous data

            self._refresh_content()
        except Exception as e:
            self._current_model_name = "Error Loading Model"
            self._show_error(f"Error loading model: {str(e)}")

    def _refresh_content(self):
        """Rebuild the content with channel data table."""
        if not self._current_model:
            return

        # Clear all widgets in the channels tab
        self._channels_tab.clear_widgets()

        # Always create the channels table (will show placeholder if no data)
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
        self._channels_tab.add_widget(self._data_table)

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
        # Clear all widgets in the channels tab
        self._channels_tab.clear_widgets()

        error_label = MDLabel(text=error_msg, theme_text_color="Error", halign="center")
        self._channels_tab.add_widget(error_label)
