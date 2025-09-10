from __future__ import annotations
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.metrics import dp
from .channel_bar import ChannelBar


class ChannelRow(MDBoxLayout):
    def __init__(self, channel_number: int, channel_type: str, **kw):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            padding=(dp(8), 0, dp(8), 0),
            spacing=dp(8),
            **kw,
        )
        self.channel_number = channel_number
        self.channel_type = channel_type or "unipolar"
        base_label = f"CH_{channel_number}"
        self.label = MDLabel(text=base_label, size_hint_x=None, width=dp(60))
        self.bar = ChannelBar(self.channel_type, size_hint_x=1)
        self.value_label = MDLabel(
            text="0.00", size_hint_x=None, width=dp(60), halign="right"
        )
        self.add_widget(self.label)
        self.add_widget(self.bar)
        self.add_widget(self.value_label)

    def update_value(self, value: float):
        self.bar.value = value
        self.value_label.text = (
            f"{value:+.2f}" if self.channel_type == "bipolar" else f"{value:.2f}"
        )
