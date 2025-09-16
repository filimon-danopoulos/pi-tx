from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabs

from .components.channels_tab import ChannelsTab


class LivePage(MDBoxLayout):
    """Live page for real-time channel control and monitoring.

    Features:
      - Channels tab with existing channel panel UI
      - Ready for additional tabs in the future
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        # Create tabs with explicit sizing
        self._tabs = MDTabs(size_hint=(1, 1))

        # Create the channels tab with the existing channel panel
        self._channels_tab = ChannelsTab()

        # Add tabs to the tab widget
        self._tabs.add_widget(self._channels_tab)

        # Add tabs to main container
        self.add_widget(self._tabs)

    @property
    def channel_panel(self):
        """Provide access to the channel panel for backwards compatibility."""
        return self._channels_tab.channel_panel if self._channels_tab else None

    def set_values(self, snapshot: dict):
        """Update channel values - pass through to the channels tab."""
        if self._channels_tab:
            self._channels_tab.update_values(snapshot)
