from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase
from kivy.uix.scrollview import ScrollView

from .channel_panel import ChannelPanel


class ChannelsTab(MDBoxLayout, MDTabsBase):
    """Tab for live channel monitoring and control."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.title = "Channels"
        self.icon = "chart-line"

        # Ensure tab fills available space
        self.size_hint = (1, 1)
        self.spacing = 0
        self.padding = 0

        # Create the channel panel (keeping the existing UI intact)
        self.channel_panel = ChannelPanel()

        # Put it in a scroll view
        scroll = ScrollView()
        scroll.add_widget(self.channel_panel)
        self.add_widget(scroll)

    def update_values(self, snapshot: dict):
        """Update channel values - pass through to the channel panel."""
        if self.channel_panel:
            self.channel_panel.update_values(snapshot)

