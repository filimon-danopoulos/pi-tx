from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.button import MDFlatButton as _SelectorButton
from kivy.metrics import dp
from kivy.clock import Clock


class DifferentialEditDialog:
    """Placeholder dialog for editing a differential processor mix.

    (Future) Expected fields:
      - Left channel selector
      - Right channel selector
      - Inverse toggle
    """

    def __init__(self, on_close=None, on_apply=None):
        self.on_close = on_close
        self.on_apply = on_apply
        self.dialog: MDDialog | None = None
        self._left_btn: _SelectorButton | None = None
        self._right_btn: _SelectorButton | None = None
        self._inverse_switch = None
        self._menus = []

    def show(
        self,
        all_channels: list[str],
        left: str | None = None,
        right: str | None = None,
        inverse: bool = False,
    ):
        if self.dialog and self.dialog.parent:
            return
        if not all_channels:
            all_channels = ["ch1"]
        # Fallback defaults
        left = left or all_channels[0]
        right = right or (all_channels[1] if len(all_channels) > 1 else all_channels[0])

        root = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(12),
            padding=(dp(12), dp(12), dp(12), dp(4)),
        )

        # Helper to create horizontal row: Label | Button (aligned)
        def build_selector(label_text: str, initial: str):
            row = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(44),
                spacing=dp(8),
            )
            lbl = MDLabel(
                text=label_text,
                size_hint_x=0.45,
                halign="left",
                valign="middle",
            )
            lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))
            btn = _SelectorButton(text=initial, size_hint=(0.55, 1))
            row.add_widget(lbl)
            row.add_widget(btn)
            return row, btn

        left_row, self._left_btn = build_selector("Left Channel", left)
        right_row, self._right_btn = build_selector("Right Channel", right)
        root.add_widget(left_row)
        root.add_widget(right_row)

        # Inverse switch
        inv_row = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(12)
        )
        inv_row.add_widget(MDLabel(text="Inverse", size_hint_x=0.5, halign="left"))
        # Create switch first; defer setting active to next frame to avoid KeyError 'thumb'
        self._inverse_switch = MDSwitch()
        inv_row.add_widget(self._inverse_switch)
        if inverse:
            Clock.schedule_once(
                lambda *_: setattr(self._inverse_switch, "active", True), 0
            )
        root.add_widget(inv_row)

        # Info text
        info = MDLabel(
            text="Configure a differential mix. Result overwrites both channels.",
            halign="left",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(40),
        )
        root.add_widget(info)

        # Attach dropdown menus (recreate on each open to reflect channel set)
        def open_menu(btn: _SelectorButton):  # pragma: no cover
            for m in self._menus:
                try:
                    m.dismiss()
                except Exception:
                    pass
            self._menus.clear()

            def choose(val: str):
                self._set_choice(btn, val)

            # Determine counterpart button & exclude its current selection (if >1 channels total)
            other_selected = None
            if btn is self._left_btn and self._right_btn:
                other_selected = self._right_btn.text
            elif btn is self._right_btn and self._left_btn:
                other_selected = self._left_btn.text

            filtered = [
                ch
                for ch in all_channels
                if not (
                    other_selected and ch == other_selected and len(all_channels) > 1
                )
            ]
            # Safety: never present empty list
            if not filtered:
                filtered = all_channels[:]

            items = [
                {
                    "text": ch,
                    "viewclass": "OneLineListItem",
                    "on_release": (lambda c=ch: choose(c)),
                }
                for ch in filtered
            ]
            menu = MDDropdownMenu(caller=btn, items=items, width_mult=3)
            self._menus.append(menu)
            menu.open()

        if self._left_btn:
            self._left_btn.bind(on_release=lambda *_: open_menu(self._left_btn))
        if self._right_btn:
            self._right_btn.bind(on_release=lambda *_: open_menu(self._right_btn))

        self.dialog = MDDialog(
            title="Edit Differential",
            type="custom",
            content_cls=root,
            buttons=[
                MDFlatButton(text="CLOSE", on_release=lambda *_: self.close()),
                MDRaisedButton(text="APPLY", on_release=lambda *_: self._apply()),
            ],
        )
        self.dialog.open()

    def _set_choice(self, btn: _SelectorButton, value: str):  # pragma: no cover
        try:
            btn.text = value
        finally:
            for m in self._menus:
                try:
                    m.dismiss()
                except Exception:
                    pass

    def _apply(self):  # pragma: no cover
        left = self._left_btn.text if self._left_btn else "ch1"
        right = self._right_btn.text if self._right_btn else left
        inverse = bool(self._inverse_switch.active) if self._inverse_switch else False
        if self.on_apply:
            try:
                self.on_apply(left, right, inverse)
            except Exception:
                pass
        self.close()

    def close(self):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
        if self.on_close:
            self.on_close()
