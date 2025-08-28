import os
import json
from typing import Dict

from kivy.clock import Clock
from kivy.properties import StringProperty, DictProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout  # noqa: F401 (kept for potential kv usage)

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.button import MDFlatButton
from kivymd.uix.toolbar import MDTopAppBar as MDToolbar  # Using modern KivyMD component
from kivymd.uix.list import OneLineListItem
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.properties import NumericProperty, ListProperty

"""KivyMD GUI application providing model selection and live channel values."""

from state import channel_state

MODELS_DIR = "models"
LAST_MODEL_FILE = ".last_model"


class ChannelBar(Widget):
    value = NumericProperty(0.0)
    channel_type = StringProperty("unipolar")
    bar_color = ListProperty([0, 0.6, 1, 1])

    def __init__(self, channel_type: str, **kwargs):
        super().__init__(**kwargs)
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
            self.bar_color = [0.30, 0.80, 0.40, 1]  # green
        elif self.channel_type == "button":
            self.bar_color = [0.90, 0.25, 0.25, 1]  # red
        else:
            self.bar_color = [0.22, 0.55, 0.95, 1]  # blue

    def _redraw(self):
        self.canvas.clear()
        with self.canvas:
            # Background
            Color(*self._bg_color)
            Rectangle(pos=self.pos, size=self.size)
            # Foreground bar
            val = float(self.value)
            if self.channel_type == "bipolar":
                # value in -1..1, draw from center
                half_w = self.width / 2.0
                center_x = self.x + half_w
                magnitude = max(0.0, min(1.0, abs(val))) * half_w
                if val >= 0:
                    bar_x = center_x
                else:
                    bar_x = center_x - magnitude
                bar_w = magnitude
            else:
                # unipolar/button value assumed 0..1
                clamped = max(0.0, min(1.0, val))
                bar_x = self.x
                bar_w = self.width * clamped
            Color(*self.bar_color)
            Rectangle(pos=(bar_x, self.y), size=(bar_w, self.height))


