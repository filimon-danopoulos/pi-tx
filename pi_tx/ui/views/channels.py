from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from ..components.channel_panel import ChannelPanel
from ..components.model_topbar import ModelTopBar


class ChannelsView(MDBoxLayout):
    """Container view for the Channels page (scrollable channel panel).

    Provides a `channel_panel` attribute for external controllers (e.g. model
    selection, store updates). Kept lightweight so future UI (filters, search,
    per-channel tools) can be added above the scroll view.
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        # Add custom topbar
        self._topbar = ModelTopBar()
        self.add_widget(self._topbar)

        # Channel panel in scroll view
        self.channel_panel = ChannelPanel()
        scroll = ScrollView()
        scroll.add_widget(self.channel_panel)
        self.add_widget(scroll)

    def set_model_name(self, model_name: str):
        """Update the title to show the current model name."""
        if model_name:
            self._topbar.set_model_name(f"Model: {model_name}")
        else:
            self._topbar.set_model_name("No Model Selected")

    def set_values(self, snapshot: dict):  # convenience pass-through
        if self.channel_panel:
            self.channel_panel.update_values(snapshot)
