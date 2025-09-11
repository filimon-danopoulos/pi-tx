from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.scrollview import MDScrollView


class LeftDrawer(MDNavigationDrawer):
    """Simple left navigation drawer hosting settings & model actions."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        # Set drawer width and anchor
        self.width = "240dp"  # Set explicit width
        self.anchor = "left"  # Ensure it's left-anchored
        container = MDBoxLayout(orientation="vertical", padding=8, spacing=8)
        self._list = MDList()
        scroll = MDScrollView()
        scroll.add_widget(self._list)
        container.add_widget(scroll)
        self.add_widget(container)

        # Listen for model selection changes to refresh the display
        if hasattr(app, "bind"):
            app.bind(on_model_selected=self._on_model_changed)

        self.refresh()

    def refresh(self):
        self._list.clear_widgets()

        # Model section header (simple as item)
        if not self.app.available_models:
            self.app.refresh_models()

        # Get currently selected model for highlighting
        current_model = getattr(self.app, "selected_model", "")

        for name in self.app.available_models:
            # Use a proper closure to capture the current name value
            def create_selection_handler(model_name):
                def handler(*args):
                    self.app.select_model(model_name)
                    self.set_state("close")

                return handler

            # Create list item with visual indication of current selection
            item_text = f"{name}" if name == current_model else f"  {name}"
            item = OneLineListItem(
                text=item_text, on_release=create_selection_handler(name)
            )

            # Highlight currently selected model
            if name == current_model:
                item.theme_text_color = "Custom"
                item.text_color = item.theme_cls.primary_color

            self._list.add_widget(item)

    def _open_system(self):
        # Switch bottom nav to system tab if available
        if hasattr(self.app, "_bottom_nav") and self.app._bottom_nav:
            try:
                self.app._bottom_nav.switch_tab("system")
            except Exception:
                pass
        self.set_state("close")

    def _on_model_changed(self, app, model_name):
        """Called when a model is selected to refresh the drawer display."""
        # Only refresh if we're not currently closing/opening
        if hasattr(self, "state") and self.state in ("close", "open"):
            self.refresh()
