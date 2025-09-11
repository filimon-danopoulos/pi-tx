from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel


class SystemSettingsView(MDBoxLayout):
    """Placeholder for system-wide settings.

    Potential future additions:
      - Serial/UART configuration
      - Input device selection
      - Theme / palette toggle
      - Logging / diagnostics
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.add_widget(
            MDLabel(
                text="System Settings (coming soon)",
                halign="center",
                valign="center",
            )
        )
