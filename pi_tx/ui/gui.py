from __future__ import annotations
from typing import Dict
from kivy.clock import Clock
from kivy.properties import StringProperty, DictProperty
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.toolbar import MDTopAppBar as MDToolbar
from kivymd.uix.list import OneLineListItem
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.properties import NumericProperty, ListProperty

from ..domain.model_repo import ModelRepository, Model
from ..domain.channel_store import channel_store
from ..input.controls import InputController
from ..config.settings import MODELS_DIR, LAST_MODEL_FILE


class ChannelBar(Widget):
    value = NumericProperty(0.0)
    channel_type = StringProperty("unipolar")
    bar_color = ListProperty([0, 0.6, 1, 1])

    def __init__(self, channel_type: str, **kw):
        super().__init__(**kw)
        self.channel_type = channel_type or "unipolar"
        self._bg_color = (0.18, 0.18, 0.18, 1)
        self._update_bar_color()
        self.bind(
            pos=lambda *_: self._redraw(),
            size=lambda *_: self._redraw(),
            value=lambda *_: self._redraw(),
        )

    def _update_bar_color(self):
        if self.channel_type == "bipolar":
            self.bar_color = [0.30, 0.80, 0.40, 1]
        elif self.channel_type == "button":
            self.bar_color = [0.90, 0.25, 0.25, 1]
        else:
            self.bar_color = [0.22, 0.55, 0.95, 1]

    def _redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self._bg_color)
            Rectangle(pos=self.pos, size=self.size)
            val = float(self.value)
            if self.channel_type == "bipolar":
                half_w = self.width / 2.0
                center_x = self.x + half_w
                magnitude = max(0.0, min(1.0, abs(val))) * half_w
                bar_x = center_x if val >= 0 else center_x - magnitude
                bar_w = magnitude
            else:
                clamped = max(0.0, min(1.0, val))
                bar_x = self.x
                bar_w = self.width * clamped
            Color(*self.bar_color)
            Rectangle(pos=(bar_x, self.y), size=(bar_w, self.height))


class ChannelRow(MDBoxLayout):
    def __init__(self, channel_number: int, channel_type: str, **kw):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            padding=(dp(8), 0, dp(8), 0),
            spacing=dp(8),
            **kw,
        )
        self.channel_number = channel_number
        self.channel_type = channel_type or "unipolar"
        self.label = MDLabel(
            text=f"CH_{channel_number}", size_hint_x=None, width=dp(60)
        )
        self.bar = ChannelBar(self.channel_type, size_hint_x=1)
        self.value_label = MDLabel(
            text="0.00", size_hint_x=None, width=dp(60), halign="right"
        )
        self.add_widget(self.label)
        self.add_widget(self.bar)
        self.add_widget(self.value_label)

    def update_value(self, value: float):
        self.bar.value = value
        self.value_label.text = (
            f"{value:+.2f}" if self.channel_type == "bipolar" else f"{value:.2f}"
        )


