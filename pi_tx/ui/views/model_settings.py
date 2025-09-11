from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem, ThreeLineListItem

from ..services.model_manager import ModelManager
from ...domain.model_json import Model


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
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)

        # Header label
        self._header = MDLabel(
            text="Model Settings: (no model)",
            halign="center",
            size_hint_y=None,
            height="48dp",
            theme_text_color="Primary",
        )
        self.add_widget(self._header)

        # Scrollable content
        scroll = MDScrollView()
        self._content = MDList()
        scroll.add_widget(self._content)
        self.add_widget(scroll)

        # Model manager for loading model details
        self._model_manager = ModelManager()
        self._current_model: Model | None = None
        self._raw_data = {}

    def set_model(self, name: str):
        """Load and display the full model configuration."""
        try:
            self._header.text = f"Model Settings: {name}"
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
            self._header.text = f"Model Settings: {name} (Error loading)"
            self._show_error(f"Error loading model: {str(e)}")

    def _refresh_content(self):
        """Rebuild the content list with model details."""
        if not self._current_model:
            return

        self._content.clear_widgets()

        # Basic Model Information
        self._add_section_header("Model Information")
        self._add_info_item("Name", self._current_model.name)
        self._add_info_item("Model ID", self._current_model.model_id[:16] + "...")
        self._add_info_item("RX Number", str(self._current_model.rx_num))
        self._add_info_item("Model Index", str(self._current_model.model_index))
        self._add_info_item("Total Channels", str(len(self._current_model.channels)))

        # Add spacing
        spacer = MDLabel(text="", size_hint_y=None, height="16dp")
        self._content.add_widget(spacer)

        # Channel Configuration
        if self._current_model.channels:
            self._add_section_header("Channel Configuration")
            for ch_id in sorted(self._current_model.channels.keys()):
                channel = self._current_model.channels[ch_id]
                self._add_channel_item(channel)

            # Add spacing
            spacer = MDLabel(text="", size_hint_y=None, height="16dp")
            self._content.add_widget(spacer)

        # Processors Configuration
        if self._current_model.processors:
            self._add_section_header("Processor Configuration")
            self._add_processors_info(self._current_model.processors)

    def _add_section_header(self, title: str):
        """Add a section header."""
        header = MDLabel(
            text=title,
            theme_text_color="Primary",
            bold=True,
            size_hint_y=None,
            height="32dp",
        )
        self._content.add_widget(header)

    def _add_info_item(self, label: str, value: str):
        """Add a simple info item with label and value."""
        item = TwoLineListItem(
            text=label, secondary_text=str(value), theme_text_color="Primary"
        )
        self._content.add_widget(item)

    def _add_channel_item(self, channel):
        """Add a detailed channel configuration item."""
        # Get additional info from raw JSON if available
        raw_channel = {}
        if hasattr(self, "_raw_data") and "channels" in self._raw_data:
            raw_channel = self._raw_data["channels"].get(str(channel.channel_id), {})

        # Format device info - handle virtual channels
        device_info = (
            "Virtual Channel" if not channel.device_path else channel.device_path
        )
        device_name = raw_channel.get("device_name", "")
        if device_name and device_name != "virtual":
            device_info = f"{device_name} - {device_info}"

        # Format control info
        control_info = f"Code: {channel.control_code}, Type: {channel.control_type}"
        control_name = raw_channel.get("control_name", "")
        if control_name:
            control_info = f"{control_name} ({control_info})"

        item = ThreeLineListItem(
            text=f"Channel {channel.channel_id}",
            secondary_text=device_info,
            tertiary_text=control_info,
            theme_text_color="Primary",
        )
        self._content.add_widget(item)

    def _add_processors_info(self, processors):
        """Add processor configuration details."""
        for proc_type, config in processors.items():
            if proc_type == "reverse" and isinstance(config, dict):
                # Show reverse settings
                reversed_channels = [ch for ch, enabled in config.items() if enabled]
                if reversed_channels:
                    item = TwoLineListItem(
                        text="Reverse Channels",
                        secondary_text=f"Channels: {', '.join(reversed_channels)}",
                        theme_text_color="Primary",
                    )
                    self._content.add_widget(item)

            elif proc_type == "differential" and isinstance(config, list):
                # Show differential pairs
                for i, diff in enumerate(config):
                    if isinstance(diff, dict):
                        left = diff.get("left", "?")
                        right = diff.get("right", "?")
                        inverse = diff.get("inverse", False)
                        inverse_text = " (inverted)" if inverse else ""
                        item = TwoLineListItem(
                            text=f"Differential Pair {i+1}",
                            secondary_text=f"Left: CH{left}, Right: CH{right}{inverse_text}",
                            theme_text_color="Primary",
                        )
                        self._content.add_widget(item)

            elif proc_type == "aggregate" and isinstance(config, list):
                # Show aggregate mixing
                for i, agg in enumerate(config):
                    if isinstance(agg, dict) and "channels" in agg and "target" in agg:
                        channels_info = []
                        for ch in agg["channels"]:
                            if isinstance(ch, dict):
                                ch_id = ch.get("id", "?")
                                value = ch.get("value", 0)
                                channels_info.append(f"CH{ch_id}({value})")
                        target = agg["target"]
                        item = TwoLineListItem(
                            text=f"Aggregate Mix {i+1} → CH{target}",
                            secondary_text=f"Sources: {', '.join(channels_info)}",
                            theme_text_color="Primary",
                        )
                        self._content.add_widget(item)

    def _show_error(self, error_msg: str):
        """Show an error message in the content area."""
        self._content.clear_widgets()
        error_item = OneLineListItem(text=error_msg, theme_text_color="Error")
        self._content.add_widget(error_item)
