from __future__ import annotations

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase
from kivy.metrics import dp
import uuid
from pathlib import Path

from .dialogs.model_create_dialog import ModelCreateDialog
from .dialogs.model_remove_dialog import ModelRemoveDialog
from .....infrastructure.file_cache import load_json, save_json


class ModelsTab(MDBoxLayout, MDTabsBase):
    """Tab for model selection and management (FAB removed)."""

    def __init__(self, app=None, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.title = "Models"
        self.icon = "folder-multiple"
        self.app = app
        self.size_hint = (1, 1)
        self.spacing = 0
        self.padding = 0

        self.remove_dialog = None
        self.create_dialog = None

        self._selected_models = set()
        self._table_data = []

        # Layout container (previously held FAB; now table only)
        self._float_layout = MDFloatLayout()

        # Create the data table immediately
        self._create_data_table()

        # FAB removed; placeholder attribute to avoid attribute errors
        self._fab = None

        # Add the float layout to the main container
        self.add_widget(self._float_layout)

        # FAB state logic removed (no-op retained for compatibility)
        self._update_fab_state()

    def _create_data_table(self):
        """Create the data table as the main content."""
        # Prepare table data
        self._table_data = []
        self._update_table_data()

        # Create data table
        self._data_table = MDDataTable(
            use_pagination=False,
            check=True,  # Enable built-in checkboxes
            rows_num=50,  # Set high enough to show all models without pagination
            column_data=[
                ("Model Name", dp(60)),
                ("RX Number", dp(25)),
                ("Model Index", dp(30)),
                ("Channels", dp(25)),
            ],
            row_data=self._table_data,
        )

        # Bind to row selection and checkbox events
        self._data_table.bind(on_row_press=self._on_row_selected)
        self._data_table.bind(on_check_press=self._on_checkbox_press)

        # Add table to the float layout
        self._float_layout.add_widget(self._data_table)

    def _update_table_data(self):
        """Update the table data with current models."""
        self._table_data.clear()

        if not self.app or not self.app.available_models:
            # Show placeholder when no models
            self._table_data.append(
                (
                    "No models found",
                    "-",
                    "-",
                    "-",
                )
            )
            return

            # Add each model to the table
        for model_name in self.app.available_models:
            try:
                # Load model data to get details
                model_file = Path("models") / f"{model_name}.json"
                if model_file.exists():
                    model_data = load_json(str(model_file))
                    rx_num = model_data.get("rx_num", "?")
                    model_index = model_data.get("model_index", "?")
                    channels = len(model_data.get("channels", {}))
                else:
                    rx_num = "?"
                    model_index = "?"
                    channels = "?"

                row_data = (
                    model_name,
                    str(rx_num),
                    str(model_index),
                    str(channels),
                )
                self._table_data.append(row_data)

            except Exception as e:
                # Fallback for corrupted model files
                row_data = (
                    model_name,
                    "?",
                    "?",
                    "?",
                )
                self._table_data.append(row_data)

    def set_app(self, app):
        """Set the app reference after initialization."""
        self.app = app
        self.refresh_models()
        if hasattr(app, "bind"):
            app.bind(on_model_selected=self._on_model_changed)

    def refresh_models(self):
        """Refresh the model table display."""
        if not self.app:
            return

        # Get available models
        if not self.app.available_models:
            self.app.refresh_models()

        # Update table data and refresh display
        self._update_table_data()
        self._data_table.row_data = self._table_data

        # Clear selection when refreshing
        self._selected_models.clear()

        # Update FAB state after refreshing
        self._update_fab_state()  # no-op

    def _on_row_selected(self, instance, row):  # noqa: D401
        """Handle row selection in the data table."""
        # Row selection is now just for display - model activation is separate
        pass

    def _on_checkbox_press(self, instance, current_row):  # noqa: D401
        """Handle checkbox press for model selection."""
        if not isinstance(current_row, (list, tuple)) or len(current_row) == 0:
            return

        display_name = current_row[0]

        # Skip placeholder rows
        if display_name == "No models found":
            return

        # Toggle selection
        if display_name in self._selected_models:
            self._selected_models.remove(display_name)
        else:
            self._selected_models.add(display_name)

        # Update FAB state
        self._update_fab_state()  # no-op

    def _update_fab_state(self):  # noqa: D401
        """FAB removed: no-op retained for compatibility."""
        return

    def _on_model_changed(self, app, model_name):
        """Called when a model is selected to refresh the display."""
        self.refresh_models()

    def _refresh_table(self, *args):
        """Refresh the table data and update display."""
        self._update_table_data()
        self._data_table.row_data = self._table_data
        # Clear selection when refreshing
        self._selected_models.clear()
        self._update_fab_state()  # no-op

    def _show_remove_model_dialog(self, *args):
        """Show confirmation dialog to remove the selected models."""
        if not self._selected_models:
            return

        # For now, handle single selection (can be extended for multiple)
        selected_model = next(iter(self._selected_models))  # Get first item from set

        # Create dialog if it doesn't exist
        if not self.remove_dialog:
            self.remove_dialog = ModelRemoveDialog(
                on_confirm=self._remove_selected_model,
                on_cancel=self._close_remove_dialog,
            )

        self.remove_dialog.show_dialog(selected_model)

    def _close_remove_dialog(self, *args):
        """Close the remove model dialog."""
        if self.remove_dialog:
            self.remove_dialog.close_dialog()
        return True

    def _remove_selected_model(self, *args):
        """Remove the selected models."""
        if not self._selected_models or not self.app:
            self._close_remove_dialog()
            return

        try:
            removed_models = self._selected_models.copy()  # Copy before clearing

            # Remove all selected models
            for model_name in self._selected_models:
                model_file = Path("models") / f"{model_name}.json"
                if model_file.exists():
                    model_file.unlink()  # Delete the file

            # Clear selection after removal
            self._selected_models.clear()

            # Clear current selection if it was one of the removed models
            if (
                hasattr(self.app, "selected_model")
                and self.app.selected_model in removed_models
            ):
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

        self._close_remove_dialog()

    def _show_create_model_dialog(self, *args):
        """Show a dialog to create a new model with name input."""
        # Create dialog if it doesn't exist
        if not self.create_dialog:
            self.create_dialog = ModelCreateDialog(
                on_confirm=self._save_new_model,
                on_cancel=self._close_create_dialog,
                existing_models=self.app.available_models if self.app else [],
            )

        # Update existing models list
        if self.app:
            self.create_dialog.update_existing_models(self.app.available_models)

        self.create_dialog.show_dialog()

    def _close_create_dialog(self, *args):
        """Close the create model dialog."""
        if self.create_dialog:
            self.create_dialog.close_dialog()
        return True

    def _save_new_model(self, model_name):
        """Save the new model with the entered name."""
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

            save_json(str(model_file), model_data)

            # Refresh the app's model list and UI
            self.app.refresh_models()
            self.refresh_models()

            # Close the dialog
            self._close_create_dialog()

        except Exception as e:
            print(f"Error saving model: {str(e)}")
            # The dialog will handle displaying this error
            return False

        return True

    def _allocate_rx_num(self):
        """Allocate an unused RX number (0-15)."""
        used = set()
        models_dir = Path("models")
        if models_dir.exists():
            for model_file in models_dir.glob("*.json"):
                try:
                    data = load_json(str(model_file))
                    if data and "rx_num" in data:
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
                    data = load_json(str(model_file))
                    if data and "model_index" in data:
                        used.add(int(data["model_index"]))
                except Exception:
                    continue

        idx = 1
        while idx in used:
            idx += 1
        return idx

    # New action provider for global FAB menu
    def get_actions(self):  # pragma: no cover (UI integration)
        """Return list of unique action dicts for this tab.

        Each action: { 'text': str, 'callback': callable }
        Text values are unique across tabs for testing.
        """
        return [
            {
                "text": "Models: Create New",
                "callback": self._show_create_model_dialog,
                "icon": "plus-box",
            },
            {
                "text": "Models: Remove Selected",
                "callback": self._show_remove_model_dialog,
                "icon": "delete-forever",
            },
            {
                "text": "Models: Refresh",
                "callback": self.refresh_models,
                "icon": "refresh",
            },
        ]
