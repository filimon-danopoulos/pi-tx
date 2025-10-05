"""
Main UI application for pi-tx.

Uses navigation rail with live channel display and placeholder pages for model/system settings.
Integrates with the channel_store from the old application.
"""

import sys
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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pi_tx.logging_config import init_logging, get_logger
from pi_tx.domain.channel_store import channel_store
from pi_tx.input.controls import InputController
from ui.components.navigation_rail import MainNavigationRail

# Import the cat_d6t model for initialization
from models.cat_d6t import cat_d6t

log = get_logger(__name__)


class PiTxApp(MDApp):
    """Main Kivy MD application with navigation rail."""

    def __init__(self, input_controller: InputController, **kwargs):
        super().__init__(**kwargs)
        self.input_controller = input_controller
        self.channel_panel = None
        self._last_snapshot = None

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
            # Create navigation rail with all pages
            nav = MainNavigationRail()
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

        # Initialize the channel panel with the cat_d6t model
        self._initialize_model()

        # Schedule polling of model values at 20Hz
        Clock.schedule_interval(self._poll_store_and_refresh, 1.0 / 20.0)

        screen.add_widget(root)
        screen_manager.add_widget(screen)
        return screen_manager

    def _initialize_model(self):
        """Initialize the channel panel with the cat_d6t model."""
        try:
            # Build channel mapping from the cat_d6t model
            mapping = {}
            for i, channel in enumerate(cat_d6t.channels, start=1):
                mapping[str(i)] = {
                    "name": channel.name,
                    "control_type": "bipolar",  # Default to bipolar for cat_d6t
                    "device_path": None,  # Virtual channels
                    "control_code": None,
                }

            if self.channel_panel:
                self.channel_panel.rebuild(mapping)
                log.info(f"Initialized channel panel with {len(mapping)} channels")

            # Start the model's listen() method in a background thread
            self._start_model_listening()
        except Exception as e:
            log.error(f"Failed to initialize model: {e}")

    def _start_model_listening(self):
        """Start the model.listen() method in a background thread."""
        import asyncio
        import threading

        def run_listen():
            # Create a new event loop for this thread
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)

            # Run listen indefinitely
            try:
                event_loop.run_until_complete(cat_d6t.listen())
            except Exception as e:
                log.error(f"Listen thread error: {e}")
            finally:
                event_loop.close()

        listen_thread = threading.Thread(target=run_listen, daemon=True)
        listen_thread.start()
        log.info("Started model.listen() in background thread")

    def _poll_store_and_refresh(self, dt):
        """Poll the model and update UI if values changed."""
        try:
            # Get processed values from the model (includes mixes and post-processing)
            values = cat_d6t.readValues()

            # Convert to list for channel_panel (which expects a list)
            snap = [values.get(ch.name, 0.0) for ch in cat_d6t.channels]

            # Only update UI if snapshot actually changed
            if snap != self._last_snapshot:
                self._last_snapshot = snap[:]  # Store a copy
                if self.channel_panel:
                    self.channel_panel.update_values(snap)
        except Exception as e:
            log.error(f"Poll/refresh error: {e}")

    def on_stop(self):
        """Clean up when application stops."""
        return True


def main():
    """Run the UI application."""
    # Initialize logging
    init_logging(level="INFO")

    # Create input controller (debug mode, no real gamepad required)
    controller = InputController(debug=False)

    # Run the Kivy app
    app = PiTxApp(input_controller=controller)
    app.run()


if __name__ == "__main__":
    main()
