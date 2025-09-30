from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.button import MDFlatButton as _SelectorButton  # legacy
from .....components.option_menu_button import OptionMenuButton
from kivy.metrics import dp
from kivy.clock import Clock
from .....components.settings_dialog import SettingsDialog


class DifferentialEditDialog(SettingsDialog):  # pragma: no cover
    def __init__(self, on_close=None, on_apply=None):
        super().__init__(
            title="Edit Differential", on_close=on_close, add_close_button=True
        )
        self.on_apply = on_apply
        self.on_delete = None
        self._delete_confirm_dialog: MDDialog | None = None
        self._left_btn: _SelectorButton | None = None
        self._right_btn: _SelectorButton | None = None
        self._inverse_switch = None
        self._inverse_btn: _SelectorButton | None = None
        self._menus: list[MDDropdownMenu] = []
        self._all_channels: list[str] = []
        self._initial_inverse = False
        # fixed inner width similar to aggregate dialog (dialog width - horizontal padding allowance)
        self._inner_width = self.DIALOG_W - 16

    # Buttons
    def build_buttons(self):  # pragma: no cover
        buttons = []
        if self.on_delete:
            b = MDFlatButton(
                text="DELETE", on_release=lambda *_: self._open_delete_confirm()
            )
            try:
                b.theme_text_color = "Custom"
                b.text_color = (1, 0.2, 0.2, 1)
            except Exception:
                pass
            buttons.append(b)
        buttons.append(MDFlatButton(text="CLOSE", on_release=lambda *_: self.close()))
        buttons.append(
            MDRaisedButton(text="APPLY", on_release=lambda *_: self._apply())
        )
        return buttons

    # Public show
    def show(
        self,
        all_channels: list[str],
        left: str | None = None,
        right: str | None = None,
        inverse: bool = False,
        *,
        can_delete=False,
        on_delete=None,
    ):  # pragma: no cover
        if self.dialog and self.dialog.parent:
            return
        if not all_channels:
            all_channels = ["ch1"]
        self._all_channels = all_channels[:]
        self.on_delete = on_delete if can_delete else None
        left = left or all_channels[0]
        right = right or (all_channels[1] if len(all_channels) > 1 else all_channels[0])
        self._initial_inverse = bool(inverse)
        self.open()
        Clock.schedule_once(lambda *_: self._build_contents(left, right), 0)

    # Content
    def _build_contents(self, left: str, right: str):  # pragma: no cover
        if not self.body:
            return
        self.body.clear_widgets()
        # Left / Right selector buttons using shared row helper
        # Option buttons (channels filtered to avoid duplicate selection)
        def channel_options_left():
            return self._all_channels

        def channel_options_right():
            # exclude left selection if >1 channel available
            if len(self._all_channels) > 1 and self._left_btn:
                return [c for c in self._all_channels if c != self._left_btn.text]
            return self._all_channels

        self._left_btn = OptionMenuButton(
            text=left,
            options_provider=channel_options_left,
            on_select=lambda *_: None,
        )
        self._right_btn = OptionMenuButton(
            text=right,
            options_provider=channel_options_right,
            on_select=lambda *_: None,
        )

        left_row = self.make_input_row("Left Channel", self._left_btn, content_align="fill")
        right_row = self.make_input_row("Right Channel", self._right_btn, content_align="fill")
        self.body.add_widget(left_row)
        self.body.add_widget(right_row)

        # Inverse Yes/No selector using OptionMenuButton
        self._inverse_btn = OptionMenuButton(
            text=("Yes" if self._initial_inverse else "No"),
            options=["Yes", "No"],
        )
        inv_row = self.make_input_row("Inverse", self._inverse_btn, content_align="fill")
        self.body.add_widget(inv_row)
    # No manual binding needed; OptionMenuButton handles open

    # Menus
    def _open_menu(self, btn: _SelectorButton):  # pragma: no cover
        for m in self._menus:
            try:
                m.dismiss()
            except Exception:
                pass
        self._menus.clear()
        # Exclude other button selection if >1 channels
        other_selected = None
        if btn is self._left_btn and self._right_btn:
            other_selected = self._right_btn.text
        elif btn is self._right_btn and self._left_btn:
            other_selected = self._left_btn.text
        filtered = [
            ch
            for ch in self._all_channels
            if not (
                other_selected and ch == other_selected and len(self._all_channels) > 1
            )
        ] or self._all_channels[:]
        items = [
            {
                "text": ch,
                "viewclass": "OneLineListItem",
                "on_release": (lambda c=ch: self._choose(btn, c)),
            }
            for ch in filtered
        ]
        menu = MDDropdownMenu(caller=btn, items=items, width_mult=3)
        self._menus.append(menu)
        menu.open()

    def _choose(self, btn: _SelectorButton, value: str):  # pragma: no cover
        try:
            btn.text = value
        finally:
            for m in self._menus:
                try:
                    m.dismiss()
                except Exception:
                    pass
            self._menus.clear()

    # Apply
    def _apply(self):  # pragma: no cover
        left = (
            self._left_btn.text
            if self._left_btn
            else (self._all_channels[0] if self._all_channels else "ch1")
        )
        right = self._right_btn.text if self._right_btn else left
        inverse = False
        if self._inverse_btn:
            try:
                inverse = self._inverse_btn.text.strip().lower() == "yes"
            except Exception:
                inverse = False
        if self.on_apply:
            try:
                self.on_apply(left, right, inverse)
            except Exception:
                pass
        self.close()

    # Inverse Yes/No menu binding
    def _bind_inverse_menu(self, btn: _SelectorButton):  # pragma: no cover
        def open_menu(*_):
            # Close other menus
            for m in self._menus:
                try:
                    m.dismiss()
                except Exception:
                    pass
            self._menus.clear()
            items = []
            for label in ("Yes", "No"):
                items.append(
                    {
                        "text": label,
                        "viewclass": "OneLineListItem",
                        "on_release": (lambda v=label: choose(v)),
                    }
                )
            menu = MDDropdownMenu(caller=btn, items=items, width_mult=2)
            self._menus.append(menu)
            menu.open()

        def choose(val):
            try:
                btn.text = val
            finally:
                for m in self._menus:
                    try:
                        m.dismiss()
                    except Exception:
                        pass
                self._menus.clear()

        btn.bind(on_release=open_menu)

    # Delete logic unchanged below

    # Legacy dropdown helpers removed (OptionMenuButton now used)
