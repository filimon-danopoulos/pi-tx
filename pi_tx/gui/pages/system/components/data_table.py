from __future__ import annotations

"""Generic, reusable scrollable data table with:

Features:
  * Configurable columns (header text, size hints, value extractors)
  * Dynamic row population via a provider function
  * Per-row context menu (actions builder callback)
  * Optional inline creation row (configurable validator + create handler)
  * Global actions list convenience (for FAB/menus outside the table)
  * Alternating row colors (theme adaptive)

The component purposely avoids any model-specific logic; callers supply the
behaviour through simple callables.

Intended usage example (pseudo):

  table = DataTable(
      columns=[
          ColumnSpec('name', 'Name', 0.5),
          ColumnSpec('count', 'Count', 0.3, extractor=lambda r: len(r.items)),
      ],
      row_provider=lambda: my_store.list_rows(),
      row_actions_builder=lambda row: [
          ActionItem('Open', lambda r=row: open_row(r)),
          ActionItem('Delete', lambda r=row: delete_row(r)),
      ],
      inline_create=InlineCreateConfig(
          placeholder='New name',
          validator=lambda txt: bool(txt) and txt.isidentifier(),
          create_handler=lambda name: create_row(name),
      ),
      global_actions=[ GlobalAction('Refresh', icon='refresh', callback=lambda: table.refresh()) ]
  )

The implementation mirrors the earlier bespoke model table so existing visual
behaviour (spacing, sizing, icons) remains consistent.
"""

from dataclasses import dataclass
from typing import Callable, Iterable, Any, Sequence

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField


@dataclass
class ColumnSpec:
    key: str
    header: str
    size_hint_x: float
    extractor: Callable[[Any], Any] | None = None  # None => row[key]


@dataclass
class ActionItem:
    text: str
    callback: Callable[[], None]


@dataclass
class GlobalAction:
    text: str
    callback: Callable[[], None]
    icon: str


@dataclass
class InlineCreateConfig:
    placeholder: str
    validator: Callable[[str], bool]
    create_handler: Callable[[str], bool | None]
    helper_text: str = ""
    size_hint_x: float = 0.55
    enabled: bool = True