class PiTxApp(MDApp):
    selected_model = StringProperty("")
    model_mapping: DictProperty = DictProperty({})

    def __init__(self, input_controller: InputController, **kw):
        super().__init__(**kw)
        self.input_controller = input_controller
        self.channel_rows = {}
        self.available_models = []
        self._model_repo = ModelRepository(MODELS_DIR)
        self._current_model: Model | None = None
        self.register_event_type("on_model_selected")

    def on_model_selected(self, model_name: str):
        pass

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        root = MDBoxLayout(orientation="vertical")
        toolbar = MDToolbar(title="pi-tx")
        toolbar.right_action_items = [
            ["folder", lambda x: self.open_model_menu(x)],
            ["refresh", lambda x: self.refresh_models()],
        ]
        root.add_widget(toolbar)
        self._toolbar = toolbar
        scroll = ScrollView()
        self.channel_container = MDBoxLayout(
            orientation="vertical", size_hint_y=None, padding=(0, 10, 0, 10), spacing=4
        )
        self.channel_container.bind(
            minimum_height=self.channel_container.setter("height")
        )
        scroll.add_widget(self.channel_container)
        root.add_widget(scroll)
        Clock.schedule_once(lambda *_: self.refresh_models(), 0)
        Clock.schedule_interval(self._process_input_events, 0)
        return root

    def refresh_models(self):
        self.available_models = self._model_repo.list_models()
        if hasattr(self, "_model_menu") and self._model_menu:
            self._model_menu.dismiss()
            self._model_menu = None
        if not self.selected_model:
            self._autoload_last_model()

    def open_model_menu(self, caller_widget=None):
        if not getattr(self, "available_models", None):
            self.refresh_models()
        items = []
        for model_name in self.available_models:

            def _cb(m=model_name):
                self._select_model_and_close(m)

            items.append(
                {"viewclass": "OneLineListItem", "text": model_name, "on_release": _cb}
            )
        if not items:
            items = [
                {
                    "viewclass": "OneLineListItem",
                    "text": "No models found",
                    "on_release": lambda: None,
                }
            ]
        if hasattr(self, "_model_menu") and self._model_menu:
            self._model_menu.dismiss()
        from kivymd.uix.menu import MDDropdownMenu

        self._model_menu = MDDropdownMenu(
            caller=caller_widget or self._toolbar, items=items, width_mult=4
        )
        self._model_menu.open()

    def _select_model_and_close(self, model_name: str):
        if getattr(self, "_model_menu", None):
            self._model_menu.dismiss()
            self.select_model(model_name)

    def select_model(self, model_name: str):
        model = self._model_repo.load_model(model_name)
        self._current_model = model
        self.selected_model = model.name
        self.model_mapping = {
            "name": model.name,
            "channels": {
                str(k): {
                    "device_path": v.device_path,
                    "control_code": v.control_code,
                    "control_type": v.control_type,
                }
                for k, v in model.channels.items()
            },
        }
        if hasattr(self, "_toolbar") and self._toolbar:
            self._toolbar.title = f"pi-tx: {model_name}"
        self._rebuild_channel_rows()
        self._apply_model_mapping()
        self.dispatch("on_model_selected", model_name)
        try:
            with open(LAST_MODEL_FILE, "w") as f:
                f.write(model_name.strip())
        except Exception as e:
            print(f"Warning: couldn't persist last model: {e}")

    def _rebuild_channel_rows(self):
        self.channel_container.clear_widgets()
        self.channel_rows.clear()
        channels = self.model_mapping.get("channels", {})
        if not channels:
            self.channel_container.add_widget(
                MDLabel(text="No channels configured", halign="center")
            )
            return
        for ch_str in sorted(channels.keys(), key=lambda x: int(x)):
            ch = int(ch_str)
            ch_type = channels[ch_str].get(
                "control_type", channels[ch_str].get("type", "unipolar")
            )
            row = ChannelRow(ch, ch_type)
            row.update_value(channel_store.get(ch))
            self.channel_rows[ch] = row
            self.channel_container.add_widget(row)

    def _apply_model_mapping(self):
        if not self.input_controller:
            return
        self.input_controller.clear_callbacks()
        self.input_controller.enable_queue_mode()
        channels = self.model_mapping.get("channels", {})
        for ch, row in self.channel_rows.items():
            if str(ch) not in channels:
                row.update_value(0.0)
        for channel, mapping in channels.items():
            try:
                channel_id = int(channel)
                device_path = mapping["device_path"]
                control_code = int(mapping["control_code"])
                self.input_controller.register_channel_mapping(
                    device_path, control_code, channel_id
                )
            except Exception as e:
                print(f"Failed to register callback for channel {channel}: {e}")
        self.input_controller.start()

    def _process_input_events(self, *_):
        if not self.input_controller:
            return
        last: Dict[int, float] = {}
        for ch_id, value in self.input_controller.pop_events():
            last[ch_id] = value
        for ch_id, value in last.items():
            channel_store.set(ch_id, value)
            row = self.channel_rows.get(ch_id)
            if row:
                row.update_value(value)

    def _autoload_last_model(self):
        try:
            if LAST_MODEL_FILE.exists():
                name = LAST_MODEL_FILE.read_text().strip()
                if name and name in self._model_repo.list_models():
                    Clock.schedule_once(lambda *_: self.select_model(name), 0)
        except Exception as e:
            print(f"Warning: failed to autoload last model: {e}")


def create_gui(input_controller: InputController):
    return PiTxApp(input_controller=input_controller)
