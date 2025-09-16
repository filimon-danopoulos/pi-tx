from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.tab import MDTabsBase


class GeneralTab(MDBoxLayout, MDTabsBase):
    """Tab for general system settings."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "General"
        self.icon = "cog"

        # Placeholder content for future system settings
        self.add_widget(
            MDLabel(
                text="General system settings coming soon...\n\n• Serial/UART configuration\n• Input device selection\n• Theme settings\n• Logging options",
                halign="left",
                valign="top",
            )
        )
