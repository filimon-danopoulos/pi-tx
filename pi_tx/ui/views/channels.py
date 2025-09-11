from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.scrollview import ScrollView

from ..components.channel_panel import ChannelPanel


class ChannelsView(MDBoxLayout):
    """Container view for the Channels page (scrollable channel panel).

    Provides a `channel_panel` attribute for external controllers (e.g. model
    selection, store updates). Kept lightweight so future UI (filters, search,
    per-channel tools) can be added above the scroll view.
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.channel_panel = ChannelPanel()
        scroll = ScrollView()
        scroll.add_widget(self.channel_panel)
        self.add_widget(scroll)

    def set_values(self, snapshot: dict):  # convenience pass-through
        if self.channel_panel:
            self.channel_panel.update_values(snapshot)
