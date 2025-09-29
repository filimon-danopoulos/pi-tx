from __future__ import annotations
from typing import Dict
from kivy.clock import Clock
from kivy.properties import StringProperty, DictProperty
from kivymd.app import MDApp
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager
from kivy.properties import StringProperty
from ..logging_config import get_logger

log = get_logger(__name__)

from ..domain.channel_store import channel_store
from ..input.controls import InputController
from .services.model_manager import ModelManager, Model
from .services.model_selection import ModelSelectionController
from .services.input_event_pump import InputEventPump
from .pages.live.components.channel_panel import ChannelPanel
from .components.navigation_rail import MainNavigationRail


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
        self._selecting_model = False  # Flag to prevent recursion
        # Cache last snapshot to avoid redundant UI updates
        self._last_snapshot = None
        self.register_event_type("on_model_selected")

    def on_model_selected(self, model_name: str):
        pass

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        screen_manager = ScreenManager()
        screen = MDScreen()
        root = MDFloatLayout()
        try:  # pragma: no cover
            nav = MainNavigationRail()
            self.channels_view = nav.channels_view
            self.channel_panel = nav.channel_panel
            self.model_settings_view = nav.model_settings_view
            self.system_settings_view = nav.system_settings_view
            self.system_settings_view.set_app(self)
            self._model_selector.set_channel_panel(self.channel_panel)
            nav.size_hint = (1, 1)
            root.add_widget(nav)
            self._actions_menu = None
            self._navigation_rail = nav
        except Exception as e:  # pragma: no cover
            log.error("Navigation init failed: %s", e)
            self._navigation_rail = None
        Clock.schedule_once(lambda *_: self.refresh_models(), 0)
        Clock.schedule_interval(self._input_pump.tick, 1.0 / 100.0)
        Clock.schedule_interval(self._poll_store_and_refresh, 1.0 / 20.0)
        screen.add_widget(root)
        screen_manager.add_widget(screen)
        return screen_manager

    # (Global FAB logic removed)

    def refresh_models(self):
        self.available_models = self._model_manager.list_models()
        if not self.selected_model and not self._selecting_model:
            self._autoload_last_model()
        try:
            if hasattr(self, "system_settings_view") and self.system_settings_view:
                self.system_settings_view.refresh_models()
        except Exception:
            pass

    def _poll_store_and_refresh(self, *_):
        snap = channel_store.snapshot()

        # Only update UI if snapshot actually changed
        if snap != self._last_snapshot:
            self._last_snapshot = snap[:]  # Store a copy
            if hasattr(self, "channels_view") and self.channel_panel:
                self.channel_panel.update_values(snap)

    def _autoload_last_model(self):
        try:
            name = self._model_manager.autoload_last()
            if name:
                Clock.schedule_once(lambda *_: self.select_model(name), 0)
        except Exception as e:
            log.warning("Failed to autoload last model: %s", e)

    def select_model(self, model_name: str):
        if self._selecting_model:
            return  # Prevent recursion

        self._selecting_model = True
        try:
            if not model_name:
                # Handle empty model name (clear selection)
                self._current_model = None
                self.selected_model = ""
                self.model_mapping = {}
                if hasattr(self, "model_settings_view") and self.model_settings_view:
                    self.model_settings_view.title_label.text = "No Model Selected"
                self.dispatch("on_model_selected", "")
                return

            model, mapping = self._model_selector.apply_selection(model_name)
            self._current_model = model
            self.selected_model = model.name
            self.model_mapping = {"name": model.name, "channels": mapping}
            if hasattr(self, "model_settings_view") and self.model_settings_view:
                self.model_settings_view.set_model(model_name)
            self.dispatch("on_model_selected", model_name)
        finally:
            self._selecting_model = False


def create_gui(input_controller: InputController):
    return PiTxApp(input_controller=input_controller)


## Removed ActionMenuItem (unused after FAB removal)
