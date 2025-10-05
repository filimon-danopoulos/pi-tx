from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabs
from kivymd.uix.label import MDLabel

from ...services.model_manager import ModelManager
from ....domain.model_json import Model
from .components.channels_tab import ChannelsTab
from .components.settings_tab import SettingsTab
from .components.modifiers_tab import ModifiersTab
from .components.processors_tab import ProcessorsTab


class ModelPage(MDBoxLayout):
    """Model configuration page showing detailed model settings.

    Displays:
      - Basic model information (name, ID, RX number, etc.)
      - Channel configurations with device mappings
      - Processor configurations (reverse, differential, aggregate)

    Future enhancements:
      - Rename model
      - Edit channel config (reverse, trim, expo)
      - Persistence / duplication actions
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=0, spacing=0, **kwargs)

        # Create tabs container
        self._tabs = MDTabs()

        # Instantiate tabs
        self._channels_tab = ChannelsTab()
        self._modifiers_tab = ModifiersTab()
        self._processors_tab = ProcessorsTab()
        self._settings_tab = SettingsTab()

        # Register tabs
        for tab in (
            self._channels_tab,
            self._modifiers_tab,
            self._processors_tab,
            self._settings_tab,
        ):
            self._tabs.add_widget(tab)

        # Add to layout
        self.add_widget(self._tabs)

        # Model manager and current model state
        self._model_manager = ModelManager()
        self._current_model: Model | None = None
        self._current_model_name = "No Model Selected"

    def set_model(self, name: str):
        """Load and display the full model configuration."""
        try:
            # Try to get cached model first, fall back to loading from file
            self._current_model = self._model_manager.get_cached_model(name)
            if self._current_model is None:
                self._current_model = self._model_manager._repo.load_model(name)

            self._current_model_name = f"Model: {name}"

            # Pass model to tabs
            self._channels_tab.set_model(self._current_model, self._model_manager)
            self._modifiers_tab.set_model(self._current_model, self._model_manager)
            self._processors_tab.set_model(self._current_model, self._model_manager)
            self._settings_tab.set_model(self._current_model, self._model_manager)

            self._refresh_content()
        except Exception as e:
            self._current_model_name = "Error Loading Model"
            self._show_error(f"Error loading model: {str(e)}")

    def _refresh_content(self):
        """Rebuild the content with channel data table."""
        if not self._current_model:
            return

        # Refresh the channel data table
        self._channels_tab.refresh_table()
        if hasattr(self, "_modifiers_tab"):
            self._modifiers_tab.refresh_table()
        if hasattr(self, "_processors_tab"):
            self._processors_tab.refresh_table()

    def _show_error(self, error_msg: str):
        """Show an error message."""
        # Clear all widgets in the channels tab
        self._channels_tab.clear_widgets()

        error_label = MDLabel(text=error_msg, theme_text_color="Error", halign="center")
        self._channels_tab.add_widget(error_label)
