from __future__ import annotations

from typing import Callable, Sequence, Any
from kivymd.uix.button import MDFlatButton
from kivymd.uix.menu import MDDropdownMenu


class OptionMenuButton(MDFlatButton):  # pragma: no cover (UI)
    """Reusable dropdown menu button.

    Parameters
    ----------
    text: str
        Initial button text.
    options: Sequence[str] | Sequence[tuple[str, Any]] | None
        Static options (ignored if options_provider supplied). Each entry can be a
        simple display string or (display, value) tuple. The button text is set
        to the display; the callback receives the *value* (or display if no
        tuple provided).
    options_provider: callable returning same as options
        Called each time the menu is opened to provide dynamic option list.
    on_select: callable(value, display) invoked after selection.
    width_mult: int width multiplier for dropdown width.
    style: optional callable(button) to style the button. If omitted a gray
        background + white text is applied.
    """

    # Track open menus globally so opening one closes others
    _open_menus: list[MDDropdownMenu] = []

    def __init__(
        self,
        text: str,
        *,
        options: Sequence[Any] | None = None,
        options_provider: Callable[[], Sequence[Any]] | None = None,
        on_select: Callable[[Any, str], None] | None = None,
        width_mult: int = 3,
    ):
        super().__init__(text=text)
        self._static_options = options
        self._options_provider = options_provider
        self._on_select = on_select
        self._width_mult = width_mult
        self._menu: MDDropdownMenu | None = None
        # Always apply standardized styling (previously injected from dialogs)
        self._apply_default_style()
        self.bind(on_release=lambda *_: self._open_menu())

    # Styling -----------------------------------------------------------------
    def _apply_default_style(self):  # pragma: no cover
        for attr in ("md_bg_color", "background_color"):
            try:
                setattr(self, attr, (0.3, 0.3, 0.3, 1))
                break
            except Exception:
                continue
        try:
            self.theme_text_color = "Custom"
            self.text_color = (1, 1, 1, 1)
        except Exception:
            pass

    # Options handling ---------------------------------------------------------
    def set_options(self, options: Sequence[Any]):  # pragma: no cover
        self._static_options = options

    def _resolve_options(self) -> list[tuple[str, Any]]:  # pragma: no cover
        raw = []
        if self._options_provider:
            try:
                raw = list(self._options_provider()) or []
            except Exception:
                raw = []
        elif self._static_options is not None:
            raw = list(self._static_options)
        resolved: list[tuple[str, Any]] = []
        for entry in raw:
            if isinstance(entry, tuple) and len(entry) >= 2:
                disp, val = entry[0], entry[1]
            else:
                disp, val = str(entry), entry
            resolved.append((str(disp), val))
        return resolved

    # Menu ---------------------------------------------------------------------
    def _open_menu(self):  # pragma: no cover
        # Close any existing menus (including others)
        for m in list(self._open_menus):
            try:
                m.dismiss()
            except Exception:
                pass
        self._open_menus.clear()
        options = self._resolve_options()
        if not options:
            return

        def _choose(val_disp, val_actual):
            try:
                self.text = val_disp
                if self._on_select:
                    self._on_select(val_actual, val_disp)
            finally:
                for m in list(self._open_menus):
                    try:
                        m.dismiss()
                    except Exception:
                        pass
                self._open_menus.clear()

        items = [
            {
                "text": disp,
                "viewclass": "OneLineListItem",
                "on_release": (lambda d=disp, v=val: _choose(d, v)),
            }
            for disp, val in options
        ]
        self._menu = MDDropdownMenu(caller=self, items=items, width_mult=self._width_mult)
        self._open_menus.append(self._menu)
        self._menu.open()

