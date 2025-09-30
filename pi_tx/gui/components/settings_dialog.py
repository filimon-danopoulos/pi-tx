from __future__ import annotations

from typing import Callable, Optional
from kivy.uix.widget import Widget
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout


class SettingsDialog:  # pragma: no cover - UI scaffolding
    """Base class for fixed-size settings dialogs on a fixed 800x480 canvas.

    Provides:
      - Fixed dimensions: 90% of 800x480 => 720x432 (override via class attrs)
      - Scrollable body region (self.body) inside a vertical layout
      - Optional close button

    Subclass responsibilities:
      - Call open() then populate self.body with widgets
      - Optionally override build_buttons()/build_static_header()
    """

    CANVAS_W = 800
    CANVAS_H = 480
    DIALOG_W = int(CANVAS_W * 0.9)  # 720
    DIALOG_H = int(CANVAS_H * 0.9)  # 432

    def __init__(
        self,
        title: str,
        on_close: Optional[Callable[[], None]] = None,
        add_close_button: bool = True,
    ):
        self.title = title
        self.on_close = on_close
        self.add_close_button = add_close_button
        self.dialog: MDDialog | None = None
        self.body = None  # type: ignore
        self._content = None
        self._scroll = None

    # Hooks ---------------------------------------------------------
    def build_buttons(self):  # pragma: no cover
        buttons = []
        if self.add_close_button:
            buttons.append(
                MDFlatButton(text="CLOSE", on_release=lambda *_: self.close())
            )
        return buttons

    def build_static_header(self):  # pragma: no cover
        return None

    # Internal ------------------------------------------------------
    def _build_content(self):  # pragma: no cover
        PAD = 8
        TITLE_EST = 56
        BUTTONS_EST = 52 if self.build_buttons() else 0
        content_h = self.DIALOG_H - TITLE_EST - BUTTONS_EST - (PAD * 2)
        if content_h < 120:
            content_h = 120
        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(6),
            padding=(PAD, PAD, PAD, PAD),
            size_hint=(None, None),
            width=self.DIALOG_W - PAD * 2,
            height=content_h,
        )
        static_header = self.build_static_header()
        if static_header is not None:
            content.add_widget(static_header)
        # Scroll area
        scroll = ScrollView(
            size_hint=(None, None),
            width=content.width,
            height=content.height - (static_header.height if static_header else 0),
            do_scroll_x=False,
        )
        body = MDBoxLayout(
            orientation="vertical",
            spacing=dp(6),
            padding=(dp(4), dp(4), dp(4), dp(4)),
            size_hint_y=None,
        )
        body.bind(minimum_height=lambda inst, val: setattr(inst, "height", val))
        scroll.add_widget(body)
        content.add_widget(scroll)
        self.body = body
        self._content = content
        self._scroll = scroll
        return content

    # Public --------------------------------------------------------
    def open(self):  # pragma: no cover
        if self.dialog and self.dialog.parent:
            return
        content = self._build_content()
        buttons = self.build_buttons()
        self.dialog = MDDialog(
            title=self.title,
            type="custom",
            content_cls=content,
            buttons=buttons,
            size_hint=(None, None),
        )
        self.dialog.open()
        self.dialog.width = self.DIALOG_W
        self.dialog.height = self.DIALOG_H

    def close(self):  # pragma: no cover
        if self.dialog:
            try:
                self.dialog.dismiss()
            except Exception:
                pass
            self.dialog = None
        if self.on_close:
            try:
                self.on_close()
            except Exception:
                pass

    # -------- Reusable layout helpers (for subclasses) -----------------
    def make_divider(self, text: str):  # pragma: no cover
        """Return a standard section divider label."""

        return MDLabel(
            text=text,
            size_hint_y=None,
            height=dp(26),
            theme_text_color="Secondary",
        )

    def make_input_row(
        self, label_text: str, content_widget, *, content_align: str = "fill"
    ):  # pragma: no cover
        """Create a fixed-width row with a left label and arbitrary content widget.

        Returns (row_layout, label_widget, content_widget)
        content_align:
            fill  - content widget stretches (default behavior)
            right - widget kept natural width, aligned right via spacer
            left  - widget kept natural width, aligned left (spacer after)
        """

        label_ratio: float = 0.25
        height_dp: int = 40
        spacing_dp: int = 8
        enforce_content_width: bool = True

        inner_width = getattr(self, "_inner_width", self.DIALOG_W - 16)
        row = MDBoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            width=inner_width,
            height=dp(height_dp),
            spacing=dp(spacing_dp),
            padding=(0, 0, 0, 0),
        )
        label_w = int(inner_width * label_ratio)
        lbl = MDLabel(
            text=label_text,
            size_hint=(None, 1),
            width=label_w,
            halign="left",
            valign="middle",
        )
        lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))

        remaining_w = inner_width - label_w - 5 * dp(spacing_dp)
        if remaining_w < 10:
            remaining_w = max(10, inner_width // 2)

        container = MDBoxLayout(
            orientation="horizontal",
            size_hint=(None, 1),
            width=remaining_w,
            spacing=0,
            padding=(0, 0, 0, 0),
        )

        if content_align == "fill":
            content_widget.size_hint = (1, 1)
            container.add_widget(content_widget)
        elif content_align == "right":
            container.add_widget(Widget(size_hint=(1, 1)))
            container.add_widget(content_widget)
        else:
            container.add_widget(content_widget)
            container.add_widget(Widget(size_hint=(1, 1)))

        row.add_widget(lbl)
        row.add_widget(container)
        return row
