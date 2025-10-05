from __future__ import annotations

from kivymd.uix.navigationrail import MDNavigationRail, MDNavigationRailItem
from kivymd.uix.boxlayout import MDBoxLayout

from ..pages.live.live_page import LivePage
from ..pages.model.model_page import ModelPage
from ..pages.system.system_page import SystemPage


class MainNavigationRail(MDBoxLayout):
    """Primary navigation rail for the app.

    Navigation Items:
      - Channels
      - Model Settings
      - System Settings
    Exposes attributes for parent hookup.
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        # Create views first
        self.channels_view = LivePage()
        self.model_settings_view = ModelPage()
        self.system_settings_view = SystemPage()

        # Store views for easy access
        self._views = {
            "channels": self.channels_view,
            "model": self.model_settings_view,
            "system": self.system_settings_view,
        }

        # Create the navigation rail
        self._nav_rail = MDNavigationRail(
            selected_color_background=self.theme_cls.primary_color,
            ripple_color_item=self.theme_cls.primary_color,
            width="62dp",
        )

        # Create navigation items with proper callback binding
        self.channels_item = MDNavigationRailItem(
            text="Live",
            icon="view-list",
        )
        self.channels_item.bind(on_release=lambda x: self._switch_view("channels"))

        self.model_item = MDNavigationRailItem(
            text="Model",
            icon="tune",
        )
        self.model_item.bind(on_release=lambda x: self._switch_view("model"))

        self.system_item = MDNavigationRailItem(
            text="System",
            icon="cog",
        )
        self.system_item.bind(on_release=lambda x: self._switch_view("system"))

        # Add items to navigation rail
        self._nav_rail.add_widget(self.channels_item)
        self._nav_rail.add_widget(self.model_item)
        self._nav_rail.add_widget(self.system_item)

        # Create content area for views
        self._content_area = MDBoxLayout(orientation="vertical", size_hint=(1, 1))

        # Set initial view
        self._current_view = "channels"
        self._content_area.add_widget(self.channels_view)

        # Add components to layout
        self.add_widget(self._nav_rail)
        self.add_widget(self._content_area)

        # Expose channel panel for compatibility
        self.channel_panel = self.channels_view.channel_panel

    def _switch_view(self, view_name):
        """Switch to the specified view."""
        if view_name in self._views and view_name != self._current_view:
            # Remove current view
            self._content_area.clear_widgets()

            # Add new view
            self._content_area.add_widget(self._views[view_name])
            self._current_view = view_name

    def switch_to_tab(self, tab_name):
        """Programmatically switch to a specific tab."""
        if tab_name in self._views:
            self._switch_view(tab_name)
