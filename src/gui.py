import os
import json
from functools import partial
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from state import channel_state
from setup import setup_controls

MODELS_DIR = "models"


class AxisSlider(Widget):
    value = NumericProperty(0.0)
    axis_name = StringProperty("")
    control_name = StringProperty("")


class ModelSelector(BoxLayout):
    selected_model = StringProperty("")
    dropdown = ObjectProperty(None)  # Define as property

    def __init__(self, **kwargs):
        # Initialize dropdown before super().__init__
        self.dropdown = DropDown()
        super().__init__(**kwargs)

        # Bind the dropdown selection
        self.dropdown.bind(on_select=self._on_select)

        # Create initial dropdown items
        self.refresh_models()

    def on_kv_post(self, base_widget):
        # Bind the dropdown to the button after KV rules are applied
        if self.ids.model_button:
            self.ids.model_button.bind(on_release=self.dropdown.open)

    def refresh_models(self, *args):
        """Refresh the list of available models"""
        self.dropdown.clear_widgets()
        models = self.get_available_models()

        for model_name in models:
            btn = Button(text=model_name, size_hint_y=None, height=44)
            btn.bind(on_release=lambda btn: self.dropdown.select(btn.text))
            self.dropdown.add_widget(btn)

    def _on_select(self, instance, model_name):
        """Called when a model is selected from the dropdown"""
        if hasattr(self, "ids") and "model_button" in self.ids:
            self.ids.model_button.text = model_name
        self.load_model(model_name)
        self.selected_model = model_name

    def get_available_models(self):
        """Get list of available models"""
        if not os.path.exists(MODELS_DIR):
            return []
        return sorted([f[:-5] for f in os.listdir(MODELS_DIR) if f.endswith(".json")])

    def load_model(self, model_name):
        """Load the selected model"""
        try:
            # Load the model
            model_path = os.path.join(MODELS_DIR, f"{model_name}.json")
            with open(model_path, "r") as f:
                model_data = json.load(f)

            # Ensure the model has a name
            model_data["name"] = model_name

            # Save as active model
            with open("model_mapping.json", "w") as f:
                json.dump(model_data, f, indent=2)

            # Reset all channel values in the state
            for i in range(1, 11):
                channel_state.update_channel(i, 0.0)

            # Notify parent to refresh
            if self.parent and hasattr(self.parent, "on_model_changed"):
                self.parent.on_model_changed()

            # Trigger the property change properly
            self.property("selected_model").dispatch(self)

            # Update button text
            if hasattr(self, "ids") and "model_button" in self.ids:
                self.ids.model_button.text = model_name

        except Exception as e:
            print(f"Error loading model: {e}")


class ValueDisplay(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = channel_state
        # Bind to state changes
        self.state.bind(channels=self.on_state_change)

        # Create the model selector
        self.model_selector = ModelSelector()
        self.add_widget(self.model_selector)

        # Create grid for channel sliders
        from kivy.uix.gridlayout import GridLayout

        self.channel_grid = GridLayout(cols=5, spacing=10, size_hint_y=1)
        self.add_widget(self.channel_grid)

        # Bind to model changes
        self.model_selector.bind(selected_model=self.on_model_selected)

        # Load initial model if it exists
        if os.path.exists("model_mapping.json"):
            with open("model_mapping.json", "r") as f:
                try:
                    model_data = json.load(f)
                    if "name" in model_data:
                        model_name = model_data["name"]
                        self.model_selector.selected_model = model_name
                        if (
                            hasattr(self.model_selector, "ids")
                            and "model_button" in self.model_selector.ids
                        ):
                            self.model_selector.ids.model_button.text = model_name
                except Exception as e:
                    print(f"Error loading initial model: {e}")

        # Create initial sliders
        self.create_channel_sliders()

    def create_channel_sliders(self):
        """Create sliders based on the model mapping configuration"""
        try:
            with open("model_mapping.json", "r") as f:
                mapping = json.load(f)
        except FileNotFoundError:
            print("No model mapping found!")
            return

        # Clear existing sliders
        self.channel_grid.clear_widgets()
        self.slider_refs = {}  # Clear stored references

        # Add new sliders
        for channel, config in sorted(mapping["channels"].items()):
            slider = AxisSlider()
            slider.id = f"ch{channel}"
            slider.axis_name = f"CH{channel}"
            slider.control_name = config["control_name"]
            self.channel_grid.add_widget(slider)
            self.slider_refs[slider.id] = slider  # Store reference

    def on_model_selected(self, instance, value):
        """Called when a new model is selected"""
        self.create_channel_sliders()

    def on_model_changed(self, *args):
        """Called when model content changes"""
        self.create_channel_sliders()

    def on_state_change(self, instance, value):
        """Called when channel_values changes in state"""
        for channel, val in value.items():
            slider_id = f"ch{channel}"
            if slider_id in self.slider_refs:
                self.slider_refs[slider_id].value = val

    def update_channel(self, channel: int, value: float):
        """Update the value for a specific channel

        Args:
            channel: Channel number (1-10)
            value: Normalized value (-1 to 1)
        """
        if 1 <= channel <= 10:
            self.state.update_channel(channel, value)


class ControllerApp(App):
    def __init__(self, input_controller, **kwargs):
        super().__init__(**kwargs)
        self.input_controller = input_controller
        self.display = None
        self.state = channel_state

    def build(self):
        Window.size = (800, 480)
        self.display = ValueDisplay()

        # Set up model change handler
        self.display.model_selector.bind(selected_model=self.on_model_change)
        return self.display

    def on_model_change(self, instance, value):
        """Handle model changes"""
        if value:  # Only handle non-empty model names
            # Clear existing callbacks
            self.input_controller.clear_callbacks()
            # Setup new control mappings
            setup_controls(self.input_controller, self)

    def update_value(self, control_id: int, value: float):
        """Update a control value in the display

        Args:
            control_id: The control ID (1-10)
            value: The normalized value for the control
        """
        if self.display:
            self.display.update_channel(control_id, value)


def create_gui(input_controller):
    """Create and run the GUI application"""
    app = ControllerApp(input_controller)
    return app
