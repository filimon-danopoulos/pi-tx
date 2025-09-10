from __future__ import annotations
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.metrics import dp


class ChannelBar(Widget):
    value = NumericProperty(0.0)
    channel_type = StringProperty("unipolar")
    bar_color = ListProperty([0, 0.6, 1, 1])

    def __init__(self, channel_type: str, **kw):
        super().__init__(**kw)
        self.channel_type = channel_type or "unipolar"
        self._bg_color = (0.18, 0.18, 0.18, 1)
        self._update_bar_color()
        self.bind(
            pos=lambda *_: self._redraw(),
            size=lambda *_: self._redraw(),
            value=lambda *_: self._redraw(),
        )

    def _update_bar_color(self):
        if self.channel_type == "bipolar":
            self.bar_color = [0.30, 0.80, 0.40, 1]
        elif self.channel_type == "button":
            self.bar_color = [0.90, 0.25, 0.25, 1]
        elif self.channel_type == "virtual":
            self.bar_color = [0.65, 0.45, 0.95, 1]
        else:
            self.bar_color = [0.22, 0.55, 0.95, 1]

    def _redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self._bg_color)
            Rectangle(pos=self.pos, size=self.size)
            val = float(self.value)
            if self.channel_type == "bipolar":
                half_w = self.width / 2.0
                center_x = self.x + half_w
                magnitude = max(0.0, min(1.0, abs(val))) * half_w
                bar_x = center_x if val >= 0 else center_x - magnitude
                bar_w = magnitude
            else:
                clamped = max(0.0, min(1.0, val))
                bar_x = self.x
                bar_w = self.width * clamped
            Color(*self.bar_color)
            Rectangle(pos=(bar_x, self.y), size=(bar_w, self.height))
