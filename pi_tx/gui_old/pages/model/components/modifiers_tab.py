from __future__ import annotations

from typing import List, Tuple
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase

from ....components.data_table import (
    DataTable,
    ColumnSpec,
)
from .....logging_config import get_logger


class ModifiersTab(MDBoxLayout, MDTabsBase):  # pragma: no cover - UI heavy
    """Channel modifiers: polarity (reverse) and endpoint ranges.

    Displays per-channel reverse flag plus min/max endpoint (or defaults).
    """

    icon = "swap-vertical"
    title = "Modifiers"

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self._log = get_logger(__name__)
        self._current_model = None
        self._model_manager = None
        self._table: DataTable | None = None
        self._build_table()

    def set_model(self, model, model_manager):  # pragma: no cover
        self._current_model = model
        self._model_manager = model_manager
        self.refresh_table()

    def refresh_table(self):  # pragma: no cover
        if self._table:
            self._table.refresh()

    # Internal helpers -------------------------------------------------
    def _build_table(self):
        def row_provider():
            return self._build_rows()

        self._table = DataTable(
            columns=[
                ColumnSpec("channel", "Channel", 0.25, extractor=lambda r: r[0]),
                ColumnSpec("reversed", "Reversed", 0.25, extractor=lambda r: r[1]),
                ColumnSpec("min", "Min", 0.25, extractor=lambda r: r[2]),
                ColumnSpec("max", "Max", 0.25, extractor=lambda r: r[3]),
            ],
            row_provider=row_provider,
        )
        self.add_widget(self._table)

    def _build_rows(self) -> List[Tuple[str, str, str, str]]:
        if not self._current_model:
            return [("-", "-", "-", "-")]
        rows: List[Tuple[str, str, str, str]] = []
        rev_map = {}
        ep_map = {}
        try:
            processors = self._current_model.processors or {}
            rev_map = processors.get("reverse", {}) or {}
            raw_eps = processors.get("endpoints", {}) or {}
            if isinstance(raw_eps, dict):
                ep_map = raw_eps
        except Exception:
            rev_map = {}
            ep_map = {}
        channel_ids = sorted(self._current_model.channels.keys())
        for ch in channel_ids:
            ch_key = f"ch{ch}"
            channel_cfg = self._current_model.channels.get(ch)
            ctype = (channel_cfg.control_type if channel_cfg else "").lower()
            # Default ranges: unipolar -> 0..1, otherwise -1..1
            default_min, default_max = (
                (0.0, 1.0) if ctype == "unipolar" else (-1.0, 1.0)
            )
            reversed_flag = rev_map.get(ch_key, False)
            ep_entry = ep_map.get(ch_key, {}) if isinstance(ep_map, dict) else {}
            mn = ep_entry.get("min") if isinstance(ep_entry, dict) else None
            mx = ep_entry.get("max") if isinstance(ep_entry, dict) else None
            # If endpoints missing, fall back to defaults
            if not isinstance(mn, (int, float)):
                mn = default_min
            if not isinstance(mx, (int, float)):
                mx = default_max
            # Clamp just in case mis-ordered
            if mn > mx:
                mn, mx = mx, mn
            mn_s = f"{mn:.2f}"
            mx_s = f"{mx:.2f}"
            rows.append((ch_key, "Yes" if reversed_flag else "No", mn_s, mx_s))
        if not rows:
            rows.append(("-", "-", "-", "-"))
        return rows
