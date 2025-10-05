from __future__ import annotations

from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.slider import MDSlider
from kivymd.uix.menu import MDDropdownMenu  # legacy for now (sources unaffected)
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.metrics import dp
from kivymd.uix.dialog import MDDialog
from kivy.clock import Clock
from .....components.settings_dialog import SettingsDialog
from .....components.option_menu_button import OptionMenuButton


class AggregateEditDialog(SettingsDialog):  # pragma: no cover
    def __init__(self, on_close=None, on_apply=None):
        super().__init__(title="Aggregate", on_close=on_close, add_close_button=True)
        self.on_apply = on_apply
        self._config_ref = None
        self.on_delete = None
        self._delete_confirm_dialog = None
        # dynamic UI state
        self._all_channels = []  # list[str]
        self._target_btn = None
        self._source_rows = []  # list of dict entries {row, channel, slider }
        self._menus = []
        self._sources_container = None
        # cached layout width (fixed pixel layout inside dialog body)
        self._inner_width = (
            self.DIALOG_W - 16
        )  # approximate horizontal padding allowance

    # Override base buttons to inject DELETE when allowed
    def build_buttons(self):  # pragma: no cover
        buttons = []
        if self.on_delete:
            del_btn = MDFlatButton(
                text="DELETE", on_release=lambda *_: self._open_delete_confirm()
            )
            try:
                del_btn.theme_text_color = "Custom"
                del_btn.text_color = (1, 0.25, 0.25, 1)
            except Exception:
                pass
            buttons.append(del_btn)
        buttons.append(MDFlatButton(text="CLOSE", on_release=lambda *_: self.close()))
        buttons.append(
            MDRaisedButton(text="APPLY", on_release=lambda *_: self._apply())
        )
        return buttons

    def show(
        self,
        all_channels: list[str],  # unused placeholder
        config: dict | None = None,
        *,
        can_delete: bool = False,
        on_delete=None,
    ):
        if self.dialog and self.dialog.parent:
            return
        self._all_channels = all_channels[:] if all_channels else ["ch1"]
        self._config_ref = config
        self.on_delete = on_delete if can_delete else None
        # reset dynamic state
        self._source_rows.clear()
        self._menus.clear()
        self.open()
        Clock.schedule_once(lambda *_: self._build_contents(), 0)

    # Build content after dialog body created ---------------------
    def _build_contents(self):  # pragma: no cover
        if not self.body:
            return
        self.body.clear_widgets()
        target, channels = self._extract_config(self._config_ref)
        # Target row (using abstraction)
        # Target channel selector using OptionMenuButton
        def target_options():
            return self._all_channels

        self._target_btn = OptionMenuButton(
            text=target,
            options_provider=target_options,
            on_select=lambda *_: self._rebuild_sources({
                entry.get("channel"): entry.get("slider").value
                for entry in self._source_rows if entry.get("channel")
            }),
        )

        t_row = self.make_input_row("Target", self._target_btn, content_align="fill")
        self.body.add_widget(t_row)

        # Divider for sources
        self.body.add_widget(self.make_divider("Channel Weights"))

        self._sources_container = MDBoxLayout(
            orientation="vertical", spacing=dp(4), size_hint_y=None
        )
        self._sources_container.bind(
            minimum_height=lambda inst, val: setattr(inst, "height", val)
        )
        self.body.add_widget(self._sources_container)
        weight_map = {cid: wt for cid, wt in channels}
        self._rebuild_sources(weight_map)
    # No manual binding needed; OptionMenuButton handles its own menu

    # Extract config -----------------------------------------------
    def _extract_config(self, config):  # pragma: no cover
        target = None
        chs = []
        if isinstance(config, dict):
            t = config.get("target")
            if isinstance(t, str):
                target = t
            for e in config.get("channels") or []:
                if isinstance(e, dict):
                    cid = e.get("id") or e.get("ch") or e.get("channel")
                    if isinstance(cid, str):
                        try:
                            wt = float(e.get("value", 0.0))
                        except Exception:
                            wt = 0.0
                        chs.append((cid, wt))
        if not chs:
            chs.append((self._all_channels[0], 0.0))
        if not target:
            target = chs[0][0]
        return target, chs

    def _rebuild_sources(
        self, weight_map: dict[str, float] | None = None
    ):  # pragma: no cover
        if not self._sources_container:
            return
        self._sources_container.clear_widgets()
        self._source_rows.clear()
        target = self._target_btn.text if self._target_btn else None
        other_channels = [ch for ch in self._all_channels if ch != target]
        if not other_channels:
            self._sources_container.add_widget(
                MDLabel(text="No other channels", size_hint_y=None, height=dp(24))
            )
            return
        for ch in other_channels:
            init = 0.0
            if weight_map and ch in weight_map:
                try:
                    init = float(weight_map[ch])
                except Exception:
                    init = 0.0
            # clamp
            init = max(0.0, min(1.0, init))
            slider = MDSlider(min=0.0, max=1.0, value=init, step=0.05)
            row = self.make_input_row(ch, slider, content_align="fill")
            self._sources_container.add_widget(row)
            self._source_rows.append({"row": row, "channel": ch, "slider": slider})

    # _bind_dropdown removed (OptionMenuButton now used)

    def _apply(self):  # pragma: no cover
        target = self._target_btn.text if self._target_btn else None
        sources = []
        for entry in self._source_rows:
            ch = entry.get("channel")
            slider = entry.get("slider")
            if not ch or slider is None:
                continue
            wt = float(getattr(slider, "value", 0.0) or 0.0)
            if abs(wt) > 1e-6:
                sources.append({"id": ch, "value": wt})
        if not target and sources:
            target = sources[0]["id"]
        if self.on_apply:
            try:
                self.on_apply(target, sources)
            except Exception:
                pass
        self.close()

    # Delete handling -------------------------------------------------
    def _open_delete_confirm(self):  # pragma: no cover
        if self._delete_confirm_dialog and self._delete_confirm_dialog.parent:
            return
        self._delete_confirm_dialog = MDDialog(
            title="Confirm Delete",
            text="Delete this aggregate processor? This cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="CANCEL", on_release=lambda *_: self._dismiss_delete_confirm()
                ),
                MDRaisedButton(
                    text="DELETE",
                    md_bg_color=(0.9, 0.3, 0.3, 1),
                    on_release=lambda *_: self._perform_delete(),
                ),
            ],
        )
        self._delete_confirm_dialog.open()

    def _dismiss_delete_confirm(self):  # pragma: no cover
        if self._delete_confirm_dialog:
            try:
                self._delete_confirm_dialog.dismiss()
            except Exception:
                pass
            self._delete_confirm_dialog = None

    def _perform_delete(self):  # pragma: no cover
        try:
            if self.on_delete:
                self.on_delete()
        except Exception:
            pass
        self._dismiss_delete_confirm()
        self.close()

    def close(self):  # pragma: no cover
        # Ensure confirm dialog closed
        self._dismiss_delete_confirm()
        super().close()
