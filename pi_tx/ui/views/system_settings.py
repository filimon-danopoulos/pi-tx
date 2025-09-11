from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDSeparator, MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivy.metrics import dp
import uuid
import json
import os
from pathlib import Path


class ModelsTab(MDBoxLayout, MDTabsBase):
    """Tab for model selection and management."""
    
    def __init__(self, app=None, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "Models"
        self.icon = "folder-multiple"
        self.app = app
        
        # Button row
        button_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=8,
        )
        
        # Remove model button
        self.remove_button = MDRaisedButton(
            text="Remove Selected",
            icon="delete",
            theme_icon_color="Custom",
            icon_color="white",
            md_bg_color="red",
            on_release=self._show_remove_model_dialog,
            disabled=True,  # Initially disabled until a model is selected
        )
        
        # Create model button
        self.create_button = MDRaisedButton(
            text="Create New",
            icon="plus",
            theme_icon_color="Custom",
            icon_color="white",
            on_release=self._show_create_model_dialog,
        )
        
        button_layout.add_widget(self.remove_button)
        button_layout.add_widget(MDLabel())  # Spacer
        button_layout.add_widget(self.create_button)
        self.add_widget(button_layout)
        
        # Model list card
        model_card = MDCard(
            orientation="vertical",
            size_hint_y=1,
            padding=8,
            spacing=4,
            elevation=2,
        )
        
        self._model_list = MDList()
        scroll = MDScrollView()
        scroll.add_widget(self._model_list)
        model_card.add_widget(scroll)
        self.add_widget(model_card)

    def set_app(self, app):
        """Set the app reference after initialization."""
        self.app = app
        self.refresh_models()
        if hasattr(app, "bind"):
            app.bind(on_model_selected=self._on_model_changed)

    def refresh_models(self):
        """Refresh the model list display."""
        if not self.app:
            return
            
        self._model_list.clear_widgets()

        # Get available models
        if not self.app.available_models:
            self.app.refresh_models()

        # Get currently selected model for highlighting
        current_model = getattr(self.app, "selected_model", "")
        
        # Update remove button state based on selection
        self.remove_button.disabled = not current_model

        for name in self.app.available_models:
            # Use a proper closure to capture the current name value
            def create_selection_handler(model_name):
                def handler(*args):
                    self.app.select_model(model_name)
                return handler

            # Create list item with visual indication of current selection
            item = OneLineListItem(
                text=name, 
                on_release=create_selection_handler(name)
            )

            # Highlight currently selected model
            if name == current_model:
                item.theme_text_color = "Custom"
                item.text_color = item.theme_cls.primary_color

            self._model_list.add_widget(item)

    def _on_model_changed(self, app, model_name):
        """Called when a model is selected to refresh the display."""
        self.refresh_models()

    def _show_remove_model_dialog(self, *args):
        """Show confirmation dialog to remove the selected model."""
        if not self.app or not hasattr(self.app, 'selected_model') or not self.app.selected_model:
            return

        selected_model = self.app.selected_model

        # Create confirmation dialog
        self.remove_dialog = MDDialog(
            title="Remove Model",
            text=f"Are you sure you want to remove the model '{selected_model}'?\n\nThis action cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=self._close_remove_dialog,
                ),
                MDRaisedButton(
                    text="Remove",
                    theme_icon_color="Custom",
                    icon_color="white",
                    md_bg_color="red",
                    on_release=self._remove_selected_model,
                ),
            ],
        )
        self.remove_dialog.open()

    def _close_remove_dialog(self, button_instance):
        """Close the remove model dialog."""
        if hasattr(self, "remove_dialog") and self.remove_dialog:
            self.remove_dialog.dismiss()
            self.remove_dialog = None
        return True

    def _remove_selected_model(self, button_instance):
        """Remove the currently selected model."""
        if not self.app or not hasattr(self.app, 'selected_model') or not self.app.selected_model:
            self._close_remove_dialog(button_instance)
            return

        try:
            model_name = self.app.selected_model
            model_file = Path("models") / f"{model_name}.json"
            
            if model_file.exists():
                model_file.unlink()  # Delete the file
                
                # Clear current selection
                self.app.selected_model = ""
                self.app._current_model = None
                
                # Refresh model lists
                self.app.refresh_models()
                self.refresh_models()
                
                # Try to auto-load another model if available
                if self.app.available_models:
                    # Select the first available model
                    first_model = self.app.available_models[0]
                    self.app.select_model(first_model)
                
        except Exception as e:
            print(f"Error removing model: {e}")
        
        self._close_remove_dialog(button_instance)

    def _show_create_model_dialog(self, *args):
        """Show a dialog to create a new model with name input."""
        # Check if dialog is already open
        if hasattr(self, "create_dialog") and self.create_dialog and self.create_dialog.parent:
            return

        # Create text field for model name
        self.name_field = MDTextField(
            hint_text="Enter model name",
            helper_text="Only letters, numbers, and underscores allowed",
            helper_text_mode="on_focus",
            size_hint_y=None,
            height="56dp",
        )

        # Clear error when user starts typing
        self.name_field.bind(text=self._on_name_text_changed)

        # Create dialog
        self.create_dialog = MDDialog(
            title="Create New Model",
            type="custom",
            content_cls=self.name_field,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=self._close_create_dialog,
                ),
                MDRaisedButton(
                    text="Save",
                    on_release=self._save_new_model,
                ),
            ],
        )
        self.create_dialog.open()

    def _close_create_dialog(self, button_instance):
        """Close the create model dialog."""
        if hasattr(self, "create_dialog") and self.create_dialog:
            self.create_dialog.dismiss()
            self.create_dialog = None
        return True

    def _on_name_text_changed(self, instance, text):
        """Clear error state when user starts typing."""
        if hasattr(self, "name_field") and self.name_field:
            self.name_field.error = False
            self.name_field.helper_text = "Only letters, numbers, and underscores allowed"

    def _save_new_model(self, button_instance):
        """Save the new model with the entered name."""
        if not hasattr(self, "name_field") or not self.name_field:
            return

        model_name = self.name_field.text.strip()

        # Validate model name
        if not model_name:
            self.name_field.error = True
            self.name_field.helper_text = "Model name is required"
            return

        # Check if name contains only letters, numbers, and underscores
        if not all(c.isalnum() or c == "_" for c in model_name):
            self.name_field.error = True
            self.name_field.helper_text = "Only letters, numbers, and underscores allowed"
            return

        # Check if model already exists
        if model_name in self.app.available_models:
            self.name_field.error = True
            self.name_field.helper_text = "Model with this name already exists"
            return

        try:
            # Create model data
            model_data = {
                "name": model_name,
                "model_index": self._allocate_model_index(),
                "rx_num": self._allocate_rx_num(),
                "id": str(uuid.uuid4()),
                "channels": {},
            }

            # Save to file
            models_dir = Path("models")
            models_dir.mkdir(exist_ok=True)
            model_file = models_dir / f"{model_name}.json"

            with open(model_file, "w") as f:
                json.dump(model_data, f, indent=2)

            # Refresh the app's model list and UI
            self.app.refresh_models()
            self.refresh_models()

            # Close the dialog
            self._close_create_dialog(button_instance)

        except Exception as e:
            self.name_field.error = True
            self.name_field.helper_text = f"Error saving model: {str(e)}"

    def _allocate_rx_num(self):
        """Allocate an unused RX number (0-15)."""
        used = set()
        models_dir = Path("models")
        if models_dir.exists():
            for model_file in models_dir.glob("*.json"):
                try:
                    with open(model_file, "r") as f:
                        data = json.load(f)
                    if "rx_num" in data:
                        used.add(int(data["rx_num"]))
                except Exception:
                    continue

        for rx_num in range(16):  # 0-15
            if rx_num not in used:
                return rx_num
        return 0  # Fallback

    def _allocate_model_index(self):
        """Allocate a unique model index."""
        used = set()
        models_dir = Path("models")
        if models_dir.exists():
            for model_file in models_dir.glob("*.json"):
                try:
                    with open(model_file, "r") as f:
                        data = json.load(f)
                    if "model_index" in data:
                        used.add(int(data["model_index"]))
                except Exception:
                    continue

        idx = 1
        while idx in used:
            idx += 1
        return idx


