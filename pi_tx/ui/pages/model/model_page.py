"""Model selection page for switching between RC models."""

from __future__ import annotations
import sys
import importlib.util
from pathlib import Path
from typing import Optional

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import MDList, OneLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.label import MDLabel
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

# Add models directory to path
_models_dir = Path(__file__).parent.parent.parent.parent.parent / "models"
sys.path.insert(0, str(_models_dir))

from ....logging_config import get_logger

log = get_logger(__name__)


class ModelListItem(OneLineAvatarIconListItem):
    """List item for a model with icon."""

    def __init__(
        self, model_name: str, model_path: Path, icon: str, on_select_callback, **kwargs
    ):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.model_path = model_path
        self.on_select_callback = on_select_callback

        # Set up the list item
        self.text = model_name

        # Add icon on the left
        icon_widget = IconLeftWidget(icon=icon)
        self.add_widget(icon_widget)

        # Handle click
        self.on_release = self._on_item_click

    def _on_item_click(self):
        """Handle item click - switch to this model."""
        log.info(f"Model selected: {self.model_name}")
        if self.on_select_callback:
            self.on_select_callback(self.model_name, self.model_path)


class ModelPage(MDBoxLayout):
    """Model selection page for switching between different RC models."""

    def __init__(self, on_model_changed=None, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.on_model_changed = on_model_changed
        self.current_model = None

        # Ensure page fills available space
        self.size_hint = (1, 1)
        self.spacing = dp(10)
        self.padding = dp(20)

        # Add title
        title = MDLabel(
            text="Select Model",
            halign="left",
            font_style="H5",
            size_hint_y=None,
            height=dp(24),
        )
        self.add_widget(title)

        # Create the model list
        self.model_list = MDList()

        # Populate the list with available models
        self._load_models()

        # Put it in a scroll view
        scroll = ScrollView()
        scroll.add_widget(self.model_list)
        self.add_widget(scroll)

        # Load the last selected model
        self._load_last_model()

    def _load_models(self):
        """Load all available models from the models directory."""
        models_dir = Path(__file__).parent.parent.parent.parent.parent / "models"

        if not models_dir.exists():
            log.error(f"Models directory not found: {models_dir}")
            return

        # Find all Python files in models directory (excluding __pycache__)
        model_files = sorted(
            [f for f in models_dir.glob("*.py") if not f.name.startswith("_")]
        )

        log.info(f"Found {len(model_files)} model files in {models_dir}")

        for model_file in model_files:
            model_name = model_file.stem

            # Load the model to get its icon
            icon = self._get_model_icon(model_name, model_file)

            item = ModelListItem(
                model_name=model_name,
                model_path=model_file,
                icon=icon,
                on_select_callback=self._on_model_selected,
            )
            self.model_list.add_widget(item)

    def _get_model_icon(self, model_name: str, model_path: Path) -> str:
        """Load a model file and extract its icon."""
        try:
            # Load the model module
            spec = importlib.util.spec_from_file_location(model_name, model_path)
            if spec is None or spec.loader is None:
                log.warning(f"Cannot load model from {model_path}")
                return "excavator"  # Default icon

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the model instance (convention: model variable has same name as file)
            if hasattr(module, model_name):
                model = getattr(module, model_name)
                if hasattr(model, "icon"):
                    # Icon can be either a ModelIcon enum or a string
                    icon = model.icon
                    return icon.value if hasattr(icon, 'value') else str(icon)
            else:
                # Try to find any Model instance in the module
                from ....domain.models import Model

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, Model):
                        if hasattr(attr, "icon"):
                            # Icon can be either a ModelIcon enum or a string
                            icon = attr.icon
                            return icon.value if hasattr(icon, 'value') else str(icon)
                        break

            # Default if no icon found
            return "excavator"
        except Exception as e:
            log.warning(f"Failed to load icon for {model_name}: {e}")
            return "excavator"  # Default icon

    def _on_model_selected(self, model_name: str, model_path: Path):
        """Handle model selection."""
        try:
            self.current_model = model_name

            # Update the visual highlight
            self._update_highlight(model_name)

            # Save the selection
            self._save_last_model(model_name)

            # Notify the app about the change
            if self.on_model_changed:
                self.on_model_changed(model_name, model_path)

            log.info(f"Switched to model: {model_name}")
        except Exception as e:
            log.error(f"Failed to switch model: {e}", exc_info=True)

    def _save_last_model(self, model_name: str):
        """Save the last selected model to a file."""
        try:
            last_model_file = (
                Path(__file__).parent.parent.parent.parent.parent / ".last_model"
            )
            last_model_file.write_text(model_name)
            log.info(f"Saved last model: {model_name}")
        except Exception as e:
            log.error(f"Failed to save last model: {e}")

    def _load_last_model(self):
        """Load and highlight the last selected model."""
        try:
            last_model_file = (
                Path(__file__).parent.parent.parent.parent.parent / ".last_model"
            )
            if last_model_file.exists():
                last_model = last_model_file.read_text().strip()
                self.current_model = last_model
                log.info(f"Last model loaded: {last_model}")

                # Highlight the current model in the list
                self._update_highlight(last_model)
        except Exception as e:
            log.error(f"Failed to load last model: {e}")

    def _update_highlight(self, model_name: str):
        """Update the visual highlight for the selected model."""
        # Clear all highlights and set the selected one
        for child in self.model_list.children:
            if isinstance(child, ModelListItem):
                if child.model_name == model_name:
                    child.bg_color = (0.2, 0.6, 0.6, 0.3)  # Teal highlight
                else:
                    child.bg_color = (0, 0, 0, 0)  # Transparent (no highlight)
