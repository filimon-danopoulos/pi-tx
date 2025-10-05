"""
Main UI application for pi-tx.

Uses navigation rail with live channel display and placeholder pages for model/system settings.
"""

import sys
import asyncio
import threading
import importlib.util
from pathlib import Path

from kivy.config import Config

Config.set("graphics", "width", "800")
Config.set("graphics", "height", "480")
Config.set("graphics", "resizable", "0")

from kivymd.app import MDApp
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager
from kivy.clock import Clock
from kivy.core.window import Window

from ..logging import init_logging, get_logger
from ..settings import MODELS_DIR, LAST_MODEL_FILE
from .components.navigation_rail import MainNavigationRail

log = get_logger(__name__)


class PiTxApp(MDApp):
    """Main Kivy MD application with navigation rail."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.channel_panel = None
        self._last_snapshot = None
        self.current_model = None
        self._listen_thread = None
        self._event_loop = None
        self._models_dir = MODELS_DIR
        
        # Add models directory to path
        sys.path.insert(0, str(self._models_dir))

    def build(self):
        """Build the application UI."""
        # Set theme
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"

        # Set window properties
        Window.clearcolor = (0.12, 0.12, 0.12, 1)

        # Create screen manager and screen
        screen_manager = ScreenManager()
        screen = MDScreen()
        root = MDFloatLayout()

        try:
            # Create navigation rail with all pages and pass model change callback
            nav = MainNavigationRail(on_model_changed=self._on_model_changed)
            self.channels_view = nav.channels_view
            self.channel_panel = nav.channel_panel
            self.model_settings_view = nav.model_settings_view
            self.system_settings_view = nav.system_settings_view

            nav.size_hint = (1, 1)
            root.add_widget(nav)
            self._navigation_rail = nav
        except Exception as e:
            log.error("Navigation init failed: %s", e)
            self._navigation_rail = None

        # Load the last selected model or default to cat_d6t
        self._load_initial_model()

        # Schedule polling of model values at 20Hz
        Clock.schedule_interval(self._poll_store_and_refresh, 1.0 / 20.0)

        screen.add_widget(root)
        screen_manager.add_widget(screen)
        return screen_manager

    def _load_initial_model(self):
        """Load the initial model (last selected or default)."""
        try:
            if LAST_MODEL_FILE.exists():
                model_name = LAST_MODEL_FILE.read_text().strip()
                log.info(f"Loading last selected model: {model_name}")
            else:
                model_name = "cat_d6t"
                log.info(f"No last model found, defaulting to: {model_name}")
            
            model_path = self._models_dir / f"{model_name}.py"
            if model_path.exists():
                self._load_model(model_name, model_path)
            else:
                log.error(f"Model file not found: {model_path}, trying cat_d6t")
                self._load_model("cat_d6t", self._models_dir / "cat_d6t.py")
        except Exception as e:
            log.error(f"Failed to load initial model: {e}", exc_info=True)

    def _on_model_changed(self, model_name: str, model_path: Path):
        """Handle model change from the UI."""
        log.info(f"Model change requested: {model_name}")
        self._load_model(model_name, model_path)

    def _load_model(self, model_name: str, model_path: Path):
        """Load a model from a file."""
        try:
            # Disconnect the current model if running
            if self.current_model:
                old_model_name = self.current_model.name if hasattr(self.current_model, 'name') else 'unknown'
                log.info(f"Disconnecting current model: {old_model_name}")
                self._stop_model_listening()
                
            # Load the model module
            spec = importlib.util.spec_from_file_location(model_name, model_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load model from {model_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get the model instance (convention: model variable has same name as file)
            if hasattr(module, model_name):
                model = getattr(module, model_name)
            else:
                # Try to find any Model instance in the module
                from ..domain import Model
                model = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, Model):
                        model = attr
                        break
                if model is None:
                    raise AttributeError(f"No Model instance found in {model_name}")
            
            self.current_model = model
            log.info(f"Loaded model: {model.name}")
            
            # Initialize the channel panel with the new model
            self._initialize_model_channels()
            
            # Start the model's listener
            self._start_model_listening()
            
        except Exception as e:
            log.error(f"Failed to load model {model_name}: {e}", exc_info=True)

    def _initialize_model_channels(self):
        """Initialize the channel panel with the current model."""
        if not self.current_model:
            log.error("No current model to initialize")
            return
            
        try:
            # Build channel mapping from the current model
            mapping = {}
            for i, channel in enumerate(self.current_model.channels, start=1):
                mapping[str(i)] = {
                    "name": channel.name,
                    "control_type": "bipolar",  # Default to bipolar
                    "device_path": None,  # Virtual channels
                    "control_code": None,
                }

            if self.channel_panel:
                self.channel_panel.rebuild(mapping)
                log.info(f"Initialized channel panel with {len(mapping)} channels")
        except Exception as e:
            log.error(f"Failed to initialize model channels: {e}", exc_info=True)

    def _stop_model_listening(self):
        """Stop the current model's connection gracefully."""
        if not self.current_model:
            return
            
        if self._event_loop and self._listen_thread and self._listen_thread.is_alive():
            try:
                # Schedule disconnect in the model's event loop
                future = asyncio.run_coroutine_threadsafe(
                    self.current_model.disconnect(),
                    self._event_loop
                )
                # Wait for disconnect to complete (with timeout)
                future.result(timeout=2.0)
                log.info(f"Model '{self.current_model.name}' disconnected successfully")
            except Exception as e:
                log.error(f"Error during model disconnect: {e}", exc_info=True)
                # Force stop the event loop if disconnect failed
                try:
                    self._event_loop.call_soon_threadsafe(self._event_loop.stop)
                except Exception:
                    pass

    def _start_model_listening(self):
        """Start the model's connection in a background thread."""
        if not self.current_model:
            log.error("No current model to start listening")
            return

        def run_connect():
            # Create a new event loop for this thread
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            try:
                # Connect to the model (starts monitoring in background)
                self._event_loop.run_until_complete(self.current_model.connect())
                # Keep the event loop running
                self._event_loop.run_forever()
            except Exception as e:
                log.error(f"Connection thread error: {e}", exc_info=True)
            finally:
                self._event_loop.close()
                self._event_loop = None

        self._listen_thread = threading.Thread(target=run_connect, daemon=True)
        self._listen_thread.start()
        log.info("Started model connection in background thread")

    def _poll_store_and_refresh(self, dt):
        """Poll the model and update UI if values changed."""
        if not self.current_model:
            return
            
        try:
            # Get processed values from the model (includes mixes and post-processing)
            values = self.current_model.readValues()

            # Convert to list for channel_panel (which expects a list)
            snap = [values.get(ch.name, 0.0) for ch in self.current_model.channels]

            # Only update UI if snapshot actually changed
            if snap != self._last_snapshot:
                self._last_snapshot = snap[:]  # Store a copy
                if self.channel_panel:
                    self.channel_panel.update_values(snap)
        except Exception as e:
            log.error(f"Poll/refresh error: {e}")

    def on_stop(self):
        """Clean up when application stops."""
        log.info("Application stopping, disconnecting model...")
        if self.current_model:
            self._stop_model_listening()
        return True


def create_app():
    """Create and return the UI application without running it."""
    init_logging(level="INFO")
    app = PiTxApp()
    return app


def main():
    """Run the UI application."""
    app = create_app()
    app.run()


if __name__ == "__main__":
    main()
