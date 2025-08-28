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

"""KivyMD GUI application providing model selection and live channel values."""

from state import channel_state

MODELS_DIR = "models"


class ChannelRow(MDBoxLayout):
    """Simple two-column row for a channel label and its current value."""

    def __init__(self, channel_number: int, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height="40dp",
            padding=(10, 0, 10, 0),
            **kwargs,
        )
        self.channel_number = channel_number
        self.label = MDLabel(
            text=f"CH_{channel_number}", halign="left", size_hint_x=0.4
        )
        self.value_label = MDLabel(text="0.00", halign="right")
        self.add_widget(self.label)
        self.add_widget(self.value_label)

    def update_value(self, value: float):
        self.value_label.text = f"{value:.2f}"


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
        return root

    # ---- Model Handling ----
    def refresh_models(self):
        self.available_models = self._list_models()
        # Close existing menu if open
        if hasattr(self, "_model_menu") and self._model_menu:
            self._model_menu.dismiss()
        self._model_menu = None

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
            row = ChannelRow(ch)
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
        # Clear previous callbacks
        self.input_controller.clear_callbacks()
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

                def make_cb(ch_id):
                    return lambda value: channel_state.update_channel(ch_id, value)

                self.input_controller.register_callback(
                    device_path, control_code, make_cb(channel_id)
                )
            except Exception as e:
                print(f"Failed to register callback for channel {channel}: {e}")

        # Start controller if not already running
        self.input_controller.start()


def create_gui(input_controller):
    """Factory to create the PiTxApp instance.

    Args:
        input_controller: instance of InputController
    Returns:
        PiTxApp instance (not yet running)
    """
    return PiTxApp(input_controller=input_controller)
