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

    # Provide actions for the global FAB menu
    def get_actions(self):  # pragma: no cover (UI integration)
        return [
            {
                "text": "General: Show Info",
                "callback": self._show_info,
                "icon": "information",
            },
        ]

    def _show_info(self, *args):  # simple illustrative callback
        # Could be replaced with a dialog; for now just log
        print("GeneralTab info action triggered")
