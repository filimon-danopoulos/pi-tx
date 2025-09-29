from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.tab import MDTabsBase

from ....components.data_table import (
    DataTable,
    ColumnSpec,
    GlobalAction,
    ActionItem,
    InlineCreateConfig,
)

from .....config.settings import STICK_MAPPING_FILE
from .....infrastructure.file_cache import load_json
from .....logging_config import get_logger


class ChannelsTab(MDBoxLayout, MDTabsBase):
    """Tab containing the channels data table."""

    # Pre-compute common dp values for better performance
    # Size hint distribution approximating previous dp widths (total ~135)
    _column_size_hints = [0.18, 0.20, 0.22, 0.22, 0.18]

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=0, **kwargs)
        self.title = "Channels"
        self.icon = "view-list"
        self._log = get_logger(__name__)

        self._table = None
        self._current_model = None

    def set_model(self, model, model_manager):
        """Set the current model and model manager reference."""
        self._current_model = model
        self._model_manager = model_manager
        self._create_channels_table()

    def refresh_table(self):
        """Refresh the table data and update display."""
        if self._table:
            self._table.refresh()

    def _refresh_content(self):
        """Rebuild the content with channel data table."""
        # Clear all widgets
        self.clear_widgets()
        if not self._current_model:
            self._show_error("No model selected")
            return
        self._create_channels_table()

    def _create_channels_table(self):
        """Create and display the channels data table."""

        def row_provider():
            return self._build_rows()

        self._table = DataTable(
            columns=[
                ColumnSpec(
                    "channel",
                    "Channel",
                    self._column_size_hints[0],
                    extractor=lambda r: r[0],
                ),
                ColumnSpec(
                    "type", "Type", self._column_size_hints[1], extractor=lambda r: r[1]
                ),
                ColumnSpec(
                    "device",
                    "Device",
                    self._column_size_hints[2],
                    extractor=lambda r: r[2],
                ),
                ColumnSpec(
                    "control",
                    "Control",
                    self._column_size_hints[3],
                    extractor=lambda r: r[3],
                ),
                ColumnSpec(
                    "code", "Code", self._column_size_hints[4], extractor=lambda r: r[4]
                ),
            ],
            row_provider=row_provider,
            row_actions_builder=self._row_actions,  # mocked actions for now
            inline_create=InlineCreateConfig(
                placeholder="Add ch #",
                validator=self._validate_new_channel,
                create_handler=self._inline_add_channel,
                helper_text="Number 1-99; creates placeholder",
            ),
            global_actions=[
                GlobalAction(
                    text="Model Channels: Refresh",
                    icon="refresh",
                    callback=self.refresh_table,
                )
            ],
        )
        self.add_widget(self._table)

    def _build_rows(self):
        if not self._current_model or not self._current_model.channels:
            return [("-", "-", "-", "-", "-")]

        stick_mapping = self._load_stick_mapping()
        channels = self._current_model.channels
        rows = []
        for ch_id in sorted(channels.keys()):
            channel = channels[ch_id]
            if not channel.device_path:
                device_display = "Virtual"
            else:
                device_info = stick_mapping.get(channel.device_path, {})
                device_display = device_info.get("name", "Unknown Device")
                if device_display == "Unknown Device":
                    device_display = (
                        channel.device_path.split("/")[-1]
                        if "/" in channel.device_path
                        else channel.device_path
                    )
            channel_name = f"ch{channel.channel_id}"
            control_type = channel.control_type.title()
            control_display = f"Code {channel.control_code}"
            control_code_str = str(channel.control_code)
            rows.append(
                (
                    channel_name,
                    control_type,
                    device_display,
                    control_display,
                    control_code_str,
                )
            )
        return rows

    def _refresh_table(self, *args):
        """Refresh the table data and update display."""
        if self._table:
            self._table.refresh()

    # ------------------------------------------------------------------
    # Mocked per-row actions
    # ------------------------------------------------------------------
    def _row_actions(self, row):  # pragma: no cover - UI only
        channel_name = row[0]
        return [
            ActionItem("Edit", lambda r=channel_name: self._mock_edit(r)),
            ActionItem(
                "Toggle Reverse", lambda r=channel_name: self._mock_toggle_reverse(r)
            ),
            ActionItem("Delete", lambda r=channel_name: self._mock_delete(r)),
        ]

    def _mock_edit(self, channel_name):  # pragma: no cover - placeholder
        self._log.info("Mock edit action for %s", channel_name)

    def _mock_toggle_reverse(self, channel_name):  # pragma: no cover
        self._log.info("Mock toggle reverse for %s", channel_name)

    def _mock_delete(self, channel_name):  # pragma: no cover
        self._log.info("Mock delete for %s", channel_name)

    # ------------------------------------------------------------------
    # Inline create helpers (adds placeholder channel to current model)
    # ------------------------------------------------------------------
    def _validate_new_channel(self, text: str) -> bool:  # pragma: no cover
        if not text.isdigit():
            return False
        ch = int(text)
        if ch < 1 or ch > 99:
            return False
        if not self._current_model:
            return False
        # current model uses integer channel ids
        existing = self._current_model.channels.keys() if self._current_model else []
        return ch not in existing

    def _inline_add_channel(self, text: str):  # pragma: no cover
        try:
            if not self._current_model:
                return False
            ch = int(text)
            if ch in self._current_model.channels:
                return False
            # Minimal placeholder channel config
            from .....domain.model_json import ChannelConfig

            self._current_model.channels[ch] = ChannelConfig(
                channel_id=ch,
                control_type="unipolar",
                device_path="",
                control_code="virtual",
                device_name="",
                control_name="",
            )
            # If model_manager has a save method, attempt persistence
            if hasattr(self, "_model_manager") and hasattr(
                self._model_manager, "save_model"
            ):
                try:
                    self._model_manager.save_model(self._current_model)
                except Exception:  # pragma: no cover
                    self._log.info("Model manager save unavailable or failed")
            self.refresh_table()
            return True
        except Exception as e:  # pragma: no cover
            self._log.warning("Inline add failed: %s", e)
            return False

    def _load_stick_mapping(self):
        """Load stick mapping from JSON file using file cache."""
        return load_json(STICK_MAPPING_FILE, default_value={})

    def _show_error(self, error_msg: str):
        """Show an error message."""
        # Clear all widgets
        self.clear_widgets()

        error_label = MDLabel(text=error_msg, theme_text_color="Error", halign="center")
        self.add_widget(error_label)

