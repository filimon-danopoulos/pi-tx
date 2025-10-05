"""Live page for real-time channel monitoring."""
from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.scrollview import ScrollView

from ...components.channel_panel import ChannelPanel


class LivePage(MDBoxLayout):
    """Live page for real-time channel control and monitoring."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        # Ensure page fills available space
        self.size_hint = (1, 1)
        self.spacing = 0
        self.padding = 0

        # Create the channel panel
        self.channel_panel = ChannelPanel()

        # Put it in a scroll view
        scroll = ScrollView()
        scroll.add_widget(self.channel_panel)
        self.add_widget(scroll)

    def update_values(self, snapshot: list[float]):
        """Update channel values - pass through to the channel panel."""
        if self.channel_panel:
            self.channel_panel.update_values(snapshot)
