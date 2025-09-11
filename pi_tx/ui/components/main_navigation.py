from __future__ import annotations

from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem

from ..views.channels import ChannelsView
from ..views.model_settings import ModelSettingsView
from ..views.system_settings import SystemSettingsView


class MainNavigation(MDBottomNavigation):
    """Primary bottom navigation for the app.

    Tabs:
      - Channels
      - Model Settings
      - System Settings
    Exposes attributes for parent hookup.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Channels tab
        channels_tab = MDBottomNavigationItem(
            name="channels", text="Channels", icon="view-list"
        )
        self.channels_view = ChannelsView()
        self.channel_panel = self.channels_view.channel_panel
        channels_tab.add_widget(self.channels_view)
        self.add_widget(channels_tab)

        # Model settings tab
        model_tab = MDBottomNavigationItem(name="model", text="Model", icon="tune")
        self.model_settings_view = ModelSettingsView()
        model_tab.add_widget(self.model_settings_view)
        self.add_widget(model_tab)

        # System settings tab
        system_tab = MDBottomNavigationItem(name="system", text="System", icon="cog")
        self.system_settings_view = SystemSettingsView()
        system_tab.add_widget(self.system_settings_view)
        self.add_widget(system_tab)

        self._tabs = [channels_tab, model_tab, system_tab]

    # (No custom active-tab styling)
