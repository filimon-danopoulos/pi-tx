from __future__ import annotations

import uuid
from pathlib import Path
from typing import Iterable

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase

from ....components.data_table import (
    DataTable,
    ColumnSpec,
    ActionItem,
    GlobalAction,
    InlineCreateConfig,
)
from .dialogs.model_create_dialog import ModelCreateDialog
from .dialogs.model_remove_dialog import ModelRemoveDialog
from .....infrastructure.file_cache import load_json, save_json
from .....logging_config import get_logger


class ModelsTab(MDBoxLayout, MDTabsBase):  # pragma: no cover - UI heavy
    """Models management using the generic DataTable.

    Previously this logic lived in a separate `ModelTable` wrapper; now inlined
    for simplicity since we have a reusable generic table.
    """

    def __init__(self, app=None, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self._log = get_logger(__name__)
        self.title = "Models"
        self.icon = "folder-multiple"
        self.app = app

        # Dialog refs
        self.remove_dialog: ModelRemoveDialog | None = None
        self.create_dialog: ModelCreateDialog | None = None
        self._pending_remove: set[str] = set()

        # Configure the generic table
        self._table = DataTable(
            columns=[
                ColumnSpec("name", "Model Name", 0.45, extractor=lambda r: r[0]),
                ColumnSpec("rx", "RX", 0.15, extractor=lambda r: r[1]),
                ColumnSpec("channels", "Channels", 0.20, extractor=lambda r: r[2]),
            ],
            row_provider=self._get_models,
            row_actions_builder=self._row_actions,
            inline_create=InlineCreateConfig(
                placeholder="New model name",
                validator=self._validate_new_name,
                create_handler=self._save_new_model,
                helper_text="letters/numbers/_",
            ),
            global_actions=[
                GlobalAction(
                    text="Models: Create New",
                    icon="plus-box",
                    callback=self._show_create_model_dialog,
                ),
                GlobalAction(
                    text="Models: Refresh", icon="refresh", callback=self.refresh_models
                ),
            ],
        )
        self.add_widget(self._table)

    # Public API -------------------------------------------------------
    def set_app(self, app):  # pragma: no cover
        self.app = app
        self.refresh_models()
        if hasattr(app, "bind"):
            app.bind(on_model_selected=lambda *_: self.refresh_models())

    def refresh_models(self):  # pragma: no cover
        if self.app and not self.app.available_models:
            self.app.refresh_models()
        self._table.refresh()


    # Data helpers -----------------------------------------------------
    def _get_models(self) -> Iterable[tuple[str, str, str]]:
        if not self.app or not self.app.available_models:
            return []
        rows: list[tuple[str, str, str]] = []
        for name in self.app.available_models:
            try:
                p = Path("models") / f"{name}.json"
                if p.exists():
                    d = load_json(str(p))
                    rx = d.get("rx_num", "?")
                    ch = len(d.get("channels", {}))
                else:
                    rx = ch = "?"
                rows.append((name, str(rx), str(ch)))
            except Exception:  # pragma: no cover
                rows.append((name, "?", "?"))
        return rows

    # Row actions ------------------------------------------------------
    def _row_actions(self, row: tuple[str, str, str]):  # pragma: no cover
        name = row[0]
        actions = []
        if self.app and hasattr(self.app, "select_model"):
            actions.append(
                ActionItem("Activate", lambda n=name: self._activate_model(n))
            )
        actions.append(ActionItem("Remove", lambda n=name: self._remove_model(n)))
        actions.append(ActionItem("Refresh", lambda: self.refresh_models()))
        return actions

    def _activate_model(self, name):  # pragma: no cover
        if self.app and hasattr(self.app, "select_model"):
            self.app.select_model(name)

    def _remove_model(self, name):  # pragma: no cover
        self._pending_remove = {name}
        self._show_remove_model_dialog()

    # Validation / creation -------------------------------------------
    def _validate_new_name(self, value: str) -> bool:  # pragma: no cover
        valid = bool(value) and all(c.isalnum() or c == "_" for c in value)
        if self.app and value in (self.app.available_models or []):
            valid = False
        return valid

    def _save_new_model(self, model_name):  # pragma: no cover
        try:
            data = {
                "name": model_name,
                "rx_num": self._allocate_rx_num(),
                "id": str(uuid.uuid4()),
                "channels": {},
            }
            models_dir = Path("models")
            models_dir.mkdir(exist_ok=True)
            model_file = models_dir / f"{model_name}.json"
            save_json(str(model_file), data)
            if self.app:
                self.app.refresh_models()
            self.refresh_models()
            self._close_create_model_dialog()
        except Exception as e:  # pragma: no cover
            self._log.error("Error saving model: %s", e)
            return False
        return True

    def _allocate_rx_num(self):  # pragma: no cover
        used = set()
        models_dir = Path("models")
        if models_dir.exists():
            for p in models_dir.glob("*.json"):
                try:
                    d = load_json(str(p))
                    if d and "rx_num" in d:
                        used.add(int(d["rx_num"]))
                except Exception:
                    continue
        for rx in range(16):
            if rx not in used:
                return rx
        return 0

    # Dialog handling --------------------------------------------------
    def _show_remove_model_dialog(self):  # pragma: no cover
        if not self._pending_remove:
            return
        name = next(iter(self._pending_remove))
        if not self.remove_dialog:
            self.remove_dialog = ModelRemoveDialog(
                on_confirm=self._confirm_remove,
                on_cancel=self._close_remove_model_dialog,
            )
        self.remove_dialog.show_dialog(name)

    def _confirm_remove(self, *args):  # pragma: no cover
        try:
            for name in self._pending_remove:
                p = Path("models") / f"{name}.json"
                if p.exists():
                    p.unlink()
            if self.app:
                if (
                    hasattr(self.app, "selected_model")
                    and getattr(self.app, "selected_model", None)
                    in self._pending_remove
                ):
                    self.app.selected_model = ""
                    if hasattr(self.app, "_current_model"):
                        self.app._current_model = None
                self.app.refresh_models()
            self.refresh_models()
        except Exception as e:  # pragma: no cover
            self._log.warning("Error removing model: %s", e)
        self._close_remove_model_dialog()

    def _close_remove_model_dialog(self, *args):  # pragma: no cover
        if self.remove_dialog:
            self.remove_dialog.close_dialog()
        self._pending_remove = set()
        return True

    def _show_create_model_dialog(self, *args):  # pragma: no cover
        if not self.create_dialog:
            self.create_dialog = ModelCreateDialog(
                on_confirm=self._save_new_model,
                on_cancel=self._close_create_model_dialog,
                existing_models=self.app.available_models if self.app else [],
            )
        if self.app:
            self.create_dialog.update_existing_models(self.app.available_models)
        self.create_dialog.show_dialog()

    def _close_create_model_dialog(self, *args):  # pragma: no cover
        if self.create_dialog:
            self.create_dialog.close_dialog()
        return True
