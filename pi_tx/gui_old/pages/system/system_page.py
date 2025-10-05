from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabs

from .components.models_tab import ModelsTab
from .components.value_store_tab import ValueStoreTab
from .components.general_tab import GeneralTab


class SystemPage(MDBoxLayout):
    """System-wide settings with tabbed interface.

    Features:
      - Model management in Models tab
      - System values display in Value Store tab
      - General system settings in General tab
    """

    def __init__(self, app=None, **kwargs):
        super().__init__(orientation="vertical", padding=0, spacing=0, **kwargs)
        self.app = app
        self.size_hint = (1, 1)

        # Create tabs with explicit sizing
        self._tabs = MDTabs(size_hint=(1, 1))

        # Create tab instances
        self._models_tab = ModelsTab(app=app)
        self._value_store_tab = ValueStoreTab()
        self._general_tab = GeneralTab()

        # Add tabs to the tab widget
        self._tabs.add_widget(self._models_tab)
        self._tabs.add_widget(self._value_store_tab)
        self._tabs.add_widget(self._general_tab)

        # Container layout (keep existing vertical orientation)
        self.add_widget(self._tabs)

    def set_app(self, app):
        """Set the app reference after initialization."""
        self.app = app
        self._models_tab.set_app(app)

    def refresh_models(self):
        """Refresh the model list display."""
        if self._models_tab:
            self._models_tab.refresh_models()
