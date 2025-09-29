from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout

from ....components.data_table import (
    DataTable,
    ColumnSpec,
    ActionItem,
    GlobalAction,
    InlineCreateConfig,
)

from .....domain.value_store import value_store
from .....logging_config import get_logger
from .dialogs.value_add_dialog import ValueAddDialog
from .dialogs.value_remove_dialog import ValueRemoveDialog


class ValueStoreTab(MDBoxLayout, MDTabsBase):
    """Tab for viewing value store data in read-only mode (FAB removed)."""

    # Required properties for MDTabsBase
    icon = "table"
    title = "System Values"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 0
        self.padding = 0
        # Ensure tab fills available space
        self.size_hint = (1, 1)

        # Logger
        self._log = get_logger(__name__)

        # Table and selection state
        self._table = None
        self._selected_rows: list[tuple] = []  # hold last rows pending removal
        # Dialog references
        self._add_dialog = None
        self._remove_dialog = None

        # Layout container for table content
        self._float_layout = MDFloatLayout()

        # Create the table immediately
        self._create_table()

        # Add the float layout to the main container
        self.add_widget(self._float_layout)

    def _create_table(self):
        """Create generic DataTable for value store view."""

        def row_provider():
            return self._build_rows()

        def row_actions_builder(row):  # pragma: no cover - UI event
            return [
                ActionItem("Remove", lambda r=row: self._prepare_and_remove([r])),
                ActionItem("Refresh", lambda: self._refresh_table()),
            ]

        self._table = DataTable(
            columns=[
                ColumnSpec("id", "Id", 0.14, extractor=lambda r: r[0]),
                ColumnSpec("device", "Device", 0.26, extractor=lambda r: r[1]),
                ColumnSpec("control", "Control", 0.20, extractor=lambda r: r[2]),
                ColumnSpec("type", "Type", 0.20, extractor=lambda r: r[3]),
                ColumnSpec("rev", "Reversed", 0.10, extractor=lambda r: r[4]),
            ],
            row_provider=row_provider,
            row_actions_builder=row_actions_builder,
            inline_create=InlineCreateConfig(
                placeholder="Add channel (1-32)",
                validator=self._validate_inline_channel,
                create_handler=self._inline_add_channel,
                helper_text="Enter number; adds default unipolar channel",
            ),
            global_actions=[
                GlobalAction(
                    text="Values: Add", icon="plus", callback=self._show_add_dialog
                ),
                GlobalAction(
                    text="Values: Remove Selected",
                    icon="delete",
                    callback=lambda: self._show_remove_confirmation(
                        self._selected_rows
                    ),
                ),
                GlobalAction(
                    text="Values: Refresh",
                    icon="refresh",
                    callback=self._refresh_table,
                ),
            ],
        )
        self._float_layout.add_widget(self._table)

    def on_size(self, instance, size):  # noqa: D401 (simple handler)
        """Called when tab size changes (unused)."""
        pass

    def _build_rows(self):
        rows = []
        for ch in range(1, value_store.size() + 1):
            ch_type = value_store.get_channel_type(ch)
            is_reversed = value_store.is_reversed(ch)
            has_config = ch_type != "unipolar" or is_reversed
            if has_config:
                rows.append(
                    (
                        f"var{ch}",
                        value_store.get_device_name(ch),
                        value_store.get_control_name(ch),
                        ch_type,
                        "Yes" if is_reversed else "No",
                    )
                )
        if not rows:
            rows.append(("-", "No configured channels", "-", "-", "-"))
        return rows

    def _refresh_table(self, *args):  # noqa: D401
        self._selected_rows = []
        if self._table:
            self._table.refresh()

    # Selection assistance – track last row passed for removal when invoking dialog
    def _prepare_and_remove(self, rows):  # pragma: no cover - UI event
        self._selected_rows = list(rows)
        self._show_remove_confirmation(self._selected_rows)

    def _show_add_dialog(self):
        """Show dialog to add new system value."""
        if not self._add_dialog:
            self._add_dialog = ValueAddDialog(
                on_confirm=self._add_system_value,
                on_cancel=lambda: None,
            )
        self._add_dialog.show_dialog()

    def _show_remove_confirmation(self, selected_rows):
        """Show confirmation dialog for removing selected system values."""
        if not selected_rows:
            self._log.info("No rows selected for removal")
            return

        if not self._remove_dialog:
            self._remove_dialog = ValueRemoveDialog(
                on_confirm=self._remove_system_values,
                on_cancel=lambda: None,
            )
        self._remove_dialog.show_dialog(selected_rows)

    def _add_system_value(self, channel_num):
        """Add a new system value based on user input."""
        try:
            if not hasattr(value_store, "_channel_values"):
                self._log.error("Value store not initialized")
                return False

            value_store._channel_values[channel_num] = {  # type: ignore[attr-defined]
                "control_type": "unipolar",
                "device_path": "manual",
                "control_code": f"manual_{channel_num}",
            }
            value_store.save_configuration()
            self._refresh_table()
            self._log.info("Added system value for channel %s", channel_num)
            return True
        except Exception as e:  # pragma: no cover - defensive
            self._log.error("Error adding system value: %s", e)
            return False

    # Inline create helpers -------------------------------------------
    def _validate_inline_channel(self, text: str) -> bool:  # pragma: no cover
        if not text.isdigit():
            return False
        ch = int(text)
        if not (1 <= ch <= value_store.size()):
            return False
        # Accept if not already configured
        return ch not in getattr(value_store, "_channel_values", {})

    def _inline_add_channel(self, text: str):  # pragma: no cover
        try:
            ch = int(text)
            if not (1 <= ch <= value_store.size()):
                return False
            if ch in getattr(value_store, "_channel_values", {}):
                return False
            value_store._channel_values[ch] = {  # type: ignore[attr-defined]
                "control_type": "unipolar",
                "device_path": "manual",
                "control_code": f"manual_{ch}",
            }
            value_store.save_configuration()
            self._refresh_table()
            return True
        except Exception as e:  # pragma: no cover
            self._log.error("Inline add failed: %s", e)
            return False

    def _remove_system_values(self, selected_rows):
        """Remove multiple selected system values."""
        try:
            if not selected_rows:
                self._log.info("No rows selected for removal")
                return

            removed_channels = []
            failed_removals = []

            for row in selected_rows:
                try:
                    if isinstance(row, (list, tuple)) and len(row) > 0:
                        row_id = row[0]
                    else:
                        self._log.warning("Invalid row selection format: %s", row)
                        failed_removals.append(str(row))
                        continue

                    if row_id and isinstance(row_id, str) and row_id.startswith("var"):
                        channel_num = int(row_id[3:])
                        if (
                            hasattr(value_store, "_channel_values")
                            and channel_num in value_store._channel_values  # type: ignore[attr-defined]
                        ):
                            del value_store._channel_values[channel_num]  # type: ignore[attr-defined]
                        value_store.set_reverse(channel_num, False)
                        value_store.save_configuration()
                        removed_channels.append(channel_num)
                        self._log.info(
                            "Removed system value for channel %s", channel_num
                        )
                    else:
                        self._log.warning(
                            "Cannot determine channel number from row ID: %s", row_id
                        )
                        failed_removals.append(str(row_id))
                except (ValueError, IndexError) as e:
                    self._log.warning("Error processing row %s: %s", row, e)
                    failed_removals.append(str(row))
                    continue

            self._selected_rows = []
            self._refresh_table()

            if removed_channels:
                self._log.info(
                    "Removed %d system values: %s",
                    len(removed_channels),
                    removed_channels,
                )
            if failed_removals:
                self._log.warning(
                    "Failed to remove %d items: %s",
                    len(failed_removals),
                    failed_removals,
                )
            return True
        except Exception as e:  # pragma: no cover - defensive
            self._log.error("Error removing system values: %s", e)
            return False

    # New action provider for global FAB menu
    def get_actions(self):  # pragma: no cover - delegate to generic table
        if self._table:
            return self._table.get_actions()
        return []
