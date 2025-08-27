import os
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from state import channel_state

MODELS_DIR = "models"


class AxisSlider(Widget):
    value = NumericProperty(0.0)
    axis_name = StringProperty("")
    control_name = StringProperty("")


class ModelSelector(BoxLayout):
    selected_model = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = 50
        self.padding = 10
        self.spacing = 10

        # Create the dropdown button
        self.dropdown = DropDown()
        self.dropdown_button = Button(text="Select Model", size_hint_y=None, height=40)
        self.dropdown_button.bind(on_release=self.dropdown.open)

        # Add a label
        self.add_widget(
            Label(
                text="Model:", size_hint=(None, None), size=(100, 40), valign="middle"
            )
        )

        # Add the dropdown button
        self.add_widget(self.dropdown_button)

        # Populate the dropdown
        self.refresh_models()

    def refresh_models(self, *args):
        """Refresh the list of available models"""
        self.dropdown.clear_widgets()

        # Get available models
        models = self.get_available_models()

        for model_name in models:
            btn = Button(text=model_name, size_hint_y=None, height=44)
            btn.bind(on_release=lambda btn: self.select_model(btn.text))
            self.dropdown.add_widget(btn)

    def select_model(self, model_name):
        """Select a model and load it"""
        self.dropdown.dismiss()
        self.dropdown_button.text = model_name
        self.selected_model = model_name
        self.load_model(model_name)

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

            # Save as active model
            with open("model_mapping.json", "w") as f:
                json.dump(model_data, f, indent=2)

            # Notify parent to refresh
            if hasattr(self.parent, "on_model_changed"):
                self.parent.on_model_changed()

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
        grid = self.ids.channel_grid
        grid.clear_widgets()
        self.ids.clear()  # Clear stored references

        # Add new sliders
        for channel, config in sorted(mapping["channels"].items()):
            slider = AxisSlider()
            slider.id = f"ch{channel}"
            slider.axis_name = f"CH{channel}"
            slider.control_name = config["control_name"]
            grid.add_widget(slider)
            self.ids[slider.id] = slider

    def on_model_changed(self, *args):
        """Called when a new model is selected"""
        self.create_channel_sliders()

    def on_state_change(self, instance, value):
        """Called when channel_values changes in state"""
        for channel, val in value.items():
            slider_id = f"ch{channel}"
            if slider_id in self.ids:
                self.ids[slider_id].value = val

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
        return self.display

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
