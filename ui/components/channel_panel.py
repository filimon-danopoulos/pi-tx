"""Channel panel widget for displaying multiple channels."""
from __future__ import annotations
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.metrics import dp
from .channel_row import ChannelRow


class ChannelPanel(MDBoxLayout):
    """Container displaying a dynamic list of channel rows."""

    def __init__(self, **kw):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            padding=(0, 10, 0, 10),
            spacing=4,
            **kw,
        )
        self.bind(minimum_height=self.setter("height"))
        self.rows = {}

    def rebuild(self, mapping: dict[str, dict]):
        self.clear_widgets()
        self.rows.clear()
        if not mapping:
            self.add_widget(MDLabel(text="No channels configured", halign="center"))
            return
        for ch_str in sorted(mapping.keys(), key=lambda x: int(x)):
            ch = int(ch_str)
            ch_info = mapping[ch_str]
            ch_type = ch_info.get("control_type", ch_info.get("type", "unipolar"))
            ctrl_code = str(ch_info.get("control_code", ""))
            if (not ch_info.get("device_path")) or (not ctrl_code.isdigit()):
                ch_type = "virtual"
            row = ChannelRow(ch, ch_type)
            row.update_value(0.0)
            self.rows[ch] = row
            self.add_widget(row)

    def update_values(self, snapshot: list[float]):
        # Pre-calculate length to avoid repeated len() calls
        snapshot_len = len(snapshot)
        
        for ch, row in self.rows.items():
            idx = ch - 1
            val = snapshot[idx] if idx < snapshot_len else 0.0
            # Only update if value actually changed (avoid unnecessary UI updates)
            if row.bar.value != val:
                row.update_value(val)
