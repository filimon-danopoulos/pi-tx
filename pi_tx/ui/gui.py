from __future__ import annotations
from typing import Dict
from kivy.clock import Clock
from kivy.properties import StringProperty, DictProperty
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.toolbar import MDTopAppBar as MDToolbar
from kivymd.uix.list import OneLineListItem

from ..domain.channel_store import channel_store
from ..input.controls import InputController

# LAST_MODEL_FILE handling moved into ModelManager; no direct import needed here
from .services.model_manager import ModelManager, Model
from .services.model_selection import ModelSelectionController
from .services.input_event_pump import InputEventPump
from .components.channel_panel import ChannelPanel


"""GUI main module (PiTxApp) composed from smaller component modules."""


class PiTxApp(MDApp):
    selected_model = StringProperty("")
    model_mapping: DictProperty = DictProperty({})

    def __init__(self, input_controller: InputController, **kw):
        super().__init__(**kw)
        self.input_controller = input_controller
        self.channel_panel: ChannelPanel | None = None
        self.available_models: list[str] = []
        self._model_manager = ModelManager()
        self._model_selector = ModelSelectionController(
            self._model_manager, self.input_controller, None
        )
        self._current_model: Model | None = None
        self._input_pump = InputEventPump(self.input_controller, channel_store.set_many)
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
            ["wifi", lambda x: self.trigger_bind()],  # trigger bind window
        ]
        root.add_widget(toolbar)
        self._toolbar = toolbar
        scroll = ScrollView()
        self.channel_panel = ChannelPanel()
        # inform selector about panel now that it's created
        self._model_selector.set_channel_panel(self.channel_panel)
        scroll.add_widget(self.channel_panel)
        root.add_widget(scroll)
        # Schedule tasks after first frame so layout exists
        Clock.schedule_once(lambda *_: self.refresh_models(), 0)
        Clock.schedule_interval(self._input_pump.tick, 1.0 / 100.0)
        Clock.schedule_interval(self._poll_store_and_refresh, 1.0 / 30.0)
        return root

    def refresh_models(self):
        self.available_models = self._model_manager.list_models()
        if hasattr(self, "_model_menu") and self._model_menu:
            self._model_menu.dismiss()
            self._model_menu = None
        if not self.selected_model:
            self._autoload_last_model()

    def trigger_bind(self, duration: float = 2.0):
        try:
            from ..app import UART_SENDER
        except Exception:
            UART_SENDER = None  # type: ignore
        sender = globals().get("UART_SENDER") or locals().get("UART_SENDER")
        # Prefer imported global from app
        try:
            from .. import app as app_mod

            sender = app_mod.UART_SENDER
        except Exception:
            pass
        if not sender or not getattr(sender, "tx", None):
            print("Bind: UART sender not active")
            return
        try:
            sender.tx.start_bind(duration)
        except Exception as e:
            print(f"Bind trigger failed: {e}")

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
        model, mapping = self._model_selector.apply_selection(model_name)
        self._current_model = model
        self.selected_model = model.name
        self.model_mapping = {"name": model.name, "channels": mapping}
        if hasattr(self, "_toolbar") and self._toolbar:
            self._toolbar.title = f"pi-tx: {model_name}"
        self.dispatch("on_model_selected", model_name)

    # Legacy methods kept minimal or removed; selection logic moved to controller

    # Input processing now handled by InputEventPump (scheduled in build)

    def _poll_store_and_refresh(self, *_):
        snap = channel_store.snapshot()
        if self.channel_panel:
            self.channel_panel.update_values(snap)

    def _autoload_last_model(self):
        try:
            name = self._model_manager.autoload_last()
            if name:
                Clock.schedule_once(lambda *_: self.select_model(name), 0)
        except Exception as e:
            print(f"Warning: failed to autoload last model: {e}")


def create_gui(input_controller: InputController):
    return PiTxApp(input_controller=input_controller)
