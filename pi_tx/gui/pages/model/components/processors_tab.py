from __future__ import annotations

from typing import Any, List, Tuple

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase

from ....components.data_table import DataTable, ColumnSpec, ActionItem
from .dialogs import (
    DifferentialEditDialog,
    AggregateEditDialog,
)
from .....logging_config import get_logger


class ProcessorsTab(MDBoxLayout, MDTabsBase):  # pragma: no cover - UI heavy
    """Displays non-modifier processors (differential, aggregate, etc.).

    Columns:
      - Type: processor category (Differential, Aggregate, ...)
      - Target Channel(s): channel(s) whose value(s) are written by the processor
      - Source Channels: comma separated list of channels read by the processor

    Row actions (placeholder implementations):
      - Edit: opens a type specific dialog (TBD)
      - Remove: removes the processor config entry (TBD)
    """

    icon = "tune"
    title = "Processors"

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self._log = get_logger(__name__)
        self._current_model = None
        self._model_manager = None
        self._table: DataTable | None = None
        self._active_dialog = None
        # Precomputed processor items (list of dicts with metadata)
        self._processor_items = []  # type: list[dict]
        # Dialog instances
        self._diff_dialog = DifferentialEditDialog(
            on_close=self._clear_active_dialog,
            on_apply=self._on_diff_apply_placeholder,
        )
        self._agg_dialog = AggregateEditDialog(
            on_close=self._clear_active_dialog,
            on_apply=self._on_agg_apply,
        )
        # Removal now handled inside edit dialogs; no separate remove dialog
        self._build_table()

    # Public API ------------------------------------------------------
    def set_model(self, model, model_manager):  # pragma: no cover
        self._current_model = model
        self._model_manager = model_manager
        self._rebuild_processor_items()
        self.refresh_table()

    def refresh_table(self):  # pragma: no cover
        if self._table:
            self._table.refresh()

    # Internal helpers ------------------------------------------------
    def _build_table(self):
        def row_provider():
            return self._build_rows()

        self._table = DataTable(
            columns=[
                ColumnSpec("type", "Type", 0.28, extractor=lambda r: r[0]),
                ColumnSpec(
                    "targets", "Target Channel(s)", 0.32, extractor=lambda r: r[1]
                ),
                ColumnSpec(
                    "sources", "Source Channels", 0.40, extractor=lambda r: r[2]
                ),
            ],
            row_provider=row_provider,
            row_actions_builder=None,
            row_action=lambda row: self._edit_processor(row),
            add_actions_column=True,
        )
        self.add_widget(self._table)

    def _build_rows(self) -> List[Tuple[str, str, str, str]]:
        if not self._processor_items:
            return [("-", "-", "-")]
        rows: List[Tuple[str, str, str, str]] = []
        for idx, item in enumerate(self._processor_items):
            rows.append((item["type"], item["targets"], item["sources"], str(idx)))
        return rows

    # Precompute processor list -------------------------------------
    def _rebuild_processor_items(self):  # pragma: no cover
        self._processor_items = []
        if not self._current_model:
            return
        processors = self._current_model.processors or {}
        # Differential
        diff_list = processors.get("differential")
        if isinstance(diff_list, list):
            for d in diff_list:
                if not (
                    isinstance(d, dict)
                    and isinstance(d.get("left"), str)
                    and isinstance(d.get("right"), str)
                ):
                    continue
                left = d.get("left")
                right = d.get("right")
                targets = f"{left},{right}"
                self._processor_items.append(
                    {
                        "type": "Differential",
                        "targets": targets,
                        "sources": targets,
                        "config": d,
                    }
                )
        # Aggregate
        agg_list = processors.get("aggregate")
        if isinstance(agg_list, list):
            for a in agg_list:
                if not isinstance(a, dict):
                    continue
                ch_entries = a.get("channels") or []
                src_chs: List[str] = []
                for entry in ch_entries:
                    try:
                        if isinstance(entry, dict):
                            ch_id = (
                                entry.get("id")
                                or entry.get("ch")
                                or entry.get("channel")
                            )
                            if isinstance(ch_id, str) and ch_id.startswith("ch"):
                                src_chs.append(ch_id)
                        elif isinstance(entry, str) and entry.startswith("ch"):
                            src_chs.append(entry)
                    except Exception:
                        continue
                target_raw = a.get("target")
                target = None
                if isinstance(target_raw, str) and target_raw.startswith("ch"):
                    target = target_raw
                if target is None and src_chs:
                    target = src_chs[0]
                targets = target or "-"
                sources = ",".join(src_chs) if src_chs else "-"
                self._processor_items.append(
                    {
                        "type": "Aggregate",
                        "targets": targets,
                        "sources": sources,
                        "config": a,
                    }
                )

    # Action callbacks (placeholders) --------------------------------
    def _edit_processor(self, row):  # pragma: no cover
        ptype, targets, sources = row[:3]
        idx = None
        if len(row) > 3:
            try:
                idx = int(row[3])
            except Exception:
                idx = None
        self._log.info("Edit processor requested: %s (idx=%s)", ptype, idx)
        self._clear_active_dialog()
        config_obj = None
        if idx is not None and 0 <= idx < len(self._processor_items):
            config_obj = self._processor_items[idx].get("config")
        if ptype == "Differential" and config_obj:
            inverse_flag = bool(config_obj.get("inverse"))
            left = config_obj.get("left")
            right = config_obj.get("right")
            all_channels = [
                f"ch{c}" for c in sorted(self._current_model.channels.keys())
            ]
            self._editing_diff_entry = config_obj
            self._diff_dialog.show(
                all_channels=all_channels,
                left=left,
                right=right,
                inverse=inverse_flag,
                can_delete=True,
                on_delete=self._on_diff_delete,
            )
            self._active_dialog = self._diff_dialog.dialog
        elif ptype == "Aggregate" and config_obj:
            self._editing_agg_entry = config_obj
            all_channels = [
                f"ch{c}" for c in sorted(self._current_model.channels.keys())
            ]
            self._agg_dialog.show(
                all_channels=all_channels,
                config=config_obj,
                can_delete=True,
                on_delete=self._on_agg_delete,
            )
            self._active_dialog = self._agg_dialog.dialog
        else:
            all_channels = [
                f"ch{c}" for c in sorted(self._current_model.channels.keys())
            ]
            self._agg_dialog.show(all_channels=all_channels, config=None)
            self._active_dialog = self._agg_dialog.dialog

    # Removal now handled via edit dialog delete buttons

    # Dialog helpers --------------------------------------------------
    def _clear_active_dialog(self):  # pragma: no cover
        self._active_dialog = None

    def _on_diff_delete(self):  # pragma: no cover
        self._log.info("Delete differential processor entry")
        if not self._current_model:
            return
        diff_list = None
        try:
            diff_list = self._current_model.processors.get("differential")
        except Exception:
            diff_list = None
        if isinstance(diff_list, list) and hasattr(self, "_editing_diff_entry"):
            try:
                if self._editing_diff_entry in diff_list:
                    diff_list.remove(self._editing_diff_entry)
            except Exception:
                pass
        if self._model_manager and hasattr(self._model_manager, "save_model"):
            try:
                self._model_manager.save_model(self._current_model)
            except Exception:
                self._log.warning("Failed to save model after differential delete")
        self._editing_diff_entry = None
        self._rebuild_processor_items()
        self.refresh_table()
        self._clear_active_dialog()

    def _on_agg_delete(self):  # pragma: no cover
        self._log.info("Delete aggregate processor entry")
        if not self._current_model:
            return
        agg_list = None
        try:
            agg_list = self._current_model.processors.get("aggregate")
        except Exception:
            agg_list = None
        if isinstance(agg_list, list) and hasattr(self, "_editing_agg_entry"):
            try:
                if self._editing_agg_entry in agg_list:
                    agg_list.remove(self._editing_agg_entry)
            except Exception:
                pass
        if self._model_manager and hasattr(self._model_manager, "save_model"):
            try:
                self._model_manager.save_model(self._current_model)
            except Exception:
                self._log.warning("Failed to save model after aggregate delete")
        self._editing_agg_entry = None
        self._rebuild_processor_items()
        self.refresh_table()
        self._clear_active_dialog()

    def _on_agg_apply(self, target: str, sources: list[dict]):  # pragma: no cover
        self._log.info("Apply aggregate edit target=%s sources=%s", target, sources)
        if not self._current_model:
            return
        if not self._current_model.processors:
            self._current_model.processors = {}
        agg_list = self._current_model.processors.get("aggregate")
        if not isinstance(agg_list, list):
            agg_list = []
            self._current_model.processors["aggregate"] = agg_list

        # If editing existing entry mutate; else append
        updated = False
        try:
            if (
                hasattr(self, "_editing_agg_entry")
                and self._editing_agg_entry in agg_list
            ):
                entry = self._editing_agg_entry
                entry["target"] = target
                entry["channels"] = sources
                updated = True
        except Exception:
            pass
        if not updated:
            agg_list.append({"target": target, "channels": sources})
        if self._model_manager and hasattr(self._model_manager, "save_model"):
            try:
                self._model_manager.save_model(self._current_model)
            except Exception:
                self._log.warning("Failed to save model after aggregate apply")
        self._editing_agg_entry = None
        self._rebuild_processor_items()
        self.refresh_table()
        self._clear_active_dialog()

    def _on_diff_apply_placeholder(
        self, left: str, right: str, inverse: bool
    ):  # pragma: no cover
        self._log.info(
            "Apply differential edit left=%s right=%s inverse=%s", left, right, inverse
        )
        if not self._current_model:
            return
        if not self._current_model.processors:
            self._current_model.processors = {}
        diff_list = self._current_model.processors.get("differential")
        if not isinstance(diff_list, list):
            diff_list = []
            self._current_model.processors["differential"] = diff_list

        # If we were editing an existing entry, mutate it; otherwise add new
        updated = False
        try:
            if (
                hasattr(self, "_editing_diff_entry")
                and self._editing_diff_entry in diff_list
            ):
                entry = self._editing_diff_entry
                entry["left"] = left
                entry["right"] = right
                entry["inverse"] = bool(inverse)
                updated = True
        except Exception:
            pass
        if not updated:
            # Ensure uniqueness: remove any existing with same pair first
            diff_list[:] = [
                e
                for e in diff_list
                if not (
                    isinstance(e, dict)
                    and e.get("left") == left
                    and e.get("right") == right
                )
            ]
            diff_list.append({"left": left, "right": right, "inverse": bool(inverse)})
        # Recompute processor items list
        self._rebuild_processor_items()

        # Persist model if manager supports it
        if self._model_manager and hasattr(self._model_manager, "save_model"):
            try:
                self._model_manager.save_model(self._current_model)
            except Exception:
                self._log.warning("Failed to save model after differential edit")
        self.refresh_table()
        # Clear edit reference
        if hasattr(self, "_editing_diff_entry"):
            self._editing_diff_entry = None