class DataTable(MDBoxLayout):  # pragma: no cover - UI heavy
    def __init__(
        self,
        *,
        columns: Sequence[ColumnSpec],
        row_provider: Callable[[], Iterable[Any]],
        row_actions_builder: Callable[[Any], Sequence[ActionItem]] | None = None,
        inline_create: InlineCreateConfig | None = None,
        global_actions: Sequence[GlobalAction] | None = None,
        add_actions_column: bool = True,
        header_height: int = 32,
        row_height: int = 32,
        **kwargs,
    ):
        super().__init__(orientation="vertical", **kwargs)
        self._columns = list(columns)
        self._row_provider = row_provider
        self._row_actions_builder = row_actions_builder
        self._inline_create = inline_create
        self._global_actions = list(global_actions) if global_actions else []
        self._add_actions_col = add_actions_column
        self._header_height = header_height
        self._row_height = row_height

        self._row_widgets: list[MDBoxLayout] = []
        self._context_menus = {}

        self._float_layout = MDFloatLayout()
        self.add_widget(self._float_layout)
        self._build()

    # Public API -------------------------------------------------------
    def refresh(self):  # pragma: no cover - called by controller
        self._refresh_table()

    def get_actions(self):  # pragma: no cover
        return [
            {"text": a.text, "callback": a.callback, "icon": a.icon}
            for a in self._global_actions
        ]

    # Construction -----------------------------------------------------
    def _build(self):
        self._scroll = MDScrollView(size_hint=(1, 1))
        self._table_box = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(2),
            padding=(dp(4), dp(4)),
        )
        self._table_box.bind(minimum_height=self._table_box.setter("height"))
        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(self._header_height),
            padding=(dp(4), 0),
        )
        for col in self._columns:
            header.add_widget(
                MDLabel(
                    text=col.header,
                    bold=True,
                    halign="left",
                    size_hint_x=col.size_hint_x,
                )
            )
        if self._add_actions_col:
            header.add_widget(MDLabel(text="", size_hint_x=0.10))
        self._table_box.add_widget(header)
        self._scroll.add_widget(self._table_box)
        self._float_layout.add_widget(self._scroll)
        self._refresh_table()

    # Table ops --------------------------------------------------------
    def _refresh_table(self):
        if not hasattr(self, "_table_box"):
            return
        for w in list(self._table_box.children):
            labels = [c for c in getattr(w, "children", []) if isinstance(c, MDLabel)]
            if any(getattr(l, "bold", False) for l in labels):
                continue
            self._table_box.remove_widget(w)
        self._row_widgets.clear()
        self._context_menus.clear()

        rows = list(self._row_provider() or [])
        if not rows:
            placeholder = MDBoxLayout(
                orientation="horizontal", size_hint_y=None, height=dp(self._row_height)
            )
            placeholder.add_widget(MDLabel(text="No data", halign="left"))
            self._table_box.add_widget(placeholder)
        else:
            for i, r in enumerate(rows):
                self._add_row(r, index=i)

        if self._inline_create and self._inline_create.enabled:
            self._add_inline_create_row()

    # Helpers ----------------------------------------------------------
    def _row_color(self, index):
        try:  # pragma: no cover - theme dependent
            bg = getattr(self.theme_cls, "background_color", (0.12, 0.12, 0.12, 1))
            primary = getattr(self.theme_cls, "primary_color", (0.25, 0.5, 0.9, 1))
            lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
            even = (0, 0, 0, 0)
            if lum < 0.5:
                mix = (
                    (primary[0] + 1.0) / 2.0,
                    (primary[1] + 1.0) / 2.0,
                    (primary[2] + 1.0) / 2.0,
                    0.14,
                )
                odd = mix
            else:
                mix = (
                    primary[0] * 0.4,
                    primary[1] * 0.4,
                    primary[2] * 0.4,
                    0.12,
                )
                odd = mix
        except Exception:  # pragma: no cover
            even = (0, 0, 0, 0)
            odd = (1, 1, 1, 0.14)
        return even if index % 2 == 0 else odd

    def _extract_value(self, row, col: ColumnSpec):
        if col.extractor:
            try:
                return col.extractor(row)
            except Exception:  # pragma: no cover - fallback safety
                return "?"
        if isinstance(row, dict):
            return row.get(col.key, "")
        return getattr(row, col.key, "")

    def _add_row(self, row_data, index=0):
        row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(self._row_height),
            padding=(dp(4), 0),
            md_bg_color=self._row_color(index),
        )
        for col in self._columns:
            value = str(self._extract_value(row_data, col))
            row.add_widget(
                MDLabel(
                    text=value, halign="left", size_hint_x=col.size_hint_x, shorten=True
                )
            )

        if self._add_actions_col and self._row_actions_builder:
            btn = MDIconButton(
                icon="dots-vertical",
                size_hint=(None, None),
                size=(dp(28), dp(28)),
                pos_hint={"center_y": 0.5},
                icon_size="20dp",
            )
            btn.size_hint_x = 0.10

            def open_menu(*_):  # pragma: no cover
                self._open_row_menu(row_data, btn)

            btn.bind(on_release=open_menu)
            row.add_widget(btn)

        self._table_box.add_widget(row)
        self._row_widgets.append(row)

    def _open_row_menu(self, row_data, caller):  # pragma: no cover - UI event
        for m in list(self._context_menus.values()):
            try:
                m.dismiss()
            except Exception:
                pass
        self._context_menus.clear()

        action_items = (
            self._row_actions_builder(row_data) if self._row_actions_builder else []
        )
        items = []
        for a in action_items:
            items.append(
                {
                    "text": a.text,
                    "viewclass": "OneLineListItem",
                    "on_release": (lambda cb=a.callback: self._invoke_and_close(cb)),
                }
            )
        if not items:
            return
        menu = MDDropdownMenu(caller=caller, items=items, width_mult=3)
        self._context_menus[id(row_data)] = menu
        menu.open()

    def _invoke_and_close(self, cb):  # pragma: no cover - UI event
        for m in list(self._context_menus.values()):
            try:
                m.dismiss()
            except Exception:
                pass
        self._context_menus.clear()
        try:
            cb()
        finally:
            self.refresh()

    # Inline create ----------------------------------------------------
    def _add_inline_create_row(self):
        cfg = self._inline_create
        if not cfg:
            return
        container = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            padding=(dp(6), 0, dp(6), 0),
        )
        tf = MDTextField(
            hint_text=cfg.placeholder,
            size_hint_x=cfg.size_hint_x,
            size_hint_y=None,
            height=dp(48),
            helper_text=cfg.helper_text,
            helper_text_mode="on_focus" if cfg.helper_text else "persistent",
        )
        container.add_widget(tf)
        # Fill remaining column slots (excluding actions col)
        remaining = len(self._columns) - 1
        for i in range(remaining):
            container.add_widget(
                MDLabel(text="", size_hint_x=self._columns[i + 1].size_hint_x)
            )
        if self._add_actions_col:
            add_btn = MDIconButton(
                icon="plus-circle",
                disabled=True,
                size_hint=(None, None),
                size=(dp(44), dp(44)),
                pos_hint={"center_y": 0.5},
                icon_size="30dp",
            )
            add_btn.size_hint_x = 0.10
            container.add_widget(add_btn)

            def validate(instance, value):  # pragma: no cover
                add_btn.disabled = not cfg.validator(value)

            tf.bind(text=validate)

            def add(*_):  # pragma: no cover
                name = tf.text.strip()
                if not name:
                    return
                ok = cfg.create_handler(name)
                if ok is not False:
                    tf.text = ""
                    add_btn.disabled = True

            add_btn.bind(on_release=add)
        self._table_box.add_widget(container)