class ChannelRow(MDBoxLayout):
    """Row with channel label, colored bar, and numeric value."""

    def __init__(self, channel_number: int, channel_type: str, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            padding=(dp(8), 0, dp(8), 0),
            spacing=dp(8),
            **kwargs,
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
    """Main KivyMD application handling model selection and channel display."""

    selected_model = StringProperty("")
    model_mapping: DictProperty = DictProperty({})

    def __init__(self, input_controller, **kwargs):
        super().__init__(**kwargs)
        self.input_controller = input_controller
        self.channel_rows: Dict[int, ChannelRow] = {}
        self.available_models = []
        # Register custom event for external binding (e.g. setup_controls after selection)
        self.register_event_type("on_model_selected")
        channel_state.bind(channels=self._on_channel_state_change)

    # Event stub (can be bound in main_md.py)
    def on_model_selected(self, model_name: str):  # noqa: D401 - Kivy event
        pass

    def build(self):  # noqa: D401 - Kivy build method
        self.theme_cls.primary_palette = "Blue"
        root = MDBoxLayout(orientation="vertical")

        # Top App Bar
        toolbar = MDToolbar(title="pi-tx")
        toolbar.right_action_items = [
            ["folder", lambda x: self.open_model_menu(x)],
            ["refresh", lambda x: self.refresh_models()],
        ]
        root.add_widget(toolbar)

        # Keep reference for menu anchoring
        self._toolbar = toolbar

        # Container for channels inside a scrollview
        scroll = ScrollView()
        self.channel_container = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=(0, 10, 0, 10),
            spacing=4,
        )
        self.channel_container.bind(
            minimum_height=self.channel_container.setter("height")
        )
        scroll.add_widget(self.channel_container)
        root.add_widget(scroll)

        # Initial populate of model list
        Clock.schedule_once(lambda *_: self.refresh_models(), 0)
        # Schedule queue processing for low-latency updates
        Clock.schedule_interval(self._process_input_events, 0)
        return root

    # ---- Model Handling ----
    def refresh_models(self):
        self.available_models = self._list_models()
        # Close existing menu if open
        if hasattr(self, "_model_menu") and self._model_menu:
            self._model_menu.dismiss()
        self._model_menu = None
        # Attempt auto-load of last model (only once, if none selected yet)
        if not self.selected_model:
            self._autoload_last_model()

    def open_model_menu(self, caller_widget=None):
        # Ensure models list is current
        if not getattr(self, "available_models", None):
            self.refresh_models()

        items = []
        for model_name in self.available_models:

            def _cb(m=model_name):
                self._select_model_and_close(m)

            items.append(
                {
                    "viewclass": "OneLineListItem",
                    "text": model_name,
                    "on_release": _cb,
                }
            )
        if not items:
            items = [
                {
                    "viewclass": "OneLineListItem",
                    "text": "No models found",
                    "on_release": lambda: None,
                }
            ]

        # Close existing menu if open
        if hasattr(self, "_model_menu") and self._model_menu:
            self._model_menu.dismiss()

        self._model_menu = MDDropdownMenu(
            caller=caller_widget or self._toolbar,
            items=items,
            width_mult=4,
        )
        self._model_menu.open()

    def _select_model_and_close(self, model_name: str):
        if self._model_menu:
            self._model_menu.dismiss()
        self.select_model(model_name)

    def select_model(self, model_name: str):
        """Load selected model mapping, apply it (register callbacks) and update UI."""
        path = os.path.join(MODELS_DIR, f"{model_name}.json")
        try:
            with open(path, "r") as f:
                mapping = json.load(f)
        except FileNotFoundError:
            mapping = {"name": model_name, "channels": {}}

        self.selected_model = model_name
        self.model_mapping = mapping
        # Update toolbar title to reflect model
        if hasattr(self, "_toolbar") and self._toolbar:
            self._toolbar.title = f"pi-tx: {model_name}"
        self._rebuild_channel_rows()
        # Apply mapping to input controller
        self._apply_model_mapping()
        # Signal selection (legacy external binds)
        self.dispatch("on_model_selected", model_name)
        # Persist last selected model name
        try:
            with open(LAST_MODEL_FILE, "w") as f:
                f.write(model_name.strip())
        except Exception as e:
            print(f"Warning: couldn't persist last model: {e}")

    def _list_models(self):
        if not os.path.exists(MODELS_DIR):
            return []
        return sorted([f[:-5] for f in os.listdir(MODELS_DIR) if f.endswith(".json")])

    # ---- Channel Display ----
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
            row.update_value(channel_state.get_channel(ch))
            self.channel_rows[ch] = row
            self.channel_container.add_widget(row)

    def _on_channel_state_change(self, *_):
        # Update only rows we display
        for ch, row in self.channel_rows.items():
            row.update_value(channel_state.get_channel(ch))

    # ---- Input Controller Callback Wiring ----
    def _apply_model_mapping(self):
        """Register callbacks for current model mapping directly without file persistence."""
        if not self.input_controller:
            return
        # Clear previous callbacks and enable queue mode
        self.input_controller.clear_callbacks()
        self.input_controller.enable_queue_mode()
        channels = self.model_mapping.get("channels", {})
        # Zero channels not in mapping to avoid stale values
        for ch in list(channel_state.channels.keys()):
            if str(ch) not in channels:
                channel_state.update_channel(ch, 0.0)

        for channel, mapping in channels.items():
            try:
                channel_id = int(channel)
                device_path = mapping["device_path"]
                control_code = int(mapping["control_code"])

                # Register mapping for queue mode
                self.input_controller.register_channel_mapping(
                    device_path, control_code, channel_id
                )
            except Exception as e:
                print(f"Failed to register callback for channel {channel}: {e}")

        # Start controller if not already running
        self.input_controller.start()

    def _process_input_events(self, *_):
        if not self.input_controller:
            return
        for ch_id, value in self.input_controller.pop_events():
            # Update state (if others rely on it) and row directly
            channel_state.update_channel(ch_id, value)
            row = self.channel_rows.get(ch_id)
            if row:
                row.update_value(value)

    # ---- Last Model Autoload ----
    def _autoload_last_model(self):
        try:
            if os.path.exists(LAST_MODEL_FILE):
                with open(LAST_MODEL_FILE, "r") as f:
                    name = f.read().strip()
                if name and name in self.available_models:
                    # Delay selection to allow UI build completion
                    Clock.schedule_once(lambda *_: self.select_model(name), 0)
        except Exception as e:
            print(f"Warning: failed to autoload last model: {e}")


def create_gui(input_controller):
    """Factory to create the PiTxApp instance.

    Args:
        input_controller: instance of InputController
    Returns:
        PiTxApp instance (not yet running)
    """
    return PiTxApp(input_controller=input_controller)
