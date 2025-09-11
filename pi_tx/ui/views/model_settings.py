from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel


class ModelSettingsView(MDBoxLayout):
    """Placeholder for per-model settings; updates label with selected model name.

    Future enhancements:
      - Rename model
      - Channel config (reverse, trim, expo)
      - Persistence / duplication actions
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self._label = MDLabel(
            text="Model Settings: (no model)", halign="center", valign="center"
        )
        self.add_widget(self._label)

    def set_model(self, name: str):
        try:  # pragma: no cover - UI only
            self._label.text = f"Model Settings: {name}"
        except Exception:
            pass
