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
from ..components.model_topbar import ModelTopBar


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

        # Add custom topbar
        self._topbar = ModelTopBar()
        self.add_widget(self._topbar)

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
        self._current_model_name = "No Model Selected"

    def set_model(self, name: str):
        """Load and display the full model configuration."""
        try:
            # Try to get cached model first, fall back to loading from file
            self._current_model = self._model_manager.get_cached_model(name)
            if self._current_model is None:
                self._current_model = self._model_manager._repo.load_model(name)
            
            self._current_model_name = f"Model: {name}"

            # Update topbar
            self._topbar.set_model_name(self._current_model_name)

            # Use the already loaded model instead of re-reading the file
            # The raw JSON data can be reconstructed if needed, but most display
            # fields should be available from the parsed model object
            self._raw_data = {}  # Clear previous data

            self._refresh_content()
        except Exception as e:
            self._current_model_name = "Error Loading Model"
            self._topbar.set_model_name(self._current_model_name)
            self._show_error(f"Error loading model: {str(e)}")

    def _refresh_content(self):
        """Rebuild the content with channel data table."""
        if not self._current_model:
            return

        # Clear all widgets in the channels tab
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

            # Format device info without relying on raw JSON
            if not channel.device_path:
                device_display = "Virtual"
            else:
                # Extract device name from path or use a generic name
                device_display = channel.device_path.split("/")[-1] if "/" in channel.device_path else channel.device_path

            # Format control info - use control code directly
            control_display = f"Code {channel.control_code}"

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
        # Clear all widgets in the channels tab
        self._channels_tab.clear_widgets()

        error_label = MDLabel(text=error_msg, theme_text_color="Error", halign="center")
        self._channels_tab.add_widget(error_label)
