from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.metrics import dp


class ModelTopBar(MDBoxLayout):
    """Custom topbar widget to display the current model name."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            spacing=dp(8),
            padding=[dp(16), dp(4), dp(16), dp(4)],
            md_bg_color=(0.0, 0.588, 0.533, 1),  # Teal background
            **kwargs,
        )

        # Model name label
        self.model_label = MDLabel(
            text="No Model Selected",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 0.87),  # White text
            font_style="Subtitle1",
            halign="left",
            valign="center",
            size_hint_x=1,
        )
        self.add_widget(self.model_label)

    def set_model_name(self, model_name: str):
        """Update the displayed model name."""
        self.model_label.text = model_name