class GeneralTab(MDBoxLayout, MDTabsBase):
    """Tab for general system settings."""
    
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=8, **kwargs)
        self.title = "General"
        self.icon = "cog"
        
        # Placeholder content for future system settings
        self.add_widget(
            MDLabel(
                text="General system settings coming soon...\n\n• Serial/UART configuration\n• Input device selection\n• Theme settings\n• Logging options",
                halign="left",
                valign="top",
            )
        )


class SystemSettingsView(MDBoxLayout):
    """System-wide settings with tabbed interface.

    Features:
      - Model management in Models tab
      - General system settings in General tab
    """

    def __init__(self, app=None, **kwargs):
        super().__init__(orientation="vertical", padding=0, spacing=0, **kwargs)
        self.app = app
        
        # Create tabs
        self._tabs = MDTabs()
        
        # Create tab instances
        self._models_tab = ModelsTab(app=app)
        self._general_tab = GeneralTab()
        
        # Add tabs to the tab widget
        self._tabs.add_widget(self._models_tab)
        self._tabs.add_widget(self._general_tab)
        
        # Add tabs to main container
        self.add_widget(self._tabs)

    def set_app(self, app):
        """Set the app reference after initialization."""
        self.app = app
        self._models_tab.set_app(app)

    def refresh_models(self):
        """Refresh the model list display."""
        if self._models_tab:
            self._models_tab.refresh_models()
