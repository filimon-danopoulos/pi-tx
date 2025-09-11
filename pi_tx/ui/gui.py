from __future__ import annotations
from typing import Dict
from kivy.clock import Clock
from kivy.properties import StringProperty, DictProperty
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationdrawer import MDNavigationLayout
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager

from ..domain.channel_store import channel_store
from ..input.controls import InputController
from .services.model_manager import ModelManager, Model
from .services.model_selection import ModelSelectionController
from .services.input_event_pump import InputEventPump
from .components.channel_panel import ChannelPanel
from .components.main_navigation import MainNavigation
from .components.top_bar import TopBar
from .components.left_drawer import LeftDrawer


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
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        nav_layout = MDNavigationLayout()
        screen_manager = ScreenManager()
        screen = MDScreen()
        content_root = MDBoxLayout(orientation="vertical")

        toolbar = TopBar(
            title="pi-tx",
            left_callback=self.toggle_left_drawer,
        )
        content_root.add_widget(toolbar)
        self._toolbar = toolbar

        self._left_drawer = LeftDrawer(self)

        try:  # pragma: no cover
            nav = MainNavigation()
            self.channels_view = nav.channels_view
            self.channel_panel = nav.channel_panel
            self.model_settings_view = nav.model_settings_view
            self.system_settings_view = nav.system_settings_view
            self._model_selector.set_channel_panel(self.channel_panel)
            content_root.add_widget(nav)
            self._bottom_nav = nav
        except Exception as e:  # pragma: no cover
            print(f"Navigation init failed: {e}")
            self._bottom_nav = None

        Clock.schedule_once(lambda *_: self.refresh_models(), 0)
        Clock.schedule_interval(self._input_pump.tick, 1.0 / 100.0)
        Clock.schedule_interval(self._poll_store_and_refresh, 1.0 / 30.0)
        screen.add_widget(content_root)
        screen_manager.add_widget(screen)
        # Store reference to nav_layout for drawer control
        self._nav_layout = nav_layout
        nav_layout.add_widget(screen_manager)
        nav_layout.add_widget(self._left_drawer)
        return nav_layout

    def refresh_models(self):
        self.available_models = self._model_manager.list_models()
        if not self.selected_model:
            self._autoload_last_model()
        # Update drawer list
        try:
            if self._left_drawer:
                self._left_drawer.refresh()
        except Exception:
            pass

    def toggle_left_drawer(self):
        drawer = getattr(self, "_left_drawer", None)
        if not drawer:
            return

        try:
            state = getattr(drawer, "state", "close")

            if state == "close":
                # Force drawer to open by setting properties
                drawer.state = "open"
                drawer.set_state("open")
                drawer.refresh()  # Refresh when opening
            else:
                drawer.state = "close"
                drawer.set_state("close")

        except Exception as e:
            print(f"Drawer toggle failed: {e}")

    def _poll_store_and_refresh(self, *_):
        snap = channel_store.snapshot()
        if hasattr(self, "channels_view") and self.channel_panel:
            self.channel_panel.update_values(snap)

    def _autoload_last_model(self):
        try:
            name = self._model_manager.autoload_last()
            if name:
                Clock.schedule_once(lambda *_: self.select_model(name), 0)
        except Exception as e:
            print(f"Warning: failed to autoload last model: {e}")

    def select_model(self, model_name: str):
        model, mapping = self._model_selector.apply_selection(model_name)
        self._current_model = model
        self.selected_model = model.name
        self.model_mapping = {"name": model.name, "channels": mapping}
        if hasattr(self, "_toolbar") and self._toolbar:
            self._toolbar.title = f"{model_name}"
        if hasattr(self, "model_settings_view") and self.model_settings_view:
            self.model_settings_view.set_model(model_name)
        self.dispatch("on_model_selected", model_name)


def create_gui(input_controller: InputController):
    return PiTxApp(input_controller=input_controller)
