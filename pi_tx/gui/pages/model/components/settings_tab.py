from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.tab import MDTabsBase
from kivy.metrics import dp
from kivy.clock import Clock
import threading
from datetime import datetime
from .....logging_config import get_logger


class SettingsTab(MDBoxLayout, MDTabsBase):
    """Tab for model settings and bind functionality."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "Settings"
        self.icon = "cog"
        self._log = get_logger(__name__)

        self._current_model = None
        self._model_manager = None

        # Bind button for model pairing
        self._bind_button = MDRaisedButton(
            text="Bind Model",
            icon="link-variant",
            theme_icon_color="Custom",
            icon_color="white",
            md_bg_color=(0.2, 0.6, 1.0, 1.0),  # Nice blue color
            size_hint_y=None,
            height=dp(48),
            on_release=self._on_bind_pressed,
        )
        self.add_widget(self._bind_button)

        # Status label
        self._status_label = MDLabel(
            text="Ready to bind",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(40),
        )
        self.add_widget(self._status_label)

        # Placeholder content for future settings
        placeholder_label = MDLabel(
            text="Additional model settings coming soon",
            halign="center",
            valign="center",
        )
        self.add_widget(placeholder_label)

    def set_model(self, model, model_manager):
        """Set the current model and model manager reference."""
        self._current_model = model
        self._model_manager = model_manager
        self._update_bind_button_text()

    def _update_bind_button_text(self, dt=None):
        """Update button text based on current model's bind status."""
        if not self._current_model:
            return

        model = self._current_model
        if hasattr(model, "bind_timestamp") and model.bind_timestamp:
            self._bind_button.text = "Rebind Model"
            self._bind_button.icon = "link-variant-plus"
            self._status_label.text = (
                f"Last bound: {self._format_bind_time(model.bind_timestamp)}"
            )
        else:
            self._bind_button.text = "Bind Model"
            self._bind_button.icon = "link-variant"
            self._status_label.text = "Ready to bind"

    def _format_bind_time(self, timestamp: str) -> str:
        """Format bind timestamp for display."""
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp)
                return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass
        return "Unknown"

    def _on_bind_pressed(self, button_instance):
        """Handle bind button press."""
        # Disable button during binding
        self._bind_button.disabled = True
        self._bind_button.text = "Binding..."

        # Start bind process in background thread
        bind_thread = threading.Thread(target=self._bind_worker)
        bind_thread.daemon = True
        bind_thread.start()

    def _bind_worker(self):
        """Background worker to handle the bind process."""
        try:
            # Get the UART transmitter from the app
            from ..... import app as app_mod

            uart_sender = getattr(app_mod, "UART_SENDER", None)

            if uart_sender and hasattr(uart_sender, "bind_for_seconds"):
                # Perform binding for 2 seconds
                uart_sender.bind_for_seconds(2.0)
                success = True
                message = "Binding complete!"
            else:
                success = False
                message = "UART transmitter not available"

        except Exception as e:
            success = False
            message = f"Binding failed: {str(e)}"

        # Schedule UI update on main thread
        Clock.schedule_once(lambda dt: self._bind_complete(success, message))

    def _bind_complete(self, success, message):
        """Complete the bind process and update UI."""
        self._bind_button.disabled = False

        if success:
            # Save bind timestamp to model file
            self._save_bind_timestamp()
            # Update button text to show "Rebind"
            self._update_bind_button_text()
            self._status_label.text = message
            self._status_label.theme_text_color = "Custom"
            self._status_label.text_color = (0.2, 0.8, 0.2, 1.0)  # Green
            # Reset to default after 3 seconds
            Clock.schedule_once(lambda dt: self._reset_status(), 3.0)
        else:
            self._bind_button.text = (
                "Bind Model" if not self._is_model_bound() else "Rebind Model"
            )
            self._status_label.text = message
            self._status_label.theme_text_color = "Error"
            # Reset to default after 5 seconds
            Clock.schedule_once(lambda dt: self._reset_status(), 5.0)

    def _save_bind_timestamp(self):
        """Save the current timestamp as bind time to the model file."""
        if not self._current_model or not self._model_manager:
            return

        try:
            # Update the model object
            model = self._current_model
            model.bind_timestamp = datetime.now().isoformat()

            # Save to file using ModelRepository
            repo = self._model_manager._repo
            repo.save_model(model)

            self._log.info("Saved bind timestamp for model %s", model.name)
        except Exception as e:
            self._log.error("Error saving bind timestamp: %s", e)

    def _is_model_bound(self) -> bool:
        """Check if current model has been bound."""
        if not self._current_model:
            return False
        return bool(getattr(self._current_model, "bind_timestamp", None))

    def _reset_status(self):
        """Reset status label to default."""
        if self._is_model_bound():
            model = self._current_model
            self._status_label.text = (
                f"Last bound: {self._format_bind_time(model.bind_timestamp)}"
            )
        else:
            self._status_label.text = "Ready to bind"
        self._status_label.theme_text_color = "Secondary"

