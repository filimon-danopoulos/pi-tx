from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem, ThreeLineListItem
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivy.metrics import dp

from ..services.model_manager import ModelManager
from ...domain.model_json import Model


class ChannelsTab(MDBoxLayout, MDTabsBase):
    """Tab containing the channels data table."""
    
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=0, **kwargs)
        self.title = "Channels"
        self.icon = "view-list"


class SettingsTab(MDBoxLayout, MDTabsBase):
    """Tab for model settings (placeholder for future features)."""
    
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "Settings"
        self.icon = "cog"
        
        # Placeholder content
        self.add_widget(
            MDLabel(
                text="Model settings coming soon",
                halign="center",
                valign="center",
            )
        )


class ModelSettingsView(MDBoxLayout):
    """Shows detailed contents and settings for the selected model.

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
        self._settings_tab = SettingsTab()
        
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

    def set_model(self, name: str):
        """Load and display the full model configuration."""
        try:
            self._current_model = self._model_manager._repo.load_model(name)

            # Also load the raw JSON for additional display fields
            import os
            import json

            model_path = os.path.join(
                self._model_manager._repo.models_dir, f"{name}.json"
            )
            self._raw_data = {}
            if os.path.exists(model_path):
                with open(model_path, "r") as f:
                    self._raw_data = json.load(f)

            self._refresh_content()
        except Exception as e:
            self._show_error(f"Error loading model: {str(e)}")

    def _refresh_content(self):
        """Rebuild the content with channel data table."""
        if not self._current_model:
            return

        self._channels_tab.clear_widgets()

        # Create channel mappings data table
        if self._current_model.channels:
            self._create_channels_table()

    def _create_channels_table(self):
        """Create and display the channels data table."""
        # Prepare row data for the table
        row_data = []

        for ch_id in sorted(self._current_model.channels.keys()):
            channel = self._current_model.channels[ch_id]

            # Get additional info from raw JSON if available
            raw_channel = {}
            if hasattr(self, "_raw_data") and "channels" in self._raw_data:
                raw_channel = self._raw_data["channels"].get(
                    str(channel.channel_id), {}
                )

            # Format device info
            device_name = raw_channel.get("device_name", "Unknown")
            if not channel.device_path or device_name == "virtual":
                device_display = "Virtual"
            else:
                device_display = device_name

            # Format control info
            control_name = raw_channel.get("control_name", "")
            control_display = (
                control_name if control_name else f"Code {channel.control_code}"
            )

            # Add row to table data
            row_data.append(
                (
                    f"CH{channel.channel_id}",
                    channel.control_type.title(),
                    device_display,
                    control_display,
                    str(channel.control_code),
                )
            )

        # Remove existing table if present
        if self._data_table:
            self._channels_tab.remove_widget(self._data_table)

        # Create the data table
        self._data_table = MDDataTable(
            use_pagination=False,
            column_data=[
                ("Channel", dp(25)),
                ("Type", dp(30)),
                ("Device", dp(45)),
                ("Control", dp(35)),
                ("Code", dp(20)),
            ],
            row_data=row_data,
            sorted_on="Channel",
            sorted_order="ASC",
        )

        # Add table to channels tab
        self._channels_tab.add_widget(self._data_table)

    def _show_error(self, error_msg: str):
        """Show an error message."""
        self._channels_tab.clear_widgets()
        error_label = MDLabel(text=error_msg, theme_text_color="Error", halign="center")
        self._channels_tab.add_widget(error_label)
