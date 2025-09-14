from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem, ThreeLineListItem
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.button import MDRaisedButton
from kivy.metrics import dp
from kivy.clock import Clock
import threading
from datetime import datetime

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

    def __init__(self, parent_view=None, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "Settings"
        self.icon = "cog"
        self.parent_view = parent_view

        # Bind button for model pairing
        self._bind_button = MDRaisedButton(
            text="Bind Model",
            icon="link-variant",
            theme_icon_color="Custom",
            icon_color="white",
            md_bg_color=(0.2, 0.6, 1.0, 1.0),  # Nice blue color
            size_hint_y=None,
            height=dp(48),
            on_release=self._on_bind_pressed,
        )
        self.add_widget(self._bind_button)

        # Status label
        self._status_label = MDLabel(
            text="Ready to bind",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(40),
        )
        self.add_widget(self._status_label)

        # Placeholder content for future settings
        placeholder_label = MDLabel(
            text="Additional model settings coming soon",
            halign="center",
            valign="center",
        )
        self.add_widget(placeholder_label)

        # Update button text based on bind status when created
        Clock.schedule_once(self._update_bind_button_text, 0.1)

    def _update_bind_button_text(self, dt=None):
        """Update button text based on current model's bind status."""
        if not self.parent_view or not self.parent_view._current_model:
            return
        
        model = self.parent_view._current_model
        if model.bind_timestamp:
            self._bind_button.text = "Rebind Model"
            self._bind_button.icon = "link-variant-plus" 
            self._status_label.text = f"Last bound: {self._format_bind_time(model.bind_timestamp)}"
        else:
            self._bind_button.text = "Bind Model"
            self._bind_button.icon = "link-variant"
            self._status_label.text = "Ready to bind"

    def _format_bind_time(self, timestamp: str) -> str:
        """Format bind timestamp for display."""
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp)
                return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass
        return "Unknown"

    def _on_bind_pressed(self, button_instance):
        """Handle bind button press."""
        # Disable button during binding
        self._bind_button.disabled = True
        self._bind_button.text = "Binding..."

        # Start bind process in background thread
        bind_thread = threading.Thread(target=self._bind_worker)
        bind_thread.daemon = True
        bind_thread.start()

    def _bind_worker(self):
        """Background worker to handle the bind process."""
        try:
            # Get the UART transmitter from the app
            from ... import app as app_mod

            uart_sender = getattr(app_mod, "UART_SENDER", None)

            if uart_sender and hasattr(uart_sender, "bind_for_seconds"):
                # Perform binding for 2 seconds
                uart_sender.bind_for_seconds(2.0)
                success = True
                message = "Binding complete!"
            else:
                success = False
                message = "UART transmitter not available"

        except Exception as e:
            success = False
            message = f"Binding failed: {str(e)}"

        # Schedule UI update on main thread
        Clock.schedule_once(lambda dt: self._bind_complete(success, message))

    def _bind_complete(self, success, message):
        """Complete the bind process and update UI."""
        self._bind_button.disabled = False
        
        if success:
            # Save bind timestamp to model file
            self._save_bind_timestamp()
            # Update button text to show "Rebind"
            self._update_bind_button_text()
            self._status_label.text = message
            self._status_label.theme_text_color = "Custom"
            self._status_label.text_color = (0.2, 0.8, 0.2, 1.0)  # Green
            # Reset to default after 3 seconds
            Clock.schedule_once(lambda dt: self._reset_status(), 3.0)
        else:
            self._bind_button.text = "Bind Model" if not self._is_model_bound() else "Rebind Model"
            self._status_label.text = message
            self._status_label.theme_text_color = "Error"
            # Reset to default after 5 seconds
            Clock.schedule_once(lambda dt: self._reset_status(), 5.0)

    def _save_bind_timestamp(self):
        """Save the current timestamp as bind time to the model file."""
        if not self.parent_view or not self.parent_view._current_model:
            return
        
        try:
            # Update the model object
            model = self.parent_view._current_model
            model.bind_timestamp = datetime.now().isoformat()
            
            # Save to file using ModelRepository
            repo = self.parent_view._model_manager._repo
            repo.save_model(model)
            
            print(f"Saved bind timestamp for model {model.name}")
        except Exception as e:
            print(f"Error saving bind timestamp: {e}")

    def _is_model_bound(self) -> bool:
        """Check if current model has been bound."""
        if not self.parent_view or not self.parent_view._current_model:
            return False
        return bool(self.parent_view._current_model.bind_timestamp)

    def _reset_status(self):
        """Reset status label to default."""
        if self._is_model_bound():
            model = self.parent_view._current_model
            self._status_label.text = f"Last bound: {self._format_bind_time(model.bind_timestamp)}"
        else:
            self._status_label.text = "Ready to bind"
        self._status_label.theme_text_color = "Secondary"


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

            # Update bind button text in settings tab
            self._settings_tab._update_bind_button_text()

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
                device_display = (
                    channel.device_path.split("/")[-1]
                    if "/" in channel.device_path
                    else channel.device_path
                )

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
