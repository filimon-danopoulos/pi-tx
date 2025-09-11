from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDSeparator
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton


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

        # Add dividing line
        separator = MDSeparator()
        self._list.add_widget(separator)

        # Add create model button
        create_button = OneLineListItem(
            text="+ Create New Model", on_release=self._show_simple_dialog
        )
        create_button.theme_text_color = "Custom"
        create_button.text_color = create_button.theme_cls.primary_color
        self._list.add_widget(create_button)

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

    def _show_simple_dialog(self, *args):
        """Show a simple test dialog that can be closed."""
        # Debug: Check if dialog is already open to prevent double-calling
        if (
            hasattr(self, "test_dialog")
            and self.test_dialog
            and self.test_dialog.parent
        ):
            # Dialog is already open, ignore this call
            return

        # Create a simple dialog with one close button
        # Based on KivyMD source code analysis, the key is to store dialog reference
        # and use simple method reference (not lambda) for button callback
        self.test_dialog = MDDialog(
            title="Create New Model",
            text="This is a test dialog. Click the button to close it.",
            buttons=[
                MDFlatButton(
                    text="Close",
                    on_release=self._close_simple_dialog,
                ),
            ],
        )
        self.test_dialog.open()

    def _close_simple_dialog(self, button_instance):
        """Close the simple dialog."""
        # Simple, direct dismissal - exactly as shown in KivyMD examples
        if hasattr(self, "test_dialog") and self.test_dialog:
            self.test_dialog.dismiss()
            self.test_dialog = None
