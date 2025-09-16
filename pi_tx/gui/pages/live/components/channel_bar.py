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
        self.bar_color = [0.22, 0.55, 0.95, 1]

    def _redraw(self):
        """Draw value in normalized range -1.0..1.0 always centered.

        Negative values extend left from center, positive to the right.
        Magnitude saturates at the half-width.
        """
        self.canvas.clear()
        with self.canvas:
            Color(*self._bg_color)
            Rectangle(pos=self.pos, size=self.size)
            val = max(-1.0, min(1.0, float(self.value)))
            half_w = max(1.0, self.width / 2.0)
            center_x = self.x + half_w
            magnitude = abs(val) * half_w
            bar_x = center_x if val >= 0 else center_x - magnitude
            bar_w = magnitude
            Color(*self.bar_color)
            Rectangle(pos=(bar_x, self.y), size=(bar_w, self.height))
